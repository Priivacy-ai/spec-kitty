"""Migration: expand glossary-context skill with pipeline architecture documentation.

The original skill only covered curation (inspect, update, resolve). This adds
the full 5-layer middleware pipeline explanation, term extraction methods,
checkpoint/resume mechanism, step-level configuration, integration patterns,
and all 8 event types — everything an agent needs to understand how the glossary
actually runs during mission execution.

Uses the reusable skill_update utility to find and replace skill files across
all agent skill roots.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from ..registry import MigrationRegistry
from ..skill_update import file_contains_any, find_skill_files
from .base import BaseMigration, MigrationResult

_SKILL_NAME = "spec-kitty-glossary-context"

# The old SKILL.md starts with "## Step 1: Locate Glossary Context" without
# the "## How the Glossary Works" architecture section.
_OLD_MARKERS = [
    "## Step 1: Locate Glossary Context\n\nIdentify the glossary state",
]

# New markers prove the fix was applied.
_NEW_MARKERS = [
    "## How the Glossary Works",
    "5-layer middleware pipeline",
]


@MigrationRegistry.register
class FixGlossaryContextSkillMigration(BaseMigration):
    """Expand glossary-context skill with full pipeline architecture."""

    migration_id = "2.1.2_fix_glossary_context_skill"
    description = (
        "Expand glossary-context skill with pipeline architecture, extraction "
        "methods, checkpoint/resume, step config, and all 8 event types"
    )
    target_version = "2.1.2"

    def detect(self, project_path: Path) -> bool:
        """Return True if any glossary-context SKILL.md lacks the pipeline docs."""
        for info in find_skill_files(project_path, _SKILL_NAME, ["SKILL.md"]):
            if file_contains_any(info.path, _OLD_MARKERS):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if project has glossary-context skill files."""
        files_found = find_skill_files(project_path, _SKILL_NAME)
        if not files_found:
            return False, "No glossary-context skill files found in any skill root"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Replace glossary-context SKILL.md with expanded version."""
        changes: list[str] = []
        errors: list[str] = []

        # Load canonical content from doctrine package
        try:
            doctrine_root = files("doctrine")
            canonical_path = doctrine_root.joinpath(
                "skills", _SKILL_NAME, "SKILL.md"
            )
            new_content = canonical_path.read_text(encoding="utf-8")
        except Exception:
            # Fallback: try filesystem path relative to this module
            fallback = (
                Path(__file__).resolve().parents[3]
                / "doctrine"
                / "skills"
                / _SKILL_NAME
                / "SKILL.md"
            )
            if fallback.is_file():
                new_content = fallback.read_text(encoding="utf-8")
            else:
                return MigrationResult(
                    success=False,
                    errors=["Cannot locate canonical SKILL.md for glossary-context"],
                )

        for info in find_skill_files(project_path, _SKILL_NAME, ["SKILL.md"]):
            if not file_contains_any(info.path, _OLD_MARKERS):
                continue
            rel = str(info.path.relative_to(project_path))
            if dry_run:
                changes.append(f"Would replace {rel}")
            else:
                try:
                    info.path.write_text(new_content, encoding="utf-8")
                    changes.append(f"Replaced {rel}")
                except OSError as e:
                    errors.append(f"Failed to write {rel}: {e}")

        if not changes and not errors:
            changes.append("All glossary-context skill files already up to date")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
        )
