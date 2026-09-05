"""Tests for the core tail-reader primitives (mission event-push-watch-channel, WP01).

Covers FR-002 (offset-resumable reads), FR-003 (reopen-by-path), FR-006 (mid-line JSON
tear tolerance), and FR-008 (wait for a not-yet-created log file). See
``kitty-specs/event-push-watch-channel-01M1K6W2/tasks/WP01-core-tail-reader-primitives.md``
for the full subtask breakdown these tests satisfy.

Marker/CI discipline (C-008/SK-144): this module is collected by ``fast-tests-status``
(``.github/workflows/ci-quality.yml``, path filter ``tests/status/ tests/specify_cli/status/``,
marker ``fast and not windows_ci and not (git_repo or integration or stress)``).
"""

from __future__ import annotations

import itertools
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from specify_cli.status import tail_reader
from specify_cli.status.store import StoreError
from specify_cli.status.tail_reader import EMPTY_DIGEST, ResumeRefused, TailCursor, poll_once

pytestmark = [pytest.mark.fast]


def test_torn_trailing_line_retried_then_emitted_once(tmp_path: Path) -> None:
    """User Story 4: a torn trailing line is retried, never signaled, emitted once.

    T001 (ATDD, red-first): pins the exact contract before ``poll_once()`` exists.
    Simulates SK-131's measured mid-write catch (a writer's ``write(2)`` for one
    line only partially flushed) with a ``tmp_path``-based synthetic log file --
    never a real ``kitty-specs/`` mission dir (C-007 immutable-roots hygiene).
    """
    log_path = tmp_path / "status.events.jsonl"
    complete_line = json.dumps({"event": "one"}) + "\n"
    # Deliberately non-``\n``-terminated partial-JSON fragment: syntactically
    # incomplete/invalid JSON at this moment, simulating a writer caught mid-``write(2)``.
    torn_fragment = '{"event": "two", "detail": "unterminated'
    log_path.write_bytes((complete_line + torn_fragment).encode("utf-8"))

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    result = poll_once(log_path, cursor)

    # The torn tail is not signaled as an error or truncation, and emits nothing yet.
    assert [event["event"] for event in result.events] == ["one"]
    # The cursor's offset must not advance past the last complete `\n`-terminated line.
    assert result.cursor.offset == len(complete_line.encode("utf-8"))

    # Complete the torn line: append the missing bytes plus the terminating `\n`.
    completion = '", "trailing": "done"}\n'
    with log_path.open("ab") as fh:
        fh.write(completion.encode("utf-8"))

    result_after_completion = poll_once(log_path, result.cursor)

    # The now-complete line is parsed and emitted exactly once -- never duplicated,
    # never dropped, and no error/truncation signal appears anywhere in the sequence.
    assert [event["event"] for event in result_after_completion.events] == ["two"]
    assert result_after_completion.cursor.offset == log_path.stat().st_size


