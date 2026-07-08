"""Machine-contract API commands for external orchestrators.

All commands emit a single JSON object to stdout via the canonical envelope.
Non-zero exit on any failure. Output is always JSON (no prose mode).

Error codes used:
  USAGE_ERROR                 -- CLI parse/usage error (missing required arg, bad option, etc.)
  POLICY_METADATA_REQUIRED    -- --policy missing on a run-affecting command
  POLICY_VALIDATION_FAILED    -- policy JSON invalid or contains secrets
  MISSION_NOT_FOUND           -- mission slug does not resolve to a kitty-specs dir
  STATUS_READ_PATH_NOT_FOUND  -- coord topology with a stale/unaddressable primary surface
                                 (fail-closed read-path guard fired; carries coord/primary candidates)
  WP_NOT_FOUND                -- WP ID does not exist in the mission
  TRANSITION_REJECTED         -- transition not allowed by state machine
  WP_ALREADY_CLAIMED          -- WP claimed by a different actor
  MISSION_NOT_READY           -- not all WPs approved/done (for accept-mission)
  HISTORY_COMMIT_FAILED       -- append-history could not create its commit
  PLACEMENT_RESOLUTION_REQUIRED -- append-history's write placement could not be
                                 resolved (D11 fail-closed; FR-004 -- never a
                                 silent current-branch fallback)
  SAFE_COMMIT_*               -- structured safe_commit refusal/failure
  WORKFLOW_EVIDENCE_REQUIRED  -- workflow files changed without runner proof
  PREFLIGHT_FAILED            -- preflight checks failed (for merge-mission)
  CONTRACT_VERSION_MISMATCH   -- provider version is below MIN_PROVIDER_VERSION
  UNSUPPORTED_STRATEGY        -- merge strategy not implemented
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from contextlib import suppress
from datetime import datetime, UTC
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from specify_cli.lanes.models import ExecutionLane, LanesManifest

import typer

from mission_runtime import CommitTarget
from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.git.commit_helpers import (
    SafeCommitBackstopError,
    SafeCommitError,
    SafeCommitRecoveryFailed,
    safe_commit,
)
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.status import wp_state_for
from specify_cli.status import Lane

from .envelope import (
    CONTRACT_VERSION,
    MIN_PROVIDER_VERSION,
    make_envelope,
    parse_and_validate_policy,
    policy_to_dict,
)

import click
from typer import core as typer_core
from typer.core import TyperGroup

# Typer 0.26+ vendors click as typer._click; exceptions from that module are
# distinct from the standalone click package's exceptions. We need to catch both
# so that _JSONErrorGroup works regardless of the installed typer version.
try:
    from typer import _click as _typer_click_module  # type: ignore[attr-defined]
    _CLICK_USAGE_ERRORS: tuple[type, ...] = (
        click.UsageError,
        _typer_click_module.exceptions.UsageError,
    )
    _CLICK_ABORTS: tuple[type, ...] = (click.Abort, _typer_click_module.exceptions.Abort)
except ImportError:
    _CLICK_USAGE_ERRORS = (click.UsageError,)
    _CLICK_ABORTS = (click.Abort,)


_CLICK = typer_core._click if hasattr(typer_core, "_click") else typer_core.click
_USAGE_ERROR = getattr(_CLICK, "UsageError", _CLICK.exceptions.UsageError)
_ABORT = getattr(_CLICK, "Abort", _CLICK.exceptions.Abort)
_EXIT = getattr(_CLICK, "Exit", _CLICK.exceptions.Exit)


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
        except _CLICK_USAGE_ERRORS as exc:
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
        except _CLICK_USAGE_ERRORS as exc:
            self._emit_error(exc.format_message())
            ctx.exit(2)
        except _CLICK_ABORTS:
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
        except _CLICK_USAGE_ERRORS as exc:
            self._emit_error(exc.format_message())
            raise SystemExit(2) from exc
        except _CLICK_ABORTS:
            self._emit_error("Command aborted")
            raise SystemExit(2)
        except _EXIT as exc:
            raise SystemExit(exc.exit_code) from exc
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
# Deduplicated genuine-not-found message (Sonar S1192: emitted by 8 endpoints).
_MISSION_NOT_FOUND_MESSAGE = "Mission '{mission}' not found in kitty-specs/"
_HELP_WP_ID = "Work package ID"
_HELP_ACTOR = "Actor identity"
_HELP_POLICY = "Policy metadata JSON (required)"


def _transition_requires_policy(lane: str) -> bool:
    """Return True if transitioning to *lane* requires ``--policy`` metadata.

    A transition requires policy when the target's WPState is neither terminal,
    blocked, nor not-yet-started — i.e. claimed/in_progress/for_review/in_review/
    approved. Note this is intentionally NARROWER than ``WPState.is_run_affecting``
    (which also counts ``planned`` as active): a transition to ``planned`` does not
    require policy. The two are distinct concepts despite the historical shared name
    (#1775 review FSM-7); do not collapse them.
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


def _fail(command: str, error_code: str, message: str, data: dict | None = None) -> NoReturn:
    """Print failure envelope and exit non-zero.

    Typed ``NoReturn`` (FR-004 / S5747): this always raises ``typer.Exit``, so
    mypy proves any code after a ``_fail(...)`` call is unreachable — callers
    need no sentinel ``raise`` to satisfy their return type.
    """
    envelope = make_envelope(
        command=command,
        success=False,
        data=data or {"message": message},
        error_code=error_code,
    )
    _emit(envelope)
    raise typer.Exit(1)


def _fail_wp_not_found(cmd: str, wp: str, mission: str) -> NoReturn:
    """The ONE ``WP_NOT_FOUND`` emission (S1192 5×; locks error-surface parity)."""
    _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission}")


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
    """Return the coord-aware mission status directory if it exists, else None.

    For modern missions (coord-branch topology), returns the coordination
    worktree path. For legacy missions, returns the primary checkout path.
    Falls back to ``None`` only when the mission genuinely does not exist.

    This is now a thin consumer of the ONE guarded read-side seam
    :func:`resolve_handle_to_read_path` (WP01 / IC-01 / NFR-004): the seam owns
    the prototype cascade this endpoint pioneered — ``assert_safe_path_segment``
    → primary-``meta.json`` probe → the single sanctioned ``resolve_declared_mid8``
    cascade (NFR-005) → fail-closed coord-declared gate → the existence-gated
    :func:`resolve_mission_read_path`. The orchestrator's old inline duplicate of
    that cascade is GONE; only this ``.exists() → None`` adapter (the endpoint's
    own "absent ⇒ None, not a path" contract) remains here.

    Read-path SAFETY (FR-011 / M3, #2016) and the M5 fail-closed semantics are
    UNCHANGED — they are exactly the seam's invariants (the seam was lifted from
    this very prototype). ``require_exists`` is left at its default ``False`` so
    the seam returns the best-known candidate; this adapter decides absence by a
    single ``.exists()`` stat, preserving the historical ``Path | None`` contract.

    Typed-error fidelity (FR-001 / M2): :class:`StatusReadPathNotFound` from the
    seam's fail-closed gate is NOT caught here — it propagates so the calling
    endpoint surfaces the resolver's typed ``error_code`` (+ ``coord_candidate`` /
    ``primary_candidate``) instead of flattening every miss to
    ``MISSION_NOT_FOUND``.
    """
    from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

    mission_dir = resolve_handle_to_read_path(main_repo_root, mission_slug)
    return mission_dir if mission_dir.exists() else None


