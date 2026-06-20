# Implementation Plan: Single Mission-Surface Resolver

**Branch**: `feat/single-mission-surface-resolver` | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/single-mission-surface-resolver-01KVGCE8/spec.md` (source: GitHub #2040)

## Summary

Strangle the coord-vs-primary mission-surface **selection** decision — today owned by
**4+1 parallel resolvers** — down to one canonical resolver
(`coordination/surface_resolver.resolve_status_surface_with_anchor`), proven safe to
collapse by a cross-resolver **differential equivalence test** (FR-002, the deletion
gate) and locked by a **load-bearing architectural guard** (FR-004). Sequencing follows
the spec's Tidy-First Inputs: unify the divergent primitives and extract a shared
delegator FIRST (so the equivalence matrix asserts over a clean surface), land the two
cheap behavioral slices (FR-008 silent-glob removal, FR-005 typed-error pass-through),
then gate the collapse + shim retirement + `#1900` allowlist drain on equivalence-green.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib `pathlib`; existing seams — `coordination/surface_resolver.py` (canonical owner), `missions/_read_path_resolver.py`, `status/aggregate.py`, `mission_runtime/resolution.py`, `coordination/status_transition.py` (#1900 predicates); reused 01KVFTFV scaffolding (`tests/architectural/untrusted_path_audit/audit.py` AST walker + `test_untrusted_path_containment.py` guard pattern, C-001)
**Storage**: filesystem — `kitty-specs/<slug>[-mid8]/` on the primary checkout vs `.worktrees/<slug>-coord/` (the divergent surfaces); git worktree registry
**Testing**: pytest — FR-002 differential equivalence test over the input-class matrix (no-coord / coord-fresh / coord-behind / coord-empty / ambiguous-mid8 / bare-slug-vs-`<slug>-<mid8>`-handle); mutation-killing tests per guard/fix; architectural guard in `tests/architectural/`
**Target Platform**: cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: single (CLI library: `src/specify_cli` + `src/mission_runtime`)
**Performance Goals**: no regression — resolution is metadata/path composition (no I/O added beyond existing `resolve()`/registry reads); no benchmark gate
**Constraints**: `ruff` + `mypy --strict` 0 on changed code (no new `# noqa`/`# type: ignore`); **migrate, don't wrap** — no new parallel resolver (C-002); FR-002 equivalence-green BEFORE deleting any duplicate (C-004); no version prescription (C-003)
**Scale/Scope**: ~5 resolver sites + the `mission_runtime` caller boundary + 30+ `feature_dir_resolver` shim import sites (T6 bulk-edit slice)

## Charter Check

*GATE: passes before Phase 0; re-checked post-design.*

