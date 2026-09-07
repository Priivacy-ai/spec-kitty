"""Lock-key and bounded-timeout pins for ``status/locking.py`` (WP01 T006/T007).

FR-004 / C-003 (rule c): the mission status lock is keyed on the mission
directory name (``feature_dir.name``), never on the slug. NFR-003 (rules a/b):
a finite-timeout take that loses surfaces a structured error naming the lock
file and the recorded holder.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import pytest

import specify_cli.status.emit as emit_module
from specify_cli.coordination.legacy_resolution import _mission_specs_dir_name
from specify_cli.retrospective.lifecycle_events import retro_status_lock
from specify_cli.review.verdict_commit_queue import DEFAULT_VERDICT_SAVE_TIMEOUT_SECONDS
from specify_cli.status import (
    BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS,
    FeatureStatusLockTimeoutError,
    TransitionRequest,
    emit_status_transition,
    feature_status_lock,
)
from specify_cli.status.locking import (
    _describe_holder,
    _get_thread_locks,
    _holder_path,
    _read_holder,
    feature_status_lock_path,
)
from specify_cli.workspace.root_resolver import resolve_status_lock_root
from tests.status.conftest import seed_wp_to_planned

pytestmark = [pytest.mark.unit]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "kitty-specs").mkdir()
    return tmp_path


def _mission_dir(repo: Path, name: str, slug: str) -> Path:
    fd = repo / "kitty-specs" / name
    fd.mkdir()
    (fd / "meta.json").write_text(json.dumps({"mission_slug": slug}), encoding="utf-8")
    return fd


# ---------------------------------------------------------------------------
# Rule (c): one lock key
# ---------------------------------------------------------------------------


def test_colliding_slugs_resolve_distinct_lock_files(repo: Path) -> None:
    """Two missions with ``mission_slug == "foo"`` never share a lock file (L-1)."""
    a = _mission_dir(repo, "foo-01AAAAAA", "foo")
    b = _mission_dir(repo, "foo-01BBBBBB", "foo")
    lock_a = feature_status_lock_path(resolve_status_lock_root(a), a.name)
    lock_b = feature_status_lock_path(resolve_status_lock_root(b), b.name)
    assert lock_a != lock_b
    assert lock_a.name == "foo-01AAAAAA.status.lock"
    assert lock_b.name == "foo-01BBBBBB.status.lock"
    # Both live in the same checkout lock directory.
    assert lock_a.parent == lock_b.parent


def test_legacy_bare_slug_dir_writers_share_one_lock_file(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A bare legacy dir's retro writer and emit path lock the same file (L-2)."""
    fd = _mission_dir(repo, "017-foo", "017-foo")
    seed_wp_to_planned(fd, "WP01", slug="017-foo")
    taken: list[Path] = []
    original = emit_module.feature_status_lock

    def _recording(root: Path, key: str, **kwargs: Any) -> Any:
        taken.append(feature_status_lock_path(root, key))
        return original(root, key, **kwargs)

    monkeypatch.setattr(emit_module, "feature_status_lock", _recording)
    emit_status_transition(TransitionRequest(feature_dir=fd, mission_slug="017-foo", wp_id="WP01", to_lane="claimed", actor="t"))
    with retro_status_lock(fd) as retro_lock:
        pass
    assert taken and all(path == retro_lock for path in taken)
    assert retro_lock.name == "017-foo.status.lock"


