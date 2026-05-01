"""Machine-contract API commands for external orchestrators.

All commands emit a single JSON object to stdout via the canonical envelope.
Non-zero exit on any failure. Output is always JSON (no prose mode).

Error codes used:
  USAGE_ERROR                 -- CLI parse/usage error (missing required arg, bad option, etc.)
  POLICY_METADATA_REQUIRED    -- --policy missing on a run-affecting command
  POLICY_VALIDATION_FAILED    -- policy JSON invalid or contains secrets
  MISSION_NOT_FOUND           -- mission slug does not resolve to a kitty-specs dir
  WP_NOT_FOUND                -- WP ID does not exist in the mission
  TRANSITION_REJECTED         -- transition not allowed by state machine
  WP_ALREADY_CLAIMED          -- WP claimed by a different actor
  MISSION_NOT_READY           -- not all WPs done (for accept-mission)
  PREFLIGHT_FAILED            -- preflight checks failed (for merge-mission)
  CONTRACT_VERSION_MISMATCH   -- provider version is below MIN_PROVIDER_VERSION
  UNSUPPORTED_STRATEGY        -- merge strategy not implemented
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path
from dataclasses import dataclass

import typer

from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.git.commit_helpers import safe_commit
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.status import wp_state_for
from specify_cli.status.models import Lane

from .envelope import (
    CONTRACT_VERSION,
    MIN_PROVIDER_VERSION,
    make_envelope,
    parse_and_validate_policy,
    policy_to_dict,
)

import click
from typer.core import TyperGroup


class _JSONErrorGroup(TyperGroup):
    """Click Group that guarantees JSON envelopes for all error paths.

    The orchestrator-api contract requires *every* stdout emission to be a
    single JSON envelope, including parser-level failures (missing required
    args, unknown options, etc.).  Three overrides cooperate to cover every
    dispatch path:

    ``make_context(info_name, args, parent, **extra)``
        Catches errors during *group-level argument parsing* when nested.
        When the parent group calls ``make_context()`` on this sub-group
        (e.g. ``orchestrator-api --bogus``), the error would otherwise
        propagate to the parent's ``BannerGroup``.  This is the outermost
        catch for the nested path.

    ``invoke(ctx)``
        Catches errors during *subcommand dispatch*.  When this group is
        registered as a sub-group of the root CLI via ``add_typer()``, Click
        dispatches through ``invoke()``, not ``main()``.  Without this
        override the root ``BannerGroup`` would format the error as prose.

    ``main(*args, **kwargs)``
        Catches errors during *direct invocation* and group-level argument
        parsing (e.g. ``orchestrator-api --unknown-flag``).  Uses
        ``standalone_mode=False`` so ``click.UsageError`` propagates as an
        exception rather than being printed as plain text.

    Interaction: when both paths are active (direct invocation), a subcommand
    error is caught by ``invoke()`` first, which calls ``ctx.exit(2)``
    (raising ``SystemExit(2)``).  ``main()`` passes ``SystemExit`` through
    via ``except SystemExit: raise``, so no double emission occurs.
    """

    def _emit_error(self, message: str) -> None:
        """Emit a USAGE_ERROR JSON envelope to stdout."""
        _emit(
            make_envelope(
                command="unknown",
                success=False,
                data={"message": message},
                error_code="USAGE_ERROR",
            )
        )

    def make_context(self, info_name, args, parent=None, **extra):
        """Catch group-level parse errors when nested (e.g. orchestrator-api --bogus).

        When nested as a sub-group, the parent's invoke() calls
        make_context() on this group to parse its own arguments.  Errors
        here would propagate to the parent's BannerGroup, producing prose.
        """
        try:
            return super().make_context(info_name, args, parent=parent, **extra)
        except click.UsageError as exc:
            self._emit_error(exc.format_message())
            raise SystemExit(2) from exc

    def invoke(self, ctx):
        """Catch errors during subcommand dispatch (nested invocation path).

        When this group is registered as a sub-group of the root CLI via
        add_typer(), Click dispatches to invoke(), not main(). This override
        ensures parse/usage errors produce JSON envelopes even when the root
        CLI's BannerGroup would otherwise emit prose.
        """
        try:
            return super().invoke(ctx)
        except click.UsageError as exc:
            self._emit_error(exc.format_message())
            ctx.exit(2)
        except click.Abort:
            self._emit_error("Command aborted")
            ctx.exit(2)

    def main(self, *args, standalone_mode: bool = True, **kwargs):  # type: ignore[override]
        try:
            rv = super().main(*args, standalone_mode=False, **kwargs)
            # With standalone_mode=False, typer.Exit(code) is caught by
            # Typer's _main() and returned as an integer.  Re-raise it so
            # that CliRunner (and real invocations) see the correct exit code.
            if isinstance(rv, int) and rv != 0:
                raise SystemExit(rv)
            return rv
        except click.UsageError as exc:
            self._emit_error(exc.format_message())
            raise SystemExit(2) from exc
        except click.Abort:
            self._emit_error("Command aborted")
            raise SystemExit(2)
        except SystemExit:
            raise


# The public ``app`` used by the main CLI to register orchestrator-api.
# Uses _JSONErrorGroup so that Click/Typer parse errors become JSON envelopes.
app = typer.Typer(
    name="orchestrator-api",
    help="Machine-contract API for external orchestrators (JSON-first)",
    no_args_is_help=False,
    cls=_JSONErrorGroup,
)

# Boy Scout (DIRECTIVE_025): deduplicated CLI help strings.
_HELP_MISSION_SLUG = "Mission slug"
_HELP_WP_ID = "Work package ID"
_HELP_ACTOR = "Actor identity"
_HELP_POLICY = "Policy metadata JSON (required)"


def _is_run_affecting(lane: str) -> bool:
    """Return True if transitioning to *lane* requires --policy metadata.

    A lane is run-affecting when its WPState is neither terminal, blocked,
    nor not-yet-started.  This replaces the former ``_RUN_AFFECTING_LANES``
    frozenset with a state-object query.
    """
    state = wp_state_for(lane)
    return state.progress_bucket() not in ("not_started", "terminal") and not state.is_blocked


@dataclass
class _MergePreflightResult:
    target_branch: str
    errors: list[str]


def _emit(envelope: dict) -> None:
    """Print canonical JSON envelope to stdout."""
    print(json.dumps(envelope))


def _fail(command: str, error_code: str, message: str, data: dict | None = None) -> None:
    """Print failure envelope and exit non-zero."""
    envelope = make_envelope(
        command=command,
        success=False,
        data=data or {"message": message},
        error_code=error_code,
    )
    _emit(envelope)
    raise typer.Exit(1)


def _get_main_repo_root() -> Path:
    """Resolve main repository root from current working directory."""
    from specify_cli.core.paths import get_main_repo_root, locate_project_root

    cwd = Path.cwd()
    root = locate_project_root(cwd)
    if root is None:
        # Fall back to canonical resolver for worktree-aware behavior.
        return get_main_repo_root(cwd)
    return root


def _resolve_mission_dir(main_repo_root: Path, mission_slug: str) -> Path | None:
    """Return the mission directory if it exists, else None."""
    mission_dir = main_repo_root / "kitty-specs" / mission_slug
    if not mission_dir.exists():
        return None
    return mission_dir


def _mission_identity_payload(mission_dir: Path) -> dict[str, str]:
    """Return canonical mission identity fields for machine-facing payloads."""
    identity = resolve_mission_identity(mission_dir)
    return {
        "mission_slug": identity.mission_slug,
        "mission_number": identity.mission_number,
        "mission_type": identity.mission_type,
    }


def _get_last_actor(mission_dir: Path, wp_id: str) -> str | None:
    """Get the actor of the most recent event for this WP."""
    from specify_cli.status.store import read_events

    events = read_events(mission_dir)
    for event in reversed(events):
        if event.wp_id == wp_id:
            return event.actor
    return None


_WP_ID_RE = re.compile(r"^(WP\d+)")


def _extract_wp_id(stem: str) -> str | None:
    """Extract canonical WP ID from a task filename stem.

    Examples:
        "WP07"                         -> "WP07"
        "WP07-adapter-implementations" -> "WP07"
        "README"                       -> None
    """
    m = _WP_ID_RE.match(stem)
    return m.group(1) if m else None


def _resolve_wp_file(tasks_dir: Path, wp_id: str) -> Path | None:
    """Locate the task file for a WP, accepting suffixed filenames.

    Checks for an exact match first (WP07.md), then falls back to any
    file whose name starts with '<wp_id>-' (e.g. WP07-adapter-implementations.md).
    Returns the first match found, or None if no file exists.
    """
    exact = tasks_dir / f"{wp_id}.md"
    if exact.exists():
        return exact
    for p in sorted(tasks_dir.glob(f"{wp_id}-*.md")):
        return p
    return None


def _resolve_merge_target_branch(main_repo_root: Path, mission_slug: str, target: str | None) -> str:
    if target is not None:
        return target

    from specify_cli.core.paths import get_feature_target_branch

    return get_feature_target_branch(main_repo_root, mission_slug)


def _build_merge_preflight(
    main_repo_root: Path,
    mission_dir: Path,
    mission_slug: str,
    target: str | None,
) -> _MergePreflightResult:
    """Validate merge prerequisites and collect machine-readable errors."""
    from specify_cli.core.git_preflight import build_git_preflight_failure_payload, run_git_preflight
    from specify_cli.core.git_ops import run_command
    from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json

    resolved_target = _resolve_merge_target_branch(main_repo_root, mission_slug, target)
    errors: list[str] = []

    if (main_repo_root / ".git").exists():
        preflight = run_git_preflight(main_repo_root, check_worktree_list=True)
        if not preflight.passed:
            payload = build_git_preflight_failure_payload(preflight, command_name="orchestrator-api merge-mission")
            errors.append(payload["error"])
            errors.extend(payload.get("remediation", []))

        ret_local, _, _ = run_command(
            ["git", "rev-parse", "--verify", f"refs/heads/{resolved_target}"],
            capture=True,
            check_return=False,
            cwd=main_repo_root,
        )
        ret_remote, _, _ = run_command(
            ["git", "rev-parse", "--verify", f"refs/remotes/origin/{resolved_target}"],
            capture=True,
            check_return=False,
            cwd=main_repo_root,
        )
        if ret_local != 0 and ret_remote != 0:
            errors.append(f"Target branch '{resolved_target}' does not exist locally or on origin.")

    try:
        require_lanes_json(mission_dir)
    except (MissingLanesError, CorruptLanesError) as exc:
        errors.append(str(exc))

    return _MergePreflightResult(target_branch=resolved_target, errors=errors)


def _execute_lane_merge(
    main_repo_root: Path,
    mission_dir: Path,
    mission_slug: str,
    target_branch: str,
    *,
    push: bool,
    delete_branch: bool,
    remove_worktree: bool,
) -> None:
    """Execute the lane-based merge flow without emitting console prose."""
    from specify_cli.cli.commands.merge import _mark_wp_merged_done
    from specify_cli.core.git_ops import has_remote, run_command
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.compute import PLANNING_LANE_ID
    from specify_cli.lanes.merge import merge_lane_to_mission, merge_mission_to_target
    from specify_cli.lanes.persistence import require_lanes_json
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    lanes_manifest = require_lanes_json(mission_dir)
    lanes_manifest.target_branch = target_branch

    policy = load_policy_config(main_repo_root)
    all_wp_ids = [wp for lane in lanes_manifest.lanes for wp in lane.wp_ids]
    gate_eval = evaluate_merge_gates(
        mission_dir,
        mission_slug,
        all_wp_ids,
        policy.merge_gates,
        main_repo_root,
    )
    if not gate_eval.overall_pass:
        blocking = [gate.details for gate in gate_eval.gates if gate.blocking]
        raise RuntimeError("; ".join(blocking) or "Merge gates failed.")

    for lane in lanes_manifest.lanes:
        lane_result = merge_lane_to_mission(main_repo_root, mission_slug, lane.lane_id, lanes_manifest)
        if not lane_result.success:
            raise RuntimeError("; ".join(lane_result.errors) or f"Lane {lane.lane_id} merge failed.")

    mission_result = merge_mission_to_target(main_repo_root, mission_slug, lanes_manifest)
    if not mission_result.success:
        raise RuntimeError("; ".join(mission_result.errors) or "Mission merge failed.")

    for lane in lanes_manifest.lanes:
        for wp_id in lane.wp_ids:
            _mark_wp_merged_done(main_repo_root, mission_slug, wp_id, lanes_manifest.target_branch)

    if push and has_remote(main_repo_root):
        run_command(["git", "push", "origin", lanes_manifest.target_branch], cwd=main_repo_root)

    if remove_worktree:
        for lane in lanes_manifest.lanes:
            wt_path = main_repo_root / ".worktrees" / f"{mission_slug}-{lane.lane_id}"
            if wt_path.exists():
                run_command(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=main_repo_root,
                    check_return=False,
                )

    if delete_branch:
        for lane in lanes_manifest.lanes:
            if lane.lane_id == PLANNING_LANE_ID:
                continue
            run_command(
                [
                    "git",
                    "branch",
                    "-D",
                    lane_branch_name(
                        mission_slug,
                        lane.lane_id,
                        planning_base_branch=lanes_manifest.target_branch,
                    ),
                ],
                cwd=main_repo_root,
                check_return=False,
            )
        run_command(
            ["git", "branch", "-D", lanes_manifest.mission_branch],
            cwd=main_repo_root,
            check_return=False,
        )


# ── Command 1: contract-version ────────────────────────────────────────────


@app.command(name="contract-version")
def contract_version(
    provider_version: str = typer.Option(
        None,
        "--provider-version",
        help="Caller's provider version; returns CONTRACT_VERSION_MISMATCH if below minimum",
    ),
) -> None:
    """Return the current API contract version.

    Pass --provider-version to check compatibility before running state-mutating commands.
    """
    cmd = "contract-version"

    if provider_version is not None:
        from packaging.version import Version, InvalidVersion

        try:
            if Version(provider_version) < Version(MIN_PROVIDER_VERSION):
                _fail(
                    cmd,
                    "CONTRACT_VERSION_MISMATCH",
                    f"Provider version {provider_version!r} is below minimum {MIN_PROVIDER_VERSION!r}",
                    {
                        "provider_version": provider_version,
                        "min_supported_provider_version": MIN_PROVIDER_VERSION,
                        "api_version": CONTRACT_VERSION,
                    },
                )
                return
        except InvalidVersion:
            _fail(
                cmd,
                "CONTRACT_VERSION_MISMATCH",
                f"Provider version {provider_version!r} is not a valid version string",
                {"provider_version": provider_version},
            )
            return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "api_version": CONTRACT_VERSION,
            "min_supported_provider_version": MIN_PROVIDER_VERSION,
        },
    )
    _emit(envelope)


# ── Command 2: mission-state ────────────────────────────────────────────────


@app.command(name="mission-state")
def mission_state(
    mission: str = typer.Option(
        ...,
        "--mission",
        help=_HELP_MISSION_SLUG,
    ),
) -> None:
    """Return the full state of a mission (all WPs, lanes, dependencies)."""
    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(
            "mission-state",
            "MISSION_NOT_FOUND",
            f"Mission '{mission}' not found in kitty-specs/",
        )
        return

    from specify_cli.status.reducer import reduce
    from specify_cli.status.store import read_events
    from specify_cli.core.dependency_graph import build_dependency_graph

    # Query endpoint: reduce from event log without rewriting status.json.
    snapshot = reduce(read_events(mission_dir))
    dep_graph = build_dependency_graph(mission_dir)

    # Build the full WP set from task files + dep graph + snapshot
    # so that untouched WPs (no events yet) still appear as "planned"
    tasks_dir = mission_dir / "tasks"
    task_file_wp_ids: set[str] = set()
    if tasks_dir.exists():
        for p in tasks_dir.iterdir():
            if p.suffix == ".md":
                wp_id = _extract_wp_id(p.stem)
                if wp_id is not None:
                    task_file_wp_ids.add(wp_id)

    all_wp_ids = task_file_wp_ids | set(dep_graph.keys()) | set(snapshot.work_packages.keys())

    work_packages = []
    for wp_id in sorted(all_wp_ids):
        wp_snapshot = snapshot.work_packages.get(wp_id, {})
        work_packages.append(
            {
                "wp_id": wp_id,
                "lane": wp_snapshot.get("lane", Lane.PLANNED),
                "dependencies": dep_graph.get(wp_id, []),
                "last_actor": wp_snapshot.get("last_actor"),
            }
        )

    data = {
        **_mission_identity_payload(mission_dir),
        "summary": snapshot.summary,
        "work_packages": work_packages,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command="mission-state",
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 3: list-ready ──────────────────────────────────────────────────


@app.command(name="list-ready")
def list_ready(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
) -> None:
    """List WPs that are ready to start (planned and all deps done)."""
    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(
            "list-ready",
            "MISSION_NOT_FOUND",
            f"Mission '{mission}' not found in kitty-specs/",
        )
        return

    from specify_cli.status.reducer import reduce
    from specify_cli.status.store import read_events
    from specify_cli.core.dependency_graph import build_dependency_graph

    # Query endpoint: reduce from event log without rewriting status.json.
    snapshot = reduce(read_events(mission_dir))
    dep_graph = build_dependency_graph(mission_dir)
    wp_states = snapshot.work_packages

    ready_wps = []
    for wp_id, deps in dep_graph.items():
        wp_snapshot = wp_states.get(wp_id, {})
        lane = wp_snapshot.get("lane", Lane.PLANNED)
        state = wp_state_for(lane)
        if state.progress_bucket() != "not_started":
            continue

        # Check all dependencies are done (completed, not merely terminal —
        # canceled deps do NOT satisfy the dependency requirement).
        all_deps_done = all(
            wp_state_for(wp_states.get(dep, {}).get("lane", Lane.PLANNED)).lane == Lane.DONE
            for dep in deps
        )

        ready_wps.append(
            {
                "wp_id": wp_id,
                "lane": lane,
                "dependencies_satisfied": all_deps_done,
            }
        )

    # Filter to only truly ready ones
    ready_wps = [wp for wp in ready_wps if wp["dependencies_satisfied"]]

    data = {
        **_mission_identity_payload(mission_dir),
        "ready_work_packages": ready_wps,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command="list-ready",
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 4: start-implementation ────────────────────────────────────────


@app.command(name="start-implementation")
def start_implementation(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    wp: str = typer.Option(..., "--wp", help=_HELP_WP_ID),
    actor: str = typer.Option(..., "--actor", help=_HELP_ACTOR),
    policy: str = typer.Option(None, "--policy", help=_HELP_POLICY),
) -> None:
    """Composite transition: planned->claimed->in_progress (idempotent)."""
    cmd = "start-implementation"

    # Policy required
    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for start-implementation")
        return

    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
        return

    policy_dict = policy_to_dict(policy_obj)

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError
    from specify_cli.status.models import TransitionRequest

    snapshot = materialize(mission_dir)
    wp_snapshot = snapshot.work_packages.get(wp, {})
    current_lane = wp_snapshot.get("lane", Lane.PLANNED)
    state = wp_state_for(current_lane)
    last_actor = _get_last_actor(mission_dir, wp)

    workspace_path = str(main_repo_root / ".worktrees" / f"{mission}-{wp}")
    prompt_path = str(wp_path)

    try:
        if state.lane == Lane.PLANNED:
            # Composite: planned -> claimed -> in_progress
            emit_status_transition(TransitionRequest(
                feature_dir=mission_dir,
                mission_slug=mission,
                wp_id=wp,
                to_lane=Lane.CLAIMED,
                actor=actor,
                policy_metadata=policy_dict,
            ))
            emit_status_transition(TransitionRequest(
                feature_dir=mission_dir,
                mission_slug=mission,
                wp_id=wp,
                to_lane=Lane.IN_PROGRESS,
                actor=actor,
                workspace_context=workspace_path,
                execution_mode="worktree",
                policy_metadata=policy_dict,
            ))
            from_lane_reported = Lane.PLANNED
            no_op = False

        elif state.lane == Lane.CLAIMED:
            if last_actor is not None and last_actor != actor:
                _fail(
                    cmd,
                    "WP_ALREADY_CLAIMED",
                    f"WP {wp} is already claimed by '{last_actor}'",
                    {
                        **_mission_identity_payload(mission_dir),
                        "claimed_by": last_actor,
                        "requesting_actor": actor,
                    },
                )
                return
            emit_status_transition(TransitionRequest(
                feature_dir=mission_dir,
                mission_slug=mission,
                wp_id=wp,
                to_lane=Lane.IN_PROGRESS,
                actor=actor,
                workspace_context=workspace_path,
                execution_mode="worktree",
                policy_metadata=policy_dict,
            ))
            from_lane_reported = Lane.CLAIMED
            no_op = False

        elif state.lane == Lane.IN_PROGRESS:
            if last_actor is not None and last_actor != actor:
                _fail(
                    cmd,
                    "WP_ALREADY_CLAIMED",
                    f"WP {wp} is already in_progress by '{last_actor}'",
                    {
                        **_mission_identity_payload(mission_dir),
                        "claimed_by": last_actor,
                        "requesting_actor": actor,
                    },
                )
                return
            # Idempotent success
            from_lane_reported = Lane.IN_PROGRESS
            no_op = True

        else:
            _fail(
                cmd,
                "TRANSITION_REJECTED",
                f"WP {wp} is in '{current_lane}', cannot start implementation",
            )
            return

    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    data = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "from_lane": from_lane_reported,
        "to_lane": Lane.IN_PROGRESS,
        "workspace_path": workspace_path,
        "prompt_path": prompt_path,
        "policy_metadata_recorded": True,
        "no_op": no_op,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command=cmd,
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 5: start-review ────────────────────────────────────────────────


@app.command(name="start-review")
def start_review(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    wp: str = typer.Option(..., "--wp", help=_HELP_WP_ID),
    actor: str = typer.Option(..., "--actor", help=_HELP_ACTOR),
    policy: str = typer.Option(None, "--policy", help=_HELP_POLICY),
    review_ref: str = typer.Option(None, "--review-ref", help="Review feedback reference (optional, not required for for_review→in_review)"),
) -> None:
    """Transition a WP from for_review to in_review (reviewer claims review)."""
    cmd = "start-review"

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for start-review")
        return

    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
        return

    policy_dict = policy_to_dict(policy_obj)

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError
    from specify_cli.status.models import TransitionRequest

    snapshot = materialize(mission_dir)
    wp_snapshot = snapshot.work_packages.get(wp, {})
    from_lane = wp_snapshot.get("lane", Lane.PLANNED)

    prompt_path = str(wp_path)

    try:
        emit_status_transition(TransitionRequest(
            feature_dir=mission_dir,
            mission_slug=mission,
            wp_id=wp,
            to_lane=Lane.IN_REVIEW,
            actor=actor,
            review_ref=review_ref,
            execution_mode="worktree",
            policy_metadata=policy_dict,
        ))
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    data = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "from_lane": from_lane,
        "to_lane": Lane.IN_REVIEW,
        "prompt_path": prompt_path,
        "policy_metadata_recorded": True,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command=cmd,
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 6: transition ──────────────────────────────────────────────────


@app.command(name="transition")
def transition(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    wp: str = typer.Option(..., "--wp", help=_HELP_WP_ID),
    to: str = typer.Option(..., "--to", help="Target lane"),
    actor: str = typer.Option(..., "--actor", help=_HELP_ACTOR),
    note: str = typer.Option(None, "--note", help="Reason/note for the transition"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required for run-affecting lanes)"),
    force: bool = typer.Option(False, "--force", help="Force the transition"),
    review_ref: str = typer.Option(None, "--review-ref", help="Review reference"),
    evidence_json: str = typer.Option(None, "--evidence-json", help="JSON string with done evidence"),
    subtasks_complete: bool = typer.Option(None, "--subtasks-complete", help="Whether required subtasks are complete for in_progress->for_review"),
    implementation_evidence_present: bool = typer.Option(
        None, "--implementation-evidence-present", help="Whether implementation evidence exists for in_progress->for_review"
    ),
) -> None:
    """Emit a single lane transition for a WP."""
    cmd = "transition"

    from specify_cli.status.transitions import resolve_lane_alias

    to_lane = resolve_lane_alias(to)

    # Policy required for run-affecting lanes
    policy_dict: dict | None = None
    if _is_run_affecting(to_lane):
        if not policy:
            _fail(
                cmd,
                "POLICY_METADATA_REQUIRED",
                f"--policy is required when transitioning to '{to_lane}'",
            )
            return
        try:
            policy_obj = parse_and_validate_policy(policy)
            policy_dict = policy_to_dict(policy_obj)
        except ValueError as exc:
            _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
            return
    elif policy:
        # Optional policy for non-run-affecting lanes
        try:
            policy_obj = parse_and_validate_policy(policy)
            policy_dict = policy_to_dict(policy_obj)
        except ValueError as exc:
            _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
            return

    evidence: dict | None = None
    if evidence_json is not None:
        try:
            parsed_evidence = json.loads(evidence_json)
        except json.JSONDecodeError as exc:
            _fail(cmd, "USAGE_ERROR", f"Invalid JSON in --evidence-json: {exc}")
            return
        if not isinstance(parsed_evidence, dict):
            _fail(cmd, "USAGE_ERROR", "--evidence-json must decode to a JSON object")
            return
        evidence = parsed_evidence

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError
    from specify_cli.status.models import TransitionRequest

    snapshot = materialize(mission_dir)
    wp_snapshot = snapshot.work_packages.get(wp, {})
    from_lane = wp_snapshot.get("lane", Lane.PLANNED)

    try:
        emit_status_transition(TransitionRequest(
            feature_dir=mission_dir,
            mission_slug=mission,
            wp_id=wp,
            to_lane=to_lane,
            actor=actor,
            reason=note,
            force=force,
            evidence=evidence,
            review_ref=review_ref,
            subtasks_complete=subtasks_complete,
            implementation_evidence_present=implementation_evidence_present,
            execution_mode="worktree",
            policy_metadata=policy_dict,
        ))
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    data = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "policy_metadata_recorded": policy_dict is not None,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command=cmd,
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 7: append-history ──────────────────────────────────────────────


@app.command(name="append-history")
def append_history(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    wp: str = typer.Option(..., "--wp", help=_HELP_WP_ID),
    actor: str = typer.Option(..., "--actor", help=_HELP_ACTOR),
    note: str = typer.Option(..., "--note", help="History note to append"),
) -> None:
    """Append a history entry to a WP prompt file."""
    cmd = "append-history"

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission}")
        return

    from specify_cli.task_utils import (
        split_frontmatter,
        build_document,
        append_activity_log,
    )

    raw = wp_path.read_text(encoding="utf-8")
    fm, body, padding = split_frontmatter(raw)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry_text = f"- [{timestamp}] {actor}: {note}"
    new_body = append_activity_log(body, entry_text)

    wp_path.write_text(build_document(fm, new_body, padding), encoding="utf-8")

    safe_commit(
        repo_path=main_repo_root,
        files_to_commit=[wp_path],
        commit_message=f"hist: append activity log entry for {mission}/{wp}",
        allow_empty=True,
    )

    entry_id = "hist-" + uuid.uuid4().hex

    data = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "history_entry_id": entry_id,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command=cmd,
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 8: accept-mission ──────────────────────────────────────────────


@app.command(name="accept-mission")
def accept_mission(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    actor: str = typer.Option(..., "--actor", help=_HELP_ACTOR),
) -> None:
    """Accept a mission after all WPs are done."""
    cmd = "accept-mission"

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission}' not found in kitty-specs/")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.core.dependency_graph import build_dependency_graph

    snapshot = materialize(mission_dir)
    dep_graph = build_dependency_graph(mission_dir)

    # Check all WPs (from dep_graph) are done — include WPs with no events (implicitly planned)
    all_wp_ids = set(dep_graph.keys()) | set(snapshot.work_packages.keys())
    incomplete = [wp_id for wp_id in sorted(all_wp_ids) if wp_state_for(snapshot.work_packages.get(wp_id, {}).get("lane", Lane.PLANNED)).lane != Lane.DONE]
    if incomplete:
        _fail(
            cmd,
            "MISSION_NOT_READY",
            f"Mission has {len(incomplete)} incomplete WP(s)",
            {
                **_mission_identity_payload(mission_dir),
                "incomplete_wps": sorted(incomplete),
            },
        )
        return

    # Write acceptance record via centralized metadata writer
    from specify_cli.mission_metadata import record_acceptance

    accepted_at = datetime.now(UTC).isoformat()
    record_acceptance(
        mission_dir,
        accepted_by=actor,
        mode="orchestrator",
    )

    data = {
        **_mission_identity_payload(mission_dir),
        "accepted": True,
        "mode": "auto",
        "accepted_at": accepted_at,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command=cmd,
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 9: merge-mission ───────────────────────────────────────────────


@app.command(name="merge-mission")
def merge_mission(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    target: str = typer.Option(None, "--target", help="Target branch to merge into (auto-detected from meta.json)"),
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    push: bool = typer.Option(False, "--push", help="Push target branch after merge"),
) -> None:
    """Merge a lane-based mission into target."""
    cmd = "merge-mission"

    _SUPPORTED_STRATEGIES = frozenset(["merge", "squash", "rebase"])
    if strategy not in _SUPPORTED_STRATEGIES:
        _fail(
            cmd,
            "UNSUPPORTED_STRATEGY",
            f"Strategy '{strategy}' is not supported. Supported strategies: {sorted(_SUPPORTED_STRATEGIES)}",
            {"strategy": strategy, "supported": sorted(_SUPPORTED_STRATEGIES)},
        )
        return

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission}' not found in kitty-specs/")
        return

    preflight = _build_merge_preflight(main_repo_root, mission_dir, mission, target)
    if preflight.errors:
        _fail(
            cmd,
            "PREFLIGHT_FAILED",
            "Merge failed",
            {
                **_mission_identity_payload(mission_dir),
                "target_branch": preflight.target_branch,
                "errors": preflight.errors,
            },
        )
        return

    try:
        _execute_lane_merge(
            main_repo_root,
            mission_dir,
            mission,
            preflight.target_branch,
            push=push,
            delete_branch=True,
            remove_worktree=True,
        )
    except RuntimeError as exc:
        _fail(
            cmd,
            "PREFLIGHT_FAILED",
            "Merge failed",
            {
                **_mission_identity_payload(mission_dir),
                "target_branch": preflight.target_branch,
                "errors": [str(exc)],
            },
        )
        return

    data = {
        **_mission_identity_payload(mission_dir),
        "merged": True,
        "target_branch": preflight.target_branch,
        "strategy": strategy,
        "worktree_removed": False,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command=cmd,
        success=True,
        data=data,
    )
    _emit(envelope)


__all__ = ["app"]
