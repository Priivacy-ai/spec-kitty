---
work_package_id: WP05
title: Generation Gate & Strictness Policy
lane: "planned"
dependencies: [WP04]
base_branch: 041-mission-glossary-semantic-integrity-WP04
base_commit: 50ac9da5882b14d5dbf0c212e6a6708039ab0a56
created_at: '2026-02-16T15:38:23.226688+00:00'
subtasks: [T021, T022, T023, T024]
shell_pid: "7357"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package Prompt: WP05 -- Generation Gate & Strictness Policy

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-16

**Issue 1**: Event emission failures can bypass blocking. In `src/specify_cli/glossary/middleware.py:421-439`, `emit_generation_blocked_event` is called without protection. If that emitter raises (e.g., downstream transport failure), the middleware will exit before raising `BlockedByConflict`, violating the edge-case requirement to block even when event emission fails. Wrap the emit in `try/except` (log the emission error) and always proceed to raise `BlockedByConflict`.

**Issue 2**: Unknown severities are not treated as HIGH and can crash categorization. In `src/specify_cli/glossary/strictness.py:149-159` and `:162-207`, the code assumes all conflicts use `Severity` enum. A conflict with an unexpected/unknown severity would be treated as non-blocking in MEDIUM mode and would raise `KeyError` in `categorize_conflicts`, contrary to the spec's edge-case guidance to treat unknown severities as HIGH for safety. Add a fallback that maps unrecognized severities to `Severity.HIGH` (and buckets them accordingly) so MEDIUM blocks and categorization stays stable.


## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Implement the generation gate middleware that blocks LLM generation on unresolved high-severity semantic conflicts, with a configurable strictness policy system supporting three modes (off/medium/max) and four-tier precedence resolution (global → mission → step → runtime override).

**Success Criteria**:
1. `off` strictness mode allows all generation to proceed without any glossary checks or blocking.
2. `medium` strictness mode warns on low/medium conflicts but ONLY blocks on high-severity unresolved conflicts.
3. `max` strictness mode blocks generation on ANY unresolved conflict regardless of severity.
4. Strictness precedence is correctly resolved: runtime override > step metadata > mission config > global default.
5. When generation is blocked, GenerationBlockedBySemanticConflict event is emitted with complete conflict details.
6. Strictness policy can be overridden at runtime via `--strictness` CLI flag.
7. Integration tests verify all three modes with various conflict severities and precedence combinations.

## Context & Constraints

**Architecture References**:
- `spec.md` FR-004: System MUST block LLM generation on unresolved high-severity conflicts in medium and max strictness modes
- `spec.md` FR-005: System MUST support 3 strictness modes (off/medium/max)
- `spec.md` FR-006: System MUST apply strictness precedence: global → mission → primitive/step → runtime
- `plan.md` middleware pipeline architecture: GenerationGateMiddleware is layer 3 of 5
- `data-model.md` defines Strictness enum, SemanticConflict severity levels (low/medium/high)
- `contracts/events.md` GenerationBlockedBySemanticConflict event schema

**Dependency Artifacts Available** (from completed WPs):
- WP01 provides `glossary/models.py` with SemanticConflict, Severity enums
- WP04 provides `glossary/conflict.py` with conflict detection and severity scoring
- WP04 provides `glossary/middleware.py` with SemanticCheckMiddleware that populates `context.conflicts`

**Constraints**:
- Python 3.11+ only (per constitution requirement)
- No new external dependencies (strictness is pure Python enum + precedence logic)
- Gate must raise `BlockedByConflict` exception to halt the middleware pipeline
- Event emission must occur BEFORE raising the exception (ensure observability even when blocked)
- Strictness defaults: global default is `medium` (per spec.md SC-001, SC-002)
- Precedence resolution must be deterministic and testable

**Implementation Command**: `spec-kitty implement WP05 --base WP04`

## Subtasks & Detailed Guidance

### T021: Create Strictness Policy Module

**Purpose**: Build the core strictness policy system with enum definitions and four-tier precedence resolution logic.

**Steps**:
1. Create `src/specify_cli/glossary/strictness.py`.

2. Define the Strictness enum:
   ```python
   from enum import StrEnum

   class Strictness(StrEnum):
       """Glossary enforcement strictness levels."""
       OFF = "off"          # No enforcement, generation always proceeds
       MEDIUM = "medium"    # Warn broadly, block only high-severity
       MAX = "max"          # Block any unresolved conflict
   ```

