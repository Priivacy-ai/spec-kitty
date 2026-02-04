#!/usr/bin/env python3
"""Shared task helper module for Spec Kitty task operations.

This module is the single source of truth for task helper logic used by both:
- ``specify_cli.tasks_support`` (installed package entrypoint)
- ``specify_cli.scripts.tasks.task_helpers`` (standalone script entrypoint)

All shared functions live here. Both consumers import and re-export from this
module so that callers do not need to change their import paths.

Functions are dependency-light (stdlib only) and fully typed.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LANES: Tuple[str, ...] = ("planned", "doing", "for_review", "done")
"""Valid work-package lane names."""

TIMESTAMP_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"
"""ISO-8601 timestamp format used in activity logs."""

LEGACY_LANE_DIRS: List[str] = ["planned", "doing", "for_review", "done"]
"""Lane directories that indicate legacy format when they contain .md files."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TaskCliError(RuntimeError):
    """Raised when task operations cannot be completed safely."""


# ---------------------------------------------------------------------------
# Repository root detection (worktree-aware)
# ---------------------------------------------------------------------------


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Find the MAIN repository root, even when inside a worktree.

    This function correctly handles git worktrees by detecting when ``.git`` is
    a file (worktree pointer) vs a directory (main repo), and following the
    pointer back to the main repository.

    Args:
        start: Starting directory for search (defaults to cwd)

    Returns:
        Path to the main repository root

    Raises:
        TaskCliError: If repository root cannot be found
    """
    current = (start or Path.cwd()).resolve()

    for candidate in [current, *current.parents]:
        git_path = candidate / ".git"

        if git_path.is_file():
            # This is a worktree! The .git file contains a pointer to the main
            # repo.  Format: "gitdir: /path/to/main/.git/worktrees/name"
            try:
                content = git_path.read_text().strip()
                if content.startswith("gitdir:"):
                    gitdir = Path(content.split(":", 1)[1].strip())
                    # Navigate: .git/worktrees/name -> .git -> main repo root
                    main_git_dir = gitdir.parent.parent
                    main_repo = main_git_dir.parent
                    if main_repo.exists():
                        return main_repo
            except (OSError, ValueError):
                pass

        elif git_path.is_dir():
            return candidate

        # Also check for .kittify marker (fallback for non-git scenarios)
        if (candidate / ".kittify").exists():
            return candidate

    raise TaskCliError("Unable to locate repository root (missing .git or .kittify).")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def run_git(
    args: List[str], cwd: Path, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a git command inside the repository.

    Args:
        args: Arguments to pass to ``git``.
        cwd: Working directory for the git command.
        check: If True, raise ``TaskCliError`` on non-zero exit.

    Returns:
        Completed process result.

    Raises:
        TaskCliError: If git is not on PATH or if the command fails with
            *check=True*.
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=check,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise TaskCliError("git is not available on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        if check:
            message = exc.stderr.strip() or exc.stdout.strip() or "Unknown git error"
            raise TaskCliError(message)
        return exc  # type: ignore[return-value]


def git_status_lines(repo_root: Path) -> List[str]:
    """Return non-empty porcelain status lines for *repo_root*.

    Args:
        repo_root: Path to the repository root.

    Returns:
        List of non-empty ``git status --porcelain`` output lines.
    """
    result = run_git(["status", "--porcelain"], cwd=repo_root, check=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _normalize_status_path(raw: str) -> str:
    """Normalize a path from ``git status`` output for comparison."""
    candidate = raw.split(" -> ", 1)[0].strip()
    candidate = candidate.lstrip("./")
    return candidate.replace("\\", "/")


def path_has_changes(status_lines: List[str], path: Path) -> bool:
    """Return True if git status indicates modifications for *path*.

    Args:
        status_lines: Output of :func:`git_status_lines`.
        path: Path to check.

    Returns:
        True if the path appears in the status lines.
    """
    normalized = _normalize_status_path(str(path))
    for line in status_lines:
        if len(line) < 4:
            continue
        candidate = _normalize_status_path(line[3:])
        if candidate == normalized:
            return True
    return False


# ---------------------------------------------------------------------------
# Lane helpers
# ---------------------------------------------------------------------------


def ensure_lane(value: str) -> str:
    """Validate and normalize a lane name.

    Args:
        value: Raw lane string.

    Returns:
        Normalized, lowercase lane name.

    Raises:
        TaskCliError: If the lane is invalid.
    """
    lane = value.strip().lower()
    if lane not in LANES:
        raise TaskCliError(
            f"Invalid lane '{value}'. Expected one of {', '.join(LANES)}."
        )
    return lane


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


def now_utc() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


# ---------------------------------------------------------------------------
# Note helpers
# ---------------------------------------------------------------------------


def normalize_note(note: Optional[str], target_lane: str) -> str:
    """Return a cleaned note string, falling back to a default message.

    Args:
        note: Raw user-supplied note (may be None or empty).
        target_lane: Lane name used for the default message.

    Returns:
        Cleaned note string.
    """
    default = f"Moved to {target_lane}"
    cleaned = (note or default).strip()
    return cleaned or default


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


def detect_conflicting_wp_status(
    status_lines: List[str],
    feature: str,
    old_path: Path,
    new_path: Path,
) -> List[str]:
    """Return staged work-package entries unrelated to the requested move.

    Handles the delete suffix case: if a status line marks a path as deleted
    (``D``) and that path ends with one of the allowed suffixes, it is *not*
    treated as a conflict.

    Args:
        status_lines: Output of :func:`git_status_lines`.
        feature: Feature slug.
        old_path: Original work-package path.
        new_path: Destination work-package path.

    Returns:
        List of status lines that represent conflicting changes.
    """
    base_path = Path("kitty-specs") / feature / "tasks"
    prefix = f"{base_path.as_posix()}/"
    allowed = {
        str(old_path).lstrip("./"),
        str(new_path).lstrip("./"),
    }

    def _wp_suffix(path: Path) -> Optional[str]:
        try:
            relative = path.relative_to(base_path)
        except ValueError:
            return None
        parts = relative.parts
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        return Path(*parts[1:]).as_posix()

    suffixes = {
        suffix for suffix in (_wp_suffix(old_path), _wp_suffix(new_path)) if suffix
    }
    conflicts: List[str] = []
    for line in status_lines:
        path_str = line[3:] if len(line) > 3 else ""
        if not path_str.startswith(prefix):
            continue
        clean = path_str.strip()
        if clean not in allowed:
            if suffixes and line and line[0] == "D":
                for suffix in suffixes:
                    if clean.endswith(suffix):
                        break
                else:
                    conflicts.append(line)
                    continue
                continue
            conflicts.append(line)
    return conflicts


# ---------------------------------------------------------------------------
# Legacy format detection
# ---------------------------------------------------------------------------


def is_legacy_format(feature_path: Path) -> bool:
    """Check if feature uses legacy directory-based lanes.

    A feature is considered to use legacy format if:
    - It has a ``tasks/`` subdirectory
    - Any of the lane subdirectories (``planned/``, ``doing/``, etc.) exist
      AND contain at least one ``.md`` file

    Args:
        feature_path: Path to the feature directory
            (e.g. ``kitty-specs/007-feature/``).

    Returns:
        True if legacy directory-based lanes detected, False otherwise.

    Note:
        Empty lane directories (containing only ``.gitkeep``) are NOT
        considered legacy format.
    """
    tasks_dir = feature_path / "tasks"
    if not tasks_dir.exists():
        return False

    for lane in LEGACY_LANE_DIRS:
        lane_path = tasks_dir / lane
        if lane_path.is_dir():
            md_files = list(lane_path.glob("*.md"))
            if md_files:
                return True

    return False


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------


def match_frontmatter_line(frontmatter: str, key: str) -> Optional[re.Match]:
    """Match a YAML scalar line in raw frontmatter text.

    Args:
        frontmatter: Raw frontmatter string (without ``---`` delimiters).
        key: YAML key to match.

    Returns:
        Regex match object or None.
    """
    pattern = re.compile(
        rf"^({re.escape(key)}:\s*)(\".*?\"|'.*?'|[^#\n]*)(.*)$",
        flags=re.MULTILINE,
    )
    return pattern.search(frontmatter)


def extract_scalar(frontmatter: str, key: str) -> Optional[str]:
    """Extract a scalar value from raw frontmatter text.

    Args:
        frontmatter: Raw frontmatter string (without ``---`` delimiters).
        key: YAML key to extract.

    Returns:
        Unquoted scalar value, or None if the key is not found.
    """
    match = match_frontmatter_line(frontmatter, key)
    if not match:
        return None
    raw_value = match.group(2).strip()
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return raw_value[1:-1]
    if raw_value.startswith("'") and raw_value.endswith("'"):
        return raw_value[1:-1]
    return raw_value.strip() or None


def set_scalar(frontmatter: str, key: str, value: str) -> str:
    """Replace or insert a scalar value while preserving trailing comments.

    Args:
        frontmatter: Raw frontmatter string.
        key: YAML key to set.
        value: New value (will be double-quoted).

    Returns:
        Updated frontmatter string.
    """
    match = match_frontmatter_line(frontmatter, key)
    replacement_line = f'{key}: "{value}"'
    if match:
        prefix = match.group(1)
        comment = match.group(3)
        comment_suffix = f"{comment}" if comment else ""
        return (
            frontmatter[: match.start()]
            + f'{prefix}"{value}"{comment_suffix}'
            + frontmatter[match.end() :]
        )

    insertion = f"{replacement_line}\n"
    history_match = re.compile(r"^\s*history:\s*$", flags=re.MULTILINE).search(
        frontmatter
    )
    if history_match:
        idx = history_match.start()
        return frontmatter[:idx] + insertion + frontmatter[idx:]

    if frontmatter and not frontmatter.endswith("\n"):
        frontmatter += "\n"
    return frontmatter + insertion


def split_frontmatter(text: str) -> Tuple[str, str, str]:
    """Split a markdown document into frontmatter, body, and padding.

    Args:
        text: Full document text.

    Returns:
        Tuple of ``(frontmatter, body, padding)`` where *padding* is the
        whitespace between the closing ``---`` and the body.
    """
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return "", normalized, ""

    closing_idx = normalized.find("\n---", 4)
    if closing_idx == -1:
        return "", normalized, ""

    front = normalized[4:closing_idx]
    tail = normalized[closing_idx + 4 :]
    padding = ""
    while tail.startswith("\n"):
        padding += "\n"
        tail = tail[1:]
    return front, tail, padding


def build_document(frontmatter: str, body: str, padding: str) -> str:
    """Reassemble a markdown document from its parts.

    Args:
        frontmatter: Raw frontmatter (without ``---`` delimiters).
        body: Document body.
        padding: Whitespace between frontmatter closing and body.

    Returns:
        Complete document string.
    """
    frontmatter = frontmatter.rstrip("\n")
    doc = f"---\n{frontmatter}\n---"
    if padding or body:
        doc += padding or "\n"
    doc += body
    if not doc.endswith("\n"):
        doc += "\n"
    return doc


# ---------------------------------------------------------------------------
# Activity log helpers
# ---------------------------------------------------------------------------


def append_activity_log(body: str, entry: str) -> str:
    """Append an entry to the ``## Activity Log`` section of a document body.

    If the section does not exist it is created at the end of the body.

    Args:
        body: Document body text.
        entry: Activity log line to append (should start with ``- ``).

    Returns:
        Updated body text.
    """
    header = "## Activity Log"
    if header not in body:
        block = f"{header}\n\n{entry}\n"
        if body and not body.endswith("\n\n"):
            return body.rstrip() + "\n\n" + block
        return body + "\n" + block if body else block

    pattern = re.compile(r"(## Activity Log.*?)(?=\n## |\Z)", flags=re.DOTALL)
    match = pattern.search(body)
    if not match:
        return body + ("\n" if not body.endswith("\n") else "") + entry + "\n"

    section = match.group(1).rstrip()
    if not section.endswith("\n"):
        section += "\n"
    section += f"{entry}\n"
    return body[: match.start(1)] + section + body[match.end(1) :]


def activity_entries(body: str) -> List[Dict[str, str]]:
    """Parse activity log entries from a document body.

    Supports both en-dash and hyphen separators and agent names containing
    hyphens (e.g. ``cursor-agent``, ``claude-reviewer``).

    Args:
        body: Document body text.

    Returns:
        List of dicts with keys ``timestamp``, ``agent``, ``lane``, ``note``,
        and ``shell_pid``.
    """
    pattern = re.compile(
        r"^\s*-\s*"
        r"(?P<timestamp>[0-9T:-]+Z)\s+[–-]\s+"
        r"(?P<agent>\S+(?:\s+\S+)*?)\s+[–-]\s+"
        r"(?:shell_pid=(?P<shell>\S*)\s+[–-]\s+)?"
        r"lane=(?P<lane>[a-z_]+)\s+[–-]\s+"
        r"(?P<note>.*)$",
        flags=re.MULTILINE,
    )
    entries: List[Dict[str, str]] = []
    for match in pattern.finditer(body):
        entries.append(
            {
                "timestamp": match.group("timestamp").strip(),
                "agent": match.group("agent").strip(),
                "lane": match.group("lane").strip(),
                "note": match.group("note").strip(),
                "shell_pid": (match.group("shell") or "").strip(),
            }
        )
    return entries


# ---------------------------------------------------------------------------
# WorkPackage data class
# ---------------------------------------------------------------------------


@dataclass
class WorkPackage:
    """In-memory representation of a work-package prompt file."""

    feature: str
    path: Path
    current_lane: str
    relative_subpath: Path
    frontmatter: str
    body: str
    padding: str

    @property
    def work_package_id(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "work_package_id")

    @property
    def title(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "title")

    @property
    def assignee(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "assignee")

    @property
    def agent(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "agent")

    @property
    def shell_pid(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "shell_pid")

    @property
    def lane(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "lane")


# ---------------------------------------------------------------------------
# Work-package location and loading
# ---------------------------------------------------------------------------


def locate_work_package(
    repo_root: Path, feature: str, wp_id: str
) -> WorkPackage:
    """Locate a work package by ID, supporting both legacy and new formats.

    Legacy format: WP files in ``tasks/{lane}/`` subdirectories.
    New format: WP files in flat ``tasks/`` directory with lane in frontmatter.

    Args:
        repo_root: Path to repository root.
        feature: Feature slug.
        wp_id: Work-package identifier (e.g. ``"WP01"``).

    Returns:
        Populated :class:`WorkPackage` instance.

    Raises:
        TaskCliError: If the WP cannot be found or multiple matches exist.
    """
    feature_path = repo_root / "kitty-specs" / feature
    tasks_root = feature_path / "tasks"
    if not tasks_root.exists():
        raise TaskCliError(
            f"Feature '{feature}' has no tasks directory at {tasks_root}."
        )

    # Use exact WP ID matching with word boundary to avoid WP04 matching WP04b
    wp_pattern = re.compile(rf"^{re.escape(wp_id)}(?:[-_.]|\.md$)")

    use_legacy = is_legacy_format(feature_path)
    candidates: List[Tuple[str, Path, Path]] = []

    if use_legacy:
        for lane_dir in tasks_root.iterdir():
            if not lane_dir.is_dir():
                continue
            lane = lane_dir.name
            for path in lane_dir.rglob("*.md"):
                if wp_pattern.match(path.name):
                    candidates.append((lane, path, lane_dir))
    else:
        for path in tasks_root.glob("*.md"):
            if path.name.lower() == "readme.md":
                continue
            if wp_pattern.match(path.name):
                lane = get_lane_from_frontmatter(path, warn_on_missing=False)
                candidates.append((lane, path, tasks_root))

    if not candidates:
        raise TaskCliError(
            f"Work package '{wp_id}' not found under kitty-specs/{feature}/tasks."
        )
    if len(candidates) > 1:
        joined = "\n".join(
            str(item[1].relative_to(repo_root)) for item in candidates
        )
        raise TaskCliError(
            f"Multiple files matched '{wp_id}'. Refine the ID or clean "
            f"duplicates:\n{joined}"
        )

    lane, path, base_dir = candidates[0]
    text = path.read_text(encoding="utf-8-sig")
    front, body, padding = split_frontmatter(text)
    relative = path.relative_to(base_dir)
    return WorkPackage(
        feature=feature,
        path=path,
        current_lane=lane,
        relative_subpath=relative,
        frontmatter=front,
        body=body,
        padding=padding,
    )


def load_meta(meta_path: Path) -> Dict:
    """Load and return parsed JSON from a ``meta.json`` file.

    Args:
        meta_path: Path to the meta JSON file.

    Returns:
        Parsed dictionary.

    Raises:
        TaskCliError: If the file does not exist.
    """
    if not meta_path.exists():
        raise TaskCliError(f"Meta file not found at {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8-sig"))


def get_lane_from_frontmatter(
    wp_path: Path, warn_on_missing: bool = True
) -> str:
    """Extract lane from WP file frontmatter.

    This is the authoritative way to determine a work package's lane in the
    frontmatter-only lane system.

    Args:
        wp_path: Path to the work package markdown file.
        warn_on_missing: If True, print warning when lane field is missing.

    Returns:
        Lane value (``planned``, ``doing``, ``for_review``, ``done``).

    Raises:
        ValueError: If lane value is not in :data:`LANES`.
    """
    content = wp_path.read_text(encoding="utf-8-sig")
    frontmatter, _, _ = split_frontmatter(content)

    lane = extract_scalar(frontmatter, "lane")

    if lane is None:
        if warn_on_missing:
            try:
                from rich.console import Console

                console = Console(stderr=True)
                console.print(
                    f"[yellow]Warning: {wp_path.name} missing lane field, "
                    f"defaulting to 'planned'[/yellow]"
                )
            except ImportError:
                import sys

                print(
                    f"Warning: {wp_path.name} missing lane field, "
                    f"defaulting to 'planned'",
                    file=sys.stderr,
                )
        return "planned"

    if lane not in LANES:
        raise ValueError(
            f"Invalid lane '{lane}' in {wp_path.name}. "
            f"Valid lanes: {', '.join(LANES)}"
        )

    return lane


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "LANES",
    "LEGACY_LANE_DIRS",
    "TIMESTAMP_FORMAT",
    "TaskCliError",
    "WorkPackage",
    "append_activity_log",
    "activity_entries",
    "build_document",
    "detect_conflicting_wp_status",
    "ensure_lane",
    "extract_scalar",
    "find_repo_root",
    "get_lane_from_frontmatter",
    "git_status_lines",
    "is_legacy_format",
    "load_meta",
    "locate_work_package",
    "match_frontmatter_line",
    "normalize_note",
    "now_utc",
    "path_has_changes",
    "run_git",
    "set_scalar",
    "split_frontmatter",
]
