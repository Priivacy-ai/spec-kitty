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
    """uv tool installs must repair the tool interpreter, not the consumer repo."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.find_repo_root",
        lambda: repo_root,
    )

    from specify_cli.cli.commands.review import InstallMethod, TestExtraMissing

    def _raise_missing(_: Path) -> None:
        raise TestExtraMissing("MISSION_REVIEW_TEST_EXTRA_MISSING")

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.assert_pytest_available",
        _raise_missing,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.get_version",
        lambda: "3.2.0rc25",
    )

    app = _build_cli_app()
    runner = CliRunner()
    result = runner.invoke(app, ["--mission", _MISSION_SLUG])

    assert result.exit_code == 1, result.output
    assert '"diagnostic_code": "MISSION_REVIEW_TEST_EXTRA_MISSING"' in result.output
    assert "uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25" in result.output
    assert '"remediation": "uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25"' in result.output


def test_uv_tool_remediation_preserves_directory_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local directory uv tool installs must not be rewritten to a PyPI pin."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    source_dir = tmp_path / "source-checkout"
    source_dir.mkdir()
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        f'requirements = [{{ name = "spec-kitty-cli", directory = "{source_dir}" }}]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force --with pytest {source_dir!s}"
    )


def test_uv_tool_remediation_prefers_active_receipt_over_source_detection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A uv-tool executable must repair the tool even when cwd looks like source."""
    import specify_cli.cli.commands.review as review_mod

    repo_root = Path(__file__).resolve().parents[4]
    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "spec-kitty-cli", specifier = "==3.2.0rc25" }]\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod.detect_install_method() == review_mod.InstallMethod.SOURCE
    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} "
        "uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_preserves_git_receipt_and_existing_with(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git uv tool installs must preserve source provenance and injected deps."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        "requirements = [\n"
        '  { name = "spec-kitty-cli", git = "file:///tmp/spec-kitty" },\n'
        '  { name = "click" },\n'
        "]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force --with click "
        "--with pytest spec-kitty-cli --from git+file:///tmp/spec-kitty"
    )


def test_uv_tool_remediation_preserves_editable_with_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Injected editable deps must stay editable when pytest is added."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    extra_dir = tmp_path / "extra-dep"
    extra_dir.mkdir()
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        "requirements = [\n"
        '  { name = "spec-kitty-cli", specifier = "==3.2.0rc25" },\n'
        f'  {{ name = "extra-dep", editable = "{extra_dir}" }},\n'
        "]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force "
        f"--with-editable {extra_dir!s} --with pytest spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_does_not_duplicate_existing_pytest_with(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing pytest injection should not become duplicate --with pytest."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        "requirements = [\n"
        '  { name = "spec-kitty-cli", specifier = "==3.2.0rc25" },\n'
        '  { name = "pytest" },\n'
        "]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force --with pytest "
        "spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_with_unmapped_receipt_does_not_pin_to_pypi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Present-but-unmapped receipts must fail conservative, not rewrite source."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "other-tool" }]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.get_version",
        lambda: "3.2.0rc25",
    )

    remediation = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert "spec-kitty-cli==3.2.0rc25" not in remediation
    assert "same uv tool source" in remediation


def test_uv_tool_remediation_with_unsupported_main_requirement_is_conservative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown main-package receipt shapes must not collapse to PyPI names."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "spec-kitty-cli", unknown-source = "opaque" }]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.get_version",
        lambda: "3.2.0rc25",
    )

    remediation = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert "uv tool install --force" not in remediation
    assert "spec-kitty-cli==3.2.0rc25" not in remediation
    assert "same uv tool source" in remediation


def test_uv_tool_remediation_with_unsupported_existing_dep_is_conservative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown injected deps must not be silently dropped from remediation."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        "requirements = [\n"
        '  { name = "spec-kitty-cli", specifier = "==3.2.0rc25" },\n'
        '  { name = "extra-dep", unknown-source = "opaque" },\n'
        "]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.get_version",
        lambda: "3.2.0rc25",
    )

    remediation = review_mod._missing_test_extra_remediation()  # noqa: SLF001
    assert "uv tool install --force" not in remediation
    assert "extra-dep" not in remediation
    assert "same uv tool source" in remediation


