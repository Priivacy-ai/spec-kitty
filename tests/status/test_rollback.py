"""The status-owned, lock-held, tail-verified rollback truncate (spec-kitty #3960).

Mission ``fsm-write-path-integrity-01M1TZV6`` post-merge mission-review DRIFT-2:
both rollback truncates (the coord fallback arm and its workflow twin) used to
cut ``status.events.jsonl`` back to a pre-emit byte size blindly -- a
concurrent writer's rows in the cut region were destroyed.
``specify_cli.status.rollback.rollback_events_log_tail`` is the replacement:
it re-acquires the same per-mission ``feature_status_lock`` the write pipeline
uses, verifies the tail is exactly the rows the operation appended (or, when
the caller cannot state them, that the tail is whole JSONL rows), and only
then truncates through the store's raw primitive. Every refusal leaves the
log intact -- stranding one already-emitted row is recoverable, destroying
another writer's durable events is not.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.locking import FeatureStatusLockTimeoutError, feature_status_lock, feature_status_lock_path
from specify_cli.status.rollback import (
    capture_events_tail_ids,
    owned_emission_window,
    rollback_events_log_tail,
    rollback_status_artifacts,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _row(event_id: str) -> str:
    return json.dumps({"event_id": event_id, "wp_id": "WP01"}) + "\n"


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    fd = tmp_path / "kitty-specs" / "001-demo-01ABCDEF"
    fd.mkdir(parents=True)
    return fd


def _events_path(feature_dir: Path) -> Path:
    return feature_dir / "status.events.jsonl"


def test_truncates_the_tail_when_ids_match(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    pre_size = len(_row("before"))

    assert rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=["mine"])
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_id_order_does_not_matter(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before") + _row("a") + _row("b"), encoding="utf-8")
    pre_size = len(_row("before"))

    assert rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=["b", "a"])
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_refuses_when_a_foreign_writer_appended_after_the_capture(feature_dir: Path) -> None:
    """The DRIFT-2 hazard itself: a concurrent writer's rows survive the rollback."""
    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    pre_size = len(_row("before"))
    expected = capture_events_tail_ids(_events_path(feature_dir), pre_size)
    assert expected == ["mine"]
    # A concurrent writer lands one more row AFTER the capture.
    _events_path(feature_dir).write_text(_row("before") + _row("mine") + _row("foreign"), encoding="utf-8")

    assert not rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=expected)
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + _row("mine") + _row("foreign")


def test_refuses_when_the_tail_is_not_whole_rows(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before") + '{"torn": ', encoding="utf-8")

    assert not rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=len(_row("before")), expected_event_ids=None)
    # A torn row is never cut blind -- the log is left exactly as found.
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + '{"torn": '


def test_structural_mode_cuts_whole_rows_without_expected_ids(feature_dir: Path) -> None:
    """Callers that cannot state their rows (emit failed) still roll back whole rows."""
    _events_path(feature_dir).write_text(_row("before") + _row("partial-emit"), encoding="utf-8")

    assert rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=len(_row("before")), expected_event_ids=None)
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_noop_when_nothing_was_appended(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before"), encoding="utf-8")

    assert rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=len(_row("before")), expected_event_ids=[])
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_noop_when_the_log_never_existed(feature_dir: Path) -> None:
    assert rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=0, expected_event_ids=None)
    assert not _events_path(feature_dir).exists()


def test_refuses_when_the_log_shrank_below_the_pre_emit_size(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("x"), encoding="utf-8")

    assert not rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=10_000, expected_event_ids=None)
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("x")


