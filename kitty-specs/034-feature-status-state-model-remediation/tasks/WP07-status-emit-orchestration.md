---
work_package_id: WP07
title: Status Emit Orchestration
lane: "doing"
dependencies:
- WP02
base_branch: 2.x
base_commit: a81e80bda571a3156ad85fe5564a4a5d0edad983
created_at: '2026-02-08T14:48:38.002527+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
phase: Phase 1 - Canonical Log
assignee: ''
agent: ''
shell_pid: "50636"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 -- Status Emit Orchestration

## Review Feedback Status

> **IMPORTANT**: Before starting implementation, check the `review_status` field in this file's frontmatter.
> - If `review_status` is empty or `""`, proceed with implementation as described below.
> - If `review_status` is `"has_feedback"`, read the **Review Feedback** section below FIRST and address all feedback items before continuing.
> - If `review_status` is `"approved"`, this WP has been accepted -- no further implementation needed.

## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Create the central orchestration pipeline that is the single entry point for ALL state changes in the canonical status model. The pipeline validates a transition, appends an event to the JSONL log, materializes a status snapshot, updates legacy compatibility views, and emits SaaS telemetry.

**Success Criteria**:
1. A single function call (`emit_status_transition()`) performs the entire pipeline end-to-end.
2. After a successful emit, `status.events.jsonl` contains the new event, `status.json` reflects the updated state, and WP frontmatter lanes match.
3. SaaS telemetry is emitted when the sync module is available; failures do not block canonical persistence.
4. Invalid transitions are rejected BEFORE any data is persisted.
5. Force transitions require actor and reason; done transitions require evidence.
6. Integration tests verify the full pipeline from emit through to every downstream artifact.

## Context & Constraints

**Architecture References**:
- `plan.md` AD-6 defines the unified fan-out architecture for this orchestration.
- `plan.md` AD-8 shows how `move_task()` will delegate to this pipeline (implemented in WP09).
- `data-model.md` defines StatusEvent, StatusSnapshot, DoneEvidence schemas.
- `contracts/event-schema.json` is the JSON Schema for events.
- `contracts/snapshot-schema.json` is the JSON Schema for materialized snapshots.

**Dependency Artifacts Available** (from completed WPs):
- WP02 provides `status/store.py` with `append_event()` and `read_events()`.
- WP03 provides `status/reducer.py` with `reduce()` and `materialize()`.
- WP04 provides `status/phase.py` with `resolve_phase()`.
- WP06 provides `status/legacy_bridge.py` with `update_frontmatter_views()` and `update_tasks_md_views()`.

**Constraints**:
- Python 3.11+ only. No legacy fallbacks.
- No new external dependencies.
- SaaS sync import must use try/except to handle 0.1x branch where `sync/` is absent.
- The orchestration function must never leave the system in a partially-persisted state for validation failures.
- If append succeeds but materialization fails, the event is still recoverable from the log.

**Implementation Command**: `spec-kitty implement WP07 --base WP06`
You may also need to merge WP02, WP03, and WP04 branches if they are not already in WP06's lineage.

## Subtasks & Detailed Guidance

### T032: Create Emit Orchestration Function

**Purpose**: Build the central `emit_status_transition()` function that orchestrates the entire canonical pipeline.

**Steps**:
1. Create `src/specify_cli/status/emit.py` (or add to `status/__init__.py` -- prefer a dedicated module for clarity).
2. Define the function signature:
   ```python
   def emit_status_transition(
       feature_dir: Path,
       feature_slug: str,
       wp_id: str,
       to_lane: str,
       actor: str,
       *,
       force: bool = False,
       reason: str | None = None,
       evidence: dict | None = None,
       review_ref: str | None = None,
       execution_mode: str = "worktree",
       repo_root: Path | None = None,
   ) -> StatusEvent:
   ```
3. Implement the pipeline in this exact order:
   - `resolved_lane = resolve_lane_alias(to_lane)` -- from `transitions.py`
   - Read current lane: `events = store.read_events(feature_dir)`, derive `from_lane` from the last event for this WP (or `"planned"` if no events exist)
   - `validate_transition(from_lane, resolved_lane, force, actor, reason, evidence, review_ref)` -- from `transitions.py`
   - Create `StatusEvent` with ULID event_id, all fields populated
   - `store.append_event(feature_dir, event)` -- from `store.py`
   - `snapshot = reducer.materialize(feature_dir, feature_slug)` -- from `reducer.py`
   - `legacy_bridge.update_all_views(feature_dir, snapshot)` -- from `legacy_bridge.py`
   - `_saas_fan_out(event, feature_slug, repo_root)` -- see T033
   - Return the event
4. Export `emit_status_transition` from `status/__init__.py`.

**Files**: `src/specify_cli/status/emit.py`, `src/specify_cli/status/__init__.py`

**Validation**: Unit test calling `emit_status_transition()` with a valid transition and verifying the event is returned with all fields populated.

**Edge Cases**:
- First event for a WP: `from_lane` should be `"planned"` (initial state).
- Multiple events for same WP: `from_lane` is derived from the last event's `to_lane`.
- WP has never been seen: treat as starting from `"planned"`.

