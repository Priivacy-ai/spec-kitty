---
work_package_id: WP09
title: Middleware Pipeline Integration
lane: "planned"
dependencies: []
base_branch: 041-mission-glossary-semantic-integrity-WP08
base_commit: ff769aa6a680f4ad197e1d71736da9f8a69eced5
created_at: '2026-02-16T17:25:17.996693+00:00'
subtasks: [T040, T041, T042, T043]
shell_pid: "52237"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package Prompt: WP09 -- Middleware Pipeline Integration

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-16

**Issue 1 (blocking)**: Glossary pipeline is never attached to mission primitives or CLI flows. `attach_glossary_pipeline` is only defined and tested in isolation but not invoked anywhere in the mission executor/commands, so `glossary_check` metadata is ignored during real primitive execution and the pipeline never runs. Wire the attachment into the mission primitive execution hook (and expose the `--strictness` flag) so glossary checks actually execute.

**Issue 2 (blocking)**: `PrimitiveExecutionContext.is_glossary_enabled` mishandles boolean metadata. YAML values such as `glossary_check: false` or `glossary_check: true` are treated as enabled because the method only checks the string "disabled" (primitives.py:104-112). This contradicts FR-020 and the helper `read_glossary_check_metadata`, so steps that explicitly disable glossary checks will still run the pipeline and may block. Treat boolean False (and case-insensitive "disabled") as disabled and add tests.

**Issue 3 (major)**: Interactive clarification is effectively disabled. `create_standard_pipeline` unconditionally passes `prompt_fn=None` regardless of `interaction_mode`, so `ClarificationMiddleware` always defers conflicts and never prompts/resolves them (pipeline.py:131-195). The end-to-end flow (block → clarification → resolution → resume) in the success criteria cannot occur. Respect `interaction_mode` by wiring an interactive prompt function for interactive mode and add a test that a conflict can be resolved and removed.

**Issue 4 (medium)**: Pipeline mutates a shared context object despite the spec constraint that the context be immutable between middleware stages. `PrimitiveExecutionContext` is documented as mutable (primitives.py:16-29) and middleware modifies lists in place, increasing coupling and making checkpoints harder to reason about. Consider returning a new context per stage or documenting the deviation with tests guarding against unintended mutations.


## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Integrate all glossary middleware components into a unified pipeline that attaches to mission primitives via metadata-driven configuration, executes in correct order (extraction → semantic check → generation gate → clarification → resume), handles exceptions gracefully, and emits events at appropriate boundaries.

**Success Criteria**:
1. `GlossaryMiddlewarePipeline` class orchestrates all 5 middleware components in correct order.
2. Pipeline attaches to mission primitives automatically when `glossary_check: enabled` metadata is present.
3. Pipeline executes sequentially with proper context passing between middleware layers.
4. Exceptions (`BlockedByConflict`, `DeferredToAsync`, `AbortResume`) propagate correctly and trigger appropriate handlers.
5. `PrimitiveExecutionContext` is extended with glossary-specific fields (extracted_terms, conflicts, effective_strictness, checkpoint).
6. Metadata-driven attachment reads mission.yaml config and attaches pipeline only when enabled.
7. Integration tests verify full end-to-end flow: specify step → term extraction → conflict detection → generation block → clarification prompt → resolution → resume.

## Context & Constraints

**Architecture References**:
- `plan.md` middleware pipeline architecture: 5-layer sequential execution model
- `contracts/middleware.md` defines GlossaryMiddleware protocol and pipeline composition
- `spec.md` FR-015: System MUST attach glossary checks via metadata in mission config files
- `spec.md` FR-020: Glossary checks enabled by default unless explicitly disabled
- `data-model.md` defines PrimitiveExecutionContext extensions

**Dependency Artifacts Available** (from completed WPs):
- WP01 provides `glossary/models.py` with base entity classes
- WP02 provides `glossary/scope.py` with scope management and seed file loading
- WP03 provides `glossary/extraction.py` with term extraction middleware
- WP04 provides `glossary/conflict.py` with semantic check middleware
- WP05 provides `glossary/strictness.py` with generation gate middleware
- WP06 provides `glossary/clarification.py` with clarification middleware
- WP07 provides `glossary/checkpoint.py` with resume middleware
- WP08 provides `glossary/events.py` with event emission for all canonical events

