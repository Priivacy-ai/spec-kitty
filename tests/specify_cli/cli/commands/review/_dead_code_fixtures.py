"""Shared scan entry point for the dead-code baseline test split.

``test_dead_code_baseline.py`` (``fast``) and ``test_dead_code_baseline_git.py``
(``integration`` + ``git_repo``) are two halves of one subject. They were split
so the ``fast`` lane keeps its no-subprocess contract — see
``tests/architectural/test_pytest_marker_correctness.py`` Rule 2 and
``docs/context/testing-taxonomy.md`` under "Fast". Both halves drive
``scan_dead_code`` through the same helper, so it lives here instead of being
duplicated (and allowed to drift) across the two modules.

This module deliberately contains no ``subprocess`` call of its own: the real
``git`` plumbing lives only in the ``git_repo``-marked module that needs it, so
importing this from the ``fast`` half cannot smuggle a process spawn into the
inner developer loop.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from specify_cli.cli.commands.review._dead_code import scan_dead_code


def scan(repo_root: Path, baseline: str) -> tuple[list[dict[str, str]], str]:
    """Run the dead-code scan, returning (findings, rendered console text)."""
    findings: list[dict[str, str]] = []
    console = Console(force_terminal=False, no_color=True, record=True)
    scan_dead_code(
        baseline_merge_commit=baseline,
        repo_root=repo_root,
        console=console,
        findings=findings,
        mission_id="01KRKTT58XC5KR0HF523333R9S",
        mission_slug="example-modern-mission-01KRKTT5",
    )
    return findings, console.export_text()
