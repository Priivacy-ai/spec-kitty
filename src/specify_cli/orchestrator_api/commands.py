"""Machine-contract API commands for external orchestrators.

All commands emit a single JSON object to stdout via the canonical envelope.
Non-zero exit on any failure. Output is always JSON (no prose mode).

Error codes used:
  USAGE_ERROR                 -- CLI parse/usage error (missing required arg, bad option, etc.)
  POLICY_METADATA_REQUIRED    -- --policy missing on a run-affecting command
  POLICY_VALIDATION_FAILED    -- policy JSON invalid or contains secrets
  MISSION_NOT_FOUND           -- mission slug does not resolve to a kitty-specs dir
  WP_NOT_FOUND                -- WP ID does not exist in mission
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
import subprocess
import uuid
from datetime import datetime, UTC
from pathlib import Path

import typer

from specify_cli.git.commit_helpers import safe_commit
from specify_cli.merge import run_preflight, get_merge_order

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
    no_args_is_help=True,
    cls=_JSONErrorGroup,
)

# Lanes that require --policy (run-affecting)
_RUN_AFFECTING_LANES = frozenset(["claimed", "in_progress", "for_review"])


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


def _get_last_actor(mission_dir: Path, wp_id: str) -> str | None:
    """Get the actor of the most recent event for this WP."""
    from specify_cli.status.store import read_events

    events = read_events(mission_dir)
    for event in reversed(events):
        if event.wp_id == wp_id:
            return event.actor.tool
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
    mission: str | None = typer.Option(None, "--mission", help="Mission slug (e.g. 034-my-mission)"),
) -> None:
    """Return the full state of a mission (all WPs, lanes, dependencies)."""
    mission_slug = mission
    if not mission_slug:
        _fail("mission-state", "USAGE_ERROR", "--mission is required")
        return
    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(
            "mission-state",
            "MISSION_NOT_FOUND",
            f"Mission '{mission_slug}' not found in kitty-specs/",
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
        wp_state = snapshot.work_packages.get(wp_id, {})
        work_packages.append(
            {
                "wp_id": wp_id,
                "lane": wp_state.get("lane", "planned"),
                "dependencies": dep_graph.get(wp_id, []),
                "last_actor": wp_state.get("last_actor"),
            }
        )

    envelope = make_envelope(
        command="mission-state",
        success=True,
        data={
            "mission_slug": mission_slug,
            "summary": snapshot.summary,
            "work_packages": work_packages,
        },
    )
    _emit(envelope)


# ── Command 3: list-ready ──────────────────────────────────────────────────


@app.command(name="list-ready")
def list_ready(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug"),
) -> None:
    """List WPs that are ready to start (planned and all deps done)."""
    mission_slug = mission
    if not mission_slug:
        _fail("list-ready", "USAGE_ERROR", "--mission is required")
        return
    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(
            "list-ready",
            "MISSION_NOT_FOUND",
            f"Mission '{mission_slug}' not found in kitty-specs/",
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
        wp_state = wp_states.get(wp_id, {})
        lane = wp_state.get("lane", "planned")
        if lane != "planned":
            continue

        # Check all dependencies are done
        all_deps_done = all(wp_states.get(dep, {}).get("lane") == "done" for dep in deps)

        recommended_base = deps[-1] if deps else None

        ready_wps.append(
            {
                "wp_id": wp_id,
                "lane": lane,
                "dependencies_satisfied": all_deps_done,
                "recommended_base": recommended_base,
            }
        )

    # Filter to only truly ready ones
    ready_wps = [wp for wp in ready_wps if wp["dependencies_satisfied"]]

    envelope = make_envelope(
        command="list-ready",
        success=True,
        data={
            "mission_slug": mission_slug,
            "ready_work_packages": ready_wps,
        },
    )
    _emit(envelope)


# ── Command 4: start-implementation ────────────────────────────────────────


@app.command(name="start-implementation")
def start_implementation(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID (e.g. WP01)"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required)"),
) -> None:
    """Composite transition: planned→claimed→in_progress (idempotent)."""
    cmd = "start-implementation"
    mission_slug = mission
    if not mission_slug:
        _fail(cmd, "USAGE_ERROR", "--mission is required")
        return

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
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission_slug}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission_slug}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError

    snapshot = materialize(mission_dir)
    wp_state = snapshot.work_packages.get(wp, {})
    current_lane = wp_state.get("lane", "planned")
    last_actor = _get_last_actor(mission_dir, wp)

    workspace_path = str(main_repo_root / ".worktrees" / f"{mission_slug}-{wp}")
    prompt_path = str(wp_path)

    try:
        if current_lane == "planned":
            # Composite: planned → claimed → in_progress
            emit_status_transition(
                mission_dir,
                mission_slug,
                wp,
                "claimed",
                actor,
                policy_metadata=policy_dict,
            )
            emit_status_transition(
                mission_dir,
                mission_slug,
                wp,
                "in_progress",
                actor,
                workspace_context=workspace_path,
                execution_mode="worktree",
                policy_metadata=policy_dict,
            )
            from_lane_reported = "planned"
            no_op = False

        elif current_lane == "claimed":
            if last_actor is not None and last_actor != actor:
                _fail(
                    cmd,
                    "WP_ALREADY_CLAIMED",
                    f"WP {wp} is already claimed by '{last_actor}'",
                    {"claimed_by": last_actor, "requesting_actor": actor},
                )
                return
            emit_status_transition(
                mission_dir,
                mission_slug,
                wp,
                "in_progress",
                actor,
                workspace_context=workspace_path,
                execution_mode="worktree",
                policy_metadata=policy_dict,
            )
            from_lane_reported = "claimed"
            no_op = False

        elif current_lane == "in_progress":
            if last_actor is not None and last_actor != actor:
                _fail(
                    cmd,
                    "WP_ALREADY_CLAIMED",
                    f"WP {wp} is already in_progress by '{last_actor}'",
                    {"claimed_by": last_actor, "requesting_actor": actor},
                )
                return
            # Idempotent success
            from_lane_reported = "in_progress"
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

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "mission_slug": mission_slug,
            "wp_id": wp,
            "from_lane": from_lane_reported,
            "to_lane": "in_progress",
            "workspace_path": workspace_path,
            "prompt_path": prompt_path,
            "policy_metadata_recorded": True,
            "no_op": no_op,
        },
    )
    _emit(envelope)


# ── Command 5: start-review ────────────────────────────────────────────────


@app.command(name="start-review")
def start_review(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required)"),
    review_ref: str = typer.Option(None, "--review-ref", help="Review feedback reference (required)"),
) -> None:
    """Transition a WP from for_review back to in_progress (reviewer rollback)."""
    cmd = "start-review"
    mission_slug = mission
    if not mission_slug:
        _fail(cmd, "USAGE_ERROR", "--mission is required")
        return

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for start-review")
        return

    if not review_ref:
        _fail(cmd, "TRANSITION_REJECTED", "--review-ref is required for start-review (for_review→in_progress guard)")
        return

    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
        return

    policy_dict = policy_to_dict(policy_obj)

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission_slug}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission_slug}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError

    snapshot = materialize(mission_dir)
    wp_state = snapshot.work_packages.get(wp, {})
    from_lane = wp_state.get("lane", "planned")

    prompt_path = str(wp_path)

    try:
        emit_status_transition(
            mission_dir,
            mission_slug,
            wp,
            "in_progress",
            actor,
            review_ref=review_ref,
            execution_mode="worktree",
            policy_metadata=policy_dict,
        )
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "mission_slug": mission_slug,
            "wp_id": wp,
            "from_lane": from_lane,
            "to_lane": "in_progress",
            "prompt_path": prompt_path,
            "policy_metadata_recorded": True,
        },
    )
    _emit(envelope)


# ── Command 6: transition ──────────────────────────────────────────────────


@app.command(name="transition")
def transition(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID"),
    to: str = typer.Option(..., "--to", help="Target lane"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    note: str = typer.Option(None, "--note", help="Reason/note for the transition"),
    policy: str = typer.Option(None, "--policy", help="Policy metadata JSON (required for run-affecting lanes)"),
    force: bool = typer.Option(False, "--force", help="Force the transition"),
    review_ref: str = typer.Option(None, "--review-ref", help="Review reference"),
) -> None:
    """Emit a single lane transition for a WP."""
    cmd = "transition"
    mission_slug = mission
    if not mission_slug:
        _fail(cmd, "USAGE_ERROR", "--mission is required")
        return

    from specify_cli.status.transitions import resolve_lane_alias

    to_lane = resolve_lane_alias(to)

    # Policy required for run-affecting lanes
    policy_dict: dict | None = None
    if to_lane in _RUN_AFFECTING_LANES:
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

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission_slug}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission_slug}")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.status.emit import emit_status_transition, TransitionError

    snapshot = materialize(mission_dir)
    wp_state = snapshot.work_packages.get(wp, {})
    from_lane = wp_state.get("lane", "planned")

    try:
        emit_status_transition(
            mission_dir,
            mission_slug,
            wp,
            to_lane,
            actor,
            reason=note,
            force=force,
            review_ref=review_ref,
            execution_mode="worktree",
            policy_metadata=policy_dict,
        )
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "mission_slug": mission_slug,
            "wp_id": wp,
            "from_lane": from_lane,
            "to_lane": to_lane,
            "policy_metadata_recorded": policy_dict is not None,
        },
    )
    _emit(envelope)


# ── Command 7: append-history ──────────────────────────────────────────────


@app.command(name="append-history")
def append_history(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug"),
    wp: str = typer.Option(..., "--wp", help="Work package ID"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    note: str = typer.Option(..., "--note", help="History note to append"),
) -> None:
    """Append a history entry to a WP prompt file."""
    cmd = "append-history"
    mission_slug = mission
    if not mission_slug:
        _fail(cmd, "USAGE_ERROR", "--mission is required")
        return

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission_slug}' not found in kitty-specs/")
        return

    wp_path = _resolve_wp_file(mission_dir / "tasks", wp)
    if wp_path is None:
        _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission_slug}")
        return

    from specify_cli.tasks_support import (
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
        commit_message=f"hist: append activity log entry for {mission_slug}/{wp}",
        allow_empty=True,
    )

    entry_id = "hist-" + uuid.uuid4().hex

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "mission_slug": mission_slug,
            "wp_id": wp,
            "history_entry_id": entry_id,
        },
    )
    _emit(envelope)


# ── Command 8: accept-mission ──────────────────────────────────────────────


@app.command(name="accept-mission")
def accept_mission(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
) -> None:
    """Accept a mission after all WPs are done."""
    cmd = "accept-mission"
    mission_slug = mission
    if not mission_slug:
        _fail(cmd, "USAGE_ERROR", "--mission is required")
        return

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission_slug}' not found in kitty-specs/")
        return

    from specify_cli.status.reducer import materialize
    from specify_cli.core.dependency_graph import build_dependency_graph

    snapshot = materialize(mission_dir)
    dep_graph = build_dependency_graph(mission_dir)

    # Check all WPs (from dep_graph) are done — include WPs with no events (implicitly planned)
    all_wp_ids = set(dep_graph.keys()) | set(snapshot.work_packages.keys())
    incomplete = [wp_id for wp_id in sorted(all_wp_ids) if snapshot.work_packages.get(wp_id, {}).get("lane") != "done"]
    if incomplete:
        _fail(
            cmd,
            "MISSION_NOT_READY",
            f"Mission has {len(incomplete)} incomplete WP(s)",
            {"incomplete_wps": sorted(incomplete)},
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

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "mission_slug": mission_slug,
            "accepted": True,
            "mode": "auto",
            "accepted_at": accepted_at,
        },
    )
    _emit(envelope)


# ── Command 9: merge-mission ───────────────────────────────────────────────


@app.command(name="merge-mission")
def merge_mission(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug"),
    target: str = typer.Option(None, "--target", help="Target branch to merge into (auto-detected from meta.json)"),
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    push: bool = typer.Option(False, "--push", help="Push target branch after merge"),
) -> None:
    """Run preflight checks then merge all WP branches into target."""
    cmd = "merge-mission"
    mission_slug = mission
    if not mission_slug:
        _fail(cmd, "USAGE_ERROR", "--mission is required")
        return

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
    mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    if mission_dir is None:
        _fail(cmd, "MISSION_NOT_FOUND", f"Mission '{mission_slug}' not found in kitty-specs/")
        return

    # Auto-detect target branch from meta.json if not specified
    if target is None:
        from specify_cli.core.mission_detection import get_mission_target_branch

        target = get_mission_target_branch(main_repo_root, mission_slug)

    # Discover worktrees for this mission
    worktrees_root = main_repo_root / ".worktrees"
    wp_workspaces: list[tuple[Path, str, str]] = []
    if worktrees_root.exists():
        for wt_path in sorted(worktrees_root.iterdir()):
            if wt_path.name.startswith(f"{mission_slug}-") and wt_path.is_dir():
                # Extract WP ID from directory name: e.g. "034-mission-WP01" → "WP01"
                suffix = wt_path.name[len(mission_slug) + 1 :]
                if suffix.startswith("WP"):
                    wp_id = suffix
                    branch_name = wt_path.name
                    wp_workspaces.append((wt_path, wp_id, branch_name))

    # Run preflight
    preflight_result = run_preflight(
        mission_slug=mission_slug,
        target_branch=target,
        repo_root=main_repo_root,
        wp_workspaces=wp_workspaces,
    )

    if not preflight_result.passed:
        _fail(
            cmd,
            "PREFLIGHT_FAILED",
            "Preflight checks failed",
            {"errors": preflight_result.errors},
        )
        return

    # Determine merge order
    ordered_workspaces = get_merge_order(wp_workspaces, mission_dir)

    # Execute merges using git directly (simplified)
    merged_wps = []
    for wt_path, wp_id, branch_name in ordered_workspaces:
        try:
            # Checkout target branch and merge
            subprocess.run(
                ["git", "-C", str(main_repo_root), "checkout", target],
                check=True,
                capture_output=True,
            )
            if strategy == "squash":
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "merge", "--squash", branch_name],
                    check=True,
                    capture_output=True,
                )
                # squash leaves staged changes; commit them
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(main_repo_root),
                        "commit",
                        "-m",
                        f"squash merge: {mission_slug}/{wp_id} into {target}",
                    ],
                    check=True,
                    capture_output=True,
                )
            elif strategy == "rebase":
                # Rebase WP branch onto target, then fast-forward target.
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "checkout", branch_name],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "rebase", target],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "checkout", target],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "-C", str(main_repo_root), "merge", "--ff-only", branch_name],
                    check=True,
                    capture_output=True,
                )
            else:
                # Default: --no-ff merge
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(main_repo_root),
                        "merge",
                        "--no-ff",
                        branch_name,
                        "-m",
                        f"merge: {mission_slug}/{wp_id} into {target}",
                    ],
                    check=True,
                    capture_output=True,
                )
            merged_wps.append(wp_id)
        except subprocess.CalledProcessError as exc:
            _fail(
                cmd,
                "MERGE_FAILED",
                f"Failed to merge {wp_id}: {exc.stderr.decode() if exc.stderr else str(exc)}",
                {"merged_so_far": merged_wps, "failed_wp": wp_id},
            )
            return

    if push:
        try:
            subprocess.run(
                ["git", "-C", str(main_repo_root), "push", "origin", target],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            _fail(
                cmd,
                "PUSH_FAILED",
                f"Merge succeeded but push failed: {exc.stderr.decode() if exc.stderr else str(exc)}",
                {"merged_wps": merged_wps},
            )
            return

    envelope = make_envelope(
        command=cmd,
        success=True,
        data={
            "mission_slug": mission_slug,
            "merged": True,
            "target_branch": target,
            "strategy": strategy,
            "merged_wps": merged_wps,
            "worktree_removed": False,
        },
    )
    _emit(envelope)


__all__ = ["app"]
