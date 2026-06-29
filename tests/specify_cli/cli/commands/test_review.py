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
_MISSING_BASELINE = object()


def _write_meta(
    feature_dir: Path,
    *,
    baseline_merge_commit: str | None | object = _MISSING_BASELINE,
) -> None:
    """Write a minimal meta.json to feature_dir."""
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "friendly_name": "Test Review Mission",
        "mission_type": "software-dev",
        "mission_number": None,
    }
    if baseline_merge_commit is not _MISSING_BASELINE:
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
    baseline_merge_commit: str | None | object = _MISSING_BASELINE,
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


def _make_uv_runtime(
    tool_dir: Path | None = None,
    is_default_tool_dir: bool = True,
    python: str | None = None,
    platform: str = "posix",
    *,
    requirements: tuple[object, ...] | None = None,
    bin_dir: Path | None = None,
    is_default_bin_dir: bool = True,
) -> object:
    """Return a UV_TOOL InstalledCliRuntime for use in detect_runtime() mocks.

    Args:
        tool_dir: The uv tool directory. Defaults to a sentinel Path when None
            (only needed if is_default_tool_dir=False).
        is_default_tool_dir: Whether tool_dir is the default uv tool dir.
        python: Optional python version override from the receipt.
        platform: "posix" or "windows".
        requirements: uv receipt requirement entries (provenance). Defaults to a
            single bare ``spec-kitty-cli`` entry so the reinstall path preserves
            provenance instead of conservatively refusing.
        bin_dir / is_default_bin_dir: uv tool bin dir provenance.
    """
    from typing import Literal

    from specify_cli.compat._detect.install_method import InstallMethod
    from specify_cli.compat._detect.runtime import (
        InstalledCliRuntime,
        PackageSource,
        UvRequirement,
    )

    resolved_tool_dir = tool_dir if tool_dir is not None else Path("/home/user/.local/share/uv/tools")
    resolved_platform: Literal["posix", "windows"] = "windows" if platform == "windows" else "posix"
    resolved_reqs: tuple[object, ...] = (
        requirements
        if requirements is not None
        else (UvRequirement(name="spec-kitty-cli"),)
    )

    return InstalledCliRuntime(
        install_method=InstallMethod.UV_TOOL,
        executable="/home/user/.local/share/uv/tools/spec-kitty-cli/bin/python",
        receipt_path=resolved_tool_dir / "spec-kitty-cli" / "uv-receipt.toml",
        tool_dir=resolved_tool_dir,
        bin_dir=bin_dir if bin_dir is not None else Path("/home/user/.local/share/uv/bin"),
        is_default_tool_dir=is_default_tool_dir,
        is_default_bin_dir=is_default_bin_dir,
        python=python,
        requirements=resolved_reqs,  # type: ignore[arg-type]
        package_source=PackageSource.PYPI_SPECIFIER,
        platform=resolved_platform,
        safe_for_auto_upgrade=True,
    )


