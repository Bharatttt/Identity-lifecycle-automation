import json
from contextlib import redirect_stdout
from io import StringIO
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from action_planner import build_action_plan
from mock_ad_connector import MockActiveDirectoryConnector
from rbac import load_rbac_mapping
from run_lifecycle import APPLY_MOCK_MODE, run_lifecycle


class GroupReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = load_rbac_mapping()
        self.base_connector = MockActiveDirectoryConnector()

    def test_mover_uses_actual_mock_ad_memberships_and_keeps_unmanaged_groups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory_path = Path(temp_dir) / "ad_directory.json"

            with (PROJECT_ROOT / "mock_data" / "ad_directory.json").open(
                mode="r",
                encoding="utf-8",
            ) as source_file:
                directory = json.load(source_file)

            for user in directory["users"]:
                if user["employee_id"] == "E1002":
                    user["groups"] = [
                        "GG-All-Employees",
                        "GG-Finance",
                        "GG-Finance-Analysts",
                        "GG-Finance-Reporting",
                        "GG-Sales",
                        "GG-Shadow-Access",
                    ]

            with directory_path.open(mode="w", encoding="utf-8") as target_file:
                json.dump(directory, target_file, indent=2)

            connector = MockActiveDirectoryConnector(directory_file=directory_path)
            event = {
                "event_type": "MOVER",
                "employee_id": "E1002",
                "email": "meera.iyer@example.com",
                "current_user": {
                    "employee_id": "E1002",
                    "department": "Engineering",
                    "role": "QA Engineer",
                    "email": "meera.iyer@example.com",
                    "status": "active",
                },
                "previous_user": {
                    "employee_id": "E1002",
                    "department": "Finance",
                    "role": "Financial Analyst",
                    "email": "meera.iyer@example.com",
                    "status": "active",
                },
                "changes": {
                    "department": {"before": "Finance", "after": "Engineering"},
                    "role": {"before": "Financial Analyst", "after": "QA Engineer"},
                },
            }

            actions = build_action_plan(event, self.mapping, connector=connector)
            ad_actions = [
                action for action in actions
                if action["target_system"] == "ACTIVE_DIRECTORY"
            ]

            self.assertEqual(ad_actions[0]["action"], "UPDATE_USER_ATTRIBUTES")
            self.assertEqual(
                [action["group"] for action in ad_actions if action["action"] == "ADD_GROUP_MEMBERSHIP"],
                ["GG-Engineering", "GG-QA-Engineers", "GG-Test-Environment"],
            )
            self.assertEqual(
                [action["group"] for action in ad_actions if action["action"] == "REMOVE_GROUP_MEMBERSHIP"],
                ["GG-Finance", "GG-Finance-Analysts", "GG-Finance-Reporting", "GG-Sales"],
            )
            self.assertNotIn(
                "GG-Shadow-Access",
                [action.get("group") for action in ad_actions if action.get("group")],
            )

    def test_leaver_missing_mock_ad_account_is_not_found_or_skipped(self):
        event = {
            "event_type": "LEAVER",
            "employee_id": "E9999",
            "email": "missing.person@example.com",
            "current_user": {
                "employee_id": "E9999",
                "department": "Finance",
                "role": "Financial Analyst",
                "email": "missing.person@example.com",
                "status": "terminated",
            },
            "previous_user": None,
            "changes": {},
        }

        actions = build_action_plan(event, self.mapping, connector=self.base_connector)

        self.assertEqual(actions[0]["status"], "NOT_FOUND")
        self.assertEqual(actions[1]["status"], "SKIPPED")

    def test_apply_mock_moves_e1002_and_preserves_unmanaged_groups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            directory_path = temp_root / "ad_directory.json"
            backup_root = temp_root / "backups"
            audit_log_file = temp_root / "jml_audit.jsonl"

            with (PROJECT_ROOT / "mock_data" / "ad_directory.json").open(
                mode="r",
                encoding="utf-8",
            ) as source_file:
                directory = json.load(source_file)

            for user in directory["users"]:
                if user["employee_id"] == "E1002":
                    user["groups"].append("GG-Shadow-Access")

            with directory_path.open(mode="w", encoding="utf-8") as target_file:
                json.dump(directory, target_file, indent=2)

            with redirect_stdout(StringIO()):
                run_lifecycle(
                    mode=APPLY_MOCK_MODE,
                    directory_file=directory_path,
                    audit_log_file=audit_log_file,
                    backup_root=backup_root,
                )

            with directory_path.open(mode="r", encoding="utf-8") as result_file:
                result = json.load(result_file)

            e1002 = next(user for user in result["users"] if user["employee_id"] == "E1002")

            self.assertTrue(e1002["enabled"])
            self.assertEqual(e1002["department"], "Engineering")
            self.assertEqual(e1002["title"], "QA Engineer")
            self.assertIn("GG-Engineering", e1002["groups"])
            self.assertIn("GG-QA-Engineers", e1002["groups"])
            self.assertIn("GG-Test-Environment", e1002["groups"])
            self.assertIn("GG-Shadow-Access", e1002["groups"])
            self.assertNotIn("GG-Finance", e1002["groups"])
            self.assertNotIn("GG-Finance-Analysts", e1002["groups"])
            self.assertNotIn("GG-Finance-Reporting", e1002["groups"])

    def test_apply_mock_disables_leaver_account(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            directory_path = temp_root / "ad_directory.json"
            backup_root = temp_root / "backups"
            audit_log_file = temp_root / "jml_audit.jsonl"

            with (PROJECT_ROOT / "mock_data" / "ad_directory.json").open(
                mode="r",
                encoding="utf-8",
            ) as source_file:
                directory = json.load(source_file)

            directory["users"].append(
                {
                    "employee_id": "E1003",
                    "sam_account_name": "test.rohan",
                    "user_principal_name": "test.rohan@lab.example.local",
                    "display_name": "Rohan Das (Test)",
                    "email": "test.rohan@lab.example.local",
                    "department": "Sales",
                    "title": "Account Executive",
                    "enabled": True,
                    "groups": [
                        "GG-All-Employees",
                        "GG-Sales",
                        "GG-Sales-Account-Executives",
                        "GG-CRM-Users",
                        "GG-Shadow-Access",
                    ],
                }
            )

            with directory_path.open(mode="w", encoding="utf-8") as target_file:
                json.dump(directory, target_file, indent=2)

            with redirect_stdout(StringIO()):
                run_lifecycle(
                    mode=APPLY_MOCK_MODE,
                    directory_file=directory_path,
                    audit_log_file=audit_log_file,
                    backup_root=backup_root,
                )

            with directory_path.open(mode="r", encoding="utf-8") as result_file:
                result = json.load(result_file)

            e1003 = next(user for user in result["users"] if user["employee_id"] == "E1003")

            self.assertFalse(e1003["enabled"])
            self.assertIn("GG-Shadow-Access", e1003["groups"])
            self.assertNotIn("GG-Sales", e1003["groups"])
            self.assertNotIn("GG-Sales-Account-Executives", e1003["groups"])
            self.assertNotIn("GG-CRM-Users", e1003["groups"])

    def test_apply_mock_rolls_back_on_simulated_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            directory_path = temp_root / "ad_directory.json"
            backup_root = temp_root / "backups"
            audit_log_file = temp_root / "jml_audit.jsonl"

            with (PROJECT_ROOT / "mock_data" / "ad_directory.json").open(
                mode="r",
                encoding="utf-8",
            ) as source_file:
                original_directory = json.load(source_file)

            with directory_path.open(mode="w", encoding="utf-8") as target_file:
                json.dump(original_directory, target_file, indent=2)

            original_copy = json.loads(json.dumps(original_directory))

            def failing_add_group_membership(self, employee_id, group_name):
                if group_name == "GG-QA-Engineers":
                    raise RuntimeError("simulated write failure")

                return original_add_group_membership(self, employee_id, group_name)

            original_add_group_membership = MockActiveDirectoryConnector.add_group_membership

            with patch.object(
                MockActiveDirectoryConnector,
                "add_group_membership",
                failing_add_group_membership,
            ):
                with redirect_stdout(StringIO()):
                    run_lifecycle(
                        mode=APPLY_MOCK_MODE,
                        directory_file=directory_path,
                        audit_log_file=audit_log_file,
                        backup_root=backup_root,
                    )

            with directory_path.open(mode="r", encoding="utf-8") as result_file:
                restored_directory = json.load(result_file)

            self.assertEqual(restored_directory, original_copy)

            with audit_log_file.open(mode="r", encoding="utf-8") as audit_file:
                audit_log = audit_file.read()

            self.assertIn('"status": "FAILED"', audit_log)
            self.assertIn('"status": "ROLLED_BACK"', audit_log)


if __name__ == "__main__":
    unittest.main()