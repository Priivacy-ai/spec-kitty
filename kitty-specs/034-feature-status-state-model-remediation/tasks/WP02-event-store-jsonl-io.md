---
work_package_id: WP02
title: Event Store (JSONL I/O)
lane: "for_review"
dependencies:
- WP01
base_branch: 2.x
base_commit: 1b37d3a7c2a626005000cff7b1dd2e76a87de203
created_at: '2026-02-08T14:31:33.820128+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-wp02"
shell_pid: "42565"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 -- Event Store (JSONL I/O)

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

This WP depends on WP01 (StatusEvent model for serialization/deserialization). Branch from WP01's branch.

---

## Objectives & Success Criteria

Create the append-only JSONL event store -- the persistence layer for canonical status events. This WP delivers:

1. `append_event()` function that atomically appends a single StatusEvent as a JSON line
2. `read_events()` function that reads and deserializes all events from the log
3. `read_events_raw()` function that reads events as raw dicts (for debugging/inspection)
4. Corruption detection that reports specific line numbers and fails rather than silently skipping
5. Idempotent file/directory creation on first event
6. Comprehensive unit tests

**Success**: Append an event, read it back, verify it matches. Corrupt a line, verify the exact line number is reported in the error. Append multiple events, verify ordering is preserved. Empty file returns empty list.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- FR-001 (append-only JSONL), FR-002 (event fields), Edge Cases (corruption, concurrent appends)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-1 (Event Schema), AD-2 (Reducer Algorithm step 2: validate each line)
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- StatusEvent entity, File Layout section
- **Contracts**: `kitty-specs/034-feature-status-state-model-remediation/contracts/event-schema.json` -- full field definitions

**Key constraints**:
- File path: `kitty-specs/<feature>/status.events.jsonl` (relative to repo root)
- One JSON object per line -- no pretty-printing within lines
- `json.dumps(event.to_dict(), sort_keys=True)` for deterministic key ordering per line
- Never silently skip bad lines -- report line number and fail
- Use `open(path, "a")` for append (safe for single-writer scenarios)
- Concurrent writers handled at git merge time (append-only files concatenate cleanly)
- No fallback mechanisms -- corruption is always a hard error

---

## Subtasks & Detailed Guidance

### Subtask T006 -- Create `src/specify_cli/status/store.py`

**Purpose**: Core I/O module for the event store. Three public functions: append, read typed, read raw.

**Steps**:
1. Create `src/specify_cli/status/store.py` with imports:
   ```python
   from __future__ import annotations

   import json
   from pathlib import Path

   from specify_cli.status.models import StatusEvent
   ```

2. Define the store file name constant:
   ```python
   EVENTS_FILENAME = "status.events.jsonl"
   ```

3. Define custom exception:
   ```python
   class StoreError(Exception):
       """Raised when event store operations fail (corruption, I/O errors)."""
       pass
   ```

4. Implement `_events_path()` helper:
   ```python
   def _events_path(feature_dir: Path) -> Path:
       """Return the path to the events JSONL file for a feature directory."""
       return feature_dir / EVENTS_FILENAME
   ```

5. Implement `append_event()`:
   ```python
   def append_event(feature_dir: Path, event: StatusEvent) -> None:
       """Append a single StatusEvent as a JSON line to the event store.

       Creates the file and parent directories if they do not exist.
       Uses deterministic key ordering (sort_keys=True) for consistent output.
       """
       path = _events_path(feature_dir)
       path.parent.mkdir(parents=True, exist_ok=True)
       line = json.dumps(event.to_dict(), sort_keys=True) + "\n"
       with open(path, "a", encoding="utf-8") as f:
           f.write(line)
   ```

6. Implement `read_events()`:
   ```python
   def read_events(feature_dir: Path) -> list[StatusEvent]:
       """Read and deserialize all events from the event store.

       Returns an empty list if the file does not exist.
       Raises StoreError on any corruption (invalid JSON, invalid event structure).
       """
       path = _events_path(feature_dir)
       if not path.exists():
           return []
       raw = read_events_raw(feature_dir)
       events: list[StatusEvent] = []
       for i, entry in enumerate(raw, start=1):
           try:
               events.append(StatusEvent.from_dict(entry))
           except (KeyError, ValueError, TypeError) as exc:
               raise StoreError(
                   f"Line {i}: invalid event structure: {exc}"
               ) from exc
       return events
   ```

