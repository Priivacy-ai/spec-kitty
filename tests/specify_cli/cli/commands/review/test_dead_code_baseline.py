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
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from specify_cli.cli.commands.review._dead_code import scan_dead_code
from specify_cli.cli.commands.review._diagnostics import MissionReviewDiagnostic

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


def test_modern_mission_with_baseline_runs_scan_unchanged(
    tmp_path: Path,
) -> None:
    """Modern mission + populated baseline → existing scan path runs unchanged."""
    findings: list[dict[str, str]] = []
    console = Console(force_terminal=False, no_color=True, record=True)

    # tmp_path is not a git repo; the scan's `git diff` returns no output, so
    # no symbols are detected and no findings are appended.
    scan_dead_code(
        baseline_merge_commit="0000000000000000000000000000000000000000",
        repo_root=tmp_path,
        console=console,
        findings=findings,
        mission_id="01KRKTT58XC5KR0HF523333R9S",
        mission_slug="example-modern-mission-01KRKTT5",
    )

    assert findings == []
    output = console.export_text()
    # The post-083 clean-scan path is what produces "0 unreferenced public symbols".
    assert "0 unreferenced public symbols" in output
    # And it does NOT emit either of the new diagnostic tags.
    assert "LIGHTWEIGHT_REVIEW_MISSING_BASELINE" not in output
    assert "LEGACY_MISSION_DEAD_CODE_SKIP" not in output


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
