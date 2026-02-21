# Research: Frontmatter-Only Lane Management

**Feature**: 007-frontmatter-only-lane
**Date**: 2025-12-17
**Status**: Complete

## Executive Summary

Codebase exploration confirms the refactoring is well-scoped. Lane management flows through ~6 core modules with ~20 functions directly depending on directory-based lane detection. The architecture supports clean separation of concerns, making the transition to frontmatter-only lanes straightforward.

## Key Decisions

### D-001: Command Rename (move → update)

**Decision**: Rename the `move` command to `update`

**Rationale**:

- "Move" implies file relocation, which no longer happens
- "Update" accurately describes the operation: modifying frontmatter metadata
- Clean semantic break reinforces the new paradigm

**Alternatives Rejected**:

- Keep "move" name: Confusing since no files move
- "set-lane": Too verbose, breaks existing muscle memory partially

### D-002: No Backwards Compatibility

**Decision**: Clean break - new format only, require migration first

**Rationale**:

- Hybrid mode adds significant complexity
- Two code paths = two sets of bugs
- Clear migration path via `spec-kitty upgrade`
- User preference for clean breaks

**Alternatives Rejected**:

- Support both formats: Complexity not worth transitional convenience
- Auto-migrate on first command: Too surprising, could cause data issues

### D-003: All-at-Once Migration

**Decision**: Single `spec-kitty upgrade` migrates main repo + all worktrees

**Rationale**:

- Consistent state across entire project
- No confusion about which features are migrated
- Single confirmation prompt for entire operation
- Idempotent design allows safe re-runs

**Alternatives Rejected**:

- Per-feature migration: More prompts, inconsistent state possible
- Per-worktree migration: Complex, worktrees should track main repo format

### D-004: Default Lane for Missing Field

**Decision**: Default to "planned" with warning when `lane:` field missing

**Rationale**:

- "Planned" is the safest default (nothing lost, nothing in progress)
- Warning ensures visibility of the issue
- Matches current template behavior (new WPs start as planned)

**Alternatives Rejected**:

- Error and refuse: Too strict for minor data quality issues
- Default to "doing": Could cause incorrect status assumptions

## Codebase Analysis

### Current Architecture

Lane management is implemented across these key locations:

| Module | Location | Role |
|--------|----------|------|
| Tasks CLI | `scripts/tasks/tasks_cli.py` | User-facing lane commands |
| Task Helpers | `scripts/tasks/task_helpers.py` | WP location, frontmatter parsing |
| Tasks Support | `src/specify_cli/tasks_support.py` | Duplicate helper functions |
| Dashboard Scanner | `src/specify_cli/dashboard/scanner.py` | Lane visualization |
| Metadata Validation | `src/specify_cli/task_metadata_validation.py` | Lane mismatch detection |
| Acceptance | `src/specify_cli/acceptance.py` | Lane-based acceptance checks |

### Directory-Based Lane Detection Points

1. **`locate_work_package()`** in `task_helpers.py:289-328`
   - Iterates `tasks_root.iterdir()` expecting lane subdirectories
   - Will change to: Scan flat `tasks/`, return lane from frontmatter

2. **`stage_move()`** in `tasks_cli.py:51-87`
   - Builds `target_dir = tasks / target_lane` path
   - Performs `shutil.move()` between directories
   - Will change to: Update frontmatter only, no file movement

3. **`scan_feature_kanban()`** in `scanner.py:293-370`
   - Loops through `for lane in lanes.keys()` with `lane_dir = tasks_dir / lane`
   - Will change to: Scan flat `tasks/`, group results by frontmatter `lane:`

4. **`detect_lane_mismatch()`** in `task_metadata_validation.py:34-76`
   - Extracts expected lane from file path
   - Will change to: Remove entirely (no directory to mismatch)

5. **`scan_all_features()`** in `scanner.py:259-267`
   - Counts items per lane directory
   - Will change to: Count by frontmatter field

### LANES Constant Locations

The `LANES` tuple is defined in multiple places (sync required):

- `scripts/tasks/task_helpers.py:14`
- `src/specify_cli/tasks_support.py:14`

**Recommendation**: Consider consolidating to single source, imported by both modules.

### WP Frontmatter Structure

Current WP files already include the `lane:` field:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
lane: "done"              # Single source of truth (new design)
phase: "Phase 1"
assignee: ""
activity_log: |
  - 2025-01-16T12:45:07Z – system – lane=planned – Created
---
```

**Key Finding**: No schema changes needed - the `lane:` field already exists and is populated. The change is purely about which mechanism is authoritative.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration data loss | Low | High | Idempotent design, confirmation prompt, backup recommendation |
| Test suite breakage | High | Medium | Systematic test updates planned, tracked in tasks |
| Concurrent edit conflicts | Low | Low | No files move, standard git conflict resolution |
| Dashboard rendering issues | Medium | Medium | Test with real data before release |

## Open Questions

All questions resolved during planning interrogation:

- Command naming: Confirmed `update`
- Backwards compatibility: Confirmed none (clean break)
- Migration scope: Confirmed all-at-once

## Evidence Sources

| ID | Source | Type | Relevance |
|----|--------|------|-----------|
| E-001 | `scripts/tasks/tasks_cli.py` | Codebase | Primary move command implementation |
| E-002 | `scripts/tasks/task_helpers.py` | Codebase | WP location logic |
| E-003 | `src/specify_cli/dashboard/scanner.py` | Codebase | Dashboard lane rendering |
| E-004 | `src/specify_cli/task_metadata_validation.py` | Codebase | Lane mismatch detection |
| E-005 | `tests/test_tasks_cli_commands.py` | Codebase | Existing test patterns |
| E-006 | User planning input | Stakeholder | Clean break preference confirmed |
