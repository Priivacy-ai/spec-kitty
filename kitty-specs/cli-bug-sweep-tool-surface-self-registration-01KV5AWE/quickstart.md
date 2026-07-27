# Quickstart: Validating the Four Fixes

Run these commands from the repository root after implementation to confirm each fix.

## IC-01 — xfail removed

```bash
# Must produce PASSED or FAILED (not XFAIL/XPASS)
PWHEADLESS=1 pytest tests/adversarial/test_distribution.py::TestUpgradeWithAllMissions::test_upgrade_updates_templates -v
```

## IC-02 — Branch naming pathological case

```bash
# Must pass including the new pathological-case parameterization
PWHEADLESS=1 pytest tests/core/test_branch_naming_human_slug.py -v
```

## IC-03 — Charter bundle validation

```bash
# Must exit 0 with no errors
spec-kitty charter bundle validate --json

# Must not fail on fresh-seed state
PWHEADLESS=1 pytest tests/specify_cli/charter/ -v -k "built_in_only or fresh_seed"
```

## IC-04 — Tool surface self-registration

```bash
# Conformance test: service.py has no central provider literals
PWHEADLESS=1 pytest tests/specify_cli/tool_surface/test_provider_registration.py -v

# Existing tool surface behavior is unchanged
PWHEADLESS=1 pytest tests/specify_cli/tool_surface/ -v

# Full suite — no regressions
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q

# Type check
.venv/bin/mypy src/ --strict

# Lint
.venv/bin/ruff check .
```
