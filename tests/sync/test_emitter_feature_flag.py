from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from specify_cli.sync.emitter import EventEmitter


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

class _Clock:
    node_id = "test-node"

    def tick(self) -> int:
        return 1


def test_saas_flag_disabled_suppresses_direct_ingress_resolution(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")
    monkeypatch.setattr(
        EventEmitter,
        "_get_identity",
        lambda self: SimpleNamespace(
            build_id="build-1",
            project_uuid=uuid4(),
            project_slug="project-1",
        ),
    )
    monkeypatch.setattr(
        EventEmitter,
        "_get_git_metadata",
        lambda self: SimpleNamespace(
            git_branch=None,
            head_commit_sha=None,
            repo_slug=None,
        ),
    )
    monkeypatch.setattr(EventEmitter, "_validate_event", lambda self, event: True)
    monkeypatch.setattr("specify_cli.sync.emitter.validate_outbound_payload", lambda event, gate: None)

    def fail_if_team_slug_resolves(self) -> str | None:
        raise AssertionError("direct-ingress team resolver should stay behind the SaaS feature flag")

    monkeypatch.setattr(EventEmitter, "_get_team_slug", fail_if_team_slug_resolves)

    routed: list[dict] = []
    monkeypatch.setattr(
        EventEmitter,
        "_route_event",
        lambda self, event: routed.append(event) or True,
    )

    emitter = EventEmitter(clock=_Clock())
    event = emitter._emit(
        event_type="BuildRegistered",
        aggregate_id="build-1",
        aggregate_type="Build",
        payload={},
    )

    assert event is not None
    # Since #3799 a disabled SaaS flag disarms ``sync_active()``, so ``_emit``
    # returns the constructed envelope but routes NOTHING (the arming gate sits
    # before ``_route_event`` — matching ``tests/deactivation/test_seam_gating``'s
    # capture/queue-not-reached contract). Pre-#3799 the disabled flag still routed
    # locally; that granular "route-but-skip-direct-ingress" behavior is gone.
    assert routed == []
    # The envelope is still fully shaped: direct-ingress team-slug resolution
    # stays behind the flag (``fail_if_team_slug_resolves`` above proves the
    # resolver was never called) and the disabled marker is stamped.
    assert event["team_slug"] is None
    assert event["drain_blocked_reason"] == "saas_disabled"
    assert "direct ingress skipped" not in caplog.text
