---
work_package_id: WP03
title: Emission Pipeline and Orchestrator Integration
lane: "done"
dependencies: [WP01]
base_branch: feature/doctrine-kitty-2x
base_commit: a3505ae86accdeb8991e664f58da7942909cc00f
created_at: '2026-02-15T20:23:42.008223+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Core Integration
assignee: ''
agent: copilot
shell_pid: '503502'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T19:43:21Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Emission Pipeline and Orchestrator Integration

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

Depends on WP01 (SimpleJsonStore).

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Implement `emit_execution_event()` — the single entry point for recording agent invocations
- Wire Lamport clock for causal ordering of execution events
- Enrich `InvocationResult` with optional telemetry fields (`model`, `input_tokens`, `output_tokens`, `cost_usd`)
- Hook emission into orchestrator after both implementation and review invocations
- Emission NEVER blocks or raises — fire-and-forget with `logger.warning` on failure
- Existing orchestrator tests continue to pass without modification
- 90%+ coverage for new emission code

## Context & Constraints

- **Spec**: FR-004 through FR-007 (emission requirements)
- **Plan**: AD-4 (enrich InvocationResult), AD-5 (fire-and-forget)
- **Data model**: ExecutionEvent payload schema
- **Research**: R4 (orchestrator integration hook point)
- **InvocationResult**: `src/specify_cli/orchestrator/agents/base.py` — existing dataclass to enrich
- **Orchestrator hooks**: `src/specify_cli/orchestrator/integration.py` — `process_wp_implementation()` and `process_wp_review()`
- **Existing pattern**: `emit_wp_assigned()` in integration.py uses try/except with logger.warning — follow this pattern
- **LamportClock**: `src/specify_cli/spec_kitty_events/clock.py` — `LamportClock(node_id, storage)`
- **ClockStorage ABC**: `src/specify_cli/spec_kitty_events/storage.py` — needs a file-backed implementation for clock persistence

## Subtasks & Detailed Guidance

### Subtask T011 – Create emit_execution_event()

- **Purpose**: Single entry point for recording agent invocations to the telemetry JSONL.
- **Steps**:
  1. Create `src/specify_cli/telemetry/emit.py`
  2. Implement:

     ```python
     def emit_execution_event(
         feature_dir: Path,
         feature_slug: str,
         wp_id: str,
         agent: str,
         role: str,  # "implementer" or "reviewer"
         *,
         model: str | None = None,
         input_tokens: int | None = None,
         output_tokens: int | None = None,
         cost_usd: float | None = None,
         duration_ms: int = 0,
         success: bool = True,
         error: str | None = None,
         exit_code: int = 0,
         node_id: str = "cli",
     ) -> None:
     ```

  3. Inside the function:
     - Generate a ULID for `event_id` (use `python-ulid`: `from ulid import ULID; str(ULID())`)
     - Get current UTC timestamp: `datetime.now(timezone.utc)`
     - Tick the Lamport clock (see T012)
     - Construct `Event` from `spec_kitty_events.models`:

       ```python
       event = Event(
           event_id=str(ULID()),
           event_type="ExecutionEvent",
           aggregate_id=feature_slug,
           timestamp=datetime.now(timezone.utc),
           node_id=node_id,
           lamport_clock=clock.tick(),
           causation_id=None,
           payload={
               "wp_id": wp_id,
               "agent": agent,
               "role": role,
               "model": model,
               "input_tokens": input_tokens,
               "output_tokens": output_tokens,
               "cost_usd": cost_usd,
               "duration_ms": duration_ms,
               "success": success,
               "error": error,
               "exit_code": exit_code,
           },
       )
       ```

     - Save via `SimpleJsonStore(feature_dir / "execution.events.jsonl").save_event(event)`
- **Files**: `src/specify_cli/telemetry/emit.py` (new, ~70 lines)
- **Notes**: The `Event` constructor validates via Pydantic — invalid data raises `ValidationError`. This is caught by the fire-and-forget wrapper (T013).

### Subtask T012 – Wire Lamport clock into emission

- **Purpose**: Ensure execution events have monotonically increasing logical clock values for causal ordering.
- **Steps**:
  1. Create a simple file-backed `ClockStorage` implementation in `telemetry/emit.py` (or `telemetry/clock.py` if cleaner):

     ```python
     class FileClockStorage(ClockStorage):
         def __init__(self, file_path: Path) -> None:
             self._file_path = file_path

         def load(self, node_id: str) -> int:
             if not self._file_path.exists():
                 return 0
             try:
                 data = json.loads(self._file_path.read_text(encoding="utf-8"))
                 return data.get(node_id, 0)
             except (json.JSONDecodeError, OSError):
                 return 0  # Corrupted clock file — reset to 0

         def save(self, node_id: str, clock_value: int) -> None:
             data = {}
             if self._file_path.exists():
                 try:
                     data = json.loads(self._file_path.read_text(encoding="utf-8"))
                 except (json.JSONDecodeError, OSError):
                     pass
             data[node_id] = clock_value
             self._file_path.parent.mkdir(parents=True, exist_ok=True)
             self._file_path.write_text(
                 json.dumps(data, sort_keys=True), encoding="utf-8"
             )
     ```

  2. In `emit_execution_event()`, instantiate:

     ```python
     clock_storage = FileClockStorage(feature_dir / ".telemetry-clock.json")
     clock = LamportClock(node_id=node_id, storage=clock_storage)
     ```

  3. Call `clock.tick()` to get the next clock value for the event
  4. Clock file location: per-feature `<feature_dir>/.telemetry-clock.json`
