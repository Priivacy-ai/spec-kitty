"""Unit tests for ``specify_cli.coordination.transaction`` (WP05 T022–T025).

Covers:

* Happy path: ``acquire → append_event → commit → release``.
* Pre-flight refusal short-circuits BEFORE any disk write.
* Commit failure triggers byte-identical rollback (verified via SHA-256).
* Double event_id raises ``BookkeepingDoubleEventId``.
* Deferred outbound runs on success, in registration order.
* Deferred outbound skipped on rollback.
* Deferred outbound individual failure logged, others still run.
* Nested-lock attempt times out.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest

import specify_cli.coordination.transaction as transaction_module
from specify_cli.coordination.transaction import (
    BookkeepingCommitFailed,
    BookkeepingDoubleEventId,
    BookkeepingLockTimeout,
    BookkeepingPolicyRefused,
    BookkeepingTransaction,
)
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.git.commit_helpers import SafeCommitRecoveryFailed
from specify_cli.status.emit import build_status_event
from specify_cli.status import store as _store
from specify_cli.status.models import StatusEvent

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


MISSION_SLUG = "demo-feature"
MID8 = "01J6XW9K"
MISSION_ID = "01J6XW9K00000000000000000P"  # 26-char placeholder ULID
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}-{MID8}"
FEATURE_DIRNAME = f"{MISSION_SLUG}-{MID8}"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Tmp repo with the coordination branch pre-created (post-WP03 state)."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "seed.txt").write_text("seed\n")
    _git(r, "add", "seed.txt")
    _git(r, "commit", "-q", "-m", "initial")
    _git(r, "branch", COORD_BRANCH)
    return r


def _make_event(wp_id: str = "WP01", to_lane: str = "claimed") -> StatusEvent:
    return build_status_event(
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id=wp_id,
        from_lane="planned",
        to_lane=to_lane,
        actor="implementer-ivan",
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_acquire_creates_coord_worktree_and_holds_lock(repo: Path) -> None:
    """A fresh acquire creates the coord worktree and returns a usable txn."""
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="test_happy",
    ) as txn:
        assert txn.worktree_root.exists()
        assert txn.feature_dir.parent.name == "kitty-specs"
        assert txn.destination_ref == COORD_BRANCH


def test_concurrent_first_acquire_serializes_coord_worktree_creation(repo: Path) -> None:
    """Concurrent first use must not race ``git worktree add``."""
    worktree_path = CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)
    assert not worktree_path.exists()

    barrier = threading.Barrier(8)
    results: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        try:
            with BookkeepingTransaction.acquire(
                repo_root=repo,
                mission_id=MISSION_ID,
                mission_slug=MISSION_SLUG,
                mid8=MID8,
                destination_ref=COORD_BRANCH,
                operation="concurrent_first_acquire",
                timeout=10.0,
            ) as txn:
                assert txn.worktree_root == worktree_path
        except Exception as exc:  # noqa: BLE001 - test records all failures
            outcome = f"{type(exc).__name__}: {exc}"
        else:
            outcome = "ok"
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == ["ok"] * 8


def test_append_event_then_commit_returns_receipt(repo: Path) -> None:
    event = _make_event()
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="test_emit",
    ) as txn:
        handle = txn.append_event(event)
        assert handle.event_id == event.event_id
        receipt = txn.commit("status: WP01 → claimed")
        assert receipt.commit_sha
        assert receipt.event_ids == (event.event_id,)
        assert receipt.destination_ref == COORD_BRANCH

    # After exit: lock released, event readable from disk.
    feature_dir = (
        repo / ".worktrees" / f"{FEATURE_DIRNAME}-coord"
        / "kitty-specs" / FEATURE_DIRNAME
    )
    events = _store.read_events(feature_dir)
    assert len(events) == 1
    assert events[0].event_id == event.event_id


# ---------------------------------------------------------------------------
# Pre-flight refusal
# ---------------------------------------------------------------------------


def test_policy_refusal_short_circuits_before_any_write(repo: Path) -> None:
    """Refusing on ``main`` happens BEFORE the lock is acquired or any file written."""
    feature_dir = (
        repo / ".worktrees" / f"{FEATURE_DIRNAME}-coord"
        / "kitty-specs" / FEATURE_DIRNAME
    )
    events_path = feature_dir / "status.events.jsonl"
    assert not events_path.exists()

    with pytest.raises(BookkeepingPolicyRefused) as excinfo:
        BookkeepingTransaction.acquire(
            repo_root=repo,
            mission_id=MISSION_ID,
            mission_slug=MISSION_SLUG,
            mid8=MID8,
            destination_ref="main",
            operation="forbidden_emit",
        )

    assert excinfo.value.verdict.error_code == "PROTECTED_BRANCH_REFUSED"
    # No event log ever materialised.
    assert not events_path.exists()


def test_destination_ref_refs_heads_prefix_refused(repo: Path) -> None:
    """A long-form ref is refused as INVALID_SHAPE (C-016)."""
    with pytest.raises(BookkeepingPolicyRefused) as excinfo:
        BookkeepingTransaction.acquire(
            repo_root=repo,
            mission_id=MISSION_ID,
            mission_slug=MISSION_SLUG,
            mid8=MID8,
            destination_ref=f"refs/heads/{COORD_BRANCH}",
            operation="long_form",
        )
    assert excinfo.value.verdict.error_code == "DESTINATION_REF_INVALID_SHAPE"


# ---------------------------------------------------------------------------
# Rollback (byte-identical via SHA-256)
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _install_rejecting_pre_commit_hook(worktree_root: Path) -> None:
    hooks_dir_raw = subprocess.check_output(
        ["git", "-C", str(worktree_root), "rev-parse", "--git-path", "hooks"],
        text=True,
    ).strip()
    hooks_dir = Path(hooks_dir_raw)
    if not hooks_dir.is_absolute():
        hooks_dir = worktree_root / hooks_dir
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'rejected'\nexit 1\n")
    hook.chmod(0o755)


def test_commit_failure_rolls_back_event_log_byte_identical(repo: Path) -> None:
    """When safe_commit fails, status.events.jsonl is restored byte-identical."""
    # Seed: first transaction succeeds → known event log on disk.
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="seed",
    ) as txn:
        txn.append_event(_make_event("WP01", "claimed"))
        txn.commit("status: seed")

    feature_dir = (
        repo / ".worktrees" / f"{FEATURE_DIRNAME}-coord"
        / "kitty-specs" / FEATURE_DIRNAME
    )
    events_path = feature_dir / "status.events.jsonl"
    pre_rollback_sha = _sha256(events_path)
    assert pre_rollback_sha is not None

    # Now: open a second txn, append an event, then trigger commit
    # failure by injecting a pre-commit hook that rejects.
    worktree_root = (
        repo / ".worktrees" / f"{FEATURE_DIRNAME}-coord"
    )
    _install_rejecting_pre_commit_hook(worktree_root)

    with pytest.raises(BookkeepingCommitFailed), BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="rollback_test",
    ) as txn:
        txn.append_event(_make_event("WP02", "claimed"))
        txn.commit("status: should reject")

    post_rollback_sha = _sha256(events_path)
    assert post_rollback_sha == pre_rollback_sha, (
        "rollback must restore status.events.jsonl byte-identical"
    )


def test_commit_failure_removes_event_log_created_by_transaction(repo: Path) -> None:
    """If no event log existed before emit, rollback must not leave an empty file."""
    worktree_root = CoordinationWorkspace.resolve(repo, MISSION_SLUG, MID8)
    feature_dir = worktree_root / "kitty-specs" / FEATURE_DIRNAME
    events_path = feature_dir / "status.events.jsonl"
    status_path = feature_dir / "status.json"
    assert not events_path.exists()
    assert not status_path.exists()

    _install_rejecting_pre_commit_hook(worktree_root)

    with pytest.raises(BookkeepingCommitFailed), BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="rollback_missing_event_log",
    ) as txn:
        txn.append_event(_make_event("WP02", "claimed"))
        txn.commit("status: should reject")

    assert not events_path.exists()
    assert not status_path.exists()


def test_write_artifact_refuses_paths_outside_worktree(repo: Path, tmp_path: Path) -> None:
    """Artifact writes must stay confined to the transaction worktree."""
    outside = tmp_path / "outside.txt"

    with (
        BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="artifact_path_confined",
    ) as txn,
        pytest.raises(ValueError, match="outside worktree"),
    ):
        txn.write_artifact(outside, b"blocked")

    assert not outside.exists()


def test_stage_path_refuses_paths_outside_worktree(repo: Path, tmp_path: Path) -> None:
    """Staged paths must stay confined to the transaction worktree."""
    outside = tmp_path / "outside.txt"
    outside.write_text("seed", encoding="utf-8")

    with (
        BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="stage_path_confined",
    ) as txn,
        pytest.raises(ValueError, match="outside worktree"),
    ):
        txn.stage_path(outside)


def test_commit_failure_restores_empty_status_json(repo: Path) -> None:
    """An originally empty status.json must stay empty, not be unlinked."""
    worktree_root = CoordinationWorkspace.resolve(repo, MISSION_SLUG, MID8)
    feature_dir = worktree_root / "kitty-specs" / FEATURE_DIRNAME
    feature_dir.mkdir(parents=True, exist_ok=True)
    status_path = feature_dir / "status.json"
    status_path.write_bytes(b"")

    _install_rejecting_pre_commit_hook(worktree_root)

    with pytest.raises(BookkeepingCommitFailed), BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="rollback_empty_status",
    ) as txn:
        txn.append_event(_make_event("WP02", "claimed"))
        txn.commit("status: should reject")

    assert status_path.exists()
    assert status_path.read_bytes() == b""


def test_post_commit_recovery_failure_does_not_roll_back_committed_artifacts(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If safe_commit created a commit, recovery failure is not a no-commit rollback."""
    worktree_root = CoordinationWorkspace.resolve(repo, MISSION_SLUG, MID8)
    events_path = worktree_root / "kitty-specs" / FEATURE_DIRNAME / "status.events.jsonl"
    emitted_bytes: bytes | None = None

    def fail_after_commit(**_kwargs: object) -> None:
        raise SafeCommitRecoveryFailed(
            "commit created but staging recovery failed",
            destination_ref=COORD_BRANCH,
            worktree_root=worktree_root,
            orphan_stash_ref="stash@{0}",
            commit_sha="abc123",
        )

    monkeypatch.setattr(transaction_module, "safe_commit", fail_after_commit)

    with pytest.raises(BookkeepingCommitFailed), BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="post_commit_recovery",
    ) as txn:
        txn.append_event(_make_event("WP02", "claimed"))
        emitted_bytes = events_path.read_bytes()
        txn.commit("status: committed then recovery failed")

    assert emitted_bytes is not None
    assert events_path.read_bytes() == emitted_bytes


