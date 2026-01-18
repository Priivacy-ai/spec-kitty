# Work Packages: Smarter Feature Merge with Pre-flight and Auto-cleanup

**Inputs**: Design documents from `kitty-specs/017-smarter-feature-merge-with-preflight/`
**Prerequisites**: plan.md (architecture), spec.md (27 FRs, 6 user stories), data-model.md (entities)

**Tests**: Not explicitly requested - unit tests encouraged but not mandatory.

**Organization**: 29 subtasks (`T001`-`T029`) rolled into 6 work packages (`WP01`-`WP06`). Each WP maps to a module in the new `merge/` subpackage.

**Prompt Files**: Each work package has a matching prompt file in `tasks/` with detailed implementation guidance.

---

## Work Package WP01: Merge Subpackage Setup (Priority: P0)

**Goal**: Create the `src/specify_cli/merge/` subpackage structure and add `topological_sort()` to dependency graph.
**Independent Test**: Import `from specify_cli.merge import *` succeeds; `topological_sort()` passes basic tests.
**Prompt**: `tasks/WP01-merge-subpackage-setup.md`

### Included Subtasks
- [x] T001 Create `src/specify_cli/merge/` directory with `__init__.py` and module stubs
- [x] T002 Add `topological_sort()` function to `src/specify_cli/core/dependency_graph.py`

### Implementation Notes
- Create empty module files: `preflight.py`, `forecast.py`, `ordering.py`, `status_resolver.py`, `state.py`, `executor.py`
- Implement Kahn's algorithm for topological sort in `dependency_graph.py`
- Export new function in `__all__`

### Parallel Opportunities
- T001 and T002 can proceed in parallel (different files)

### Dependencies
- None (starting package)

### Risks & Mitigations
- None significant; foundational scaffolding only

---

## Work Package WP02: Pre-flight Validation (Priority: P1) 🎯 MVP

**Goal**: Implement pre-flight checks (FR-001 to FR-004) and CLI integration for User Story 1.
**Independent Test**: Run `spec-kitty merge` on a feature with dirty worktrees; all issues reported upfront with remediation steps.
**Prompt**: `tasks/WP02-preflight-validation.md`

### Included Subtasks
- [x] T003 [P] Implement `WPStatus` and `PreflightResult` dataclasses in `merge/preflight.py`
- [x] T004 [P] Implement `check_worktree_status()` for uncommitted change detection
- [x] T005 [P] Implement `check_target_divergence()` for fast-forward verification
- [x] T006 Implement `run_preflight()` orchestration and formatted output with remediation
- [x] T026 Update `merge.py` CLI to call preflight before any merge operation
- [x] T027 Add `--feature <slug>` flag for invocation from main branch

### Implementation Notes
1. Dataclasses use `@dataclass` from dataclasses module
2. `check_worktree_status()` runs `git status --porcelain` in each worktree
3. `check_target_divergence()` compares local and origin refs
4. `run_preflight()` collects all results into `PreflightResult`
5. Display using Rich console with color-coded status
6. CLI changes add new flags without breaking existing behavior

### Parallel Opportunities
- T003, T004, T005 can proceed in parallel (independent functions)

### Dependencies
- Depends on WP01 (subpackage structure)

### Risks & Mitigations
- Risk: Worktree detection fails in edge cases → reuse existing `find_wp_worktrees()` from merge.py

---

## Work Package WP03: Smart Merge Ordering (Priority: P2)

**Goal**: Implement dependency-based merge ordering (FR-008 to FR-011) and refactor merge execution for User Story 3.
**Independent Test**: Feature with WP02 depending on WP01 merges WP01 first regardless of worktree location.
**Prompt**: `tasks/WP03-smart-merge-ordering.md`

### Included Subtasks
- [x] T010 [P] Implement `get_merge_order()` in `merge/ordering.py` using `build_dependency_graph()` and `topological_sort()`
- [x] T011 [P] Add cycle detection error reporting with clear cycle path display
- [x] T012 [P] Implement fallback to numerical order when frontmatter lacks dependencies
- [x] T021 Extract core merge loop from `merge.py` into `merge/executor.py`
- [x] T022 Integrate preflight into executor flow
- [x] T023 Integrate ordering into executor (use ordered list instead of sorted glob)

