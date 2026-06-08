"""Tests for RefreshOrientationBlockMigration.

Covers detect/apply/dry_run/idempotency and the two key scenarios:
  1. AGENTS.md stale block → refreshed
  2. Non-AGENTS writer (cursor) stale block → refreshed
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_WORKTREE_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))

import specify_cli.upgrade.migrations.m_3_2_0rc39_refresh_orientation_block  # noqa: F401
from specify_cli.session_presence.content import SECTION_CLOSE, SECTION_OPEN
from specify_cli.upgrade.migrations.m_3_2_0rc39_refresh_orientation_block import (
    RefreshOrientationBlockMigration,
)
from specify_cli.upgrade.registry import MigrationRegistry

# ---------------------------------------------------------------------------
# Stale block fixture — mimics a pre-3.2.0rc39 orientation block
# ---------------------------------------------------------------------------

_OLD_BLOCK = (
    f"{SECTION_OPEN}\n"
    "**Spec Kitty v3.2.0rc38** — project: example (healthy)\n\n"
    "Two usage patterns:\n"
    "- **Full mission** (spec → plan → tasks → implement → review → merge):\n"
    '  trigger: "spec out", "create a mission", "write a spec", "plan this"\n'
    "  → run `/spec-kitty.specify`\n"
    "- **Lightweight dispatch** (ad-hoc fix, question, or advice — no mission created):\n"
    '  trigger: "hey spec kitty", "use spec kitty to", "spec kitty, fix/do/ask/advise"\n'
    '  → run `spec-kitty do "<request verbatim>"`\n'
    f"{SECTION_CLOSE}\n"
)


# ---------------------------------------------------------------------------
# Project factory helpers
# ---------------------------------------------------------------------------


def _make_project(
    tmp_path: Path,
    agents: list[str] | None = None,
    agent_dirs: list[str] | None = None,
) -> Path:
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    avail = agents or []
    lines = (
        "agents:\n  available:\n" + "".join(f"    - {a}\n" for a in avail)
        if avail
        else "agents:\n  available: []\n"
    )
    (tmp_path / ".kittify" / "config.yaml").write_text(lines, encoding="utf-8")
    for d in agent_dirs or []:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _apply_with_mocks(
    migration: RefreshOrientationBlockMigration,
    project_path: Path,
    dry_run: bool = False,
) -> object:
    with (
        patch("specify_cli.session_presence.manager.UpgradeChecker") as mock_checker_cls,
        patch("importlib.metadata.version", return_value="3.2.0rc39"),
        patch("specify_cli.compat.plan", side_effect=Exception("no compat")),
    ):
        mock_checker_cls.return_value.get_available_version.return_value = None
        return migration.apply(project_path, dry_run=dry_run)


def _detect_with_mocks(migration: RefreshOrientationBlockMigration, project_path: Path) -> bool:
    with (
        patch("specify_cli.session_presence.manager.UpgradeChecker") as mock_checker_cls,
        patch("importlib.metadata.version", return_value="3.2.0rc39"),
        patch("specify_cli.compat.plan", side_effect=Exception("no compat")),
    ):
        mock_checker_cls.return_value.get_available_version.return_value = None
        return migration.detect(project_path)


# ---------------------------------------------------------------------------
# TestDetect
# ---------------------------------------------------------------------------


class TestDetect:
    def test_false_when_no_kittify(self, tmp_path: Path) -> None:
        migration = RefreshOrientationBlockMigration()
        assert migration.detect(tmp_path) is False

    def test_false_when_no_presence_installed(self, tmp_path: Path) -> None:
        """Absent blocks are the install migration's job — detect() must be False."""
        project = _make_project(tmp_path, agents=["codex"])
        # No AGENTS.md written → has_presence() is False → not our job
        migration = RefreshOrientationBlockMigration()
        assert _detect_with_mocks(migration, project) is False

    def test_false_when_block_already_current(self, tmp_path: Path) -> None:
        """detect() is False when the installed block already matches render()."""
        project = _make_project(tmp_path, agents=["codex"])
        migration = RefreshOrientationBlockMigration()
        # First write fresh content via apply
        _apply_with_mocks(migration, project)
        # Now detect() must see no staleness
        assert _detect_with_mocks(migration, project) is False

    def test_true_when_agents_md_block_is_stale(self, tmp_path: Path) -> None:
        """detect() is True when AGENTS.md contains an old orientation block."""
        project = _make_project(tmp_path, agents=["codex"])
        (project / "AGENTS.md").write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        assert _detect_with_mocks(migration, project) is True

    def test_true_when_non_agents_writer_block_is_stale(self, tmp_path: Path) -> None:
        """detect() is True when a cursor block contains old orientation content."""
        project = _make_project(tmp_path, agents=["cursor"], agent_dirs=[".cursor"])
        rules_file = project / ".cursor" / "rules" / "spec-kitty.mdc"
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        rules_file.write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        assert _detect_with_mocks(migration, project) is True


