---
work_package_id: WP07
title: SaaS Read-Model Policy
dependencies:
- WP06
requirement_refs:
- FR-010
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "22491"
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: src/specify_cli/invocation/projection_policy.py
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/projection_policy.py
- src/specify_cli/invocation/propagator.py
- tests/specify_cli/invocation/test_projection_policy.py
- tests/specify_cli/invocation/test_propagator_policy.py
tags: []
---

# WP07 — SaaS Read-Model Policy

## Objective

Implement the typed `projection_policy.py` module with `ModeOfWork` (re-exported), `EventKind`, `ProjectionRule`, `POLICY_TABLE`, and `resolve_projection()`. Wire `src/specify_cli/invocation/propagator.py::_propagate_one` through the policy so that `(mode, event)` pairs project predictably. Preserve the local-first invariant (sync-gate short-circuits before the policy lookup). Preserve dashboard behaviour for `task_execution` / `mission_step` — those rows keep their 3.2.0a5 projection semantics exactly.

## Context

- **Design records**: [ADR-003](../decisions/ADR-003-projection-policy.md).
- **Data model**: [data-model.md](../data-model.md) §4, §5.
- **Contract**: [contracts/projection-policy.md](../contracts/projection-policy.md).
- **Baseline propagator**: `src/specify_cli/invocation/propagator.py::_propagate_one` currently projects `started` and `completed` events unconditionally once the sync-gate and auth check pass. WP06 added correlation events (`artifact_link`, `commit_link`) that currently also project unconditionally — a transient over-projection that WP07 corrects.

**Invariants preserved**:
- Sync-gate (`routing.effective_sync_enabled=False` → early return) stays as the first check.
- Authentication lookup (`_get_saas_client(...) is None` → early return) stays second.
- Policy evaluation is read-only; raises no uncaught exception; never blocks.
- `propagation-errors.jsonl` never grows during clean sync-disabled runs (NFR-007).

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP07 depends on WP06 (needs `ModeOfWork`, `EventKind` definitions and the correlation events to exist).

## Subtask Guidance

### T033 — Create `projection_policy.py`

**Purpose**: Ship the typed policy module.

**File to create**: `src/specify_cli/invocation/projection_policy.py`

```python
"""SaaS read-model projection policy.

Single source of truth for per-(mode, event) projection behaviour.
See ADR-003-projection-policy.md and docs/trail-model.md (SaaS Read-Model Policy).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from specify_cli.invocation.modes import ModeOfWork

__all__ = [
    "ModeOfWork",
    "EventKind",
    "ProjectionRule",
    "POLICY_TABLE",
    "resolve_projection",
]


class EventKind(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ARTIFACT_LINK = "artifact_link"
    COMMIT_LINK = "commit_link"


@dataclass(frozen=True)
class ProjectionRule:
    project: bool
    include_request_text: bool
    include_evidence_ref: bool


POLICY_TABLE: dict[tuple[ModeOfWork, EventKind], ProjectionRule] = {
    # Advisory — timeline entries with no body.
    (ModeOfWork.ADVISORY, EventKind.STARTED):       ProjectionRule(True,  False, False),
    (ModeOfWork.ADVISORY, EventKind.COMPLETED):     ProjectionRule(True,  False, False),
    (ModeOfWork.ADVISORY, EventKind.ARTIFACT_LINK): ProjectionRule(False, False, False),
    (ModeOfWork.ADVISORY, EventKind.COMMIT_LINK):   ProjectionRule(False, False, False),

    # Task execution — full bodies projected; correlation events projected without bodies.
    (ModeOfWork.TASK_EXECUTION, EventKind.STARTED):       ProjectionRule(True, True,  False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMPLETED):     ProjectionRule(True, True,  True),
    (ModeOfWork.TASK_EXECUTION, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMMIT_LINK):   ProjectionRule(True, False, False),

    # Mission step — same as task_execution.
    (ModeOfWork.MISSION_STEP, EventKind.STARTED):       ProjectionRule(True, True,  False),
    (ModeOfWork.MISSION_STEP, EventKind.COMPLETED):     ProjectionRule(True, True,  True),
    (ModeOfWork.MISSION_STEP, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.MISSION_STEP, EventKind.COMMIT_LINK):   ProjectionRule(True, False, False),

    # Query — no projection.
    (ModeOfWork.QUERY, EventKind.STARTED):       ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMPLETED):     ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.ARTIFACT_LINK): ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMMIT_LINK):   ProjectionRule(False, False, False),
}


_DEFAULT_RULE = ProjectionRule(project=True, include_request_text=True, include_evidence_ref=True)


def resolve_projection(
    mode: ModeOfWork | None,
    event: EventKind,
) -> ProjectionRule:
    """Return the projection rule for (mode, event).

    ``mode is None`` (pre-mission records) → treated as TASK_EXECUTION to preserve
    pre-WP06 unconditional projection behaviour for legacy records.

    Unknown ``(mode, event)`` pair → falls back to ``_DEFAULT_RULE`` (project all).
    The table is exhaustive for the enums as defined; this path is only hit if
    a future EventKind is added before the table is extended.
    """
    effective_mode = mode if mode is not None else ModeOfWork.TASK_EXECUTION
    return POLICY_TABLE.get((effective_mode, event), _DEFAULT_RULE)
```

