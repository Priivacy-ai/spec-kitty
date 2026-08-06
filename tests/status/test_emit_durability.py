"""WP03 (T012-T015, FR-008): the verdict-durability write at the emit seam.

Contract: ``kitty-specs/verdict-seam-write-unification-01KZ9Q35/contracts/
verdict-durability-write.md`` -- ``status/emit.py::emit_status_transition``'s
event-log append is THE authoritative durable act for a recorded verdict
(any outbound-from-``in_review`` transition, which the FSM requires to carry
a ``ReviewResult``). The ``review-cycle-N.md`` artifact commit
(``review/cycle.py::_commit_review_cycle_artifact``) stays a SEPARATE,
still-hard-error render this WP does not touch -- WP05 owns the demote to
best-effort once its reader flip lands (D-PLAN-11).

This file is deliberately hermetic (no real git repo, no ``review/cycle.py``
call) -- it exercises the append seam directly through ``emit_status_
transition``, mirroring ``tests/status/test_emit.py``'s own fixtures and
seeding helper rather than the heavier, git-backed harness ``tests/
integration/test_review_durability_matrix.py`` (WP05-owned) uses for the
``.md`` artifact's own commit path.

Covers:

* **T012/SC-003** -- two concurrent distinct verdicts (different WPs, same
  mission) must both survive durably, or one must raise an explicit refusal
  -- never a silent drop. Driven through 2 real OS processes because
  ``feature_status_lock`` is an inter-process ``FileLock``; a threaded
  harness would not exercise the real serialization boundary.
* **T013/FR-008** -- the event append alone is sufficient for the reducer
  snapshot to carry the recorded verdict, with a non-vacuity guard proving
  the assertion is not a tautology.
* **T014/NFR-001** -- no ``git``/subprocess call is ever made while the
  durability lock is held (the append discipline is the serialization, not
  a lock spanning ``git``).
* **T014/NFR-004** -- exactly one authoritative durability-append call
  occurs per recorded verdict (the ``.md`` render commit is excluded from
  this count by construction -- this file never calls into ``review/
  cycle.py`` at all).
* **T015/NFR-005** -- a single verdict record, including durable
  persistence, completes well under the 2-second budget.
"""

from __future__ import annotations

import multiprocessing
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import specify_cli.status.emit as emit_module
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.models import ReviewResult, TransitionRequest
from specify_cli.status.reducer import event_sourced_review_result, materialize

from tests.status.conftest import seed_wp_to_planned as _seed_planned

_MISSION_SLUG = "091-verdict-durability"

# ── Fixtures / shared helpers ────────────────────────────────────────────


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """A minimal kitty-specs feature directory for a fresh mission."""
    fd = tmp_path / "kitty-specs" / _MISSION_SLUG
    fd.mkdir(parents=True)
    return fd


def _advance_to_in_review(feature_dir: Path, wp_id: str, mission_slug: str) -> None:
    """Drive a WP from genesis through ``in_review`` (no verdict yet).

    Mirrors the production ``move-task`` lifecycle up to the point a
    reviewer records a verdict -- the seam this file's tests exercise.
    """
    _seed_planned(feature_dir, wp_id, slug=mission_slug)
    emit_status_transition(TransitionRequest(
        feature_dir=feature_dir, mission_slug=mission_slug, wp_id=wp_id,
        to_lane="claimed", actor="implementer",
    ))
    emit_status_transition(TransitionRequest(
        feature_dir=feature_dir, mission_slug=mission_slug, wp_id=wp_id,
        to_lane="in_progress", actor="implementer",
    ))
    emit_status_transition(TransitionRequest(
        feature_dir=feature_dir, mission_slug=mission_slug, wp_id=wp_id,
        to_lane="for_review", actor="implementer", subtasks_complete=True,
    ))
    emit_status_transition(TransitionRequest(
        feature_dir=feature_dir, mission_slug=mission_slug, wp_id=wp_id,
        to_lane="in_review", actor="reviewer",
    ))


def _record_verdict(
    feature_dir: Path,
    wp_id: str,
    mission_slug: str,
    *,
    reviewer: str = "reviewer",
    reference: str = "PR#100",
) -> ReviewResult:
    """Record an ``approved`` verdict for *wp_id* through the emit seam."""
    review_result = ReviewResult(reviewer=reviewer, verdict="approved", reference=reference)
    emit_status_transition(TransitionRequest(
        feature_dir=feature_dir, mission_slug=mission_slug, wp_id=wp_id,
        to_lane="approved", actor=reviewer, review_result=review_result,
    ))
    return review_result


