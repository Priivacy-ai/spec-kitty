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
  PREFLIGHT_FAILED            -- preflight checks failed (for merge-mission)
  CONTRACT_VERSION_MISMATCH   -- provider version is below MIN_PROVIDER_VERSION
  UNSUPPORTED_STRATEGY        -- merge strategy not implemented
  ANCESTRY_NOT_ESTABLISHED    -- #3281/FR-007: the recorded planning commit or an
                                 approved dependency lane's tip is not (yet) a git
                                 ancestor of the claimed workspace's HEAD, even
                                 after self-heal re-ran the reuse-path merges
  MISSION_ALREADY_EXISTS      -- specify: the delegate mission-creation call failed
                                 with a duplicate/no-op-commit signature (WP03)
  MISSION_CREATE_FAILED       -- specify: mission creation failed for a reason
                                 other than a detected duplicate (WP03)
  PLAN_SETUP_FAILED           -- plan: the delegate plan-scaffold call failed and
                                 carried no more specific error_code of its own (WP03)
  TASKS_FINALIZE_FAILED       -- tasks: the delegate finalize-tasks call failed and
                                 carried no more specific error_code of its own (WP03)
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import uuid
from kernel.clock import now_utc_stamp
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from specify_cli.core.paths import RetentionDecision
    from specify_cli.lanes.models import ExecutionLane, LanesManifest

import typer

from mission_runtime import CommitTarget, MissionTopology
from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.status import wp_state_for
from specify_cli.status import Lane
from specify_cli.status import ReviewResult
from specify_cli.status import parse_review_result_json

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

# Typer 0.26+ vendors click as ``typer._click``; exceptions raised by that copy
# are distinct classes from the standalone ``click`` package's, so every catch
# below must name both.  The vendored module's surface is itself a moving
# target: 0.26.x exposed ``exceptions.Abort``/``exceptions.Exit``, while 0.27.x
# exposes only ``exceptions.UsageError`` and raises typer's own public
# ``typer.Abort``/``typer.Exit`` instead (spec-kitty#713).  Every class is
# therefore resolved with ``getattr`` and a ``None`` default — never as an
# eagerly evaluated default expression such as ``getattr(m, "Abort",
# m.exceptions.Abort)``, which raised ``AttributeError`` at import time — and
# typer's stable public ``typer.Abort``/``typer.Exit`` are always included.


def _vendored_click_exception(name: str) -> type[BaseException] | None:
    """Return ``typer._click``'s exception class ``name``, or ``None`` if absent.

    Looks in the vendored ``exceptions`` submodule first, then the package
    root, and never touches an attribute it has not confirmed exists.
    """
    module = getattr(typer_core, "_click", None)
    if module is None:
        return None
    for holder in (getattr(module, "exceptions", None), module):
        candidate = getattr(holder, name, None) if holder is not None else None
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            return candidate
    return None


def _exception_classes(*candidates: type[BaseException] | None) -> tuple[type[BaseException], ...]:
    """Deduplicate ``candidates`` into an ``except``-clause tuple, dropping ``None``."""
    classes: list[type[BaseException]] = []
    for candidate in candidates:
        if candidate is not None and candidate not in classes:
            classes.append(candidate)
    return tuple(classes)


_CLICK_USAGE_ERRORS = _exception_classes(click.UsageError, _vendored_click_exception("UsageError"))
_CLICK_ABORTS = _exception_classes(click.Abort, typer.Abort, _vendored_click_exception("Abort"))
# ``typer.Exit`` is click's ``Exit`` on typer <= 0.25 and typer's own class on
# >= 0.26, so it covers the standalone-click spelling in both eras (TID251).
_EXIT = _exception_classes(typer.Exit, _vendored_click_exception("Exit"))


def _vendored_click_exception(name: str) -> type[BaseException] | None:
    """Return ``typer._click``'s exception class ``name``, or ``None`` if absent.

    Looks in the vendored ``exceptions`` submodule first, then the package
    root, and never touches an attribute it has not confirmed exists.
    """
    module = getattr(typer_core, "_click", None)
    if module is None:
        return None
    for holder in (getattr(module, "exceptions", None), module):
        candidate = getattr(holder, name, None) if holder is not None else None
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            return candidate
    return None


def _exception_classes(*candidates: type[BaseException] | None) -> tuple[type[BaseException], ...]:
    """Deduplicate ``candidates`` into an ``except``-clause tuple, dropping ``None``."""
    classes: list[type[BaseException]] = []
    for candidate in candidates:
        if candidate is not None and candidate not in classes:
            classes.append(candidate)
    return tuple(classes)


