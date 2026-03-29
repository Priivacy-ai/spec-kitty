---
work_package_id: WP12
title: Remove Stale specify_cli/missions Content and Clean Up References
lane: "done"
dependencies:
- WP11
base_branch: feature/agent-profile-implementation
base_commit: 98bb83b0e228b7771657285fffe687fe017a28db
created_at: '2026-03-10T07:17:13.899371+00:00'
subtasks:
- T057
- T058
- T059
- T060
phase: Phase 4 - Mission Consolidation
assignee: ''
agent: ''
shell_pid: '612100'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-10T06:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated manually
requirement_refs: []
---

# Work Package Prompt: WP12 - Remove Stale specify_cli/missions Content and Clean Up References

## ⚠️ IMPORTANT: Review Feedback Status

- If review feedback exists, address it before treating this WP as complete.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

- `src/specify_cli/missions/` no longer contains command-templates or templates subdirectories for any mission (software-dev, documentation, research, plan).
- `src/specify_cli/missions/` retains only Python modules (`__init__.py`, `glossary_hook.py`, `primitives.py`) and `mission.yaml` files if needed for backward compatibility.
- The `specify_cli/missions` fallback in `get_package_asset_root()` is removed.
- `pyproject.toml` no longer packages markdown/yaml template content from `specify_cli/missions/`.
- All migration code that references `specify_cli/missions/` as a template source is updated to use `doctrine/missions/`.
- No stale path references to `specify_cli/missions/*/command-templates/` remain in code comments, docstrings, or markdown templates.
- All existing tests continue to pass.

## Context & Constraints

- WP11 redirects runtime resolution to `doctrine/missions/`. This WP removes the now-unused stale copies.
- `src/specify_cli/missions/` currently contains both Python code (kept) and doctrine content (removed).
- Three migration files reference `specify_cli/missions/` as a template source — these must be updated.
- Template markdown files themselves reference `specify_cli/missions/` in documentation text — these references should point to `doctrine/missions/`.

## Subtasks & Detailed Guidance

### Subtask T057 - Remove command-templates and templates from `specify_cli/missions/`

- **Purpose**: Eliminate the stale duplicate content.
- **Steps**:
  1. Delete `src/specify_cli/missions/software-dev/command-templates/` directory.
  2. Delete `src/specify_cli/missions/software-dev/templates/` directory.
  3. Delete `src/specify_cli/missions/documentation/command-templates/` and `templates/` directories.
  4. Delete `src/specify_cli/missions/research/command-templates/` and `templates/` directories.
  5. Delete `src/specify_cli/missions/plan/command-templates/` and `templates/` directories.
  6. Keep `__init__.py`, `glossary_hook.py`, `primitives.py`, and any `mission.yaml` files.
  7. If a mission subdirectory becomes empty after removal (no Python files, no mission.yaml), remove the entire subdirectory.
- **Files**: `src/specify_cli/missions/*/command-templates/`, `src/specify_cli/missions/*/templates/`
- **Notes**: Use `git rm -r` to ensure proper tracking. Verify no Python imports reference files being deleted.

### Subtask T058 - Update migration code references

- **Purpose**: Ensure migrations that copy templates source from `doctrine/missions/` not `specify_cli/missions/`.
- **Steps**:
  1. Grep for `specify_cli.*missions.*command-templates` and `specify_cli.*missions.*templates` across `src/specify_cli/upgrade/migrations/`.
  2. Update each reference to use `doctrine/missions/` as the source.
  3. Verify backward compatibility — older migrations may need to handle both paths for projects that haven't upgraded yet.
- **Files**: The three files with `specify_cli/missions/` references are:
  - `src/specify_cli/upgrade/migrations/m_0_11_0_workspace_per_wp.py` (line 90: command-templates source path)
  - `src/specify_cli/upgrade/migrations/m_0_14_0_centralized_feature_detection.py` (line 226: plan.md template path)
  - `src/specify_cli/upgrade/migrations/m_0_9_2_research_mission_templates.py` (line 203: research mission directory)

### Subtask T059 - Remove `specify_cli/missions` fallback and update packaging

- **Purpose**: Clean up the backward-compatibility fallback added in WP11 and stop packaging stale content.
- **Steps**:
  1. In `src/specify_cli/runtime/home.py`, remove the `specify_cli/missions` fallback from `get_package_asset_root()`.
  2. In `pyproject.toml`, remove `"src/specify_cli/missions/"` from the packages list if it was only included for template content. Keep it if needed for Python module packaging.
  3. Verify the package still builds correctly.
- **Files**: `src/specify_cli/runtime/home.py`, `pyproject.toml`

### Subtask T060 - Fix stale path references and run full test suite

- **Purpose**: Clean up documentation references and verify nothing is broken.
- **Steps**:
  1. Grep the entire codebase for `specify_cli/missions/.*command-templates` and `specify_cli/missions/.*templates/` in comments, docstrings, and markdown content.
  2. Update references to point to `doctrine/missions/` instead.
  3. Run full test suite.
  4. Run ruff and mypy checks.
- **Files**: Various — grep-driven discovery.
- **Notes**: Pay attention to markdown files in `src/doctrine/missions/` that may reference the old `specify_cli` path in their prose content.

## Test Strategy

- `pytest -q tests/` (full suite — critical since template sources are changing)
- `ruff check src/`
- `mypy src/specify_cli/runtime/home.py --ignore-missing-imports`
- Verify `spec-kitty init` still works by running it in a temp directory (if feasible in CI).

## Risks & Mitigations

- Removing template content from `specify_cli/missions/` could break installed distributions if WP11's packaging update is incomplete. Verify with a test build before merging.
- Migration files that still reference the old path will fail for new projects. Keep both-path fallback logic in migration code if needed.
- Some tests may fixture against `specify_cli/missions/` paths. Update them to use `doctrine/missions/`.

## Review Guidance

- Confirm `src/specify_cli/missions/` has no remaining `.md` or `.yaml` template files (only Python modules).
- Confirm all migration code sources templates from `doctrine/missions/`.
- Confirm `pyproject.toml` packages `doctrine/missions/` and no longer needs `specify_cli/missions/` for template content.
- Confirm no stale `specify_cli/missions/*/command-templates/` references remain in the codebase.

## Activity Log

- 2026-03-10T06:00:00Z - system - lane=planned - Prompt created.
- 2026-03-10T10:45:12Z – unknown – shell_pid=612100 – lane=done – Moved to done
