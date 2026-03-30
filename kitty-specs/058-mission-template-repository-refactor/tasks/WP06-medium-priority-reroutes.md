---
work_package_id: WP06
title: MEDIUM Priority Consumer Reroutes
lane: planned
dependencies:
- WP01
requirement_refs:
- FR-017
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
phase: Phase 2 - Consumer Rerouting
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-27T04:37:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – MEDIUM Priority Consumer Reroutes

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. `runtime/resolver.py` tier-5 lookups use `MissionTemplateRepository._*_path()` instead of `get_package_asset_root()` + direct construction
2. `runtime/bootstrap.py` uses `MissionTemplateRepository.default()._missions_root` for source path
3. `runtime/migrate.py` uses `MissionTemplateRepository.default()._missions_root` for package root
4. `template/manager.py` uses `MissionTemplateRepository.default()._missions_root` for missions source
5. The 5-tier resolver's internal logic is unchanged (C-003) -- only tier-5 source changes
6. No regressions in any tests

**Success gate**: `pytest tests/specify_cli/runtime/ -v` passes. Tier-5 resolution still works correctly.

## Context & Constraints

- **Research**: `kitty-specs/058-mission-template-repository-refactor/research/consumer-analysis.md`
- **Constraint C-003**: The 5-tier resolver's internal logic must not change. Only the tier-5 source path resolution changes.
- **Note**: These files use private `_*_path()` and `_missions_root` -- this is by design. They are internal callers that need filesystem access for bulk operations (copying, migration, tier-5 path checking).
- **Prerequisite**: WP04 tests provide confidence. WP05 is NOT a hard dependency -- WP05 and WP06 can run in parallel.

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP06 --base WP04`

## Subtasks & Detailed Guidance

### Subtask T023 – Reroute runtime/resolver.py tier-5 lookups

- **Purpose**: Replace `get_package_asset_root()` in the resolver's tier-5 (PACKAGE_DEFAULT) with repository private methods. This centralizes the path convention inside the repository.
- **Steps**:
  1. **Before**: Run resolver tests:
     ```bash
     pytest tests/ -v -k "resolver" --co -q
     pytest tests/specify_cli/runtime/ -v
     ```
  2. **Read** `src/specify_cli/runtime/resolver.py`, focusing on:
     - Lines ~174-175: `pkg_missions = get_package_asset_root()` / `pkg_path = pkg_missions / mission / subdir / name` (template resolution)
     - Lines ~302-303: `pkg_missions = get_package_asset_root()` / `pkg_path = pkg_missions / name / filename` (config resolution)
  3. **Change 1** (template tier-5, lines ~174-175):
     Replace direct path construction with repository private method:
     ```python
     from doctrine.missions import MissionTemplateRepository
     _repo = MissionTemplateRepository.default()

     # In the tier-5 block:
     if subdir == "command-templates":
         pkg_path = _repo._command_template_path(mission, name.removesuffix(".md"))
     elif subdir == "templates":
         pkg_path = _repo._content_template_path(mission, name)
     else:
         # Fallback for unknown subdirs
         pkg_path = _repo._missions_root / mission / subdir / name
     ```
     **Note**: The resolver passes `name` WITH `.md` extension for command templates but `_command_template_path()` expects name WITHOUT `.md`. Use `.removesuffix(".md")`.
  4. **Change 2** (config tier-5, lines ~302-303):
     ```python
     # For mission config resolution:
     pkg_path = _repo._mission_config_path(name)
     ```
     **Note**: Check what `name` and `filename` represent in this context. The resolver may pass the mission name + filename separately.
  5. **Important**: The `_repo` instance should be created inside the function body (not at module level) to avoid import-time side effects. Or use a lazy-init pattern.
  6. **Tiers 1-4 are UNTOUCHED**. They construct project-local and user-global paths which are intentionally outside the repository.
  7. **After**: Re-run resolver tests
- **Files**: `src/specify_cli/runtime/resolver.py`
- **Parallel?**: Yes, independent of T024-T026
- **Notes**: The resolver's `_*_path()` methods return `None` if the file doesn't exist, matching the `is_file()` check the resolver already does. Verify the control flow handles `None` correctly (an `if pkg_path:` check).

### Subtask T024 – Reroute runtime/bootstrap.py

- **Purpose**: Replace `get_package_asset_root()` with `MissionTemplateRepository.default()._missions_root` for the missions source path in `populate_from_package()`.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "bootstrap" --co -q
     ```
  2. **Read** `src/specify_cli/runtime/bootstrap.py`, focusing on `populate_from_package()` (lines ~67-93)
  3. **Change** (line ~74): Replace `asset_root = get_package_asset_root()` with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     asset_root = MissionTemplateRepository.default()._missions_root
     ```
  4. **Note on parent traversal**: Lines ~84 and ~89 use `asset_root.parent` to access sibling directories (`scripts/`, `AGENTS.md`). With the repository, `_missions_root` points to `doctrine/missions/`, so `_missions_root.parent` is the `doctrine/` package root. This is the same result as `get_package_asset_root().parent`. Document this coupling in a comment.
  5. **After**: Re-run tests
  6. **Cleanup**: If `get_package_asset_root` is no longer imported elsewhere in this file, remove the import.
- **Files**: `src/specify_cli/runtime/bootstrap.py`
- **Parallel?**: Yes
- **Notes**: This is a bulk copy operation (`shutil.copytree`). The path just needs to point to the right directory. No behavior change.

### Subtask T025 – Reroute runtime/migrate.py

- **Purpose**: Replace `get_package_asset_root()` with repository for package root resolution in the migration module.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "migrate" --co -q
     ```
  2. **Read** `src/specify_cli/runtime/migrate.py`, focusing on:
     - Line ~177: `package_root = get_package_asset_root()`
     - Lines ~50-66: `_find_package_counterpart()` which uses `package_root / mission / str(rel)`
  3. **Change** (line ~177): Replace with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     package_root = MissionTemplateRepository.default()._missions_root
     ```
  4. **Note**: `_find_package_counterpart()` at line ~57 constructs `pkg_path = package_root / mission / str(rel)` for arbitrary relative paths within a mission. This generic construction may not have a specific repository method. The `_missions_root` gives the right base directory, and the rest is the same path arithmetic.
  5. **After**: Re-run tests
  6. **Cleanup**: Remove unused `get_package_asset_root` import if applicable.
- **Files**: `src/specify_cli/runtime/migrate.py`
- **Parallel?**: Yes
- **Notes**: The migration module compares files. It needs the root path, not individual asset content. `_missions_root` is the right abstraction level.

### Subtask T026 – Reroute template/manager.py

- **Purpose**: Replace direct `importlib.resources.files("doctrine").joinpath("missions")` with repository for missions source path.
- **Steps**:
  1. **Before**: Run tests:
     ```bash
     pytest tests/ -v -k "manager or template" --co -q
     ```
  2. **Read** `src/specify_cli/template/manager.py`, focusing on:
     - Lines ~165-170: `missions_src = repo_root / "src" / "doctrine" / "missions"` (dev mode)
     - Lines ~242-243: `files("doctrine").joinpath("missions")` (package mode)
     - Lines ~247-249: Legacy fallback paths
  3. **Change** (package mode, lines ~242-243): Replace with:
     ```python
     from doctrine.missions import MissionTemplateRepository
     missions_root = MissionTemplateRepository.default()._missions_root
     ```
  4. **Dev mode** (lines ~165-170): This constructs `repo_root / "src" / "doctrine" / "missions"` which is an editable-install path. `MissionTemplateRepository.default_missions_root()` already handles this case via `importlib.resources.files("doctrine") / "missions"`. Replace with the repository call.
  5. **Legacy fallbacks** (lines ~247-249): These check for `data_root.joinpath("missions")`, `data_root.joinpath(".kittify", "missions")`, etc. These may still be needed for edge cases. Evaluate whether `MissionTemplateRepository.default()._missions_root` covers all cases.
  6. **After**: Re-run tests
  7. **Cleanup**: Remove unused `importlib.resources.files` import if no longer needed for missions (it may still be needed for `templates/` which is non-mission-scoped).
- **Files**: `src/specify_cli/template/manager.py`
- **Parallel?**: Yes
- **Notes**: `manager.py` has complex path resolution for both dev and installed modes. The repository already handles both via `importlib.resources`. Be careful with the dev-mode code paths -- they may probe for `src/doctrine/` directory existence, which is a separate concern from asset access.

## Test Strategy

For each file, find and run its tests before and after changes:

```bash
# Find tests
grep -rl "resolver\|bootstrap\|migrate\|manager" tests/ --include="*.py" | head -20

