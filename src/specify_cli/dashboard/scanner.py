"""Mission scanning helpers for the Spec Kitty dashboard."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from specify_cli.dashboard.constitution_path import resolve_project_constitution_path
from specify_cli.core.mission_detection import detect_mission
from specify_cli.legacy_detector import is_legacy_format
from specify_cli.template import parse_frontmatter
from specify_cli.text_sanitization import sanitize_file

logger = logging.getLogger(__name__)

__all__ = [
    "format_path_for_display",
    "gather_mission_paths",
    "get_mission_artifacts",
    "get_workflow_status",
    "read_file_resilient",
    "resolve_mission_dir",
    "resolve_active_mission",
    "scan_all_missions",
    "scan_mission_kanban",
]


def read_file_resilient(file_path: Path, *, auto_fix: bool = True) -> tuple[str | None, str | None]:
    """Read a file with resilience to encoding errors.

    This function attempts to read a file as UTF-8, and if that fails:
    1. Tries alternative encodings (cp1252, latin-1)
    2. Optionally auto-fixes the file by sanitizing and re-saving as UTF-8
    3. Returns clear error messages for the dashboard to display

    Args:
        file_path: Path to the file to read
        auto_fix: If True, automatically sanitize and fix encoding errors

    Returns:
        Tuple of (content, error_message)
        - content: File content if successful, None if failed
        - error_message: None if successful, error description if failed

    Examples:
        >>> from pathlib import Path
        >>> content, error = read_file_resilient(Path("good-file.md"))
        >>> content is not None
        True
        >>> error is None
        True
    """
    if not file_path.exists():
        return None, f"File not found: {file_path.name}"

    try:
        # Try strict UTF-8 first
        content = file_path.read_text(encoding="utf-8-sig")
        return content, None
    except UnicodeDecodeError as exc:
        # Log the encoding error
        logger.warning(f"UTF-8 decoding failed for {file_path.name} at byte {exc.start}: {exc.reason}")

        if not auto_fix:
            return None, (
                f"Encoding error in {file_path.name} at byte {exc.start}. "
                f"File contains non-UTF-8 characters (possibly Windows-1252 smart quotes). "
                f"Run 'spec-kitty validate-encoding --fix' to repair."
            )

        # Attempt auto-fix
        try:
            logger.info(f"Attempting to auto-fix encoding for {file_path.name}")
            was_modified, error = sanitize_file(file_path, backup=True, dry_run=False)

            if error:
                return None, error

            if was_modified:
                # Read the fixed file
                content = file_path.read_text(encoding="utf-8-sig")
                logger.info(f"Successfully fixed encoding for {file_path.name}")
                return content, None
            else:
                # Shouldn't happen, but handle it
                return None, f"Auto-fix failed for {file_path.name}: no changes made"

        except Exception as fix_exc:
            logger.error(f"Auto-fix failed for {file_path.name}: {fix_exc}")
            return None, (
                f"Encoding error in {file_path.name} and auto-fix failed: {fix_exc}. "
                f"Manually repair the file or run 'spec-kitty validate-encoding --fix'."
            )
    except Exception as exc:
        logger.error(f"Unexpected error reading {file_path.name}: {exc}")
        return None, f"Error reading {file_path.name}: {exc}"


def format_path_for_display(path_str: str | None) -> str | None:
    """Return a human-readable path that shortens the user's home directory."""
    if not path_str:
        return path_str

    try:
        path = Path(path_str).expanduser()
    except (TypeError, ValueError):
        return path_str

    try:
        resolved = path.resolve()
    except Exception:
        resolved = path

    try:
        home = Path.home().resolve()
    except Exception:
        home = Path.home()

    try:
        relative = resolved.relative_to(home)
    except ValueError:
        return str(resolved)

    relative_str = str(relative)
    if relative_str in {"", "."}:
        return "~"
    return f"~{os.sep}{relative_str}"


def format_mission_display_name(mission_id: str, friendly_name: str) -> str:
    """Return a dashboard label that preserves the numeric mission prefix."""
    label = friendly_name.strip() or mission_id
    number_match = re.match(r"^(\d+)", mission_id)
    if not number_match:
        return label

    mission_number = number_match.group(1)
    if re.match(rf"^{re.escape(mission_number)}(?:\b|[-:_\s])", label):
        return label

    return f"{mission_number} - {label}"


