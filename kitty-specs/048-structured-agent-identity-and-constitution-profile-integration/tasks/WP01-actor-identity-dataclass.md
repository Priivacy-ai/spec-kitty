---
work_package_id: WP01
title: ActorIdentity Dataclass & StatusEvent Backwards Compat
lane: "done"
dependencies: []
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: ''
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: ''
history:
- timestamp: '2026-03-08T10:13:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- NFR-001
- NFR-004
- C-001
---

# Work Package Prompt: WP01 – ActorIdentity Dataclass & StatusEvent Backwards Compat

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No `--base` flag needed (no dependencies).

---

## Objectives & Success Criteria

- Create the `ActorIdentity` frozen dataclass as the structured 4-part agent identity primitive
- Update `StatusEvent.actor` to use `ActorIdentity` internally with full backwards compatibility
- Ensure all existing JSONL event files with bare-string actors can be read without errors
- Ensure new events write structured actor dicts that round-trip correctly

**Success metrics**:
- `ActorIdentity.from_compact("claude:opus-4:impl:impl").to_dict()` → `{"tool": "claude", "model": "opus-4", "profile": "impl", "role": "impl"}`
- `ActorIdentity.from_legacy("claude-opus").to_compact()` → `"claude-opus:unknown:unknown:unknown"`
- `StatusEvent.from_dict({"actor": "claude", ...})` produces `ActorIdentity(tool="claude", model="unknown", profile="unknown", role="unknown")`
- `StatusEvent.from_dict({"actor": {"tool": "claude", ...}, ...})` produces structured `ActorIdentity`

## Context & Constraints

- **Spec**: `kitty-specs/048-structured-agent-identity-and-constitution-profile-integration/spec.md` — User Story 1, FR-001, FR-002
- **Data model**: `kitty-specs/048-structured-agent-identity-and-constitution-profile-integration/data-model.md` — ActorIdentity and StatusEvent sections
- **Contracts**: `kitty-specs/048-structured-agent-identity-and-constitution-profile-integration/contracts.md` — Contract 1 (ActorIdentity Protocol), Contract 5 (Backwards Compatibility)
- **Research**: `kitty-specs/048-structured-agent-identity-and-constitution-profile-integration/research.md` — R1 (serialisation strategy), R2 (compound parsing)
- **Constraint C-001**: No event log migration — existing JSONL files must not be modified
- **Constitution**: `.kittify/constitution/constitution.md` — Python 3.11+, mypy --strict, pytest 90%+

## Subtasks & Detailed Guidance

### Subtask T001 – Create ActorIdentity Frozen Dataclass

**Purpose**: Establish the domain primitive for structured agent identity. This dataclass is the single representation used across the entire codebase.

**Steps**:
1. Create new file `src/specify_cli/identity.py`
2. Define the frozen dataclass:
   ```python
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class ActorIdentity:
       """Structured 4-part agent identity.
       
       Fields:
           tool: Agent tool name (e.g., "claude", "copilot", "codex")
           model: Model variant (e.g., "claude-opus-4-6", "unknown")
           profile: Governance profile ID (e.g., "implementer", "unknown")
           role: Current role (e.g., "implementer", "reviewer", "unknown")
       """
       tool: str
       model: str = "unknown"
       profile: str = "unknown"
       role: str = "unknown"
   ```
3. Add `__post_init__` validation:
   - All fields must be non-empty strings after stripping whitespace
   - No field may contain `:` (colon) — it's the compound separator
   - Raise `ValueError` with clear message on violation

**Files**: `src/specify_cli/identity.py` (NEW, ~120 lines total after all T001+T002 methods)
**Parallel?**: No — T002 builds directly on this

### Subtask T002 – Implement Serialisation Methods

**Purpose**: Provide all conversion paths between `ActorIdentity` and external formats (dict, compact string, legacy string).

**Steps**:
1. Add `to_dict()` method:
   ```python
   def to_dict(self) -> dict[str, str]:
       return {"tool": self.tool, "model": self.model, "profile": self.profile, "role": self.role}
   ```

2. Add `from_dict()` classmethod:
   ```python
   @classmethod
   def from_dict(cls, d: dict[str, str]) -> "ActorIdentity":
       return cls(
           tool=str(d.get("tool", "unknown")),
           model=str(d.get("model", "unknown")),
           profile=str(d.get("profile", "unknown")),
           role=str(d.get("role", "unknown")),
       )
   ```

3. Add `to_compact()` method:
   ```python
   def to_compact(self) -> str:
       return f"{self.tool}:{self.model}:{self.profile}:{self.role}"
   ```

4. Add `from_compact()` classmethod — **this is the most complex method**:
   ```python
   @classmethod
   def from_compact(cls, s: str) -> "ActorIdentity":
       """Parse compact string 'tool:model:profile:role'.
       
       Fewer than 4 parts fills from the right with 'unknown':
         'claude' → tool=claude, model=unknown, profile=unknown, role=unknown
         'claude:opus' → tool=claude, model=opus, profile=unknown, role=unknown
         'claude:opus:impl' → tool=claude, model=opus, profile=impl, role=unknown
       """
       if not s or not s.strip():
           raise ValueError("Empty identity string")
       parts = s.strip().split(":")
       # Pad to 4 parts with "unknown"
       while len(parts) < 4:
           parts.append("unknown")
       return cls(tool=parts[0], model=parts[1], profile=parts[2], role=parts[3])
   ```

