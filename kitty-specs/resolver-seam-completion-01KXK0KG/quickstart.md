# Quickstart / Validation — Mission-Type DRG Node + Cross-Grain Integrity

Validation scenarios (map to Success Criteria). Run in the clone with `uv run`.

## V1 — `mission_type` is a graph citizen (SC-001)
```bash
uv run spec-kitty doctrine regenerate-graph --check   # fresh, green
grep -c 'kind: mission_type' src/doctrine/graph.yaml    # == 4 (built-in types)
```
Expected: freshness gate green; 4 `mission_type` nodes.

## V2 — cascade for mission-type traverses (SC-001)
```bash
uv run spec-kitty charter activate mission-type research --cascade all --json
```
Expected: cascade acts (no silent no-op); traverses the mission_type node's edges.

## V3 — integrity gate non-vacuous (SC-002)
```bash
PWHEADLESS=1 uv run pytest tests/doctrine/drg/test_cross_grain_integrity.py -q
```
Expected: passes on the shipped (disjoint) tree; the non-vacuity twin fails when pointed at the deliberate-collision temp-tree fixture (asserted within the test).

## V4 — hot path stays cheap, gating byte-identical (SC-003)
```bash
PWHEADLESS=1 uv run pytest tests/specify_cli/next/test_runtime_bridge_dispatch.py \
  tests/charter tests/next -q -n auto --dist loadfile
```
Expected: the hot `.action_sequence` path triggers zero `load_action_index` (spy); charter + next suites green with unchanged activation-gating outputs.

## V5 — single union authority, no scaffold survives (SC-004)
```bash
rg -n "_resolve_union|load_action_index\(" tests/ | rg -v "test_cross_grain_integrity"   # no rogue second union
rg -l "parity_scaffold" src/ tests/ || echo "no parity_scaffold artifact — good"
```
Expected: the two former test-side unions now assert against production's bundle; no `parity_scaffold` file remains.

## Gate before hand-off
```bash
uv run ruff check .
uv run mypy --strict src/charter/mission_type_profiles.py src/doctrine/drg
```
Expected: zero issues.