**Constraints**:
- Python 3.11+ only (per constitution requirement)
- No new external dependencies (all middleware already implemented)
- Pipeline must be composable and testable in isolation
- Context object must be immutable between middleware stages (each middleware returns new context)
- Mission primitive integration must not require changes to mission framework core (use hooks/decorators)
- Performance: full pipeline execution < 200ms for typical step (no LLM in hot path)

**Implementation Command**: `spec-kitty implement WP09 --base WP08`

## Subtasks & Detailed Guidance

### T040: Extend PrimitiveExecutionContext

**Purpose**: Add glossary-specific fields to the primitive execution context to enable middleware communication and state tracking.

**Steps**:
1. Locate or create `src/specify_cli/missions/primitives.py`.

2. Extend `PrimitiveExecutionContext` dataclass:
   ```python
   from dataclasses import dataclass, field
   from typing import Optional, List
   from specify_cli.glossary.models import (
       SemanticConflict,
       ExtractedTerm,
   )
   from specify_cli.glossary.strictness import Strictness
   from specify_cli.glossary.scope import ScopeRef

   @dataclass
   class PrimitiveExecutionContext:
       """Execution context for mission primitives."""
       # Existing fields (preserve all)
       step_id: str
       mission_id: str
       run_id: str
       inputs: dict
       metadata: dict
       config: dict

       # NEW: Glossary-specific fields
       extracted_terms: List[ExtractedTerm] = field(default_factory=list)
       conflicts: List[SemanticConflict] = field(default_factory=list)
       effective_strictness: Optional[Strictness] = None
       checkpoint_token: Optional[str] = None
       scope_refs: List[ScopeRef] = field(default_factory=list)

       # Metadata accessors for strictness precedence
       @property
       def mission_strictness(self) -> Optional[Strictness]:
           """Extract mission-level strictness from config."""
           if "glossary" in self.config and "strictness" in self.config["glossary"]:
               return Strictness(self.config["glossary"]["strictness"])
           return None

       @property
       def step_strictness(self) -> Optional[Strictness]:
           """Extract step-level strictness from metadata."""
           if "glossary_check_strictness" in self.metadata:
               return Strictness(self.metadata["glossary_check_strictness"])
           return None
   ```

3. Add helper method for glossary check enablement:
   ```python
   @dataclass
   class PrimitiveExecutionContext:
       # ... (existing fields)

       def is_glossary_enabled(self) -> bool:
           """Determine if glossary checks are enabled for this step.

           Rules:
           - Explicit metadata `glossary_check: disabled` → False
           - Explicit metadata `glossary_check: enabled` → True
           - Mission config `glossary.enabled: false` → False
           - Default → True (enabled by default per FR-020)
           """
           # Check step metadata first (highest precedence)
           if "glossary_check" in self.metadata:
               return self.metadata["glossary_check"] != "disabled"

           # Check mission config
           if "glossary" in self.config:
               if "enabled" in self.config["glossary"]:
                   return self.config["glossary"]["enabled"] is not False

           # Default: enabled (per FR-020)
           return True
   ```

4. Export from `missions/__init__.py`: `PrimitiveExecutionContext`.

**Files**:
- `src/specify_cli/missions/primitives.py` (extend PrimitiveExecutionContext, ~40 lines added)
- `src/specify_cli/missions/__init__.py` (update exports)

**Validation**:
- [ ] `PrimitiveExecutionContext` has all 5 new glossary fields
- [ ] `extracted_terms` defaults to empty list
- [ ] `conflicts` defaults to empty list
- [ ] `mission_strictness` property correctly extracts from config
- [ ] `step_strictness` property correctly extracts from metadata
- [ ] `is_glossary_enabled()` returns True by default
- [ ] `is_glossary_enabled()` returns False when metadata has `glossary_check: disabled`

