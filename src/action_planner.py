from typing import Any, Dict, List, Optional

from mock_ad_connector import MockActiveDirectoryConnector
from rbac import get_managed_ad_groups, get_required_groups


def _build_group_actions(
    previous_groups: List[str],
    desired_groups: List[str],
    target_system: str,
) -> List[Dict[str, Any]]:
    groups_to_add = sorted(set(desired_groups) - set(previous_groups))
    groups_to_remove = sorted(set(previous_groups) - set(desired_groups))

    actions = []

    for group in groups_to_add:
        actions.append(
            {
                "target_system": target_system,
                "action": "ADD_GROUP_MEMBERSHIP",
                "group": group,
                "status": "PLANNED",
            }
        )

    for group in groups_to_remove:
        actions.append(
            {
                "target_system": target_system,
                "action": "REMOVE_GROUP_MEMBERSHIP",
                "group": group,
                "status": "PLANNED",
            }
        )

    return actions


def _make_action(
    target_system: str,
    action: str,
    group: Optional[str] = None,
    status: str = "PLANNED",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = {
        "target_system": target_system,
        "action": action,
        "group": group,
        "status": status,
    }

    if details:
        result["details"] = details

    return result


def get_groups_for_user(
    user: Dict[str, str],
    mapping: Dict[str, Any],
) -> Dict[str, List[str]]:
    return get_required_groups(
        department=user["department"],
        role=user["role"],
        mapping=mapping,
    )


def build_action_plan(
    event: Dict[str, Any],
    mapping: Dict[str, Any],
    connector: Optional[MockActiveDirectoryConnector] = None,
) -> List[Dict[str, Any]]:
    connector = connector or MockActiveDirectoryConnector()
    managed_ad_groups = set(get_managed_ad_groups(mapping))
    event_type = event["event_type"]
    current_user = event["current_user"]
    previous_user = event["previous_user"]

    if event_type == "UNCHANGED":
        return []

    if event_type == "JOINER":
        desired_groups = get_groups_for_user(current_user, mapping)

        actions = [
            _make_action(
                target_system="ACTIVE_DIRECTORY",
                action="CREATE_USER",
            ),
            _make_action(
                target_system="ENTRA_ID",
                action="CREATE_USER",
            ),
        ]

        actions.extend(
            _build_group_actions(
                previous_groups=[],
                desired_groups=[
                    group for group in desired_groups["ad_groups"]
                    if group in managed_ad_groups
                ],
                target_system="ACTIVE_DIRECTORY",
            )
        )

        actions.extend(
            _build_group_actions(
                previous_groups=[],
                desired_groups=desired_groups["entra_groups"],
                target_system="ENTRA_ID",
            )
        )

        return actions

    if event_type == "MOVER":
        desired_groups = get_groups_for_user(current_user, mapping)
        previous_groups = get_groups_for_user(previous_user, mapping)
        actual_groups = connector.get_user_groups(current_user["employee_id"])

        actual_managed_groups = [
            group for group in actual_groups
            if group in managed_ad_groups
        ]
        desired_managed_groups = [
            group for group in desired_groups["ad_groups"]
            if group in managed_ad_groups
        ]

        actions = [
            _make_action(
                target_system="ACTIVE_DIRECTORY",
                action="UPDATE_USER_ATTRIBUTES",
            ),
            _make_action(
                target_system="ENTRA_ID",
                action="UPDATE_USER_ATTRIBUTES",
            ),
        ]

        for group in sorted(set(desired_managed_groups) - set(actual_managed_groups)):
            actions.append(
                _make_action(
                    target_system="ACTIVE_DIRECTORY",
                    action="ADD_GROUP_MEMBERSHIP",
                    group=group,
                )
            )

        for group in sorted(set(actual_managed_groups) - set(desired_managed_groups)):
            actions.append(
                _make_action(
                    target_system="ACTIVE_DIRECTORY",
                    action="REMOVE_GROUP_MEMBERSHIP",
                    group=group,
                )
            )

        actions.extend(
            _build_group_actions(
                previous_groups=previous_groups["entra_groups"],
                desired_groups=desired_groups["entra_groups"],
                target_system="ENTRA_ID",
            )
        )

        return actions

    if event_type == "LEAVER":
        actual_groups = connector.get_user_groups(current_user["employee_id"])
        managed_groups_to_remove = [
            group for group in actual_groups
            if group in managed_ad_groups
        ]

        if not connector.find_user_by_employee_id(current_user["employee_id"]):
            return [
                _make_action(
                    target_system="ACTIVE_DIRECTORY",
                    action="DISABLE_USER",
                    status="NOT_FOUND",
                    details={"reason": "Mock AD account not found"},
                ),
                _make_action(
                    target_system="ACTIVE_DIRECTORY",
                    action="REMOVE_MANAGED_GROUP_MEMBERSHIPS",
                    status="SKIPPED",
                    details={"reason": "Mock AD account not found"},
                ),
            ]

        actions = [
            _make_action(
                target_system="ACTIVE_DIRECTORY",
                action="DISABLE_USER",
            ),
        ]

        if managed_groups_to_remove:
            actions.append(
                _make_action(
                    target_system="ACTIVE_DIRECTORY",
                    action="REMOVE_MANAGED_GROUP_MEMBERSHIPS",
                    details={"groups": sorted(managed_groups_to_remove)},
                )
            )
        else:
            actions.append(
                _make_action(
                    target_system="ACTIVE_DIRECTORY",
                    action="REMOVE_MANAGED_GROUP_MEMBERSHIPS",
                    status="SKIPPED",
                    details={"reason": "No managed AD groups to remove"},
                )
            )

        return actions

    raise ValueError(f"Unsupported lifecycle event: {event_type}")