### Implementation Notes
1. `get_merge_order()` calls `build_dependency_graph()` on feature's tasks/ directory
2. If graph has dependencies, call `topological_sort()`; else sort by WP number
3. Cycle detection uses existing `detect_cycles()` from `dependency_graph.py`
4. `executor.py` becomes the main entry point; `merge.py` remains a thin CLI wrapper
5. Executor takes ordered WP list and processes sequentially

### Parallel Opportunities
- T010, T011, T012 can proceed in parallel (different concerns)
- T021, T022, T023 must be sequential (refactoring chain)

### Dependencies
- Depends on WP01 (topological_sort)
- Depends on WP02 (preflight integration)

### Risks & Mitigations
- Risk: Refactoring breaks existing merge behavior → keep legacy paths until fully tested

---

## Work Package WP04: Conflict Forecast (Priority: P2)

**Goal**: Implement conflict prediction for `--dry-run` (FR-005 to FR-007) for User Story 2.
**Independent Test**: `spec-kitty merge --dry-run` shows files that will conflict and marks status files as auto-resolvable.
**Prompt**: `tasks/WP04-conflict-forecast.md`

### Included Subtasks
- [ ] T007 [P] Implement `ConflictPrediction` dataclass in `merge/forecast.py`
- [ ] T008 [P] Implement `build_file_wp_mapping()` using `git diff --name-only`
- [ ] T009 [P] Implement `detect_status_files()` pattern matching for `kitty-specs/**/tasks/*.md`

### Implementation Notes
1. For each WP branch, run `git diff --name-only <target>...<branch>` to get modified files
2. Build dict: `{file_path: [wp_ids]}` where len > 1 indicates potential conflict
3. Use `fnmatch` to detect status file patterns
4. Mark status files as "auto-resolvable" in dry-run output
5. Integrate into executor's dry-run path

### Parallel Opportunities
- All subtasks can proceed in parallel (independent functions)

### Dependencies
- Depends on WP01 (subpackage)
- Depends on WP03 (executor integration point)

### Risks & Mitigations
- Risk: git merge-tree not available (< 2.38) → use diff-based heuristic as fallback

---

## Work Package WP05: Status File Auto-Resolution (Priority: P3)

**Goal**: Implement automatic conflict resolution for status files (FR-012 to FR-016) for User Story 4.
**Independent Test**: Merge with conflicting `lane:` values in task frontmatter auto-resolves without user intervention.
**Prompt**: `tasks/WP05-status-file-auto-resolution.md`

### Included Subtasks
- [ ] T013 [P] Implement `parse_conflict_markers()` to extract HEAD/theirs content from conflict markers
- [ ] T014 [P] Implement `resolve_lane_conflict()` with "more done" wins logic
- [ ] T015 [P] Implement `resolve_checkbox_conflict()` preferring `[x]` over `[ ]`
- [ ] T016 [P] Implement `resolve_history_conflict()` merging arrays chronologically
- [ ] T024 Integrate status resolution into executor (call after each WP merge)
- [ ] T028 Ensure cleanup continues even if resolution fails for some files
- [ ] T029 [P] Update slash command templates for all 12 agents with new merge features

### Implementation Notes
1. After `git merge`, check `git diff --name-only --diff-filter=U` for conflicted files
2. For each file matching `kitty-specs/**/tasks/*.md` or `kitty-specs/**/tasks.md`:
   - Parse conflict markers (<<<<<<< / ======= / >>>>>>>)
   - Extract YAML frontmatter from both sides
   - Apply resolution rules based on field type
   - Write resolved content, run `git add`
3. If non-status conflicts remain, pause for manual resolution
4. Lane priority: done > for_review > doing > planned

### Parallel Opportunities
- T013-T016 can proceed in parallel (independent resolution functions)
- T029 can proceed in parallel with implementation

### Dependencies
- Depends on WP03 (executor)

### Risks & Mitigations
- Risk: Malformed YAML causes resolution failure → validate with ruamel.yaml, skip file if invalid
- Risk: Non-status content in status files → only resolve recognized patterns

---

## Work Package WP06: Merge State & Resume (Priority: P4)

**Goal**: Implement merge state persistence and `--resume` capability (FR-021 to FR-024) for User Story 6.
**Independent Test**: Interrupt merge mid-way (Ctrl+C), run `spec-kitty merge --resume`, merge continues from next WP.
**Prompt**: `tasks/WP06-merge-state-and-resume.md`

