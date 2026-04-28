"""Mission lifecycle commands for AI agents."""

from __future__ import annotations

import contextlib
import json
import os
from kernel._safe_re import re
import shutil
from datetime import datetime, UTC
from importlib.resources import files
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from typing import Annotated

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.cli.selector_resolution import resolve_mission_handle, resolve_selector
from specify_cli.cli.commands.accept import accept as top_level_accept
from specify_cli.cli.commands.merge import merge as top_level_merge
from specify_cli.core.dependency_graph import (
    detect_cycles,
    validate_dependencies,
)
from specify_cli.core.git_ops import get_current_branch, is_git_repo, run_command
from specify_cli.core.git_preflight import (
    build_git_preflight_failure_payload,
    run_git_preflight,
)
from specify_cli.core.paths import get_main_repo_root, locate_project_root
from specify_cli.core.paths import (
    get_feature_target_branch,
)
from specify_cli.git import safe_commit
from specify_cli.core.worktree import (
    validate_feature_structure,
)
from specify_cli.frontmatter import write_frontmatter
from specify_cli.status.wp_metadata import WPMetadata, read_wp_frontmatter
from specify_cli.mission import get_mission_type
from specify_cli.ownership import infer_ownership, validate_ownership
from specify_cli.ownership.audit_targets import validate_audit_coverage
from specify_cli.ownership.validation import validate_glob_matches
from specify_cli.core.wps_manifest import (
    load_wps_manifest,
    dependencies_are_explicit,
    generate_tasks_md_from_manifest,
)
from specify_cli.diagnostics import mark_invocation_succeeded
from specify_cli.status.bootstrap import bootstrap_canonical_state
from specify_cli.sync.events import emit_wp_created, get_emitter
from specify_cli.workspace_context import resolve_feature_worktree
from specify_cli.merge.config import MergeStrategy

app = typer.Typer(name="mission", help="Mission lifecycle commands for AI agents", no_args_is_help=True)

console = Console()


def _extract_wp_ids_from_task_files(wp_files: list[Path]) -> list[str]:
    """Return canonical WP IDs discovered from task filenames."""
    wp_ids: set[str] = set()
    for wp_file in wp_files:
        wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
        if wp_id_match:
            wp_ids.add(wp_id_match.group(1))
    return sorted(wp_ids)


def _collect_finalize_artifacts(
    feature_dir: Path,
    tasks_dir: Path,
    mission_slug: str,
    lanes_path: Path | None = None,
) -> list[Path]:
    """Return all deterministic artifacts finalize-tasks may need to commit."""
    candidates: list[Path] = [
        feature_dir / "status.events.jsonl",
        feature_dir / "status.json",
        feature_dir / "tasks.md",
        feature_dir / ".kittify" / "dossiers" / mission_slug / "snapshot-latest.json",
    ]
    candidates.extend(sorted(path for path in tasks_dir.iterdir() if path.is_file()))
    if lanes_path is not None:
        candidates.append(lanes_path)

    seen: set[Path] = set()
    artifacts: list[Path] = []
    for candidate in candidates:
        if candidate.exists() and candidate not in seen:
            artifacts.append(candidate)
            seen.add(candidate)
    return artifacts


def _with_cli_version(payload: dict[str, object]) -> dict[str, object]:
    """Attach CLI version metadata to JSON payloads for log observability."""
    if "spec_kitty_version" in payload:
        return payload
    enriched = dict(payload)
    enriched["spec_kitty_version"] = SPEC_KITTY_VERSION
    return enriched


def _with_mission_aliases(payload: dict[str, object]) -> dict[str, object]:
    """Return canonical mission nouns only on live JSON surfaces."""
    return dict(payload)


def _emit_json(payload: dict[str, object]) -> None:
    """Emit a deterministic single JSON object."""
    print(json.dumps(_with_cli_version(_with_mission_aliases(payload))))


