"""Migration 3.2.0: Move Codex from .codex/prompts/ to .agents/skills/.

Before 3.2.0 Spec Kitty wrote command prompt files for Codex into
``.codex/prompts/spec-kitty.<command>.md``.  Starting with 3.2.0, the Codex
integration is delivered as Agent Skills packages under
``.agents/skills/spec-kitty.<command>/SKILL.md`` — the same layout used by the
Vibe agent.

This migration:
1. No-ops when ``codex`` is absent from ``agents.available`` in
   ``.kittify/config.yaml``.
2. Installs the new ``.agents/skills/`` packages via
   :func:`specify_cli.skills.command_installer.install`.
3. Removes every ``.codex/prompts/spec-kitty.<command>.md`` file whose basename
   is in :data:`._legacy_codex_hashes.LEGACY_CODEX_FILENAMES` (owned files).
4. Leaves any other files in ``.codex/prompts/`` untouched (third-party).
5. Removes ``.codex/prompts/`` itself if it is empty after cleanup.  The
   ``.codex/`` directory is **never** touched.

Hash-comparison simplification
--------------------------------
This migration uses filename-only classification (Option A).  It does not
compare SHA-256 digests against pre-3.2 known hashes.  Any
``spec-kitty.<command>.md`` file — regardless of whether it has been edited —
is treated as owned and deleted after the new skills are installed.

Users who have hand-edited these files should stash them before running
``spec-kitty upgrade``.  See :mod:`._legacy_codex_hashes` for the full
rationale.

Non-recursive scope
-------------------
Only ``.md`` files directly inside ``.codex/prompts/`` are inspected.  The
pre-3.2 renderer never produced nested subdirectories, so recursive search is
unnecessary and is intentionally omitted.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from ._legacy_codex_hashes import LEGACY_CODEX_FILENAMES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classifier dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegacyCodexPrompt:
    """Represents a single ``.codex/prompts/*.md`` file and its classification.

    Attributes
    ----------
    path:
        Absolute path to the file.
    current_hash:
        SHA-256 hex digest of the file as it currently exists on disk.
        Empty string if the file could not be read.
    previous_version_hash:
        ``None`` — hash comparison is not performed in this migration
        (Option A simplification; see module docstring).
    status:
        ``"owned_unedited"`` if the filename is in
        :data:`LEGACY_CODEX_FILENAMES` (will be deleted after install).
        ``"third_party"`` otherwise (left untouched).
        ``"owned_edited"`` is unused in the Option-A implementation but
        retained in the type for forward-compatibility.
    """

    path: Path
    current_hash: str
    previous_version_hash: str | None
    status: Literal["owned_unedited", "owned_edited", "third_party"]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _compute_hash(path: Path) -> str:
    """Return the SHA-256 hex digest of *path*, or empty string on error."""
    import hashlib  # noqa: PLC0415

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _classify(prompts_dir: Path) -> list[LegacyCodexPrompt]:
    """Enumerate direct ``.md`` children of *prompts_dir* and classify each.

    Only non-recursive, direct children are examined.  This matches the layout
    produced by the pre-3.2 renderer, which never nested files.
    """
    results: list[LegacyCodexPrompt] = []
    for child in prompts_dir.iterdir():
        if not child.is_file() or child.suffix != ".md":
            continue
        if child.name in LEGACY_CODEX_FILENAMES:
            status: Literal["owned_unedited", "owned_edited", "third_party"] = (
                "owned_unedited"
            )
        else:
            status = "third_party"
        results.append(
            LegacyCodexPrompt(
                path=child,
                current_hash=_compute_hash(child),
                previous_version_hash=None,
                status=status,
            )
        )
    return results


def _install_skills(project_path: Path) -> None:
    """Install ``.agents/skills/`` packages for the ``codex`` agent."""
    from specify_cli.skills import command_installer  # noqa: PLC0415

    command_installer.install(project_path, "codex")


def _print_preservation_notice(preserved: list[LegacyCodexPrompt]) -> None:
    """Emit a notice to stderr listing files that were left untouched.

    The message is intentionally plain text so that grep-based CI does not
    mistake it for an error.
    """
    lines = [
        "spec-kitty upgrade notice: the following .codex/prompts/ files were "
        "left untouched because they are not Spec Kitty-owned files:",
    ]
    for p in preserved:
        lines.append(f"  • {p.path}")
    lines.append(
        "Your Codex integration now reads from .agents/skills/; "
        "these files will not be invoked automatically."
    )
    print("\n".join(lines), file=sys.stderr)


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


@MigrationRegistry.register
class CodexToSkillsMigration(BaseMigration):
    """Move Codex from .codex/prompts/ to .agents/skills/ (Agent Skills)."""

    migration_id = "3.2.0_codex_to_skills"
    description = "Move Codex from .codex/prompts/ to .agents/skills/ (Agent Skills)"
    target_version = "3.2.0"

    def detect(self, project_path: Path) -> bool:
        """Return True if legacy .codex/prompts/spec-kitty.*.md files exist."""
        prompts_dir = project_path / ".codex" / "prompts"
        if not prompts_dir.is_dir():
            return False
        return any(
            f.name in LEGACY_CODEX_FILENAMES
            for f in prompts_dir.iterdir()
            if f.is_file()
        )

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that .kittify/ exists (project is initialized)."""
        kittify = project_path / ".kittify"
        if not kittify.is_dir():
            return False, ".kittify/ directory does not exist (not initialized)"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply the Codex → Agent Skills migration.

        Parameters
        ----------
        project_path:
            Root of the project (contains ``.kittify/``, ``.codex/``, etc.).
        dry_run:
            If ``True``, report what *would* happen without touching the
            filesystem or the manifest.
        """
        from specify_cli.core.agent_config import load_agent_config  # noqa: PLC0415

        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        # --- No-op guard (T032) -----------------------------------------------
        try:
            agent_config = load_agent_config(project_path)
        except Exception as exc:
            errors.append(f"Could not load agent config: {exc}")
            return MigrationResult(success=False, errors=errors)

        if "codex" not in agent_config.available:
            logger.debug(
                "Skipping CodexToSkillsMigration: codex not in agents.available"
            )
            return MigrationResult(success=True, changes_made=[], warnings=[], errors=[])

        # --- Classify existing .codex/prompts/ files --------------------------
        prompts_dir = project_path / ".codex" / "prompts"
        classified: list[LegacyCodexPrompt] = []

        if prompts_dir.exists():
            classified = _classify(prompts_dir)

        owned = [p for p in classified if p.status == "owned_unedited"]
        third_party = [p for p in classified if p.status == "third_party"]

        # --- Install new .agents/skills/ packages ----------------------------
        if dry_run:
            changes.append(
                "Would install 11 Codex skill packages under .agents/skills/"
            )
            changes.append(
                f"Would delete {len(owned)} owned .codex/prompts/ file(s)"
            )
            if third_party:
                warnings.append(
                    f"Would preserve {len(third_party)} third-party file(s): "
                    + ", ".join(p.path.name for p in third_party)
                )
            return MigrationResult(
                success=True, changes_made=changes, warnings=warnings, errors=errors
            )

        try:
            _install_skills(project_path)
            changes.append(
                "Installed 11 Codex skill packages under .agents/skills/"
            )
        except Exception as exc:
            errors.append(f"Skill installation failed: {exc}")
            return MigrationResult(
                success=False, changes_made=changes, warnings=warnings, errors=errors
            )

        # --- Delete owned files -----------------------------------------------
        deleted = 0
        for p in owned:
            try:
                p.path.unlink()
                deleted += 1
            except OSError as exc:
                warnings.append(f"Could not remove {p.path.name}: {exc}")

        if deleted:
            changes.append(
                f"Migrated {deleted} Codex prompts from .codex/prompts/ to .agents/skills/"
            )

        # --- Notify about third-party files -----------------------------------
        if third_party:
            _print_preservation_notice(third_party)
            warnings.append(
                f"Preserved {len(third_party)} third-party file(s) in .codex/prompts/"
            )

        # --- Remove prompts dir if empty -------------------------------------
        if prompts_dir.exists():
            try:
                remaining = list(prompts_dir.iterdir())
                if not remaining:
                    prompts_dir.rmdir()
                    changes.append("Removed empty .codex/prompts/ directory")
            except OSError as exc:
                warnings.append(f"Could not remove .codex/prompts/ directory: {exc}")

        return MigrationResult(
            success=True, changes_made=changes, warnings=warnings, errors=errors
        )
