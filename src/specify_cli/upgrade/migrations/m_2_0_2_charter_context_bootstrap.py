"""Migration: Insert charter context bootstrap into deployed agent prompts.

Updates generated agent prompts in user projects to:
- Insert ``spec-kitty charter context --action <action> --json`` bootstrap block
  before the prompt body when it is absent.
- Strip inline governance prose sections (## Governance, ## Directives, ## Tactics,
  ## Toolguides, ## Styleguides) that were moved to runtime doctrine assets in WP04.
- Remove obsolete ``.kittify/charter/library/`` directories.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project

# Actions that get their own bootstrap call
BOOTSTRAP_ACTIONS: tuple[str, ...] = ("specify", "plan", "implement", "review")

# Inline governance headings that should be stripped (moved to runtime doctrine)
_INLINE_GOVERNANCE_HEADINGS = ("Governance", "Directives", "Tactics", "Toolguides", "Styleguides")

# Match a governance section from its ## heading (exact name, no trailing words)
# to the next ## heading or end-of-string.
# The heading must be followed immediately by \n so that "## Governance Context"
# (our bootstrap block heading) is NOT matched.
_GOVERNANCE_RE = re.compile(
    r"\n## (?:" + "|".join(_INLINE_GOVERNANCE_HEADINGS) + r")\n.*?(?=\n## |\Z)",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bootstrap_block(action: str) -> str:
    """Return the Markdown bootstrap block for *action*."""
    return (
        "\n## Governance Context\n\n"
        "> Run to load runtime doctrine for this action:\n"
        "> ```\n"
        f"> spec-kitty charter context --action {action} --json\n"
        "> ```\n"
    )


def _bootstrap_sentinel(action: str) -> str:
    return f"spec-kitty charter context --action {action}"


def _action_from_path(file_path: Path) -> str | None:
    """Derive the action name from a filename like ``spec-kitty.specify.md``."""
    # stem for "spec-kitty.specify.md" → "spec-kitty.specify"
    stem = file_path.stem
    parts = stem.split(".")
    if len(parts) >= 2 and parts[-1] in BOOTSTRAP_ACTIONS:
        return parts[-1]
    return None


def _needs_bootstrap(content: str, action: str) -> bool:
    return _bootstrap_sentinel(action) not in content


def _has_inline_governance(content: str) -> bool:
    return bool(_GOVERNANCE_RE.search(content))


def _strip_inline_governance(content: str) -> str:
    return _GOVERNANCE_RE.sub("", content)


def _insert_bootstrap_md(content: str, action: str) -> str:
    """Insert bootstrap block after YAML frontmatter (or at start) in Markdown content."""
    block = _bootstrap_block(action)

    if content.startswith("---"):
        # Find the closing frontmatter delimiter after the opening ---
        end = content.find("\n---", 3)
        if end != -1:
            close_end = end + 4  # length of "\n---"
            return content[:close_end] + block + content[close_end:]

    return block + content


def _insert_bootstrap_toml(content: str, action: str) -> str:
    """Insert bootstrap block at the start of the ``prompt = \"\"\"`` string in TOML content."""
    block = _bootstrap_block(action)
    marker = 'prompt = """'
    idx = content.find(marker)
    if idx != -1:
        insert_at = idx + len(marker)
        return content[:insert_at] + block + content[insert_at:]
    # Fallback: prepend to the whole file
    return block + content


def _process_file(content: str, action: str, *, is_toml: bool) -> tuple[str, bool]:
    """Return ``(updated_content, was_changed)`` after applying all transformations."""
    updated = content

    if _has_inline_governance(updated):
        updated = _strip_inline_governance(updated)

    if _needs_bootstrap(updated, action):
        updated = _insert_bootstrap_toml(updated, action) if is_toml else _insert_bootstrap_md(updated, action)

    return updated, updated != content


# ---------------------------------------------------------------------------
# Migration class
# ---------------------------------------------------------------------------

_ACTION_FILE_GLOBS = tuple(
    f"spec-kitty.{action}.*" for action in BOOTSTRAP_ACTIONS
)

_LIBRARY_SUBPATH = ".kittify/charter/library"


@MigrationRegistry.register
class CharterContextBootstrapMigration(BaseMigration):
    """Insert charter context bootstrap calls into deployed agent prompts.

    This migration:
    1. Inserts a ``## Governance Context`` bootstrap block before the prompt body
       of each action file (specify, plan, implement, review) when absent.
    2. Strips inline governance prose sections that were moved to runtime doctrine.
    3. Removes the obsolete ``.kittify/charter/library/`` directory tree.
    """

    migration_id = "2.0.2_charter_context_bootstrap"
    description = "Insert charter context bootstrap into deployed agent prompts"
    target_version = "2.0.2"

    def detect(self, project_path: Path) -> bool:
        """Return True when any action prompt file needs updating or library dir exists."""
        if (project_path / _LIBRARY_SUBPATH).exists():
            return True

        for file_path in self._iter_action_prompt_files(project_path):
            action = _action_from_path(file_path)
            if action is None:
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except OSError:
                continue
            if _needs_bootstrap(content, action) or _has_inline_governance(content):
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply bootstrap insertion, governance stripping, and library cleanup."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        for file_path in self._iter_action_prompt_files(project_path):
            action = _action_from_path(file_path)
            if action is None:
                continue

            try:
                original = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                warnings.append(f"Skipped unreadable file {file_path}: {exc}")
                continue

            is_toml = file_path.suffix == ".toml"
            updated, changed = _process_file(original, action, is_toml=is_toml)

            if not changed:
                continue

            rel = str(file_path.relative_to(project_path))
            if dry_run:
                changes.append(f"Would update: {rel}")
                continue

            try:
                file_path.write_text(updated, encoding="utf-8")
            except OSError as exc:
                errors.append(f"Failed to update {rel}: {exc}")
                continue

            changes.append(f"Updated: {rel}")

        # Remove obsolete library directory
        library_dir = project_path / _LIBRARY_SUBPATH
        if library_dir.exists():
            if dry_run:
                changes.append(f"Would remove: {_LIBRARY_SUBPATH}")
            else:
                try:
                    shutil.rmtree(library_dir)
                    changes.append(f"Removed: {_LIBRARY_SUBPATH}")
                except OSError as exc:
                    errors.append(f"Failed to remove {_LIBRARY_SUBPATH}: {exc}")

        if not changes and not errors:
            changes.append("No action prompt files needed updating")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    # ------------------------------------------------------------------

    def _iter_action_prompt_files(self, project_path: Path) -> list[Path]:
        """Enumerate action prompt files for all configured agent directories."""
        files: list[Path] = []
        for agent_dir, subdir in get_agent_dirs_for_project(project_path):
            command_dir = project_path / agent_dir / subdir
            if not command_dir.exists():
                continue
            for pattern in _ACTION_FILE_GLOBS:
                files.extend(sorted(command_dir.glob(pattern)))
        return files
