"""Tests for WP03 diff-coverage policy validation report.

Covers the contract surface defined in
kitty-specs/068-post-merge-reliability-and-release-hardening/contracts/diff_coverage_policy.md.

Tests:
- test_validation_report_authored        — report file exists and has all required sections
- test_decision_is_recorded              — exactly one decision is marked
- test_validation_report_close_path_populated  — content gate: non-vacuous rationale + findings
- test_close_with_evidence_does_not_modify_workflow  — only name: changes when closing
- test_tighten_workflow_passes_large_pr_sample  — active when tighten_workflow is chosen; verifies advisory-only contract via YAML inspection
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Locate project root and report path
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
# tests/release/ -> tests/ -> project root
_PROJECT_ROOT = _THIS_FILE.parent.parent.parent
_REPORT_PATH = _PROJECT_ROOT / "kitty-specs" / "068-post-merge-reliability-and-release-hardening" / "wp03-validation-report.md"
_WORKFLOW_PATH = _PROJECT_ROOT / ".github" / "workflows" / "ci-quality.yml"

# ---------------------------------------------------------------------------
# Required sections that MUST appear in the validation report
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = [
    "Validated at commit",
    "Workflow path",
    "Sample PR",
    "Critical-path threshold",
    "Full-diff threshold",
    "Findings",
    "Decision",
    "Rationale",
]

# The two mutually-exclusive decision markers (the checked-box variants)
DECISION_CLOSE = "[x] close_with_evidence"
DECISION_TIGHTEN = "[x] tighten_workflow"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_report() -> str:
    """Return the raw text of the validation report.

    The report must exist before this function is called — tests that depend
    on the report will fail with a clear FileNotFoundError if it is missing.
    """
    return _REPORT_PATH.read_text(encoding="utf-8")


def _report_decision(text: str) -> str:
    """Return 'close_with_evidence', 'tighten_workflow', or raises."""
    close_checked = DECISION_CLOSE in text
    tighten_checked = DECISION_TIGHTEN in text
    if close_checked and tighten_checked:
        raise AssertionError("Both decisions are checked in the validation report — exactly one must be.")
    if not close_checked and not tighten_checked:
        raise AssertionError("Neither decision is checked in the validation report — exactly one must be.")
    return "close_with_evidence" if close_checked else "tighten_workflow"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_validation_report_authored() -> None:
    """FR-010: The validation report file must exist and contain all required sections."""
    assert _REPORT_PATH.exists(), f"Validation report not found at {_REPORT_PATH}. WP03 (T015) must author this file before any other step."
    text = _read_report()
    for section in REQUIRED_SECTIONS:
        assert section in text, f"Required section '{section}' is missing from the validation report. Report path: {_REPORT_PATH}"


@pytest.mark.fast
def test_decision_is_recorded() -> None:
    """FR-010: Exactly one of close_with_evidence or tighten_workflow must be checked."""
    text = _read_report()
    # _report_decision raises if zero or both are checked
    decision = _report_decision(text)
    assert decision in ("close_with_evidence", "tighten_workflow"), f"Unexpected decision value: {decision!r}"


@pytest.mark.fast
def test_validation_report_close_path_populated() -> None:
    """Content gate (FR-010, FR-011): when decision == close_with_evidence,
    rationale must be >= 50 chars AND every finding entry must carry
    a 'satisfied by' citation (preventing a vacuous report).
    """
    text = _read_report()
    decision = _report_decision(text)

    if decision != "close_with_evidence":
        pytest.skip("FR-012 path taken; close_with_evidence content gate does not apply.")

    # Extract rationale section (everything after "## Rationale" heading)
    rationale_match = re.search(
        r"##\s+Rationale\s*\n(.*?)(?:\n##|\Z)",
        text,
        re.DOTALL,
    )
    assert rationale_match is not None, "Could not locate '## Rationale' section in the validation report."
    rationale_text = rationale_match.group(1).strip()
    assert len(rationale_text) >= 50, (
        f"Rationale is too short ({len(rationale_text)} chars, minimum 50). A vacuous one-liner does not constitute evidence — expand the rationale."
    )

    # Extract findings section and verify every checked finding has "satisfied by"
    findings_match = re.search(
        r"##\s+Findings\s*\n(.*?)(?:\n##|\Z)",
        text,
        re.DOTALL,
    )
    assert findings_match is not None, "Could not locate '## Findings' section in the validation report."
    findings_text = findings_match.group(1)

    # Find all checked findings ([x] ...)
    checked_findings = re.findall(r"- \[x\] .+", findings_text)

    if checked_findings:
        # Every checked finding must carry "satisfied by" (case-insensitive)
        for finding in checked_findings:
            assert "satisfied by" in finding.lower(), (
                f"Checked finding is missing 'satisfied by' rationale:\n  {finding}\n"
                "Each finding in a close_with_evidence report must cite the specific "
                "workflow line or mechanism that satisfies the requirement."
            )


@pytest.mark.fast
def test_close_with_evidence_does_not_modify_workflow() -> None:
    """FR-011: when decision == close_with_evidence, git diff against main
    on ci-quality.yml must be empty OR contain only 'name:' field changes.
    """
    text = _read_report()
    decision = _report_decision(text)

    if decision != "close_with_evidence":
        pytest.skip("FR-012 path taken; close_with_evidence workflow-diff gate does not apply.")

    # Run git diff against the base branch to see what changed in ci-quality.yml
    result = subprocess.run(
        [
            "git",
            "diff",
            "origin/main",
            "--",
            ".github/workflows/ci-quality.yml",
        ],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # If origin/main is not available, fall back to comparing against the base commit
    if result.returncode != 0:
        result = subprocess.run(
            [
                "git",
                "diff",
                "HEAD~1",
                "--",
                ".github/workflows/ci-quality.yml",
            ],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

    diff_output = result.stdout.strip()

    if not diff_output:
        # No changes at all — perfectly consistent with close_with_evidence
        return

    # Allow ONLY +/- lines that touch 'name:' fields
    changed_lines = [line for line in diff_output.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]

    non_name_changes = [line for line in changed_lines if "name:" not in line.lower()]

    assert not non_name_changes, (
        "The close_with_evidence decision forbids logic changes to ci-quality.yml. "
        "Only 'name:' field renames are allowed. Found non-name changes:\n" + "\n".join(non_name_changes)
    )


@pytest.mark.fast
def test_tighten_workflow_passes_large_pr_sample() -> None:
    """FR-012: only relevant when tighten_workflow is chosen.

    Verifies that the modified workflow correctly handles a large PR that meets
    critical-path coverage but misses full-diff coverage, by inspecting the
    ci-quality.yml YAML structure for the advisory-only contract.

    Specifically checks:
    1. The full-diff step uses ``|| true`` so it never hard-fails.
    2. The critical-path step has ``--fail-under=90`` (enforced gate exists).
    3. The critical-path ``--include`` list restricts enforcement to the
       designated high-risk modules only — files outside this set (e.g.
       ``src/specify_cli/cli/*``) are NOT subject to the 90% floor, so a
       large PR touching only non-critical-path files passes regardless of
       its full-diff coverage ratio.
    4. The new status-layer coverage reports are wired into both steps so
       that ``src/specify_cli/status/*`` and ``src/kernel/*`` changes are
       covered under the enforced 90% gate.

    If FR-011 (close_with_evidence) fired instead, this test is skipped.
    """
    text = _read_report()
    decision = _report_decision(text)

    if decision != "tighten_workflow":
        pytest.skip("FR-011 (close_with_evidence) path taken. No workflow logic changes were made, so the large-PR sample test is not applicable.")

    workflow_text = _WORKFLOW_PATH.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # 1. Full-diff advisory step must use ``|| true`` (never hard-fails)
    # ------------------------------------------------------------------
    advisory_match = re.search(
        r'name:\s*"diff-coverage \(full-diff, advisory\)".*?run:\s*\|(.*?)(?=\n      - name:|\Z)',
        workflow_text,
        re.DOTALL,
    )
    assert advisory_match is not None, (
        "Could not locate the 'diff-coverage (full-diff, advisory)' step in ci-quality.yml. The advisory step is required for FR-012 compliance."
    )
    advisory_run = advisory_match.group(1)
    assert "|| true" in advisory_run, (
        "The full-diff advisory step must append '|| true' to the diff-cover invocation "
        "to guarantee it never hard-fails. Large PRs that miss full-diff coverage must pass."
    )
    assert "--fail-under" not in advisory_run, "The full-diff advisory step must NOT have --fail-under; it is advisory-only."

    # ------------------------------------------------------------------
    # 2. Critical-path enforced step must have --fail-under=90
    # ------------------------------------------------------------------
    enforced_match = re.search(
        r'name:\s*"diff-coverage \(critical-path, enforced\)".*?run:\s*\|(.*?)(?=\n      - name:|\Z)',
        workflow_text,
        re.DOTALL,
    )
    assert enforced_match is not None, "Could not locate the 'diff-coverage (critical-path, enforced)' step in ci-quality.yml."
    enforced_run = enforced_match.group(1)
    assert "--fail-under=90" in enforced_run, "The critical-path enforced step must include '--fail-under=90'."

    # ------------------------------------------------------------------
    # 3. Critical-path --include list must contain the designated modules
    #    and NOT contain generic non-critical paths (proving large PRs that
    #    only touch non-critical files are exempt from the hard gate)
    # ------------------------------------------------------------------
    critical_path_modules = [
        "src/kernel/*",
        "src/doctrine/*",
        "src/charter/*",
        "src/specify_cli/status/*",
        "src/specify_cli/core/mission_detection.py",
        "src/specify_cli/dashboard/handlers/*",
        "src/specify_cli/dashboard/scanner.py",
        "src/specify_cli/merge/*",
        "src/specify_cli/next/*",
    ]
    for module in critical_path_modules:
        assert module in enforced_run, f"Critical-path module '{module}' is missing from the --include list in the enforced diff-coverage step."

    # Non-critical-path glob must NOT appear in the enforced --include list.
    # This is the key proof that large PRs touching only non-critical-path files
    # (e.g. CLI commands, validators, upgrade scripts) are not subject to the 90% floor.
    non_critical_examples = [
        "src/specify_cli/cli/*",
        "src/specify_cli/validators/*",
        "src/specify_cli/upgrade/*",
    ]
    for non_critical in non_critical_examples:
        assert non_critical not in enforced_run, (
            f"Non-critical-path glob '{non_critical}' must NOT appear in the enforced --include list. Only designated high-risk modules should be gated."
        )

    # ------------------------------------------------------------------
    # 4. Coverage artifacts are downloaded and discovered dynamically
    #    (FR-012 tightening). The diff-coverage job must use a wildcard
    #    download pattern and find-based discovery so that ALL upstream
    #    coverage reports (including kernel and status) feed the gate.
    # ------------------------------------------------------------------
    assert "coverage-*.xml" in enforced_run, (
        "The enforced diff-coverage step must use a dynamic find pattern (coverage-*.xml) to discover all coverage reports from upstream jobs."
    )
    assert "coverage-*.xml" in advisory_run, (
        "The advisory diff-coverage step must use a dynamic find pattern (coverage-*.xml) to discover all coverage reports from upstream jobs."
    )

    # ------------------------------------------------------------------
    # 5. diff-coverage must wait for charter coverage uploads when the
    #    enforced gate includes charter files.
    # ------------------------------------------------------------------
    assert "fast-tests-charter" in workflow_text, (
        "The CI workflow must define a fast-tests-charter job so charter coverage can feed the enforced diff-coverage gate."
    )
    assert re.search(r"diff-coverage:\s*\n(?:.*\n)*?\s+needs:\s*\n(?:.*\n)*?\s+- fast-tests-charter", workflow_text), (
        "diff-coverage must depend on fast-tests-charter; otherwise charter-only changes can race artifact upload and produce timing-dependent results."
    )
    assert re.search(r"diff-coverage:\s*\n(?:.*\n)*?\s+needs:\s*\n(?:.*\n)*?\s+- fast-tests-core-misc", workflow_text), (
        "diff-coverage must depend on fast-tests-core-misc; otherwise uncategorized "
        "core/specify_cli changes can race coverage upload and fail before their "
        "artifact exists."
    )

    # ------------------------------------------------------------------
    # 6. quality-gate is the aggregate signal and must fail when
    #    diff-coverage fails on PRs.
    # ------------------------------------------------------------------
    assert re.search(r"quality-gate:\s*\n(?:.*\n)*?\s+needs:\s*\n(?:.*\n)*?\s+- diff-coverage", workflow_text), (
        "quality-gate must depend on diff-coverage so a red coverage gate cannot be masked by a green aggregate check."
    )
