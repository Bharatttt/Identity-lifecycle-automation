# Identity Lifecycle Automation

Portfolio-ready Joiner-Mover-Leaver (JML) automation in Python, designed for safe local execution with mock data only.

## Overview

This project demonstrates a safe IAM lifecycle workflow that:

- Reads HR data from CSV
- Classifies identities as Joiners, Movers, Leavers, or Unchanged
- Maps department and role to approved RBAC access
- Reconciles actual mock Active Directory group memberships with required policy groups
- Supports both `DRY_RUN` and `APPLY_MOCK` modes
- Writes structured JSONL audit logs for every action

This project is intentionally scoped for portfolio work and does **not** connect to any real Active Directory, Microsoft Entra ID, AWS, or production system.

## Features

- Joiner-Mover-Leaver lifecycle classification
- RBAC-based access planning
- Mock Active Directory reconciliation
- Managed-group protection
- Structured audit logging
- CLI-based execution
- Safe mock apply mode with backup and rollback
- Focused unit tests for reconciliation behavior

## Architecture Summary

- `data/hr_users.csv` - HR source of truth
- `state/previous_hr_snapshot.json` - Prior HR snapshot used for lifecycle classification
- `config/rbac_mapping.json` - Department and role-based access policy
- `mock_data/ad_directory.json` - Mock Active Directory users and groups
- `src/lifecycle.py` - Classifies identities
- `src/action_planner.py` - Builds lifecycle actions
- `src/mock_ad_connector.py` - Reads and updates mock AD state
- `src/audit_logger.py` - Writes JSONL audit events
- `src/run_lifecycle.py` - Executes the lifecycle workflow
- `src/cli.py` - Provides a menu-driven CLI

## IAM Concepts Demonstrated

### Joiner-Mover-Leaver

The workflow classifies each employee as a Joiner, Mover, Leaver, or Unchanged identity based on current HR data and the previous HR snapshot.

### RBAC

Approved access is derived from `config/rbac_mapping.json` using department and role.

### Least Privilege

Only groups explicitly approved by policy are planned or applied.

### Audit Logging

Each action is recorded in JSONL format with run metadata, event type, employee ID, action, target system, status, and non-secret details.

## Managed Group Registry

The managed AD group registry is derived from the AD group names in `config/rbac_mapping.json` by collecting:

- Each department's default AD groups
- Each role's AD groups

Only groups in that managed registry can be removed during reconciliation. Any group outside that registry is treated as unmanaged and left untouched.

## Operating Modes

### `DRY_RUN`

- Prints planned lifecycle actions
- Writes audit events
- Does not modify mock AD or any real system

### `APPLY_MOCK`

- Writes only to `mock_data/ad_directory.json`
- Creates a timestamped backup before the first write
- Restores the backup automatically if a mock write fails
- Applies only mock Active Directory actions
- Leaves Microsoft Entra ID actions as `SKIPPED`

## How to Run

Run the CLI:

```bash
python src/cli.py
```

Menu options:

- Run dry-run lifecycle
- Apply mock AD changes
- Run tests
- Show latest audit-log lines
- Exit

You can also run the dry-run workflow directly:

```bash
python src/run_lifecycle.py
```

## Testing

Run the reconciliation tests with:

```bash
python -m unittest discover -s tests -p "test_group_reconciliation.py"
```

Run all tests with:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Example Scenario

### E1002 - Mover

For employee `E1002` (Meera Iyer), the lifecycle run detects a mover event from Finance Financial Analyst to Engineering QA Engineer.

The workflow:

- Plans `UPDATE_USER_ATTRIBUTES`
- Adds required managed AD groups such as `GG-Engineering`, `GG-QA-Engineers`, and `GG-Test-Environment`
- Removes only managed groups that are no longer required, such as `GG-Finance`, `GG-Finance-Analysts`, and `GG-Finance-Reporting`

This demonstrates role-based access reconciliation using actual mock directory state.

## Limitations

- Active Directory integration is mock-based only
- Microsoft Entra ID actions are placeholder planning only
- No real directory or cloud changes are performed
- The project is designed for safe local portfolio demonstration

## License

## License

This project is licensed under the MIT License.
