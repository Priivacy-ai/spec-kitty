"""Execution-state resolution entry point (canonical surface, internal module).

This is an **internal** submodule of the :mod:`mission_runtime` umbrella. It is
import-forbidden from outside the package — consumers use the symbols re-exported
from :mod:`mission_runtime` only (see ADR 2026-06-07-1 and
``tests/architectural/test_mission_runtime_surface.py``).

WP03 relocates the hardened ``resolve_action_context`` (and its helpers) from
``specify_cli.core.execution_context`` here under the Strangler migration. The
implementation is moved verbatim — this is the single sanctioned resolver
(FR-003/FR-005); behaviour is preserved (NFR-001) and no parallel resolver
survives (NFR-002). The old ``core/execution_context.py`` is removed entirely —
no importers remained after the caller migration, so it is deleted, not shimmed.

Prompts should not discover context on their own. They call into this
command-owned resolver, which determines the active mission, target branch,
work package, workspace path, and any action-specific commands to run.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, cast, get_args

from mission_runtime.context import ExecutionContext


ActionName = Literal[
    "tasks",
    "tasks_outline",
    "tasks_packages",
    "tasks_finalize",
    "implement",
    "review",
    "accept",
]
ACTION_NAMES: tuple[str, ...] = cast(tuple[str, ...], get_args(ActionName))


class ActionContextError(RuntimeError):
    """Raised when canonical action context cannot be resolved.

    The single error type consumers catch. The resolver raises this on
    unresolvable context — there is never a silent fallback (see the contract).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _resolve_mission_slug(
    repo_root: Path,
    *,
    feature: str | None,
    cwd: Path | None,  # noqa: ARG001 -- kept for signature compatibility
    env: Mapping[str, str] | None,  # noqa: ARG001 -- kept for signature compatibility
) -> tuple[str, Path]:
    """Resolve mission slug and read-side directory.

    Mission directory resolution is CWD-independent and topology-aware
    (WP08 T037, FR-030): for missions on the coord-branch topology the
    returned ``feature_dir`` points into the coordination worktree;
    for legacy missions it points into the primary checkout.  The
    caller never has to guess which view the operator is sitting in.

    Raises ActionContextError if feature is not provided or the mission
    directory cannot be located in either view.
    """
    from specify_cli.core.paths import require_explicit_feature

    try:
        slug = require_explicit_feature(feature, command_hint="--mission <slug>")
    except ValueError as exc:
        raise ActionContextError("FEATURE_CONTEXT_UNRESOLVED", str(exc)) from exc

    # Derive mid8 from the post-WP03 ``<slug>-<mid8>`` shape when present.
    mid8 = _read_side_mid8_from_slug(slug)

    # Late import to avoid a hard module-load dependency for legacy
    # consumers of the resolver that pre-date its introduction.
    from specify_cli.missions._read_path_resolver import (
        resolve_mission_read_path,
    )

    feature_dir = resolve_mission_read_path(repo_root, slug, mid8)
    if not feature_dir.exists():
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED",
            f"Mission directory not found: {feature_dir}. Check that "
            f"'{slug}' is the correct mission slug.",
        )
    return slug, feature_dir


def _read_side_mid8_from_slug(slug: str) -> str:
    from specify_cli.lanes.branch_naming import mid8_from_slug

    parsed = mid8_from_slug(slug)
    if parsed:
        return str(parsed)
    tail = slug.rsplit("-", 1)[-1] if "-" in slug else ""
    if len(tail) == 8 and tail == tail.upper() and tail.isalnum():
        return tail
    return ""


def _tasks_commands(mission_slug: str) -> dict[str, str]:
    return {
        "check_prerequisites": (f"spec-kitty agent mission check-prerequisites --json --paths-only --include-tasks --mission {mission_slug}"),
        "finalize_tasks": (f"spec-kitty agent mission finalize-tasks --mission {mission_slug} --json"),
    }


