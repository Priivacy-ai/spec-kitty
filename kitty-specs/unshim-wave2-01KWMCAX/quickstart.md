# Quickstart — unshim-wave2-01KWMCAX validation

```bash
export PATH="$PWD/.venv/bin:$PATH"
```

## Per-WP gate (after every re-point batch and every deletion — C-005 check)

```bash
PWHEADLESS=1 pytest tests/architectural/test_shim_registry_schema.py tests/architectural/test_unregistered_shim_scanner.py -q
ruff check .; python -m mypy src/ 2>&1 | tail -2   # mypy must stay: Success, 0 issues
```

## Interception proof (per occurrence-map patch-string row; FR-002 ledger)

Either the site carries a call/consumption assertion (name it in the row's `interception_proof`), or record a red-first flip:

```bash
# 1. point the rewritten patch at a bogus target -> the test MUST fail
# 2. restore the canonical target -> green; record evidence in the ledger row
PWHEADLESS=1 pytest <test file> -q
```

## Injection-seam consumption proof (FR-001 / AC-1.3)

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_selector_resolution.py -q
# the injector tests assert the fake's observable side-effect (captured dict), not exit code
```

## CI-only charter shards (run locally in IC-04 — they don't run in fast local shards)

```bash
PWHEADLESS=1 pytest tests/integration/test_quickstart_end_to_end.py tests/contract/test_next_no_implicit_success.py \
  tests/agent/cli/commands/test_next_preflight.py tests/agent/cli/commands/test_implement_preflight.py \
  tests/test_dashboard/test_dashboard_preflight.py -q
```

## Post-deletion checks (NFR-002 — import-scoped; run at merge, must be empty)

```bash
grep -rnE "(from|import)\s+specify_cli\.(next|glossary|charter_lint|charter_freshness|charter_preflight)\b|patch(\.dict)?\(\s*[\"']?(sys\.modules[\"',\s{]*[\"'])?specify_cli\.(next|glossary|charter_lint|charter_freshness|charter_preflight)" src/ tests/
python -c "import specify_cli.next" 2>&1 | grep -q ModuleNotFoundError && echo next-GONE
python -c "import specify_cli.glossary" 2>&1 | grep -q ModuleNotFoundError && echo glossary-GONE
spec-kitty next --help >/dev/null && echo "next command OK (canonical import path)"
```

## WS1 non-vacuity (FR-009)

```bash
PWHEADLESS=1 pytest tests/architectural/test_layer_rules.py -q   # incl. the committed negative test
```

## Mission-level closing sweep (merged branch)

```bash
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q
```

Expected end state: shim-registry has zero legacy rows; `test_charter_runtime_shim_paths.py` retired (disposition table recorded); `_baselines.yaml` category_b at the honest live count (≤215, re-derived); `05_ownership_manifest.yaml`/`05_ownership_map.md` scrubbed; CHANGELOG entry present.