### T033: SaaS Fan-Out Integration

**Purpose**: After canonical persistence, conditionally emit a SaaS telemetry event via the existing sync pipeline.

**Steps**:
1. Create a private helper function `_saas_fan_out()` in `emit.py`:
   ```python
   def _saas_fan_out(
       event: StatusEvent,
       feature_slug: str,
       repo_root: Path | None,
   ) -> None:
       try:
           from specify_cli.sync.events import emit_wp_status_changed
           emit_wp_status_changed(
               event.wp_id,
               event.from_lane,
               event.to_lane,
           )
       except ImportError:
           pass  # SaaS sync not available (0.1x branch)
       except Exception:
           import logging
           logging.getLogger(__name__).warning(
               "SaaS fan-out failed for event %s; canonical log unaffected",
               event.event_id,
           )
   ```
2. The try/except ImportError handles the 0.1x branch where `sync/` module does not exist.
3. The broad Exception catch ensures SaaS failures NEVER block canonical persistence.
4. Log a warning on SaaS failure but do not raise.

**Files**: `src/specify_cli/status/emit.py`

**Validation**: Test with mock that verifies `emit_wp_status_changed` is called when available. Test with ImportError to verify graceful skip.

**Edge Cases**:
- `sync.events` exists but `emit_wp_status_changed` raises a network error: must not propagate.
- `sync.events` import succeeds but the emitter is not configured: should still not fail.

### T034: Atomic Operation Wrapping

**Purpose**: Ensure that validation failures never result in persisted data, while allowing recovery from post-append failures.

**Steps**:
1. The pipeline order in T032 is itself the atomicity contract:
   - `validate_transition()` is called BEFORE `append_event()`. If validation fails, nothing is persisted.
   - `append_event()` is called BEFORE `materialize()`. If append succeeds but materialize fails, the event is in the JSONL log and can be recovered by running `status materialize` manually.
   - `update_all_views()` is best-effort after materialization. If it fails, the canonical state (JSONL + status.json) is still correct.
2. Do NOT implement filesystem transactions (rename tricks) at this level -- that is the store's responsibility (WP02).
3. If `validate_transition()` raises `TransitionError`, re-raise it directly. Do not catch and wrap.
4. If `materialize()` fails, log a warning but still return the event (the event IS persisted).

**Files**: `src/specify_cli/status/emit.py`

**Validation**: Test that a failed validation does not create any event. Test that a failed materialize still leaves the event in JSONL.

**Edge Cases**:
- Disk full during append: store.append_event() should raise; orchestration should propagate.
- Corrupted existing JSONL: read_events() for from_lane detection should fail-fast (not silently skip).

### T035: Force Transition Handling

**Purpose**: When `force=True`, bypass guard conditions but still validate the audit trail.

**Steps**:
1. In the validate step within `emit_status_transition()`:
   - If `force=True`: verify `actor` is non-empty and `reason` is non-empty. Raise `TransitionError` if either is missing.
   - If `force=True`: skip guard condition checks (e.g., subtask completeness, workspace context).
   - If `force=True`: still verify that `to_lane` is a valid canonical lane (force does not allow invalid lane values).
2. The StatusEvent must have `force=True` and `reason` populated in the persisted event.
3. The reducer (WP03) already handles force events correctly -- it tracks `force_count` per WP.

**Files**: `src/specify_cli/status/emit.py`

**Validation**:
- Test force=True with actor and reason: succeeds even for normally-illegal transitions (e.g., `done -> in_progress`).
- Test force=True without reason: rejected with clear error.
- Test force=True without actor: rejected with clear error.
- Test force=True with invalid to_lane (e.g., `"invalid"`): rejected.

**Edge Cases**:
- Force from `done` state: this is the only way to exit the terminal `done` state.
- Force to `done` without evidence: allowed (force bypasses evidence requirement).

### T036: Done-Evidence Contract

**Purpose**: Enforce that transitions to `done` include structured evidence unless force-overridden.

**Steps**:
1. In `validate_transition()` or as a guard condition:
   - When `to_lane == "done"` and `force == False`:
     - `evidence` parameter must not be None.
     - `evidence` must contain at least a `"review"` key with `"reviewer"` and `"verdict"` sub-keys.
     - If missing, raise `TransitionError("Moving to done requires evidence with review.reviewer and review.verdict")`.
   - When `to_lane == "done"` and `force == True`:
     - Evidence is optional (force bypasses the requirement).
     - Actor and reason are still required (handled in T035).
2. Build `DoneEvidence` from the provided dict:
   ```python
   if evidence:
       done_evidence = DoneEvidence(
           review=ReviewApproval(
               reviewer=evidence["review"]["reviewer"],
               verdict=evidence["review"]["verdict"],
               reference=evidence["review"].get("reference", ""),
           ),
           repos=[RepoEvidence(**r) for r in evidence.get("repos", [])],
           verification=[VerificationResult(**v) for v in evidence.get("verification", [])],
       )
   ```
3. The event's `evidence` field stores the serialized DoneEvidence.

