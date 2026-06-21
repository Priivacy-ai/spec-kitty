# Issue matrix — mission-surface-resolver-safety-net-01KVN754

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2040 | Single mission-surface resolver — strangler-finish (driver) | fixed | The 3-leg convergence landed: WP01 (helpers+reroute), WP04 (coord-empty Option B), WP05 (coord-deleted converge) drained the gate to 13/0. All five WPs approved. |
| #1718 | Create→first-write window must read primary | verified-already-fixed | Preserved structurally; WP04/WP05 keep the create-window → primary (C-002) and are guarded by the existing `test_create_first_write_window_resolves_primary`. Not regressed. |
| #2052 | Extract pure `_resolve_lanes_dir()` seam (residual of #1993) | fixed | WP03 (approved, commit `44e54ca2f`): pure extraction + zero-mock test, zero behavior change. |
| #2061 | commit_router inverted layering (coordination→cli reach-in) | fixed | WP02 (commit `c28f8f8d0`): routes to `surface_resolver.is_under_worktrees_segment`; import-direction guard added. |
| #2046 | Read-CLI bare-slug→coord unification | verified-already-fixed | Closed/fixed (read CLIs route through `resolve_handle_to_read_path`→`resolve_declared_mid8`); FR-008 / the `coord-*/bare` differential cells regression-guard it (WP01). |
| #1848 | `CoordinationBranchDeleted` hard-fail (merged PR) | verified-already-fixed | Not an open issue (merged PR). The coord-deleted hard-fail is preserved and converged across all three legs by WP05 (data-loss carve-out, C-001). |
| #2010 | [2007/C3] read-path resolver unification (parent, closed) | verified-already-fixed | Closed; its bug #15 typed-error pass-through already landed (`runtime_bridge.py:243-249`). This mission is its residual. |
| #15 | #2010 "bug #15" (typed-error flattening) — sub-bug, not a standalone issue | verified-already-fixed | Same evidence as #2010: `STATUS_READ_PATH_NOT_FOUND`/`MISSION_AMBIGUOUS_SELECTOR`/`COORDINATION_BRANCH_DELETED` preserved in `runtime_bridge.py`. Spurious prose-parse of "bug #15"; no standalone tracker item. |
| #1716 | Coordination topology coherence (epic) | deferred-with-followup | The coord-empty fallback policy facet is decided + applied (Option B, WP04; ADR 2026-06-19-1 amended); the broader topology-coherence epic remains tracked in #1716 (Follow-up: #1716). |
| #1868 | Canonical seams / authority-in-name-only (epic) | deferred-with-followup | The single-resolver guard adoption + the convergence advance it; the canonical-seams epic remains tracked in #1868 (Follow-up: #1868). |
| #1993 | Extraction-without-adoption (closed) | verified-already-fixed | Closed; #2052 is its live residual tracker, addressed by WP03 (the adoption: route + privatize the duplicate primitive). |
| #2007 | 3.2.0 read/write desync epic | deferred-with-followup | Being closed mission-by-mission; this mission discharges the surface-resolution convergence facet; epic remains tracked in #2007 (Follow-up: #2007). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
