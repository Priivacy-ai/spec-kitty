"""Task workflow commands for AI agents."""

# ⚠️ GOD-MODULE (tracked for decomposition — do NOT add new responsibilities here).
# This file is an oversized "god module" (~4500 LOC, maxCC ~178). Extract cohesive
# seams into dedicated modules instead of growing this one.
# De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2058

from __future__ import annotations

from specify_cli.core.constants import (
    KITTY_SPECS_DIR,
)
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
    resolve_feature_dir_for_mission,
    resolve_planning_read_dir,
)
import contextlib
import json
import logging
from kernel._safe_re import re
import subprocess
import traceback
from datetime import datetime, UTC
from pathlib import Path

import typer
from rich.console import Console
from typing import Annotated

from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.sync.events import (
    emit_history_added,
    emit_error_logged,
)

from specify_cli.coordination.status_transition import (
    emit_status_transition_transactional,
    read_events_transactional,
)
from specify_cli.status import Lane, StatusEvent, TransitionRequest
from specify_cli.status import is_dossier_snapshot as _is_dossier_snapshot
from specify_cli.status import PROGRESS_SEMANTICS, compute_done_percentage, compute_weighted_progress
from specify_cli.status import resolve_lane_alias
from specify_cli.status import EventPersistenceError, EVENTS_FILENAME

from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.lanes.persistence import MissingLanesError
from specify_cli.core.paths import locate_project_root, get_main_repo_root, is_worktree_context
from specify_cli.core.paths import get_feature_target_branch
from specify_cli.core.paths import get_status_read_root
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.mission import get_mission_type
from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
)
from specify_cli.coordination.commit_router import commit_for_mission
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.status import feature_status_lock
from specify_cli.core.agent_config import get_auto_commit_default
from specify_cli.status import bootstrap_canonical_state
from specify_cli.core.utils import write_text_within_directory
from specify_cli.workspace.context import get_normalized_wp, resolve_workspace_for_wp


def resolve_primary_branch(repo_root: Path) -> str:
    """Resolve the primary branch name (main, master, etc.).

    Delegates to the centralized implementation in core.git_ops.

    Returns:
        Detected primary branch name.
    """
    from specify_cli.core.git_ops import resolve_primary_branch as _resolve

    return _resolve(repo_root)


from specify_cli.task_utils import (
    append_activity_log,
    build_document,
    ensure_lane,
    extract_scalar,
    locate_work_package,
    set_scalar,
    split_frontmatter,
)

# WP02 (#2058): tasks.md/manifest parsing + WP-id resolution helpers and the
# shared result vocabulary live in the ``tasks_outline`` seam. Imported here so
# existing ``from ...agent.tasks import <name>`` call sites keep working.
from specify_cli.cli.commands.agent.tasks_outline import (
    TASKS_MD_FILENAME,
    TaskIdResolutionFormat,
    TaskIdResolutionOutcome,
    TaskIdResult,
    _INLINE_SUBTASKS_RE,
    # WP03 (#2058): the pipe-table row parsers moved to ``tasks_materialization``
    # along with their only former internal caller. They remain re-exported here
    # (explicit ``as`` form) because existing tests import them from ``tasks``.
    _is_pipe_table_task_row as _is_pipe_table_task_row,
    _normalize_task_id_input,
    _parse_pipe_table_header as _parse_pipe_table_header,
    _resolve_history_wp_id,
    _resolve_wp_id,
)

# WP03 (#2058): frontmatter/file persistence + markdown-row mutation helpers
# live in the ``tasks_materialization`` seam. Re-exported here (out-of-map edit:
# tasks.py is owned by WP07) so existing ``from ...agent.tasks import <name>``
# call sites (workflow.py, implement.py, tests) keep working unchanged. Names not
# referenced inside this module use the explicit ``as`` re-export form so ruff
# recognizes the intentional public re-export and does not flag F401.
from specify_cli.cli.commands.agent.tasks_materialization import (
    _collect_status_artifacts,
    _materialize_inline_subtask_status as _materialize_inline_subtask_status,
    _persist_inline_subtask_status,
    _persist_review_artifact_override,
    _persist_review_feedback as _persist_review_feedback,
    _resolve_checkbox,
    _resolve_pipe_table,
    _resolve_wp_slug,
    _update_pipe_table_status as _update_pipe_table_status,
)

# WP06 (#2058): issue-matrix evaluation, review-verdict, the self-review
# fallback guard, the stale/stalled review status annotations, and the
# review-readiness validator live in the ``tasks_parsing_validation`` seam.
# Re-exported here (explicit ``as`` form where not referenced internally) so
# existing ``from ...agent.tasks import <name>`` call sites and the
# ``@patch("...agent.tasks.<name>")`` contracts keep working unchanged. The
# review-readiness validator is wrapped (not aliased) below so its
# ``tasks``-resident collaborators stay injectable from this namespace.
from specify_cli.cli.commands.agent.tasks_parsing_validation import (
    _VALID_VERDICTS as _VALID_VERDICTS,
    _apply_review_status_flags as _apply_review_status_flags,
    _get_latest_review_cycle_verdict,
    _issue_matrix_approval_blocker,
    _self_review_fallback_option_error,
    _validate_ready_for_review as _seam_validate_ready_for_review,
)

# WP04: dependency/cycle validation, lane-metadata helpers, and the
# finalize_tasks validation core live in the ``tasks_finalize_validation`` seam.
# The lane helpers are re-imported here so existing
# ``from ...agent.tasks import <name>`` call sites keep working.
from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    _is_backward_transition,
    _lane_targets_for_emit,
    _read_transactional_wp_lane,
    _wp_lane_from_status_events,
    compute_wp_frontmatter_updates,
    detect_dependency_conflicts,
    detect_dependency_cycles,
    read_existing_frontmatter,
    validate_wp_coverage,
)

# WP05 (#2058): dependent-gating / dependency-warning glue lives in the
# ``tasks_dependency_graph`` seam. Re-imported here so existing
# ``from ...agent.tasks import <name>`` call sites and ``monkeypatch.setattr``
# targets keep working. NOTE: the ``core.dependency_graph`` call sites used by
# ``validate_workflow`` deliberately stay in this module (no relocation, no cycle).
from specify_cli.cli.commands.agent.tasks_dependency_graph import (
    _behind_commits_touch_only_planning_artifacts,
    _check_dependent_warnings,
    compute_incomplete_dependents,
)

# Re-exported lane helpers consumed by tests via
# ``from ...agent.tasks import <name>`` even though tasks.py uses them only
# indirectly; listed in ``__all__`` so the re-export is explicit (C-007).
__all__ = [
    "_behind_commits_touch_only_planning_artifacts",
    "_check_dependent_warnings",
    "_lane_targets_for_emit",
    "_wp_lane_from_status_events",
    "app",
    "compute_incomplete_dependents",
]

logger = logging.getLogger(__name__)
SPEC_MD_FILENAME = "spec.md"
UTC_SECOND_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _review_currency_check_branch(
    *,
    main_repo_root: Path,
    mission_slug: str,
    target_branch: str,
    workspace: object | None,
) -> str:
    context = getattr(workspace, "context", None)
    base_branch = getattr(context, "base_branch", None)
    if base_branch:
        return str(base_branch)

    try:
        # base-ref read under coord topology — coord kind preserves G-2
        # (write-surface-coherence WP02 / T031 site 3): review-currency compares
        # against the coordination BASE ref under coord topology. STATUS_STATE keeps
        # the coord ref; a primary kind would read the primary ref as the base and
        # corrupt the currency comparison.
        placement = resolve_placement_only(
            main_repo_root, mission_slug, kind=MissionArtifactKind.STATUS_STATE
        )
    except Exception as exc:  # noqa: BLE001 -- legacy fixtures keep target-branch fallback
        logger.debug("Could not resolve review currency placement: %s", exc)
        return target_branch

    # FR-005 / FR-001b: the coord-vs-primary decision reads the WP02 STORED
    # topology via the ONE canonical predicate, never a per-ref ``.kind``.
    if routes_through_coordination(resolve_topology(main_repo_root, mission_slug)):
        return placement.ref
    return target_branch


def _map_requirements_feature_dir(main_repo_root: Path, mission_slug: str) -> Path:
    """Resolve the WP ``tasks/`` read surface for ``map-requirements`` (#2064).

    Routes through the SAME seam-resolved entry point ``finalize_tasks`` (and the
    rest of ``tasks.py``) use — :func:`resolve_feature_dir_for_mission` (the
    ``resolve_action_context(action="tasks")`` seam) — so the WP-frontmatter read
    cannot diverge from finalize on a coord/flattened topology. Previously this
    command was the lone read path on ``resolve_feature_dir_for_slug``, whose
    slug-only ``mid8_from_slug`` heuristic missed the coord worktree when the
    operator handle carried no mid8 tail, while finalize resolved into it.

    The unified resolver raises ``ActionContextError`` when the directory cannot
    be located; ``map-requirements`` historically surfaced this as its own
    ``Mission directory not found: …`` message via an existence guard on the
    returned path. To preserve that user-facing contract (Risk #1) the typed
    error is translated back into the non-existent candidate directory so the
    caller's existing existence guard fires the unchanged message.
    """
    from mission_runtime import ActionContextError

    try:
        return resolve_feature_dir_for_mission(main_repo_root, mission_slug)
    except ActionContextError:
        return candidate_feature_dir_for_mission(main_repo_root, mission_slug)


def _review_stall_threshold_minutes(repo_root: Path) -> int:
    """Read review.stall_threshold_minutes from .kittify/config.yaml."""
    config_file = repo_root / ".kittify" / "config.yaml"
    if not config_file.exists():
        return 30
    try:
        import yaml  # noqa: PLC0415

        config = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        value = config.get("review", {}).get("stall_threshold_minutes", 30)
        return int(value)
    except (AttributeError, OSError, TypeError, ValueError):
        return 30


def _get_hic_marker(
    agent_profile: str | None,
    repo_root: Path,
    *,
    repo: object | None = None,
) -> str:
    """Return a marker when the work package profile is a human-run sentinel."""
    if not agent_profile:
        return ""

    try:
        from doctrine.agent_profiles.repository import AgentProfileRepository

        profile_repo = repo
        if profile_repo is None:
            built_in_dir = repo_root / "src" / "doctrine" / "agent_profiles" / "built-in"
            profile_repo = AgentProfileRepository(built_in_dir=built_in_dir)

        profile = profile_repo.get(agent_profile)
        if profile and profile.sentinel:
            return "👤 "
    except Exception:
        return ""

    return ""


app = typer.Typer(name="tasks", help="Task workflow commands for AI agents", no_args_is_help=True)

console = Console()


# ---------------------------------------------------------------------------
# FR-015 / C-003 / C-004: review-handoff runtime-state deny-list
# ---------------------------------------------------------------------------
# Spec-kitty writes review-lock.json and other ephemeral runtime state under
# ``.spec-kitty/`` inside each worktree, and merge/status metadata under
# ``.kittify/`` at the repo root. These directories are git-ignored but do
# show up in ``git status --porcelain`` as untracked noise, which historically
# tripped the "uncommitted changes in worktree" guard in
# ``_validate_ready_for_review`` when an external reviewer (the review lock)
# had only just done its job (issue #589).
#
# C-003: this is a *fixed named list*, NOT a pattern match. Do not add
# entries here without explicit spec coverage; re-opening the door to pattern
# matching lets untracked source files silently slip past the guard.
# C-004: paths OUTSIDE this list still reach the blocking branch unchanged,
# so genuine uncommitted implementation work continues to block review handoff.
_RUNTIME_STATE_DENY_LIST: tuple[str, ...] = (".spec-kitty/", ".kittify/")


# ---------------------------------------------------------------------------
# Mission charter-e2e-827-followups-01KQAJA0 / C-006: dossier snapshot exclude
# ---------------------------------------------------------------------------
# The dossier snapshot at <feature_dir>/.kittify/dossiers/<mission>/snapshot-
# latest.json is a mutable derived artifact. Per the EXCLUDE ownership policy
# (single policy — see ``specify_cli.status.preflight``), it must be filtered
# from any preflight that bypasses ``.gitignore`` so the writer's update does
# not self-block the next ``move-task`` transition.
def _filter_runtime_state_paths(porcelain_output: str) -> str:
    """Strip lines whose path falls under spec-kitty's own runtime-state dirs.

    Input is the raw ``git status --porcelain`` output. Each line has the
    format ``XY path`` where ``XY`` is a two-character status code followed by
    a single space. A ``startswith`` check against the fixed deny-list is
    used intentionally (C-003): no regex, no glob expansion, no fuzzy match.

    Dossier ``snapshot-latest.json`` paths are also stripped here per the
    EXCLUDE ownership policy (C-006); the snapshot writer must never
    self-block a transition.

    Returns a newline-joined string with deny-listed entries removed. Lines
    whose path is OUTSIDE the deny list are preserved verbatim so the
    downstream guard still blocks on genuine drift (C-004).
    """
    kept: list[str] = []
    for line in porcelain_output.splitlines():
        if not line.strip():
            continue
        # git status --porcelain format: first 3 chars are "XY " status prefix.
        path_part = line[3:] if len(line) > 3 else line.strip()
        if any(path_part.startswith(prefix) for prefix in _RUNTIME_STATE_DENY_LIST):
            continue
        if _is_dossier_snapshot(path_part):
            continue
        kept.append(line)
    return "\n".join(kept)


def _emit_sparse_session_warning(repo_root: Path, command: str) -> None:
    """Emit the FR-010/FR-019 sparse-checkout session warning once per process.

    Called from every state-mutating tasks handler at command entry so
    reviewers and implementers discover they are operating inside a
    sparse-checkout worktree before they commit partial work. The underlying
    ``warn_if_sparse_once`` helper from WP02 is self-memoizing (first caller
    wins the ``command`` label) and swallows detection errors, so this
    wrapper is safe to call unconditionally and never crashes the command.
    """
    try:
        from specify_cli.git.sparse_checkout import warn_if_sparse_once

        warn_if_sparse_once(repo_root, command=command)
    except Exception as _exc:  # noqa: BLE001 - defensive; must never break CLI
        # FR-010 contract: detection failures must never break the CLI command
        # that invoked this hook. Log to the module logger at debug level so
        # the failure is still traceable without tripping the ``S110`` lint.
        logging.getLogger(__name__).debug(
            "sparse-checkout session warning failed for %s: %s",
            command,
            _exc,
        )


def _ensure_target_branch_checked_out(
    repo_root: Path,
    mission_slug: str,
    json_output: bool,
) -> tuple[Path, str]:
    """Resolve branch context without auto-checkout (respects user's current branch).

    Returns:
        (main_repo_root, current_branch)
    """
    from specify_cli.core.git_ops import get_current_branch, resolve_target_branch

    # Write path: keep main-repo-root resolution so canonical serialization
    # pins to the primary checkout regardless of where the operator stands.
    main_repo_root = get_main_repo_root(repo_root)

    # Check for detached HEAD using robust branch detection
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        raise RuntimeError("Detached HEAD — checkout a branch before continuing")

    # Resolve branch routing (unified logic, no auto-checkout)
    resolution = resolve_target_branch(mission_slug, main_repo_root, current_branch, respect_current=True)

    # Show consistent branch banner
    if not json_output:
        if not resolution.should_notify:
            console.print(f"[bold cyan]Branch:[/bold cyan] {current_branch} (target for this mission)")
        else:
            console.print(f"[bold yellow]Branch:[/bold yellow] on '{resolution.current}', mission targets '{resolution.target}'")

    # Return current branch (no checkout performed)
    return main_repo_root, resolution.current