def test_uv_tool_remediation_preserves_url_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wheel URL uv tool installs must stay URL-based when adding pytest."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "spec-kitty-cli", url = "https://example.test/pkg.whl" }]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} "
        "uv tool install --force --with pytest https://example.test/pkg.whl"
    )


def test_uv_tool_remediation_preserves_url_with_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Injected URL deps must not be dropped when pytest is added."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        "requirements = [\n"
        '  { name = "spec-kitty-cli", specifier = "==3.2.0rc25" },\n'
        '  { name = "extra-dep", url = "https://example.test/extra.whl" },\n'
        "]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force "
        "--with https://example.test/extra.whl --with pytest spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_preserves_editable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Editable uv tool installs must stay editable when adding pytest."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    source_dir = tmp_path / "source-checkout"
    source_dir.mkdir()
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        f'requirements = [{{ name = "spec-kitty-cli", editable = "{source_dir}" }}]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force --with pytest --editable {source_dir!s}"
    )


def test_uv_tool_remediation_preserves_custom_bin_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reinstall remediation must not move shims out of a custom uv bin dir."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    shim_dir = tmp_path / "custom-bin"
    shim_dir.mkdir()
    shim_path = shim_dir / "spec-kitty"
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "spec-kitty-cli", specifier = "==3.2.0rc25" }]\n'
        "entrypoints = [\n"
        f'  {{ name = "spec-kitty", install-path = "{shim_path}" }},\n'
        "]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} UV_TOOL_BIN_DIR={shim_dir!s} "
        "uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_preserves_receipt_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reinstall remediation must keep the uv tool Python interpreter."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "spec-kitty-cli", specifier = "==3.2.0rc25" }]\n'
        'python = "3.13"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force --python 3.13 --with pytest spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_uses_powershell_env_prefix_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows remediation must be pasteable in PowerShell, not POSIX-only."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool dir" / "spec-kitty-cli"
    bin_dir = tool_env / "Scripts"
    bin_dir.mkdir(parents=True)
    shim_dir = tmp_path / "custom bin"
    shim_dir.mkdir()
    shim_path = shim_dir / "spec-kitty.exe"
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "spec-kitty-cli", specifier = "==3.2.0rc25" }]\n'
        "entrypoints = [\n"
        f'  {{ name = "spec-kitty", install-path = "{shim_path}" }},\n'
        "]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python.exe"))
    monkeypatch.setattr(review_mod.sys, "platform", "win32")

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"$env:UV_TOOL_DIR='{tool_env.parent!s}'; "
        f"$env:UV_TOOL_BIN_DIR='{shim_dir!s}'; "
        "uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25"
    )


def test_uv_tool_remediation_quotes_specifier_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Specifier receipts must remain copy/paste safe in POSIX shells."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = tmp_path / "tool" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"
    bin_dir.mkdir(parents=True)
    (tool_env / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "spec-kitty-cli", specifier = ">=3.0" }]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        f"UV_TOOL_DIR={tool_env.parent!s} uv tool install --force --with pytest 'spec-kitty-cli>=3.0'"
    )


def test_uv_tool_remediation_omits_uv_tool_dir_for_default_tool_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default uv tool installs should keep the short copy/paste command."""
    import specify_cli.cli.commands.review as review_mod

    tool_env = Path.home() / ".local" / "share" / "uv" / "tools" / "spec-kitty-cli"
    bin_dir = tool_env / "bin"

    # Stub out all receipt-based paths so the function reaches detect_install_method.
    # A real uv receipt on disk short-circuits the function before the mocked
    # detect_install_method / get_version are ever reached without these stubs.
    monkeypatch.setattr(
        "specify_cli.cli.commands.review._uv_tool_reinstall_command",
        lambda: None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review._active_uv_tool_receipt_has_spec_kitty",
        lambda: False,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review._active_uv_tool_receipt_path",
        lambda: None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.detect_install_method",
        lambda: review_mod.InstallMethod.UV_TOOL,
    )
    monkeypatch.setattr(review_mod.sys, "executable", str(bin_dir / "python"))
    monkeypatch.setattr(
        "specify_cli.cli.commands.review.get_version",
        lambda: "3.2.0rc25",
    )

    assert review_mod._missing_test_extra_remediation() == (  # noqa: SLF001
        "uv tool install --force --with pytest spec-kitty-cli==3.2.0rc25"
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