def test_rollback_skips_deferred_outbound(repo: Path) -> None:
    """On rollback, deferred callables MUST NOT run."""
    # Inject failing hook.
    worktree = CoordinationWorkspace.resolve(repo, MISSION_SLUG, MID8)
    hooks_dir_raw = subprocess.check_output(
        ["git", "-C", str(worktree), "rev-parse", "--git-path", "hooks"],
        text=True,
    ).strip()
    hooks_dir = Path(hooks_dir_raw)
    if not hooks_dir.is_absolute():
        hooks_dir = worktree / hooks_dir
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)

    ran: list[str] = []
    with pytest.raises(BookkeepingCommitFailed), BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="rollback_outbound",
    ) as txn:
        txn.append_event(_make_event("WP03", "claimed"))
        txn.defer_outbound(lambda: ran.append("a"))
        txn.commit("status: reject")

    assert ran == []


# ---------------------------------------------------------------------------
# Double event_id
# ---------------------------------------------------------------------------


def test_double_event_id_raises(repo: Path) -> None:
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="double",
    ) as txn:
        ev = _make_event()
        txn.append_event(ev)
        with pytest.raises(BookkeepingDoubleEventId):
            txn.append_event(ev)
        # Ensure we still commit/rollback cleanly.
        import contextlib
        with contextlib.suppress(Exception):
            txn.commit("status: WP01")