def _utc_now_iso() -> str:
    """Return deterministic UTC timestamp string for prompt/runtime variables."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_feature_meta(feature_dir: Path) -> dict[str, object]:
    """Read feature metadata when present."""
    meta_file = feature_dir / "meta.json"
    if not meta_file.exists():
        return {}
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_feature_target_branch(feature_dir: Path, repo_root: Path) -> str:
    """Resolve canonical target/base branch from metadata with branch fallback."""
    meta = _read_feature_meta(feature_dir)
    target = str(meta.get("target_branch", "")).strip()
    if target:
        return target
    return get_current_branch(repo_root) or "main"


def _inject_branch_contract(
    payload: dict[str, object],
    *,
    target_branch: str,
    current_branch: str | None = None,
) -> dict[str, object]:
    """Attach deterministic branch/runtime aliases for templates and agents."""
    enriched = dict(payload)
    raw_runtime_vars = enriched.get("runtime_vars", {})
    runtime_vars = dict(raw_runtime_vars) if isinstance(raw_runtime_vars, dict) else {}
    now_utc_iso = str(runtime_vars.get("now_utc_iso", _utc_now_iso()))
    resolved_current_branch = str(current_branch or target_branch).strip() or target_branch
    planning_base_branch = target_branch
    merge_target_branch = target_branch
    branch_matches_target = resolved_current_branch == target_branch
    branch_strategy_summary = (
        f"Current branch at workflow start: {resolved_current_branch}. "
        f"Planning/base branch for this feature: {planning_base_branch}. "
        f"Completed changes must merge into {merge_target_branch}."
    )
    runtime_vars["now_utc_iso"] = now_utc_iso
    runtime_vars["current_branch"] = resolved_current_branch
    runtime_vars["target_branch"] = target_branch
    runtime_vars["base_branch"] = target_branch
    runtime_vars["planning_base_branch"] = planning_base_branch
    runtime_vars["merge_target_branch"] = merge_target_branch
    runtime_vars["branch_matches_target"] = branch_matches_target
    runtime_vars["branch_strategy_summary"] = branch_strategy_summary

    branch_context = {
        "current_branch": resolved_current_branch,
        "target_branch": target_branch,
        "base_branch": target_branch,
        "planning_base_branch": planning_base_branch,
        "merge_target_branch": merge_target_branch,
        "expected_checkout_branch": target_branch,
        "matches_target": branch_matches_target,
        "branch_strategy_summary": branch_strategy_summary,
    }

    enriched["current_branch"] = resolved_current_branch
    enriched["CURRENT_BRANCH"] = resolved_current_branch
    enriched["target_branch"] = target_branch
    enriched["base_branch"] = target_branch
    enriched["TARGET_BRANCH"] = target_branch
    enriched["BASE_BRANCH"] = target_branch
    enriched["planning_base_branch"] = planning_base_branch
    enriched["PLANNING_BASE_BRANCH"] = planning_base_branch
    enriched["merge_target_branch"] = merge_target_branch
    enriched["MERGE_TARGET_BRANCH"] = merge_target_branch
    enriched["EXPECTED_TARGET_BRANCH"] = target_branch
    enriched["EXPECTED_BASE_BRANCH"] = target_branch
    enriched["branch_matches_target"] = branch_matches_target
    enriched["BRANCH_MATCHES_TARGET"] = branch_matches_target
    enriched["branch_strategy_summary"] = branch_strategy_summary
    enriched["runtime_vars"] = runtime_vars
    enriched["NOW_UTC_ISO"] = now_utc_iso
    enriched["branch_context"] = branch_context
    return enriched


def _enforce_git_preflight(
    repo_root: Path,
    *,
    json_output: bool,
    command_name: str,
) -> None:
    """Run git preflight and exit with deterministic remediation payload on failure."""
    if not (repo_root / ".git").exists():
        return

    preflight = run_git_preflight(repo_root, check_worktree_list=True)
    if preflight.passed:
        return

    payload = build_git_preflight_failure_payload(preflight, command_name=command_name)
    if json_output:
        _emit_json(payload)
    else:
        console.print(f"[red]Error:[/red] {payload['error']}")
        for cmd in payload.get("remediation", []):
            console.print(f"  - Run: {cmd}")
    raise typer.Exit(1)


def _show_branch_context(
    repo_root: Path,
    mission_slug: str,
    json_output: bool = False,
) -> tuple[Path, str]:
    """Show branch context banner. Returns (main_repo_root, current_branch).

    Uses the canonical resolve_target_branch() from core.git_ops.
    Shows a consistent, visible banner at the start of every command.
    """
    from specify_cli.core.git_ops import resolve_target_branch
    from specify_cli.core.paths import get_main_repo_root

    main_repo_root = get_main_repo_root(repo_root)
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        raise RuntimeError("Detached HEAD — checkout a branch before continuing")

    resolution = resolve_target_branch(mission_slug, main_repo_root, current_branch, respect_current=True)

    if not json_output:
        if not resolution.should_notify:
            console.print(f"[bold cyan]Branch:[/bold cyan] {current_branch} (target for this mission)")
        else:
            console.print(f"[bold yellow]Branch:[/bold yellow] on '{resolution.current}', mission targets '{resolution.target}'")

    return main_repo_root, resolution.current


def _resolve_planning_branch(repo_root: Path, feature_dir: Path) -> str:
    """Resolve planning branch for a mission directory.

    Compatibility shim for tests and callers that patch this helper directly.
    """
    try:
        _, target_branch = _show_branch_context(repo_root, feature_dir.name, json_output=True)
        return target_branch
    except RuntimeError:
        # In detached/non-git contexts (unit tests, fixtures), fall back to main.
        return "main"


def _ensure_branch_checked_out(
    repo_root: Path,
    target_branch: str,
    *,
    json_output: bool = False,
) -> None:
    """Ensure target branch is checked out in the main planning repo.

    Compatibility shim used by finalize-tasks call path and tests.
    """
    from specify_cli.core.paths import get_main_repo_root

    main_repo_root = get_main_repo_root(repo_root)
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        # Detached/non-git contexts are handled downstream during commit operations.
        return

    if current_branch == target_branch:
        return

    rc, _stdout, stderr = run_command(
        ["git", "checkout", target_branch],
        check_return=False,
        capture=True,
        cwd=main_repo_root,
    )
    if rc != 0:
        raise RuntimeError(f"Failed to checkout target branch '{target_branch}': {stderr.strip() or 'unknown error'}")

    if not json_output:
        console.print(f"[green]✓[/green] Switched to branch [bold]{target_branch}[/bold]")


def _commit_to_branch(
    file_path: Path,
    mission_slug: str,
    artifact_type: str,
    repo_root: Path,
    _target_branch: str,
    json_output: bool = False,
) -> None:
    """Commit planning artifact to current branch (respects user context).

    Args:
        file_path: Path to file being committed
        mission_slug: Feature slug (e.g., "001-my-feature")
        artifact_type: Type of artifact ("spec", "plan", "tasks")
        repo_root: Repository root path (ensures commits go to planning repo, not worktree)
        target_branch: Branch the mission targets (for informational messages only)
        json_output: If True, suppress Rich console output

    Raises:
        subprocess.CalledProcessError: If commit fails unexpectedly
    """
    try:
        current_branch = get_current_branch(repo_root)
        if current_branch is None:
            raise RuntimeError("Not in a git repository")

        # Commit only this file (preserves staging area)
        commit_msg = f"Add {artifact_type} for feature {mission_slug}"
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
        stderr = e.stderr if hasattr(e, "stderr") and e.stderr else ""
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


def _find_feature_directory(
    repo_root: Path,
    _cwd: Path,
    explicit_feature: str | None = None,
) -> Path:
    """Find the mission directory from an explicit mission slug.

    Uses the canonical mission resolver which handles ambiguous numeric-prefix
    handles, mid8 prefixes, and full ULID forms.

    Args:
        repo_root: Repository root path
        _cwd: Current working directory (unused — kept for signature compatibility)
        explicit_feature: Mission handle provided explicitly (required)

    Returns:
        Path to mission directory

    Raises:
        ValueError: If no handle is provided.
    """
    if not explicit_feature:
        raise ValueError("--mission <slug> is required")
    try:
        resolved = resolve_mission_handle(explicit_feature, repo_root)
        return resolved.feature_dir
    except (SystemExit, typer.Exit):
        candidate = repo_root / "kitty-specs" / explicit_feature
        if candidate.exists():
            return candidate
        raise ValueError(f"Mission directory not found: {explicit_feature}") from None


def _list_feature_spec_candidates(repo_root: Path) -> list[dict[str, object]]:
    """List candidate missions with absolute spec.md paths for remediation output."""
    main_repo_root = get_main_repo_root(repo_root)
    kitty_specs_dir = main_repo_root / "kitty-specs"
    if not kitty_specs_dir.is_dir():
        return []

    candidates: list[dict[str, object]] = []
    for feature_dir in sorted(kitty_specs_dir.iterdir()):
        if not feature_dir.is_dir():
            continue
        spec_file = feature_dir / "spec.md"
        meta_file = feature_dir / "meta.json"
        if not spec_file.exists() and not meta_file.exists():
            continue
        candidates.append(
            {
                "mission_slug": feature_dir.name,
                "feature_dir": str(feature_dir.resolve()),
                "spec_file": str(spec_file.resolve()),
                "spec_exists": spec_file.exists(),
            }
        )
    return candidates


def _build_setup_plan_detection_error(
    repo_root: Path,
    _base_error: str,
    mission_flag: str | None,
    *,
    error_code: str = "PLAN_CONTEXT_UNRESOLVED",
    command_name: str = "setup-plan",
    command_args: list[str] | None = None,
) -> dict[str, object]:
    """Build a concise mission-context detection error payload.

    This payload is consumed by LLMs via ``--json`` output.  Keep it small:
    slugs only (no absolute paths), one example command, and a short
    remediation string so the agent can act without parsing kilobytes of
    redundant path data.
    """
    candidates = _list_feature_spec_candidates(repo_root)
    command_args = command_args if command_args is not None else ["--json"]

    payload: dict[str, object] = {
        "error_code": error_code,
        "mission_flag": mission_flag,
        "spec_kitty_version": SPEC_KITTY_VERSION,
    }

    if not candidates:
        payload["error"] = "No missions found in kitty-specs/"
        payload["remediation"] = "Run /spec-kitty.specify or: spec-kitty agent mission create <name> --json"
        return payload

    slugs = [str(c["mission_slug"]) for c in candidates]
    n = len(slugs)
    payload["error"] = f"{n} missions found, pass --mission <slug> to disambiguate"
    payload["available_missions"] = slugs

    # One example command so the LLM knows the exact syntax
    args_suffix = f" {' '.join(command_args)}" if command_args else ""
    payload["example_command"] = f"spec-kitty agent mission {command_name} --mission {slugs[0]}{args_suffix}"
    payload["remediation"] = "Re-run with --mission <slug>"
    return payload


@app.command(name="branch-context")
def branch_context(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    target_branch: Annotated[
        str | None,
        typer.Option(
            "--target-branch",
            help="Planned landing branch (defaults to current branch)",
        ),
    ] = None,
) -> None:
    """Return deterministic branch contract for planning-stage prompts."""
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        if not is_git_repo(repo_root):
            error_msg = "Not in a git repository. Branch context requires git."
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        current_branch = get_current_branch(repo_root)
        if not current_branch or current_branch == "HEAD":
            error_msg = "Must be on a branch to resolve branch context (detached HEAD detected)."
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        resolved_target_branch = str(target_branch).strip() if target_branch and str(target_branch).strip() else current_branch
        payload = {
            "result": "success",
            "repo_root": str(repo_root.resolve()),
            "target_branch_source": "cli_arg" if target_branch else "current_branch",
            "next_step": ("Use this deterministic branch contract during specify/plan prompts; do not rediscover branch state inside the LLM."),
        }
        enriched = _inject_branch_contract(
            payload,
            target_branch=resolved_target_branch,
            current_branch=current_branch,
        )

        if json_output:
            _emit_json(enriched)
        else:
            console.print(f"[bold cyan]Current branch:[/bold cyan] {enriched['current_branch']}")
            console.print(f"[bold cyan]Planning/base branch:[/bold cyan] {enriched['planning_base_branch']}")
            console.print(f"[bold cyan]Merge target:[/bold cyan] {enriched['merge_target_branch']}")
            console.print(f"[bold cyan]Matches target:[/bold cyan] {enriched['branch_matches_target']}")

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command(name="create")
def create_mission(
    mission_slug: Annotated[str, typer.Argument(help="Mission slug (e.g., 'user-auth')")],
    mission_type: Annotated[
        str | None,
        typer.Option("--mission-type", help="Mission type (e.g., 'documentation', 'software-dev')"),
    ] = None,
    mission: Annotated[
        str | None,
        typer.Option("--mission", hidden=True, help="(deprecated) Use --mission-type"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    target_branch: Annotated[str | None, typer.Option("--target-branch", help="Target branch (defaults to current branch)")] = None,
    friendly_name: Annotated[str | None, typer.Option("--friendly-name", help="Human-friendly mission title")] = None,
    purpose_tldr: Annotated[str | None, typer.Option("--purpose-tldr", help="One-line stakeholder TLDR for the mission")] = None,
    purpose_context: Annotated[str | None, typer.Option("--purpose-context", help="Short stakeholder-facing paragraph for the mission")] = None,
    pr_bound: Annotated[bool, typer.Option("--pr-bound/--no-pr-bound", help="Mark mission as PR-bound (gate fires on merge_target_branch)")] = False,
    branch_strategy: Annotated[
        str | None,
        typer.Option(
            "--branch-strategy",
            help="Branch-strategy gate control (e.g., 'already-confirmed' to bypass the prompt)",
        ),
    ] = None,
) -> None:
    """Create new mission directory structure in the project root checkout.

    This command is designed for AI agents to call programmatically.
    Creates mission directory in kitty-specs/ and commits to the current branch.

    Examples:
        spec-kitty agent mission create "new-dashboard" --json
    """
    from specify_cli.core.mission_creation import (
        MissionCreationError,
        create_mission_core,
    )

    repo_root = locate_project_root()
    resolved_mission_type = mission_type

    if mission_type is not None or mission is not None:
        try:
            resolved = resolve_selector(
                canonical_value=mission_type,
                canonical_flag="--mission-type",
                alias_value=mission,
                alias_flag="--mission",
                suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
                command_hint="--mission-type <name>",
            )
            resolved_mission_type = resolved.canonical_value
        except typer.BadParameter as exc:
            if json_output:
                _emit_json({"error": str(exc)})
            else:
                console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(1) from exc

    # Branch-strategy gate (FR-033, WP07/T040): when the mission is PR-bound
    # and the operator is on the merge target branch, prompt for confirmation
    # unless `--branch-strategy already-confirmed` is supplied.
    from specify_cli.cli.commands._branch_strategy_gate import (
        BranchStrategyGateError,
        evaluate_branch_strategy,
    )

    current_branch = get_current_branch(repo_root)
    effective_merge_target = target_branch or current_branch
    try:
        gate_outcome = evaluate_branch_strategy(
            pr_bound=pr_bound,
            current_branch=current_branch,
            merge_target_branch=effective_merge_target,
            branch_strategy=branch_strategy,
            prompt=lambda message: typer.confirm(message, default=False),
        )
    except BranchStrategyGateError as exc:
        if json_output:
            _emit_json({"error": str(exc)})
        else:
            console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if gate_outcome.prompted and not gate_outcome.decision.proceed:
        message = (
            "Mission creation aborted by operator at branch-strategy gate. "
            "Switch to a feature branch or pass `--branch-strategy already-confirmed`."
        )
        if json_output:
            _emit_json({"error": message, "branch_strategy_gate": "aborted"})
        else:
            console.print(f"[yellow]Aborted:[/yellow] {message}")
        raise typer.Exit(1)

    try:
        result = create_mission_core(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mission=resolved_mission_type,
            target_branch=target_branch,
            friendly_name=friendly_name,
            purpose_tldr=purpose_tldr,
            purpose_context=purpose_context,
        )
    except MissionCreationError as exc:
        error_msg = str(exc)
        if json_output:
            _emit_json({"error": error_msg})
        else:
            console.print(f"[bold red]Error:[/bold red] {error_msg}")
            # Provide worktree navigation hint when applicable
            if "worktree" in error_msg.lower():
                cwd = Path.cwd().resolve()
                main_repo = locate_project_root(cwd)
                if main_repo is None:
                    # Fallback: try .worktrees path heuristic
                    for i, part in enumerate(cwd.parts):
                        if part == ".worktrees":
                            main_repo = Path(*cwd.parts[:i])
                            break
                if main_repo is not None:
                    console.print("\n[cyan]Run from the main repository instead:[/cyan]")
                    console.print(f"  cd {main_repo}")
                    console.print(f"  spec-kitty agent mission create {mission_slug}")
        raise typer.Exit(1) from exc
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e

    # Persist pr_bound flag in meta.json (FR-033 schema addition).
    if pr_bound:
        try:
            meta_file = result.feature_dir / "meta.json"
            if meta_file.exists():
                meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                if not meta_data.get("pr_bound"):
                    meta_data["pr_bound"] = True
                    from specify_cli.mission_metadata import write_meta

                    write_meta(result.feature_dir, meta_data)
        except (OSError, json.JSONDecodeError):
            pass

    # -- Output formatting (stays in the CLI layer) --
    if not json_output:
        console.print(f"[bold cyan]Branch:[/bold cyan] {result.target_branch} (target for this mission)")
        if resolved_mission_type == "documentation":
            console.print("[cyan]\u2192 Documentation state initialized in meta.json[/cyan]")

    if json_output:
        feature_dir = result.feature_dir
        spec_file = feature_dir / "spec.md"
        meta_file = feature_dir / "meta.json"
        tasks_readme = feature_dir / "tasks" / "README.md"
        create_payload: dict[str, object] = {
            "result": "success",
            "mission_slug": result.mission_slug,
            "mission_number": result.mission_number,
            "mission_id": str(result.meta.get("mission_id", "")),
            "mission_type": str(result.meta.get("mission_type", result.meta.get("mission", ""))),
            "slug": str(result.meta.get("slug", "")),
            "friendly_name": str(result.meta.get("friendly_name", "")),
            "purpose_tldr": str(result.meta.get("purpose_tldr", "")),
            "purpose_context": str(result.meta.get("purpose_context", "")),
            "feature_dir": str(feature_dir),
            "spec_file": str(spec_file),
            "meta_file": str(meta_file),
            "created_at": str(result.meta.get("created_at", "")),
            "created_files": [str(spec_file), str(meta_file), str(tasks_readme)],
            "write_mode": "update_existing_files",
            "next_step": "Read then update spec_file/meta_file; do not recreate with blind write.",
            "origin_binding": {
                "attempted": result.origin_binding_attempted,
                "succeeded": result.origin_binding_succeeded,
                "error": result.origin_binding_error,
            },
        }
        _emit_json(
            _inject_branch_contract(
                create_payload,
                target_branch=result.target_branch,
                current_branch=result.current_branch,
            )
        )
        # FR-008: signal atexit handlers that this invocation succeeded so
        # post-success shutdown warnings (sync/runtime stop) are silenced.
        # Scoped intentionally to the JSON success path of `agent mission
        # create`; auditing other JSON-emitting commands is OUT OF SCOPE
        # for WP06 (see contracts/mission_create_clean_output.contract.md).
        mark_invocation_succeeded()
    else:
        console.print(f"[green]\u2713[/green] Mission created: {result.mission_slug}")
        console.print(f"   Title: {result.meta.get('friendly_name', '')}")
        console.print(f"   TLDR: {result.meta.get('purpose_tldr', '')}")
        console.print(f"   Context: {result.meta.get('purpose_context', '')}")
        console.print(f"   Directory: {result.feature_dir}")
        # Issue #846: spec.md is no longer auto-committed at create time.
        # The agent commits it from /spec-kitty.specify after writing substantive content.
        console.print(f"   Meta committed to {result.target_branch}; spec.md scaffold left untracked")


@app.command(name="check-prerequisites")
def check_prerequisites(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    paths_only: Annotated[bool, typer.Option("--paths-only", help="Only output path variables")] = False,
    include_tasks: Annotated[bool, typer.Option("--include-tasks", help="Include tasks.md in validation")] = False,
    require_tasks: Annotated[
        bool,
        typer.Option("--require-tasks", hidden=True, help="Deprecated alias for --include-tasks"),
    ] = False,
) -> None:
    """Validate mission structure and prerequisites.

    This command is designed for AI agents to call programmatically.

    Examples:
        spec-kitty agent mission check-prerequisites --json
        spec-kitty agent mission check-prerequisites --mission 020-my-feature --paths-only --json
    """
    try:
        if require_tasks and not include_tasks:
            include_tasks = True
            if not json_output:
                console.print("[yellow]Warning:[/yellow] --require-tasks is deprecated; use --include-tasks.")

        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1) from None

        _enforce_git_preflight(
            repo_root,
            json_output=json_output,
            command_name="spec-kitty agent mission check-prerequisites",
        )

        # Determine feature directory (main repo or worktree)
        cwd = Path.cwd().resolve()
        try:
            feature_dir = _find_feature_directory(
                repo_root,
                cwd,
                explicit_feature=feature,
            )
        except ValueError as detection_error:
            command_args: list[str] = []
            if json_output:
                command_args.append("--json")
            if paths_only:
                command_args.append("--paths-only")
            if include_tasks:
                command_args.append("--include-tasks")

            payload = _build_setup_plan_detection_error(
                repo_root,
                str(detection_error),
                feature,
                error_code="FEATURE_CONTEXT_UNRESOLVED",
                command_name="check-prerequisites",
                command_args=command_args,
            )
            if json_output:
                _emit_json(payload)
            else:
                console.print(f"[red]Error:[/red] {payload['error']}")
                for slug in payload.get("available_missions", [])[:10]:
                    console.print(f"  - {slug}")
                if "example_command" in payload:
                    console.print(f"  {payload['example_command']}")
            raise typer.Exit(1) from None

        validation_result = validate_feature_structure(feature_dir, check_tasks=include_tasks)
        target_branch = _resolve_feature_target_branch(feature_dir, repo_root)
        current_branch = get_current_branch(repo_root) or target_branch

        if json_output:
            if paths_only:
                paths_payload = dict(validation_result["paths"])
                paths_payload["artifact_files"] = validation_result.get("artifact_files", {})
                paths_payload["artifact_dirs"] = validation_result.get("artifact_dirs", {})
                paths_payload["available_docs"] = validation_result.get("available_docs", [])
                paths_payload["FEATURE_DIR"] = paths_payload.get("feature_dir", "")
                paths_payload["SPEC_FILE"] = paths_payload.get("spec_file", "")
                paths_payload["PLAN_FILE"] = paths_payload.get("plan_file", "")
                paths_payload["TASKS_FILE"] = paths_payload.get("tasks_file", "")
                paths_payload["FEATURE_SPEC"] = paths_payload.get("spec_file", "")
                paths_payload["IMPL_PLAN"] = paths_payload.get("plan_file", "")
                paths_payload["TASKS"] = paths_payload.get("tasks_file", "")
                feature_dir_value = str(paths_payload.get("feature_dir", ""))
                paths_payload["SPECS_DIR"] = str(Path(feature_dir_value).parent) if feature_dir_value else ""
                _emit_json(
                    _inject_branch_contract(
                        paths_payload,
                        target_branch=target_branch,
                        current_branch=current_branch,
                    )
                )
            else:
                result_payload = dict(validation_result)
                _emit_json(
                    _inject_branch_contract(
                        result_payload,
                        target_branch=target_branch,
                        current_branch=current_branch,
                    )
                )
        else:
            if validation_result["valid"]:
                console.print("[green]✓[/green] Prerequisites check passed")
                console.print(f"   Mission: {feature_dir.name}")
            else:
                console.print("[red]✗[/red] Prerequisites check failed")
                for error in validation_result["errors"]:
                    console.print(f"   • {error}")

            if validation_result["warnings"]:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in validation_result["warnings"]:
                    console.print(f"   • {warning}")

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command(name="setup-plan")
def setup_plan(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Scaffold implementation plan template in the project root checkout.

    This command is designed for AI agents to call programmatically.
    Creates plan.md and commits to target branch.

    Examples:
        spec-kitty agent mission setup-plan --json
        spec-kitty agent mission setup-plan --mission 020-my-feature --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root. Run from within spec-kitty repository."
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        _enforce_git_preflight(
            repo_root,
            json_output=json_output,
            command_name="spec-kitty agent mission setup-plan",
        )

        # Determine feature directory using centralized detection.
        # For planning bootstrap, disallow latest-incomplete fallback so the agent
        # cannot silently bind to the wrong feature in fresh sessions.
        cwd = Path.cwd().resolve()
        try:
            feature_dir = _find_feature_directory(
                repo_root,
                cwd,
                explicit_feature=feature,
            )
        except ValueError as detection_error:
            payload = _build_setup_plan_detection_error(repo_root, str(detection_error), feature)
            if json_output:
                _emit_json(payload)
            else:
                console.print(f"[red]Error:[/red] {payload['error']}")
                for slug in payload.get("available_missions", [])[:10]:
                    console.print(f"  - {slug}")
                if "example_command" in payload:
                    console.print(f"  {payload['example_command']}")
            raise typer.Exit(1) from None

        mission_slug = feature_dir.name
        _, target_branch = _show_branch_context(repo_root, mission_slug, json_output)
        current_branch = get_current_branch(repo_root) or target_branch

        spec_file = feature_dir / "spec.md"
        plan_file = feature_dir / "plan.md"

        if not spec_file.exists():
            payload = {
                "error_code": "SPEC_FILE_MISSING",
                "error": f"Required spec not found for mission '{mission_slug}': {spec_file.resolve()}",
                "mission_slug": mission_slug,
                "feature_dir": str(feature_dir.resolve()),
                "spec_file": str(spec_file.resolve()),
                "remediation": [
                    f"Restore the missing spec file at {spec_file.resolve()}",
                    "Or select another mission explicitly: spec-kitty agent mission setup-plan --mission <mission-slug> --json",
                ],
            }
            if json_output:
                _emit_json(payload)
            else:
                console.print(f"[red]Error:[/red] {payload['error']}")
                for step in payload["remediation"]:
                    console.print(f"  - {step}")
            raise typer.Exit(1)

        # Issue #846 entry gate: spec.md must be committed AND substantive
        # before plan.md can be scaffolded or committed. Section-presence only;
        # scaffold + arbitrary prose without an FR row is NOT substantive.
        from specify_cli.missions._substantive import is_committed, is_substantive

        spec_is_committed = is_committed(spec_file, repo_root)
        spec_is_substantive = is_substantive(spec_file, "spec")
        if not spec_is_committed or not spec_is_substantive:
            blocked_reason = (
                "spec.md must be committed AND substantive before setup-plan can run. "
                "Populate the Functional Requirements (at least one FR-### row with "
                "real description content), commit spec.md, then re-run setup-plan."
            )
            payload = {
                "result": "blocked",
                "phase_complete": False,
                "blocked_reason": blocked_reason,
                "error_code": "SPEC_NOT_SUBSTANTIVE_OR_UNCOMMITTED",
                "mission_slug": mission_slug,
                "feature_dir": str(feature_dir.resolve()),
                "spec_file": str(spec_file.resolve()),
                "spec_committed": spec_is_committed,
                "spec_substantive": spec_is_substantive,
            }
            if json_output:
                _emit_json(
                    _inject_branch_contract(
                        payload,
                        target_branch=target_branch,
                        current_branch=current_branch,
                    )
                )
            else:
                console.print(f"[yellow]Blocked:[/yellow] {blocked_reason}")
            return

        # Find plan template
        plan_template_candidates = [
            repo_root / ".kittify" / "templates" / "plan-template.md",
            repo_root / "src" / "specify_cli" / "templates" / "plan-template.md",
            repo_root / "templates" / "plan-template.md",
        ]

        plan_template = None
        for candidate in plan_template_candidates:
            if candidate.exists():
                plan_template = candidate
                break

        # C-007: never overwrite an existing plan.md. The agent may have
        # populated it between setup-plan invocations and we must not silently
        # delete or rewrite their content.
        if not plan_file.exists():
            if plan_template is not None:
                shutil.copy2(plan_template, plan_file)
            else:
                package_template = files("specify_cli").joinpath("templates", "plan-template.md")
                if not package_template.exists():
                    raise FileNotFoundError("Plan template not found in repository or package")
                with package_template.open("rb") as src, open(plan_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        # Issue #846 exit gate: only commit plan.md when its Technical Context
        # has been populated with real (non-placeholder) values. A bare
        # template stays untracked so the dashboard / workflow JSON does not
        # falsely advertise the plan phase as complete.
        plan_is_substantive = is_substantive(plan_file, "plan")
        plan_blocked_reason: str | None = None
        if plan_is_substantive:
            _commit_to_branch(plan_file, mission_slug, "plan", repo_root, target_branch, json_output)
        else:
            plan_blocked_reason = (
                "plan.md content is not substantive yet; populate Technical Context with real "
                "values (e.g., Language/Version) — not template placeholders — and re-run "
                "setup-plan to commit."
            )
            if not json_output:
                console.print(f"[yellow]Plan not committed:[/yellow] {plan_blocked_reason}")

        # T014 + T016: Documentation mission wiring for plan
        mission_type = get_mission_type(feature_dir)
        gap_analysis_path = None
        generators_detected = []

        if mission_type == "documentation":
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
                            analysis = generate_gap_analysis_report(docs_dir, gap_analysis_output, project_root=repo_root)
                            gap_analysis_path = str(gap_analysis_output)
                            # Update documentation state with audit metadata
                            set_audit_metadata(
                                meta_file,
                                last_audit_date=analysis.analysis_date,
                                coverage_percentage=analysis.coverage_matrix.get_coverage_percentage(),
                            )
                            # Commit gap analysis and updated meta.json
                            with contextlib.suppress(Exception):  # Non-fatal: agent can commit separately
                                safe_commit(
                                    repo_path=repo_root,
                                    files_to_commit=[gap_analysis_output, meta_file],
                                    commit_message=f"Add gap analysis for feature {mission_slug}",
                                    allow_empty=False,
                                )
                            if not json_output:
                                coverage_pct = analysis.coverage_matrix.get_coverage_percentage() * 100
                                console.print(f"[cyan]→ Gap analysis generated: {gap_analysis_output.name} (coverage: {coverage_pct:.1f}%)[/cyan]")
                        except Exception as gap_err:
                            if not json_output:
                                console.print(f"[yellow]Warning:[/yellow] Gap analysis failed: {gap_err}")
                    else:
                        if not json_output:
                            console.print("[yellow]Warning:[/yellow] No docs/ directory found, skipping gap analysis")

            # T016: Detect and configure generators
            all_generators = [JSDocGenerator(), SphinxGenerator(), RustdocGenerator()]
            for gen in all_generators:
                with contextlib.suppress(Exception):  # Skip generators that fail detection
                    if gen.detect(repo_root):
                        generators_detected.append(
                            {
                                "name": gen.name,
                                "language": gen.languages[0],
                                "config_path": "",
                            }
                        )
                        if not json_output:
                            console.print(f"[cyan]→ Detected {gen.name} generator (languages: {', '.join(gen.languages)})[/cyan]")

            if generators_detected and meta_file.exists():
                try:
                    set_generators_configured(meta_file, generators_detected)
                    with contextlib.suppress(Exception):  # Non-fatal
                        safe_commit(
                            repo_path=repo_root,
                            files_to_commit=[meta_file],
                            commit_message=f"Update generator config for feature {mission_slug}",
                            allow_empty=False,
                        )
                except Exception as gen_err:
                    if not json_output:
                        console.print(f"[yellow]Warning:[/yellow] Failed to save generator config: {gen_err}")
        # Dossier sync (fire-and-forget)
        with contextlib.suppress(Exception):
            from specify_cli.sync.dossier_pipeline import (
                trigger_feature_dossier_sync_if_enabled,
            )

            trigger_feature_dossier_sync_if_enabled(
                feature_dir,
                mission_slug,
                repo_root,
            )

        if json_output:
            result: dict[str, object] = {
                "result": "success" if plan_is_substantive else "blocked",
                "phase_complete": plan_is_substantive,
                "mission_slug": mission_slug,
                "plan_file": str(plan_file),
                "feature_dir": str(feature_dir),
                "spec_file": str(spec_file),
                "plan_substantive": plan_is_substantive,
            }
            if plan_blocked_reason is not None:
                result["blocked_reason"] = plan_blocked_reason
            if gap_analysis_path:
                result["gap_analysis"] = gap_analysis_path
            if generators_detected:
                result["generators_detected"] = generators_detected
            _emit_json(
                _inject_branch_contract(
                    result,
                    target_branch=target_branch,
                    current_branch=current_branch,
                )
            )
        else:
            console.print(f"[green]✓[/green] Plan scaffolded: {plan_file}")

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


def _find_latest_feature_worktree(repo_root: Path) -> Path | None:
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


def _find_feature_worktree(repo_root: Path, mission_slug: str) -> Path | None:
    """Find a deterministic worktree for a feature slug."""
    return resolve_feature_worktree(repo_root, mission_slug)


def _get_current_branch(repo_root: Path) -> str:
    """Get current git branch name.

    Args:
        repo_root: Repository root directory

    Returns:
        Current branch name, or detected primary branch if not in a git repo
    """
    from specify_cli.core.git_ops import resolve_primary_branch

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    return result.stdout.strip() if result.returncode == 0 else resolve_primary_branch(repo_root)


@app.command(name="accept")
def accept_feature(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (required in multi-mission repos)")] = None,
    mode: Annotated[str, typer.Option("--mode", help="Acceptance mode: auto, pr, local, checklist")] = "auto",
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON for agent parsing")] = False,
    lenient: Annotated[bool, typer.Option("--lenient", help="Skip strict metadata validation")] = False,
    no_commit: Annotated[bool, typer.Option("--no-commit", help="Skip auto-commit (report only)")] = False,
) -> None:
    """Perform mission acceptance workflow.

    This command:
    1. Validates all tasks are in 'done' lane
    2. Runs acceptance checks from checklist files
    3. Creates acceptance report
    4. Marks mission as ready for merge

    Wrapper for top-level accept command with agent-specific defaults.

    Examples:
        # Run acceptance workflow
        spec-kitty agent mission accept --mission 077-my-mission

        # With JSON output for agents
        spec-kitty agent mission accept --mission 077-my-mission --json

        # Lenient mode (skip strict validation)
        spec-kitty agent mission accept --mission 077-my-mission --lenient --json
    """
    # Delegate to top-level accept command
    try:
        # Call top-level accept with mapped parameters
        top_level_accept(
            mission=feature,
            feature=None,
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
        raise typer.Exit(1) from None


@app.command(name="merge")
def merge_feature(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (required in multi-mission repos)")] = None,
    target: Annotated[str | None, typer.Option("--target", help="Target branch to merge into (required in multi-feature repos)")] = None,
    strategy: Annotated[str, typer.Option("--strategy", help="Merge strategy: merge, squash, rebase")] = "merge",
    push: Annotated[bool, typer.Option("--push", help="Push to origin after merging")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show actions without executing")] = False,
    keep_branch: Annotated[bool, typer.Option("--keep-branch", help="Keep mission branch after merge (default: delete)")] = False,
    keep_worktree: Annotated[bool, typer.Option("--keep-worktree", help="Keep worktree after merge (default: remove)")] = False,
    auto_retry: Annotated[
        bool, typer.Option("--auto-retry/--no-auto-retry", help="Auto-navigate to a deterministic mission worktree if in the wrong location")
    ] = False,
) -> None:
    """Merge mission branch into target branch.

    This command:
    1. Validates the mission is accepted
    2. Merges the mission branch into target (usually 'main')
    3. Cleans up worktree
    4. Deletes the mission branch

    Auto-retry logic:
    If current branch doesn't match feature pattern and auto-retry is enabled,
    it retries only when --mission is provided so worktree selection is deterministic.

    Delegates to existing tasks_cli.py merge implementation.

    Examples:
        # Merge into main branch
        spec-kitty agent mission merge --mission 077-my-mission

        # Merge into specific branch with push
        spec-kitty agent mission merge --mission 077-my-mission --target develop --push

        # Dry-run mode
        spec-kitty agent mission merge --mission 077-my-mission --dry-run

        # Keep worktree and branch after merge
        spec-kitty agent mission merge --mission 077-my-mission --keep-worktree --keep-branch
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error = "Could not locate project root"
            print(json.dumps({"error": error, "success": False}))
            sys.exit(1)

        # Resolve the mission handle to a canonical slug before delegating.
        resolved_feature = feature
        if feature:
            try:
                _resolved = resolve_mission_handle(feature, repo_root)
            except (SystemExit, typer.Exit):
                # Preserve legacy wrapper behavior in tests and programmatic
                # callers that pass a raw slug/worktree hint without a real
                # mission directory. The delegated merge flow still performs
                # its own resolution when operating against a real repo.
                _resolved = None
            if _resolved is not None:
                resolved_feature = _resolved.mission_slug

        # Resolve target branch dynamically if not specified
        if target is None:
            if resolved_feature:
                target = get_feature_target_branch(repo_root, resolved_feature)
            else:
                from specify_cli.core.git_ops import resolve_primary_branch

                target = resolve_primary_branch(repo_root)

        # Auto-retry logic: Check if we're on a feature branch
        if auto_retry and not os.environ.get("SPEC_KITTY_AUTORETRY"):
            current_branch = _get_current_branch(repo_root)
            is_feature_branch = re.match(r"^\d{3}-", current_branch)

            if not is_feature_branch:
                if not resolved_feature:
                    raise RuntimeError(f"Not on mission branch ({current_branch}). Auto-retry requires --mission to choose a deterministic worktree.")

                retry_worktree = _find_feature_worktree(repo_root, resolved_feature)
                if not retry_worktree:
                    raise RuntimeError(f"Could not find worktree for mission {resolved_feature} under {repo_root / '.worktrees'}.")

                console.print(f"[yellow]Auto-retry:[/yellow] Not on mission branch ({current_branch}). Running merge in {retry_worktree.name}")

                # Set env var to prevent infinite recursion
                env = os.environ.copy()
                env["SPEC_KITTY_AUTORETRY"] = "1"

                # Re-run command in worktree; pass canonical slug so retry is unambiguous.
                retry_cmd = ["spec-kitty", "agent", "mission", "merge"]
                retry_cmd.extend(["--mission", resolved_feature])
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
                    cwd=retry_worktree,
                    env=env,
                )
                sys.exit(result.returncode)

        # Delegate to top-level merge command with parameter mapping
        # Note: Agent uses --keep-branch/--keep-worktree (default: False)
        #       Top-level uses --delete-branch/--remove-worktree (default: True)
        #       So we need to invert the logic
        try:
            top_level_merge(
                strategy=MergeStrategy(strategy),
                delete_branch=not keep_branch,  # Invert: keep -> delete
                remove_worktree=not keep_worktree,  # Invert: keep -> remove
                push=push,
                target_branch=target,  # Note: parameter name differs
                dry_run=dry_run,
                json_output=False,
                mission=(resolved_feature or ""),
                feature=None,
                resume=False,  # Agent commands don't support resume
                abort=False,  # Agent commands don't support abort
                context_token=None,
                keep_workspace=False,
            )
        except typer.Exit:
            # Propagate typer.Exit cleanly
            raise
        except Exception as e:
            print(json.dumps({"error": str(e), "success": False}))
            raise typer.Exit(1) from None

    except typer.Exit:
        raise
    except Exception as e:
        print(json.dumps({"error": str(e), "success": False}))
        raise typer.Exit(1) from None