- **Tests for new functionality / ATDD**: satisfied — FR-002 equivalence test + per-fix mutation tests + FR-004 guard.
- **Code Quality (ruff/mypy --strict 0, complexity ≤ 15)**: satisfied — NFR-001.
- **Canonical seams (#1868)**: directly advanced — bind surface-selection authority to one owner + a guard.
- **Terminology Canon**: Mission; `feature_dir`/`feature_slug` referenced as existing field/var names only.
- **Migrate-don't-wrap / no shadow path (#1993)**: C-002 binding — the collapse removes resolvers, never adds one.
- **Bulk-edit note**: only the **T6 shim-retirement** slice (migrate 30+ `missions.feature_dir_resolver` import sites) is an import-path bulk edit. The mission is NOT globally `change_mode: bulk_edit` (that would wrongly gate the non-bulk WPs); the T6 WP MUST produce a **scoped `occurrence_map.yaml`** (import_paths category) via the occurrence-classification guardrail at its implement time — after the IC-02 audit fixes the exact site set. Flagged for /tasks.
- No charter violations → no Complexity Tracking entries.

## Project Structure

```
src/specify_cli/
├── coordination/
│   ├── surface_resolver.py        # CANONICAL owner (resolve_status_surface_with_anchor) — IC-06
│   └── status_transition.py       # #1900 coord predicates → migrate to canonical (IC-06)
├── missions/
│   ├── _read_path_resolver.py     # unify primary_feature_dir (T1/FR-009), shared delegator (T4) — IC-01
│   └── feature_dir_resolver.py    # C-004 shim → retire (T6) — IC-06
├── status/
│   └── aggregate.py               # _find_meta_path glob (T2/FR-008) + _resolve_read_dir re-gate (T3) — IC-03/IC-06
├── mission_read_path.py           # opportunistic shim retirement (T7)
└── (mission_runtime/resolution.py)# typed-error pass-through (FR-005) — IC-04

tests/
├── architectural/
│   ├── <surface-resolution audit> # repointed AST walker (FR-003) — IC-02
│   └── <single-resolver guard>    # load-bearing guard (FR-004) — IC-07
└── <differential equivalence test># FR-002 deletion safety gate — IC-05
```

**Structure Decision**: single-project CLI. Work concentrates in `coordination/` (canonical owner), `missions/` (primitives + shim), `status/aggregate.py`, `mission_runtime/resolution.py`, and `tests/architectural/`. **Refactor mission → WP ownership overlap on the resolver files is expected; the IC map linearizes the shared surfaces** (per the refactor-overlap practice).

## Complexity Tracking

No charter violations — none.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. Sequencing encodes the tidy-first → equivalence-gate → collapse flow.

### IC-01 — Tidy-BEFORE: unify the resolver primitives
- **Purpose**: Remove the hidden divergence so the equivalence test asserts over a clean surface. Disambiguate the two `primary_feature_dir_for_mission` (T1/FR-009): keep the **raw-slug topology-blind** `_read_path_resolver.py:410` as canonical, make the `feature_dir_resolver.py:23` mid8-composing twin re-export it (NOT a merge onto mid8). Confirm `_compose_mission_dir` is the single grammar (T5) for the topology-aware/resolved path; extract ONE shared `resolve-dir-or-typed-error` delegator (T4) from the duplicated wrappers in `aggregate._resolve_read_dir` and `mission_runtime/resolution.py`.
- **Relevant requirements**: FR-009, (enables FR-001/FR-002), C-002
- **Affected surfaces**: `missions/_read_path_resolver.py`, `missions/feature_dir_resolver.py` (the divergent copy), `mission_runtime/resolution.py`, `status/aggregate.py`
- **Sequencing/depends-on**: none — FIRST.
- **Risks** (squad-corrected 2026-06-19): the canonical primary anchor is **raw-slug by design** (topology-blind; 01KTRC04 FR-003; `_mid8_from_primary_meta` calls it to derive mid8 — composing mid8 there is circular). Do NOT merge onto the mid8-composing form — that would reintroduce the split-brain. Pin the topology-blind contract with a regression on the existing raw-slug callers (`_mid8_from_primary_meta`, finalize-tasks). The T4 delegator's fallback-target + exception-set difference must be reconciled (a recorded decision).

### IC-02 — Surface-resolution audit (read-only inventory)
- **Purpose**: Repoint the 01KVFTFV AST walker to enumerate every mission-surface-resolution callsite, classified `routed-through-resolver` / `topology-blind-by-design` / `raw-bypass`. The map that scopes the guard (IC-07) and the shim migration (IC-06/T6).
- **Relevant requirements**: FR-003
- **Affected surfaces**: `tests/architectural/` (new audit module, reuse `untrusted_path_audit/audit.py` machinery); read-only over `src/specify_cli` + `src/mission_runtime`
- **Sequencing/depends-on**: none — parallel with IC-01.
- **Risks**: distinguish `topology-blind-by-design` (legitimate primary-only reads, e.g. meta.json) from `raw-bypass`; do NOT flag the `WorktreeTopology`/`classify_worktree_topology` machinery (correct authority, out of scope).

### IC-03 — FR-008 / T2: single mid8 disambiguation
- **Purpose**: Eliminate `aggregate._find_meta_path`'s silent-first-match `glob("{slug}-*/meta.json")`; route mid8 handles through the one canonical handle resolver so `--mission <mid8>` resolves identically everywhere (or raises `MISSION_AMBIGUOUS_SELECTOR`). Closes the S8 selection ambiguity.
- **Relevant requirements**: FR-008
- **Affected surfaces**: `status/aggregate.py` (`_find_meta_path`), the canonical handle resolver
- **Sequencing/depends-on**: after IC-01 (single composition grammar).
- **Risks**: behavior change (silent-pick → typed error) — carry the mutation-killing test; it is the intended FR-008 fix.

### IC-04 — FR-005 / typed-error pass-through (cheapest behavioral slice)
- **Purpose**: Translate the **un-caught** `MISSION_AMBIGUOUS_SELECTOR` through the `mission_runtime` boundary (add the `except MissionSelectorAmbiguous` arm in `resolution.py` mirroring the existing `StatusReadPathNotFound` translation at `:185-190`). No resolver change.
- **Relevant requirements**: FR-005
- **Affected surfaces**: `mission_runtime/resolution.py` (the `:183` try); the error types already exist
- **Sequencing/depends-on**: depends on IC-01 (shared delegator); independent of the collapse.
- **Risks** (squad-corrected 2026-06-19): the original "flatten to `MISSION_NOT_FOUND`" premise was FALSE — `resolution.py:185-190` already preserves `StatusReadPathNotFound` and `runtime_bridge.py:3163` is already guarded. The residual is the **un-caught ambiguous-selector**. Use a LIVE ambiguous-handle repro (red on `main`); reject a born-green test.

### IC-05 — FR-002 / differential equivalence test (the deletion safety gate)
- **Purpose**: Feed the same `(slug, mid8, topology)` matrix to every resolution entry point; assert identical dir OR identical typed error. MUST be green before any duplicate resolver is deleted (C-004).
- **Relevant requirements**: FR-002, NFR-003
- **Affected surfaces**: new test; exercises all resolvers
- **Sequencing/depends-on**: after IC-01 + IC-02 + IC-03 (clean surface + inventory + mid8 fixed).
- **Risks**: must cover the FR-009 mid8-handle class or T1 hides a false-green; the matrix is the gate, not a smoke test.

### IC-06 — FR-001/FR-007 / collapse to one resolver (gated on IC-05 green)
- **Purpose**: Make `resolve_status_surface_with_anchor` the sole authority. `aggregate._resolve_read_dir` → thin adapter (drop the unmaterialized-coord re-gate, T3); migrate `status_transition.py` coord predicates to the canonical resolver and **drain its C-002 topology-ratchet allowlist** (#1900, the SC-005 proof); retire the `feature_dir_resolver.py` C-004 shim (T6, 30+ import sites → scoped `occurrence_map.yaml`).
- **Relevant requirements**: FR-001, FR-007, #1900
- **Affected surfaces**: `coordination/surface_resolver.py`, `status/aggregate.py`, `coordination/status_transition.py`, `missions/feature_dir_resolver.py` (+ 30+ callers), `tests/architectural/test_topology_resolution_boundary.py` (allowlist)
- **Sequencing/depends-on**: **IC-05 (equivalence green) — hard gate (C-004)**; IC-01.
- **Risks**: the bulk import migration (T6) and the allowlist drain are the highest-overlap surfaces — linearize; do NOT delete a resolver until the equivalence test covers its input classes.

### IC-07 — FR-004 / load-bearing architectural guard
- **Purpose**: Clone the 01KVFTFV guard — a `raw-bypass` join outside the blessed resolver/delegator set fails CI; proven load-bearing (real-code mutation + non-empty coverage assertion anchored on the IC-02 inventory).
- **Relevant requirements**: FR-004, SC-002
- **Affected surfaces**: `tests/architectural/<new guard>`
- **Sequencing/depends-on**: after IC-02 (inventory) + IC-06 (asserts the collapsed state).
- **Risks**: anchor strictly on the inventory (low false-positive); self-test must bite.

### IC-08 — FR-006 / coord-empty hard-fail policy + ADR
- **Purpose**: A materialized-but-empty coord worktree hard-fails with `STATUS_READ_PATH_NOT_FOUND` whose message names BOTH recovery paths (collapse/flatten OR recreate/populate the coord branch) — never a silent primary fallback. Record the decision in an ADR; bind it to the single resolver. (Distinct from the no-coord create→first-write window, where primary is authoritative.)
- **Relevant requirements**: FR-006, NFR-004, #1716
- **Affected surfaces**: `coordination/surface_resolver.py` (the policy), `architecture/**/adr/` (the ADR), tests
- **Sequencing/depends-on**: with/after IC-06 (bound to the canonical resolver).
- **Risks**: must not regress the legitimate no-coord primary path; the message must be actionable (NFR-004).

### Opportunistic (not load-bearing): T7 (`mission_read_path.py` shim retirement), T8 (`CoordinationBranchDeleted` error-ownership relocation when FR-005 lands). Fold only if cheap; skip T7 if it costs a bulk-edit.

## Post-Planning Brownfield Checks

*(recorded per standing practice; the adjacent-issues + boy-scout squads performed the bulk of this before plan)*

- **Foldable-issue search** — DONE (adjacent-issues squad): exactly one genuine fold, **#1900** (the `status_transition.py` 5th selection site), now in the issue-matrix + IC-06. Everything else in the coord/worktree neighborhood (#1357 races, #1887 merge-staging, #1829/#1890/#1891, #2017 umbrella) explicitly NOT folded (same-family-different-deliverable / orthogonal). No scope bloat.
- **Split-brain / duplication scan** — DONE (boy-scout squad): the T1 divergent `primary_feature_dir_for_mission` (the hidden 2nd instance of the mission's own bug) is the headline split-brain → FR-009/IC-01. Other duplications (T3 re-gate, T4 wrappers) mapped to ICs.
- **LOC / scope** — bounded: ~5 resolver files + `mission_runtime` boundary + the T6 import migration; refactor-overlap linearized in the IC map. Not a codebase-wide rename.
- **Deprecation check** — see Phase 0 research (the C-004 `feature_dir_resolver.py` + `mission_read_path.py` shims ARE due deprecations this mission retires; confirm no other strangler shim in the surface is past its removal milestone).
- Outcome: no scope expansion beyond the locked decisions + the single #1900 fold; the equivalence gate (C-004) is the safety mechanism for the collapse.
