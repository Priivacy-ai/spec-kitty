# Tasks: Merge Abort, Review, and Status Hardening Sprint

**Mission ID**: 01KQFF35BPH2H8971KR0TEY8ST
**Branch**: `main` → `main`
**Generated**: 2026-04-30

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Locate `_GLOBAL_MERGE_LOCK_ID` constant and derive lock file path | WP01 | |
| T002 | Add idempotent lock file deletion to `--abort` handler | WP01 | |
| T003 | Add idempotent merge-state JSON deletion to `--abort` handler | WP01 | [P] |
| T004 | Add conditional `git merge --abort` for in-progress git merges | WP01 | |
| T005 | Annotate `merge.py` BLE001 suppressions (L1026, L1275) | WP01 | [P] |
| T006 | Write tests: `test_abort_clears_lock_and_state`, `test_abort_idempotent` | WP01 | |
| T007 | Add `_get_latest_review_cycle_verdict(wp_dir)` helper to `agent/tasks.py` | WP02 | |
| T008 | Add verdict enum validation (warn on unknown values) | WP02 | [P] |
| T009 | Add rejected-verdict guard to `move_task()` for `--force` transitions to `approved`/`done` | WP02 | |
| T010 | Add `--skip-review-artifact-check` option to `move_task()` | WP02 | [P] |
| T011 | Locate lane guard block (~L1003), load `planning_base_branch` from meta.json | WP02 | |
| T012 | Rewrite lane guard error message to name planning branch and suggest `git show` | WP02 | |
| T013 | Add legacy-mission fallback when `meta.json` is absent or missing the field | WP02 | [P] |
| T014 | Write tests: verdict guard + skip option + lane guard message | WP02 | |
| T015 | Annotate bare BLE001 suppressions in `src/specify_cli/cli/helpers.py` | WP03 | [P] |
| T016 | Annotate bare suppressions in `src/specify_cli/cli/commands/charter.py` | WP03 | [P] |
| T017 | Annotate bare suppressions in `materialize.py`, `tracker.py`, `mission_type.py` | WP03 | [P] |
| T018 | Annotate bare suppressions in `charter_bundle.py` | WP03 | [P] |
| T019 | Run `uv run ruff check src/` end-to-end; fix any breakage | WP03 | |
| T020 | Read `command-templates/review.md` and identify insertion point | WP04 | | [D] |
| T021 | Add deletion-test checklist item to error-path coverage section | WP04 | | [D] |
| T022 | Confirm no generated agent copies were modified | WP04 | | [D] |
| T023 | Add `_get_wp_review_verdict()` helper and stale-verdict warning in `show_kanban_status()` | WP05 | |
| T024 | Add `_get_last_event_time()` helper for stall age computation | WP05 | [P] |
| T025 | Add stall detection loop in `show_kanban_status()` with config-loaded threshold | WP05 | |
| T026 | Return stalled WP list from `show_kanban_status()` in return dict | WP05 | |
| T027 | Surface stalled WP intervention block in `next_cmd.py` | WP05 | |
| T028 | Write tests: stale verdict warning, stall detection (below/at/above threshold), next output | WP05 | |
| T029 | Create `review.py` with mission resolver, WP lane check (FR-013) | WP06 | |
| T030 | Implement dead-code scan step (FR-014) | WP06 | |
| T031 | Implement BLE001 unjustified-suppression audit step (FR-015) | WP06 | |
| T032 | Implement report writer: `mission-review-report.md` with frontmatter (FR-016) | WP06 | |
| T033 | Register `review` command in `cli/commands/__init__.py` | WP06 | |
| T034 | Write integration test for `spec-kitty review --mission` | WP06 | |

## Work Packages

### Phase 1 — Bugs

---

## WP01 — merge --abort cleanup + merge.py BLE001 (#903, #907-partial)

**Goal**: Make `spec-kitty merge --abort` idempotent and fully clean up after a crashed merge. Also annotate the two BLE001 suppressions in `merge.py` that lack justification, keeping all `merge.py` changes in one WP.
**Priority**: High (blocks repeated merge attempts after a crash)
**Estimated prompt size**: ~280 lines
**Independent test**: Run `spec-kitty merge --abort` twice on a repo with no lock/state; both invocations exit 0.

