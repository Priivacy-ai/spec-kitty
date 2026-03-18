---
work_package_id: WP01
title: Create feature_metadata.py Module
lane: "for_review"
dependencies: []
base_branch: 2.x
base_commit: f48b32383ceac06813581229982d5d14984f5c10
created_at: '2026-03-18T20:31:36.756124+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 0 - Foundation
assignee: ''
agent: coordinator
shell_pid: '47655'
review_status: has_feedback
reviewed_by: Robert Douglass
review_feedback: feedback://051-canonical-state-authority-single-metadata-writer/WP01/20260318T204319Z-19617ea1.md
history:
- timestamp: '2026-03-18T20:21:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-007
- FR-008
- FR-010
- NFR-001
- NFR-002
- NFR-003
---

# Work Package Prompt: WP01 – Create feature_metadata.py Module

## Objectives & Success Criteria

- Create `src/specify_cli/feature_metadata.py` as the single metadata writer API for all `meta.json` operations.
- Extend the existing `write_feature_meta()` formatting convention from `upgrade/feature_meta.py`, adding `sort_keys=True` and atomic writes.
- Provide TypedDict definitions for static type checking, runtime validation at write boundaries, and explicit mutation helpers for common operations.
- All public functions have unit tests. `mypy --strict` passes.

**Success gate**: Import `feature_metadata` and exercise every public function against a temp directory. Formatting is consistent (`indent=2, ensure_ascii=False, sort_keys=True, trailing newline`). Atomic write handles interruption safely.

## Context & Constraints

- **Spec**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/spec.md`
- **Plan**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/plan.md`
- **Data model**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/data-model.md`
- **Research**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/research.md`
- **Existing helper**: `src/specify_cli/upgrade/feature_meta.py` — contains `load_feature_meta()` and `write_feature_meta()`. This is the starting point.
- **TypedDict precedent**: `src/specify_cli/doc_state.py` lines 44-63 — uses `TypedDict` for `DocumentationState` and `GeneratorConfig`.
- **No new dependencies**: Use only stdlib (`json`, `os`, `tempfile`, `typing`, `pathlib`).
- **Python 3.11+**: Can use modern type syntax.

**Implementation command**:
```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create feature_metadata.py with TypedDict definitions

**Purpose**: Define the schema for meta.json's stable top-level fields so that mypy can catch type errors at development time.

**Steps**:
1. Create `src/specify_cli/feature_metadata.py`.
2. Define TypedDicts following the pattern in `doc_state.py`:

```python
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, TypedDict

class FeatureMetaRequired(TypedDict):
    """Required fields — always present in a valid meta.json."""
    feature_number: str
    slug: str
    feature_slug: str
    friendly_name: str
    mission: str
    target_branch: str
    created_at: str

class FeatureMetaOptional(TypedDict, total=False):
    """Optional fields — present only after specific operations."""
    vcs: str
    vcs_locked_at: str
    accepted_at: str
    accepted_by: str
    acceptance_mode: str
    accepted_from_commit: str
    accept_commit: str
    acceptance_history: list[dict[str, Any]]
    merged_at: str
    merged_by: str
    merged_into: str
    merged_strategy: str
    merged_push: bool
    merged_commit: str
    merge_history: list[dict[str, Any]]
    documentation_state: dict[str, Any]
    source_description: str

