---
work_package_id: WP01
title: Status Model Read-Path Cleanup
dependencies: []
requirement_refs:
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-075-mission-build-identity-contract-cutover
base_commit: 5bb0632a2e1dfadffdc36aa1c63a25c0eddb6ba7
created_at: '2026-04-08T05:23:00.522840+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
shell_pid: '6171'
history:
- date: '2026-04-08'
  actor: planner
  action: created
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
mission_slug: 075-mission-build-identity-contract-cutover
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/validate.py
- tests/cross_branch/fixtures/legacy_feature_slug_event.jsonl
- tests/specify_cli/status/test_models.py
- tests/specify_cli/status/test_validate.py
tags: []
---

# WP01 — Status Model Read-Path Cleanup

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Workspace**: allocated by `spec-kitty implement WP01` (lane-based worktree)
- **Command**: `spec-kitty implement WP01 --mission 075-mission-build-identity-contract-cutover`

## Objective

Remove all `feature_slug` read-path fallbacks from `status/models.py` and `status/validate.py`. These are the two status-domain files that silently normalize legacy inbound events — after this WP they fail closed with `KeyError` when `mission_slug` is absent. Also remove the now-dead `with_tracked_mission_slug_aliases` import and call from `status/models.py`.

**What "fail closed" means here**: any code path that receives a dict without `mission_slug` (regardless of whether `feature_slug` is present) must raise an explicit error, not silently normalize the input.

## Context

The prior cutover left these fallbacks in place as temporary bridges. They are the remaining live compatibility bridges on the read path (FR-013). The contract gate (`contract_gate.py`) already prevents `feature_slug` from leaving the system on outbound paths; this WP closes the inbound side.

**Files you will touch**:
- `src/specify_cli/status/models.py` — three locations: StatusEvent.from_dict (line 221), StatusSnapshot.from_dict (line 264), and the with_tracked_mission_slug_aliases call (line ~251)
- `src/specify_cli/status/validate.py` — one location: validate_event_schema (line 72)
- `tests/cross_branch/fixtures/legacy_feature_slug_event.jsonl` — new fixture file
- `tests/specify_cli/status/test_models.py` — add failing-then-passing tests
- `tests/specify_cli/status/test_validate.py` — add failing-then-passing test

## Subtask Guidance

### T001 — Create legacy event fixture

**File**: `tests/cross_branch/fixtures/legacy_feature_slug_event.jsonl`

Write a single-line JSONL file containing one synthetic status event that uses `feature_slug` instead of `mission_slug`. This fixture is the test input for T002 and T004.

```json
{"actor":"claude","at":"2025-01-01T00:00:00+00:00","event_id":"01HXXXXXXXXXXXXXXXXXXXXXXX","evidence":null,"execution_mode":"worktree","feature_slug":"034-legacy-feature","force":false,"from_lane":"planned","reason":null,"review_ref":null,"to_lane":"claimed","wp_id":"WP01"}
```

Key properties:
- `feature_slug` is present (`"034-legacy-feature"`)
- `mission_slug` is **absent** (this is the legacy shape)
- All other required fields are present so the only failure is the missing `mission_slug`

**Validation**: `wc -l` returns 1; `python3 -c "import json; json.loads(open('...').read())"` parses without error.

---

### T002 — Write failing test: StatusEvent.from_dict raises KeyError

**File**: `tests/specify_cli/status/test_models.py`

Add a test (before making any production changes) that reads the legacy fixture and asserts `KeyError` is raised. This test must **fail** before T003 (the current code silently backfills).

```python
import json
from pathlib import Path
import pytest
from specify_cli.status.models import StatusEvent

LEGACY_EVENT = json.loads(
    (Path(__file__).parent.parent.parent / "cross_branch/fixtures/legacy_feature_slug_event.jsonl").read_text()
)

def test_status_event_from_dict_rejects_feature_slug_only():
    """StatusEvent.from_dict must raise KeyError when mission_slug is absent."""
    with pytest.raises(KeyError, match="mission_slug"):
        StatusEvent.from_dict(LEGACY_EVENT)
```

Run `pytest tests/specify_cli/status/test_models.py -k test_status_event_from_dict_rejects_feature_slug_only` — it should FAIL at this point (the test is red). Proceed to T003 to make it green.

---

### T003 — Remove feature_slug fallback from StatusEvent.from_dict

**File**: `src/specify_cli/status/models.py`, line ~221

Locate:
```python
mission_slug=data.get("mission_slug") or data.get("feature_slug", ""),
```

Replace with:
```python
mission_slug=data["mission_slug"],
```

The bracket access raises `KeyError("mission_slug")` if absent — that's the desired behavior.

Run the test from T002 — it should now pass (green).

**Audit**: Search for any other `data.get("feature_slug")` calls in this file before moving on. The StatusSnapshot path (T004-T005) is below.

---

### T004 — Write failing test: StatusSnapshot.from_dict raises KeyError

**File**: `tests/specify_cli/status/test_models.py`

Add an analogous test for `StatusSnapshot.from_dict`:

