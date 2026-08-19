# Quickstart — verify the sync degod

## Freeze first (before any extraction)
Land the golden-CLI-characterization harness and confirm it passes on the pre-decomposition code:
```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 .venv/bin/python -m pytest \
  tests/characterization/test_sync_*.py -q -p no:cacheprovider
```

## After each extraction (behavior + seam co-gate)
```bash
# behavior: golden green unchanged
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 .venv/bin/python -m pytest tests/characterization/test_sync_*.py -q -p no:cacheprovider
# seam: the ~60 monkeypatch tests green
PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 .venv/bin/python -m pytest tests/sync/ tests/cli/commands/test_sync_*.py -q -p no:cacheprovider
# real-port/daemon tests serially
PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_orphan_sweep.py -n0 -q
# two-authority arch-test
.venv/bin/python -m pytest tests/architectural/test_sync_two_authority.py -q
# complexity: the 3 C901 gone, no net-new suppressions
.venv/bin/ruff check src/specify_cli/cli/commands/sync.py src/specify_cli/sync/
.venv/bin/mypy --strict src/specify_cli/sync/ src/specify_cli/cli/commands/sync.py
```

## Campsite (independent, lands first)
```bash
# walker.py S1192 -> 0, frozenset-equality guard
PWHEADLESS=1 .venv/bin/python -m pytest tests/calibration/test_walker.py -q -p no:cacheprovider
.venv/bin/ruff check src/specify_cli/calibration/walker.py
```
