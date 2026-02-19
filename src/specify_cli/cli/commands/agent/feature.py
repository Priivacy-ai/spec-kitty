"""Feature lifecycle commands for AI agents."""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from importlib.resources import files
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.cli.commands.accept import accept as top_level_accept
from specify_cli.cli.commands.merge import merge as top_level_merge
from specify_cli.core.dependency_graph import (
    detect_cycles,
    validate_dependencies,
)
from specify_cli.core.git_ops import get_current_branch, is_git_repo, run_command
from specify_cli.core.paths import is_worktree_context, locate_project_root
from specify_cli.core.feature_detection import (
    detect_feature_directory,
    FeatureDetectionError,
)
from specify_cli.git import safe_commit
from specify_cli.core.worktree import (
    get_next_feature_number,
    validate_feature_structure,
)
from specify_cli.frontmatter import read_frontmatter, write_frontmatter
from specify_cli.mission import get_feature_mission_key
from specify_cli.sync.events import emit_feature_created, emit_wp_created, get_emitter

app = typer.Typer(
    name="feature",
    help="Feature lifecycle commands for AI agents",
    no_args_is_help=True
)

console = Console()


def _resolve_primary_branch(repo_root: Path) -> str:
    """Resolve the primary branch name (main, master, etc.).

    Delegates to the centralized implementation in core.git_ops.
    """
    from specify_cli.core.git_ops import resolve_primary_branch
    return resolve_primary_branch(repo_root)


def _resolve_planning_branch(repo_root: Path, feature_dir: Path | None = None) -> str:
    """Resolve the planning branch for a feature (target_branch if set, else current branch)."""
    current_branch = get_current_branch(repo_root) or _resolve_primary_branch(repo_root)
    if feature_dir is None:
        return current_branch

    meta_file = feature_dir / "meta.json"
    if not meta_file.exists():
        return current_branch

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return current_branch

    target_branch = meta.get("target_branch")
    return target_branch or current_branch


def _ensure_branch_checked_out(
    repo_root: Path,
    target_branch: str,
    json_output: bool = False,
) -> None:
    """Check branch context without auto-checkout (respects user's current branch).

    Shows notification if current branch differs from target branch.
    Does NOT perform git checkout.
    """
    if not (repo_root / ".git").exists():
        return

    current_branch = get_current_branch(repo_root)
    if current_branch is None:
        return
    if current_branch == "HEAD":
        raise RuntimeError("Planning repo is in detached HEAD state; checkout a branch before continuing")

    # If branches differ, show notification (no auto-checkout)
    if current_branch != target_branch:
        if not json_output:
            console.print(
                f"[yellow]Note:[/yellow] You are on '{current_branch}', "
                f"feature targets '{target_branch}'. "
                f"Operations will use '{current_branch}'."
            )


def _should_emit_execution_event(
    *,
    agent: Optional[str],
    model: Optional[str],
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    cost_usd: Optional[float],
    duration_ms: Optional[int],
) -> bool:
    """Emit execution telemetry only when caller supplied telemetry context."""
    return any(
        value is not None
        for value in (agent, model, input_tokens, output_tokens, cost_usd, duration_ms)
    )


def _commit_to_branch(
    file_path: Path,
    feature_slug: str,
    artifact_type: str,
    repo_root: Path,
    target_branch: str,
    json_output: bool = False,
) -> None:
    """Commit planning artifact to current branch (respects user context).

    Args:
        file_path: Path to file being committed
        feature_slug: Feature slug (e.g., "001-my-feature")
        artifact_type: Type of artifact ("spec", "plan", "tasks")
        repo_root: Repository root path (ensures commits go to planning repo, not worktree)
        target_branch: Branch feature targets (for informational messages only)
        json_output: If True, suppress Rich console output

    Raises:
        subprocess.CalledProcessError: If commit fails unexpectedly
    """
    try:
        current_branch = get_current_branch(repo_root)
        if current_branch is None:
            raise RuntimeError("Not in a git repository")

        # Commit only this file (preserves staging area)
        commit_msg = f"Add {artifact_type} for feature {feature_slug}"
        success = safe_commit(
            repo_path=repo_root,
            files_to_commit=[file_path],
            commit_message=commit_msg,
            allow_empty=False,
        )
        if not success:
            error_msg = f"Failed to commit {artifact_type}"
            if not json_output:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise RuntimeError(error_msg)

        if not json_output:
            console.print(f"[green]✓[/green] {artifact_type.capitalize()} committed to {current_branch}")

    except subprocess.CalledProcessError as e:
        # Check if it's just "nothing to commit" (benign)
        stderr = e.stderr if hasattr(e, 'stderr') and e.stderr else ""
        if "nothing to commit" in stderr or "nothing added to commit" in stderr:
            # Benign - file unchanged
            if not json_output:
                console.print(f"[dim]{artifact_type.capitalize()} unchanged, no commit needed[/dim]")
        else:
            # Actual error
            if not json_output:
                console.print(f"[yellow]Warning:[/yellow] Failed to commit {artifact_type}: {e}")
                console.print(f"[yellow]You may need to commit manually:[/yellow] git add {file_path} && git commit")
            raise


