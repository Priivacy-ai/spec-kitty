"""Feature scanning helpers for the Spec Kitty dashboard."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from specify_cli.template import parse_frontmatter
from specify_cli.text_sanitization import sanitize_file

logger = logging.getLogger(__name__)

__all__ = [
    "format_path_for_display",
    "gather_feature_paths",
    "get_feature_artifacts",
    "get_workflow_status",
    "read_file_resilient",
    "resolve_feature_dir",
    "scan_all_features",
    "scan_feature_kanban",
]


def read_file_resilient(
    file_path: Path, *, auto_fix: bool = True
) -> tuple[Optional[str], Optional[str]]:
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
        content = file_path.read_text(encoding="utf-8")
        return content, None
    except UnicodeDecodeError as exc:
        # Log the encoding error
        logger.warning(
            f"UTF-8 decoding failed for {file_path.name} at byte {exc.start}: {exc.reason}"
        )

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
                content = file_path.read_text(encoding="utf-8")
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


def format_path_for_display(path_str: Optional[str]) -> Optional[str]:
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


def work_package_sort_key(task: Dict[str, Any]) -> tuple:
    """Provide a natural sort key for work package identifiers."""
    work_id = str(task.get("id", "")).strip()
    if not work_id:
        return ((), "")

    number_parts = [int(part.lstrip("0") or "0") for part in re.findall(r"\d+", work_id)]
    return (tuple(number_parts), work_id.lower())


def _get_artifact_info(path: Path) -> Dict[str, any]:
    """Get artifact information including existence, mtime, and size."""
    if not path.exists():
        return {"exists": False, "mtime": None, "size": None}

    stat = path.stat()
    return {
        "exists": True,
        "mtime": stat.st_mtime,
        "size": stat.st_size if path.is_file() else None,
    }


def get_feature_artifacts(feature_dir: Path) -> Dict[str, Dict[str, any]]:
    """Return which artifacts exist for a feature with modification info."""
    return {
        "constitution": _get_artifact_info(feature_dir / "constitution.md"),
        "spec": _get_artifact_info(feature_dir / "spec.md"),
        "plan": _get_artifact_info(feature_dir / "plan.md"),
        "tasks": _get_artifact_info(feature_dir / "tasks.md"),
        "research": _get_artifact_info(feature_dir / "research.md"),
        "quickstart": _get_artifact_info(feature_dir / "quickstart.md"),
        "data_model": _get_artifact_info(feature_dir / "data-model.md"),
        "contracts": _get_artifact_info(feature_dir / "contracts"),
        "checklists": _get_artifact_info(feature_dir / "checklists"),
        "kanban": _get_artifact_info(feature_dir / "tasks"),
    }


def get_workflow_status(artifacts: Dict[str, Dict[str, any]]) -> Dict[str, str]:
    """Determine workflow progression status."""
    has_spec = artifacts.get("spec", {}).get("exists", False)
    has_plan = artifacts.get("plan", {}).get("exists", False)
    has_tasks = artifacts.get("tasks", {}).get("exists", False)
    has_kanban = artifacts.get("kanban", {}).get("exists", False)

    workflow: Dict[str, str] = {}

    if not has_spec:
        workflow.update(
            {"specify": "pending", "plan": "pending", "tasks": "pending", "implement": "pending"}
        )
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


def gather_feature_paths(project_dir: Path) -> Dict[str, Path]:
    """Collect candidate feature directories from root and worktrees."""
    feature_paths: Dict[str, Path] = {}

    root_specs = project_dir / "kitty-specs"
    if root_specs.exists():
        for feature_dir in root_specs.iterdir():
            if feature_dir.is_dir():
                feature_paths[feature_dir.name] = feature_dir

    worktrees_root = project_dir / ".worktrees"
    if worktrees_root.exists():
        for worktree_dir in worktrees_root.iterdir():
            if not worktree_dir.is_dir():
                continue
            wt_specs = worktree_dir / "kitty-specs"
            if not wt_specs.exists():
                continue
            for feature_dir in wt_specs.iterdir():
                if feature_dir.is_dir():
                    feature_paths[feature_dir.name] = feature_dir

    return feature_paths


def resolve_feature_dir(project_dir: Path, feature_id: str) -> Optional[Path]:
    """Resolve the on-disk directory for the requested feature."""
    feature_paths = gather_feature_paths(project_dir)
    return feature_paths.get(feature_id)


def scan_all_features(project_dir: Path) -> List[Dict[str, Any]]:
    """Scan all features and return metadata."""
    features: List[Dict[str, Any]] = []
    feature_paths = gather_feature_paths(project_dir)

    for feature_id, feature_dir in feature_paths.items():
        if not (re.match(r"^\d+", feature_dir.name) or (feature_dir / "tasks").exists()):
            continue

        friendly_name = feature_dir.name
        meta_data: Dict[str, Any] | None = None
        meta_path = feature_dir / "meta.json"
        if meta_path.exists():
            try:
                meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
                potential_name = meta_data.get("friendly_name")
                if isinstance(potential_name, str) and potential_name.strip():
                    friendly_name = potential_name.strip()
            except json.JSONDecodeError:
                meta_data = None

        artifacts = get_feature_artifacts(feature_dir)
        workflow = get_workflow_status(artifacts)

        kanban_stats = {"total": 0, "planned": 0, "doing": 0, "for_review": 0, "done": 0}
        if artifacts["kanban"]:
            tasks_dir = feature_dir / "tasks"
            for lane in ["planned", "doing", "for_review", "done"]:
                lane_dir = tasks_dir / lane
                if lane_dir.exists():
                    count = len(list(lane_dir.rglob("WP*.md")))
                    kanban_stats[lane] = count
                    kanban_stats["total"] += count

        worktree_root = project_dir / ".worktrees"
        worktree_path = worktree_root / feature_dir.name
        worktree_exists = worktree_path.exists()

        features.append(
            {
                "id": feature_id,
                "name": friendly_name,
                "path": str(feature_dir.relative_to(project_dir)),
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

    features.sort(key=lambda f: f["id"], reverse=True)
    return features


def scan_feature_kanban(project_dir: Path, feature_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Scan kanban board for a specific feature."""
    feature_dir = resolve_feature_dir(project_dir, feature_id)
    lanes: Dict[str, List[Dict[str, Any]]] = {
        "planned": [],
        "doing": [],
        "for_review": [],
        "done": [],
    }

    if feature_dir is None or not feature_dir.exists():
        return lanes

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return lanes

    for lane in lanes.keys():
        lane_dir = tasks_dir / lane
        if not lane_dir.exists():
            continue

        for prompt_file in lane_dir.rglob("WP*.md"):
            try:
                # Use resilient reader with auto-fix
                content, error = read_file_resilient(prompt_file, auto_fix=True)

                if content is None:
                    # Log the error and create an error task card
                    logger.error(f"Failed to read {prompt_file.name}: {error}")
                    lanes[lane].append(
                        {
                            "id": prompt_file.stem,
                            "title": f"⚠️ Encoding Error: {prompt_file.name}",
                            "lane": lane,
                            "subtasks": [],
                            "agent": "",
                            "assignee": "",
                            "phase": "",
                            "prompt_markdown": f"**Encoding Error**\n\n{error}",
                            "prompt_path": str(prompt_file.relative_to(project_dir))
                            if prompt_file.is_relative_to(project_dir)
                            else str(prompt_file),
                            "encoding_error": True,
                        }
                    )
                    continue

                frontmatter, prompt_body, _ = parse_frontmatter(content)

                if "work_package_id" not in frontmatter:
                    continue

                title_match = re.search(r"^#\s+Work Package Prompt:\s+(.+)$", content, re.MULTILINE)
                title = title_match.group(1) if title_match else prompt_file.stem

                task_data = {
                    "id": frontmatter.get("work_package_id", prompt_file.stem),
                    "title": title,
                    "lane": frontmatter.get("lane", lane),
                    "subtasks": frontmatter.get("subtasks", []),
                    "agent": frontmatter.get("agent", ""),
                    "assignee": frontmatter.get("assignee", ""),
                    "phase": frontmatter.get("phase", ""),
                    "prompt_markdown": prompt_body.strip(),
                    "prompt_path": str(prompt_file.relative_to(project_dir))
                    if prompt_file.is_relative_to(project_dir)
                    else str(prompt_file),
                }

                lanes[lane].append(task_data)
            except Exception as exc:
                logger.error(f"Unexpected error processing {prompt_file.name}: {exc}")
                continue

        lanes[lane].sort(key=work_package_sort_key)

    return lanes