# ---------------------------------------------------------------------------
# Deferred outbound
# ---------------------------------------------------------------------------


def test_deferred_outbound_runs_in_order_on_success(repo: Path) -> None:
    ran: list[str] = []
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="outbound_order",
    ) as txn:
        txn.append_event(_make_event())
        txn.defer_outbound(lambda: ran.append("a"))
        txn.defer_outbound(lambda: ran.append("b"))
        txn.defer_outbound(lambda: ran.append("c"))
        txn.commit("status: WP01")
    assert ran == ["a", "b", "c"]


def test_deferred_outbound_individual_failure_logged(
    repo: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    """One callable failing does NOT abort the rest."""
    ran: list[str] = []

    def boom() -> None:
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.WARNING), BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="outbound_logged",
    ) as txn:
        txn.append_event(_make_event())
        txn.defer_outbound(lambda: ran.append("a"))
        txn.defer_outbound(boom)
        txn.defer_outbound(lambda: ran.append("c"))
        txn.commit("status: WP01")
    assert ran == ["a", "c"]
    assert any("kaboom" in rec.getMessage() for rec in caplog.records)


def test_write_artifact_refuses_paths_outside_coordination_worktree(repo: Path) -> None:
    """Artifact writes must stay inside the coordination worktree."""
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="artifact_scope",
    ) as txn:
        outside_path = repo / "outside.txt"
        with pytest.raises(ValueError, match="outside coordination worktree"):
            txn.write_artifact(outside_path, b"bad")


# ---------------------------------------------------------------------------
# Nested-lock
# ---------------------------------------------------------------------------


def test_nested_lock_attempt_times_out_from_other_thread(repo: Path) -> None:
    """A second acquire() from a different thread must hit the lock timeout."""
    # First, acquire the lock in the main thread and HOLD it.
    txn = BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="nested_outer",
    )
    txn.__enter__()
    try:
        # Try to acquire from a worker thread with a short timeout.
        error_container: dict[str, Any] = {}

        def attempt() -> None:
            try:
                BookkeepingTransaction.acquire(
                    repo_root=repo,
                    mission_id=MISSION_ID,
                    mission_slug=MISSION_SLUG,
                    mid8=MID8,
                    destination_ref=COORD_BRANCH,
                    operation="nested_inner",
                    timeout=0.5,
                )
            except BookkeepingLockTimeout as exc:
                error_container["exc"] = exc
            except Exception as exc:  # noqa: BLE001
                error_container["other"] = exc

        worker = threading.Thread(target=attempt)
        worker.start()
        worker.join(timeout=5.0)
        assert not worker.is_alive(), "worker hung — lock not contended?"
        assert "exc" in error_container, (
            f"expected BookkeepingLockTimeout, got: {error_container}"
        )
    finally:
        txn.__exit__(None, None, None)