3. Implement precedence resolution function:
   ```python
   def resolve_strictness(
       global_default: Strictness = Strictness.MEDIUM,
       mission_override: Strictness | None = None,
       step_override: Strictness | None = None,
       runtime_override: Strictness | None = None,
   ) -> Strictness:
       """Resolve effective strictness using precedence chain.

       Precedence (highest to lowest):
       1. Runtime override (CLI --strictness flag)
       2. Step metadata (glossary_check_strictness in step definition)
       3. Mission config (mission.yaml default)
       4. Global default (Strictness.MEDIUM)

       Returns:
           The effective strictness mode to apply.
       """
       # Apply precedence: most specific wins
       if runtime_override is not None:
           return runtime_override
       if step_override is not None:
           return step_override
       if mission_override is not None:
           return mission_override
       return global_default
   ```

4. Add helper for loading strictness from config:
   ```python
   from pathlib import Path
   import ruamel.yaml

   def load_global_strictness(repo_root: Path) -> Strictness:
       """Load global strictness from .kittify/config.yaml.

       Returns Strictness.MEDIUM if config file doesn't exist or has no setting.
       """
       config_path = repo_root / ".kittify" / "config.yaml"
       if not config_path.exists():
           return Strictness.MEDIUM

       yaml = ruamel.yaml.YAML(typ="safe")
       try:
           config = yaml.load(config_path)
           if config and "glossary" in config and "strictness" in config["glossary"]:
               value = config["glossary"]["strictness"]
               return Strictness(value)
       except Exception:
           # Invalid config, return default
           pass

       return Strictness.MEDIUM
   ```

5. Export from `glossary/__init__.py`: `Strictness`, `resolve_strictness`, `load_global_strictness`.

**Files**:
- `src/specify_cli/glossary/strictness.py` (new file, ~80 lines)
- `src/specify_cli/glossary/__init__.py` (update exports)

**Validation**:
- [ ] `Strictness` enum has exactly 3 values: OFF, MEDIUM, MAX
- [ ] `resolve_strictness()` with all None returns `Strictness.MEDIUM`
- [ ] Runtime override takes precedence over all others
- [ ] Step override takes precedence over mission and global
- [ ] Mission override takes precedence over global
- [ ] `load_global_strictness()` returns MEDIUM when config doesn't exist
- [ ] `load_global_strictness()` correctly parses valid config value

**Edge Cases**:
- All overrides are None: returns global_default
- Config file is malformed YAML: catch exception, return MEDIUM (fail-safe)
- Config has glossary section but no strictness key: return MEDIUM
- Invalid strictness value in config (e.g., "strict"): catch ValueError from Strictness(value), return MEDIUM
- Multiple precedence levels set: highest priority wins (deterministic)

---

### T022: Implement Gate Decision Logic

**Purpose**: Implement the core blocking logic that determines whether generation should proceed based on strictness mode and conflict severity.

**Steps**:
1. Add the `should_block()` function to `strictness.py`:
   ```python
   from specify_cli.glossary.models import SemanticConflict, Severity

   def should_block(
       strictness: Strictness,
       conflicts: list[SemanticConflict],
   ) -> bool:
       """Determine if generation should be blocked.

       Blocking rules:
       - OFF: Never block (return False regardless of conflicts)
       - MEDIUM: Block only if ANY high-severity conflict exists
       - MAX: Block if ANY conflict exists (regardless of severity)

       Args:
           strictness: The effective strictness mode
           conflicts: List of detected semantic conflicts

       Returns:
           True if generation should be blocked, False otherwise
       """
       if strictness == Strictness.OFF:
           return False

       if strictness == Strictness.MAX:
           return len(conflicts) > 0

       # MEDIUM mode: block only on high-severity
       return any(c.severity == Severity.HIGH for c in conflicts)
   ```

2. Add helper to categorize conflicts by severity:
   ```python
   def categorize_conflicts(
       conflicts: list[SemanticConflict],
   ) -> dict[Severity, list[SemanticConflict]]:
       """Group conflicts by severity level for reporting.

       Returns:
           Dict mapping severity to list of conflicts at that level.
       """
       categorized: dict[Severity, list[SemanticConflict]] = {
           Severity.LOW: [],
           Severity.MEDIUM: [],
           Severity.HIGH: [],
       }

       for conflict in conflicts:
           categorized[conflict.severity].append(conflict)

       return categorized
   ```