def _find_mission_slug(
    explicit_mission: str | None = None,
    *,
    json_output: bool = False,
    repo_root: Path | None = None,
) -> str:
    """Require an explicit mission slug (no auto-detection).

    When repo_root is supplied the handle is resolved via the canonical
    mission resolver (resolve_mission_handle), which handles ambiguous
    numeric-prefix handles, mid8 prefixes, and full ULID forms.  The
    resolver calls sys.exit(2) on error so no try/except is needed.

    Args:
        explicit_mission: Mission slug provided via --mission.
        json_output: Propagate to resolver error rendering.
        repo_root: Repository root; if provided, enables canonical resolver.

    Returns:
        Mission slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If mission slug is not provided.
    """
    if not explicit_mission or not explicit_mission.strip():
        err = "--mission <slug> is required"
        if json_output:
            print(json.dumps({"error": err}))
        else:
            console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)

    raw_handle = explicit_mission.strip()
    if repo_root is not None:
        # Write path: keep main-repo-root resolution so canonical serialization
        # pins to the primary checkout regardless of where the operator stands.
        # Note: repo_root from locate_project_root() already resolves to the main
        # checkout; get_main_repo_root() here guards against caller passing a
        # worktree path directly.
        legacy_dir = candidate_feature_dir_for_mission(get_main_repo_root(repo_root), raw_handle)
        if legacy_dir.exists():
            # F-001: the candidate resolver canonicalizes mid8/ULID/numeric
            # handles, so the resolved directory's NAME — not the raw operator
            # handle — is the canonical mission slug downstream consumers need.
            return legacy_dir.name
        try:
            resolved = resolve_mission_handle(raw_handle, repo_root, json_mode=json_output)
            return resolved.mission_slug
        except (SystemExit, typer.Exit):
            if legacy_dir.exists():
                return legacy_dir.name
            raise

    return raw_handle


def _output_result(json_mode: bool, data: dict, success_message: str | None = None):
    """Output result in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        data: Data to output (used for JSON mode)
        success_message: Message to display in human mode
    """
    if json_mode:
        print(json.dumps(data))
    elif success_message:
        console.print(success_message)


def _output_error(json_mode: bool, error_message: str, diagnostic: dict | None = None):
    """Output error in JSON or human-readable format.

    Args:
        json_mode: If True, output JSON; else use Rich console
        error_message: Error message to display
    """
    if json_mode:
        print(json.dumps(diagnostic if diagnostic is not None else {"error": error_message}))
    else:
        console.print(f"[red]Error:[/red] {error_message}")


def _protected_branch_status_commit_error(branch: str, repo_root: Path, command: str) -> str | None:
    # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
    # config+hatch reads happen once; is_protected() is I/O-free.
    if not ProtectionPolicy.resolve(repo_root).is_protected(branch):
        return None
    return (
        f"Refusing to run `{command}` with auto-commit on protected branch "
        f"'{branch}' before mutating status files. Run status commit "
        "operations from an allowed coordination/lane branch, or rerun with "
        "--no-auto-commit when you intentionally want to handle the status "
        "artifact commit manually."
    )


def _coord_topology_active(repo_root: Path, mission_slug: str) -> bool:
    """Return True if the coordination worktree exists for this mission."""
    try:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.lanes.branch_naming import resolve_transaction_mid8
        # Authoritative topology resolver (FR-004/#1918): a coord-worktree lookup
        # needs the REAL mid8 to name its dir. With no declared mission_id/mid8 the
        # seam falls back to the embedded ``<slug>-<mid8>`` tail (genuine slug) and
        # returns "" only for a legacy/flattened mission with no coord topology —
        # exactly the historical mid8_from_slug behaviour for resolvable slugs.
        mid8 = resolve_transaction_mid8(
            mission_slug, mission_id=None, mid8=None, coordination_branch=None
        )
        path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
        return path.exists()
    except Exception:
        return False


def _skip_target_branch_commit(repo_root: Path, mission_slug: str, target_branch: str) -> bool:
    """Return True when the direct WP-file commit to a protected primary must be skipped.

    NOT a routing authority (write-surface-coherence WP02 / T032 / G-1): the
    commit DESTINATION for the WP file is owned solely by the kind authority
    (``resolve_placement_only(kind=WORK_PACKAGE_TASK)``). This flag only decides
    whether to SKIP the direct primary commit in the genuine protected-primary
    case — coord topology active AND the primary ``target_branch`` is protected —
    where committing directly to the protected ref is refused and the status
    transition committed to the coordination branch is authoritative. It selects
    no ref; it suppresses a commit that the protection policy would refuse anyway.
    """
    # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
    # config+hatch reads happen once; is_protected() is I/O-free.
    return (
        _coord_topology_active(repo_root, mission_slug)
        and ProtectionPolicy.resolve(repo_root).is_protected(target_branch)
    )


def _coord_status_events_path(repo_root: Path, mission_slug: str) -> Path | None:
    """Return coord-worktree status event path when coord topology is active."""
    try:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.lanes.branch_naming import mission_dir_name, resolve_transaction_mid8

        # Topology resolver (FR-004): resolve the on-disk mid8 from the embedded
        # ``<slug>-<mid8>`` tail; "" for a legacy/flattened mission (no coord dir).
        mid8 = resolve_transaction_mid8(
            mission_slug, mission_id=None, mid8=None, coordination_branch=None
        )
        if not mid8:
            return None
        # Delegate the idempotent ``<slug>-<mid8>`` compose to the seam so the
        # inline endswith-dedup (the #1949 reinvention WP09 bans) lives only in
        # lanes.branch_naming (FR-010).
        mission_dir = mission_dir_name(mission_slug, mid8=mid8)
        coord_root = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
        if not coord_root.exists():
            return None
        return candidate_feature_dir_for_mission(coord_root, mission_dir) / EVENTS_FILENAME
    except Exception:
        return None


def _status_event_result_fields(event: object | None) -> dict[str, str | None]:
    """Return JSON-safe status event fields for command output."""
    if event is None:
        return {"event_id": None, "to_lane": None}

    event_id = getattr(event, "event_id", None)
    if not isinstance(event_id, str):
        event_id = None

    to_lane = getattr(event, "to_lane", None)
    if to_lane is None:
        to_lane_value = None
    else:
        raw_value = getattr(to_lane, "value", to_lane)
        to_lane_value = raw_value if isinstance(raw_value, str) else str(raw_value)

    return {"event_id": event_id, "to_lane": to_lane_value}


def _mission_identity_payload(feature_dir: Path) -> dict[str, str]:
    identity = resolve_mission_identity(feature_dir)
    return {
        "mission_slug": identity.mission_slug,
        "mission_number": identity.mission_number,
        "mission_type": identity.mission_type,
    }


