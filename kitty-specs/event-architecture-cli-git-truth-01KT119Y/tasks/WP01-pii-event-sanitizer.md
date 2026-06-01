---
work_package_id: WP01
title: PII Event Sanitizer
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:claude-sonnet-4-6:orchestrator:orchestrator"
shell_pid: "64378"
history:
- date: '2026-06-01'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/events/
execution_mode: code_change
owned_files:
- src/specify_cli/events/__init__.py
- src/specify_cli/events/sanitizer.py
- tests/specify_cli/events/test_sanitizer.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

This sets your working style, quality bar, and tool preferences for Python implementation work.

---

## Objective

Create the `src/specify_cli/events/` package and implement `sanitize_event_for_log()` — a pure function that strips PII fields from any event envelope dict and replaces absolute session timestamps with a relative `session_duration_s` value. This is a foundational building block; WP02 and WP03 both consume it.

**Implement command**: `spec-kitty agent action implement WP01 --agent claude`

---

## Context

The event architecture redesign requires that no PII fields appear in any git-committed event file. Rather than scattering field-stripping logic across every write site, we centralise it in a single pure function. "Pure" means: takes a dict, returns a new dict, never mutates the input, never has side effects.

**Spec references**: FR-006, FR-007, FR-008, FR-009

**PII fields to strip** (at all nesting levels in the envelope):
- `machine_name`
- `hostname`
- `workspace_path`
- `developer_name`
- `developer_email`

**Timestamp replacement**: If `session_started_at` and `session_ended_at` are both present, compute `session_duration_s = int((ended - started).total_seconds())` and remove both source fields. If only `session_started_at` is present (session still running), remove it without replacement.

**Fields to preserve** (not PII): `node_id`, `build_id`, `mission_id`, `project_uuid`, `git_branch`, `head_commit_sha`, `session_duration_s`, all event-type-specific payload fields.

---

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Your execution worktree is resolved from `lanes.json` by `spec-kitty agent action implement WP01 --agent <name>`. Do not branch manually.

---

## Subtask Guidance

### T001 — Create `src/specify_cli/events/__init__.py`

**Purpose**: Establish the new `events` package under `specify_cli`. Expose `sanitize_event_for_log` as the public API.

**Steps**:
1. Create `src/specify_cli/events/__init__.py` with:
   ```python
   """Event utilities for the Spec Kitty CLI.

   Public API:
       sanitize_event_for_log: Strip PII fields from an event envelope dict.
   """
   from .sanitizer import sanitize_event_for_log

   __all__ = ["sanitize_event_for_log"]
   ```
2. Confirm `src/specify_cli/events/` directory is created.

**Files**: `src/specify_cli/events/__init__.py` (new, ~10 lines)

---

### T002 — Implement `sanitize_event_for_log()` — strip PII fields

**Purpose**: Remove each PII field from the envelope dict. Must work at all nesting levels (top-level envelope AND nested payload dicts).

**Steps**:
1. Create `src/specify_cli/events/sanitizer.py`.
2. Define `_PII_FIELDS: frozenset[str]` constant:
   ```python
   _PII_FIELDS: frozenset[str] = frozenset({
       "machine_name",
       "hostname",
       "workspace_path",
       "developer_name",
       "developer_email",
   })
   ```
3. Implement `sanitize_event_for_log(envelope: dict[str, Any]) -> dict[str, Any]`:
   - Deep-copy the input so the function is pure.
   - Recursively walk any nested dicts and strip `_PII_FIELDS` at every level.
   - Do NOT strip fields from lists of non-dict items.
   - Return the cleaned copy.
4. Add `mypy --strict`-compatible type annotations. Use `from __future__ import annotations` for forward-compatible annotations.

**Example:**
```python
# Input
{"event_type": "DecisionInputRequested", "machine_name": "roberts-mbp", "payload": {"workspace_path": "/Users/robert/project"}}

# Output
{"event_type": "DecisionInputRequested", "payload": {}}
```

**Files**: `src/specify_cli/events/sanitizer.py` (~50 lines)

---

### T003 — Implement session timestamp replacement

**Purpose**: Replace absolute session start/end timestamps (which reveal working hours) with a relative `session_duration_s` integer.

**Steps**:
1. In `sanitize_event_for_log()`, after stripping PII fields from the top-level dict:
   - If both `session_started_at` and `session_ended_at` are present:
     - Parse both as ISO8601 datetimes.
     - Compute `session_duration_s = int((ended - started).total_seconds())`.
     - Remove `session_started_at` and `session_ended_at`.
     - Add `session_duration_s` to the result dict.
   - If only `session_started_at` is present (session still running):
     - Remove `session_started_at` without replacement.
   - `session_ended_at` alone (no started): remove it, no replacement.