- **Files**: `src/specify_cli/telemetry/emit.py` (modify, ~40 lines added)
- **Notes**: The `LamportClock.__init__` calls `storage.load(node_id)` to resume from previous value. Each `tick()` increments, persists, and returns the new value. If the clock file is corrupted, resetting to 0 is safe — events are still dedupable by `event_id`, and the ULID provides temporal ordering as a fallback.

### Subtask T013 – Add fire-and-forget error handling

- **Purpose**: Ensure telemetry emission never blocks or crashes the orchestrator pipeline.
- **Steps**:
  1. Wrap the entire body of `emit_execution_event()` in try/except:

     ```python
     def emit_execution_event(...) -> None:
         try:
             # ... event construction and save ...
         except Exception as e:
             logger.warning("Telemetry emission failed for %s/%s: %s", feature_slug, wp_id, e)
     ```

  2. Use `logging.getLogger(__name__)` for the logger
  3. The function returns `None` in all cases — no return value, no exception propagation
  4. Log at WARNING level (not ERROR) — telemetry failure is degraded, not broken
- **Files**: `src/specify_cli/telemetry/emit.py` (modify)
- **Notes**: This matches the pattern in `integration.py` where `emit_wp_assigned()` is wrapped in try/except. The spec (FR-007) explicitly requires this behavior.

### Subtask T014 – Write unit tests for emission

- **Purpose**: Verify event construction, clock wiring, and error swallowing.
- **Steps**:
  1. Create `tests/specify_cli/telemetry/test_emit.py`
  2. Test cases:
     - **test_emit_creates_event**: Call `emit_execution_event()` with all fields, read JSONL, verify event structure
     - **test_emit_minimal_fields**: Call with only required fields (nulls for optional), verify event saved
     - **test_emit_increments_clock**: Emit 3 events, verify lamport_clock is 1, 2, 3
     - **test_emit_clock_persists**: Emit event, create new store instance, emit again, verify clock continues from 2
     - **test_emit_swallows_errors**: Patch `SimpleJsonStore.save_event` to raise, verify no exception propagated, verify warning logged
     - **test_emit_creates_dirs**: Emit to non-existent feature dir, verify dirs created
  3. Use `tmp_path` for all paths
  4. Use `caplog` fixture to verify warning messages
- **Files**: `tests/specify_cli/telemetry/test_emit.py` (new, ~100 lines)

### Subtask T015 – Add telemetry fields to InvocationResult

- **Purpose**: Enrich the orchestrator's invocation result with optional model and token data.
- **Steps**:
  1. Open `src/specify_cli/orchestrator/agents/base.py`
  2. Add optional fields to the `InvocationResult` dataclass:

     ```python
     @dataclass
     class InvocationResult:
         success: bool
         exit_code: int
         stdout: str
         stderr: str
         duration_seconds: float
         files_modified: list[str] = field(default_factory=list)
         commits_made: list[str] = field(default_factory=list)
         errors: list[str] = field(default_factory=list)
         warnings: list[str] = field(default_factory=list)
         # Telemetry fields (populated by agent invokers when available)
         model: str | None = None
         input_tokens: int | None = None
         output_tokens: int | None = None
         cost_usd: float | None = None
     ```

  3. Verify all existing code that constructs `InvocationResult` still works (new fields have defaults)
  4. Run existing orchestrator tests to confirm no breakage
- **Files**: `src/specify_cli/orchestrator/agents/base.py` (modify, 4 lines added)
- **Notes**: This is fully backward-compatible. Existing code constructs `InvocationResult` with positional or keyword args for the original fields — new optional fields default to `None`. No existing code needs modification.

### Subtask T016 – Add emission hook after process_wp_implementation()

