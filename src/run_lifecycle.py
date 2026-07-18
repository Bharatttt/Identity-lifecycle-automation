from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from mock_ad_connector import MOCK_AD_FILE, MockActiveDirectoryConnector
from action_planner import build_action_plan
from audit_logger import create_run_id, write_audit_event
from lifecycle import classify_all_users, load_previous_snapshot
from rbac import load_rbac_mapping
from read_hr_data import HR_FILE, read_hr_users
from rbac import get_managed_ad_groups

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = PROJECT_ROOT / "backups" / "mock_ad"
AUDIT_LOG_FILE = PROJECT_ROOT / "logs" / "jml_audit.jsonl"
DRY_RUN_MODE = "DRY_RUN"
APPLY_MOCK_MODE = "APPLY_MOCK"


def print_action(action):
    group = action.get("group")
    status = action.get("status", "PLANNED")
    details = action.get("details") or {}

    if group:
        rendered_value = group
    elif details.get("groups"):
        rendered_value = ", ".join(details["groups"])
    else:
        rendered_value = None

    if rendered_value:
        print(
            f"  {action['target_system']:<18} "
            f"{action['action']:<26} {rendered_value}"
            + ("" if status == "PLANNED" else f" [{status}]")
        )
    else:
        print(
            f"  {action['target_system']:<18} "
            f"{action['action']}"
            + ("" if status == "PLANNED" else f" [{status}]")
        )


def print_event(event):
    print(
        f"\n{event['event_type']:<10} | "
        f"{event['employee_id']} | "
        f"{event['email']}"
    )

    for field, values in event["changes"].items():
        print(
            f"  CHANGE {field}: "
            f"'{values['before']}' -> '{values['after']}'"
        )


def print_summary(event_counts, status_counts, action_count, mode) -> None:
    print("\nSummary")
    print(f"  Joiners:   {event_counts['JOINER']}")
    print(f"  Movers:    {event_counts['MOVER']}")
    print(f"  Leavers:   {event_counts['LEAVER']}")
    print(f"  Unchanged: {event_counts['UNCHANGED']}")
    if mode == DRY_RUN_MODE:
        print(f"  Planned:   {status_counts['PLANNED']}")
        print(f"  Blocked:   {status_counts['BLOCKED']}")
        print(f"  Skipped:   {status_counts['SKIPPED']}")
        print(f"  Not found: {status_counts['NOT_FOUND']}")
        print(f"  Planned actions: {action_count}")
        print("  Mode: DRY_RUN — no directory changes were made.")
    else:
        print(f"  Applied:   {status_counts['APPLIED']}")
        print(f"  Skipped:   {status_counts['SKIPPED']}")
        print(f"  Not found: {status_counts['NOT_FOUND']}")
        print(f"  Failed:    {status_counts['FAILED']}")
        print(f"  Rolled back: {status_counts['ROLLED_BACK']}")
        print(f"  Applied actions: {action_count}")
        print("  Mode: APPLY_MOCK — wrote only to mock_data/ad_directory.json.")
    print("  Audit log: logs/jml_audit.jsonl")


