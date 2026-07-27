---
work_package_id: WP01
title: 'Mission Metadata: change_mode Field'
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-bulk-edit-occurrence-classification-guardrail-01KP423X
base_commit: ab8bd1f6a518f389e31f8bc695faed365d0d1924
created_at: '2026-04-13T18:56:20.510111+00:00'
subtasks:
- T001
- T002
shell_pid: "47414"
agent: "claude:opus:reviewer:reviewer"
history:
- date: '2026-04-13'
  author: claude
  action: created
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/mission_metadata.py
- tests/specify_cli/test_mission_metadata_change_mode.py
tags: []
---

# WP01 — Mission Metadata: change_mode Field

## Objective

Add the `change_mode` optional field to mission metadata (`meta.json`) so missions can explicitly declare themselves as occurrence-sensitive bulk edits. This is the foundation field that all other WPs check.

## Context

- **Spec**: FR-001 — Mission metadata supports a `change_mode` field with at least the value `bulk_edit`
- **Plan**: Integration Point 4 — Mission Metadata Extension
- **Data model**: `change_mode` is `str | None`, only defined value is `"bulk_edit"`, absent means "not a bulk edit"
- The existing `MissionMetaOptional` TypedDict in `src/specify_cli/mission_metadata.py` (line 49) already holds all optional fields like `vcs`, `accepted_at`, `documentation_state`, etc.
- The existing mutation helper pattern uses `load_meta()` → modify → `write_meta()` with atomic writes

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

---

### Subtask T001: Add change_mode to MissionMetaOptional + Validation

**Purpose**: Extend the metadata TypedDict and add validation so `change_mode` is recognized and constrained.

**Steps**:

1. Open `src/specify_cli/mission_metadata.py`

2. Add `change_mode` to `MissionMetaOptional` (after `mission_branch: str`):
   ```python
   change_mode: str  # "bulk_edit" — declares occurrence-sensitive mission
   ```

3. Add a `VALID_CHANGE_MODES` constant near the other constants (~line 76):
   ```python
   VALID_CHANGE_MODES: frozenset[str] = frozenset({"bulk_edit"})
   ```

4. Update the `validate_meta()` function to check `change_mode` when present:
   - If `"change_mode"` key exists in meta dict
   - And its value is not in `VALID_CHANGE_MODES`
   - Append an error: `f"change_mode must be one of {sorted(VALID_CHANGE_MODES)}, got {meta['change_mode']!r}"`
   - `None` / absent is valid (means "not a bulk edit")

5. Add a `set_change_mode()` mutation helper following the established pattern:
   ```python
   def set_change_mode(feature_dir: Path, mode: str) -> dict[str, Any]:
       """Set the ``change_mode`` field in meta.json."""
       if mode not in VALID_CHANGE_MODES:
           raise ValueError(
               f"change_mode must be one of {sorted(VALID_CHANGE_MODES)}, got {mode!r}"
           )
       meta = load_meta(feature_dir)
       if meta is None:
           raise FileNotFoundError(f"No meta.json in {feature_dir}")
       meta["change_mode"] = mode
       write_meta(feature_dir, meta)
       return meta
   ```

6. Add a convenience reader:
   ```python
   def get_change_mode(feature_dir: Path) -> str | None:
       """Return the change_mode from meta.json, or None if absent."""
       meta = load_meta(feature_dir)
       if meta is None:
           return None
       return meta.get("change_mode")
   ```

**Files**: `src/specify_cli/mission_metadata.py`

**Validation**:
- [ ] `change_mode` accepted in TypedDict without mypy errors
- [ ] `validate_meta()` passes for meta without `change_mode` (backward compat)
- [ ] `validate_meta()` passes for `change_mode: "bulk_edit"`
- [ ] `validate_meta()` fails for `change_mode: "invalid_value"`
- [ ] `set_change_mode()` writes atomically and round-trips
- [ ] `get_change_mode()` returns None when field is absent

---

### Subtask T002: Unit Tests for change_mode Metadata Field

**Purpose**: Verify backward compatibility, validation, and mutation helper behavior.

**Steps**:

1. Create `tests/specify_cli/test_mission_metadata_change_mode.py`

2. Test cases:
   - `test_validate_meta_without_change_mode_passes`: Existing meta without field validates cleanly
   - `test_validate_meta_with_bulk_edit_passes`: Meta with `change_mode: "bulk_edit"` validates
   - `test_validate_meta_with_invalid_change_mode_fails`: Meta with `change_mode: "invalid"` produces error
   - `test_set_change_mode_bulk_edit`: Sets field and round-trips via `load_meta()`
   - `test_set_change_mode_invalid_raises`: Raises `ValueError` for unknown modes
   - `test_set_change_mode_missing_meta_raises`: Raises `FileNotFoundError` when no meta.json
   - `test_get_change_mode_absent_returns_none`: Returns None when field not present
   - `test_get_change_mode_present_returns_value`: Returns `"bulk_edit"` when set
   - `test_change_mode_preserved_through_write_meta`: Other fields unaffected by set_change_mode

3. Use `tmp_path` fixture for isolated filesystem tests. Create minimal valid meta.json in each test using `write_meta()`.

**Files**: `tests/specify_cli/test_mission_metadata_change_mode.py`

**Validation**:
- [ ] All tests pass with `pytest tests/specify_cli/test_mission_metadata_change_mode.py -v`
- [ ] `mypy --strict src/specify_cli/mission_metadata.py` passes
- [ ] No regressions in existing metadata tests

## Definition of Done

- [ ] `change_mode` field recognized in `MissionMetaOptional`
- [ ] Validation enforces allowed values
- [ ] Mutation helper and reader work atomically
- [ ] All unit tests pass
- [ ] mypy --strict passes
- [ ] No regressions in existing tests

## Risks

- **Low**: Adding a field to TypedDict could surface mypy issues in downstream code that destructures meta dicts. Mitigate by keeping it optional (total=False).

## Reviewer Guidance

- Verify backward compatibility: existing meta.json without `change_mode` must continue to work
- Check that `validate_meta()` change is additive (no existing behavior changed)
- Confirm atomic write pattern matches other mutation helpers

## Activity Log

- 2026-04-13T18:56:20Z – claude:opus:implementer:implementer – shell_pid=40561 – Assigned agent via action command
- 2026-04-13T19:00:14Z – claude:opus:implementer:implementer – shell_pid=40561 – Ready for review
- 2026-04-13T19:00:28Z – claude:opus:reviewer:reviewer – shell_pid=47414 – Started review via action command
- 2026-04-13T19:01:01Z – claude:opus:reviewer:reviewer – shell_pid=47414 – Review passed: clean TypedDict extension, validation, mutation helper, reader. 9 tests. Follows existing patterns.
- 2026-04-13T19:32:06Z – claude:opus:reviewer:reviewer – shell_pid=47414 – Done override: Feature merged to main