**Subtasks**:
- [ ] T001 Locate `_GLOBAL_MERGE_LOCK_ID` constant and derive lock file path (WP01)
- [ ] T002 Add idempotent lock file deletion to `--abort` handler (WP01)
- [ ] T003 Add idempotent merge-state JSON deletion to `--abort` handler (WP01)
- [ ] T004 Add conditional `git merge --abort` for in-progress git merges (WP01)
- [ ] T005 Annotate `merge.py` BLE001 suppressions at L1026 and L1275 (WP01)
- [ ] T006 Write tests: `test_abort_clears_lock_and_state`, `test_abort_idempotent` (WP01)

**Owned files**: `src/specify_cli/cli/commands/merge.py`, `tests/specify_cli/cli/commands/test_merge.py` (create if absent)
**Dependencies**: none
**Risks**: Lock path derivation must match actual path used by `acquire_merge_lock`; verify by grepping for the path construction pattern.

---

## WP02 — move-task verdict guard + lane guard UX (#904, #905)

**Goal**: Block force-approvals when the latest review artifact has `verdict: rejected`; improve lane guard error message to name the planning branch. Both changes are in `agent/tasks.py`.
**Priority**: High (two separate correctness gaps, same file)
**Estimated prompt size**: ~420 lines
**Independent test**: Run `move-task WP01 --to approved --force` on a WP whose review-cycle-1.md has `verdict: rejected`; command exits 1 with a named warning.

**Subtasks**:
- [ ] T007 Add `_get_latest_review_cycle_verdict(wp_dir)` helper to `agent/tasks.py` (WP02)
- [ ] T008 Add verdict enum validation: warn on unknown values (WP02)
- [ ] T009 Add rejected-verdict guard to `move_task()` for `--force` to `approved`/`done` (WP02)
- [ ] T010 Add `--skip-review-artifact-check` option to `move_task()` (WP02)
- [ ] T011 Locate lane guard block (~L1003) and load `planning_base_branch` from meta.json (WP02)
- [ ] T012 Rewrite lane guard error to name planning branch + suggest `git show` (WP02)
- [ ] T013 Add legacy-mission fallback when `meta.json`/field is absent (WP02)
- [ ] T014 Write tests: verdict guard, skip option, lane guard message variants (WP02)

**Owned files**: `src/specify_cli/cli/commands/agent/tasks.py`, `tests/specify_cli/cli/commands/agent/test_tasks.py` (create if absent)
**Dependencies**: none
**Risks**: `move_task()` signature change (new option) must not break callers that don't pass it. Default `False` handles this.

---

### Phase 2 — Enhancements (independent, parallelisable)

---

## WP03 — BLE001 suppression justification (#907)

**Goal**: Every `# noqa: BLE001` in `src/specify_cli/cli/commands/` and `src/specify_cli/cli/helpers.py` must have an inline justification. Auth suppressions already have justifications and need no changes.
**Priority**: Medium
**Estimated prompt size**: ~220 lines
**Independent test**: `grep "noqa: BLE001" src/specify_cli/cli/ src/specify_cli/auth/` — every match has text after `BLE001`. `uv run ruff check src/` passes.

**Subtasks**:
- [ ] T015 Annotate bare BLE001 suppressions in `src/specify_cli/cli/helpers.py` (WP03)
- [ ] T016 Annotate bare suppressions in `src/specify_cli/cli/commands/charter.py` (WP03)
- [ ] T017 Annotate bare suppressions in `materialize.py`, `tracker.py`, `mission_type.py` (WP03)
- [ ] T018 Annotate bare suppressions in `charter_bundle.py` (WP03)
- [ ] T019 Run `uv run ruff check src/`; fix any breakage (WP03)

