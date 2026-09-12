# Tasks: Coord Commit-Surface Authority

**Mission**: coord-commit-surface-authority-01M1M553 | **Branch**: `fix/coord-commit-surface-authority`
**Plan**: [plan.md](./plan.md) · **Contract**: [contracts/authoritative-surface.md](./contracts/authoritative-surface.md)

4 work packages. **WP01 (foundation) lands first; WP02/WP03/WP04 run in parallel after** (disjoint files). All behavior changes follow characterize-then-diff (freeze current behavior, then re-freeze the intentional delta), asserting JSON-mode exit codes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `coordination/surface_authority.py` with `coord_topology_reachable` (pure) | WP01 | |
| T002 | Add `resolve_surface_authority` returning kind-aware `SurfaceVerdict` (RouteToCoord/Refuse/NoOp) | WP01 | |
| T003 | Unit tests for both functions across the full `{kind × topology × protection}` matrix | WP01 | [P] |
| T004 | Golden characterization harness freezing current arms (move-task, map-requirements, mark-status, no-op, spec-commit, wrong-surface) | WP01 | [P] |
| T005 | Consume `coord_topology_reachable` in `_resolve_default_topology_phase` (insert into `pr_bound` arm; key on primary-target protection) | WP02 | |
| T006 | Thread resolved topology through `create_mission_core` (no logic) | WP02 | |
| T007 | Freeze tripwire `test_mission_create.py:455` (pr-bound-on-feature/target=main → coord stays green) | WP02 | [P] |
| T008 | Regression: `--pr-bound --start-branch <unprotected>` mints NO coordination branch (closes #2533 + B16-c2 appearance) | WP02 | [P] |
| T009 | Collapse `_skip_target_branch_commit` + `_protected_branch_status_commit_error` into `resolve_surface_authority` in `tasks_shared.py` | WP03 | |
| T010 | Wire `move-task` (lifecycle-kind → RouteToCoord/exit-0) to the shared helper; behavior preserved | WP03 | |
| T011 | Wire `map-requirements` (planning-kind → Refuse/exit-1) to the shared helper; unify remedy string | WP03 | |
| T012 | Freeze `mark-status` event-log-only no-commit contract (assert; NO behavior change; do not revive `_ms_commit`) | WP03 | [P] |
| T013 | Characterization diff (JSON-mode exit codes) across the three commands + genuine-no-op→exit-0 rows | WP03 | [P] |
| T014 | Make `_resolve_mid8 → None` fail loud in `_materialise_coord_worktree` (`:700-701`) | WP04 | |
| T015 | Make the twin `except Exception → primary` fallbacks fail loud (`:705-711`, `:950-954`) + mid8-None at `:939-940` | WP04 | |
| T016 | Align `commit_router` refuse path to `resolve_surface_authority` (map `no_op_wrong_surface` → Refuse) | WP04 | |
| T017 | Guard tests: each hardened fallback fails loud (coord-routed) instead of silent primary write | WP04 | [P] |

## Work Packages

### WP01 — Authoritative-surface foundation *(the canonical rule)*
- **Goal**: one pure module `coordination/surface_authority.py` both `cli` and `coordination` import (no cycle); freeze current behavior in goldens.
- **Priority**: P1 (foundation) · **Independent test**: unit matrix + goldens green with zero consumer changes.
- **Subtasks**: T001, T002, T003, T004
- **Dependencies**: none
- **Risks**: getting the kind-aware rule wrong ripples to all consumers → mitigated by the full-matrix unit tests being authored here first.
- **Est**: ~350 lines.

### WP02 — Create-time topology honesty (#2533 / DD-2)
- **Goal**: mint COORD only when coordination routing is reachable (`pr_bound and (primary_protected(target) or current_is_primary)`); `--pr-bound --start-branch <unprotected>` → SINGLE_BRANCH.
- **Priority**: P1 · **Independent test**: tripwire T007 stays green; regression T008 proves no coord branch minted.
- **Subtasks**: T005, T006, T007, T008
- **Dependencies**: WP01
- **Risks**: keying on checkout instead of target would invert the #2581 tripwire → T007 guards it.
- **Est**: ~300 lines.

### WP03 — Task-command shared-rule consultation (#2300 / DD-1)
- **Goal**: move-task + map-requirements consult `resolve_surface_authority`; mark-status frozen event-log-only. Same rule, kind-aware verdicts.
- **Priority**: P1 · **Independent test**: characterization diff shows verdicts derive from the shared rule; JSON-mode exit codes asserted.
- **Subtasks**: T009, T010, T011, T012, T013
- **Dependencies**: WP01
- **Risks**: (a) reviving dead `_ms_commit` on mark-status — explicitly forbidden (T012); (b) regressing move-task's correct RouteToCoord — guarded by T013 freeze-first.
- **Est**: ~450 lines.

### WP04 — commit_router fail-loud all sites + align (DD-3)
- **Goal**: every silent primary-fallback in `commit_router` fails loud (or documented exclusion); refuse path aligned to the helper.
- **Priority**: P1 · **Independent test**: guard tests T017 — each fallback fails loud, no silent primary write.
- **Subtasks**: T014, T015, T016, T017
- **Dependencies**: WP01
- **Risks**: over-hardening a legitimate fallback — mitigated by architect finding that `_materialise_coord_worktree` is only reached under `use_coord` (coord-routed missions), so fail-loud is correct there.
- **Est**: ~350 lines.

## Sequencing & MVP
- **MVP / first**: WP01 (canonical rule) — nothing else can consume until it lands.
- **Then parallel**: WP02, WP03, WP04 (disjoint files, one lane each).
- **Integration**: WP02's regression + WP03's characterization diff + WP04's guard tests jointly prove INV-1..INV-4.
