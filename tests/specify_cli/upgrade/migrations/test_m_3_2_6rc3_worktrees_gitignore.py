"""Regression tests for the ``.worktrees/`` gitignore backfill (#3689).

Every mission worktree is a full checkout under ``.worktrees/``, but only
the <0.13.1 migration ever excluded that root (via the local-only
``.git/info/exclude``), so projects initialised since then show
``?? .worktrees/`` forever and a stray ``git add -A`` stages entire nested
checkouts. Fresh ``init`` now emits the entry from the state contract;
this migration heals existing projects.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from kernel.clock import now_utc

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations import auto_discover_migrations
from specify_cli.upgrade.migrations.m_3_2_6rc3_worktrees_gitignore_backfill import (
    _WORKTREES_ENTRY,
    WorktreesGitignoreBackfillMigration,
)
from specify_cli.upgrade.registry import MigrationRegistry
from specify_cli.upgrade.runner import MigrationRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _init_git_repo(project_root: Path) -> None:
    subprocess.run(["git", "-C", str(project_root), "init", "-q"], check=True)


def _write_gitignore(project_root: Path, *entries: str) -> None:
    project_root.joinpath(".gitignore").write_text(
        "# Added by Spec Kitty CLI (auto-managed)\n" + "\n".join(entries) + "\n",
        encoding="utf-8",
    )


def _write_metadata(project_root: Path, version: str) -> None:
    ProjectMetadata(version=version, initialized_at=now_utc()).save(project_root / ".kittify")


def _read_gitignore(project_root: Path) -> str:
    return project_root.joinpath(".gitignore").read_text(encoding="utf-8")


def test_apply_adds_entry(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)

    WorktreesGitignoreBackfillMigration().apply(tmp_path)

    assert _WORKTREES_ENTRY in _read_gitignore(tmp_path)


def test_detect_true_when_missing(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")  # unrelated entry only

    assert WorktreesGitignoreBackfillMigration().detect(tmp_path) is True


@pytest.mark.parametrize("existing", [".worktrees/", ".worktrees", "/.worktrees/", "/.worktrees"])
def test_detect_false_when_equivalent_form_present(tmp_path: Path, existing: str) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, existing)

    assert WorktreesGitignoreBackfillMigration().detect(tmp_path) is False


def test_leading_whitespace_does_not_false_claim_coverage(tmp_path: Path) -> None:
    """Leading whitespace is significant; `` .worktrees/`` ignores another name."""
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, " .worktrees/")
    migration = WorktreesGitignoreBackfillMigration()

    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)

    assert result.success
    assert _read_gitignore(tmp_path).splitlines()[-1] == _WORKTREES_ENTRY
    ignored = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--quiet", "--no-index", ".worktrees/probe"],
        check=False,
    )
    assert ignored.returncode == 0


def test_later_negation_is_repaired_by_final_managed_rule(tmp_path: Path) -> None:
    """A textual occurrence neutralized later must not record a false-safe no-op."""
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".worktrees/", "!.worktrees/", "!.worktrees/**")
    migration = WorktreesGitignoreBackfillMigration()

    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)

    assert result.success
    assert _read_gitignore(tmp_path).splitlines()[-1] == _WORKTREES_ENTRY
    ignored = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--quiet", "--no-index", ".worktrees/probe"],
        check=False,
    )
    assert ignored.returncode == 0


def test_narrow_reinclusion_is_repaired_even_when_probe_is_ignored(tmp_path: Path) -> None:
    """One ignored sentinel cannot prove every worktree descendant is ignored."""
    _init_git_repo(tmp_path)
    _write_gitignore(
        tmp_path,
        ".worktrees/",
        "!.worktrees/",
        ".worktrees/*",
        "!.worktrees/demo/",
        "!.worktrees/demo/**",
    )
    nested = tmp_path / ".worktrees" / "demo"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("visible\n", encoding="utf-8")
    migration = WorktreesGitignoreBackfillMigration()

    probe = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--quiet", "--no-index", ".worktrees/probe"],
        check=False,
    )
    visible = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--quiet", "--no-index", ".worktrees/demo/file.txt"],
        check=False,
    )
    assert probe.returncode == 0
    assert visible.returncode == 1
    assert migration.detect(tmp_path) is True

    result = migration.apply(tmp_path)

    assert result.success
    assert _read_gitignore(tmp_path).splitlines()[-1] == _WORKTREES_ENTRY
    repaired = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--quiet", "--no-index", ".worktrees/demo/file.txt"],
        check=False,
    )
    assert repaired.returncode == 0


def test_apply_reports_added_entry(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    result = WorktreesGitignoreBackfillMigration().apply(tmp_path)

    assert result.changes_made == [f"Added gitignore entry: {_WORKTREES_ENTRY}"]


def test_dry_run_reports_without_mutating(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    result = WorktreesGitignoreBackfillMigration().apply(tmp_path, dry_run=True)

    assert result.success
    assert result.changes_made == [f"Would add {_WORKTREES_ENTRY} to .gitignore"]
    assert _WORKTREES_ENTRY not in _read_gitignore(tmp_path)


def test_dry_run_reports_no_changes_when_effectively_ignored(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _WORKTREES_ENTRY)

    result = WorktreesGitignoreBackfillMigration().apply(tmp_path, dry_run=True)

    assert result.success
    assert result.changes_made == []


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    first = WorktreesGitignoreBackfillMigration().apply(tmp_path)
    second = WorktreesGitignoreBackfillMigration().apply(tmp_path)

    assert first.success and second.success
    assert second.changes_made == ["gitignore entry already present"]
    assert _read_gitignore(tmp_path).count(_WORKTREES_ENTRY) == 1


@pytest.mark.parametrize("dangling", [False, True])
def test_symlinked_gitignore_is_rejected_without_external_write(tmp_path: Path, dangling: bool) -> None:
    _init_git_repo(tmp_path)
    external = tmp_path.parent / f"worktrees-external-{tmp_path.name}.txt"
    if not dangling:
        external.write_text("outside\n", encoding="utf-8")
    tmp_path.joinpath(".gitignore").symlink_to(external)

    migration = WorktreesGitignoreBackfillMigration()
    assert migration.detect(tmp_path) is True
    ok, reason = migration.can_apply(tmp_path)
    result = migration.apply(tmp_path)

    assert ok is False
    assert "symlink" in reason.lower()
    assert result.success is False
    if dangling:
        assert not external.exists()
    else:
        assert external.read_text(encoding="utf-8") == "outside\n"


def test_invalid_utf8_gitignore_fails_loud(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    tmp_path.joinpath(".gitignore").write_bytes(b"\xff")
    migration = WorktreesGitignoreBackfillMigration()

    assert migration.detect(tmp_path) is True
    ok, reason = migration.can_apply(tmp_path)
    result = migration.apply(tmp_path)

    assert ok is False
    assert "utf-8" in reason.lower()
    assert result.success is False


@pytest.mark.parametrize("root_kind", ["symlink", "file"])
def test_invalid_worktrees_root_fails_loud(tmp_path: Path, root_kind: str) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _WORKTREES_ENTRY)
    root = tmp_path / ".worktrees"
    if root_kind == "symlink":
        external = tmp_path.parent / f"worktrees-root-{tmp_path.name}"
        external.mkdir()
        root.symlink_to(external, target_is_directory=True)
    else:
        root.write_text("not a directory\n", encoding="utf-8")
    migration = WorktreesGitignoreBackfillMigration()

    assert migration.detect(tmp_path) is True
    ok, reason = migration.can_apply(tmp_path)
    result = migration.apply(tmp_path)

    assert ok is False
    assert root_kind in reason.lower() or "not a directory" in reason.lower()
    assert result.success is False


@pytest.mark.parametrize("committed", [False, True], ids=["staged", "committed"])
def test_tracked_worktree_descendant_fails_loud(tmp_path: Path, committed: bool) -> None:
    _init_git_repo(tmp_path)
    nested = tmp_path / ".worktrees" / "demo"
    nested.mkdir(parents=True)
    tracked = nested / "file.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".worktrees/demo/file.txt"], check=True)
    if committed:
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "-c",
                "user.name=Spec Kitty Test",
                "-c",
                "user.email=spec-kitty@example.invalid",
                "commit",
                "-qm",
                "track worktree fixture",
            ],
            check=True,
        )
    migration = WorktreesGitignoreBackfillMigration()

    assert migration.detect(tmp_path) is True
    ok, reason = migration.can_apply(tmp_path)
    result = migration.apply(tmp_path)

    assert ok is False
    assert "tracked paths" in reason.lower()
    assert "git rm -r --cached" in reason
    assert result.success is False
    assert tracked.read_text(encoding="utf-8") == "tracked\n"
    assert not tmp_path.joinpath(".gitignore").exists()


def test_tracked_worktree_recovery_reaches_ignored_state(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    nested = tmp_path / ".worktrees" / "demo"
    nested.mkdir(parents=True)
    tracked = nested / "file.txt"
    tracked.write_text("preserve me\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".worktrees/demo/file.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Spec Kitty Test",
            "-c",
            "user.email=spec-kitty@example.invalid",
            "commit",
            "-qm",
            "track worktree fixture",
        ],
        check=True,
    )
    migration = WorktreesGitignoreBackfillMigration()

    blocked = migration.apply(tmp_path)
    subprocess.run(
        ["git", "-C", str(tmp_path), "rm", "-r", "--cached", "--", ".worktrees"],
        check=True,
    )
    recovered = migration.apply(tmp_path)

    assert blocked.success is False
    assert "rerun `spec-kitty upgrade`" in blocked.errors[0]
    assert recovered.success
    assert tracked.read_text(encoding="utf-8") == "preserve me\n"
    assert (
        subprocess.run(
            ["git", "-C", str(tmp_path), "check-ignore", "--quiet", ".worktrees/demo/file.txt"],
            check=False,
        ).returncode
        == 0
    )


def test_entry_actually_makes_git_ignore_a_worktree(tmp_path: Path) -> None:
    """End to end against real git: after the backfill, a worktree checkout
    under ``.worktrees/`` is invisible to ``git status`` (#3689's observable)."""
    _init_git_repo(tmp_path)

    WorktreesGitignoreBackfillMigration().apply(tmp_path)

    nested = tmp_path / ".worktrees" / "demo-mission-abc123"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("x\n", encoding="utf-8")

    check = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", ".worktrees/demo-mission-abc123/file.txt"],
        check=False,
        capture_output=True,
    )
    assert check.returncode == 0, "expected .worktrees/ contents to be gitignored"

    porcelain = subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert ".worktrees" not in porcelain


def test_backfill_fires_on_already_current_3_2_6rc3_project(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_metadata(tmp_path, "3.2.6rc3")
    _write_gitignore(tmp_path, ".kittify/logs/")  # logs present, .worktrees/ absent

    MigrationRegistry.clear()
    auto_discover_migrations()
    result = MigrationRunner(tmp_path).upgrade("3.2.6rc3", include_worktrees=False)

    assert result.success
    assert WorktreesGitignoreBackfillMigration.migration_id in result.migrations_applied
    assert _WORKTREES_ENTRY in _read_gitignore(tmp_path)
