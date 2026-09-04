"""Truncation-detection tests for the tail-reader core (mission event-push-watch-channel, WP02).

Covers FR-005 (size check AND independent, every-poll hash check), FR-007 (clean
record-boundary truncation detected even when the remainder still parses), and
FR-013 (``validate_resume_cursor()``'s structural-then-content refusal sequence). See
``kitty-specs/event-push-watch-channel-01M1K6W2/tasks/WP02-truncation-detection.md``
for the full subtask breakdown these tests satisfy.

**ATDD precision (WP02 prompt, Context section)**: T009 and T010 (this file's first
two test functions) must fail against WP01's final commit for an ASSERTION about
missing ``log_truncated`` behavior -- NOT a collection error -- because
``poll_once()`` already exists (WP01 created it); it simply has zero truncation
detection yet. That is why this module's imports below deliberately start narrow
(``EMPTY_DIGEST``, ``TailCursor``, ``poll_once`` only) and only pick up
``ResumeRefused``/``validate_resume_cursor`` once this WP's own T012 implementation
commit has landed -- importing a not-yet-existing symbol at T009/T010's commit time
would produce the WRONG kind of red (a collection error, which is T012's expected
red shape, not T009/T010's).

Marker/CI discipline (C-008/SK-144): this module is collected by ``fast-tests-status``
(``.github/workflows/ci-quality.yml``, path filter ``tests/status/ tests/specify_cli/status/``,
marker ``fast and not windows_ci and not (git_repo or integration or stress)``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.status.tail_reader import (
    EMPTY_DIGEST,
    ResumeRefused,
    TailCursor,
    poll_once,
    validate_resume_cursor,
)

pytestmark = [pytest.mark.fast]


def _write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    """Write ``events`` as a fresh JSONL file (overwriting any existing content)."""
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")


def test_clean_boundary_truncation_detected_via_size_check_even_when_parseable(
    tmp_path: Path,
) -> None:
    """T009 (User Story 2 AC1 / Edge Cases shape-(b)): a clean record-boundary
    truncation -- the file shrinks to an earlier line boundary and stays shrunk,
    with NO regrow -- must be detected as truncation via the size check
    (``current_size < O``), even though the remaining bytes still parse as valid
    JSON on their own.

    This reproduces, as its own separately-named test, the exact scenario a
    sibling mission's ``design-status`` verb was rejected at severity 4 for: a
    reader that only tests the mid-line tear shape (shape-(a), WP01's T001) and
    never plain clean-boundary truncation (shape-(b)) reports a confidently wrong
    (incomplete) result on a rollback that lands exactly at a line boundary.
    """
    log_path = tmp_path / "status.events.jsonl"
    all_events = [{"event": f"line-{i}"} for i in range(4)]
    _write_jsonl(log_path, all_events)

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    consumed = poll_once(log_path, cursor)
    assert [event["event"] for event in consumed.events] == [
        event["event"] for event in all_events
    ]
    offset_o = consumed.cursor.offset
    assert offset_o == log_path.stat().st_size

    # Truncate the file at an EARLIER line boundary (after the first two events)
    # -- a clean record-boundary shrink with NO regrow: the file just shrinks and
    # stays shrunk. `boundary` is guaranteed to land on a `\n` because it is the
    # byte length of a prefix of complete JSONL lines.
    original_bytes = log_path.read_bytes()
    first_two_serialized = "".join(
        json.dumps(event) + "\n" for event in all_events[:2]
    ).encode("utf-8")
    boundary = len(first_two_serialized)
    assert original_bytes[:boundary] == first_two_serialized
    log_path.write_bytes(original_bytes[:boundary])
    assert log_path.stat().st_size == boundary < offset_o

    # Self-check the fixture itself (T009 step 5): the remaining bytes DO parse as
    # valid JSON -- this assertion is what proves the fixture exercises shape-(b),
    # not shape-(a); it must fail if the fixture were ever changed to produce a
    # mid-line tear instead.
    remaining_bytes = log_path.read_bytes()
    for line in remaining_bytes.splitlines():
        json.loads(line)

    result = poll_once(log_path, consumed.cursor)

    # Detected via the size check (`current_size < O`), independent of the fact
    # (proven above) that the remainder still parses cleanly -- shape-(b)'s whole
    # point per FR-007: parsing is never consulted to decide truncation.
    assert result.events == [
        {
            "type": "log_truncated",
            "reason": "size_shrink",
            "detected_at_offset": offset_o,
            "tail_offset": 0,
            "tail_invariant": EMPTY_DIGEST,
        }
    ]
    assert result.cursor == TailCursor(offset=0, content_invariant=EMPTY_DIGEST)

    # Recovery half of the resync (User Story 2 AC2): re-poll from the resynced
    # cursor and confirm exactly what's actually present post-truncation is
    # (re-)emitted -- nothing fabricated, nothing from the gone-forever tail
    # replayed.
    recovered = poll_once(log_path, result.cursor)
    assert [event["event"] for event in recovered.events] == [
        event["event"] for event in all_events[:2]
    ]
    assert recovered.cursor.offset == boundary


def test_truncate_then_regrow_within_one_poll_detected_via_hash_check(
    tmp_path: Path,
) -> None:
    """T010 (User Story 2 AC3): a rollback truncation immediately followed by a
    regrowth -- both completing within a single poll interval, before the reader's
    next ``poll_once()`` call samples the file -- must be caught by the hash check,
    even though the size check alone (``current_size < O``) would report "grew,
    looks fine."

    This is a separately-named test from T009 above -- not a ``parametrize`` case,
    not a shared function body -- per the WP02 prompt's explicit warning (and
    plan.md's IC-02 ATDD requirement) that the three truncation shapes across this
    mission must each be independently nameable in a CI failure's test node ID.

    Committed BEFORE the hash check exists in ``tail_reader.py``: it is red on
    WP01's final commit, and stays red immediately after T009's own
    size-check-only implementation lands (a pure size check cannot see a race that
    ends at or above the pre-truncation offset).
    """
    log_path = tmp_path / "status.events.jsonl"
    original_events = [{"event": f"orig-{i}"} for i in range(3)]
    _write_jsonl(log_path, original_events)

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    consumed = poll_once(log_path, cursor)
    assert [event["event"] for event in consumed.events] == [
        event["event"] for event in original_events
    ]
    offset_o = consumed.cursor.offset

    # Simulate a rollback truncate (below O) immediately followed by a regrowth
    # with DIFFERENT content, both completing within a single poll interval.
    #
    # The first 3 regrown lines are BYTE-LENGTH-IDENTICAL to the 3 original lines
    # (same key, same-length value: "orig-N" <-> "flip-N", both 6 chars) so the
    # regrown file's byte range [0, offset_o) ends in a `\n` at exactly the same
    # position as the original -- i.e. offset_o is STILL a clean line boundary in
    # the regrown file, so a naive read from offset_o never trips over a JSON
    # fragment. This isolates the test to the ONE thing it must prove: content at
    # that boundary silently changed (caught only by the hash check), not "the
    # offset now points mid-line" (a different, already-covered failure shape).
    # Two further NEW lines are appended after that boundary so the regrown file's
    # size is strictly greater than offset_o (never merely equal), and so a
    # WP01-baseline read (no hash check) has real "new" content to wrongly accept
    # as legitimate growth.
    flipped_events = [{"event": f"flip-{i}"} for i in range(3)]
    extra_events = [{"event": f"new-after-regrow-{i}"} for i in range(2)]
    regrown_events = flipped_events + extra_events
    _write_jsonl(log_path, regrown_events)

    flipped_prefix = "".join(json.dumps(event) + "\n" for event in flipped_events).encode(
        "utf-8"
    )
    assert len(flipped_prefix) == offset_o, (
        "fixture precondition: the flipped prefix must be byte-length-identical "
        "to the original 3 lines so offset_o stays a clean line boundary"
    )

    # The test's own precondition, asserted immediately before the call under
    # test (WP02 T010 step 3): the regrown size is >= O, so the size check alone
    # could never observe a shrink here -- this is what makes "cannot pass by
    # accident via the size check alone" self-evident from the test body itself.
    assert log_path.stat().st_size > offset_o

    result = poll_once(log_path, consumed.cursor)

    # Caught via the hash check -- the content-invariant mismatch -- even though
    # the size check alone would have reported "grew, looks fine."
    assert result.events == [
        {
            "type": "log_truncated",
            "reason": "content_mismatch",
            "detected_at_offset": offset_o,
            "tail_offset": 0,
            "tail_invariant": EMPTY_DIGEST,
        }
    ]
    assert result.cursor == TailCursor(offset=0, content_invariant=EMPTY_DIGEST)

    # Recovery half of the resync (User Story 2 AC2): re-poll from the resynced
    # cursor and confirm the regrown file's actual content from offset 0 onward is
    # (re-)emitted -- none of the pre-truncation (now-gone) events fabricated or
    # replayed.
    recovered = poll_once(log_path, result.cursor)
    assert [event["event"] for event in recovered.events] == [
        event["event"] for event in regrown_events
    ]


def test_poll_once_fd_sharing_invariant_for_hash_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T013: `poll_once()`'s hash-check read shares the one fd opened at the top of
    the call -- `Path.stat()` is NEVER called (unconditional raise, not just
    "after initial open"), and `Path.open()` is called exactly ONE time total --
    on a poll that actually exercises the hash check (`current_size >=
    cursor.offset`), closing the gap WP01's own fd-sharing test
    (`test_poll_once_fd_sharing_invariant` in `test_tail_reader.py`) could not
    close: the hash check did not exist yet in WP01.

    Reuses this file's truncate-then-regrow fixture shape (see
    `test_truncate_then_regrow_within_one_poll_detected_via_hash_check` above) so
    the hash check genuinely runs this poll, not just the size check + drain read
    WP01's T007 already covered. Same corrected asymmetric pattern as WP01's T007
    -- see that test's docstring for the full derivation of why a shared "after
    initial open" condition would silently pass the plan's own named lazy
    `path.stat()`-then-second-`open()` pattern.
    """
    log_path = tmp_path / "status.events.jsonl"
    original_events = [{"event": f"orig-{i}"} for i in range(3)]
    _write_jsonl(log_path, original_events)

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    consumed = poll_once(log_path, cursor)
    offset_o = consumed.cursor.offset

    flipped_events = [{"event": f"flip-{i}"} for i in range(3)]
    extra_events = [{"event": f"new-after-regrow-{i}"} for i in range(2)]
    _write_jsonl(log_path, flipped_events + extra_events)
    assert log_path.stat().st_size > offset_o  # hash check must run, not size check

    def _stat_raises(self: Path, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unexpected Path.stat() call inside poll_once()")

    monkeypatch.setattr(Path, "stat", _stat_raises)

    real_open = Path.open
    open_calls: list[Path] = []

    def _counting_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        open_calls.append(self)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _counting_open)

    result = poll_once(log_path, consumed.cursor)

    assert result.events[0]["type"] == "log_truncated"
    assert result.events[0]["reason"] == "content_mismatch"
    assert len(open_calls) == 1


def test_validate_resume_cursor_fd_sharing_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T014: `validate_resume_cursor()` shares ONE fd across the structural
    (in-range) check, the backward scan, AND the hash-check read -- `Path.stat()`
    is NEVER called (unconditional raise on ANY invocation, no "after initial
    open" carve-out), and `Path.open()` (never `os.open`) is called exactly ONE
    time total for the whole call. Same corrected asymmetric pattern as T013/WP01's
    T007 -- see WP01's `test_poll_once_fd_sharing_invariant` docstring for the full
    derivation of why a shared "after initial open" condition would silently pass
    the plan's own named lazy `path.stat()`-then-second-`open()` implementation.
    """
    log_path = tmp_path / "status.events.jsonl"
    events = [{"event": f"line-{i}"} for i in range(3)]
    _write_jsonl(log_path, events)

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    consumed = poll_once(log_path, cursor)
    offset_o = consumed.cursor.offset
    invariant_at_o = consumed.cursor.content_invariant

    def _stat_raises(self: Path, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "unexpected Path.stat() call inside validate_resume_cursor()"
        )

    monkeypatch.setattr(Path, "stat", _stat_raises)

    real_open = Path.open
    open_calls: list[Path] = []

    def _counting_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        open_calls.append(self)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _counting_open)

    result = validate_resume_cursor(log_path, offset_o, invariant_at_o)

    assert result == TailCursor(offset=offset_o, content_invariant=invariant_at_o)
    assert len(open_calls) == 1


# ---------------------------------------------------------------------------
# T015 -- remaining FR-013 refusal shapes, the resume SUCCESS path, and the
# opt-in-without-invariant structural-only path.
# ---------------------------------------------------------------------------


def test_validate_resume_cursor_refuses_negative_offset(tmp_path: Path) -> None:
    """FR-013 structural refusal shape: a negative offset is always refused,
    regardless of whether a log file even exists yet."""
    log_path = tmp_path / "status.events.jsonl"
    _write_jsonl(log_path, [{"event": "one"}])

    with pytest.raises(ResumeRefused) as exc_info:
        validate_resume_cursor(log_path, -1, None)
    assert exc_info.value.reason == "negative"


def test_validate_resume_cursor_refuses_out_of_range_offset(tmp_path: Path) -> None:
    """FR-013 structural refusal shape: an offset beyond the current file size is
    refused -- never silently clamped to the actual size."""
    log_path = tmp_path / "status.events.jsonl"
    _write_jsonl(log_path, [{"event": "one"}])
    file_size = log_path.stat().st_size

    with pytest.raises(ResumeRefused) as exc_info:
        validate_resume_cursor(log_path, file_size + 100, None)
    assert exc_info.value.reason == "out_of_range"


def test_validate_resume_cursor_refuses_misaligned_offset(tmp_path: Path) -> None:
    """FR-013 structural refusal shape: an offset that is structurally in-range
    but not immediately after a `\\n` (not on a line boundary) is refused -- never
    silently rounded/guessed to the nearest boundary."""
    log_path = tmp_path / "status.events.jsonl"
    _write_jsonl(log_path, [{"event": "one"}, {"event": "two"}])

    # Offset 1 is mid-line (inside the first line's JSON body), not immediately
    # after a `\n`.
    with pytest.raises(ResumeRefused) as exc_info:
        validate_resume_cursor(log_path, 1, None)
    assert exc_info.value.reason == "misaligned"


def test_validate_resume_cursor_refuses_content_mismatch(tmp_path: Path) -> None:
    """FR-013 content refusal shape: a structurally valid offset with a supplied,
    mismatched content invariant is refused -- e.g. a rollback-then-regrow that
    completed entirely while the consumer was offline (the same failure class
    FR-005 detects live, per FR-013's own text)."""
    log_path = tmp_path / "status.events.jsonl"
    _write_jsonl(log_path, [{"event": "one"}, {"event": "two"}])
    file_size = log_path.stat().st_size

    wrong_invariant = hashlib.sha256(  # noqa: TID251 — file-integrity content
        # invariant for a deliberately-wrong test fixture value (proving the
        # comparison actually fires), not the charter hash.
        b"deliberately-wrong-content-not-actually-in-the-file"
    ).hexdigest()

    with pytest.raises(ResumeRefused) as exc_info:
        validate_resume_cursor(log_path, file_size, wrong_invariant)
    assert exc_info.value.reason == "content_mismatch"


def test_validate_resume_cursor_accepts_offset_only_without_invariant(
    tmp_path: Path,
) -> None:
    """FR-013's explicit "opt-in" clause: `--from-offset` supplied without a
    paired `--from-invariant` applies ONLY the structural checks -- no content
    comparison happens, and the returned cursor still carries a usable (derived,
    not compared) content invariant for future live polling."""
    log_path = tmp_path / "status.events.jsonl"
    initial_events = [{"event": f"line-{i}"} for i in range(3)]
    _write_jsonl(log_path, initial_events)

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    consumed = poll_once(log_path, cursor)
    offset_o = consumed.cursor.offset

    resumed_cursor = validate_resume_cursor(log_path, offset_o, None)
    assert resumed_cursor.offset == offset_o
    assert resumed_cursor.content_invariant == consumed.cursor.content_invariant


def test_validate_resume_cursor_accepts_structurally_valid_offset_and_resumes_correctly(
    tmp_path: Path,
) -> None:
    """T015 step 2 (User Story 3 AC1): the SUCCESS path of a resume -- the
    mission's headline P2 resumability guarantee. Every other test in this WP
    exercises only `validate_resume_cursor()`'s REFUSAL branches; this proves the
    accept path actually resumes correctly (exactly the newly-appended events are
    yielded on the next poll, none of the pre-resume events re-emitted, none
    skipped), not merely that no exception was raised.
    """
    log_path = tmp_path / "status.events.jsonl"
    initial_events = [{"event": f"line-{i}"} for i in range(3)]
    _write_jsonl(log_path, initial_events)

    cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    consumed = poll_once(log_path, cursor)
    offset_o = consumed.cursor.offset
    invariant_at_o = consumed.cursor.content_invariant

    resumed_cursor = validate_resume_cursor(log_path, offset_o, invariant_at_o)
    assert resumed_cursor == TailCursor(
        offset=offset_o, content_invariant=invariant_at_o
    )

    new_events = [{"event": f"appended-{i}"} for i in range(2)]
    with log_path.open("a", encoding="utf-8") as fh:
        for event in new_events:
            fh.write(json.dumps(event) + "\n")

    result = poll_once(log_path, resumed_cursor)
    assert [event["event"] for event in result.events] == [
        event["event"] for event in new_events
    ]


def test_validate_resume_cursor_accepts_offset_zero_on_an_existing_file(
    tmp_path: Path,
) -> None:
    """FR-013: offset 0 is always structurally valid (nothing consumed yet), even
    against a populated, existing file -- and its derived content invariant is
    always ``EMPTY_DIGEST`` regardless of what the file actually contains, since
    the backward scan for "the start of the last line" at offset 0 has no prior
    line to look for."""
    log_path = tmp_path / "status.events.jsonl"
    _write_jsonl(log_path, [{"event": "one"}, {"event": "two"}])

    resumed_cursor = validate_resume_cursor(log_path, 0, EMPTY_DIGEST)
    assert resumed_cursor == TailCursor(offset=0, content_invariant=EMPTY_DIGEST)


def test_validate_resume_cursor_missing_file_treats_offset_zero_as_valid(
    tmp_path: Path,
) -> None:
    """FR-013's structural checks still apply when the log file does not exist
    yet (mirrors poll_once()'s FR-008 tolerance, without inventing a new signal
    shape): offset 0 with no invariant, or a matching EMPTY_DIGEST invariant, is
    accepted; a nonzero offset is refused as out_of_range (there are zero bytes
    to be in range of); a mismatched invariant at offset 0 is refused as
    content_mismatch."""
    missing_log_path = tmp_path / "does-not-exist-yet.jsonl"
    assert not missing_log_path.exists()

    accepted = validate_resume_cursor(missing_log_path, 0, None)
    assert accepted == TailCursor(offset=0, content_invariant=EMPTY_DIGEST)

    accepted_matching = validate_resume_cursor(missing_log_path, 0, EMPTY_DIGEST)
    assert accepted_matching == TailCursor(offset=0, content_invariant=EMPTY_DIGEST)

    with pytest.raises(ResumeRefused) as out_of_range_info:
        validate_resume_cursor(missing_log_path, 1, None)
    assert out_of_range_info.value.reason == "out_of_range"

    with pytest.raises(ResumeRefused) as content_mismatch_info:
        validate_resume_cursor(missing_log_path, 0, "not-the-empty-digest")
    assert content_mismatch_info.value.reason == "content_mismatch"
