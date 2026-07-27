# Quickstart — ci-suite-map-bind-01KWNPMP validation

```bash
export PATH="$PWD/.venv/bin:$PATH"
```

## Per-WP gate (after every invariant or workflow edit)

```bash
PWHEADLESS=1 pytest tests/architectural/test_gate_coverage.py tests/architectural/test_marker_registry_single_source.py -q
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider    # full arch sweep before handoff
ruff check <changed .py>; python -m mypy src/ 2>&1 | tail -2       # must stay: Success
```

## Live census re-derivations (NFR-004 — pin honest numbers, never spec literals)

```bash
# orphans + duplicates (the authoritative model)
python -m tests.architectural._gate_coverage --check   # expect: orphans 0 post-FR-006; duplicates <= re-derived pre-mission value

# residual selection count (FR-002)
PWHEADLESS=1 pytest -m "(unit or contract) and not (fast or integration or git_repo or slow or e2e or architectural or distribution or windows_ci or quarantine or timing)" --collect-only -q 2>/dev/null | tail -2

# routed-by-marker set (FR-001 state i) — PSEUDO until WP builds the extractor:
# parse each gate's g.marker_expr via _pytest.mark.expression.Expression (negation-aware
# positive-token walk); Gate has NO positive_tokens attribute today (debbie: a getattr
# default here silently prints [] — do not trust an empty result from a shortcut).
# Expected live set pre-mission (8): fast, integration, git_repo, architectural, slow, timing, quarantine, windows_ci
```

## Fault-injection proofs (every invariant needs its red)

```bash
# FR-001: add `synthetic_probe: probe marker` to a pytest.ini COPY in a fixture -> invariant red naming it
# FR-001 ineligibility: put `unit` in CI_INVISIBLE in a fixture -> STILL red (hard-assert)
# FR-003: fixture workflow with needs.<x>.result read but <x> undeclared -> red
# FR-010: fixture filter block missing a src package with no catch-all -> red
# FR-011: fixture gate state (filter true, job skipped, no full-run) -> aggregator arm red
# FR-012: fixture --ignore list containing a dir not shard-owned -> red
# Record each red verbatim in the WP report; restore -> green.
```

## Residual-job dry-run (FR-002 / C-007 — before the workflow lands)

```bash
PWHEADLESS=1 pytest -m "<final residual expression>" -q -p no:cacheprovider   # must be 100% green locally
# then after push: the probe PR run must show the job green + blocking in quality-gate
```

## FR-010 catch-all probe (must NOT full-run on matched changes)

```bash
# probe branch A (NON-DRAFT — core-misc is draft-gated): touch src/glossary/<file> -> unmatched=true -> run_all path fires
# probe branch B: touch a well-mapped file (e.g. src/specify_cli/status/…) -> its shard runs, unmatched=false (also fixture-asserted via the parsed model)
# probe C (FR-013): open draft, mark ready -> ci-quality re-triggers (ready_for_review type)
```

## Workflow-scope preflight (C-004 / IC-01 — do this FIRST)

```bash
git checkout -b probe/workflow-scope && printf '\n' >> .github/workflows/ci-quality.yml
git commit -am "probe: workflow scope" && unset GITHUB_TOKEN && git push origin probe/workflow-scope
# success -> delete the probe branch remote+local; failure -> STOP, report the OAuth gap
```

## Mission-level closing sweep (merged branch)

```bash
python -m tests.architectural._gate_coverage --check          # orphans: 0
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q
```

Expected end state: `unit`/`contract` ROUTED-BY-MARKER via the residual job; 37/37 markers in a verified state (i/ii/iii); orphan baseline 0; quality-gate needs↔loop symmetric incl. `mission-loader-coverage` + the residual job; `src/mission_runtime` cov-backed; src/** fail-closed (catch-all); skipped-suite table live; guard surfaces self-mapped; `--ignore` mirrors bound; `ci-windows.yml` widened; #2297/#2296/#2034/#2333 closed by the PR.