def work_package_sort_key(task: dict[str, Any]) -> tuple:
    """Provide a natural sort key for work package identifiers."""
    work_id = str(task.get("id", "")).strip()
    if not work_id:
        return ((), "")

    number_parts = [int(part.lstrip("0") or "0") for part in re.findall(r"\d+", work_id)]
    return (tuple(number_parts), work_id.lower())


def _get_artifact_info(path: Path) -> dict[str, any]:
    """Get artifact information including existence, mtime, and size."""
    if not path.exists():
        return {"exists": False, "mtime": None, "size": None}

    stat = path.stat()
    return {
        "exists": True,
        "mtime": stat.st_mtime,
        "size": stat.st_size if path.is_file() else None,
    }


def get_mission_artifacts(
    mission_dir: Path,
    project_dir: Path | None = None,
) -> dict[str, dict[str, any]]:
    """Return which artifacts exist for a mission with modification info.

    Constitution status is project-level. If project_dir is omitted, we fall back
    to mission_dir.parent.parent for compatibility with older call sites.
    """
    project_root = project_dir if project_dir is not None else mission_dir.parent.parent
    constitution_path = resolve_project_constitution_path(project_root)

    constitution_info = (
        _get_artifact_info(constitution_path)
        if constitution_path is not None
        else {"exists": False, "mtime": None, "size": None}
    )

    return {
        "constitution": constitution_info,
        "spec": _get_artifact_info(mission_dir / "spec.md"),
        "plan": _get_artifact_info(mission_dir / "plan.md"),
        "tasks": _get_artifact_info(mission_dir / "tasks.md"),
        "research": _get_artifact_info(mission_dir / "research.md"),
        "quickstart": _get_artifact_info(mission_dir / "quickstart.md"),
        "data_model": _get_artifact_info(mission_dir / "data-model.md"),
        "contracts": _get_artifact_info(mission_dir / "contracts"),
        "checklists": _get_artifact_info(mission_dir / "checklists"),
        "kanban": _get_artifact_info(mission_dir / "tasks"),
    }


def get_workflow_status(artifacts: dict[str, dict[str, any]]) -> dict[str, str]:
    """Determine workflow progression status."""
    has_spec = artifacts.get("spec", {}).get("exists", False)
    has_plan = artifacts.get("plan", {}).get("exists", False)
    has_tasks = artifacts.get("tasks", {}).get("exists", False)
    has_kanban = artifacts.get("kanban", {}).get("exists", False)

    workflow: dict[str, str] = {}

    if not has_spec:
        workflow.update({"specify": "pending", "plan": "pending", "tasks": "pending", "implement": "pending"})
        return workflow
    workflow["specify"] = "complete"

    if not has_plan:
        workflow.update({"plan": "pending", "tasks": "pending", "implement": "pending"})
        return workflow
    workflow["plan"] = "complete"

    if not has_tasks:
        workflow.update({"tasks": "pending", "implement": "pending"})
        return workflow
    workflow["tasks"] = "complete"

    workflow["implement"] = "in_progress" if has_kanban else "pending"
    return workflow


def gather_mission_paths(project_dir: Path) -> dict[str, Path]:
    """Collect candidate mission directories from root and worktrees.

    Main repo (kitty-specs/) paths take priority over worktree copies.
    Worktrees may have stale data from when they were created, so the
    main repo should be the source of truth for mission status.
    """
    mission_paths: dict[str, Path] = {}

    # First scan worktrees (lower priority - may have stale data)
    worktrees_root = project_dir / ".worktrees"
    if worktrees_root.exists():
        for worktree_dir in worktrees_root.iterdir():
            if not worktree_dir.is_dir():
                continue
            wt_specs = worktree_dir / "kitty-specs"
            if not wt_specs.exists():
                continue
            for mission_dir in wt_specs.iterdir():
                if mission_dir.is_dir():
                    mission_paths[mission_dir.name] = mission_dir

    # Then scan main repo (higher priority - source of truth)
    # This will overwrite any worktree paths with the same mission name
    root_specs = project_dir / "kitty-specs"
    if root_specs.exists():
        for mission_dir in root_specs.iterdir():
            if mission_dir.is_dir():
                mission_paths[mission_dir.name] = mission_dir

    return mission_paths