2. Use `datetime.fromisoformat()` for parsing; handle both `+00:00` and `Z` suffixes (Python 3.11+ handles `Z`).
3. If parsing fails (malformed timestamp), remove the field silently and log a debug message; do not raise.

**Files**: `src/specify_cli/events/sanitizer.py` (extension of T002, +30 lines)

---

### T004 — Unit tests for PII field removal

**Purpose**: Table-driven tests that confirm each PII field is removed in isolation and in combination.

**Steps**:
1. Create `tests/specify_cli/events/test_sanitizer.py`.
2. Write `@pytest.mark.parametrize` test for each field in `_PII_FIELDS`:
   ```python
   @pytest.mark.parametrize("pii_field", ["machine_name", "hostname", "workspace_path", "developer_name", "developer_email"])
   def test_pii_field_stripped(pii_field: str) -> None:
       envelope = {"event_type": "TestEvent", pii_field: "sensitive-value"}
       result = sanitize_event_for_log(envelope)
       assert pii_field not in result
       assert result["event_type"] == "TestEvent"
   ```
3. Add test for nested PII (field in `payload` dict):
   ```python
   def test_pii_stripped_from_nested_payload() -> None:
       envelope = {"event_type": "E", "payload": {"machine_name": "x", "safe_field": "keep"}}
       result = sanitize_event_for_log(envelope)
       assert "machine_name" not in result["payload"]
       assert result["payload"]["safe_field"] == "keep"
   ```
4. Add test confirming input is not mutated:
   ```python
   def test_does_not_mutate_input() -> None:
       original = {"machine_name": "x"}
       sanitize_event_for_log(original)
       assert original == {"machine_name": "x"}
   ```
5. Add test confirming preserved fields remain unchanged.

**Files**: `tests/specify_cli/events/test_sanitizer.py` (~80 lines)

---

### T005 — Unit tests for timestamp replacement edge cases

**Purpose**: Cover the three timestamp scenarios and error handling.

**Steps**:
1. Test both timestamps present → `session_duration_s` computed, both originals removed:
   ```python
   def test_both_timestamps_replaced_with_duration() -> None:
       envelope = {
           "session_started_at": "2026-06-01T07:00:00Z",
           "session_ended_at": "2026-06-01T07:05:30Z",
       }
       result = sanitize_event_for_log(envelope)
       assert "session_started_at" not in result
       assert "session_ended_at" not in result
       assert result["session_duration_s"] == 330  # 5m30s
   ```
2. Test only `session_started_at` → removed, no replacement, no key error.
3. Test only `session_ended_at` → removed, no replacement.
4. Test malformed timestamp → field removed, no exception raised.
5. Test neither field present → output unchanged.

**Files**: `tests/specify_cli/events/test_sanitizer.py` (extension of T004, +50 lines)

---

## Definition of Done

- [ ] `src/specify_cli/events/__init__.py` exports `sanitize_event_for_log`
- [ ] `src/specify_cli/events/sanitizer.py` implements the function with full PII stripping and timestamp replacement
- [ ] `sanitize_event_for_log()` is pure — does not mutate its input
- [ ] `mypy --strict src/specify_cli/events/` passes with zero errors
- [ ] `pytest tests/specify_cli/events/test_sanitizer.py -v` passes with 100% coverage
- [ ] None of the six PII fields appear in any return value of the function

## Risks

- Python 3.11's `datetime.fromisoformat()` handles `Z` suffix; earlier versions do not. The project requires 3.11+, so this is safe, but add a comment noting the version dependency.
- Deeply nested structures (e.g., payload within payload) must be handled recursively. Confirm the recursion guard handles circular references if they're theoretically possible (in practice they aren't in event dicts, but a safe guard is good practice).

## Reviewer Guidance

Confirm:
1. Function is truly pure (no global mutation, no side effects, test confirms input unchanged)
2. Recursion covers nested dicts at all depths
3. `mypy --strict` passes — no `Any` leakage in the public signature
4. Test parametrization covers every field in `_PII_FIELDS` individually

## Activity Log

- 2026-06-01T08:28:21Z – claude – Implementation complete, cycle 1. Tests pass (28/28), lint clean. sanitize_event_for_log() pure function with full PII stripping and timestamp replacement.
- 2026-06-01T08:29:02Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=64378 – Started review via action command