7. Implement `read_events_raw()`:
   ```python
   def read_events_raw(feature_dir: Path) -> list[dict]:
       """Read all events as raw dicts without deserializing into StatusEvent.

       Returns an empty list if the file does not exist.
       Raises StoreError on invalid JSON lines.
       """
       path = _events_path(feature_dir)
       if not path.exists():
           return []
       entries: list[dict] = []
       with open(path, "r", encoding="utf-8") as f:
           for line_num, line in enumerate(f, start=1):
               stripped = line.strip()
               if not stripped:
                   continue  # Skip blank lines (e.g., trailing newline)
               try:
                   entries.append(json.loads(stripped))
               except json.JSONDecodeError as exc:
                   preview = stripped[:80]
                   raise StoreError(
                       f"Line {line_num}: invalid JSON: {preview}"
                   ) from exc
       return entries
   ```

**Files**: `src/specify_cli/status/store.py` (new file)

**Validation**:
- `append_event(dir, event)` creates the file if it does not exist
- `read_events(dir)` returns the same event back
- `read_events_raw(dir)` returns the raw dict representation

**Edge Cases**:
- Blank lines between events (e.g., from manual editing) should be skipped
- Trailing newline at end of file is normal (each append adds `\n`)
- File with only whitespace returns empty list
- Non-existent file returns empty list (not an error)

---

### Subtask T007 -- JSONL serialization with deterministic key ordering

**Purpose**: Ensure every JSON line in the event store has deterministic key ordering for git-friendly diffs.

**Steps**:
1. In `append_event()`, use `json.dumps(event.to_dict(), sort_keys=True)` -- this is already specified in T006
2. Verify that `StatusEvent.to_dict()` produces a flat dict (no nested objects that might serialize non-deterministically)
3. For nested objects (evidence, repos, verification), `to_dict()` must recursively produce dicts with string keys
4. Verify round-trip: `json.loads(json.dumps(event.to_dict(), sort_keys=True))` produces the same dict

**Files**: `src/specify_cli/status/store.py` (same file as T006)

**Validation**: Write two events with different field insertion orders in their source dicts. After serialization, the JSON lines should have identical key ordering.

**Edge Cases**:
- Unicode in actor names or reasons: `ensure_ascii=False` is NOT used in per-line serialization (only in snapshot materialization). Per-line uses default `ensure_ascii=True` for maximum compatibility
- Empty string values should serialize as `""`, not be omitted
- `None` values should serialize as `null`

---

### Subtask T008 -- Corruption detection

**Purpose**: When the event store contains invalid JSON, report the exact line number and fail immediately.

**Steps**:
1. The corruption detection is already implemented in `read_events_raw()` (T006) -- this subtask ensures comprehensive error reporting
2. Error message format: `"Line {N}: invalid JSON: {first_80_chars_of_line}"`
3. For invalid event structure (valid JSON but wrong fields): `"Line {N}: invalid event structure: {exception_message}"`
4. Never catch and silently skip -- every error propagates as `StoreError`

**Files**: `src/specify_cli/status/store.py` (same file)

**Validation**:
- Insert `{"this is not a valid event"}` as a line -- should raise StoreError with "invalid JSON"
- Insert `not json at all` as a line -- should raise StoreError with "invalid JSON"
- Insert `{"event_id": "bad"}` (valid JSON, missing fields) -- should raise StoreError with "invalid event structure"

**Edge Cases**:
- Very long corrupted lines: preview truncated to 80 chars
- Binary data in file: json.loads will raise JSONDecodeError, caught and re-raised as StoreError
- Empty JSON object `{}` is valid JSON but invalid event -- caught in `read_events()` at the StatusEvent.from_dict level

---

### Subtask T009 -- File and directory creation on first event

**Purpose**: Idempotent creation of the events file and its parent directory tree.

**Steps**:
1. In `append_event()`, call `path.parent.mkdir(parents=True, exist_ok=True)` before opening
2. The `open(path, "a")` call will create the file if it does not exist
3. On subsequent appends, `mkdir` is a no-op (`exist_ok=True`) and `open("a")` appends

