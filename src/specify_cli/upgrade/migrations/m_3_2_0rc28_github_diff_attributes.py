"""Migration 3.2.0rc28: collapse generated Spec Kitty artifacts in GitHub PRs."""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

_ATTRIBUTES_ENTRIES = (
    "kitty-specs/**/status.json linguist-generated=true",
    "kitty-specs/**/status.events.jsonl linguist-generated=true",
    "kitty-specs/**/lanes.json linguist-generated=true",
    "kitty-specs/**/mission-events.jsonl linguist-generated=true",
    "kitty-specs/**/snapshot-latest.json linguist-generated=true",
    "kitty-specs/**/acceptance-matrix.json linguist-generated=true",
    "kitty-specs/**/occurrence_map.yaml linguist-generated=true",
    "kitty-specs/**/tasks/** linguist-generated=true",
    "kitty-specs/**/research/evidence-log.csv linguist-generated=true",
    "kitty-specs/**/research/source-register.csv linguist-generated=true",
    "kitty-specs/**/test-transcripts/** linguist-generated=true",
    "kitty-specs/**/baseline/** linguist-generated=true",
    "kitty-specs/**/canary-evidence/** linguist-generated=true",
    ".kittify/workspaces/** linguist-generated=true",
    ".kittify/workspaces/** -diff",
    ".kittify/migrations/** linguist-generated=true",
    ".kittify/migrations/** -diff",
)


def _missing_entries(project_path: Path) -> list[str]:
    attributes_path = project_path / ".gitattributes"
    if not attributes_path.exists():
        return list(_ATTRIBUTES_ENTRIES)

    existing = set(attributes_path.read_text(encoding="utf-8").splitlines())
    return [entry for entry in _ATTRIBUTES_ENTRIES if entry not in existing]


@MigrationRegistry.register
class GitHubDiffAttributesMigration(BaseMigration):
    """Mark Spec Kitty generated artifacts as generated in GitHub PR diffs."""

    migration_id = "3.2.0rc28_github_diff_attributes"
    description = "Mark Spec Kitty generated artifacts as generated in .gitattributes"
    target_version = "3.2.0rc28"

    def detect(self, project_path: Path) -> bool:
        return bool(_missing_entries(project_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        missing = _missing_entries(project_path)
        if not missing:
            return MigrationResult(success=True)

        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=[f"Would add .gitattributes entry: {entry}" for entry in missing],
            )

        attributes_path = project_path / ".gitattributes"
        lines: list[str] = []
        if attributes_path.exists():
            lines = attributes_path.read_text(encoding="utf-8").splitlines()

        lines.extend(missing)
        attributes_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        return MigrationResult(
            success=True,
            changes_made=[f"Added .gitattributes entry: {entry}" for entry in missing],
        )