def _commit_to_main(
    file_path: Path,
    feature_slug: str,
    artifact_type: str,
    repo_root: Path,
    target_branch: str,
    json_output: bool = False,
) -> None:
    """Backward-compatible alias used by legacy tests."""
    _commit_to_branch(
        file_path=file_path,
        feature_slug=feature_slug,
        artifact_type=artifact_type,
        repo_root=repo_root,
        target_branch=target_branch,
        json_output=json_output,
    )


def _find_feature_directory(repo_root: Path, cwd: Path, explicit_feature: str | None = None) -> Path:
    """Find the current feature directory using centralized detection.

    This function now uses the centralized feature detection module
    to provide deterministic, consistent behavior across all commands.

    Args:
        repo_root: Repository root path
        cwd: Current working directory
        explicit_feature: Optional explicit feature slug from --feature flag

    Returns:
        Path to feature directory

    Raises:
        ValueError: If feature directory cannot be determined
        FeatureDetectionError: If detection fails
    """
    try:
        return detect_feature_directory(
            repo_root,
            explicit_feature=explicit_feature,
            cwd=cwd,
            mode="strict"  # Raise error if ambiguous
        )
    except FeatureDetectionError as e:
        # Convert to ValueError for backward compatibility
        raise ValueError(str(e)) from e