**Edge Cases**:
- `config` dict is empty: `mission_strictness` returns None
- `metadata` dict is empty: `step_strictness` returns None, `is_glossary_enabled()` returns True
- Invalid strictness value in config/metadata: catch ValueError, return None
- Both mission and step strictness set: both properties return their respective values (precedence resolved in middleware)
- `glossary_check: null` in metadata: treat as unset, fall back to mission config

---

### T041: Implement GlossaryMiddlewarePipeline

**Purpose**: Create the pipeline orchestrator that composes all middleware components, executes them in order, and handles exception propagation.

**Steps**:
1. Create `src/specify_cli/glossary/pipeline.py`:

2. Implement the base GlossaryMiddleware protocol:
   ```python
   from typing import Protocol
   from specify_cli.missions.primitives import PrimitiveExecutionContext

   class GlossaryMiddleware(Protocol):
       """Base protocol for glossary middleware components."""

       def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
           """Process primitive execution context.

           Args:
               context: Current execution context

           Returns:
               Modified context (may add fields like extracted_terms, conflicts)

           Raises:
               BlockedByConflict: If generation must be blocked
               DeferredToAsync: If clarification deferred
               AbortResume: If resume aborted
           """
           ...
   ```

3. Implement the pipeline orchestrator:
   ```python
   from typing import List
   from specify_cli.glossary.extraction import GlossaryCandidateExtractionMiddleware
   from specify_cli.glossary.conflict import SemanticCheckMiddleware
   from specify_cli.glossary.strictness import GenerationGateMiddleware
   from specify_cli.glossary.clarification import ClarificationMiddleware
   from specify_cli.glossary.checkpoint import ResumeMiddleware
   from specify_cli.glossary.models import BlockedByConflict, DeferredToAsync, AbortResume

   class GlossaryMiddlewarePipeline:
       """Orchestrate glossary middleware components."""

       def __init__(
           self,
           middleware: List[GlossaryMiddleware],
           skip_on_disabled: bool = True,
       ):
           """Initialize pipeline.

           Args:
               middleware: Ordered list of middleware components
               skip_on_disabled: Skip pipeline if glossary checks disabled
           """
           self.middleware = middleware
           self.skip_on_disabled = skip_on_disabled

       def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
           """Execute middleware pipeline.

           Args:
               context: Initial execution context

           Returns:
               Final context (after all middleware)

           Raises:
               BlockedByConflict: If generation gate blocks
               DeferredToAsync: If clarification deferred
               AbortResume: If resume aborted
           """
           # Check if glossary enabled for this step
           if self.skip_on_disabled and not context.is_glossary_enabled():
               return context

           # Execute middleware sequentially
           current_context = context
           for mw in self.middleware:
               try:
                   current_context = mw.process(current_context)
               except (BlockedByConflict, DeferredToAsync, AbortResume):
                   # Expected exceptions - re-raise for caller to handle
                   raise
               except Exception as e:
                   # Unexpected exception - wrap with context
                   raise RuntimeError(
                       f"Glossary middleware {mw.__class__.__name__} failed: {e}"
                   ) from e

           return current_context
   ```

4. Add factory function for standard pipeline:
   ```python
   from pathlib import Path

   def create_standard_pipeline(
       repo_root: Path,
       runtime_strictness: Strictness | None = None,
       interaction_mode: str = "interactive",
   ) -> GlossaryMiddlewarePipeline:
       """Create standard 5-layer glossary middleware pipeline.

       Args:
           repo_root: Path to repository root (for config loading)
           runtime_strictness: CLI --strictness override (highest precedence)
           interaction_mode: "interactive" or "non-interactive"

       Returns:
           Configured pipeline instance
       """
       from specify_cli.glossary.extraction import ExtractionConfig
       from specify_cli.glossary.scope import GlossaryStore
       from specify_cli.glossary.strictness import StrictnessPolicy

       # Load glossary store (with seed files)
       glossary_store = GlossaryStore.from_repo_root(repo_root)

       # Create middleware in order
       middleware = [
           # Layer 1: Extract terms
           GlossaryCandidateExtractionMiddleware(
               extraction_config=ExtractionConfig.from_repo_root(repo_root)
           ),

           # Layer 2: Resolve terms, detect conflicts
           SemanticCheckMiddleware(glossary_store=glossary_store),

           # Layer 3: Block generation on high-severity conflicts
           GenerationGateMiddleware(
               repo_root=repo_root,
               runtime_override=runtime_strictness,
           ),

           # Layer 4: Prompt user for clarification (if blocked)
           ClarificationMiddleware(interaction_mode=interaction_mode),

           # Layer 5: Resume from checkpoint (on retry)
           ResumeMiddleware(repo_root=repo_root),
       ]

       return GlossaryMiddlewarePipeline(middleware=middleware)
   ```

