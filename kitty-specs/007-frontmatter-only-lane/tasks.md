# Work Packages: Frontmatter-Only Lane Management

**Inputs**: Design documents from `kitty-specs/007-frontmatter-only-lane/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Testing updates included where existing tests require modification.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/` (flat structure per this feature's design).

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Include precise file paths or modules.

---

## Work Package WP01: Foundation - Legacy Detection & Shared Utilities (Priority: P0)

**Goal**: Create the foundation components that all other work packages depend on - legacy format detection and shared lane utilities.
**Independent Test**: `legacy_detector.py` correctly identifies old format (subdirectories present) vs new format (flat tasks/).
**Prompt**: `tasks/WP01-foundation-legacy-detection.md`

### Included Subtasks
- [ ] T001 Create `src/specify_cli/legacy_detector.py` with `is_legacy_format(feature_path)` function
- [ ] T002 [P] Add `get_lane_from_frontmatter(wp_path)` utility function in `scripts/tasks/task_helpers.py`
- [ ] T003 [P] Add same utility to `src/specify_cli/tasks_support.py` (keep in sync)
- [ ] T004 Document the LANES constant location and ensure single source of truth

### Implementation Notes
- `is_legacy_format()` checks for presence of `tasks/planned/`, `tasks/doing/`, `tasks/for_review/`, `tasks/done/` subdirectories with .md files
- `get_lane_from_frontmatter()` parses YAML frontmatter and returns `lane:` value, defaulting to "planned" with warning if missing
- Invalid lane values should raise clear error with valid options listed

### Parallel Opportunities
- T002 and T003 can proceed in parallel (different files)
- T001 is independent of T002/T003

### Dependencies
- None (starting package)

### Risks & Mitigations
- Risk: Inconsistent utility implementations in task_helpers.py vs tasks_support.py
- Mitigation: Consider extracting to shared module, or ensure both call same underlying logic

---

## Work Package WP02: CLI Refactoring - Update Command (Priority: P1) 🎯 MVP

**Goal**: Refactor the tasks CLI to use frontmatter-only lane management. Rename `move` to `update`, remove file movement operations.
spec-kitty agent workflow implement WP01
**Prompt**: `tasks/WP02-cli-refactoring-update-command.md`

### Included Subtasks
- [ ] T005 Rename `move_command()` to `update_command()` in `scripts/tasks/tasks_cli.py`
- [ ] T006 Refactor `stage_move()` to `stage_update()` - remove `shutil.move()`, update frontmatter only
- [ ] T007 Update `locate_work_package()` in `scripts/tasks/task_helpers.py` to search flat `tasks/` directory
- [ ] T008 [P] Update `locate_work_package()` in `src/specify_cli/tasks_support.py` (same changes)
- [ ] T009 Remove or repurpose `detect_lane_mismatch()` in `src/specify_cli/task_metadata_validation.py`
- [ ] T010 Update `list_command()` to scan flat `tasks/` and group by frontmatter lane
- [ ] T011 Add legacy format check at command entry points (warn but don't block)

### Implementation Notes
1. `locate_work_package()` changes:
   - Remove iteration through lane subdirectories
   - Scan `tasks/*.md` directly with glob pattern `WP*.md`
   - Read lane from frontmatter, not from path
2. `stage_update()` changes:
   - Keep frontmatter update logic
   - Remove file move logic entirely
   - Keep activity log append
   - Keep git staging of modified file
3. Command rename:
   - Update CLI registration from `move` to `update`
   - Update help text to reflect metadata-only change

### Parallel Opportunities
- T007 and T008 can proceed in parallel (different files, same changes)
- T009 is independent

### Dependencies
- Depends on WP01 (legacy detection, lane utilities)

### Risks & Mitigations
- Risk: Breaking existing workflows that expect `move` command
- Mitigation: Clean break is intentional; migration guide in documentation
- Risk: Rollback command depends on move logic
- Mitigation: Update rollback to use frontmatter-only approach

---

## Work Package WP03: Status Command & Dashboard (Priority: P1)

**Goal**: Enhance status command for frontmatter-based grouping and update dashboard scanner to read lanes from frontmatter.
**Independent Test**: `tasks_cli.py status` shows WPs grouped by their `lane:` frontmatter value, not directory location.
**Prompt**: `tasks/WP03-status-command-dashboard.md`

### Included Subtasks
- [ ] T012 Enhance `status` command in `scripts/tasks/tasks_cli.py` with formatted lane grouping
- [ ] T013 [P] Add auto-detect feature from worktree/branch when feature argument omitted
- [ ] T014 Update `scan_feature_kanban()` in `src/specify_cli/dashboard/scanner.py` to read frontmatter
- [ ] T015 [P] Update `scan_all_features()` in `src/specify_cli/dashboard/scanner.py` for frontmatter counting
- [ ] T016 [P] Update `src/specify_cli/acceptance.py` lane collection to use frontmatter

### Implementation Notes
1. Status command output format:
   ```
   Feature: 007-frontmatter-only-lane

   PLANNED (2)
     WP01  Foundation - Legacy Detection
     WP02  CLI Refactoring

   DOING (1)
     WP03  Status Command & Dashboard

   FOR REVIEW (0)
     (none)

   DONE (0)
     (none)
   ```
2. `scan_feature_kanban()` changes:
   - Remove `lane_dir = tasks_dir / lane` iteration
   - Scan flat `tasks/` directory
   - Group results by `lane:` frontmatter field
3. Auto-detect feature:
   - Parse current branch name (e.g., `007-frontmatter-only-lane`)
   - Or detect from worktree path

### Parallel Opportunities
- T014, T015, T016 can all proceed in parallel (different files)
- T13 is independent of dashboard changes

### Dependencies
- Depends on WP01 (lane utilities)
- Can proceed in parallel with WP02

### Risks & Mitigations
- Risk: Dashboard performance with many WPs
- Mitigation: Status command target is <1s for 50 WPs (per spec)

---

## Work Package WP04: Migration Command (Priority: P1)

**Goal**: Implement `spec-kitty upgrade` command to migrate from directory-based to frontmatter-only lanes.
**Independent Test**: Running `spec-kitty upgrade` flattens `tasks/planned/WP01.md` to `tasks/WP01.md` with `lane: "planned"` preserved.
**Prompt**: `tasks/WP04-migration-command.md`

### Included Subtasks
- [ ] T017 Create `src/specify_cli/commands/upgrade.py` with command skeleton
- [ ] T018 Implement feature scanning logic (find all features in kitty-specs/ and .worktrees/)
- [ ] T019 Implement single-feature migration logic (flatten lane directories)
- [ ] T020 Ensure lane preservation: set `lane:` frontmatter from source directory name
- [ ] T021 [P] Handle .worktrees/ migration (iterate all worktree feature directories)
- [ ] T022 Add confirmation prompt with explicit warning about file changes
- [ ] T023 Make migration idempotent (safe to run multiple times)
- [ ] T024 Clean up empty lane subdirectories after migration

### Implementation Notes
1. Migration algorithm:
   ```python
   for each feature in kitty-specs/ and .worktrees/*/kitty-specs/:
       if is_legacy_format(feature):
           for lane in ["planned", "doing", "for_review", "done"]:
               for wp_file in tasks/{lane}/*.md:
                   # Set lane: in frontmatter if not already correct
                   # Move file to tasks/
                   # Remove empty lane directory
   ```
2. Idempotency:
   - Check if file already in flat tasks/ before moving
   - Check if lane: field already set correctly
   - Skip already-migrated files
3. Warning prompt:
   ```
   WARNING: This will migrate your project to frontmatter-only lanes.

   Changes:
   - All WP files will be moved to flat tasks/ directories
   - Lane subdirectories (planned/, doing/, etc.) will be removed
   - The lane: frontmatter field becomes the source of truth

   This affects:
   - kitty-specs/ (X features)
   - .worktrees/ (Y features)

   Continue? [y/N]
   ```

### Parallel Opportunities
- T021 (worktrees handling) can be developed in parallel with T19 (single feature migration)

### Dependencies
- Depends on WP01 (legacy detection)
- Can proceed in parallel with WP02, WP03

### Risks & Mitigations
- Risk: Data loss if migration fails mid-way
- Mitigation: Idempotent design allows safe re-run; recommend git commit before upgrade
- Risk: Partial migration leaves inconsistent state
- Mitigation: Process all features in single transaction; rollback on failure

---

## Work Package WP05: Legacy Detection Integration (Priority: P2)

**Goal**: Integrate legacy format detection into CLI commands to warn users about old format.
**Independent Test**: Running `tasks_cli.py list` on old-format project shows warning suggesting upgrade.
**Prompt**: `tasks/WP05-legacy-detection-integration.md`

### Included Subtasks
- [ ] T025 Add legacy detection check to `tasks_cli.py` command entry points
- [ ] T026 Create warning message function with consistent formatting
- [ ] T027 Ensure warning doesn't block command execution (warn only)
- [ ] T028 Add detection to dashboard routes that display task information

### Implementation Notes
1. Warning message format:
   ```
   ⚠️  Legacy directory-based lanes detected.
   Run `spec-kitty upgrade` to migrate to frontmatter-only lanes.
   ```
2. Integration points:
   - `list_command()`
   - `status_command()` (new name for status)
   - `update_command()` (was move)
   - Dashboard feature views
3. Warning should appear once per command invocation, not per WP

### Parallel Opportunities
- T28 (dashboard) can proceed in parallel with T25-T27 (CLI)

### Dependencies
- Depends on WP01 (legacy detector), WP02 (CLI refactoring)

### Risks & Mitigations
- Risk: Warning fatigue if shown on every command
- Mitigation: Show once per session or allow suppression via flag

---

## Work Package WP06: Documentation & Test Updates (Priority: P2)

**Goal**: Update documentation and tests to reflect the new frontmatter-only lane system.
**Independent Test**: All existing tests pass; documentation accurately describes new behavior.
**Prompt**: `tasks/WP06-documentation-test-updates.md`

### Included Subtasks
- [ ] T029 Update `.kittify/AGENTS.md` - remove "don't edit lane" warning, explain new approach
- [ ] T030 [P] Update `.kittify/templates/task-prompt-template.md` - remove directory-based instructions
- [ ] T031 [P] Update/create `tasks/README.md` template for features explaining flat structure
- [ ] T032 Update `tests/test_tasks_cli_commands.py` for `update` command and flat structure
- [ ] T033 [P] Create `tests/test_migration.py` for upgrade command
- [ ] T034 [P] Update `tests/test_dashboard/test_scanner.py` for frontmatter-based scanning
- [ ] T035 Run full test suite and fix any regressions

### Implementation Notes
1. AGENTS.md changes:
   - Change: "Never manually edit the `lane:` field" → "You can directly edit the `lane:` field"
   - Add: Explanation of flat tasks/ structure
   - Add: Note that `move` command is now `update`
2. Template changes:
   spec-kitty agent workflow implement WP##
   - Remove: Directory-based instructions section
   spec-kitty agent workflow implement WP##
3. Test updates:
   - Change directory-based assertions to frontmatter-based
   - Add tests for legacy detection
   - Add tests for migration idempotency

### Parallel Opportunities
- T029, T030, T031 (docs) can proceed in parallel
- T032, T033, T034 (tests) can proceed in parallel

### Dependencies
- Depends on WP02, WP03, WP04, WP05 (need implementation complete to test)

### Risks & Mitigations
- Risk: Missing test coverage for edge cases
- Mitigation: Review spec edge cases section; ensure each has test coverage

---

## Dependency & Execution Summary

```
WP01 (Foundation) ──┬──→ WP02 (CLI) ────────┬──→ WP05 (Detection) ──→ WP06 (Docs/Tests)
                    │                        │
                    ├──→ WP03 (Status/Dash) ─┤
                    │                        │
                    └──→ WP04 (Migration) ───┘
```

- **Sequence**: WP01 → WP02/WP03/WP04 (parallel) → WP05 → WP06
- **Parallelization**: After WP01, work packages WP02, WP03, WP04 can proceed in parallel
- **MVP Scope**: WP01 + WP02 (Core lane update functionality)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create legacy_detector.py | WP01 | P0 | No |
| T002 | Add get_lane_from_frontmatter() to task_helpers.py | WP01 | P0 | Yes |
| T003 | Add get_lane_from_frontmatter() to tasks_support.py | WP01 | P0 | Yes |
| T004 | Document LANES constant location | WP01 | P0 | No |
| T005 | Rename move_command() to update_command() | WP02 | P1 | No |
| T006 | Refactor stage_move() to stage_update() | WP02 | P1 | No |
| T007 | Update locate_work_package() in task_helpers.py | WP02 | P1 | No |
| T008 | Update locate_work_package() in tasks_support.py | WP02 | P1 | Yes |
| T009 | Remove/repurpose detect_lane_mismatch() | WP02 | P1 | Yes |
| T010 | Update list_command() for flat structure | WP02 | P1 | No |
| T011 | Add legacy format check to CLI entry points | WP02 | P1 | No |
| T012 | Enhance status command with lane grouping | WP03 | P1 | No |
| T013 | Add auto-detect feature from worktree | WP03 | P1 | Yes |
| T014 | Update scan_feature_kanban() for frontmatter | WP03 | P1 | No |
| T015 | Update scan_all_features() for frontmatter | WP03 | P1 | Yes |
| T016 | Update acceptance.py lane collection | WP03 | P1 | Yes |
| T017 | Create upgrade.py command skeleton | WP04 | P1 | No |
| T018 | Implement feature scanning logic | WP04 | P1 | No |
| T019 | Implement single-feature migration | WP04 | P1 | No |
| T020 | Ensure lane preservation in frontmatter | WP04 | P1 | No |
| T021 | Handle .worktrees/ migration | WP04 | P1 | Yes |
| T022 | Add confirmation prompt with warning | WP04 | P1 | No |
| T023 | Make migration idempotent | WP04 | P1 | No |
| T024 | Clean up empty lane subdirectories | WP04 | P1 | No |
| T025 | Add legacy detection to CLI entry points | WP05 | P2 | No |
| T026 | Create warning message function | WP05 | P2 | No |
| T027 | Ensure warning doesn't block execution | WP05 | P2 | No |
| T028 | Add detection to dashboard routes | WP05 | P2 | Yes |
| T029 | Update AGENTS.md | WP06 | P2 | No |
| T030 | Update task-prompt-template.md | WP06 | P2 | Yes |
| T031 | Update/create tasks/README.md template | WP06 | P2 | Yes |
| T032 | Update test_tasks_cli_commands.py | WP06 | P2 | No |
| T033 | Create test_migration.py | WP06 | P2 | Yes |
| T034 | Update test_scanner.py | WP06 | P2 | Yes |
| T035 | Run full test suite and fix regressions | WP06 | P2 | No |
