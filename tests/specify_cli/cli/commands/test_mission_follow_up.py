"""ATDD coverage for ``spec-kitty mission follow-up`` (WP02 / FR-001).

Pins the binding contract:

* exactly one of ``--commit <40-hex>`` / ``--pr <int>`` (validated);
* appends a ``FollowUpRecorded`` event attributed to ``mission_id``;
* idempotent: re-recording the same reference is a no-op (no duplicate event);
* allowed in ANY mission state (passive post-merge follow-ups are valid);
* ambiguous handle → ``MISSION_AMBIGUOUS_SELECTOR``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import mission_type
from specify_cli.status.lifecycle_events import (
    FOLLOW_UP_RECORDED,
    mission_event_log_path,
    read_lifecycle_events,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

runner = CliRunner()

_ULID = "01KV0S99ABCDEFGHJKMNPQRSTV"
_MID8 = _ULID[:8]
_SHA = "a" * 40


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify").mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed")
    return repo


def _make_mission(repo: Path, *, slug: str = "demo-mission", mission_id: str = _ULID) -> Path:
    feature_dir = repo / "kitty-specs" / f"{slug}-{_MID8}"
    feature_dir.mkdir(parents=True)
    meta = {
        "slug": f"{slug}-{_MID8}",
        "mission_slug": f"{slug}-{_MID8}",
        "friendly_name": "Demo Mission",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-01-01T00:00:00+00:00",
        "mission_id": mission_id,
        "mid8": _MID8,
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return feature_dir


def _invoke(repo: Path, *args: str):
    return runner.invoke(mission_type.app, list(args), env={"PWD": str(repo)})


def _follow_ups(feature_dir: Path) -> list[dict]:
    events = read_lifecycle_events(mission_event_log_path(feature_dir))
    return [e for e in events if e.get("event_type") == FOLLOW_UP_RECORDED]


def test_follow_up_commit_records_event(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    feature_dir = _make_mission(repo)
    monkeypatch.chdir(repo)

    result = _invoke(repo, "follow-up", _MID8, "--commit", _SHA)
    assert result.exit_code == 0, result.output

    ups = _follow_ups(feature_dir)
    assert len(ups) == 1
    payload = ups[0]["payload"]
    assert payload["follow_up_type"] == "commit"
    assert payload["commit_sha"] == _SHA
    assert payload["mission_id"] == _ULID


def test_follow_up_pr_records_event(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    feature_dir = _make_mission(repo)
    monkeypatch.chdir(repo)

    result = _invoke(repo, "follow-up", _MID8, "--pr", "1234")
    assert result.exit_code == 0, result.output

    ups = _follow_ups(feature_dir)
    assert len(ups) == 1
    assert ups[0]["payload"]["follow_up_type"] == "pr"
    assert ups[0]["payload"]["pr_number"] == 1234


def test_follow_up_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    feature_dir = _make_mission(repo)
    monkeypatch.chdir(repo)

    first = _invoke(repo, "follow-up", _MID8, "--commit", _SHA)
    second = _invoke(repo, "follow-up", _MID8, "--commit", _SHA)
    assert first.exit_code == 0
    assert second.exit_code == 0, "idempotent re-record is a successful no-op"
    assert len(_follow_ups(feature_dir)) == 1


def test_follow_up_requires_exactly_one_of_commit_or_pr(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    _make_mission(repo)
    monkeypatch.chdir(repo)

    # neither
    assert _invoke(repo, "follow-up", _MID8).exit_code != 0
    # both
    assert _invoke(repo, "follow-up", _MID8, "--commit", _SHA, "--pr", "1").exit_code != 0


def test_follow_up_rejects_malformed_commit(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    _make_mission(repo)
    monkeypatch.chdir(repo)

    result = _invoke(repo, "follow-up", _MID8, "--commit", "nothex")
    assert result.exit_code != 0


def test_follow_up_allowed_in_any_state(tmp_path: Path, monkeypatch) -> None:
    # No status.events.jsonl at all (a freshly-created mission) — follow-up still allowed.
    repo = _init_repo(tmp_path)
    feature_dir = _make_mission(repo)
    monkeypatch.chdir(repo)

    result = _invoke(repo, "follow-up", _MID8, "--pr", "7")
    assert result.exit_code == 0, result.output
    assert len(_follow_ups(feature_dir)) == 1


def test_follow_up_ambiguous_handle_emits_structured_error(tmp_path: Path, monkeypatch) -> None:
    repo = _init_repo(tmp_path)
    _make_mission(repo, slug="alpha", mission_id=_MID8 + "AAAAAAAAAAAAAAAAAA")
    second = repo / "kitty-specs" / f"beta-{_MID8}b"
    second.mkdir(parents=True)
    meta = {
        "slug": f"beta-{_MID8}b",
        "mission_slug": f"beta-{_MID8}b",
        "friendly_name": "Beta",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-01-01T00:00:00+00:00",
        "mission_id": _MID8 + "BBBBBBBBBBBBBBBBBB",
        "mid8": _MID8,
    }
    (second / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    monkeypatch.chdir(repo)

    result = _invoke(repo, "follow-up", _MID8, "--commit", _SHA)
    assert result.exit_code != 0
    assert "MISSION_AMBIGUOUS_SELECTOR" in result.output
