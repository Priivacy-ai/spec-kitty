---
work_package_id: WP06
title: Migration and Release
lane: done
history:
- timestamp: '2025-12-15T11:55:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: ''
assignee: ''
phase: Phase 5 - Release
review_status: ''
reviewed_by: ''
shell_pid: ''
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
---

# Work Package Prompt: WP06 – Migration and Release

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add migration to `spec-kitty upgrade` that removes `.kittify/active-mission`
- Document all breaking changes in CHANGELOG
- Bump version to 0.8.0
- Update README with new per-feature mission workflow

**Success Metrics** (from spec):
- SC-006: `spec-kitty upgrade` removes `.kittify/active-mission` files
- Version shows 0.8.0
- CHANGELOG documents all breaking changes
- README explains new workflow

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/006-per-feature-mission/spec.md` (Breaking Changes, FR-007)
- Plan: `kitty-specs/006-per-feature-mission/plan.md` (Phase 5, Phase 6)
- Quickstart: `kitty-specs/006-per-feature-mission/quickstart.md` (User workflow)

**Files to Modify**:
- `src/specify_cli/cli/commands/upgrade.py` - Upgrade command
- `CHANGELOG.md` - Release notes
- `pyproject.toml` - Version number
- `README.md` - User documentation

**Constraints**:
- Migration must be non-destructive (just removes obsolete files)
- CHANGELOG should follow existing format
- README should be updated, not replaced

## Subtasks & Detailed Guidance

### Subtask T031 – Add migration step to `spec-kitty upgrade`

- **Purpose**: Clean up obsolete `.kittify/active-mission` from existing projects
- **Files**: `src/specify_cli/cli/commands/upgrade.py`
- **Steps**:
  1. Find the upgrade command implementation
  2. Add migration step for v0.8.0:
     ```python
     def migrate_to_0_8_0(kittify_dir: Path, console: Console) -> None:
         """Remove deprecated active-mission file/symlink."""
         active_mission = kittify_dir / "active-mission"

         if active_mission.exists() or active_mission.is_symlink():
             try:
                 active_mission.unlink()
                 console.print("[yellow]Removed deprecated .kittify/active-mission[/yellow]")
                 console.print("  Missions are now selected per-feature during /spec-kitty.specify")
             except OSError as e:
                 console.print(f"[red]Warning: Could not remove active-mission: {e}[/red]")
         else:
             console.print("[dim]No active-mission file found (already migrated or new project)[/dim]")
     ```
  3. Register migration in upgrade command's migration list
  4. Ensure migration only runs if version < 0.8.0
- **Parallel?**: No (core migration logic)

### Subtask T032 – Document breaking changes in CHANGELOG

- **Purpose**: Inform users of breaking changes before upgrade
- **Files**: `CHANGELOG.md`
- **Steps**:
  1. Add new section at top of CHANGELOG:
     ```markdown
     ## [0.8.0] - 2025-12-XX

     ### Breaking Changes

     - **Mission system refactored to per-feature model**
       - Missions are now selected during `/spec-kitty.specify` instead of `spec-kitty init`
       - Each feature stores its mission in `meta.json`
       - `.kittify/active-mission` is no longer used
       - Run `spec-kitty upgrade` to clean up existing projects

     - **Removed commands**
       - `spec-kitty mission switch` - Missions are now per-feature, not per-project

     - **Removed flags**
       - `--mission` flag from `spec-kitty init` - Use `/spec-kitty.specify` instead

     ### Added

     - Mission inference during `/spec-kitty.specify` - LLM suggests appropriate mission based on feature description
     - Per-feature mission storage in `meta.json`
     - Updated `spec-kitty mission list` with source indicators

     ### Changed

     - All downstream commands now read mission from feature's `meta.json`
     - Legacy features without mission field default to `software-dev`

     ### Migration

     Run `spec-kitty upgrade` to:
     - Remove obsolete `.kittify/active-mission` file
     - No changes required to existing feature specs
     ```
  2. Update the date when releasing
- **Parallel?**: Yes (documentation task)

### Subtask T033 – Version bump to 0.8.0

- **Purpose**: Update version number for release
- **Files**: `pyproject.toml`
- **Steps**:
  1. Find version in pyproject.toml:
     ```bash
     grep "version" pyproject.toml
     ```
  2. Update from current version to 0.8.0:
     ```toml
     [project]
     name = "specify-cli"
     version = "0.8.0"
     ```
  3. Also update any `__version__` in Python code if present:
     ```bash
     grep -r "__version__" src/
     ```
- **Parallel?**: Yes (simple change)

### Subtask T034 – Update README with new workflow

- **Purpose**: Document new per-feature mission workflow for users
- **Files**: `README.md`
- **Steps**:
  1. Find existing mission documentation section
  2. Update or add section explaining new workflow:
     ```markdown
     ## Mission Selection

     Spec-kitty supports different mission types for different kinds of work:

     - **software-dev**: For building features, APIs, CLI tools, applications
     - **research**: For investigations, literature reviews, analysis

     ### How Mission Selection Works

     Missions are selected per-feature during the specification phase:

     1. Run `/spec-kitty.specify` and describe your feature
     2. The system analyzes your description and suggests an appropriate mission
     3. Confirm the suggestion or choose a different mission
     4. The selected mission is stored in your feature's `meta.json`

     All downstream commands (`/spec-kitty.plan`, `/spec-kitty.tasks`, etc.) automatically use the feature's mission.

     ### Explicit Mission Override

     Skip inference by passing `--mission`:

     ```bash
     /spec-kitty.specify --mission research "Investigate caching strategies"
     ```

     ### Listing Available Missions

     ```bash
     spec-kitty mission list
     ```
     ```
  3. Remove any documentation about `spec-kitty mission switch` or `--mission` flag on init
  4. Update Quick Start section if it mentions mission selection during init
- **Parallel?**: Yes (documentation task)

### Subtask T035 – Update other documentation files

- **Purpose**: Ensure all docs reflect new mission model
- **Files**: Any other docs referencing missions
- **Steps**:
  1. Search for other markdown files mentioning missions:
     ```bash
     grep -r "mission" --include="*.md" docs/ 2>/dev/null || true
     grep -r "active-mission" --include="*.md" . 2>/dev/null || true
     ```
  2. Update any found references to reflect per-feature model
  3. Check for outdated screenshots or examples
  4. Update any developer documentation or contributing guides
- **Parallel?**: Yes (documentation task)

### Subtask T036 – Final validation

- **Purpose**: End-to-end test of complete workflow
- **Files**: N/A (testing task)
- **Steps**:
  1. Create a test project:
     ```bash
     mkdir test-project && cd test-project
     spec-kitty init
     ```
  2. Test specify with software description:
     ```bash
     /spec-kitty.specify "Build a REST API for user management"
     # Verify: software-dev mission suggested and stored
     ```
  3. Test specify with research description:
     ```bash
     /spec-kitty.specify "Research best practices for API security"
     # Verify: research mission suggested and stored
     ```
  4. Test downstream commands:
     ```bash
     /spec-kitty.plan
     /spec-kitty.tasks
     ```
  5. Test upgrade on project with active-mission:
     ```bash
     # Create fake active-mission
     ln -s missions/software-dev .kittify/active-mission
     spec-kitty upgrade
     # Verify: active-mission removed
     ```
  6. Test mission list:
     ```bash
     spec-kitty mission list
     # Verify: shows Source column
     ```
  7. Test deprecated command:
     ```bash
     spec-kitty mission switch research
     # Verify: helpful error message
     ```
  8. Document any issues found
- **Parallel?**: No (final validation step)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Migration fails on edge cases | Test on various project configurations |
| Users miss breaking changes | Prominent CHANGELOG and upgrade message |
| Documentation inconsistent | Review all docs before release |
| Version conflicts | Ensure pyproject.toml is single source of truth |

## Definition of Done Checklist

- [ ] `spec-kitty upgrade` removes `.kittify/active-mission`
- [ ] CHANGELOG documents all breaking changes
- [ ] Version bumped to 0.8.0 in pyproject.toml
- [ ] README updated with new workflow
- [ ] All other docs updated
- [ ] Final validation passes all scenarios
- [ ] Ready for release

## Review Guidance

- Run `spec-kitty upgrade` on project with active-mission → should remove it
- Check `spec-kitty --version` shows 0.8.0
- Review CHANGELOG for completeness and clarity
- Verify README workflow matches actual behavior
- Test complete workflow end-to-end on fresh project

## Activity Log

- 2025-12-15T11:55:00Z – system – lane=planned – Prompt created.
