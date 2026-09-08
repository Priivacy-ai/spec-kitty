"""Coord-fallback rollback refusal (spec-kitty #4072 operator acceptance).

The workflow twin's schedule-2 defect had a coord fallback twin: when
``_rollback_events_log_tail`` refused the cut (a foreign row in the tail),
``_restore_coord_status_artifacts`` ignored the refusal and restored the
pre-emit ``status.json`` bytes anyway -- obsolete derived state over a
preserved log.

This test drives the REAL coord fallback arm
(``emit_status_transition_transactional`` forced onto the
``_emit_on_coord_then_commit`` door, real git repo, real coord branch, real
L1) with a commit seam that lands a foreign row on the coord log inside the
hold (the non-lock-honoring / log-rewrite hazard class) and then fails. The
rollback must refuse, BOTH coord artifacts must stay at their newer coherent
state, and the refusal must be logged as the recoverable outcome.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination import status_transition as st
from specify_cli.status.locking import feature_status_lock
from specify_cli.status.models import Lane, StatusEvent, TransitionRequest

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "coord-fallback-rollback-refusal"
MID8 = "01M1RFUS"
MISSION_ID = "01M1RFUS000000000000000000"
MISSION_DIRNAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIRNAME}"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True, text=True)


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
    meta = {
        "mission_slug": MISSION_SLUG,
        "mission_id": MISSION_ID,
        "mid8": MID8,
        "coordination_branch": COORD_BRANCH,
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
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
        actor="coord-fallback-rollback-refusal-test",
        repo_root=repo,
    )


def _seed_planned_on_coord(repo: Path) -> None:
    """Seed WP01 in 'planned' directly on the coord branch (real git worktree)."""
    seed_event = StatusEvent(
        event_id="01SEEDGENESIS0000000000003",
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.GENESIS,
        to_lane=Lane.PLANNED,
        at="2026-05-31T00:00:00+00:00",
        actor="seed",
        force=False,
        reason="seed",
        execution_mode="worktree",
    )
    worktree = repo / ".worktrees" / "seed-genesis"
    _git(repo, "worktree", "add", "-q", str(worktree), COORD_BRANCH)
    events_path = worktree / "kitty-specs" / MISSION_DIRNAME / "status.events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(seed_event.to_dict()) + "\n")
    _git(worktree, "add", "kitty-specs")
    _git(worktree, "commit", "-q", "-m", "seed WP01 planned")
    _git(repo, "worktree", "remove", "-f", str(worktree))


def _force_fallback_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(st, "_transaction_topology_available", lambda *_args, **_kwargs: False)


def test_coord_fallback_refused_rollback_preserves_coord_artifacts(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A foreign row on the coord tail refuses the cut -- and the coord
    ``status.json`` is preserved at its newer coherent state (never unlinked
    or restored to pre-emit bytes), with the refusal logged as recoverable."""
    import logging

    _seed_planned_on_coord(repo)
    _force_fallback_path(monkeypatch)

    status_bytes_at_commit: list[bytes] = []

    def _land_foreign_row_then_fail(**kwargs: object) -> None:
        coord_fd = Path(kwargs["coord_feature_dir"])  # type: ignore[arg-type]
        events_path = coord_fd / "status.events.jsonl"
        status_path = coord_fd / "status.json"
        status_bytes_at_commit.append(status_path.read_bytes())
        # A non-lock-honoring writer lands a whole foreign row inside the L1
        # hold (the log-rewrite hazard class): the tail is no longer exactly
        # this operation's rows.
        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event_id": "foreign-B", "wp_id": "WP01"}) + "\n")
        raise RuntimeError("coord commit failed after a foreign row landed")

    monkeypatch.setattr(st, "_commit_status_artifacts_to_coord", _land_foreign_row_then_fail)

    with caplog.at_level(logging.WARNING, logger="specify_cli.coordination.status_transition"), pytest.raises(RuntimeError, match="coord commit failed"):
        st.emit_status_transition_transactional(_request(repo), ensure_sync_daemon=False)

    # The coord fallback arm materializes its worktree on demand: find the
    # coord feature dir it wrote to (the only checked-out coord worktree).
    coord_fds = [path.parent for path in (repo / ".worktrees").glob(f"*/kitty-specs/{MISSION_DIRNAME}/status.events.jsonl")]
    assert len(coord_fds) == 1, f"expected exactly one coord worktree surface, found {coord_fds}"
    coord_fd = coord_fds[0]
    events_path = coord_fd / "status.events.jsonl"
    status_path = coord_fd / "status.json"

    rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    row_ids = {row.get("event_id") for row in rows}
    assert "foreign-B" in row_ids, "the foreign row must survive the refused rollback"
    assert any(row.get("to_lane") == "claimed" for row in rows), "this operation's own emitted row must also survive the refusal (stranded, recoverable)"
    # Schedule-2 fix on the coord twin: the derived snapshot is preserved at
    # its newer coherent state -- the pre-emit state had no status.json, and
    # the old code would have UNLINKED this one.
    assert status_path.exists(), "the coord status.json must NOT be unlinked by a refused rollback"
    assert status_path.read_bytes() == status_bytes_at_commit[0], "the coord status.json must stay at its newer coherent state"
    # The explicit recoverable diagnostic is logged on the refusal path.
    assert any("Refused rollback restore" in record.message for record in caplog.records), "the refusal must be logged loudly as the recoverable outcome"
    # The mission lock is free afterwards (the L1 hold ended with the window).
    with feature_status_lock(repo, MISSION_DIRNAME, timeout=1):
        pass
