import subprocess
import sys
from pathlib import Path

from run_lifecycle import APPLY_MOCK_MODE, DRY_RUN_MODE, run_lifecycle

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG_FILE = PROJECT_ROOT / "logs" / "jml_audit.jsonl"


MENU_TEXT = """JML Portfolio CLI
1) Run dry-run lifecycle
2) Apply mock AD changes
3) Run tests
4) Show latest audit-log lines
5) Exit"""


def run_tests() -> int:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_*.py",
    ]
    result = subprocess.run(command, cwd=str(PROJECT_ROOT))
    return result.returncode


def run_dry_run() -> None:
    run_lifecycle(mode=DRY_RUN_MODE)


def run_apply_mock() -> None:
    run_lifecycle(mode=APPLY_MOCK_MODE)


def show_latest_audit_lines(line_count=10) -> None:
    if not AUDIT_LOG_FILE.exists():
        print("No audit log found.")
        return

    with AUDIT_LOG_FILE.open(mode="r", encoding="utf-8") as file:
        lines = file.readlines()[-line_count:]

    for line in lines:
        print(line.rstrip())


def main() -> None:
    while True:
        print(MENU_TEXT)
        choice = input("Select an option: ").strip()

        if choice == "1":
            run_dry_run()
        elif choice == "2":
            run_apply_mock()
        elif choice == "3":
            run_tests()
        elif choice == "4":
            show_latest_audit_lines()
        elif choice == "5":
            break
        else:
            print("Invalid option. Choose 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()