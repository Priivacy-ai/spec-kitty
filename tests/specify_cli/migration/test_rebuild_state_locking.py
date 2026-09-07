"""Locking pins for ``migration/rebuild_state.py`` (WP07 T041).

Family 9 of the writer census (mission ``fsm-write-path-integrity-01M1TZV6``,
``design-notes/WP01-lock-rules.md`` addendum): ``rebuild_event_log`` rewrites
a mission's whole ``status.events.jsonl`` (``tmp.open("w")`` + ``os.replace``).
WP03's AST writes gate found the rewrite holding no mission status lock, so an
append landing between the read (step 1) and the ``os.replace`` (step 6) was
silently lost. After WP07 the whole read -> reconcile -> rewrite runs under
ONE acquisition of the lock keyed on ``feature_dir.name``; the ``os.replace``
shape is unchanged.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest

import specify_cli.migration.rebuild_state as rebuild_state
from specify_cli.migration.rebuild_state import rebuild_event_log
from specify_cli.status._unsafe import append_raw_rows_atomic
from specify_cli.status.locking import _get_thread_locks, feature_status_lock, feature_status_lock_path
from specify_cli.workspace.root_resolver import resolve_status_lock_root
from tests.specify_cli.migration.test_rebuild_state import _make_feature, _write_events_file, _write_metadata

pytestmark = [pytest.mark.unit, pytest.mark.fast]

SLUG = "rebuild-locking-01KR7B1LD"
EVENTS_LOG = "status.events.jsonl"
SEED_ID = "01EVT00000000000000000001"


def _event(event_id: str, wp_id: str, to_lane: str, at: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "mission_slug": SLUG,
        "wp_id": wp_id,
        "from_lane": "planned",
        "to_lane": to_lane,
        "at": at,
        "actor": "test",
        "force": False,
        "execution_mode": "worktree",
        "reason": None,
        "review_ref": None,
        "evidence": None,
    }


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """A mission with one logged WP and one frontmatter-only WP: the rebuild synthesizes WP02's chain."""
    _write_metadata(tmp_path)
    fd = _make_feature(tmp_path, SLUG, wps=[{"name": "WP01", "lane": "claimed"}, {"name": "WP02", "lane": "in_progress"}])
    _write_events_file(fd, [_event(SEED_ID, "WP01", "claimed", "2026-01-01T00:00:00+00:00")])
    return fd


def _rows(feature_dir: Path) -> list[dict[str, Any]]:
    path = feature_dir / EVENTS_LOG
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _lock_path(feature_dir: Path) -> Path:
    return feature_status_lock_path(resolve_status_lock_root(feature_dir), feature_dir.name)


def _hold_lock_in_thread(feature_dir: Path) -> tuple[threading.Thread, threading.Event, threading.Event]:
    """Start a thread holding the mission lock until ``release`` is set."""
    ready = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        with feature_status_lock(resolve_status_lock_root(feature_dir), feature_dir.name, timeout=5):
            ready.set()
            release.wait(timeout=20)

    holder = threading.Thread(target=_hold)
    holder.start()
    assert ready.wait(timeout=5), "holder thread never acquired the lock"
    return holder, ready, release


def test_rewrite_blocks_while_another_thread_holds_the_mission_lock(feature_dir: Path) -> None:
    """The rewrite waits for the lock (L1 is per-thread re-entrant, so a second thread contends)."""
    holder, _ready, release = _hold_lock_in_thread(feature_dir)
    before = (feature_dir / EVENTS_LOG).read_bytes()
    results: list[Any] = []
    worker = threading.Thread(target=lambda: results.append(rebuild_event_log(feature_dir, SLUG, {})))
    try:
        worker.start()
        worker.join(timeout=1.0)
        assert worker.is_alive(), "rebuild did not wait for the mission lock"
        assert (feature_dir / EVENTS_LOG).read_bytes() == before, "log rewritten while another thread held the lock"
    finally:
        release.set()
        holder.join(timeout=10)
        worker.join(timeout=15)
    assert not worker.is_alive() and not holder.is_alive()
    assert results and not results[0].skipped and results[0].events_generated >= 1
    rows = _rows(feature_dir)
    assert rows[0]["event_id"] == SEED_ID and len(rows) > 1
    assert (feature_dir / EVENTS_LOG).read_bytes() != before, "fixture must make the rewrite change the log"


