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
    BookkeepingError,
    BookkeepingLockTimeout,
    BookkeepingPolicyRefused,
    BookkeepingTransaction,
)
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.commit_guard import GuardCapability
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


def _write_modern_meta(repo: Path, coordination_branch: str = COORD_BRANCH) -> None:
    feature_dir = repo / "kitty-specs" / FEATURE_DIRNAME
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        (
            "{\n"
            f'  "mission_id": "{MISSION_ID}",\n'
            f'  "mission_slug": "{FEATURE_DIRNAME}",\n'
            f'  "target_branch": "main",\n'
            f'  "coordination_branch": "{coordination_branch}"\n'
            "}\n"
        ),
        encoding="utf-8",
    )


def _write_legacy_meta(repo: Path) -> None:
    feature_dir = repo / "kitty-specs" / FEATURE_DIRNAME
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        (
            "{\n"
            f'  "mission_id": "{MISSION_ID}",\n'
            f'  "mission_slug": "{FEATURE_DIRNAME}",\n'
            '  "target_branch": "main"\n'
            "}\n"
        ),
        encoding="utf-8",
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


def test_legacy_transaction_appends_to_primary_checkout(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy no-coordination-branch missions write through primary contract."""
    _write_legacy_meta(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("SPEC_KITTY_TEST_MODE", "1")

    event = _make_event()
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="legacy_emit",
        capability=GuardCapability.TEST_MODE,
    ) as txn:
        assert txn.worktree_root == repo
        assert txn.destination_ref == "main"
        txn.append_event(event)
        txn.commit("status: legacy emit")

    events = _store.read_events(repo / "kitty-specs" / FEATURE_DIRNAME)
    assert [existing.event_id for existing in events] == [event.event_id]
    assert not (
        repo / ".worktrees" / f"{FEATURE_DIRNAME}-coord" / "kitty-specs" / FEATURE_DIRNAME
    ).exists()


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


def test_protected_target_ref_recovers_only_with_explicit_coord_meta(repo: Path) -> None:
    """Modern meta can prove ``main`` is the target, not the bookkeeping destination."""
    _write_modern_meta(repo)

    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref="main",
        operation="recover_target_ref",
    ) as txn:
        assert txn.destination_ref == COORD_BRANCH
        assert txn.worktree_root == CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)


def test_protected_target_ref_with_mismatched_coord_meta_refused(repo: Path) -> None:
    """A protected caller ref must not be laundered through spoofed coordination metadata."""
    _write_modern_meta(repo, coordination_branch="kitty/mission-other-01J6XW9K")

    with pytest.raises(BookkeepingPolicyRefused) as excinfo:
        BookkeepingTransaction.acquire(
            repo_root=repo,
            mission_id=MISSION_ID,
            mission_slug=MISSION_SLUG,
            mid8=MID8,
            destination_ref="main",
            operation="recover_target_ref",
        )

    assert excinfo.value.verdict.error_code == "PROTECTED_BRANCH_REFUSED"


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


def test_mission_slug_path_traversal_is_rejected(repo: Path) -> None:
    """User-controlled mission selectors must not escape kitty-specs/."""
    with pytest.raises(BookkeepingError, match="safe path segment"):
        BookkeepingTransaction.acquire(
            repo_root=repo,
            mission_id=MISSION_ID,
            mission_slug="../escape",
            mid8=MID8,
            destination_ref=COORD_BRANCH,
            operation="unsafe_slug",
        )


@pytest.mark.parametrize(
    ("field_name", "mission_slug", "mid8"),
    [
        ("mission_slug", " demo-feature", MID8),
        ("mission_slug", "demo-feature ", MID8),
        ("mid8", MISSION_SLUG, " 01J6XW9K"),
        ("mid8", MISSION_SLUG, "01J6XW9K "),
    ],
)
def test_whitespace_bearing_selectors_are_rejected(
    repo: Path, field_name: str, mission_slug: str, mid8: str,
) -> None:
    with pytest.raises(
        BookkeepingError,
        match=rf"{field_name} is not a safe path segment",
    ):
        BookkeepingTransaction.acquire(
            repo_root=repo,
            mission_id=MISSION_ID,
            mission_slug=mission_slug,
            mid8=mid8,
            destination_ref=COORD_BRANCH,
            operation="unsafe_whitespace",
        )


def test_legacy_warning_marker_confines_mission_id(repo: Path) -> None:
    with pytest.raises(BookkeepingError, match="mission_id is not a safe path segment"):
        transaction_module._legacy_warning_marker_path(repo, "../escape")


# ---------------------------------------------------------------------------
# Rollback (byte-identical via SHA-256)
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 — file-integrity checksum of read_bytes() to assert byte-identical rollback, not charter freshness hashing


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


def test_rollback_artifact_restore_refuses_parent_symlink_escape(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rollback restore must not write snapshots through a swapped parent."""
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    worktree = CoordinationWorkspace.resolve(repo, MISSION_SLUG, MID8)

    def fail_commit(**_kwargs: object) -> None:
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(transaction_module, "safe_commit", fail_commit)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(BookkeepingCommitFailed),
        BookkeepingTransaction.acquire(
            repo_root=repo,
            mission_id=MISSION_ID,
            mission_slug=MISSION_SLUG,
            mid8=MID8,
            destination_ref=COORD_BRANCH,
            operation="rollback_artifact_symlink_escape",
        ) as txn,
    ):
        link_path = worktree / "kitty-specs" / FEATURE_DIRNAME / "rollback-link"
        artifact = link_path / "artifact.txt"
        link_path.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(b"old-inside")

        txn.write_artifact(artifact, b"new-inside")

        backup_path = link_path.with_name("rollback-link-backup")
        link_path.rename(backup_path)
        link_path.symlink_to(outside_dir, target_is_directory=True)
        txn.commit("status: should reject")

    assert not (outside_dir / "artifact.txt").exists()
    assert any(
        "rollback: restore of" in record.getMessage()
        and "resolves outside worktree" in record.getMessage()
        for record in caplog.records
    )


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