@app.command(name="create-feature")
def create_feature(
    feature_slug: Annotated[str, typer.Argument(help="Feature slug (e.g., 'user-auth')")],
    mission: Annotated[Optional[str], typer.Option("--mission", help="Mission type (e.g., 'documentation', 'software-dev')")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent identifier (for telemetry)")] = None,
    model: Annotated[Optional[str], typer.Option("--model", help="Model used (for telemetry)")] = None,
    input_tokens: Annotated[Optional[int], typer.Option("--input-tokens", help="Input tokens consumed (for telemetry)")] = None,
    output_tokens: Annotated[Optional[int], typer.Option("--output-tokens", help="Output tokens generated (for telemetry)")] = None,
    cost_usd: Annotated[Optional[float], typer.Option("--cost-usd", help="Cost in USD (for telemetry)")] = None,
    duration_ms: Annotated[Optional[int], typer.Option("--duration-ms", help="Duration in milliseconds (for telemetry)")] = None,
) -> None:
    """Create new feature directory structure in planning repository.

    This command is designed for AI agents to call programmatically.
    Creates feature directory in kitty-specs/ and commits to the current branch.

    Examples:
        spec-kitty agent create-feature "new-dashboard" --json
        spec-kitty agent create-feature "new-dashboard" --agent claude --model claude-sonnet-4.5 --input-tokens 5000 --output-tokens 2500
    """
    # Validate kebab-case format early (before any operations)
    KEBAB_CASE_PATTERN = r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
    if not re.match(KEBAB_CASE_PATTERN, feature_slug):
        error_msg = (
            f"Invalid feature slug '{feature_slug}'. "
            "Must be kebab-case (lowercase letters, numbers, hyphens only)."
            "\n\nValid examples:"
            "\n  - user-auth"
            "\n  - fix-bug-123"
            "\n  - new-dashboard"
            "\n\nInvalid examples:"
            "\n  - User-Auth (uppercase)"
            "\n  - user_auth (underscores)"
            "\n  - 123-fix (starts with number)"
        )
        if json_output:
            console.print(json.dumps({"error": error_msg}))
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)

    try:
        # GUARD: Refuse to run from inside a worktree (must be in planning repo)
        cwd = Path.cwd().resolve()
        if is_worktree_context(cwd):
            error_msg = "Cannot create features from inside a worktree. Run from the planning repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[bold red]Error:[/bold red] {error_msg}")
                # Find and suggest the main repo path
                for i, part in enumerate(cwd.parts):
                    if part == ".worktrees":
                        main_repo = Path(*cwd.parts[:i])
                        console.print("\n[cyan]Run from the main repository instead:[/cyan]")
                        console.print(f"  cd {main_repo}")
                        console.print(f"  spec-kitty agent create-feature {feature_slug}")
                        break
            raise typer.Exit(1)

        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Verify we're in a git repository
        if not is_git_repo(repo_root):
            error_msg = "Not in a git repository. Feature creation requires git."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Verify we're on a branch (not detached HEAD)
        current_branch = get_current_branch(repo_root)
        if not current_branch or current_branch == "HEAD":
            error_msg = "Must be on a branch to create features (detached HEAD detected)."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Guardrail: feature creation must happen on the primary branch.
        primary_branch = _resolve_primary_branch(repo_root)
        if current_branch != primary_branch:
            error_msg = (
                f"Feature creation must run on '{primary_branch}' branch "
                f"(current: '{current_branch}')."
            )
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)
        planning_branch = current_branch

        # Get next feature number
        feature_number = get_next_feature_number(repo_root)
        feature_slug_formatted = f"{feature_number:03d}-{feature_slug}"

        # Create feature directory in main repo
        feature_dir = repo_root / "kitty-specs" / feature_slug_formatted
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (feature_dir / "checklists").mkdir(exist_ok=True)
        (feature_dir / "research").mkdir(exist_ok=True)
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        # Create tasks/.gitkeep and README.md
        (tasks_dir / ".gitkeep").touch()

        # Create tasks/README.md (using same content from setup_feature_directory)
        tasks_readme_content = '''# Tasks Directory

This directory contains work package (WP) prompt files with lane status in frontmatter.

## Directory Structure (v0.9.0+)

```
tasks/
├── WP01-setup-infrastructure.md
├── WP02-user-authentication.md
├── WP03-api-endpoints.md
└── README.md
```

All WP files are stored flat in `tasks/`. The lane (planned, doing, for_review, done) is stored in the YAML frontmatter `lane:` field.

## Work Package File Format

Each WP file **MUST** use YAML frontmatter:

```yaml
---
work_package_id: "WP01"
title: "Work Package Title"
lane: "planned"
subtasks:
  - "T001"
  - "T002"
phase: "Phase 1 - Setup"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-01-01T00:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Work Package Title

[Content follows...]
```

## Valid Lane Values

- `planned` - Ready for implementation
- `doing` - Currently being worked on
- `for_review` - Awaiting review
- `done` - Completed

## Moving Between Lanes

Use the CLI (updates frontmatter only, no file movement):
```bash
spec-kitty agent tasks move-task <WPID> --to <lane>
```

Example:
```bash
spec-kitty agent tasks move-task WP01 --to doing
```

## File Naming

- Format: `WP01-kebab-case-slug.md`
- Examples: `WP01-setup-infrastructure.md`, `WP02-user-auth.md`
'''
        (tasks_dir / "README.md").write_text(tasks_readme_content, encoding='utf-8')

        # Copy spec template if it exists
        spec_file = feature_dir / "spec.md"
        if not spec_file.exists():
            spec_template_candidates = [
                repo_root / ".kittify" / "templates" / "spec-template.md",
                repo_root / "templates" / "spec-template.md",
            ]

            for template in spec_template_candidates:
                if template.exists():
                    shutil.copy2(template, spec_file)
                    break
            else:
                # No template found, create empty spec.md
                spec_file.touch()

        # Commit spec.md to planning branch
        _commit_to_main(spec_file, feature_slug_formatted, "spec", repo_root, planning_branch, json_output)

        # Ensure baseline feature metadata exists for downstream commands
        # (implement/merge/mission detection rely on meta.json in every mission).
        meta_file = feature_dir / "meta.json"
        meta: dict[str, object] = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}

        meta.setdefault("feature_number", f"{feature_number:03d}")
        meta.setdefault("slug", feature_slug_formatted)
        meta.setdefault("feature_slug", feature_slug_formatted)
        meta.setdefault("friendly_name", feature_slug.replace("-", " ").strip())
        meta.setdefault("mission", mission or "software-dev")
        meta.setdefault("target_branch", planning_branch)
        meta.setdefault("created_at", datetime.now(timezone.utc).isoformat())

        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        try:
            _commit_to_branch(
                meta_file,
                feature_slug_formatted,
                "meta",
                repo_root,
                planning_branch,
                json_output,
            )
        except Exception:
            # Non-fatal: file is still present for local workflows.
            pass

        # T013: Initialize documentation state if mission is documentation
        if mission == "documentation":
            meta.setdefault("mission", "documentation")
            if "documentation_state" not in meta:
                meta["documentation_state"] = {
                    "iteration_mode": "initial",
                    "divio_types_selected": [],
                    "generators_configured": [],
                    "target_audience": "developers",
                    "last_audit_date": None,
                    "coverage_percentage": 0.0,
                }
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            try:
                _commit_to_branch(
                    meta_file,
                    feature_slug_formatted,
                    "meta",
                    repo_root,
                    planning_branch,
                    json_output,
                )
            except Exception:
                pass
            if not json_output:
                console.print("[cyan]→ Documentation state initialized in meta.json[/cyan]")

        # Emit FeatureCreated event (non-blocking)
        try:
            emit_feature_created(
                feature_slug=feature_slug_formatted,
                feature_number=f"{feature_number:03d}",
                target_branch=planning_branch,
                wp_count=0,
            )
        except Exception:
            pass  # Non-blocking, event emission failures are not fatal

        # Emit ExecutionEvent for telemetry (always emit, nullable fields OK)
        if _should_emit_execution_event(
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        ):
            try:
                from specify_cli.telemetry.emit import emit_execution_event
                emit_execution_event(
                    feature_dir=feature_dir,
                    feature_slug=feature_slug_formatted,
                    wp_id="N/A",  # No WP for feature creation
                    agent=agent or "unknown",
                    role="planner",  # Planning role, not implementer
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    duration_ms=duration_ms or 0,
                    success=True,
                    error=None,
                )
            except Exception as e:
                # Non-blocking: log but don't fail command
                if not json_output:
                    console.print(f"[yellow]Warning:[/yellow] Telemetry emission failed: {e}")

        if json_output:
            print(json.dumps({
                "result": "success",
                "feature": feature_slug_formatted,
                "feature_dir": str(feature_dir)
            }))
        else:
            console.print(f"[green]✓[/green] Feature created: {feature_slug_formatted}")
            console.print(f"   Directory: {feature_dir}")
            console.print(f"   Spec committed to {planning_branch}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="check-prerequisites")
def check_prerequisites(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    paths_only: Annotated[bool, typer.Option("--paths-only", help="Only output path variables")] = False,
    include_tasks: Annotated[bool, typer.Option("--include-tasks", help="Include tasks.md in validation")] = False,
) -> None:
    """Validate feature structure and prerequisites.

    This command is designed for AI agents to call programmatically.

    Examples:
        spec-kitty agent check-prerequisites --json
        spec-kitty agent check-prerequisites --paths-only --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory (main repo or worktree)
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd)

        validation_result = validate_feature_structure(feature_dir, check_tasks=include_tasks)

        if json_output:
            if paths_only:
                print(json.dumps(validation_result["paths"]))
            else:
                print(json.dumps(validation_result))
        else:
            if validation_result["valid"]:
                console.print("[green]✓[/green] Prerequisites check passed")
                console.print(f"   Feature: {feature_dir.name}")
            else:
                console.print("[red]✗[/red] Prerequisites check failed")
                for error in validation_result["errors"]:
                    console.print(f"   • {error}")

            if validation_result["warnings"]:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in validation_result["warnings"]:
                    console.print(f"   • {warning}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="setup-plan")
def setup_plan(
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (e.g., '020-my-feature')")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent identifier (for telemetry)")] = None,
    model: Annotated[Optional[str], typer.Option("--model", help="Model used (for telemetry)")] = None,
    input_tokens: Annotated[Optional[int], typer.Option("--input-tokens", help="Input tokens consumed (for telemetry)")] = None,
    output_tokens: Annotated[Optional[int], typer.Option("--output-tokens", help="Output tokens generated (for telemetry)")] = None,
    cost_usd: Annotated[Optional[float], typer.Option("--cost-usd", help="Cost in USD (for telemetry)")] = None,
    duration_ms: Annotated[Optional[int], typer.Option("--duration-ms", help="Duration in milliseconds (for telemetry)")] = None,
) -> None:
    """Scaffold implementation plan template in planning repository.

    This command is designed for AI agents to call programmatically.
    Creates plan.md and commits to target branch.

    Examples:
        spec-kitty agent setup-plan --json
        spec-kitty agent setup-plan --feature 020-my-feature --json
        spec-kitty agent setup-plan --agent claude --model claude-sonnet-4.5 --input-tokens 8000 --output-tokens 4000
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory using centralized detection
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd, explicit_feature=feature)

        target_branch = _resolve_planning_branch(repo_root, feature_dir)
        _ensure_branch_checked_out(repo_root, target_branch, json_output)

        plan_file = feature_dir / "plan.md"

        # Find plan template
        plan_template_candidates = [
            repo_root / ".kittify" / "templates" / "plan-template.md",
            repo_root / "src" / "specify_cli" / "templates" / "plan-template.md",
            repo_root / "src" / "specify_cli" / "missions" / "software-dev" / "templates" / "plan-template.md",
            repo_root / "src" / "doctrine" / "templates" / "plan-template.md",
            repo_root / "templates" / "plan-template.md",
        ]

        plan_template = None
        for candidate in plan_template_candidates:
            if candidate.exists():
                plan_template = candidate
                break

        if plan_template is not None:
            shutil.copy2(plan_template, plan_file)
        else:
            package_candidates = [
                files("specify_cli").joinpath("templates", "plan-template.md"),
                files("doctrine").joinpath("templates", "plan-template.md"),
            ]
            package_template = next((p for p in package_candidates if p.exists()), None)
            if package_template is None:
                raise FileNotFoundError("Plan template not found in repository or package")
            with package_template.open("rb") as src, open(plan_file, "wb") as dst:
                shutil.copyfileobj(src, dst)

        # Commit plan.md to target branch
        feature_slug = feature_dir.name
        _commit_to_main(plan_file, feature_slug, "plan", repo_root, target_branch, json_output)

        # T014 + T016: Documentation mission wiring for plan
        mission_key = get_feature_mission_key(feature_dir)
        generators_detected = []

        if mission_key == "documentation":
            from specify_cli.doc_state import (
                read_documentation_state,
                set_audit_metadata,
                set_generators_configured,
            )
            from specify_cli.gap_analysis import generate_gap_analysis_report
            from specify_cli.doc_generators import (
                JSDocGenerator,
                SphinxGenerator,
                RustdocGenerator,
            )

            meta_file = feature_dir / "meta.json"

            # T014: Run gap analysis for gap_filling or feature_specific modes
            if meta_file.exists():
                doc_state = read_documentation_state(meta_file)
                iteration_mode = doc_state.get("iteration_mode", "initial") if doc_state else "initial"

                if iteration_mode in ("gap_filling", "feature_specific"):
                    docs_dir = repo_root / "docs"
                    if docs_dir.exists():
                        gap_analysis_output = feature_dir / "gap-analysis.md"
                        try:
                            analysis = generate_gap_analysis_report(
                                docs_dir, gap_analysis_output, project_root=repo_root
                            )
                            # Update documentation state with audit metadata
                            set_audit_metadata(
                                meta_file,
                                last_audit_date=analysis.analysis_date,
                                coverage_percentage=analysis.coverage_matrix.get_coverage_percentage(),
                            )
                            # Commit gap analysis and updated meta.json
                            try:
                                safe_commit(
                                    repo_path=repo_root,
                                    files_to_commit=[gap_analysis_output, meta_file],
                                    commit_message=f"Add gap analysis for feature {feature_slug}",
                                    allow_empty=False,
                                )
                            except Exception:
                                pass  # Non-fatal: agent can commit separately
                            if not json_output:
                                coverage_pct = analysis.coverage_matrix.get_coverage_percentage() * 100
                                console.print(
                                    f"[cyan]→ Gap analysis generated: {gap_analysis_output.name} "
                                    f"(coverage: {coverage_pct:.1f}%)[/cyan]"
                                )
                        except Exception as gap_err:
                            if not json_output:
                                console.print(
                                    f"[yellow]Warning:[/yellow] Gap analysis failed: {gap_err}"
                                )
                    else:
                        if not json_output:
                            console.print(
                                "[yellow]Warning:[/yellow] No docs/ directory found, skipping gap analysis"
                            )

            # T016: Detect and configure generators
            all_generators = [JSDocGenerator(), SphinxGenerator(), RustdocGenerator()]
            for gen in all_generators:
                try:
                    if gen.detect(repo_root):
                        generators_detected.append({
                            "name": gen.name,
                            "language": gen.languages[0],
                            "config_path": "",
                        })
                        if not json_output:
                            console.print(
                                f"[cyan]→ Detected {gen.name} generator "
                                f"(languages: {', '.join(gen.languages)})[/cyan]"
                            )
                except Exception:
                    pass  # Skip generators that fail detection

            if generators_detected and meta_file.exists():
                try:
                    set_generators_configured(meta_file, generators_detected)
                    try:
                        safe_commit(
                            repo_path=repo_root,
                            files_to_commit=[meta_file],
                            commit_message=f"Update generator config for feature {feature_slug}",
                            allow_empty=False,
                        )
                    except Exception:
                        pass  # Non-fatal
                except Exception as gen_err:
                    if not json_output:
                        console.print(
                            f"[yellow]Warning:[/yellow] Failed to save generator config: {gen_err}"
                        )

        # Emit ExecutionEvent for telemetry (always emit, nullable fields OK)
        if _should_emit_execution_event(
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        ):
            try:
                from specify_cli.telemetry.emit import emit_execution_event
                emit_execution_event(
                    feature_dir=feature_dir,
                    feature_slug=feature_slug,
                    wp_id="N/A",  # No WP for plan creation
                    agent=agent or "unknown",
                    role="planner",
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    duration_ms=duration_ms or 0,
                    success=True,
                    error=None,
                )
            except Exception as e:
                # Non-blocking: log but don't fail command
                if not json_output:
                    console.print(f"[yellow]Warning:[/yellow] Telemetry emission failed: {e}")

        if json_output:
            print(json.dumps({
                "result": "success",
                "plan_file": str(plan_file),
                "feature_dir": str(feature_dir)
            }))
        else:
            console.print(f"[green]✓[/green] Plan scaffolded: {plan_file}")

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

