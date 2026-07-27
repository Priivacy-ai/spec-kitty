# Tasks: Mission-Surface Resolver Strangler-Finish

**Mission**: mission-surface-resolver-safety-net-01KVN754 · **Branch**: feat/mission-surface-resolver-safety-net

The differential equivalence gate (`tests/missions/test_surface_resolution_equivalence.py`) is the
deletion-safety net: live baseline **9 passed / 4 xfailed** → **9/4 (WP01, unchanged) → 11/2 (WP04) →
13/0 (WP05)**, green at every WP boundary. **Campsite-cleaning (#1970) is active for every WP.**

> Post-tasks adversarial squad re-baselined the decomposition (WP01 drains zero; the read-path divergence was
> already closed by #2046). Each WP now OWNS the tests its change breaks; xfail retirement is **per-row**; the
> shared `*/bare` constant is deleted only in WP05 (last). Operator chose the **full shared-helper extraction**
> (WP01 introduces `coord_feature_dir()` + `probe_coord_state()`; WP04/WP05 adopt them).

## Lanes & dependencies

- **Chain (lanes a→d→e, serialized by deps + cross-lane tip-merge):** WP01 → WP04 → WP05.
- **Parallel (disjoint lanes b, c):** WP02, WP03.

## Subtask Index

| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Extract `coord_feature_dir()` shared compose; route the 2 read-path sites | WP01 | |
| T002 | Extract `probe_coord_state()` (reuse `_coord_branch_exists`); route read-path | WP01 | |
| T003 | Reroute the 2 external callers onto `resolve_handle_to_read_path`; drop dead derivations | WP01 | |
| T004 | Privatize `resolve_mission_read_path` → `_resolve_mission_read_path`; preserve the shim alias | WP01 | |
| T005 | NFR-005 zero-direct-callers assertion | WP01 | |
| T006 | Zero-mock unit test for the shared helpers | WP01 | |
| T007 | Campsite: adjacent debt in touched files | WP01 | |
| T008 | Swap `commit_router` import to `surface_resolver.is_under_worktrees_segment` (#2061) | WP02 | [P] |
| T009 | Byte-identical + no-`coordination→cli`-reach-in test | WP02 | [P] |
| T010 | Campsite (do NOT delete `merge.path_is_under_worktrees` — 5 callers) | WP02 | [P] |
| T011 | Verify-first the lanes-dir behavior at `implement.py:~1019` (#2052) | WP03 | [P] |
| T012 | Extract pure `_resolve_lanes_dir(repo_root, mission_slug)` | WP03 | [P] |
| T013 | Zero-mock unit test (coord + flat topology) | WP03 | [P] |
| T014 | Campsite | WP03 | [P] |
| T015 | Coord-empty → primary fallback (stop raising; adopt `probe_coord_state`) | WP04 | |
| T016 | Emit the LOUD warning (WARNING-level, both recovery commands) | WP04 | |
| T017 | Delete `CoordinationWorktreeEmpty` + 2 helpers; route `:637` to `candidate_feature_dir_for_mission` | WP04 | |
| T018 | Warning-fires test (3-part non-fakeable conjunction) | WP04 | |
| T019 | OWN + invert the stranded coord-empty tests (collapse, aggregate, mission_runtime, +2 out-of-map) | WP04 | |
| T020 | Retire the coord-empty xfail cells PER-ROW (9/4 → 11/2) | WP04 | |
| T021 | Campsite: stale "primary fallback" docstring | WP04 | |
| T022 | Fold the deleted-branch discriminator into the read-path leg (out-of-map) | WP05 | |
| T023 | Aggregate: `except CoordinationBranchDeleted: raise` BEFORE `StatusReadPathNotFound` (+ import) | WP05 | |
| T024 | Remove the 2 dead-symbol allowlist entries (BLOCKER-3 + the dangling one) | WP05 | |
| T025 | Migrate the `agent status` public contract (two `except` tuples) | WP05 | |
| T026 | Migrate the coord-deleted contract tests | WP05 | |
| T027 | Campsite C6 (split-brain delete) + C8 (literal hoist) | WP05 | |
| T028 | Retire coord-deleted xfail cells + delete the shared constant LAST → 13/0 | WP05 | |

## Work Packages

### WP01 — Shared-helper foundation + privatize/reroute the read primitive
**Goal:** extract `coord_feature_dir()`/`probe_coord_state()`, reroute the 2 callers, privatize the worker,
preserve the back-compat shim. **WP01 drains ZERO cells (gate stays 9/4).** **Deps:** none.
Prompt: [WP01-privatize-reroute-read-primitive.md](tasks/WP01-privatize-reroute-read-primitive.md)

- [ ] T001 Extract `coord_feature_dir()`; route 2 read-path sites (WP01)
- [ ] T002 Extract `probe_coord_state()` (reuse `_coord_branch_exists`) (WP01)
- [ ] T003 Reroute 2 external callers; drop dead derivations (keep `_mid8_from_primary_meta`) (WP01)
- [ ] T004 Privatize worker; preserve shim public alias (WP01)
- [ ] T005 NFR-005 zero-direct-callers (WP01)
- [ ] T006 Zero-mock helper unit test (WP01)
- [ ] T007 Campsite (WP01)

### WP02 — commit_router inverted-layering fix (#2061)
**Goal:** remove the only `coordination/ → cli/` reach-in, byte-identical. Do NOT delete the merge helper
(5 callers). **Deps:** none (parallel). Prompt: [WP02-commit-router-layering.md](tasks/WP02-commit-router-layering.md)

- [ ] T008 Swap import to `surface_resolver.is_under_worktrees_segment` (WP02)
- [ ] T009 Byte-identical + no-reach-in test (WP02)
- [ ] T010 Campsite (keep `merge.path_is_under_worktrees`) (WP02)

### WP03 — `_resolve_lanes_dir` pure extraction (#2052)
**Goal:** extract a pure, zero-mock, topology-aware seam (verify-first — behavior already correct).
**Deps:** none (parallel). Prompt: [WP03-resolve-lanes-dir-extraction.md](tasks/WP03-resolve-lanes-dir-extraction.md)

- [ ] T011 Verify-first the lanes-dir behavior (WP03)
- [ ] T012 Extract pure `_resolve_lanes_dir` (WP03)
- [ ] T013 Zero-mock unit test (WP03)
- [ ] T014 Campsite (WP03)

### WP04 — Coord-empty Option B (loud primary fallback)
**Goal:** coord-empty → primary + loud warning; delete the error + 2 helpers; own+invert the stranded
coord-empty tests; per-row xfail (9/4 → 11/2). **Deps:** WP01.
Prompt: [WP04-coord-empty-option-b.md](tasks/WP04-coord-empty-option-b.md)

- [ ] T015 Coord-empty → primary fallback (adopt `probe_coord_state`) (WP04)
- [ ] T016 LOUD warning (WARNING-level, both recovery commands) (WP04)
- [ ] T017 Delete `CoordinationWorktreeEmpty` + 2 helpers; route `:637` (WP04)
- [ ] T018 Warning-fires test (3-part non-fakeable) (WP04)
- [ ] T019 OWN + invert stranded coord-empty tests (WP04)
- [ ] T020 Retire coord-empty xfail cells PER-ROW → 11/2 (WP04)
- [ ] T021 Campsite (stale docstring) (WP04)

### WP05 — Coord-deleted convergence + public-contract migration
**Goal:** converge coord-deleted on `CoordinationBranchDeleted` (hard-fail preserved) via the more-specific
`except … : raise` + the read-path fold; migrate the `agent status` contract + the 2 allowlist entries;
C6 split-brain delete; per-row xfail + delete the shared constant last → 13/0. **Deps:** WP04.
Prompt: [WP05-coord-deleted-convergence.md](tasks/WP05-coord-deleted-convergence.md)

- [ ] T022 Fold deleted-branch discriminator into read-path (out-of-map) (WP05)
- [ ] T023 Aggregate `except CoordinationBranchDeleted: raise` before `StatusReadPathNotFound` (+ import) (WP05)
- [ ] T024 Remove the 2 dead-symbol allowlist entries (WP05)
- [ ] T025 Migrate `agent status` public contract (two `except` tuples) (WP05)
- [ ] T026 Migrate coord-deleted contract tests (WP05)
- [ ] T027 Campsite C6 split-brain delete + C8 literal hoist (WP05)
- [ ] T028 Retire coord-deleted xfail + delete shared constant LAST → 13/0 (WP05)