### Included Subtasks
- [ ] T017 [P] Implement `MergeState` dataclass in `merge/state.py`
- [ ] T018 [P] Implement `save_state()` and `load_state()` for `.kittify/merge-state.json`
- [ ] T019 Implement `--resume` flag detection and continuation logic in CLI
- [ ] T020 Implement `clear_state()` on successful completion or `--abort`
- [ ] T025 Integrate state persistence into executor (save after each WP)

### Implementation Notes
1. `MergeState` fields: feature_slug, target_branch, wp_order, completed_wps, current_wp, has_pending_conflicts, strategy, timestamps
2. Save state to `.kittify/merge-state.json` after each WP merge
3. On `--resume`: load state, skip completed WPs, continue from current_wp
4. Detect active git merge state with `git rev-parse -q --verify MERGE_HEAD`
5. Clear state file on success or explicit `--abort` flag

### Parallel Opportunities
- T017, T018 can proceed in parallel (dataclass and I/O)
- T019, T020, T025 must be sequential (integration chain)

### Dependencies
- Depends on WP03 (executor)

### Risks & Mitigations
- Risk: State file corruption → validate JSON on load, clear and restart if invalid
- Risk: Git merge state mismatch → check MERGE_HEAD before resuming

---

## Dependency & Execution Summary

```
WP01 (Setup)
  │
  ├──→ WP02 (Pre-flight) 🎯 MVP
  │
  └──→ WP03 (Ordering)
         │
         ├──→ WP04 (Forecast)
         │
         ├──→ WP05 (Status Resolution)
         │
         └──→ WP06 (State & Resume)
```

- **Sequence**: WP01 → WP02 → WP03 → WP04/WP05/WP06 (last three can parallelize after WP03)
- **Parallelization**: WP04, WP05, WP06 are independent of each other after WP03 completes
- **MVP Scope**: WP01 + WP02 delivers pre-flight validation, the highest-impact improvement

---

## Subtask Index (Reference)

| ID | Summary | WP | Priority | Parallel |
|----|---------|-----|----------|----------|
| T001 | Create merge/ subpackage structure | WP01 | P0 | Yes |
| T002 | Add topological_sort() to dependency_graph.py | WP01 | P0 | Yes |
| T003 | Implement WPStatus and PreflightResult dataclasses | WP02 | P1 | Yes |
| T004 | Implement worktree dirty check | WP02 | P1 | Yes |
| T005 | Implement target branch divergence check | WP02 | P1 | Yes |
| T006 | Implement run_preflight() with formatted output | WP02 | P1 | No |
| T007 | Implement ConflictPrediction dataclass | WP04 | P2 | Yes |
| T008 | Build file→WPs mapping via git diff | WP04 | P2 | Yes |
| T009 | Detect status file patterns in predictions | WP04 | P2 | Yes |
| T010 | Implement get_merge_order() | WP03 | P2 | Yes |
| T011 | Add cycle detection error reporting | WP03 | P2 | Yes |
| T012 | Fallback to numerical order | WP03 | P2 | Yes |
| T013 | Implement conflict marker parser | WP05 | P3 | Yes |
| T014 | Implement lane resolution (more-done wins) | WP05 | P3 | Yes |
| T015 | Implement checkbox resolution | WP05 | P3 | Yes |
| T016 | Implement history array merge | WP05 | P3 | Yes |
| T017 | Implement MergeState dataclass | WP06 | P4 | Yes |
| T018 | Implement save_state() and load_state() | WP06 | P4 | Yes |
| T019 | Implement --resume detection and continuation | WP06 | P4 | No |
| T020 | Implement clear_state() | WP06 | P4 | No |
| T021 | Extract merge logic to executor.py | WP03 | P2 | No |
| T022 | Integrate preflight into executor | WP03 | P1 | No |
| T023 | Integrate ordering into executor | WP03 | P2 | No |
| T024 | Integrate status resolution into executor | WP05 | P3 | No |
| T025 | Integrate state persistence into executor | WP06 | P4 | No |
| T026 | Update merge.py CLI with preflight call | WP02 | P1 | No |
| T027 | Add --feature flag for main-branch invocation | WP02 | P1 | No |
| T028 | Ensure cleanup continues on partial failure | WP05 | P3 | No |
| T029 | Update slash command templates for all agents | WP05 | P3 | Yes |
