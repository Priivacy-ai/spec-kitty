"""Transactional status-transition integration tests for issue #1356."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from specify_cli.coordination.status_transition import (
    emit_status_transition_transactional,
    read_events_transactional,
)
from specify_cli.coordination.status_service import (
    EventLogReadContract,
    EventLogWriteContract,
    StatusContractError,
    append_event_log,
    merge_append_preserving_coordination_event_log_bytes,
    read_event_log,
)
from specify_cli.coordination.transaction import BookkeepingCommitFailed, BookkeepingWorktreeMissing
from specify_cli.status.models import Lane, StatusEvent, TransitionRequest

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


def _status_event(event_id: str, *, to_lane: str = "claimed") -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane(to_lane),
        at="2026-06-01T00:00:00+00:00",
        actor="contract-test",
        force=False,
        execution_mode="worktree",
    )


def _seed_planned_on_coord(repo: Path) -> StatusEvent:
    """Seed WP01 out of the non-display 'genesis' state into 'planned'.

    A fresh WP derives from_lane 'genesis', so the first lane transition must
    be genesis -> planned (as finalize-tasks does). The seed is written and
    committed directly on the coordination branch via a throwaway worktree, so
    it does not fan out — only the transition under test does.
    """
    seed_event = StatusEvent(
        event_id="01SEEDGENESIS0000000000001",
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.GENESIS,
        to_lane=Lane.PLANNED,
        at="2026-05-31T00:00:00+00:00",
        actor="seed",
        force=True,
        reason="seed",
        execution_mode="worktree",
    )
    worktree = repo / ".worktrees" / "seed-genesis"
    _git(repo, "worktree", "add", "-q", str(worktree), COORD_BRANCH)
    coord_feature_dir = worktree / "kitty-specs" / MISSION_DIRNAME
    append_event_log(
        EventLogWriteContract.coordination_transaction_append(coord_feature_dir),
        seed_event,
    )
    _git(worktree, "add", "kitty-specs")
    _git(worktree, "commit", "-q", "-m", "seed genesis->planned")
    _git(repo, "worktree", "remove", "-f", str(worktree))
    return seed_event


def test_transactional_emit_fans_out_only_after_commit(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    _seed_planned_on_coord(repo)
    event = emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 1
    assert mock_saas_sink.last_kwargs["causation_id"] == event.event_id

    show = _git(repo, "show", f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/status.events.jsonl")
    assert event.event_id in show.stdout


def test_transactional_read_targets_coordination_branch(repo: Path) -> None:
    seed = _seed_planned_on_coord(repo)
    event = emit_status_transition_transactional(_request(repo), sync_dossier=False)

    events = read_events_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        repo_root=repo,
    )

    # The coordination branch carries the genesis->planned seed plus the
    # planned->claimed transition under test.
    assert [e.event_id for e in events] == [seed.event_id, event.event_id]
    assert not (repo / "kitty-specs" / MISSION_DIRNAME / "status.events.jsonl").exists()


def test_primary_checkout_event_log_read_remains_explicit(repo: Path) -> None:
    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    event = _status_event("01PRIMARY00000000000000000")

    append_event_log(EventLogWriteContract.primary_checkout_append(feature_dir), event)
    events = read_event_log(EventLogReadContract.primary_checkout(feature_dir))

    assert [e.event_id for e in events] == [event.event_id]
    assert (feature_dir / "status.events.jsonl").exists()


def test_coordination_branch_ref_read_ignores_stale_primary_checkout(repo: Path) -> None:
    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    primary_event = _status_event("01PRIMARYSTALE00000000000", to_lane="planned")
    coord_event = _status_event("01COORDCURRENT00000000000", to_lane="claimed")
    append_event_log(EventLogWriteContract.primary_checkout_append(feature_dir), primary_event)

    worktree = repo / ".worktrees" / "seed-coord"
    _git(repo, "worktree", "add", "-q", str(worktree), COORD_BRANCH)
    coord_feature_dir = worktree / "kitty-specs" / MISSION_DIRNAME
    append_event_log(
        EventLogWriteContract.coordination_transaction_append(coord_feature_dir),
        coord_event,
    )
    _git(worktree, "add", "kitty-specs")
    _git(worktree, "commit", "-q", "-m", "seed coord event")
    _git(repo, "worktree", "remove", "-f", str(worktree))

    events = read_event_log(
        EventLogReadContract.coordination_branch_ref(
            repo_root=repo,
            destination_ref=COORD_BRANCH,
            feature_dir=coord_feature_dir,
            parser_feature_dir=feature_dir,
        )
    )

    assert [e.event_id for e in events] == [coord_event.event_id]
    assert read_event_log(EventLogReadContract.primary_checkout(feature_dir))[0].event_id == primary_event.event_id


def test_read_contract_cannot_be_used_as_write_contract(repo: Path) -> None:
    event = _status_event("01CONTRACTFAIL000000000000")

    with pytest.raises(StatusContractError):
        append_event_log(  # type: ignore[arg-type]
            EventLogReadContract.primary_checkout(repo / "kitty-specs" / MISSION_DIRNAME),
            event,
        )


def test_wrong_write_target_fails_loudly(repo: Path) -> None:
    event = _status_event("01WRONGTARGET000000000000")
    primary_feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    coordination_feature_dir = repo / ".worktrees" / "coord" / "kitty-specs" / MISSION_DIRNAME

    with pytest.raises(StatusContractError, match="primary_checkout_append"):
        append_event_log(
            EventLogWriteContract.primary_checkout_append(coordination_feature_dir),
            event,
        )

    with pytest.raises(StatusContractError, match="coordination_transaction_append"):
        append_event_log(
            EventLogWriteContract.coordination_transaction_append(primary_feature_dir),
            event,
        )


def test_wrong_read_source_fails_loudly(repo: Path) -> None:
    primary_feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    coordination_feature_dir = repo / ".worktrees" / "coord" / "kitty-specs" / MISSION_DIRNAME

    with pytest.raises(StatusContractError, match="primary_checkout"):
        read_event_log(EventLogReadContract.primary_checkout(coordination_feature_dir))

    with pytest.raises(StatusContractError, match="coordination_worktree"):
        read_event_log(EventLogReadContract.coordination_worktree(primary_feature_dir))


def test_append_preserving_coordination_merge_keeps_existing_history() -> None:
    coord = b'{"event_id":"existing"}\n'
    incoming = b'{"event_id":"existing"}\n{"event_id":"new"}\n'

    merged = merge_append_preserving_coordination_event_log_bytes(coord, incoming)

    assert merged == b'{"event_id":"existing"}\n{"event_id":"new"}\n'


def test_transactional_read_does_not_create_coordination_worktree(repo: Path) -> None:
    assert not (repo / ".worktrees").exists()

    events = read_events_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        repo_root=repo,
    )

    assert events == []
    assert not (repo / ".worktrees").exists()
    assert _git(repo, "status", "--short").stdout == ""


def test_transactional_emit_skips_fanout_when_commit_rolls_back(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    # Seed planned before installing the rejecting hook so the transition
    # under test is genesis-free (claimed is reachable from planned).
    _seed_planned_on_coord(repo)

    hooks_dir = repo / ".git" / "hooks-reject"
    hooks_dir.mkdir()
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    _git(repo, "config", "core.hooksPath", str(hooks_dir))

    with pytest.raises(BookkeepingCommitFailed):
        emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 0
    # The coord branch still carries only the seed (genesis->planned); the
    # rolled-back claimed transition must NOT have been committed.
    committed = _git(
        repo,
        "show",
        f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/status.events.jsonl",
        check=False,
    )
    assert committed.returncode == 0
    assert '"to_lane": "planned"' in committed.stdout
    assert '"to_lane": "claimed"' not in committed.stdout


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
