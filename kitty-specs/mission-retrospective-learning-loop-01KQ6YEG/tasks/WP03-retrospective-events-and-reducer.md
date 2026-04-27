---
work_package_id: WP03
title: Retrospective Events + Reducer Integration
dependencies:
- WP02
requirement_refs:
- FR-017
- FR-018
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet:implementer:implementer"
shell_pid: "88719"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/retrospective/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/retrospective/events.py
- src/specify_cli/status/models.py
- src/specify_cli/status/reducer.py
- tests/retrospective/test_events_shapes.py
- tests/retrospective/test_reducer_integration.py
- tests/architectural/test_retrospective_events_boundary.py
priority: P1
status: planned
tags: []
---

# WP03 — Retrospective Events + Reducer Integration

## Objective

Define the eight retrospective events locally in `specify_cli.retrospective.events` (per Q4-C cutover plan), wire them into the existing mission event log via append-only emission, and extend the status reducer to surface a `RetrospectiveSnapshot` on the existing `StatusSnapshot` (additive only).

## Spec coverage

- **FR-017** eight stable event names.
- **FR-018** events join the canonical mission event log; reducer surfaces them; retries representable as additional events.
- **NFR-005** append-only invariant.

## Context

The eight event names and payload contracts are pinned in [`../contracts/retrospective_events_v1.md`](../contracts/retrospective_events_v1.md). The cutover plan is documented in [`../plan.md`](../plan.md) AD-004 and in research R-007: ship local Pydantic models now, mirror upstream `spec_kitty_events` in parallel, switch imports + delete local module when upstream lands.

The reducer extension is **additive**: existing snapshot consumers see no change. The new field is `retrospective: RetrospectiveSnapshot | None`, defaulting to `None` for missions with no retrospective events.

## Subtasks

### T010 [P] — Pydantic event models for the eight retrospective events

In `src/specify_cli/retrospective/events.py`, define one Pydantic v2 payload model per event, plus an optional thin envelope helper that matches the shared mission-event envelope (`event_id`, `event_name`, `at`, `actor`, `mission_id`, `mid8`, `mission_slug`, `payload`).

Eight payload models:

- `RequestedPayload(mode: Mode, terminus_step_id: str, requested_by: ActorRef)`
- `StartedPayload(facilitator_profile_id: str, action_id: str)`
- `CompletedPayload(record_path: str, record_hash: str, findings_summary: dict, proposals_count: int)`
- `SkippedPayload(record_path: str, skip_reason: str, skipped_by: ActorRef)`
- `FailedPayload(failure_code: str, message: str, record_path: str | None)`
- `ProposalGeneratedPayload(proposal_id: str, kind: str, record_path: str)`
- `ProposalAppliedPayload(proposal_id: str, kind: str, target_urn: str, provenance_ref: str, applied_by: ActorRef)`
- `ProposalRejectedPayload(proposal_id: str, kind: str, reason: Literal["human_decline", "conflict", "stale_evidence", "invalid_payload"], detail: str, rejected_by: ActorRef)`

Add a top-level `RETROSPECTIVE_EVENT_NAMES: frozenset[str]` constant containing the eight stable names.

Add a TODO comment near the module docstring referencing the upstream `spec_kitty_events` issue link (the issue is opened in WP12); leave the link as `<TODO: WP12>` for now.

### T011 — Event emission helper

Add a function:

```python
def emit_retrospective_event(
    *,
    feature_dir: Path,
    mission_slug: str,
    mission_id: str,
    mid8: str,
    actor: ActorRef,
    event_name: str,
    payload: BaseModel,
) -> str:  # returns event_id
    """Append a retrospective event to the mission's status.events.jsonl.

    Append-only. Sorted-key JSON. Returns the assigned event_id (ULID).
    """
```

Implementation: build the envelope dict with sorted keys, use the existing `specify_cli.status.store.append_event` (or equivalent) to persist. Do NOT modify `status.emit.emit_status_transition`'s shape; this is a sibling helper for retrospective events that don't change WP lane state.

### T012 — Reducer integration

Extend `src/specify_cli/status/models.py`:

```python
class RetrospectiveSnapshot(BaseModel):
    status: Literal["completed", "skipped", "failed", "pending", "absent"]
    mode: Mode | None
    record_path: str | None
    proposals_total: int
    proposals_applied: int
    proposals_rejected: int
    proposals_pending: int

class StatusSnapshot(BaseModel):
    # existing fields ...
    retrospective: RetrospectiveSnapshot | None = None
```

Extend `src/specify_cli/status/reducer.py` `materialize()` (and `reduce()` if it accumulates) to compute `RetrospectiveSnapshot` from retrospective events:

- `absent` if no retrospective events seen.
- Status reflects the latest of `completed`/`skipped`/`failed` (by `at`, `event_id` tiebreak).
- Proposal counts derived from `proposal.{generated,applied,rejected}` events.

Existing reducer tests must continue to pass unchanged.

### T013 — Tests: append-only invariant, retry semantics, name uniqueness

In `tests/retrospective/test_events_shapes.py` and `tests/retrospective/test_reducer_integration.py`:

- Each event payload validates with required fields and rejects extras.
- The eight event names do not collide with existing mission event names (assert by enumerating existing event names in the codebase; if a constant/list exists, use it; otherwise grep).
- A second `retrospective.completed` event for the same mission becomes the active snapshot; the prior remains in the log (append-only invariant).
- `RetrospectiveSnapshot` reflects the `proposal.generated`/`applied`/`rejected` counts correctly.

### T014 — Boundary test (skipped, pending upstream)

Add `tests/architectural/test_retrospective_events_boundary.py` with the following body:

```python
import pytest

@pytest.mark.skip(reason="pending spec_kitty_events upstream release: <TODO: WP12 issue link>")
def test_retrospective_events_single_home_post_cutover() -> None:
    """When upstream ships, no Retrospective*Event Pydantic models live outside spec_kitty_events.

    This test is unskipped in the cutover PR (see docs/migration/retrospective-events-upstream.md).
    """
    raise AssertionError("intentionally not implemented until cutover")
```

Document in a top-of-file comment that the test will become active when the upstream PR is merged and `events.py` switches imports.

## Definition of Done

- [ ] Eight events with payload Pydantic models exist and validate.
- [ ] Emission helper persists envelope JSON via the existing event-log primitive (no new file/format).
- [ ] `StatusSnapshot.retrospective` is additive; existing tests still pass.
- [ ] Reducer test fixture covers retry semantics + status precedence by latest.
- [ ] Architectural boundary test exists, skipped with clear reason.
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90% on new modules.
- [ ] No changes outside `owned_files`.

## Risks

- **Reducer change touches existing code**: keep the change strictly additive. Run the full status test suite before claiming done.
- **Event-name collision**: be explicit; assert non-collision in tests.
- **JSONL format drift**: the envelope must match existing event lines. Don't introduce a different separator or key order.

## Reviewer guidance

- Verify the additive nature of the reducer change by running existing status reducer tests unmodified.
- Verify the boundary test is `pytest.skip(...)` with a reason that names the upstream tracking issue (will be updated by WP12).
- Verify no event-name collisions with existing mission events.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Activity Log

- 2026-04-27T09:10:22Z – claude:sonnet:implementer:implementer – shell_pid=88719 – Started implementation via action command
- 2026-04-27T09:18:24Z – claude:sonnet:implementer:implementer – shell_pid=88719 – Ready for review: 8 events + emission helper + additive RetrospectiveSnapshot on StatusSnapshot
