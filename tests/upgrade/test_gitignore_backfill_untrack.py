"""WP05 T026 — gitignore-backfill must untrack, not just ignore (#3393, FR-010).

Contract ``contracts/seam-contracts.md`` C6: after
``AgentsSkillsGitignoreBackfillMigration`` runs, no path is both git-tracked
and gitignored. Adding an entry to ``.gitignore`` alone does not stop git from
continuing to track a path that was already committed -- the working tree
stays dirty forever. This must be exercised against a REAL git repository
(``git init`` + a real commit) and asserted on real ``git ls-files`` tracking
state / ``git status`` porcelain output, not just on the rendered
``.gitignore`` text -- the defect this closes is invisible if you only check
the ignore file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_2_5_agents_skills_gitignore_backfill import (
    AgentsSkillsGitignoreBackfillMigration,
    _MANIFEST_ENTRY,
    _SKILLS_ROOT_ENTRY,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")


def _ls_files(root: Path) -> set[str]:
    out = _git(root, "ls-files").stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def _porcelain(root: Path) -> list[str]:
    out = _git(root, "status", "--porcelain").stdout
    return [line for line in out.splitlines() if line.strip()]


def test_apply_untracks_a_previously_committed_skills_root(tmp_path: Path) -> None:
    """The realistic #3393 shape: `.agents/skills/` was committed before this
    migration existed. After apply(), it must be gitignored AND untracked --
    tracked-and-ignored must never coexist."""
    root = tmp_path / "repo"
    _init_repo(root)

    skills_dir = root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "spec-kitty.implement" / "SKILL.md").parent.mkdir(parents=True, exist_ok=True)
    (skills_dir / "spec-kitty.implement" / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init (accidentally committed skills root)")

    assert any(p.startswith(".agents/skills") for p in _ls_files(root)), "fixture sanity: must start tracked"

    migration = AgentsSkillsGitignoreBackfillMigration()
    assert migration.detect(root) is True

    result = migration.apply(root, dry_run=False)
    assert result.success is True

    gitignore_text = (root / ".gitignore").read_text(encoding="utf-8")
    assert _SKILLS_ROOT_ENTRY in gitignore_text

    tracked_after = _ls_files(root)
    assert not any(p.startswith(".agents/skills") for p in tracked_after), (
        f"path must be untracked after the backfill, still tracked: {tracked_after}"
    )

    # `git rm --cached` stages the removal (a "D " index entry) rather than
    # committing it -- consistent with this codebase's existing convention
    # that the main checkout's commit is left for the CLI caller (see
    # MigrationRunner._upgrade_worktrees's own docstring). That staged
    # deletion is expected here. The actual invariant this migration must
    # hold is narrower and is what would break WITHOUT the fix: the path
    # must never show up as a plain "??" (untracked-and-NOT-ignored) entry --
    # that would mean the gitignore coverage never actually took effect.
    dirt = _porcelain(root)
    assert not any(line.startswith("??") and "skills" in line for line in dirt), dirt
    assert any(line.startswith("D") and "skills" in line for line in dirt), (
        f"expected a staged removal of the untracked path, got: {dirt}"
    )


def test_apply_untracks_a_previously_committed_manifest(tmp_path: Path) -> None:
    """Same invariant for the second backfilled path, the skills manifest."""
    root = tmp_path / "repo"
    _init_repo(root)

    (root / ".kittify").mkdir()
    (root / ".kittify" / "skills-manifest.json").write_text("{}\n", encoding="utf-8")
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init (accidentally committed manifest)")

    assert ".kittify/skills-manifest.json" in _ls_files(root)

    migration = AgentsSkillsGitignoreBackfillMigration()
    result = migration.apply(root, dry_run=False)
    assert result.success is True

    assert _MANIFEST_ENTRY in (root / ".gitignore").read_text(encoding="utf-8")
    assert ".kittify/skills-manifest.json" not in _ls_files(root)


def test_apply_leaves_untracked_paths_untouched(tmp_path: Path) -> None:
    """The common (non-regression) case: the path was never committed. The
    backfill must still work -- git rm --cached has nothing to do, so no
    error surfaces and the ignore entry still lands."""
    root = tmp_path / "repo"
    _init_repo(root)
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")

    skills_dir = root / ".agents" / "skills" / "spec-kitty.implement"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# skill\n", encoding="utf-8")

    migration = AgentsSkillsGitignoreBackfillMigration()
    result = migration.apply(root, dry_run=False)
    assert result.success is True
    assert _SKILLS_ROOT_ENTRY in (root / ".gitignore").read_text(encoding="utf-8")
    assert not any(p.startswith(".agents/skills") for p in _ls_files(root))


def test_dry_run_does_not_untrack_or_write(tmp_path: Path) -> None:
    """A dry run must not mutate the git index or .gitignore at all."""
    root = tmp_path / "repo"
    _init_repo(root)

    skills_dir = root / ".agents" / "skills" / "spec-kitty.implement"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")

    tracked_before = _ls_files(root)
    assert any(p.startswith(".agents/skills") for p in tracked_before)

    migration = AgentsSkillsGitignoreBackfillMigration()
    result = migration.apply(root, dry_run=True)
    assert result.success is True

    assert _ls_files(root) == tracked_before, "dry-run must not touch the git index"
    assert not (root / ".gitignore").exists(), "dry-run must not write .gitignore"
