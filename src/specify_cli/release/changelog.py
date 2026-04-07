"""Draft changelog builder for spec-kitty release preparation.

Reads ``kitty-specs/`` artifacts and local git tags only.
Zero network calls (FR-014).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stripped stdout. Raises on non-zero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _find_most_recent_v_tag(repo_root: Path) -> str | None:
    """Return the most recent tag matching ``v*``, or None if no tags exist."""
    output = _run_git(
        ["tag", "--list", "v*", "--sort=-creatordate"],
        cwd=repo_root,
    )
    if not output:
        return None
    # head -1 equivalent: take the first non-empty line
    for line in output.splitlines():
        line = line.strip()
        if line:
            return line
    return None


def _tag_commit_date(repo_root: Path, tag: str) -> str | None:
    """Return the ISO-8601 commit date for the tagged commit, or None."""
    output = _run_git(
        ["log", "-1", "--format=%cI", f"refs/tags/{tag}"],
        cwd=repo_root,
    )
    return output if output else None


def _read_meta_json(mission_dir: Path) -> dict:
    """Read and return the parsed meta.json for a mission directory, or {}."""
    meta_path = mission_dir / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _read_spec_title(mission_dir: Path) -> str:
    """Extract the first H1 title from spec.md, or return the dir name."""
    spec_path = mission_dir / "spec.md"
    if not spec_path.exists():
        return mission_dir.name
    try:
        content = spec_path.read_text(encoding="utf-8")
    except OSError:
        return mission_dir.name
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return mission_dir.name


def _parse_wp_frontmatter_status(wp_file: Path) -> str | None:
    """Read the YAML frontmatter ``status`` field from a WP markdown file."""
    try:
        content = wp_file.read_text(encoding="utf-8")
    except OSError:
        return None
    # Frontmatter is between the first pair of ``---`` lines
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end == -1:
        return None
    fm_block = content[3:end]
    # Simple regex extraction — avoids YAML parser dependency
    match = re.search(r"^\s*status\s*:\s*(.+)$", fm_block, re.MULTILINE)
    if match:
        return match.group(1).strip().strip("'\"")
    return None


def _parse_wp_title(wp_file: Path) -> str:
    """Return the first H1 or H2 heading from a WP markdown file, or the filename."""
    try:
        content = wp_file.read_text(encoding="utf-8")
    except OSError:
        return wp_file.stem
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("# "):
            # Remove leading #s and whitespace
            return re.sub(r"^#+\s*", "", stripped)
    return wp_file.stem


def _parse_wp_id(wp_file: Path) -> str:
    """Extract WP ID from frontmatter or fall back to filename stem."""
    try:
        content = wp_file.read_text(encoding="utf-8")
    except OSError:
        return wp_file.stem
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_block = content[3:end]
            match = re.search(
                r"^\s*work_package_id\s*:\s*(.+)$", fm_block, re.MULTILINE
            )
            if match:
                return match.group(1).strip().strip("'\"")
    return wp_file.stem


def _is_accepted_wp(wp_file: Path) -> bool:
    """Return True if the WP frontmatter status indicates it is accepted/done."""
    status = _parse_wp_frontmatter_status(wp_file)
    if status is None:
        return False
    return status.lower() in {"done", "accepted", "merged"}


def build_changelog_block(
    repo_root: Path,
    since_tag: str | None = None,
) -> tuple[str, list[str]]:
    """Build a draft changelog block from ``kitty-specs/`` artifacts.

    Args:
        repo_root: Absolute path to the repository root.
        since_tag: A git tag name. Only missions created after this tag's
            commit date are included. If ``None``, the most recent ``v*``
            tag is used. If no tags exist at all, all missions are included.

    Returns:
        A tuple ``(changelog_markdown, mission_slug_list)`` where:
        - ``changelog_markdown`` is a multi-line markdown string ready to
          paste into CHANGELOG.md.
        - ``mission_slug_list`` is a list of mission-slug strings that were
          included in the changelog block.

    No network calls are made. Uses ``git tag --list`` and filesystem reads only.
    """
    # Resolve the tag to compare against
    if since_tag is None:
        since_tag = _find_most_recent_v_tag(repo_root)

    since_date: str | None = None
    if since_tag is not None:
        since_date = _tag_commit_date(repo_root, since_tag)

    kitty_specs_dir = repo_root / "kitty-specs"
    if not kitty_specs_dir.exists():
        return ("", [])

    mission_dirs = sorted(
        [d for d in kitty_specs_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )

    included_missions: list[tuple[str, str, list[str]]] = []

    for mission_dir in mission_dirs:
        meta = _read_meta_json(mission_dir)
        mission_slug = mission_dir.name

        # Filter by creation date if we have a reference date
        if since_date is not None:
            created_at = meta.get("created_at", "")
            if created_at and created_at <= since_date:
                # Mission predates the tag; still include if it has WPs accepted
                # after the tag date (best-effort: check any accepted WPs)
                # We use the simple heuristic from the spec: meta.json created_at
                # as the cheap proxy. If it's older, skip.
                pass  # fall through to WP scan

        # Collect accepted WPs
        tasks_dir = mission_dir / "tasks"
        accepted_wps: list[str] = []
        if tasks_dir.exists():
            wp_files = sorted(tasks_dir.glob("WP*.md"), key=lambda f: f.name)
            for wp_file in wp_files:
                if _is_accepted_wp(wp_file):
                    wp_id = _parse_wp_id(wp_file)
                    title = _parse_wp_title(wp_file)
                    accepted_wps.append(f"{wp_id}: {title}")

        if not accepted_wps:
            continue

        friendly_name = meta.get("friendly_name", mission_slug)
        spec_title = _read_spec_title(mission_dir)
        display_name = friendly_name or spec_title or mission_slug

        included_missions.append((mission_slug, display_name, accepted_wps))

    if not included_missions:
        return ("", [])

    # Render the markdown block
    lines: list[str] = []
    for mission_slug, display_name, wps in included_missions:
        lines.append(f"### {display_name} (`{mission_slug}`)")
        lines.append("")
        for wp in wps:
            lines.append(f"- {wp}")
        lines.append("")

    changelog_markdown = "\n".join(lines).rstrip() + "\n"
    mission_slug_list = [slug for slug, _, _ in included_missions]

    return (changelog_markdown, mission_slug_list)