3. Create comprehensive test suite in `tests/specify_cli/glossary/test_strictness.py`:
   - Test all 9 combinations: 3 strictness modes × 3 severity levels
   - Test empty conflicts list (should_block always returns False)
   - Test mixed-severity conflicts (MEDIUM should block if ANY are HIGH)
   - Test precedence resolution with all 16 combinations (4 levels × 4 options)

**Files**:
- `src/specify_cli/glossary/strictness.py` (add ~50 lines)
- `tests/specify_cli/glossary/test_strictness.py` (new file, ~200 lines)

**Validation**:
- [ ] OFF mode never blocks (0 conflicts → False, high-severity conflicts → False)
- [ ] MEDIUM mode blocks only on high-severity (low → False, medium → False, high → True)
- [ ] MAX mode blocks on any conflict (low → True, medium → True, high → True)
- [ ] Mixed conflicts in MEDIUM: blocks if ANY are high (2 low + 1 high → True)
- [ ] Empty conflicts list: never blocks regardless of strictness
- [ ] `categorize_conflicts()` correctly groups all conflicts by severity
- [ ] All tests pass with >90% coverage on strictness.py

**Edge Cases**:
- Single high-severity conflict in MEDIUM: blocks
- 100 low-severity conflicts in MEDIUM: does not block
- Single low-severity conflict in MAX: blocks
- Conflicts list is empty: all modes return False
- Conflict with unknown severity (not in enum): handle gracefully (treat as HIGH to be safe)

---

### T023: Implement GenerationGateMiddleware

**Purpose**: Create the middleware component that integrates strictness policy, conflict evaluation, and event emission into the mission primitive pipeline.

**Steps**:
1. Add `GenerationGateMiddleware` class to `src/specify_cli/glossary/middleware.py`:
   ```python
   from specify_cli.glossary.strictness import (
       resolve_strictness,
       should_block,
       Strictness,
   )
   from specify_cli.glossary.models import (
       PrimitiveExecutionContext,
       BlockedByConflict,
   )
   from specify_cli.glossary.events import emit_generation_blocked_event

   class GenerationGateMiddleware:
       """Generation gate that blocks LLM calls on unresolved conflicts."""

       def __init__(
           self,
           repo_root: Path | None = None,
           runtime_override: Strictness | None = None,
       ):
           """Initialize gate with optional runtime override.

           Args:
               repo_root: Path to repository root (for loading config)
               runtime_override: CLI --strictness flag value (highest precedence)
           """
           self.repo_root = repo_root
           self.runtime_override = runtime_override

       def process(
           self,
           context: PrimitiveExecutionContext,
       ) -> PrimitiveExecutionContext:
           """Evaluate conflicts and block if necessary.

           Pipeline position: Layer 3 (after extraction and semantic check)

           Raises:
               BlockedByConflict: When strictness policy requires blocking

           Returns:
               Unmodified context if generation is allowed to proceed
           """
           # Resolve effective strictness
           global_default = Strictness.MEDIUM
           if self.repo_root:
               from specify_cli.glossary.strictness import load_global_strictness
               global_default = load_global_strictness(self.repo_root)

           effective_strictness = resolve_strictness(
               global_default=global_default,
               mission_override=context.mission_strictness,
               step_override=context.step_strictness,
               runtime_override=self.runtime_override,
           )

           # Store effective strictness in context for observability
           context.effective_strictness = effective_strictness

           # Evaluate blocking decision
           if should_block(effective_strictness, context.conflicts):
               # Emit event BEFORE raising exception (ensure observability)
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

       def _format_block_message(
           self,
           conflicts: list[SemanticConflict],
       ) -> str:
           """Format user-facing error message for blocked generation."""
           high_severity = [c for c in conflicts if c.severity == Severity.HIGH]
           conflict_count = len(conflicts)
           high_count = len(high_severity)

           if high_count > 0:
               return (
                   f"Generation blocked: {high_count} high-severity "
                   f"semantic conflict(s) detected (out of {conflict_count} total). "
                   f"Resolve conflicts before proceeding."
               )
           else:
               return (
                   f"Generation blocked: {conflict_count} unresolved "
                   f"semantic conflict(s) detected. Resolve conflicts before proceeding."
               )
   ```