- **Purpose**: Record telemetry after each WP implementation invocation.
- **Steps**:
  1. Open `src/specify_cli/orchestrator/integration.py`
  2. Locate where `execute_with_logging()` returns in `process_wp_implementation()` (after the result is obtained, before status transitions)
  3. Add emission call:

     ```python
     # Telemetry emission (fire-and-forget)
     try:
         from specify_cli.telemetry.emit import emit_execution_event
         emit_execution_event(
             feature_dir=feature_dir,
             feature_slug=feature_slug,
             wp_id=wp_id,
             agent=agent_id,
             role="implementer",
             model=result.model,
             input_tokens=result.input_tokens,
             output_tokens=result.output_tokens,
             cost_usd=result.cost_usd,
             duration_ms=int(result.duration_seconds * 1000),
             success=result.success,
             error=result.errors[0] if result.errors else None,
             exit_code=result.exit_code,
         )
     except Exception as e:
         logger.warning("Telemetry emission failed for %s: %s", wp_id, e)
     ```

  4. The outer try/except catches import errors or any unexpected failure — double safety net
- **Files**: `src/specify_cli/orchestrator/integration.py` (modify, ~15 lines added)
- **Parallel?**: Yes — independent from T017 (different function).
- **Notes**: The lazy import (`from specify_cli.telemetry.emit import ...`) inside the try block ensures the orchestrator works even if the telemetry package has import issues.

### Subtask T017 – Add emission hook after process_wp_review()

- **Purpose**: Record telemetry after each WP review invocation.
- **Steps**:
  1. In `src/specify_cli/orchestrator/integration.py`, locate `process_wp_review()`
  2. Add the same emission pattern as T016, with `role="reviewer"`:

     ```python
     try:
         from specify_cli.telemetry.emit import emit_execution_event
         emit_execution_event(
             feature_dir=feature_dir,
             feature_slug=feature_slug,
             wp_id=wp_id,
             agent=agent_id,
             role="reviewer",
             model=result.model,
             input_tokens=result.input_tokens,
             output_tokens=result.output_tokens,
             cost_usd=result.cost_usd,
             duration_ms=int(result.duration_seconds * 1000),
             success=result.success,
             error=result.errors[0] if result.errors else None,
             exit_code=result.exit_code,
         )
     except Exception as e:
         logger.warning("Telemetry emission failed for %s review: %s", wp_id, e)
     ```

- **Files**: `src/specify_cli/orchestrator/integration.py` (modify, ~15 lines added)
- **Parallel?**: Yes — independent from T016 (different function).

### Subtask T018 – Write integration tests for orchestrator telemetry

- **Purpose**: Verify end-to-end: orchestrator invocation → telemetry event in JSONL.
- **Steps**:
  1. Create `tests/specify_cli/orchestrator/test_telemetry_integration.py`
  2. Test cases:
     - **test_implementation_emits_event**: Mock `execute_with_logging` to return an `InvocationResult` with telemetry fields populated. Call `process_wp_implementation()`. Verify `execution.events.jsonl` contains an ExecutionEvent with `role="implementer"`.
     - **test_review_emits_event**: Same pattern for `process_wp_review()` with `role="reviewer"`.
     - **test_emission_failure_does_not_block**: Patch `emit_execution_event` to raise. Run implementation. Verify orchestrator continues without error.
     - **test_missing_telemetry_fields**: `InvocationResult` with all telemetry fields as None. Verify event still emitted with null payload values.
  3. Use extensive mocking — do NOT invoke real agents
  4. Use `tmp_path` for feature directory
- **Files**: `tests/specify_cli/orchestrator/test_telemetry_integration.py` (new, ~120 lines)
- **Notes**: The orchestrator's `process_wp_implementation` has many dependencies (state management, git operations). Mock heavily — focus only on verifying the telemetry hook fires and captures the right data.

## Risks & Mitigations

- **Breaking existing orchestrator tests**: `InvocationResult` changes are additive. Run the full orchestrator test suite after T015 to catch any unexpected failures.
- **Import cycle**: `telemetry.emit` imports from `spec_kitty_events` and `telemetry.store`. The orchestrator imports from `telemetry.emit`. No cycle — all imports flow one direction.
- **Clock file contention**: If multiple agents run in parallel (different worktrees), they write to different feature dirs — no contention. Same-feature parallel writes are not supported (single-process CLI).

## Review Guidance

- Verify `InvocationResult` changes don't break existing test suite
- Verify emission hooks are in the correct location (after invocation, before status transitions)
- Verify fire-and-forget: patch `emit_execution_event` to raise, confirm orchestrator continues
- Verify Lamport clock increments monotonically across multiple emissions
- Verify event payload matches the schema in `data-model.md`
- Run `mypy --strict` on modified files

## Activity Log

- 2026-02-15T19:43:21Z – system – lane=planned – Prompt created.
- 2026-02-15T20:23:42Z – copilot – shell_pid=503502 – lane=doing – Assigned agent via workflow command
- 2026-02-15T20:55:29Z – copilot – shell_pid=503502 – lane=for_review – Implementation complete: emit_execution_event, FileClockStorage, InvocationResult enrichment, orchestrator hooks, 15 tests
- 2026-02-15T21:16:05Z – copilot – shell_pid=503502 – lane=done – Review passed: clock race condition fixed via per-WP node_id, 26 tests pass