def _find_first_wp(feature_dir: Path, lane: str) -> str | None:
    """Find the first WP with the given lane from the canonical event log."""
    import re as _re
    from specify_cli.status import CanonicalStatusNotFoundError
    from specify_cli.status import Lane
    from specify_cli.status import get_wp_lane
    from specify_cli.status import resolve_lane_alias

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        wp_match = _re.match(r"(WP\d+)", wp_file.stem)
        if wp_match is None:
            continue
        wp_id = wp_match.group(1)
        try:
            wp_lane_raw = str(get_wp_lane(feature_dir, wp_id))
        except CanonicalStatusNotFoundError:
            wp_lane_raw = Lane.PLANNED
        # WPs with no canonical event yet (or an "uninitialized" sentinel) are
        # treated as planned for the purposes of "find the first WP in this
        # lane". This matches the legacy ``event_log_lanes.get(wp_id, "planned")``
        # fallback that previous iterations used and keeps zero-migration
        # support (FR-019) intact for missions that have not emitted events for
        # every WP.
        if wp_lane_raw == "uninitialized":
            wp_lane_raw = Lane.PLANNED
        wp_lane = resolve_lane_alias(wp_lane_raw)
        if wp_lane == lane:
            return wp_id
    return None


def _resolve_review_wp_id(feature_dir: Path) -> str | None:
    """Find the WP to review: first ``for_review``, else a review-claimed WP."""
    from specify_cli.status import CanonicalStatusNotFoundError
    from specify_cli.status import Lane
    from specify_cli.status import get_wp_lane
    from specify_cli.status import read_events
    from specify_cli.task_utils import extract_scalar, split_frontmatter

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    try:
        events = read_events(feature_dir)

        candidate_wp_ids = _review_candidate_wp_ids(
            tasks_dir,
            extract_scalar=extract_scalar,
            split_frontmatter=split_frontmatter,
        )

        review_ready_wp_id = _first_wp_in_lane(
            feature_dir,
            candidate_wp_ids,
            target_lane=Lane.FOR_REVIEW,
            get_wp_lane=get_wp_lane,
        )
        if review_ready_wp_id is not None:
            return review_ready_wp_id

        for candidate_wp_id in candidate_wp_ids:
            candidate_lane = get_wp_lane(feature_dir, candidate_wp_id)
            if candidate_lane not in (Lane.IN_PROGRESS, Lane.IN_REVIEW):
                continue
            if _is_review_claimed(events, candidate_wp_id, Lane=Lane):
                return candidate_wp_id
    except CanonicalStatusNotFoundError as exc:
        raise ActionContextError("CANONICAL_STATUS_NOT_FOUND", str(exc)) from exc
    except ActionContextError:
        raise
    except Exception:
        return None
    return None


def _review_candidate_wp_ids(
    tasks_dir: Path,
    *,
    extract_scalar: Callable[[str, str], str | None],
    split_frontmatter: Callable[[str], tuple[str, str, str]],
) -> list[str]:
    candidate_wp_ids: list[str] = []
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        frontmatter = split_frontmatter(wp_file.read_text(encoding="utf-8-sig"))[0]
        candidate_wp_id = extract_scalar(frontmatter, "work_package_id")
        if candidate_wp_id:
            candidate_wp_ids.append(str(candidate_wp_id))
    return candidate_wp_ids


def _first_wp_in_lane(
    feature_dir: Path,
    candidate_wp_ids: list[str],
    *,
    target_lane: object,
    get_wp_lane: Callable[[Path, str], object],
) -> str | None:
    for candidate_wp_id in candidate_wp_ids:
        if get_wp_lane(feature_dir, candidate_wp_id) == target_lane:
            return candidate_wp_id
    return None


def _is_review_claimed(events: Sequence[Any], candidate_wp_id: str, *, Lane: Any) -> bool:
    latest_event = next(
        (
            event
            for event in reversed(events)
            if getattr(event, "wp_id", None) == candidate_wp_id
        ),
        None,
    )
    if latest_event is None:
        return False
    return bool(
        latest_event.to_lane == Lane.IN_REVIEW
        or (
            latest_event.to_lane == Lane.IN_PROGRESS
            and latest_event.review_ref == "action-review-claim"
        )
    )