# ── T013 -- the event append is the authoritative durability write ──────


class TestT013EventAppendIsAuthoritative:
    """FR-008: the event-log append persists a recorded verdict; the
    reducer snapshot carries it after the append alone."""

    def test_review_result_transition_persists_via_event_append(self, feature_dir: Path) -> None:
        _advance_to_in_review(feature_dir, "WP01", _MISSION_SLUG)
        review_result = _record_verdict(feature_dir, "WP01", _MISSION_SLUG, reference="PR#101")

        lookup = event_sourced_review_result(feature_dir, "WP01")
        assert lookup.slot_present is True
        assert lookup.result == review_result

    def test_durability_depends_on_the_append_not_on_a_tautology(
        self, feature_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-vacuity guard (mirrors WP05's own commit-removal mutation
        pattern, ``test_matrix_is_sensitive_to_commit_removal``): if the
        authoritative append is neutered, the verdict must NOT be
        observable afterward -- proving the assertion above genuinely
        exercises the append rather than re-reading a pre-existing state."""
        _advance_to_in_review(feature_dir, "WP01", _MISSION_SLUG)

        def _neutered_append(*_args: Any, **_kwargs: Any) -> None:
            return None  # swallow the durability write entirely

        monkeypatch.setattr(
            emit_module._store, "append_event_stream_atomic_verified", _neutered_append
        )

        _record_verdict(feature_dir, "WP01", _MISSION_SLUG, reference="PR#102")

        lookup = event_sourced_review_result(feature_dir, "WP01")
        assert lookup.slot_present is False, (
            "the verdict should be unobservable once the authoritative append "
            "is neutered -- if it still appears, the positive assertion above "
            "was vacuous"
        )


# ── T012/SC-003 -- concurrent distinct verdicts are both durable ────────


def _mp_record_verdict(
    feature_dir: str,
    mission_slug: str,
    wp_id: str,
    reviewer: str,
    reference: str,
    result_queue: multiprocessing.Queue,
) -> None:
    """Worker target for the SC-003 concurrency harness (T012).

    Runs in a genuinely separate OS process -- ``feature_status_lock`` is an
    inter-process ``FileLock``, so a same-process/threaded harness would not
    exercise the real serialization boundary (mirrors ``tests/integration/
    test_review_durability_matrix.py``'s own SC-004 multiprocessing harness).
    Reports its outcome through a ``Queue`` rather than raising across the
    process boundary.
    """
    try:
        review_result = ReviewResult(reviewer=reviewer, verdict="approved", reference=reference)
        event = emit_status_transition(TransitionRequest(
            feature_dir=Path(feature_dir),
            mission_slug=mission_slug,
            wp_id=wp_id,
            to_lane="approved",
            actor=reviewer,
            review_result=review_result,
        ))
        result_queue.put(("ok", event.event_id))
    except Exception as exc:  # noqa: BLE001 -- report to the parent, never crash silently
        result_queue.put(("error", repr(exc)))


@pytest.mark.stress
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="multiprocessing 'fork' start method is POSIX-only",
)
def test_two_concurrent_distinct_verdicts_are_both_durable(feature_dir: Path) -> None:
    """SC-003: two concurrent distinct verdicts (different WPs, same
    mission) must both survive durably, or one must raise an explicit
    refusal -- never a silent drop."""
    _advance_to_in_review(feature_dir, "WP01", _MISSION_SLUG)
    _advance_to_in_review(feature_dir, "WP02", _MISSION_SLUG)

    ctx = multiprocessing.get_context("fork")
    queue: multiprocessing.Queue = ctx.Queue()
    proc_a = ctx.Process(
        target=_mp_record_verdict,
        args=(str(feature_dir), _MISSION_SLUG, "WP01", "reviewer-a", "PR#201", queue),
    )
    proc_b = ctx.Process(
        target=_mp_record_verdict,
        args=(str(feature_dir), _MISSION_SLUG, "WP02", "reviewer-b", "PR#202", queue),
    )
    proc_a.start()
    proc_b.start()
    results = [queue.get(timeout=30) for _ in range(2)]
    proc_a.join(timeout=30)
    proc_b.join(timeout=30)

    assert proc_a.exitcode == 0, f"worker A crashed (exitcode={proc_a.exitcode})"
    assert proc_b.exitcode == 0, f"worker B crashed (exitcode={proc_b.exitcode})"

    errors = [r for r in results if r[0] == "error"]
    oks = [r for r in results if r[0] == "ok"]
    assert oks, f"neither concurrent verdict succeeded (errors={errors})"

    # A fresh materialize from the parent guarantees we read the union of
    # both processes' appends, regardless of which one happened to finish
    # materializing last.
    materialize(feature_dir)

    if len(oks) == 2:
        # Both writers reported success -- SC-003 requires both durable.
        lookup_wp01 = event_sourced_review_result(feature_dir, "WP01")
        lookup_wp02 = event_sourced_review_result(feature_dir, "WP02")
        assert lookup_wp01.slot_present and lookup_wp01.result is not None
        assert lookup_wp02.slot_present and lookup_wp02.result is not None
        assert lookup_wp01.result.reference == "PR#201"
        assert lookup_wp02.result.reference == "PR#202"
    else:
        # SC-003 also accepts an explicit single-side refusal -- but exactly
        # one side must have refused, never a silent 2-for-2 "success" that
        # masks a half-written record.
        assert len(oks) == 1 and len(errors) == 1, (
            f"expected either 2 durable records or exactly one explicit "
            f"refusal, got oks={oks} errors={errors}"
        )


# ── T014 -- NFR-001 (no lock across git) + NFR-004 (single authoritative call) ──


class TestT014DurabilityStructuralGuarantees:
    """NFR-001: no inter-process lock is held across a ``git`` subprocess.
    NFR-004: exactly one authoritative durability-append call per verdict."""

    def test_no_subprocess_call_is_made_while_the_durability_lock_is_held(
        self, feature_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Names the NFR-001 mechanism concretely: instruments BOTH the lock
        context manager and ``subprocess.run`` (any ``git`` invoker included)
        and asserts no subprocess call is ever recorded while the real lock
        is held -- the event-log append discipline is the serialization,
        never a lock spanning a ``git`` subprocess."""
        _advance_to_in_review(feature_dir, "WP01", _MISSION_SLUG)

        lock_state = {"held": False}
        real_lock = emit_module.feature_status_lock
        calls_while_locked: list[tuple[Any, ...]] = []
        real_run = subprocess.run

        @contextmanager
        def _instrumented_lock(*args: Any, **kwargs: Any):
            with real_lock(*args, **kwargs) as lock_path:
                lock_state["held"] = True
                try:
                    yield lock_path
                finally:
                    lock_state["held"] = False

        def _spy_run(*args: Any, **kwargs: Any) -> Any:
            if lock_state["held"]:
                calls_while_locked.append(args)
            return real_run(*args, **kwargs)

        monkeypatch.setattr(emit_module, "feature_status_lock", _instrumented_lock)
        monkeypatch.setattr(subprocess, "run", _spy_run)

        _record_verdict(feature_dir, "WP01", _MISSION_SLUG, reference="PR#401")

        assert calls_while_locked == [], (
            "a subprocess call was made while the feature_status_lock was "
            f"held (NFR-001 violation): {calls_while_locked}"
        )

    def test_exactly_one_authoritative_append_per_recorded_verdict(
        self, feature_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NFR-004: exactly one authoritative ``emit_status_transition``
        append occurs per recorded verdict. The best-effort ``.md`` render
        commit is excluded from this count by construction -- this test
        never calls into ``review/cycle.py``."""
        _advance_to_in_review(feature_dir, "WP01", _MISSION_SLUG)

        call_count = {"n": 0}
        real_append = emit_module._store.append_event_stream_atomic_verified

        def _counting_append(*args: Any, **kwargs: Any) -> None:
            call_count["n"] += 1
            real_append(*args, **kwargs)

        monkeypatch.setattr(
            emit_module._store, "append_event_stream_atomic_verified", _counting_append
        )

        _record_verdict(feature_dir, "WP01", _MISSION_SLUG, reference="PR#301")

        assert call_count["n"] == 1, (
            "NFR-004 requires exactly one authoritative durability-append "
            f"call per recorded verdict; observed {call_count['n']}"
        )


# ── T015 -- NFR-005 responsiveness ───────────────────────────────────────


class TestT015Responsiveness:
    """NFR-005: verdict recording, including durable persistence, completes
    under the existing 2-second budget."""

    def test_verdict_recording_completes_under_two_seconds(self, feature_dir: Path) -> None:
        _advance_to_in_review(feature_dir, "WP01", _MISSION_SLUG)

        started = time.monotonic()
        _record_verdict(feature_dir, "WP01", _MISSION_SLUG, reference="PR#501")
        elapsed = time.monotonic() - started

        assert elapsed < 2.0, (
            f"verdict recording took {elapsed:.3f}s, exceeding the NFR-005 2s budget"
        )