5. Export from `glossary/__init__.py`: `GlossaryMiddlewarePipeline`, `create_standard_pipeline`.

**Files**:
- `src/specify_cli/glossary/pipeline.py` (new file, ~120 lines)
- `src/specify_cli/glossary/__init__.py` (update exports)

**Validation**:
- [ ] `GlossaryMiddlewarePipeline` accepts list of middleware
- [ ] Pipeline executes middleware in order (test with 3 mock middleware)
- [ ] Pipeline skips execution when `is_glossary_enabled()` returns False
- [ ] `BlockedByConflict` exception propagates to caller (not caught)
- [ ] Unexpected exceptions are wrapped with RuntimeError (preserves traceback)
- [ ] `create_standard_pipeline()` returns pipeline with 5 middleware components
- [ ] Standard pipeline has correct order: extraction → check → gate → clarification → resume

**Edge Cases**:
- Empty middleware list: pipeline returns context unchanged
- Middleware raises unexpected exception: wrapped with context, includes middleware class name
- Context is None: pipeline should validate and raise clear error
- Middleware returns None instead of context: validate and raise error
- Multiple exceptions raised in sequence: first exception wins (early exit)

---

### T042: Metadata-Driven Attachment to Mission Primitives

**Purpose**: Implement the mechanism to attach the glossary pipeline to mission primitives automatically when `glossary_check` metadata is enabled.

**Steps**:
1. Locate mission primitive execution hook in `src/specify_cli/missions/` (exact location depends on mission framework architecture).

2. Create `src/specify_cli/glossary/attachment.py`:
   ```python
   from pathlib import Path
   from typing import Callable, Optional
   from specify_cli.missions.primitives import PrimitiveExecutionContext
   from specify_cli.glossary.pipeline import create_standard_pipeline
   from specify_cli.glossary.strictness import Strictness
   from specify_cli.glossary.models import BlockedByConflict, DeferredToAsync

   def attach_glossary_pipeline(
       repo_root: Path,
       runtime_strictness: Optional[Strictness] = None,
       interaction_mode: str = "interactive",
   ) -> Callable[[PrimitiveExecutionContext], PrimitiveExecutionContext]:
       """Create glossary pipeline attachment for mission primitives.

       Returns a decorator/hook that wraps primitive execution.

       Args:
           repo_root: Path to repository root
           runtime_strictness: CLI --strictness override
           interaction_mode: "interactive" or "non-interactive"

       Returns:
           Function that processes context through glossary pipeline
       """
       pipeline = create_standard_pipeline(
           repo_root=repo_root,
           runtime_strictness=runtime_strictness,
           interaction_mode=interaction_mode,
       )

       def process_with_glossary(
           context: PrimitiveExecutionContext
       ) -> PrimitiveExecutionContext:
           """Process context through glossary pipeline.

           Raises:
               BlockedByConflict: Generation blocked, clarification required
               DeferredToAsync: User deferred resolution
           """
           return pipeline.process(context)

       return process_with_glossary
   ```

