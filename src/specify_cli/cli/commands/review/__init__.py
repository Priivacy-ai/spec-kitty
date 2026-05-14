"""Mission-review command package.

Public entry: review_mission()
Internal modules:
  _diagnostics.py   — MissionReviewDiagnostic StrEnum (WP03)
  _mode.py          — MissionReviewMode + resolve_mode() (WP03)
  _issue_matrix.py  — issue-matrix validator (WP03)
  _lane_gate.py     — Gate 1: WP lane consistency check
  _dead_code.py     — Gate 2: dead-code scan
  _ble001_audit.py  — Gate 3: BLE001 broad-except audit
  _report.py        — Gate 4: report writer

See: src/specify_cli/cli/commands/review/ERROR_CODES.md (authored by WP03)
"""

from __future__ import annotations

import json
import subprocess  # noqa: F401  (monkeypatched in tests)
from pathlib import Path
from typing import Annotated, Optional

import typer

from specify_cli.cli.commands._test_env_check import (  # noqa: F401
    TestExtraMissing,
    assert_pytest_available,
)
from specify_cli.cli.selector_resolution import resolve_mission_handle  # noqa: F401
from specify_cli.task_utils import TaskCliError, find_repo_root  # noqa: F401

from ._ble001_audit import (  # noqa: F401
    Ble001SuppressionFinding,
    audit_auth_storage_ble001_line,
    collect_auth_storage_ble001_findings,
)
from ._dead_code import scan_dead_code  # noqa: F401
from ._diagnostics import MissionReviewDiagnostic  # noqa: F401
from ._issue_matrix import validate_issue_matrix  # noqa: F401
from ._lane_gate import check_wp_lanes  # noqa: F401
from ._mode import MissionReviewMode, ModeMismatchError, resolve_mode  # noqa: F401
from ._report import GateRecord, write_review_report  # noqa: F401