@app.command(name="finalize-tasks")
def finalize_tasks(
    feature: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-mission')")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    validate_only: Annotated[
        bool, typer.Option("--validate-only", help="Run all validations without committing. Reports issues that would block finalization.")
    ] = False,
) -> None:
    """Parse dependencies from tasks.md and update WP frontmatter, then commit to target branch.

    This command is designed to be called after LLM generates WP files via /spec-kitty.tasks.
    It post-processes the generated files to add dependency information and commits everything.

    Use --validate-only to check for issues (missing requirement mappings, ownership overlaps,
    dependency cycles) without making any changes or committing.

    Bootstrap Mutation Surface (FR-003 / SC-002)
    =============================================
    The following 8 frontmatter fields may be written or overwritten by this
    command. When ``--validate-only`` is active, ALL writes are skipped — the
    ``frontmatter_changed and not validate_only`` guard ensures zero bytes of
    mutation on disk.

    +--------------------------+------------------------------+-----------------------------+
    | Field                    | Source                       | Condition                   |
    +--------------------------+------------------------------+-----------------------------+
    | dependencies             | Parsed from tasks.md         | Written if absent or differs|
    | planning_base_branch     | _resolve_planning_branch()   | Written if differs          |
    | merge_target_branch      | Same as target_branch        | Written if differs          |
    | branch_strategy          | Computed long-form string    | Written if differs          |
    | requirement_refs         | WP frontmatter / tasks.md    | Written if absent or differs|
    | execution_mode           | infer_ownership()            | Written only if absent      |
    | owned_files              | infer_ownership()            | Written only if absent      |
    | authoritative_surface    | infer_ownership()            | Written only if absent      |
    +--------------------------+------------------------------+-----------------------------+

    In validate-only mode, the bootstrap loop still infers all 8 fields in
    memory so that downstream validation (ownership overlap checks, lane
    preview) operates against the post-bootstrap state — not the stale
    on-disk frontmatter.  The in-memory snapshots are stored in
    ``_inmemory_frontmatter`` / ``_inmemory_bodies`` and consumed by the
    manifest-building loop that follows.

    See also: ``tasks.py:finalize-tasks()`` which writes ``dependencies`` via
    ``build_document() + write_text()`` — guarded the same way (T002).
    Examples:
        spec-kitty agent mission finalize-tasks --mission 020-my-feature --json
        spec-kitty agent mission finalize-tasks --mission 020-my-feature --validate-only --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            error_msg = "Could not locate project root"
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Determine feature directory
        cwd = Path.cwd().resolve()
        try:
            feature_dir = _find_feature_directory(
                repo_root,
                cwd,
                explicit_feature=feature,
            )
        except ValueError as detection_error:
            payload = _build_setup_plan_detection_error(
                repo_root,
                str(detection_error),
                feature,
                error_code="FEATURE_CONTEXT_UNRESOLVED",
                command_name="finalize-tasks",
                command_args=["--json"] if json_output else [],
            )
            if json_output:
                _emit_json(payload)
            else:
                console.print(f"[red]Error:[/red] {payload['error']}")
                for slug in payload.get("available_missions", [])[:10]:
                    console.print(f"  - {slug}")
                if "example_command" in payload:
                    console.print(f"  {payload['example_command']}")
            raise typer.Exit(1) from None

        mission_slug = feature_dir.name
        target_branch = _resolve_planning_branch(repo_root, feature_dir)
        _ensure_branch_checked_out(repo_root, target_branch, json_output=json_output)
        if not json_output:
            console.print(f"[bold cyan]Branch:[/bold cyan] {target_branch} (target for this mission)")

        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.exists():
            error_msg = f"Tasks directory not found: {tasks_dir}"
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)
        wp_files = list(tasks_dir.glob("WP*.md"))
        expected_wp_ids = _extract_wp_ids_from_task_files(wp_files)

        spec_md = feature_dir / "spec.md"
        if not spec_md.exists():
            error_msg = f"spec.md not found: {spec_md}"
            if json_output:
                print(json.dumps({"error": error_msg}))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        spec_content = spec_md.read_text(encoding="utf-8")
        spec_requirement_ids = _parse_requirement_ids_from_spec_md(spec_content)
        all_spec_requirement_ids = set(spec_requirement_ids["all"])
        functional_spec_requirement_ids = set(spec_requirement_ids["functional"])

        # ─── TIER 0: wps.yaml manifest ────────────────────────────────────────
        try:
            wps_manifest = load_wps_manifest(feature_dir)
        except Exception as exc:
            error_msg = f"wps.yaml is present but could not be loaded: {exc}"
            if json_output:
                _emit_json({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # ─── TIER 1+: existing dependency resolution ──────────────────────────
        # Parse dependencies and requirement refs using 2-tier priority:
        # 1. WP frontmatter (primary — map-requirements writes here directly)
        # 2. tasks.md text parsing (backward compat for pre-API projects)
        tasks_md = feature_dir / "tasks.md"
        wp_dependencies: dict[str, list[str]] = {}
        wp_requirement_refs: dict[str, list[str]] = {}

        if wps_manifest is not None:
            # Build wp_dependencies from manifest (explicit deps only)
            for entry in wps_manifest.work_packages:
                if dependencies_are_explicit(entry):
                    wp_dependencies[entry.id] = list(entry.dependencies)
                else:
                    wp_dependencies[entry.id] = []

        # PRIMARY: WP frontmatter (map-requirements writes here directly)
        wp_requirement_refs = _parse_requirement_refs_from_wp_files(wp_files)

        if wps_manifest is None and tasks_md.exists():
            # Read tasks.md and parse dependency mapping (always needed)
            tasks_content = tasks_md.read_text(encoding="utf-8")
            from specify_cli.core.dependency_parser import parse_dependencies_from_tasks_md as _shared_parse_deps

            wp_dependencies = _shared_parse_deps(tasks_content)
            missing_wp_sections = [wp_id for wp_id in expected_wp_ids if wp_id not in wp_dependencies]
            extra_wp_sections = sorted(set(wp_dependencies) - set(expected_wp_ids))
            if missing_wp_sections or extra_wp_sections:
                error_msg = (
                    "tasks.md work package coverage is incomplete. "
                    "finalize-tasks could not match all WP files to parsed sections, "
                    "so dependency lanes would be unreliable."
                )
                payload = {
                    "error": error_msg,
                    "missing_wp_sections": missing_wp_sections,
                    "extra_wp_sections": extra_wp_sections,
                    "hint": "Use supported section headers such as '## WP01', '## Work Package WP01', or '## Work Package 1 — Title'.",
                }
                if json_output:
                    _emit_json(payload)
                else:
                    console.print(f"[red]Error:[/red] {error_msg}")
                    if missing_wp_sections:
                        console.print(f"  Missing WP sections: {', '.join(missing_wp_sections)}")
                    if extra_wp_sections:
                        console.print(f"  Extra WP sections: {', '.join(extra_wp_sections)}")
                    console.print(f"  {payload['hint']}")
                raise typer.Exit(1)

            # FALLBACK: tasks.md text (backward compat for pre-API projects)
            tasks_md_refs = _parse_requirement_refs_from_tasks_md(tasks_content)
            for wp_id, refs in tasks_md_refs.items():
                if refs and not wp_requirement_refs.get(wp_id):
                    wp_requirement_refs[wp_id] = refs

        # Validate dependencies (detect cycles, invalid references)
        if wp_dependencies:
            # Check for circular dependencies
            cycles = detect_cycles(wp_dependencies)
            if cycles:
                error_msg = f"Circular dependencies detected: {cycles}"
                if json_output:
                    _emit_json({"error": error_msg, "cycles": cycles})
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
                        _emit_json({"error": error_msg, "wp_id": wp_id, "errors": errors})
                    else:
                        console.print(f"[red]Error:[/red] Invalid dependencies for {wp_id}:")
                        for err in errors:
                            console.print(f"  - {err}")
                    raise typer.Exit(1)

        # Update each WP file's frontmatter with dependencies + requirement refs
        wp_files = list(tasks_dir.glob("WP*.md"))
        wp_ids = _extract_wp_ids_from_task_files(wp_files)

        missing_requirement_refs_wps: list[str] = []
        unknown_requirement_refs: dict[str, list[str]] = {}
        mapped_requirement_ids: set[str] = set()

        for wp_id in sorted(set(wp_ids)):
            refs = wp_requirement_refs.get(wp_id, [])
            if not refs:
                missing_requirement_refs_wps.append(wp_id)
                continue

            unknown_refs = sorted(ref for ref in refs if ref not in all_spec_requirement_ids)
            if unknown_refs:
                unknown_requirement_refs[wp_id] = unknown_refs
            else:
                mapped_requirement_ids.update(refs)

        unmapped_functional_requirements = sorted(functional_spec_requirement_ids - mapped_requirement_ids)

        if missing_requirement_refs_wps or unknown_requirement_refs or unmapped_functional_requirements:
            error_msg = "Requirement mapping validation failed"
            payload = {
                "error": error_msg,
                "missing_requirement_refs_wps": missing_requirement_refs_wps,
                "unknown_requirement_refs": unknown_requirement_refs,
                "unmapped_functional_requirements": unmapped_functional_requirements,
                "dependencies_parsed": wp_dependencies,
                "requirement_refs_parsed": wp_requirement_refs,
            }
            if json_output:
                print(json.dumps(payload))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
                if missing_requirement_refs_wps:
                    console.print("[red]Missing requirement refs:[/red]")
                    for wp_id in missing_requirement_refs_wps:
                        console.print(f"  - {wp_id}")
                if unknown_requirement_refs:
                    console.print("[red]Unknown requirement refs:[/red]")
                    for wp_id, refs in unknown_requirement_refs.items():
                        console.print(f"  - {wp_id}: {', '.join(refs)}")
                if unmapped_functional_requirements:
                    console.print("[red]Unmapped functional requirements:[/red]")
                    for req_id in unmapped_functional_requirements:
                        console.print(f"  - {req_id}")
            raise typer.Exit(1)

        updated_count = 0
        work_packages: list[dict[str, object]] = []
        # Per-WP outcome tracking (T008)
        modified_wps: list[str] = []
        unchanged_wps: list[str] = []
        preserved_wps: list[str] = []
        # Would-be changes for --validate-only report (T007)
        would_modify: list[dict[str, object]] = []
        planning_base_branch = target_branch
        merge_target_branch = target_branch
        branch_strategy = (
            f"Planning artifacts for this feature were generated on {planning_base_branch}. "
            f"During /spec-kitty.implement this WP may branch from a dependency-specific base, "
            f"but completed changes must merge back into {merge_target_branch} unless the human explicitly redirects the landing branch."
        )

        # --- Pre-loop: read all existing frontmatter for conflict detection (T004) ---
        existing_frontmatter: dict[str, WPMetadata] = {}
        for _wp_file in wp_files:
            _wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", _wp_file.name)
            if not _wp_id_match:
                continue
            _wp_id = _wp_id_match.group(1)
            try:
                _wp_meta, _ = read_wp_frontmatter(_wp_file)
                existing_frontmatter[_wp_id] = _wp_meta
            except Exception:
                existing_frontmatter[_wp_id] = WPMetadata(work_package_id=_wp_id, title=_wp_id)

        # --- Dependency conflict detection (T004: disagree-loud) ---
        dep_conflict_errors: list[str] = []
        for wp_id_chk, parsed_deps in wp_dependencies.items():
            existing_meta = existing_frontmatter.get(wp_id_chk)
            existing_deps: list[str] = list(existing_meta.dependencies) if existing_meta else []
            if existing_deps and parsed_deps and set(existing_deps) != set(parsed_deps):
                dep_conflict_errors.append(
                    f"{wp_id_chk}: frontmatter has {sorted(existing_deps)}, "
                    f"tasks.md parsed {sorted(parsed_deps)}. "
                    f"Resolve the disagreement in tasks.md or WP frontmatter before finalizing."
                )
        if dep_conflict_errors:
            error_msg = "Dependency disagreement detected:\n" + "\n".join(dep_conflict_errors)
            if json_output:
                _emit_json({"error": error_msg, "dependency_conflicts": dep_conflict_errors})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)

        all_ownership_warnings: list[str] = []

        # Accumulate in-memory post-bootstrap frontmatter for each WP.
        # In validate-only mode the disk is not written, so downstream
        # validation (ownership manifests, lane preview) must use these
        # snapshots instead of re-reading the unchanged files.
        _inmemory_frontmatter: dict[str, WPMetadata] = {}
        _inmemory_bodies: dict[str, str] = {}

        for wp_file in wp_files:
            # Extract WP ID from filename
            wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
            if not wp_id_match:
                continue

            wp_id = wp_id_match.group(1)

            # Detect whether dependencies field exists in raw frontmatter
            raw_content = wp_file.read_text(encoding="utf-8")
            has_dependencies_line = False
            has_requirement_refs_line = False
            if raw_content.startswith("---"):
                parts = raw_content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1]
                    has_dependencies_line = re.search(r"^\s*dependencies\s*:", frontmatter_text, re.MULTILINE) is not None
                    has_requirement_refs_line = re.search(r"^\s*requirement_refs\s*:", frontmatter_text, re.MULTILINE) is not None

            # Read current frontmatter (typed)
            try:
                wp_meta, body = read_wp_frontmatter(wp_file)
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Could not read {wp_file.name}: {e}")
                continue

            # --- Dependency resolution with preserve-existing (T004) ---
            parsed_deps = wp_dependencies.get(wp_id, [])
            existing_deps = list(wp_meta.dependencies)
            # When wps.yaml is the authority, never fall back to existing frontmatter deps.
            # The manifest is always authoritative regardless of whether parsed_deps is empty.
            if wps_manifest is None and not parsed_deps and existing_deps:
                # Parser found nothing but frontmatter has deps — preserve existing
                deps = existing_deps
                preserved_wps.append(wp_id)
            else:
                deps = parsed_deps

            requirement_refs = wp_requirement_refs.get(wp_id, [])
            title = wp_meta.display_title
            work_packages.append(
                {
                    "id": wp_id,
                    "title": title,
                    "dependencies": deps,
                    "requirement_refs": requirement_refs,
                }
            )

            frontmatter_changed = False
            changed_fields: dict[str, object] = {}

            # Build updates using typed comparison against WPMetadata fields
            bld = wp_meta.builder()

            # Update frontmatter with dependencies + requirement refs
            if not has_dependencies_line or list(wp_meta.dependencies) != deps:
                changed_fields["dependencies"] = deps
                bld.set(dependencies=deps)
                frontmatter_changed = True

            if wp_meta.planning_base_branch != planning_base_branch:
                changed_fields["planning_base_branch"] = planning_base_branch
                bld.set(planning_base_branch=planning_base_branch)
                frontmatter_changed = True

            if wp_meta.merge_target_branch != merge_target_branch:
                changed_fields["merge_target_branch"] = merge_target_branch
                bld.set(merge_target_branch=merge_target_branch)
                frontmatter_changed = True

            if wp_meta.branch_strategy != branch_strategy:
                changed_fields["branch_strategy"] = branch_strategy
                bld.set(branch_strategy=branch_strategy)
                frontmatter_changed = True

            if not has_requirement_refs_line or list(wp_meta.requirement_refs) != requirement_refs:
                changed_fields["requirement_refs"] = requirement_refs
                bld.set(requirement_refs=requirement_refs)
                frontmatter_changed = True

            # Ownership manifest: infer missing fields, write to frontmatter
            if not wp_meta.execution_mode or not wp_meta.owned_files:
                wp_raw_content = wp_file.read_text(encoding="utf-8")
                ownership, infer_warnings = infer_ownership(wp_raw_content, mission_slug)
                all_ownership_warnings.extend(infer_warnings)
                if not wp_meta.execution_mode:
                    changed_fields["execution_mode"] = str(ownership.execution_mode)
                    bld.set(execution_mode=str(ownership.execution_mode))
                    frontmatter_changed = True
                if not wp_meta.owned_files:
                    changed_fields["owned_files"] = list(ownership.owned_files)
                    bld.set(owned_files=list(ownership.owned_files))
                    frontmatter_changed = True
                if not wp_meta.authoritative_surface:
                    changed_fields["authoritative_surface"] = ownership.authoritative_surface
                    bld.set(authoritative_surface=ownership.authoritative_surface)
                    frontmatter_changed = True

            # Build the updated WPMetadata (validated)
            updated_meta = bld.build() if frontmatter_changed else wp_meta

            # Snapshot the post-bootstrap in-memory state for downstream
            # validation (especially in validate-only mode where disk is untouched).
            _inmemory_frontmatter[wp_id] = updated_meta
            _inmemory_bodies[wp_id] = body

            if frontmatter_changed:
                # Gate ALL file writes on validate_only (T006)
                if not validate_only:
                    write_frontmatter(
                        wp_file,
                        updated_meta.model_dump(exclude_none=True, mode="json"),
                        body,
                    )
                else:
                    would_modify.append({"wp_id": wp_id, "changes": changed_fields})
                updated_count += 1
                if wp_id not in preserved_wps:
                    modified_wps.append(wp_id)
            else:
                if wp_id not in preserved_wps:
                    unchanged_wps.append(wp_id)

        # T017: Regenerate tasks.md from wps.yaml manifest (FR-008, FR-011)
        if wps_manifest is not None:
            tasks_md_content = generate_tasks_md_from_manifest(wps_manifest, mission_slug)
            tasks_md.write_text(tasks_md_content, encoding="utf-8")
            if not json_output:
                console.print(f"[green]Regenerated[/green] tasks.md from wps.yaml ({len(wps_manifest.work_packages)} WPs)")

        # Validate ownership manifests across all WPs (hard errors block finalization)
        #
        # In validate-only mode the bootstrap loop above populates frontmatter
        # in memory but does NOT write to disk.  Re-reading from disk would miss
        # the inferred ownership fields, silently skipping ownership/lane
        # validation.  We therefore use the in-memory state when available.
        wp_manifests: dict[str, object] = {}
        wp_bodies: dict[str, str] = {}
        for wp_file in wp_files:
            wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
            if not wp_id_match:
                continue
            wp_id = wp_id_match.group(1)
            with contextlib.suppress(Exception):  # Skip WPs with unreadable frontmatter
                if wp_id in _inmemory_frontmatter:
                    fm_meta = _inmemory_frontmatter[wp_id]
                    wp_body = _inmemory_bodies[wp_id]
                else:
                    fm_meta, wp_body = read_wp_frontmatter(wp_file)
                wp_bodies[wp_id] = wp_body
                if fm_meta.execution_mode and fm_meta.owned_files:
                    from specify_cli.ownership.models import OwnershipManifest

                    wp_manifests[wp_id] = OwnershipManifest.from_frontmatter(fm_meta)

        if wp_manifests:
            ownership_result = validate_ownership(wp_manifests)  # type: ignore[arg-type]
            for warning in ownership_result.warnings:
                if not json_output:
                    console.print(f"[yellow]Ownership warning:[/yellow] {warning}")
            if not ownership_result.passed:
                error_msg = "Ownership validation failed"
                if json_output:
                    _emit_json({"error": error_msg, "ownership_errors": ownership_result.errors})
                else:
                    console.print(f"[red]Error:[/red] {error_msg}")
                    for err in ownership_result.errors:
                        console.print(f"  - {err}")
                raise typer.Exit(1) from None

            # Soft check: warn when owned_files globs match zero files (T013)
            glob_warnings = validate_glob_matches(wp_manifests, repo_root)  # type: ignore[arg-type]
            all_ownership_warnings.extend(glob_warnings)
            if not json_output:
                for warning in glob_warnings:
                    console.print(f"[yellow]Ownership warning:[/yellow] {warning}")

            # Soft check: warn when codebase-wide WPs miss audit targets
            codebase_wide_owned_files = [list(manifest.owned_files) for manifest in wp_manifests.values() if manifest.is_codebase_wide]
            audit_warnings = validate_audit_coverage(codebase_wide_owned_files, repo_root)
            all_ownership_warnings.extend(audit_warnings)
            if not json_output:
                for warning in audit_warnings:
                    console.print(f"[yellow]Audit coverage warning:[/yellow] {warning}")

        # Prepare metadata for event emission
        mission_slug = feature_dir.name
        meta_path = feature_dir / "meta.json"
        meta = None
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                console.print(f"[yellow]Warning:[/yellow] Failed to read meta.json for event emission: {exc}")
        else:
            console.print("[yellow]Warning:[/yellow] meta.json missing; skipping MissionCreated emission")

        # Commit tasks.md and WP files to target branch
        commit_created = False
        commit_hash = None
        files_committed = []

        if validate_only:
            # Bootstrap dry-run: report what would be seeded (no mutation)
            bootstrap_result = bootstrap_canonical_state(
                feature_dir,
                mission_slug,
                dry_run=True,
            )
            bootstrap_stats = {
                "total_wps": bootstrap_result.total_wps,
                "newly_seeded": bootstrap_result.newly_seeded,
                "already_initialized": bootstrap_result.already_initialized,
            }

            # Validate lane computation (dry-run — compute but don't write)
            lanes_stats: dict[str, object] = {"computed": False}
            if wp_manifests and wp_dependencies:
                from specify_cli.lanes.compute import compute_lanes as _compute_lanes_validate

                lanes_manifest_dry = _compute_lanes_validate(
                    dependency_graph=wp_dependencies,
                    ownership_manifests=wp_manifests,  # type: ignore[arg-type]
                    mission_slug=mission_slug,
                    target_branch=target_branch,
                    wp_bodies=wp_bodies,
                    mission_id=meta.get("mission_id") if meta else None,
                )
                _cr_dry = lanes_manifest_dry.collapse_report
                lanes_stats = {
                    "computed": True,
                    "count": len(lanes_manifest_dry.lanes),
                    "lane_ids": [lane.lane_id for lane in lanes_manifest_dry.lanes],
                    "planning_artifact_wps": lanes_manifest_dry.planning_artifact_wps,
                    "collapse_report": _cr_dry.to_dict() if _cr_dry else None,
                }

            if json_output:
                _emit_json(
                    {
                        "result": "validation_passed",
                        "mission_slug": mission_slug,
                        "wp_count": len(work_packages),
                        "validate_only": True,
                        "would_modify": would_modify,
                        "would_preserve": preserved_wps,
                        "unchanged": unchanged_wps,
                        "updated_wp_count": updated_count,
                        "ownership_warnings": all_ownership_warnings,
                        "validation": {
                            "bootstrap_preview": bootstrap_stats,
                            "lanes_preview": lanes_stats,
                        },
                        "message": "All validations passed. Run without --validate-only to commit.",
                    }
                )
            else:
                console.print("[green]✓[/green] All validations passed (--validate-only mode, no commit)")
                console.print(f"  Mission: {mission_slug}")
                console.print(f"  WPs validated: {len(work_packages)}")
                console.print(f"  Would modify: {len(would_modify)} WP(s), preserve: {len(preserved_wps)}, unchanged: {len(unchanged_wps)}")
                console.print(f"  Bootstrap: {bootstrap_result.newly_seeded} WPs would be seeded, {bootstrap_result.already_initialized} already initialized")
                if lanes_stats.get("computed"):
                    console.print(f"  Lanes: {lanes_stats['count']} lane(s) would be computed")
                    _cr_info = lanes_stats.get("collapse_report")
                    if _cr_info and _cr_info.get("independent_wps_collapsed", 0) > 0:
                        console.print(
                            f"[yellow]⚠[/yellow] {_cr_info['independent_wps_collapsed']} independent WP pair(s) "
                            f"collapsed into same lane. Run with --json to see details."
                        )
            return

        # Bootstrap canonical status state for all WPs
        bootstrap_result = bootstrap_canonical_state(
            feature_dir,
            mission_slug,
            dry_run=False,
        )
        if not json_output and bootstrap_result.newly_seeded:
            console.print(f"[green]✓[/green] Bootstrapped canonical status: {bootstrap_result.newly_seeded} WPs seeded")

        # Compute execution lanes from dependency graph + ownership manifests
        lanes_path = None
        lanes_manifest = None
        if wp_manifests and wp_dependencies:
            from specify_cli.lanes.compute import compute_lanes
            from specify_cli.lanes.persistence import write_lanes_json

            lanes_manifest = compute_lanes(
                dependency_graph=wp_dependencies,
                ownership_manifests=wp_manifests,  # type: ignore[arg-type]
                mission_slug=mission_slug,
                target_branch=target_branch,
                wp_bodies=wp_bodies,
                mission_id=meta.get("mission_id") if meta else None,
            )
            lanes_path = write_lanes_json(feature_dir, lanes_manifest)
            if not json_output:
                console.print(f"[green]✓[/green] Computed {len(lanes_manifest.lanes)} execution lane(s)")
                if lanes_manifest.collapse_report and lanes_manifest.collapse_report.independent_wps_collapsed > 0:
                    console.print(
                        f"[yellow]⚠[/yellow] {lanes_manifest.collapse_report.independent_wps_collapsed} "
                        f"independent WP pair(s) collapsed into same lane. Run with --json to see details."
                    )

            # Compute parallelization risk report
            from specify_cli.policy.config import load_policy_config
            from specify_cli.policy.risk_scorer import compute_risk_report

            _policy = load_policy_config(repo_root)
            risk_report = compute_risk_report(
                lanes_manifest,
                wp_bodies=wp_bodies,
                policy=_policy.risk,
            )
            if risk_report.overall_score > 0 and not json_output:
                console.print(f"[yellow]⚠[/yellow] Parallelization risk: {risk_report.overall_score:.2f} (threshold: {risk_report.threshold:.2f})")
                for pr in risk_report.lane_pair_risks:
                    if pr.score > 0:
                        console.print(f"  {pr.lane_a} ↔ {pr.lane_b}: {pr.score:.2f}")
                        for d in pr.shared_parent_dirs[:3]:
                            console.print(f"    shared dir: {d}")
                        for c in pr.import_coupling[:3]:
                            console.print(f"    coupling: {c}")
            if risk_report.exceeds_threshold and _policy.risk.mode == "block":
                error_msg = (
                    f"Parallelization risk {risk_report.overall_score:.2f} exceeds threshold "
                    f"{risk_report.threshold:.2f}. Adjust the risk policy to proceed."
                )
                if json_output:
                    _emit_json(
                        {
                            "error": error_msg,
                            "risk_report": {
                                "overall_score": risk_report.overall_score,
                                "threshold": risk_report.threshold,
                            },
                        }
                    )
                else:
                    console.print(f"[red]Error:[/red] {error_msg}")
                raise typer.Exit(1)

        # Run dossier sync before the commit so its deterministic snapshot lands
        # atomically with the rest of the planning artifacts.
        with contextlib.suppress(Exception):
            from specify_cli.sync.dossier_pipeline import (
                trigger_feature_dossier_sync_if_enabled,
            )

            trigger_feature_dossier_sync_if_enabled(
                feature_dir,
                mission_slug,
                repo_root,
            )

        try:
            files_to_commit = _collect_finalize_artifacts(
                feature_dir,
                tasks_dir,
                mission_slug,
                lanes_path=lanes_path,
            )
            files_to_commit_rel = [str(path.relative_to(repo_root)) for path in files_to_commit]
            files_committed = list(files_to_commit_rel)

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
                    console.print("[dim]Tasks unchanged, no commit needed[/dim]")
            else:
                # Commit with descriptive message (safe_commit preserves staging area)
                commit_msg = f"Add tasks for feature {mission_slug}"
                commit_success = safe_commit(
                    repo_path=repo_root,
                    files_to_commit=files_to_commit,
                    commit_message=commit_msg,
                    allow_empty=False,
                )

                if commit_success:
                    # Commit succeeded - get hash
                    _rc, stdout, _stderr = run_command(["git", "rev-parse", "HEAD"], check_return=True, capture=True, cwd=repo_root)
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
                        console.print(f"[red]Error:[/red] Git commit failed: {error_output}")
                    raise typer.Exit(1)

        except typer.Exit:
            raise
        except Exception as e:
            # Unexpected error
            if json_output:
                _emit_json({"error": str(e)})
            else:
                console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

        # Emit WPCreated events (non-blocking)
        # MissionCreated is emitted earlier during mission create
        causation_id = get_emitter().generate_causation_id()

        for wp in work_packages:
            try:
                emit_wp_created(
                    wp_id=str(wp["id"]),
                    title=str(wp["title"]),
                    dependencies=list(wp["dependencies"]),
                    mission_slug=mission_slug,
                    causation_id=causation_id,
                )
            except Exception as exc:
                console.print(f"[yellow]Warning:[/yellow] WPCreated emission failed for {wp['id']}: {exc}")

        if json_output:
            _emit_json(
                {
                    "result": "success",
                    "wp_count": len(work_packages),
                    "updated_wp_count": updated_count,
                    "modified_wps": modified_wps,
                    "unchanged_wps": unchanged_wps,
                    "preserved_wps": preserved_wps,
                    "tasks_dir": str(tasks_dir),
                    "commit_created": commit_created,
                    "commit_hash": commit_hash,
                    "files_committed": files_committed,
                    "dependencies_parsed": wp_dependencies,
                    "requirement_refs_parsed": wp_requirement_refs,
                    "bootstrap": {
                        "total_wps": bootstrap_result.total_wps,
                        "newly_seeded": bootstrap_result.newly_seeded,
                        "already_initialized": bootstrap_result.already_initialized,
                    },
                    "lanes": {
                        "computed": lanes_manifest is not None,
                        "count": len(lanes_manifest.lanes) if lanes_manifest else 0,
                        "lane_ids": [lane.lane_id for lane in lanes_manifest.lanes] if lanes_manifest else [],
                        "planning_artifact_wps": lanes_manifest.planning_artifact_wps if lanes_manifest else [],
                        "collapse_report": (lanes_manifest.collapse_report.to_dict() if lanes_manifest and lanes_manifest.collapse_report else None),
                    },
                    "ownership_warnings": all_ownership_warnings,
                }
            )

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


def _parse_wp_sections_from_tasks_md(tasks_content: str) -> dict[str, str]:
    """Extract WP sections from tasks.md keyed by WP ID."""
    sections: dict[str, str] = {}
    matches = list(
        re.finditer(
            r"(?m)^#{2,4}\s+(?:Work Package\s+)?(WP\d{2})(?:\b|:)",
            tasks_content,
        )
    )

    for idx, match in enumerate(matches):
        wp_id = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tasks_content)
        sections[wp_id] = tasks_content[start:end]

    return sections


def _parse_dependencies_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse WP dependencies from tasks.md content."""
    dependencies: dict[str, list[str]] = {}

    for wp_id, section_content in _parse_wp_sections_from_tasks_md(tasks_content).items():
        explicit_deps: list[str] = []

        # Pattern: "Depends on WP01" or "Depends on WP01, WP02"
        depends_matches = re.findall(
            r"Depends?\s+on\s+(WP\d{2}(?:\s*,\s*WP\d{2})*)",
            section_content,
            re.IGNORECASE,
        )
        for match in depends_matches:
            explicit_deps.extend(re.findall(r"WP\d{2}", match))

        # Pattern: "**Dependencies**: WP01" or "Dependencies: WP01, WP02"
        deps_line_matches = re.findall(
            r"\*?\*?Dependencies\*?\*?\s*:\s*(.+)",
            section_content,
            re.IGNORECASE,
        )
        for match in deps_line_matches:
            explicit_deps.extend(re.findall(r"WP\d{2}", match))

        dependencies[wp_id] = list(dict.fromkeys(explicit_deps))

    return dependencies