### T034 — Wire `_propagate_one` through the policy

**Purpose**: Policy-gate envelope creation; keep sync-gate + auth short-circuits first.

**File to modify**: `src/specify_cli/invocation/propagator.py`

**Changes inside `_propagate_one(record, repo_root)`**:

1. Add imports at top:
   ```python
   from specify_cli.invocation.projection_policy import (
       EventKind, ModeOfWork, resolve_projection,
   )
   ```

2. After the existing sync-gate and auth short-circuits (which stay first), add:
   ```python
   # Consult projection policy. Sync-gate and auth have already passed.
   raw_event = record.event
   try:
       event = EventKind(raw_event)
   except ValueError:
       # Unknown event kind (e.g., future EventKind); project with default rule.
       event = EventKind.STARTED  # safest conservative default; see resolve_projection fallback
   raw_mode = getattr(record, "mode_of_work", None)
   mode: ModeOfWork | None = ModeOfWork(raw_mode) if raw_mode else None
   rule = resolve_projection(mode, event)
   if not rule.project:
       return  # Policy says no projection for this (mode, event).
   ```

3. When building the envelope for `started` events, gate field inclusion on `rule.include_request_text`:
   ```python
   if record.event == "started":
       event_dict: dict[str, object] = {
           "event_type": "ProfileInvocationStarted",
           "invocation_id": record.invocation_id,
           "profile_id": record.profile_id,
           "action": record.action,
           "governance_context_hash": record.governance_context_hash,
           "actor": record.actor,
           "started_at": record.started_at,
       }
       if rule.include_request_text:
           event_dict["request_text"] = record.request_text
       if mode is not None:
           event_dict["mode_of_work"] = mode.value
   ```

4. For `completed` events, gate `evidence_ref` on `rule.include_evidence_ref`:
   ```python
   else:  # completed
       event_dict = {
           "event_type": "ProfileInvocationCompleted",
           "invocation_id": record.invocation_id,
           "outcome": record.outcome,
           "completed_at": record.completed_at,
       }
       if rule.include_evidence_ref:
           event_dict["evidence_ref"] = record.evidence_ref
   ```

5. For correlation events — the propagator needs to accept dict records for `artifact_link` / `commit_link` events (WP06 submits them via `propagator.submit(record_or_dict)` if the implementer extended `submit` to accept dicts; if not, skip this and document that correlation events do not propagate in this release — acceptable). Recommended: add a small adapter in `_propagate_one` that detects dict inputs and routes:
   ```python
   if isinstance(record, dict):
       event_type_map = {
           "artifact_link": "ProfileInvocationArtifactLink",
           "commit_link": "ProfileInvocationCommitLink",
       }
       envelope_event_type = event_type_map.get(record["event"])
       if envelope_event_type is None:
           return
       envelope = {"event_type": envelope_event_type, **record}
       # ... call client.send_event(envelope) ...
   ```

**Note**: If WP06 did not wire correlation-event submission to `propagator.submit(...)`, then WP07 only needs to touch the existing `started`/`completed` paths. Verify the WP06 merge state before implementing T034 step 5.

### T035 — Unit tests for all 16 policy rows + null-mode fallback

**Purpose**: Cover every row of `POLICY_TABLE` and the `resolve_projection(None, ...)` contract.

**File to create**: `tests/specify_cli/invocation/test_projection_policy.py`