def test_write_artifact_refuses_symlink_escape(repo: Path, tmp_path: Path) -> None:
    """Artifact writes must reject symlinks that resolve outside the worktree."""
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="artifact_symlink_escape",
    ) as txn:
        link_path = txn.worktree_root / "kitty-specs" / FEATURE_DIRNAME / "escape-link"
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(outside_dir, target_is_directory=True)

        with pytest.raises(ValueError, match="outside worktree"):
            txn.write_artifact(link_path / "artifact.txt", b"bad")


def test_write_artifact_rechecks_after_parent_creation(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parent creation must not open a post-validation symlink escape."""
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    original_mkdir = Path.mkdir
    swapped = False

    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="artifact_late_symlink_escape",
    ) as txn:
        link_path = txn.worktree_root / "kitty-specs" / FEATURE_DIRNAME / "late-link"

        def swap_to_symlink_after_mkdir(
            self: Path,
            mode: int = 0o777,
            parents: bool = False,
            exist_ok: bool = False,
        ) -> None:
            nonlocal swapped
            original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)
            if self == link_path and not swapped:
                swapped = True
                self.rmdir()
                self.symlink_to(outside_dir, target_is_directory=True)

        monkeypatch.setattr(Path, "mkdir", swap_to_symlink_after_mkdir)

        with pytest.raises(ValueError, match="outside worktree"):
            txn.write_artifact(link_path / "artifact.txt", b"bad")
        assert not (outside_dir / "artifact.txt").exists()


def test_write_artifact_refuses_parent_swap_after_final_validation(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Final write must bind to a verified parent instead of a swapped symlink."""
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    original_resolve = transaction_module._resolve_confined_artifact_path
    resolve_count = 0

    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="artifact_post_validation_symlink_escape",
    ) as txn:
        link_path = txn.worktree_root / "kitty-specs" / FEATURE_DIRNAME / "late-link"

        def swap_after_final_validation(worktree_root: Path, path: Path) -> Path:
            nonlocal resolve_count
            resolved = original_resolve(worktree_root, path)
            resolve_count += 1
            if resolve_count == 3:
                link_path.rmdir()
                link_path.symlink_to(outside_dir, target_is_directory=True)
            return resolved

        monkeypatch.setattr(
            transaction_module,
            "_resolve_confined_artifact_path",
            swap_after_final_validation,
        )

        with pytest.raises(ValueError, match="unsafe path changed during write"):
            txn.write_artifact(link_path / "artifact.txt", b"bad")
        assert not (outside_dir / "artifact.txt").exists()


