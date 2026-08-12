# Quickstart: Meta.json Fail-Closed Read Routing

How to measure the live gates, run the three governance checks, and follow the red-first pattern. All commands from the repo root with the in-tree package installed (`pip install -e .`).

## Measure the live routed census (before/after routing)

```bash
python -c "from tests.architectural.test_inline_meta_read_gate import scan_routed_load_meta_calls, SRC_ROOT; print(len(scan_routed_load_meta_calls(SRC_ROOT)))"
```
Baseline on this branch: **134** (floor 130, margin 4 → at the ceiling). After routing all 5 sites AND extending `ROUTED_CALLEES` with the L1 + public-L2 names, re-measure and set `ROUTED_LOAD_META_FLOOR = live - 3`.

## Run the three named governance gates

```bash
PWHEADLESS=1 python -m pytest \
  tests/architectural/test_inline_meta_read_gate.py \
  tests/specify_cli/test_meta_fail_closed_full_census_contract.py \
  -q -p no:cacheprovider
```
Must be green at every WP boundary that changes the census (with the floor re-derived).

## Verify the layer boundary (NFR-004)

```bash
# ref_advance must import zero specify_cli modules
grep -nE "^\s*(from|import)\s+specify_cli" src/specify_cli/git/ref_advance.py || echo "OK: no specify_cli imports"
PWHEADLESS=1 python -m pytest tests/architectural/test_layer_rules.py -q -p no:cacheprovider
```

## Red-first pattern (per site, FR-007)

1. Author the corrupt-file test BEFORE routing the site. Inject a malformed `meta.json` at the site's seam (see data-model.md injection column).
2. Run it against pre-routing code → capture the FAILING output (it currently absorbs corruption silently, so the test asserting a raised `MetaDecodeError` + a message naming `meta.json` + the source id is RED). Save that captured red as the proof-of-red deliverable.
3. Route the site onto the seam.
4. Re-run → GREEN. The valid/missing/empty assertions (FR-005) stay green throughout.

Markers (C-004): real-git sites carry `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`; a `tests/runtime` test (if any) is registered in `tests/_next_shard_map.py`.

## L1 unit coverage (IC-01)

`tests/architectural/test_meta_decode_l1.py` (new; declare a `pytestmark`) covers, for `str` and `bytes`: valid dict; `on_malformed` none→`None` / empty→`{}` / raise→`MetaDecodeError` on each malformed class (bad JSON, invalid utf-8 bytes, non-object top level).

## Enumeration + completeness gates (IC-05, FR-010)

After all routing lands, the new architectural gate asserts 0 `json.loads`/`json.load` over `meta.json` content outside the kernel L1, and 0 un-routed bypass reads beyond the enumerated set. Run the full `tests/architectural/` suite as the final safety net.