def review_mission(
    mission: Annotated[
        str,
        typer.Option("--mission", help="Mission handle (id, mid8, or slug)."),
    ] = "",
    mode: Annotated[
        Optional[str],
        typer.Option(
            "--mode",
            help=(
                "Review mode: 'lightweight' (consistency check only) or "
                "'post-merge' (full release-gate contract). "
                "Auto-detected from meta.json.baseline_merge_commit when omitted."
            ),
            show_default=False,
        ),
    ] = None,
) -> None:
    """Validate a merged mission: WP lane check, dead-code scan, BLE001 audit.

    Writes kitty-specs/<slug>/mission-review-report.md with a machine-readable
    verdict.  See module docstring for known false-positive scenarios in the
    dead-code scan step.
    """
    from rich.console import Console

    console = Console()

    # ------------------------------------------------------------------
    # Resolve repo root
    # ------------------------------------------------------------------
    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2)

    # ------------------------------------------------------------------
    # Preflight: assert pytest is importable from the active venv.
    # Fails fast with MISSION_REVIEW_TEST_EXTRA_MISSING before any gate
    # subprocess runs, preventing PATH fallthrough to system pytest.
    # See: src/specify_cli/cli/commands/review/ERROR_CODES.md
    #
    # The probe is delegated to ``assert_pytest_available()`` so the helper
    # IS the production path — tests that exercise the helper (via real
    # ``venv.create()`` fixtures) directly assert the live behaviour. No
    # parallel inline implementation; no path-specific test coupling.
    # ------------------------------------------------------------------
    try:
        assert_pytest_available(repo_root)
    except TestExtraMissing:
        import json as _json
        import sys as _sys

        diagnostic_code = MissionReviewDiagnostic.TEST_EXTRA_MISSING
        diagnostic = {
            "diagnostic_code": str(diagnostic_code),
            "message": (
                "pytest is not importable from the active Python interpreter. "
                "Run `uv sync --extra test` to install the test extra, then retry."
            ),
            "remediation": "uv sync --extra test",
        }
        console.print(
            f"[red]Error:[/red] {diagnostic_code}: {diagnostic['message']}"
        )
        _sys.stdout.write(_json.dumps(diagnostic) + "\n")
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Resolve mission handle → feature_dir
    # ------------------------------------------------------------------
    handle = mission.strip()
    if not handle:
        console.print("[red]Error:[/red] --mission is required.")
        raise typer.Exit(2)

    resolved = resolve_mission_handle(handle, repo_root)
    feature_dir = resolved.feature_dir
    mission_slug = resolved.mission_slug

    # ------------------------------------------------------------------
    # Read meta.json for display fields and baseline_merge_commit
    # ------------------------------------------------------------------
    meta_path = feature_dir / "meta.json"
    meta: dict[str, object] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    friendly_name: str = str(meta.get("friendly_name") or mission_slug)
    _bmc_raw = meta.get("baseline_merge_commit")
    baseline_merge_commit: str | None = str(_bmc_raw) if _bmc_raw else None

    # ------------------------------------------------------------------
    # Resolve review mode (FR-005, FR-006, FR-023)
    # ------------------------------------------------------------------
    try:
        review_mode, auto_detected = resolve_mode(
            cli_flag=mode,
            baseline_merge_commit=baseline_merge_commit,
        )
    except ModeMismatchError as exc:
        import json as _json2

        diagnostic = {
            "diagnostic_code": str(exc.diagnostic_code),
            "message": exc.message,
        }
        console.print(
            f"[red]Error:[/red] {exc.diagnostic_code}"
        )
        console.print(exc.message)
        import sys as _sys2
        _sys2.stdout.write(_json2.dumps(diagnostic) + "\n")
        raise typer.Exit(1)

    mode_label = f"{review_mode.value} ({'auto-detected' if auto_detected else 'explicit'})"
    console.print(f"\nReviewing mission: {friendly_name} ({mission_slug})")
    console.print(f"Mode: {mode_label}\n")

    findings: list[dict[str, str]] = []
    gates_recorded: list[GateRecord] = []

    # ==================================================================
    # Step 1 — WP lane check (Gate 1)
    # ==================================================================
    lane_findings_before = len(findings)
    check_wp_lanes(feature_dir, repo_root, console, findings)
    gate1_result: str = "fail" if len(findings) > lane_findings_before else "pass"
    gates_recorded.append(
        GateRecord(
            id="gate_1",
            name="wp_lane_check",
            command="spec-kitty review (internal gate 1)",
            exit_code=1 if gate1_result == "fail" else 0,
            result=gate1_result,  # type: ignore[arg-type]
        )
    )

    # ==================================================================
    # Step 2 — Dead-code scan (Gate 2)
    # ==================================================================
    dead_code_findings_before = len(findings)
    _mission_id_raw = meta.get("mission_id")
    _mission_id: str | None = str(_mission_id_raw) if _mission_id_raw else None
    scan_dead_code(
        baseline_merge_commit,
        repo_root,
        console,
        findings,
        mission_id=_mission_id,
        mission_slug=mission_slug,
    )
    gate2_result: str = "fail" if len(findings) > dead_code_findings_before else "pass"
    gates_recorded.append(
        GateRecord(
            id="gate_2",
            name="dead_code_scan",
            command="spec-kitty review (internal gate 2)",
            exit_code=1 if gate2_result == "fail" else 0,
            result=gate2_result,  # type: ignore[arg-type]
        )
    )

    # ==================================================================
    # Step 3 — BLE001 unjustified suppression audit (Gate 3)
    # ==================================================================
    ble001_findings = collect_auth_storage_ble001_findings(repo_root)
    for finding in ble001_findings:
        findings.append(
            {
                "type": "ble001_suppression",
                "file": finding.file,
                "line": str(finding.line),
                "content": finding.suppression,
                "remediation": finding.remediation,
            }
        )

    if ble001_findings:
        console.print(
            f"  [red]✗[/red]  BLE001 audit: {len(ble001_findings)} unjustified suppression(s)"
        )
        for finding in ble001_findings:
            console.print(f"       {finding.file}:{finding.line}")
            console.print(f"       suppression: {finding.suppression}")
            console.print(f"       remediation: {finding.remediation}")
        gate3_result = "fail"
    else:
        console.print("  [green]✓[/green]  BLE001 audit: 0 unjustified suppressions")
        gate3_result = "pass"

    gates_recorded.append(
        GateRecord(
            id="gate_3",
            name="ble001_audit",
            command="spec-kitty review (internal gate 3)",
            exit_code=1 if gate3_result == "fail" else 0,
            result=gate3_result,  # type: ignore[arg-type]
        )
    )

    # ==================================================================
    # Step 3b — Issue matrix validation (post-merge gate, FR-006, FR-028-032)
    # ==================================================================
    issue_matrix_path = feature_dir / "issue-matrix.md"
    issue_matrix_present: bool | str

    if review_mode is MissionReviewMode.POST_MERGE:
        if issue_matrix_path.exists():
            matrix_result = validate_issue_matrix(issue_matrix_path)
            issue_matrix_present = True
            if not matrix_result.passed:
                for diag in matrix_result.diagnostics:
                    console.print(
                        f"  [red]✗[/red]  Issue matrix: {diag['diagnostic_code']}: {diag['message']}"
                    )
                    findings.append(
                        {
                            "type": "issue_matrix_violation",
                            "diagnostic_code": diag["diagnostic_code"],
                            "message": diag["message"],
                        }
                    )
            else:
                console.print(
                    f"  [green]✓[/green]  Issue matrix: "
                    f"{len(matrix_result.rows)} row(s) validated"
                )
        else:
            issue_matrix_present = False
            console.print(
                f"  [red]✗[/red]  Issue matrix: "
                f"{MissionReviewDiagnostic.ISSUE_MATRIX_MISSING}: "
                "issue-matrix.md not found (required in post-merge mode)"
            )
            findings.append(
                {
                    "type": "issue_matrix_violation",
                    "diagnostic_code": str(MissionReviewDiagnostic.ISSUE_MATRIX_MISSING),
                    "message": "issue-matrix.md is required in post-merge mode",
                }
            )
    else:
        issue_matrix_present = "not_applicable"

    # ==================================================================
    # Mission exception check
    # ==================================================================
    mission_exception_path = feature_dir / "mission-exception.md"
    if review_mode is MissionReviewMode.POST_MERGE:
        mission_exception_present: bool | str = mission_exception_path.exists()
    else:
        mission_exception_present = "not_applicable"

    # ==================================================================
    # Step 4 — Write report (Gate 4)
    # ==================================================================
    write_review_report(
        feature_dir,
        repo_root,
        findings,
        console,
        mode=review_mode.value,
        gates_recorded=gates_recorded,
        issue_matrix_present=issue_matrix_present,
        mission_exception_present=mission_exception_present,
    )
    gates_recorded.append(
        GateRecord(
            id="gate_4",
            name="report_writer",
            command="spec-kitty review (internal gate 4)",
            exit_code=0,
            result="pass",
        )
    )


__all__ = [
    "Ble001SuppressionFinding",
    "GateRecord",
    "MissionReviewDiagnostic",
    "MissionReviewMode",
    "ModeMismatchError",
    "TestExtraMissing",
    "assert_pytest_available",
    "audit_auth_storage_ble001_line",
    "collect_auth_storage_ble001_findings",
    "resolve_mode",
    "review_mission",
    "validate_issue_matrix",
]
