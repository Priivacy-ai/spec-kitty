"""create command family for ``agent mission`` (#2056 WP05).

Hosts the ``create`` command, decomposed from its pre-decomposition 281-LOC
monolith into ≤15-CC phase helpers: start-branch resolution, mission-type
selector resolution, the PR-bound branch-strategy gate, the core-creation
error funnel, the ``pr_bound`` meta write-back, and the JSON / human output
builders. Each phase helper is a small deterministic unit with focused tests
(``test_mission_create_phases.py``).

The command is defined here as a plain callable; ``mission`` registers it on its
Typer ``app`` and re-exports the name so ``mission.create_mission`` keeps
resolving — ``lifecycle.py`` binds ``agent.mission as agent_feature`` and calls
``agent_feature.create_mission``. To honor the established
``mission.locate_project_root`` / ``mission.get_current_branch`` patch targets
the command resolves those (and the relocated ``_switch_to_start_branch``)
through the ``mission`` module at call time.

One-way leaf (INV-8): imports lower layers + sibling Seam B/C leaves only, never
back into ``mission`` at module scope (the ``mission`` lookup inside the command
is a deferred, call-time import). Behavior is preserved byte-for-byte from the
pre-decomposition ``mission.py``; the WP01 golden harness is the regression net.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

from rich.console import Console
import typer

from specify_cli.cli.selector_resolution import resolve_selector
from specify_cli.core.constants import MISSION_TYPE_DOCUMENTATION
from specify_cli.diagnostics import mark_invocation_succeeded

from specify_cli.cli.commands.agent.mission_branch_context import (
    _inject_branch_contract,
)
from specify_cli.cli.commands.agent.mission_check_prerequisites import (
    _read_meta_for_pr_bound,
)
from specify_cli.cli.commands.agent.mission_parsing import _emit_json

if TYPE_CHECKING:
    from specify_cli.core.mission_creation import MissionCreationResult

console = Console()

# ``--start-branch`` / ``--target-branch`` must name the same branch because
# mission creation stores exactly one planning branch.
START_TARGET_MISMATCH_MESSAGE = (
    "--start-branch and --target-branch must match because mission "
    "creation stores one planning branch. Omit --target-branch for "
    "the recommended PR-bound feature-branch flow."
)


def _resolve_start_branch_phase(
    *,
    repo_root: Path | None,
    start_branch: str | None,
    target_branch: str | None,
    json_output: bool,
) -> None:
    """Validate start/target branch coherence and switch to ``--start-branch``.

    No-op when ``--start-branch`` is omitted. Exits 1 with a structured payload
    on a start/target mismatch or a branch-switch failure. The branch switch
    routes through ``mission._switch_to_start_branch`` to preserve the historical
    monkeypatch seam.
    """
    if start_branch is None:
        return

    from specify_cli.cli.commands.agent import mission as _mission

    normalized_start_branch = start_branch.strip()
    normalized_target_branch = target_branch.strip() if target_branch else None
    if normalized_target_branch and normalized_target_branch != normalized_start_branch:
        if json_output:
            _emit_json(
                {
                    "error_code": "START_BRANCH_TARGET_MISMATCH",
                    "error": START_TARGET_MISMATCH_MESSAGE,
                    "start_branch": start_branch,
                    "target_branch": target_branch,
                }
            )
        else:
            console.print(f"[bold red]Error:[/bold red] {START_TARGET_MISMATCH_MESSAGE}")
        raise typer.Exit(1)

    try:
        _mission._switch_to_start_branch(repo_root, start_branch)
    except Exception as exc:
        if json_output:
            _emit_json(
                {
                    "error_code": "START_BRANCH_FAILED",
                    "error": str(exc),
                    "start_branch": start_branch,
                }
            )
        else:
            console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc


def _resolve_mission_type_phase(
    *,
    mission_type: str | None,
    mission: str | None,
    json_output: bool,
) -> str | None:
    """Resolve the canonical mission type from the ``--mission-type``/``--mission`` pair.

    Returns the resolved mission type (``mission_type`` unchanged when neither
    flag is supplied). Exits 1 on a selector conflict.
    """
    if mission_type is None and mission is None:
        return mission_type
    try:
        resolved = resolve_selector(
            canonical_value=mission_type,
            canonical_flag="--mission-type",
            alias_value=mission,
            alias_flag="--mission",
            suppress_env_var="SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION",
            command_hint="--mission-type <name>",
        )
        return cast("str | None", resolved.canonical_value)
    except typer.BadParameter as exc:
        if json_output:
            _emit_json({"error": str(exc)})
        else:
            console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc


def _enforce_branch_strategy_gate_phase(
    *,
    pr_bound: bool,
    current_branch: str | None,
    target_branch: str | None,
    branch_strategy: str | None,
    start_branch: str | None,
    json_output: bool,
) -> None:
    """Run the FR-033 PR-bound branch-strategy gate (WP07/T040).

    When the mission is PR-bound and the operator is on the merge target branch,
    prompt for confirmation unless ``--branch-strategy already-confirmed`` is
    supplied. Exits 1 when confirmation is required in ``--json`` mode or the
    operator declines the interactive prompt.
    """
    from specify_cli.cli.commands._branch_strategy_gate import (
        ALREADY_CONFIRMED,
        BranchStrategyGateError,
        evaluate_branch_strategy,
    )

    effective_merge_target = target_branch or current_branch
    gate_branch_strategy = branch_strategy or (ALREADY_CONFIRMED if start_branch is not None else None)
    try:
        gate_outcome = evaluate_branch_strategy(
            pr_bound=pr_bound,
            current_branch=current_branch,
            merge_target_branch=effective_merge_target,
            branch_strategy=gate_branch_strategy,
            prompt=None if json_output else lambda message: typer.confirm(message, default=False),
        )
    except BranchStrategyGateError as exc:
        if json_output:
            _emit_json(
                {
                    "error_code": "BRANCH_STRATEGY_CONFIRMATION_REQUIRED",
                    "error": ("PR-bound mission creation requires explicit branch-strategy confirmation in --json mode."),
                    "branch_strategy_gate": "confirmation_required",
                    "current_branch": current_branch,
                    "merge_target_branch": effective_merge_target,
                    "remediation": "Pass `--branch-strategy already-confirmed` or run without --json to confirm interactively.",
                }
            )
        else:
            console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if gate_outcome.prompted and not gate_outcome.decision.proceed:
        message = "Mission creation aborted by operator at branch-strategy gate. Switch to a feature branch or pass `--branch-strategy already-confirmed`."
        if json_output:
            _emit_json({"error": message, "branch_strategy_gate": "aborted"})
        else:
            console.print(f"[yellow]Aborted:[/yellow] {message}")
        raise typer.Exit(1)


def _print_worktree_navigation_hint(mission_slug: str, error_msg: str) -> None:
    """Print the 'run from main repo' hint when a worktree error blocked creation."""
    if "worktree" not in error_msg.lower():
        return
    # Route through the ``mission`` module so the ``mission.locate_project_root``
    # patch seam keeps reaching this branch after relocation.
    from specify_cli.cli.commands.agent import mission as _mission

    cwd = Path.cwd().resolve()
    main_repo = _mission.locate_project_root(cwd)
    if main_repo is None:
        # Fallback: try .worktrees path heuristic.
        for i, part in enumerate(cwd.parts):
            if part == ".worktrees":
                main_repo = Path(*cwd.parts[:i])
                break
    if main_repo is not None:
        console.print("\n[cyan]Run from the main repository instead:[/cyan]")
        console.print(f"  cd {main_repo}")
        console.print(f"  spec-kitty agent mission create {mission_slug}")


def _run_create_core_phase(
    *,
    repo_root: Path | None,
    mission_slug: str,
    resolved_mission_type: str | None,
    target_branch: str | None,
    friendly_name: str | None,
    purpose_tldr: str | None,
    purpose_context: str | None,
    force_recreate_coordination_branch: bool,
    json_output: bool,
) -> MissionCreationResult:
    """Invoke ``create_mission_core`` with the deterministic error funnel.

    Exits 1 (with the appropriate structured payload) on the three documented
    failure classes: coordination-branch divergence (NFR-007 stable error_code),
    a ``MissionCreationError`` (with worktree navigation hint), or any other
    unexpected exception.
    """
    from specify_cli.core.mission_creation import (
        MissionCreationError,
        create_mission_core,
    )
    from specify_cli.missions._create import CoordinationBranchDiverged

    try:
        return create_mission_core(
            repo_root=repo_root,
            mission_slug=mission_slug,
            mission=resolved_mission_type,
            target_branch=target_branch,
            friendly_name=friendly_name,
            purpose_tldr=purpose_tldr,
            purpose_context=purpose_context,
            force_recreate_coordination_branch=force_recreate_coordination_branch,
        )
    except CoordinationBranchDiverged as exc:
        # Structured error path (NFR-007): emit a stable error_code payload
        # so scripted callers (CI, doctor) can detect this case unambiguously.
        if json_output:
            _emit_json({"error": str(exc), **exc.to_dict()})
        else:
            console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except MissionCreationError as exc:
        error_msg = str(exc)
        if json_output:
            _emit_json({"error": error_msg})
        else:
            console.print(f"[bold red]Error:[/bold red] {error_msg}")
            _print_worktree_navigation_hint(mission_slug, error_msg)
        raise typer.Exit(1) from exc
    except Exception as e:
        if json_output:
            _emit_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


def _persist_pr_bound_phase(result: MissionCreationResult, *, pr_bound: bool) -> None:
    """Persist the ``pr_bound`` flag in ``meta.json`` (FR-033 schema addition)."""
    if not pr_bound:
        return
    meta_data = _read_meta_for_pr_bound(result.feature_dir)
    if meta_data and not meta_data.get("pr_bound"):
        meta_data["pr_bound"] = True
        from specify_cli.mission_metadata import write_meta

        write_meta(result.feature_dir, meta_data)


def _build_create_payload(result: MissionCreationResult) -> dict[str, object]:
    """Build the ``--json`` success payload (pre-branch-contract enrichment)."""
    feature_dir = result.feature_dir
    spec_file = feature_dir / "spec.md"
    meta_file = feature_dir / "meta.json"
    tasks_readme = feature_dir / "tasks" / "README.md"
    return {
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
        "scaffold_only": True,
        "requires_agent_authoring": True,
        "plan_guard": "SPEC_NOT_SUBSTANTIVE_OR_UNCOMMITTED",
        "next_step": ("Created scaffold only. Run `/spec-kitty.specify <intent>` in your agent or edit and commit spec_file before `spec-kitty plan`."),
        "origin_binding": {
            "attempted": result.origin_binding_attempted,
            "succeeded": result.origin_binding_succeeded,
            "error": result.origin_binding_error,
        },
        # Coordination branch (WP03 / issue #1348) — top-level field so
        # downstream tooling (lane allocator, BookkeepingTransaction, merge)
        # can read the canonical ref without re-deriving it.
        "coordination_branch": getattr(result, "coordination_branch", None),
        "coordination_branch_created": getattr(result, "coordination_branch_created", False),
    }


def _emit_create_result_phase(
    result: MissionCreationResult,
    *,
    resolved_mission_type: str | None,
    json_output: bool,
) -> None:
    """Emit the create result in JSON or human form (output stays in the CLI layer)."""
    if not json_output:
        console.print(f"[bold cyan]Branch:[/bold cyan] {result.target_branch} (target for this mission)")
        if resolved_mission_type == MISSION_TYPE_DOCUMENTATION:
            console.print("[cyan]→ Documentation state initialized in meta.json[/cyan]")

    if json_output:
        _emit_json(
            _inject_branch_contract(
                _build_create_payload(result),
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
        console.print(f"[green]✓[/green] Mission created: {result.mission_slug}")
        console.print(f"   Title: {result.meta.get('friendly_name', '')}")
        console.print(f"   TLDR: {result.meta.get('purpose_tldr', '')}")
        console.print(f"   Context: {result.meta.get('purpose_context', '')}")
        console.print(f"   Directory: {result.feature_dir}")
        # Issue #846: spec.md is no longer auto-committed at create time.
        # The agent commits it from /spec-kitty.specify after writing substantive content.
        console.print(f"   Meta committed to {result.target_branch}; spec.md scaffold left untracked")
        console.print("   [yellow]Scaffold only:[/yellow] run [cyan]/spec-kitty.specify <intent>[/cyan] in your agent, or edit and commit spec.md before planning.")


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
    start_branch: Annotated[
        str | None,
        typer.Option(
            "--start-branch",
            help="Create or switch to this branch before mission files are written",
        ),
    ] = None,
    force_recreate_coordination_branch: Annotated[
        bool,
        typer.Option(
            "--force-recreate-coordination-branch",
            help=(
                "Delete and recreate the per-mission coordination branch if it "
                "already exists and has diverged from the target. Operator "
                "escape hatch; never used by automation."
            ),
        ),
    ] = False,
) -> None:
    """Create new mission directory structure in the project root checkout.

    This command is designed for AI agents to call programmatically.
    Creates mission directory in kitty-specs/ and commits to the current branch.

    Examples:
        spec-kitty agent mission create "new-dashboard" --json
    """
    # Deferred import keeps this leaf free of an import cycle while honoring the
    # ``mission.locate_project_root`` / ``mission.get_current_branch`` /
    # ``mission._switch_to_start_branch`` patch targets the tests rely on.
    from specify_cli.cli.commands.agent import mission as _mission

    repo_root = _mission.locate_project_root()

    _resolve_start_branch_phase(
        repo_root=repo_root,
        start_branch=start_branch,
        target_branch=target_branch,
        json_output=json_output,
    )

    resolved_mission_type = _resolve_mission_type_phase(
        mission_type=mission_type,
        mission=mission,
        json_output=json_output,
    )

    current_branch = _mission.get_current_branch(repo_root)
    _enforce_branch_strategy_gate_phase(
        pr_bound=pr_bound,
        current_branch=current_branch,
        target_branch=target_branch,
        branch_strategy=branch_strategy,
        start_branch=start_branch,
        json_output=json_output,
    )

    result = _run_create_core_phase(
        repo_root=repo_root,
        mission_slug=mission_slug,
        resolved_mission_type=resolved_mission_type,
        target_branch=target_branch,
        friendly_name=friendly_name,
        purpose_tldr=purpose_tldr,
        purpose_context=purpose_context,
        force_recreate_coordination_branch=force_recreate_coordination_branch,
        json_output=json_output,
    )

    _persist_pr_bound_phase(result, pr_bound=pr_bound)
    _emit_create_result_phase(
        result,
        resolved_mission_type=resolved_mission_type,
        json_output=json_output,
    )
