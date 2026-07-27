# Implementation Plan: Mission-Type DRG Edges + Graph Sharding

**Branch**: `feat/mission-type-drg-edges` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)
**Input**: `kitty-specs/mission-type-drg-edges-01KXKY2N/spec.md` · **Issues**: #2677 + #2680 · **ADR slice**: S0 (edge completion)

## Summary

Two-phase, single-subsystem (`src/doctrine/drg`), **edges-first** (reversed from the original fold after the
post-plan squad — see [traces/design-decisions.md](./traces/design-decisions.md) DD-0):

- **Phase 1 (#2677) — mission-type edges.** Emit `mission_type:X → action:X/<step>` (`requires`) edges from
  each type's `action_sequence`, regenerate + commit the **monolith** `graph.yaml`, and turn the red orphan
  gate green (18→10; ceiling unchanged). Re-pin the S0 placeholder test. ~2 src + ~2 test files, no
  correctness traps. Lands first so the time-sensitive gate-clear isn't held hostage.
- **Phase 2 (#2680) — graph sharding.** Behavior-preserving migration of the now-edge-complete graph into
  deterministic per-kind `src/doctrine/*.graph.yaml` fragments. Impose a **canonical built-in-graph seam**
  first, switch ~6 src + ~22 test monolith readers through it, delete the monolith atomically, partition every
  populated node-kind, and prove equality (merged-graph set-equality under an explicit merge-order contract
  **and** on the three `DRGLoadError`-swallowing consumer surfaces). Re-point `_count_orphans` + the freshness
  twins at the sharded layout so every gate stays green. No in-YAML import.

Operator rationale for keeping both in one mission: "we need to do it anyway, so I prefer to keep it close to
the change it risks impacting — that gives us the clearest warning/errors."

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: ruamel.yaml (graph I/O), pytest, mypy --strict, ruff
**Storage**: Filesystem doctrine tree (`src/doctrine/missions/mission_types/*.yaml`, `.../<type>/actions/*/`) + generated `src/doctrine/graph.yaml` (Phase 1) → `src/doctrine/*.graph.yaml` fragments (Phase 2)
**Testing**: pytest (`tests/doctrine/drg/`, `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py`, `tests/charter/`); ATDD red-first; byte-identity freshness gate
**Target Platform**: cross-platform CLI/library
**Project Type**: single (doctrine DRG generator)
**Performance Goals**: regeneration deterministic + byte-identical; no runtime hot-path touched; Phase 2 adds no import-time I/O beyond the current monolith read
**Constraints**: `assert_valid` clean (no dangling / `requires`-cycle / duplicate); ruff + mypy --strict clean; complexity ≤ 15; ceiling 14 unchanged; fragment dir == loader glob root; atomic monolith delete
**Scale/Scope**: Phase 1 = 1 generator pass, 21 edges, ~2 src + 2 test files, 1 regenerated artefact. Phase 2 = 1 seam + generator write-partition + ~6 src readers + ~22 test readers re-pointed + monolith deleted + ~N fragments + docstring sweep.

## Charter Check

| Principle | Applies how | Status |
|-----------|-------------|--------|
| Single canonical authority | Phase 1: `action_sequence` is the single source of the steps; the edge pass derives from it. Phase 2: the built-in-graph **seam** becomes the single authority for reading the shipped graph (retiring 4 bespoke path-builders). | PASS |
| Architectural alignment | Both passes live in the DRG generator/loader (`doctrine/drg/`); doctrine-layer only. The seam lives beside `load_graph_or_dir` in `loader.py`. | PASS |
| Architectural gate discipline | Phase 1 makes the orphan gate meaningful again (green at 10). Phase 2 must keep it green while re-pointing its reader — the gate is a first-class Phase-2 acceptance surface, not collateral. | PASS |
| Test remediation (re-pin) | The stale S0 placeholder `test_mission_type_nodes_have_no_incident_edges` is **inverted/re-pinned** (stale→re-pin), not deleted. The ~22 monolith-path test readers are **migrated to a shared seam fixture** (not deleted). | PASS |
| ATDD-first | RED-first each phase: edge/orphan assertions before the generator emits (C-005); sharding-equality + silent-degrade assertions before the monolith is deleted. | PASS |
| Campsite / whack-a-field | Phase 2 imposes ONE seam instead of repeating a load-path edit across ~22 sites (paula-patterns finding; DD-6). | PASS |
| Mission tracer files | Seed 3 tracers at planning; DD-0/DD-6..DD-10 record the squad-forced decisions. | PASS (seeded + appended) |
| Canonical sources | Relation grounded in the #883 brief + mission-type-resolution ADR (`requires`, cascade-aligned); no improvised relation (C-006). | PASS |

No charter conflicts.

## Implementation Concern Map

The `/spec-kitty.tasks` phase will decompose. **Delivery order is IC-1 (edges) → IC-2 (edge tests) → IC-3
(sharding).** Phase 1 (IC-1/IC-2) is independently shippable and clears the red gate; Phase 2 (IC-3) is the
migration and must land after, preserving green gates. IC-3 is large enough that the tasks phase will likely
split it into several WPs (seam+readers / generator-partition+atomic-retire / equality+silent-degrade proofs /
docstring+snapshot sweep).

### IC-1 — Emit `mission_type → action` edges + regenerate the monolith (Phase 1, #2677)

- Add `extract_mission_type_edges(doctrine_root) -> list[DRGEdge]` in
  `src/doctrine/drg/migration/extractor.py` (sibling of `_discover_mission_type_nodes` @768): for each
  `mission_types/<id>.yaml`, read `action_sequence` and emit `DRGEdge(source=f"mission_type:{id}",
  target=f"action:{id}/{step}", relation=Relation.REQUIRES)`. Concatenate into `all_edges` @~847 (before
  `calibrate_surfaces` @851 and the deterministic sort @866-871).
- **Decision (C-007):** add a `"mission_type"` entry to `_KIND_MAP` (`extractor.py:122-131`) so the backfill
  loop can never silently drop a mission_type endpoint in a future partial-node state; update the obsolete
  `:778` "do not add … until edges exist" caveat.
- Update the `models.py:46` comment (FR-005).
- Regenerate `src/doctrine/graph.yaml` via `spec-kitty doctrine regenerate-graph`; commit it in the same WP
  (byte-identity gate). **Expect a diff possibly wider than 21 lines** from calibration reweighting (C-008).
- Hoist any `"missions"` literal used ≥3× to a small helper/const (Sonar S1192 — SAFE campsite fold).

### IC-2 — Phase-1 tests: RED-first, re-pin, and the un-red (Phase 1, #2677)

- [ATDD RED] Focused generator tests: `mission_type:plan` emits exactly its 4 plan-action `requires` edges;
  a non-plan type (`mission_type:documentation`) emits its full 7-edge sequence; **no** `mission_type:*`
  node remains orphan (SC-001; 21 total).
- **Re-pin** `test_mission_type_nodes_have_no_incident_edges` (`test_mission_type_nodes.py:87-99` — the file
  is 99 lines; the test spans 87-99) — invert to assert the `requires` edges exist; correct the stale
  class/method docstrings (FR-004).
- `test_shipped_graph_orphan_count_within_documented_residual` goes green at 10 ≤ 14 (do NOT raise the
  ceiling — C-002).
- **Residual-doc reconciliation (FR-006 / C-003):** the shared `drg-orphan-residual.md` is a stale "Residual
  orphans (14)" snapshot whose 14 rows contain **none** of the 8 nodes this mission wires. Reconcile it so the
  recorded residual reads 10: the 8 wired nodes never enter the table; correct/remove the ~4 already-stale
  non-orphan rows; leave the 10 true standalone rows for #1923. Assign this file to exactly one WP.

### IC-3 — Shard the generated graph (Phase 2, #2680)

Sequenced AFTER IC-1/IC-2. Sub-concerns (tasks phase will WP-split):

- **IC-3a — Canonical seam (DD-6, do first):** add `load_built_in_graph() -> DRGGraph` (and/or
  `built_in_graph_source() -> Path`) in `src/doctrine/drg/loader.py` wrapping
  `load_graph_or_dir(resolve_doctrine_root())`. Route the 4 bespoke src path-builders through it:
  `agent_profiles/repository.py` (`_default_drg_path` ~:270-278 + `:289` — note the real path has **no** `drg/`
  segment), `specify_cli/doctrine/pack_validator.py:513`, `specify_cli/calibration/walker.py:430-437`
  (`_built_in_graph_path`), `specify_cli/charter_runtime/lint/_drg.py:52,85`. Also route the 6 already-safe
  `load_graph_or_dir` consumers through the seam for uniformity. **Org-pack readers**
  (`pack_assembler.py:209`, `pack_validator.py:527/:977`) are OUT (they read `pack/drg/`).
- **IC-3b — Generator write-partition + atomic retire (DD-7/DD-8):** change `generate_graph`/`_write_graph_yaml`
  to emit one `src/doctrine/<kind>.graph.yaml` per **populated node-kind** (edges assigned by source-node kind;
  target-only kinds still get a fragment). **Delete `src/doctrine/graph.yaml` in the same change.** Update
  `spec-kitty doctrine regenerate-graph` (+ `--check`) to write/verify the sharded layout. Pin fragment dir ==
  loader glob root; test "fragments present ∧ monolith absent".
- **IC-3c — Equality + silent-degrade proofs (DD-9/DD-10):** the behavior-preserving test asserts merged-graph
  set-equality under the chosen merge-order contract (re-sort merged OR per-fragment byte-identity — pin in
  the implement tracer), partition-totality (every node-kind round-trips), AND the three consumer outputs
  (profile lineage, charter-lint `GraphState`, pack-validator built-in URN set) identical before/after.
- **IC-3d — Test-reader migration + docstring/snapshot sweep (FR-009/FR-014/FR-016):** migrate **~22** test
  modules (WP04, incl. the 6 the post-task squad added + 3 repo-root sentinels) to one shared seam fixture /
  delete-stable marker (esp. `test_doctrine_regenerate_graph.py::_count_orphans` + freshness twins — made
  layout-agnostic so the orphan gate stays green); review `snapshot.py:62/200` filename categorization; update
  the load-bearing `models.py`-family docstrings (WP03 T017) that name a monolithic `graph.yaml`. The docstring
  sweep + snapshot land in **WP03**; the test migration in **WP04**.

## Project Structure — files this mission touches

```
# --- Phase 1 (IC-1/IC-2): mission-type edges, against the monolith ---
src/doctrine/drg/migration/extractor.py   # IC-1: extract_mission_type_edges + _KIND_MAP entry + "missions" const
src/doctrine/drg/models.py                # IC-1: models.py:46 comment (+ obsolete :778 caveat)
src/doctrine/graph.yaml                    # IC-1: regenerated monolith (byte-identity) — edges added
tests/doctrine/drg/test_mission_type_nodes.py                       # IC-2: re-pin (invert) + docstrings (87-99)
tests/doctrine/drg/migration/test_extractor.py                      # IC-2: new focused edge tests (or a new file)
tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py    # IC-2: orphan gate greens at 10 (Phase 1)
kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md  # IC-2: reconcile 14→10 (C-003)

# --- Phase 2 (IC-3): sharding, the migration ---
src/doctrine/drg/loader.py                 # IC-3a: NEW built-in-graph seam (load_built_in_graph / built_in_graph_source)
src/doctrine/agent_profiles/repository.py  # IC-3a: _default_drg_path + :289 → seam (NB real path has no drg/ segment)
src/specify_cli/doctrine/pack_validator.py # IC-3a: :513 monolith read → seam
src/specify_cli/calibration/walker.py      # IC-3a: _built_in_graph_path :430-437 → seam
src/specify_cli/charter_runtime/lint/_drg.py  # IC-3a: :52,85 monolith candidate → seam
src/charter/_drg_helpers.py, compiler.py, reference_resolver.py  # IC-3a: route through seam (already load_graph_or_dir)
src/specify_cli/cli/commands/{_status_collectors.py,_doctrine_collect.py,_profile_health_render.py}  # IC-3a: seam
src/doctrine/drg/migration/extractor.py    # IC-3b: generate_graph/_write_graph_yaml → per-kind fragments + delete monolith
src/specify_cli/cli/commands/doctrine.py   # IC-3b: regenerate-graph writes/verifies sharded layout + atomic delete
src/doctrine/*.graph.yaml                  # IC-3b: NEW per-kind fragments (replaces src/doctrine/graph.yaml)
src/specify_cli/doctrine/snapshot.py       # IC-3d: :62/:200 filename categorization review
src/doctrine/{directives,procedures,tactics,paradigms,styleguides,agent_profiles,shared}/*.py  # IC-3d: docstring sweep
tests/doctrine/conftest.py                 # IC-3d: shared seam fixture (SHIPPED_GRAPH_PATH)
tests/doctrine/**, tests/charter/**        # IC-3d: ~16 modules migrated to the seam fixture (see FR-009 inventory)
```

## Phase 0 — Research

See [research.md](./research.md). The Phase-1 edge design is fully resolved (21 edges, residual 10,
`_KIND_MAP`, calibration diff-width). The Phase-2 sharding surface was resolved by the post-plan investigation
squad (architect-alphonso + paula-patterns + reviewer-renata): the ~22-site inventory, the canonical seam, the
atomic-retire / loader-precedence trap, partition-totality, the merge-order equality contract, and the three
silent-degrade surfaces are all captured in DD-6..DD-10 + the spec's FR-007..S10. No `[NEEDS CLARIFICATION]`
remain (the merge-order contract choice, DD-9, is a plan-authored decision to pin at implement time, not an
open clarification).

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — the edge shape + the decision table (relation, `_KIND_MAP`) + the
  fragment partition scheme (per populated node-kind; edges by source kind).
- [contracts/](./contracts/) — the `extract_mission_type_edges` contract + the `load_built_in_graph` seam contract.
- [quickstart.md](./quickstart.md) — regenerate + verify locally (both layouts).

## Complexity Tracking

No charter gate violations. Phase-1 edge pass is a linear read→emit loop (≤15). Phase-2 write-partition is a
group-by-kind + per-fragment sort (keep helpers small, ≤15). Repeated literals hoisted (S1192). Every new
branch/helper gets a focused test (IC-2 / IC-3c). The one deliberate risk the squad flagged — a "tidy-first"
migration exceeding the feature it enables — is mitigated by (a) shipping the edges independently first and
(b) the seam + totality + equality + silent-degrade tests gating the monolith delete.