3. Integrate with mission primitive executor (location depends on mission framework):
   ```python
   # Example integration (adapt to actual mission framework):
   # In src/specify_cli/missions/executor.py or similar

   def execute_primitive(
       primitive_name: str,
       context: PrimitiveExecutionContext,
   ) -> dict:
       """Execute mission primitive with glossary checks.

       Args:
           primitive_name: Name of primitive to execute
           context: Execution context

       Returns:
           Primitive output
       """
       # Attach glossary pipeline
       glossary_processor = attach_glossary_pipeline(
           repo_root=context.repo_root,
           runtime_strictness=context.runtime_strictness,
           interaction_mode=context.interaction_mode,
       )

       try:
           # Pre-process through glossary pipeline
           processed_context = glossary_processor(context)

           # Execute primitive with processed context
           result = _execute_primitive_impl(primitive_name, processed_context)

           return result

       except BlockedByConflict as e:
           # Generation blocked - log and exit
           logger.error(f"Generation blocked by {len(e.conflicts)} conflict(s)")
           for conflict in e.conflicts:
               logger.error(f"  - {conflict.term}: {conflict.conflict_type.value}")
           raise

       except DeferredToAsync as e:
           # Clarification deferred - log and exit
           logger.info(f"Conflict {e.conflict_id} deferred to async resolution")
           raise
   ```

4. Add CLI flag for runtime strictness override in primitive commands:
   ```python
   # Example: In src/specify_cli/cli/commands/specify.py

   @app.command()
   def specify(
       description: str,
       strictness: Optional[str] = typer.Option(
           None,
           "--strictness",
           help="Override glossary strictness mode (off/medium/max)",
       ),
   ):
       """Run specify primitive with glossary checks."""
       runtime_override = Strictness(strictness) if strictness else None

       context = PrimitiveExecutionContext(
           step_id="specify-001",
           mission_id="software-dev",
           runtime_strictness=runtime_override,
           # ... other fields
       )

       execute_primitive("specify", context)
   ```

**Files**:
- `src/specify_cli/glossary/attachment.py` (new file, ~60 lines)
- `src/specify_cli/missions/executor.py` (modify to integrate glossary pipeline, ~30 lines)
- `src/specify_cli/cli/commands/specify.py` (add --strictness flag, ~10 lines per command)

**Validation**:
- [ ] `attach_glossary_pipeline()` returns callable that processes context
- [ ] When `glossary_check: enabled`, pipeline executes before primitive
- [ ] When `glossary_check: disabled`, pipeline is skipped
- [ ] `--strictness` CLI flag overrides config and metadata (highest precedence)
- [ ] `BlockedByConflict` exception halts primitive execution, logs conflicts
- [ ] `DeferredToAsync` exception halts primitive execution, logs conflict_id
- [ ] Pipeline execution time is logged (performance monitoring)

**Edge Cases**:
- Mission config missing glossary section: use defaults (enabled, medium strictness)
- Invalid --strictness value: typer should reject with validation error
- Primitive has no metadata: treated as enabled (default behavior)
- Pipeline raises unexpected exception: logged with full traceback, primitive halts
- Context missing required fields (step_id, mission_id): validate and raise clear error

---

### T043: Full Pipeline Integration Tests

**Purpose**: Write comprehensive integration tests that verify the full end-to-end glossary workflow from term extraction through conflict resolution and resume.

**Steps**:
1. Create `tests/specify_cli/glossary/test_pipeline_integration.py`:

