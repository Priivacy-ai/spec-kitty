# Contract — CONSOLIDATED write surface (Lane A)

The single write resolver, phase-aware, CONSOLIDATED-wired. No parallel resolver (C-006); phase derived internally (C-001).

## `resolve_placement_only(mission_slug, kind, …)` — phase-aware (internal)

- Derives `LifecyclePhase` internally from durable `meta.json` + git state (D2). Callers pass NO phase.
- **PRE_CONSOLIDATION** → behaviour unchanged from #3076 (regression floor).
- **CONSOLIDATED (E1)** → for a kind that should follow the integrated tree, resolves through the CONSOLIDATED surface = Target Ref tree.
- **PUBLISHED (E2)** → resolves through the CONSOLIDATED surface = repo-root checkout, gated by the content-presence predicate (D1); if content absent → structured refusal carrying the FR-006 recovery action.
- `STATUS_STATE` / `DECISION_LOG` share this resolver: their pre-consolidation resolution is unchanged (SC-005); their post-consolidation resolution shifts as the shared-resolver consequence (C-005) — NOT via per-kind branching in the resolver.

**Invariants**: single resolver (no second path); probe and commit derive identical phase; `get_feature_target_branch` stays unrouted.

## `SurfaceLocations.consolidated` + `translate_surface(CONSOLIDATED, …)`

- `SurfaceLocations.consolidated` is populated per phase (was always `None`).
- `translate_surface` already has the total CONSOLIDATED arm — no change to the translation map; only the location is now supplied.
- `None` (genuinely unroutable) → existing `ValueError` guard → surfaced as FR-006 refuse-with-recovery, never a fabricated ref.

## Content-presence predicate (D1)

```
consolidated_location_valid(mission_slug, HEAD) :=
    exists(HEAD:kitty-specs/<mission_slug>/meta.json)   # squash-robust; NOT commit-ancestry
```
Anchored by `baseline_merge_commit` (phase signal) — together they replace the non-existent "recorded merge target."

## Write-seam staging thunk (FR-005 / #3073)

```
write_artifact(kind, stage: Callable[[], tuple[Path, ...]], …) -> WriteSeamResult
```
- `_probe_write_target(...)` runs FIRST; only on OK is `stage()` invoked (materialize), then `commit_for_mission`.
- Refused write ⇒ `stage()` never called ⇒ zero untracked residue (SC-003).
- Composed writers pass a thunk; `write_acceptance_matrix` stays standalone (wrapped, not broken).

## Acceptance scenarios → contract tests

- SC-001 red-first: `safe-commit` on a PRIMARY artifact, E2 mission, Target-Ref deleted → today refuses at HEAD-guard; after IC-05 → exit 0, committed to CONSOLIDATED, clean tree.
- SC-002: E2 `write_artifact` for issue-matrix/tracer/acceptance → `committed` (not `refused`).
- SC-003: unroutable write → 0 untracked files.
- SC-004: checkout lacking consolidated content → refuse-with-recovery naming the checkout, non-zero, no checkout performed.
- SC-005: `STATUS_STATE`/`DECISION_LOG` pre-consolidation resolution unchanged (non-regression).
- SC-009: `review --mode post-merge` on an E2 mission exits 0 end-to-end.