**Owned files**: `src/specify_cli/cli/helpers.py`, `src/specify_cli/cli/commands/charter.py`, `src/specify_cli/cli/commands/materialize.py`, `src/specify_cli/cli/commands/tracker.py`, `src/specify_cli/cli/commands/mission_type.py`, `src/specify_cli/cli/commands/charter_bundle.py`
**Dependencies**: none
**Risks**: Bare suppressions that mask genuine errors should be fixed (exception propagation) rather than justified; read each context before annotating.

---

## WP04 — WP review DoD deletion-test item (#906)

**Goal**: Add an explicit "deletion test" checklist item to the WP review source template so reviewers must verify error-path tests are reachable.
**Priority**: High (systematic review quality gap)
**Estimated prompt size**: ~140 lines
**Independent test**: The word "deletion test" appears in `src/specify_cli/missions/software-dev/command-templates/review.md`; no `.claude/commands/` or other agent-copy files are modified.

**Subtasks**:
- [x] T020 Read `command-templates/review.md` and identify insertion point (WP04)
- [x] T021 Add deletion-test checklist item under error-path test coverage section (WP04)
- [x] T022 Confirm no generated agent copies were modified (WP04)

**Owned files**: `src/specify_cli/missions/software-dev/command-templates/review.md`
**Dependencies**: none
**Risks**: None — pure text addition to a template.

---

## WP05 — stale verdict status warning + stalled reviewer detection (#904-status, #909)

**Goal**: `show_kanban_status()` warns when a `done`/`approved` WP has `verdict: rejected`; marks `in_review` WPs stalled after the threshold; `spec-kitty next` surfaces intervention commands for stalled WPs.
**Priority**: Medium
**Estimated prompt size**: ~310 lines
**Independent test**: Create a mock `in_review` WP with last event 45 min ago; `show_kanban_status()` returns `⚠ STALLED — no move-task in 45m`; running `spec-kitty next` prints intervention commands.

**Subtasks**:
- [ ] T023 Add `_get_wp_review_verdict()` helper + stale-verdict warning in `show_kanban_status()` (WP05)
- [ ] T024 Add `_get_last_event_time()` helper for age computation (WP05)
- [ ] T025 Add stall detection loop in `show_kanban_status()` with config-loaded threshold (WP05)
- [ ] T026 Return stalled WP list from `show_kanban_status()` in return dict (WP05)
- [ ] T027 Surface stalled WP intervention block in `next_cmd.py` (WP05)
- [ ] T028 Write tests: stale verdict warning, stall detection, next output (WP05)

**Owned files**: `src/specify_cli/agent_utils/status.py`, `src/specify_cli/cli/commands/next_cmd.py`, tests
**Dependencies**: none
**Risks**: Config loading must gracefully handle absence of `review.stall_threshold_minutes`; default to 30.

---

### Phase 3 — New command

---

## WP06 — spec-kitty review --mission command (#908)

**Goal**: Add `spec-kitty review --mission <slug>` as a first-class post-merge validation gate with WP lane check, dead-code scan, and BLE001 audit.
**Priority**: Medium
**Estimated prompt size**: ~380 lines
**Independent test**: `spec-kitty review --mission merge-review-status-hardening-sprint-01KQFF35` exits 0 after mission is done; `mission-review-report.md` is written with `verdict: pass`.

**Subtasks**:
- [ ] T029 Create `review.py` with mission resolver and WP lane check (FR-013) (WP06)
- [ ] T030 Implement dead-code scan step: diff + grep for unreferenced symbols (FR-014) (WP06)
- [ ] T031 Implement BLE001 unjustified-suppression audit step (FR-015) (WP06)
- [ ] T032 Implement report writer: `mission-review-report.md` with frontmatter (FR-016) (WP06)
- [ ] T033 Register `review` command in `cli/commands/__init__.py` (WP06)
- [ ] T034 Write integration test for `spec-kitty review --mission` (WP06)

**Owned files**: `src/specify_cli/cli/commands/review.py`, `src/specify_cli/cli/commands/__init__.py`, tests
**Dependencies**: none
**Risks**: Dead-code scan is heuristic (`def`/`class` grep + caller grep); document the known false-positive cases (e.g., `__all__` exports, dynamic dispatch) in the command's `--help`.