def resolve_mission_dir(project_dir: Path, mission_id: str) -> Path | None:
    """Resolve the on-disk directory for the requested mission."""
    mission_paths = gather_mission_paths(project_dir)
    return mission_paths.get(mission_id)


def resolve_active_mission(
    project_dir: Path,
    missions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Resolve active mission using the same detector as CLI status commands."""
    if not missions:
        return None

    context = detect_mission(
        project_dir,
        cwd=project_dir,
        mode="lenient",
    )
    if context:
        for mission in missions:
            if mission.get("id") == context.slug:
                return mission

    # Keep previous deterministic fallback for edge cases.
    return missions[0]


def _count_wps_by_lane_frontmatter(tasks_dir: Path) -> dict[str, int]:
    """Count work packages by lane from frontmatter (new format)."""
    counts = {"planned": 0, "doing": 0, "for_review": 0, "in_review": 0, "approved": 0, "done": 0}

    if not tasks_dir.exists():
        return counts

    for wp_file in tasks_dir.glob("WP*.md"):
        content, error = read_file_resilient(wp_file, auto_fix=True)
        if content is None:
            continue

        frontmatter, _, _ = parse_frontmatter(content)
        lane = frontmatter.get("lane", "planned") if isinstance(frontmatter, dict) else "planned"
        if lane == "claimed":
            lane = "planned"
        elif lane == "in_progress":
            lane = "doing"
        if lane in counts:
            counts[lane] += 1

    return counts


def scan_all_missions(project_dir: Path) -> list[dict[str, Any]]:
    """Scan all missions and return metadata."""
    missions: list[dict[str, Any]] = []
    mission_paths = gather_mission_paths(project_dir)

    for mission_id, mission_dir in mission_paths.items():
        if not (re.match(r"^\d+", mission_dir.name) or (mission_dir / "tasks").exists()):
            continue

        friendly_name = mission_dir.name
        meta_data: dict[str, Any] | None = None
        meta_path = mission_dir / "meta.json"
        if meta_path.exists():
            try:
                meta_data = json.loads(meta_path.read_text(encoding="utf-8-sig"))
                potential_name = meta_data.get("friendly_name")
                if isinstance(potential_name, str) and potential_name.strip():
                    friendly_name = potential_name.strip()
            except json.JSONDecodeError:
                meta_data = None

        artifacts = get_mission_artifacts(mission_dir, project_dir)
        workflow = get_workflow_status(artifacts)

        kanban_stats = {"total": 0, "planned": 0, "doing": 0, "for_review": 0, "in_review": 0, "approved": 0, "done": 0}
        if artifacts["kanban"]:
            tasks_dir = mission_dir / "tasks"
            use_legacy = is_legacy_format(mission_dir)

            if use_legacy:
                # Legacy format: count WPs in lane subdirectories
                for lane in ["planned", "doing", "for_review", "done"]:
                    lane_dir = tasks_dir / lane
                    if lane_dir.exists():
                        count = len(list(lane_dir.rglob("WP*.md")))
                        kanban_stats[lane] = count
                        kanban_stats["total"] += count
            else:
                # New format: count WPs by frontmatter lane
                lane_counts = _count_wps_by_lane_frontmatter(tasks_dir)
                for lane, count in lane_counts.items():
                    kanban_stats[lane] = count
                    kanban_stats["total"] += count

        worktree_root = project_dir / ".worktrees"
        worktree_path = worktree_root / mission_dir.name
        worktree_exists = worktree_path.exists()
        display_name = format_mission_display_name(mission_id, friendly_name)

        missions.append(
            {
                "id": mission_id,
                "name": friendly_name,
                "display_name": display_name,
                "path": str(mission_dir.relative_to(project_dir)),
                "artifacts": artifacts,
                "workflow": workflow,
                "kanban_stats": kanban_stats,
                "meta": meta_data or {},
                "worktree": {
                    "path": format_path_for_display(str(worktree_path)),
                    "exists": worktree_exists,
                },
            }
        )

    missions.sort(key=lambda f: f["id"], reverse=True)
    return missions


def _process_wp_file(
    prompt_file: Path,
    project_dir: Path,
    default_lane: str,
) -> dict[str, Any] | None:
    """Process a single WP file and return task data or None on error."""
    content, error = read_file_resilient(prompt_file, auto_fix=True)

    if content is None:
        logger.error(f"Failed to read {prompt_file.name}: {error}")
        return {
            "id": prompt_file.stem,
            "title": f"⚠️ Encoding Error: {prompt_file.name}",
            "lane": default_lane,
            "subtasks": [],
            "agent": "",
            "assignee": "",
            "phase": "",
            "agent_profile": "",
            "role": "",
            "approved_by": "",
            "task_type": "",
            "prompt_markdown": f"**Encoding Error**\n\n{error}",
            "prompt_path": str(prompt_file.relative_to(project_dir))
            if prompt_file.is_relative_to(project_dir)
            else str(prompt_file),
            "encoding_error": True,
        }

    frontmatter, prompt_body, _ = parse_frontmatter(content)

    if not isinstance(frontmatter, dict) or "work_package_id" not in frontmatter:
        return None

    title_match = re.search(r"^#\s+Work Package Prompt:\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else prompt_file.stem

    agent_raw = frontmatter.get("agent", "")
    # Normalize structured agent mapping (e.g. {tool: claude, model: opus, ...}) to tool string
    agent_str = agent_raw.get("tool", "") if isinstance(agent_raw, dict) else str(agent_raw) if agent_raw else ""

    return {
        "id": frontmatter.get("work_package_id", prompt_file.stem),
        "title": title,
        "lane": frontmatter.get("lane", default_lane),
        "subtasks": frontmatter.get("subtasks", []),
        "agent": agent_str,
        "assignee": frontmatter.get("assignee", ""),
        "phase": frontmatter.get("phase", ""),
        "agent_profile": frontmatter.get("agent_profile", ""),
        "role": frontmatter.get("role", ""),
        "approved_by": frontmatter.get("approved_by", ""),
        "task_type": frontmatter.get("task_type", ""),
        "prompt_markdown": prompt_body.strip(),
        "prompt_path": str(prompt_file.relative_to(project_dir))
        if prompt_file.is_relative_to(project_dir)
        else str(prompt_file),
    }


def scan_mission_kanban(project_dir: Path, mission_id: str) -> dict[str, list[dict[str, Any]]]:  # noqa: C901
    """Scan kanban board for a specific mission.

    Supports both legacy (directory-based) and new (frontmatter-based) lane formats.
    """
    mission_dir = resolve_mission_dir(project_dir, mission_id)
    lanes: dict[str, list[dict[str, Any]]] = {
        "planned": [],
        "doing": [],
        "for_review": [],
        "in_review": [],
        "approved": [],
        "done": [],
    }

    if mission_dir is None or not mission_dir.exists():
        return lanes

    tasks_dir = mission_dir / "tasks"
    if not tasks_dir.exists():
        return lanes

    use_legacy = is_legacy_format(mission_dir)

    if use_legacy:
        # Legacy format: scan lane subdirectories
        for lane in lanes:
            lane_dir = tasks_dir / lane
            if not lane_dir.exists():
                continue

            for prompt_file in lane_dir.rglob("WP*.md"):
                try:
                    task_data = _process_wp_file(prompt_file, project_dir, lane)
                    if task_data is not None:
                        lanes[lane].append(task_data)
                except Exception as exc:
                    logger.error(f"Unexpected error processing {prompt_file.name}: {exc}")
                    continue

            lanes[lane].sort(key=work_package_sort_key)
    else:
        # New format: scan flat tasks/ directory, lane from frontmatter
        for prompt_file in tasks_dir.glob("WP*.md"):
            try:
                task_data = _process_wp_file(prompt_file, project_dir, "planned")
                if task_data is not None:
                    lane = task_data.get("lane", "planned")
                    if lane == "claimed":
                        lane = "planned"
                    elif lane == "in_progress":
                        lane = "doing"
                    if lane not in lanes:
                        lane = "planned"
                    lanes[lane].append(task_data)
            except Exception as exc:
                logger.error(f"Unexpected error processing {prompt_file.name}: {exc}")
                continue

        # Sort all lanes
        for lane in lanes:
            lanes[lane].sort(key=work_package_sort_key)

    return lanes
