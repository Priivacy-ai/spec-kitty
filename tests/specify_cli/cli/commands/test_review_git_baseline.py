"""Real-git half of the ``spec-kitty review --mission`` CLI tests (WP06).

Split out of ``test_review.py``: every test here needs an *earned* dead-code
diff baseline, which means a real git repository built with real ``git``
subprocess calls (FR-015 — a zero-symbol scan must mean the scan examined the
right files, not that it matched nothing). That makes the module ``git_repo``
and disqualifies it from ``fast`` — see
``tests/architectural/test_pytest_marker_correctness.py`` (Rules 1 and 2) and
``docs/context/testing-taxonomy.md`` under "Fast" / "Git Repo". The
subprocess-free tests stay ``fast`` in ``test_review.py``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.specify_cli.cli.commands._review_fixtures import (
    MISSING_BASELINE as _MISSING_BASELINE,
)
from tests.specify_cli.cli.commands._review_fixtures import (
    MISSION_SLUG as _MISSION_SLUG,
)
from tests.specify_cli.cli.commands._review_fixtures import (
    build_cli_app as _build_cli_app,
)
from tests.specify_cli.cli.commands._review_fixtures import (
    make_mock_resolved as _make_mock_resolved,
)
from tests.specify_cli.cli.commands._review_fixtures import (
    setup_fixture as _setup_pure_fixture,
)

# ``non_sandbox``: these tests spawn the real git binary, which mutmut's forked
# sandbox cannot host (ADR 2026-04-20-1).
pytestmark = [
    pytest.mark.integration,
    pytest.mark.git_repo,
    pytest.mark.non_sandbox,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_git(
    repo_root: Path,
    *args: str,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=capture_output,
        text=True,
    )


def _init_supported_git_diff(repo_root: Path) -> str:
    """Create an earned clean-scan baseline for review-command fixtures."""
    repo_root.mkdir(parents=True)
    _run_git(repo_root, "init", "-q")
    _run_git(repo_root, "config", "user.name", "Review Test")
    _run_git(repo_root, "config", "user.email", "review-test@example.invalid")
    (repo_root / "README.md").write_text("# review fixture\n", encoding="utf-8")
    _run_git(repo_root, "add", "README.md")
    _run_git(repo_root, "commit", "-qm", "baseline")
    baseline = _run_git(
        repo_root,
        "rev-parse",
        "HEAD",
        capture_output=True,
    ).stdout.strip()
    source_dir = repo_root / "src"
    source_dir.mkdir()
    (source_dir / "review_fixture.py").write_text(
        "REVIEW_FIXTURE = True\n",
        encoding="utf-8",
    )
    _run_git(repo_root, "add", "src/review_fixture.py")
    _run_git(repo_root, "commit", "-qm", "supported change")
    return baseline


def _setup_fixture(
    tmp_path: Path,
    wp_lanes: dict[str, str],
    *,
    baseline_merge_commit: str | None | object = _MISSING_BASELINE,
) -> tuple[Path, Path]:
    """Mission fixture backed by a real git repo with an earned scan baseline.

    Any non-null ``baseline_merge_commit`` the caller names is replaced by a
    real commit SHA from a freshly initialised repository, so the dead-code gate
    has a genuine diff to examine instead of a SHA that resolves to nothing.

    Returns (repo_root, feature_dir).
    """
    repo_root = tmp_path / "repo"

    resolved_baseline = baseline_merge_commit
    if baseline_merge_commit is not _MISSING_BASELINE and baseline_merge_commit is not None:
        resolved_baseline = _init_supported_git_diff(repo_root)

    return _setup_pure_fixture(
        tmp_path,
        wp_lanes,
        baseline_merge_commit=resolved_baseline,
    )


def _write_malformed_review_artifact(feature_dir: Path, wp_id: str) -> Path:
    """Write a review-cycle artifact with legacy string affected_files entries."""
    artifact_dir = feature_dir / "tasks" / f"{wp_id}-regression-harness"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "review-cycle-1.md"
    artifact_path.write_text(
        "---\n"
        "affected_files:\n"
        "  - src/foo.py\n"
        "cycle_number: 1\n"
        f"mission_slug: {_MISSION_SLUG}\n"
        "reviewed_at: '2026-06-05T12:00:00+00:00'\n"
        "reviewer_agent: reviewer-renata\n"
        "verdict: approved\n"
        f"wp_id: {wp_id}\n"
        "---\n"
        "\n"
        "# Review\n",
        encoding="utf-8",
    )
    return artifact_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_review_passes_when_all_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit 0 and verdict: pass when all WPs are done and a baseline_merge_commit is present.

    Modern missions (with ``mission_id`` set) now require ``baseline_merge_commit``
    for lightweight review (issue #989). Provide one so the dead-code gate has a
    real diff baseline; the fixture's changed source set carries no public
    symbols, so the scan is clean because it looked, not because it skipped.
    """
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done", "WP02": "done"},
        baseline_merge_commit="0000000000000000000000000000000000000000",
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

    runner = CliRunner()
    app = _build_cli_app()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

    assert result.exit_code == 0, result.output

    report_path = feature_dir / "mission-review-report.md"
    assert report_path.exists(), "mission-review-report.md was not written"

    content = report_path.read_text(encoding="utf-8")
    assert "verdict: pass" in content
    assert "findings: 0" in content


