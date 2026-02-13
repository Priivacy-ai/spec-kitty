"""Research command implementation for Spec Kitty CLI."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from specify_cli.acceptance import AcceptanceError, detect_feature_slug
from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit, show_banner
from specify_cli.core import MISSION_CHOICES
from specify_cli.core.project_resolver import resolve_template_path, resolve_worktree_aware_feature_dir
from specify_cli.mission import get_feature_mission_key
from specify_cli.plan_validation import PlanValidationError, validate_plan_filled
from specify_cli.tasks_support import TaskCliError, find_repo_root


def research(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug to target (auto-detected when omitted)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing research artifacts"),
) -> None:
    """Execute Phase 0 research workflow to scaffold artifacts."""

    show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    project_root = get_project_root_or_exit(repo_root)
    check_version_compatibility(project_root, "research")

    tracker = StepTracker("Research Phase Setup")
    tracker.add("project", "Locate project root")
    tracker.add("feature", "Resolve feature directory")
    tracker.add("research-md", "Ensure research.md")
    tracker.add("data-model", "Ensure data-model.md")
    tracker.add("research-csv", "Ensure research CSV stubs")
    tracker.add("summary", "Summarize outputs")
    console.print()

    tracker.start("project")
    tracker.complete("project", str(project_root))

    tracker.start("feature")
    try:
        feature_slug = (feature or detect_feature_slug(repo_root, cwd=Path.cwd())).strip()
    except AcceptanceError as exc:
        tracker.error("feature", str(exc))
        console.print(tracker.render())
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    feature_dir = resolve_worktree_aware_feature_dir(repo_root, feature_slug, Path.cwd(), console)
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Get mission from feature's meta.json (not project-level default)
    mission_key = get_feature_mission_key(feature_dir)
    mission_display = MISSION_CHOICES.get(mission_key, mission_key)
    tracker.complete("feature", f"{feature_dir} ({mission_display})")

    # Validate that plan.md has been filled out before proceeding
    plan_path = feature_dir / "plan.md"
    try:
        validate_plan_filled(plan_path, feature_slug=feature_slug, strict=True)
    except PlanValidationError as exc:
        console.print(tracker.render())
        console.print()
        console.print(f"[red]Error:[/red] {exc}")
        console.print()
        console.print("[yellow]Next steps:[/yellow]")
        console.print("  1. Run [cyan]/spec-kitty.plan[/cyan] to fill in the technical architecture")
        console.print("  2. Complete all [FEATURE], [DATE], and technical context placeholders")
        console.print("  3. Remove [REMOVE IF UNUSED] sections and choose your project structure")
        console.print("  4. Then run [cyan]/spec-kitty.research[/cyan] again")
        raise typer.Exit(1)

    created_paths: list[Path] = []

    def _copy_asset(step_key: str, label: str, relative_path: Path, template_name: Path) -> None:
        tracker.start(step_key)
        dest_path = feature_dir / relative_path
        template_path = resolve_template_path(project_root, mission_key, template_name)

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dest_path.exists() and not force:
                created_paths.append(dest_path)
                return
            if template_path and template_path.is_file():
                shutil.copy2(template_path, dest_path)
            else:
                if dest_path.exists():
                    dest_path.unlink()
                dest_path.touch()
            created_paths.append(dest_path)
            tracker.complete(step_key, label)
        except Exception as exc:  # pragma: no cover - surfaces filesystem errors
            tracker.error(step_key, str(exc))
            console.print(tracker.render())
            raise typer.Exit(1)

    _copy_asset("research-md", "research.md ready", Path("research.md"), Path("research.md"))
    _copy_asset("data-model", "data-model.md ready", Path("data-model.md"), Path("data-model.md"))

    tracker.start("research-csv")
    csv_targets = [
        (Path("research") / "evidence-log.csv", Path("research") / "evidence-log.csv"),
        (Path("research") / "source-register.csv", Path("research") / "source-register.csv"),
    ]
    csv_errors: list[str] = []
    for dest_rel, template_rel in csv_targets:
        dest_path = feature_dir / dest_rel
        template_path = resolve_template_path(project_root, mission_key, template_rel)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dest_path.exists() and not force:
                created_paths.append(dest_path)
                continue
            if template_path and template_path.is_file():
                shutil.copy2(template_path, dest_path)
            else:
                if dest_path.exists():
                    dest_path.unlink()
                dest_path.touch()
            created_paths.append(dest_path)
        except Exception as exc:  # pragma: no cover
            csv_errors.append(f"{dest_rel}: {exc}")

    if csv_errors:
        tracker.error("research-csv", "; ".join(csv_errors))
        console.print(tracker.render())
        raise typer.Exit(1)
    else:
        tracker.complete("research-csv", "CSV templates ready")

    # T015: Run gap analysis for documentation missions
    mission_key_value = get_feature_mission_key(feature_dir)
    if mission_key_value == "documentation":
        tracker.add("gap-analysis", "Gap analysis for documentation")
        tracker.start("gap-analysis")
        try:
            from specify_cli.doc_state import read_documentation_state, set_audit_metadata
            from specify_cli.gap_analysis import generate_gap_analysis_report

            meta_file = feature_dir / "meta.json"
            doc_state = None
            if meta_file.exists():
                doc_state = read_documentation_state(meta_file)

            iteration_mode = "initial"
            if doc_state:
                iteration_mode = doc_state.get("iteration_mode", "initial")

            if iteration_mode in ("gap_filling", "feature_specific"):
                docs_dir = repo_root / "docs"
                if docs_dir.exists():
                    gap_analysis_output = feature_dir / "gap-analysis.md"
                    analysis = generate_gap_analysis_report(
                        docs_dir, gap_analysis_output, project_root=repo_root
                    )
                    created_paths.append(gap_analysis_output)

                    # Update documentation state with audit metadata
                    if meta_file.exists():
                        set_audit_metadata(
                            meta_file,
                            last_audit_date=analysis.analysis_date,
                            coverage_percentage=analysis.coverage_matrix.get_coverage_percentage(),
                        )

                    coverage_pct = analysis.coverage_matrix.get_coverage_percentage() * 100
                    tracker.complete(
                        "gap-analysis",
                        f"Gap analysis ready (coverage: {coverage_pct:.1f}%)"
                    )
                else:
                    tracker.complete("gap-analysis", "Skipped: no docs/ directory found")
            else:
                tracker.complete("gap-analysis", f"Skipped: iteration_mode={iteration_mode}")
        except Exception as gap_err:
            tracker.error("gap-analysis", f"Failed: {gap_err}")

    tracker.start("summary")
    tracker.complete("summary", f"{len(created_paths)} artifacts ready")

    console.print(tracker.render())

    relative_paths = [
        str(path.relative_to(feature_dir)) if path.is_relative_to(feature_dir) else str(path)
        for path in created_paths
    ]
    summary_lines = "\n".join(f"- [cyan]{rel}[/cyan]" for rel in sorted(set(relative_paths)))
    console.print()
    console.print(
        Panel(
            summary_lines or "No artifacts were created (existing files kept).",
            title="Research Artifacts",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


__all__ = ["research"]