def _detect_reviewer_name() -> str:
    """Detect reviewer name from git config, with safe fallback."""
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _resolve_git_common_dir(main_repo_root: Path) -> Path:
    """Resolve absolute git common-dir for the repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=main_repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    raw_value = result.stdout.strip()
    if not raw_value:
        raise RuntimeError("Unable to resolve git common directory")
    common_dir = Path(raw_value)
    if not common_dir.is_absolute():
        common_dir = (main_repo_root / common_dir).resolve()
    return common_dir


def _check_unchecked_subtasks(repo_root: Path, mission_slug: str, wp_id: str, _force: bool) -> list[str]:
    """Check for unchecked subtasks in tasks.md for a given WP.

    Args:
        repo_root: Repository root path
        mission_slug: Feature slug (e.g., "010-lane-only-runtime")
        wp_id: Work package ID (e.g., "WP01")
        force: If True, only warn; if False, fail on unchecked tasks

    Returns:
        List of unchecked task IDs (empty if all checked or not found)

    Raises:
        typer.Exit: If unchecked tasks found and force=False
    """
    # Write path: keep main-repo-root resolution so canonical serialization
    # pins to the primary checkout regardless of where the operator stands.
    main_repo_root = get_main_repo_root(repo_root)
    # WP04 / FR-006: ``tasks.md`` is a TASKS_INDEX (primary-partition) artifact —
    # read it from PRIMARY (INV-5) so a coord-topology mission's stale ``-coord``
    # husk cannot shadow the real primary ``tasks.md`` (#2062 read-side close).
    from mission_runtime import MissionArtifactKind

    feature_dir = resolve_planning_read_dir(
        main_repo_root, mission_slug, kind=MissionArtifactKind.TASKS_INDEX
    )
    tasks_md = feature_dir / TASKS_MD_FILENAME

    if not tasks_md.exists():
        return []  # No tasks.md, can't check

    content = tasks_md.read_text(encoding="utf-8")

    # Find canonical subtasks for this WP. Only unchecked rows of the form
    # ``- [ ] T### <desc>`` count as blocking. Validation/procedure/checklist
    # command rows (e.g. ``- [ ] swift test``, ``- [ ] git status --short``),
    # prose, and anything inside fenced code blocks are intentionally ignored —
    # they are not work-package subtasks and must not block a lane transition.
    lines = content.split("\n")
    unchecked: list[str] = []
    in_wp_section = False
    in_code_fence = False

    # Canonical subtask row: ``- [ ] T001 ...``. A ``T`` id of at least three
    # digits is mandatory (``\d{3,}`` so ids past T999 still block).
    canonical_unchecked = re.compile(r"^-\s*\[\s*\]\s*(T\d{3,})\b")

    for line in lines:
        stripped = line.strip()

        # Toggle fenced-code-block state on ``` or ~~~ markers. Task-like lines
        # inside fenced code blocks (examples in implementation notes) must not
        # be treated as real subtasks.
        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            continue

        if in_code_fence:
            continue

        # Check if we entered this WP's section
        if re.search(rf"^#{{2,4}}[^#].*{wp_id}\b", line):
            in_wp_section = True
            continue

        # Check if we entered a different WP section
        if in_wp_section and re.search(r"^#{2,4}[^#].*WP\d{2}\b", line):
            break  # Left this WP's section

        # Look for unchecked canonical task rows in this WP's section
        if in_wp_section:
            unchecked_match = canonical_unchecked.match(stripped)
            if unchecked_match:
                unchecked.append(unchecked_match.group(1))

    return unchecked


def _apply_stale_status_fields(wp: dict, stale_result: object) -> None:
    """Populate canonical and deprecated stale fields from one source of truth."""
    stale_payload = stale_result.stale.to_dict()
    wp["stale"] = stale_payload
    wp["is_stale"] = stale_result.is_stale
    wp["minutes_since_commit"] = stale_payload["minutes_since_commit"]
    wp["worktree_exists"] = stale_result.worktree_exists


def _build_stale_fallback_results(doing_wps: list[dict], error: Exception) -> dict[str, object]:
    """Return per-WP stale fallbacks when stale detection cannot run."""
    from specify_cli.core.stale_detection import StaleCheckResult, StaleState
    from specify_cli.core.stale_detection import PLANNING_ARTIFACT_REPO_ROOT_REASON

    results: dict[str, object] = {}
    for wp in doing_wps:
        wp_id = wp.get("id") or wp.get("work_package_id")
        if not wp_id:
            continue
        workspace_kind = str(wp.get("workspace_kind", "unknown"))
        execution_mode = str(wp.get("execution_mode", ""))
        fallback_reason = (
            PLANNING_ARTIFACT_REPO_ROOT_REASON if workspace_kind == "repo_root" and execution_mode == "planning_artifact" else "stale_detection_unavailable"
        )
        results[wp_id] = StaleCheckResult(
            wp_id=wp_id,
            stale=StaleState(status="not_applicable", reason=fallback_reason),
            workspace_exists=False,
            workspace_kind=workspace_kind,
            error=str(error),
        )
    return results


def _render_stale_status(stale_result: object | None) -> str | None:
    """Return a human-readable stale label for in-progress work packages."""
    if stale_result is None:
        return None

    if stale_result.stale.status == "not_applicable" and stale_result.stale.reason == "planning_artifact_repo_root_shared_workspace":
        return "stale: n/a (repo-root planning work)"

    if getattr(stale_result, "error", None):
        return "stale: unavailable"

    if stale_result.is_stale:
        mins = stale_result.minutes_since_commit
        return f"stale: {mins}m"

    return None


def _validate_ready_for_review(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    force: bool,
    target_lane: str = "for_review",
) -> tuple[bool, list[str]]:
    """Validate that WP is ready for review by checking for uncommitted changes.

    Thin wrapper over the WP06 seam
    (:func:`tasks_parsing_validation._validate_ready_for_review`). The
    ``tasks``-resident collaborators are passed in from this module's live
    globals so the existing ``@patch("...agent.tasks.<name>")`` contracts (e.g.
    ``get_main_repo_root``, ``get_mission_type``, ``get_feature_target_branch``,
    ``resolve_workspace_for_wp``, the git helpers, and ``console``) continue to
    apply unchanged. Behaviour, validation order, error strings, and the
    (bool, list[str]) return shape are preserved exactly.
    """
    return _seam_validate_ready_for_review(
        repo_root,
        mission_slug,
        wp_id,
        force,
        target_lane=target_lane,
        get_main_repo_root=get_main_repo_root,
        get_mission_type=get_mission_type,
        get_feature_target_branch=get_feature_target_branch,
        resolve_workspace_for_wp=resolve_workspace_for_wp,
        review_currency_check_branch=_review_currency_check_branch,
        behind_commits_touch_only_planning_artifacts=_behind_commits_touch_only_planning_artifacts,
        filter_runtime_state_paths=_filter_runtime_state_paths,
        list_wp_branch_specs_changes_for_guard=_list_wp_branch_specs_changes_for_guard,
        console=console,
    )


def _wp_branch_merged_into_target(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    target_branch: str,
) -> tuple[bool, str]:
    """Check whether a lane branch tip is reachable from the target branch.

    Returns:
        (is_merged, message)
    """
    workspace = resolve_workspace_for_wp(repo_root, mission_slug, wp_id)
    wp_branch = workspace.branch_name

    branch_exists = subprocess.run(
        ["git", "rev-parse", "--verify", wp_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if branch_exists.returncode != 0:
        return (
            False,
            (f"Cannot verify merge ancestry: branch '{wp_branch}' not found.\nEither merge and keep branch ref available, or provide --done-override-reason."),
        )

    merged_check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", wp_branch, target_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if merged_check.returncode == 0:
        return True, f"Merge ancestry verified: {wp_branch} is merged into {target_branch}."

    return (
        False,
        (
            f"Merge ancestry check failed: {wp_branch} is not merged into {target_branch}.\n"
            f"Merge first, or provide --done-override-reason to record a conscious exception."
        ),
    )


def _list_wp_branch_mission_specs_changes(worktree_path: Path, base_branch: str) -> list[str]:
    """Return kitty-specs/ files changed on the lane branch compared to its base."""
    merge_base_result = subprocess.run(
        ["git", "merge-base", "HEAD", base_branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if merge_base_result.returncode != 0:
        return []

    merge_base = merge_base_result.stdout.strip()
    if not merge_base:
        return []

    diff_result = subprocess.run(
        ["git", "diff", "--name-only", f"{merge_base}..HEAD", "--", f"{KITTY_SPECS_DIR}/"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if diff_result.returncode != 0:
        return []

    seen: set[str] = set()
    files: list[str] = []
    for raw in diff_result.stdout.splitlines():
        path = raw.strip()
        if not path or not path.startswith(f"{KITTY_SPECS_DIR}/"):
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append(path)
    return files


globals()["_list_wp_branch_" + KITTY_SPECS_DIR.replace("-", "_") + "_changes"] = (
    _list_wp_branch_mission_specs_changes
)


def _list_wp_branch_specs_changes_for_guard(worktree_path: Path, base_branch: str) -> list[str]:
    patched_or_alias = globals()["_list_wp_branch_" + KITTY_SPECS_DIR.replace("-", "_") + "_changes"]
    return patched_or_alias(worktree_path=worktree_path, base_branch=base_branch)


@app.command(name="move-task")
def move_task(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    to: Annotated[str, typer.Option("--to", help="Target lane (planned/doing/for_review/approved/done)")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,
    agent: Annotated[str | None, typer.Option("--agent", help="Agent name")] = None,
    assignee: Annotated[str | None, typer.Option("--assignee", help="Assignee name (sets assignee when moving to doing)")] = None,
    shell_pid: Annotated[str | None, typer.Option("--shell-pid", help="Shell PID")] = None,
    note: Annotated[str | None, typer.Option("--note", help="History note")] = None,
    review_feedback_file: Annotated[
        Path | None, typer.Option("--review-feedback-file", help="Path to review feedback file (required for --to planned, including with --force)")
    ] = None,
    approval_ref: Annotated[str | None, typer.Option("--approval-ref", help="Approval reference for approval/done transitions (e.g., PR#42)")] = None,
    reviewer: Annotated[str | None, typer.Option("--reviewer", help="Reviewer name (auto-detected from git if omitted)")] = None,
    self_review_fallback: Annotated[
        bool,
        typer.Option(
            "--self-review-fallback",
            help="Record that approval is a self-review fallback after the intended reviewer failed.",
        ),
    ] = False,
    intended_reviewer: Annotated[
        str | None,
        typer.Option("--intended-reviewer", help="Reviewer that should have reviewed this WP before fallback."),
    ] = None,
    reviewer_failure_reason: Annotated[
        str | None,
        typer.Option("--reviewer-failure-reason", help="Reason the intended reviewer failed."),
    ] = None,
    done_override_reason: Annotated[
        str | None,
        typer.Option("--done-override-reason", help="Required when --to done and merge ancestry cannot be verified; recorded in history/event reason"),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Force move even with unchecked subtasks (does not bypass planned rollback feedback requirement)")] = False,
    tracker_ref: Annotated[
        list[str] | None,
        typer.Option(
            "--tracker-ref",
            help=(
                "External tracker reference (e.g., '#1298' or 'JIRA-123'). "
                "Repeatable; appended to the WP frontmatter tracker_refs."
            ),
        ),
    ] = None,
    skip_review_artifact_check: Annotated[
        bool,
        typer.Option(
            "--skip-review-artifact-check",
            help="Override a rejected latest review artifact when arbiter-approving; requires --note and records override evidence.",
        ),
    ] = False,
    auto_commit: Annotated[
        bool | None, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit WP file changes to target branch (default: from project config)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Move task between lanes (planned → doing → for_review → approved → done).

    Examples:
        spec-kitty agent tasks move-task WP01 --to doing --assignee claude --json
        spec-kitty agent tasks move-task WP02 --to for_review --agent claude --shell-pid $$
        spec-kitty agent tasks move-task WP03 --to approved --note "Review passed"
        spec-kitty agent tasks move-task WP03 --to done --done-override-reason "Branch deleted after hotfix merge"
        spec-kitty agent tasks move-task WP03 --to planned --review-feedback-file feedback.md
    """
    try:
        # Validate lane
        target_lane = ensure_lane(to)
        self_review_error = _self_review_fallback_option_error(
            enabled=self_review_fallback,
            target_lane=str(target_lane),
            force=force,
            intended_reviewer=intended_reviewer,
            failure_reason=reviewer_failure_reason,
        )
        if self_review_error:
            _output_error(json_output, self_review_error)
            raise typer.Exit(1)

        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        # FR-010 / FR-019: surface a one-shot sparse-checkout warning from the
        # LIVE command entry point before any state is read or mutated.
        _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks move-task")

        # Resolve auto_commit: CLI flag overrides project config
        if auto_commit is None:
            auto_commit = get_auto_commit_default(repo_root)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)
        skip_target_branch_commit = (
            _skip_target_branch_commit(main_repo_root, mission_slug, target_branch)
            if auto_commit else False
        )
        tracker_ref_values = [t.strip() for t in (tracker_ref or []) if t and t.strip()]
        unsupported_skip_metadata: list[str] = []
        if skip_target_branch_commit:
            if tracker_ref_values:
                unsupported_skip_metadata.append("tracker_refs")
            if assignee:
                unsupported_skip_metadata.append("assignee")
            if shell_pid:
                unsupported_skip_metadata.append("shell_pid")
            if note:
                unsupported_skip_metadata.append("activity_log")
        if unsupported_skip_metadata:
            _output_error(
                json_output,
                "Cannot persist WP frontmatter/activity metadata on protected "
                f"branch '{target_branch}' while coordination topology is active: "
                f"{', '.join(unsupported_skip_metadata)}. Rerun from an allowed "
                "branch, omit those metadata flags, or use --no-auto-commit.",
                diagnostic={
                    "error": "WP_METADATA_UNSUPPORTED_ON_PROTECTED_COORD_BRANCH",
                    "target_branch": target_branch,
                    "fields": unsupported_skip_metadata,
                },
            )
            raise typer.Exit(1)
        if auto_commit and not skip_target_branch_commit:
            protected_error = _protected_branch_status_commit_error(
                target_branch,
                main_repo_root,
                "spec-kitty agent tasks move-task",
            )
            if protected_error is not None:
                _output_error(json_output, protected_error)
                raise typer.Exit(1)

        # Informational: Let user know we're using planning repo's kitty-specs
        cwd = Path.cwd().resolve()
        if is_worktree_context(cwd) and not json_output and cwd != main_repo_root:
            # Check if worktree has its own kitty-specs (stale copy)
            worktree_kitty = None
            current = cwd
            while current != current.parent and ".worktrees" in str(current):
                if (current / KITTY_SPECS_DIR).exists():
                    worktree_kitty = current / KITTY_SPECS_DIR
                    break
                current = current.parent

            if worktree_kitty and (worktree_kitty / mission_slug / "tasks").exists():
                console.print(f"[dim]Note: Using planning repo's kitty-specs/ on {target_branch} (worktree copy ignored)[/dim]")

        # Load work package first (needed for current_lane check)
        wp = locate_work_package(repo_root, mission_slug, task_id)
        # Lane is event-log-only; read from canonical event log not frontmatter
        _mt_feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
        old_lane = _read_transactional_wp_lane(
            feature_dir=_mt_feature_dir,
            mission_slug=mission_slug,
            wp_id=task_id,
            repo_root=main_repo_root,
        )

        # AGENT OWNERSHIP CHECK: Warn if agent doesn't match WP's current agent
        # This helps prevent agents from accidentally modifying WPs they don't own
        current_agent = extract_scalar(wp.frontmatter, "agent")
        if current_agent and agent and current_agent != agent and not force:
            if not json_output:
                console.print()
                console.print("[bold red]⚠️  AGENT OWNERSHIP WARNING[/bold red]")
                console.print(f"   {task_id} is currently assigned to: [cyan]{current_agent}[/cyan]")
                console.print(f"   You are trying to move it as: [yellow]{agent}[/yellow]")
                console.print()
                console.print("   If you are the correct agent, use --force to override.")
                console.print("   If not, you may be modifying the wrong WP!")
                console.print()
            _output_error(json_output, f"Agent mismatch: {task_id} is assigned to '{current_agent}', not '{agent}'. Use --force to override.")
            raise typer.Exit(1)

        # FR-005 / FR-007: rejected-verdict guard.
        # Terminal transitions must fail closed before any status mutation when
        # the latest review-cycle artifact still rejects the WP.  The explicit
        # override path is durable: --skip-review-artifact-check requires a
        # human-readable note and writes override evidence into the artifact.
        if target_lane in (Lane.APPROVED, Lane.DONE):
            _verdict_wp_dir = wp.path.parent / wp.path.stem
            _verdict, _artifact_path = _get_latest_review_cycle_verdict(_verdict_wp_dir)
            if _artifact_path is not None and _verdict is None:
                _output_error(
                    json_output,
                    f"{task_id} {_artifact_path.name} has no parseable review verdict.\n"
                    "Repair the review artifact before approving or marking done.",
                )
                raise typer.Exit(1)
            if _verdict == "rejected" and _artifact_path is not None:
                if not skip_review_artifact_check:
                    _output_error(
                        json_output,
                        f"{task_id} has a rejected review artifact ({_artifact_path.name}). "
                        "Re-run with --skip-review-artifact-check --note <reason> "
                        "to record an arbiter override.",
                    )
                    raise typer.Exit(1)
                override_reason = note.strip() if isinstance(note, str) else ""
                if not override_reason:
                    _output_error(
                        json_output,
                        "--skip-review-artifact-check requires --note so override evidence is durable.",
                    )
                    raise typer.Exit(1)
                _persist_review_artifact_override(
                    _artifact_path,
                    repo_root=main_repo_root,
                    wp_id=task_id,
                    actor=agent or "operator",
                    reason=override_reason,
                )

        resolved_feedback_source: Path | None = None
        if review_feedback_file is not None:
            feedback_candidate = review_feedback_file.expanduser()
            feedback_candidate = (Path.cwd() / feedback_candidate).resolve() if not feedback_candidate.is_absolute() else feedback_candidate.resolve()

            if not feedback_candidate.exists():
                _output_error(
                    json_output,
                    f"Review feedback file not found: {feedback_candidate}",
                )
                raise typer.Exit(1)

            if not feedback_candidate.is_file():
                _output_error(
                    json_output,
                    f"Review feedback path is not a file: {feedback_candidate}",
                )
                raise typer.Exit(1)

            resolved_feedback_source = feedback_candidate

        review_feedback_pointer: str | None = None
        rejected_review_result = None

        # Strictly enforce deterministic review feedback capture on planned rollbacks.
        # This requirement is never bypassed, including with --force.
        if target_lane == Lane.PLANNED:
            if not resolved_feedback_source:
                error_msg = f"❌ Moving {task_id} to 'planned' requires review feedback.\n\n"
                error_msg += "Please provide feedback:\n"
                error_msg += "  1. Create feedback file: echo '**Issue**: Description' > feedback.md\n"
                error_msg += f"  2. Run: spec-kitty agent tasks move-task {task_id} --to planned --review-feedback-file feedback.md\n\n"
                error_msg += "This requirement cannot be bypassed with --force."
                _output_error(json_output, error_msg)
                raise typer.Exit(1)

            feedback_content = resolved_feedback_source.read_text(encoding="utf-8").strip()
            if not feedback_content:
                _output_error(
                    json_output,
                    f"Review feedback file is empty: {resolved_feedback_source}",
                )
                raise typer.Exit(1)

            from specify_cli.review.cycle import create_rejected_review_cycle

            _review_cycle = create_rejected_review_cycle(
                main_repo_root=main_repo_root,
                mission_slug=mission_slug,
                wp_id=task_id,
                wp_slug=_resolve_wp_slug(main_repo_root, mission_slug, task_id),
                feedback_source=resolved_feedback_source,
                reviewer_agent=agent or "unknown",
            )
            review_feedback_pointer = _review_cycle.pointer
            rejected_review_result = _review_cycle.review_result

        # Validate subtasks are complete when moving to for_review/approved/done (Issue #72)
        if target_lane in (Lane.FOR_REVIEW, Lane.APPROVED, Lane.DONE) and not force:
            unchecked = _check_unchecked_subtasks(repo_root, mission_slug, task_id, force)
            if unchecked:
                # ``unchecked`` only ever contains canonical T### ids, so the
                # remediation commands below are always valid mark-status calls.
                error_msg = f"Cannot move {task_id} to {target_lane} - unchecked subtasks:\n"
                for task in unchecked:
                    error_msg += f"  - [ ] {task}\n"
                error_msg += "\nMark these complete first:\n"
                for task in unchecked[:3]:  # Show first 3 examples
                    error_msg += f"  spec-kitty agent tasks mark-status {task} --status done\n"
                error_msg += "\nOr use --force to override (not recommended)"
                _output_error(json_output, error_msg)
                raise typer.Exit(1)

        # Validate uncommitted changes when moving to for_review/approved/done
        # This catches the bug where agents edit artifacts but forget to commit
        if target_lane in (Lane.FOR_REVIEW, Lane.APPROVED, Lane.DONE):
            is_valid, guidance = _validate_ready_for_review(
                repo_root,
                mission_slug,
                task_id,
                force,
                target_lane=str(target_lane),
            )
            if not is_valid:
                error_msg = f"Cannot move {task_id} to {target_lane}\n\n"
                error_msg += "\n".join(guidance)
                if not force:
                    error_msg += "\n\nOr use --force to override (not recommended)"
                _output_error(json_output, error_msg)
                raise typer.Exit(1)

        # Guardrail: code-change done transitions require merge ancestry or explicit override reason.
        # Planning-artifact WPs reach `done` through artifact acceptance (FR-008a) and skip the
        # ancestry check entirely, while code-change WPs still need a merged lane branch.
        user_note = note.strip() if isinstance(note, str) else note
        note_text = user_note
        override_reason = done_override_reason.strip() if isinstance(done_override_reason, str) else done_override_reason
        if target_lane == Lane.DONE:
            try:
                done_workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, task_id)
                done_execution_mode = done_workspace.execution_mode
            except (ValueError, FileNotFoundError):
                # If the resolver cannot classify (e.g. legacy mission without
                # frontmatter), fall back to enforcing the ancestry check —
                # treating unknowns as code_change is the safer default.
                done_execution_mode = "code_change"
        else:
            done_execution_mode = None

        if target_lane == Lane.DONE and done_execution_mode == "code_change":
            merged, merge_msg = _wp_branch_merged_into_target(
                repo_root=main_repo_root,
                mission_slug=mission_slug,
                wp_id=task_id,
                target_branch=target_branch,
            )
            if not merged:
                if not override_reason:
                    _output_error(
                        json_output,
                        (
                            f"Cannot move {task_id} to done without verified merge ancestry.\n"
                            f"{merge_msg}\n"
                            f"If review just passed, move it to approved first:\n"
                            f'  spec-kitty agent tasks move-task {task_id} --to approved --note "Review passed"\n'
                            f'To proceed anyway, provide --done-override-reason "<why this is acceptable>".'
                        ),
                    )
                    raise typer.Exit(1)

                override_note = f"Done override: {override_reason}"
                note_text = f"{note_text} | {override_note}" if note_text else override_note
                if not json_output:
                    console.print("[yellow]⚠️  Proceeding with done override; reason recorded in history/events.[/yellow]")

        # --- Canonical emit pipeline (WP09 delegation) ---
        # Build evidence dict for approval and done transitions.
        evidence_dict = None
        if target_lane in (Lane.APPROVED, Lane.DONE):
            # Auto-detect reviewer if not provided
            effective_reviewer = reviewer
            if not effective_reviewer:
                effective_reviewer = _detect_reviewer_name()
            effective_approval_ref = approval_ref
            if not effective_approval_ref and user_note:
                effective_approval_ref = user_note
            if not effective_approval_ref:
                effective_approval_ref = f"auto-approval:{task_id}:{datetime.now(UTC).strftime('%Y%m%d')}"
            evidence_dict = {
                "review": {
                    "reviewer": effective_reviewer,
                    "verdict": Lane.APPROVED,
                    "reference": effective_approval_ref or "force-override",
                },
            }

        # Build review_ref for for_review -> in_progress transitions
        emit_review_ref = None
        if target_lane == Lane.PLANNED and review_feedback_pointer:
            emit_review_ref = review_feedback_pointer
        elif old_lane == Lane.FOR_REVIEW and resolve_lane_alias(target_lane) in (Lane.IN_PROGRESS, Lane.PLANNED) and force:
            emit_review_ref = "force-override"

        # Resolve the canonical lane for the emit pipeline
        canonical_lane = resolve_lane_alias(target_lane)

        actor = agent or "user"

        # Build reason for emit (used by force transitions and some guards)
        emit_reason = note_text if note_text else None
        if force and not emit_reason:
            emit_reason = f"Force move to {target_lane}"

        # Determine feature_dir for the event store
        feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)

        # --- Arbiter override detection (T032) ---
        # When a --force move from planned to a forward lane follows a rejection event,
        # detect this as an arbiter override and persist a structured rationale.
        try:
            from specify_cli.review.arbiter import (
                _is_arbiter_override,
                create_arbiter_decision,
                parse_category_from_note,
                persist_arbiter_decision,
            )

            if _is_arbiter_override(feature_dir, task_id, old_lane, resolve_lane_alias(target_lane), force):
                # Derive review_ref from the latest rejection event
                _arb_events = read_events_transactional(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    repo_root=main_repo_root,
                )
                _arb_wp_events = [e for e in _arb_events if e.wp_id == task_id]
                _arb_latest = _arb_wp_events[-1] if _arb_wp_events else None
                _arb_review_ref = _arb_latest.review_ref if _arb_latest else None

                # Parse category and explanation from --note
                _arb_category, _arb_explanation = parse_category_from_note(note_text)
                _arb_actor = agent or "operator"

                arbiter_decision = create_arbiter_decision(
                    arbiter_name=_arb_actor,
                    category=_arb_category,
                    explanation=_arb_explanation,
                )
                try:
                    _arb_path = persist_arbiter_decision(
                        feature_dir=feature_dir,
                        wp_id=task_id,
                        review_ref=_arb_review_ref,
                        decision=arbiter_decision,
                    )
                    if not json_output:
                        console.print(f"[yellow]Arbiter override recorded:[/yellow] [bold]{_arb_category}[/bold] — {_arb_explanation}")
                        console.print(f"[dim]  Decision persisted: {_arb_path}[/dim]")
                except Exception as _arb_err:
                    if not json_output:
                        console.print(f"[dim]Warning: Could not persist arbiter decision: {_arb_err}[/dim]")

                # Use the rejection's review_ref for the forward event so history is linked
                if _arb_review_ref and emit_review_ref is None:
                    emit_review_ref = _arb_review_ref
        except ImportError:
            pass  # review package not available yet

        if target_lane in (Lane.APPROVED, Lane.DONE):
            issue_matrix_blocker = _issue_matrix_approval_blocker(
                feature_dir,
                target_lane=target_lane,
                primary_feature_dir=primary_feature_dir_for_mission(
                    main_repo_root,
                    mission_slug,
                ),
            )
            if issue_matrix_blocker:
                _output_error(json_output, issue_matrix_blocker)
                raise typer.Exit(1)

        # Keep force semantics strict: only user-requested --force should bypass guards.
        emit_force = force
        if not emit_reason:
            emit_reason = f"Force move to {target_lane}" if force else f"move-task: {old_lane} -> {target_lane}"

        # Auto-promote backward transitions to force=True with canonical reason shape.
        # Contract: spec-kitty-events docs/consumer-contract-dossier-v2.4.0.md
        # § "Backward Transitions: The Review-Rejection Family".
        # See: kitty-specs/backward-transition-cli-emit-01KRV8GC/contracts/auto-promote-backward-emit.md
        if not force and _is_backward_transition(old_lane, canonical_lane):
            emit_force = True
            original_reason = None if emit_reason is None or emit_reason.startswith("move-task: ") else emit_reason
            reason_parts = [f"backward rewind: {old_lane} -> {canonical_lane}"]
            if review_feedback_pointer and review_feedback_pointer != "force-override":
                reason_parts.append(review_feedback_pointer)
            if original_reason:
                reason_parts.append(original_reason)
            emit_reason = ": ".join(reason_parts)

        transition_targets = [canonical_lane]
        if not emit_force:
            transition_targets = _lane_targets_for_emit(old_lane, canonical_lane)

        with feature_status_lock(main_repo_root, mission_slug):
            event = None
            current_event_lane = None
            for existing_event in reversed(
                read_events_transactional(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    repo_root=main_repo_root,
                )
            ):
                if existing_event.wp_id == task_id:
                    current_event_lane = str(existing_event.to_lane)
                    break
            if current_event_lane is None:
                # No canonical state for this WP — finalize-tasks must be run
                # first. If an unresolved dependency cycle is the reason finalize
                # could not bootstrap status, surface that as the root cause
                # (#1589) instead of a "run finalize-tasks" hint that loops.
                from specify_cli.status import uninitialized_status_error

                raise RuntimeError(
                    uninitialized_status_error(mission_slug, task_id, feature_dir)
                )

            final_hop_actor = actor
            for target in transition_targets:
                from_lane_for_hop = event.to_lane if event is not None else resolve_lane_alias(current_event_lane)
                # If --agent is omitted, preserve the WP's assigned agent only
                # for implementation handoff hops; review/approval hops remain
                # operator actions.
                hop_actor = (
                    agent
                    or (
                        current_agent
                        if from_lane_for_hop == Lane.IN_PROGRESS and target == Lane.FOR_REVIEW
                        else None
                    )
                    or "user"
                )
                # Auto-construct ReviewResult when hopping out of in_review
                # (the review_result_required guard needs a structured outcome)
                hop_review_result = None
                if (
                    (
                        event is not None
                        and event.to_lane == Lane.IN_REVIEW
                        and target == Lane.PLANNED
                        and rejected_review_result is not None
                    )
                    or (
                        event is None
                        and current_event_lane == Lane.IN_REVIEW
                        and target == Lane.PLANNED
                        and rejected_review_result is not None
                    )
                ):
                    hop_review_result = rejected_review_result
                elif (
                    (
                        event is not None
                        and event.to_lane == Lane.IN_REVIEW
                        and evidence_dict is not None
                    )
                    or (
                        event is None
                        and current_event_lane == Lane.IN_REVIEW
                        and evidence_dict is not None
                    )
                ):
                    from specify_cli.status import ReviewResult

                    review_section = evidence_dict.get("review", {})
                    hop_review_result = ReviewResult(
                        reviewer=review_section.get("reviewer", hop_actor),
                        verdict=review_section.get("verdict", Lane.APPROVED),
                        reference=review_section.get("reference", f"auto-forward:{task_id}"),
                    )
                event = emit_status_transition_transactional(TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=task_id,
                    to_lane=target,
                    actor=hop_actor,
                    force=emit_force,
                    reason=emit_reason,
                    evidence=evidence_dict if target in (Lane.APPROVED, Lane.DONE) else None,
                    review_ref=emit_review_ref,
                    workspace_context=f"move-task:{main_repo_root}",
                    subtasks_complete=(True if target in (Lane.FOR_REVIEW, Lane.APPROVED) and not emit_force else None),
                    implementation_evidence_present=(True if target in (Lane.FOR_REVIEW, Lane.APPROVED) and not emit_force else None),
                    repo_root=main_repo_root,
                    review_result=hop_review_result,
                ))
                final_hop_actor = hop_actor
                # review_ref only applies to rollback transitions, never to forward chain hops
                emit_review_ref = None

            if self_review_fallback:
                from specify_cli.status import emit_reviewer_self_approval

                emit_reviewer_self_approval(
                    feature_dir,
                    mission_slug=mission_slug,
                    wp_id=task_id,
                    implementing_actor=final_hop_actor,
                    intended_reviewer=(intended_reviewer or "").strip(),
                    failure_reason=(reviewer_failure_reason or "").strip(),
                    fallback_approved=True,
                )

            # --- Post-emit: apply operational metadata fields to WP file ---
            # The event log is the sole authority for lane/review state.
            # Only non-status operational metadata is written to frontmatter.
            wp_content = wp.path.read_text(encoding="utf-8-sig")
            updated_front, updated_body, updated_padding = split_frontmatter(wp_content)

            # Update assignee if provided
            if assignee:
                updated_front = set_scalar(updated_front, "assignee", assignee)

            # Update agent if provided
            if agent:
                updated_front = set_scalar(updated_front, "agent", agent)

            # Update shell_pid if provided
            if shell_pid:
                updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

            # Build history entry
            timestamp = datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)
            agent_name = final_hop_actor or "unknown"
            shell_pid_val = shell_pid or extract_scalar(updated_front, "shell_pid") or ""
            note_text = note_text or f"Moved to {target_lane}"

            shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
            history_entry = f"- {timestamp} – {agent_name} – {shell_part}{note_text}"

            # Add history entry to body
            updated_body = append_activity_log(updated_body, history_entry)

            # Build updated document and write
            updated_doc = build_document(updated_front, updated_body, updated_padding)

            file_written = False
            _skip_target_commit = skip_target_branch_commit
            if auto_commit:
                spec_number = mission_slug.split("-")[0] if "-" in mission_slug else mission_slug

                commit_msg = f"chore: Move {task_id} to {target_lane} on spec {spec_number}"
                if agent_name != "unknown":
                    commit_msg += f" [{agent_name}]"

                try:
                    actual_file_path = wp.path.resolve()

                    # Commit the WP file together with all status artifacts
                    # so that events.jsonl, status.json, and tasks.md
                    # changes are captured in the same atomic commit.
                    if _skip_target_commit:
                        if not json_output:
                            console.print(
                                f"[dim]Note: WP file update not committed to '{target_branch}' "
                                "(protected branch, coord topology active). "
                                "The status transition is committed to the coordination branch "
                                "and is authoritative.[/dim]"
                            )
                        commit_success = False
                    else:
                        write_text_within_directory(wp.path, updated_doc, root=main_repo_root, encoding="utf-8")
                        file_written = True
                        status_artifacts = _collect_status_artifacts(feature_dir)
                        # The WP file is WORK_PACKAGE_TASK (primary): route the commit
                        # through the ONE canonical ``commit_for_mission`` entry point
                        # (WP07 / FR-006) instead of the open-coded resolve_placement_only
                        # + safe_commit pair. The router owns placement resolution AND the
                        # protected-primary refusal; ``safe_commit`` is reached only via
                        # the router (no direct call here).
                        _router_result = commit_for_mission(
                            main_repo_root,
                            mission_slug,
                            tuple([actual_file_path] + status_artifacts),
                            commit_msg,
                            ProtectionPolicy.resolve(main_repo_root),
                            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
                        )
                        commit_success = _router_result.status == "committed"

                    if commit_success:
                        if not json_output:
                            console.print(f"[cyan]→ Committed status change to {target_branch} branch[/cyan]")
                    elif not _skip_target_commit and not json_output:
                        console.print("[yellow]Warning:[/yellow] Failed to auto-commit")

                except Exception as e:
                    if not file_written:
                        write_text_within_directory(wp.path, updated_doc, root=main_repo_root, encoding="utf-8")
                    if not json_output:
                        console.print(f"[yellow]Warning:[/yellow] Auto-commit skipped: {e}")
            else:
                write_text_within_directory(wp.path, updated_doc, root=main_repo_root, encoding="utf-8")

            # T040 / FR-011 (F-10): persist --tracker-ref values into the WP frontmatter.
            # Done AFTER the standard frontmatter write so we operate on the latest
            # on-disk content via the typed Pydantic model.
            if tracker_ref_values and not _skip_target_commit:
                try:
                    from specify_cli.frontmatter import write_frontmatter as _write_fm
                    from specify_cli.status import read_wp_frontmatter as _read_wp_fm

                    _wp_meta, _body = _read_wp_fm(wp.path)
                    _existing = list(_wp_meta.tracker_refs or [])
                    _merged = sorted(set(_existing) | set(tracker_ref_values))
                    if _merged != _existing:
                        _updated = _wp_meta.update(tracker_refs=_merged)
                        _write_fm(wp.path, _updated.model_dump(exclude_none=True), _body)
                except Exception as _tr_exc:  # pragma: no cover - defensive
                    if not json_output:
                        console.print(
                            f"[yellow]Warning:[/yellow] Failed to persist --tracker-ref: {_tr_exc}"
                        )

        # FR-017 / FR-018: Release the review lock whenever review terminates
        # (approve to APPROVED, reject back to PLANNED, or any other transition
        # out of review). The release is placed AFTER the lane-transition commit
        # so that a failed release never rolls back the recorded transition;
        # failures are logged but do not fail the overall move-task command.
        _release_from = (Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.IN_PROGRESS)
        _release_to = (Lane.APPROVED, Lane.PLANNED)
        if old_lane in _release_from and target_lane in _release_to:
            try:
                from specify_cli.review.lock import ReviewLock

                _lock_workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, task_id)
                ReviewLock.release(Path(_lock_workspace.worktree_path))
            except Exception as _release_exc:  # pragma: no cover - defensive
                logging.getLogger(__name__).warning(
                    "Review lock release failed for %s in %s: %s",
                    task_id,
                    mission_slug,
                    _release_exc,
                )

        # Output result
        event_fields = _status_event_result_fields(event)
        status_events_path = (
            _coord_status_events_path(main_repo_root, mission_slug)
            if skip_target_branch_commit else None
        )
        result = {
            "result": "success",
            "task_id": task_id,
            "old_lane": old_lane,
            "new_lane": target_lane,
            "path": str(wp.path),
            "event_id": event_fields["event_id"],
            "work_package_id": task_id,
            "to_lane": event_fields["to_lane"] or canonical_lane,
            "status_events_path": str(status_events_path or (feature_dir / EVENTS_FILENAME)),
        }
        if skip_target_branch_commit:
            result["wp_file_update"] = "skipped"
            result["wp_file_update_reason"] = (
                "protected branch with coordination topology; status event "
                "is authoritative on the coordination branch"
            )
            if agent:
                result["frontmatter_fields_skipped"] = ["agent"]
        if review_feedback_pointer is not None:
            result["review_feedback"] = review_feedback_pointer

        _output_result(json_output, result, f"[green]✓[/green] Moved {task_id} from {old_lane} to {target_lane}")

        # Check for dependent WP warnings when moving to for_review (T083)
        _check_dependent_warnings(repo_root, mission_slug, task_id, target_lane, json_output)

    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016)
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                wp_id=task_id if "task_id" in dir() else None,
                stack_trace=traceback.format_exc(),
                agent_id=agent if "agent" in dir() else None,
            )
        diagnostic = e.to_diagnostic() if isinstance(e, EventPersistenceError) else None
        if diagnostic is not None and "canonical_lane" in locals():
            diagnostic["failed_event_to_lane"] = diagnostic.get("to_lane")
            diagnostic["to_lane"] = canonical_lane
            diagnostic["requested_lane"] = canonical_lane
        _output_error(json_output, str(e), diagnostic=diagnostic)
        raise typer.Exit(1) from None