def test_review_fails_with_schema_diagnostic_for_malformed_review_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review lane gate must not crash on schema-invalid review-cycle frontmatter."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
        baseline_merge_commit="0000000000000000000000000000000000000000",
    )
    _write_malformed_review_artifact(feature_dir, "WP01")

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
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

    assert result.exit_code == 1, result.output
    assert "diagnostic_code: REVIEW_ARTIFACT_SCHEMA_INVALID" in result.output
    assert "affected_files entries must be mappings" in result.output.replace("\n", "")
    assert "Traceback" not in result.output

    report_text = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "review_artifact_schema_invalid" in report_text
    assert "REVIEW_ARTIFACT_SCHEMA_INVALID" in report_text


def test_review_report_frontmatter_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Report file has valid YAML frontmatter with verdict, reviewed_at, findings keys."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
        baseline_merge_commit="0000000000000000000000000000000000000000",
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
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

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


def test_review_post_merge_requires_issue_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-merge mode must fail when issue-matrix.md is missing."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
        baseline_merge_commit="0000000000000000000000000000000000000000",
    )

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.assert_pytest_available",
        lambda _: None,
    )
    _mock_resolved = _make_mock_resolved(feature_dir)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.resolve_mission_handle",
        lambda handle, repo_root: _mock_resolved,
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "post-merge"])

    assert result.exit_code == 1, result.output

    report_text = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "ISSUE_MATRIX_MISSING" in result.output
    assert "issue_matrix_present: false" in report_text


def test_review_post_merge_invalid_issue_matrix_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-merge mode must fail when issue-matrix.md validator diagnostics fire."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
        baseline_merge_commit="0000000000000000000000000000000000000000",
    )
    (feature_dir / "issue-matrix.md").write_text(
        "\n".join(
            [
                "# Issue Matrix",
                "",
                "| issue | verdict | evidence_ref |",
                "|-------|---------|--------------|",
                "| #123 | deferred | commit abc123 |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.assert_pytest_available",
        lambda _: None,
    )
    _mock_resolved = _make_mock_resolved(feature_dir)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.resolve_mission_handle",
        lambda handle, repo_root: _mock_resolved,
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "post-merge"])

    assert result.exit_code == 1, result.output

    report_text = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "ISSUE_MATRIX_VERDICT_UNKNOWN" in result.output
    assert "ISSUE_MATRIX_VERDICT_UNKNOWN" in report_text
    assert "issue_matrix_present: true" in report_text


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

    def _fake_run(  # type: ignore[no-untyped-def]
        cmd,
        cwd=None,
        capture_output=False,
        text=False,
        encoding=None,
        errors=None,
    ):
        # WP01 hermetic-gate preflight: pytest-availability probe. The
        # production path is `assert_pytest_available()` in
        # `specify_cli.cli.commands._test_env_check`, but the monkeypatch
        # below targets `subprocess.run` globally, so this branch must
        # accept the probe shape and report success.
        if len(cmd) == 3 and cmd[1:] == ["-c", "import pytest"]:
            return SimpleNamespace(stdout="", stderr="", returncode=0)
        if cmd[:2] == ["git", "diff"]:
            if "--name-only" in cmd:
                return SimpleNamespace(stdout="src/pkg/example.py\n", returncode=0)
            return SimpleNamespace(
                stdout="+++ b/src/pkg/example.py\n+def PublicSymbol():\n",
                returncode=0,
            )
        raise AssertionError(f"unexpected command: {cmd!r}")

    monkeypatch.setattr("specify_cli.cli.commands.review.subprocess.run", _fake_run)

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

    assert result.exit_code == 0, result.output
    report_path = feature_dir / "mission-review-report.md"
    content = report_path.read_text(encoding="utf-8")
    assert "verdict: pass_with_notes" in content
    assert "dead_code" in content


def test_check_env_skew_warn_branch_prints_mismatch_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Warn-loud (default) divergence prints the mismatch message but does
    NOT exit -- the review command must run through to completion (SC-001).
    """
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done", "WP02": "done"},
        baseline_merge_commit="0000000000000000000000000000000000000000",
    )

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.assert_pytest_available",
        lambda _: None,
    )
    _mock_resolved = _make_mock_resolved(feature_dir)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.resolve_mission_handle",
        lambda handle, repo_root: _mock_resolved,
    )

    from specify_cli.cli.commands.review import PackageSkew

    mismatches = [PackageSkew("typer", "0.24.2", "0.26.0")]
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.assert_typer_click_lock_parity",
        lambda repo_root: mismatches,
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

    assert result.exit_code == 0, result.output
    assert "locked=0.24.2" in result.output
    assert "installed=0.26.0" in result.output

    # The review must have run to completion past the warn-loud preflight,
    # not exited early.
    report_path = feature_dir / "mission-review-report.md"
    assert report_path.exists(), (
        "warn-loud env-skew divergence must not stop the review from running"
    )