def _format_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _make_apply_details(event: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
    details = {
        "changes": event["changes"],
    }

    if action.get("group"):
        details["group"] = action["group"]

    if action.get("details"):
        details.update(action["details"])

    return details


def _apply_active_directory_action(
    connector: MockActiveDirectoryConnector,
    action: Dict[str, Any],
    event: Dict[str, Any],
    managed_groups: List[str],
) -> Dict[str, Any]:
    employee_id = event["employee_id"]

    if action["action"] == "CREATE_USER":
        connector.create_user(event["current_user"])
        return {"status": "APPLIED"}

    if action["action"] == "UPDATE_USER_ATTRIBUTES":
        connector.update_user_attributes(
            employee_id,
            {
                "department": event["current_user"].get("department", ""),
                "role": event["current_user"].get("role", ""),
            },
        )
        return {"status": "APPLIED"}

    if action["action"] == "ADD_GROUP_MEMBERSHIP":
        connector.add_group_membership(employee_id, action["group"])
        return {"status": "APPLIED"}

    if action["action"] == "REMOVE_GROUP_MEMBERSHIP":
        connector.remove_group_membership(employee_id, action["group"])
        return {"status": "APPLIED"}

    if action["action"] == "DISABLE_USER":
        connector.disable_user(employee_id)
        return {"status": "APPLIED"}

    if action["action"] == "REMOVE_MANAGED_GROUP_MEMBERSHIPS":
        removed_groups = connector.remove_managed_group_memberships(
            employee_id,
            managed_groups,
        )
        if removed_groups:
            return {"status": "APPLIED", "details": {"groups": removed_groups}}
        return {"status": "SKIPPED", "details": {"reason": "No managed AD groups to remove"}}

    raise ValueError(f"Unsupported APPLY_MOCK action: {action['action']}")


def run_lifecycle(
    mode: str = DRY_RUN_MODE,
    directory_file: Path = MOCK_AD_FILE,
    audit_log_file: Path = AUDIT_LOG_FILE,
    backup_root: Path = BACKUP_ROOT,
) -> Dict[str, Any]:
    run_id = create_run_id()
    current_users = read_hr_users(HR_FILE)
    previous_users_by_id = load_previous_snapshot()
    mapping = load_rbac_mapping()
    connector = MockActiveDirectoryConnector(directory_file=directory_file)
    managed_ad_groups = get_managed_ad_groups(mapping)

    events = classify_all_users(
        current_users=current_users,
        previous_users_by_id=previous_users_by_id,
    )

    action_count = 0
    status_counts = Counter()
    backup_file = None
    abort_run = False

    print(f"\nJML {mode} | run_id={run_id}")

    if mode == APPLY_MOCK_MODE:
        print("JML APPLY_MOCK | writing only to mock_data/ad_directory.json")
        backup_file = connector.create_timestamped_backup(backup_root)
        print(f"Backup created: {_format_path(backup_file)}")

    for event in events:
        if abort_run:
            break

        print_event(event)

        try:
            actions = build_action_plan(
                event,
                mapping,
                connector=connector,
            )

            if not actions:
                print("  No directory action required.")

            for action in actions:
                if mode == DRY_RUN_MODE:
                    print_action(action)
                    status = action.get("status", "PLANNED")
                    status_counts[status] += 1
                    details = _make_apply_details(event, action)
                    write_audit_event(
                        run_id=run_id,
                        event_type=event["event_type"],
                        employee_id=event["employee_id"],
                        email=event["email"],
                        action=action["action"],
                        target_system=action["target_system"],
                        status=status,
                        mode=mode,
                        details=details,
                        log_file=audit_log_file,
                    )
                    action_count += 1
                    continue

                if action["target_system"] == "ENTRA_ID":
                    skipped_action = dict(action)
                    skipped_action["status"] = "SKIPPED"
                    print_action(skipped_action)
                    status_counts["SKIPPED"] += 1
                    write_audit_event(
                        run_id=run_id,
                        event_type=event["event_type"],
                        employee_id=event["employee_id"],
                        email=event["email"],
                        action=action["action"],
                        target_system=action["target_system"],
                        status="SKIPPED",
                        mode=mode,
                        details={
                            "reason": "Entra ID planning remains placeholder in APPLY_MOCK mode",
                            "changes": event["changes"],
                        },
                        log_file=audit_log_file,
                    )
                    continue

                if action.get("status") in ("SKIPPED", "NOT_FOUND"):
                    print_action(action)
                    status_counts[action["status"]] += 1
                    write_audit_event(
                        run_id=run_id,
                        event_type=event["event_type"],
                        employee_id=event["employee_id"],
                        email=event["email"],
                        action=action["action"],
                        target_system=action["target_system"],
                        status=action["status"],
                        mode=mode,
                        details=_make_apply_details(event, action),
                        log_file=audit_log_file,
                    )
                    continue

                try:
                    result = _apply_active_directory_action(
                        connector=connector,
                        action=action,
                        event=event,
                        managed_groups=managed_ad_groups,
                    )
                    if result["status"] == "APPLIED":
                        connector.save_directory()
                    applied_action = dict(action)
                    applied_action["status"] = result["status"]
                    if result.get("details"):
                        applied_action["details"] = result["details"]
                    print_action(applied_action)
                    status_counts[result["status"]] += 1
                    write_audit_event(
                        run_id=run_id,
                        event_type=event["event_type"],
                        employee_id=event["employee_id"],
                        email=event["email"],
                        action=action["action"],
                        target_system=action["target_system"],
                        status=result["status"],
                        mode=mode,
                        details=_make_apply_details(event, applied_action),
                        log_file=audit_log_file,
                    )
                    action_count += 1
                except Exception as error:
                    status_counts["FAILED"] += 1
                    print(f"  APPLY_MOCK FAILED: {error}")
                    write_audit_event(
                        run_id=run_id,
                        event_type=event["event_type"],
                        employee_id=event["employee_id"],
                        email=event["email"],
                        action=action["action"],
                        target_system=action["target_system"],
                        status="FAILED",
                        mode=mode,
                        details={
                            "reason": str(error),
                            "changes": event["changes"],
                        },
                        log_file=audit_log_file,
                    )
                    if backup_file is not None:
                        connector.restore_from_backup(backup_file)
                        write_audit_event(
                            run_id=run_id,
                            event_type=event["event_type"],
                            employee_id=event["employee_id"],
                            email=event["email"],
                            action="ROLLBACK",
                            target_system="MOCK_AD",
                            status="ROLLED_BACK",
                            mode=mode,
                            details={
                                "reason": "Restored mock AD from backup after failure",
                                "backup_file": str(backup_file),
                            },
                            log_file=audit_log_file,
                        )
                        status_counts["ROLLED_BACK"] += 1
                    abort_run = True
                    break

        except ValueError as error:
            status_counts["BLOCKED"] += 1
            print(f"  POLICY BLOCKED: {error}")

            write_audit_event(
                run_id=run_id,
                event_type=event["event_type"],
                employee_id=event["employee_id"],
                email=event["email"],
                action="NO_ACTION",
                target_system="JML_ENGINE",
                status="BLOCKED",
                mode=mode,
                details={
                    "reason": str(error),
                    "changes": event["changes"],
                },
                log_file=audit_log_file,
            )

    event_counts = Counter(event["event_type"] for event in events)
    print_summary(event_counts, status_counts, action_count, mode)

    return {
        "run_id": run_id,
        "event_counts": event_counts,
        "status_counts": status_counts,
        "action_count": action_count,
    }


def main() -> None:
    run_lifecycle(mode=DRY_RUN_MODE)


if __name__ == "__main__":
    main()