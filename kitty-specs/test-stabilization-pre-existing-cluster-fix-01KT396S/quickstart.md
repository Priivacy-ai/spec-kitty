# Quickstart: Test Stabilization — Pre-Existing Failure Cluster Fix

## Prerequisites

```bash
cd spec-kitty          # repo root (this package)
uv sync --frozen       # install all dependencies into .venv
```

## Running the failing tests per cluster

### Cluster #1303 (charter synthesizer)
```bash
pytest tests/charter/synthesizer/test_bundle_validate_extension.py \
       tests/charter/synthesizer/test_path_guard.py \
       tests/charter/synthesizer/test_manifest.py -v
```

### Cluster #1304 (doctrine/glossary)
```bash
pytest tests/doctrine/test_glossary_link_integrity.py \
       tests/doctrine/test_tactic_compliance.py -v
```

### Cluster #1305 (next CLI)
```bash
pytest tests/next/test_next_command_integration.py \
       tests/next/test_query_mode_unit.py -v
```

### Cluster #1307 (charter integration)
```bash
pytest tests/charter/ -v
```

### Cluster #1310 residual
```bash
pytest tests/auth/integration/test_refresh_through_transport.py \
       tests/specify_cli/invocation/ \
       tests/specify_cli/migration/test_schema_version.py \
       tests/specify_cli/status/test_wp_metadata.py \
       tests/missions/test_mission_switching_integration.py \
       tests/cli/commands/test_implement_base_flag.py \
       tests/cli/test_implement_bulk_edit_planning.py \
       tests/init/ \
       tests/architectural/ \
       tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -v
```

## mypy strict check

```bash
.venv/bin/mypy --strict src/specify_cli/mission_step_contracts/executor.py
```

To check all modified modules at once:
```bash
.venv/bin/mypy --strict src/charter/synthesizer/ src/specify_cli/next/ src/specify_cli/auth/
```

## PathGuard lint grep (WP02)

Run this to find any direct write calls in the synthesizer package:
```bash
grep -rn "\.write_text\|\.write_bytes\|\.mkdir\|\.replace(" \
  src/charter/synthesizer/ --include="*.py" | grep -v "path_guard.py"
```
Expected output after the fix: no lines.

## Tactic schema validation (WP01)

```bash
spec-kitty doctrine validate  # if available
# or load and validate via Python:
python -c "
from doctrine.drg.loader import load_tactic
t = load_tactic('five-paradigm-parallel-debugging')
print('valid' if t else 'invalid')
"
```

## Full suite sanity check (before and after)

```bash
pytest tests/ -q --tb=no 2>&1 | tail -5
```

Note the total failure count before starting. The goal is to reduce it by at least 25.
