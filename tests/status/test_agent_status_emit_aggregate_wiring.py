"""Wiring + behavior-parity tests for ``agent status emit`` (WP01, FR-004).

These tests prove that ``spec-kitty agent status emit`` routes its write
through the ``MissionStatus`` aggregate (``MissionStatus.transition``) instead
of calling ``emit_status_transition_transactional`` directly, and that doing so
is behavior-preserving (same emitted ``StatusEvent`` fields, same CLI JSON
output) relative to the prior direct path.

T005 — emit routes through ``MissionStatus.transition``.
T006 — behavior-parity snapshot against the prior direct transactional path.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app

pytestmark = pytest.mark.fast

runner = CliRunner()


@pytest.fixture(autouse=True)
def _disable_emit_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep these tests focused on local persistence + routing."""
    import specify_cli.status.emit as status_emit

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    monkeypatch.setattr(status_emit, "fire_dossier_sync", lambda *args, **kwargs: None)


def _make_repo_with_mission(root: Path, slug: str) -> Path:
    repo = root / "repo"
    feature_dir = repo / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    (repo / ".kittify").mkdir()
    return repo


def _emit_args(slug: str) -> list[str]:
    return [
        "emit",
        "WP01",
        "--to",
        "claimed",
        "--actor",
        "codex",
        "--mission",
        slug,
        "--json",
    ]


# ---------------------------------------------------------------------------
# T005 — emit routes through MissionStatus.transition
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.agent.status.locate_project_root")
@patch("specify_cli.cli.commands.agent.status._find_mission_slug")
def test_emit_invokes_mission_status_transition(
    mock_slug,
    mock_root,
    tmp_path: Path,
) -> None:
    """The command must call MissionStatus.transition exactly once."""
    slug = "017-test-feature"
    repo = _make_repo_with_mission(tmp_path, slug)
    mock_root.return_value = repo
    mock_slug.return_value = slug

    import specify_cli.status.aggregate as aggregate_mod

    real_transition = aggregate_mod.MissionStatus.transition
    calls: list[tuple] = []

    def _spy_transition(self, request):  # noqa: ANN001
        calls.append((self.mission_slug, request.wp_id, request.to_lane))
        return real_transition(self, request)

    with patch.object(aggregate_mod.MissionStatus, "transition", _spy_transition):
        result = runner.invoke(app, _emit_args(slug))

    assert result.exit_code == 0, result.stdout
    assert len(calls) == 1, "MissionStatus.transition must be invoked exactly once"
    assert calls[0] == (slug, "WP01", "claimed")


@patch("specify_cli.cli.commands.agent.status.locate_project_root")
@patch("specify_cli.cli.commands.agent.status._find_mission_slug")
def test_emit_does_not_call_transactional_emit_directly(
    mock_slug,
    mock_root,
    tmp_path: Path,
) -> None:
    """The command must not import/call emit_status_transition_transactional itself.

    Routing must go through the aggregate. We patch the transactional symbol on
    the *aggregate* module (the only legitimate caller) so that if the command
    were calling it directly via its own import it would bypass the spy and the
    event would not be produced through the aggregate.
    """
    slug = "017-test-feature"
    repo = _make_repo_with_mission(tmp_path, slug)
    mock_root.return_value = repo
    mock_slug.return_value = slug

    import specify_cli.coordination.status_transition as status_transition

    real_transactional = status_transition.emit_status_transition_transactional
    seen: list[str] = []

    def _spy_transactional(request, **kwargs):  # noqa: ANN001, ANN003
        # The aggregate enriches feature_dir/mission_slug before delegating.
        seen.append(request.mission_slug or "")
        return real_transactional(request, **kwargs)

    with patch.object(
        status_transition,
        "emit_status_transition_transactional",
        _spy_transactional,
    ):
        result = runner.invoke(app, _emit_args(slug))

    assert result.exit_code == 0, result.stdout
    # The aggregate path reaches the transactional helper exactly once.
    assert seen == [slug]


