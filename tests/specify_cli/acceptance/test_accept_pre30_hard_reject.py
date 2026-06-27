"""Regression: the acceptance/verify/merge surface hard-rejects pre-3.0 layout.

Squad review (PR #2168, Blocker 1 / #1057) found a silent regression: retiring
the pre-3.0 readers made the acceptance engine *warn-and-skip* a pre-3.0
(legacy lane-directory) mission. ``_iter_work_packages`` then yielded ZERO work
packages, so ``AcceptanceSummary.all_done`` was **vacuously True** and ``accept``
auto-committed an unmigrated mission whose real WPs still sat in
``tasks/planned/`` — "all acceptance checks passed" on un-done work.

These tests pin the contract: a pre-3.0 mission reaching the accept / verify /
merge surface must **exit 1** with the ``spec-kitty upgrade`` migration message
and write **nothing** (no acceptance commit), matching the guarded task
commands. The engine-level test pins the same hard reject at
``collect_feature_summary`` so accept AND verify inherit it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.acceptance import collect_feature_summary
from specify_cli.scripts.tasks import tasks_cli
from specify_cli.status import Lane
from specify_cli.status.models import StatusEvent
from specify_cli.status.store import append_event
from specify_cli.upgrade.pre30_guard import Pre30LayoutError

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_SLUG = "099-legacy-pre30-mission"
_UPGRADE_HINT = "spec-kitty upgrade"
_GUARD_MARKER = "Pre-3.0 layout detected"


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _pre30_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real git repo whose mission uses the pre-3.0 lane-directory layout.

    The mission carries the full acceptance surface — spec/plan/tasks present, a
    ``status.events.jsonl`` showing WP01 ``done``, and NO ``lanes.json`` — so that
    WITHOUT the guard the summary is vacuously ``all_done`` and ``accept`` would
    auto-commit. The work package itself lives in ``tasks/planned/WP01.md`` (the
    legacy lane directory the retired reader no longer sees).
    """
    repo = tmp_path / "repo"
    fd = repo / "kitty-specs" / _SLUG
    (fd / "tasks" / "planned").mkdir(parents=True)

    (fd / "tasks" / "planned" / "WP01.md").write_text(
        "---\nwork_package_id: WP01\nagent: claude\nshell_pid: '12345'\n"
        "assignee: pedro\ntitle: Legacy work package\n---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    (fd / "spec.md").write_text("# Spec\n\nReal spec content.\n", encoding="utf-8")
    (fd / "plan.md").write_text("# Plan\n\nReal plan content.\n", encoding="utf-8")
    (fd / "tasks.md").write_text("# Tasks\n\n## WP01\n\nNo unchecked checkboxes.\n", encoding="utf-8")
    (fd / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01KW0LEGACY0000000000000099",
                "mission_slug": _SLUG,
                "friendly_name": "Legacy pre-3.0 mission",
                "target_branch": "main",
            }
        ),
        encoding="utf-8",
    )
    append_event(
        fd,
        StatusEvent(
            event_id="01KW0LEGACYEVENT0000000001",
            mission_slug=_SLUG,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at="2026-06-26T00:00:00+00:00",
            actor="claude",
            force=False,
            execution_mode="direct_repo",
            mission_id="01KW0LEGACY0000000000000099",
        ),
    )

    _run_git(repo, "init", "-q")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-qm", "seed legacy mission")
    return repo, fd


def _head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


# ---------------------------------------------------------------------------
# Engine: collect_feature_summary must hard-reject, never vacuously pass
# ---------------------------------------------------------------------------


def test_collect_feature_summary_rejects_pre30(tmp_path: Path) -> None:
    """The acceptance engine raises Pre30LayoutError for a pre-3.0 mission.

    Before the fix the engine warn-skipped, returning a vacuously ``all_done``
    summary (``ok``) that let ``accept`` commit an unmigrated mission.
    """
    repo, fd = _pre30_repo(tmp_path)
    with (
        patch(
            "specify_cli.acceptance.resolve_feature_dir_for_mission",
            return_value=fd,
        ),
        patch(
            "specify_cli.acceptance._primary_anchor_feature_dir",
            return_value=fd,
        ),
        pytest.raises(Pre30LayoutError) as exc_info,
    ):
        collect_feature_summary(repo, _SLUG)
    message = str(exc_info.value)
    assert _GUARD_MARKER in message
    assert _UPGRADE_HINT in message


# ---------------------------------------------------------------------------
# accept: exit 1 + migration message + NO acceptance commit
# ---------------------------------------------------------------------------


def _accept_args() -> argparse.Namespace:
    return argparse.Namespace(
        feature=_SLUG,
        mode="local",
        actor=None,
        test=None,
        json=False,
        lenient=False,
        no_commit=False,
        allow_fail=False,
        normalize_encoding=False,
    )


def test_accept_command_hard_rejects_pre30_and_commits_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, fd = _pre30_repo(tmp_path)
    head_before = _head(repo)

    with (
        patch.object(tasks_cli, "find_repo_root", return_value=repo),
        patch.object(tasks_cli, "resolve_feature_dir_for_mission", return_value=fd),
        pytest.raises(SystemExit) as exc_info,
    ):
        tasks_cli.accept_command(_accept_args())

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert _GUARD_MARKER in err
    assert _UPGRADE_HINT in err

    # No acceptance commit was created and no acceptance metadata was recorded.
    assert _head(repo) == head_before
    meta = json.loads((fd / "meta.json").read_text(encoding="utf-8"))
    assert "accepted_at" not in meta
    assert "acceptance_history" not in meta


# ---------------------------------------------------------------------------
# verify: exit 1 + migration message
# ---------------------------------------------------------------------------


def test_verify_command_hard_rejects_pre30(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, fd = _pre30_repo(tmp_path)
    args = argparse.Namespace(
        feature=_SLUG, json=False, lenient=False, normalize_encoding=False
    )
    with (
        patch.object(tasks_cli, "find_repo_root", return_value=repo),
        patch.object(tasks_cli, "resolve_feature_dir_for_mission", return_value=fd),
        pytest.raises(SystemExit) as exc_info,
    ):
        tasks_cli.verify_command(args)
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert _GUARD_MARKER in err
    assert _UPGRADE_HINT in err


# ---------------------------------------------------------------------------
# merge: exit 1 + migration message + NO merge commit
# ---------------------------------------------------------------------------


def test_merge_command_hard_rejects_pre30(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, fd = _pre30_repo(tmp_path)
    # merge_command requires HEAD on the feature branch (!= target).
    _run_git(repo, "branch", "-m", "main")
    _run_git(repo, "checkout", "-q", "-b", _SLUG)
    head_before = _head(repo)
    monkeypatch.chdir(repo)

    args = argparse.Namespace(
        feature=_SLUG,
        strategy="merge",
        target="main",
        push=False,
        delete_branch=False,
        remove_worktree=False,
        dry_run=False,
    )
    with (
        patch.object(tasks_cli, "find_repo_root", return_value=repo),
        patch.object(tasks_cli, "resolve_feature_dir_for_mission", return_value=fd),
        pytest.raises(SystemExit) as exc_info,
    ):
        tasks_cli.merge_command(args)
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert _GUARD_MARKER in err
    assert _UPGRADE_HINT in err
    # Still on the feature branch with no merge performed.
    assert _head(repo) == head_before
