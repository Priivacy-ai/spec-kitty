"""WP06 T034 — `charter generate` auto-tracks + non-git fail-fast (issue #841).

These tests lock in the parity contract: after `charter generate` succeeds in a
fresh git repo, the produced ``.kittify/charter/charter.md`` is auto-staged so
the immediately-following ``charter bundle validate`` accepts it without any
operator ``git add`` between the two commands. In a non-git environment,
``generate`` exits non-zero with an actionable error containing both ``git``
and ``init``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app as charter_app
from specify_cli.cli.commands.charter_bundle import app as charter_bundle_app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git_init(repo: Path) -> None:
    """Initialize a minimal git repo with identity configured."""
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _write_minimal_interview(repo: Path) -> None:
    """Place a minimal interview answers.yaml so charter generate can run.

    The interview file shape is what ``charter.interview.read_interview_answers``
    parses. We supply only the fields ``compile_charter`` consults.
    """
    interview_dir = repo / ".kittify" / "charter" / "interview"
    interview_dir.mkdir(parents=True, exist_ok=True)
    (interview_dir / "answers.yaml").write_text(
        "mission: software-dev\n"
        "profile: minimal\n"
        "selected_paradigms: []\n"
        "selected_directives: []\n"
        "available_tools: []\n"
        "answers:\n"
        "  purpose: Test charter for auto-track contract.\n",
        encoding="utf-8",
    )


def _ls_files_stage(repo: Path) -> list[str]:
    """Return repo-relative paths reported by ``git ls-files --stage``."""
    result = subprocess.run(
        ["git", "ls-files", "--stage"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        # format: <mode> <hash> <stage>\t<path>
        if "\t" in line:
            paths.append(line.split("\t", 1)[1])
    return paths


# ---------------------------------------------------------------------------
# T034a — generate then bundle validate succeeds in fresh git repo
# ---------------------------------------------------------------------------


def test_generate_then_bundle_validate_succeeds_in_fresh_git_repo(
    tmp_path: Path,
) -> None:
    """After ``charter generate`` in a fresh git repo, ``bundle validate``
    accepts the bundle without any intervening ``git add``.
    """
    _git_init(tmp_path)
    _write_minimal_interview(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        gen_result = runner.invoke(
            charter_app,
            ["generate", "--from-interview", "--json"],
            catch_exceptions=False,
        )
        assert gen_result.exit_code == 0, f"generate failed: stdout={gen_result.stdout!r} stderr={getattr(gen_result, 'stderr', '')!r}"

        # NO manual `git add` between generate and validate.
        val_result = runner.invoke(
            charter_bundle_app,
            ["validate", "--json"],
            catch_exceptions=False,
        )
        assert val_result.exit_code == 0, f"bundle validate failed after generate: stdout={val_result.stdout!r}"
    finally:
        os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# T034b — generate in non-git dir fails fast
# ---------------------------------------------------------------------------


def test_generate_in_non_git_dir_fails_fast(tmp_path: Path) -> None:
    """``charter generate`` outside a git repo MUST exit non-zero with a
    message containing both ``git`` and ``init``.
    """
    # NOT calling _git_init: tmp_path is a plain directory.
    _write_minimal_interview(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            charter_app,
            ["generate", "--from-interview"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code != 0, f"generate must fail in non-git dir; got exit 0. output={result.stdout!r}"
    combined = (result.stdout or "") + (result.output or "")
    lowered = combined.lower()
    assert "git" in lowered, f"error message must mention 'git'. output={combined!r}"
    assert "init" in lowered, f"error message must mention 'init' (the remediation). output={combined!r}"


# ---------------------------------------------------------------------------
# T034c — generate stages produced files
# ---------------------------------------------------------------------------


def test_generate_stages_produced_files(tmp_path: Path) -> None:
    """After ``charter generate`` succeeds, ``git ls-files --stage`` MUST
    include ``.kittify/charter/charter.md`` (the manifest's tracked file).
    """
    _git_init(tmp_path)
    _write_minimal_interview(tmp_path)

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            charter_app,
            ["generate", "--from-interview"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"generate failed: output={result.stdout!r}"
        staged = _ls_files_stage(tmp_path)
    finally:
        os.chdir(old_cwd)

    assert ".kittify/charter/charter.md" in staged, f"charter.md must be auto-staged after generate; got staged paths: {staged!r}"


# ---------------------------------------------------------------------------
# Additional safety: pre-existing staging area not corrupted by generate
# ---------------------------------------------------------------------------


def test_generate_does_not_disturb_unrelated_staged_changes(
    tmp_path: Path,
) -> None:
    """Auto-track must not blow away the operator's pre-existing stage."""
    _git_init(tmp_path)
    _write_minimal_interview(tmp_path)

    # Pre-stage an unrelated file.
    unrelated = tmp_path / "README.md"
    unrelated.write_text("hello\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            charter_app,
            ["generate", "--from-interview"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"generate failed: output={result.stdout!r}"
        staged = _ls_files_stage(tmp_path)
    finally:
        os.chdir(old_cwd)

    assert "README.md" in staged, f"pre-staged README.md must remain staged; got {staged!r}"
    assert ".kittify/charter/charter.md" in staged