def test_command_module_has_no_direct_transactional_reference() -> None:
    """Static guard: the command module body has no direct transactional call.

    Reads the source of the status command module and asserts that the
    ``emit_status_transition_transactional`` symbol is not referenced as a call
    anywhere in it (FR-004 review guidance).
    """
    import specify_cli.cli.commands.agent.status as status_cmd

    source = Path(status_cmd.__file__).read_text(encoding="utf-8")
    assert "emit_status_transition_transactional(" not in source


# ---------------------------------------------------------------------------
# T006 — behavior parity with the prior direct transactional path
# ---------------------------------------------------------------------------

_VOLATILE_EVENT_FIELDS = {"event_id", "at"}


def _emit_via_command(repo: Path, slug: str) -> tuple[int, dict]:
    with patch(
        "specify_cli.cli.commands.agent.status.locate_project_root",
        return_value=repo,
    ), patch(
        "specify_cli.cli.commands.agent.status._find_mission_slug",
        return_value=slug,
    ):
        result = runner.invoke(app, _emit_args(slug))
    payload = json.loads(result.stdout) if result.stdout.strip() else {}
    return result.exit_code, payload


def _emit_via_legacy_direct_path(repo: Path, slug: str) -> dict:
    """Reproduce the pre-WP01 behavior: call the transactional helper directly."""
    from specify_cli.coordination.status_transition import (
        emit_status_transition_transactional,
    )
    from specify_cli.status.models import TransitionRequest

    feature_dir = repo / "kitty-specs" / slug
    event = emit_status_transition_transactional(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="codex",
            execution_mode="worktree",
            repo_root=repo,
        )
    )
    return event.to_dict()


def _stable(event_dict: dict) -> dict:
    return {k: v for k, v in event_dict.items() if k not in _VOLATILE_EVENT_FIELDS}


def test_emit_event_fields_match_prior_direct_path(tmp_path: Path) -> None:
    """The StatusEvent emitted by the command matches the prior direct path."""
    slug = "017-test-feature"

    # New path (via command + aggregate).
    repo_new = _make_repo_with_mission(tmp_path / "new", slug)
    captured: list[dict] = []

    import specify_cli.status.aggregate as aggregate_mod

    real_transition = aggregate_mod.MissionStatus.transition

    def _capture_transition(self, request):  # noqa: ANN001
        event = real_transition(self, request)
        captured.append(event.to_dict())
        return event

    with patch.object(aggregate_mod.MissionStatus, "transition", _capture_transition):
        exit_code, payload = _emit_via_command(repo_new, slug)

    assert exit_code == 0, payload
    assert captured, "transition should have produced an event"
    new_event = captured[0]

    # Prior path (direct transactional helper) against an identical fresh repo.
    repo_old = _make_repo_with_mission(tmp_path / "old", slug)
    old_event = _emit_via_legacy_direct_path(repo_old, slug)

    assert _stable(new_event) == _stable(old_event)
    # Sanity-check the load-bearing fields explicitly.
    assert new_event["wp_id"] == "WP01"
    assert new_event["from_lane"] == "planned"
    assert new_event["to_lane"] == "claimed"
    assert new_event["actor"] == "codex"


def test_emit_json_output_contract_is_preserved(tmp_path: Path) -> None:
    """The CLI JSON output keeps its documented contract fields after rewiring."""
    slug = "017-test-feature"
    repo = _make_repo_with_mission(tmp_path, slug)

    exit_code, payload = _emit_via_command(repo, slug)

    assert exit_code == 0, payload
    assert payload["event_id"]
    assert payload["wp_id"] == "WP01"
    assert payload["work_package_id"] == "WP01"
    assert payload["from_lane"] == "planned"
    assert payload["to_lane"] == "claimed"
    assert payload["actor"] == "codex"
    assert payload["status_events_path"] == str(
        repo / "kitty-specs" / slug / "status.events.jsonl"
    )