def _resolve_mission_dir_or_fail(command: str, main_repo_root: Path, mission_slug: str) -> Path:
    """Resolve the mission status dir, emitting the correct failure envelope on a miss.

    Single seam consumed by all 8 read endpoints (avoids 8 divergent patches):

    * a typed :class:`StatusReadPathNotFound` (coord topology + stale/unaddressable
      primary) surfaces the resolver's real ``error_code`` plus the
      ``coord_candidate`` / ``primary_candidate`` paths — the M2 fidelity fix; the
      external envelope *shape* is unchanged, only the code/data fidelity is raised
      (C-IC02 applied to the external surface).
    * a genuine absence (no such mission, no coord topology) keeps the historical
      ``MISSION_NOT_FOUND`` envelope.

    ``_fail`` is typed ``NoReturn`` (always raises ``typer.Exit``), so mypy proves
    the post-call paths unreachable — no sentinel ``raise`` is needed to satisfy
    the ``Path`` return type.
    """
    from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

    try:
        mission_dir = _resolve_mission_dir(main_repo_root, mission_slug)
    except StatusReadPathNotFound as exc:
        _fail(
            command,
            exc.error_code,
            str(exc),
            data={
                "message": str(exc),
                "mission_slug": exc.mission_slug,
                "mid8": exc.mid8,
                "coord_candidate": str(exc.coord_candidate),
                "primary_candidate": str(exc.primary_candidate),
            },
        )
    if mission_dir is None:
        _fail(command, "MISSION_NOT_FOUND", _MISSION_NOT_FOUND_MESSAGE.format(mission=mission_slug))
    return mission_dir


def _planning_read_dir(main_repo_root: Path, mission_slug: str) -> Path:
    """Return the PRIMARY-surface mission dir for planning-artifact reads (#2118).

    PRIMARY-partition artifacts — ``lanes.json`` (``LANE_STATE``) and the WP
    ``tasks/`` files (``WORK_PACKAGE_TASK``) — live with their mission on the
    primary ``target_branch`` for EVERY topology since the write-surface-coherence
    work (#2090): planning never transits the coordination branch. The coord-aware
    :func:`_resolve_mission_dir` returns the *coordination worktree*, which carries
    ONLY status artifacts (``status.events.jsonl`` / ``status.json``) +
    coordination-owned ones (``analysis-report.md``). Reading ``lanes.json`` or
    ``tasks/`` off that surface under coordination topology silently no-ops — the
    dependency graph comes back empty and the orchestrator stalls with every WP
    stuck at ``lane=planned`` (#2118).

    This routes PRIMARY-partition reads through the canonical kind-aware
    placement seam (:func:`mission_runtime.placement_seam`, coord-primary-
    partition-lock WP01 T004 — DRY-only repoint, out-of-map edit; this file is
    not a WP01 owned file), the read-side twin of the write-side partition
    (``mission_runtime.is_primary_artifact_kind``): a PRIMARY kind resolves the
    topology-blind primary dir, so both ``LANE_STATE`` and ``WORK_PACKAGE_TASK``
    co-resolve here. STATUS reads (``read_events`` / ``reduce`` / ``materialize``
    / status-event writes) MUST keep the coord-aware :func:`_resolve_mission_dir`
    — the append-only event log stays on coordination for coord-topology
    missions. This mirrors the meta.json treatment already in
    :func:`_resolve_merge_target_branch`.
    """
    from mission_runtime import MissionArtifactKind, placement_seam

    return placement_seam(main_repo_root, mission_slug).read_dir(
        MissionArtifactKind.WORK_PACKAGE_TASK
    )


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
    from specify_cli.status import read_events

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
    """Resolve the branch ``merge-mission`` integrates into.

    Order: explicit ``--target`` > meta ``merge_target_branch`` > meta
    ``target_branch`` > repo default.

    The mission target lives in the PRIMARY-checkout meta.json (like
    ``coordination_branch``), so it is read via ``primary_feature_dir_for_mission``
    — NOT the topology-aware candidate. Under coordination topology that candidate
    resolves to the coordination worktree, whose mission dir has no meta.json; the
    prior code read that surface, missed the mission's ``target_branch``, and
    silently fell back to the repo default (main) — merging into the wrong branch.
    """
    from specify_cli.core.paths import resolve_merge_target_branch

    return resolve_merge_target_branch(main_repo_root, mission_slug, target)[0]