# ---------------------------------------------------------------------------
# TestApply
# ---------------------------------------------------------------------------


class TestApply:
    def test_apply_refreshes_stale_agents_md_block(self, tmp_path: Path) -> None:
        """Stale AGENTS.md block is replaced with current content."""
        project = _make_project(tmp_path, agents=["codex"])
        (project / "AGENTS.md").write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        result = _apply_with_mocks(migration, project)

        assert result.success  # type: ignore[union-attr]
        text = (project / "AGENTS.md").read_text(encoding="utf-8")
        assert SECTION_OPEN in text
        # New wording must be present; old single-line dispatch must be gone
        assert "ALWAYS run" in text
        assert "do NOT answer directly" in text
        assert '  → run `spec-kitty do "<request verbatim>"`\n' not in text

    def test_apply_refreshes_stale_non_agents_writer_block(self, tmp_path: Path) -> None:
        """Stale cursor block is replaced with current content."""
        project = _make_project(tmp_path, agents=["cursor"], agent_dirs=[".cursor"])
        rules_file = project / ".cursor" / "rules" / "spec-kitty.mdc"
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        rules_file.write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        result = _apply_with_mocks(migration, project)

        assert result.success  # type: ignore[union-attr]
        text = rules_file.read_text(encoding="utf-8")
        assert "ALWAYS run" in text
        assert "do NOT answer directly" in text

    def test_apply_skips_current_block(self, tmp_path: Path) -> None:
        """apply() is a no-op when the block is already current."""
        project = _make_project(tmp_path, agents=["codex"])
        migration = RefreshOrientationBlockMigration()
        # Write current block
        _apply_with_mocks(migration, project)
        # Second call — nothing stale
        result = _apply_with_mocks(migration, project)
        assert result.success  # type: ignore[union-attr]
        assert result.changes_made == []  # type: ignore[union-attr]

    def test_apply_skips_missing_presence(self, tmp_path: Path) -> None:
        """apply() does not write anything when no block is installed."""
        project = _make_project(tmp_path, agents=["codex"])
        migration = RefreshOrientationBlockMigration()
        result = _apply_with_mocks(migration, project)
        assert result.success  # type: ignore[union-attr]
        assert result.changes_made == []  # type: ignore[union-attr]
        assert not (project / "AGENTS.md").exists()

    def test_apply_dry_run_no_filesystem_changes(self, tmp_path: Path) -> None:
        """dry_run=True reports pending refreshes but writes nothing."""
        project = _make_project(tmp_path, agents=["codex"])
        (project / "AGENTS.md").write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        result = _apply_with_mocks(migration, project, dry_run=True)
        assert result.success  # type: ignore[union-attr]
        assert len(result.changes_made) >= 1  # type: ignore[union-attr]
        # File must be unchanged
        assert (project / "AGENTS.md").read_text(encoding="utf-8") == _OLD_BLOCK

    def test_apply_dry_run_change_describes_harness(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, agents=["codex"])
        (project / "AGENTS.md").write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        result = _apply_with_mocks(migration, project, dry_run=True)
        assert any("codex" in change for change in result.changes_made)  # type: ignore[union-attr]

    def test_apply_idempotent(self, tmp_path: Path) -> None:
        """Applying twice on a stale block leaves exactly one orientation section."""
        project = _make_project(tmp_path, agents=["codex"])
        (project / "AGENTS.md").write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        _apply_with_mocks(migration, project)
        _apply_with_mocks(migration, project)
        text = (project / "AGENTS.md").read_text(encoding="utf-8")
        assert text.count(SECTION_OPEN) == 1

    def test_apply_returns_change_entry_per_stale_key(self, tmp_path: Path) -> None:
        """apply() reports one change entry per refreshed harness key."""
        project = _make_project(tmp_path, agents=["codex"])
        (project / "AGENTS.md").write_text(_OLD_BLOCK, encoding="utf-8")
        migration = RefreshOrientationBlockMigration()
        result = _apply_with_mocks(migration, project)
        assert len(result.changes_made) == 1  # type: ignore[union-attr]
        assert "codex" in result.changes_made[0]  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# TestMigrationAttributes
# ---------------------------------------------------------------------------


class TestMigrationAttributes:
    def test_migration_id(self) -> None:
        assert RefreshOrientationBlockMigration.migration_id == "3_2_0rc39_refresh_orientation_block"

    def test_runs_on_worktrees_is_false(self) -> None:
        assert RefreshOrientationBlockMigration.runs_on_worktrees is False

    def test_target_version(self) -> None:
        assert RefreshOrientationBlockMigration.target_version == "3.2.0rc39"

    def test_migration_registered_in_registry(self) -> None:
        migration_ids = {m.migration_id for m in MigrationRegistry.get_all()}
        assert "3_2_0rc39_refresh_orientation_block" in migration_ids
