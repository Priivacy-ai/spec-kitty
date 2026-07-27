---
work_package_id: WP03
title: Status Write Path Sanitization
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-event-architecture-cli-git-truth-01KT119Y
base_commit: ae6af4c716fad6a07424bdcf326c141ee33abdbb
created_at: '2026-06-01T08:38:11.652586+00:00'
subtasks:
- T012
- T013
- T014
agent: "claude:claude-sonnet-4-6:orchestrator:orchestrator"
shell_pid: "73148"
history:
- date: '2026-06-01'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/store.py
- src/specify_cli/decisions/emit.py
- tests/specify_cli/status/test_store_sanitized.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Apply `sanitize_event_for_log()` at the two existing git-write boundaries for event data: `status/store.py::append_event()` (writes `status.events.jsonl`) and `decisions/emit.py` (writes `DecisionPointOpened/Resolved` events to `status.events.jsonl`). Confirm zero PII fields in any written output.

**Implement command**: `spec-kitty agent action implement WP03 --agent claude`

**Prerequisite**: WP01 must be merged.

Can run in parallel with WP02 (different files, no conflict).

---

## Context

The sanitizer from WP01 is a drop-in call at write boundaries. Two existing write paths need it applied:

1. **`status/store.py::append_event()`** — the central write function for `status.events.jsonl`. Every status transition (WP lane changes) goes through here. Adding the sanitizer here covers all future status writes automatically.

2. **`decisions/emit.py`** — emits `DecisionPointOpened` and `DecisionPointResolved` events (decision *lifecycle*, not the same as the `DecisionInputRequested/Answered` events handled by WP02). These currently write to `status.events.jsonl` and must also be sanitized.

**Spec references**: FR-006, FR-007, FR-008, NFR-001

**Files to read before starting**:
- `src/specify_cli/status/store.py` — find `append_event()` function
- `src/specify_cli/decisions/emit.py` — find `_append_raw_event()` function (line ~80)

---

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`

---

## Subtask Guidance

### T012 — Apply `sanitize_event_for_log()` in `status/store.py::append_event()`

**Purpose**: Gate all `status.events.jsonl` writes through the sanitizer.

**Steps**:
1. Read `src/specify_cli/status/store.py` fully.
2. Find the `append_event()` function.
3. Add a sanitization call before the JSON serialization:
   ```python
   from specify_cli.events import sanitize_event_for_log

   def append_event(feature_dir: Path, event: StatusEvent) -> None:
       event_dict = event.model_dump()  # or .dict() depending on Pydantic version
       sanitized = sanitize_event_for_log(event_dict)
       line = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
       # ... existing write logic ...
   ```
4. If `append_event()` already serializes to JSON at a different point, insert the sanitizer call on the dict representation before that serialization.
5. Ensure the modification does not change the append-only write behavior, atomic semantics, or error handling.

**Files**: `src/specify_cli/status/store.py` (+5 lines, 1 import)

---

### T013 — Apply sanitizer in `decisions/emit.py` for `DecisionPointOpened/Resolved` writes

**Purpose**: Sanitize decision lifecycle events before they are appended to `status.events.jsonl`.

**Steps**:
1. Read `src/specify_cli/decisions/emit.py` fully.
2. Find `_append_raw_event()` (approximately line 80) — the shared write function for both `emit_decision_opened` and `emit_decision_resolved`.
3. Apply the sanitizer to the `event_dict` parameter before JSON serialization:
   ```python
   from specify_cli.events import sanitize_event_for_log

   def _append_raw_event(events_path: Path, event_dict: dict) -> int:
       sanitized = sanitize_event_for_log(event_dict)
       line = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
       # ... existing file write ...
   ```
4. Do NOT change the function signature or return type.

**Files**: `src/specify_cli/decisions/emit.py` (+4 lines, 1 import)

---

### T014 — Tests confirming zero PII in `status.events.jsonl` and `decisions.events.jsonl` writes

**Purpose**: Table-driven tests proving that no PII field survives the write path.

**Steps**:
1. Create `tests/specify_cli/status/test_store_sanitized.py`.
2. Build a synthetic event dict containing all six PII fields + known non-PII fields.
3. Call the write function (patched to write to `tmp_path`).
4. Read back the written line and parse as JSON.
5. Assert none of the PII field names appear as keys in the parsed dict (at any nesting level):
   ```python
   @pytest.mark.parametrize("pii_field", ["machine_name", "hostname", "workspace_path", "developer_name", "developer_email", "session_started_at"])
   def test_pii_absent_from_status_events_jsonl(tmp_path, pii_field):
       # Write an event with the PII field present
       # Read back the written line
       # Assert PII field absent
       ...
   ```
6. Assert that non-PII fields (`event_id`, `mission_id`, `at`, event-type-specific payload fields) are preserved.
7. If testing `decisions/emit.py`, repeat the same assertion for `DecisionPointOpened` and `DecisionPointResolved` events.

**Files**: `tests/specify_cli/status/test_store_sanitized.py` (~80 lines)

---

## Definition of Done

- [ ] `status/store.py::append_event()` calls `sanitize_event_for_log()` before writing
- [ ] `decisions/emit.py::_append_raw_event()` calls `sanitize_event_for_log()` before writing
- [ ] `mypy --strict` passes on both modified files
- [ ] All existing `status` and `decisions` tests still pass
- [ ] New tests confirm zero PII fields in all write-path output
- [ ] ≥90% line coverage on new test file

## Risks

- `status/store.py` may use a `StatusEvent` Pydantic model rather than a raw dict at the point of serialization. If so, call `.model_dump()` before passing to `sanitize_event_for_log()`.
- Existing tests that assert on exact event line content may fail if they include PII fields in their fixture payloads — update those fixtures to omit PII, not to disable the sanitizer.

## Reviewer Guidance

1. Check that the sanitizer is called on the **dict** representation, not on the serialized JSON string
2. Confirm existing tests still pass (no fixture regressions from sanitizing)
3. Verify the write semantics (append-only, atomic) are unchanged

## Activity Log

- 2026-06-01T08:38:11Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=73148 – Assigned agent via action command