2. Implement comprehensive integration test scenarios:

   **Test: Full happy path (no conflicts)**:
   ```python
   import pytest
   from pathlib import Path
   from specify_cli.glossary.pipeline import create_standard_pipeline
   from specify_cli.missions.primitives import PrimitiveExecutionContext

   def test_pipeline_no_conflicts(tmp_path):
       """Verify pipeline executes successfully when no conflicts detected."""
       # Setup: Create minimal repo structure
       repo_root = tmp_path
       (repo_root / ".kittify").mkdir()

       # Create context with simple inputs (no conflicting terms)
       context = PrimitiveExecutionContext(
           step_id="test-001",
           mission_id="test-mission",
           run_id="run-001",
           inputs={"description": "Simple test with no technical terms"},
           metadata={},
           config={},
       )

       # Execute pipeline
       pipeline = create_standard_pipeline(repo_root)
       result = pipeline.process(context)

       # Verify
       assert result.extracted_terms == []  # No terms extracted
       assert result.conflicts == []
       assert result.effective_strictness == Strictness.MEDIUM  # Default
   ```

   **Test: Conflict detected and blocked**:
   ```python
   def test_pipeline_blocks_on_high_severity_conflict(tmp_path, monkeypatch):
       """Verify generation gate blocks on high-severity unresolved conflict."""
       # Setup: Create repo with team_domain seed file
       repo_root = tmp_path
       glossaries_dir = repo_root / ".kittify" / "glossaries"
       glossaries_dir.mkdir(parents=True)

       # Seed file with ambiguous term "workspace"
       team_domain = glossaries_dir / "team_domain.yaml"
       team_domain.write_text("""
       terms:
         - surface: workspace
           senses:
             - definition: Git worktree directory for a work package
               confidence: 0.9
             - definition: VS Code workspace configuration file
               confidence: 0.7
       """)

       # Create context with ambiguous term
       context = PrimitiveExecutionContext(
           step_id="specify-001",
           mission_id="software-dev",
           run_id="run-001",
           inputs={"description": "The workspace contains implementation files"},
           metadata={"glossary_check": "enabled"},
           config={},
       )

       # Execute pipeline
       pipeline = create_standard_pipeline(repo_root, interaction_mode="non-interactive")

       # Verify: Should raise BlockedByConflict
       from specify_cli.glossary.models import BlockedByConflict
       with pytest.raises(BlockedByConflict) as exc_info:
           pipeline.process(context)

       # Verify conflict details
       assert len(exc_info.value.conflicts) == 1
       conflict = exc_info.value.conflicts[0]
       assert conflict.term == "workspace"
       assert conflict.conflict_type == ConflictType.AMBIGUOUS
       assert conflict.severity == Severity.HIGH
   ```

   **Test: Clarification and resume flow**:
   ```python
   def test_pipeline_clarification_and_resume(tmp_path, monkeypatch):
       """Verify full flow: conflict → clarification → resolution → resume."""
       # Setup (same as previous test)
       repo_root = tmp_path
       # ... (create seed file with ambiguous term)

       context = PrimitiveExecutionContext(
           step_id="specify-001",
           mission_id="software-dev",
           run_id="run-001",
           inputs={"description": "The workspace contains implementation files"},
           metadata={"glossary_check": "enabled"},
           config={},
       )

       # Mock interactive prompt to select candidate #1
       def mock_prompt(message, choices):
           return "1"  # Select first candidate

       monkeypatch.setattr("typer.prompt", mock_prompt)

       # First execution: conflict detected, user resolves
       pipeline = create_standard_pipeline(repo_root, interaction_mode="interactive")

       # Should not raise (clarification middleware resolves interactively)
       result = pipeline.process(context)

       # Verify: Conflict resolved, glossary updated
       assert len(result.conflicts) == 0
       assert result.effective_strictness == Strictness.MEDIUM

       # Verify: GlossaryClarificationResolved event emitted
       # (Check event log for event)
       events = read_events(repo_root)
       resolved_events = [e for e in events if e["event_type"] == "GlossaryClarificationResolved"]
       assert len(resolved_events) == 1
       assert resolved_events[0]["term_surface"] == "workspace"
   ```

   **Test: Strictness precedence (runtime override)**:
   ```python
   def test_pipeline_strictness_precedence(tmp_path):
       """Verify runtime --strictness override takes precedence."""
       # Setup: Mission config has strictness=max
       repo_root = tmp_path
       config_file = repo_root / ".kittify" / "config.yaml"
       config_file.parent.mkdir()
       config_file.write_text("""
       glossary:
         strictness: max
       """)

       context = PrimitiveExecutionContext(
           step_id="test-001",
           mission_id="test-mission",
           run_id="run-001",
           inputs={"description": "Test"},
           metadata={"glossary_check_strictness": "medium"},  # Step override
           config={"glossary": {"strictness": "max"}},  # Mission override
       )

       # Runtime override: OFF (should win)
       pipeline = create_standard_pipeline(
           repo_root,
           runtime_strictness=Strictness.OFF,
       )

       result = pipeline.process(context)

       # Verify: Runtime override wins
       assert result.effective_strictness == Strictness.OFF
   ```

   **Test: Pipeline skips when disabled**:
   ```python
   def test_pipeline_skips_when_disabled(tmp_path):
       """Verify pipeline skips execution when glossary_check: disabled."""
       repo_root = tmp_path
       (repo_root / ".kittify").mkdir()

       context = PrimitiveExecutionContext(
           step_id="test-001",
           mission_id="test-mission",
           run_id="run-001",
           inputs={"description": "Test with technical terms workspace mission"},
           metadata={"glossary_check": "disabled"},  # Explicitly disabled
           config={},
       )

       pipeline = create_standard_pipeline(repo_root)
       result = pipeline.process(context)

       # Verify: No extraction, no conflicts
       assert result.extracted_terms == []
       assert result.conflicts == []
       assert result.effective_strictness is None  # Never resolved
   ```

