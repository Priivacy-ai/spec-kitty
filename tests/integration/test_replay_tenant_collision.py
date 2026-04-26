"""Integration test: replay tenant/project collision (FR-028, T036).

Drives :func:`specify_cli.sync.replay.replay_events` against paired
event streams covering:

* match → idempotent apply (and idempotent under a second pass).
* tenant mismatch → :class:`TenantMismatch` raised when
  ``raise_on_mismatch=True``; structured conflict logged when
  ``raise_on_mismatch=False``.
* project mismatch → :class:`ProjectMismatch` (separately, NOT
  collapsed into the tenant case per the reviewer guidance in
  ``WP06-sync-and-auth.md``).
"""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.sync.replay import (
    ProjectMismatch,
    ReplayTarget,
    TenantMismatch,
    replay_events,
)


TARGET = ReplayTarget(tenant_id="tenant-A", project_id="proj-1")


def _event(
    *,
    tenant: str,
    project: str,
    eid: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"data": "value"}
    if extra:
        payload.update(extra)
    return {
        "event_id": eid,
        "event_type": "ReplayProbe",
        "tenant_id": tenant,
        "project_id": project,
        "payload": payload,
    }


class TestReplayTenantCollision:
    """FR-028: deterministic, structured replay collision handling."""

    def test_matching_events_apply_once(self) -> None:
        applied: list[dict[str, Any]] = []
        events = [
            _event(tenant="tenant-A", project="proj-1", eid="evt-001"),
            _event(tenant="tenant-A", project="proj-1", eid="evt-002"),
        ]

        result = replay_events(
            events,
            TARGET,
            apply_callable=applied.append,
        )
        assert result.applied == 2
        assert result.skipped_tenant == 0
        assert result.skipped_project == 0
        assert [e["event_id"] for e in applied] == ["evt-001", "evt-002"]

    def test_idempotent_apply_does_not_double_write(self) -> None:
        """Replaying the same stream twice routes events through ``apply_callable``
        exactly once per replay invocation; idempotency guarantees come from
        the *caller's* apply implementation. The reducer itself MUST not
        mutate the underlying store; we verify that by deduping event_ids.
        """
        applied_set: set[str] = set()

        def _idempotent_apply(event: dict[str, Any]) -> None:
            # Caller-side dedup keyed on event_id — the canonical idempotent
            # apply pattern for replay.
            applied_set.add(event["event_id"])

        events = [_event(tenant="tenant-A", project="proj-1", eid="evt-001")]

        result_a = replay_events(events, TARGET, apply_callable=_idempotent_apply)
        result_b = replay_events(events, TARGET, apply_callable=_idempotent_apply)

        assert result_a.applied == 1
        assert result_b.applied == 1
        # Despite two replays, only a single event_id was committed.
        assert applied_set == {"evt-001"}

    def test_tenant_mismatch_raises_when_strict(self) -> None:
        events = [
            _event(tenant="tenant-B", project="proj-1", eid="evt-tenant-bad"),
        ]
        with pytest.raises(TenantMismatch) as exc_info:
            replay_events(events, TARGET, raise_on_mismatch=True)
        err = exc_info.value
        assert err.error_code == "tenant_mismatch"
        assert err.tenant_id == "tenant-B"
        assert err.target_tenant_id == "tenant-A"
        assert err.event_id == "evt-tenant-bad"

    def test_tenant_mismatch_logs_and_skips_when_lenient(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        applied: list[dict[str, Any]] = []
        events = [
            _event(tenant="tenant-A", project="proj-1", eid="evt-ok"),
            _event(tenant="tenant-B", project="proj-1", eid="evt-bad-tenant"),
            _event(tenant="tenant-A", project="proj-1", eid="evt-ok2"),
        ]

        with caplog.at_level("WARNING", logger="specify_cli.sync.replay.conflict"):
            result = replay_events(events, TARGET, apply_callable=applied.append)

        assert result.applied == 2
        assert result.skipped_tenant == 1
        assert result.skipped_project == 0
        assert [e["event_id"] for e in applied] == ["evt-ok", "evt-ok2"]

        assert any(
            rec.levelname == "WARNING"
            and "replay.conflict" in rec.getMessage()
            and "tenant_mismatch" in rec.getMessage()
            for rec in caplog.records
        )

        # Conflict records are structured (machine-readable).
        record = result.conflicts[0]
        assert record.error_code == "tenant_mismatch"
        assert record.event_id == "evt-bad-tenant"
        assert record.tenant_id == "tenant-B"
        assert record.target_tenant_id == "tenant-A"

    def test_project_mismatch_raises_when_strict(self) -> None:
        """Project mismatch is its OWN exception type (not collapsed into tenant)."""
        events = [
            _event(tenant="tenant-A", project="proj-2", eid="evt-bad-project"),
        ]
        with pytest.raises(ProjectMismatch) as exc_info:
            replay_events(events, TARGET, raise_on_mismatch=True)
        err = exc_info.value
        assert err.error_code == "project_mismatch"
        # Sanity: it is NOT a TenantMismatch — distinct surfaces.
        assert not isinstance(err, TenantMismatch)
        assert err.project_id == "proj-2"
        assert err.target_project_id == "proj-1"

    def test_project_mismatch_logs_and_skips_when_lenient(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        events = [
            _event(tenant="tenant-A", project="proj-2", eid="evt-bad-project"),
        ]
        with caplog.at_level("WARNING", logger="specify_cli.sync.replay.conflict"):
            result = replay_events(events, TARGET)

        assert result.applied == 0
        assert result.skipped_tenant == 0
        assert result.skipped_project == 1
        assert any(
            "project_mismatch" in rec.getMessage() for rec in caplog.records
        )

    def test_paired_streams_exercise_both_surfaces(self) -> None:
        """Mixed stream: match + tenant-mismatch + project-mismatch all in one pass."""
        events = [
            _event(tenant="tenant-A", project="proj-1", eid="match"),
            _event(tenant="tenant-B", project="proj-1", eid="bad-tenant"),
            _event(tenant="tenant-A", project="proj-2", eid="bad-project"),
        ]
        result = replay_events(events, TARGET)
        assert result.applied == 1
        assert result.skipped_tenant == 1
        assert result.skipped_project == 1

        verdicts = {d.event_id: d.verdict for d in result.decisions}
        assert verdicts == {
            "match": "apply",
            "bad-tenant": "tenant_mismatch",
            "bad-project": "project_mismatch",
        }
