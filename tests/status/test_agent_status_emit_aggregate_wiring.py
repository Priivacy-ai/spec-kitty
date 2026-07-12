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
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()


@pytest.fixture(autouse=True)
def _disable_emit_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep these tests focused on local persistence + routing."""
    import specify_cli.status.emit as status_emit

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    monkeypatch.setattr(status_emit, "fire_dossier_sync", lambda *args, **kwargs: None)


from tests.status.conftest import seed_wp_to_planned as _seed_planned_shared


def _seed_planned(feature_dir: Path, slug: str, wp_id: str = "WP01") -> None:
    """Seed a WP out of the non-display 'genesis' state into 'planned'."""
    _seed_planned_shared(feature_dir, wp_id, slug=slug)


def _make_repo_with_mission(root: Path, slug: str) -> Path:
    repo = root / "repo"
    feature_dir = repo / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    (repo / ".kittify").mkdir()
    _seed_planned(feature_dir, slug)
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


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".kittify").mkdir()
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return repo


def _status_event(
    slug: str,
    wp_id: str,
    from_lane: str,
    to_lane: str,
    event_id: str,
) -> dict:
    return {
        "event_id": event_id,
        "mission_slug": slug,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "at": "2026-06-01T12:00:00+00:00",
        "actor": "codex",
        "force": False,
        "execution_mode": "worktree",
        "evidence": None,
        "reason": None,
        "review_ref": None,
        "feature_slug": slug,
    }


def _write_events(feature_dir: Path, events: list[dict]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    feature_dir.joinpath("status.events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )


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


def test_transition_helper_maps_uninitialized_lane_to_genesis(tmp_path: Path) -> None:
    """Aggregate helper resolves an unseeded transactional read to genesis (#1775).

    An unseeded WP is not claimable; resolving to genesis lets the FSM reject the
    claim rather than silently treating the WP as planned.
    """
    from specify_cli.status import TransitionRequest
    from specify_cli.status.aggregate import MissionStatus
    from specify_cli.status.models import Lane

    ms = MissionStatus(
        mission_slug="017-helper-lane",
        mission_id=None,
        mid8="",
        topology="legacy",
        read_dir=tmp_path,
        repo_root=tmp_path,
    )
    request = TransitionRequest(
        wp_id="WP01",
        to_lane="claimed",
        actor="codex",
        feature_dir=tmp_path,
        mission_slug=ms.mission_slug,
    )

    from_lane, current_actor = ms._resolve_current_lane(
        request=request,
        read_current_wp_state_transactional=lambda **_: ("uninitialized", "codex"),
        lane_unseeded=Lane.GENESIS,
    )

    assert from_lane == "genesis"
    assert current_actor == "codex"


def test_transition_helper_prefers_explicit_workspace_context(tmp_path: Path) -> None:
    """Aggregate helper must not overwrite caller-provided workspace context."""
    from specify_cli.status import TransitionRequest
    from specify_cli.status.aggregate import MissionStatus

    ms = MissionStatus(
        mission_slug="017-helper-workspace-context",
        mission_id=None,
        mid8="",
        topology="legacy",
        read_dir=tmp_path,
        repo_root=tmp_path,
    )
    request = TransitionRequest(
        wp_id="WP01",
        to_lane="claimed",
        actor="codex",
        feature_dir=tmp_path,
        mission_slug=ms.mission_slug,
        workspace_context="explicit-context",
    )

    assert ms._resolve_workspace_context(request) == "explicit-context"


def test_transition_helper_infers_missing_review_gate_inputs(tmp_path: Path) -> None:
    """Aggregate helper infers both review-gate booleans on enter-review.

    WP02/T010: the subtasks-completeness read now threads through
    ``resolve_planning_read_dir(..., kind=TASKS_INDEX)`` (PRIMARY-partition),
    landing on ``repo_root / "kitty-specs" / mission_slug`` rather than the
    raw ``self.read_dir`` -- even though this legacy-topology fixture's
    ``read_dir == repo_root == tmp_path`` pre-resolution. Implementation
    evidence is untouched by this WP and still reads ``self.read_dir`` as-is.
    """
    from specify_cli.status import TransitionRequest
    from specify_cli.status.aggregate import MissionStatus
    from specify_cli.status.models import Lane

    ms = MissionStatus(
        mission_slug="017-helper-review-gates",
        mission_id=None,
        mid8="",
        topology="legacy",
        read_dir=tmp_path,
        repo_root=tmp_path,
    )
    request = TransitionRequest(
        wp_id="WP07",
        to_lane="for_review",
        actor="codex",
        feature_dir=tmp_path,
        mission_slug=ms.mission_slug,
    )
    expected_primary_subtasks_dir = tmp_path / "kitty-specs" / ms.mission_slug

    class _StatusEmit:
        @staticmethod
        def _infer_subtasks_complete(read_dir: Path, wp_id: str) -> bool:
            assert read_dir == expected_primary_subtasks_dir
            assert wp_id == "WP07"
            return True

        @staticmethod
        def _infer_implementation_evidence(read_dir: Path, wp_id: str) -> bool:
            assert read_dir == tmp_path
            assert wp_id == "WP07"
            return True

    subtasks_complete, implementation_evidence_present = ms._resolve_review_gate_inputs(
        request=request,
        from_lane_str=str(Lane.IN_PROGRESS),
        resolved_to_lane=str(Lane.FOR_REVIEW),
        status_emit=_StatusEmit,
        lane_in_progress=Lane.IN_PROGRESS,
        lane_for_review=Lane.FOR_REVIEW,
    )

    assert subtasks_complete is True
    assert implementation_evidence_present is True


@patch("specify_cli.cli.commands.agent.status.locate_project_root")
@patch("specify_cli.cli.commands.agent.status._find_mission_slug")
def test_emit_reaches_transition_when_coord_declared_before_worktree_materialized(
    mock_slug,
    mock_root,
    tmp_path: Path,
) -> None:
    """Declared-but-unmaterialized coord topology must not block first write."""
    slug = "demo-feature-01ABCDEF"
    repo = _make_repo_with_mission(tmp_path, slug)
    (repo / "kitty-specs" / slug / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01ABCDEF1234567890123456",
                "coordination_branch": "kitty/mission-demo-feature-01ABCDEF",
                "mission_slug": slug,
            }
        ),
        encoding="utf-8",
    )
    mock_root.return_value = repo
    mock_slug.return_value = slug

    import specify_cli.status.aggregate as aggregate_mod

    calls: list[str] = []

    def _fake_transition(self, request):  # noqa: ANN001
        calls.append(str(self.read_dir))
        return SimpleNamespace(
            event_id="01EVENTID1234567890123456",
            wp_id=request.wp_id,
            from_lane="planned",
            to_lane=request.to_lane,
            actor=request.actor,
        )

    with patch.object(aggregate_mod.MissionStatus, "transition", _fake_transition):
        result = runner.invoke(app, _emit_args(slug))

    assert result.exit_code == 0, result.stdout
    assert calls == [str(repo / "kitty-specs" / slug)]


@patch("specify_cli.cli.commands.agent.status.locate_project_root")
def test_emit_resolves_bare_modern_mission_slug_before_aggregate_load(
    mock_root,
    tmp_path: Path,
) -> None:
    """Bare human slug handles must resolve to post-WP03 ``<slug>-<mid8>`` dirs."""
    full_slug = "bare-fallback-01ABCDEF"
    bare_slug = "bare-fallback"
    repo = _make_repo_with_mission(tmp_path, full_slug)
    (repo / "kitty-specs" / full_slug / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01ABCDEF1234567890123456",
                "coordination_branch": "kitty/mission-bare-fallback-01ABCDEF",
                "mission_slug": full_slug,
            }
        ),
        encoding="utf-8",
    )
    mock_root.return_value = repo

    import specify_cli.status.aggregate as aggregate_mod

    calls: list[tuple[str, str, str]] = []

    def _fake_transition(self, request):  # noqa: ANN001
        calls.append((self.mission_slug, str(self.read_dir), request.mission_slug))
        return SimpleNamespace(
            event_id="01EVENTID1234567890123456",
            wp_id=request.wp_id,
            from_lane="planned",
            to_lane=request.to_lane,
            actor=request.actor,
        )

    with patch.object(aggregate_mod.MissionStatus, "transition", _fake_transition):
        result = runner.invoke(app, _emit_args(bare_slug))

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert calls == [
        (
            full_slug,
            str(repo / "kitty-specs" / full_slug),
            full_slug,
        )
    ]
    assert payload["status_events_path"] == str(
        repo / "kitty-specs" / full_slug / "status.events.jsonl"
    )


@patch("specify_cli.cli.commands.agent.status.locate_project_root")
def test_emit_json_reports_coord_write_target_after_worktree_materialization(
    mock_root,
    tmp_path: Path,
) -> None:
    """Coord-branch writes must report the event log actually affected."""
    slug = "coord-ahead"
    mission_id = "01ABCDEF1234567890123456"
    mid8 = mission_id[:8]
    coord_branch = f"kitty/mission-{slug}-{mid8}"
    repo = _make_git_repo(tmp_path)

    primary_dir = repo / "kitty-specs" / slug
    primary_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "coordination_branch": coord_branch,
                "mission_slug": slug,
            }
        ),
        encoding="utf-8",
    )
    _write_events(
        primary_dir,
        [_status_event(slug, "WP01", "planned", "claimed", "01HXYZ0123456789ABCDEFGH40")],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "primary claimed")

    _git(repo, "checkout", "-b", coord_branch)
    coord_branch_dir = repo / "kitty-specs" / f"{slug}-{mid8}"
    _write_events(
        coord_branch_dir,
        [
            _status_event(slug, "WP01", "planned", "claimed", "01HXYZ0123456789ABCDEFGH41"),
            _status_event(slug, "WP01", "claimed", "in_progress", "01HXYZ0123456789ABCDEFGH42"),
        ],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "coord in progress")
    _git(repo, "checkout", "main")
    mock_root.return_value = repo

    result = runner.invoke(
        app,
        [
            "emit",
            "WP01",
            "--to",
            "for_review",
            "--actor",
            "codex",
            "--mission",
            slug,
            "--subtasks-complete",
            "--implementation-evidence-present",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["from_lane"] == "in_progress"
    assert payload["to_lane"] == "for_review"

    from specify_cli.coordination.workspace import CoordinationWorkspace

    coord_worktree_dir = (
        CoordinationWorkspace.worktree_path(repo, slug, mid8)
        / "kitty-specs"
        / f"{slug}-{mid8}"
    )
    assert payload["status_events_path"] == str(
        coord_worktree_dir / "status.events.jsonl"
    )
    assert (primary_dir / "status.events.jsonl").read_text(encoding="utf-8").count("\n") == 1
    assert (coord_worktree_dir / "status.events.jsonl").read_text(encoding="utf-8").count("\n") == 3