3. Add performance test:
   ```python
   import time

   def test_pipeline_performance(tmp_path):
       """Verify full pipeline execution < 200ms (constitution requirement)."""
       repo_root = tmp_path
       (repo_root / ".kittify").mkdir()

       context = PrimitiveExecutionContext(
           step_id="perf-001",
           mission_id="perf-mission",
           run_id="run-001",
           inputs={"description": "Test with some technical terms"},
           metadata={},
           config={},
       )

       pipeline = create_standard_pipeline(repo_root)

       start = time.perf_counter()
       result = pipeline.process(context)
       elapsed = time.perf_counter() - start

       # Verify: < 200ms (per constraints)
       assert elapsed < 0.2, f"Pipeline too slow: {elapsed:.3f}s"
   ```

**Files**:
- `tests/specify_cli/glossary/test_pipeline_integration.py` (new file, ~400 lines)

**Validation**:
- [ ] Happy path test passes (no conflicts, pipeline executes fully)
- [ ] Conflict detection test raises BlockedByConflict with correct details
- [ ] Clarification/resume test verifies full resolution flow
- [ ] Strictness precedence test verifies runtime override wins
- [ ] Disabled pipeline test verifies skip behavior
- [ ] Performance test verifies < 200ms execution time
- [ ] All tests pass with `pytest tests/specify_cli/glossary/test_pipeline_integration.py -v`

**Edge Cases**:
- Context with 100+ terms: should still execute < 200ms (deterministic extraction)
- Seed file is malformed YAML: should log warning, skip that scope
- Event log write fails: should not halt pipeline (log error, continue)
- Multiple conflicts in single step: all shown in BlockedByConflict exception
- Resume with changed inputs: should prompt for confirmation (verify with mock)

---

## Test Strategy

**Unit Tests** (in existing test files):
- `test_primitives.py`: Test PrimitiveExecutionContext extensions (properties, helpers)
- `test_pipeline.py`: Test GlossaryMiddlewarePipeline orchestration (mock middleware)
- `test_attachment.py`: Test metadata-driven attachment logic

**Integration Tests** (in `test_pipeline_integration.py`):
- Full pipeline: extraction → check → gate → clarification → resume
- Conflict scenarios: no conflicts, low/medium/high severity, multiple conflicts
- Strictness modes: off, medium, max with various conflict types
- Metadata attachment: enabled, disabled, mission override, step override
- Performance: < 200ms for typical step

**Running Tests**:
```bash
# Unit tests
python -m pytest tests/specify_cli/glossary/test_pipeline.py -v
python -m pytest tests/specify_cli/glossary/test_attachment.py -v

# Integration tests
python -m pytest tests/specify_cli/glossary/test_pipeline_integration.py -v

# Full glossary test suite
python -m pytest tests/specify_cli/glossary/ -v --cov=src/specify_cli/glossary/pipeline --cov=src/specify_cli/glossary/attachment
```

