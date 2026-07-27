# Tasks: LOC-insensitive census freshness gate

**Mission**: `census-freshness-loc-insensitive-01KWVD6Y` · **Tracker**: [#2416](https://github.com/Priivacy-ai/spec-kitty/issues/2416)
**Planning base**: `fix/census-freshness-loc-insensitive` · **Merge target**: `fix/census-freshness-loc-insensitive`

One cohesive work package. The change is confined to three files under
`tests/architectural/` and is tightly coupled (one shared derivation, one consumer test
module, one regenerated artifact) with a hard ATDD ordering constraint, so it is a
single lane — splitting would create artificial cross-WP file ownership on the same
three files.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | ATDD red-first: failing rank-altering-churn test (FR-001 + FR-007) | WP01 | — |
| T002 | Add `worklist_routing_index()`; drop `loc` from `live_derived_worklist`; sort by `dir` | WP01 | — |
| T003 | Rewrite freshness test → dir-keyed index compare | WP01 | — |
| T004 | Re-point `test_every_worklist_dir_meets_loc_floor` to live LOC | WP01 | — |
| T005 | Self-mutation teeth tests (drop-dir / phantom-dir / routing-edit / floor-crossing) | WP01 | — |
| T006 | Regenerate census via `--emit-census` | WP01 | — |
| T007 | Validate: targeted arch tests + ruff + mypy + zero `src/` changes | WP01 | — |

## WP01 — Narrow census freshness gate to membership + live-floor

- **Goal**: Stop the CI-topology census freshness gate reddening on exact-LOC churn while
  preserving all anti-tamper teeth. Fix at the shared derivation; keep the LOC floor live.
- **Priority**: P1 (MVP — this is the whole mission).
- **Independent test**: `PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_ci_topology_worklist.py -p no:cacheprovider -q -o addopts=""` is green with `loc` gone from the census, and a `+N`-line change to a worklist dir keeps it green.
- **Dependencies**: none.
- **Estimated prompt size**: ~380 lines.

### Included subtasks

- [ ] T001 ATDD red-first: add failing rank-altering-churn test (monkeypatch two adjacent members' live LOC to swap rank; assert freshness holds) — RED on base branch (WP01)
- [ ] T002 Add pure `worklist_routing_index()` helper; drop `loc` from `live_derived_worklist()` entries; sort committed worklist by `dir` (WP01)
- [ ] T003 Rewrite `test_census_worklist_matches_live_derivation` to compare `worklist_routing_index(census)` == `worklist_routing_index(live)` (order/LOC-insensitive) (WP01)
- [ ] T004 Re-point `test_every_worklist_dir_meets_loc_floor` to assert live `src_package_loc()[dir] >= t_loc` (WP01)
- [ ] T005 Add self-mutation teeth tests (drop-dir, phantom-dir, routing-edit, floor-crossing via dynamic `t_high`) each red the index compare, plus a durable shape-independent `test_committed_census_carries_no_loc` (C-001) (WP01)
- [ ] T006 Regenerate `ci_topology_census.json` via `uv run python -m tests.architectural._gate_coverage --emit-census` (WP01)
- [ ] T007 Validate: targeted `tests/architectural/`, `ruff check`, `mypy` clean; `git diff --name-only` touches no `src/` file (WP01)

### Implementation sketch

1. **T001 first (ATDD contract commit).** Author the red-first test that a rank-altering
   LOC churn keeps the freshness gate green. Commit it alone; confirm it is RED on the
   base branch (the current `==` compares exact `loc`/order).
2. **T002 derivation fix.** In `_gate_coverage.py`: add `worklist_routing_index(entries)`
   returning `{dir: {"cone_roots": [...], "target_group": ..., "target_shard": ...}}`;
   make `live_derived_worklist()` emit entries without `loc`, sorted by `dir`.
3. **T003/T004 consumer tests.** Rewrite the freshness assertion to the index compare;
   re-point the floor test to live LOC.
4. **T005 teeth.** Add the four self-mutation tests (all exercise the index compare / live
   derivation, no source-tree mutation; floor-crossing uses a dynamic raised floor).
5. **T006 regen.** Emit the census; the diff should only remove `loc` keys.
6. **T007 gate.** Targeted arch tests + lint/type + prove zero `src/` change.

### Parallel opportunities

None — single file surface, ATDD ordering. Sequential within the lane.

### Risks

- Skipping T006 leaves the committed census with stale `loc`. The loc-blind index
  freshness test stays green on this **by design**, so a dedicated shape-independent
  `test_committed_census_carries_no_loc` (C-001) is what reds. Regen **and** that
  assertion are both mandatory in this WP.
- Teeth tests that build a private comparison instead of calling the real
  `worklist_routing_index` / `live_derived_worklist` would be vacuous (violates C-004).
- `mypy --strict`: `worklist_routing_index` needs precise typing (`dict[str, dict[str, Any]]`
  or a `TypedDict`); avoid `# type: ignore`.
