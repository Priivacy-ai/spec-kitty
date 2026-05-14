"""Gate 1: WP lane consistency check.

Extracted verbatim from src/specify_cli/cli/commands/review.py (WP07).
No behaviour change.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from rich.console import Console

from specify_cli.post_merge.review_artifact_consistency import (
    find_rejected_review_artifact_conflicts,
    format_review_artifact_conflict,
    review_artifact_conflict_diagnostic,
)
from specify_cli.status.reducer import materialize


def check_wp_lanes(
    feature_dir: Path,
    repo_root: Path,
    console: Console,
    findings: list[dict[str, str]],
) -> None:
    """Step 1 — WP lane check.

    Appends findings to the provided list and prints to console.
    """
    snapshot = materialize(feature_dir)
    non_done = [
        wp_id
        for wp_id, state in snapshot.work_packages.items()
        if state.get("lane") != "done"
    ]
    if non_done:
        console.print(
            f"  [red]✗[/red]  WP lane check: {len(non_done)} WP(s) not in done"
        )
        for wp_id in non_done:
            lane_val = snapshot.work_packages[wp_id].get("lane", "unknown")
            console.print(f"       {wp_id}: {lane_val}")
            findings.append(
                {"type": "wp_not_done", "wp_id": wp_id, "lane": str(lane_val)}
            )
    else:
        console.print(
            f"  [green]✓[/green]  WP lane check: all {len(snapshot.work_packages)} WP(s) in done"
        )

    review_artifact_conflicts = find_rejected_review_artifact_conflicts(feature_dir)
    if review_artifact_conflicts:
        console.print(
            "  [red]✗[/red]  Review artifact consistency: latest rejected artifact "
            "exists for terminal WP(s)"
        )
        for conflict in review_artifact_conflicts:
            diagnostic = review_artifact_conflict_diagnostic(
                conflict,
                repo_root=repo_root,
            )
            console.print(
                f"       {format_review_artifact_conflict(conflict, repo_root=repo_root)}"
            )
            console.print(f"       diagnostic_code: {diagnostic['diagnostic_code']}")
            console.print(
                f"       branch_or_work_package: {diagnostic['branch_or_work_package']}"
            )
            console.print(
                f"       violated_invariant: {diagnostic['violated_invariant']}"
            )
            for line in cast(list[str], diagnostic["remediation"]):
                console.print(f"       remediation: {line}")
            findings.append(
                {
                    "type": "rejected_review_artifact",
                    "wp_id": conflict.wp_id,
                    "lane": conflict.lane,
                    "artifact_path": str(conflict.artifact_path),
                    "diagnostic_code": str(diagnostic["diagnostic_code"]),
                    "branch_or_work_package": str(
                        diagnostic["branch_or_work_package"]
                    ),
                    "violated_invariant": str(diagnostic["violated_invariant"]),
                    "remediation": "; ".join(
                        str(line) for line in cast(list[str], diagnostic["remediation"])
                    ),
                    "latest_review_cycle_verdict": str(
                        diagnostic["latest_review_cycle_verdict"]
                    ),
                }
            )
    else:
        console.print(
            "  [green]✓[/green]  Review artifact consistency: no terminal WP has a latest rejected artifact"
        )