**Files**: `src/specify_cli/status/store.py` (same file)

**Validation**:
- Given a completely non-existent directory tree, `append_event()` creates all needed directories and the file
- Given an existing directory but no file, `append_event()` creates just the file
- Given an existing file, `append_event()` appends to it

**Edge Cases**:
- Permission errors (read-only filesystem) should propagate as OSError, not caught
- Race condition: two processes creating the same directory simultaneously -- `exist_ok=True` handles this

---

### Subtask T010 -- Unit tests for store

**Purpose**: Comprehensive testing of all store operations.

**Steps**:
1. Create `tests/specify_cli/status/test_store.py`
2. Use `tmp_path` fixture for isolated test environments
3. Create a helper function or fixture to build valid `StatusEvent` instances for testing
4. Test cases:

   - `test_append_and_read_round_trip` -- append one event, read back, verify equality
   - `test_multiple_appends_preserve_order` -- append 3 events, read back, verify order matches append order
   - `test_read_empty_file` -- create empty file, read returns empty list
   - `test_read_nonexistent_file` -- read from non-existent path returns empty list
   - `test_file_created_on_first_event` -- verify file exists after first append
   - `test_directory_created_on_first_event` -- verify parent dirs created
   - `test_corruption_invalid_json` -- write a bad line manually, read raises StoreError with line number
   - `test_corruption_reports_line_number` -- corrupt line 3 of 5, error message contains "Line 3"
   - `test_corruption_invalid_event_structure` -- write valid JSON but missing required fields, read_events raises StoreError
   - `test_read_raw_returns_dicts` -- read_events_raw returns list[dict], not StatusEvent
   - `test_deterministic_key_ordering` -- two events with different internal ordering produce same-ordered JSON
   - `test_blank_lines_skipped` -- manually insert blank lines, read still works

**Files**: `tests/specify_cli/status/test_store.py` (new file)

**Validation**: `python -m pytest tests/specify_cli/status/test_store.py -v` -- all pass

**Edge Cases**:
- Test with unicode characters in event fields (actor name with non-ASCII)
- Test with very long reason strings
- Test that appending to an existing file with prior content does not corrupt it

---

## Test Strategy

**Required per user requirements**: Unit tests covering all store operations.

- **Coverage target**: 100% of store.py
- **Test runner**: `python -m pytest tests/specify_cli/status/test_store.py -v`
- **Fixtures**: Use `tmp_path` for isolated test environments. Create factory functions for valid StatusEvent instances
- **Corruption tests**: Manually write bad content to file, then call read functions
- **Idempotency tests**: Call append multiple times, verify file grows correctly
- **Negative tests**: Every error path (corruption, missing fields) must have a dedicated test

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Concurrent writers corrupting file | Interleaved partial lines | Git merge of append-only files handles this; ULID deduplication in reducer (WP03) handles overlaps |
| Large event files slow reads | Performance degradation | For MVP, read all lines. Future optimization: streaming/generator. Typical scale is 10s-100s of events |
| File system permissions | write failure | Let OSError propagate -- no fallback, no silent skip |
| Encoding issues | Mojibake in actor names | Use `encoding="utf-8"` explicitly on all file operations |
| Blank line handling | False corruption detection | Skip blank lines in read_events_raw (trailing newlines are normal) |

---

## Review Guidance

- **Check append_event**: Uses `sort_keys=True`, appends `\n`, creates directories with `parents=True`
- **Check read_events_raw**: Reports exact line number on corruption, never silently skips
- **Check read_events**: Converts raw dicts to StatusEvent via `from_dict()`, reports structural errors with line number
- **Check idempotency**: mkdir with `exist_ok=True`, open with `"a"` mode
- **Check error messages**: Format is `"Line {N}: invalid JSON: {preview}"` or `"Line {N}: invalid event structure: {exc}"`
- **No fallback mechanisms**: Corruption is always StoreError, never silently handled
- **No silent data loss**: Every line must be valid JSON and valid StatusEvent, or the operation fails

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T14:31:35Z – claude-wp02 – shell_pid=42565 – lane=doing – Assigned agent via workflow command
- 2026-02-08T14:46:37Z – claude-wp02 – shell_pid=42565 – lane=for_review – Moved to for_review
