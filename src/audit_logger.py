import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIRECTORY = PROJECT_ROOT / "logs"


def write_audit_event(
    run_id: str,
    event_type: str,
    employee_id: str,
    email: str,
    action: str,
    target_system: str,
    status: str,
    mode: str = "DRY_RUN",
    details: Optional[Dict[str, Any]] = None,
    log_file: Optional[Path] = None,
) -> None:
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if log_file is None:
        log_file = LOG_DIRECTORY / "jml_audit.jsonl"

    audit_event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "event_type": event_type,
        "employee_id": employee_id,
        "email": email,
        "action": action,
        "target_system": target_system,
        "status": status,
        "mode": mode,
        "details": details or {},
    }

    with log_file.open(mode="a", encoding="utf-8") as file:
        file.write(json.dumps(audit_event) + "\n")


def create_run_id() -> str:
    return str(uuid4())