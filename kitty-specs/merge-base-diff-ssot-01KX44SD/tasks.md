# Tasks: Consolidate git merge-base/diff idiom

**Mission**: merge-base-diff-ssot-01KX44SD | **Branch**: `fix/merge-base-diff-ssot` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Behaviour-preserving consolidation of the 5-copy `git merge-base` → `git diff --name-only` idiom onto one `core/vcs/git.py` surface. Zero behaviour change (NFR-001).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `git_merge_base` primitive | WP01 | |
| T002 | Add `git_diff_names` primitive (pathspec + diff_filter, C-002 kwargs) | WP01 | |
| T003 | Add `merge_base_changed_files` convenience | WP01 | |
| T004 | Direct tests: normal/empty-mb/mb-fail/diff-fail/pathspec/diff_filter | WP01 | |
| T005 | Direct tests: non-HEAD branch-target (F1) + range↔two-arg equivalence | WP01 | |
| T006 | Repoint `tasks_move_task._mt_pre_review_changed_files` | WP02 | [P] |
| T007 | Repoint `tasks_dependency_graph` (two-ref primitive, NOT HEAD convenience) | WP02 | [P] |
| T008 | Verify WP02 sites: no expected-value edits; dependency_graph branch-target asserted | WP02 | |
| T009 | Repoint `lanes/stale_check` primitives (+C-002; update dead-symbol/arch guard) | WP03 | [P] |
| T010 | Repoint `tasks_shared` first pass (preserve filter+dedup+content re-check verbatim) | WP03 | [P] |
| T011 | Repoint `acceptance._changed_workflow_files` (5th copy; diff_filter=AMR; three-dot pin) | WP03 | [P] |
| T012 | Verify WP03 sites + grep-verify zero residual copies across all 5 sites (SC-001) | WP03 | |
| T013 | Add `ScopeResult.from_override` classmethod | WP04 | |
| T014 | Retire hand-built ScopeResult in `tasks_move_task` override tier (out-of-map, respects symbol guard) | WP04 | |
| T015 | Tests for `from_override`; confirm `_MOVE_SET` symbol-identity guard green | WP04 | |

## Work Packages

### WP01 — Canonical merge-base/diff surface + direct tests

- **Goal**: Create the single source of truth (`git_merge_base`, `git_diff_names`, `merge_base_changed_files`) in `core/vcs/git.py`, proven by direct tests. Foundation for all repoints.
- **Priority**: P0 (MVP — everything depends on it) · **Dependencies**: none
- **Independent test**: `pytest -k merge_base_diff_surface` green; all FR-006 branches (incl. F1 branch-target + range↔two-arg equivalence) exercised.
- **Requirements**: FR-001, FR-006, NFR-002, NFR-003, NFR-004, C-002
- **Prompt**: [tasks/WP01-canonical-surface.md](tasks/WP01-canonical-surface.md) (~5 subtasks, ~300 lines)

- [x] T001 Add `git_merge_base(repo, ref_a, ref_b) -> str | None` (WP01)
- [x] T002 Add `git_diff_names(repo, base, head, *, pathspec=None, diff_filter=None) -> tuple[str, ...]` (WP01)
- [x] T003 Add `merge_base_changed_files(worktree, base_ref, *, pathspec=None, diff_filter=None) -> tuple[str, ...]` (WP01)
- [x] T004 Direct tests: normal, empty merge-base, merge-base fail, diff fail, pathspec, diff_filter (WP01)
- [x] T005 Direct tests: non-HEAD branch-target (F1 fence) + range↔two-arg equivalence on a real temp repo (WP01)

### WP02 — Low-risk HEAD/branch repoints

- **Goal**: Route the two straightforward copies through the surface, behaviour-preserving.
- **Priority**: P1 · **Dependencies**: WP01 · **Parallel with**: WP03 (disjoint files)
- **Independent test**: existing `tasks_move_task` + `tasks_dependency_graph` test suites green with no expected-value edits; a test asserts dependency_graph diffs `check_branch`, not HEAD.
- **Requirements**: FR-002, FR-004, NFR-001, C-001
- **Prompt**: [tasks/WP02-low-risk-repoints.md](tasks/WP02-low-risk-repoints.md) (~3 subtasks, ~250 lines)

