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
from specify_cli.core.feature_detection import (
    FeatureContext,
    detect_feature,
    get_feature_target_branch,
)
from specify_cli.core.implement_validation import (
    BaseResolutionError,
    validate_and_resolve_base,
)
from specify_cli.status.transitions import resolve_lane_alias
from specify_cli.tasks_support import extract_scalar, locate_work_package, split_frontmatter


ActionName = Literal[
    "tasks",
    "tasks_outline",
    "tasks_packages",
    "tasks_finalize",
    "implement",
    "review",
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
    feature_slug: str
    feature_dir: str
    target_branch: str
    detection_method: str
    wp_id: str | None = None
    wp_file: str | None = None
    lane: str | None = None
    dependencies: list[str] = field(default_factory=list)
    resolved_base: str | None = None
    auto_merge: bool = False
    workspace_path: str | None = None
    commands: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _resolve_feature_context(
    repo_root: Path,
    *,
    feature: str | None,
    cwd: Path | None,
    env: Mapping[str, str] | None,
) -> FeatureContext:
    try:
        ctx = detect_feature(
            repo_root,
            explicit_feature=feature,
            cwd=cwd,
            env=env,
            mode="strict",
            allow_latest_incomplete=True,
        )
    except Exception as exc:
        raise ActionContextError("MISSION_CONTEXT_UNRESOLVED", str(exc)) from exc
    if ctx is None:
        raise ActionContextError(
            "MISSION_CONTEXT_UNRESOLVED",
            "Could not resolve feature context.",
        )
    return ctx


def _tasks_commands(feature_slug: str) -> dict[str, str]:
    return {
        "check_prerequisites": (
            "spec-kitty agent mission check-prerequisites "
            f"--json --paths-only --include-tasks --mission {feature_slug}"
        ),
        "finalize_tasks": (
            f"spec-kitty agent mission finalize-tasks --mission {feature_slug} --json"
        ),
    }


def _find_first_wp(feature_dir: Path, lane: str) -> str | None:
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return None

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        wp_lane = resolve_lane_alias(extract_scalar(frontmatter, "lane") or "planned")
        if wp_lane == lane:
            wp_id = extract_scalar(frontmatter, "work_package_id")
            if wp_id:
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
        for lane in ("planned", "in_progress"):
            wp_id = _find_first_wp(feature_dir, lane)
            if wp_id:
                return wp_id
        return None

    if action == "review":
        for lane in ("for_review", "in_progress"):
            wp_id = _find_first_wp(feature_dir, lane)
            if wp_id:
                return wp_id
        return None

    return None


def resolve_action_context(
    repo_root: Path,
    *,
    action: ActionName,
    feature: str | None = None,
    wp_id: str | None = None,
    base: str | None = None,
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

    feature_ctx = _resolve_feature_context(repo_root, feature=feature, cwd=cwd, env=env)
    feature_slug = feature_ctx.slug
    feature_dir = feature_ctx.directory
    target_branch = get_feature_target_branch(repo_root, feature_slug)

    context = ActionContext(
        action=action,
        feature_slug=feature_slug,
        feature_dir=str(feature_dir),
        target_branch=target_branch,
        detection_method=feature_ctx.detection_method,
        commands=_tasks_commands(feature_slug),
    )

    if action in {"tasks", "tasks_outline", "tasks_packages", "tasks_finalize"}:
        return context

    normalized_wp_id = _resolve_wp_id(action, feature_dir, wp_id)
    if normalized_wp_id is None:
        raise ActionContextError(
            "WORK_PACKAGE_UNRESOLVED",
            f"No work package available for action '{action}' in feature {feature_slug}.",
        )

    try:
        wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)
    except Exception as exc:
        raise ActionContextError("WORK_PACKAGE_UNRESOLVED", str(exc)) from exc

    dependencies = parse_wp_dependencies(wp.path)
    lane = resolve_lane_alias(wp.lane or "planned")
    workspace_path = repo_root / ".worktrees" / f"{feature_slug}-{normalized_wp_id}"

    context.wp_id = normalized_wp_id
    context.wp_file = str(wp.path)
    context.lane = lane
    context.dependencies = dependencies
    context.workspace_path = str(workspace_path)

    if action == "implement":
        try:
            resolved_base, auto_merge = validate_and_resolve_base(
                wp_id=normalized_wp_id,
                wp_file=wp.path,
                base=base,
                feature_slug=feature_slug,
                repo_root=repo_root,
                auto_detect_single_dependency=True,
                quiet=True,
                raise_on_error=True,
            )
        except BaseResolutionError as exc:
            raise ActionContextError(
                "WORK_PACKAGE_BASE_UNRESOLVED",
                str(exc),
            ) from exc

        context.resolved_base = resolved_base
        context.auto_merge = auto_merge

        command = f"spec-kitty agent workflow implement {normalized_wp_id}"
        if resolved_base:
            command += f" --base {resolved_base}"
        if agent:
            command += f" --agent {agent}"
        context.commands["workflow"] = command
        return context

    command = f"spec-kitty agent workflow review {normalized_wp_id}"
    if agent:
        command += f" --agent {agent}"
    context.commands["workflow"] = command
    context.commands["approve"] = (
        f"spec-kitty agent tasks move-task {normalized_wp_id} --to approved "
        '--note "Review passed: <summary>"'
    )
    context.commands["reject"] = (
        f"spec-kitty agent tasks move-task {normalized_wp_id} "
        "--to planned --review-feedback-file <feedback-file>"
    )
    return context