2. Add `BlockedByConflict` exception to `models.py`:
   ```python
   class BlockedByConflict(Exception):
       """Raised when generation gate blocks due to unresolved conflicts."""

       def __init__(
           self,
           conflicts: list[SemanticConflict],
           strictness: Strictness,
           message: str,
       ):
           super().__init__(message)
           self.conflicts = conflicts
           self.strictness = strictness
   ```

3. Add `emit_generation_blocked_event()` stub to `events.py`:
   ```python
   def emit_generation_blocked_event(
       step_id: str,
       mission_id: str,
       conflicts: list[SemanticConflict],
       strictness_mode: Strictness,
   ) -> None:
       """Emit GenerationBlockedBySemanticConflict event.

       This is a stub for WP05. Full implementation in WP08.
       """
       # TODO (WP08): Import from spec_kitty_events.glossary.events
       # For now, just log
       import logging
       logger = logging.getLogger(__name__)
       logger.info(
           f"Generation blocked: {len(conflicts)} conflicts, "
           f"strictness={strictness_mode}, step={step_id}"
       )
   ```

**Files**:
- `src/specify_cli/glossary/middleware.py` (add ~100 lines)
- `src/specify_cli/glossary/models.py` (add BlockedByConflict exception, ~15 lines)
- `src/specify_cli/glossary/events.py` (add stub, ~15 lines)

**Validation**:
- [ ] Middleware initializes with repo_root and runtime_override
- [ ] `process()` correctly resolves effective strictness from all four precedence levels
- [ ] `process()` stores `effective_strictness` in context for downstream observability
- [ ] Blocking raises `BlockedByConflict` with conflicts, strictness, and message
- [ ] Event is emitted BEFORE exception is raised (verify with mock)
- [ ] Non-blocking returns context unchanged
- [ ] Error message includes conflict count and severity breakdown

