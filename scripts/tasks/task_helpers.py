#!/usr/bin/env python3
"""Standalone helpers for Spec Kitty task prompt management."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# IMPORTANT: Keep in sync with src/specify_cli/tasks_support.py
LANES: Tuple[str, ...] = ("planned", "doing", "for_review", "done")

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Lane directories that indicate legacy format when they contain .md files
LEGACY_LANE_DIRS: List[str] = ["planned", "doing", "for_review", "done"]


def is_legacy_format(feature_path: Path) -> bool:
    """Check if feature uses legacy directory-based lanes.

    A feature is considered to use legacy format if:
    - It has a tasks/ subdirectory
    - Any of the lane subdirectories (planned/, doing/, for_review/, done/)
      exist AND contain at least one .md file

    Args:
        feature_path: Path to the feature directory (e.g., kitty-specs/007-feature/)

    Returns:
        True if legacy directory-based lanes detected, False otherwise.

    Note:
        Empty lane directories (containing only .gitkeep) are NOT considered
        legacy format - only directories with actual .md work package files.
    """
    tasks_dir = feature_path / "tasks"
    if not tasks_dir.exists():
        return False

    for lane in LEGACY_LANE_DIRS:
        lane_path = tasks_dir / lane
        if lane_path.is_dir():
            # Check if there are any .md files (not just .gitkeep)
            md_files = list(lane_path.glob("*.md"))
            if md_files:
                return True

    return False


class TaskCliError(RuntimeError):
    """Raised when task operations cannot be completed safely."""


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Find the MAIN repository root, even when inside a worktree.

    This function correctly handles git worktrees by detecting when .git is a
    file (worktree pointer) vs a directory (main repo), and following the
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
            # This is a worktree! The .git file contains a pointer to the main repo.
            # Format: "gitdir: /path/to/main/.git/worktrees/worktree-name"
            try:
                content = git_path.read_text().strip()
                if content.startswith("gitdir:"):
                    gitdir = Path(content.split(":", 1)[1].strip())
                    # Navigate: .git/worktrees/name -> .git -> main repo root
                    # gitdir points to .git/worktrees/xxx, so .parent.parent is .git
                    main_git_dir = gitdir.parent.parent
                    main_repo = main_git_dir.parent
                    if main_repo.exists():
                        return main_repo
            except (OSError, ValueError):
                # If we can't read or parse the .git file, continue searching
                pass

        elif git_path.is_dir():
            # This is the main repo (or a regular git repo)
            return candidate

        # Also check for .kittify marker (fallback for non-git scenarios)
        if (candidate / ".kittify").exists():
            return candidate

    raise TaskCliError("Unable to locate repository root (missing .git or .kittify).")


def run_git(args: List[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command inside the repository."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=check,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise TaskCliError("git is not available on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        if check:
            message = exc.stderr.strip() or exc.stdout.strip() or "Unknown git error"
            raise TaskCliError(message)
        return exc


def ensure_lane(value: str) -> str:
    lane = value.strip().lower()
    if lane not in LANES:
        raise TaskCliError(f"Invalid lane '{value}'. Expected one of {', '.join(LANES)}.")
    return lane


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def git_status_lines(repo_root: Path) -> List[str]:
    result = run_git(["status", "--porcelain"], cwd=repo_root, check=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _normalize_status_path(raw: str) -> str:
    candidate = raw.split(" -> ", 1)[0].strip()
    candidate = candidate.lstrip("./")
    return candidate.replace("\\", "/")


def path_has_changes(status_lines: List[str], path: Path) -> bool:
    """Return True if git status indicates modifications for the given path."""
    normalized = _normalize_status_path(str(path))
    for line in status_lines:
        if len(line) < 4:
            continue
        candidate = _normalize_status_path(line[3:])
        if candidate == normalized:
            return True
    return False


def normalize_note(note: Optional[str], target_lane: str) -> str:
    default = f"Moved to {target_lane}"
    cleaned = (note or default).strip()
    return cleaned or default


def detect_conflicting_wp_status(
    status_lines: List[str], feature: str, old_path: Path, new_path: Path
) -> List[str]:
    """Return staged work-package entries unrelated to the requested move."""
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

    suffixes = {suffix for suffix in (_wp_suffix(old_path), _wp_suffix(new_path)) if suffix}
    conflicts = []
    for line in status_lines:
        path = line[3:] if len(line) > 3 else ""
        if not path.startswith(prefix):
            continue
        clean = path.strip()
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


def match_frontmatter_line(frontmatter: str, key: str) -> Optional[re.Match]:
    pattern = re.compile(
        rf"^({re.escape(key)}:\s*)(\".*?\"|'.*?'|[^#\n]*)(.*)$",
        flags=re.MULTILINE,
    )
    return pattern.search(frontmatter)


def extract_scalar(frontmatter: str, key: str) -> Optional[str]:
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
    """Replace or insert a scalar value while preserving trailing comments."""
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
    history_match = re.compile(r"^\s*history:\s*$", flags=re.MULTILINE).search(frontmatter)
    if history_match:
        idx = history_match.start()
        return frontmatter[:idx] + insertion + frontmatter[idx:]

    if frontmatter and not frontmatter.endswith("\n"):
        frontmatter += "\n"
    return frontmatter + insertion


def split_frontmatter(text: str) -> Tuple[str, str, str]:
    """Return (frontmatter, body, padding) while preserving spacing after frontmatter."""
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
    frontmatter = frontmatter.rstrip("\n")
    doc = f"---\n{frontmatter}\n---"
    if padding or body:
        doc += padding or "\n"
    doc += body
    if not doc.endswith("\n"):
        doc += "\n"
    return doc


def append_activity_log(body: str, entry: str) -> str:
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
    # Match both en-dash (–) and hyphen (-) as separators
    # The separator is always surrounded by whitespace, so we match non-whitespace for fields
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


@dataclass
class WorkPackage:
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


def locate_work_package(repo_root: Path, feature: str, wp_id: str) -> WorkPackage:
    """Locate a work package by ID, supporting both legacy and new formats.

    Legacy format: WP files in tasks/{lane}/ subdirectories
    New format: WP files in flat tasks/ directory with lane in frontmatter
    """
    feature_path = repo_root / "kitty-specs" / feature
    tasks_root = feature_path / "tasks"
    if not tasks_root.exists():
        raise TaskCliError(f"Feature '{feature}' has no tasks directory at {tasks_root}.")

    # Use exact WP ID matching with word boundary to avoid WP04 matching WP04b
    # Matches: WP04.md, WP04-something.md, WP04_something.md
    # Does NOT match: WP04b.md, WP04b-something.md
    wp_pattern = re.compile(rf"^{re.escape(wp_id)}(?:[-_.]|\.md$)")

    use_legacy = is_legacy_format(feature_path)
    candidates = []

    if use_legacy:
        # Legacy format: search lane subdirectories
        for lane_dir in tasks_root.iterdir():
            if not lane_dir.is_dir():
                continue
            lane = lane_dir.name
            for path in lane_dir.rglob("*.md"):
                if wp_pattern.match(path.name):
                    candidates.append((lane, path, lane_dir))
    else:
        # New format: search flat tasks/ directory
        for path in tasks_root.glob("*.md"):
            if path.name.lower() == "readme.md":
                continue
            if wp_pattern.match(path.name):
                # Get lane from frontmatter
                lane = get_lane_from_frontmatter(path, warn_on_missing=False)
                candidates.append((lane, path, tasks_root))

    if not candidates:
        raise TaskCliError(f"Work package '{wp_id}' not found under kitty-specs/{feature}/tasks.")
    if len(candidates) > 1:
        joined = "\n".join(str(item[1].relative_to(repo_root)) for item in candidates)
        raise TaskCliError(
            f"Multiple files matched '{wp_id}'. Refine the ID or clean duplicates:\n{joined}"
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
    if not meta_path.exists():
        raise TaskCliError(f"Meta file not found at {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8-sig"))


def get_lane_from_frontmatter(wp_path: Path, warn_on_missing: bool = True) -> str:
    """Extract lane from WP file frontmatter.

    This is the authoritative way to determine a work package's lane
    in the frontmatter-only lane system.

    Args:
        wp_path: Path to the work package markdown file
        warn_on_missing: If True, print warning when lane field is missing

    Returns:
        Lane value (planned, doing, for_review, done)

    Raises:
        ValueError: If lane value is not in LANES
    """
    content = wp_path.read_text(encoding="utf-8-sig")
    frontmatter, _, _ = split_frontmatter(content)

    lane = extract_scalar(frontmatter, "lane")

    if lane is None:
        if warn_on_missing:
            # Import here to avoid circular dependency issues
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
                    f"Warning: {wp_path.name} missing lane field, defaulting to 'planned'",
                    file=sys.stderr
                )
        return "planned"

    if lane not in LANES:
        raise ValueError(
            f"Invalid lane '{lane}' in {wp_path.name}. "
            f"Valid lanes: {', '.join(LANES)}"
        )

    return lane


__all__ = [
    "LANES",
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
    "normalize_note",
    "now_utc",
    "path_has_changes",
    "run_git",
    "set_scalar",
    "split_frontmatter",
]