def _uv_req(**kwargs: object) -> object:
    """A spec-kitty-cli uv requirement entry (provenance)."""
    from specify_cli.compat._detect.runtime import UvRequirement

    return UvRequirement(name="spec-kitty-cli", **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_review_passes_when_all_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit 0 and verdict: pass when all WPs are done and a baseline_merge_commit is present.

    Modern missions (with ``mission_id`` set) now require ``baseline_merge_commit``
    for lightweight review (issue #989). Provide one so the dead-code gate has a
    diff baseline; with no real git diff under ``tmp_path`` the scan finds nothing.
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

    from specify_cli.cli.commands.review import review_mission

    runner = CliRunner()
    app = _build_cli_app()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

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


def test_issue_matrix_violation_is_hard_failure(tmp_path: Path) -> None:
    """Report writer must fail-hard on issue-matrix violations."""
    import io

    import typer
    from rich.console import Console

    from specify_cli.cli.commands.review._report import write_review_report

    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)

    findings = [
        {
            "type": "issue_matrix_violation",
            "diagnostic_code": "MISSION_REVIEW_ISSUE_MATRIX_MISSING",
            "message": "issue-matrix.md is required in post-merge mode",
        }
    ]

    with pytest.raises(typer.Exit) as exc_info:
        write_review_report(
            feature_dir,
            repo_root,
            findings,
            Console(file=io.StringIO()),
            mode="post-merge",
            issue_matrix_present=False,
        )

    assert exc_info.value.exit_code == 1
    report_text = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "MISSION_REVIEW_ISSUE_MATRIX_MISSING" in report_text


def test_review_lightweight_modern_missing_baseline_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modern lightweight review must fail when baseline_merge_commit is missing."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
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
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

    assert result.exit_code == 1, result.output

    report_text = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" in result.output
    assert "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" in report_text
    assert "issue_matrix_present: not_applicable" in report_text


def test_review_lightweight_modern_null_baseline_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue #1428: explicit null baseline_merge_commit must fail lightweight review."""
    repo_root, feature_dir = _setup_fixture(
        tmp_path,
        {"WP01": "done"},
        baseline_merge_commit=None,
    )
    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert "baseline_merge_commit" in meta
    assert meta["baseline_merge_commit"] is None

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
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

    assert result.exit_code == 1, result.output

    report_text = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" in result.output
    assert "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" in report_text
    assert (
        "  - id: gate_2\n"
        "    name: dead_code_scan\n"
        "    command: spec-kitty review (internal gate 2)\n"
        "    exit_code: 1\n"
        "    result: fail"
    ) in report_text


def test_dead_code_baseline_missing_is_hard_failure(tmp_path: Path) -> None:
    """Report writer must fail-hard on missing dead-code baselines."""
    import io

    import typer
    from rich.console import Console

    from specify_cli.cli.commands.review._report import write_review_report

    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)

    findings = [
        {
            "type": "dead_code_baseline_missing",
            "diagnostic_code": "LIGHTWEIGHT_REVIEW_MISSING_BASELINE",
            "remediation": "Run `spec-kitty merge` to bake baseline_merge_commit into meta.json.",
        }
    ]

    with pytest.raises(typer.Exit) as exc_info:
        write_review_report(
            feature_dir,
            repo_root,
            findings,
            Console(file=io.StringIO()),
            mode="lightweight",
        )

    assert exc_info.value.exit_code == 1
    report_text = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" in report_text


def test_review_emits_json_diagnostic_when_pytest_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing test extra should fail before selector resolution and print JSON."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )

    from specify_cli.cli.commands.review import TestExtraMissing

    def _raise_missing(_: Path) -> None:
        raise TestExtraMissing("MISSION_REVIEW_TEST_EXTRA_MISSING")

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.assert_pytest_available",
        _raise_missing,
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG])

    assert result.exit_code == 1, result.output
    assert '"diagnostic_code": "MISSION_REVIEW_TEST_EXTRA_MISSING"' in result.output
    assert "uv sync --extra test" in result.output


def test_review_emits_uv_tool_remediation_when_pytest_missing_in_uv_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """uv tool installs must repair the tool interpreter using --extra test."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )

    from specify_cli.cli.commands.review import TestExtraMissing

    def _raise_missing(_: Path) -> None:
        raise TestExtraMissing("MISSION_REVIEW_TEST_EXTRA_MISSING")

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.assert_pytest_available",
        _raise_missing,
    )
    # Mock detect_runtime() to return a UV_TOOL runtime with the default tool dir
    # (no UV_TOOL_DIR env prefix needed when using the default location).
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(),
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG])

    assert result.exit_code == 1, result.output
    assert '"diagnostic_code": "MISSION_REVIEW_TEST_EXTRA_MISSING"' in result.output
    assert "uv tool install --force --with pytest spec-kitty-cli" in result.output
    assert '"remediation": "uv tool install --force --with pytest spec-kitty-cli"' in result.output


def test_uv_tool_remediation_non_default_tool_dir_adds_env_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UV_TOOL installs with a non-default tool_dir emit a UV_TOOL_DIR env prefix.

    Uses a short fixed path so the composed command stays within CHK028's 128-char limit.
    """
    import specify_cli.cli.commands.review as review_mod

    # Short path keeps the composed command within CHK028's 128-char ceiling.
    tool_dir = Path("/opt/uv-tools")
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(tool_dir=tool_dir, is_default_tool_dir=False),
    )

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_dir!s} uv tool install --force --with pytest spec-kitty-cli"
    )


