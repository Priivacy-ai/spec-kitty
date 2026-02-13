"""Status file auto-resolution for merge conflicts.

Implements FR-012 through FR-016: automatically resolving conflicts in
status tracking files (lane fields, checkboxes, history arrays).
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "ConflictRegion",
    "ResolutionResult",
    "parse_conflict_markers",
    "resolve_status_conflicts",
    "get_conflicted_files",
    "is_status_file",
]


CONFLICT_PATTERN = re.compile(
    r"^<<<<<<< .*?\n(.*?)^=======\n(.*?)^>>>>>>> .*?\n",
    re.MULTILINE | re.DOTALL,
)
CHECKBOX_PATTERN = re.compile(r"^(\s*-\s*\[)([x ])\](.*)$", re.MULTILINE)
LANE_PATTERN = re.compile(r"^(\s*lane:\s*)([\"']?)(\w+)([\"']?)\s*$", re.MULTILINE)
HISTORY_BLOCK_PATTERN = re.compile(
    r"^(?P<indent>\s*)history:\s*\n(?P<body>(?:^(?P=indent)\s+-.*\n?)+)",
    re.MULTILINE,
)

STATUS_FILE_PATTERNS = [
    "kitty-specs/*/tasks/*.md",
    "kitty-specs/*/tasks.md",
    "kitty-specs/*/*/tasks/*.md",
    "kitty-specs/*/*/tasks.md",
]

LANE_PRIORITY = {
    "done": 4,
    "for_review": 3,
    "doing": 2,
    "planned": 1,
}


@dataclass
class ConflictRegion:
    """A single conflict region in a file."""

    start_line: int
    end_line: int
    ours: str
    theirs: str
    original: str


@dataclass
class ResolutionResult:
    """Result of auto-resolving a status file conflict."""

    file_path: Path
    resolved: bool
    resolution_type: str
    original_conflicts: int
    resolved_conflicts: int


def parse_conflict_markers(content: str) -> list[ConflictRegion]:
    """Parse conflict markers from file content."""
    regions = []
    for match in CONFLICT_PATTERN.finditer(content):
        regions.append(
            ConflictRegion(
                start_line=content[:match.start()].count("\n"),
                end_line=content[:match.end()].count("\n"),
                ours=match.group(1),
                theirs=match.group(2),
                original=match.group(0),
            )
        )
    return regions


def _preserve_trailing_newline(resolved: str, original: str) -> str:
    if original.endswith("\n") and not resolved.endswith("\n"):
        return resolved + "\n"
    return resolved


def is_status_file(file_path: str) -> bool:
    """Check if file matches status file patterns."""
    for pattern in STATUS_FILE_PATTERNS:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def extract_lane_value(content: str) -> str | None:
    """Extract lane value from YAML frontmatter content."""
    match = LANE_PATTERN.search(content)
    return match.group(3) if match else None


def replace_lane_value(content: str, lane_value: str) -> str:
    """Replace lane value in content with the provided value."""
    if not LANE_PATTERN.search(content):
        return content
    return LANE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{lane_value}{match.group(4)}",
        content,
        count=1,
    )


def resolve_lane_conflict(ours: str, theirs: str) -> str | None:
    """Resolve lane conflict by choosing 'more done' value."""
    our_lane = extract_lane_value(ours)
    their_lane = extract_lane_value(theirs)

    if not our_lane or not their_lane:
        return None

    our_priority = LANE_PRIORITY.get(our_lane, 0)
    their_priority = LANE_PRIORITY.get(their_lane, 0)
    chosen = their_lane if their_priority > our_priority else our_lane

    return replace_lane_value(ours, chosen)


def resolve_checkbox_conflict(ours: str, theirs: str) -> str:
    """Resolve checkbox conflict by preferring checked [x]."""
    our_lines = ours.strip().split("\n")
    their_lines = theirs.strip().split("\n")

    result_lines = []
    max_lines = max(len(our_lines), len(their_lines))

    for i in range(max_lines):
        our_line = our_lines[i] if i < len(our_lines) else ""
        their_line = their_lines[i] if i < len(their_lines) else ""

        our_match = CHECKBOX_PATTERN.match(our_line)
        their_match = CHECKBOX_PATTERN.match(their_line)

        if our_match and their_match:
            if their_match.group(2) == "x" and our_match.group(2) != "x":
                result_lines.append(their_line)
            else:
                result_lines.append(our_line)
        elif their_match and not our_line.strip():
            result_lines.append(their_line)
        else:
            result_lines.append(our_line)

    return "\n".join(result_lines)


def _parse_history_entries(content: str) -> list[dict[str, Any]] | None:
    match = HISTORY_BLOCK_PATTERN.search(content)
    if not match:
        return []

    history_yaml = f"history:\n{match.group('body')}"
    try:
        data = yaml.safe_load(history_yaml) or {}
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    entries = data.get("history", [])
    if not isinstance(entries, list):
        return None

    return [entry for entry in entries if isinstance(entry, dict)]


def _merge_history_entries(
    ours: list[dict[str, Any]], theirs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = ours + theirs

    seen: set[tuple[str, str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for entry in merged:
        key = (
            str(entry.get("timestamp", "")),
            str(entry.get("action", "")),
            str(entry.get("lane", "")),
            str(entry.get("agent", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)

    unique.sort(key=lambda entry: str(entry.get("timestamp", "")))
    return unique


def _build_history_block(entries: list[dict[str, Any]], indent: str = "") -> str:
    dumped = yaml.safe_dump(
        {"history": entries},
        sort_keys=False,
        default_flow_style=False,
    ).rstrip("\n")
    if not indent:
        return dumped
    return "\n".join(f"{indent}{line}" if line else line for line in dumped.split("\n"))


def resolve_history_conflict(ours: str, theirs: str) -> str | None:
    """Resolve history array conflict by merging chronologically."""
    our_entries = _parse_history_entries(ours)
    their_entries = _parse_history_entries(theirs)

    if our_entries is None or their_entries is None:
        return None

    if not our_entries and not their_entries:
        return None

    merged = _merge_history_entries(our_entries, their_entries)

    base = ours if HISTORY_BLOCK_PATTERN.search(ours) else theirs
    match = HISTORY_BLOCK_PATTERN.search(base)
    if not match:
        return None

    indent = match.group("indent")
    history_block = _build_history_block(merged, indent=indent)
    return base[: match.start()] + history_block + base[match.end() :]


def resolve_status_conflicts(repo_root: Path) -> list[ResolutionResult]:
    """Auto-resolve conflicts in status files after merge."""
    results: list[ResolutionResult] = []
    conflicted = get_conflicted_files(repo_root)

    for file_path in conflicted:
        rel_path = str(file_path.relative_to(repo_root))
        if not is_status_file(rel_path):
            results.append(
                ResolutionResult(
                    file_path=file_path,
                    resolved=False,
                    resolution_type="manual_required",
                    original_conflicts=1,
                    resolved_conflicts=0,
                )
            )
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            results.append(
                ResolutionResult(
                    file_path=file_path,
                    resolved=False,
                    resolution_type="error",
                    original_conflicts=1,
                    resolved_conflicts=0,
                )
            )
            continue

        regions = parse_conflict_markers(content)
        if not regions:
            continue

        resolved_content = content
        resolved_count = 0
        resolution_types: set[str] = set()

        for region in regions:
            if CHECKBOX_PATTERN.search(region.ours) or CHECKBOX_PATTERN.search(region.theirs):
                resolved_region = resolve_checkbox_conflict(region.ours, region.theirs)
                resolved_region = _preserve_trailing_newline(resolved_region, region.original)
                resolved_content = resolved_content.replace(region.original, resolved_region)
                resolved_count += 1
                resolution_types.add("checkbox")
                continue

            resolved_region = resolve_history_conflict(region.ours, region.theirs)
            if resolved_region is not None:
                lane_resolved = resolve_lane_conflict(region.ours, region.theirs)
                if lane_resolved is not None:
                    lane_value = extract_lane_value(lane_resolved)
                    if lane_value:
                        resolved_region = replace_lane_value(resolved_region, lane_value)
                    resolution_types.add("lane")
                resolution_types.add("history")
                resolved_region = _preserve_trailing_newline(resolved_region, region.original)
                resolved_content = resolved_content.replace(region.original, resolved_region)
                resolved_count += 1
                continue

            lane_resolved = resolve_lane_conflict(region.ours, region.theirs)
            if lane_resolved is not None:
                lane_resolved = _preserve_trailing_newline(lane_resolved, region.original)
                resolved_content = resolved_content.replace(region.original, lane_resolved)
                resolved_count += 1
                resolution_types.add("lane")

        resolved_all = resolved_count == len(regions)
        if resolved_count:
            file_path.write_text(resolved_content, encoding="utf-8")
            if resolved_all:
                subprocess.run(
                    ["git", "add", str(file_path)],
                    cwd=str(repo_root),
                    check=False,
                )

        if not resolution_types:
            resolution_types.add("manual_required")

        results.append(
            ResolutionResult(
                file_path=file_path,
                resolved=resolved_all,
                resolution_type="mixed" if len(resolution_types) > 1 else next(iter(resolution_types)),
                original_conflicts=len(regions),
                resolved_conflicts=resolved_count,
            )
        )

    return results


def get_conflicted_files(repo_root: Path) -> list[Path]:
    """Get list of files with merge conflicts."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    files: list[Path] = []
    for line in result.stdout.strip().split("\n"):
        if line:
            files.append(repo_root / line)
    return files