# Constants
REQUIRED_FIELDS: frozenset[str] = frozenset(FeatureMetaRequired.__annotations__)
HISTORY_CAP: int = 20
```

3. Note: The TypedDicts are for static type checking documentation. The actual in-memory payload remains `dict[str, Any]` — callers don't need to change their dict construction.

**Files**: `src/specify_cli/feature_metadata.py` (new file)

### Subtask T002 – Implement load_meta()

**Purpose**: Centralized read function for meta.json, relocated from `upgrade/feature_meta.py`.

**Steps**:
1. Implement `load_meta(feature_dir: Path) -> dict[str, Any] | None`:
   ```python
   def load_meta(feature_dir: Path) -> dict[str, Any] | None:
       """Load meta.json from feature directory. Returns None if missing."""
       meta_path = feature_dir / "meta.json"
       if not meta_path.exists():
           return None
       text = meta_path.read_text(encoding="utf-8")
       return json.loads(text)
   ```
2. Handle malformed JSON gracefully — raise a clear `ValueError` with the file path.
3. This replaces `load_feature_meta()` from `upgrade/feature_meta.py` (same logic, new home).

**Files**: `src/specify_cli/feature_metadata.py`

### Subtask T003 – Implement validate_meta()

**Purpose**: Runtime validation at write boundaries — ensures meta.json won't be written with missing required fields.

**Steps**:
1. Implement `validate_meta(meta: dict[str, Any]) -> list[str]`:
   ```python
   def validate_meta(meta: dict[str, Any]) -> list[str]:
       """Validate meta.json content. Returns list of error messages (empty = valid)."""
       errors: list[str] = []
       for field in REQUIRED_FIELDS:
           if field not in meta or not meta[field]:
               errors.append(f"Missing or empty required field: {field}")
       return errors
   ```
2. Only validate required fields. Unknown fields are preserved (forward compatibility, FR-010).
3. Return error messages as strings — callers decide whether to raise or log.

**Files**: `src/specify_cli/feature_metadata.py`

### Subtask T004 – Implement _atomic_write()

**Purpose**: Atomic file write via temp file + `os.replace()` to prevent corruption on interruption.

**Steps**:
1. Implement internal helper:
   ```python
   def _atomic_write(path: Path, content: str) -> None:
       """Write content atomically. File is either old or new, never partial."""
       fd, tmp_path = tempfile.mkstemp(
           dir=path.parent,
           prefix=".meta-",
           suffix=".tmp",
       )
       try:
           os.write(fd, content.encode("utf-8"))
           os.close(fd)
           fd = -1  # Mark as closed
           os.replace(tmp_path, str(path))
       except BaseException:
           if fd >= 0:
               os.close(fd)
           try:
               os.unlink(tmp_path)
           except OSError:
               pass
           raise
   ```
2. `os.replace()` is atomic on POSIX (single rename syscall). On Windows it's near-atomic (replaces target).
3. Temp file created in same directory to ensure same filesystem — prevents cross-mount rename failure.
4. Cleanup: if anything goes wrong, close fd and remove temp file.

**Files**: `src/specify_cli/feature_metadata.py`

### Subtask T005 – Implement write_meta()

**Purpose**: The single write function for meta.json. Validates, serializes with standard format, and writes atomically.

**Steps**:
1. Implement:
   ```python
   def write_meta(feature_dir: Path, meta: dict[str, Any]) -> None:
       """Write meta.json with validation, standard formatting, and atomic write.

       Standard format: sorted keys, 2-space indent, Unicode preserved, trailing newline.
       Raises ValueError if validation fails.
       """
       errors = validate_meta(meta)
       if errors:
           raise ValueError(
               f"Invalid meta.json for {feature_dir.name}: {'; '.join(errors)}"
           )
       content = json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
       meta_path = feature_dir / "meta.json"
       _atomic_write(meta_path, content)
   ```
2. This is the ONLY function that writes meta.json. All mutation helpers call this.
3. Standard format extends existing `write_feature_meta()` by adding `sort_keys=True`.

**Files**: `src/specify_cli/feature_metadata.py`

### Subtask T006 – Implement mutation helpers

**Purpose**: Explicit, named functions for common meta.json operations. Callers use these instead of ad-hoc dict surgery.

**Steps**:
1. Implement each mutation helper following the pattern: load → mutate → validate → write → return.

2. **`record_acceptance()`**:
   ```python
   def record_acceptance(
       feature_dir: Path,
       *,
       accepted_by: str,
       mode: str,
       from_commit: str | None = None,
       accept_commit: str | None = None,
   ) -> dict[str, Any]:
       """Record acceptance metadata. Appends to bounded history."""
       meta = load_meta(feature_dir)
       if meta is None:
           raise FileNotFoundError(f"No meta.json in {feature_dir}")

       now = _now_iso()
       entry = {
           "accepted_at": now,
           "accepted_by": accepted_by,
           "acceptance_mode": mode,
       }
       if from_commit is not None:
           entry["accepted_from_commit"] = from_commit
       if accept_commit is not None:
           entry["accept_commit"] = accept_commit

       # Set top-level fields
       meta["accepted_at"] = now
       meta["accepted_by"] = accepted_by
       meta["acceptance_mode"] = mode
       if from_commit is not None:
           meta["accepted_from_commit"] = from_commit
       if accept_commit is not None:
           meta["accept_commit"] = accept_commit

       # Bounded history
       history = meta.get("acceptance_history", [])
       history.append(entry)
       if len(history) > HISTORY_CAP:
           history = history[-HISTORY_CAP:]
       meta["acceptance_history"] = history

       write_meta(feature_dir, meta)
       return meta
   ```

3. **`record_merge()`**:
   ```python
   def record_merge(
       feature_dir: Path,
       *,
       merged_by: str,
       merged_into: str,
       strategy: str,
       push: bool,
   ) -> dict[str, Any]:
       """Record merge metadata. Appends to bounded history."""
       meta = load_meta(feature_dir)
       if meta is None:
           raise FileNotFoundError(f"No meta.json in {feature_dir}")

       now = _now_iso()
       meta["merged_at"] = now
       meta["merged_by"] = merged_by
       meta["merged_into"] = merged_into
       meta["merged_strategy"] = strategy
       meta["merged_push"] = push

       entry = {
           "merged_at": now,
           "merged_by": merged_by,
           "merged_into": merged_into,
           "merged_strategy": strategy,
           "merged_push": push,
           "merged_commit": None,
       }
       history = meta.get("merge_history", [])
       history.append(entry)
       if len(history) > HISTORY_CAP:
           history = history[-HISTORY_CAP:]
       meta["merge_history"] = history

       write_meta(feature_dir, meta)
       return meta
   ```

4. **`finalize_merge()`**:
   ```python
   def finalize_merge(
       feature_dir: Path,
       *,
       merged_commit: str,
   ) -> dict[str, Any]:
       """Set final merge commit hash. Updates both top-level and latest history entry."""
       meta = load_meta(feature_dir)
       if meta is None:
           raise FileNotFoundError(f"No meta.json in {feature_dir}")

       meta["merged_commit"] = merged_commit
       history = meta.get("merge_history", [])
       if history:
           history[-1]["merged_commit"] = merged_commit
       meta["merge_history"] = history

       write_meta(feature_dir, meta)
       return meta
   ```

5. **`set_vcs_lock()`**:
   ```python
   def set_vcs_lock(
       feature_dir: Path,
       *,
       vcs_type: str,
       locked_at: str | None = None,
   ) -> dict[str, Any]:
       """Set VCS type and lock timestamp."""
       meta = load_meta(feature_dir)
       if meta is None:
           raise FileNotFoundError(f"No meta.json in {feature_dir}")

       meta["vcs"] = vcs_type
       if locked_at is not None:
           meta["vcs_locked_at"] = locked_at

       write_meta(feature_dir, meta)
       return meta
   ```

6. **`set_documentation_state()`**:
   ```python
   def set_documentation_state(
       feature_dir: Path,
       state: dict[str, Any],
   ) -> dict[str, Any]:
       """Set or replace documentation_state subtree."""
       meta = load_meta(feature_dir)
       if meta is None:
           raise FileNotFoundError(f"No meta.json in {feature_dir}")

       meta["documentation_state"] = state

       write_meta(feature_dir, meta)
       return meta
   ```

7. **`set_target_branch()`**:
   ```python
   def set_target_branch(
       feature_dir: Path,
       branch: str,
   ) -> dict[str, Any]:
       """Set target_branch field."""
       meta = load_meta(feature_dir)
       if meta is None:
           raise FileNotFoundError(f"No meta.json in {feature_dir}")

       meta["target_branch"] = branch

       write_meta(feature_dir, meta)
       return meta
   ```

8. **Helper**:
   ```python
   from datetime import datetime, timezone

   def _now_iso() -> str:
       """Current UTC time in ISO 8601."""
       return datetime.now(timezone.utc).isoformat()
   ```

**Files**: `src/specify_cli/feature_metadata.py`

### Subtask T007 – Unit tests

**Purpose**: Comprehensive test coverage for the metadata API.

**Steps**:
1. Create `tests/specify_cli/test_feature_metadata.py`.
2. Test cases:

   **load_meta tests**:
   - Load valid meta.json → returns dict
   - Load from missing file → returns None
   - Load malformed JSON → raises ValueError

   **validate_meta tests**:
   - Valid meta with all required fields → empty error list
   - Missing `feature_number` → error
   - Missing multiple required fields → multiple errors
   - Extra unknown fields → no errors (forward compatibility)

   **write_meta tests**:
   - Writes valid meta → file exists with standard format
   - Verify format: sorted keys, 2-space indent, `ensure_ascii=False`, trailing newline
   - Invalid meta → raises ValueError, file unchanged
   - Atomic safety: monkeypatch `os.replace` to raise → original file preserved, no temp file left

   **Mutation helper tests**:
   - `record_acceptance()`: sets all fields, appends to history
   - `record_acceptance()` with cap: 21 acceptances → history has 20 entries (oldest dropped)
   - `record_merge()` + `finalize_merge()`: sets merge fields, finalizes commit hash
   - `set_vcs_lock()`: sets vcs and vcs_locked_at
   - `set_documentation_state()`: sets/replaces documentation_state
   - `set_target_branch()`: updates target_branch
   - All helpers on missing meta.json → raises FileNotFoundError

   **Unknown field preservation**:
   - Write meta with unknown field `"custom_field": "value"` → field preserved after mutation

3. Each test uses `tmp_path` fixture for isolated temp directories.
4. Run: `python -m pytest tests/specify_cli/test_feature_metadata.py -v`

**Files**: `tests/specify_cli/test_feature_metadata.py` (new file)

## Risks & Mitigations

- **Risk**: Adding `sort_keys=True` to existing convention changes diff output when existing meta.json files are mutated.
  **Mitigation**: This is expected — the one-time reformat happens naturally on first mutation. Document in commit message.
- **Risk**: `os.replace()` on Windows requires target to not be open by another process.
  **Mitigation**: meta.json is only written during CLI operations, never held open by a server process.

## Review Guidance

- Verify `_atomic_write()` cleanup logic: if `os.replace()` fails, temp file is removed and fd is closed.
- Verify `sort_keys=True` is present in `write_meta()` — this is the only format addition over the existing helper.
- Verify bounded history uses `[-HISTORY_CAP:]` (keeps most recent, drops oldest).
- Verify unknown fields survive a round-trip: `load_meta()` → mutation → `write_meta()` preserves keys not in TypedDict.
- Check `mypy --strict` passes on the new module.

## Activity Log

- 2026-03-18T20:21:07Z – system – lane=planned – Prompt created.
- 2026-03-18T20:31:37Z – coordinator – shell_pid=45023 – lane=doing – Assigned agent via workflow command
- 2026-03-18T20:37:03Z – coordinator – shell_pid=45023 – lane=for_review – All 7 subtasks implemented and tested. 41 tests passing, mypy --strict clean, ruff clean.
- 2026-03-18T20:37:19Z – codex – shell_pid=46484 – lane=doing – Started review via workflow command
- 2026-03-18T20:43:19Z – codex – shell_pid=46484 – lane=planned – Moved to planned
- 2026-03-18T20:43:31Z – coordinator – shell_pid=47655 – lane=doing – Started implementation via workflow command
- 2026-03-18T20:45:21Z – coordinator – shell_pid=47655 – lane=for_review – Fixed short write bug per Codex feedback (cycle 2/3): replaced os.write() with os.fdopen() context manager, added 2 completeness tests
