import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = PROJECT_ROOT / "state" / "previous_hr_snapshot.json"

TRACKED_MOVER_FIELDS = ("department", "role", "manager_email")


def load_previous_snapshot(
    state_file: Path = STATE_FILE,
) -> Dict[str, Dict[str, str]]:
    if not state_file.exists():
        return {}

    with state_file.open(mode="r", encoding="utf-8") as file:
        previous_users = json.load(file)

    return {
        user["employee_id"]: user
        for user in previous_users
    }


def classify_user(
    current_user: Dict[str, str],
    previous_user: Optional[Dict[str, str]],
) -> Tuple[str, Dict[str, Dict[str, str]]]:
    if current_user["status"] == "terminated":
        return "LEAVER", {}

    if previous_user is None:
        return "JOINER", {}

    changes = {
        field: {
            "before": previous_user.get(field, ""),
            "after": current_user.get(field, ""),
        }
        for field in TRACKED_MOVER_FIELDS
        if previous_user.get(field, "") != current_user.get(field, "")
    }

    if changes:
        return "MOVER", changes

    return "UNCHANGED", {}


def classify_all_users(
    current_users: List[Dict[str, str]],
    previous_users_by_id: Dict[str, Dict[str, str]],
) -> List[Dict[str, Any]]:
    results = []

    for current_user in current_users:
        employee_id = current_user["employee_id"]
        previous_user = previous_users_by_id.get(employee_id)

        event_type, changes = classify_user(
            current_user=current_user,
            previous_user=previous_user,
        )

        results.append(
            {
                "event_type": event_type,
                "employee_id": employee_id,
                "email": current_user["email"],
                "current_user": current_user,
                "previous_user": previous_user,
                "changes": changes,
            }
        )

    return results


def save_snapshot(
    current_users: List[Dict[str, str]],
    state_file: Path = STATE_FILE,
) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)

    with state_file.open(mode="w", encoding="utf-8") as file:
        json.dump(current_users, file, indent=2)