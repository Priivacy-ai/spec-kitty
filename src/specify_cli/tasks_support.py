#!/usr/bin/env python3
"""Shared utilities for manipulating Spec Kitty task prompts."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LANES: Tuple[str, ...] = ("planned", "doing", "for_review", "done")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TaskCliError(RuntimeError):
    """Raised when task operations cannot be completed safely."""


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk upward until a Git or .kittify root is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / ".kittify").exists():
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


def normalize_note(note: Optional[str], target_lane: str) -> str:
    default = f"Moved to {target_lane}"
    cleaned = (note or default).strip()
    return cleaned or default


def detect_conflicting_wp_status(
    status_lines: List[str], feature: str, old_path: Path, new_path: Path
) -> List[str]:
    """Return staged work-package entries unrelated to the requested move."""
    prefix = f"kitty-specs/{feature}/tasks/"
    allowed = {
        str(old_path).lstrip("./"),
        str(new_path).lstrip("./"),
    }
    conflicts = []
    for line in status_lines:
        path = line[3:] if len(line) > 3 else ""
        if not path.startswith(prefix):
            continue
        clean = path.strip()
        if clean not in allowed:
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
    history_match = re.search(r"^\s*history:\s*$", frontmatter, flags=re.MULTILINE)
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
    pattern = re.compile(
        r"^\s*-\s*"
        r"(?P<timestamp>[0-9T:-]+Z)\s*[–-]\s*"
        r"(?P<agent>[^–-]+?)\s*[–-]\s*"
        r"(?:shell_pid=(?P<shell>[^–-]*?)\s*[–-]\s*)?"
        r"lane=(?P<lane>[a-z_]+)\s*[–-]\s*"
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
    tasks_root = repo_root / "kitty-specs" / feature / "tasks"
    if not tasks_root.exists():
        raise TaskCliError(f"Feature '{feature}' has no tasks directory at {tasks_root}.")

    candidates = []
    for lane_dir in tasks_root.iterdir():
        if not lane_dir.is_dir():
            continue
        lane = lane_dir.name
        lane_path = tasks_root / lane
        for path in lane_path.rglob("*.md"):
            if path.name.startswith(wp_id):
                candidates.append((lane, path, lane_path))

    if not candidates:
        raise TaskCliError(f"Work package '{wp_id}' not found under kitty-specs/{feature}/tasks.")
    if len(candidates) > 1:
        joined = "\n".join(str(item[1].relative_to(repo_root)) for item in candidates)
        raise TaskCliError(
            f"Multiple files matched '{wp_id}'. Refine the ID or clean duplicates:\n{joined}"
        )

    lane, path, lane_path = candidates[0]
    text = path.read_text(encoding="utf-8")
    front, body, padding = split_frontmatter(text)
    relative = path.relative_to(lane_path)
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
    return json.loads(meta_path.read_text(encoding="utf-8"))


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
    "git_status_lines",
    "load_meta",
    "locate_work_package",
    "match_frontmatter_line",
    "normalize_note",
    "now_utc",
    "run_git",
    "set_scalar",
    "split_frontmatter",
]
