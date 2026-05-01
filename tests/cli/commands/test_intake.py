"""Integration tests for the ``spec-kitty intake`` CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.mission_brief import BRIEF_SOURCE_FILENAME, MISSION_BRIEF_FILENAME

# non_sandbox: intake --show CWD walk-up escapes tmp_path in mutmut's forked sandbox
# and finds the also_copy'd .kittify/; passes in normal pytest. See ADR 2026-04-20-1.
pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]

runner = CliRunner()

PLAN_CONTENT = "# My Plan\n\nDo the thing.\n"


def test_intake_file_writes_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """intake <file> exits 0 and creates both .kittify/ artefacts."""
    monkeypatch.chdir(tmp_path)
    plan_file = tmp_path / "PLAN.md"
    plan_file.write_text(PLAN_CONTENT)

    result = runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)

    assert result.exit_code == 0
    assert (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).exists()
    assert (tmp_path / ".kittify" / BRIEF_SOURCE_FILENAME).exists()


def test_intake_file_content_in_brief(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Original content is present in mission-brief.md after intake."""
    monkeypatch.chdir(tmp_path)
    plan_file = tmp_path / "PLAN.md"
    plan_file.write_text(PLAN_CONTENT)

    runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)

    brief_text = (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).read_text(encoding="utf-8")
    assert PLAN_CONTENT in brief_text


def test_intake_stdin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """intake - reads from stdin and records source_file as 'stdin'."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["intake", "-"],
        input="my plan content\n",
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).exists()

    import yaml  # noqa: PLC0415

    source = yaml.safe_load(
        (tmp_path / ".kittify" / BRIEF_SOURCE_FILENAME).read_text(encoding="utf-8")
    )
    assert source["source_file"] == "stdin"


def test_intake_force_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--force allows overwriting an existing brief."""
    monkeypatch.chdir(tmp_path)
    plan_file = tmp_path / "PLAN.md"
    plan_file.write_text(PLAN_CONTENT)

    result1 = runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)
    assert result1.exit_code == 0

    plan_file.write_text("# Updated Plan\n\nNew content.\n")
    result2 = runner.invoke(app, ["intake", "--force", str(plan_file)], catch_exceptions=False)
    assert result2.exit_code == 0

    brief_text = (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).read_text(encoding="utf-8")
    assert "Updated Plan" in brief_text
    assert "New content." in brief_text


def test_intake_no_force_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second intake without --force exits 1; original file is unchanged."""
    monkeypatch.chdir(tmp_path)
    plan_file = tmp_path / "PLAN.md"
    plan_file.write_text(PLAN_CONTENT)

    result1 = runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)
    assert result1.exit_code == 0

    original_brief = (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).read_text(encoding="utf-8")

    plan_file.write_text("# Different content\n")
    result2 = runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)
    assert result2.exit_code == 1

    current_brief = (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).read_text(encoding="utf-8")
    assert current_brief == original_brief


def test_intake_show_prints_brief(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--show prints the provenance info and brief content; exits 0."""
    monkeypatch.chdir(tmp_path)
    plan_file = tmp_path / "PLAN.md"
    plan_file.write_text(PLAN_CONTENT)

    runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)

    result = runner.invoke(app, ["intake", "--show"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Source:" in result.output or PLAN_CONTENT in result.output


def test_intake_show_no_brief_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--show exits 1 when no brief has been written."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["intake", "--show"], catch_exceptions=False)
    assert result.exit_code == 1


def test_intake_missing_file_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """intake with a non-existent file exits 1 and writes no artefacts."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["intake", "nonexistent.md"], catch_exceptions=False)
    assert result.exit_code == 1
    assert not (tmp_path / ".kittify" / MISSION_BRIEF_FILENAME).exists()
    assert not (tmp_path / ".kittify" / BRIEF_SOURCE_FILENAME).exists()


def test_intake_from_subdir_writes_to_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When invoked below the repo root, intake writes artifacts to the repo root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".kittify").mkdir()
    subdir = repo_root / "docs"
    subdir.mkdir()
    plan_file = repo_root / "PLAN.md"
    plan_file.write_text(PLAN_CONTENT)

    monkeypatch.chdir(subdir)

    result = runner.invoke(app, ["intake", str(plan_file)], catch_exceptions=False)

    assert result.exit_code == 0
    assert (repo_root / ".kittify" / MISSION_BRIEF_FILENAME).exists()
    assert (repo_root / ".kittify" / BRIEF_SOURCE_FILENAME).exists()
    assert not (subdir / ".kittify" / MISSION_BRIEF_FILENAME).exists()


def test_intake_show_reports_invalid_source_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--show fails loud when the provenance YAML is malformed."""
    monkeypatch.chdir(tmp_path)
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / MISSION_BRIEF_FILENAME).write_text(PLAN_CONTENT, encoding="utf-8")
    (kittify / BRIEF_SOURCE_FILENAME).write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    result = runner.invoke(app, ["intake", "--show"], catch_exceptions=False)

    assert result.exit_code == 2
    assert "Brief provenance" in result.output
    assert "unreadable" in result.output
