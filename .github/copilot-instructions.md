# Identity Lifecycle Automation - Project Instructions

## Project goal
Build a portfolio-ready Joiner-Mover-Leaver IAM automation project using Python.
Current development is local and safe: use mock data only unless explicitly told otherwise.

## Security rules
- Default to DRY_RUN mode.
- Never connect to, create, modify, disable, delete, or query a real Active Directory, Entra ID tenant, AWS account, or production-like system without an explicit user instruction.
- Never hardcode passwords, access tokens, client secrets, API keys, or connection strings.
- Never print or log secrets.
- Keep `.env`, `.venv/`, logs, local state, and `__pycache__/` out of Git.
- Treat the mock AD JSON directory as read-only unless a task explicitly asks for a controlled simulation write.
- Do not use destructive terminal commands such as `rm -rf`, `rmdir /s`, `del /s`, git reset, git clean, or force push.

## Python compatibility
- Maintain Python 3.8/3.9 compatibility.
- Do not use `X | None`, `list[str]`, `dict[str, str]`, or other Python 3.10+ typing syntax.
- Use `Optional`, `List`, `Dict`, and `Any` from `typing`.

## IAM design rules
- HR CSV/JSON is the identity source of truth.
- `employee_id` is the immutable identity correlation key.
- RBAC mapping determines approved access based on department and role.
- Enforce least privilege and deny unsafe/unmapped roles.
- Reconcile actual directory groups against desired RBAC groups.
- Never remove groups outside an explicit JML-managed group registry.
- Disable before cleanup for leaver actions.
- Maintain timestamped JSONL audit events with run_id, lifecycle event, employee ID, action, system, status, mode, and non-secret details.
- Valid statuses include PLANNED, BLOCKED, SKIPPED, NOT_FOUND, SUCCESS, and FAILED.

## Code quality
- Inspect existing files before editing.
- Make focused changes; do not rewrite unrelated files.
- Use clear function names and small functions.
- Add or update tests when changing lifecycle logic.
- Run relevant tests after edits.
- Report files changed, tests run, results, and any assumptions.