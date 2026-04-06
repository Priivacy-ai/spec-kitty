"""Context resolution: raw arguments to persisted MissionContext.

The resolver reads identity from project metadata and WP frontmatter.
It does NOT use branch names, environment variables, or directory walking.
Both ``wp_code`` and ``mission_slug`` are REQUIRED -- there is no scanning,
no heuristic fallback, and no single-feature auto-detection.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ruamel.yaml import YAML
from ulid import ULID

from specify_cli.context.errors import (
    FeatureNotFoundError,
    MissingArgumentError,
    MissingIdentityError,
    WorkPackageNotFoundError,
)
from specify_cli.context.models import MissionContext
from specify_cli.context.store import load_context as _load_context
from specify_cli.context.store import save_context
from specify_cli.lanes.branch_naming import lane_branch_name
from specify_cli.lanes.persistence import require_lanes_json


def _generate_token() -> str:
    """Generate an opaque context token: ctx- prefix + ULID."""
    return f"ctx-{ULID()}"


def _read_project_uuid(repo_root: Path) -> str:
    """Read project_uuid from .kittify/config.yaml."""
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        msg = (
            f"Project config not found at {config_path}. "
            "Run `spec-kitty init` to initialize the project."
        )
        raise MissingIdentityError(msg)

    yaml = YAML()
    data = yaml.load(config_path.read_text(encoding="utf-8"))

    project_section = data.get("project", {}) if data else {}
    uuid_val = project_section.get("uuid")
    if not uuid_val:
        msg = (
            "project.uuid not found in .kittify/config.yaml. "
            "Run `spec-kitty init` to assign a project identity."
        )
        raise MissingIdentityError(msg)
    return str(uuid_val)


def _read_meta_json(feature_dir: Path) -> dict[str, str]:
    """Read mission_id and target_branch from meta.json."""
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        msg = f"meta.json not found at {meta_path}."
        raise MissingIdentityError(msg)

    data = json.loads(meta_path.read_text(encoding="utf-8"))

    # mission_id may not exist yet in current metadata;
    # fall back to mission_slug as the identifier during transition
    mission_id = data.get("mission_id", data.get("mission_slug", ""))
    target_branch = data.get("target_branch", "main")

    if not mission_id:
        msg = (
            f"Neither mission_id nor mission_slug found in {meta_path}. "
            "The feature metadata is incomplete."
        )
        raise MissingIdentityError(msg)

    return {"mission_id": mission_id, "target_branch": target_branch}


def _read_wp_frontmatter(feature_dir: Path, wp_code: str) -> dict[str, object]:
    """Read WP frontmatter fields from the task markdown file.

    Scans tasks/ directory for a file matching the wp_code pattern
    (e.g., WP01-*.md or WP01.md).
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        msg = f"tasks/ directory not found at {tasks_dir}."
        raise WorkPackageNotFoundError(msg)

    # Find matching WP file: WP01-*.md or WP01.md
    candidates = list(tasks_dir.glob(f"{wp_code}-*.md")) + list(
        tasks_dir.glob(f"{wp_code}.md")
    )
    if not candidates:
        msg = (
            f"No task file found for '{wp_code}' in {tasks_dir}. "
            f"Expected a file matching {wp_code}-*.md or {wp_code}.md."
        )
        raise WorkPackageNotFoundError(msg)

    wp_path = candidates[0]
    content = wp_path.read_text(encoding="utf-8")

    # Extract YAML frontmatter between --- delimiters
    if not content.startswith("---"):
        msg = f"WP file {wp_path} has no YAML frontmatter."
        raise WorkPackageNotFoundError(msg)

    parts = content.split("---", 2)
    if len(parts) < 3:
        msg = f"WP file {wp_path} has malformed YAML frontmatter."
        raise WorkPackageNotFoundError(msg)

    yaml = YAML()
    fm = yaml.load(parts[1])
    if not isinstance(fm, dict):
        msg = f"WP file {wp_path} frontmatter is not a YAML mapping."
        raise WorkPackageNotFoundError(msg)

    return dict(fm)


