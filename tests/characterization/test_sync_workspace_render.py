"""WP11 monkeypatch-golden for the ``spec-kitty sync workspace`` render (T021).

``sync_workspace`` is the third ``# noqa: C901`` monster (measured complexity 18).
Unlike ``status``/``doctor`` it has **no** pre-existing WP02 golden, and its
substantive SYNCED / CONFLICTS / FAILED arms run a **live ``git rebase``** against a
black-box snapshot — non-deterministic. So this is a *genuine freeze* (pedro Pd-4),
not a verify: it stubs the two seams the command consumes — ``sync.get_vcs`` and
``sync._detect_workspace_context`` — to return **fixed** :class:`SyncResult`s, so no
real rebase ever runs, then snapshots the full render **including the emoji glyphs**
(``✓`` / ``⚠`` / ``✗``) with the capture encoding pinned to UTF-8. It also freezes
the ``mission_slug is None`` → exit-1 arm.

The stubs target the same late-bound module attributes the T022 restructure
preserves (INV-4), so this golden stays green **before and after** the extraction.
It touches no DIR-041 ratchet (C-003).

NB: ``sync_workspace`` contains **no** daemon read/guard code — the
``_require_daemon_owner_coherence`` guard lives on the ``share``/``unshare``/
``opt-in``/``opt-out`` commands, not here — so the C-004 "relocate the daemon guard
intact" constraint is vacuously satisfied for this WP; there is nothing to move.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import Result
from typer.testing import CliRunner

import specify_cli.cli.commands.sync as sync
from specify_cli.cli.commands.sync import app
from specify_cli.core.vcs import ChangeInfo, ConflictInfo, SyncResult, SyncStatus
from specify_cli.core.vcs.types import ConflictType
from kernel.clock import now_utc

runner = CliRunner()


@pytest.fixture(autouse=True)
def _hermetic_sync_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the CORRECT SaaS-enable var + HOME/XDG isolation + wide UTF-8 capture.

    Mirrors the WP02 harness (``test_sync_cli_safe.py``): ``chdir`` into a fresh
    non-repo directory, isolate ``HOME``/``XDG_*``, pin ``PYTHONIOENCODING=utf-8``
    so the ``✓``/``⚠``/``✗`` glyphs are byte-stable, and force a wide console so
    Rich never soft-wraps a line.
    """
    home = tmp_path / "home"
    for sub in ("", "cfg", "data", "state", "cache", "AppData"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / "cache"))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "AppData"))
    monkeypatch.delenv("SPEC_KITTY_SAAS_SYNC", raising=False)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setenv("COLUMNS", "1000")
    monkeypatch.chdir(tmp_path)


def invoke(*args: str) -> Result:
    """Drive the ``sync`` app in-process and return the click ``Result``."""
    return runner.invoke(app, list(args))


class _FakeVCS:
    """A ``get_vcs`` stand-in whose ``sync_workspace`` returns a fixed result.

    This is the whole point of the monkeypatch-golden: the fixed ``SyncResult``
    replaces the live ``git rebase`` so each arm's render is deterministic.
    """

    def __init__(self, result: SyncResult) -> None:
        self._result = result

    def sync_workspace(self, workspace_path: Path) -> SyncResult:
        return self._result


def _stub_workspace(
    monkeypatch: pytest.MonkeyPatch,
    *,
    result: SyncResult | None,
    mission_slug: str | None = "042-demo",
) -> None:
    """Stub the two seams so no real rebase runs.

    ``_detect_workspace_context`` yields a fixed ``(path, mission_slug)`` and
    ``get_vcs`` yields a :class:`_FakeVCS` bound to ``result``. Both are patched as
    ``sync.<name>`` module attributes — the exact late-bound seam the T022
    restructure keeps reachable (INV-4).
    """
    workspace_path = Path("/tmp/.worktrees/042-demo-lane-a")
    monkeypatch.setattr(sync, "_detect_workspace_context", lambda: (workspace_path, mission_slug))
    if result is not None:
        monkeypatch.setattr(sync, "get_vcs", lambda *a, **k: _FakeVCS(result))


def _change(commit_id: str, message: str) -> ChangeInfo:
    return ChangeInfo(
        change_id=None,
        commit_id=commit_id,
        message=message,
        message_full=message,
        author="Ada",
        author_email="ada@example.com",
        timestamp=now_utc(),
        parents=[],
        is_merge=False,
        is_conflicted=False,
        is_empty=False,
    )


