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
from specify_cli.status.rollback import capture_events_tail_ids, rollback_events_log_tail

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

    assert rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=["mine"]
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_id_order_does_not_matter(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before") + _row("a") + _row("b"), encoding="utf-8")
    pre_size = len(_row("before"))

    assert rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=["b", "a"]
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_refuses_when_a_foreign_writer_appended_after_the_capture(feature_dir: Path) -> None:
    """The DRIFT-2 hazard itself: a concurrent writer's rows survive the rollback."""
    _events_path(feature_dir).write_text(_row("before") + _row("mine"), encoding="utf-8")
    pre_size = len(_row("before"))
    expected = capture_events_tail_ids(_events_path(feature_dir), pre_size)
    assert expected == ["mine"]
    # A concurrent writer lands one more row AFTER the capture.
    _events_path(feature_dir).write_text(_row("before") + _row("mine") + _row("foreign"), encoding="utf-8")

    assert not rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=expected
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + _row("mine") + _row("foreign")


def test_refuses_when_the_tail_is_not_whole_rows(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before") + '{"torn": ', encoding="utf-8")

    assert not rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=len(_row("before")), expected_event_ids=None
    )
    # A torn row is never cut blind -- the log is left exactly as found.
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before") + '{"torn": '


def test_structural_mode_cuts_whole_rows_without_expected_ids(feature_dir: Path) -> None:
    """Callers that cannot state their rows (emit failed) still roll back whole rows."""
    _events_path(feature_dir).write_text(_row("before") + _row("partial-emit"), encoding="utf-8")

    assert rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=len(_row("before")), expected_event_ids=None
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_noop_when_nothing_was_appended(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("before"), encoding="utf-8")

    assert rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=len(_row("before")), expected_event_ids=[]
    )
    assert _events_path(feature_dir).read_text(encoding="utf-8") == _row("before")


def test_noop_when_the_log_never_existed(feature_dir: Path) -> None:
    assert rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=0, expected_event_ids=None
    )
    assert not _events_path(feature_dir).exists()


def test_refuses_when_the_log_shrank_below_the_pre_emit_size(feature_dir: Path) -> None:
    _events_path(feature_dir).write_text(_row("x"), encoding="utf-8")

    assert not rollback_events_log_tail(
        feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=10_000, expected_event_ids=None
    )
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
        assert rollback_events_log_tail(
            feature_dir, repo_root=feature_dir.parent.parent, pre_emit_event_size=pre_size, expected_event_ids=["mine"]
        )
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