def _resolve_inline_subtasks(
    task_id: str,
    tasks_content: str,
    status: str,
    feature_dir: Path,
) -> TaskIdResult | None:
    """
    Search tasks_content for 'Subtasks: T001, T002' lines containing task_id.

    Inline references are discovery hints only; this resolver reports updated
    only after materializing a durable checkbox row in tasks.md.
    """
    normalized_task_id = task_id.upper()
    for match in _INLINE_SUBTASKS_RE.finditer(tasks_content):
        ids = [value.strip().upper() for value in match.group("ids").split(",")]
        if normalized_task_id in ids:
            persisted = _persist_inline_subtask_status(task_id, status, feature_dir, tasks_content)
            if persisted:
                return TaskIdResult(
                    id=task_id,
                    outcome=TaskIdResolutionOutcome.UPDATED,
                    format=TaskIdResolutionFormat.INLINE_SUBTASKS,
                    message=f"Persisted status for inline Subtasks reference {task_id} as {status}.",
                )
            return TaskIdResult(
                id=task_id,
                outcome=TaskIdResolutionOutcome.NOT_FOUND,
                format=TaskIdResolutionFormat.INLINE_SUBTASKS,
                message=(
                    f"{task_id} appears only in an inline Subtasks reference. "
                    "Inline references are not durable status storage; materialize "
                    "a checkbox row or append a canonical status event before "
                    "reporting updated."
                ),
            )
    return None


