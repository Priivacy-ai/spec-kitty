"""The human-console accept summary must render ``summary.warnings``.

Follow-on to #1892 (Lynn Cole's ``accept --lenient`` feature): that change
downgrades unmet mission path conventions from a blocking ``path_violations``
entry to a non-blocking ``AcceptanceSummary.warnings`` entry. The ``--json``
output already carries ``warnings``, but the human-readable console renderer
(`_print_acceptance_summary`) never printed them, so a ``--lenient`` operator
not using ``--json`` got no signal about what was downgraded.

These tests drive the console renderer directly with constructed summaries (a
pure seam — no git/fixture scaffolding) and assert that a non-empty
``warnings`` list is surfaced, while a clean summary shows no spurious warnings
section.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

import specify_cli.cli.commands.accept as accept_cmd
from specify_cli.acceptance import AcceptanceSummary
from specify_cli.task_utils import LANES

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _summary(*, warnings: list[str]) -> AcceptanceSummary:
    """Build a minimal accept-ready summary carrying the given warnings."""
    repo_root = Path("/tmp/repo")
    feature_dir = repo_root / "kitty-specs" / "099-demo"
    return AcceptanceSummary(
        feature="099-demo",
        repo_root=repo_root,
        feature_dir=feature_dir,
        tasks_dir=feature_dir / "tasks",
        branch="kitty/mission-099-demo",
        worktree_root=repo_root,
        primary_repo_root=repo_root,
        lanes={lane: [] for lane in LANES},
        work_packages=[],
        metadata_issues=[],
        activity_issues=[],
        unchecked_tasks=[],
        needs_clarification=[],
        missing_artifacts=[],
        optional_missing=[],
        git_dirty=[],
        path_violations=[],
        warnings=warnings,
    )


def _render(summary: AcceptanceSummary, monkeypatch: pytest.MonkeyPatch) -> str:
    buf = StringIO()
    monkeypatch.setattr(
        accept_cmd, "console", Console(file=buf, highlight=False, markup=True, width=200)
    )
    accept_cmd._print_acceptance_summary(summary)
    return buf.getvalue()


def test_lenient_path_convention_warning_is_rendered_in_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A downgraded path-convention warning appears in the human console output."""
    warning = "Mission 'Software Dev Kitty' expects tests/ but it is missing."
    output = _render(_summary(warnings=[warning]), monkeypatch)

    assert "Warnings" in output
    assert "expects tests/" in output


def test_clean_summary_renders_no_warnings_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A summary with no warnings must not print a spurious Warnings section."""
    output = _render(_summary(warnings=[]), monkeypatch)

    assert "Warnings" not in output