def test_append_landing_during_the_rebuild_is_not_lost(feature_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A locked shell append that arrives mid-rebuild lands AFTER the rewrite, not under it.

    The append is triggered from inside the rebuild (after step 1 has read the
    log, before step 6 rewrites it) so it contends for the lock the rebuild
    now holds. Before WP07 the rebuild held nothing: the append landed at once
    and the ``os.replace`` of the pre-append content erased it.
    """
    late_row = _event("01EVT0000000000000000LATE", "WP02", "claimed", "2026-01-02T00:00:00+00:00")
    thread_errors: list[BaseException] = []

    def _shell_append() -> None:
        try:
            with feature_status_lock(resolve_status_lock_root(feature_dir), feature_dir.name, timeout=15):
                append_raw_rows_atomic(feature_dir / EVENTS_LOG, [late_row])
        except BaseException as exc:
            thread_errors.append(exc)

    appender = threading.Thread(target=_shell_append)
    original_dedup = rebuild_state._dedup_events

    def _dedup_then_race(events: list[dict[str, Any]]) -> Any:
        appender.start()
        appender.join(timeout=0.5)  # unlocked: lands now; locked: still waiting
        return original_dedup(events)

    monkeypatch.setattr(rebuild_state, "_dedup_events", _dedup_then_race)
    result = rebuild_event_log(feature_dir, SLUG, {})
    appender.join(timeout=15)
    assert not appender.is_alive() and not thread_errors, thread_errors
    assert not result.skipped

    ids = [row["event_id"] for row in _rows(feature_dir)]
    assert ids[0] == SEED_ID, "positive control: the rebuilt log kept the original row"
    assert late_row["event_id"] in ids, "the shell append was lost under the whole-log rewrite"
    assert ids[-1] == late_row["event_id"], "the append landed after the rewrite, not inside it"


def test_rewrite_runs_while_mission_lock_is_held(feature_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ``os.replace`` landing step sees the mission lock among this thread's held locks."""
    held_at_replace: list[set[str]] = []
    original_replace = os.replace

    def _record(src: Any, dst: Any, *args: Any, **kwargs: Any) -> None:
        if Path(dst).name == EVENTS_LOG:
            held_at_replace.append(set(_get_thread_locks()))
        original_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", _record)
    result = rebuild_event_log(feature_dir, SLUG, {})
    assert not result.skipped
    expected = str(_lock_path(feature_dir))
    assert held_at_replace, "the rewrite never landed"
    assert all(expected in held for held in held_at_replace), held_at_replace
    assert expected not in _get_thread_locks(), "lock not released after the rewrite"
    assert not (feature_dir / "status.events.jsonl.tmp").exists()


def test_skipped_rebuild_still_releases_the_lock(tmp_path: Path) -> None:
    """The early-return arms (nothing to do) run inside the lock and release it."""
    _write_metadata(tmp_path)
    fd = _make_feature(tmp_path, SLUG, wps=[])
    result = rebuild_event_log(fd, SLUG, {})
    assert result.skipped
    assert str(_lock_path(fd)) not in _get_thread_locks()
    assert not (fd / EVENTS_LOG).exists()


def test_no_git_subprocess_while_holding_the_mission_lock(feature_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR-001 / C-002: nothing runs git while L1 is held, and the module never imports a subprocess API.

    The lock root's own git probe (``_git_common_dir`` / ``resolve_canonical_root``)
    legitimately spawns ``git`` BEFORE the acquire (WP01 section 3); the
    assertion is on spawns that see the mission lock among the held locks.
    """
    held_at_spawn: list[set[str]] = []
    original_run = subprocess.run
    original_popen = subprocess.Popen

    def _record_run(*args: Any, **kwargs: Any) -> Any:
        held_at_spawn.append(set(_get_thread_locks()))
        return original_run(*args, **kwargs)

    def _record_popen(*args: Any, **kwargs: Any) -> Any:
        held_at_spawn.append(set(_get_thread_locks()))
        return original_popen(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _record_run)
    monkeypatch.setattr(subprocess, "Popen", _record_popen)
    rebuild_event_log(feature_dir, SLUG, {})
    expected = str(_lock_path(feature_dir))
    assert not [held for held in held_at_spawn if expected in held], "a subprocess was spawned while L1 was held"

    tree = ast.parse(Path(rebuild_state.__file__).read_text(encoding="utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name.startswith("subprocess") or "git_ops" in name for name in imported), sorted(imported)
    # The lock never minted a fake repo root in the bare tree (WP01 section 6).
    assert not (feature_dir.parent.parent / ".git").exists()
