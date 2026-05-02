"""Integration tests for the ``spec-kitty review --mission`` command (WP06).

These tests exercise the command end-to-end using a temporary filesystem
fixture and verify:

- Exit 0 + verdict: pass when all WPs are in done and no findings
- Exit 1 + verdict: fail when any WP is not in done
- Report file has valid frontmatter with expected keys
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MISSION_SLUG = "test-review-mission-01KQTEST0"
_MISSION_ID = "01KQTEST000000000000000000"


def _write_meta(feature_dir: Path, *, baseline_merge_commit: str | None = None) -> None:
    """Write a minimal meta.json to feature_dir."""
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "friendly_name": "Test Review Mission",
        "mission_type": "software-dev",
        "mission_number": None,
    }
    if baseline_merge_commit is not None:
        meta["baseline_merge_commit"] = baseline_merge_commit
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _seed_wp_event(
    feature_dir: Path,
    wp_id: str,
    to_lane: str,
    event_id: str,
) -> None:
    """Append a single status event taking a WP directly to *to_lane*."""
    from_lane = "planned" if to_lane != "planned" else "planned"
    event = StatusEvent(
        event_id=event_id,
        mission_slug=_MISSION_SLUG,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at="2026-04-30T12:00:00+00:00",
        actor="test-agent",
        force=False,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _build_cli_app():
    """Return a Typer app with the review command as the default command."""
    import typer

    from specify_cli.cli.commands.review import review_mission

    app = typer.Typer()
    # Register as the default (unnamed) command so runner.invoke(app, ["--mission", ...]) works
    app.command()(review_mission)
    return app


def _setup_fixture(
    tmp_path: Path,
    wp_lanes: dict[str, str],
    *,
    baseline_merge_commit: str | None = None,
) -> tuple[Path, Path]:
    """Create a minimal mission fixture.

    Returns (repo_root, feature_dir).
    """
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG

    _write_meta(feature_dir, baseline_merge_commit=baseline_merge_commit)

    for idx, (wp_id, lane) in enumerate(wp_lanes.items()):
        event_id = f"01KQTEST{idx:018d}"
        _seed_wp_event(feature_dir, wp_id, lane, event_id)

    return repo_root, feature_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_review_passes_when_all_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit 0 and verdict: pass when all WPs are done, no dead-code scan (no baseline)."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done", "WP02": "done"},
    )

    # Patch find_repo_root to return our tmp repo
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )
    # Patch mission resolver to return a resolved mission pointing at feature_dir
    _mock_resolved = _make_mock_resolved(feature_dir)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.resolve_mission_handle",
        lambda handle, repo_root: _mock_resolved,
    )

    from specify_cli.cli.commands.review import review_mission

    runner = CliRunner()
    app = _build_cli_app()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG])

    assert result.exit_code == 0, result.output

    report_path = feature_dir / "mission-review-report.md"
    assert report_path.exists(), "mission-review-report.md was not written"

    content = report_path.read_text(encoding="utf-8")
    assert "verdict: pass" in content
    assert "findings: 0" in content


def test_review_fails_when_wp_not_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit 1 and verdict: fail when a WP is in in_progress."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "in_progress", "WP02": "done"},
    )

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )
    _mock_resolved = _make_mock_resolved(feature_dir)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.resolve_mission_handle",
        lambda handle, repo_root: _mock_resolved,
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG])

    assert result.exit_code == 1, result.output

    report_path = feature_dir / "mission-review-report.md"
    assert report_path.exists(), "mission-review-report.md was not written"

    content = report_path.read_text(encoding="utf-8")
    assert "verdict: fail" in content
    # WP01 must appear in findings
    assert "WP01" in content


def test_review_report_frontmatter_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Report file has valid YAML frontmatter with verdict, reviewed_at, findings keys."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
    )

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )
    _mock_resolved = _make_mock_resolved(feature_dir)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.resolve_mission_handle",
        lambda handle, repo_root: _mock_resolved,
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG])

    assert result.exit_code == 0, result.output

    report_path = feature_dir / "mission-review-report.md"
    content = report_path.read_text(encoding="utf-8")

    # Must start with frontmatter delimiters
    assert content.startswith("---\n"), f"Expected frontmatter, got: {content[:80]!r}"

    # Parse the frontmatter block manually
    lines = content.splitlines()
    end_idx = lines.index("---", 1)
    fm_lines = lines[1:end_idx]
    fm_dict: dict[str, str] = {}
    for fl in fm_lines:
        key, _, value = fl.partition(": ")
        fm_dict[key.strip()] = value.strip()

    assert "verdict" in fm_dict, f"Missing 'verdict' in frontmatter: {fm_dict}"
    assert "reviewed_at" in fm_dict, f"Missing 'reviewed_at' in frontmatter: {fm_dict}"
    assert "findings" in fm_dict, f"Missing 'findings' in frontmatter: {fm_dict}"
    assert fm_dict["verdict"] in ("pass", "pass_with_notes", "fail"), (
        f"Invalid verdict: {fm_dict['verdict']}"
    )
    # reviewed_at must look like an ISO timestamp
    assert "T" in fm_dict["reviewed_at"] and "+" in fm_dict["reviewed_at"], (
        f"reviewed_at not ISO 8601: {fm_dict['reviewed_at']!r}"
    )
    assert fm_dict["findings"].isdigit(), f"findings must be integer, got: {fm_dict['findings']!r}"


def test_review_exits_2_when_mission_is_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit code 2 when --mission flag is empty."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", ""])

    assert result.exit_code == 2, result.output


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _make_mock_resolved(feature_dir: Path) -> object:
    """Return a minimal ResolvedMission-like object for monkeypatching."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _MockResolved:
        mission_id: str
        mission_slug: str
        feature_dir: Path
        mid8: str

    return _MockResolved(
        mission_id=_MISSION_ID,
        mission_slug=_MISSION_SLUG,
        feature_dir=feature_dir,
        mid8=_MISSION_ID[:8],
    )


def test_review_passes_with_notes_when_dead_code_scan_finds_symbol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
        baseline_merge_commit="abc123",
    )

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )
    _mock_resolved = _make_mock_resolved(feature_dir)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.resolve_mission_handle",
        lambda handle, repo_root: _mock_resolved,
    )

    from types import SimpleNamespace

    def _fake_run(cmd, cwd=None, capture_output=False, text=False):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["git", "diff"]:
            return SimpleNamespace(
                stdout="+++ b/src/pkg/example.py\n+def PublicSymbol():\n",
                returncode=0,
            )
        if cmd[:3] == ["grep", "-r", "--include=*.py"]:
            return SimpleNamespace(stdout="", returncode=1)
        if cmd[:2] == ["grep", "-rn"]:
            return SimpleNamespace(stdout="", returncode=1)
        raise AssertionError(f"unexpected command: {cmd!r}")

    monkeypatch.setattr("specify_cli.cli.commands.review.subprocess.run", _fake_run)

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG])

    assert result.exit_code == 0, result.output
    report_path = feature_dir / "mission-review-report.md"
    content = report_path.read_text(encoding="utf-8")
    assert "verdict: pass_with_notes" in content
    assert "dead_code" in content