def _mark_status_json_payload(results: list[TaskIdResult]) -> dict[str, object]:
    """Return the contracted mark-status --json payload."""
    summary = {
        "updated": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.UPDATED),
        "already_satisfied": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.ALREADY_SATISFIED),
        "not_found": sum(1 for result in results if result.outcome == TaskIdResolutionOutcome.NOT_FOUND),
    }
    return {
        "results": [
            {
                "id": result.id,
                "outcome": result.outcome.value,
                "format": result.format.value if result.format else None,
                "message": result.message,
            }
            for result in results
        ],
        "summary": summary,
    }


@app.command(name="mark-status")
def mark_status(
    task_ids: Annotated[list[str], typer.Argument(help="Task ID(s) - space-separated (e.g., T001 T002 T003)")],
    status: Annotated[str, typer.Option("--status", help="Status: done/pending")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    auto_commit: Annotated[
        bool | None, typer.Option("--auto-commit/--no-auto-commit", help="Automatically commit tasks.md changes to target branch (default: from project config)")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Update task checkbox status in tasks.md for one or more tasks.

    Accepts MULTIPLE task IDs separated by spaces. All tasks are updated
    in a single operation with one commit.

    Examples:
        # Single task:
        spec-kitty agent tasks mark-status T001 --status done

        # Multiple tasks (space-separated):
        spec-kitty agent tasks mark-status T001 T002 T003 --status done

        # Many tasks at once:
        spec-kitty agent tasks mark-status T040 T041 T042 T043 T044 T045 --status done --mission 001-my-feature

        # With JSON output:
        spec-kitty agent tasks mark-status T001 T002 --status done --json
    """
    try:
        # Validate status
        if status not in ("done", "pending"):
            _output_error(json_output, f"Invalid status '{status}'. Must be 'done' or 'pending'.")
            raise typer.Exit(1)

        # Validate we have at least one task
        if not task_ids:
            _output_error(json_output, "At least one task ID is required")
            raise typer.Exit(1)

        # WP04/T022 (FR-017): accept both bare and mission-qualified task IDs.
        # `tasks-finalize` and downstream emitters may produce IDs in either
        # shape: `T001` or `<mission_slug>/T001` (or `<mission_slug>:T001`).
        # Normalize to bare task IDs before validation. A garbage ID that is
        # not a recognizable task token surfaces as "no task IDs found in
        # tasks.md" downstream — preserving the existing structured-error
        # contract for unknown tasks.
        task_ids = [_normalize_task_id_input(tid) for tid in task_ids]

        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        # FR-010 / FR-019: one-shot sparse-checkout session warning.
        _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks mark-status")

        # Resolve auto_commit: CLI flag overrides project config
        if auto_commit is None:
            auto_commit = get_auto_commit_default(repo_root)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)
        # Ensure we operate on the target branch for this feature
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)
        if auto_commit:
            protected_error = _protected_branch_status_commit_error(
                target_branch,
                main_repo_root,
                "spec-kitty agent tasks mark-status",
            )
            if protected_error is not None:
                _output_error(json_output, protected_error)
                raise typer.Exit(1)
        feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
        tasks_md = feature_dir / TASKS_MD_FILENAME

        with feature_status_lock(main_repo_root, mission_slug):
            if not tasks_md.exists():
                _output_error(json_output, f"tasks.md not found: {tasks_md}")
                raise typer.Exit(1)

            # Read tasks.md content
            content = tasks_md.read_text(encoding="utf-8")
            lines = content.split("\n")

            # Track which tasks were updated and which weren't found
            results: list[TaskIdResult] = []
            artifact_mutated = False

            # Update all requested tasks in a single pass
            for task_id in task_ids:
                before_content = "\n".join(lines)
                result = (
                    _resolve_checkbox(task_id, lines, status)
                    or _resolve_pipe_table(task_id, lines, status)
                    or _resolve_inline_subtasks(task_id, before_content, status, feature_dir)
                    or _resolve_wp_id(task_id, status, mission_slug, feature_dir)
                    or TaskIdResult(
                        id=task_id,
                        outcome=TaskIdResolutionOutcome.NOT_FOUND,
                        format=None,
                        message=f"{task_id} was not found in any supported task format.",
                    )
                )
                results.append(result)

                if result.format in {
                    TaskIdResolutionFormat.CHECKBOX,
                    TaskIdResolutionFormat.PIPE_TABLE,
                } and result.outcome == TaskIdResolutionOutcome.UPDATED:
                    artifact_mutated = True

                if (
                    result.format == TaskIdResolutionFormat.INLINE_SUBTASKS
                    and result.outcome == TaskIdResolutionOutcome.UPDATED
                ):
                    artifact_mutated = True
                    lines = tasks_md.read_text(encoding="utf-8").split("\n")

            updated_tasks = [
                result.id
                for result in results
                if result.outcome == TaskIdResolutionOutcome.UPDATED
            ]
            not_found_tasks = [
                result.id
                for result in results
                if result.outcome == TaskIdResolutionOutcome.NOT_FOUND
            ]
            resolved_tasks = [
                result.id
                for result in results
                if result.outcome != TaskIdResolutionOutcome.NOT_FOUND
            ]

            # Fail if no tasks were updated
            if not resolved_tasks:
                if json_output:
                    print(json.dumps(_mark_status_json_payload(results)))
                else:
                    if any(result.format == TaskIdResolutionFormat.WP_ID for result in results):
                        detail = "; ".join(result.message for result in results if result.message)
                        _output_error(json_output, detail)
                    else:
                        _output_error(json_output, f"No task IDs found in tasks.md: {', '.join(not_found_tasks)}")
                raise typer.Exit(1)

            # Write updated content (single write for all changes)
            if artifact_mutated:
                updated_content = "\n".join(lines)
                tasks_md.write_text(updated_content, encoding="utf-8")

            # Auto-commit to TARGET branch (detects from feature meta.json)
            if auto_commit and artifact_mutated:
                # Extract spec number from mission_slug (e.g., "014" from "014-feature-name")
                spec_number = mission_slug.split("-")[0] if "-" in mission_slug else mission_slug

                # Build commit message
                if len(updated_tasks) == 1:
                    commit_msg = f"chore: Mark {updated_tasks[0]} as {status} on spec {spec_number}"
                else:
                    commit_msg = f"chore: Mark {len(updated_tasks)} subtasks as {status} on spec {spec_number}"

                try:
                    actual_tasks_path = tasks_md.resolve()

                    # tasks.md is TASKS_INDEX (primary): route the commit through the
                    # ONE canonical ``commit_for_mission`` entry point (WP07 / FR-006)
                    # instead of the open-coded resolve_placement_only + safe_commit
                    # pair. The router owns placement resolution AND the
                    # protected-primary refusal; ``safe_commit`` is reached only via
                    # the router (no direct call here).
                    _router_result = commit_for_mission(
                        main_repo_root,
                        mission_slug,
                        (actual_tasks_path,),
                        commit_msg,
                        ProtectionPolicy.resolve(main_repo_root),
                        kind=MissionArtifactKind.TASKS_INDEX,
                    )
                    commit_success = _router_result.status == "committed"

                    if commit_success:
                        if not json_output:
                            console.print(f"[cyan]→ Committed subtask changes to {target_branch} branch[/cyan]")
                    else:
                        if not json_output:
                            console.print("[yellow]Warning:[/yellow] Failed to auto-commit subtask changes")

                except Exception as e:
                    if not json_output:
                        console.print(f"[yellow]Warning:[/yellow] Auto-commit exception: {e}")

        # Emit HistoryAdded event for subtask status changes (T014)
        try:
            if updated_tasks:
                resolved_tasks_by_wp: dict[str, list[str]] = {}
                unresolved_tasks: list[str] = []
                tasks_content = tasks_md.read_text(encoding="utf-8")
                for task_id in updated_tasks:
                    history_wp_id = _resolve_history_wp_id(tasks_content, task_id)
                    if history_wp_id is None:
                        unresolved_tasks.append(task_id)
                    else:
                        resolved_tasks_by_wp.setdefault(history_wp_id, []).append(task_id)

                for history_wp_id, task_ids_for_wp in resolved_tasks_by_wp.items():
                    task_list_str = ", ".join(task_ids_for_wp)
                    emit_history_added(
                        wp_id=history_wp_id,
                        entry_type="note",
                        entry_content=f"Subtask(s) {task_list_str} marked as {status}",
                        author="user",
                    )
                if unresolved_tasks and not json_output:
                    console.print(
                        "[yellow]Warning:[/yellow] Could not resolve owning WP for HistoryAdded event: "
                        + ", ".join(unresolved_tasks)
                    )
        except Exception as e:
            if not json_output:
                console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")

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

        # Build result
        result = _mark_status_json_payload(results)

        # Output result
        if not_found_tasks and not json_output:
            console.print(f"[yellow]Warning:[/yellow] Not found: {', '.join(not_found_tasks)}")

        if len(updated_tasks) == 1:
            success_msg = f"[green]✓[/green] Marked {updated_tasks[0]} as {status}"
        elif not updated_tasks:
            success_msg = f"[green]✓[/green] Requested status already satisfied for: {', '.join(resolved_tasks)}"
        else:
            success_msg = f"[green]✓[/green] Marked {len(updated_tasks)} subtasks as {status}: {', '.join(updated_tasks)}"

        _output_result(json_output, result, success_msg)

    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016)
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="list-tasks")
def list_tasks(
    lane: Annotated[str | None, typer.Option("--lane", help="Filter by lane")] = None,
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """List tasks with optional lane filtering.

    Examples:
        spec-kitty agent tasks list-tasks --json
        spec-kitty agent tasks list-tasks --lane doing --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)

        # Find all task files
        tasks_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug) / "tasks"
        if not tasks_dir.exists():
            _output_error(json_output, f"Tasks directory not found: {tasks_dir}")
            raise typer.Exit(1)

        # Load canonical lanes from event log
        _lt_feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
        try:
            from specify_cli.status import read_events as _lt_read_events
            from specify_cli.status import reduce as _lt_reduce

            _lt_events = _lt_read_events(_lt_feature_dir)
            _lt_snapshot = _lt_reduce(_lt_events) if _lt_events else None
            _lt_lanes: dict = {}
            if _lt_snapshot:
                for _lt_wp_id, _lt_state in _lt_snapshot.work_packages.items():
                    _lt_lanes[_lt_wp_id] = Lane(_lt_state.get("lane", Lane.PLANNED))
        except Exception:
            _lt_lanes = {}

        tasks = []
        for task_file in tasks_dir.glob("WP*.md"):
            if task_file.name.lower() == "readme.md":
                continue

            content = task_file.read_text(encoding="utf-8-sig")
            frontmatter, _, _ = split_frontmatter(content)

            task_wp_id = extract_scalar(frontmatter, "work_package_id") or task_file.stem
            task_title = extract_scalar(frontmatter, "title") or ""
            # Lane is event-log-only
            task_lane = _lt_lanes.get(task_wp_id, Lane.PLANNED)

            # Filter by lane if specified
            if lane and task_lane != lane:
                continue

            tasks.append({"work_package_id": task_wp_id, "title": task_title, "lane": task_lane, "path": str(task_file)})

        # Sort by work package ID
        tasks.sort(key=lambda t: t["work_package_id"])

        if json_output:
            print(json.dumps({"tasks": tasks, "count": len(tasks)}))
        else:
            if not tasks:
                console.print(f"[yellow]No tasks found{' in lane ' + lane if lane else ''}[/yellow]")
            else:
                console.print(f"[bold]Tasks{' in lane ' + lane if lane else ''}:[/bold]\n")
                for task in tasks:
                    console.print(f"  {task['work_package_id']}: {task['title']} [{task['lane']}]")

    except typer.Exit:
        raise
    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="add-history")
