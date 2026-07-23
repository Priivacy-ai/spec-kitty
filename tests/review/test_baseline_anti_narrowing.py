"""WP03 (mission ``scopesource-gate-followup-01KY6S9P``) — anti-narrowing
guard (C-005 / FR-012, T017).

The baseline capture path must run the scope source's WHOLE declared
command, verbatim, never narrowed the way the pre-review head run narrows
via ``[*command, *scope.test_targets]`` (``pre_review_gate.py:889``,
``_evaluate_via_scope_source``). Baseline and head legitimately run
DIFFERENT scopes -- baseline is the broad, whole-suite proof of pre-existing
failures; head narrows to the files that actually changed -- only the
COMMAND *authority* is unified (NFR-005: both call the same
``ScopeSource.test_command()``). This guard proves the invariant so a
future refactor that threads a ``scope``/``test_targets`` parameter into the
baseline path (silently narrowing it to match head) fails loudly here first.
"""
from __future__ import annotations

import inspect
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.review.baseline import BaselineFailure, _capture_baseline_via_scope_source, capture_baseline
from specify_cli.review.scope_source import RawRunResult

pytestmark = pytest.mark.git_repo


class _StubScopeSource:
    """Minimal ``ScopeSource`` stub whose ``test_command()`` is a fixed,
    known argv -- lets the test assert the EXACT command reaching
    ``subprocess.run`` with nothing appended."""

    def __init__(self, command: list[str]) -> None:
        self._command = command

    def test_command(self) -> list[str] | None:
        return list(self._command)

    def file_to_scope(self, _path: str) -> tuple[str, ...]:
        return ()

    def parse_results(self, _raw: RawRunResult) -> tuple[BaselineFailure, ...]:
        return ()

    def parse_mode(self, _raw: RawRunResult) -> str:
        return "none"


def _make_wp_dir(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Set up a minimal fake repo structure (mirrors test_baseline.py's own
    helper -- subprocess is fully mocked below, so a real ``.git`` is not
    needed, only a directory :func:`_find_repo_root` will recognise)."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    feature_dir = repo / "kitty-specs" / "anti-narrow-test"
    (feature_dir / "tasks" / "WPXX-test").mkdir(parents=True)
    return repo, feature_dir, feature_dir / "tasks" / "WPXX-test"


def test_baseline_command_runs_whole_declared_command_without_narrowing(tmp_path: Path) -> None:
    """The exact argv ``subprocess.run`` receives for the baseline test run
    must equal ``scope_source.test_command()`` verbatim -- no
    ``scope.test_targets`` appended, unlike the head diff-time run."""
    repo, feature_dir, _wp_task_dir = _make_wp_dir(tmp_path)
    declared_command = ["custom-runner", "--flag-a", "--flag-b"]
    stub = _StubScopeSource(declared_command)

    seen_commands: list[list[str]] = []

    def fake_run(cmd: Sequence[str], **_kwargs: object) -> MagicMock:
        result = MagicMock()
        result.returncode = 0
        result.stdout = "abc1234def5\n"
        result.stderr = ""
        if isinstance(cmd, list) and cmd[:2] == ["git", "rev-parse"]:
            return result
        if isinstance(cmd, list) and cmd[:2] == ["git", "worktree"]:
            return result
        seen_commands.append(list(cmd))
        return result

    with patch("subprocess.run", side_effect=fake_run):
        result = capture_baseline(
            worktree_path=repo,
            base_branch="main",
            wp_id="WPXX",
            mission_slug="anti-narrow-test",
            feature_dir=feature_dir,
            wp_slug="WPXX-test",
            scope_source=stub,
        )

    assert result is not None
    assert seen_commands == [declared_command], (
        "baseline capture must run the scope source's WHOLE declared command "
        "verbatim exactly once (C-005) -- it must never append a per-file "
        "scope.test_targets narrowing the way the head diff-time run does"
    )


def test_capture_baseline_via_scope_source_has_no_scope_narrowing_parameter() -> None:
    """Structural guard: the scope-source capture path takes no
    ``scope``/``test_targets`` parameter at all, so there is nothing to
    narrow with in the first place -- a future refactor cannot silently
    thread per-file narrowing through without this test flagging the new
    parameter."""
    params = inspect.signature(_capture_baseline_via_scope_source).parameters
    assert "scope" not in params
    assert "test_targets" not in params