def _find_latest_feature_worktree(repo_root: Path) -> Optional[Path]:
    """Find the latest feature worktree by number.

    Migrated from find_latest_feature_worktree() in common.sh

    Args:
        repo_root: Repository root directory

    Returns:
        Path to latest worktree, or None if no worktrees exist
    """
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return None

    latest_num = 0
    latest_worktree = None

    for worktree_dir in worktrees_dir.iterdir():
        if not worktree_dir.is_dir():
            continue

        # Match pattern: 001-feature-name
        match = re.match(r"^(\d{3})-", worktree_dir.name)
        if match:
            num = int(match.group(1))
            if num > latest_num:
                latest_num = num
                latest_worktree = worktree_dir

    return latest_worktree


def _get_current_branch(repo_root: Path) -> str:
    """Get current git branch name.

    Args:
        repo_root: Repository root directory

    Returns:
        Current branch name, or 'main' if not in a git repo
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False
    )
    return result.stdout.strip() if result.returncode == 0 else _resolve_primary_branch(repo_root)


@app.command(name="accept")
def accept_feature(
    feature: Annotated[
        Optional[str],
        typer.Option(
            "--feature",
            help="Feature directory slug (auto-detected if not specified)"
        )
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Acceptance mode: auto, pr, local, checklist"
        )
    ] = "auto",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON for agent parsing"
        )
    ] = False,
    lenient: Annotated[
        bool,
        typer.Option(
            "--lenient",
            help="Skip strict metadata validation"
        )
    ] = False,
    no_commit: Annotated[
        bool,
        typer.Option(
            "--no-commit",
            help="Skip auto-commit (report only)"
        )
    ] = False,
) -> None:
    """Perform feature acceptance workflow.

    This command:
    1. Validates all tasks are in 'done' lane
    2. Runs acceptance checks from checklist files
    3. Creates acceptance report
    4. Marks feature as ready for merge

    Wrapper for top-level accept command with agent-specific defaults.

    Examples:
        # Run acceptance workflow
        spec-kitty agent feature accept

        # With JSON output for agents
        spec-kitty agent feature accept --json

        # Lenient mode (skip strict validation)
        spec-kitty agent feature accept --lenient --json
    """
    # Delegate to top-level accept command
    try:
        # Call top-level accept with mapped parameters
        top_level_accept(
            feature=feature,
            mode=mode,
            actor=None,  # Agent commands don't use --actor
            test=[],  # Agent commands don't use --test
            json_output=json_output,
            lenient=lenient,
            no_commit=no_commit,
            allow_fail=False,  # Agent commands use strict validation
        )
    except typer.Exit:
        # Propagate typer.Exit cleanly
        raise
    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e), "success": False}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="merge")
def merge_feature(
    feature: Annotated[
        Optional[str],
        typer.Option(
            "--feature",
            help="Feature directory slug (auto-detected if not specified)"
        )
    ] = None,
    target: Annotated[
        Optional[str],
        typer.Option(
            "--target",
            help="Target branch to merge into (auto-detected if not specified)"
        )
    ] = None,
    strategy: Annotated[
        str,
        typer.Option(
            "--strategy",
            help="Merge strategy: merge, squash, rebase"
        )
    ] = "merge",
    push: Annotated[
        bool,
        typer.Option(
            "--push",
            help="Push to origin after merging"
        )
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show actions without executing"
        )
    ] = False,
    keep_branch: Annotated[
        bool,
        typer.Option(
            "--keep-branch",
            help="Keep feature branch after merge (default: delete)"
        )
    ] = False,
    keep_worktree: Annotated[
        bool,
        typer.Option(
            "--keep-worktree",
            help="Keep worktree after merge (default: remove)"
        )
    ] = False,
    auto_retry: Annotated[
        bool,
        typer.Option(
            "--auto-retry/--no-auto-retry",
            help="Auto-navigate to latest worktree if in wrong location"
        )
    ] = True,
) -> None:
    """Merge feature branch into target branch.

    This command:
    1. Validates feature is accepted
    2. Merges feature branch into target (usually 'main')
    3. Cleans up worktree
    4. Deletes feature branch

    Auto-retry logic (from merge-feature.sh):
    If current branch doesn't match feature pattern (XXX-name) and auto-retry is enabled,
    automatically finds and navigates to latest worktree.

    Delegates to existing tasks_cli.py merge implementation.

    Examples:
        # Merge into main branch
        spec-kitty agent feature merge

        # Merge into specific branch with push
        spec-kitty agent feature merge --target develop --push

        # Dry-run mode
        spec-kitty agent feature merge --dry-run

        # Keep worktree and branch after merge
        spec-kitty agent feature merge --keep-worktree --keep-branch
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error = "Could not locate project root"
            print(json.dumps({"error": error, "success": False}))
            sys.exit(1)

        # Resolve target branch dynamically if not specified
        if target is None:
            target = _resolve_primary_branch(repo_root)

        # Auto-retry logic: Check if we're on a feature branch
        if auto_retry and not os.environ.get("SPEC_KITTY_AUTORETRY"):
            current_branch = _get_current_branch(repo_root)
            is_feature_branch = re.match(r"^\d{3}-", current_branch)

            if not is_feature_branch:
                # Try to find latest worktree and retry there
                latest_worktree = _find_latest_feature_worktree(repo_root)
                if latest_worktree:
                    console.print(
                        f"[yellow]Auto-retry:[/yellow] Not on feature branch ({current_branch}). "
                        f"Running merge in {latest_worktree.name}"
                    )

                    # Set env var to prevent infinite recursion
                    env = os.environ.copy()
                    env["SPEC_KITTY_AUTORETRY"] = "1"

                    # Re-run command in worktree
                    retry_cmd = ["spec-kitty", "agent", "feature", "merge"]
                    if feature:
                        retry_cmd.extend(["--feature", feature])
                    retry_cmd.extend(["--target", target, "--strategy", strategy])
                    if push:
                        retry_cmd.append("--push")
                    if dry_run:
                        retry_cmd.append("--dry-run")
                    if keep_branch:
                        retry_cmd.append("--keep-branch")
                    if keep_worktree:
                        retry_cmd.append("--keep-worktree")
                    retry_cmd.append("--no-auto-retry")

                    result = subprocess.run(
                        retry_cmd,
                        cwd=latest_worktree,
                        env=env,
                    )
                    sys.exit(result.returncode)

        # Delegate to top-level merge command with parameter mapping
        # Note: Agent uses --keep-branch/--keep-worktree (default: False)
        #       Top-level uses --delete-branch/--remove-worktree (default: True)
        #       So we need to invert the logic
        try:
            top_level_merge(
                strategy=strategy,
                delete_branch=not keep_branch,  # Invert: keep -> delete
                remove_worktree=not keep_worktree,  # Invert: keep -> remove
                push=push,
                target_branch=target,  # Note: parameter name differs
                dry_run=dry_run,
                feature=feature,
                resume=False,  # Agent commands don't support resume
                abort=False,  # Agent commands don't support abort
            )
        except typer.Exit:
            # Propagate typer.Exit cleanly
            raise
        except Exception as e:
            print(json.dumps({"error": str(e), "success": False}))
            raise typer.Exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e), "success": False}))
        raise typer.Exit(1)


