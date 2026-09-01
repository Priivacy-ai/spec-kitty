"""Baseline<->head parity for the live ``ScopeSource`` implementation (T024,
mission ``scopesource-gate-followup-01KY6S9P`` WP04, FR-010/FR-014).

Proves ``capture_baseline`` (WP03) and ``evaluate_pre_review_gate`` (this WP)
land in ONE shared failure-identity namespace for a REAL repo — the SAME
committed script/test producing the SAME failure identity on both sides
never false-mismatches and never false-``NEW_FAILURES``.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from specify_cli.review.baseline import BaselineTestResult, capture_baseline
from specify_cli.review.pre_review_gate import GateOutcome, evaluate_pre_review_gate
from specify_cli.review.scope_source import DeclaredCommandScopeSource, ScopeSource

pytestmark = [pytest.mark.git_repo]

_MISSION_SLUG = "scopesource-gate-followup-01KY6S9P"


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def _write_file(repo: Path, relative_path: str, content: str) -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _git_commit_all(path: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True)


def _capture(repo: Path, *, wp_slug: str, scope_source: ScopeSource) -> BaselineTestResult | None:
    feature_dir = repo.parent / "kitty-specs" / _MISSION_SLUG
    return capture_baseline(
        worktree_path=repo,
        base_branch="main",
        wp_id="WP04",
        mission_slug=_MISSION_SLUG,
        feature_dir=feature_dir,
        wp_slug=wp_slug,
        scope_source=scope_source,
    )


_JUNIT_SCRIPT = textwrap.dedent(
    """\
    import sys
    from pathlib import Path

    JUNIT_XML = (
        '<?xml version="1.0" encoding="utf-8"?>\\n'
        '<testsuites>\\n'
        '  <testsuite name="pytest" tests="1" failures="1" errors="0" skipped="0">\\n'
        '    <testcase classname="tests.test_thing" name="test_boom" '
        'file="tests/test_thing.py" line="3">\\n'
        '      <failure message="AssertionError: boom">AssertionError: boom</failure>\\n'
        '    </testcase>\\n'
        '  </testsuite>\\n'
        '</testsuites>\\n'
    )

    # Worktree-relative (the B1 shape): written against the process's OWN
    # cwd, which both capture_baseline (a detached worktree) and the head
    # run (the repo root) invoke this script from.
    Path("results.xml").write_text(JUNIT_XML, encoding="utf-8")
    sys.exit(1)
    """
)

_FAIL_TEXT_SCRIPT = "print('FAIL tests.test_thing.test_boom: boom')\nraise SystemExit(1)\n"


def _build_declared_command_repo(tmp_path: Path, *, script_name: str, script_body: str) -> Path:
    repo = tmp_path / f"declared-command-repo-{script_name}"
    _init_git_repo(repo)
    _write_file(repo, script_name, script_body)
    test_command = f"{sys.executable} {script_name} --junitxml=results.xml" if script_name.endswith("junit.py") else f"{sys.executable} {script_name}"
    _write_file(repo, ".kittify/config.yaml", f"review:\n  test_command: {test_command!r}\n")
    _git_commit_all(repo, "base commit with a declared test command")
    return repo


def test_declared_command_scope_source_worktree_relative_junit_parity(tmp_path: Path) -> None:
    repo = _build_declared_command_repo(tmp_path, script_name="write_junit.py", script_body=_JUNIT_SCRIPT)
    baseline = _capture(repo, wp_slug="WP04-dc-junit", scope_source=DeclaredCommandScopeSource(repo_root=repo))
    assert baseline is not None
    assert baseline.source_identity == "DeclaredCommandScopeSource/junit_xml"
    assert baseline.failures and baseline.failures[0].test == "tests.test_thing.test_boom"

    verdict = evaluate_pre_review_gate(
        ["anything/at/all.rb"],
        repo_root=repo,
        baseline=baseline,
        scope_source=DeclaredCommandScopeSource(repo_root=repo),
    )

    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert any(f.test == "tests.test_thing.test_boom" for f in verdict.pre_existing_failures)


def test_declared_command_scope_source_fail_text_parity(tmp_path: Path) -> None:
    repo = _build_declared_command_repo(tmp_path, script_name="run_tests.py", script_body=_FAIL_TEXT_SCRIPT)
    baseline = _capture(repo, wp_slug="WP04-dc-text", scope_source=DeclaredCommandScopeSource(repo_root=repo))
    assert baseline is not None
    assert baseline.source_identity == "DeclaredCommandScopeSource/text"
    assert baseline.failures and baseline.failures[0].test == "tests.test_thing.test_boom"

    verdict = evaluate_pre_review_gate(
        ["anything/at/all.rb"],
        repo_root=repo,
        baseline=baseline,
        scope_source=DeclaredCommandScopeSource(repo_root=repo),
    )

    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert any(f.test == "tests.test_thing.test_boom" for f in verdict.pre_existing_failures)
