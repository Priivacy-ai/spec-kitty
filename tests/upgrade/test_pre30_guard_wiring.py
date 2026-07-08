"""WP02 acceptance tests: boundary guard wired into command entrypoints.

Verifies IC-02 / IC-03 from the pre30-guard-contract:
- Pre-3.0 fixture passed to a wired command → exit 1 + "Pre-3.0 layout detected"
  + "spec-kitty upgrade" (hard-reject, no mutation).
- Post-3.0 fixture passes the guard without raising / exiting early.

Covers:
- agent/tasks.py: move-task, mark-status, add-history, finalize-tasks,
  map-requirements, validate-workflow, list-dependents
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SLUG = "test-mission-01KW0MJE"


def _pre30_feature(tmp_path: Path) -> Path:
    """Return a pre-3.0 mission dir: tasks/planned/WP01.md exists."""
    fd = tmp_path / "kitty-specs" / _SLUG
    (fd / "tasks" / "planned").mkdir(parents=True)
    (fd / "tasks" / "planned" / "WP01.md").write_text(
        "---\nwork_package_id: WP01\n---\n", encoding="utf-8"
    )
    return fd


def _post30_feature(tmp_path: Path) -> Path:
    """Return a post-3.0 mission dir: tasks/WP01.md at flat level."""
    fd = tmp_path / "kitty-specs" / _SLUG
    (fd / "tasks").mkdir(parents=True)
    (fd / "tasks" / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\n---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    (fd / "meta.json").write_text(
        json.dumps({"mission_id": "01KW0MJE000000000000000000"}), encoding="utf-8"
    )
    return fd


def _base_patches(tmp_path: Path, feature_dir: Path):
    """Context manager providing the standard env patches for agent/tasks tests."""
    from contextlib import ExitStack, contextmanager

    @contextmanager
    def _ctx():
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "specify_cli.cli.commands.agent.tasks.locate_project_root",
                    return_value=tmp_path,
                )
            )
            stack.enter_context(
                patch(
                    "specify_cli.cli.commands.agent.tasks.get_status_read_root",
                    return_value=tmp_path,
                )
            )
            stack.enter_context(
                patch(
                    "specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out",
                    return_value=(tmp_path, "main"),
                )
            )
            stack.enter_context(
                patch(
                    "specify_cli.cli.commands.agent.tasks._find_mission_slug",
                    return_value=_SLUG,
                )
            )
            stack.enter_context(
                patch(
                    "specify_cli.cli.commands.agent.tasks.get_auto_commit_default",
                    return_value=False,
                )
            )
            # read-surface-ssot-closeout WP08 / FR-001: the kind-blind
            # ``tasks.resolve_feature_dir_for_mission`` module export is retired —
            # the STATUS-partition reads that used it (``validate-workflow``,
            # ``finalize-tasks`` via ``_ft_apply_writes``) now route through
            # ``mission_runtime.placement_seam(...).read_dir(STATUS_STATE)``, a
            # module-scope import in BOTH ``tasks.py`` and ``tasks_finalize.py`` —
            # two separate bindings, so a single generic stub can no longer
            # intercept both call sites here. ``feature_dir`` is a REAL directory
            # on ``tmp_path`` (``_post30_feature`` / ``_pre30_feature`` write it to
            # disk), and this fixture's mission carries no ``-coord`` worktree /
            # ``coordination_branch`` — so the real topology-aware seam resolves
            # the SAME primary dir the retired mock used to return. No stub needed
            # (mirrors the WP05 ``implement.py`` precedent of dropping the stub
            # once the seam is topology-blind for the fixture under test).
            stack.enter_context(
                patch(
                    "specify_cli.cli.commands.agent.tasks._map_requirements_feature_dir",
                    return_value=feature_dir,
                )
            )
            yield

    return _ctx()


# ---------------------------------------------------------------------------
# agent/tasks.py — move-task
# ---------------------------------------------------------------------------


class TestMoveTaskGuard:
    def test_rejects_pre30_project(self, tmp_path: Path) -> None:
        """Pre-3.0 layout causes move-task to exit 1 with guard message (IC-02)."""
        fd = _pre30_feature(tmp_path)
        with _base_patches(tmp_path, fd):
            result = runner.invoke(
                app, ["move-task", "WP01", "--to", "doing", "--json"]
            )
        assert result.exit_code == 1
        assert "Pre-3.0 layout detected" in result.stdout + result.stderr

    def test_passes_post30_project(self, tmp_path: Path) -> None:
        """Post-3.0 layout does not trigger the guard (no guard message)."""
        fd = _post30_feature(tmp_path)
        with _base_patches(tmp_path, fd):
            # The command may fail for other reasons (no events, etc.) but guard
            # must not fire.
            result = runner.invoke(
                app, ["move-task", "WP01", "--to", "doing", "--json"]
            )
        assert "Pre-3.0 layout detected" not in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# agent/tasks.py — mark-status
# ---------------------------------------------------------------------------


class TestMarkStatusGuard:
    def test_rejects_pre30_project(self, tmp_path: Path) -> None:
        """Pre-3.0 layout causes mark-status to exit 1 with guard message (IC-02)."""
        fd = _pre30_feature(tmp_path)
        with _base_patches(tmp_path, fd), patch(
            "specify_cli.cli.commands.agent.tasks.feature_status_lock",
            side_effect=AssertionError("guard should fire before lock"),
        ):
            result = runner.invoke(
                app,
                ["mark-status", "T001", "--status", "done", "--json", "--no-auto-commit"],
            )
        assert result.exit_code == 1
        assert "Pre-3.0 layout detected" in result.stdout + result.stderr

    def test_passes_post30_project(self, tmp_path: Path) -> None:
        """Post-3.0 layout does not trigger the guard."""
        fd = _post30_feature(tmp_path)
        # Write a minimal tasks.md so mark-status can try to proceed
        (fd / "tasks.md").write_text("# Tasks\n\n## WP01\n- [ ] T001\n", encoding="utf-8")
        with _base_patches(tmp_path, fd), patch(
            "specify_cli.cli.commands.agent.tasks.feature_status_lock",
            new_callable=MagicMock,
        ) as mock_lock:
            mock_lock.return_value.__enter__ = MagicMock(return_value=None)
            mock_lock.return_value.__exit__ = MagicMock(return_value=False)
            result = runner.invoke(
                app,
                ["mark-status", "T001", "--status", "done", "--json", "--no-auto-commit"],
            )
        assert "Pre-3.0 layout detected" not in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# agent/tasks.py — add-history
# ---------------------------------------------------------------------------


class TestAddHistoryGuard:
    def test_rejects_pre30_project(self, tmp_path: Path) -> None:
        """Pre-3.0 layout causes add-history to exit 1 with guard message (IC-02)."""
        fd = _pre30_feature(tmp_path)
        with _base_patches(tmp_path, fd):
            result = runner.invoke(
                app,
                ["add-history", "WP01", "--note", "test note", "--json"],
            )
        assert result.exit_code == 1
        assert "Pre-3.0 layout detected" in result.stdout + result.stderr

    def test_passes_post30_project(self, tmp_path: Path) -> None:
        """Post-3.0 layout does not trigger the guard."""
        fd = _post30_feature(tmp_path)
        with _base_patches(tmp_path, fd), patch(
            "specify_cli.cli.commands.agent.tasks.locate_work_package"
        ) as mock_lwp, patch(
            "specify_cli.cli.commands.agent.tasks.emit_history_added"
        ):
            mock_lwp.return_value = MagicMock(
                frontmatter={"work_package_id": "WP01"},
                body="## Activity Log\n",
                padding="",
                path=fd / "tasks" / "WP01.md",
            )
            result = runner.invoke(
                app,
                ["add-history", "WP01", "--note", "test note", "--json"],
            )
        assert "Pre-3.0 layout detected" not in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# agent/tasks.py — finalize-tasks
# ---------------------------------------------------------------------------


class TestFinalizeTasksGuard:
    def test_rejects_pre30_project(self, tmp_path: Path) -> None:
        """Pre-3.0 layout causes finalize-tasks to exit 1 with guard message (IC-02)."""
        fd = _pre30_feature(tmp_path)
        with _base_patches(tmp_path, fd):
            result = runner.invoke(
                app, ["finalize-tasks", "--mission", _SLUG, "--json"]
            )
        assert result.exit_code == 1
        assert "Pre-3.0 layout detected" in result.stdout + result.stderr

    def test_passes_post30_project(self, tmp_path: Path) -> None:
        """Post-3.0 layout does not trigger the guard."""
        fd = _post30_feature(tmp_path)
        # Provide a minimal tasks.md so finalize-tasks can proceed past the guard
        (fd / "tasks.md").write_text("# Tasks\n\n## WP01\n\nNo explicit dependencies.\n", encoding="utf-8")
        with _base_patches(tmp_path, fd):
            result = runner.invoke(
                app, ["finalize-tasks", "--mission", _SLUG, "--json"]
            )
        assert "Pre-3.0 layout detected" not in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# agent/tasks.py — validate-workflow
# ---------------------------------------------------------------------------


class TestValidateWorkflowGuard:
    def test_rejects_pre30_project(self, tmp_path: Path) -> None:
        """Pre-3.0 layout causes validate-workflow to exit 1 with guard message (IC-02)."""
        fd = _pre30_feature(tmp_path)
        with _base_patches(tmp_path, fd):
            result = runner.invoke(
                app, ["validate-workflow", "WP01", "--json"]
            )
        assert result.exit_code == 1
        assert "Pre-3.0 layout detected" in result.stdout + result.stderr

    def test_passes_post30_project(self, tmp_path: Path) -> None:
        """Post-3.0 layout does not trigger the guard."""
        fd = _post30_feature(tmp_path)
        with _base_patches(tmp_path, fd), patch(
            "specify_cli.cli.commands.agent.tasks.locate_work_package"
        ) as mock_lwp:
            mock_lwp.return_value = MagicMock(
                frontmatter={"work_package_id": "WP01", "title": "Test"},
                body="## Activity Log\n",
                path=fd / "tasks" / "WP01.md",
            )
            result = runner.invoke(
                app, ["validate-workflow", "WP01", "--json"]
            )
        assert "Pre-3.0 layout detected" not in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# agent/tasks.py — list-dependents
# ---------------------------------------------------------------------------


class TestListDependentsGuard:
    def test_rejects_pre30_project(self, tmp_path: Path) -> None:
        """Pre-3.0 layout causes list-dependents to exit 1 with guard message (IC-02)."""
        fd = _pre30_feature(tmp_path)
        with _base_patches(tmp_path, fd):
            result = runner.invoke(
                app, ["list-dependents", "WP01", "--json"]
            )
        assert result.exit_code == 1
        assert "Pre-3.0 layout detected" in result.stdout + result.stderr

    def test_passes_post30_project(self, tmp_path: Path) -> None:
        """Post-3.0 layout does not trigger the guard."""
        fd = _post30_feature(tmp_path)
        with _base_patches(tmp_path, fd), patch(
            "specify_cli.cli.commands.agent.tasks.build_dependency_graph",
            return_value={},
        ), patch(
            "specify_cli.cli.commands.agent.tasks.get_dependents",
            return_value=[],
        ), patch(
            "specify_cli.cli.commands.agent.tasks.locate_work_package",
            side_effect=FileNotFoundError,
        ):
            result = runner.invoke(
                app, ["list-dependents", "WP01", "--json"]
            )
        assert "Pre-3.0 layout detected" not in result.stdout + result.stderr


# NOTE: the standalone ``tasks_cli`` guard classes (update_command / list_command /
# history_command) were retired with the standalone tasks surface (WP03/FR-004).
# The canonical pre-3.0 boundary guard is exercised through the live
# ``agent/tasks.py`` command entrypoints above and below (move-task, mark-status,
# add-history, finalize-tasks, validate-workflow, list-dependents,
# map-requirements), which share the same ``check_pre30_layout`` guard.


# ---------------------------------------------------------------------------
# agent/tasks.py — map-requirements
# ---------------------------------------------------------------------------


class TestMapRequirementsGuard:
    def test_rejects_pre30_project(self, tmp_path: Path) -> None:
        """Pre-3.0 layout causes map-requirements to exit 1 with guard message (IC-02)."""
        fd = _pre30_feature(tmp_path)
        with _base_patches(tmp_path, fd):
            result = runner.invoke(
                app,
                ["map-requirements", "--wp", "WP01", "--refs", "FR-001"],
            )
        assert result.exit_code == 1
        assert "Pre-3.0 layout detected" in result.stdout + result.stderr

    def test_passes_post30_project(self, tmp_path: Path) -> None:
        """Post-3.0 layout does not trigger the guard."""
        fd = _post30_feature(tmp_path)
        with _base_patches(tmp_path, fd), patch(
            "specify_cli.cli.commands.agent.tasks.primary_feature_dir_for_mission",
            return_value=fd,
        ):
            result = runner.invoke(
                app,
                ["map-requirements", "--wp", "WP01", "--refs", "FR-001"],
            )
        assert "Pre-3.0 layout detected" not in result.stdout + result.stderr


# NOTE: ``TestTasksCliHistoryCommandGuard`` (standalone ``tasks_cli.history_command``)
# was retired with the standalone tasks surface (WP03/FR-004). The canonical
# ``add-history`` guard is covered by ``TestAddHistoryGuard`` above.