def test_uv_tool_remediation_source_install_falls_back_to_uv_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SOURCE install_method (e.g. dev checkout) falls back to uv sync --extra test."""
    import specify_cli.cli.commands.review as review_mod
    from specify_cli.compat._detect.runtime import InstalledCliRuntime, PackageSource
    from specify_cli.compat._detect.install_method import InstallMethod

    source_runtime = InstalledCliRuntime(
        install_method=InstallMethod.SOURCE,
        executable="/src/venv/bin/python",
        receipt_path=None,
        tool_dir=None,
        bin_dir=None,
        is_default_tool_dir=None,
        is_default_bin_dir=None,
        python=None,
        requirements=(),
        package_source=PackageSource.UNKNOWN,
        platform="posix",
        safe_for_auto_upgrade=False,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: source_runtime,
    )

    assert review_mod._missing_test_extra_remediation() == "uv sync --extra test"  # noqa: SLF001


def test_uv_tool_remediation_uses_with_pytest_not_extra_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UV_TOOL REINSTALL_WITH_TEST injects pytest via --with pytest, preserving source.

    FR-019 / SC-003 / issue #1358: ``--extra test`` would re-pin to PyPI and
    clobber the user's real source; the reinstall path must use ``--with pytest``.
    """
    import specify_cli.cli.commands.review as review_mod

    tool_dir = Path("/opt/uv-t")
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(tool_dir=tool_dir, is_default_tool_dir=False),
    )

    remediation = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert "--with pytest" in remediation
    assert "--extra test" not in remediation
    assert "spec-kitty-cli" in remediation


def test_uv_tool_remediation_preserves_receipt_specifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A receipt version specifier is preserved (not dropped) in the reinstall."""
    import specify_cli.cli.commands.review as review_mod

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(requirements=(_uv_req(specifier="==3.2.0rc25"),)),
    )

    remediation = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert remediation == "uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25"


def test_uv_tool_remediation_with_no_receipt_falls_back_to_uv_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the receipt is absent and install_method is not UV_TOOL, use uv sync."""
    import specify_cli.cli.commands.review as review_mod
    from specify_cli.compat._detect.runtime import InstalledCliRuntime, PackageSource
    from specify_cli.compat._detect.install_method import InstallMethod

    unknown_runtime = InstalledCliRuntime(
        install_method=InstallMethod.UNKNOWN,
        executable=str(tmp_path / "bin" / "python"),
        receipt_path=None,
        tool_dir=None,
        bin_dir=None,
        is_default_tool_dir=None,
        is_default_bin_dir=None,
        python=None,
        requirements=(),
        package_source=PackageSource.UNKNOWN,
        platform="posix",
        safe_for_auto_upgrade=False,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: unknown_runtime,
    )

    assert review_mod._missing_test_extra_remediation() == "uv sync --extra test"  # noqa: SLF001


