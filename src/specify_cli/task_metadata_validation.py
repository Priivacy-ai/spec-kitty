"""Task metadata validation and repair for Spec Kitty.

Detects and fixes inconsistencies between work package file locations
and their frontmatter metadata.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from specify_cli.template import parse_frontmatter
from specify_cli.tasks_support import build_document

__all__ = [
    "TaskMetadataError",
    "detect_lane_mismatch",
    "repair_lane_mismatch",
    "validate_task_metadata",
    "scan_all_tasks_for_mismatches",
]


class TaskMetadataError(Exception):
    """Raised when task metadata is inconsistent."""

    pass


def detect_lane_mismatch(task_file: Path) -> tuple[bool, Optional[str], Optional[str]]:
    """Detect if task file's lane metadata doesn't match its directory.

    Args:
        task_file: Path to the work package prompt file

    Returns:
        Tuple of (has_mismatch, expected_lane, actual_lane)
        - has_mismatch: True if lane doesn't match directory
        - expected_lane: Lane based on file location (e.g., "for_review")
        - actual_lane: Lane from frontmatter metadata

    Examples:
        >>> task_file = Path("tasks/for_review/WP01.md")
        >>> has_mismatch, expected, actual = detect_lane_mismatch(task_file)
        >>> if has_mismatch:
        ...     print(f"File in {expected} but metadata says {actual}")
    """
    if not task_file.exists():
        return False, None, None

    # Determine expected lane from file path
    expected_lane = None
    for lane in ["planned", "doing", "for_review", "done"]:
        if f"/tasks/{lane}/" in str(task_file) or f"\\tasks\\{lane}\\" in str(task_file):
            expected_lane = lane
            break

    if not expected_lane:
        # File not in a recognized lane directory
        return False, None, None

    # Read frontmatter
    try:
        content = task_file.read_text(encoding="utf-8")
        frontmatter, _, _ = parse_frontmatter(content)
    except Exception:
        return False, expected_lane, None

    actual_lane = frontmatter.get("lane", "").strip()

    has_mismatch = actual_lane != expected_lane
    return has_mismatch, expected_lane, actual_lane


def repair_lane_mismatch(
    task_file: Path,
    *,
    agent: str = "system",
    shell_pid: str = "",
    add_history: bool = True,
    dry_run: bool = False,
) -> tuple[bool, Optional[str]]:
    """Repair lane mismatch by updating frontmatter to match directory.

    Args:
        task_file: Path to the work package prompt file
        agent: Agent name for activity log
        shell_pid: Shell PID for activity log
        add_history: If True, append activity log entry
        dry_run: If True, don't modify file

    Returns:
        Tuple of (was_repaired, error_message)
        - was_repaired: True if repair was needed and applied
        - error_message: None if successful, error description if failed

    Examples:
        >>> was_repaired, error = repair_lane_mismatch(
        ...     Path("tasks/for_review/WP01.md"),
        ...     agent="codex",
        ...     shell_pid="12345"
        ... )
        >>> if was_repaired:
        ...     print("Fixed lane metadata")
    """
    has_mismatch, expected_lane, actual_lane = detect_lane_mismatch(task_file)

    if not has_mismatch:
        return False, None  # No repair needed

    if expected_lane is None:
        return False, f"Could not determine expected lane for {task_file.name}"

    try:
        content = task_file.read_text(encoding="utf-8")
        frontmatter, body, padding = parse_frontmatter(content)
    except Exception as exc:
        return False, f"Failed to parse frontmatter: {exc}"

    # Update lane in frontmatter
    frontmatter["lane"] = expected_lane

    # Add activity log entry if requested
    if add_history:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        history_entry = (
            f"  - timestamp: \"{timestamp}\"\n"
            f"    lane: \"{expected_lane}\"\n"
            f"    agent: \"{agent}\"\n"
            f"    shell_pid: \"{shell_pid}\"\n"
            f"    action: \"Auto-repaired lane metadata (was: {actual_lane})\"\n"
        )

        # Find activity_log in frontmatter
        if "activity_log" in frontmatter:
            # Append to existing activity log
            existing_log = frontmatter.get("activity_log", "")
            if isinstance(existing_log, list):
                # Already parsed as list - append dict
                frontmatter["activity_log"].append({
                    "timestamp": timestamp,
                    "lane": expected_lane,
                    "agent": agent,
                    "shell_pid": shell_pid,
                    "action": f"Auto-repaired lane metadata (was: {actual_lane})"
                })
            elif isinstance(existing_log, str):
                # Raw YAML string - append entry
                frontmatter["activity_log"] = existing_log.rstrip() + "\n" + history_entry
        else:
            # Create new activity log
            frontmatter["activity_log"] = history_entry

    if dry_run:
        return True, None  # Would repair but dry run

    # Rebuild file content
    try:
        # Convert frontmatter dict back to YAML string
        frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
        new_content = build_document(frontmatter_yaml, body, padding)
        task_file.write_text(new_content, encoding="utf-8")
        return True, None
    except Exception as exc:
        return False, f"Failed to write file: {exc}"


def validate_task_metadata(task_file: Path) -> list[str]:
    """Validate task metadata and return list of issues.

    Args:
        task_file: Path to the work package prompt file

    Returns:
        List of validation issues (empty if valid)

    Issues checked:
    - Lane mismatch between directory and frontmatter
    - Missing required frontmatter fields
    - Invalid lane values
    - Malformed activity log

    Examples:
        >>> issues = validate_task_metadata(Path("tasks/doing/WP01.md"))
        >>> if issues:
        ...     for issue in issues:
        ...         print(f"⚠️ {issue}")
    """
    issues = []

    if not task_file.exists():
        issues.append(f"File not found: {task_file}")
        return issues

    # Check lane mismatch
    has_mismatch, expected_lane, actual_lane = detect_lane_mismatch(task_file)
    if has_mismatch:
        issues.append(
            f"Lane mismatch: file in '{expected_lane}/' but metadata says '{actual_lane}'"
        )

    # Parse frontmatter
    try:
        content = task_file.read_text(encoding="utf-8")
        frontmatter, _, _ = parse_frontmatter(content)
    except Exception as exc:
        issues.append(f"Failed to parse frontmatter: {exc}")
        return issues

    # Check required fields
    required_fields = ["work_package_id", "lane"]
    for field in required_fields:
        if field not in frontmatter or not frontmatter[field]:
            issues.append(f"Missing required field: {field}")

    # Validate lane value
    lane = frontmatter.get("lane", "")
    valid_lanes = ["planned", "doing", "for_review", "done"]
    if lane and lane not in valid_lanes:
        issues.append(f"Invalid lane value: '{lane}' (must be one of {valid_lanes})")

    # Check work_package_id format
    wp_id = frontmatter.get("work_package_id", "")
    if wp_id and not re.match(r"^WP\d+$", wp_id):
        issues.append(f"Invalid work_package_id format: '{wp_id}' (should be WP##)")

    return issues


def scan_all_tasks_for_mismatches(
    feature_dir: Path,
) -> dict[str, tuple[bool, Optional[str], Optional[str]]]:
    """Scan all task files in a feature for lane mismatches.

    Args:
        feature_dir: Path to feature directory (e.g., kitty-specs/001-feature)

    Returns:
        Dictionary mapping file paths to (has_mismatch, expected_lane, actual_lane)
        Only includes files with mismatches.

    Examples:
        >>> feature_dir = Path("kitty-specs/001-my-feature")
        >>> mismatches = scan_all_tasks_for_mismatches(feature_dir)
        >>> for file_path, (_, expected, actual) in mismatches.items():
        ...     print(f"{file_path}: {actual} → {expected}")
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return {}

    mismatches = {}

    # Scan all lanes
    for lane in ["planned", "doing", "for_review", "done"]:
        lane_dir = tasks_dir / lane
        if not lane_dir.exists():
            continue

        for task_file in lane_dir.rglob("WP*.md"):
            has_mismatch, expected, actual = detect_lane_mismatch(task_file)
            if has_mismatch:
                # Store relative path for readability
                try:
                    rel_path = task_file.relative_to(feature_dir)
                except ValueError:
                    rel_path = task_file
                mismatches[str(rel_path)] = (has_mismatch, expected, actual)

    return mismatches
