"""Gate function for bulk edit occurrence classification.

Blocks implementation and review for missions marked change_mode: bulk_edit
when the occurrence_map.yaml is missing or structurally incomplete.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specify_cli.mission_metadata import load_meta
from specify_cli.bulk_edit.diff_check import (
    DiffCheckResult,
    check_diff_compliance,
)
from specify_cli.bulk_edit.occurrence_map import (
    check_admissibility,
    load_occurrence_map,
    validate_occurrence_map,
)


@dataclass(frozen=True)
class GateResult:
    """Outcome of the occurrence classification gate check."""

    passed: bool
    change_mode: str | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def ensure_occurrence_classification_ready(feature_dir: Path) -> GateResult:
    """Check if a bulk_edit mission has a valid occurrence map.

    For non-bulk-edit missions, always passes (zero cost).
    """
    meta = load_meta(feature_dir)
    if meta is None:
        return GateResult(passed=True, change_mode=None)

    change_mode = meta.get("change_mode")
    if change_mode != "bulk_edit":
        return GateResult(passed=True, change_mode=change_mode)

    # Load and validate occurrence map
    omap = load_occurrence_map(feature_dir)
    if omap is None:
        return GateResult(
            passed=False,
            change_mode="bulk_edit",
            errors=[f"Occurrence map required for bulk_edit missions. Create {feature_dir}/occurrence_map.yaml with target, categories, and actions."],
        )

    validation = validate_occurrence_map(omap)
    if not validation.valid:
        return GateResult(
            passed=False,
            change_mode="bulk_edit",
            errors=validation.errors,
            warnings=validation.warnings,
        )

    admissibility = check_admissibility(omap)
    if not admissibility.valid:
        return GateResult(
            passed=False,
            change_mode="bulk_edit",
            errors=admissibility.errors,
            warnings=admissibility.warnings,
        )

    return GateResult(
        passed=True,
        change_mode="bulk_edit",
        warnings=validation.warnings + admissibility.warnings,
    )


def render_gate_failure(result: GateResult, console: Console) -> None:
    """Display gate failure with Rich formatting."""
    panel = Panel(
        "\n".join(f"  \u2022 {e}" for e in result.errors),
        title="[bold red]Bulk Edit Gate: BLOCKED[/]",
        subtitle="Create or fix occurrence_map.yaml before proceeding",
        border_style="red",
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Review-time diff compliance (FR-007 + FR-008)
# ---------------------------------------------------------------------------


def _git_diff_files(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> list[str]:
    """Return the list of files changed between *base_ref* and *head_ref*.

    Uses ``git diff --name-only <base>..<head>`` and returns one path per
    line, relative to *repo_root*. Returns an empty list on any git failure;
    the caller is responsible for deciding whether an empty diff is
    acceptable.
    """
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}..{head_ref}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def check_review_diff_compliance(
    feature_dir: Path,
    repo_root: Path,
    base_ref: str,
    head_ref: str,
) -> DiffCheckResult | None:
    """Run the review-time diff compliance check (FR-007 + FR-008).

    Returns ``None`` when the mission is not a bulk_edit — callers should
    skip any further review-time checks in that case.

    Returns a :class:`DiffCheckResult` with ``passed`` set according to
    whether the diff respects the occurrence map's category actions and
    exceptions. Callers are expected to render the result via
    :func:`render_diff_check_failure` and ``raise typer.Exit(1)`` when
    ``passed`` is False.
    """
    meta = load_meta(feature_dir)
    if meta is None or meta.get("change_mode") != "bulk_edit":
        return None

    omap = load_occurrence_map(feature_dir)
    if omap is None:
        # The artifact-admissibility gate should have rejected this case
        # already; if we got here, something is off — fall through and
        # surface the error.
        return DiffCheckResult(
            passed=False,
            errors=["Review diff check cannot run: occurrence_map.yaml is missing despite change_mode: bulk_edit."],
        )

    changed_files = _git_diff_files(repo_root, base_ref, head_ref)
    return check_diff_compliance(changed_files, omap)


def render_diff_check_failure(
    result: DiffCheckResult,
    console: Console,
) -> None:
    """Display a diff compliance failure with a Rich table of assessments."""
    table = Table(title="Bulk Edit Review: Diff Compliance", show_lines=False)
    table.add_column("File", overflow="fold")
    table.add_column("Category", no_wrap=True)
    table.add_column("Action", no_wrap=True)
    table.add_column("Verdict", no_wrap=True)
    for a in result.assessments:
        verdict = "[bold red]BLOCK[/]" if a.violation else ("[yellow]review[/]" if a.action == "manual_review" else "[green]ok[/]")
        table.add_row(
            a.path,
            a.category or "(unclassified)",
            a.action or "(none)",
            verdict,
        )
    console.print(table)

    if result.errors:
        panel = Panel(
            "\n".join(f"  \u2022 {e}" for e in result.errors),
            title="[bold red]Review Rejected: Diff Compliance Violations[/]",
            subtitle="FR-007/FR-008 — forbidden or unclassified surfaces touched",
            border_style="red",
        )
        console.print(panel)
