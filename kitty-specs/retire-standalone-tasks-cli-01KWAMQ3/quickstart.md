# Quickstart / Verification: Retire Standalone Tasks CLI

How to verify the mission is complete and correct.

## 1. Surface is gone
```bash
test ! -e scripts/tasks && test ! -e src/specify_cli/scripts/tasks \
  && test ! -e .kittify/overrides/scripts/tasks && echo "all 3 copies removed"
grep -rn "specify_cli.scripts.tasks" tests/ src/ && echo "FAIL: residual reference" || echo "no residual references"
```

## 2. Suite collects and passes (no missed importer)
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q
# Real-port/daemon tests serially:
PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_orphan_sweep.py -n0 -q
```
Expect: green (pre-existing/unrelated failures reported per the charter rule, not introduced here). A collection-time `ImportError` mentioning `scripts.tasks` means an importer was missed (FR-004 incomplete).

## 3. Encoding capability preserved on the supported surface (FR-005 / NFR-004)
```bash
# Repair on demand:
spec-kitty accept --mission <slug> --normalize-encoding   # repairs mojibake artifacts, then proceeds
# Default (no flag) leaves artifacts untouched and surfaces a clean error on invalid UTF-8:
spec-kitty accept --mission <slug>                        # exit 1 + "Run with --normalize-encoding"
```
Tests: ≥1 repair-with-flag, ≥1 no-rewrite-default, ≥1 error-without-flag.

## 4. Ratchet shrank (FR-007 / C-002)
```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/architectural/test_no_dead_symbols.py \
  tests/architectural/test_no_dead_modules.py \
  tests/architectural/test_gate_read_literal_ban.py \
  tests/architectural/test_ratchet_baselines.py -p no:cacheprovider -q
```
Expect: green, with `_baselines.yaml` `category_b_grandfathered_legacy` and `category_3_external_cli_entrypoints` equal to their new live frozenset sizes; no dangling allowlist entry pointing at a deleted file.

## 5. Quality gates
```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy src/specify_cli   # zero new issues
```

## 6. Pre-3.0 hard-reject still proven (SC-5 / FR-009)
The engine test `test_collect_feature_summary_rejects_pre30` plus the new real-CLI regression (CliRunner on a pre-3.0 repo → exit 1 + "spec-kitty upgrade" + no commit) both pass.