def _conflict(path: str) -> ConflictInfo:
    return ConflictInfo(
        file_path=Path(path),
        conflict_type=ConflictType.CONTENT,
        line_ranges=[(10, 20)],
        sides=2,
        is_resolved=False,
        our_content="ours",
        their_content="theirs",
        base_content=None,
    )


def _result(status: SyncStatus, **overrides: Any) -> SyncResult:
    base: dict[str, Any] = {
        "status": status,
        "conflicts": [],
        "files_updated": 0,
        "files_added": 0,
        "files_deleted": 0,
        "changes_integrated": [],
        "message": "",
    }
    base.update(overrides)
    return SyncResult(**base)


# ---------------------------------------------------------------------------
# mission_slug is None → exit 1 (the "not in a workspace" arm)
# ---------------------------------------------------------------------------


def test_mission_slug_none_exits_1_with_workspace_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_workspace(monkeypatch, result=None, mission_slug=None)
    result = invoke("workspace")
    assert result.exit_code == 1
    assert "⚠ Not in a recognized workspace" in result.output
    assert "Run this command from a worktree directory:" in result.output
    assert ".worktrees/" in result.output


# ---------------------------------------------------------------------------
# SYNCED arm (emoji glyph frozen)
# ---------------------------------------------------------------------------


def test_synced_arm_renders_check_glyph_and_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_workspace(
        monkeypatch,
        result=_result(
            SyncStatus.SYNCED,
            files_updated=3,
            files_added=1,
            files_deleted=2,
            message="Fast-forwarded 4 commits",
        ),
    )
    result = invoke("workspace")
    assert result.exit_code == 0
    assert "✓ Synced" in result.output
    assert "3 updated, 1 added, 2 deleted" in result.output
    assert "Fast-forwarded 4 commits" in result.output
    # Non-verbose: integrated-changes block is not shown.
    assert "Changes integrated" not in result.output


def test_synced_arm_no_file_changes_renders_default_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_workspace(monkeypatch, result=_result(SyncStatus.SYNCED))
    result = invoke("workspace")
    assert result.exit_code == 0
    assert "✓ Synced" in result.output
    assert "no file changes" in result.output


def test_synced_arm_verbose_shows_integrated_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_workspace(
        monkeypatch,
        result=_result(
            SyncStatus.SYNCED,
            files_updated=1,
            changes_integrated=[_change("abcdef1234567", "add feature core")],
        ),
    )
    result = invoke("workspace", "--verbose")
    assert result.exit_code == 0
    assert "✓ Synced" in result.output
    assert "Changes integrated (1)" in result.output
    assert "abcdef1" in result.output


# ---------------------------------------------------------------------------
# CONFLICTS arm (emoji glyph frozen)
# ---------------------------------------------------------------------------


def test_conflicts_arm_renders_warning_glyph_and_table(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_workspace(
        monkeypatch,
        result=_result(
            SyncStatus.CONFLICTS,
            conflicts=[_conflict("src/app.py")],
        ),
    )
    result = invoke("workspace")
    assert result.exit_code == 0
    assert "⚠ Synced with conflicts" in result.output
    assert "You must resolve conflicts before continuing." in result.output
    assert "src/app.py" in result.output
    assert "Conflicts (1 files)" in result.output


# ---------------------------------------------------------------------------
# FAILED arm (emoji glyph frozen + exit 1)
# ---------------------------------------------------------------------------


def test_failed_arm_renders_cross_glyph_and_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_workspace(
        monkeypatch,
        result=_result(
            SyncStatus.FAILED,
            message="rebase aborted: unmerged paths",
            conflicts=[_conflict("src/broken.py")],
        ),
    )
    result = invoke("workspace")
    assert result.exit_code == 1
    assert "✗ Sync failed" in result.output
    assert "rebase aborted: unmerged paths" in result.output
    assert "src/broken.py" in result.output
    assert "spec-kitty sync workspace --repair" in result.output


# ---------------------------------------------------------------------------
# UP_TO_DATE arm (no glyph regression + exit 0)
# ---------------------------------------------------------------------------


def test_up_to_date_arm_renders_already_up_to_date(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_workspace(
        monkeypatch,
        result=_result(SyncStatus.UP_TO_DATE, message="Already at tip"),
    )
    result = invoke("workspace")
    assert result.exit_code == 0
    assert "✓ Already up to date" in result.output
    assert "Already at tip" in result.output
