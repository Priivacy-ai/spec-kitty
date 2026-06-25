"""check-prerequisites command family for ``agent mission`` (#2056 WP05).

Hosts the ``check-prerequisites`` command and its dedicated emit helpers
(``_emit_check_prerequisites_detection_error``, ``_emit_check_prerequisites_result``,
``_paths_only_payload``) plus the small ``meta.json`` readers
(``_read_meta_for_pr_bound``, ``_read_meta_for_emission``) the create/finalize
lifecycle shares.

The command is defined here as a plain callable; ``mission`` registers it on its
Typer ``app`` (and re-exports the name so ``mission.check_prerequisites`` — the
documented agent-alias dispatch target and patch target — keeps resolving). The
command resolves the not-yet-relocated ``_enforce_git_preflight`` preflight guard
through the ``mission`` module at call time so the existing
``mission._enforce_git_preflight`` patch seam is preserved without an import
cycle (the guard relocates with the setup-plan family in WP06).

One-way leaf (INV-8): imports lower layers + sibling Seam B/C/D leaves only,
never back into ``mission`` at module scope. Behavior is preserved byte-for-byte
from the pre-decomposition ``mission.py``; the WP01 golden harness is the
regression net.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, cast

from rich.console import Console
import typer

from mission_runtime import ActionContextError

from specify_cli.cli.commands.agent.mission_branch_context import (
    _inject_branch_contract,
    _resolve_feature_target_branch,
)
from specify_cli.cli.commands.agent.mission_feature_resolution import (
    _build_setup_plan_detection_error,
)
from specify_cli.cli.commands.agent.mission_parsing import (
    _emit_console_or_json_error,
    _emit_json,
)

console = Console()

PROJECT_ROOT_NOT_FOUND = "Could not locate project root"
PROJECT_ROOT_NOT_FOUND_MESSAGE = f"{PROJECT_ROOT_NOT_FOUND}. Run from within spec-kitty repository."


def _read_meta_for_pr_bound(feature_dir: Path) -> dict[str, Any]:
    """Read ``meta.json`` for the ``pr_bound`` write-back, silent-empty contract.

    Routes through the canonical ``mission_metadata.load_meta`` authority
    (FR-009 / SC-004) via ``load_meta_or_empty``: a missing *or* malformed file
    degrades to ``{}`` so the write-back is skipped, preserving the prior
    ``except (OSError, JSONDecodeError): pass`` (a corrupt meta never crashes
    the create flow).
    """
    from specify_cli.mission_metadata import load_meta_or_empty

    return load_meta_or_empty(feature_dir)


def _read_meta_for_emission(feature_dir: Path) -> dict[str, Any] | None:
    """Read ``meta.json`` for finalize-tasks event emission, silent-none contract.

    Routes through the canonical ``mission_metadata.load_meta`` authority
    (FR-009 / SC-004) with ``on_malformed="none"``: a missing *or* malformed
    file degrades to ``None`` (the caller warns and skips emission), preserving
    the prior ``except (JSONDecodeError, OSError)`` warn-and-continue behavior.
    """
    from specify_cli.mission_metadata import load_meta

    return load_meta(feature_dir, allow_missing=True, on_malformed="none")


def _emit_check_prerequisites_detection_error(
    *,
    repo_root: Path,
    detection_error: ValueError | ActionContextError,
    feature: str | None,
    json_output: bool,
    paths_only: bool,
    include_tasks: bool,
) -> None:
    """Emit the existing feature-detection payload for prerequisite checks."""
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
        return

    console.print(f"[red]Error:[/red] {payload['error']}")
    for slug in cast(list[str], payload.get("available_missions", []))[:10]:
        console.print(f"  - {slug}")
    if "example_command" in payload:
        console.print(f"  {payload['example_command']}")


def _paths_only_payload(validation_result: dict[str, object]) -> dict[str, object]:
    """Build the legacy paths-only payload shape for prerequisite checks."""
    paths_payload = dict(cast(dict[str, object], validation_result["paths"]))
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
    return paths_payload


def _emit_check_prerequisites_result(
    *,
    validation_result: dict[str, object],
    feature_dir: Path,
    json_output: bool,
    paths_only: bool,
    target_branch: str,
    current_branch: str,
) -> None:
    """Emit prerequisite-check output in JSON or human form."""
    if json_output:
        payload = _paths_only_payload(validation_result) if paths_only else dict(validation_result)
        _emit_json(
            _inject_branch_contract(
                payload,
                target_branch=target_branch,
                current_branch=current_branch,
            )
        )
        return

    if validation_result["valid"]:
        console.print("[green]✓[/green] Prerequisites check passed")
        console.print(f"   Mission: {feature_dir.name}")
    else:
        console.print("[red]✗[/red] Prerequisites check failed")
        for error in cast(list[str], validation_result["errors"]):
            console.print(f"   • {error}")

    warnings = cast(list[str], validation_result["warnings"])
    for warning in warnings:
        if warning == warnings[0]:
            console.print("\n[yellow]Warnings:[/yellow]")
        console.print(f"   • {warning}")


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
    # Deferred import keeps this leaf free of an import cycle while honoring the
    # historical ``mission.<name>`` patch seams (tests patch ``locate_project_root``
    # / ``_enforce_git_preflight`` / ``_primary_anchored_feature_dir`` /
    # ``_find_feature_directory`` / ``validate_feature_structure`` /
    # ``get_current_branch`` on the ``mission`` module).
    from specify_cli.cli.commands.agent import mission as _mission

    try:
        if require_tasks and not include_tasks:
            include_tasks = True
            if not json_output:
                console.print("[yellow]Warning:[/yellow] --require-tasks is deprecated; use --include-tasks.")

        repo_root = _mission.locate_project_root()
        if repo_root is None:
            _emit_console_or_json_error(
                json_output=json_output,
                message=PROJECT_ROOT_NOT_FOUND_MESSAGE,
            )
            raise typer.Exit(1) from None

        _mission._enforce_git_preflight(
            repo_root,
            json_output=json_output,
            command_name="spec-kitty agent mission check-prerequisites",
        )

        # Determine feature directory (main repo or worktree).
        #
        # #2017-class surface-split fix: the planning-authoring surface this
        # command reports MUST agree with where ``finalize-tasks`` reads its
        # inputs. ``finalize-tasks`` deliberately anchors to the PRIMARY checkout
        # (``primary_feature_dir_for_mission`` — CWD/topology-invariant, the same
        # anchoring ``resolve_placement_only`` uses). The coord-aware read
        # resolver, by contrast, returns the coordination worktree once it is
        # materialized — so an agent authoring tasks at the reported ``feature_dir``
        # would write to coord while finalize reads primary, and finalize parses an
        # empty primary ``tasks/``. Delegate to the SAME primary anchor finalize
        # uses so the two agree by construction; fall back to the coord-aware
        # resolver only when the mission has no primary-surface directory (e.g. a
        # coord-only legacy materialization). The full topology-aware unification
        # of every planning command onto one surface authority is tracked by the
        # single-authority-topology-cleanup mission (#1716 write-surface coherence).
        cwd = Path.cwd().resolve()
        try:
            feature_dir = _mission._primary_anchored_feature_dir(repo_root, feature)
            if feature_dir is None:
                feature_dir = _mission._find_feature_directory(
                    repo_root,
                    cwd,
                    explicit_feature=feature,
                )
        except (ValueError, ActionContextError) as detection_error:
            _emit_check_prerequisites_detection_error(
                repo_root=repo_root,
                detection_error=detection_error,
                feature=feature,
                json_output=json_output,
                paths_only=paths_only,
                include_tasks=include_tasks,
            )
            raise typer.Exit(1) from None

        validation_result = _mission.validate_feature_structure(feature_dir, check_tasks=include_tasks)
        target_branch = _resolve_feature_target_branch(feature_dir, repo_root)
        current_branch = _mission.get_current_branch(repo_root) or target_branch
        _emit_check_prerequisites_result(
            validation_result=validation_result,
            feature_dir=feature_dir,
            json_output=json_output,
            paths_only=paths_only,
            target_branch=target_branch,
            current_branch=current_branch,
        )

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