**Edge Cases**:
- `repo_root` is None: use MEDIUM as global default (no config loading)
- Context has no conflicts: always returns context (never blocks)
- Context has conflicts but strictness is OFF: returns context (never blocks)
- Event emission fails: should still raise BlockedByConflict (don't let event failure prevent blocking)
- Mission and step both have strictness overrides: step wins (higher precedence)

---

### T024: Integration Tests for Gate Behavior

**Purpose**: Write comprehensive integration tests that verify the full generation gate pipeline with realistic primitive execution contexts.

**Steps**:
1. Create `tests/specify_cli/glossary/test_generation_gate.py`:

2. Implement test fixtures:
   ```python
   import pytest
   from pathlib import Path
   from specify_cli.glossary.models import (
       PrimitiveExecutionContext,
       SemanticConflict,
       Severity,
       TermSurface,
       ConflictType,
   )
   from specify_cli.glossary.middleware import GenerationGateMiddleware
   from specify_cli.glossary.strictness import Strictness

   @pytest.fixture
   def mock_context():
       """Create mock primitive execution context."""
       return PrimitiveExecutionContext(
           step_id="specify-step-001",
           mission_id="software-dev",
           mission_strictness=None,
           step_strictness=None,
           conflicts=[],
       )

   @pytest.fixture
   def high_severity_conflict():
       """Create high-severity conflict for testing."""
       return SemanticConflict(
           term=TermSurface(surface_text="workspace"),
           conflict_type=ConflictType.AMBIGUOUS,
           severity=Severity.HIGH,
           confidence=0.9,
           candidate_senses=[],
           context="term 'workspace' has multiple active senses",
       )

   @pytest.fixture
   def low_severity_conflict():
       """Create low-severity conflict for testing."""
       return SemanticConflict(
           term=TermSurface(surface_text="helper"),
           conflict_type=ConflictType.UNKNOWN,
           severity=Severity.LOW,
           confidence=0.3,
           candidate_senses=[],
           context="term 'helper' not found in any scope",
       )
   ```

3. Write comprehensive test cases covering all combinations:

   **Test: OFF mode never blocks**:
   ```python
   def test_off_mode_never_blocks(mock_context, high_severity_conflict):
       """OFF strictness allows generation even with high-severity conflicts."""
       gate = GenerationGateMiddleware(runtime_override=Strictness.OFF)
       mock_context.conflicts = [high_severity_conflict]

       # Should NOT raise
       result = gate.process(mock_context)

       assert result == mock_context
       assert result.effective_strictness == Strictness.OFF
   ```

   **Test: MEDIUM blocks only high-severity**:
   ```python
   def test_medium_blocks_high_severity(mock_context, high_severity_conflict):
       """MEDIUM strictness blocks on high-severity conflicts."""
       gate = GenerationGateMiddleware(runtime_override=Strictness.MEDIUM)
       mock_context.conflicts = [high_severity_conflict]

       with pytest.raises(BlockedByConflict) as exc_info:
           gate.process(mock_context)

       assert exc_info.value.strictness == Strictness.MEDIUM
       assert len(exc_info.value.conflicts) == 1
       assert "high-severity" in str(exc_info.value).lower()

   def test_medium_allows_low_severity(mock_context, low_severity_conflict):
       """MEDIUM strictness allows generation with low-severity conflicts."""
       gate = GenerationGateMiddleware(runtime_override=Strictness.MEDIUM)
       mock_context.conflicts = [low_severity_conflict]

       # Should NOT raise
       result = gate.process(mock_context)
       assert result == mock_context
   ```

   **Test: MAX blocks any conflict**:
   ```python
   def test_max_blocks_any_conflict(mock_context, low_severity_conflict):
       """MAX strictness blocks even on low-severity conflicts."""
       gate = GenerationGateMiddleware(runtime_override=Strictness.MAX)
       mock_context.conflicts = [low_severity_conflict]

       with pytest.raises(BlockedByConflict):
           gate.process(mock_context)
   ```

   **Test: Precedence resolution**:
   ```python
   def test_runtime_override_takes_precedence(mock_context):
       """Runtime override beats all other strictness settings."""
       gate = GenerationGateMiddleware(runtime_override=Strictness.OFF)
       mock_context.mission_strictness = Strictness.MAX
       mock_context.step_strictness = Strictness.MAX

       # Runtime override (OFF) should win
       result = gate.process(mock_context)
       assert result.effective_strictness == Strictness.OFF

   def test_step_override_beats_mission(mock_context):
       """Step strictness beats mission strictness."""
       gate = GenerationGateMiddleware()  # No runtime override
       mock_context.mission_strictness = Strictness.OFF
       mock_context.step_strictness = Strictness.MAX
       mock_context.conflicts = [low_severity_conflict]

       # Step override (MAX) should win, blocking generation
       with pytest.raises(BlockedByConflict):
           gate.process(mock_context)
   ```

   **Test: Event emission before blocking**:
   ```python
   def test_event_emitted_before_blocking(mock_context, high_severity_conflict, monkeypatch):
       """Verify event is emitted BEFORE exception is raised."""
       from specify_cli.glossary import events

       emission_order = []

       def mock_emit(*args, **kwargs):
           emission_order.append("event")

       monkeypatch.setattr(events, "emit_generation_blocked_event", mock_emit)

       gate = GenerationGateMiddleware(runtime_override=Strictness.MEDIUM)
       mock_context.conflicts = [high_severity_conflict]

       try:
           gate.process(mock_context)
       except BlockedByConflict:
           emission_order.append("exception")

       # Event should be emitted before exception
       assert emission_order == ["event", "exception"]
   ```

4. Add edge case tests:
   - Empty conflicts list with MAX strictness (should not block)
   - Mixed-severity conflicts in MEDIUM (blocks if ANY are high)
   - Config file doesn't exist (falls back to MEDIUM)
   - Invalid config file (fails gracefully, uses MEDIUM)
   - All precedence levels are None (uses MEDIUM default)

**Files**:
- `tests/specify_cli/glossary/test_generation_gate.py` (new file, ~350 lines)

**Validation**:
- [ ] All strictness modes tested with all severity levels (9 combinations)
- [ ] All 4 precedence levels tested (runtime, step, mission, global)
- [ ] Event emission ordering verified (before exception)
- [ ] Edge cases covered (empty conflicts, mixed severity, invalid config)
- [ ] Test coverage >95% on GenerationGateMiddleware
- [ ] All tests pass with `pytest tests/specify_cli/glossary/test_generation_gate.py -v`

**Edge Cases**:
- No repo_root provided: global_default stays MEDIUM
- Config file is YAML but has no glossary section: MEDIUM
- Conflicts list has 0 items: never blocks (all modes)
- Conflicts list has 100 items but all low-severity in MEDIUM: doesn't block
- Event emission raises exception: should still proceed to raise BlockedByConflict

---

## Test Strategy

**Unit Tests** (in `tests/specify_cli/glossary/test_strictness.py`):
- Test `resolve_strictness()` with all 16 precedence combinations
- Test `should_block()` with 9 mode×severity combinations
- Test `categorize_conflicts()` with mixed-severity lists
- Test `load_global_strictness()` with various config states

**Integration Tests** (in `tests/specify_cli/glossary/test_generation_gate.py`):
- Test `GenerationGateMiddleware.process()` with realistic contexts
- Verify event emission ordering (event before exception)
- Test precedence resolution with full middleware
- Test all strictness modes with conflicts

**Running Tests**:
```bash
# Unit tests
python -m pytest tests/specify_cli/glossary/test_strictness.py -v

# Integration tests
python -m pytest tests/specify_cli/glossary/test_generation_gate.py -v

# Full glossary test suite
python -m pytest tests/specify_cli/glossary/ -v --cov=src/specify_cli/glossary/strictness --cov=src/specify_cli/glossary/middleware
```

## Definition of Done

- [ ] 4 subtasks complete (T021-T024)
- [ ] `strictness.py`: ~200 lines (enum, precedence, config loading, helpers)
- [ ] `middleware.py`: GenerationGateMiddleware added (~120 lines)
- [ ] `models.py`: BlockedByConflict exception added (~15 lines)
- [ ] `events.py`: emit_generation_blocked_event stub added (~15 lines)
- [ ] Unit tests: ~200 lines covering strictness.py
- [ ] Integration tests: ~350 lines covering GenerationGateMiddleware
- [ ] All tests pass with >90% coverage on strictness.py and middleware.py
- [ ] mypy --strict passes on all new code
- [ ] All three strictness modes work correctly (OFF never blocks, MEDIUM blocks high only, MAX blocks all)
- [ ] Precedence resolution is deterministic and tested

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Precedence logic has subtle bugs | Wrong strictness applied, unexpected blocking/non-blocking | Exhaustive test matrix (16 precedence combinations), property-based testing |
| Event emission failure blocks generation | Loss of observability when blocking occurs | Event emission in try/except, failure logged but doesn't prevent blocking |
| Config file is malformed | Crashes on startup | Graceful fallback to MEDIUM on any config parse error |
| Severity enum changes in future | Blocking logic breaks | Use explicit Severity.HIGH comparison, not enum ordering assumptions |
| Context lacks mission/step strictness fields | AttributeError crashes middleware | Default to None if fields missing, use getattr() with default |

## Review Guidance

When reviewing this WP, verify:
1. **Strictness modes are correct**:
   - OFF: Never blocks (0 conflicts → pass, high conflicts → pass)
   - MEDIUM: Only blocks high-severity (low → pass, medium → pass, high → block)
   - MAX: Always blocks if conflicts exist (low → block, medium → block, high → block)

2. **Precedence is deterministic**:
   - Runtime > Step > Mission > Global (in that order)
   - All 4 levels tested independently
   - When multiple levels set, highest priority wins

3. **Event emission happens before blocking**:
   - Mock/spy on `emit_generation_blocked_event()` to verify call order
   - Event call should appear in test logs BEFORE exception is raised

4. **Config loading is fail-safe**:
   - Missing file → MEDIUM
   - Malformed YAML → MEDIUM
   - Missing key → MEDIUM
   - Never crashes, always falls back to safe default

5. **Error messages are user-friendly**:
   - Include conflict count
   - Include severity breakdown for high-severity blocks
   - Clear actionable guidance ("Resolve conflicts before proceeding")

6. **Test coverage is comprehensive**:
   - 9 combinations tested (3 modes × 3 severity levels)
   - 16 precedence combinations tested (4 levels × 4 settings)
   - Edge cases covered (empty list, mixed severity, config errors)

7. **No fallback mechanisms**:
   - If something fails (config parse, unknown severity), fail clearly
   - Do not silently allow generation when blocking is appropriate

## Activity Log

- 2026-02-16T00:00:00Z -- llm:claude-sonnet-4.5 -- lane=planned -- WP created with comprehensive guidance
- 2026-02-16T15:38:23Z – coordinator – shell_pid=3144 – lane=doing – Assigned agent via workflow command
- 2026-02-16T15:45:43Z – coordinator – shell_pid=3144 – lane=for_review – Ready for review - generation gate implemented with strictness modes (OFF/MEDIUM/MAX), 4-tier precedence resolution, comprehensive tests with 93% coverage
- 2026-02-16T15:46:17Z – codex – shell_pid=7357 – lane=doing – Started review via workflow command
- 2026-02-16T15:49:44Z – codex – shell_pid=7357 – lane=planned – Moved to planned
