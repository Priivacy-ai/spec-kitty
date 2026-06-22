# Quickstart: validating the convergence (live-evidence + pure recipes)

The structural recipes the implement loop MUST run. R1/R2/R3 are LIVE repros (NFR-001 — no
close-on-static; #2062 carries C-002). R0 is the pure-resolver unit proof (NFR-005). R4 is the
dual-derivation retirement proof (SC-001). Each live repro is a throwaway tmp git repo.

## R0 — Pure resolver: feed (id, topology), assert ExecutionContext (NFR-005, FR-004)

```python
# ZERO filesystem / git fixtures — the resolver is a pure projection over build_execution_context.
from mission_runtime.context import MissionTopology
from mission_runtime.resolution import resolve_context_for_mission
for topo in MissionTopology:                       # SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD
    ctx = resolve_context_for_mission(mission_id="01KV...REAL_ULID", topology=topo)
    # assert the projected surface fields match the topology:
    #   COORD/LANES_WITH_COORD -> destination_ref routes_through_coordination; coord surfaces set
    #   SINGLE_BRANCH/LANES    -> primary surfaces; routes_through_coordination is False
```
**Pass**: all four topologies return a correct `ExecutionContext` with NO test doubles for the
filesystem or git — proves the functional-core/imperative-shell split (NFR-005) and that the
resolver is a projection over the single door, not a parallel resolver (C-003).

## R1 — Flattened mission resolves PRIMARY on all legs × all handles (FR-006, #2062)

```python
# Build: meta.json topology = SINGLE_BRANCH/LANES (flattened provenance) + a stale -coord husk on disk.
#   kitty-specs/<slug>-<mid8>/meta.json            -> {"mission_id": ..., "topology": "single_branch"}
#   kitty-specs/<slug>-<mid8>/status.events.jsonl  -> canonical = approved
#   .worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/status.events.jsonl -> stale = planned
from specify_cli.coordination.surface_resolver import resolve_status_surface_with_anchor
from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path
# For handle in {<slug>-<mid8>, bare-mid8, full-ULID, bare-human-slug}:
#   surface  leg -> PRIMARY
#   read_path leg (require_exists=True) -> PRIMARY   # was STALE-COORD: the #2062 bug
#   aggregate leg -> PRIMARY
```
**Pass**: all read legs return PRIMARY for every handle form **because the STORED topology drives
the read path** — the on-disk husk is structurally not consulted (FR-006/C-004). This is a strict
row in `tests/missions/test_surface_resolution_equivalence.py` (the retained on-disk leg, FR-010).

## R2 — spec.md visible to /tasks + finalize from one surface (FR-007, #2063)

```bash
# Coord-topology mission. Commit spec.md via the seam-resolved mission-aware path.
spec-kitty spec-commit --mission <slug> --message "..." <feature_dir>/spec.md
spec-kitty agent mission finalize-tasks --validate-only --mission <slug> --json   # no "spec.md not found"
```
**Pass**: no "spec.md not found" / "Tasks directory not found" divergence — the commit and the
following read resolve the SAME surface through the seam.

## R3 — map-requirements full coverage == finalize zero-unmapped (FR-008, #2064)

```bash
spec-kitty agent tasks map-requirements --mission <slug> --wp WP01 --refs FR-001   # reports 1/1 mapped
spec-kitty agent mission finalize-tasks --validate-only --mission <slug> --json    # unmapped == []
```
**Pass**: after map-requirements reports full coverage, finalize `--validate-only` reports ZERO
`unmapped_functional_requirements` (same seam-resolved WP-frontmatter surface).

## R4 — both derivations retired; no live topology inference remains (SC-001, FR-004)

```bash
# After the retirement, NO live decision path re-infers shape from coordination_branch is None
# or a worktree stat. Both ladders are gone:
rg -n "coordination_branch is None" src/mission_runtime/resolution.py src/runtime/next/runtime_bridge.py
rg -n "_coord_path\.exists\(\)" src/runtime/next/runtime_bridge.py
# Expect: zero LIVE decision sites (only the one-time backfill computation may reference the
# legacy signal, clearly marked).
```
**Pass**: both `resolution.py:705-718` and `runtime_bridge.py:144-211` are retired in favor of the
stored topology; a grep finds no live `coordination_branch is None` / `_coord_path.exists()`
decision site (alphonso's scope gap closed). The create-window (#1718) / coord-deleted (#1848)
probe paths are preserved (C-006) and are NOT topology inferences.

## R5 — is_committed single-surface, full suite green (FR-011, NFR-003)

```bash
# Only after R1+R2 are witnessed live (the surface is structurally single):
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
```
**Pass**: `is_committed` is a single-surface check on the resolved placement ref; the full suite is
green including the preserved #1718/#1848 guards. Gated on the live convergence proof (NFR-001/C-002).