def _build_merge_preflight(
    main_repo_root: Path,
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
        # lanes.json is a PRIMARY-partition artifact — read from the primary
        # surface, NOT the coord worktree mission_dir (#2118).
        require_lanes_json(_planning_read_dir(main_repo_root, mission_slug))
    except (MissingLanesError, CorruptLanesError) as exc:
        errors.append(str(exc))

    return _MergePreflightResult(target_branch=resolved_target, errors=errors)


def _execute_planning_only_merge(
    main_repo_root: Path,
    mission_slug: str,
    target_branch: str,
    *,
    strategy: object,
    push: bool,
    delete_branch: bool,
    remove_worktree: bool,
) -> None:
    """Run the hardened CLI closeout path while preserving JSON-only stdout."""
    import typer

    from specify_cli.cli.commands import merge as merge_command

    try:
        with merge_command.console.capture():
            merge_command._run_lane_based_merge(
                repo_root=main_repo_root,
                mission_slug=mission_slug,
                push=push,
                delete_branch=delete_branch,
                remove_worktree=remove_worktree,
                target_override=target_branch,
                strategy=strategy,
                assume_yes=True,
            )
    except typer.Exit as exc:
        raise RuntimeError(
            f"Planning-artifact closeout failed with exit code {exc.exit_code}"
        ) from exc


def _execute_lane_merge(
    main_repo_root: Path,
    mission_dir: Path,
    mission_slug: str,
    target_branch: str,
    *,
    strategy: str,
    push: bool,
    delete_branch: bool,
    remove_worktree: bool,
) -> None:
    """Execute the lane-based merge flow without emitting console prose."""
    from specify_cli.cli.commands.merge import _mark_wp_merged_done
    from specify_cli.core.git_ops import has_remote, run_command
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.compute import is_planning_artifact_only, is_planning_lane
    from specify_cli.lanes.merge import merge_lane_to_mission, merge_mission_to_target
    from specify_cli.lanes.persistence import require_lanes_json
    from specify_cli.merge.config import MergeStrategy
    from specify_cli.policy.config import load_policy_config
    from specify_cli.policy.merge_gates import evaluate_merge_gates

    # lanes.json is PRIMARY-partition — read from the primary surface, not the
    # coord worktree mission_dir (#2118).
    lanes_manifest = require_lanes_json(_planning_read_dir(main_repo_root, mission_slug))
    lanes_manifest.target_branch = target_branch
    merge_strategy = MergeStrategy(strategy)

    if is_planning_artifact_only(lanes_manifest):
        _execute_planning_only_merge(
            main_repo_root,
            mission_slug,
            target_branch,
            strategy=merge_strategy,
            push=push,
            delete_branch=delete_branch,
            remove_worktree=remove_worktree,
        )
        return

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

    mission_result = merge_mission_to_target(
        main_repo_root,
        mission_slug,
        lanes_manifest,
        strategy=merge_strategy,
    )
    if not mission_result.success:
        raise RuntimeError("; ".join(mission_result.errors) or "Mission merge failed.")

    for lane in lanes_manifest.lanes:
        for wp_id in lane.wp_ids:
            _mark_wp_merged_done(main_repo_root, mission_slug, wp_id, lanes_manifest.target_branch)

    if push and has_remote(main_repo_root):
        run_command(["git", "push", "origin", lanes_manifest.target_branch], cwd=main_repo_root)

    if remove_worktree:
        from specify_cli.lanes.branch_naming import worktree_path

        for lane in lanes_manifest.lanes:
            # Legacy lane-worktree grammar ({slug}-{lane}, no mid8) ⇒ mission_id=None
            # reproduces the historical name byte-identically (FR-005).
            wt_path = worktree_path(
                main_repo_root, mission_slug, mission_id=None, lane_id=lane.lane_id
            )
            if wt_path.exists():
                run_command(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=main_repo_root,
                    check_return=False,
                )

    if delete_branch:
        for lane in lanes_manifest.lanes:
            if is_planning_lane(lane):
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
    mission_dir = _resolve_mission_dir_or_fail("mission-state", main_repo_root, mission)

    from specify_cli.status import reduce
    from specify_cli.status import read_events
    from specify_cli.core.dependency_graph import build_dependency_graph

    # STATUS reads stay on the coord-aware dir; PRIMARY reads (dep graph from WP
    # frontmatter, tasks/ enumeration) come from the primary surface (#2118).
    planning_dir = _planning_read_dir(main_repo_root, mission)

    # Query endpoint: reduce from event log without rewriting status.json.
    snapshot = reduce(read_events(mission_dir))
    dep_graph = build_dependency_graph(planning_dir)

    # Build the full WP set from task files + dep graph + snapshot
    # so that untouched WPs (no events yet) still appear as "planned"
    tasks_dir = planning_dir / "tasks"
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
    """List WPs that are ready to start (planned and all deps approved or done)."""
    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir_or_fail("list-ready", main_repo_root, mission)

    from specify_cli.status import reduce
    from specify_cli.status import read_events
    from specify_cli.core.dependency_graph import build_dependency_graph, dependency_readiness_for_wp

    # Query endpoint: reduce from event log without rewriting status.json.
    # STATUS read off the coord-aware dir; the dependency graph (WP frontmatter,
    # PRIMARY-partition) off the primary surface (#2118 — an empty dep graph here
    # is exactly what stalls the orchestrator under coordination topology).
    snapshot = reduce(read_events(mission_dir))
    dep_graph = build_dependency_graph(_planning_read_dir(main_repo_root, mission))
    wp_states = snapshot.work_packages
    wp_lanes = {
        dep_id: wp_state_for(state.get("lane", Lane.PLANNED)).lane
        for dep_id, state in wp_states.items()
    }

    ready_wps = []
    for wp_id, deps in dep_graph.items():
        wp_snapshot = wp_states.get(wp_id, {})
        lane = wp_snapshot.get("lane", Lane.PLANNED)
        state = wp_state_for(lane)
        if state.progress_bucket() != "not_started":
            continue

        readiness = dependency_readiness_for_wp(wp_id, deps, wp_lanes)

        ready_wps.append(
            {
                "wp_id": wp_id,
                "lane": lane,
                "dependencies_satisfied": readiness.satisfied,
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


@dataclass(frozen=True)
class _StartWorkspace:
    """The workspace resolved for a WP at start-implementation.

    For a lane WP (lanes.json present and the WP is assigned to a lane) the lane
    fields are populated and ``workspace_path`` is a real lane worktree. For a
    legacy / non-lane mission (no lanes.json, or a planning-artifact WP) the lane
    fields stay ``None`` and ``workspace_path`` is the historical bare path —
    preserving the prior contract for those missions.
    """

    workspace_path: str
    lane_id: str | None = None
    lane_branch: str | None = None
    lane_base_ref: str | None = None


def _lane_base_ref(main_repo_root: Path, mission: str, manifest: object) -> str:
    """The ref the lane was parented on — the base for the commit gate.

    Uses the canonical placement authority (`resolve_placement_only`) — the same
    one the native review gate consults — which resolves to the coordination
    branch under coord topology. On the coord path this PR targets, both gates
    therefore agree on the base. The fallback ordering differs for legacy
    missions: this gate falls back to the manifest's mission_branch then the repo
    default, whereas the native gate prefers the workspace context's base_branch;
    the commit-existence check (`rev-list <base>..HEAD` count > 0) is robust to
    that difference as long as the base is an ancestor of HEAD, which holds for
    both.
    """
    from mission_runtime import (
        ActionContextError,
        MissionArtifactKind,
        resolve_placement_only,
    )

    try:
        # base-ref read under coord topology — coord kind preserves G-2
        # (write-surface-coherence WP02 / T031 site 4): the lane-base gate compares
        # against the coordination BASE ref under coord topology. STATUS_STATE keeps
        # the coord ref; a primary kind would read the primary ref as the base and
        # corrupt the gate's `rev-list <base>..HEAD` ancestry check.
        return str(
            resolve_placement_only(
                main_repo_root, mission, kind=MissionArtifactKind.STATUS_STATE
            ).ref
        )
    except ActionContextError:
        # Never return an empty ref: the commit gate runs `git rev-list <base>..HEAD`,
        # and an empty base silently degrades to an unreliable HEAD..HEAD. Fall back to
        # the manifest's mission_branch, or the repo default branch as a last resort.
        from specify_cli.core.git_ops import resolve_primary_branch

        return str(
            getattr(manifest, "mission_branch", "") or resolve_primary_branch(main_repo_root)
        )


def _lane_assignment_or_legacy(
    main_repo_root: Path, mission: str, wp: str
) -> tuple[LanesManifest, ExecutionLane] | _StartWorkspace:
    """Shared prologue of the two workspace resolvers (ONE fallback grammar).

    Returns the ``(manifest, lane)`` pair when ``wp`` is lane-assigned;
    otherwise the legacy bare-path ``_StartWorkspace`` — the WP-based worktree
    form ``{mission}-{wp}`` with no mid8 (the seam's ``mission_id=None``
    grammar reproduces the historical name byte-identically) — so legacy /
    non-lane missions keep working unchanged.

    lanes.json is PRIMARY-partition — read from the primary surface (#2118).
    SSOT: this is the ONLY place this surface decides lane-vs-legacy; a future
    fallback-grammar change is a single edit.
    """
    from specify_cli.lanes.branch_naming import worktree_path as _wt_path
    from specify_cli.lanes.persistence import read_lanes_json

    manifest = read_lanes_json(_planning_read_dir(main_repo_root, mission))
    lane = manifest.lane_for_wp(wp) if manifest is not None else None
    if manifest is None or lane is None:
        return _StartWorkspace(
            workspace_path=str(_wt_path(main_repo_root, mission, mission_id=None, lane_id=wp))
        )
    return manifest, lane


def _resolve_start_workspace(
    cmd: str, main_repo_root: Path, mission: str, mission_dir: Path, wp: str
) -> _StartWorkspace:
    """Resolve (allocating if needed) the workspace for ``wp``.

    When the mission has a lanes manifest and ``wp`` is assigned to a lane, this
    mirrors spec-kitty's native implement flow: it allocates (or reuses) the lane
    worktree on its lane branch — parented on the coordination branch, with
    approved dependency-lane tips merged into the base — so ``merge-mission`` has
    a real lane branch to integrate and dependent WPs see their dependencies'
    code. Idempotent: re-invoking reuses the existing lane worktree and re-merges
    any newly-approved dependency tips.

    When there is no lanes.json (legacy / non-lane missions) or ``wp`` is not in
    any lane (planning-artifact WP), it falls back to the historical bare-path
    behaviour (via :func:`_lane_assignment_or_legacy`) so those missions keep
    working unchanged.

    A genuine allocation failure for a lane WP (dirty reuse, dependency-merge
    conflict) fails closed with ``LANE_ALLOCATION_FAILED``.
    """
    assignment = _lane_assignment_or_legacy(main_repo_root, mission, wp)
    if isinstance(assignment, _StartWorkspace):
        return assignment
    manifest, lane = assignment

    from specify_cli.lanes.worktree_allocator import (
        DependencyLaneMergeConflictError,
        DirtyWorktreeError,
        LaneNotFoundError,
        allocate_lane_worktree,
    )

    try:
        worktree_path, lane_branch = allocate_lane_worktree(
            repo_root=main_repo_root,
            mission_slug=mission,
            wp_id=wp,
            lanes_manifest=manifest,
        )
    except (
        LaneNotFoundError,
        DirtyWorktreeError,
        DependencyLaneMergeConflictError,
        RuntimeError,
    ) as exc:
        _fail(
            cmd,
            "LANE_ALLOCATION_FAILED",
            str(exc),
            {**_mission_identity_payload(mission_dir), "wp_id": wp},
        )

    # _fail is NoReturn (always raises typer.Exit), so this is reached only on the
    # success path, where worktree_path / lane_branch are bound.
    return _StartWorkspace(
        workspace_path=str(worktree_path),
        lane_id=lane.lane_id,
        lane_branch=lane_branch,
        lane_base_ref=_lane_base_ref(main_repo_root, mission, manifest),
    )


def _resolve_existing_workspace(
    main_repo_root: Path, mission: str, wp: str
) -> _StartWorkspace:
    """Read-only companion of :func:`_resolve_start_workspace` (#2337).

    Resolves the WP's lane ``workspace_path`` + ``lane_branch`` for its EXISTING
    lane via the canonical naming seams (``lane_branch_name`` + ``worktree_path``)
    — WITHOUT allocating, creating, validating-clean, or merging dependency tips.
    Lets a caller obtain the workspace for a WP already past start-implementation
    (e.g. an external orchestrator resuming a ``for_review`` WP) without the
    ``planned->claimed->in_progress`` composite transition start-implementation
    performs. Shares start-implementation's legacy/non-lane fallback via
    :func:`_lane_assignment_or_legacy`, and takes placement from the allocator's
    own :func:`~specify_cli.lanes.worktree_allocator.predict_lane_worktree` seam
    so the read-only mirror can never diverge from what the write authority
    would create.
    """
    from specify_cli.lanes.worktree_allocator import predict_lane_worktree

    assignment = _lane_assignment_or_legacy(main_repo_root, mission, wp)
    if isinstance(assignment, _StartWorkspace):
        return assignment
    manifest, lane = assignment

    worktree_path, lane_branch = predict_lane_worktree(main_repo_root, mission, lane.lane_id)
    return _StartWorkspace(
        workspace_path=str(worktree_path),
        lane_id=lane.lane_id,
        lane_branch=lane_branch,
        lane_base_ref=_lane_base_ref(main_repo_root, mission, manifest),
    )


@app.command(name="resolve-workspace")
def resolve_workspace(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    wp: str = typer.Option(..., "--wp", help=_HELP_WP_ID),
) -> None:
    """Read-only: resolve a WP's lane workspace_path + prompt_path (+ lane fields).

    Does NOT allocate/create/validate-clean/transition — the read-only companion
    of ``start-implementation`` for a WP already past implementation (e.g. a
    ``for_review`` WP an external orchestrator wants to review on resume, where
    calling start-implementation would wrongly re-transition it). Contract >= 1.2.0.
    """
    cmd = "resolve-workspace"
    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    wp_path = _resolve_wp_file(_planning_read_dir(main_repo_root, mission) / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
        return

    ws = _resolve_existing_workspace(main_repo_root, mission, wp)
    # --mission accepts mission_id / mid8 / slug; the payload's mission_slug is
    # the RESOLVED identity, never the raw selector echoed back.
    data: dict = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "workspace_path": ws.workspace_path,
        "prompt_path": str(wp_path),
    }
    if ws.lane_id is not None:
        data["lane_id"] = ws.lane_id
        data["lane_branch"] = ws.lane_branch
        data["lane_base_ref"] = ws.lane_base_ref
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(command=cmd, success=True, data=data)
    _emit(envelope)


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
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    wp_path = _resolve_wp_file(_planning_read_dir(main_repo_root, mission) / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
        return

    from specify_cli.core.dependency_graph import dependency_readiness_for_wp, parse_wp_dependencies
    from specify_cli.status import reduce
    from specify_cli.status import read_events

    wp_lanes = {
        wp_id: state.get("lane", Lane.PLANNED)
        for wp_id, state in reduce(read_events(mission_dir)).work_packages.items()
    }
    # Only gate the not-yet-started claim transition. Re-invoking start-implementation
    # on a WP that is already in_progress/for_review/.../approved is a no-op resume
    # in the lifecycle layer and must not be rejected just because a dependency later
    # regressed out of approved/done.
    _self_lane = wp_state_for(wp_lanes.get(wp, Lane.PLANNED)).lane
    if _self_lane in (Lane.PLANNED, Lane.CLAIMED):
        dependency_readiness = dependency_readiness_for_wp(
            wp,
            parse_wp_dependencies(wp_path),
            wp_lanes,
        )
        if not dependency_readiness.satisfied:
            blocked = ", ".join(dependency_readiness.unsatisfied)
            _fail(
                cmd,
                "DEPENDENCIES_NOT_SATISFIED",
                (
                    f"dependencies_not_satisfied: {wp} depends on {blocked}; "
                    "all dependencies must be approved or done before implementation can start"
                ),
                {
                    **_mission_identity_payload(mission_dir),
                    "wp_id": wp,
                    "unsatisfied_dependencies": list(dependency_readiness.unsatisfied),
                },
            )
            return

    from specify_cli.status import TransitionError
    from specify_cli.status import WorkPackageClaimConflict, start_implementation_status

    # Allocate the REAL lane worktree (lane branch + dependency-lane tips merged)
    # when the mission has lanes, mirroring the native implement flow so
    # merge-mission has a lane branch to integrate. Legacy / non-lane missions
    # keep the historical bare path.
    start_ws = _resolve_start_workspace(cmd, main_repo_root, mission, mission_dir, wp)
    workspace_path = start_ws.workspace_path
    prompt_path = str(wp_path)

    try:
        start_result = start_implementation_status(
            feature_dir=mission_dir,
            mission_slug=mission,
            wp_id=wp,
            actor=actor,
            workspace_context=workspace_path,
            execution_mode="worktree",
            repo_root=main_repo_root,
            policy_metadata=policy_dict,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    except WorkPackageClaimConflict as exc:
        _fail(
            cmd,
            "WP_ALREADY_CLAIMED",
            str(exc),
            {
                **_mission_identity_payload(mission_dir),
                "claimed_by": exc.claimed_by,
                "requesting_actor": exc.requesting_actor,
            },
        )
        return
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    data = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "from_lane": start_result.from_lane,
        "to_lane": Lane.IN_PROGRESS,
        "workspace_path": workspace_path,
        "prompt_path": prompt_path,
        "policy_metadata_recorded": True,
        "no_op": start_result.no_op,
    }
    if start_ws.lane_id is not None:
        # Lane WP: carry the lane identity the orchestrator needs to commit and
        # gate. Omitted for legacy / non-lane missions (unchanged contract).
        data["lane_id"] = start_ws.lane_id
        data["lane_branch"] = start_ws.lane_branch
        data["lane_base_ref"] = start_ws.lane_base_ref
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
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    wp_path = _resolve_wp_file(_planning_read_dir(main_repo_root, mission) / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
        return

    from specify_cli.status import TransitionError
    from specify_cli.status import WorkPackageClaimConflict, start_review_status

    prompt_path = str(wp_path)

    try:
        start_result = start_review_status(
            feature_dir=mission_dir,
            mission_slug=mission,
            wp_id=wp,
            actor=actor,
            review_ref=review_ref,
            workspace_context=f"orchestrator-api:{main_repo_root}",
            execution_mode="worktree",
            repo_root=main_repo_root,
            policy_metadata=policy_dict,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    except WorkPackageClaimConflict as exc:
        _fail(
            cmd,
            "WP_ALREADY_CLAIMED",
            str(exc),
            {
                **_mission_identity_payload(mission_dir),
                "claimed_by": exc.claimed_by,
                "requesting_actor": exc.requesting_actor,
            },
        )
        return
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    data = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "from_lane": start_result.from_lane,
        "to_lane": Lane.IN_REVIEW,
        "prompt_path": prompt_path,
        "policy_metadata_recorded": True,
        "no_op": start_result.no_op,
    }
    validate_outbound_payload(data, "orchestrator_api")
    envelope = make_envelope(
        command=cmd,
        success=True,
        data=data,
    )
    _emit(envelope)


# ── Command 6: transition ──────────────────────────────────────────────────


def _enforce_for_review_commit_gate(
    cmd: str, main_repo_root: Path, mission: str, mission_dir: Path, wp: str, force: bool
) -> None:
    """Reject an in_progress->for_review transition that has no commit on the lane.

    Applies the SAME "commits beyond base" check the native ``move-task`` gate
    uses (``lanes._git.lane_has_commit_beyond_base``) so "done without a commit"
    is impossible through the orchestrator-api too. No-ops when bypassed
    (``--force``) or when the gate does not apply (no lanes.json, or the WP is
    not in any lane — e.g. planning-artifact WPs). Fails closed with
    ``TRANSITION_REJECTED`` when a lane WP has no implementation commit.
    """
    if force:
        return
    from specify_cli.lanes._git import lane_has_commit_beyond_base
    from specify_cli.lanes.worktree_allocator import predict_lane_worktree

    # Legacy/non-lane arm ⇒ guard exempt: only lane WPs carry a lane branch to
    # check commits on (the composed legacy workspace is discarded).
    assignment = _lane_assignment_or_legacy(main_repo_root, mission, wp)
    if isinstance(assignment, _StartWorkspace):
        return
    manifest, lane = assignment

    worktree, lane_branch = predict_lane_worktree(main_repo_root, mission, lane.lane_id)
    base_ref = _lane_base_ref(main_repo_root, mission, manifest)
    if not worktree.exists() or not lane_has_commit_beyond_base(worktree, base_ref):
        _fail(
            cmd,
            "TRANSITION_REJECTED",
            (
                f"{wp} cannot move to for_review: no implementation commit on lane "
                f"{lane.lane_id} ({lane_branch}) beyond "
                f"{base_ref}. Commit the work in the lane worktree first, or pass "
                "--force if there is genuinely nothing to commit."
            ),
            {**_mission_identity_payload(mission_dir), "wp_id": wp, "lane_id": lane.lane_id},
        )


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

    from specify_cli.status import resolve_lane_alias

    to_lane = resolve_lane_alias(to)

    # Policy required for transitions into active-execution lanes (not planned).
    policy_dict: dict | None = None
    if _transition_requires_policy(to_lane):
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
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    wp_path = _resolve_wp_file(_planning_read_dir(main_repo_root, mission) / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
        return

    if to_lane == Lane.FOR_REVIEW:
        _enforce_for_review_commit_gate(cmd, main_repo_root, mission, mission_dir, wp, force)

    from specify_cli.coordination.status_transition import emit_status_transition_transactional
    from specify_cli.status import TransitionError
    from specify_cli.status import TransitionRequest

    try:
        event = emit_status_transition_transactional(
            TransitionRequest(
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
                repo_root=main_repo_root,
                policy_metadata=policy_dict,
            ),
            ensure_sync_daemon=False,
            sync_dossier=False,
        )
    except TransitionError as exc:
        _fail(cmd, "TRANSITION_REJECTED", str(exc))
        return

    data = {
        **_mission_identity_payload(mission_dir),
        "wp_id": wp,
        "from_lane": str(event.from_lane),
        "to_lane": str(event.to_lane),
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


def _resolve_history_commit_args(
    main_repo_root: Path, mission: str
) -> tuple[Path, CommitTarget]:
    """Resolve (worktree_root, target) for committing a WP prompt-file edit.

    The WP prompt file is a ``WORK_PACKAGE_TASK`` — a PRIMARY artifact kind
    (write-surface-coherence WP03 / T013). So it commits to the primary
    ``target_branch`` for every topology, via the kind-aware
    :func:`resolve_placement_only`, NOT through the coordination worktree: the
    planning→coord transit is removed (FR-003 / C-005). The WP prompt edit is
    committed directly from the primary checkout.

    FR-004 (read-surface-ssot-closeout, C-005): a placement-resolution
    failure (:class:`ActionContextError`) is FAIL-CLOSED — it raises
    :class:`PlacementResolutionRequired` and propagates. It must never
    silently degrade to ``CommitTarget(ref=<current checked-out branch>)``: a
    resolver failure is a real defect (missing mission, corrupt state, a
    ``coordination_branch`` declared in meta.json but torn down in git, ...),
    and committing the WP history entry to whatever branch the operator
    happens to have checked out is a shadow write path, not a legitimate
    fallback.
    """
    from mission_runtime import (
        ActionContextError,
        MissionArtifactKind,
        resolve_placement_only,
    )

    try:
        # WORK_PACKAGE_TASK is a primary kind: the placement resolves to the
        # primary target branch for every topology (no coord transit). The WP
        # prompt edit therefore commits directly to the primary checkout.
        placement = resolve_placement_only(
            main_repo_root, mission, kind=MissionArtifactKind.WORK_PACKAGE_TASK
        )
    except ActionContextError as exc:
        raise PlacementResolutionRequired(
            "Cannot resolve the canonical write placement for this mission's "
            "WP prompt-file history commit -- refusing to commit to the "
            "currently checked-out branch (D11 fail-closed / FR-004). This "
            "usually means the mission's stored topology could not be "
            "resolved (e.g. a coordination branch declared in meta.json is "
            "missing/torn down in git). Run `spec-kitty doctor workspaces "
            "--fix`, or flatten the mission by removing `coordination_branch` "
            "from meta.json if the coordination topology was never used, "
            "then retry."
        ) from exc

    return main_repo_root, placement


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
    # Existence/identity gate via the coord-aware read seam (typed miss envelope).
    _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    # FR-003 / T013: the WP prompt file is a WORK_PACKAGE_TASK (primary kind), so
    # it is authored and committed on the PRIMARY checkout — never the coordination
    # worktree (the planning→coord transit is removed, C-005). Resolve the WP file
    # through the canonical per-kind read seam (``_planning_read_dir`` →
    # ``resolve_planning_read_dir``, the same seam the sibling planning reads use),
    # NOT a raw handle-blind ``primary_feature_dir_for_mission`` call: that primitive
    # composes the handle verbatim, so a bare ``mid8`` / full ULID / numeric handle
    # would land on a DIVERGENT dir than where the WP prompt actually lives (the
    # #2136/#2164 write/placement divergence). The seam folds the handle to its
    # canonical ``<slug>-<mid8>`` dir for every form (and propagates
    # ``MissionSelectorAmbiguous`` — no silent pick). The kind is PRIMARY so the
    # resolved dir is the primary surface — a coord-anchored path would trip
    # SAFE_COMMIT_PATH_POLICY (.worktrees/ staging).
    primary_mission_dir = _planning_read_dir(main_repo_root, mission)
    wp_path = _resolve_wp_file(primary_mission_dir / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
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

    try:
        wp_path.write_text(build_document(fm, new_body, padding), encoding="utf-8")

        commit_worktree_root, commit_target = _resolve_history_commit_args(
            main_repo_root, mission
        )
        safe_commit(
            repo_root=main_repo_root,
            worktree_root=commit_worktree_root,
            target=commit_target,
            message=f"hist: append activity log entry for {mission}/{wp}",
            paths=(wp_path,),
        )
    except (SafeCommitError, SafeCommitBackstopError) as exc:
        if not (isinstance(exc, SafeCommitRecoveryFailed) and exc.commit_sha is not None):
            with suppress(OSError):
                wp_path.write_text(raw, encoding="utf-8")
        if isinstance(exc, SafeCommitError):
            data = exc.to_dict()
        else:
            data = {
                "error_code": exc.error_code,
                "message": str(exc),
                "requested": list(exc.requested),
                "unexpected": [
                    {"path": unexpected.path, "status_code": unexpected.status_code}
                    for unexpected in exc.unexpected
                ],
            }
        _fail(cmd, exc.error_code, str(exc), data=data)
        return
    except subprocess.CalledProcessError as exc:
        with suppress(OSError):
            wp_path.write_text(raw, encoding="utf-8")
        message = exc.stderr.strip() if exc.stderr else str(exc)
        _fail(cmd, "HISTORY_COMMIT_FAILED", message)
        return
    except PlacementResolutionRequired as exc:
        # FR-004 (C-005): a fail-closed placement-resolution refusal carries
        # its own structured error_code -- it must NOT be flattened into the
        # generic HISTORY_COMMIT_FAILED below, which would hide the D11
        # fail-closed signal from the machine-contract consumer.
        with suppress(OSError):
            wp_path.write_text(raw, encoding="utf-8")
        _fail(cmd, exc.error_code, str(exc), data=exc.to_dict())
        return
    except (OSError, RuntimeError) as exc:
        with suppress(OSError):
            wp_path.write_text(raw, encoding="utf-8")
        _fail(cmd, "HISTORY_COMMIT_FAILED", str(exc))
        return

    entry_id = "hist-" + uuid.uuid4().hex

    data = {
        **_mission_identity_payload(primary_mission_dir),
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
    """Accept a mission after all WPs are approved or done."""
    cmd = "accept-mission"

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    from specify_cli.status import materialize
    from specify_cli.core.dependency_graph import build_dependency_graph

    # STATUS read off the coord-aware dir; dependency graph (WP frontmatter,
    # PRIMARY-partition) off the primary surface (#2118).
    snapshot = materialize(mission_dir)
    dep_graph = build_dependency_graph(_planning_read_dir(main_repo_root, mission))

    # Check all WPs (from dep_graph) are approved/done; WPs with no events are implicitly planned.
    all_wp_ids = set(dep_graph.keys()) | set(snapshot.work_packages.keys())
    incomplete = [
        wp_id
        for wp_id in sorted(all_wp_ids)
        if wp_state_for(snapshot.work_packages.get(wp_id, {}).get("lane", Lane.PLANNED)).lane
        not in {Lane.APPROVED, Lane.DONE}
    ]
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

    from specify_cli.acceptance import collect_feature_summary
    from specify_cli.upgrade.pre30_guard import Pre30LayoutError

    try:
        summary = collect_feature_summary(main_repo_root, mission)
    except Pre30LayoutError as exc:
        # #1057 / squad Blocker 1: pre-3.0 lane-directory missions hard-reject
        # rather than producing a vacuous all-done summary. A mission whose layout
        # the runtime no longer reads is not acceptable until migrated, so it maps
        # to MISSION_NOT_READY; the full `spec-kitty upgrade` instruction rides in
        # the message field (keeping the orchestrator JSON envelope contract).
        _fail(cmd, "MISSION_NOT_READY", str(exc), _mission_identity_payload(mission_dir))
        return
    workflow_evidence_issues = [
        issue for issue in summary.activity_issues if issue.startswith("Workflow run evidence required:")
    ]
    if workflow_evidence_issues:
        _fail(
            cmd,
            "WORKFLOW_EVIDENCE_REQUIRED",
            workflow_evidence_issues[0],
            {
                **_mission_identity_payload(mission_dir),
                "required_evidence_path": str(mission_dir / "workflow-evidence.md"),
            },
        )
        return

    # Write acceptance record via centralized metadata writer
    from specify_cli.mission_metadata import record_acceptance

    meta = record_acceptance(
        mission_dir,
        accepted_by=actor,
        mode="orchestrator",
    )
    accepted_at = str(meta["accepted_at"])
    approved_wps = list(summary.lanes.get("approved", []))
    done_wps = list(summary.lanes.get("done", []))

    data = {
        **_mission_identity_payload(mission_dir),
        "accepted": True,
        "mode": "auto",
        "accepted_at": accepted_at,
        "accepted_wps": [*approved_wps, *done_wps],
        "approved_wps": approved_wps,
        "done_wps": done_wps,
        "merge_pending_wps": approved_wps,
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
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    preflight = _build_merge_preflight(main_repo_root, mission, target)
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
            strategy=strategy,
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