_CLICK_USAGE_ERRORS = _exception_classes(click.UsageError, _vendored_click_exception("UsageError"))
_CLICK_ABORTS = _exception_classes(click.Abort, typer.Abort, _vendored_click_exception("Abort"))
# ``typer.Exit`` is click's ``Exit`` on typer <= 0.25 and typer's own class on
# >= 0.26, so it covers the standalone-click spelling in both eras (TID251).
_EXIT = _exception_classes(typer.Exit, _vendored_click_exception("Exit"))


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
    # #3548 (fail-loud / silent-drop, epics #3410/#3549): the retired
    # ``data or {"message": message}`` expression DROPPED the human-readable
    # ``message`` whenever a caller passed truthy structured ``data`` — silencing
    # 16 of 33 call sites, preferentially the most actionable errors. Merge the
    # explanation INTO the payload so BOTH reach the operator; ``message`` (the
    # param, the canonical explanation) is guaranteed present and last-wins over
    # any caller-supplied ``data["message"]``. The two callers that seed their own
    # ``data["message"]`` (the read-path seam, and the LANE_ALLOCATION_FAILED site
    # via ``StructuredError.to_dict()``) both pass the identical ``str(exc)`` the
    # param already carries, so param-wins never destroys distinct information — it
    # only guarantees the explanation is never dropped. The structured
    # ``data["error_code"]`` those callers carry is untouched (NFR-003).
    payload = {**(data or {}), "message": message}
    envelope = make_envelope(
        command=command,
        success=False,
        data=payload,
        error_code=error_code,
    )
    _emit(envelope)
    raise typer.Exit(1)


def _fail_wp_not_found(cmd: str, wp: str, mission: str) -> NoReturn:
    """The ONE ``WP_NOT_FOUND`` emission (S1192 5×; locks error-surface parity)."""
    _fail(cmd, "WP_NOT_FOUND", f"Work package '{wp}' not found in {mission}")


def _parse_policy_or_fail(cmd: str, policy: str) -> dict:
    """Parse+validate a ``--policy`` JSON string, or ``_fail`` (NoReturn) on invalid JSON.

    The ONE ``POLICY_VALIDATION_FAILED`` emission (WP03/#3281 campsite): before
    this extraction, ``start_implementation``'s required-policy parse and
    ``transition``'s two (required + optional) policy-parse blocks each
    duplicated the identical try/``parse_and_validate_policy``/except/``_fail``
    shape. Folding them into one call keeps ``transition`` at its pre-WP03
    complexity (14) after this WP adds the post-materialize ancestry gate,
    rather than pushing it over the Sonar S3776/Ruff C901 ceiling of 15.
    """
    try:
        policy_obj = parse_and_validate_policy(policy)
    except ValueError as exc:
        _fail(cmd, "POLICY_VALIDATION_FAILED", str(exc))
    return policy_to_dict(policy_obj)


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
    ONLY the coordination-partition artifacts — the status views
    (``status.events.jsonl`` / ``status.json``) and the accept/review matrices
    (``acceptance-matrix.json`` / ``issue-matrix.md``). (``analysis-report.md`` was
    re-homed COORD→PRIMARY, FR-003 coord-commit-integrity, so it is NOT here.)
    Reading ``lanes.json`` or
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

    return placement_seam(main_repo_root, mission_slug).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)


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
    delete_branch: bool | None,
    remove_worktree: bool | None,
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
        raise RuntimeError(f"Planning-artifact closeout failed with exit code {exc.exit_code}") from exc


def _resolve_lane_merge_retention(
    main_repo_root: Path,
    mission_slug: str,
    *,
    delete_branch: bool | None,
    remove_worktree: bool | None,
) -> tuple[RetentionDecision, bool]:
    """Resolve the retention decision + mission-branch-deletable flag (C-007/T010).

    ``_execute_lane_merge`` is a genuine SECOND deletion implementation (not a
    passthrough to ``merge/executor.py``), so NFR-003 ("all cleanup paths")
    requires it to route through the same
    :func:`~specify_cli.core.paths.resolve_merge_retention` authority rather
    than deleting unconditionally. Mirrors the executor's topology-aware
    coupling (#3131 T008 / INV-2): for a coord-topology mission (its primary
    meta.json carries a ``coordination_branch`` key) the mission/coordination
    branch is only deletable when BOTH ``delete_branch`` and
    ``remove_worktree`` resolve True (``teardown_coordination``); for a
    non-coord mission it stays keyed to ``delete_branch`` alone.
    """
    from mission_runtime import MissionArtifactKind, placement_seam
    from specify_cli.core.paths import resolve_merge_retention
    from specify_cli.mission_metadata import load_meta_or_empty

    primary_meta_dir = placement_seam(main_repo_root, mission_slug).read_dir(
        MissionArtifactKind.PRIMARY_METADATA
    )
    retention = resolve_merge_retention(
        primary_meta_dir,
        explicit_delete_branch=delete_branch,
        explicit_remove_worktree=remove_worktree,
    )
    is_coord = "coordination_branch" in load_meta_or_empty(primary_meta_dir)
    mission_branch_deletable = (
        retention.teardown_coordination if is_coord else retention.delete_branch
    )
    return retention, mission_branch_deletable