- [x] T006 Repoint `tasks_move_task._mt_pre_review_changed_files` → `merge_base_changed_files` (WP02)
- [x] T007 Repoint `tasks_dependency_graph` → `git_merge_base(HEAD, check_branch)` + `git_diff_names(mb, check_branch)` — two-ref, NOT convenience (WP02)
- [x] T008 Verify: no expected-value test edits (NFR-001); dependency_graph branch-target behaviour asserted (WP02)

### WP03 — Higher-touch repoints

- **Goal**: Route the three copies with extra behaviour to preserve, each with named acceptance criteria; verify the consolidation is complete.
- **Priority**: P1 · **Dependencies**: WP01 · **Parallel with**: WP02 (disjoint files)
- **Independent test**: `stale_check`, `tasks_shared` (lane-hygiene content-diff), and `acceptance` workflow-evidence suites green; grep shows zero residual merge-base/diff copies across all 5 sites.
- **Requirements**: FR-003, FR-005, FR-008, NFR-001, NFR-002, C-001, C-002, C-003
- **Prompt**: [tasks/WP03-higher-touch-repoints.md](tasks/WP03-higher-touch-repoints.md) (~4 subtasks, ~380 lines)

- [x] T009 Repoint `lanes/stale_check` primitives (+C-002 kwargs; update dead-symbol/arch guard for removed `_git_merge_base`/`_git_diff_names`) (WP03)
- [x] T010 Repoint `tasks_shared._list_wp_branch_mission_specs_changes` first pass; preserve `startswith`+dedup+content re-check verbatim (WP03)
- [x] T011 Repoint `acceptance._changed_workflow_files` (5th copy) → `merge_base_changed_files(pathspec=".github/workflows", diff_filter="AMR")`; pin three-dot↔two-arg equivalence (WP03)
- [x] T012 Verify all three sites + grep-verify zero residual copies (SC-001); full `tests/architectural/` sweep + terminology guard + ruff/mypy (WP03)

### WP04 — Secondary: ScopeResult.from_override tidy (deferrable)

- **Goal**: Retire the hand-built `ScopeResult` construction behind a `from_override` classmethod. Isolated because of the `_MOVE_SET` symbol-identity guard (F7).
- **Priority**: P3 (deferrable — may become a follow-up) · **Dependencies**: WP01, WP02 (WP02 lands the `tasks_move_task` diff first)
- **Independent test**: `from_override` unit test green; `test_tasks_move_task_seam.py` `module_defs == _MOVE_SET` guard still green.
- **Requirements**: FR-007
- **Prompt**: [tasks/WP04-scoperesult-from-override.md](tasks/WP04-scoperesult-from-override.md) (~3 subtasks, ~200 lines)

- [ ] T013 Add `ScopeResult.from_override(targets)` classmethod on `review/pre_review_gate.py` (WP04)
- [ ] T014 Retire hand-built `ScopeResult` in `tasks_move_task` FR-004 override tier (out-of-map edit; no new module-level symbols) (WP04)
- [ ] T015 Tests for `from_override`; confirm `_MOVE_SET` symbol-identity guard green (WP04)

## Dependency Graph

```
WP01 (surface + tests)
 ├──> WP02 (low-risk repoints) ──> WP04 (secondary, deferrable)
 └──> WP03 (higher-touch repoints)     [WP02 ∥ WP03]
```

## MVP & Parallelization

- **MVP**: WP01 + WP02 + WP03 (the consolidation). WP04 is deferrable.
- **Parallel**: WP02 ∥ WP03 once WP01 lands (disjoint owned_files).
- **Closeout gate** (in WP03 T012): grep-verify zero residual copies; full `tests/architectural/` sweep; terminology guard; ruff + mypy clean.
