---
work_package_id: WP07
title: Checkpoint/Resume Mechanism
lane: "doing"
dependencies: []
base_branch: 041-mission-glossary-semantic-integrity-WP05
base_commit: e123f4871b4da4d6bae8a55af3fd48f54c7d701e
created_at: '2026-02-16T15:56:00.139625+00:00'
subtasks: [T030, T031, T032, T033, T034, T035]
shell_pid: "20288"
agent: "codex"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package Prompt: WP07 -- Checkpoint/Resume Mechanism

## Review Feedback Status

> **IMPORTANT**: Before starting implementation, check the `review_status` field in this file's frontmatter.
> - If `review_status` is empty or `""`, proceed with implementation as described below.
> - If `review_status` is `"has_feedback"`, read the **Review Feedback** section below FIRST and address all feedback items before continuing.
> - If `review_status` is `"approved"`, this WP has been accepted -- no further implementation needed.

## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Implement the event-sourced checkpoint/resume mechanism that enables cross-session conflict resolution by persisting minimal state before the generation gate, verifying input hash on resume to detect context changes, and restoring execution from the checkpoint cursor.

**Success Criteria**:
1. StepCheckpoint data model captures minimal state (mission/run/step IDs, strictness, scope refs, input hash, cursor, retry token).
2. Checkpoint emission occurs before generation gate evaluation (ensure state saved before blocking).
3. Checkpoint loading retrieves the latest StepCheckpointed event for a given step_id from the event log.
4. Input hash verification computes SHA256 of current inputs and compares with checkpoint.input_hash to detect context changes.
5. Context change prompt confirms with user if input hash differs (per spec.md FR-019).
6. ResumeMiddleware orchestrates loading, verification, context restoration, and resuming from cursor.
7. Integration tests verify full checkpoint → defer → resolve → resume flow with cross-session simulation.

## Context & Constraints

**Architecture References**:
- `spec.md` FR-010: System MUST resume mission step execution from checkpoint after conflict resolution
- `spec.md` FR-011: System MUST store all glossary state in the event log (no side-channel state files)
- `spec.md` FR-019: System MUST request user confirmation before resuming if context has changed materially
- `plan.md` middleware pipeline architecture: ResumeMiddleware is layer 5 of 5
- `plan.md` research Finding 4: Checkpoint/resume via lightweight event sourcing (minimal payload before generation gate)
- `data-model.md` defines StepCheckpoint with input_hash (SHA256), cursor (execution stage), retry_token (UUID)
- `contracts/events.md` StepCheckpointed event schema (CLI-specific, pending Feature 007 approval)

**Dependency Artifacts Available** (from completed WPs):
- WP01 provides `glossary/models.py` with GlossaryScope, Strictness enums
- WP05 provides `glossary/middleware.py` with GenerationGateMiddleware that emits events before blocking
- WP06 provides `glossary/prompts.py` with prompt_context_change_confirmation() for user confirmation