**Files**: `src/specify_cli/status/emit.py`, potentially `src/specify_cli/status/transitions.py`

**Validation**:
- Test `to_lane="done"` with valid evidence: succeeds.
- Test `to_lane="done"` without evidence: rejected.
- Test `to_lane="done"` with evidence missing `review.reviewer`: rejected.
- Test `to_lane="done"` with `force=True` and no evidence: succeeds.

**Edge Cases**:
- Evidence dict with extra fields: should be accepted (forward-compatible).
- Evidence with `verdict: "changes_requested"`: this is valid -- a reviewer can mark done with changes_requested if they choose to force.

### T037: Integration Tests

**Purpose**: Verify the full emit pipeline end-to-end in a realistic filesystem environment.

**Steps**:
1. Create `tests/integration/test_status_emit_flow.py`.
2. Test cases:

   **test_emit_full_pipeline**: Create a feature directory with a WP file. Call `emit_status_transition()` to move WP01 from planned to claimed. Verify:
   - `status.events.jsonl` exists and contains exactly one line.
   - The event JSON has all required fields per `contracts/event-schema.json`.
   - `status.json` exists and shows WP01 in `claimed`.
   - WP frontmatter `lane` field reads `claimed`.

   **test_emit_multiple_transitions**: Chain transitions: planned -> claimed -> in_progress -> for_review. Verify JSONL has 3 events, status.json shows `for_review`.

   **test_emit_force_without_reason_fails**: Call with `force=True, reason=None`. Verify `TransitionError` is raised and no event is persisted.

   **test_emit_done_without_evidence_fails**: Call with `to_lane="done"` and no evidence. Verify rejection.

   **test_emit_done_with_evidence_succeeds**: Call with valid evidence dict. Verify event has evidence field populated.

   **test_emit_saas_called_when_available**: Mock `sync.events.emit_wp_status_changed`. Verify it is called after successful emit.

   **test_emit_saas_failure_does_not_block**: Mock `sync.events.emit_wp_status_changed` to raise. Verify the emit still succeeds and event is persisted.

   **test_emit_invalid_transition_rejected**: Attempt `planned -> done` without force. Verify rejection.

   **test_emit_alias_resolution**: Call with `to_lane="doing"`. Verify event has `to_lane="in_progress"`.

3. Use `tmp_path` fixture for isolated filesystem. Create minimal feature directory structure:
   ```python
   feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
   feature_dir.mkdir(parents=True)
   tasks_dir = feature_dir / "tasks"
   tasks_dir.mkdir()
   # Create a minimal WP file with frontmatter
   ```

**Files**: `tests/integration/test_status_emit_flow.py`

**Validation**: All tests pass. Coverage of emit.py reaches 90%+.

**Edge Cases**:
- Empty feature directory (no prior events): first emit creates JSONL file.
- Concurrent access: not tested here (handled by git merge semantics).

## Test Strategy

**Unit Tests** (in `tests/specify_cli/status/test_emit.py`):
- Test `emit_status_transition()` with mocked store, reducer, and legacy_bridge to verify pipeline order.
- Test `_saas_fan_out()` with mocked sync module.
- Test validation is called before persistence.

**Integration Tests** (in `tests/integration/test_status_emit_flow.py` -- T037):
- Full filesystem tests with real store, reducer, and legacy bridge.
- Verify all artifacts created correctly.

**Test Dependencies**:
- WP02 store must be functional.
- WP03 reducer must be functional.
- WP06 legacy bridge must be functional.
- WP01 models must be importable.

**Running Tests**:
```bash
python -m pytest tests/specify_cli/status/test_emit.py -x -q
python -m pytest tests/integration/test_status_emit_flow.py -x -q
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular imports between `status/` and `sync/` | Import failures at runtime | Use lazy imports (try/except) for sync module as specified in T033 |
| SaaS fan-out failure masks canonical failure | User thinks emit succeeded but nothing persisted | SaaS runs AFTER canonical append; if canonical fails, it propagates before SaaS |
| from_lane derivation reads entire event log | Slow for large logs | For MVP, read all events. Optimize later with status.json cache read |
| DoneEvidence dict structure mismatch | Runtime KeyError | Validate evidence dict structure before building dataclass; raise clear TransitionError |
| Reducer produces non-deterministic output | Drift between runs | Reducer determinism is WP03's contract; this WP relies on it |

## Review Guidance

When reviewing this WP, verify:
1. **Pipeline order is correct**: validate -> append -> materialize -> update_views -> saas. No reordering.
2. **No partial persistence on validation failure**: If validate raises, nothing is written to disk.
3. **SaaS isolation**: Confirm the try/except pattern truly prevents SaaS failures from blocking.
4. **Force audit completeness**: Every force event has actor + reason in the persisted event.
5. **Done evidence validation**: The evidence structure matches `contracts/event-schema.json` DoneEvidence definition.
6. **Integration tests cover the critical paths**: At minimum -- happy path, invalid transition, force without reason, done without evidence, SaaS failure isolation.
7. **No fallback mechanisms**: Code should fail intentionally when something is wrong, not silently degrade.

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
