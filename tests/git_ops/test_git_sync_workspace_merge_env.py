"""Issue #106: ``GitVCS.sync_workspace``'s rebase must resolve ``spec-kitty``
without the CLI being on the ambient PATH.

Same defect class as #87 (``tests/lanes/test_worktree_allocator_merge_env.py``),
one subsystem over: ``sync_workspace`` (``core/vcs/git.py``) ran
``git -C <workspace> rebase <base_branch>`` via ``subprocess.run`` with no
``env=``. A rebase replays commits through git's three-way merge machinery,
which honors custom merge drivers registered in ``.gitattributes``/gitconfig
(``merge.spec-kitty-event-log.driver = spec-kitty merge-driver-event-log %O
%B %A`` on ``kitty-specs/**/status.events.jsonl``). Under a stripped PATH
(absolute-path invocation, wrapper, agent harness) an add/add divergence on
``status.events.jsonl`` that the driver would reconcile instead makes the
driver exit 127, and ``sync_workspace`` reports spurious CONFLICTS.

The fix routes the rebase (and its ``--abort`` fallback) through
``lanes/merge.py::_make_merge_env``, which prepends THIS interpreter's venv
bin dir to the subprocess PATH. This test strips that directory from PATH
entirely and drives the real ``sync_workspace`` entry point: pre-fix it
returns ``SyncStatus.CONFLICTS``, post-fix the union driver reconciles the
add/add divergence and BOTH sides' events survive — proving the driver
actually fired via the routed env, not merely that no exception was raised.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.core.vcs.git import GitVCS
from specify_cli.core.vcs.types import SyncStatus
from specify_cli.lanes.merge import _ensure_merge_driver_git_config

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

MISSION_SLUG = "issue-106-sync-workspace-merge-env"
_EVENT_LOG_GITATTRIBUTES_ENTRY = "kitty-specs/**/status.events.jsonl merge=spec-kitty-event-log"
_EXPECTED_DRIVER_COMMAND = "spec-kitty merge-driver-event-log %O %A %B"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write_status_event(feature_dir: Path, *, event_id: str, at: str) -> None:
    events_path = feature_dir / "status.events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"event_id": event_id, "at": at, "kind": "wp_status_transition"}
    events_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _strip_this_venvs_spec_kitty_from_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove THIS interpreter's venv bin dir from the process PATH.

    This is the exact condition under which #106 (and #87) reproduces: the
    ambient PATH cannot resolve ``spec-kitty`` (nor any other copy of it —
    asserted below), so only ``_make_merge_env()``'s prepend can put the CLI
    where git's driver invocation finds it.
    """
    venv_bin = Path(sys.executable).parent
    kept = [
        entry
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry and Path(entry) != venv_bin and Path(entry).resolve() != venv_bin.resolve()
    ]
    monkeypatch.setenv("PATH", os.pathsep.join(kept))

    assert shutil.which("git") is not None, (
        "test setup broken: git itself must stay resolvable after stripping the venv bin dir, "
        "or the scenario does not model #106"
    )
    assert shutil.which("spec-kitty") is None, (
        "test setup invariant violated: spec-kitty still resolves on the "
        f"stripped PATH ({os.environ['PATH']!r}), so this test can no longer "
        "tell the fix apart from a no-op"
    )


class TestSyncWorkspaceRebaseResolvesDriverWithoutCliOnPath:
    def test_sync_workspace_reconciles_add_add_divergence_with_stripped_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@example.com")
        _git(repo, "config", "user.name", "Test")
        _git(repo, "config", "commit.gpgsign", "false")
        (repo / ".gitattributes").write_text(_EVENT_LOG_GITATTRIBUTES_ENTRY + "\n", encoding="utf-8")
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        _git(repo, "add", ".gitattributes", "seed.txt")
        _git(repo, "commit", "-q", "-m", "seed (spec-kitty init shape)")

        # A real workspace would have been allocated via worktree_allocator,
        # which self-heals this git-config; register it directly here so this
        # test isolates the env-routing defect (#106), same as #87's test.
        _ensure_merge_driver_git_config(repo)

        feature_dir = repo / "kitty-specs" / MISSION_SLUG

        # feature branch independently ADDS status.events.jsonl.
        _git(repo, "checkout", "-q", "-b", "feature")
        _write_status_event(feature_dir, event_id="evt-feature", at="2026-08-25T09:00:00Z")
        _git(repo, "add", "kitty-specs")
        _git(repo, "commit", "-q", "-m", "status: feature event")

        # main independently ADDS the SAME path with DIFFERENT content — the
        # add/add divergence only the union driver reconciles.
        _git(repo, "checkout", "-q", "main")
        _write_status_event(feature_dir, event_id="evt-main", at="2026-08-25T08:00:00Z")
        _git(repo, "add", "kitty-specs")
        _git(repo, "commit", "-q", "-m", "status: main event")

        _git(repo, "checkout", "-q", "feature")
        _strip_this_venvs_spec_kitty_from_path(monkeypatch)

        result = GitVCS().sync_workspace(repo)

        assert result.status == SyncStatus.SYNCED, (
            f"expected the rebase to reconcile via the union driver, got "
            f"{result.status!r}: {result.message!r}"
        )

        post_check = _git(repo, "config", "--get", "merge.spec-kitty-event-log.driver")
        assert post_check == _EXPECTED_DRIVER_COMMAND

        merged_text = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")
        assert "evt-main" in merged_text, f"main-branch event lost from the merged log: {merged_text!r}"
        assert "evt-feature" in merged_text, f"feature-branch event lost from the merged log: {merged_text!r}"
