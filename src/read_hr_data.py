from __future__ import annotations

import csv
from pathlib import Path

from rbac import get_required_groups, load_rbac_mapping

REQUIRED_FIELDS = {
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "department",
    "role",
    "status",
    "manager_email",
    "effective_date",
}

ALLOWED_STATUSES = {"active", "leave", "terminated"}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HR_FILE = PROJECT_ROOT / "data" / "hr_users.csv"


def validate_user(user: dict[str, str], row_number: int) -> None:
    missing_fields = REQUIRED_FIELDS - user.keys()
    if missing_fields:
        raise ValueError(
            f"Row {row_number}: missing CSV columns: {sorted(missing_fields)}"
        )

    empty_fields = [
        field for field in REQUIRED_FIELDS
        if not user.get(field, "").strip()
    ]
    if empty_fields:
        raise ValueError(
            f"Row {row_number}: empty required values: {empty_fields}"
        )

    user["status"] = user["status"].strip().lower()

    if user["status"] not in ALLOWED_STATUSES:
        raise ValueError(
            f"Row {row_number}: invalid status '{user['status']}'. "
            f"Use one of: {sorted(ALLOWED_STATUSES)}"
        )

    if "@" not in user["email"]:
        raise ValueError(
            f"Row {row_number}: invalid email address '{user['email']}'"
        )


def read_hr_users(csv_path: Path) -> list[dict[str, str]]:
    users: list[dict[str, str]] = []

    with csv_path.open(mode="r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row_number, user in enumerate(reader, start=2):
            cleaned_user = {
                key: value.strip() if value else ""
                for key, value in user.items()
            }

            validate_user(cleaned_user, row_number)
            users.append(cleaned_user)

    return users


if __name__ == "__main__":
    users = read_hr_users(HR_FILE)
    mapping = load_rbac_mapping()

    print(f"Loaded {len(users)} HR records from: {HR_FILE.name}\n")

    for user in users:
        print(
            f"{user['employee_id']} | "
            f"{user['first_name']} {user['last_name']} | "
            f"status={user['status']}"
        )

        if user["status"] == "active":
            try:
                groups = get_required_groups(
                    department=user["department"],
                    role=user["role"],
                    mapping=mapping,
                )

                print(f"  AD groups: {', '.join(groups['ad_groups'])}")
                print(f"  Entra groups: {', '.join(groups['entra_groups'])}")

            except ValueError as error:
                print(f"  POLICY BLOCKED: {error}")

        else:
            print("  No new access calculated because the user is not active.")

        print()