# Identity Lifecycle Automation

Portfolio-ready Joiner-Mover-Leaver automation in Python, designed for local mock-data execution only.

## Project Purpose

This project demonstrates a safe IAM lifecycle workflow that reads HR data, classifies identities as joiners, movers, leavers, or unchanged, and plans directory actions in dry-run mode. It is intentionally scoped for portfolio work and does not connect to any real directory or cloud identity system.

## Architecture Summary

- `data/hr_users.csv` is the HR source of truth.
- `state/previous_hr_snapshot.json` holds the prior HR snapshot used for lifecycle classification.
- `config/rbac_mapping.json` defines department and role-based access.
- `mock_data/ad_directory.json` simulates Active Directory users and groups.
- `src/lifecycle.py` classifies identities.
- `src/action_planner.py` builds lifecycle actions.
- `src/mock_ad_connector.py` reads mock AD state.
- `src/audit_logger.py` writes JSONL audit events.
- `src/run_lifecycle.py` executes the dry-run workflow.
- `src/cli.py` provides a simple menu entrypoint.

## JML, RBAC, Least Privilege, and Audit Logging

The workflow follows Joiner-Mover-Leaver principles and uses RBAC to determine approved access from department and role. Least privilege is enforced by planning only the groups that the mapping explicitly approves. Audit entries are written as JSONL with run metadata, event type, employee ID, action, target system, status, and non-secret details.

## Managed Group Registry

The managed AD group registry is derived from the AD group names in `config/rbac_mapping.json` by collecting each department’s default AD groups and each role’s AD groups. Only groups in that registry can be removed during reconciliation. Any group outside that registry is treated as unmanaged and left untouched.

## How To Run The CLI

Run the menu entrypoint:

```bash
python src/cli.py
```

Menu options:

1. Run dry-run lifecycle
2. Apply mock AD changes
3. Run tests
4. Show latest audit-log lines
5. Exit

You can also run the dry-run directly:

```bash
python src/run_lifecycle.py
```

## Current Operating Mode

AD reconciliation is mock-based only. The workflow is DRY_RUN only and does not modify real directories, snapshots, or state. Entra ID logic remains placeholder planning for this milestone.

## DRY_RUN vs APPLY_MOCK

`DRY_RUN` prints the planned lifecycle actions and writes audit events only. `APPLY_MOCK` writes only to `mock_data/ad_directory.json`, creates a timestamped backup under `backups/mock_ad/` before the first write, and restores that backup if a mock write step fails. In `APPLY_MOCK`, Active Directory mock actions are applied and Entra ID actions remain skipped.

## Example: E1002 Mover

For employee `E1002` (Meera Iyer), the lifecycle run detects a mover event from Finance Financial Analyst to Engineering QA Engineer. The dry run plans `UPDATE_USER_ATTRIBUTES`, adds missing managed AD groups such as `GG-Engineering`, `GG-QA-Engineers`, and `GG-Test-Environment`, and removes only managed groups that are no longer required, such as `GG-Finance`, `GG-Finance-Analysts`, and `GG-Finance-Reporting`.