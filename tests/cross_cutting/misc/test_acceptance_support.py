from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

import acceptance_support as acc
import task_helpers as th
from specify_cli import app as cli_app

pytestmark = [pytest.mark.integration]

ACCEPTANCE_MODE_CHECKLIST = "checklist"
runner = CliRunner()


def _write_acceptance_meta(feature_repo: Path, mission_slug: str) -> None:
    feature_dir = feature_repo / "kitty-specs" / mission_slug
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01KNXQS9ATWWFXS3K5ZJ9E5008",
                "mission_slug": mission_slug,
                "mission_number": 1,
                "slug": mission_slug,
                "friendly_name": "Demo Feature",
                "mission_type": "software-dev",
                "target_branch": "main",
                "created_at": "2026-05-27T00:00:00+00:00",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _approve_wp(feature_repo: Path, mission_slug: str, wp_id: str) -> None:
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.models import ReviewResult

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    for lane in ("claimed", "in_progress", "for_review", "in_review"):
        emit_status_transition(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            to_lane=lane,
            actor="test-agent",
            repo_root=feature_repo,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        to_lane="approved",
        actor="reviewer-agent",
        evidence={
            "review": {
                "reviewer": "reviewer-agent",
                "verdict": "approved",
                "reference": f"review:{wp_id}",
            }
        },
        review_result=ReviewResult(
            reviewer="reviewer-agent",
            verdict="approved",
            reference=f"review:{wp_id}",
        ),
        repo_root=feature_repo,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )


def test_collect_feature_summary_reports_metadata_issue(feature_repo: Path, mission_slug: str) -> None:
    # WP files now live in flat tasks/ directory
    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    from tests.utils import run_tasks_cli

    # Use 'update' command (renamed from 'move')
    run_tasks_cli(["update", mission_slug, "WP01", "doing", "--force"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, mission_slug)
    assert any("missing assignee" in issue for issue in summary.metadata_issues)


def test_detect_mission_slug_prefers_explicit(
    feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Auto-detection removed; must pass explicit_feature
    assert acc.detect_mission_slug(feature_repo, explicit_feature=mission_slug) == mission_slug


def test_detect_mission_slug_raises_without_explicit(feature_repo: Path, mission_slug: str) -> None:
    # Without explicit_feature, must raise AcceptanceError (auto-detection removed)
    with pytest.raises(acc.AcceptanceError, match="Mission slug is required"):
        acc.detect_mission_slug(feature_repo)


def test_perform_acceptance_without_commit(feature_repo: Path, mission_slug: str) -> None:
    from tests.utils import run_tasks_cli

    from tests.utils import run

    # Use 'update' command (renamed from 'move')
    run_tasks_cli(["update", mission_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    run_tasks_cli(["update", mission_slug, "WP01", "done", "--force"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert summary.lanes["planned"] == []
    assert summary.lanes.get("doing", summary.lanes.get("in_progress", [])) == []
    assert summary.lanes["for_review"] == []
    assert summary.metadata_issues == []
    assert summary.activity_issues == []

    result = acc.perform_acceptance(
        summary, mode=ACCEPTANCE_MODE_CHECKLIST, actor="Tester", auto_commit=False
    )
    payload = result.to_dict()
    assert payload["accepted_by"] == "Tester"
    assert payload["mode"] == ACCEPTANCE_MODE_CHECKLIST


def test_accept_command_closes_approved_wps(feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.status.emit as status_emit
    from tests.utils import run, write_wp

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    write_wp(feature_repo, mission_slug, "planned", "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add second WP and meta"], cwd=feature_repo)

    _approve_wp(feature_repo, mission_slug, "WP01")
    _approve_wp(feature_repo, mission_slug, "WP02")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Approve WPs"], cwd=feature_repo)

    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--mode",
            "local",
            "--actor",
            "tester",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "to_lane in {'approved', 'done'} requires evidence" not in result.output
    payload = json.loads(result.output)
    assert payload["closed_wps"] == ["WP01", "WP02"]
    assert payload["already_done_wps"] == []
    assert payload["summary"]["lanes"]["approved"] == []
    assert payload["summary"]["lanes"]["done"] == ["WP01", "WP02"]

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert summary.lanes["approved"] == []
    assert summary.lanes["done"] == ["WP01", "WP02"]


def test_accept_no_commit_reports_would_close_without_mutation(feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.status.emit as status_emit
    from specify_cli.status.store import read_events
    from tests.utils import run

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add meta"], cwd=feature_repo)
    _approve_wp(feature_repo, mission_slug, "WP01")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Approve WP01"], cwd=feature_repo)

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    before_events = len(read_events(feature_dir))
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        [
            "accept",
            "--mission",
            mission_slug,
            "--mode",
            "local",
            "--actor",
            "tester",
            "--json",
            "--no-commit",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["closed_wps"] == []
    assert payload["would_close_wps"] == ["WP01"]
    assert len(read_events(feature_dir)) == before_events
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert summary.lanes["approved"] == ["WP01"]


def test_accept_rejects_approved_wp_without_evidence(feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Accept must refuse to close a WP that reached approved without review evidence."""
    import specify_cli.status.emit as status_emit
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.store import read_events
    from tests.utils import run

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add meta"], cwd=feature_repo)

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    for lane in ("claimed", "in_progress", "for_review", "in_review"):
        emit_status_transition(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id="WP01",
            to_lane=lane,
            actor="test-agent",
            repo_root=feature_repo,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id="WP01",
        to_lane="approved",
        actor="force-user",
        force=True,
        reason="Expedited approval without review",
        repo_root=feature_repo,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Force-approve WP01"], cwd=feature_repo)

    before_events = len(read_events(feature_dir))
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        ["accept", "--mission", mission_slug, "--mode", "local", "--actor", "tester", "--json"],
    )

    assert result.exit_code == 1
    assert "no review evidence" in result.output
    assert len(read_events(feature_dir)) == before_events


def test_accept_protected_branch_no_mutation(feature_repo: Path, mission_slug: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Protected-branch guard must reject BEFORE any status mutation."""
    import specify_cli.status.emit as status_emit
    from specify_cli.git.commit_helpers import assert_not_protected_branch, ProtectedBranchCommitError
    from specify_cli.status.store import read_events
    from tests.utils import run

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    _write_acceptance_meta(feature_repo, mission_slug)
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Add meta"], cwd=feature_repo)

    _approve_wp(feature_repo, mission_slug, "WP01")
    run(["git", "add", "."], cwd=feature_repo)
    run(["git", "commit", "-m", "Approve WP01"], cwd=feature_repo)

    feature_dir = feature_repo / "kitty-specs" / mission_slug
    before_events = len(read_events(feature_dir))

    def _always_reject(repo_path, *, operation="commit"):
        raise ProtectedBranchCommitError(
            f"Refusing to {operation} on protected branch 'main'"
        )

    monkeypatch.setattr(
        "specify_cli.cli.commands.accept.assert_not_protected_branch",
        _always_reject,
    )
    monkeypatch.chdir(feature_repo)
    result = runner.invoke(
        cli_app,
        ["accept", "--mission", mission_slug, "--mode", "local", "--actor", "tester", "--json"],
    )

    assert result.exit_code == 1
    assert "Refusing" in result.output or "protected branch" in result.output.lower()
    assert len(read_events(feature_dir)) == before_events


def test_collect_feature_summary_encoding_error(feature_repo: Path, mission_slug: str) -> None:
    plan_path = feature_repo / "kitty-specs" / mission_slug / "plan.md"
    data = plan_path.read_bytes() + b"\x92"
    plan_path.write_bytes(data)

    with pytest.raises(acc.ArtifactEncodingError) as excinfo:
        acc.collect_feature_summary(feature_repo, mission_slug)

    assert str(plan_path) in str(excinfo.value)


def test_normalize_feature_encoding(feature_repo: Path, mission_slug: str) -> None:
    plan_path = feature_repo / "kitty-specs" / mission_slug / "plan.md"
    data = plan_path.read_bytes() + b"\x92"
    plan_path.write_bytes(data)

    cleaned = acc.normalize_feature_encoding(feature_repo, mission_slug)
    assert plan_path in cleaned
    # Should now be readable as UTF-8 without errors.
    plan_path.read_text(encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, mission_slug)
    assert summary.feature == mission_slug


# T039: Test that done WPs don't require assignee (Bug #119)
def test_acceptance_succeeds_for_done_wp_without_assignee(feature_repo: Path, mission_slug: str) -> None:
    """Done WPs should not require assignee."""
    from tests.utils import run_tasks_cli, run

    # Move WP01 to done without assignee
    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    run_tasks_cli(["update", mission_slug, "WP01", "done", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to done without assignee"], cwd=feature_repo)

    # Strict validation should NOT complain about missing assignee for done lane
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert not any("missing assignee" in issue for issue in summary.metadata_issues), (
        "Done WPs should not require assignee"
    )


# T040: Test that doing/for_review WPs still require assignee (Bug #119)
def test_assignee_still_required_for_active_lanes(feature_repo: Path, mission_slug: str) -> None:
    """Doing and for_review WPs should still require assignee."""
    from tests.utils import run_tasks_cli, run

    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"

    # Test doing lane
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    run_tasks_cli(["update", mission_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to doing without assignee"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing assignee" in issue for issue in summary.metadata_issues), (
        "Doing lane should still require assignee"
    )

    # Test for_review lane
    run_tasks_cli(["update", mission_slug, "WP01", "for_review", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to for_review without assignee"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing assignee" in issue for issue in summary.metadata_issues), (
        "For_review lane should still require assignee"
    )


# T041: Test required fields still enforced for active lanes
def test_required_fields_still_enforced(feature_repo: Path, mission_slug: str) -> None:
    """Agent and shell_pid should still be required for active lanes.

    Note: lane is now tracked via the event log (not frontmatter), so removing
    lane: from frontmatter no longer produces a metadata_issue.
    """
    from tests.utils import run_tasks_cli, run

    wp_path = feature_repo / "kitty-specs" / mission_slug / "tasks" / "WP01.md"

    # Test missing agent - move to doing first, then remove agent field manually
    run_tasks_cli(["update", mission_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)

    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines_no_agent = [line for line in front.splitlines() if not line.startswith("agent:")]
    wp_path.write_text(th.build_document("\n".join(lines_no_agent), body, padding), encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing agent" in issue for issue in summary.metadata_issues), "Agent should still be required"

    # Test missing shell_pid - restore agent, remove shell_pid
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines_with_agent = front.splitlines()
    if not any(line.startswith("agent:") for line in lines_with_agent):
        lines_with_agent.insert(0, "agent: test-agent")
    lines_no_pid = [line for line in lines_with_agent if not line.startswith("shell_pid:")]
    wp_path.write_text(th.build_document("\n".join(lines_no_pid), body, padding), encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, mission_slug, strict_metadata=True)
    assert any("missing shell_pid" in issue for issue in summary.metadata_issues), "Shell_pid should still be required"