```python
"""FR-010 / NFR-005 — POLICY_TABLE coverage + resolve_projection contract."""
from __future__ import annotations

import pytest

from specify_cli.invocation.projection_policy import (
    POLICY_TABLE, EventKind, ModeOfWork, ProjectionRule, resolve_projection,
)


def test_policy_table_covers_all_16_pairs() -> None:
    expected_pairs = {
        (m, e) for m in ModeOfWork for e in EventKind
    }
    assert set(POLICY_TABLE.keys()) == expected_pairs


@pytest.mark.parametrize("mode", list(ModeOfWork))
@pytest.mark.parametrize("event", list(EventKind))
def test_every_row_returns_a_projection_rule(mode: ModeOfWork, event: EventKind) -> None:
    rule = resolve_projection(mode, event)
    assert isinstance(rule, ProjectionRule)


def test_task_execution_started_projects_with_body() -> None:
    rule = resolve_projection(ModeOfWork.TASK_EXECUTION, EventKind.STARTED)
    assert rule == ProjectionRule(True, True, False)


def test_task_execution_completed_includes_evidence() -> None:
    rule = resolve_projection(ModeOfWork.TASK_EXECUTION, EventKind.COMPLETED)
    assert rule == ProjectionRule(True, True, True)


def test_mission_step_completed_includes_evidence() -> None:
    rule = resolve_projection(ModeOfWork.MISSION_STEP, EventKind.COMPLETED)
    assert rule == ProjectionRule(True, True, True)


def test_advisory_events_omit_body() -> None:
    for event in EventKind:
        rule = resolve_projection(ModeOfWork.ADVISORY, event)
        assert not rule.include_request_text
        assert not rule.include_evidence_ref


def test_query_never_projects() -> None:
    for event in EventKind:
        rule = resolve_projection(ModeOfWork.QUERY, event)
        assert not rule.project


def test_correlation_events_on_advisory_do_not_project() -> None:
    for event in (EventKind.ARTIFACT_LINK, EventKind.COMMIT_LINK):
        rule = resolve_projection(ModeOfWork.ADVISORY, event)
        assert not rule.project


def test_correlation_events_on_task_execution_project_without_body() -> None:
    for event in (EventKind.ARTIFACT_LINK, EventKind.COMMIT_LINK):
        rule = resolve_projection(ModeOfWork.TASK_EXECUTION, event)
        assert rule.project
        assert not rule.include_request_text


def test_null_mode_falls_back_to_task_execution() -> None:
    """Pre-mission records (mode_of_work=None) keep 3.2.0a5 projection behaviour."""
    rule_none = resolve_projection(None, EventKind.STARTED)
    rule_task_exec = resolve_projection(ModeOfWork.TASK_EXECUTION, EventKind.STARTED)
    assert rule_none == rule_task_exec
```

### T036 — Integration tests: propagator under mocked client

**Purpose**: Verify `_propagate_one` behaviour under every `(mode, event)` pair with a mocked authenticated client.

**File to create**: `tests/specify_cli/invocation/test_propagator_policy.py`

```python
"""Integration tests for _propagate_one + projection policy.

Verifies that:
1. Sync-disabled checkouts never call send_event.
2. Unauthenticated checkouts never call send_event.
3. Policy correctly gates projection per (mode, event).
4. Envelope fields respect include_request_text / include_evidence_ref.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.propagator import _propagate_one
from specify_cli.invocation.record import InvocationRecord


@pytest.fixture
def mock_authenticated_client() -> MagicMock:
    """Patch the auth lookup to return a mock connected client."""
    client = MagicMock()
    client.send_event = MagicMock()
    return client


def _make_record(event: str, mode: str | None, **extras) -> InvocationRecord:
    base = {
        "event": event,
        "invocation_id": "01HABC",
        "profile_id": "p",
        "action": "a",
        "request_text": "text",
        "governance_context_hash": "abc",
        "actor": "user",
        "started_at": "2026-04-23T00:00:00+00:00",
        "mode_of_work": mode,
    }
    base.update(extras)
    return InvocationRecord(**base)


@pytest.mark.parametrize("mode", ["advisory", "task_execution", "mission_step", "query"])
@pytest.mark.parametrize("event", ["started", "completed"])
def test_sync_disabled_never_calls_send(tmp_path: Path, mode: str, event: str) -> None:
    # ... patch routing.effective_sync_enabled=False, call _propagate_one, assert send_event not called ...
    pass


def test_task_execution_started_includes_request_text(tmp_path, mock_authenticated_client) -> None:
    # ... patch _get_saas_client → mock; call _propagate_one with (task_execution, started) ...
    # Assert mock_authenticated_client.send_event called once with envelope including request_text.
    pass


def test_advisory_started_omits_request_text(tmp_path, mock_authenticated_client) -> None:
    # Advisory started projects but without request_text.
    pass


def test_query_started_does_not_project(tmp_path, mock_authenticated_client) -> None:
    # Policy returns project=False; send_event never called.
    pass


def test_task_execution_completed_includes_evidence_ref(tmp_path, mock_authenticated_client) -> None:
    pass


def test_advisory_completed_omits_evidence_ref(tmp_path, mock_authenticated_client) -> None:
    pass
```

Fill in the `pass`-bodied tests with concrete setup. The existing `test_invocation_e2e.py` shows patterns for setting up `routing.effective_sync_enabled` and the mock client.

### T037 — NFR-007 / SC-008 assertion

**Purpose**: Assert that under sync-disabled conditions, `propagation-errors.jsonl` remains empty across all 4 modes.

**Add to** `tests/specify_cli/invocation/test_propagator_policy.py`:

```python
@pytest.mark.parametrize("mode", ["advisory", "task_execution", "mission_step", "query"])
def test_no_propagation_errors_under_sync_disabled(tmp_path: Path, mode: str) -> None:
    """NFR-007 / SC-008 — propagation-errors.jsonl stays empty with sync disabled."""
    # Set up a fresh repo_root at tmp_path.
    # Disable sync.
    # Run a full invocation lifecycle: advise/ask/do (depending on mode) + complete.
    # Assert .kittify/events/propagation-errors.jsonl is absent or empty.
    ...
```

### T038 — Golden-path regression: existing timeline behaviour preserved

**Purpose**: Assert that `task_execution/started` and `mission_step/completed` produce the exact same envelope shape (minus the new additive fields) as 3.2.0a5.

**Add to** `test_projection_policy.py`:

```python
def test_golden_path_task_execution_started() -> None:
    """task_execution/started MUST project with request_text (3.2.0a5 behaviour)."""
    rule = resolve_projection(ModeOfWork.TASK_EXECUTION, EventKind.STARTED)
    assert rule.project is True
    assert rule.include_request_text is True


def test_golden_path_mission_step_completed() -> None:
    """mission_step/completed MUST project with evidence_ref (3.2.0a5 behaviour)."""
    rule = resolve_projection(ModeOfWork.MISSION_STEP, EventKind.COMPLETED)
    assert rule.project is True
    assert rule.include_evidence_ref is True


def test_golden_path_null_mode_preserves_unconditional_projection() -> None:
    """Pre-WP06 records (no mode_of_work) project as before."""
    rule = resolve_projection(None, EventKind.STARTED)
    assert rule.project is True
    assert rule.include_request_text is True
```

## Definition of Done

- [ ] `src/specify_cli/invocation/projection_policy.py` exists with typed enum, dataclass, exhaustive POLICY_TABLE, `resolve_projection()`.
- [ ] `_propagate_one` in `propagator.py` consults `resolve_projection()` after sync-gate + auth; gates envelope field inclusion.
- [ ] `test_projection_policy.py` passes — 16-row coverage, 4 golden-path tests, null-mode fallback.
- [ ] `test_propagator_policy.py` passes — (mode, event) integration, sync-disabled assertions, authentication-absent assertions.
- [ ] NFR-007 / SC-008 assertion: `propagation-errors.jsonl` empty under sync-disabled across all 4 modes.
- [ ] `mypy --strict src/specify_cli/invocation/projection_policy.py src/specify_cli/invocation/propagator.py` passes.
- [ ] No change to `routing.effective_sync_enabled` short-circuit or the `_get_saas_client` lookup order.
- [ ] No change to `InvocationWriter`, `_propagate_one`'s failure-logging helper, or `InvocationSaaSPropagator` submit/shutdown semantics.

## Risks

- **Sync-gate regression**: misplacing the policy lookup before the sync-gate would cause sync-disabled checkouts to attempt SaaS calls. Mitigation: test `test_sync_disabled_never_calls_send` parameterised across all modes + events. Code review confirms order: routing → client → policy.
- **Envelope field mismatch with SaaS consumer**: dropping `request_text` for advisory events may break SaaS consumers that expect the key to always be present. Since omission (not empty string) is the policy, consumers should treat missing keys as "policy-excluded." If the SaaS-side contract does not tolerate this yet, coordinate with the SaaS team before merging. Acceptable risk because 3.2.x line has been additive.
- **Unknown EventKind default**: `resolve_projection` falls back to `_DEFAULT_RULE` for unknown pairs. This is a safety net for future EventKind additions; if a new kind lands before the table is extended, it will over-project for one release. Acceptable.
- **Dict-record handling for correlation events**: the adapter branch (T034 step 5) is conditional on whether WP06 wired correlation-event submission to the propagator. Verify first; adjust scope if needed.

## Reviewer Guidance

Reviewer should:
- Read `projection_policy.py` end-to-end; confirm POLICY_TABLE has 16 rows covering the full 4×4 product.
- Read the `_propagate_one` diff; confirm the order is unchanged: routing → client → policy.
- Confirm envelope field inclusion matches the rule for each path (started, completed, dict-records if present).
- Run both new test files + extensions; confirm all pass.
- Confirm `mypy --strict` is clean.
- Spot-check the parametrised sync-disabled tests run against ALL four modes + ALL four event kinds.

## Activity Log

- 2026-04-23T06:05:49Z – claude:sonnet-4-6:implementer:implementer – shell_pid=22491 – Started implementation via action command
- 2026-04-23T06:10:11Z – claude:sonnet-4-6:implementer:implementer – shell_pid=22491 – SaaS read-model policy complete: typed module + propagator wiring + 16-row coverage + NFR-007 green
