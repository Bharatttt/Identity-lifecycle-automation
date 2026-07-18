import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOCK_AD_FILE = PROJECT_ROOT / "mock_data" / "ad_directory.json"


class MockActiveDirectoryConnector:
    def __init__(self, directory_file: Path = MOCK_AD_FILE) -> None:
        self.directory_file = directory_file
        self.directory = self._load_directory()

    def _load_directory(self) -> Dict[str, Any]:
        with self.directory_file.open(mode="r", encoding="utf-8") as file:
            return json.load(file)

    def find_user_by_employee_id(
        self,
        employee_id: str,
    ) -> Optional[Dict[str, Any]]:
        for user in self.directory["users"]:
            if user["employee_id"] == employee_id:
                return user

        return None

    def find_group_by_name(self, group_name: str) -> Optional[Dict[str, str]]:
        if group_name in self.directory["groups"]:
            return {
                "name": group_name,
                "distinguished_name": (
                    f"CN={group_name},OU=Groups,"
                    "OU=JML-Test,DC=lab,DC=example,DC=local"
                ),
            }

        return None

    def get_user_groups(self, employee_id: str) -> List[str]:
        user = self.find_user_by_employee_id(employee_id)

        if not user:
            return []

        return sorted(user["groups"])

    def save_directory(self, directory_file: Optional[Path] = None) -> None:
        target_file = directory_file or self.directory_file
        with target_file.open(mode="w", encoding="utf-8") as file:
            json.dump(self.directory, file, indent=2)

    def create_timestamped_backup(self, backup_root: Path) -> Path:
        backup_root.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_file = backup_root / f"ad_directory_{timestamp}.json"
        shutil.copy2(self.directory_file, backup_file)
        return backup_file

    def restore_from_backup(self, backup_file: Path) -> None:
        shutil.copy2(backup_file, self.directory_file)
        self.directory = self._load_directory()

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        employee_id = user_data["employee_id"]

        if self.find_user_by_employee_id(employee_id):
            raise ValueError("Mock AD user already exists")

        email = user_data.get("email", employee_id.lower())
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        display_name = user_data.get("display_name")
        if not display_name:
            display_name = (first_name + " " + last_name).strip()
            if display_name:
                display_name = f"{display_name} (Test)"
            else:
                display_name = f"{employee_id} (Test)"

        new_user = {
            "employee_id": employee_id,
            "sam_account_name": user_data.get("sam_account_name", email.split("@")[0]),
            "user_principal_name": user_data.get("user_principal_name", email),
            "display_name": display_name,
            "email": email,
            "department": user_data.get("department", ""),
            "title": user_data.get("role", user_data.get("title", "")),
            "enabled": True,
            "groups": [],
        }

        self.directory["users"].append(new_user)
        return new_user

    def update_user_attributes(
        self,
        employee_id: str,
        attributes: Dict[str, Any],
    ) -> None:
        user = self.find_user_by_employee_id(employee_id)

        if not user:
            raise ValueError("Mock AD user not found")

        if "department" in attributes:
            user["department"] = attributes["department"]

        if "role" in attributes:
            user["title"] = attributes["role"]

        if "title" in attributes:
            user["title"] = attributes["title"]

        if "enabled" in attributes:
            user["enabled"] = attributes["enabled"]

    def add_group_membership(self, employee_id: str, group_name: str) -> None:
        user = self.find_user_by_employee_id(employee_id)

        if not user:
            raise ValueError("Mock AD user not found")

        if group_name not in user["groups"]:
            user["groups"].append(group_name)
            user["groups"] = sorted(user["groups"])

    def remove_group_membership(self, employee_id: str, group_name: str) -> None:
        user = self.find_user_by_employee_id(employee_id)

        if not user:
            raise ValueError("Mock AD user not found")

        if group_name in user["groups"]:
            user["groups"].remove(group_name)

    def disable_user(self, employee_id: str) -> None:
        self.update_user_attributes(employee_id, {"enabled": False})

    def remove_managed_group_memberships(
        self,
        employee_id: str,
        managed_groups: List[str],
    ) -> List[str]:
        user = self.find_user_by_employee_id(employee_id)

        if not user:
            raise ValueError("Mock AD user not found")

        removed_groups = [
            group for group in list(user["groups"])
            if group in managed_groups
        ]

        for group in removed_groups:
            user["groups"].remove(group)

        return removed_groups