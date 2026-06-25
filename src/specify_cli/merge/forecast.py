"""Dry-run forecast (preview + payload build) for the merge seam.

Mission #2057 (decompose ``cli/commands/merge.py``) — IC-06 / WP06.

The ``merge --dry-run`` preview was extracted byte-for-byte out of the ``merge``
command body: lanes-manifest load, the review-artifact consistency gate preview
(emits ``REJECTED_REVIEW_ARTIFACT_CONFLICT`` in both human and JSON output), the
``would_assign_mission_number`` scan, and the JSON/human payload build. The
dry-run JSON key set is frozen by contracts/cli-surface-contract.md (FR-001,
FR-004) and re-asserted by the golden CLI test. One-way import: this module
never imports the command shim.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli.helpers import console
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.core.paths import get_main_repo_root
from specify_cli.lanes.persistence import (
    CorruptLanesError,
    MissingLanesError,
    require_lanes_json,
)
from specify_cli.merge._constants import logger
from specify_cli.merge.config import MergeStrategy
from specify_cli.merge.ordering import assign_next_mission_number
from specify_cli.merge.state import needs_number_assignment
from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission
from specify_cli.post_merge.review_artifact_consistency import (
    REJECTED_REVIEW_ARTIFACT_CONFLICT,
    ReviewArtifactPreflightResult,
    format_review_artifact_finding,
    review_artifact_finding_diagnostic,
    run_review_artifact_consistency_preflight,
)


def _emit_dry_run_error(*, error_msg: str, json_output: bool) -> None:
    """Emit an unresolved-slug / missing-lanes dry-run error in the right channel."""
    if json_output:
        print(json.dumps({"spec_kitty_version": SPEC_KITTY_VERSION, "error": error_msg}))
    else:
        console.print(f"[red]Error:[/red] {error_msg}")


def _emit_review_artifact_block(
    review_artifact_preflight: ReviewArtifactPreflightResult,
    *,
    main_repo_for_diag: Path,
    resolved_feature: str,
    resolved_target_branch: str,
    json_output: bool,
) -> None:
    """Emit the review-artifact gate failure (REJECTED_REVIEW_ARTIFACT_CONFLICT)."""
    diagnostics = review_artifact_preflight.diagnostics(
        repo_root=main_repo_for_diag,
    )
    if json_output:
        diagnostic_code = (
            diagnostics[0]["diagnostic_code"]
            if diagnostics
            else REJECTED_REVIEW_ARTIFACT_CONFLICT
        )
        print(
            json.dumps(
                {
                    "spec_kitty_version": SPEC_KITTY_VERSION,
                    "mission_slug": resolved_feature,
                    "target_branch": resolved_target_branch,
                    "blocked": True,
                    "blockers": diagnostics,
                    "diagnostic_code": diagnostic_code,
                }
            )
        )
        return

    console.print("[red]Error:[/red] Review artifact consistency gate failed.")
    for finding in review_artifact_preflight.findings:
        diagnostic = review_artifact_finding_diagnostic(
            finding,
            repo_root=main_repo_for_diag,
        )
        console.print(
            f"  - {format_review_artifact_finding(finding, repo_root=main_repo_for_diag)}"
        )
        console.print(f"    diagnostic_code: {diagnostic['diagnostic_code']}")
        console.print(f"    branch_or_work_package: {diagnostic['branch_or_work_package']}")
        console.print(f"    violated_invariant: {diagnostic['violated_invariant']}")
        console.print(f"    latest_review_cycle_path: {diagnostic['latest_review_cycle_path']}")
        if "latest_review_cycle_verdict" in diagnostic:
            console.print(
                f"    latest_review_cycle_verdict: {diagnostic['latest_review_cycle_verdict']}"
            )
        if "schema_error" in diagnostic:
            console.print(f"    schema_error: {diagnostic['schema_error']}")
        remediation = diagnostic.get("remediation", [])
        if not isinstance(remediation, list):
            remediation = [str(remediation)]
        for line in remediation:
            console.print(f"    remediation: {line}")
    console.print(f"  Mission: {resolved_feature}")


def _scan_would_assign_mission_number(repo_root: Path, feature_dir_for_preview: Path) -> int | None:
    """Best-effort dry-run preview of merge-time mission_number assignment (WP10/T053)."""
    if not needs_number_assignment(feature_dir_for_preview):
        return None
    try:
        result: int = assign_next_mission_number(
            get_main_repo_root(repo_root),
            get_main_repo_root(repo_root) / KITTY_SPECS_DIR,
        )
        return result
    except Exception as exc:  # noqa: BLE001 — dry-run mission_number scan is best-effort; an unavailable kitty-specs dir must not crash the preview
        logger.warning("dry-run mission_number scan failed: %s", exc)
        return None


def run_dry_run_forecast(
    *,
    repo_root: Path,
    resolved_feature: str | None,
    resolved_target_branch: str,
    resolved_strategy: MergeStrategy,
    delete_branch: bool,
    remove_worktree: bool,
    push: bool,
    json_output: bool,
) -> None:
    """Render the ``merge --dry-run`` forecast and exit.

    Behavior-preserving extraction of the dry-run block from the ``merge``
    command body. Always terminates the dry-run path (returns on success after
    printing the payload; raises ``typer.Exit(1)`` on unresolved slug / missing
    lanes / review-artifact conflict).
    """
    if not resolved_feature:
        _emit_dry_run_error(
            error_msg="Mission slug could not be resolved. Use --mission <slug>.",
            json_output=json_output,
        )
        raise typer.Exit(1)

    try:
        lanes_manifest = require_lanes_json(
            candidate_feature_dir_for_mission(get_main_repo_root(repo_root), resolved_feature)
        )
    except (MissingLanesError, CorruptLanesError) as exc:
        _emit_dry_run_error(error_msg=str(exc), json_output=json_output)
        raise typer.Exit(1) from exc

    feature_dir_for_preview = candidate_feature_dir_for_mission(
        get_main_repo_root(repo_root), resolved_feature
    )

    # FR-007/FR-008/FR-009: Run the same review-artifact consistency gate
    # that real merge runs (issue #991). When a rejected review-cycle
    # artifact still sits on an approved/done WP, real merge exits with
    # REJECTED_REVIEW_ARTIFACT_CONFLICT — dry-run must surface the same
    # blocker in both human and JSON output, so operators can trust the
    # preview as a readiness signal.
    dry_run_all_wp_ids: list[str] = [
        wp for lane in lanes_manifest.lanes for wp in lane.wp_ids
    ]
    review_artifact_preflight = run_review_artifact_consistency_preflight(
        feature_dir_for_preview,
        wp_ids=dry_run_all_wp_ids,
    )
    if not review_artifact_preflight.passed:
        _emit_review_artifact_block(
            review_artifact_preflight,
            main_repo_for_diag=get_main_repo_root(repo_root),
            resolved_feature=resolved_feature,
            resolved_target_branch=resolved_target_branch,
            json_output=json_output,
        )
        raise typer.Exit(1)

    would_assign_number = _scan_would_assign_mission_number(repo_root, feature_dir_for_preview)

    payload: dict[str, object] = {
        "spec_kitty_version": SPEC_KITTY_VERSION,
        "mission_slug": resolved_feature,
        "target_branch": resolved_target_branch,
        "strategy": resolved_strategy.value,
        "delete_branch": delete_branch,
        "remove_worktree": remove_worktree,
        "push": push,
        "mission_branch": lanes_manifest.mission_branch,
        "lanes": [lane.to_dict() for lane in lanes_manifest.lanes],
        "would_assign_mission_number": would_assign_number,
    }
    if would_assign_number is not None and not json_output:
        console.print(
            f"[cyan]would assign[/cyan] mission_number={would_assign_number} to mission {resolved_feature}"
        )
    if json_output:
        print(json.dumps(payload))
    else:
        console.print_json(json.dumps(payload))


__all__ = ["run_dry_run_forecast"]