```python
from specify_cli.status.models import StatusSnapshot

def test_status_snapshot_from_dict_rejects_feature_slug_only():
    """StatusSnapshot.from_dict must raise KeyError when mission_slug is absent."""
    with pytest.raises(KeyError, match="mission_slug"):
        StatusSnapshot.from_dict(LEGACY_EVENT)
```

Run this test — it should FAIL. Proceed to T005.

---

### T005 — Remove feature_slug fallback from StatusSnapshot.from_dict

**File**: `src/specify_cli/status/models.py`, lines ~264-268

Locate:
```python
feature_slug = data.get("mission_slug") or data.get("feature_slug")
if feature_slug is None:
    raise KeyError("mission_slug")
return cls(
    mission_slug=feature_slug,
    ...
)
```

Replace with:
```python
return cls(
    mission_slug=data["mission_slug"],
    ...
)
```

The variable name `feature_slug` is misleading — it was holding either value. Eliminate it entirely.

Run T004's test — it should now pass.

---

### T006 — Write failing test: validate_event_schema rejects missing mission_slug without legacy fallback

**File**: `tests/specify_cli/status/test_validate.py`

Add a test asserting that validation of a legacy-shaped event (with `feature_slug` only) produces a finding that mentions `mission_slug` — without any mention of "legacy" or "feature_slug" as an acceptable alternative.

```python
from specify_cli.status.validate import validate_event_schema

def test_validate_event_schema_rejects_feature_slug_only():
    """validate_event_schema must flag missing mission_slug with no legacy fallback mention."""
    event = {"feature_slug": "034-legacy", "wp_id": "WP01", "to_lane": "claimed"}
    findings = validate_event_schema(event)
    # Must report the missing required field
    assert any("mission_slug" in f for f in findings), f"Expected mission_slug finding, got: {findings}"
    # Must NOT accept feature_slug as a substitute
    assert not any("feature_slug" in f.lower() and "ok" in f.lower() for f in findings)
```

Run — should FAIL because the current code's finding message mentions `"or legacy mission_slug"`. Proceed to T007.

---

### T007 — Remove feature_slug branch from status/validate.py

**File**: `src/specify_cli/status/validate.py`, line ~72

Locate:
```python
if "mission_slug" not in event and "feature_slug" not in event:
    findings.append("Missing required field: mission_slug (or legacy mission_slug)")
```

Replace with:
```python
if "mission_slug" not in event:
    findings.append("Missing required field: mission_slug")
```

This removes the legacy-fallback branch. An event with only `feature_slug` now produces the finding.

Run T006's test — it should pass.

---

### T008 — Remove with_tracked_mission_slug_aliases import and usage from status/models.py

**File**: `src/specify_cli/status/models.py`

After T003 and T005 are done, `with_tracked_mission_slug_aliases` in `models.py` is dead code (it backfills `mission_slug` from `feature_slug`, but `feature_slug` can no longer arrive via inbound paths). Remove it:

1. **Find the import** (line ~15):
   ```python
   from specify_cli.core.identity_aliases import with_tracked_mission_slug_aliases
   ```
   Delete this line.

2. **Find the usage** (line ~251), which wraps a dict return in a `to_dict`-style method:
   ```python
   return with_tracked_mission_slug_aliases({
       "mission_slug": self.mission_slug,
       ...
   })
   ```
   Replace with the unwrapped dict:
   ```python
   return {
       "mission_slug": self.mission_slug,
       ...
   }
   ```

3. Run `mypy --strict src/specify_cli/status/models.py` — must pass with no errors.
4. Run the full `tests/specify_cli/status/` test suite — must be green.

**Why this is safe**: After T003 and T005, `mission_slug` is always populated from the canonical field. The alias function's condition (`if enriched.get("mission_slug") is None`) would never trigger, so removing the call is a pure dead-code removal.

## Definition of Done

- [ ] `legacy_feature_slug_event.jsonl` fixture exists and is valid JSONL
- [ ] `StatusEvent.from_dict(legacy_event)` raises `KeyError("mission_slug")` — asserted by test
- [ ] `StatusSnapshot.from_dict(legacy_event)` raises `KeyError("mission_slug")` — asserted by test
- [ ] `validate_event_schema({"feature_slug": "x"})` returns finding mentioning `mission_slug` with no legacy alternative — asserted by test
- [ ] `status/models.py` imports nothing from `core.identity_aliases`
- [ ] `mypy --strict src/specify_cli/status/models.py src/specify_cli/status/validate.py` passes
- [ ] All existing `tests/specify_cli/status/` tests remain green

## Risks

| Risk | Mitigation |
|------|-----------|
| Existing tests pass legacy-shaped dicts to `StatusEvent.from_dict` | Search `tests/` for `feature_slug` before T003; update any such tests to use `mission_slug` |
| `with_tracked_mission_slug_aliases` call in `to_dict()` wraps a complex nested structure | Read the full method before simplifying; ensure the unwrapped return is identical to the wrapped one |

## Reviewer Guidance

- Confirm the legacy fixture file exists and is valid JSONL
- Confirm `data["mission_slug"]` (bracket, not `.get()`) is used in both StatusEvent and StatusSnapshot deserialization
- Confirm no import of `identity_aliases` remains in `status/models.py` or `status/validate.py`
- Grep for `feature_slug` in both files — must be zero remaining hits (excluding comments)