def _parse_requirement_refs_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse requirement references per WP from tasks.md content."""
    requirement_refs: dict[str, list[str]] = {}

    for wp_id, section_content in _parse_wp_sections_from_tasks_md(tasks_content).items():
        refs: list[str] = []
        ref_line_matches = re.findall(
            r"\*?\*?Requirements?\s*(?:Refs)?\*?\*?\s*:\s*(.+)",
            section_content,
            re.IGNORECASE,
        )
        for match in ref_line_matches:
            refs.extend(ref_id.upper() for ref_id in re.findall(r"\b(?:FR|NFR|C)-\d+\b", match, re.IGNORECASE))
        requirement_refs[wp_id] = list(dict.fromkeys(refs))

    return requirement_refs


def _parse_requirement_refs_from_wp_files(wp_files: list[Path]) -> dict[str, list[str]]:
    """Parse requirement refs directly from WP prompt frontmatter."""
    from specify_cli.requirement_mapping import normalize_requirement_refs_value
    from specify_cli.status.wp_metadata import read_wp_frontmatter

    parsed: dict[str, list[str]] = {}
    for wp_file in wp_files:
        wp_id_match = re.match(r"^(WP\d{2})(?:[-_.]|$)", wp_file.name)
        if not wp_id_match:
            continue
        wp_id = wp_id_match.group(1)
        try:
            meta, _ = read_wp_frontmatter(wp_file)
        except Exception:
            parsed.setdefault(wp_id, [])
            continue
        refs = normalize_requirement_refs_value(meta.requirement_refs)
        parsed[wp_id] = refs
    return parsed


def _parse_requirement_ids_from_spec_md(spec_content: str) -> dict[str, list[str]]:
    """Parse requirement IDs from spec.md content."""
    from specify_cli.requirement_mapping import parse_requirement_ids_from_spec_md

    return parse_requirement_ids_from_spec_md(spec_content)