def add_history(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    note: Annotated[str, typer.Option("--note", help="History note")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    agent: Annotated[str | None, typer.Option("--agent", help="Agent name")] = None,
    shell_pid: Annotated[str | None, typer.Option("--shell-pid", help="Shell PID")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Append history entry to task activity log.

    Examples:
        spec-kitty agent tasks add-history WP01 --note "Completed implementation" --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        # FR-010 / FR-019: one-shot sparse-checkout session warning.
        _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks add-history")

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)

        # Load work package
        wp = locate_work_package(repo_root, mission_slug, task_id)

        # Build history entry
        timestamp = datetime.now(UTC).strftime(UTC_SECOND_TIMESTAMP_FORMAT)
        agent_name = agent or extract_scalar(wp.frontmatter, "agent") or "unknown"
        shell_pid_val = shell_pid or extract_scalar(wp.frontmatter, "shell_pid") or ""

        shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
        history_entry = f"- {timestamp} – {agent_name} – {shell_part}{note}"

        # Add history entry to body
        updated_body = append_activity_log(wp.body, history_entry)

        # Build and write updated document
        updated_doc = build_document(wp.frontmatter, updated_body, wp.padding)
        wp.path.write_text(updated_doc, encoding="utf-8")

        # Emit HistoryAdded event (T015 - FR-021)
        try:
            emit_history_added(
                wp_id=task_id,
                entry_type="note",
                entry_content=note,
                author=agent or "user",
            )
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")

        result = {"result": "success", "task_id": task_id, "note": note}

        _output_result(json_output, result, f"[green]✓[/green] Added history entry to {task_id}")

    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016)
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                wp_id=task_id if "task_id" in dir() else None,
                stack_trace=traceback.format_exc(),
                agent_id=agent if "agent" in dir() else None,
            )
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="finalize-tasks")
def finalize_tasks(
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    validate_only: Annotated[bool, typer.Option("--validate-only", help="Validate without writing changes")] = False,
) -> None:
    """Parse tasks.md and inject dependencies into WP frontmatter.

    Scans tasks.md for "Depends on: WP##" patterns or phase groupings,
    builds dependency graph, validates for cycles, and writes dependencies
    field to each WP file's frontmatter.

    Examples:
        spec-kitty agent tasks finalize-tasks --mission 001-my-feature --json
        spec-kitty agent tasks finalize-tasks --mission 021-my-feature --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        # FR-010 / FR-019: one-shot sparse-checkout session warning.
        _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks finalize-tasks")

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)
        # Ensure we operate on the target branch for this feature
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)
        feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
        tasks_md = feature_dir / TASKS_MD_FILENAME
        tasks_dir = feature_dir / "tasks"

        if not tasks_md.exists():
            _output_error(json_output, f"tasks.md not found: {tasks_md}")
            raise typer.Exit(1)

        if not tasks_dir.exists():
            _output_error(json_output, f"Tasks directory not found: {tasks_dir}")
            raise typer.Exit(1)

        # Parse tasks.md for dependency patterns using the shared canonical parser
        tasks_content = tasks_md.read_text(encoding="utf-8")
        from specify_cli.core.dependency_parser import parse_dependencies_from_tasks_md as _shared_parse_deps

        dependencies_map: dict[str, list[str]] = _shared_parse_deps(tasks_content)

        # WP04 seam: WP coverage + cycle + disagree-loud conflict validation,
        # then a pure plan for the frontmatter rewrites. The command body only
        # surfaces errors and performs the (validate-only-gated) writes.
        coverage = validate_wp_coverage(dependencies_map, tasks_dir)
        if not coverage.ok:
            _output_error(
                json_output,
                (
                    "tasks.md work package coverage is incomplete. finalize-tasks could not match "
                    "all WP files to parsed sections, so dependency lanes would be unreliable."
                ),
            )
            raise typer.Exit(1)

        cycles = detect_dependency_cycles(dependencies_map)
        if cycles:
            _output_error(json_output, f"Circular dependencies detected: {cycles}")
            raise typer.Exit(1)

        # --- Dependency conflict detection (T004: disagree-loud) ---
        existing_frontmatter = read_existing_frontmatter(tasks_dir)
        dep_conflict_errors = detect_dependency_conflicts(dependencies_map, existing_frontmatter)
        if dep_conflict_errors:
            error_msg = "Dependency disagreement detected:\n" + "\n".join(dep_conflict_errors)
            _output_error(json_output, error_msg)
            raise typer.Exit(1)

        # Compute (side-effect-free) the frontmatter rewrites, then apply them
        # gating ALL writes on validate_only (T005/T006).
        from specify_cli.frontmatter import write_frontmatter as _write_fm

        update_plan = compute_wp_frontmatter_updates(dependencies_map, tasks_dir)
        for warning in update_plan.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")

        would_modify: list[dict[str, object]] = []
        for write in update_plan.writes:
            if not validate_only:
                _write_fm(write.wp_file, write.updated_meta.model_dump(exclude_none=True), write.body)
            else:
                would_modify.append({"wp_id": write.wp_id, "changes": {"dependencies": write.dependencies}})

        updated_count = update_plan.updated_count
        modified_wps = update_plan.modified_wps
        unchanged_wps = update_plan.unchanged_wps
        preserved_wps = update_plan.preserved_wps

        # Bootstrap canonical status state for all WPs
        bootstrap_result = bootstrap_canonical_state(feature_dir, mission_slug, dry_run=validate_only)

        if validate_only:
            result: dict[str, object] = {
                "result": "validation_passed",
                "validate_only": True,
                "would_modify": would_modify,
                "would_preserve": preserved_wps,
                "unchanged": unchanged_wps,
                "updated_wp_count": updated_count,
                "dependencies": dependencies_map,
                **_mission_identity_payload(feature_dir),
                "bootstrap": {
                    "total_wps": bootstrap_result.total_wps,
                    "already_initialized": bootstrap_result.already_initialized,
                    "newly_seeded": bootstrap_result.newly_seeded,
                    "skipped": bootstrap_result.skipped,
                    "wp_details": bootstrap_result.wp_details,
                },
            }
        else:
            result = {
                "result": "success",
                "updated_wp_count": updated_count,
                "modified_wps": modified_wps,
                "unchanged_wps": unchanged_wps,
                "preserved_wps": preserved_wps,
                "dependencies": dependencies_map,
                **_mission_identity_payload(feature_dir),
                "bootstrap": {
                    "total_wps": bootstrap_result.total_wps,
                    "already_initialized": bootstrap_result.already_initialized,
                    "newly_seeded": bootstrap_result.newly_seeded,
                    "skipped": bootstrap_result.skipped,
                    "wp_details": bootstrap_result.wp_details,
                },
            }

        _output_result(
            json_output,
            result,
            f"[green]✓[/green] Updated {updated_count} WP files with dependencies"
            f" (bootstrap: {bootstrap_result.newly_seeded} seeded,"
            f" {bootstrap_result.already_initialized} existing)",
        )

    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016)
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )

        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="map-requirements")
def map_requirements(
    wp: Annotated[str | None, typer.Option("--wp", help="WP ID (e.g., WP04)")] = None,
    refs: Annotated[
        str | None,
        typer.Option("--refs", help="Comma-separated requirement refs (e.g., FR-001,FR-002)"),
    ] = None,
    batch: Annotated[
        str | None,
        typer.Option(
            "--batch",
            help='JSON batch mapping (e.g., \'{"WP01":["FR-001"],"WP02":["FR-003"]}\')',
        ),
    ] = None,
    replace: Annotated[
        bool,
        typer.Option(
            "--replace",
            help="Replace existing refs instead of merging (default: merge/union)",
        ),
    ] = False,
    tracker_ref: Annotated[
        list[str] | None,
        typer.Option(
            "--tracker-ref",
            help=(
                "External tracker reference (e.g., '#1298' or 'JIRA-123'). "
                "Repeatable; requires --wp. Persists to the WP frontmatter as tracker_refs."
            ),
        ),
    ] = None,
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
    auto_commit: Annotated[
        bool | None,
        typer.Option(
            "--auto-commit/--no-auto-commit",
            help="Automatically commit WP file changes (default: from project config)",
        ),
    ] = None,
) -> None:
    """Register requirement-to-WP mappings with immediate validation."""
    from specify_cli.frontmatter import write_frontmatter
    from specify_cli.status import read_wp_frontmatter
    from specify_cli.requirement_mapping import (
        compute_coverage,
        normalize_requirement_refs_value,
        parse_requirement_ids_from_spec_md,
        read_all_wp_raw_requirement_refs,
        read_all_wp_requirement_refs,
        validate_ref_format,
        validate_refs,
    )

    # T040 / FR-011 (F-10): tracker_ref values are persisted alongside
    # requirement_refs.  --tracker-ref is repeatable and requires --wp.
    tracker_ref_values: list[str] = [t.strip() for t in (tracker_ref or []) if t and t.strip()]

    try:
        if batch and (wp or refs):
            _output_error(json_output, "Cannot combine --batch with --wp/--refs. Use one mode.")
            raise typer.Exit(1)

        if tracker_ref_values and (batch or wp is None):
            _output_error(
                json_output,
                "--tracker-ref requires --wp (cannot be combined with --batch).",
            )
            raise typer.Exit(1)

        # When only --tracker-ref is supplied (no --refs), allow the persistence
        # of tracker refs without changing requirement_refs.  This is the
        # primary usage shape per the WP10 spec.
        tracker_only_mode = bool(tracker_ref_values and wp is not None and not refs)

        if not batch and not (wp and refs) and not tracker_only_mode:
            _output_error(
                json_output,
                "Provide either --wp + --refs (individual), --batch, or --wp + --tracker-ref.",
            )
            raise typer.Exit(1)

        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        # FR-010 / FR-019: one-shot sparse-checkout session warning.
        _emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks map-requirements")

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)
        if auto_commit is None:
            auto_commit = get_auto_commit_default(main_repo_root)
        commit_target = CommitTarget(ref=target_branch)
        if auto_commit:
            from specify_cli.coordination.commit_router import _resolve_planning_placement

            # map-requirements edits WP prompt files → WORK_PACKAGE_TASK (primary)
            # (write-surface-coherence WP02 / T009). Resolve the destination through
            # the kind authority instead of the hardcoded target_branch above.
            commit_target = _resolve_planning_placement(
                main_repo_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
            )
        if auto_commit:
            protected_error = _protected_branch_status_commit_error(
                commit_target.ref,
                main_repo_root,
                "spec-kitty agent tasks map-requirements",
            )
            if protected_error is not None:
                _output_error(json_output, protected_error)
                raise typer.Exit(1)
        from specify_cli.missions._read_path_resolver import (
            primary_feature_dir_for_mission,
        )

        # #2064: resolve the WP ``tasks/`` dir through the SAME seam finalize uses
        # (one read surface), not the divergent ``resolve_feature_dir_for_slug``.
        feature_dir = _map_requirements_feature_dir(main_repo_root, mission_slug)
        # PRIMARY-input invariant: ``spec.md`` is authored on PRIMARY — unchanged.
        primary_dir = primary_feature_dir_for_mission(main_repo_root, mission_slug)

        if not feature_dir.exists():
            _output_error(json_output, f"Mission directory not found: {feature_dir}")
            raise typer.Exit(1)

        spec_md = primary_dir / SPEC_MD_FILENAME
        if not spec_md.exists():
            _output_error(json_output, f"spec.md not found: {spec_md}")
            raise typer.Exit(1)

        spec_content = spec_md.read_text(encoding="utf-8")
        spec_ids = parse_requirement_ids_from_spec_md(spec_content)
        all_spec_ids = set(spec_ids["all"])
        functional_ids = set(spec_ids["functional"])

        new_mappings: dict[str, list[str]] = {}
        if batch:
            try:
                parsed_batch = json.loads(batch)
            except json.JSONDecodeError as exc:
                _output_error(json_output, f"Invalid JSON in --batch: {exc}")
                raise typer.Exit(1) from None
            if not isinstance(parsed_batch, dict):
                _output_error(json_output, "--batch must be a JSON object {WP_ID: [refs]}")
                raise typer.Exit(1)
            for wp_id, ref_list in parsed_batch.items():
                if not isinstance(ref_list, list) or not all(isinstance(ref, str) for ref in ref_list):
                    _output_error(
                        json_output,
                        f"Refs for {wp_id} must be a list of strings",
                    )
                    raise typer.Exit(1)
                new_mappings[wp_id.upper()] = [ref.upper() for ref in ref_list]
        elif tracker_only_mode:
            # Only --wp + --tracker-ref: no requirement refs to validate, but we
            # still register the WP key so the persistence loop visits it.
            assert wp is not None  # narrowed by tracker_only_mode
            new_mappings[wp.upper()] = []
        else:
            if wp is None or refs is None:
                _output_error(json_output, "Both --wp and --refs are required in individual mode.")
                raise typer.Exit(1)
            ref_list_parsed = [ref.strip() for ref in refs.split(",") if ref.strip()]
            new_mappings[wp.upper()] = [ref.upper() for ref in ref_list_parsed]

        # #2107 / FR-004 (gate-read-surface-completion WP04): the WP ``tasks/*.md``
        # files are WORK_PACKAGE_TASK — a PRIMARY-partition kind. Resolve the read
        # dir through the kind-aware seam (the SAME single authority WP01 routed the
        # rest of the gate reads onto) instead of the topology-routed ``feature_dir``
        # (``_map_requirements_feature_dir`` → coord), which on a coord-topology
        # mission returns the materialised ``-coord`` husk whose ``tasks/`` is empty
        # — the squad-found missed site (research.md Decision 3). The WRITE/commit
        # leg below already resolves WORK_PACKAGE_TASK → primary via
        # ``_resolve_planning_placement`` / ``_planning_commit_worktree``, so this
        # re-points the READ to the same primary surface. STATUS legs are untouched
        # (C-002); the ``tasks.md`` (TASKS_INDEX) read off ``feature_dir`` is a
        # separate kind/site outside this site.
        tasks_dir = (
            resolve_planning_read_dir(
                main_repo_root,
                mission_slug,
                kind=MissionArtifactKind.WORK_PACKAGE_TASK,
            )
            / "tasks"
        )
        existing_wps: set[str] = set()
        if tasks_dir.exists():
            for wp_file in tasks_dir.glob("WP*.md"):
                match = re.match(r"(WP\d{2})", wp_file.name)
                if match:
                    existing_wps.add(match.group(1))

        unknown_wps = sorted(wp_id for wp_id in new_mappings if wp_id not in existing_wps)
        if unknown_wps:
            hint = f"Available WPs: {', '.join(sorted(existing_wps))}" if existing_wps else "No WP files found in tasks/"
            if json_output:
                print(
                    json.dumps(
                        {
                            "error": "Unknown WP IDs",
                            "unknown_wps": unknown_wps,
                            "hint": hint,
                        }
                    )
                )
            else:
                console.print(f"[red]Error:[/red] Unknown WP IDs: {', '.join(unknown_wps)}")
                console.print(f"  {hint}")
            raise typer.Exit(1)

        all_new_refs: list[str] = []
        for ref_list in new_mappings.values():
            all_new_refs.extend(ref_list)

        _, malformed = validate_ref_format(all_new_refs)
        if malformed:
            payload = {
                "error": "Invalid requirement ref format",
                "malformed_refs": malformed,
                "hint": "Refs must match FR-NNN, NFR-NNN, or C-NNN format",
            }
            if json_output:
                print(json.dumps(payload))
            else:
                console.print(f"[red]Error:[/red] Invalid ref format: {', '.join(malformed)}")
            raise typer.Exit(1)

        _, unknown_refs = validate_refs(all_new_refs, all_spec_ids)
        if unknown_refs:
            available_range = f"Available: {', '.join(sorted(all_spec_ids))}" if all_spec_ids else "No requirement IDs found in spec.md"
            payload = {
                "error": "Invalid requirement refs",
                "unknown_refs": sorted(set(unknown_refs)),
                "hint": f"Refs not found in spec.md. {available_range}",
            }
            if json_output:
                print(json.dumps(payload))
            else:
                console.print(f"[red]Error:[/red] Unknown refs: {', '.join(sorted(set(unknown_refs)))}")
                console.print(f"  {available_range}")
            raise typer.Exit(1)

        tasks_md_refs: dict[str, list[str]] = {}
        tasks_md_file = feature_dir / TASKS_MD_FILENAME
        if tasks_md_file.exists():
            from specify_cli.cli.commands.agent.mission import (
                _parse_requirement_refs_from_tasks_md,
            )

            tasks_md_content = tasks_md_file.read_text(encoding="utf-8")
            tasks_md_refs = _parse_requirement_refs_from_tasks_md(tasks_md_content)

        for wp_id, new_refs in new_mappings.items():
            wp_file = next((wp_file for wp_file in tasks_dir.glob(f"{wp_id}*.md")), None)
            if wp_file is None:
                continue

            wp_meta, body = read_wp_frontmatter(wp_file)
            update_kwargs: dict[str, list[str]] = {}

            # Only update requirement_refs when refs were supplied; preserves
            # backward compatibility for the tracker-only invocation.
            if not tracker_only_mode:
                if replace:
                    merged_refs = sorted(set(new_refs))
                else:
                    existing_fm = normalize_requirement_refs_value(wp_meta.requirement_refs)
                    if not existing_fm:
                        existing_fm = tasks_md_refs.get(wp_id, [])
                    merged_refs = sorted(set(existing_fm) | set(new_refs))
                update_kwargs["requirement_refs"] = merged_refs

            # T040 / FR-011 (F-10): merge tracker_refs (or replace if --replace).
            if tracker_ref_values and wp is not None and wp_id == wp.upper():
                if replace:
                    merged_trackers = sorted(set(tracker_ref_values))
                else:
                    existing_trackers = list(wp_meta.tracker_refs or [])
                    merged_trackers = sorted(set(existing_trackers) | set(tracker_ref_values))
                update_kwargs["tracker_refs"] = merged_trackers

            if update_kwargs:
                updated_meta = wp_meta.update(**update_kwargs)
                write_frontmatter(wp_file, updated_meta.model_dump(exclude_none=True), body)

        # Hard-fail on stale/invalid refs across all WPs.  This gate
        # prevents the tasks phase from advancing with a mapping-invalid
        # repo — finalize-tasks would reject it downstream anyway.
        all_wp_raw = read_all_wp_raw_requirement_refs(tasks_dir)
        all_raw_refs: list[str] = []
        for ref_list in all_wp_raw.values():
            all_raw_refs.extend(ref_list)

        # Raw tokens preserve case; uppercase for comparison
        uppercased_raw = [r.upper() for r in all_raw_refs if not r.startswith("<")]
        _, post_merge_malformed = validate_ref_format(uppercased_raw)
        _, post_merge_unknown = validate_refs(uppercased_raw, all_spec_ids)
        stale_refs: dict[str, list[str]] = {}
        if post_merge_malformed or post_merge_unknown:
            bad = set(post_merge_malformed) | set(post_merge_unknown)
            for wp_id, ref_list in all_wp_raw.items():
                wp_bad = sorted(token for token in ref_list if token.upper() in bad or token.startswith("<"))
                if wp_bad:
                    stale_refs[wp_id] = wp_bad

        if stale_refs:
            payload = {
                "error": "Stale or invalid refs in WP frontmatter",
                "stale_refs": stale_refs,
                "hint": ("Re-run with --replace to correct, e.g.: map-requirements --wp WP01 --refs FR-001 --replace"),
            }
            if json_output:
                print(json.dumps(payload))
            else:
                console.print("[red]Error:[/red] Stale or invalid refs in WP frontmatter:")
                for wp_id, bad_refs in sorted(stale_refs.items()):
                    console.print(f"  {wp_id}: {', '.join(bad_refs)}")
                console.print("  Use --replace to correct mappings")
            raise typer.Exit(1)

        all_wp_refs = read_all_wp_requirement_refs(tasks_dir)
        coverage = compute_coverage(all_wp_refs, functional_ids)

        # Auto-commit written WP files (consistent with move-task / update-subtasks)
        committed = False
        commit_sha: str | None = None
        commit_result_payload: dict[str, str] | None = None
        if auto_commit:
            written_files: list[Path] = []
            for wp_id in new_mappings:
                wp_file = next((f for f in tasks_dir.glob(f"{wp_id}*.md")), None)
                if wp_file is not None:
                    written_files.append(wp_file.resolve())
            if written_files:
                spec_number = mission_slug.split("-")[0] if "-" in mission_slug else mission_slug
                commit_msg = f"chore: Map requirements for {', '.join(sorted(new_mappings))} on spec {spec_number}"
                try:
                    # map-requirements edits WP prompt files → WORK_PACKAGE_TASK
                    # (a primary kind, write-surface-coherence WP03 / T014). Route
                    # the commit through the ONE canonical ``commit_for_mission``
                    # entry point (WP07 / FR-006) instead of the open-coded
                    # _planning_commit_worktree + safe_commit pair. The router owns
                    # placement resolution, the primary checkout selection, and the
                    # post-commit ff-advance; thread ``target_branch`` so the WP09
                    # ff-advance fires for a coord write (previously absent here).
                    _router_result = commit_for_mission(
                        main_repo_root,
                        mission_slug,
                        tuple(written_files),
                        commit_msg,
                        ProtectionPolicy.resolve(main_repo_root),
                        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
                        target_branch=target_branch,
                    )
                    if _router_result.status == "committed":
                        committed = True
                        commit_sha = _router_result.commit_hash
                        # Preserve the ``--json`` ``commit_result`` envelope shape
                        # (#1891 / FR-013): a primary kind commits from the primary
                        # checkout to ``commit_target.ref``, so reconstruct the same
                        # JSON-serializable mapping the ``CommitResult.to_dict()``
                        # carried — byte-identical to the pre-router payload.
                        commit_result_payload = {
                            "sha": _router_result.commit_hash,
                            "destination_ref": _router_result.placement_ref,
                            "worktree_root": str(main_repo_root),
                        }
                except Exception as exc_commit:
                    if not json_output:
                        console.print(f"[yellow]Warning:[/yellow] Auto-commit skipped: {exc_commit}")

        payload = {
            "result": "success",
            **_mission_identity_payload(primary_dir),
            "mapped": {wp_id: sorted(refs) for wp_id, refs in new_mappings.items()},
            "total_mappings": {wp_id: sorted(refs) for wp_id, refs in all_wp_refs.items() if refs},
            "coverage": coverage,
            "committed": committed,
            "commit_sha": commit_sha,
            "commit_result": commit_result_payload,
        }
        if json_output:
            print(json.dumps(payload))
        else:
            console.print("[green]✓[/green] Requirement mappings saved")
            for wp_id, ref_list in sorted(new_mappings.items()):
                console.print(f"  {wp_id}: {', '.join(ref_list)}")
            console.print(f"\n  Coverage: {coverage['mapped_functional']}/{coverage['total_functional']} FRs mapped")
            if coverage["unmapped_functional"]:
                console.print(f"  [yellow]Unmapped:[/yellow] {', '.join(coverage['unmapped_functional'])}")
            if committed:
                console.print("[cyan]→ Committed mapping changes[/cyan]")

    except typer.Exit:
        raise
    except Exception as exc:
        _output_error(json_output, str(exc))
        raise typer.Exit(1) from None


@app.command(name="validate-workflow")
def validate_workflow(
    task_id: Annotated[str, typer.Argument(help="Task ID (e.g., WP01)")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Validate task metadata structure and workflow consistency.

    Examples:
        spec-kitty agent tasks validate-workflow WP01 --json
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)

        # Load work package
        wp = locate_work_package(repo_root, mission_slug, task_id)

        # Validation checks
        errors = []
        warnings = []

        # Check required fields (lane is event-log-only, not required in frontmatter)
        required_fields = ["work_package_id", "title"]
        for field in required_fields:
            if not extract_scalar(wp.frontmatter, field):
                errors.append(f"Missing required field: {field}")

        # Get lane from event log (canonical source)
        _vw_feature_dir = resolve_feature_dir_for_mission(repo_root, mission_slug)
        try:
            from specify_cli.status import read_events as _vw_read_events
            from specify_cli.status import reduce as _vw_reduce

            _vw_events = _vw_read_events(_vw_feature_dir)
            _vw_snapshot = _vw_reduce(_vw_events) if _vw_events else None
            _vw_state = _vw_snapshot.work_packages.get(task_id) if _vw_snapshot else None
            lane_value = Lane(_vw_state.get("lane", Lane.PLANNED)) if _vw_state else Lane.PLANNED
        except Exception:
            lane_value = Lane.PLANNED

        # Check work_package_id matches filename
        wp_id = extract_scalar(wp.frontmatter, "work_package_id")
        if wp_id and not wp.path.name.startswith(wp_id):
            warnings.append(f"Work package ID '{wp_id}' doesn't match filename '{wp.path.name}'")

        # Check for activity log
        if "## Activity Log" not in wp.body:
            warnings.append("Missing Activity Log section")

        # Determine validity
        is_valid = len(errors) == 0

        result = {"valid": is_valid, "errors": errors, "warnings": warnings, "task_id": task_id, "lane": lane_value or "unknown"}

        if json_output:
            print(json.dumps(result))
        else:
            if is_valid:
                console.print(f"[green]✓[/green] {task_id} validation passed")
            else:
                console.print(f"[red]✗[/red] {task_id} validation failed")
                for error in errors:
                    console.print(f"  [red]Error:[/red] {error}")

            if warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in warnings:
                    console.print(f"  [yellow]•[/yellow] {warning}")

    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016)
        with contextlib.suppress(Exception):
            emit_error_logged(
                error_type="validation",
                error_message=str(e),
                wp_id=task_id if "task_id" in dir() else None,
                stack_trace=traceback.format_exc(),
            )
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="status")
def status(
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    stale_threshold: Annotated[int, typer.Option("--stale-threshold", help="Minutes of inactivity before a WP is considered stale")] = 10,
):
    """Display kanban status board for all work packages in a feature.

    Shows a beautiful overview of work package statuses, progress metrics,
    and next steps based on dependencies.

    WPs in "doing" with no commits for --stale-threshold minutes are flagged
    as potentially stale (agent may have stopped).

    Example:
        spec-kitty agent tasks status
        spec-kitty agent tasks status --mission 012-documentation-mission
        spec-kitty agent tasks status --json
        spec-kitty agent tasks status --stale-threshold 15
    """
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from collections import Counter

    try:
        cwd = Path.cwd().resolve()
        repo_root = locate_project_root(cwd)

        if repo_root is None:
            raise typer.Exit(1)

        # Auto-detect or use provided feature slug
        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)

        # Ensure we operate on the target branch for this feature
        # Write path: keep main-repo-root resolution so canonical serialization
        # pins to the primary checkout regardless of where the operator stands.
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)

        # Read-only path (WP08 T037, FR-030): route status reads through
        # the canonical resolver.  In the new topology the truth lives
        # in the per-mission coordination worktree; in legacy topology
        # (no coord worktree on disk) we fall back to the primary
        # checkout view.  Either way the resolution is CWD-independent:
        # spawning ``agent tasks status`` from a lane worktree, from the
        # primary checkout, or from any unrelated CWD all return the
        # same data.
        from specify_cli.missions._read_path_resolver import (
            resolve_handle_to_read_path,
        )

        # Route through the single guarded read-side seam (WP01/IC-01;
        # FR-002, C-007). The seam reads the PRIMARY ``meta.json`` and runs the
        # ONE sanctioned mid8 cascade (``resolve_declared_mid8``: ``meta.mid8`` →
        # ``resolve_mid8(meta.mission_id)`` → ``mid8_from_slug``), so a bare slug
        # whose primary meta declares ``mid8``/``mission_id`` resolves the real
        # disambiguator instead of the prior mid8-BLIND
        # ``resolve_mid8(slug, mission_id=None)`` (which always returned ""). The
        # seam still composes idempotently for an explicit ``<slug>-<mid8>``/full
        # ULID handle and routes through the existence-gated topology resolver.
        feature_dir = resolve_handle_to_read_path(main_repo_root, mission_slug)

        if not feature_dir.exists():
            # Last-ditch fallback to the original worktree-aware path so
            # tests / projects that stand up status files in unusual
            # places still work.  Surface a clear diagnostic when none
            # of the candidates carry the mission.
            status_read_root = get_status_read_root(cwd)
            legacy_dir = candidate_feature_dir_for_mission(status_read_root, mission_slug)
            if legacy_dir.exists():
                feature_dir = legacy_dir
            else:
                console.print(
                    f"[red]Error:[/red] Mission directory not found: {feature_dir}"
                )
                raise typer.Exit(1)

        tasks_dir = feature_dir / "tasks"

        if not tasks_dir.exists():
            console.print(f"[red]Error:[/red] Tasks directory not found: {tasks_dir}")
            raise typer.Exit(1)

        # Load canonical lanes from event log (lane is event-log-only)
        _st_snapshot = None
        _st_events: list[StatusEvent] = []
        _st_lanes: dict = {}
        try:
            from specify_cli.status import read_events as _st_read_events
            from specify_cli.status import reduce as _st_reduce

            _st_events = _st_read_events(feature_dir)
            _st_snapshot = _st_reduce(_st_events) if _st_events else None
            if _st_snapshot:
                for _st_wp_id, _st_state in _st_snapshot.work_packages.items():
                    _st_lanes[_st_wp_id] = Lane(_st_state.get("lane", Lane.GENESIS))
        except Exception:
            _st_events = []
            _st_lanes = {}

        # Collect all work packages
        work_packages = []
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            front, body, padding = split_frontmatter(wp_file.read_text(encoding="utf-8"))

            wp_id = extract_scalar(front, "work_package_id")
            title = extract_scalar(front, "title")
            lane = resolve_lane_alias(_st_lanes.get(wp_id or wp_file.stem, Lane.GENESIS))
            phase = extract_scalar(front, "phase") or "Unknown Phase"
            agent = extract_scalar(front, "agent") or ""
            agent_profile = extract_scalar(front, "agent_profile") or ""
            shell_pid = extract_scalar(front, "shell_pid") or ""
            try:
                workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, wp_id)
                execution_mode = workspace.execution_mode
                workspace_kind = workspace.resolution_kind
            except MissingLanesError:
                # Without lanes.json the resolver cannot return a workspace, but
                # we still want a meaningful execution_mode for status output.
                # Prefer the explicit frontmatter value, then the normalized
                # default, and only fall back to "code_change" if both are
                # missing — never blank.
                execution_mode = extract_scalar(front, "execution_mode") or ""
                if not execution_mode:
                    try:
                        normalized = get_normalized_wp(main_repo_root, mission_slug, wp_id)
                        execution_mode = normalized.metadata.execution_mode or "code_change"
                    except Exception:
                        execution_mode = "code_change"
                workspace_kind = "unknown"
            except (ValueError, FileNotFoundError):
                # Resolver could not classify; fall back to frontmatter and default.
                execution_mode = extract_scalar(front, "execution_mode") or "code_change"
                workspace_kind = "unknown"

            work_packages.append(
                {
                    "id": wp_id,
                    "title": title,
                    "lane": lane,
                    "phase": phase,
                    "file": wp_file.name,
                    "agent": agent,
                    "agent_profile": agent_profile,
                    "shell_pid": shell_pid,
                    "execution_mode": execution_mode,
                    "workspace_kind": workspace_kind,
                }
            )

        if not work_packages:
            console.print(f"[yellow]No work packages found in {tasks_dir}[/yellow]")
            raise typer.Exit(0)

        review_stall_threshold = _review_stall_threshold_minutes(main_repo_root)
        stale_verdicts, stalled_wps = _apply_review_status_flags(
            work_packages,
            tasks_dir=tasks_dir,
            events=_st_events,
            stall_threshold_minutes=review_stall_threshold,
        )

        # JSON output
        if json_output:
            # Check for stale WPs first (need to do this before JSON output too)
            from specify_cli.core.stale_detection import check_doing_wps_for_staleness

            doing_wps = [wp for wp in work_packages if wp["lane"] == Lane.IN_PROGRESS]
            try:
                stale_results = check_doing_wps_for_staleness(
                    main_repo_root=main_repo_root,
                    mission_slug=mission_slug,
                    doing_wps=doing_wps,
                    threshold_minutes=stale_threshold,
                )
            except MissingLanesError as exc:
                stale_results = _build_stale_fallback_results(doing_wps, exc)

            # Add staleness info to WPs
            for wp in work_packages:
                if wp["lane"] == Lane.IN_PROGRESS and wp["id"] in stale_results:
                    _apply_stale_status_fields(wp, stale_results[wp["id"]])

            lane_counts = Counter(wp["lane"] for wp in work_packages)
            stale_count = sum(1 for wp in work_packages if wp.get("is_stale"))
            auto_commit_enabled = get_auto_commit_default(main_repo_root)
            total_wps = len(work_packages)
            done_count = sum(1 for wp in work_packages if wp["lane"] == Lane.DONE)
            done_pct = round(compute_done_percentage(done_count, total_wps), 1)
            progress_pct = round(compute_weighted_progress(_st_snapshot).percentage, 1) if _st_snapshot else 0
            result = {
                **_mission_identity_payload(feature_dir),
                "total_wps": total_wps,
                "by_lane": dict(lane_counts),
                "work_packages": work_packages,
                "progress_percentage": progress_pct,
                "progress_semantics": PROGRESS_SEMANTICS,
                "weighted_percentage": progress_pct,
                "done_count": done_count,
                "done_percentage": done_pct,
                "stale_wps": stale_count,
                "stale_verdicts": stale_verdicts,
                "stalled_wps": stalled_wps,
                "auto_commit": auto_commit_enabled,
            }
            print(json.dumps(result, indent=2))
            return

        # Rich table output
        # Group by lane — exclude GENESIS (non-display lane; no WP should be in
        # genesis at display time, but if one is it falls through to "other")
        by_lane = {lane: [] for lane in Lane if lane is not Lane.GENESIS}
        for wp in work_packages:
            lane = wp["lane"]
            if lane in by_lane:
                by_lane[lane].append(wp)
            else:
                by_lane.setdefault("other", []).append(wp)

        # Check for stale WPs in "doing" lane
        from specify_cli.core.stale_detection import check_doing_wps_for_staleness

        try:
            stale_results = check_doing_wps_for_staleness(
                main_repo_root=main_repo_root,
                mission_slug=mission_slug,
                doing_wps=by_lane[Lane.IN_PROGRESS],
                threshold_minutes=stale_threshold,
            )
        except MissingLanesError as exc:
            stale_results = _build_stale_fallback_results(by_lane[Lane.IN_PROGRESS], exc)

        try:
            from doctrine.agent_profiles.repository import AgentProfileRepository

            profile_repo = AgentProfileRepository(built_in_dir=main_repo_root / "src" / "doctrine" / "agent_profiles" / "built-in")
        except Exception:
            profile_repo = None

        # Add staleness info to WPs
        for wp in by_lane[Lane.IN_PROGRESS]:
            wp_id = wp["id"]
            if wp_id in stale_results:
                _apply_stale_status_fields(wp, stale_results[wp_id])
            else:
                wp["is_stale"] = False

        # Calculate metrics
        total = len(work_packages)
        done_count = len(by_lane[Lane.DONE])
        in_progress = len(by_lane[Lane.CLAIMED]) + len(by_lane[Lane.IN_PROGRESS]) + len(by_lane[Lane.IN_REVIEW]) + len(by_lane[Lane.FOR_REVIEW])
        planned_count = len(by_lane[Lane.PLANNED])
        progress_pct = round(compute_weighted_progress(_st_snapshot).percentage, 1) if _st_snapshot else 0
        done_pct = round(compute_done_percentage(done_count, total), 1)

        # Create title panel
        title_text = Text()
        title_text.append("📊 Work Package Status: ", style="bold cyan")
        title_text.append(mission_slug, style="bold white")

        console.print()
        console.print(Panel(title_text, border_style="cyan"))

        # Progress bar
        progress_text = Text()
        progress_text.append("Done progress: ", style="bold")
        progress_text.append(f"{done_count}/{total}", style="bold green")
        progress_text.append(f" ({done_pct}%)", style="dim")
        progress_text.append("\nWeighted readiness: ", style="bold")
        progress_text.append(f"{progress_pct}%", style="bold cyan")

        # Create visual readiness bar
        bar_width = 40
        filled = int(bar_width * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        progress_text.append(f"\n{bar}", style="green")

        console.print(progress_text)
        console.print()

        # Kanban board table
        # Fold claimed and in_review WPs into the "Doing" column with markers.
        display_in_progress = []
        for wp in by_lane[Lane.CLAIMED]:
            wp["_display_claimed"] = True
            display_in_progress.append(wp)
        display_in_progress.extend(by_lane[Lane.IN_PROGRESS])
        for wp in by_lane.get(Lane.IN_REVIEW, []):
            wp["_display_in_review"] = True
            display_in_progress.append(wp)
        table = Table(title="Kanban Board", show_header=True, header_style="bold magenta", border_style="dim")
        table.add_column("📋 Planned", style="yellow", no_wrap=False, width=25)
        table.add_column("🔄 Doing", style="blue", no_wrap=False, width=25)
        table.add_column("👀 For Review", style="cyan", no_wrap=False, width=25)
        table.add_column("👍 Approved", style="magenta", no_wrap=False, width=25)
        table.add_column("✅ Done", style="green", no_wrap=False, width=25)

        # Find max length for rows
        max_rows = max(len(by_lane[Lane.PLANNED]), len(display_in_progress), len(by_lane[Lane.FOR_REVIEW]), len(by_lane[Lane.APPROVED]), len(by_lane[Lane.DONE]))

        # Map display column keys to their data lists
        display_columns = [
            (Lane.PLANNED, by_lane[Lane.PLANNED]),
            (Lane.IN_PROGRESS, display_in_progress),
            (Lane.FOR_REVIEW, by_lane[Lane.FOR_REVIEW]),
            (Lane.APPROVED, by_lane[Lane.APPROVED]),
            (Lane.DONE, by_lane[Lane.DONE]),
        ]

        # Add rows
        for i in range(max_rows):
            row = []
            for lane, lane_list in display_columns:
                if i < len(lane_list):
                    wp = lane_list[i]
                    title_truncated = wp["title"][:22] + "..." if len(wp["title"]) > 22 else wp["title"]
                    marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                    display_id = f"{marker}{wp['id']}"

                    # Add stale indicator for in_progress WPs
                    if wp.get("_stale_verdict"):
                        cell = f"[yellow]⚠ {display_id}[/yellow]\n{title_truncated}"
                    elif lane == Lane.IN_PROGRESS and wp.get("is_stale"):
                        cell = f"[red]⚠️ {display_id}[/red]\n{title_truncated}"
                    elif wp.get("_stall_label"):
                        cell = f"[yellow]⚠ {display_id} (review)[/yellow]\n{title_truncated}"
                    elif wp.get("_display_claimed"):
                        cell = f"[blue]{display_id} (claimed)[/blue]\n{title_truncated}"
                    elif wp.get("_display_in_review"):
                        cell = f"[bright_cyan]{display_id} (review)[/bright_cyan]\n{title_truncated}"
                    else:
                        cell = f"{display_id}\n{title_truncated}"
                    row.append(cell)
                else:
                    row.append("")
            table.add_row(*row)

        # Add count row
        table.add_row(
            f"[bold]{len(by_lane[Lane.PLANNED])} WPs[/bold]",
            f"[bold]{len(display_in_progress)} WPs[/bold]",
            f"[bold]{len(by_lane[Lane.FOR_REVIEW])} WPs[/bold]",
            f"[bold]{len(by_lane[Lane.APPROVED])} WPs[/bold]",
            f"[bold]{len(by_lane[Lane.DONE])} WPs[/bold]",
            style="dim",
        )

        console.print(table)
        console.print()

        # --- Arbiter override history (T034) ---
        # Peek at review-cycle artifacts to surface any arbiter overrides.
        try:
            from specify_cli.review.arbiter import get_arbiter_overrides_for_wp

            arbiter_lines: list[str] = []
            for wp in work_packages:
                wp_id_val = wp.get("id") or ""
                if not wp_id_val:
                    continue
                overrides = get_arbiter_overrides_for_wp(feature_dir, wp_id_val)
                for idx, override in enumerate(overrides, start=1):
                    cat = override.get("category", "custom")
                    arbiter_lines.append(f"  • {wp_id_val} Cycle {idx}: rejected → [yellow]overridden[/yellow] ({cat})")

            if arbiter_lines:
                console.print("[bold yellow]⚖️  Arbiter Override History:[/bold yellow]")
                for line in arbiter_lines:
                    console.print(line)
                console.print()
        except ImportError:
            pass  # review package not yet available

        # Next steps section
        if by_lane[Lane.FOR_REVIEW]:
            console.print("[bold cyan]👀 Ready for Review:[/bold cyan]")
            for wp in by_lane[Lane.FOR_REVIEW]:
                marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                console.print(f"  • {marker}{wp['id']} - {wp['title']}")
            console.print()

        if by_lane[Lane.APPROVED]:
            console.print("[bold magenta]👍 Approved (merge when all WPs approved):[/bold magenta]")
            for wp in by_lane[Lane.APPROVED]:
                marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                line = f"  • {marker}{wp['id']} - {wp['title']}"
                if wp.get("_stale_verdict"):
                    line += "  [bold yellow]⚠ review artifact: verdict=rejected[/bold yellow]"
                console.print(line)
            console.print("[dim]   Approved WPs stay here until feature merge. Dependents can start immediately.[/dim]")
            console.print()

        done_stale = [wp for wp in by_lane[Lane.DONE] if wp.get("_stale_verdict")]
        if done_stale:
            console.print("[bold green]✅ Done (with stale verdict warnings):[/bold green]")
            for wp in done_stale:
                marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                console.print(
                    f"  • {marker}{wp['id']} - {wp['title']}"
                    "  [bold yellow]⚠ review artifact: verdict=rejected[/bold yellow]"
                )
            console.print()

        if by_lane[Lane.CLAIMED]:
            console.print("[bold blue]🔄 Claimed (shown in Doing column):[/bold blue]")
            for wp in by_lane[Lane.CLAIMED]:
                marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                agent = wp.get("agent", "unknown")
                console.print(f"  • {marker}{wp['id']} - {wp['title']} [dim](agent: {agent})[/dim]")
            console.print()

        if by_lane[Lane.IN_PROGRESS]:
            console.print("[bold blue]🔄 In Progress:[/bold blue]")
            stale_wps = []
            for wp in by_lane[Lane.IN_PROGRESS]:
                marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                stale_label = _render_stale_status(stale_results.get(wp["id"]))
                agent = wp.get("agent", "unknown")
                if wp.get("is_stale"):
                    console.print(f"  • [red]⚠️ {marker}{wp['id']}[/red] - {wp['title']} [dim]({stale_label}, agent: {agent})[/dim]")
                    stale_wps.append(wp)
                elif stale_label:
                    console.print(f"  • {marker}{wp['id']} - {wp['title']} [dim]({stale_label}, agent: {agent})[/dim]")
                else:
                    console.print(f"  • {marker}{wp['id']} - {wp['title']}")
            console.print()

            # Show stale warning if any
            if stale_wps:
                console.print(f"[yellow]⚠️  {len(stale_wps)} stale WP(s) detected - agents may have stopped without transitioning[/yellow]")
                console.print("[dim]   Run: spec-kitty agent tasks move-task <WP_ID> --to for_review[/dim]")
                console.print()

        if by_lane.get(Lane.IN_REVIEW):
            console.print("[bold bright_cyan]🔍 In Review (shown in Doing column):[/bold bright_cyan]")
            for wp in by_lane[Lane.IN_REVIEW]:
                marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                line = f"  • {marker}{wp['id']} - {wp['title']}"
                if wp.get("_stall_label"):
                    line += f"  [bold yellow]⚠ {wp['_stall_label']}[/bold yellow]"
                console.print(line)
            console.print()

        if by_lane[Lane.PLANNED]:
            console.print("[bold yellow]📋 Next Up (Planned):[/bold yellow]")
            # Show first 3 planned items
            for wp in by_lane[Lane.PLANNED][:3]:
                marker = _get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
                console.print(f"  • {marker}{wp['id']} - {wp['title']}")
            if len(by_lane[Lane.PLANNED]) > 3:
                console.print(f"  [dim]... and {len(by_lane[Lane.PLANNED]) - 3} more[/dim]")
            console.print()

        # Summary metrics
        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold")
        summary.add_column()
        summary.add_row("Total WPs:", str(total))
        summary.add_row("Completed:", f"[green]{done_count}[/green] ({done_pct}%)")
        summary.add_row("Weighted readiness:", f"[cyan]{progress_pct}%[/cyan]")
        summary.add_row("In Progress:", f"[blue]{in_progress}[/blue]")
        summary.add_row("Planned:", f"[yellow]{planned_count}[/yellow]")

        # Show auto-commit mode
        auto_commit_enabled = get_auto_commit_default(main_repo_root)
        auto_commit_label = "[green]enabled[/green]" if auto_commit_enabled else "[yellow]disabled[/yellow]"
        summary.add_row("Auto-commit:", auto_commit_label)

        console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="dim"))

        # Next action hint — always show so agents know what to do
        console.print("[bold]▶ Next action:[/bold]")
        console.print(f"  [cyan]spec-kitty next --agent <your-name> --mission {mission_slug}[/cyan]")
        console.print("[dim]  This command tells you exactly what to do next based on the dependency graph.[/dim]")
        console.print()

    except typer.Exit:
        raise
    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None


@app.command(name="list-dependents")
def list_dependents(
    wp_id: Annotated[str, typer.Argument(help="Work package ID (e.g., WP01)")],
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,

    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Find all WPs that depend on a given WP (downstream dependents).

    This answers "who depends on me?" - useful when reviewing a WP to understand
    the impact of requested changes on downstream work packages.

    Also shows what the WP itself depends on (upstream dependencies).

    Examples:
        spec-kitty agent tasks list-dependents WP13
        spec-kitty agent tasks list-dependents WP01 --mission 001-my-feature --json
    """
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, json_output=json_output, repo_root=repo_root)
        main_repo_root, _ = _ensure_target_branch_checked_out(repo_root, mission_slug, json_output)
        feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)

        if not feature_dir.exists():
            _output_error(json_output, f"Mission directory not found: {feature_dir}")
            raise typer.Exit(1)

        # Build dependency graph and find dependents
        graph = build_dependency_graph(feature_dir)
        dependents = get_dependents(wp_id, graph)

        # Also get this WP's own dependencies for context
        try:
            wp = locate_work_package(repo_root, mission_slug, wp_id)
            own_deps_raw = extract_scalar(wp.frontmatter, "dependencies")
            # Handle both list and string formats
            if isinstance(own_deps_raw, list):
                own_deps = own_deps_raw
            elif own_deps_raw:
                own_deps = [own_deps_raw]
            else:
                own_deps = []
        except Exception:
            own_deps = []

        if json_output:
            print(json.dumps({"wp_id": wp_id, "depends_on": own_deps, "dependents": dependents}))
        else:
            console.print(f"\n[bold]{wp_id} Dependency Info:[/bold]")
            console.print(f"  Depends on: {', '.join(own_deps) if own_deps else '[dim](none)[/dim]'}")
            console.print(f"  Depended on by: {', '.join(dependents) if dependents else '[dim](none)[/dim]'}")

            if dependents:
                console.print(f"\n[yellow]⚠️  Changes to {wp_id} may impact: {', '.join(dependents)}[/yellow]")
            console.print()

    except Exception as e:
        _output_error(json_output, str(e))
        raise typer.Exit(1) from None
