from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from specify_cli.sync.emitter import EventEmitter


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
    assert routed == [event]
    assert event["team_slug"] is None
    assert event["drain_blocked_reason"] == "sync_disabled"
    assert "direct ingress skipped" not in caplog.text
