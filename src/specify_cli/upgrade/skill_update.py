"""Reusable utilities for upgrading skill files across all agent skill roots.

Use this module when writing migrations that update skill content. It handles
the complexity of finding skill files across all possible agent skill root
directories (native-root-required, shared-root-capable, and agent-specific).

Example migration using this utility:

    from specify_cli.upgrade.skill_update import (
        find_skill_files,
        apply_text_replacements,
        SkillFileInfo,
    )

    # Find all copies of a skill
    files = find_skill_files(project_path, "spec-kitty-setup-doctor")

    # Apply replacements
    for info in files:
        apply_text_replacements(info.path, [
            ("old text", "new text"),
            ("another old", "another new"),
        ])

See also: agent-path-matrix.md in the setup-doctor skill references.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# All possible skill root directories from agent-path-matrix.md.
# Covers native-root-required, shared-root-capable, and agent-specific roots.
SKILL_ROOTS: list[str] = [
    ".claude/skills",       # Claude Code (native-root-required)
    ".agents/skills",       # Shared root for shared-root-capable agents
    ".qwen/skills",         # Qwen Code (native-root-required)
    ".kilocode/skills",     # Kilo Code (native-root-required)
    ".github/skills",       # GitHub Copilot (agent-specific)
    ".gemini/skills",       # Gemini CLI (agent-specific)
    ".cursor/skills",       # Cursor (agent-specific)
    ".opencode/skills",     # opencode (agent-specific)
    ".windsurf/skills",     # Windsurf (agent-specific)
    ".augment/skills",      # Auggie CLI (agent-specific)
    ".roo/skills",          # Roo Code (agent-specific)
    ".agent/skills",        # Google Antigravity (agent-specific)
    ".codex/skills",        # Codex CLI (if agent-specific root exists)
]


@dataclass
class SkillFileInfo:
    """Information about a discovered skill file."""

    path: Path
    """Absolute path to the skill file."""

    skill_root: str
    """The skill root directory (e.g., '.claude/skills')."""

    skill_name: str
    """The skill directory name (e.g., 'spec-kitty-setup-doctor')."""

    relative_path: str
    """Path relative to the skill directory (e.g., 'SKILL.md' or 'references/foo.md')."""


def find_skill_files(
    project_path: Path,
    skill_name: str,
    file_patterns: list[str] | None = None,
) -> list[SkillFileInfo]:
    """Find all installed copies of a skill across all agent skill roots.

    Args:
        project_path: Root of the project directory.
        skill_name: Name of the skill directory (e.g., 'spec-kitty-setup-doctor').
        file_patterns: Optional list of relative file paths within the skill to find.
            If None, finds all files recursively.

    Returns:
        List of SkillFileInfo for each found file.
    """
    found: list[SkillFileInfo] = []

    for root in SKILL_ROOTS:
        skill_dir = project_path / root / skill_name
        if not skill_dir.is_dir():
            continue

        if file_patterns:
            for pattern in file_patterns:
                file_path = skill_dir / pattern
                if file_path.is_file():
                    found.append(SkillFileInfo(
                        path=file_path,
                        skill_root=root,
                        skill_name=skill_name,
                        relative_path=pattern,
                    ))
        else:
            for file_path in sorted(skill_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                rel = str(file_path.relative_to(skill_dir))
                found.append(SkillFileInfo(
                    path=file_path,
                    skill_root=root,
                    skill_name=skill_name,
                    relative_path=rel,
                ))

    return found


def apply_text_replacements(
    file_path: Path,
    replacements: list[tuple[str, str]],
) -> bool:
    """Apply a list of text replacements to a file.

    Args:
        file_path: Path to the file to modify.
        replacements: List of (old_text, new_text) tuples.

    Returns:
        True if the file was modified, False if no changes were needed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    original = content
    for old, new in replacements:
        content = content.replace(old, new)

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def file_contains_any(file_path: Path, markers: list[str]) -> bool:
    """Check if a file contains any of the given marker strings.

    Args:
        file_path: Path to the file to check.
        markers: List of strings to search for.

    Returns:
        True if any marker is found in the file content.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    return any(marker in content for marker in markers)


def replace_skill_file(
    project_path: Path,
    skill_name: str,
    relative_path: str,
    new_content: str,
) -> list[str]:
    """Replace a skill file across all agent skill roots with new content.

    This is for cases where text replacements aren't sufficient and you need
    to write the entire file content.

    Args:
        project_path: Root of the project directory.
        skill_name: Name of the skill directory.
        relative_path: File path relative to the skill directory.
        new_content: The new file content to write.

    Returns:
        List of paths (relative to project) that were updated.
    """
    updated: list[str] = []

    for root in SKILL_ROOTS:
        file_path = project_path / root / skill_name / relative_path
        if not file_path.is_file():
            continue

        try:
            existing = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if existing != new_content:
            file_path.write_text(new_content, encoding="utf-8")
            updated.append(str(file_path.relative_to(project_path)))

    return updated
