"""Transactional status-transition integration tests for issue #1356."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from specify_cli.coordination.status_transition import emit_status_transition_transactional
from specify_cli.coordination.transaction import BookkeepingCommitFailed, BookkeepingWorktreeMissing
from specify_cli.status.models import TransitionRequest

pytest_plugins = ("tests.conftest_saas_sink",)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "status-transaction"
MID8 = "01KT1356"
MISSION_ID = "01KT1356000000000000000000"
MISSION_DIRNAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIRNAME}"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.invalid")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    feature_dir = r / "kitty-specs" / MISSION_DIRNAME
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "coordination_branch": COORD_BRANCH,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _git(r, "add", "kitty-specs")
    _git(r, "commit", "-q", "-m", "seed mission")
    _git(r, "branch", COORD_BRANCH)
    return r


def _request(repo: Path) -> TransitionRequest:
    return TransitionRequest(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        to_lane="claimed",
        actor="issue-1356-test",
        repo_root=repo,
    )


def test_transactional_emit_fans_out_only_after_commit(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    event = emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 1
    assert mock_saas_sink.last_kwargs["causation_id"] == event.event_id

    show = _git(repo, "show", f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/status.events.jsonl")
    assert event.event_id in show.stdout


def test_transactional_emit_skips_fanout_when_commit_rolls_back(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    hooks_dir = repo / ".git" / "hooks-reject"
    hooks_dir.mkdir()
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    _git(repo, "config", "core.hooksPath", str(hooks_dir))

    with pytest.raises(BookkeepingCommitFailed):
        emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 0
    missing = _git(
        repo,
        "show",
        f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/status.events.jsonl",
        check=False,
    )
    assert missing.returncode != 0


def test_transactional_emit_fails_closed_when_coordination_branch_missing(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    _git(repo, "branch", "-D", COORD_BRANCH)

    with pytest.raises(BookkeepingWorktreeMissing):
        emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 0
    assert not (repo / "kitty-specs" / MISSION_DIRNAME / "status.events.jsonl").exists()


def test_transactional_emit_fails_closed_on_malformed_meta(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    (repo / "kitty-specs" / MISSION_DIRNAME / "meta.json").write_text(
        "{bad json",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Malformed JSON"):
        emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 0
    assert not (repo / "kitty-specs" / MISSION_DIRNAME / "status.events.jsonl").exists()
