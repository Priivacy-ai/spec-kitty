"""Resolve canonical action context for agent-facing workflows.

Prompts should not discover context on their own. They should call into a
command-owned resolver that determines the active feature, target branch,
work package, workspace path, and any action-specific commands to run.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Mapping, cast, get_args

from specify_cli.core.dependency_graph import parse_wp_dependencies
from specify_cli.core.paths import get_feature_target_branch, require_explicit_feature
from specify_cli.status.models import Lane
from specify_cli.status.transitions import resolve_lane_alias
from specify_cli.tasks_support import extract_scalar, locate_work_package, split_frontmatter
from specify_cli.workspace_context import resolve_workspace_for_wp


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
    """Raised when canonical action context cannot be resolved."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class ActionContext:
    action: str
    mission_slug: str
    feature_dir: str
    target_branch: str
    detection_method: str
    wp_id: str | None = None
    wp_file: str | None = None
    lane: str | None = None
    lane_id: str | None = None
    branch_name: str | None = None
    execution_mode: str | None = None
    resolution_kind: str | None = None
    dependencies: list[str] = field(default_factory=list)
    resolved_base: str | None = None
    auto_merge: bool = False
    workspace_path: str | None = None
    commands: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _resolve_mission_slug(
    repo_root: Path,
    *,
    feature: str | None,
    cwd: Path | None,  # noqa: ARG001 -- kept for signature compatibility
    env: Mapping[str, str] | None,  # noqa: ARG001 -- kept for signature compatibility
) -> tuple[str, Path]:
    """Resolve mission slug and directory from an explicit --mission value.

    Raises ActionContextError if feature is not provided or directory doesn't exist.
    """
    try:
        slug = require_explicit_feature(feature, command_hint="--mission <slug>")
    except ValueError as exc:
        raise ActionContextError("FEATURE_CONTEXT_UNRESOLVED", str(exc)) from exc

    feature_dir = repo_root / "kitty-specs" / slug
    if not feature_dir.exists():
        raise ActionContextError(
            "FEATURE_CONTEXT_UNRESOLVED",
            f"Mission directory not found: {feature_dir}. Check that '{slug}' is the correct mission slug.",
        )
    return slug, feature_dir


def _tasks_commands(mission_slug: str) -> dict[str, str]:
    return {
        "check_prerequisites": (f"spec-kitty agent mission check-prerequisites --json --paths-only --include-tasks --mission {mission_slug}"),
        "finalize_tasks": (f"spec-kitty agent mission finalize-tasks --mission {mission_slug} --json"),
    }


def _find_first_wp(feature_dir: Path, lane: str) -> str | None:
    """Find the first WP with the given lane from the canonical event log."""
    import re as _re
    from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
    from specify_cli.status.lane_reader import get_wp_lane

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


def _resolve_wp_id(
    action: ActionName,
    feature_dir: Path,
    explicit_wp_id: str | None,
) -> str | None:
    if explicit_wp_id:
        return explicit_wp_id.upper().split("-", 1)[0]

    if action == "implement":
        for lane in (Lane.PLANNED, Lane.IN_PROGRESS):
            wp_id = _find_first_wp(feature_dir, lane)
            if wp_id:
                return wp_id
        return None

    if action == "review":
        try:
            from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
            from specify_cli.status.lane_reader import get_wp_lane
            from specify_cli.status.store import read_events
            from specify_cli.tasks_support import extract_scalar, split_frontmatter

            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.is_dir():
                return None

            events = read_events(feature_dir)

            def _is_review_claimed(_wp_id: str) -> bool:
                for event in reversed(events):
                    if getattr(event, "wp_id", None) == _wp_id:
                        return bool(
                            event.to_lane == Lane.IN_REVIEW  # new canonical shape
                            or (
                                event.to_lane == Lane.IN_PROGRESS  # legacy shape
                                and event.review_ref == "action-review-claim"
                            )
                        )
                return False

            for wp_file in sorted(tasks_dir.glob("WP*.md")):
                content = wp_file.read_text(encoding="utf-8-sig")
                frontmatter, _, _ = split_frontmatter(content)
                candidate_wp_id = extract_scalar(frontmatter, "work_package_id")
                if not candidate_wp_id:
                    continue
                lane = get_wp_lane(feature_dir, candidate_wp_id)
                if lane == Lane.FOR_REVIEW:
                    return candidate_wp_id

            for wp_file in sorted(tasks_dir.glob("WP*.md")):
                content = wp_file.read_text(encoding="utf-8-sig")
                frontmatter, _, _ = split_frontmatter(content)
                candidate_wp_id = extract_scalar(frontmatter, "work_package_id")
                if not candidate_wp_id:
                    continue
                lane = get_wp_lane(feature_dir, candidate_wp_id)
                if lane in (Lane.IN_PROGRESS, Lane.IN_REVIEW) and _is_review_claimed(candidate_wp_id):
                    return candidate_wp_id
        except CanonicalStatusNotFoundError as exc:
            raise ActionContextError("CANONICAL_STATUS_NOT_FOUND", str(exc)) from exc
        except ActionContextError:
            raise
        except Exception:
            return None
        return None

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
) -> ActionContext:
    """Resolve canonical feature/work-package context for an agent action."""
    if action not in ACTION_NAMES:
        raise ActionContextError(
            "INVALID_ACTION",
            f"Invalid action '{action}'. Expected one of: {', '.join(ACTION_NAMES)}.",
        )

    mission_slug, feature_dir = _resolve_mission_slug(repo_root, feature=feature, cwd=cwd, env=env)
    target_branch = get_feature_target_branch(repo_root, mission_slug)

    context = ActionContext(
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
        from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
        from specify_cli.status.lane_reader import get_wp_lane as _ec_get_wp_lane

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