def test_write_artifact_preserves_existing_file_mode(repo: Path) -> None:
    """Atomic temp replace must not strip executable/user mode bits."""
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="artifact_mode_preservation",
    ) as txn:
        artifact = txn.worktree_root / "kitty-specs" / FEATURE_DIRNAME / "script.sh"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(b"old\n")
        artifact.chmod(0o744)

        txn.write_artifact(artifact, b"new\n")

        assert artifact.read_bytes() == b"new\n"
        assert artifact.stat().st_mode & 0o777 == 0o744


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


# ---------------------------------------------------------------------------
# C-004: legacy-HEAD-override block byte-freeze regression (WP14)
# ---------------------------------------------------------------------------

# The exact source text of the "legacy mode" HEAD-override block inside
# ``_acquire_locked`` (WP08 T035-T036 / C-004). This block resolves
# ``effective_destination_ref`` from the worktree's actual checked-out HEAD
# for legacy (pre-coordination-branch) missions, and every other step of
# ``acquire()`` depends on it applying uniformly across both the legacy and
# new-topology paths. WP14 (read-surface-ssot-closeout) intentionally left
# this block untouched while routing the surrounding meta.json reads onto
# the canonical ``load_meta`` reader.
#
# Pinned by *content*, not line numbers: the block's line span (751-771 at
# WP14 authoring time) naturally drifts as unrelated code above it changes
# (e.g. import routing in this same WP shifted it up ~15 lines). A
# line-number pin would false-positive on that drift; a content pin only
# fires on an actual edit to the frozen block itself.
_LEGACY_HEAD_OVERRIDE_BLOCK = (
    "        #     name resolved from the worktree's ``HEAD`` so the pre-flight\n"
    "        #     policy gate and the ``safe_commit`` HEAD assertion see a\n"
    "        #     consistent ref.\n"
    "        #\n"
    "        # Crucial invariant: **every other step of acquire() below — the\n"
    "        # pre-flight policy gate, the feature-status lock, the surgical\n"
    "        # truncate rollback, and the outbound deferral — applies\n"
    "        # uniformly to both paths.**  Only ``worktree_root`` and (in\n"
    "        # legacy mode) ``destination_ref`` differ.\n"
    "        legacy_mode = _is_legacy_mission(repo_root, safe_mission_slug, safe_mid8)\n"
    "        if legacy_mode:\n"
    "            try:\n"
    "                worktree_root, lane_branch = _resolve_legacy_lane_destination(\n"
    "                    repo_root,\n"
    "                )\n"
    "            except BookkeepingLegacyResolutionFailed:\n"
    "                raise\n"
    "            # Override caller-supplied destination_ref with the actual\n"
    "            # lane branch so policy + HEAD assertion both see truth.\n"
    "            effective_normalized_ref = _normalize_ref(lane_branch)\n"
    "            effective_destination_ref = effective_normalized_ref\n"
)


def test_legacy_head_override_block_is_byte_unchanged() -> None:
    """C-004: the legacy-mode HEAD-override block must never be edited.

    WP14 routed the module's other meta.json reads onto the canonical
    ``load_meta`` reader but was required to leave this block byte-for-byte
    identical. Guards against silent drift in a future edit.
    """
    source_path = Path(transaction_module.__file__)
    source_text = source_path.read_text(encoding="utf-8")
    assert _LEGACY_HEAD_OVERRIDE_BLOCK in source_text, (
        "The C-004 legacy-HEAD-override block in coordination/transaction.py "
        "has changed. This block is frozen by charter directive; any change "
        "must go through an explicit, reviewed decision, not an incidental "
        "refactor."
    )