## Definition of Done

- [ ] 4 subtasks complete (T040-T043)
- [ ] `primitives.py`: PrimitiveExecutionContext extended (~40 lines added)
- [ ] `pipeline.py`: GlossaryMiddlewarePipeline implemented (~120 lines)
- [ ] `attachment.py`: Metadata-driven attachment implemented (~60 lines)
- [ ] Mission primitive executor integrated with glossary pipeline (~30 lines modified)
- [ ] CLI commands have --strictness flag (~10 lines per command)
- [ ] Integration tests: ~400 lines covering full pipeline workflow
- [ ] All tests pass with >90% coverage on pipeline.py and attachment.py
- [ ] mypy --strict passes on all new code
- [ ] Performance test verifies < 200ms pipeline execution
- [ ] Full end-to-end scenario works: specify → conflict → clarification → resolution → resume

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mission framework integration point unclear | Cannot attach pipeline automatically | Review mission framework code early, identify primitive execution hook, fallback to manual integration if needed |
| Pipeline execution exceeds 200ms budget | Violates constitution performance requirement | Profile each middleware layer, optimize hotspots (e.g., seed file loading), cache glossary store |
| Exception propagation breaks mission executor | Crashes instead of graceful error handling | Comprehensive exception handling in attachment, log all exceptions with context, provide clear user-facing messages |
| Context object mutation between layers | Breaks immutability assumption, unpredictable behavior | Enforce context immutability via dataclass frozen=True or explicit copying, validate in tests |
| Metadata configuration misread | Pipeline enabled/disabled incorrectly | Extensive unit tests for `is_glossary_enabled()`, validate against all config combinations, log final decision |

## Review Guidance

When reviewing this WP, verify:
1. **Pipeline orchestration is correct**:
   - Middleware executes in order: extraction → check → gate → clarification → resume
   - Context flows correctly between layers (each middleware receives output of previous)
   - Exceptions propagate to top-level caller (not swallowed)

2. **PrimitiveExecutionContext extensions are clean**:
   - All new fields have sensible defaults (empty lists, None)
   - Properties (`mission_strictness`, `step_strictness`) correctly extract from config/metadata
   - `is_glossary_enabled()` follows FR-020 (enabled by default)

3. **Metadata-driven attachment works**:
   - Pipeline attaches when `glossary_check: enabled` (or by default)
   - Pipeline skips when `glossary_check: disabled`
   - `--strictness` CLI flag overrides all other settings (runtime precedence)

4. **Integration tests are comprehensive**:
   - Full end-to-end scenario: term extraction → conflict → resolution → resume
   - All strictness modes tested (off, medium, max)
   - Exception handling verified (BlockedByConflict, DeferredToAsync)

5. **Performance meets requirements**:
   - Pipeline execution < 200ms (measured in test)
   - No LLM calls in hot path (extraction is deterministic)

6. **Error messages are user-friendly**:
   - BlockedByConflict: lists all conflicts with term, type, severity
   - DeferredToAsync: shows conflict_id for tracking
   - Unexpected exceptions: wrapped with context, include middleware name

7. **No fallback mechanisms**:
   - If pipeline fails, it should fail loudly (no silent skips)
   - Exceptions are informative and actionable

## Activity Log

- 2026-02-16T00:00:00Z -- llm:claude-sonnet-4.5 -- lane=planned -- WP created with comprehensive guidance
- 2026-02-16T17:25:18Z – coordinator – shell_pid=49095 – lane=doing – Assigned agent via workflow command
- 2026-02-16T17:33:10Z – coordinator – shell_pid=49095 – lane=for_review – Ready for review: Pipeline orchestrator (5-layer), PrimitiveExecutionContext extensions, metadata-driven attachment, 95 tests at 97% coverage
- 2026-02-16T17:33:51Z – codex – shell_pid=52237 – lane=doing – Started review via workflow command
- 2026-02-16T17:37:46Z – codex – shell_pid=52237 – lane=planned – Moved to planned