def _apply_lane_merge_cleanup(
    main_repo_root: Path,
    mission_slug: str,
    lanes_manifest: LanesManifest,
    *,
    retention: RetentionDecision,
    mission_branch_deletable: bool,
) -> None:
    """Worktree removal + lane/mission branch deletion, gated on the RESOLVED
    retention decision (#3131 T010) — extracted from ``_execute_lane_merge``
    to stay under the complexity ceiling; not a passthrough (see there)."""
    from specify_cli.core.git_ops import run_command
    from specify_cli.lanes.branch_naming import lane_branch_name, worktree_path
    from specify_cli.lanes.compute import is_planning_lane

    if retention.remove_worktree:
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

    # LANE branches stay keyed to the plain resolved ``delete_branch`` (no
    # topology coupling — only the mission/coordination branch is coupled).
    if retention.delete_branch:
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

    # MISSION/coordination branch: topology-aware (#3131 T008/T010 parity —
    # see ``_resolve_lane_merge_retention``).
    if mission_branch_deletable:
        run_command(
            ["git", "branch", "-D", lanes_manifest.mission_branch],
            cwd=main_repo_root,
            check_return=False,
        )


def _execute_lane_merge(
    main_repo_root: Path,
    mission_dir: Path,
    mission_slug: str,
    target_branch: str,
    *,
    strategy: str,
    push: bool,
    delete_branch: bool | None,
    remove_worktree: bool | None,
) -> None:
    """Execute the lane-based merge flow without emitting console prose."""
    from specify_cli.cli.commands.merge import _mark_wp_merged_done
    from specify_cli.core.git_ops import has_remote, run_command
    from specify_cli.lanes.compute import is_planning_artifact_only
    from specify_cli.lanes.merge import consolidate_lane_into_mission, integrate_mission_into_target
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

    # #3131 C-007/T010: resolve once, before any gate/merge work, so the
    # cleanup gates below never delete unconditionally.
    retention, mission_branch_deletable = _resolve_lane_merge_retention(
        main_repo_root,
        mission_slug,
        delete_branch=delete_branch,
        remove_worktree=remove_worktree,
    )

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
        lane_result = consolidate_lane_into_mission(main_repo_root, mission_slug, lane.lane_id, lanes_manifest)
        if not lane_result.success:
            raise RuntimeError("; ".join(lane_result.errors) or f"Lane {lane.lane_id} merge failed.")

    mission_result = integrate_mission_into_target(
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

    # #3131 T010: gated on the RESOLVED decision, not the raw (possibly unset)
    # caller args — a retaining mission's branches/worktree survive.
    _apply_lane_merge_cleanup(
        main_repo_root,
        mission_slug,
        lanes_manifest,
        retention=retention,
        mission_branch_deletable=mission_branch_deletable,
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
    wp_lanes = {dep_id: wp_state_for(state.get("lane", Lane.PLANNED)).lane for dep_id, state in wp_states.items()}

    ready_wps = []
    for wp_id, deps in dep_graph.items():
        wp_snapshot = wp_states.get(wp_id, {})
        lane = wp_snapshot.get("lane", Lane.PLANNED)
        state = wp_state_for(lane)
        if state.progress_bucket() != "not_started":
            continue

        # Advisory display parity (FR-009): a canceled-with-operator-provenance
        # dependency is a documented removal, so surface its dependent as ready
        # rather than blocked. `wp_states` is the reduced snapshot already read
        # above, so this reuses the authoritative provenance with no extra I/O.
        readiness = dependency_readiness_for_wp(wp_id, deps, wp_lanes, provenance=wp_states)

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
    """Back-compat delegator to the hoisted single base-ref authority.

    The lane-base resolution now lives with the shared ``for_review`` gate
    (:func:`specify_cli.lanes.for_review_gate.resolve_lane_base_ref`) so the gate
    leaf and this surface's workspace resolvers consult ONE implementation. Kept
    as a module-level name for the two workspace resolvers below (and existing
    callers) that already reference it.
    """
    from specify_cli.lanes.for_review_gate import resolve_lane_base_ref

    return resolve_lane_base_ref(main_repo_root, mission, manifest)


def _enforce_claim_ancestry(
    cmd: str,
    main_repo_root: Path,
    mission: str,
    mission_dir: Path,
    wp: str,
    workspace_path: Path,
) -> None:
    """POST-materialize claim-ancestry gate (C-WP03/FR-007/C-005) -- the ONE
    call site shared by both of THIS module's claim paths
    (``start_implementation``'s composite and ``transition``'s raw
    ``--to claimed``), boundary-leak fix: the allocator's reuse-path self-heal
    already reached ``orchestrator_api`` via ``_resolve_start_workspace``
    (always calls ``allocate_lane_worktree``), but the ancestry GATE did not.

    Delegates the predicate + self-heal-retry contract to
    :func:`specify_cli.lanes.implement_support.resolve_claim_ancestry_gate` --
    the same shared helper the CLI seam (``workflow.py``'s ``implement()``)
    calls -- so this module and the CLI can never independently diverge on
    the ancestry decision. Fails with the structured ``ANCESTRY_NOT_ESTABLISHED``
    envelope (never a bare exception) so an external orchestrator gets the
    same contract every other claim-time refusal here already provides.
    """
    from specify_cli.lanes.implement_support import resolve_claim_ancestry_gate

    result = resolve_claim_ancestry_gate(main_repo_root, mission, mission_dir, wp, workspace_path)
    if result.ok:
        return
    _fail(
        cmd,
        "ANCESTRY_NOT_ESTABLISHED",
        (
            f"cannot claim {wp}: ancestry could not be established after "
            f"self-heal for: {', '.join(result.missing_refs)}"
        ),
        {
            **_mission_identity_payload(mission_dir),
            "wp_id": wp,
            "missing_refs": list(result.missing_refs),
        },
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
        return _StartWorkspace(workspace_path=str(_wt_path(main_repo_root, mission, mission_id=None, lane_id=wp)))
    return manifest, lane


def _resolve_start_workspace(cmd: str, main_repo_root: Path, mission: str, mission_dir: Path, wp: str) -> _StartWorkspace:
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
        UnhonorableBaseError,
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
        UnhonorableBaseError,
        RuntimeError,
    ) as exc:
        # NFR-004: UnhonorableBaseError carries a machine-readable error_code
        # (and route/wp_id/base) via to_dict() — merge it into the data
        # payload so a caller can branch on data["error_code"] ==
        # "UNHONORABLE_BASE" rather than substring-matching the message. The
        # top-level envelope error_code stays "LANE_ALLOCATION_FAILED" (the
        # generic allocation-failure surface); to_dict() is a no-op {} for
        # the other exception types in this tuple, which lack it.
        _fail(
            cmd,
            "LANE_ALLOCATION_FAILED",
            str(exc),
            # #2512: include the refusal reason in the data payload so the
            # orchestrator can surface a diagnostic without parsing the envelope
            # message string.  The message field already carries str(exc) but is
            # not structurally queryable; "reason" makes the cause machine-readable.
            {
                **_mission_identity_payload(mission_dir),
                "wp_id": wp,
                "reason": str(exc),
                **(exc.to_dict() if isinstance(exc, UnhonorableBaseError) else {}),
            },
        )

    # _fail is NoReturn (always raises typer.Exit), so this is reached only on the
    # success path, where worktree_path / lane_branch are bound.
    return _StartWorkspace(
        workspace_path=str(worktree_path),
        lane_id=lane.lane_id,
        lane_branch=lane_branch,
        lane_base_ref=_lane_base_ref(main_repo_root, mission, manifest),
    )


def _resolve_existing_workspace(main_repo_root: Path, mission: str, wp: str) -> _StartWorkspace:
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

    policy_dict = _parse_policy_or_fail(cmd, policy)

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    wp_path = _resolve_wp_file(_planning_read_dir(main_repo_root, mission) / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
        return

    from specify_cli.core.dependency_graph import dependency_readiness_for_wp, parse_wp_dependencies
    from specify_cli.status import reduce
    from specify_cli.status import read_events

    # Reduce once off the same (coord-aware) status surface the lane map already
    # reads, so the provenance map threaded into the gate is consistent with the
    # lanes it decides against.
    _snapshot = reduce(read_events(mission_dir))
    wp_lanes = {
        wp_id: state.get("lane", Lane.PLANNED)
        for wp_id, state in _snapshot.work_packages.items()
    }
    # Only gate the not-yet-started claim transition. Re-invoking start-implementation
    # on a WP that is already in_progress/for_review/.../approved is a no-op resume
    # in the lifecycle layer and must not be rejected just because a dependency later
    # regressed out of approved/done.
    _self_lane = wp_state_for(wp_lanes.get(wp, Lane.PLANNED)).lane
    if _self_lane in (Lane.PLANNED, Lane.CLAIMED):
        # Thread per-dependency provenance (FR-009): start-implementation is the
        # external-API CLAIM gate (mutating planned→claimed→in_progress), the
        # equivalent of implement.py's `_ensure_wp_claim_preconditions`. Without
        # this a dependent of a canceled-with-operator-provenance WP reproduces
        # the #2945 strand on the orchestrator-api claim path.
        dependency_readiness = dependency_readiness_for_wp(
            wp,
            parse_wp_dependencies(wp_path),
            wp_lanes,
            provenance=_snapshot.work_packages,
        )
        if not dependency_readiness.satisfied:
            blocked = ", ".join(dependency_readiness.unsatisfied)
            _fail(
                cmd,
                "DEPENDENCIES_NOT_SATISFIED",
                (f"dependencies_not_satisfied: {wp} depends on {blocked}; all dependencies must be approved or done before implementation can start"),
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

    # Seam C-005 (#3281/FR-007): POST-materialize, after allocation/self-heal
    # above, BEFORE the claim transition below emits any status event. Never
    # move this above ``_resolve_start_workspace`` -- see
    # ``_enforce_claim_ancestry``'s docstring for the deadlock hazard.
    _enforce_claim_ancestry(cmd, main_repo_root, mission, mission_dir, wp, Path(workspace_path))

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


def _enforce_for_review_commit_gate(cmd: str, main_repo_root: Path, mission: str, mission_dir: Path, wp: str, force: bool) -> None:
    """Reject an in_progress->for_review transition that has no commit on the lane.

    Thin orchestrator adapter over the shared, surface-neutral gate leaf
    (:func:`specify_cli.lanes.for_review_gate.evaluate_for_review_gate`): the leaf
    decides (returning a :class:`GateDecision`) and THIS surface renders the
    envelope ``_fail`` from that decision. The envelope (``NoReturn``) never
    leaks into the leaf, so ``agent status emit`` (WP09) can consume the same
    gate and render its own CLI error. No-ops when bypassed (``--force``) or when
    the gate does not apply (no lanes.json, or the WP is not in any lane).
    """
    from specify_cli.lanes.for_review_gate import (
        GateDecision,
        evaluate_for_review_gate,
    )

    decision: GateDecision = evaluate_for_review_gate(
        main_repo_root, mission, wp, force=force
    )
    if not decision.passed:
        _fail(
            cmd,
            "TRANSITION_REJECTED",
            decision.reason,
            {
                **_mission_identity_payload(mission_dir),
                "wp_id": wp,
                "lane_id": decision.lane_id,
            },
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
    review_result_json: str = typer.Option(
        None,
        "--review-result-json",
        help="JSON structured review outcome for transitions from in_review",
    ),
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
        policy_dict = _parse_policy_or_fail(cmd, policy)
    elif policy:
        # Optional policy for non-run-affecting lanes
        policy_dict = _parse_policy_or_fail(cmd, policy)

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

    review_result: ReviewResult | None = None
    if review_result_json is not None:
        try:
            review_result = parse_review_result_json(review_result_json)
        except ValueError as exc:
            _fail(cmd, "USAGE_ERROR", str(exc))
            return

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    wp_path = _resolve_wp_file(_planning_read_dir(main_repo_root, mission) / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
        return

    if to_lane == Lane.FOR_REVIEW:
        _enforce_for_review_commit_gate(cmd, main_repo_root, mission, mission_dir, wp, force)
    elif to_lane == Lane.CLAIMED:
        # Seam C-005 (#3281/FR-007): early-return-equivalent for every OTHER
        # target lane -- this predicate only ever runs for a raw `--to
        # claimed` transition. Allocates/self-heals the lane workspace
        # (mirrors start_implementation's own `_resolve_start_workspace`
        # call) and enforces ancestry BEFORE the `claimed` event below.
        claim_ws = _resolve_start_workspace(cmd, main_repo_root, mission, mission_dir, wp)
        _enforce_claim_ancestry(
            cmd, main_repo_root, mission, mission_dir, wp, Path(claim_ws.workspace_path)
        )

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
                review_result=review_result,
                subtasks_complete=subtasks_complete,
                implementation_evidence_present=implementation_evidence_present,
                execution_mode="worktree",
                repo_root=main_repo_root,
                policy_metadata=policy_dict,
            ),
            ensure_sync_daemon=False,
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


def _resolve_history_commit_args(main_repo_root: Path, mission: str) -> tuple[Path, CommitTarget]:
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
        placement = resolve_placement_only(main_repo_root, mission, kind=MissionArtifactKind.WORK_PACKAGE_TASK)
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
    """Append a history entry via an ``InnerStateChanged`` ``note`` annotation.

    WP08 / FR-007 / T031: this cross-package (ACL-boundary) writer no longer
    mutates the WP prompt file's ``## Activity Log`` section directly -- it
    emits a ``note``-append delta through WP01's ``emit_inner_state_changed``.
    The write target is the coord-aware STATUS-partition mission directory
    (:func:`_resolve_mission_dir_or_fail` -- the SAME seam every other STATUS
    read/write in this module uses, e.g. ``accept_mission``'s
    ``materialize(mission_dir)``), never a ``Path.cwd()``-derived join
    (C-003 / #2647 -- see the SC-008 test).
    """
    cmd = "append-history"

    main_repo_root = _get_main_repo_root()
    # Existence/identity gate via the coord-aware read seam (typed miss
    # envelope). This is also the STATUS-partition mission directory the
    # annotation below is emitted into.
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    # FR-003 / T013: the WP prompt file is a WORK_PACKAGE_TASK (primary kind),
    # so its EXISTENCE is checked on the PRIMARY checkout -- never the
    # coordination worktree (the planning→coord transit is removed, C-005).
    # Resolve it through the canonical per-kind read seam (``_planning_read_dir``
    # → ``resolve_planning_read_dir``, the same seam the sibling planning reads
    # use), NOT a raw handle-blind ``primary_feature_dir_for_mission`` call: that
    # primitive composes the handle verbatim, so a bare ``mid8`` / full ULID /
    # numeric handle would land on a DIVERGENT dir than where the WP prompt
    # actually lives (the #2136/#2164 write/placement divergence). The seam
    # folds the handle to its canonical ``<slug>-<mid8>`` dir for every form
    # (and propagates ``MissionSelectorAmbiguous`` -- no silent pick).
    primary_mission_dir = _planning_read_dir(main_repo_root, mission)
    wp_path = _resolve_wp_file(primary_mission_dir / "tasks", wp)
    if wp_path is None:
        _fail_wp_not_found(cmd, wp, mission)
        return

    from specify_cli.status import WPInnerStateDelta
    from specify_cli.status import StoreError
    from specify_cli.status import emit_inner_state_changed

    timestamp = now_utc_stamp()
    # Byte-identical to the historical rendered Activity Log line (FR-007
    # no-content-loss): the note carries the fully-formatted entry so no
    # information is lost even before a dedicated notes-render surface lands.
    entry_text = f"- [{timestamp}] {actor}: {note}"

    try:
        emit_inner_state_changed(
            mission_dir,
            wp,
            WPInnerStateDelta(note=entry_text),
            actor=actor,
            mission_slug=mission,
            repo_root=main_repo_root,
        )
    except (ValueError, StoreError) as exc:
        # A failed emit still surfaces the orchestrator-api's own structured
        # envelope (never a bare traceback) -- ``_fail`` is typed ``NoReturn``.
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
        if wp_state_for(snapshot.work_packages.get(wp_id, {}).get("lane", Lane.PLANNED)).lane not in {Lane.APPROVED, Lane.DONE}
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
    from specify_cli.config.path_conventions import PathConventionsConfigError
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
    except PathConventionsConfigError as exc:
        _fail(
            cmd,
            "MISSION_NOT_READY",
            str(exc),
            {
                "message": str(exc),
                **_mission_identity_payload(mission_dir),
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
        # #3131 C-007/T010: unset (None) so the mission's meta.json retention
        # policy governs — this CLI has no --delete-branch/--remove-worktree
        # flags of its own, so hardcoding True/True here silently bypassed a
        # retaining mission's policy every time (the exact NFR-003 gap).
        _execute_lane_merge(
            main_repo_root,
            mission_dir,
            mission,
            preflight.target_branch,
            strategy=strategy,
            push=push,
            delete_branch=None,
            remove_worktree=None,
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


# ── specify / plan / tasks (WP03) ────────────────────────────────────────
#
# Thin, in-process adapters over the SAME JSON-mode service functions the
# host CLI's own ``specify``/``plan``/``tasks`` shims
# (``specify_cli.cli.commands.lifecycle``) already delegate to. NEVER shell
# out to the host CLI: each verb captures the delegate's single ``--json``
# stdout line, then re-emits it (enriched for ``specify``, raw for
# ``plan``/``tasks``) inside the canonical orchestrator-api envelope.


def _extract_json_payload(raw_output: str) -> dict[str, Any] | None:
    """Parse the one JSON object a delegate command printed to its stdout.

    Mirrors ``lifecycle._create_mission_for_specify_json``'s own line-scan
    (first line starting with ``{`` that parses as a JSON object) rather than
    assuming line 1 verbatim -- tolerant of incidental non-JSON stdout noise
    from the delegate without duplicating its parsing logic wholesale.
    """
    for line in raw_output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


# Markers observed in ``create_mission``'s own bare-exception message when a
# second ``specify`` targets a slug/mid8 pairing that already produced an
# identical on-disk mission: the retry's meta.json/spec.md scaffold is
# byte-identical to what is already committed, so the underlying
# ``safe_commit`` sees an empty changeset and raises a plain ``RuntimeError``
# with no ``error_code`` of its own (verified against production behavior --
# see the WP03 tracer entry). This surface classifies that established
# failure into a stable, structured code instead of letting it flatten to a
# generic one.
_MISSION_DUPLICATE_MARKERS = ("nothing to commit", "empty changeset", "already exists")


def _classify_specify_create_error(
    payload: dict[str, Any] | None, raw_output: str
) -> tuple[str, str, dict[str, Any]]:
    """Classify a failed ``specify`` delegate call into ``(error_code, message, data)``.

    A typed upstream ``error_code`` (e.g. ``CharterPackConfigError``,
    ``CoordinationBranchDiverged``) is trusted verbatim. A bare
    ``{"error": ...}`` payload (``MissionCreationError`` / a generic
    ``RuntimeError``) is pattern-matched against the known duplicate-mission
    signature; anything else falls back to a generic, still-structured code
    -- never a bare exception/traceback (this repo's dominant failure mode).
    """
    if payload is None:
        message = raw_output.strip() or "mission creation failed"
        return "MISSION_CREATE_FAILED", message, {"raw_output": raw_output}
    message = str(payload.get("error") or payload.get("message") or "mission creation failed")
    error_code = payload.get("error_code")
    if error_code:
        return str(error_code), message, payload
    lowered = message.lower()
    if any(marker in lowered for marker in _MISSION_DUPLICATE_MARKERS):
        return "MISSION_ALREADY_EXISTS", message, payload
    return "MISSION_CREATE_FAILED", message, payload


def _classify_delegate_error(
    payload: dict[str, Any] | None,
    raw_output: str,
    *,
    fallback_code: str,
    fallback_message: str,
) -> tuple[str, str, dict[str, Any]]:
    """Classify a failed ``plan``/``tasks`` delegate call, trusting any typed
    ``error_code`` the delegate already carries and falling back to a
    verb-specific structured code otherwise -- never a bare exception.
    """
    if payload is None:
        message = raw_output.strip() or fallback_message
        return fallback_code, message, {"raw_output": raw_output}
    message = str(payload.get("error") or payload.get("message") or fallback_message)
    error_code = payload.get("error_code")
    if error_code:
        return str(error_code), message, payload
    return fallback_code, message, payload


# ── Command 10: specify ──────────────────────────────────────────────────


@app.command(name="specify")
def specify(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    mission_type: str = typer.Option(..., "--mission-type", help="Mission type (e.g., software-dev)"),
    topology: MissionTopology | None = typer.Option(
        None,
        "--topology",
        help=(
            "Create-time mission shape: single_branch | lanes | coord | "
            "lanes_with_coord. Default: context-derived (matches the host "
            "CLI's own --topology default)."
        ),
    ),
    policy: str = typer.Option(None, "--policy", help=_HELP_POLICY),
) -> None:
    """Create a mission scaffold, matching the host CLI's enriched ``specify --json`` contract.

    In-process only (FR-001): calls
    ``specify_cli.cli.commands.lifecycle._create_mission_for_specify_json``,
    the SAME enrichment step the host CLI's ``--json`` path runs (adds
    ``scaffold_only``/``spec_state``/``next_action``/``next_step`` on top of
    ``agent_feature.create_mission``'s raw payload) -- never the unenriched
    payload one layer beneath it.
    """
    cmd = "specify"

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for specify")
        return
    _parse_policy_or_fail(cmd, policy)

    from specify_cli.cli.commands.lifecycle import _create_mission_for_specify_json

    capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(capture):
            _create_mission_for_specify_json(mission, mission_type, topology)
    except typer.Exit:
        raw_output = capture.getvalue()
        payload = _extract_json_payload(raw_output)
        error_code, message, error_data = _classify_specify_create_error(payload, raw_output)
        _fail(cmd, error_code, message, error_data)
        return

    raw_output = capture.getvalue()
    payload = _extract_json_payload(raw_output)
    if payload is None:
        _fail(
            cmd,
            "MISSION_CREATE_FAILED",
            "specify produced no parseable JSON payload",
            {"raw_output": raw_output},
        )
        return
    # Belt-and-brace, matching ``plan``/``tasks``/``check_prerequisites``
    # (~2320/2383/2536): ``_create_mission_for_specify_json``'s own payload
    # already carries ``mission_slug`` (verified against production), so this
    # is a structural no-op on the normal path -- NOT business-payload
    # enrichment, it fills the ONE transport-contract identity field
    # (``upstream_contract.json``'s ``required_payload_fields``) every
    # orchestrator-api response must carry, only when the delegate omits it.
    #
    # Deliberately NOT a plain ``setdefault("mission_slug", mission)``: the
    # raw ``mission`` input is the PRE-mid8-suffix handle
    # (``mission_dir_name`` appends ``-<mid8>`` at creation --
    # ``lanes/branch_naming.py:488``), so it is not itself the canonical
    # slug once the mission exists on disk. Only resolve (and pay the extra
    # disk lookup) in the fallback branch, using the SAME
    # ``_mission_identity_payload(mission_dir)["mission_slug"]`` the siblings
    # read post-resolution -- the real, mid8-suffixed value -- rather than a
    # guess that could be wrong. Never overwrites a delegate-supplied value.
    if "mission_slug" not in payload:
        main_repo_root = _get_main_repo_root()
        mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)
        payload["mission_slug"] = _mission_identity_payload(mission_dir)["mission_slug"]
    validate_outbound_payload(payload, "orchestrator_api")
    envelope = make_envelope(command=cmd, success=True, data=payload)
    _emit(envelope)


# ── Command 11: plan ─────────────────────────────────────────────────────


@app.command(name="plan")
def plan(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    policy: str = typer.Option(None, "--policy", help=_HELP_POLICY),
) -> None:
    """Scaffold plan.md for a mission -- an unenriched pass-through of ``setup_plan``.

    FR-002 / Clarification 1: deliberately asymmetric with ``specify`` -- the
    host CLI's own ``--json`` path returns ``agent_feature.setup_plan``'s raw
    dict verbatim (``lifecycle.py`` adds no enrichment here), so this verb
    does the same. Do not add fields ``setup_plan`` does not already return.
    """
    cmd = "plan"

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for plan")
        return
    _parse_policy_or_fail(cmd, policy)

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    from specify_cli.cli.commands.agent import mission as agent_feature

    capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(capture):
            agent_feature.setup_plan(feature=mission, json_output=True)
    except typer.Exit:
        raw_output = capture.getvalue()
        payload = _extract_json_payload(raw_output)
        error_code, message, error_data = _classify_delegate_error(
            payload,
            raw_output,
            fallback_code="PLAN_SETUP_FAILED",
            fallback_message="plan scaffolding failed",
        )
        _fail(cmd, error_code, message, error_data)
        return

    raw_output = capture.getvalue()
    payload = _extract_json_payload(raw_output)
    if payload is None:
        _fail(
            cmd,
            "PLAN_SETUP_FAILED",
            "plan produced no parseable JSON payload",
            {"raw_output": raw_output},
        )
        return
    # ``setup_plan``'s own payload already carries ``mission_slug`` (verified
    # against production); ``setdefault`` is a structural no-op belt-and-brace
    # here -- this is NOT business-payload enrichment (T011's asymmetry bar),
    # it fills the ONE transport-contract identity field
    # (``upstream_contract.json``'s ``required_payload_fields``) every
    # orchestrator-api response must carry, using the already-resolved input
    # identity -- never overwriting a delegate-supplied value.
    payload.setdefault("mission_slug", _mission_identity_payload(mission_dir)["mission_slug"])
    validate_outbound_payload(payload, "orchestrator_api")
    envelope = make_envelope(command=cmd, success=True, data=payload)
    _emit(envelope)


# ── Command 12: tasks ────────────────────────────────────────────────────


@app.command(name="tasks")
def tasks(
    mission: str = typer.Option(..., "--mission", help=_HELP_MISSION_SLUG),
    policy: str = typer.Option(None, "--policy", help=_HELP_POLICY),
) -> None:
    """Finalize WP task metadata -- an unenriched pass-through of ``finalize_tasks``.

    FR-003 / Clarification 1: same deliberate asymmetry as ``plan`` -- the
    host CLI's own ``--json`` path returns ``agent_feature.finalize_tasks``'s
    raw dict verbatim, so this verb does the same.
    """
    cmd = "tasks"

    if not policy:
        _fail(cmd, "POLICY_METADATA_REQUIRED", "--policy is required for tasks")
        return
    _parse_policy_or_fail(cmd, policy)

    main_repo_root = _get_main_repo_root()
    mission_dir = _resolve_mission_dir_or_fail(cmd, main_repo_root, mission)

    from specify_cli.cli.commands.agent import mission as agent_feature

    capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(capture):
            agent_feature.finalize_tasks(feature=mission, json_output=True)
    except typer.Exit:
        raw_output = capture.getvalue()
        payload = _extract_json_payload(raw_output)
        error_code, message, error_data = _classify_delegate_error(
            payload,
            raw_output,
            fallback_code="TASKS_FINALIZE_FAILED",
            fallback_message="tasks finalization failed",
        )
        _fail(cmd, error_code, message, error_data)
        return

    raw_output = capture.getvalue()
    payload = _extract_json_payload(raw_output)
    if payload is None:
        _fail(
            cmd,
            "TASKS_FINALIZE_FAILED",
            "tasks produced no parseable JSON payload",
            {"raw_output": raw_output},
        )
        return
    # finalize_tasks' raw payload does NOT carry ``mission_slug`` (verified
    # against production) -- unlike ``plan``, this is a genuine gap the
    # transport contract's ``required_payload_fields`` requires filling. Same
    # non-enrichment rationale as ``plan`` above: fills the one identity field
    # from the already-resolved input, adds nothing else.
    payload.setdefault("mission_slug", _mission_identity_payload(mission_dir)["mission_slug"])
    validate_outbound_payload(payload, "orchestrator_api")
    envelope = make_envelope(command=cmd, success=True, data=payload)
    _emit(envelope)


__all__ = ["app"]
