"""Migration: expand constitution-doctrine skill with extraction rules and schemas.

The original skill documented the workflow steps but not the internals. This adds
governance.yaml schema, directives.yaml schema, sync extraction rules (heading
keyword map, regex patterns), hash-based staleness detection, context injection
mechanism, interview profiles with question-to-governance mapping, answers.yaml
schema, and available doctrine assets (paradigms, directives, template sets).

Uses the reusable skill_update utility to find and replace skill files across
all agent skill roots.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from ..registry import MigrationRegistry
from ..skill_update import file_contains_any, find_skill_files
from .base import BaseMigration, MigrationResult

_SKILL_NAME = "spec-kitty-constitution-doctrine"

# The old SKILL.md lacks the "How the Constitution System Works" architecture
# section and goes straight to "Step 1: Understand the Governance Model".
_OLD_MARKERS = [
    "## Step 1: Understand the Governance Model",
]

_NEW_MARKERS = [
    "## How the Constitution System Works",
    "### How Sync Extraction Works",
]


@MigrationRegistry.register
class FixConstitutionDoctrineSkillMigration(BaseMigration):
    """Expand constitution-doctrine skill with extraction rules and schemas."""

    migration_id = "2.1.2_fix_constitution_doctrine_skill"
    description = (
        "Expand constitution-doctrine skill with governance.yaml schema, "
        "extraction rules, interview profiles, and doctrine asset catalog"
    )
    target_version = "2.1.2"

    def detect(self, project_path: Path) -> bool:
        """Return True if any constitution-doctrine SKILL.md lacks the new docs."""
        for info in find_skill_files(project_path, _SKILL_NAME, ["SKILL.md"]):
            if file_contains_any(info.path, _OLD_MARKERS):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if project has constitution-doctrine skill files."""
        files_found = find_skill_files(project_path, _SKILL_NAME)
        if not files_found:
            return True, ""  # apply() handles missing files gracefully
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Replace constitution-doctrine SKILL.md with expanded version."""
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
                    errors=["Cannot locate canonical SKILL.md for constitution-doctrine"],
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
            changes.append("All constitution-doctrine skill files already up to date")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
        )
