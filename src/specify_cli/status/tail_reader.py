"""Core tail-reader primitives for `spec-kitty events tail` (mission event-push-watch-channel).

Pure, finite, stdlib-only domain logic -- zero Typer/CLI imports. Per plan.md's
"Architectural Seam: Core vs. Shell (FR-011 / NFR-001)" section, this is the **core**:
:class:`TailCursor`, :func:`poll_once`, the :class:`ResumeRefused` exception, and
:func:`tail_events` -- the pure, finite generator that owns the actual poll-then-sleep
loop via its injectable ``sleep_fn`` (defaulting to real ``time.sleep``), terminable via
``itertools.islice``/a ``max_events`` cap. The **shell** (WP04's
``src/specify_cli/cli/commands/events.py``) holds NO loop construct of its own -- no
``while True``, no direct ``time.sleep`` call -- it merely iterates :func:`tail_events`
in a plain ``for`` loop, alongside owning Typer flags, mission-slug resolution, and
stdout/stderr JSON rendering.

This module is created by WP01 (this file's initial content: ``TailCursor``,
``EMPTY_DIGEST``, ``ResumeRefused``, ``PollResult``, ``poll_once()``) and then extended by
BOTH WP02 (truncation detection via ``validate_resume_cursor()``) AND WP03
(``tail_events()``) -- the same file, edited by three work packages in total, strictly
sequentially (WP01 -> WP02 -> WP03), per the mission's deliberate `write_scope_overlap`
lane collapse. See the WP01 prompt's Context section for the full ownership rationale.

Charter C-007's ``__all__`` requirement does NOT apply to this module: it binds only
``src/charter/`` and ``src/kernel/`` (spec Constraint C-002 confirms this explicitly for
this mission's new modules).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from specify_cli.status.store import StoreError

#: NFR-002: `tail_events()`'s poll interval, in seconds, MUST be a fixed, documented
#: value in [0.1s, 1.0s] -- the CLI shell (`events.py`) has no poll-interval flag or
#: loop of its own; it simply iterates `tail_events()` at this default. 0.25s is chosen
#: as a midpoint: fast enough that "within one poll interval" (FR-005/US1 AC2) is a
#: sub-second, practically-instant bound for a human-observed consumer, while not so
#: fast that idle polling of a live log imposes meaningless CPU/IO load on a single
#: long-running tailer (NFR-004).
DEFAULT_POLL_INTERVAL_SECONDS: float = 0.25

#: Canonical "nothing consumed yet" content-invariant sentinel: the SHA-256 hex digest of
#: the empty byte string. `TailCursor(offset=0, ...)` always carries this value rather
#: than `None` or another ad-hoc placeholder, so `offset == 0` has one well-defined
#: invariant instead of a separately special-cased "no invariant yet" state.
EMPTY_DIGEST: str = hashlib.sha256(b"").hexdigest()  # noqa: TID251 — file-integrity content
# invariant for event-log tear/truncation detection (see plan.md's "Truncation Detection
# Design" section), not the charter's `charter.hasher.hash_content()` freshness hash. This
# is the "file-integrity checksums" sanctioned non-charter use named in the TID251
# banned-API message (pyproject.toml).


@dataclass(frozen=True)
class TailCursor:
    """The reader's resumable position in a mission's event log.

    Caller-supplied/caller-owned (per the spec's Tail cursor Key Entity): `events tail`
    never persists cursor state itself -- not in a command-owned cursor file, not under
    `.kittify/`, not anywhere else. Each `poll_once()` call returns a *new* `TailCursor`
    rather than mutating one in place, so the caller decides what (if anything) to persist
    across restarts.
    """

    offset: int
    #: 64-char lowercase hex SHA-256 digest of the last-consumed line's bytes (including
    #: its trailing `\n`), or `EMPTY_DIGEST` when `offset == 0` (nothing consumed yet).
    content_invariant: str


class ResumeRefused(Exception):
    """Raised when a supplied resume point cannot be trusted (FR-013).

    This WP only defines the shape (a raiseable exception carrying a `.reason`
    attribute) -- WP02's `validate_resume_cursor()` is the actual raiser, supplying the
    structural/content-mismatch logic that decides when to raise it.
    """

    #: One of "negative" | "out_of_range" | "misaligned" | "content_mismatch".
    reason: str

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"resume refused: {reason}")


@dataclass(frozen=True)
class PollResult:
    """The outcome of one `poll_once()` call.

    `cursor` is always the cursor to resume from on the next call (identical to the input
    cursor when nothing new was consumed this poll -- e.g. a pure tear-tail retry or a
    missing/not-yet-grown file). `events` holds newly parsed event dicts, in file order.
    `file_present` distinguishes "log file does not exist yet" (FR-008) from an ordinary
    poll of an existing file -- callers must not treat a missing file as an error.
    """

    cursor: TailCursor
    events: list[dict[str, Any]]
    file_present: bool


def _content_invariant_for(last_complete_line: bytes | None, previous: str) -> str:
    """Compute the content invariant for the cursor returned by this poll.

    When no new complete line was consumed this poll (`last_complete_line is None`), the
    invariant is unchanged from the input cursor's -- nothing new to hash. Otherwise it is
    the SHA-256 hex digest of the single most-recently-consumed complete line's bytes
    (including its trailing `\n`), per plan.md's Truncation Detection Design.

    NOTE: this WP only *computes* the invariant so every cursor `poll_once()` returns
    stays well-defined; it does not *compare* it against anything to detect truncation --
    that comparison ("the hash check") is WP02's scope, not this WP's.
    """
    if last_complete_line is None:
        return previous
    return hashlib.sha256(last_complete_line).hexdigest()  # noqa: TID251 — same
    # file-integrity content-invariant use as EMPTY_DIGEST above; every hashlib.sha256
    # call site carries its own inline justification per this repo's TID251 policy.


def _start_of_last_line(fh: IO[bytes], offset: int) -> int:
    """Backward-scan for the start of the single line occupying ``[start, offset)``.

    ``offset`` is guaranteed by construction to be either 0 or immediately after a
    ``\\n`` (WP01's line-boundary invariant, relied on by both ``poll_once()``'s
    hash check and ``validate_resume_cursor()``'s backward scan). This scans
    backward from ``offset - 1`` (excluding the line's own trailing ``\\n`` at that
    position) for the previous ``\\n``, or BOF if there is none -- per plan.md's
    Truncation Detection Design: "the content invariant is... always re-derivable
    on a cold resume via a backward scan from O - 1 for the previous \\n (or BOF)".

    Reads through the SAME fd the caller already has open (``fh``) -- never a
    fresh ``Path.open()`` -- honouring the fd-sharing invariant plan.md's
    Architectural Seam section names for both ``poll_once()`` and
    ``validate_resume_cursor()``.
    """
    if offset <= 1:
        return 0
    search_end = offset - 1
    fh.seek(0)
    prefix = fh.read(search_end)
    idx = prefix.rfind(b"\n")
    return idx + 1 if idx != -1 else 0


def _content_invariant_at(fh: IO[bytes], offset: int) -> str:
    """The file's ACTUAL content invariant at ``offset``, derived via backward scan.

    SHA-256 hex digest of ``[start_of_last_line, offset)`` -- the single
    most-recently-consumed complete line's bytes, including its trailing ``\\n`` --
    per plan.md's Truncation Detection Design. Always re-derivable purely from the
    file and ``offset`` (no persisted line length needed) because ``offset`` is
    always a line boundary. At ``offset == 0`` this naturally reduces to
    ``EMPTY_DIGEST`` (the SHA-256 of ``b""``) with no special-casing needed.

    THREAT MODEL (load-bearing): hashing only the last consumed line -- not the
    whole ``[0, offset)`` prefix -- is sufficient *because* the sole in-place
    rewriter of this log, ``coordination/transaction.py``, only ever truncates a
    suffix and re-appends; it never rewrites an earlier prefix while leaving a
    later byte identical. A future writer that rewrites in place would defeat this
    single-line invariant and must extend the hash to the full consumed prefix.
    """
    start = _start_of_last_line(fh, offset)
    fh.seek(start)
    line_bytes = fh.read(offset - start)
    return hashlib.sha256(line_bytes).hexdigest()  # noqa: TID251 — file-integrity
    # content invariant for event-log tear/truncation detection (see EMPTY_DIGEST/
    # _content_invariant_for above), not the charter's `charter.hasher.hash_content()`.


def _truncation_signal(detected_at_offset: int, reason: str) -> PollResult:
    """Build the ``log_truncated`` envelope + offset-0 resync cursor (FR-005/FR-007).

    Shared by both truncation causes (the size check and the hash check) -- either
    mismatch produces the identical signal shape and resync target, differing only
    in ``reason`` (``"size_shrink"`` vs. ``"content_mismatch"``, per plan.md's Tail
    Envelope & Cursor Schema section). No line-parsing has happened yet this poll
    (both checks run before any parsing, per FR-007), so there is nothing else to
    undo.
    """
    event: dict[str, Any] = {
        "type": "log_truncated",
        "reason": reason,
        "detected_at_offset": detected_at_offset,
        "tail_offset": 0,
        "tail_invariant": EMPTY_DIGEST,
    }
    resynced_cursor = TailCursor(offset=0, content_invariant=EMPTY_DIGEST)
    return PollResult(cursor=resynced_cursor, events=[event], file_present=True)


def _check_truncation(fh: IO[bytes], cursor: TailCursor, size: int) -> PollResult | None:
    """FR-005: the size check and the independent, every-poll hash check.

    Returns the ``log_truncated`` `PollResult` if either check fires, else `None`
    to let `poll_once()` continue to its ordinary drain-and-parse path. Both
    checks run BEFORE any line-parsing of this poll's new bytes (FR-007) and share
    the caller's fd (fd-sharing invariant) -- no fresh `Path.stat()`/`Path.open()`.
    Neither check is satisfied by the other passing: the size check alone misses a
    truncate-then-regrow completing within one poll interval; the hash check runs
    unconditionally whenever there IS a prior consumed line to verify.

    Skipped entirely at ``cursor.offset == 0``: nothing has been consumed yet, so
    there is no content invariant that could have been violated.
    """
    if cursor.offset == 0:
        return None
    if size < cursor.offset:
        return _truncation_signal(cursor.offset, "size_shrink")
    if _content_invariant_at(fh, cursor.offset) != cursor.content_invariant:
        return _truncation_signal(cursor.offset, "content_mismatch")
    return None


def poll_once(path: Path, cursor: TailCursor) -> PollResult:
    """Single reopen-by-path poll of the mission event log at `path`.

    Opens the file **exactly once** per call (`path.open("rb")`), reads its size via
    `os.fstat(fh.fileno())` on that same descriptor (never a second `Path.stat()`), and
    every subsequent read in this call (the drain read) shares that one fd -- no operation
    inside this function re-resolves `path` after the initial open. This is the fd-sharing
    invariant plan.md's Architectural Seam section names, and it is mechanically enforced
    by this module's test suite (`tests/status/test_tail_reader.py`).

    FR-005/FR-007 (dual truncation detection, before any line-parsing): the size check
    (`current_size < cursor.offset`) and the independent, every-poll hash check (does the
    content immediately preceding `cursor.offset` still hash to `cursor.content_invariant`)
    both run BEFORE any line-parsing of this poll's new bytes, and neither is satisfied by
    the other passing. Either mismatch returns the `log_truncated` signal envelope
    (`_truncation_signal()`) with a cursor resynced to offset 0, instead of proceeding to
    the ordinary drain-and-parse path below. See `_check_truncation()`.

    FR-002 (offset-resumable reads): only bytes from `cursor.offset` onward are read or
    parsed; bytes before it are never touched, so an already-consumed event is never
    re-emitted.

    FR-003 (reopen-by-path): reopening by path on every call means a writer's
    `os.replace()` inode swap between calls is always observed correctly -- there is no
    held fd/inode to go stale.

    FR-006 (mid-line JSON tear tolerance): new bytes are split on `\n`. Every chunk except
    a possible non-`\n`-terminated final remainder must parse as JSON; a chunk that does
    is emitted and the offset advances past it (including its trailing `\n`). A trailing
    remainder with no terminating `\n` yet is left unconsumed -- not parsed, not signaled,
    not dropped -- and is retried from the same starting position on the next call. An
    *interior*, already-`\n`-terminated chunk that fails to parse is corruption, not a
    tear (appends only ever extend the file at the end) -- this is left to raise
    `json.JSONDecodeError` un-caught, mirroring `read_events_raw()`'s existing "raise on
    bad JSON" precedent (`src/specify_cli/status/store.py:554`) rather than inventing new
    silent-tolerance behaviour.

    FR-008 (wait for a not-yet-created log file): the single `path.open("rb")` call is
    wrapped in `try`/`except FileNotFoundError` -- there is no separate existence probe
    (`Path.exists()`/`Path.is_file()`/`Path.is_dir()` all call `Path.stat()` internally on
    Python 3.11/3.12, which would both violate the fd-sharing invariant and be a second
    path resolution the single-open-per-call commitment forbids). A missing file reports
    `file_present=False` with no events and an unchanged cursor, never an exception.
    """
    try:
        fh = path.open("rb")
    except FileNotFoundError:
        return PollResult(cursor=cursor, events=[], file_present=False)

    try:
        size = os.fstat(fh.fileno()).st_size

        truncated = _check_truncation(fh, cursor, size)
        if truncated is not None:
            return truncated

        if size <= cursor.offset:
            # No new bytes since the last poll -- ordinary "up to date", not
            # truncation (the truncation checks above already ran and passed).
            return PollResult(cursor=cursor, events=[], file_present=True)

        fh.seek(cursor.offset)
        new_bytes = fh.read()
    finally:
        fh.close()

    chunks = new_bytes.split(b"\n")
    # `bytes.split(b"\n")` always yields one more element than the number of `\n`s in
    # `new_bytes`: the final element is b"" when `new_bytes` ends with `\n` (nothing left
    # unconsumed), or the genuine non-terminated trailing remainder otherwise. Either way
    # it must never be parsed this poll.
    complete_chunks = chunks[:-1]

    events: list[dict[str, Any]] = []
    consumed_bytes = 0
    last_complete_line: bytes | None = None
    for chunk in complete_chunks:
        parsed = json.loads(chunk)
        if not isinstance(parsed, dict):
            # Mirror store.read_events_raw()'s corruption contract: a valid-JSON but
            # non-object line (a scalar or array) is a corrupt event, not a tolerated
            # tear. Raise the canonical StoreError here rather than let the
            # reader-key injection below fail with an opaque TypeError.
            raise StoreError("Invalid event structure in tail stream: expected JSON object")
        consumed_bytes += len(chunk) + 1  # +1 for the chunk's own trailing `\n`
        last_complete_line = chunk + b"\n"
        # plan.md's Tail Envelope & Cursor Schema: every PASS-THROUGH envelope gets
        # two reader-injected sibling keys -- `tail_offset` (byte offset immediately
        # after this line) and `tail_invariant` (the SHA-256 hex digest that offset
        # now represents) -- so a real stdout consumer can persist both and supply
        # them back on restart (FR-004/FR-013). Derived purely from bytes already
        # held in-process (`chunk`/`consumed_bytes`) -- no second fd, no `Path.stat()`
        # -- honouring the fd-sharing invariant this function's own docstring names.
        parsed["tail_offset"] = cursor.offset + consumed_bytes
        parsed["tail_invariant"] = hashlib.sha256(last_complete_line).hexdigest()  # noqa: TID251 — same
        # file-integrity content-invariant use as EMPTY_DIGEST/_content_invariant_for
        # above (per-line, not the running cursor's), not the charter's
        # `charter.hasher.hash_content()` freshness hash.
        events.append(parsed)

    new_offset = cursor.offset + consumed_bytes
    new_invariant = _content_invariant_for(last_complete_line, cursor.content_invariant)
    new_cursor = TailCursor(offset=new_offset, content_invariant=new_invariant)
    return PollResult(cursor=new_cursor, events=events, file_present=True)


def _validate_resume_cursor_missing_file(offset: int, invariant: str | None) -> TailCursor:
    """FR-013 structural checks when the log file does not exist (yet).

    A missing file's "current size" is trivially 0 for the in-range check: any
    positive offset is out-of-range; offset 0 is always structurally valid (no
    misalignment possible with no bytes at all) and, if a content invariant was
    supplied, only ``EMPTY_DIGEST`` (nothing consumed yet) can match it.
    """
    if offset > 0:
        raise ResumeRefused("out_of_range")
    if invariant is not None and invariant != EMPTY_DIGEST:
        raise ResumeRefused("content_mismatch")
    return TailCursor(offset=0, content_invariant=EMPTY_DIGEST)


def validate_resume_cursor(path: Path, offset: int, invariant: str | None) -> TailCursor:
    """FR-013 cold-resume validator: the structural-then-content refusal sequence.

    Deliberately a SEPARATE function from `poll_once()`'s live FR-005 resync path
    (plan.md's Truncation Detection Design): a live, already-running poll has the
    content invariant it needs sitting in its own cursor already; a cold resume
    has no such memory -- the consumer only ever hands it an offset and (optionally)
    a digest -- so it must backward-scan the file itself before it can even compute
    a digest to compare. On any mismatch this raises `ResumeRefused`; it never
    resyncs from 0 the way `poll_once()`'s live path does -- FR-013 is
    refuse-before-streaming, not resync-while-streaming (no Tail envelope is ever
    emitted for a refused resume).

    Opens exactly ONE file descriptor for the whole call (the "Same commitment for
    `validate_resume_cursor()`" paragraph in plan.md's Architectural Seam section):
    the structural (in-range) check via `os.fstat(fd)`, the backward scan, and the
    hash-check read all share that one fd -- never a fresh `Path.stat()` or a
    second `open()`/`Path.open()` call anywhere in this function.

    Structural checks run first, each raising `ResumeRefused` with the matching
    `reason` on failure: `offset < 0` -> `"negative"`; `offset` greater than the
    current file size -> `"out_of_range"`; `offset` not on a line boundary (not 0,
    and the byte immediately before it is not `\n`) -> `"misaligned"`. If
    structurally valid AND `invariant` was supplied, the derived content invariant
    at `offset` is compared to it, raising `"content_mismatch"` on a mismatch. If
    only `offset` was supplied (`invariant is None`), FR-013's explicit "opt-in"
    clause applies: only the structural checks matter, and the returned cursor's
    own invariant is computed/stored for future live-polling use without being
    compared against anything.
    """
    if offset < 0:
        raise ResumeRefused("negative")

    try:
        fh = path.open("rb")
    except FileNotFoundError:
        return _validate_resume_cursor_missing_file(offset, invariant)

    try:
        size = os.fstat(fh.fileno()).st_size
        if offset > size:
            raise ResumeRefused("out_of_range")
        if offset != 0:
            fh.seek(offset - 1)
            if fh.read(1) != b"\n":
                raise ResumeRefused("misaligned")

        actual_invariant = _content_invariant_at(fh, offset)
        if invariant is not None and actual_invariant != invariant:
            raise ResumeRefused("content_mismatch")

        return TailCursor(offset=offset, content_invariant=actual_invariant)
    finally:
        fh.close()


def tail_events(
    path: Path,
    cursor: TailCursor,
    *,
    max_events: int | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Iterator[dict[str, Any]]:
    """FR-011's bounded-generator core: repeated poll-then-sleep-if-nothing-new.

    Built on top of `poll_once()` -- the only source of new events or state advancement
    this generator ever consults. Maintains the advancing `TailCursor` internally,
    starting from `cursor` as passed in; the caller never needs to track cursor state
    across iterations.

    Loop body, once per iteration:
      1. `poll_once(path, cursor)`.
      2. Advance the internal cursor to the poll result's new position (every poll,
         whether or not it produced events -- `poll_once()` already returns the cursor
         unchanged when nothing new was consumed).
      3. If the poll produced events (ordinary pass-through events AND `log_truncated`
         signal envelopes alike -- this generator does not distinguish between them,
         per plan.md's Truncation Detection Design), `yield` each one, in order, as it
         arrives.
      4. Otherwise (nothing new this poll), call `sleep_fn(poll_interval)` ONCE before
         the next poll -- never when a poll DID produce output, so a backlog drains at
         full speed with no artificial delay between items, and never on the very
         first poll unconditionally (this branch is only reached after an unproductive
         poll, never before the first poll has run).

    Termination (NFR-001, the literal FR-011 requirement): with `max_events=None` (the
    default) this generator is infinite by construction -- exactly the "pure, finite...
    terminable via `itertools.islice`, a `max_events` cap" FR-011 names: finiteness is a
    property the CALLER imposes (via `itertools.islice` or by supplying `max_events`),
    not an assumption this function makes about how it will be consumed. When
    `max_events` IS supplied, this generator also honors it as a first-class bound
    itself -- internally counting yields and returning once the cap is reached -- so
    `tail_events(path, cursor, max_events=N, sleep_fn=...)` alone (no external
    `itertools.islice` wrapper needed) terminates deterministically too. These two
    bounding mechanisms never diverge: `max_events` stops the generator at exactly N
    yields regardless of how it is reached; `itertools.islice` simply stops requesting
    further items, which composes identically whether or not `max_events` is also set.
    Every core-level test in this module's test suite passes an injected `sleep_fn`
    (never the real `time.sleep`) AND bounds via `max_events` and/or
    `itertools.islice` -- so no test ever hangs a real-time poll loop to exercise this
    function, satisfying NFR-001 literally, not just in spirit.

    `sleep_fn` defaults to real `time.sleep` so production callers (the CLI shell) get
    a genuine wall-clock pause between unproductive polls with no extra plumbing;
    every test in this module overrides it to a no-op or call-counting stub.

    Never catches or suppresses exceptions raised by `poll_once()` -- they propagate
    unchanged, preserving WP01/WP02's existing error-handling semantics (this WP does
    not alter them).
    """
    emitted = 0
    while max_events is None or emitted < max_events:
        result = poll_once(path, cursor)
        cursor = result.cursor

        if result.events:
            for event in result.events:
                yield event
                emitted += 1
                if max_events is not None and emitted >= max_events:
                    return
        else:
            sleep_fn(poll_interval)
