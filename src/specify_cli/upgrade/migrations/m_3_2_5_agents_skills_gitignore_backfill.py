"""Migration: backfill ``.agents/skills/`` + skills-manifest gitignore coverage (#2412).

The skills installer projects global canonical skills into the shared
``.agents/skills/`` root (codex/vibe/pi/letta), preferring **absolute
symlinks** into the user-global canonical root — machine-local content by
construction. ``.claude/`` and the other agent dirs are gitignored wholesale
by ``GitignoreManager.protect_all_agents()`` at init, but bare ``.agents/``
is absent from ``AGENT_DIRECTORIES``, so nothing ever ignored the shared
root: committing it puts ``/Users/<name>/...`` symlink blobs in the repo.
The per-machine install ledger ``.kittify/skills-manifest.json`` (timestamps,
content hashes, per-machine delivery_mode) had the same gap.

Both are now registered ``IGNORED`` state surfaces (``shared_skills_projection``
and ``skills_install_manifest`` in ``state/contract.py``), so a fresh
``spec-kitty init`` gitignores them via the full runtime entry set. This
backfill repairs already-initialised projects on ``spec-kitty upgrade``,
following the ``3.2.4_derived_mission_views`` precedent: the entries are
**hardcoded here** rather than sourced from the live contract so the
migration's behaviour is frozen and deterministic regardless of future
contract changes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from specify_cli.gitignore_manager import GitignoreManager, read_ignore_file_text

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

_SKILLS_ROOT_ENTRY = ".agents/skills/"
_MANIFEST_ENTRY = ".kittify/skills-manifest.json"

# Equivalent hand-added forms that already ignore the same paths — treat any
# of them as present so the backfill stays idempotent and never appends a
# duplicate beside a user's own entry.
_EQUIVALENT_ENTRIES: dict[str, frozenset[str]] = {
    _SKILLS_ROOT_ENTRY: frozenset(
        {".agents/skills/", ".agents/skills", ".agents/", ".agents"}
    ),
    _MANIFEST_ENTRY: frozenset({".kittify/skills-manifest.json"}),
}


def _read_gitignore_entries(project_path: Path) -> set[str]:
    content = read_ignore_file_text(project_path / ".gitignore")
    return {
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _missing_entries(project_path: Path) -> list[str]:
    present = _read_gitignore_entries(project_path)
    return [
        entry
        for entry, equivalents in _EQUIVALENT_ENTRIES.items()
        if equivalents.isdisjoint(present)
    ]


def _untrack_tracked_paths(project_path: Path, entries: list[str]) -> list[str]:
    """Untrack any of ``entries`` that are already git-tracked (FR-010, #3393).

    Adding a path to ``.gitignore`` alone does not stop git from tracking a
    path that was already committed -- the working tree stays dirty (`git
    status` keeps showing modifications) even though the path is "ignored"
    going forward. The post-condition this migration must hold is: no path is
    both tracked and gitignored. ``git rm --cached`` drops the path from the
    index while leaving the working-tree file untouched.

    Best-effort and silent on failure: a project that is not a git repo (or
    has no ``git`` binary available) is left exactly as before -- matching
    this migration's existing fail-open posture (``can_apply`` only checks
    that ``project_path`` exists).
    """
    candidates = [entry.rstrip("/") for entry in entries]
    try:
        listed = subprocess.run(
            ["git", "-C", str(project_path), "ls-files", "-z", "--", *candidates],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    tracked = sorted({p for p in listed.stdout.decode("utf-8").split("\0") if p})
    if not tracked:
        return []

    try:
        subprocess.run(
            ["git", "-C", str(project_path), "rm", "--cached", "-r", "-q", "--", *tracked],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    return tracked


@MigrationRegistry.register
class AgentsSkillsGitignoreBackfillMigration(BaseMigration):
    """Ensure the machine-local skill projection surfaces are gitignored."""

    migration_id = "3.2.5_agents_skills_gitignore_backfill"
    description = "Backfill .agents/skills/ + .kittify/skills-manifest.json gitignore coverage"
    target_version = "3.2.5"

    def detect(self, project_path: Path) -> bool:
        return bool(_missing_entries(project_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        missing = _missing_entries(project_path)

        if dry_run:
            changes = [f"Would add {entry} to .gitignore" for entry in missing]
            return MigrationResult(success=True, changes_made=changes)

        if not missing:
            return MigrationResult(
                success=True, changes_made=["gitignore entries already present"]
            )

        GitignoreManager(project_path).ensure_entries(missing)
        untracked = _untrack_tracked_paths(project_path, missing)
        changes = [f"Added gitignore entry: {entry}" for entry in missing]
        changes.extend(f"Untracked previously-tracked path: {path}" for path in untracked)
        return MigrationResult(success=True, changes_made=changes)