@app.command(name="finalize-tasks")
def finalize_tasks(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent identifier (for telemetry)")] = None,
    model: Annotated[Optional[str], typer.Option("--model", help="Model used (for telemetry)")] = None,
    input_tokens: Annotated[Optional[int], typer.Option("--input-tokens", help="Input tokens consumed (for telemetry)")] = None,
    output_tokens: Annotated[Optional[int], typer.Option("--output-tokens", help="Output tokens generated (for telemetry)")] = None,
    cost_usd: Annotated[Optional[float], typer.Option("--cost-usd", help="Cost in USD (for telemetry)")] = None,
    duration_ms: Annotated[Optional[int], typer.Option("--duration-ms", help="Duration in milliseconds (for telemetry)")] = None,
) -> None:
    """Parse dependencies from tasks.md and update WP frontmatter, then commit to target branch.

    This command is designed to be called after LLM generates WP files via /spec-kitty.tasks.
    It post-processes the generated files to add dependency information and commits everything.

    Examples:
        spec-kitty agent feature finalize-tasks --json
        spec-kitty agent finalize-tasks --agent claude --model claude-sonnet-4.5 --input-tokens 10000 --output-tokens 5000
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root"
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory
        cwd = Path.cwd().resolve()
        feature_dir = _find_feature_directory(repo_root, cwd)
        target_branch = _resolve_planning_branch(repo_root, feature_dir)
        _ensure_branch_checked_out(repo_root, target_branch, json_output)

        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.exists():
            error_msg = f"Tasks directory not found: {tasks_dir}"
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Parse dependencies from tasks.md (if it exists)
        tasks_md = feature_dir / "tasks.md"
        wp_dependencies = {}
        if tasks_md.exists():
            # Read tasks.md and parse dependencies
            tasks_content = tasks_md.read_text(encoding="utf-8")
            wp_dependencies = _parse_dependencies_from_tasks_md(tasks_content)

        # Validate dependencies (detect cycles, invalid references)
        if wp_dependencies:
            # Check for circular dependencies
            cycles = detect_cycles(wp_dependencies)
            if cycles:
                error_msg = f"Circular dependencies detected: {cycles}"
                if json_output:
                    print(json.dumps({"error": error_msg, "cycles": cycles}))
                else:
                    console.print("[red]Error:[/red] Circular dependencies detected:")
                    for cycle in cycles:
                        console.print(f"  {' → '.join(cycle)}")
                raise typer.Exit(1)

            # Validate each WP's dependencies
            for wp_id, deps in wp_dependencies.items():
                is_valid, errors = validate_dependencies(wp_id, deps, wp_dependencies)
                if not is_valid:
                    error_msg = f"Invalid dependencies for {wp_id}: {errors}"
                    if json_output:
                        print(json.dumps({"error": error_msg, "wp_id": wp_id, "errors": errors}))
                    else:
                        console.print(f"[red]Error:[/red] Invalid dependencies for {wp_id}:")
                        for err in errors:
                            console.print(f"  - {err}")
                    raise typer.Exit(1)

        # Update each WP file's frontmatter with dependencies
        wp_files = list(tasks_dir.glob("WP*.md"))
        updated_count = 0
        work_packages: list[dict[str, object]] = []

        for wp_file in wp_files:
            # Extract WP ID from filename
            wp_id_match = re.match(r"(WP\d{2})", wp_file.name)
            if not wp_id_match:
                continue

            wp_id = wp_id_match.group(1)

            # Detect whether dependencies field exists in raw frontmatter
            raw_content = wp_file.read_text(encoding="utf-8")
            has_dependencies_line = False
            if raw_content.startswith("---"):
                parts = raw_content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1]
                    has_dependencies_line = re.search(
                        r"^\s*dependencies\s*:", frontmatter_text, re.MULTILINE
                    ) is not None

            # Read current frontmatter
            try:
                frontmatter, body = read_frontmatter(wp_file)
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not read {wp_file.name}: {e}")
                continue

            # Get dependencies for this WP (default to empty list)
            deps = wp_dependencies.get(wp_id, [])
            title = (frontmatter.get("title") or "").strip() or wp_id
            work_packages.append(
                {
                    "id": wp_id,
                    "title": title,
                    "dependencies": deps,
                }
            )

            # Update frontmatter with dependencies
            if not has_dependencies_line or frontmatter.get("dependencies") != deps:
                frontmatter["dependencies"] = deps

                # Write updated frontmatter
                write_frontmatter(wp_file, frontmatter, body)
                updated_count += 1

        # Prepare metadata for event emission
        feature_slug = feature_dir.name
        meta_path = feature_dir / "meta.json"
        if meta_path.exists():
            try:
                json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to read meta.json for event emission: {exc}"
                )
        else:
            console.print("[yellow]Warning:[/yellow] meta.json missing; skipping FeatureCreated emission")

        # Commit tasks.md and WP files to target branch
        commit_created = False
        commit_hash = None
        files_committed = []

        try:
            # Build list of all files to commit via safe_commit
            files_to_commit = []
            files_to_commit_rel = []

            # Include tasks.md (if present)
            if tasks_md.exists():
                files_to_commit.append(tasks_md)
                rel_path = str(tasks_md.relative_to(repo_root))
                files_to_commit_rel.append(rel_path)
                files_committed.append(rel_path)

            # Include all files in tasks_dir
            for f in tasks_dir.iterdir():
                if f.is_file():
                    files_to_commit.append(f)
                    rel_path = str(f.relative_to(repo_root))
                    files_to_commit_rel.append(rel_path)
                    files_committed.append(rel_path)

            # Detect changes only within finalize-tasks outputs.
            # This avoids treating unrelated dirty files as commit failures.
            has_relevant_changes = False
            if files_to_commit_rel:
                _rc, status_out, _status_err = run_command(
                    ["git", "status", "--porcelain", "--", *files_to_commit_rel],
                    check_return=True,
                    capture=True,
                    cwd=repo_root,
                )
                has_relevant_changes = bool(status_out.strip())

            if not has_relevant_changes:
                # Nothing to commit (already committed)
                commit_created = False
                commit_hash = None

                if not json_output:
                    console.print(f"[dim]Tasks unchanged, no commit needed[/dim]")
            else:
                # Commit with descriptive message (safe_commit preserves staging area)
                commit_msg = f"Add tasks for feature {feature_slug}"
                commit_success = safe_commit(
                    repo_path=repo_root,
                    files_to_commit=files_to_commit,
                    commit_message=commit_msg,
                    allow_empty=False,
                )

                if commit_success:
                    # Commit succeeded - get hash
                    _rc, stdout, _stderr = run_command(
                        ["git", "rev-parse", "HEAD"],
                        check_return=True,
                        capture=True,
                        cwd=repo_root
                    )
                    commit_hash = stdout.strip()
                    commit_created = True

                    if not json_output:
                        console.print(f"[green]✓[/green] Tasks committed to {target_branch}")
                        console.print(f"[dim]Commit: {commit_hash[:7]}[/dim]")
                        console.print(f"[dim]Updated {updated_count} WP files with dependencies[/dim]")
                else:
                    error_output = "Failed to commit tasks updates"
                    if json_output:
                        print(json.dumps({"error": f"Git commit failed: {error_output}"}))
                    else:
                        console.print("[dim]No changes to commit (tasks already up to date or git failure occured)[/dim]")
                    raise typer.Exit(1)

        except typer.Exit:
            raise
        except Exception as e:
            # Unexpected error
            if json_output:
                print(json.dumps({"error": str(e)}))
            else:
                console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        # Emit WPCreated events (non-blocking)
        # FeatureCreated is emitted earlier during create-feature
        causation_id = get_emitter().generate_causation_id()

        for wp in work_packages:
            try:
                emit_wp_created(
                    wp_id=str(wp["id"]),
                    title=str(wp["title"]),
                    dependencies=list(wp["dependencies"]),
                    feature_slug=feature_slug,
                    causation_id=causation_id,
                )
            except Exception as exc:
                console.print(
                    f"[yellow]Warning:[/yellow] WPCreated emission failed for {wp['id']}: {exc}"
                )

        if json_output:
            print(json.dumps({
                "result": "success",
                "updated_wp_count": updated_count,
                "tasks_dir": str(tasks_dir),
                "commit_created": commit_created,
                "commit_hash": commit_hash,
                "files_committed": files_committed
            }))

        # Emit ExecutionEvent for telemetry (always emit, nullable fields OK)
        if _should_emit_execution_event(
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        ):
            try:
                from specify_cli.telemetry.emit import emit_execution_event
                feature_slug = feature_dir.name
                emit_execution_event(
                    feature_dir=feature_dir,
                    feature_slug=feature_slug,
                    wp_id="N/A",  # No specific WP for task finalization
                    agent=agent or "unknown",
                    role="planner",
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    duration_ms=duration_ms or 0,
                    success=True,
                    error=None,
                )
            except typer.Exit:
                raise

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _parse_dependencies_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse WP dependencies from tasks.md content.

    Parsing strategy (priority order):
    1. Explicit dependency markers ("Depends on WP01", "Dependencies: WP01, WP02")
    2. Phase grouping (Phase 2 WPs depend on Phase 1 WPs)
    3. Default to empty list if ambiguous

    Returns:
        Dict mapping WP ID to list of dependencies
        Example: {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01", "WP02"]}
    """
    dependencies = {}

    # Split into WP sections
    wp_sections = re.split(r'##\s+Work Package (WP\d{2})', tasks_content)

    # Process sections (they come in pairs: WP ID, then content)
    for i in range(1, len(wp_sections), 2):
        if i + 1 >= len(wp_sections):
            break

        wp_id = wp_sections[i]
        section_content = wp_sections[i + 1]

        # Method 1: Explicit "Depends on" or "Dependencies:"
        explicit_deps = []

        # Pattern: "Depends on WP01" or "Depends on WP01, WP02"
        depends_matches = re.findall(r'Depends?\s+on\s+(WP\d{2}(?:\s*,\s*WP\d{2})*)', section_content, re.IGNORECASE)
        for match in depends_matches:
            explicit_deps.extend(re.findall(r'WP\d{2}', match))

        # Pattern: "Dependencies: WP01, WP02"
        deps_line = re.search(r'Dependencies:\s*(.+)', section_content)
        if deps_line:
            explicit_deps.extend(re.findall(r'WP\d{2}', deps_line.group(1)))

        if explicit_deps:
            # Remove duplicates and sort
            dependencies[wp_id] = sorted(list(set(explicit_deps)))
        else:
            # Default to empty
            dependencies[wp_id] = []

    return dependencies
