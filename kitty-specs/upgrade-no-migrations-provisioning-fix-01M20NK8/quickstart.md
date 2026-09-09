# Quickstart — reproduce & verify (#4032)

## Reproduce the bug (RED-first, exact signal)
```bash
# A pre-existing failing test is the witness (adopt, don't synthesize):
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/upgrade/test_upgrade_idempotency.py::test_no_migrations_no_op_repeat_is_clean_exit_zero -q
# Expect RED on main: outcome 'failed', errors include
# "Managed skill provisioning requires an existing authority".
```

## Verify the fix
```bash
# 1. Tidy-first gate
ruff check src/specify_cli/cli/commands/upgrade.py
PWHEADLESS=1 .venv/bin/python -m pytest tests/upgrade/test_upgrade_integration.py -k no_stray_noqa_c901 -q

# 2. Frozen Group A (enumerated in tasks.md) all green
PWHEADLESS=1 .venv/bin/python -m pytest tests/upgrade/ -q

# 3. Behavior-preservation oracle (re-pinned to init-ed apply path)
PWHEADLESS=1 .venv/bin/python -m pytest tests/upgrade/test_upgrade_char_net.py -q

# 4. Guard-aligned config-absent skip + diagnostic
PWHEADLESS=1 .venv/bin/python -m pytest tests/upgrade/test_upgrade_guard_absent.py -q

# 5. Blast radius (owning subsystems)
PWHEADLESS=1 .venv/bin/python -m pytest tests/upgrade/ tests/specify_cli/skills/ -q
```

## Expected
- `spec-kitty upgrade` on a config-absent project exits 0, reports `up_to_date`, emits `deferred_provisioning` (non-error), and does NOT create `.kittify/config.yaml`.
- No C901 suppression on `upgrade()`.