5. Add `from_legacy()` classmethod:
   ```python
   @classmethod
   def from_legacy(cls, s: str) -> "ActorIdentity":
       """Coerce a bare legacy string into ActorIdentity."""
       if not s or not s.strip():
           raise ValueError("Empty legacy actor string")
       return cls(tool=s.strip(), model="unknown", profile="unknown", role="unknown")
   ```

6. Add `__str__` that delegates to `to_compact()` for logging convenience.

**Files**: `src/specify_cli/identity.py`
**Parallel?**: No — sequential with T001

**Edge cases to handle**:
- Empty string → `ValueError`
- String with only colons (e.g., `":::"`) → all parts become empty → `ValueError` from `__post_init__`
- More than 4 parts (e.g., `"a:b:c:d:e"`) → use first 4 parts, ignore rest
- Whitespace in parts → strip each part

### Subtask T003 – Modify StatusEvent.actor Type

**Purpose**: Change `StatusEvent.actor` from `str` to `ActorIdentity` so all downstream consumers work with structured identity.

**Steps**:
1. In `src/specify_cli/status/models.py`, change the field:
   ```python
   # Before:
   actor: str
   # After:
   actor: ActorIdentity
   ```
2. Add import: `from specify_cli.identity import ActorIdentity`
3. Verify no other fields or methods reference `actor` as a string in this file

**Files**: `src/specify_cli/status/models.py` (~line 147)
**Parallel?**: No — T004 builds on this

### Subtask T004 – Update StatusEvent Serialisation

**Purpose**: Make `to_dict()` and `from_dict()` handle the new `ActorIdentity` type while preserving full backwards compatibility with existing JSONL files.

**Steps**:
1. Update `to_dict()` in `StatusEvent` (~lines 154-170):
   ```python
   # Change from:
   "actor": self.actor,
   # To:
   "actor": self.actor.to_dict(),
   ```

2. Update `from_dict()` in `StatusEvent` (~lines 172-189):
   ```python
   # Parse actor field — detect str vs dict:
   raw_actor = data.get("actor", "unknown")
   if isinstance(raw_actor, dict):
       actor = ActorIdentity.from_dict(raw_actor)
   elif isinstance(raw_actor, str):
       actor = ActorIdentity.from_legacy(raw_actor)
   else:
       actor = ActorIdentity.from_legacy(str(raw_actor))
   ```

3. Verify the `event_id`, `feature_slug`, etc. fields still serialise correctly (no regressions).

**Files**: `src/specify_cli/status/models.py`
**Parallel?**: No — depends on T003

**Critical test cases**:
- Old JSONL: `{"actor": "claude", ...}` → reads as `ActorIdentity(tool="claude", ...)`
- New JSONL: `{"actor": {"tool": "claude", "model": "opus"}, ...}` → reads as structured
- Round-trip: `to_dict()` → `from_dict()` preserves all fields
- Missing actor key: defaults to `ActorIdentity.from_legacy("unknown")`

### Subtask T005 – Update _guard_actor_required()

**Purpose**: The transition guard for `planned → claimed` currently checks for non-empty string. Update it to accept `ActorIdentity`.

**Steps**:
1. In `src/specify_cli/status/transitions.py` (~lines 72-76), update:
   ```python
   # Before:
   def _guard_actor_required(actor: str | None) -> tuple[bool, str | None]:
       if not actor or not actor.strip():
           return False, "Transition planned -> claimed requires actor identity"
       return True, None
   
   # After:
   def _guard_actor_required(actor: str | ActorIdentity | None) -> tuple[bool, str | None]:
       if actor is None:
           return False, "Transition planned -> claimed requires actor identity"
       if isinstance(actor, str):
           if not actor.strip():
               return False, "Transition planned -> claimed requires actor identity"
       # ActorIdentity is always valid (validated at construction)
       return True, None
   ```
2. Add import: `from specify_cli.identity import ActorIdentity`
3. Check if `_run_guard()` passes actor correctly — it should already, since it receives from caller.

**Files**: `src/specify_cli/status/transitions.py`
**Parallel?**: Can proceed in parallel with T003/T004 (different file)

## Test Strategy

- Unit tests in `tests/specify_cli/test_identity.py` (NEW):
  - `from_compact()` with 1, 2, 3, 4 parts
  - `from_legacy()` with valid and empty strings
  - `to_dict()` / `from_dict()` round-trip
  - Validation: empty fields, colons in values
- Unit tests in `tests/specify_cli/status/test_models.py` (MODIFY):
  - `StatusEvent.to_dict()` emits structured actor
  - `StatusEvent.from_dict()` handles both str and dict actor
  - Round-trip test with both formats
- Regression: `pytest tests/specify_cli/status/ -v` must pass

## Risks & Mitigations

- **Type cascade**: Changing `actor: str` to `actor: ActorIdentity` may break callers that construct `StatusEvent` with a string actor → search for all `StatusEvent(` constructors and update them
- **JSONL compatibility**: Old files must read without errors → `from_dict()` detection logic handles str vs dict
- **mypy --strict**: Ensure all type annotations are correct for the new type

## Review Guidance

- Verify `ActorIdentity.__post_init__` rejects empty strings and colons
- Verify `from_compact()` handles all edge cases (1-4 parts, >4 parts, empty, whitespace)
- Verify `StatusEvent.from_dict()` correctly detects str vs dict for actor field
- Verify `_guard_actor_required()` still works for both string and ActorIdentity inputs
- Run `pytest tests/specify_cli/status/ -v` — 0 failures expected

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T04:29:01Z – claude-sonnet-4-6 – lane=done – Implementation complete and merged | Done override: History was rebased; branch ancestry tracking not applicable
