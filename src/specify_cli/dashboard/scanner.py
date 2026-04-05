"""Feature scanning helpers for the Spec Kitty dashboard."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from specify_cli.dashboard.charter_path import resolve_project_charter_path
from specify_cli.legacy_detector import is_legacy_format
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
    "resolve_active_feature",
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
        content = file_path.read_text(encoding="utf-8-sig")
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


def format_feature_display_name(feature_id: str, friendly_name: str) -> str:
    """Return a dashboard label that preserves the numeric feature prefix."""
    label = friendly_name.strip() or feature_id
    number_match = re.match(r"^(\d+)", feature_id)
    if not number_match:
        return label

    feature_number = number_match.group(1)
    if re.match(rf"^{re.escape(feature_number)}(?:\b|[-:_\s])", label):
        return label

    return f"{feature_number} - {label}"


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


def get_feature_artifacts(
    feature_dir: Path,
    project_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, any]]:
    """Return which artifacts exist for a feature with modification info.

    Charter status is project-level. If project_dir is omitted, we fall back
    to feature_dir.parent.parent for compatibility with older call sites.
    """
    project_root = project_dir if project_dir is not None else feature_dir.parent.parent
    charter_path = resolve_project_charter_path(project_root)

    charter_info = (
        _get_artifact_info(charter_path)
        if charter_path is not None
        else {"exists": False, "mtime": None, "size": None}
    )

    return {
        "charter": charter_info,
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
    """Collect candidate feature directories from root and worktrees.

    Main repo (kitty-specs/) paths take priority over worktree copies.
    Worktrees may have stale data from when they were created, so the
    main repo should be the source of truth for feature status.
    """
    feature_paths: Dict[str, Path] = {}

    # First scan worktrees (lower priority - may have stale data)
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

    # Then scan main repo (higher priority - source of truth)
    # This will overwrite any worktree paths with the same feature name
    root_specs = project_dir / "kitty-specs"
    if root_specs.exists():
        for feature_dir in root_specs.iterdir():
            if feature_dir.is_dir():
                feature_paths[feature_dir.name] = feature_dir

    return feature_paths


def resolve_feature_dir(project_dir: Path, feature_id: str) -> Optional[Path]:
    """Resolve the on-disk directory for the requested feature."""
    feature_paths = gather_feature_paths(project_dir)
    return feature_paths.get(feature_id)


def resolve_active_feature(
    project_dir: Path,
) -> Optional[Dict[str, Any]]:
    """Return None — active feature cannot be auto-detected; requires explicit --feature.

    This function is retained for backward-compatible call sites. Without
    auto-detection, we cannot determine the active feature without an explicit
    feature slug from the caller.
    """
    return None


def _count_wps_by_lane(tasks_dir: Path) -> Dict[str, int]:
    """Count work packages by lane from the canonical event log.

    Raises ``CanonicalStatusNotFoundError`` when the event log is absent.
    WPs not present in the event log are counted as ``"planned"``
    (mapped from ``"uninitialized"``).
    """
    counts = {"planned": 0, "doing": 0, "for_review": 0, "approved": 0, "done": 0}

    if not tasks_dir.exists():
        return counts

    # feature_dir is the parent of tasks/
    feature_dir = tasks_dir.parent

    from specify_cli.status.lane_reader import get_all_wp_lanes
    event_lanes = get_all_wp_lanes(feature_dir)

    for wp_file in tasks_dir.glob("WP*.md"):
        stem = wp_file.stem
        wp_id_match = re.match(r"^(WP\d+)", stem, re.IGNORECASE)
        wp_id = wp_id_match.group(1).upper() if wp_id_match else stem

        lane = event_lanes.get(wp_id, "uninitialized")

        # Map display aliases
        if lane in ("claimed", "uninitialized"):
            lane = "planned"
        elif lane == "in_progress":
            lane = "doing"
        if lane in counts:
            counts[lane] += 1

    return counts


def scan_all_features(project_dir: Path) -> List[Dict[str, Any]]:
    """Scan all features and return metadata."""
    from specify_cli.status.store import StoreError

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
                meta_data = json.loads(meta_path.read_text(encoding="utf-8-sig"))
                potential_name = meta_data.get("friendly_name")
                if isinstance(potential_name, str) and potential_name.strip():
                    friendly_name = potential_name.strip()
            except json.JSONDecodeError:
                meta_data = None

        artifacts = get_feature_artifacts(feature_dir, project_dir)
        workflow = get_workflow_status(artifacts)

        kanban_stats = {"total": 0, "planned": 0, "doing": 0, "for_review": 0, "approved": 0, "done": 0}
        if artifacts["kanban"]:
            tasks_dir = feature_dir / "tasks"
            use_legacy = is_legacy_format(feature_dir)

            if use_legacy:
                # Legacy format: count WPs in lane subdirectories
                for lane in ["planned", "doing", "for_review", "done"]:
                    lane_dir = tasks_dir / lane
                    if lane_dir.exists():
                        count = len(list(lane_dir.rglob("WP*.md")))
                        kanban_stats[lane] = count
                        kanban_stats["total"] += count
            else:
                # New format: count WPs by canonical event log lane
                from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
                try:
                    lane_counts = _count_wps_by_lane(tasks_dir)
                    for lane, count in lane_counts.items():
                        kanban_stats[lane] = count
                        kanban_stats["total"] += count
                except CanonicalStatusNotFoundError:
                    logger.warning(
                        "No event log for feature '%s' — skipping kanban counts",
                        feature_dir.name,
                    )
                    kanban_stats["error"] = (
                        f"Event log not found. Run: spec-kitty agent mission "
                        f"finalize-tasks --feature {feature_dir.name}"
                    )
                except StoreError as exc:
                    logger.warning(
                        "Unreadable event log for feature '%s' — dashboard counts unavailable: %s",
                        feature_dir.name,
                        exc,
                    )
                    kanban_stats["error"] = (
                        "Event log unreadable. Run: spec-kitty upgrade "
                        f"(feature {feature_dir.name})"
                    )

        worktree_root = project_dir / ".worktrees"
        worktree_path = worktree_root / feature_dir.name
        worktree_exists = worktree_path.exists()
        display_name = format_feature_display_name(feature_id, friendly_name)

        features.append(
            {
                "id": feature_id,
                "name": friendly_name,
                "display_name": display_name,
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


def _process_wp_file(
    prompt_file: Path,
    project_dir: Path,
    default_lane: str,
) -> Optional[Dict[str, Any]]:
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
            "model": "",
            "assignee": "",
            "phase": "",
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

    wp_id = frontmatter.get("work_package_id", prompt_file.stem)
    # Derive feature_dir: for flat tasks/ it's parent.parent;
    # for legacy tasks/<lane>/ it's parent.parent.parent.
    # Use has_event_log to find the right level, else fall back to default_lane.
    from specify_cli.status.lane_reader import has_event_log, get_wp_lane

    stem = prompt_file.stem
    wp_id_match = re.match(r"^(WP\d+)", stem, re.IGNORECASE)
    canonical_wp_id = wp_id_match.group(1).upper() if wp_id_match else stem

    # Try flat layout first (tasks/WP01.md → feature_dir is parent.parent)
    candidate = prompt_file.parent.parent
    if has_event_log(candidate):
        lane = get_wp_lane(candidate, canonical_wp_id)
    elif has_event_log(candidate.parent):
        # Legacy layout (tasks/planned/WP01.md → feature_dir is parent.parent.parent)
        lane = get_wp_lane(candidate.parent, canonical_wp_id)
    else:
        # No event log at either level — use default_lane only for legacy
        # features (where the directory structure IS the lane). For flat-task
        # features the event log is mandatory; let the caller handle it.
        feature_candidate = (
            candidate if candidate.name != "tasks" else candidate.parent
        )
        if is_legacy_format(feature_candidate):
            lane = default_lane
        else:
            from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
            raise CanonicalStatusNotFoundError(
                f"Canonical status not found for feature "
                f"'{feature_candidate.name}'. Run 'spec-kitty agent mission "
                f"finalize-tasks --feature {feature_candidate.name}' to "
                f"bootstrap the event log."
            )

    agent_raw = frontmatter.get("agent", "")
    # Normalize structured agent mapping (e.g. {tool: claude, model: opus, ...}) to tool string
    if isinstance(agent_raw, dict):
        agent_str = agent_raw.get("tool", "")
        model_str = agent_raw.get("model", "")
    else:
        agent_str = str(agent_raw) if agent_raw else ""
        model_str = ""

    # Also check top-level frontmatter 'model' key as fallback
    if not model_str:
        model_str = str(frontmatter.get("model", "")) if frontmatter.get("model") else ""
    return {
        "id": wp_id,
        "title": title,
        "lane": lane,
        "subtasks": frontmatter.get("subtasks", []),
        "agent": agent_str,
        "model": model_str,
        "agent_profile": frontmatter.get("agent_profile", ""),
        "role": frontmatter.get("role", ""),
        "assignee": frontmatter.get("assignee", ""),
        "phase": frontmatter.get("phase", ""),
        "prompt_markdown": prompt_body.strip(),
        "prompt_path": str(prompt_file.relative_to(project_dir))
        if prompt_file.is_relative_to(project_dir)
        else str(prompt_file),
    }


def scan_feature_kanban(project_dir: Path, feature_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Scan kanban board for a specific feature.

    Supports both legacy (directory-based) and new (event-log-based) lane formats.
    """
    feature_dir = resolve_feature_dir(project_dir, feature_id)
    lanes: Dict[str, List[Dict[str, Any]]] = {
        "planned": [],
        "doing": [],
        "for_review": [],
        "approved": [],
        "done": [],
    }

    if feature_dir is None or not feature_dir.exists():
        return lanes

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return lanes

    use_legacy = is_legacy_format(feature_dir)

    if use_legacy:
        # Legacy format: scan lane subdirectories
        for lane in lanes.keys():
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
        # New format: scan flat tasks/ directory, lane from event log
        from specify_cli.status.lane_reader import CanonicalStatusNotFoundError
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
            except CanonicalStatusNotFoundError:
                logger.warning(
                    "No event log for feature '%s' — cannot render kanban",
                    feature_dir.name,
                )
                return lanes  # Return empty kanban — feature not finalized
            except Exception as exc:
                logger.error(f"Unexpected error processing {prompt_file.name}: {exc}")
                continue

        # Sort all lanes
        for lane in lanes.keys():
            lanes[lane].sort(key=work_package_sort_key)

    return lanes