def _resolve_wp_id(
    action: ActionName,
    feature_dir: Path,
    explicit_wp_id: str | None,
) -> str | None:
    from specify_cli.status import Lane

    if explicit_wp_id:
        return explicit_wp_id.upper().split("-", 1)[0]

    if action == "implement":
        for lane in (Lane.PLANNED, Lane.IN_PROGRESS):
            wp_id = _find_first_wp(feature_dir, lane)
            if wp_id:
                return wp_id
        return None

    if action == "review":
        return _resolve_review_wp_id(feature_dir)

    return None


def resolve_action_context(
    repo_root: Path,
    *,
    action: ActionName,
    feature: str | None = None,
    wp_id: str | None = None,
    agent: str | None = None,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ExecutionContext:
    """Resolve canonical mission/work-package context for an agent action.

    CWD-invariant, topology-aware, mode-correct. Raises
    :class:`ActionContextError` on unresolvable context (no silent fallback).
    """
    if action not in ACTION_NAMES:
        raise ActionContextError(
            "INVALID_ACTION",
            f"Invalid action '{action}'. Expected one of: {', '.join(ACTION_NAMES)}.",
        )

    from specify_cli.core.dependency_graph import parse_wp_dependencies
    from specify_cli.core.paths import get_feature_target_branch
    from specify_cli.status import Lane
    from specify_cli.status import resolve_lane_alias
    from specify_cli.task_utils import locate_work_package
    from specify_cli.workspace.context import resolve_workspace_for_wp

    mission_slug, feature_dir = _resolve_mission_slug(repo_root, feature=feature, cwd=cwd, env=env)
    target_branch = get_feature_target_branch(repo_root, mission_slug)

    context = ExecutionContext(
        action=action,
        mission_slug=mission_slug,
        feature_dir=str(feature_dir),
        target_branch=target_branch,
        detection_method="explicit",
        commands=_tasks_commands(mission_slug),
    )

    if action in {"tasks", "tasks_outline", "tasks_packages", "tasks_finalize", "accept"}:
        return context

    normalized_wp_id = _resolve_wp_id(action, feature_dir, wp_id)
    if normalized_wp_id is None:
        raise ActionContextError(
            "WORK_PACKAGE_UNRESOLVED",
            f"No work package available for action '{action}' in feature {mission_slug}.",
        )

    try:
        wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
    except Exception as exc:
        raise ActionContextError("WORK_PACKAGE_UNRESOLVED", str(exc)) from exc

    dependencies = parse_wp_dependencies(wp.path)
    # Lane is event-log-only; read from canonical event log not frontmatter.
    # WPs without a canonical event yet (or with the "uninitialized" sentinel)
    # are treated as ``planned`` so legacy missions that have not emitted events
    # for every WP still resolve.
    try:
        from specify_cli.status import CanonicalStatusNotFoundError
        from specify_cli.status import get_wp_lane as _ec_get_wp_lane

        _ec_raw_lane = str(_ec_get_wp_lane(feature_dir, normalized_wp_id))
    except CanonicalStatusNotFoundError:
        _ec_raw_lane = Lane.PLANNED
    except Exception as exc:
        raise ActionContextError("CANONICAL_STATUS_UNREADABLE", str(exc)) from exc
    if _ec_raw_lane == "uninitialized":
        _ec_raw_lane = Lane.PLANNED
    lane = resolve_lane_alias(_ec_raw_lane)
    workspace = resolve_workspace_for_wp(repo_root, mission_slug, normalized_wp_id)

    context.wp_id = normalized_wp_id
    context.wp_file = str(wp.path)
    context.lane = lane
    context.lane_id = workspace.lane_id
    context.branch_name = workspace.branch_name
    context.execution_mode = workspace.execution_mode
    context.resolution_kind = workspace.resolution_kind
    context.dependencies = dependencies
    context.workspace_path = str(workspace.worktree_path)

    if action == "implement":
        command = f"spec-kitty agent action implement {normalized_wp_id}"
        if agent:
            command += f" --agent {agent}"
        context.commands["workflow"] = command
        return context

    command = f"spec-kitty agent action review {normalized_wp_id}"
    if agent:
        command += f" --agent {agent}"
    context.commands["workflow"] = command
    context.commands["approve"] = f'spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed: <summary>"'
    context.commands["reject"] = f"spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file <feedback-file> --mission {mission_slug}"
    return context
