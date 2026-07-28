"""Regression tests for lightweight review dead-code baseline parity (issue #989).

Before this fix, ``spec-kitty review --mode lightweight`` silently passed
modern numbered missions whose ``meta.json`` had ``baseline_merge_commit: null``
— the dead-code scan was skipped with a yellow warning, and the gate verdict
was ``pass``. That hid missing release evidence behind a green signal.

After the fix:

* Modern missions (with ``mission_id`` set) and ``baseline_merge_commit: null``
  must fail-hard with ``LIGHTWEIGHT_REVIEW_MISSING_BASELINE``.
* Modern missions with ``baseline_merge_commit`` populated keep the existing
  scan behavior (no regression).
* Legacy missions (no ``mission_id``) keep the historical skip-pass, but the
  verdict is tagged with ``LEGACY_MISSION_DEAD_CODE_SKIP`` so the path is
  greppable and not confusable with a clean post-083 pass.

Scope of *this* module: the ``fast`` half. Nothing here spawns a process — the
missing-baseline paths short-circuit before ``git`` is reached, and
:func:`test_missing_git_at_subprocess_boundary_is_undeterminable` injects the
failure *at* the ``subprocess`` boundary instead of letting a real executable
run. Everything that drives the real ``git`` binary lives in the sibling
``test_dead_code_baseline_git.py`` (``integration`` + ``git_repo``), keeping the
``fast`` lane's no-subprocess promise intact — see
``tests/architectural/test_pytest_marker_correctness.py`` and
``docs/context/testing-taxonomy.md`` under "Fast".
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest
from rich.console import Console

from specify_cli.cli.commands.review._dead_code import scan_dead_code
from specify_cli.cli.commands.review._diagnostics import MissionReviewDiagnostic
from tests.specify_cli.cli.commands.review._dead_code_fixtures import scan

pytestmark = pytest.mark.fast


def test_modern_mission_missing_baseline_emits_structured_failure(
    tmp_path: Path,
) -> None:
    """Modern mission + null baseline → finding appended + LIGHTWEIGHT_REVIEW_MISSING_BASELINE."""
    findings: list[dict[str, str]] = []
    console = Console(force_terminal=False, no_color=True, record=True)

    scan_dead_code(
        baseline_merge_commit=None,
        repo_root=tmp_path,
        console=console,
        findings=findings,
        mission_id="01KRKTT58XC5KR0HF523333R9S",
        mission_slug="example-modern-mission-01KRKTT5",
    )

    assert len(findings) == 1, f"Expected 1 finding, got {findings!r}"
    finding = findings[0]
    assert finding["type"] == "dead_code_baseline_missing"
    assert finding["diagnostic_code"] == str(
        MissionReviewDiagnostic.LIGHTWEIGHT_REVIEW_MISSING_BASELINE
    )
    assert finding["diagnostic_code"] == "LIGHTWEIGHT_REVIEW_MISSING_BASELINE"
    assert finding["mission_id"] == "01KRKTT58XC5KR0HF523333R9S"
    assert finding["mission_slug"] == "example-modern-mission-01KRKTT5"
    assert "baseline_merge_commit" in finding["remediation"]
    output = console.export_text()
    assert "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" in output


def test_legacy_mission_missing_baseline_skips_and_tags(
    tmp_path: Path,
) -> None:
    """Legacy mission (no mission_id) + null baseline → skip-pass tagged with LEGACY_MISSION_DEAD_CODE_SKIP."""
    findings: list[dict[str, str]] = []
    console = Console(force_terminal=False, no_color=True, record=True)

    scan_dead_code(
        baseline_merge_commit=None,
        repo_root=tmp_path,
        console=console,
        findings=findings,
        mission_id=None,
        mission_slug="example-legacy-mission",
    )

    # No finding appended → gate 2 still passes for legacy missions.
    assert findings == []
    # But the legacy skip path is greppable via the tag.
    output = console.export_text()
    assert "LEGACY_MISSION_DEAD_CODE_SKIP" in output
    assert "legacy" in output.lower()


def test_missing_git_at_subprocess_boundary_is_undeterminable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable subprocess executable yields a verdict, not a traceback.

    FR-016: the injection happens at the ``subprocess`` boundary — patching
    ``shutil.which`` instead would leave the real failure mode (an executable
    that resolves but cannot be spawned) unguarded. No process is spawned, so
    this guard belongs in the ``fast`` lane.
    """

    def unavailable(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", unavailable)

    findings, output = scan(tmp_path, "deadbeef")

    assert findings[0]["type"] == "dead_code_undeterminable"
    assert findings[0]["reason"] == "git executable is unavailable"
    assert "0 unreferenced public symbols" not in output


def test_undeterminable_finding_is_rendered_as_hard_failure(tmp_path: Path) -> None:
    import typer

    from specify_cli.cli.commands.review._report import write_review_report

    feature_dir = tmp_path / "kitty-specs" / "dead-code-report"
    feature_dir.mkdir(parents=True)
    findings = [
        {
            "type": "dead_code_undeterminable",
            "diagnostic_code": "MISSION_REVIEW_DEAD_CODE_UNDETERMINABLE",
            "reason": "git diff failed",
            "remediation": "Repair Git and retry.",
        }
    ]

    with pytest.raises(typer.Exit) as exc_info:
        write_review_report(
            feature_dir,
            tmp_path,
            findings,
            Console(file=io.StringIO()),
            mode="post-merge",
        )

    assert exc_info.value.exit_code == 1
    report = (feature_dir / "mission-review-report.md").read_text(encoding="utf-8")
    assert "verdict: fail" in report
    assert "dead_code_undeterminable" in report
    assert "MISSION_REVIEW_DEAD_CODE_UNDETERMINABLE" in report


def test_diagnostic_code_string_is_stable() -> None:
    """The wire-stable code string MUST be exactly ``LIGHTWEIGHT_REVIEW_MISSING_BASELINE``."""
    assert (
        MissionReviewDiagnostic.LIGHTWEIGHT_REVIEW_MISSING_BASELINE.value
        == "LIGHTWEIGHT_REVIEW_MISSING_BASELINE"
    )
    assert (
        MissionReviewDiagnostic.LEGACY_MISSION_DEAD_CODE_SKIP.value
        == "LEGACY_MISSION_DEAD_CODE_SKIP"
    )