**Constraints**:
- Python 3.11+ only (per constitution requirement)
- No new external dependencies (hashlib, json are stdlib)
- Event log is source of truth (per Feature 007 invariant #6) - no side-channel state files
- Minimal checkpoint payload (< 1KB per checkpoint) to keep event log lightweight
- Input hash must be deterministic (same inputs → same hash every time)
- Cursor values must be well-defined execution stages ("pre_generation_gate", "post_clarification", etc.)

**Implementation Command**: `spec-kitty implement WP07 --base WP05`

## Subtasks & Detailed Guidance

### T030: StepCheckpoint Data Model

**Purpose**: Define the StepCheckpoint data model that captures the minimal state needed to deterministically resume step execution after conflict resolution.

**Steps**:
1. Create `src/specify_cli/glossary/checkpoint.py`.

2. Define ScopeRef value object:
   ```python
   from dataclasses import dataclass
   from specify_cli.glossary.models import GlossaryScope

   @dataclass(frozen=True)
   class ScopeRef:
       """Reference to a specific glossary scope version."""
       scope: GlossaryScope
       version_id: str  # e.g., "v3", "2026-02-16-001"
   ```

3. Define StepCheckpoint data model:
   ```python
   from datetime import datetime
   from specify_cli.glossary.strictness import Strictness

   @dataclass(frozen=True)
   class StepCheckpoint:
       """Minimal state for resuming step execution after conflict resolution."""

       mission_id: str
       run_id: str
       step_id: str
       strictness: Strictness
       scope_refs: list[ScopeRef]
       input_hash: str  # SHA256 of step inputs (deterministic context snapshot)
       cursor: str  # Execution stage (e.g., "pre_generation_gate")
       retry_token: str  # UUID for this checkpoint (idempotency key)
       timestamp: datetime

       def __post_init__(self):
           """Validate checkpoint fields."""
           # Validate hash format (64 hex chars for SHA256)
           if len(self.input_hash) != 64 or not all(c in "0123456789abcdef" for c in self.input_hash):
               raise ValueError(f"Invalid input_hash format: {self.input_hash}")

           # Validate retry token is UUID format (36 chars with hyphens)
           if len(self.retry_token) != 36:
               raise ValueError(f"Invalid retry_token format: {self.retry_token}")

           # Validate cursor is known stage
           valid_cursors = ["pre_generation_gate", "post_clarification", "post_gate"]
           if self.cursor not in valid_cursors:
               raise ValueError(f"Unknown cursor value: {self.cursor}")
   ```

4. Add helper functions for checkpoint creation:
   ```python
   import uuid
   import hashlib
   import json

   def compute_input_hash(inputs: dict) -> str:
       """Compute deterministic SHA256 hash of step inputs.

       Args:
           inputs: Step input dictionary (any JSON-serializable structure)

       Returns:
           64-character hex string (SHA256 hash)
       """
       # Sort keys for determinism
       canonical = json.dumps(inputs, sort_keys=True)
       return hashlib.sha256(canonical.encode()).hexdigest()

   def create_checkpoint(
       mission_id: str,
       run_id: str,
       step_id: str,
       strictness: Strictness,
       scope_refs: list[ScopeRef],
       inputs: dict,
       cursor: str,
   ) -> StepCheckpoint:
       """Create a new checkpoint with computed input hash and fresh retry token.

       Args:
           mission_id: Mission identifier
           run_id: Run instance identifier
           step_id: Step identifier
           strictness: Resolved strictness mode
           scope_refs: Active glossary scope versions
           inputs: Step input dictionary
           cursor: Execution stage (e.g., "pre_generation_gate")

       Returns:
           StepCheckpoint instance ready for event emission
       """
       return StepCheckpoint(
           mission_id=mission_id,
           run_id=run_id,
           step_id=step_id,
           strictness=strictness,
           scope_refs=scope_refs,
           input_hash=compute_input_hash(inputs),
           cursor=cursor,
           retry_token=str(uuid.uuid4()),
           timestamp=datetime.utcnow(),
       )
   ```

5. Export from `glossary/__init__.py`: `StepCheckpoint`, `ScopeRef`, `compute_input_hash`, `create_checkpoint`.

**Files**:
- `src/specify_cli/glossary/checkpoint.py` (new file, ~100 lines)
- `src/specify_cli/glossary/__init__.py` (update exports)

**Validation**:
- [ ] `StepCheckpoint` has all required fields (9 total)
- [ ] `input_hash` is validated as 64 hex chars (SHA256)
- [ ] `retry_token` is validated as 36 chars (UUID)
- [ ] `cursor` is validated against known values
- [ ] `compute_input_hash()` is deterministic (same inputs → same hash)
- [ ] `compute_input_hash()` handles nested dicts and lists correctly
- [ ] `create_checkpoint()` generates fresh UUID for retry_token

**Edge Cases**:
- Inputs contain non-ASCII characters: JSON encoding handles UTF-8 correctly
- Inputs contain floats: JSON serialization is stable (no precision drift)
- Inputs are empty dict: hash is computed correctly (valid edge case)
- Inputs contain None values: JSON serialization handles correctly
- Multiple checkpoints for same step: each has unique retry_token
- Cursor value is invalid: raises ValueError with clear message

---

### T031: Checkpoint Emission

**Purpose**: Implement checkpoint emission logic that creates and emits StepCheckpointed events before the generation gate evaluates conflicts.

**Steps**:
1. Add checkpoint emission function to `events.py`:
   ```python
   from specify_cli.glossary.checkpoint import StepCheckpoint
   import logging

   logger = logging.getLogger(__name__)

   def emit_step_checkpointed(
       checkpoint: StepCheckpoint,
   ) -> None:
       """Emit StepCheckpointed event to event log.

       This is a stub for WP07. Full implementation in WP08 via spec-kitty-events.

       Args:
           checkpoint: Checkpoint state to persist
       """
       # TODO (WP08): Import from spec_kitty_events.glossary.events
       # For now, just log
       logger.info(
           f"Checkpoint emitted: step={checkpoint.step_id}, "
           f"cursor={checkpoint.cursor}, hash={checkpoint.input_hash[:8]}..."
       )
   ```

2. Add checkpoint creation to `GenerationGateMiddleware` in `middleware.py`:
   ```python
   from specify_cli.glossary.checkpoint import create_checkpoint, ScopeRef
   from specify_cli.glossary.events import emit_step_checkpointed

   class GenerationGateMiddleware:
       """Generation gate that blocks LLM calls on unresolved conflicts."""

       # ... (existing __init__ and fields)

       def process(
           self,
           context: PrimitiveExecutionContext,
       ) -> PrimitiveExecutionContext:
           """Evaluate conflicts and block if necessary.

           Enhanced in WP07: Emits checkpoint BEFORE blocking.

           Pipeline position: Layer 3 (after extraction and semantic check)

           Raises:
               BlockedByConflict: When strictness policy requires blocking

           Returns:
               Unmodified context if generation is allowed to proceed
           """
           # Resolve effective strictness (WP05 logic)
           # ... (existing strictness resolution)

           # Evaluate blocking decision (WP05 logic)
           should_block_generation = should_block(
               effective_strictness,
               context.conflicts
           )

           if should_block_generation:
               # CHECKPOINT BEFORE BLOCKING (WP07 addition)
               # Build scope refs from context
               scope_refs = self._build_scope_refs(context)

               # Create checkpoint
               checkpoint = create_checkpoint(
                   mission_id=context.mission_id,
                   run_id=context.run_id,
                   step_id=context.step_id,
                   strictness=effective_strictness,
                   scope_refs=scope_refs,
                   inputs=context.inputs,
                   cursor="pre_generation_gate",
               )

               # Emit checkpoint event FIRST (before blocking)
               emit_step_checkpointed(checkpoint)

               # Store checkpoint in context for downstream middleware
               context.checkpoint = checkpoint

               # Emit generation blocked event (WP05 logic)
               emit_generation_blocked_event(
                   step_id=context.step_id,
                   mission_id=context.mission_id,
                   conflicts=context.conflicts,
                   strictness_mode=effective_strictness,
               )

               # Block generation by raising exception
               raise BlockedByConflict(
                   conflicts=context.conflicts,
                   strictness=effective_strictness,
                   message=self._format_block_message(context.conflicts),
               )

           # Generation allowed - return context unchanged
           return context

       def _build_scope_refs(
           self,
           context: PrimitiveExecutionContext,
       ) -> list[ScopeRef]:
           """Build scope refs from context's active glossary scopes.

           Args:
               context: Execution context with active_scopes field

           Returns:
               List of ScopeRef instances for checkpoint
           """
           if not hasattr(context, "active_scopes"):
               return []

           return [
               ScopeRef(scope=scope, version_id=version)
               for scope, version in context.active_scopes.items()
           ]
   ```

**Files**:
- `src/specify_cli/glossary/events.py` (add ~15 lines)
- `src/specify_cli/glossary/middleware.py` (modify GenerationGateMiddleware, add ~40 lines)

**Validation**:
- [ ] `emit_step_checkpointed()` logs checkpoint details
- [ ] Checkpoint is created before `BlockedByConflict` exception is raised
- [ ] Checkpoint cursor is set to "pre_generation_gate"
- [ ] Checkpoint includes all scope refs from context
- [ ] Checkpoint input_hash is computed from context.inputs
- [ ] Checkpoint is stored in context.checkpoint for downstream access
- [ ] Generation blocked event is emitted after checkpoint event

**Edge Cases**:
- Context has no active_scopes: scope_refs is empty list (valid)
- Checkpoint emission fails (stub logs error): BlockedByConflict is still raised (don't let event failure prevent blocking)
- Multiple conflicts: single checkpoint emitted (not one per conflict)
- Checkpoint event emission is idempotent (same retry_token if retried)

---

### T032: Checkpoint Loading from Event Log

**Purpose**: Implement checkpoint loading logic that retrieves the latest StepCheckpointed event for a given step_id from the event log.

**Steps**:
1. Add checkpoint loading function to `checkpoint.py`:
   ```python
   from pathlib import Path
   from typing import Optional

   def load_checkpoint(
       project_root: Path,
       step_id: str,
   ) -> Optional[StepCheckpoint]:
       """Load latest checkpoint for step_id from event log.

       Reads StepCheckpointed events from event log and returns the most recent
       checkpoint for the given step_id.

       Args:
           project_root: Repository root (contains .kittify/events/)
           step_id: Step identifier to load checkpoint for

       Returns:
           Latest StepCheckpoint for step_id, or None if not found
       """
       # TODO (WP08): Use spec_kitty_events to read event log
       # For now, stub implementation
       import logging
       logger = logging.getLogger(__name__)
       logger.info(f"Loading checkpoint for step={step_id}")

       # Placeholder: return None (no checkpoint found)
       # Real implementation will:
       # 1. Load events from .kittify/events/glossary/
       # 2. Filter for StepCheckpointed events with matching step_id
       # 3. Return latest by timestamp
       return None
   ```

2. Add checkpoint parsing from event payload:
   ```python
   def parse_checkpoint_event(
       event_payload: dict,
   ) -> StepCheckpoint:
       """Parse StepCheckpointed event payload into StepCheckpoint instance.

       Args:
           event_payload: Event dictionary from event log

       Returns:
           Parsed StepCheckpoint instance

       Raises:
           ValueError: If payload is missing required fields or has invalid format
       """
       from datetime import datetime

       try:
           return StepCheckpoint(
               mission_id=event_payload["mission_id"],
               run_id=event_payload["run_id"],
               step_id=event_payload["step_id"],
               strictness=Strictness(event_payload["strictness"]),
               scope_refs=[
                   ScopeRef(
                       scope=GlossaryScope(ref["scope"]),
                       version_id=ref["version_id"]
                   )
                   for ref in event_payload["scope_refs"]
               ],
               input_hash=event_payload["input_hash"],
               cursor=event_payload["cursor"],
               retry_token=event_payload["retry_token"],
               timestamp=datetime.fromisoformat(event_payload["timestamp"]),
           )
       except (KeyError, ValueError) as e:
           raise ValueError(f"Invalid checkpoint event payload: {e}") from e
   ```

**Files**:
- `src/specify_cli/glossary/checkpoint.py` (add ~60 lines)

**Validation**:
- [ ] `load_checkpoint()` returns None if no checkpoint exists for step_id
- [ ] `load_checkpoint()` returns latest checkpoint if multiple exist (sorted by timestamp desc)
- [ ] `parse_checkpoint_event()` correctly reconstructs StepCheckpoint from dict
- [ ] `parse_checkpoint_event()` raises ValueError if required fields missing
- [ ] `parse_checkpoint_event()` handles ISO timestamp parsing correctly
- [ ] Scope refs are parsed correctly (scope enum + version_id)

**Edge Cases**:
- No checkpoints exist for step_id: returns None (not an error)
- Multiple checkpoints with same timestamp: uses first encountered (stable sort)
- Event payload has extra fields: ignored (forward compatibility)
- Event payload has invalid enum value (e.g., strictness="invalid"): raises ValueError with clear message
- Event log directory doesn't exist: returns None (graceful)

---

### T033: Input Hash Verification

**Purpose**: Implement input hash verification logic that detects context changes between checkpoint creation and resume by comparing SHA256 hashes.

**Steps**:
1. Add verification function to `checkpoint.py`:
   ```python
   def verify_input_hash(
       checkpoint: StepCheckpoint,
       current_inputs: dict,
   ) -> tuple[bool, str, str]:
       """Verify current inputs match checkpoint context.

       Args:
           checkpoint: Checkpoint with original input_hash
           current_inputs: Current step inputs

       Returns:
           Tuple of (matches, old_hash, new_hash):
           - matches: True if hashes match, False if context changed
           - old_hash: Original hash from checkpoint (first 16 chars for display)
           - new_hash: Current hash (first 16 chars for display)
       """
       current_hash = compute_input_hash(current_inputs)
       matches = current_hash == checkpoint.input_hash

       return (matches, checkpoint.input_hash[:16], current_hash[:16])
   ```

2. Add context change handling to `checkpoint.py`:
   ```python
   from specify_cli.glossary.prompts import prompt_context_change_confirmation

   def handle_context_change(
       checkpoint: StepCheckpoint,
       current_inputs: dict,
   ) -> bool:
       """Handle input context change between checkpoint and resume.

       Computes current input hash and prompts user for confirmation if
       context has changed materially.

       Args:
           checkpoint: Checkpoint with original input_hash
           current_inputs: Current step inputs

       Returns:
           True if user confirms resumption despite context change,
           False if user declines (abort resume)
       """
       matches, old_hash, new_hash = verify_input_hash(checkpoint, current_inputs)

       if matches:
           # Context unchanged, safe to resume
           return True

       # Context changed - prompt user for confirmation
       return prompt_context_change_confirmation(old_hash, new_hash)
   ```

3. Add detailed hash diff for debugging:
   ```python
   def compute_input_diff(
       old_inputs: dict,
       new_inputs: dict,
   ) -> dict[str, tuple[any, any]]:
       """Compute detailed diff between old and new inputs.

       Useful for debugging context changes.

       Args:
           old_inputs: Original inputs from checkpoint
           new_inputs: Current inputs

       Returns:
           Dict mapping changed keys to (old_value, new_value) tuples
       """
       diff = {}

       # Find changed/removed keys
       for key in old_inputs:
           old_val = old_inputs[key]
           new_val = new_inputs.get(key)

           if new_val != old_val:
               diff[key] = (old_val, new_val)

       # Find added keys
       for key in new_inputs:
           if key not in old_inputs:
               diff[key] = (None, new_inputs[key])

       return diff
   ```

**Files**:
- `src/specify_cli/glossary/checkpoint.py` (add ~50 lines)

**Validation**:
- [ ] `verify_input_hash()` returns (True, _, _) if hashes match
- [ ] `verify_input_hash()` returns (False, old, new) if hashes differ
- [ ] `verify_input_hash()` returns truncated hashes (16 chars) for display
- [ ] `handle_context_change()` calls prompt if hashes differ
- [ ] `handle_context_change()` returns True without prompting if hashes match
- [ ] `compute_input_diff()` detects added, changed, and removed keys
- [ ] Hash comparison is case-sensitive (lowercase hex)

**Edge Cases**:
- Inputs unchanged: hash matches, no prompt (fast path)
- Single character changed in input: hash differs, prompt shown
- Input order changed but content same: hash matches (deterministic sorting)
- New input key added: hash differs, shows as (None, new_value) in diff
- Input value changes type (e.g., "5" → 5): hash differs, diff shows both values
- User declines confirmation: `handle_context_change()` returns False

---

### T034: ResumeMiddleware Implementation

**Purpose**: Create the ResumeMiddleware component that orchestrates checkpoint loading, input hash verification, context restoration, and resuming step execution from the checkpoint cursor.

**Steps**:
1. Add `ResumeMiddleware` class to `src/specify_cli/glossary/middleware.py`:
   ```python
   from pathlib import Path
   from specify_cli.glossary.checkpoint import (
       load_checkpoint,
       handle_context_change,
   )

   class ResumeMiddleware:
       """Checkpoint/resume middleware for cross-session recovery."""

       def __init__(
           self,
           project_root: Path,
       ):
           """Initialize resume middleware.

           Args:
               project_root: Repository root (for event log access)
           """
           self.project_root = project_root

       def process(
           self,
           context: PrimitiveExecutionContext,
       ) -> PrimitiveExecutionContext:
           """Load checkpoint, verify context, restore state, resume execution.

           Pipeline position: Layer 5 (before re-running generation gate on retry)

           Args:
               context: Primitive execution context (may have retry_token set)

           Returns:
               Restored context if checkpoint found and verified,
               original context if no checkpoint (fresh execution)

           Raises:
               AbortResume: If user declines context change confirmation
           """
           # Check if this is a resume attempt (retry_token present)
           if not hasattr(context, "retry_token") or not context.retry_token:
               # Fresh execution, no resume needed
               return context

           # Load checkpoint from event log
           checkpoint = load_checkpoint(self.project_root, context.step_id)

           if checkpoint is None:
               # No checkpoint found, treat as fresh execution
               import logging
               logger = logging.getLogger(__name__)
               logger.warning(
                   f"Checkpoint not found for step={context.step_id}, "
                   f"treating as fresh execution"
               )
               return context

           # Verify input context hasn't changed
           if not handle_context_change(checkpoint, context.inputs):
               # User declined resumption
               raise AbortResume(
                   "User declined resumption due to context change"
               )

           # Restore context from checkpoint
           self._restore_context(context, checkpoint)

           # Mark as resumed for downstream middleware
           context.resumed_from_checkpoint = True

           return context

       def _restore_context(
           self,
           context: PrimitiveExecutionContext,
           checkpoint: StepCheckpoint,
       ) -> None:
           """Restore execution context from checkpoint state.

           Updates context fields with checkpoint values to recreate the
           execution state at the time of checkpoint.

           Args:
               context: Context to restore into
               checkpoint: Checkpoint with saved state
           """
           # Restore strictness
           context.strictness = checkpoint.strictness

           # Restore scope refs
           context.active_scopes = {
               ref.scope: ref.version_id
               for ref in checkpoint.scope_refs
           }

           # Store checkpoint cursor for pipeline resumption
           context.checkpoint_cursor = checkpoint.cursor

           # Store retry token for idempotency
           context.retry_token = checkpoint.retry_token
   ```

2. Add `AbortResume` exception to `models.py`:
   ```python
   class AbortResume(Exception):
       """Raised when user aborts resume due to context change."""

       def __init__(self, message: str):
           super().__init__(message)
   ```

**Files**:
- `src/specify_cli/glossary/middleware.py` (add ~100 lines)
- `src/specify_cli/glossary/models.py` (add ~10 lines)

**Validation**:
- [ ] ResumeMiddleware returns original context if no retry_token present
- [ ] Loads checkpoint via `load_checkpoint()` if retry_token present
- [ ] Returns original context if checkpoint not found (graceful fallback)
- [ ] Calls `handle_context_change()` to verify input hash
- [ ] Raises `AbortResume` if user declines context change confirmation
- [ ] Restores strictness, active_scopes, cursor from checkpoint
- [ ] Sets `context.resumed_from_checkpoint = True` on successful resume
- [ ] Logs warning if checkpoint not found but retry_token present

**Edge Cases**:
- No retry_token: treats as fresh execution (fast path)
- Checkpoint found but hash differs and user confirms: resumes anyway
- Checkpoint found but hash differs and user declines: raises AbortResume
- Multiple checkpoints for step_id: uses latest by timestamp
- Checkpoint has empty scope_refs: context.active_scopes is empty dict (valid)
- Resume after async conflict resolution: checkpoint cursor is "pre_generation_gate", re-runs gate with updated glossary

---

### T035: Checkpoint/Resume Integration Tests

**Purpose**: Write comprehensive integration tests that verify the full checkpoint → defer → resolve → resume workflow with cross-session simulation.

**Steps**:
1. Create `tests/specify_cli/glossary/test_checkpoint_resume.py`:

2. Implement test fixtures:
   ```python
   import pytest
   from unittest.mock import MagicMock, patch
   from pathlib import Path
   from specify_cli.glossary.models import PrimitiveExecutionContext
   from specify_cli.glossary.checkpoint import (
       StepCheckpoint,
       ScopeRef,
       create_checkpoint,
       compute_input_hash,
   )
   from specify_cli.glossary.strictness import Strictness
   from specify_cli.glossary.models import GlossaryScope
   from specify_cli.glossary.middleware import ResumeMiddleware
   from datetime import datetime

   @pytest.fixture
   def sample_inputs():
       """Sample step inputs."""
       return {
           "description": "Implement feature X",
           "requirements": ["req1", "req2"],
       }

   @pytest.fixture
   def sample_checkpoint(sample_inputs):
       """Create sample checkpoint."""
       return create_checkpoint(
           mission_id="041-mission",
           run_id="run-001",
           step_id="step-specify-001",
           strictness=Strictness.MEDIUM,
           scope_refs=[
               ScopeRef(scope=GlossaryScope.TEAM_DOMAIN, version_id="v3")
           ],
           inputs=sample_inputs,
           cursor="pre_generation_gate",
       )

   @pytest.fixture
   def mock_context(sample_inputs):
       """Mock primitive execution context."""
       return PrimitiveExecutionContext(
           step_id="step-specify-001",
           mission_id="041-mission",
           run_id="run-001",
           inputs=sample_inputs,
       )
   ```

3. Write test cases for checkpoint lifecycle:

   **Test: Checkpoint creation**:
   ```python
   def test_create_checkpoint_computes_hash(sample_inputs):
       """Checkpoint creation computes deterministic input hash."""
       checkpoint1 = create_checkpoint(
           mission_id="041-mission",
           run_id="run-001",
           step_id="step-001",
           strictness=Strictness.MEDIUM,
           scope_refs=[],
           inputs=sample_inputs,
           cursor="pre_generation_gate",
       )

       checkpoint2 = create_checkpoint(
           mission_id="041-mission",
           run_id="run-001",
           step_id="step-001",
           strictness=Strictness.MEDIUM,
           scope_refs=[],
           inputs=sample_inputs,
           cursor="pre_generation_gate",
       )

       # Hash is deterministic (same inputs → same hash)
       assert checkpoint1.input_hash == checkpoint2.input_hash

       # Retry token is unique (fresh UUID each time)
       assert checkpoint1.retry_token != checkpoint2.retry_token
   ```

   **Test: Input hash verification**:
   ```python
   from specify_cli.glossary.checkpoint import verify_input_hash

   def test_verify_input_hash_matches(sample_checkpoint, sample_inputs):
       """Input hash verification succeeds when inputs unchanged."""
       matches, old_hash, new_hash = verify_input_hash(
           sample_checkpoint,
           sample_inputs,
       )

       assert matches is True
       assert old_hash == new_hash

   def test_verify_input_hash_detects_change(sample_checkpoint):
       """Input hash verification detects changed inputs."""
       changed_inputs = {
           "description": "Implement feature Y",  # Changed
           "requirements": ["req1", "req2"],
       }

       matches, old_hash, new_hash = verify_input_hash(
           sample_checkpoint,
           changed_inputs,
       )

       assert matches is False
       assert old_hash != new_hash
   ```

   **Test: Resume middleware**:
   ```python
   @patch("specify_cli.glossary.checkpoint.load_checkpoint")
   @patch("specify_cli.glossary.checkpoint.handle_context_change", return_value=True)
   def test_resume_middleware_restores_context(
       mock_handle_change,
       mock_load,
       mock_context,
       sample_checkpoint,
       tmp_path,
   ):
       """ResumeMiddleware restores context from checkpoint."""
       # Mock checkpoint loading
       mock_load.return_value = sample_checkpoint

       # Set retry token to trigger resume
       mock_context.retry_token = sample_checkpoint.retry_token

       middleware = ResumeMiddleware(project_root=tmp_path)
       result = middleware.process(mock_context)

       # Verify context restored
       assert result.strictness == Strictness.MEDIUM
       assert GlossaryScope.TEAM_DOMAIN in result.active_scopes
       assert result.checkpoint_cursor == "pre_generation_gate"
       assert result.resumed_from_checkpoint is True

       # Verify handle_context_change called
       assert mock_handle_change.call_count == 1
   ```

   **Test: Context change abort**:
   ```python
   from specify_cli.glossary.models import AbortResume

   @patch("specify_cli.glossary.checkpoint.load_checkpoint")
   @patch("specify_cli.glossary.checkpoint.handle_context_change", return_value=False)
   def test_resume_aborts_on_context_change_decline(
       mock_handle_change,
       mock_load,
       mock_context,
       sample_checkpoint,
       tmp_path,
   ):
       """ResumeMiddleware raises AbortResume if user declines context change."""
       # Mock checkpoint loading
       mock_load.return_value = sample_checkpoint

       # Set retry token to trigger resume
       mock_context.retry_token = sample_checkpoint.retry_token

       middleware = ResumeMiddleware(project_root=tmp_path)

       with pytest.raises(AbortResume) as exc_info:
           middleware.process(mock_context)

       assert "context change" in str(exc_info.value).lower()
   ```

   **Test: No checkpoint found**:
   ```python
   @patch("specify_cli.glossary.checkpoint.load_checkpoint", return_value=None)
   def test_resume_graceful_when_no_checkpoint(
       mock_load,
       mock_context,
       tmp_path,
   ):
       """ResumeMiddleware treats missing checkpoint as fresh execution."""
       # Set retry token to trigger resume attempt
       mock_context.retry_token = "some-uuid"

       middleware = ResumeMiddleware(project_root=tmp_path)
       result = middleware.process(mock_context)

       # Returns original context unchanged
       assert result == mock_context
       assert not hasattr(result, "resumed_from_checkpoint")
   ```

4. Add edge case tests:
   - Checkpoint with empty scope_refs
   - Multiple checkpoints (latest selected)
   - Hash verification with nested dicts
   - Resume without retry_token (fast path)
   - Invalid checkpoint payload (parsing error)

**Files**:
- `tests/specify_cli/glossary/test_checkpoint_resume.py` (new file, ~350 lines)

**Validation**:
- [ ] Checkpoint creation is deterministic (same inputs → same hash)
- [ ] Retry tokens are unique (fresh UUID each checkpoint)
- [ ] Input hash verification correctly detects changes
- [ ] ResumeMiddleware restores context from checkpoint
- [ ] AbortResume raised when user declines context change
- [ ] Missing checkpoint treated as fresh execution
- [ ] Test coverage >95% on checkpoint.py and ResumeMiddleware

**Edge Cases**:
- Inputs unchanged: hash matches, no prompt
- Single char changed: hash differs, prompt shown
- User confirms despite context change: resume proceeds
- User declines: AbortResume raised, execution halts
- No retry_token: resume skipped (fast path)
- Checkpoint not found but retry_token present: logs warning, continues as fresh

---

## Test Strategy

**Unit Tests** (in `tests/specify_cli/glossary/test_checkpoint.py`):
- Test `compute_input_hash()` with various input structures
- Test `StepCheckpoint` validation (hash format, retry token format, cursor values)
- Test `create_checkpoint()` creates valid checkpoints
- Test `verify_input_hash()` with matching and non-matching inputs
- Test `handle_context_change()` with user confirmation scenarios

**Integration Tests** (in `tests/specify_cli/glossary/test_checkpoint_resume.py`):
- Test full `ResumeMiddleware.process()` workflow
- Mock `load_checkpoint()` to simulate event log reads
- Test checkpoint emission in `GenerationGateMiddleware`
- Test cross-session resume (checkpoint → defer → resolve → resume)

**Running Tests**:
```bash
# Unit tests
python -m pytest tests/specify_cli/glossary/test_checkpoint.py -v

# Integration tests
python -m pytest tests/specify_cli/glossary/test_checkpoint_resume.py -v

# Full glossary test suite
python -m pytest tests/specify_cli/glossary/ -v --cov=src/specify_cli/glossary
```

## Definition of Done

- [ ] 6 subtasks complete (T030-T035)
- [ ] `checkpoint.py`: ~210 lines (models, hash computation, verification, loading)
- [ ] `middleware.py`: ResumeMiddleware added (~100 lines), GenerationGateMiddleware enhanced (~40 lines)
- [ ] `events.py`: emit_step_checkpointed stub added (~15 lines)
- [ ] `models.py`: AbortResume exception added (~10 lines)
- [ ] Unit tests: ~150 lines covering checkpoint module
- [ ] Integration tests: ~350 lines covering full resume workflow
- [ ] All tests pass with >95% coverage on checkpoint and resume modules
- [ ] mypy --strict passes on all new code
- [ ] Input hash computation is deterministic (same inputs → same hash)
- [ ] Context change prompt works correctly (shows hash diff, user confirms/declines)
- [ ] Cross-session resume verified with simulated event log

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Input hash is non-deterministic | Context changes not detected reliably | Use json.dumps with sort_keys=True, test extensively with various input types |
| Checkpoint payload is too large | Event log bloated, slow to read | Keep checkpoint minimal (<1KB), only essential fields (no full glossary state) |
| Context change prompt is too aggressive | User friction on benign changes | Provide detailed hash diff for debugging, allow user override |
| Event log reads are slow | Resume latency unacceptable | Use efficient event filtering (index by step_id if possible), cache latest checkpoint per step |
| User accidentally confirms context change | Unexpected behavior after resume | Show clear warning with hash diff, default to "No" (safer) |
| Multiple agents resume simultaneously | Race condition on event log | Use retry_token as idempotency key, last-write-wins for glossary updates |

## Review Guidance

When reviewing this WP, verify:
1. **Checkpoint state is minimal**:
   - Only essential fields (mission/run/step IDs, strictness, scope refs, input hash, cursor, retry token)
   - No full glossary snapshot (violates "minimal payload" requirement)
   - Payload size <1KB (verify with sample checkpoint serialization)

2. **Input hash is deterministic**:
   - `json.dumps` uses `sort_keys=True` (deterministic key ordering)
   - SHA256 computation is stable across runs
   - Test with nested dicts, lists, various types (str, int, float, bool, None)

3. **Context change detection works**:
   - `verify_input_hash()` correctly detects any input change
   - Prompt shows clear hash diff (first 16 chars of old and new)
   - User can confirm or decline (default to decline for safety)

4. **Resume restores state correctly**:
   - ResumeMiddleware restores strictness, active_scopes, cursor
   - `context.resumed_from_checkpoint` flag set (downstream middleware can detect)
   - Original context returned unchanged if no checkpoint found (graceful fallback)

5. **Event emission ordering is correct**:
   - Checkpoint emitted BEFORE BlockedByConflict exception
   - Generation blocked event emitted AFTER checkpoint
   - Events are append-only (no updates or deletes)

6. **Error handling is robust**:
   - Missing checkpoint: logs warning, continues as fresh execution
   - Invalid checkpoint payload: raises ValueError with clear message
   - User declines context change: raises AbortResume, execution halts
   - Event emission failure: logs error, continues (don't block checkpoint)

7. **No fallback mechanisms**:
   - If checkpoint load fails, fail clearly (don't silently continue)
   - If user declines context change, halt (don't retry or bypass)

## Activity Log

- 2026-02-16T00:00:00Z -- llm:claude-sonnet-4.5 -- lane=planned -- WP created with comprehensive guidance
- 2026-02-16T15:56:00Z – coordinator – shell_pid=13209 – lane=doing – Assigned agent via workflow command
- 2026-02-16T16:07:16Z – coordinator – shell_pid=13209 – lane=for_review – Ready for review: checkpoint/resume mechanism with 91 tests, 95% coverage on checkpoint module, 345/345 glossary tests passing
- 2026-02-16T16:10:51Z – codex – shell_pid=20288 – lane=doing – Started review via workflow command