def test_uv_tool_remediation_preserves_custom_bin_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UV_TOOL with a non-default bin_dir emits a UV_TOOL_BIN_DIR env prefix.

    The reinstall must not relocate the shim out of the user's custom bin dir
    (legacy parity); short fixed paths keep the command within CHK028's limit.
    """
    import specify_cli.cli.commands.review as review_mod

    tool_dir = Path("/opt/uv-t")
    bin_dir = Path("/opt/bin")
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(
            tool_dir=tool_dir,
            is_default_tool_dir=False,
            bin_dir=bin_dir,
            is_default_bin_dir=False,
        ),
    )

    result = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert result == (
        "UV_TOOL_DIR=/opt/uv-t UV_TOOL_BIN_DIR=/opt/bin uv tool install --force "
        "--with pytest spec-kitty-cli"
    )


def test_uv_tool_remediation_preserves_receipt_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reinstall remediation must keep the uv tool Python interpreter.

    Uses a short fixed path so the composed command stays within CHK028's 128-char limit.
    """
    import specify_cli.cli.commands.review as review_mod

    # Short path keeps the composed command within CHK028's 128-char ceiling.
    tool_dir = Path("/opt/uv")
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(
            tool_dir=tool_dir, is_default_tool_dir=False, python="3.13"
        ),
    )

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_dir!s} uv tool install --force --python 3.13 "
        "--with pytest spec-kitty-cli"
    )


def test_uv_tool_remediation_uses_powershell_env_prefix_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows path with spaces causes CHK028 violation; degrades to note fallback."""
    import specify_cli.cli.commands.review as review_mod

    # A path with a space triggers the CHK028 violation in render("windows")
    # because $env:KEY='value with space'; contains chars outside the allowed set.
    tool_dir = tmp_path / "tool dir"  # has a space
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(
            tool_dir=tool_dir, is_default_tool_dir=False, platform="windows"
        ),
    )

    # render("windows") raises ValueError (CHK028) → note fallback carrying the
    # safe provenance guidance (not a clobbering command).
    result = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert "could not preserve uv receipt provenance" in result


def test_uv_tool_remediation_windows_default_tool_dir_no_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows UV_TOOL with default tool_dir (no env) renders a valid CHK028 command."""
    import specify_cli.cli.commands.review as review_mod

    # Default tool_dir → env={} → no $env: prefix → CHK028 passes
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(platform="windows"),
    )

    result = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert result == "uv tool install --force --with pytest spec-kitty-cli"


def test_uv_tool_remediation_quotes_specifier_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A CHK028-safe receipt specifier (==) is preserved in the reinstall command.

    Uses a short fixed path so the composed command stays within CHK028's 128-char limit.
    """
    import specify_cli.cli.commands.review as review_mod

    tool_dir = Path("/opt/uv-t")
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(
            tool_dir=tool_dir,
            is_default_tool_dir=False,
            requirements=(_uv_req(specifier="==3.2.0rc25"),),
        ),
    )

    remediation = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert remediation == (
        "UV_TOOL_DIR=/opt/uv-t uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_omits_uv_tool_dir_for_default_tool_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default uv tool installs should keep the short copy/paste command."""
    import specify_cli.cli.commands.review as review_mod

    # is_default_tool_dir=True → env={} → no UV_TOOL_DIR prefix
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_runtime",
        lambda: _make_uv_runtime(),  # default: is_default_tool_dir=True
    )

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        "uv tool install --force --with pytest spec-kitty-cli"
    )


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
        # WP01 hermetic-gate preflight: pytest-availability probe. The
        # production path is `assert_pytest_available()` in
        # `specify_cli.cli.commands._test_env_check`, but the monkeypatch
        # below targets `subprocess.run` globally, so this branch must
        # accept the probe shape and report success.
        if len(cmd) == 3 and cmd[1:] == ["-c", "import pytest"]:
            return SimpleNamespace(stdout="", stderr="", returncode=0)
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
    result = runner.invoke(app, ["--mission", _MISSION_SLUG, "--mode", "lightweight"])

    assert result.exit_code == 0, result.output
    report_path = feature_dir / "mission-review-report.md"
    content = report_path.read_text(encoding="utf-8")
    assert "verdict: pass_with_notes" in content
    assert "dead_code" in content