def test_emit_lock_key_is_the_directory_name_not_the_slug(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The flat shell keys on ``feature_dir.name`` even when the slug differs."""
    fd = _mission_dir(repo, "foo-01AAAAAA", "foo")
    seed_wp_to_planned(fd, "WP01", slug="foo")
    keys: list[str] = []
    original = emit_module.feature_status_lock

    def _recording(root: Path, key: str, **kwargs: Any) -> Any:
        keys.append(key)
        return original(root, key, **kwargs)

    monkeypatch.setattr(emit_module, "feature_status_lock", _recording)
    emit_status_transition(TransitionRequest(feature_dir=fd, mission_slug="foo", wp_id="WP01", to_lane="claimed", actor="t"))
    assert keys == ["foo-01AAAAAA"]


def test_transaction_lock_key_equals_its_mission_dir_name() -> None:
    """The transaction's key is the ``<slug>-<mid8>`` dir it writes into."""
    assert _mission_specs_dir_name("foo", "01AAAAAA") == "foo-01AAAAAA"
    # Idempotent on an already-embedded suffix (the T001 fixture shape).
    assert _mission_specs_dir_name("foo-01AAAAAA", "01AAAAAA") == "foo-01AAAAAA"


# ---------------------------------------------------------------------------
# Rules (a)/(b): bounded takes surface a structured error naming the holder
# ---------------------------------------------------------------------------


def test_bound_is_aligned_with_the_verdict_save_queue_bound() -> None:
    assert BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS == DEFAULT_VERDICT_SAVE_TIMEOUT_SECONDS
    assert 0 < BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS < float("inf")


def test_holder_record_written_on_acquire_and_cleared_on_release(repo: Path) -> None:
    with feature_status_lock(repo, "demo-01AAAAAA", timeout=2) as lock_path:
        holder = _read_holder(lock_path)
        assert holder is not None
        assert holder["pid"] == os.getpid()
        assert holder["thread"] == threading.current_thread().name
        assert "acquired_at" in holder
        # Re-entrant inner acquisition keeps the outer record.
        with feature_status_lock(repo, "demo-01AAAAAA", timeout=2):
            assert _read_holder(lock_path) == holder
        assert _read_holder(lock_path) == holder
    assert not _holder_path(lock_path).exists()
    assert str(lock_path) not in _get_thread_locks()


def test_read_holder_is_best_effort(tmp_path: Path) -> None:
    lock_path = tmp_path / "x.status.lock"
    assert _read_holder(lock_path) is None
    _holder_path(lock_path).write_text("not json", encoding="utf-8")
    assert _read_holder(lock_path) is None
    _holder_path(lock_path).write_text("[1, 2]", encoding="utf-8")
    assert _read_holder(lock_path) is None


def test_describe_holder_renders_both_arms() -> None:
    assert "holder unknown" in _describe_holder(None)
    text = _describe_holder({"pid": 42, "thread": "MainThread", "acquired_at": "2026-09-06T00:00:00+00:00"})
    assert "pid 42" in text and "MainThread" in text and "2026-09-06T00:00:00+00:00" in text


def test_contended_bounded_take_raises_structured_error_naming_holder(repo: Path) -> None:
    holder_ready = threading.Event()
    release = threading.Event()
    holder_thread_name = "wp01-holder"

    def _hold() -> None:
        with feature_status_lock(repo, "demo-01AAAAAA", timeout=5):
            holder_ready.set()
            release.wait(timeout=10)

    holder = threading.Thread(target=_hold, name=holder_thread_name)
    holder.start()
    try:
        assert holder_ready.wait(timeout=5)
        started = time.monotonic()
        with (
            pytest.raises(FeatureStatusLockTimeoutError) as excinfo,
            feature_status_lock(repo, "demo-01AAAAAA", timeout=0.3),
        ):
            pass
        elapsed = time.monotonic() - started
    finally:
        release.set()
        holder.join(timeout=10)
    assert not holder.is_alive()
    assert elapsed < 5.0
    exc = excinfo.value
    expected_path = feature_status_lock_path(repo, "demo-01AAAAAA")
    assert exc.lock_path == expected_path
    assert exc.timeout == 0.3
    assert exc.holder is not None and exc.holder["thread"] == holder_thread_name
    message = str(exc)
    assert "Timed out acquiring status lock" in message
    assert str(expected_path) in message
    assert f"held by pid {exc.holder['pid']}" in message


def test_unbounded_default_is_preserved(repo: Path) -> None:
    """The lock's own default stays ``-1`` (research Q2: finite default is a follow-up)."""
    import inspect

    assert inspect.signature(feature_status_lock).parameters["timeout"].default == -1


def test_annotation_waits_for_transition_directory_lock(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Annotations cannot bypass a transition holding the same mission's lock."""
    from specify_cli.status.models import WPInnerStateDelta

    fd = _mission_dir(repo, "foo-01AAAAAA", "foo")
    entered = threading.Event()
    completed = threading.Event()
    errors: list[BaseException] = []
    original = emit_module.feature_status_lock

    def _recording(root: Path, key: str, **kwargs: Any) -> Any:
        entered.set()
        return original(root, key, **kwargs)

    monkeypatch.setattr(emit_module, "feature_status_lock", _recording)

    def _write() -> None:
        try:
            emit_module.emit_inner_state_changed(
                fd, "WP01", WPInnerStateDelta(note="annotation"), actor="test", mission_slug="foo", repo_root=repo
            )
        except BaseException as exc:
            errors.append(exc)
        finally:
            completed.set()

    thread = threading.Thread(target=_write)
    with feature_status_lock(repo, fd.name):
        thread.start()
        assert entered.wait(timeout=5)
        wrote_inside_lock = completed.wait(timeout=0.3)
    thread.join(timeout=5)
    assert not errors
    assert not thread.is_alive()
    assert not wrote_inside_lock, "annotation wrote while the transition lock was held"
    assert (fd / "status.events.jsonl").exists()