def resolve_context(
    wp_code: str,
    mission_slug: str,
    agent: str,
    repo_root: Path,
) -> MissionContext:
    """Resolve a MissionContext from explicit arguments.

    Both ``wp_code`` and ``mission_slug`` are REQUIRED. This function
    does NOT scan, auto-detect, or fall back to heuristics.

    Args:
        wp_code: Work package display alias (e.g., "WP01").
        mission_slug: Feature slug (e.g., "057-canonical-context-architecture-cleanup").
        agent: Name of the agent creating this context.
        repo_root: Absolute path to the repository root.

    Returns:
        A persisted MissionContext.

    Raises:
        MissingArgumentError: If wp_code or mission_slug is empty.
        MissingIdentityError: If project_uuid or mission_id is not assigned.
        FeatureNotFoundError: If the feature slug doesn't match a kitty-specs/ dir.
        WorkPackageNotFoundError: If the wp_code is not found in tasks/.
    """
    if not wp_code:
        msg = (
            "wp_code is required. Provide the work package code "
            "(e.g., --wp WP01). No scanning or auto-detection is performed."
        )
        raise MissingArgumentError(msg)

    if not mission_slug:
        msg = (
            "mission_slug is required. Provide the feature slug "
            "(e.g., --mission 057-canonical-context-architecture-cleanup). "
            "No scanning or auto-detection is performed."
        )
        raise MissingArgumentError(msg)

    # 1. Read project_uuid
    project_uuid = _read_project_uuid(repo_root)

    # 2. Locate feature directory
    feature_dir = repo_root / "kitty-specs" / mission_slug
    if not feature_dir.exists():
        msg = (
            f"Feature directory not found: {feature_dir}. "
            f"Check that '{mission_slug}' is the correct feature slug."
        )
        raise FeatureNotFoundError(msg)

    # 3. Read meta.json
    meta = _read_meta_json(feature_dir)

    # 4. Read WP frontmatter
    fm = _read_wp_frontmatter(feature_dir, wp_code)

    # Extract fields from frontmatter
    work_package_id = str(fm.get("work_package_id", wp_code))
    execution_mode = str(fm.get("execution_mode", "code_change"))
    owned_files_raw = fm.get("owned_files")
    owned_files: tuple[str, ...] = (
        tuple(str(f) for f in owned_files_raw)
        if isinstance(owned_files_raw, list)
        else ()
    )
    dependencies_raw = fm.get("dependencies")
    dependencies: list[object] = (
        list(dependencies_raw) if isinstance(dependencies_raw, list) else []
    )

    # Compute authoritative_ref: lane branch for code_change, None for planning_artifact
    if execution_mode == "planning_artifact":
        authoritative_ref = None
    else:
        lane = require_lanes_json(feature_dir).lane_for_wp(wp_code)
        if lane is None:
            msg = f"{wp_code} is not assigned to any lane in {feature_dir / 'lanes.json'}."
            raise MissingIdentityError(msg)
        authoritative_ref = lane_branch_name(mission_slug, lane.lane_id)

    # Compute dependency_mode
    dependency_mode = "chained" if dependencies else "independent"

    # Generate opaque token
    token = _generate_token()
    now = datetime.now(timezone.utc).isoformat()

    # Build context
    context = MissionContext(
        token=token,
        project_uuid=project_uuid,
        mission_id=meta["mission_id"],
        work_package_id=work_package_id,
        wp_code=wp_code,
        mission_slug=mission_slug,
        target_branch=meta["target_branch"],
        authoritative_repo=str(repo_root),
        authoritative_ref=authoritative_ref,
        owned_files=owned_files,
        execution_mode=execution_mode,
        dependency_mode=dependency_mode,
        created_at=now,
        created_by=agent,
    )

    # Persist
    save_context(context, repo_root)

    return context


def resolve_or_load(
    token: str | None,
    wp_code: str | None,
    mission_slug: str | None,
    agent: str,
    repo_root: Path,
) -> MissionContext:
    """Main entry point: load from token or resolve from arguments.

    - If ``token`` is provided: load the persisted context directly.
    - If ``token`` is None and both ``wp_code`` and ``mission_slug`` are
      provided: resolve a new context.
    - If ``token`` is None and either ``wp_code`` or ``mission_slug`` is
      missing: raise ``MissingArgumentError``.

    This function never scans or guesses.

    Args:
        token: Existing context token, or None.
        wp_code: Work package code (e.g., "WP01"), or None.
        mission_slug: Feature slug, or None.
        agent: Agent name for new context creation.
        repo_root: Repository root path.

    Returns:
        The loaded or newly resolved MissionContext.

    Raises:
        MissingArgumentError: If neither token nor both wp_code/mission_slug
            are provided.
        ContextNotFoundError: If the token file does not exist.
        ContextCorruptedError: If the token file is invalid.
    """
    if token:
        return _load_context(token, repo_root)

    if wp_code and mission_slug:
        return resolve_context(wp_code, mission_slug, agent, repo_root)

    missing: list[str] = []
    if not wp_code:
        missing.append("--wp <WP_CODE>")
    if not mission_slug:
        missing.append("--mission <MISSION_SLUG>")

    msg = (
        f"Missing required argument(s): {', '.join(missing)}. "
        "Either provide a --context <token> or both --wp and --mission. "
        "No scanning or auto-detection is performed."
    )
    raise MissingArgumentError(msg)
