import json
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RBAC_FILE = PROJECT_ROOT / "config" / "rbac_mapping.json"


def load_rbac_mapping(mapping_path: Path = RBAC_FILE) -> Dict[str, Any]:
    with mapping_path.open(mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_required_groups(
    department: str,
    role: str,
    mapping: Dict[str, Any],
) -> Dict[str, List[str]]:
    department_policy = mapping.get(department)

    if not department_policy:
        raise ValueError(
            f"No RBAC policy exists for department: '{department}'. "
            "Do not provision access until IAM approves a mapping."
        )

    role_policy = department_policy["roles"].get(role)

    if not role_policy:
        raise ValueError(
            f"No RBAC policy exists for role: '{role}' "
            f"in department '{department}'. "
            "Do not provision access until IAM approves a mapping."
        )

    ad_groups = sorted(
        set(
            department_policy["default_ad_groups"]
            + role_policy["ad_groups"]
        )
    )

    entra_groups = sorted(
        set(
            department_policy["default_entra_groups"]
            + role_policy["entra_groups"]
        )
    )

    return {
        "ad_groups": ad_groups,
        "entra_groups": entra_groups,
    }


def get_managed_ad_groups(mapping: Dict[str, Any]) -> List[str]:
    managed_groups = set()

    for department_policy in mapping.values():
        managed_groups.update(department_policy.get("default_ad_groups", []))

        for role_policy in department_policy.get("roles", {}).values():
            managed_groups.update(role_policy.get("ad_groups", []))

    return sorted(managed_groups)