def test_poll_once_fd_sharing_invariant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T007: ``poll_once()`` opens the file exactly once and never calls ``Path.stat()``.

    Gives ``Path.stat`` and ``Path.open`` DIFFERENT tolerance semantics -- this is
    deliberate, not a simplification. A shared "after initial open" condition applied
    to both would silently pass the plan's own named lazy implementation
    (``path.stat().st_size`` for the cheap size check, followed by a *separate*
    ``path.open("rb")`` for the actual read): in that pattern ``Path.stat()`` fires
    BEFORE the one ``Path.open()`` call, so an "after initial open" guard on
    ``Path.stat`` never triggers for it, and the open-call-count check alone still
    passes unchanged (there is still only one ``open()`` call total). What actually
    closes the gap is the ASYMMETRIC pairing used here: ``Path.stat`` raises
    UNCONDITIONALLY on any invocation (catching the lazy pattern's call regardless of
    ordering), combined SEPARATELY with an exactly-one-total-call count on
    ``Path.open`` (catching a genuinely duplicated ``open()``).

    Patches ``pathlib.Path.open`` specifically -- NOT ``os.open``: ``Path.open()``
    does not route through the ``os`` module's Python-level ``os.open()`` (verified
    empirically in plan.md: patching ``os.open`` alone records zero calls for a real
    ``Path(...).open("rb")`` read), so patching the wrong target would silently never
    fire and give false confidence.

    As a side effect of the unconditional ``Path.stat`` raise applying to the ENTIRE
    ``poll_once()`` call, this also mechanically verifies T006: the missing-file check
    must be implemented as ``try``/``except FileNotFoundError`` around the single
    ``path.open("rb")`` call, never via ``Path.exists()``/``Path.is_file()``/
    ``Path.is_dir()`` -- those call ``Path.stat()`` internally on Python 3.11/3.12
    (this repo's required/CI-pinned interpreters), which would trip this test's
    unconditional raise on EVERY ``poll_once()`` call, not only missing-file ones.
    This test runs against a call where the file DOES exist, so its pass here is
    evidence T006 does not route through those pathlib convenience methods.
    """
    log_path = tmp_path / "status.events.jsonl"
    log_path.write_bytes((json.dumps({"event": "one"}) + "\n").encode("utf-8"))

    def _stat_raises(self: Path, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unexpected Path.stat() call inside poll_once()")

    monkeypatch.setattr(Path, "stat", _stat_raises)

    real_open = Path.open
    open_calls: list[Path] = []

    def _counting_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        open_calls.append(self)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _counting_open)

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    result = poll_once(log_path, cursor)

    assert [event["event"] for event in result.events] == ["one"]
    assert len(open_calls) == 1


def test_offset_resume_across_two_polls(tmp_path: Path) -> None:
    """T008: offset-resume correctness across two ``poll_once()`` calls (FR-002).

    A log with N events, polled once, then M more events appended and polled again --
    the second call yields exactly the M new events, none of the original N re-emitted,
    none dropped.
    """
    log_path = tmp_path / "status.events.jsonl"
    initial_events = [{"event": f"first-{i}"} for i in range(3)]
    log_path.write_text("".join(json.dumps(event) + "\n" for event in initial_events), encoding="utf-8")

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    first = poll_once(log_path, cursor)
    assert [event["event"] for event in first.events] == [event["event"] for event in initial_events]

    more_events = [{"event": f"second-{i}"} for i in range(2)]
    with log_path.open("a", encoding="utf-8") as fh:
        for event in more_events:
            fh.write(json.dumps(event) + "\n")

    second = poll_once(log_path, first.cursor)
    assert [event["event"] for event in second.events] == [event["event"] for event in more_events]


def test_poll_once_observes_new_inode_after_os_replace(tmp_path: Path) -> None:
    """T008: ``os.replace()``-swapped-inode correctness (FR-003).

    Mirrors the writer's own locked-append idiom (``store.py:392``): write new content
    to a temp path in the same directory, then ``os.replace(tmp_path, original_path)``.
    The reader must observe the new inode's content correctly at the resumed offset,
    never stale data from the old, now-unlinked inode -- directly exercising the
    reopen-by-path guarantee (T003).
    """
    log_path = tmp_path / "status.events.jsonl"
    log_path.write_text(json.dumps({"event": "one"}) + "\n", encoding="utf-8")

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    first = poll_once(log_path, cursor)
    assert [event["event"] for event in first.events] == ["one"]

    replacement = tmp_path / "status.events.jsonl.tmp"
    replaced_content = json.dumps({"event": "one"}) + "\n" + json.dumps({"event": "two-after-replace"}) + "\n"
    replacement.write_text(replaced_content, encoding="utf-8")
    os.replace(replacement, log_path)

    second = poll_once(log_path, first.cursor)
    assert [event["event"] for event in second.events] == ["two-after-replace"]


def test_poll_once_waits_for_missing_file_then_streams(tmp_path: Path) -> None:
    """T008: missing-file wait (FR-008).

    ``poll_once()`` against a ``tmp_path`` that does not exist yet reports "no data
    yet" without raising; once the file is created, a subsequent call behaves as an
    ordinary first poll against a populated file.
    """
    log_path = tmp_path / "status.events.jsonl"
    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)

    result = poll_once(log_path, cursor)
    assert result.file_present is False
    assert result.events == []
    assert result.cursor == cursor

    log_path.write_text(json.dumps({"event": "arrived"}) + "\n", encoding="utf-8")
    after_creation = poll_once(log_path, result.cursor)
    assert after_creation.file_present is True
    assert [event["event"] for event in after_creation.events] == ["arrived"]


def test_interior_corrupt_line_raises_distinct_from_tear(tmp_path: Path) -> None:
    """T005/T008: an interior, `\\n`-terminated chunk that fails to parse raises.

    Distinct from the tear-retry path (T001): appends only ever extend the file at
    the end, so a torn write can only ever manifest as an incomplete *trailing*
    sequence. An already-``\\n``-terminated interior chunk that fails to parse
    indicates corruption, not an in-flight write -- this mirrors
    ``read_events_raw()``'s existing "raise on bad JSON" precedent
    (``src/specify_cli/status/store.py:554``) rather than inventing new
    silent-tolerance behavior NFR-003 would then have to justify.
    """
    log_path = tmp_path / "status.events.jsonl"
    log_path.write_bytes(b'{"event": "ok"}\nnot-json\n{"event": "unreached"}\n')

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    with pytest.raises(json.JSONDecodeError):
        poll_once(log_path, cursor)


@pytest.mark.parametrize("bad_line", [b"[1, 2]", b"42", b'"x"', b"true", b"null"])
def test_interior_non_object_line_raises_store_error(tmp_path: Path, bad_line: bytes) -> None:
    """A valid-JSON but non-object interior line is corruption, not a tear.

    Landing-squad finding: ``poll_once`` parsed the line then wrote reader keys
    (``parsed["tail_offset"] = ...``) with no ``isinstance(parsed, dict)`` guard,
    so a scalar/array line raised an opaque ``TypeError`` instead of the canonical
    corruption error. This pins the guard to ``store.read_events_raw()``'s contract
    (``StoreError`` "expected JSON object", ``store.py:555``) — the single authority
    for "what is a valid event line".
    """
    log_path = tmp_path / "status.events.jsonl"
    log_path.write_bytes(b'{"event": "ok"}\n' + bad_line + b'\n{"event": "unreached"}\n')

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    with pytest.raises(StoreError, match="expected JSON object"):
        poll_once(log_path, cursor)


def test_poll_once_no_new_bytes_returns_unchanged_cursor(tmp_path: Path) -> None:
    """T004/T008: polling again with no new bytes since the last poll is an ordinary
    no-op -- ``size <= cursor.offset`` -- never truncation (the size-shrink/hash-mismatch
    truncation checks are WP02's FR-005 scope, not this WP's)."""
    log_path = tmp_path / "status.events.jsonl"
    log_path.write_text(json.dumps({"event": "one"}) + "\n", encoding="utf-8")

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    first = poll_once(log_path, cursor)
    assert [event["event"] for event in first.events] == ["one"]

    second = poll_once(log_path, first.cursor)
    assert second.events == []
    assert second.cursor == first.cursor
    assert second.file_present is True


def test_poll_once_pure_tear_from_offset_zero_leaves_cursor_unchanged(
    tmp_path: Path,
) -> None:
    """T005/T008: a poll whose ENTIRE newly-available content is an unterminated tear
    (no prior complete line in this batch) advances nothing and reports no events --
    exercising the "no new complete line consumed this poll" branch distinctly from
    T001 (which pairs a tear with one already-complete leading line)."""
    log_path = tmp_path / "status.events.jsonl"
    log_path.write_bytes(b'{"event": "half-writ')

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    result = poll_once(log_path, cursor)

    assert result.events == []
    assert result.cursor == cursor


def test_resume_refused_carries_reason_and_message() -> None:
    """T002: ``ResumeRefused`` is a raiseable exception with a ``.reason`` attribute
    and a human-readable ``str(exc)`` -- this WP only needs the shape to exist; WP02's
    ``validate_resume_cursor()`` supplies the actual raise sites."""
    exc = ResumeRefused("out_of_range")
    assert exc.reason == "out_of_range"
    assert "out_of_range" in str(exc)


def test_tail_events_bounded_termination_zero_real_sleep(tmp_path: Path) -> None:
    """T016 (ATDD, red-first): `tail_events()` with an injected no-op `sleep_fn` and
    `max_events=N` terminates deterministically and yields exactly N envelopes, with
    zero real wall-clock wait.

    Failing-first against WP02's final commit (this WP's own starting state):
    `poll_once()` and `validate_resume_cursor()` already exist there, so this test
    calls `tail_events` as an ATTRIBUTE of the already-importable `tail_reader` module
    (`from specify_cli.status import tail_reader`) rather than via a
    `from ... import tail_events` statement -- so the undefined symbol raises a precise
    `AttributeError: module 'specify_cli.status.tail_reader' has no attribute
    'tail_events'`, not a module-collection failure that would also break every other
    test in this file.

    The monotonic-clock delta assertion (not merely "returned a list of length N") is
    what distinguishes this from a weaker test: a `sleep_fn` that silently still calls
    the real `time.sleep` internally before invoking the injected callable would still
    return N items but would NOT pass this timing bound.
    """
    log_path = tmp_path / "status.events.jsonl"
    events_to_write = [{"event": f"line-{i}"} for i in range(3)]
    log_path.write_text("".join(json.dumps(event) + "\n" for event in events_to_write), encoding="utf-8")

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)

    start = time.monotonic()
    yielded = list(tail_reader.tail_events(log_path, cursor, max_events=3, sleep_fn=lambda _: None))
    elapsed = time.monotonic() - start

    assert [event["event"] for event in yielded] == [event["event"] for event in events_to_write]
    # Generous CI-safe bound: far below even one real DEFAULT_POLL_INTERVAL_SECONDS
    # (0.25s) sleep -- proves the injected no-op sleep_fn was actually honored, not
    # silently bypassed in favor of the real time.sleep.
    assert elapsed < 0.05


def test_tail_events_sleep_fn_never_called_when_poll_produces_output(
    tmp_path: Path,
) -> None:
    """T019(a): when every poll produces output, `sleep_fn` must never be invoked --
    a backlog drains at full speed with no artificial delay between items, per T017's
    explicit "never sleep when a poll DID produce output" behavior.

    Distinct assertion from T016: T016 proves termination + zero real sleep via a
    monotonic-clock bound; this test proves the *mechanism* -- a call-counting
    `sleep_fn` stub asserted to an EXACT zero count, not just "the test finished
    quickly." A generator that (incorrectly) called `sleep_fn` on every poll,
    including productive ones, would still terminate fast with a no-op stub and pass
    T016's timing bound, but would fail this exact-count assertion.
    """
    log_path = tmp_path / "status.events.jsonl"
    events_to_write = [{"event": f"line-{i}"} for i in range(4)]
    log_path.write_text("".join(json.dumps(event) + "\n" for event in events_to_write), encoding="utf-8")

    call_count = 0

    def _counting_sleep(interval: float) -> None:
        nonlocal call_count
        call_count += 1

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    yielded = list(tail_reader.tail_events(log_path, cursor, max_events=4, sleep_fn=_counting_sleep))

    assert [event["event"] for event in yielded] == [event["event"] for event in events_to_write]
    assert call_count == 0


def test_tail_events_islice_bound_mid_consumption_append_via_sleep_fn_stub(
    tmp_path: Path,
) -> None:
    """T019(b), MANDATORY shape -- User Story 1 Acceptance Scenario 2, end-to-end
    through `tail_events()`: a writer appending WHILE `events tail` is actively
    running, the appended event surfaced within one poll interval. Exercised with
    ZERO real wall-clock sleep anywhere in this test.

    The fixture starts with FEWER than N events on disk (N - 1); the remaining event
    is appended from WITHIN the `sleep_fn` stub itself -- on the poll where it is not
    yet present -- which is the synchronization point standing in for "the writer
    appends between polls." No `time.sleep`, `threading.Event.wait` with a real
    timeout, or any other real-time wait is used anywhere: the injected `sleep_fn`
    callback IS the only synchronization mechanism.

    Bounded via `itertools.islice(tail_events(...), N)` (NOT the generator's own
    internal `max_events` kwarg), per T019(b)'s required shape. This is deliberately
    NOT a degenerate substitute that pre-writes all N events up front before calling
    `tail_events()` -- that shape never exercises a writer appending mid-consumption
    and is explicitly disallowed as a stand-in for this scenario.
    """
    log_path = tmp_path / "status.events.jsonl"
    n = 3
    up_front_events = [{"event": f"line-{i}"} for i in range(n - 1)]
    log_path.write_text("".join(json.dumps(event) + "\n" for event in up_front_events), encoding="utf-8")
    appended_event = {"event": "appended-mid-consumption"}

    call_count = 0

    def _appending_sleep_stub(interval: float) -> None:
        nonlocal call_count
        call_count += 1
        # Synchronization point: the FIRST "nothing new yet" poll appends the
        # remaining event from *inside* this stub -- zero real time.sleep, zero
        # threading.Event.wait, no real-time wait anywhere in this test.
        if call_count == 1:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(appended_event) + "\n")

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    bounded = itertools.islice(tail_reader.tail_events(log_path, cursor, sleep_fn=_appending_sleep_stub), n)
    yielded = list(bounded)

    expected_events = [*up_front_events, appended_event]
    assert [event["event"] for event in yielded] == [event["event"] for event in expected_events]
    # Exactly one "nothing new" poll triggered the append -- proves sleep_fn (not
    # time.sleep) drives the no-new-data path, not merely that the test finished.
    assert call_count == 1