def test_capture_degrades_to_none_on_a_non_json_tail(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before") + "not-json\n", encoding="utf-8")

    assert capture_events_tail_ids(_events_path(feature_dir), len(_row("before"))) is None


def test_lock_is_held_during_the_truncate(feature_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The helper takes the same mission L1 the pipeline uses (R14 composition)."""
    from specify_cli.status.locking import _get_thread_locks

    import specify_cli.status.rollback as rollback_module

    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    lock_key = str(feature_status_lock_path(feature_dir.parent.parent, feature_dir.name))
    seen_held: list[bool] = []
    real_truncate = rollback_module.truncate_events_log

    def probing_truncate(fd: Path, *, pre_emit_event_size: int) -> None:
        seen_held.append(lock_key in _get_thread_locks())
        real_truncate(fd, pre_emit_event_size=pre_emit_event_size)

    monkeypatch.setattr(rollback_module, "truncate_events_log", probing_truncate)
    assert rollback_events_log_tail(
        feature_dir,
        repo_root=feature_dir.parent.parent,
        pre_emit_event_size=len(_row("before")),
        expected_event_ids=["mine"],
    )
    assert seen_held == [True]


def test_lock_is_re_entrant_for_a_caller_already_holding_it(feature_dir: Path) -> None:
    """The coord fallback arm and the review shell already hold L1 across their rollback."""
    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    pre_size = len(_row("before"))

    with feature_status_lock(feature_dir.parent.parent, feature_dir.name):
        assert rollback_events_log_tail(feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=["mine"])
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_refuses_when_the_lock_cannot_be_acquired(feature_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stalled sibling holder surfaces as a refusal, never as an unverified cut."""
    import contextlib

    import specify_cli.status.rollback as rollback_module

    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")

    @contextlib.contextmanager
    def _stalled_lock(*_args: object, **_kwargs: object) -> object:
        raise FeatureStatusLockTimeoutError(
            "injected timeout",
            lock_path=feature_dir / "x.lock",
            timeout=0.01,
            holder=None,
        )
        yield  # pragma: no cover -- the raise above always fires

    monkeypatch.setattr(rollback_module, "feature_status_lock", _stalled_lock)

    assert not rollback_events_log_tail(
        feature_dir,
        repo_root=feature_dir.parent.parent,
        pre_emit_event_size=len(_row("before")),
        expected_event_ids=["mine"],
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + _row("mine")


# ---------------------------------------------------------------------------
# The ownership window (spec-kitty #4072 operator acceptance): the pre-emit
# snapshot, the emits, and the tail capture share ONE lock-held window, so a
# concurrent lock-honoring writer can never be adopted as "expected".
# ---------------------------------------------------------------------------


def test_window_snapshots_pre_emit_state_and_captures_this_operations_rows(feature_dir: Path) -> None:
    """The window yields the pre-emit snapshot at entry and the owned ids at exit."""
    _events_path(feature_dir).write_text(_row("before"), encoding="utf-8")
    (feature_dir / "status.json").write_text('{"before":true}\n', encoding="utf-8")
    pre_status = (feature_dir / "status.json").read_bytes()

    with owned_emission_window(feature_dir, repo_root=feature_dir.parent.parent) as own:
        assert own.pre_emit_event_size == len(_row("before"))
        assert own.pre_emit_status_bytes == pre_status
        assert own.expected_event_ids is None  # not captured until the window closes
        # The operation's own emit: two rows land while the window is open.
        with _events_path(feature_dir).open("a", encoding="utf-8") as fh:
            fh.write(_row("mine-1") + _row("mine-2"))
        (feature_dir / "status.json").write_text('{"after":true}\n', encoding="utf-8")

    assert own.expected_event_ids == ["mine-1", "mine-2"]


def test_window_holds_the_mission_lock_across_snapshot_emit_and_capture(feature_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The capture at window exit runs inside the SAME lock hold as the body."""
    from specify_cli.status.locking import _get_thread_locks

    _events_path(feature_dir).write_text(_row("before"), encoding="utf-8")
    lock_key = str(feature_status_lock_path(feature_dir.parent.parent, feature_dir.name))
    seen_held: list[bool] = []
    import specify_cli.status.rollback as rollback_module

    real_capture = rollback_module.capture_events_tail_ids

    def probing_capture(events_path: Path, pre_emit_event_size: int) -> list[str] | None:
        seen_held.append(lock_key in _get_thread_locks())
        return real_capture(events_path, pre_emit_event_size)

    monkeypatch.setattr(rollback_module, "capture_events_tail_ids", probing_capture)

    with owned_emission_window(feature_dir, repo_root=feature_dir.parent.parent) as own:
        seen_held.append(lock_key in _get_thread_locks())
        with _events_path(feature_dir).open("a", encoding="utf-8") as fh:
            fh.write(_row("mine"))

    assert seen_held == [True, True]
    assert own.expected_event_ids == ["mine"]


def test_window_blocks_a_concurrent_writer_thread_across_the_whole_body(feature_dir: Path) -> None:
    """The schedule-1 barrier: writer B cannot interleave between the snapshot,
    the emit, and the capture -- a B take from another thread times out for as
    long as the window is open, and succeeds only after it closes."""
    import threading

    _events_path(feature_dir).write_text(_row("before"), encoding="utf-8")

    def _b_try_acquire(timeout: float) -> bool:
        """True when writer B (another thread) acquired the mission lock."""
        acquired: list[bool] = []

        def _b() -> None:
            try:
                with feature_status_lock(feature_dir.parent.parent, feature_dir.name, timeout=timeout):
                    acquired.append(True)
            except FeatureStatusLockTimeoutError:
                acquired.append(False)

        thread = threading.Thread(target=_b, name="writer-B")
        thread.start()
        thread.join(timeout=timeout + 5)
        assert not thread.is_alive(), "writer B never finished its lock attempt"
        return acquired[0]

    with owned_emission_window(feature_dir, repo_root=feature_dir.parent.parent) as own:
        with _events_path(feature_dir).open("a", encoding="utf-8") as fh:
            fh.write(_row("mine"))
        # B is locked out for the whole snapshot -> emit -> capture window:
        # its rows can never be adopted into THIS operation's capture.
        assert _b_try_acquire(timeout=0.4) is False

    # After the window closes, B can append -- and the rollback's multiset
    # verification (not the capture) is what refuses to cut B's row.
    assert _b_try_acquire(timeout=5) is True
    with _events_path(feature_dir).open("a", encoding="utf-8") as fh:
        fh.write(_row("foreign"))
    assert not rollback_events_log_tail(
        feature_dir,
        repo_root=feature_dir.parent.parent,
        pre_emit_event_size=own.pre_emit_event_size,
        expected_event_ids=own.expected_event_ids,
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + _row("mine") + _row("foreign")


def test_window_skips_the_capture_when_the_body_raises(feature_dir: Path) -> None:
    """An emit failure leaves no ownership record (the callers roll back only
    on COMMIT failure, never on emit failure -- structural mode is the
    fallback)."""
    _events_path(feature_dir).write_text(_row("before"), encoding="utf-8")

    with pytest.raises(RuntimeError), owned_emission_window(feature_dir, repo_root=feature_dir.parent.parent) as own:
        raise RuntimeError("emit exploded")

    assert own.expected_event_ids is None


# ---------------------------------------------------------------------------
# #4087: a vanished log is never a "verified empty" tail nor a no-op rollback.
# ---------------------------------------------------------------------------


def test_refuses_when_the_log_vanished_after_the_pre_emit_snapshot(feature_dir: Path) -> None:
    """A log that existed at the pre-emit snapshot but is now absent is a
    refusal, never a claimed no-op -- and never a NUL-extended recreation."""
    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    pre_size = len(_row("before"))
    _events_path(feature_dir).unlink()

    assert not rollback_events_log_tail(
        feature_dir,
        repo_root=feature_dir.parent.parent,
        pre_emit_event_size=pre_size,
        expected_event_ids=["mine"],
    )
    # The store's ``"ab"`` truncate must never have recreated the file.
    assert not _events_path(feature_dir).exists()


def test_missing_log_inside_the_lock_is_a_refusal_not_an_empty_tail(feature_dir: Path) -> None:
    """``_tail_rows`` in the rollback mode treats a missing log as "cannot
    verify" (the outer stat saw it exist); the capture mode keeps ``[]``."""
    import specify_cli.status.rollback as rollback_module

    assert rollback_module._tail_rows(feature_dir / "status.events.jsonl", 0, missing_as_empty=False) is None
    assert rollback_module._tail_rows(feature_dir / "status.events.jsonl", 0, missing_as_empty=True) == []


# ---------------------------------------------------------------------------
# The refusal/degradation ladder's tail (spec-kitty #4072 operator coverage
# fix round): the degradation arms of ``_tail_rows`` and BOTH outer refusal
# arms of ``rollback_status_artifacts``. Every one of them leaves the
# artifacts it did not verify exactly as found and returns the explicit
# recoverable diagnostic -- never a traceback, never a blind cut.
# ---------------------------------------------------------------------------


def test_refuses_when_the_log_cannot_be_read(feature_dir: Path) -> None:
    """A log that exists but cannot be read as bytes is "cannot verify".

    The log path here is a directory -- a deterministic stand-in for any
    non-``FileNotFoundError`` read failure (permissions, an I/O error): the
    outer ``stat()`` succeeds, ``_tail_rows``' read refuses, and the rollback
    leaves the surface exactly as found rather than judging a log it never
    saw the contents of.
    """
    _events_path(feature_dir).mkdir()

    assert not rollback_events_log_tail(
        feature_dir,
        repo_root=feature_dir.parent.parent,
        pre_emit_event_size=1,
        expected_event_ids=None,
    )
    assert _events_path(feature_dir).is_dir()


def test_capture_degrades_to_none_when_the_read_shrank_below_the_pre_emit_size(feature_dir: Path) -> None:
    """``_tail_rows`` re-checks the shrink guard on the READ, not just the stat.

    The window recorded ``pre_emit_event_size`` at entry; a log now SHORTER
    than that (a whole-log rewrite landed in the window) degrades the capture
    to ``None`` -- structural verification -- rather than parsing a region
    that starts mid-row. The rollback's own ``stat()`` guard gives the same
    refusal one step earlier; this is the same defense held against the
    stat -> read race.
    """
    _events_path(feature_dir).write_text(_row("only"), encoding="utf-8")

    assert capture_events_tail_ids(_events_path(feature_dir), 10_000) is None


def test_tolerates_a_leading_blank_line_in_the_cut_region(feature_dir: Path) -> None:
    """The append primitive normalizes a missing trailing newline by inserting
    one, which leaves a leading blank line in the ``[pre_emit:]`` region --
    blank lines are skipped, so a no-trailing-newline log still verifies and
    the owned rows still roll back."""
    pre = json.dumps({"event_id": "before", "wp_id": "WP01"})  # no trailing newline
    _events_path(feature_dir).write_text(pre + "\n" + _row("mine"), encoding="utf-8")

    assert rollback_events_log_tail(
        feature_dir,
        repo_root=feature_dir.parent.parent,
        pre_emit_event_size=len(pre),
        expected_event_ids=["mine"],
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == pre


def test_refuses_when_a_tail_row_is_not_a_json_object(feature_dir: Path) -> None:
    """A whole, valid JSON line that is not an object (an array, a scalar) is
    as unverifiable as a torn row -- the tail is never cut blind."""
    _events_path(feature_dir).write_text(_row("before") + "[1, 2]\n", encoding="utf-8")

    assert not rollback_events_log_tail(
        feature_dir,
        repo_root=feature_dir.parent.parent,
        pre_emit_event_size=len(_row("before")),
        expected_event_ids=None,
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + "[1, 2]\n"


def test_a_failed_snapshot_write_is_logged_not_fatal(feature_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    """The log half verified and was restored; a snapshot restore that cannot
    write degrades loudly, not fatally.

    The snapshot path here is a directory -- a deterministic stand-in for any
    unwritable/corrupt snapshot file: the verified log rollback still lands
    (the log is the sole authority), the caller still gets ``True``, and the
    recoverable diagnostic names the regeneration command.
    """
    import logging

    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    (feature_dir / "status.json").mkdir()

    with caplog.at_level(logging.WARNING, logger="specify_cli.status.rollback"):
        assert rollback_status_artifacts(
            feature_dir,
            repo_root=feature_dir.parent.parent,
            pre_emit_event_size=len(_row("before")),
            pre_emit_status_bytes=b'{"before":true}\n',
            expected_event_ids=["mine"],
        )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")
    assert (feature_dir / "status.json").is_dir()
    assert any("agent status materialize" in record.getMessage() for record in caplog.records)


def test_artifacts_lock_timeout_refusal_leaves_both_artifacts_intact(feature_dir: Path) -> None:
    """A stalled sibling holder surfaces as the explicit recoverable refusal
    for BOTH artifacts: while the mission lock cannot be taken, the log is
    never cut and the derived snapshot is never rewritten."""
    import threading

    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    (feature_dir / "status.json").write_text('{"after":true}\n', encoding="utf-8")
    acquired = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        with feature_status_lock(feature_dir.parent.parent, feature_dir.name):
            acquired.set()
            release.wait(timeout=30)

    holder = threading.Thread(target=_hold, name="writer-B", daemon=True)
    holder.start()
    try:
        assert acquired.wait(timeout=10), "writer B never acquired the mission lock"
        assert not rollback_status_artifacts(
            feature_dir,
            repo_root=feature_dir.parent.parent,
            pre_emit_event_size=len(_row("before")),
            pre_emit_status_bytes=b'{"before":true}\n',
            expected_event_ids=["mine"],
            timeout=0.3,
        )
    finally:
        release.set()
        holder.join(timeout=10)
        assert not holder.is_alive(), "writer B never released the mission lock"

    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + _row("mine")
    assert (feature_dir / "status.json").read_text(encoding="utf-8") == '{"after":true}\n'


def test_artifacts_outer_oserror_refusal_leaves_both_artifacts_intact(tmp_path: Path) -> None:
    """A structurally broken status surface (the mission dir itself is not a
    directory) surfaces as the explicit refusal, never a traceback: the lock
    is taken, the first artifact ``stat()`` raises, and both artifacts --
    whatever exists -- are left exactly as found."""
    broken = tmp_path / "kitty-specs" / "001-demo-01ABCDEF"
    broken.parent.mkdir(parents=True)
    broken.write_text("not a directory", encoding="utf-8")

    assert not rollback_status_artifacts(
        broken,
        repo_root=tmp_path,
        pre_emit_event_size=10,
        pre_emit_status_bytes=b"{}",
        expected_event_ids=None,
    )
    assert broken.read_text(encoding="utf-8") == "not a directory"