# Run resolver tests
source .venv/bin/activate && .venv/bin/python -m pytest tests/specify_cli/runtime/ -v

# Run full suite at end
source .venv/bin/activate && .venv/bin/python -m pytest tests/ -v
```

## Risks & Mitigations

1. **Resolver behavior change**: Only tier-5 path source changes. The `_*_path()` methods return `None` for missing files, which the resolver already handles. Verify the resolver's `None` handling.
2. **Bootstrap parent traversal**: `_missions_root.parent` gives `doctrine/` root. Same as `get_package_asset_root().parent`. Add a comment documenting this.
3. **Manager dev-mode probes**: The `get_local_repo_root()` function probes for `src/doctrine/templates/command-templates/` to detect dev mode. This is NOT a mission asset lookup -- it's a mode-detection heuristic. Leave it as-is.
4. **Import timing**: Ensure `from doctrine.missions import MissionTemplateRepository` is inside function bodies in the resolver (not at module level) to match the existing lazy-import pattern.

## Review Guidance

- Verify only tier-5 changed in resolver (tiers 1-4 untouched)
- Verify `_missions_root` usage is appropriate (bulk ops, not content reading)
- Verify parent traversal patterns are documented in comments
- Verify unused imports are cleaned up
- Verify no new module-level imports from `doctrine` in `specify_cli` modules that didn't already have them
- Run `pytest tests/specify_cli/runtime/ -v`

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
