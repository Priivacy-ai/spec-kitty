# Quickstart — measure & verify

All commands force `PYTHONPATH=src` (the global `spec-kitty` shim resolves the sibling fork).

## Measure `next` cold-start (import lever, WP-A)

```bash
# Attribution: where the import time goes (before/after the trim)
PYTHONPATH=src python -X importtime -m specify_cli next --agent test \
  --mission clean-install-fixture-01KQ22XX --json 2>importtime.log
# subprocess median (fixture, no charter) — mirrors the retired gate's method
cd tests/fixtures/clean_install_fixture_mission && \
  for i in 1 2 3 4 5; do /usr/bin/time -f '%e' \
    PYTHONPATH="$OLDPWD/src" python -m specify_cli next --agent test \
    --mission clean-install-fixture-01KQ22XX --json >/dev/null; done
```

## Measure charter-freshness cache (WP-B)

```bash
# On a charter-bearing checkout (this repo): profile the preflight, confirm the
# second run skips _safe_load_yaml (ruamel parse) via cache hit.
PYTHONPATH=src python -m cProfile -s cumtime -m specify_cli next \
  --agent test --mission <a-real-mission> --json 2>&1 | grep -E 'compute_freshness|_safe_load_yaml|ruamel'
```

## Correctness (NFR-002 / NFR-004)

```bash
PYTHONPATH=src pytest tests/charter_runtime/test_freshness_cache.py -q          # no-stale + fail-closed
PYTHONPATH=src pytest tests/specify_cli/next/test_next_output_preservation.py -q # byte-identical
```

## Performance benchmark (WP-C) — off-PR only

```bash
# Runs only with the env gate (as performance.yml sets it):
SPEC_KITTY_RUN_PERFORMANCE=1 PYTHONPATH=src pytest tests/specify_cli/next \
  -m performance --benchmark-storage=file://tests/performance/baselines -q
# Seed the baseline post-fix (human commits the artifact; workflow never auto-commits):
SPEC_KITTY_RUN_PERFORMANCE=1 PYTHONPATH=src pytest tests/specify_cli/next \
  -m performance --benchmark-save=next --benchmark-storage=file://tests/performance/baselines
```

## Verify the gate is gone (WP-D)

```bash
grep -n 'check_nfr_003_latency' .github/workflows/ci-quality.yml   # expect: no matches
test -f scripts/check_nfr_003_latency.py && echo STILL-PRESENT || echo deleted
# structural smoke still present:
grep -n 'next against fixture mission' .github/workflows/ci-quality.yml
```
