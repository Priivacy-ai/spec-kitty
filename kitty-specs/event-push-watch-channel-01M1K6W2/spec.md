# Mission Specification: Events Tail — Push/Watch Channel for External Consumers

**Mission Branch**: `feat/event-push-watch-channel-3841`
**Created**: 2026-09-03
**Status**: Draft
**Input**: GitHub issue [#3841](https://github.com/Priivacy-ai/spec-kitty/issues/3841) — "Event push/watch channel for external consumers (design discussion)"

## Clarifications & Decision Records

### 1. Scope decision — Option 1 only (operator decision, not open for re-litigation)

Issue #3841 lists three candidates in ascending ambition: (1) a long-lived `spec-kitty events
tail --mission <slug> --json` process streaming envelope JSON lines, (2) a local socket/SSE
endpoint, (3) fleet-level SaaS-adjacent aggregation. **The operator has already decided this
mission implements Option 1 only.** Options 2 and 3 are explicitly OUT OF SCOPE — not deferred
"future work" to be designed here, not a phased on-ramp this mission's architecture must
anticipate. This spec's Functional/Non-Functional Requirements describe a single-process,
single-consumer, filesystem-polling CLI command with no daemon, no socket, no network listener,
and no fleet aggregation. A reviewer who believes Option 2/3 should be in scope is re-opening an
already-closed operator decision, not finding a gap in this spec.

### 2. The issue's ordering-guarantee claim is FALSE on current `main` — corrected premise

Issue #3841 claims Option 1 would let external hosts "inherit the writer's own ordering
guarantees instead of racing the filesystem." **This was verified false by direct code reading
of this checkout, not assumed:**

- The event log is **not append-only**. `BookkeepingTransaction._rollback()`
  (`src/specify_cli/coordination/transaction.py:921-947`) truncates `status.events.jsonl` back to
  the pre-emit byte size (`fh.truncate(self._pre_emit_size)` at line 938) or unlinks it entirely
  (line 940) on rollback. The file can **shrink**. A consumer that assumes monotonic growth
  desyncs silently across any rolled-back transaction.
- Only **2 of 6+ writers** of `status.events.jsonl` take the feature status lock — ledger entry
  `SK-131` in `the mission defect ledger`. The main emit pipeline
  (`src/specify_cli/status/emit.py` → `store.py:358` `_append_serialized_atomic`) reads the whole
  file, appends in memory, and `os.replace()`s a temp file under lock. `store.append_event`
  (`src/specify_cli/status/store.py:292-303`) and the retrospective/decision/lifecycle writers use
  plain unlocked `open(path, "a")` appends that can land inside the locked pipeline's
  read-then-replace window and be silently discarded by the rename — no error, no warning.
- The **inode is replaced on every locked write** (`os.replace` in `_append_serialized_atomic`,
  `store.py:392`), so a consumer holding an open file descriptor or bare byte offset across a
  rename is unsafe. A reader must reopen by path on every poll.
- `read_events_raw()` (`src/specify_cli/status/store.py:533-560`) is one-shot, non-resumable, and
  raises `StoreError` on the first invalid JSON line (`store.py:554`) — including an
  incomplete trailing line from a write in progress. It has no offset/resume parameter and no
  partial-line tolerance.

**Corrected premise this spec builds on**: the writer's locked append path provides durability
and (for the 2-of-6 locked writers) atomicity of a single batch's replace — it does **not**, by
itself, give an external tailer safe resumable ordering across process restarts, torn reads, or
rollback truncation. **The tolerant, resumable reader this spec requires is what earns the
ordering guarantee for a consumer; it is not inherited for free from the writer.** Building
`events tail` as a thin wrapper over `read_events_raw()` would reproduce every one of the four
defects above in every external consumer that adopts it — the opposite of the issue's stated
goal.

### 3. Verification pointers for the review squad

The R1–R6 review squad reviewing this spec should verify the above directly rather than trust
this prose:

- `src/specify_cli/coordination/transaction.py:921` (`_rollback`), `:938` (truncate), `:940`
  (unlink).
- `src/specify_cli/status/store.py:292` (`append_event`, unlocked), `:358` (`_append_serialized_atomic`,
  locked, read-modify-`os.replace`), `:392` (`os.replace` call site), `:533` (`read_events_raw`),
  `:554` (`StoreError` on first bad JSON line).
- `src/specify_cli/status/emit.py:1-36` (pipeline docstring naming step 5,
  `store.append_event(feature_dir, event)`, as the sole authoritative durable act).
- Ledger `SK-131` (six-writer lock survey, corpus events may already be lost through this
  window), `SK-144` (marker-vs-directory test collection trap), `SK-147` (mid8 collision window
  for fixtures created within ~256ms).
- `spec-kitty-events>=6.0.0,<7.0.0` is pinned as an external PyPI dependency in `pyproject.toml`
  (line 80); `status.events.jsonl` rows are spec-kitty's own local `StatusEvent` dataclass
  (`src/specify_cli/status/models.py`), not the `spec_kitty_events.Event` sync envelope. This
  mission needs no change to that package's version or contract (see C-004).

### 4. Terminology — new domain terms are glossary candidates, not yet canonical

This mission introduces several domain terms that do not yet appear in
`docs/context/system-events.md`: **Tail cursor**, **resume token**, the `log_truncated` signal
shape, and the renamed **Tail envelope** Key Entity below (deliberately distinct from the
existing canonical `Event Envelope` term — see the Key Entities section for the distinction).
None of these is claimed as canonical by this spec. They are flagged here as glossary candidates
for `docs/context/system-events.md` to be resolved at plan/implement time, not decided
unilaterally by this document.

### 5. Content invariant representation — a hash, not raw bytes (operator ruling, not open for re-litigation)

An earlier draft left FR-005's content invariant as an unresolved either/or: "a hash of, or the
raw bytes of," the last-consumed line/boundary. **The operator has ruled: the content invariant is
a SHA-256 hex digest, never raw bytes.** This is a correctness decision this spec commits to, not
an implementation detail deferred to plan phase:

1. **The spec's own evidence rules out raw bytes.** User Story 4 / Edge Cases cites SK-131's
   measured 610KB event line. Embedding up to ~610KB of raw line bytes in every Tail envelope, or
   passing that value back as a `--from-invariant` CLI argument on restart, breaks realistic
   `ARG_MAX`/command-line-length limits and defeats the one-JSON-envelope-per-line streaming design
   FR-001–FR-006 are built around.
2. **Equality is the only operation the invariant performs** (FR-005, FR-013). A hash supports it
   exactly — nothing the invariant is used for requires reading the original bytes back. A fixed-
   size digest is exactly the property an envelope field and a CLI argument need, regardless of how
   large the underlying event line is.
3. **Two alternatives were considered and rejected.** *Keep both, bounded by a size threshold*:
   adds a mode switch, a threshold to justify and tune, a boundary to test, and an envelope field
   whose type varies with event size — more surface for a consumer to get wrong, in a mission whose
   whole purpose is not silently misleading consumers. *Drop the invariant, resume on offset
   alone*: reopens the exact defect the invariant closes — a rollback-then-regrow leaves the same
   offset pointing at different content, so a resuming consumer would silently read the wrong
   events.

FR-004, FR-005, FR-013, and the Tail cursor / Tail envelope Key Entities all describe the same
fixed-size SHA-256 digest consistently; there is no remaining hash-vs-raw-bytes either/or anywhere
in this document.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - External host drops its own filesystem watcher (Priority: P1)

An external desktop/companion consumer currently runs its own filesystem-watcher and debounced
re-reduction logic for one mission, polling/watching `status.events.jsonl` itself. It wants to
replace that with `spec-kitty events tail --mission <slug> --json`, consuming one JSON envelope
per line as events land, without re-deriving state from raw file-watch signals itself.

**Why this priority**: This is the entire scope of the mission (Option 1) and the only capability
that removes a consumer-side inotify stack, per the issue.

**Independent Test**: Start a mission with an empty or partially-populated `status.events.jsonl`,
run `events tail --mission <slug> --json --once` (or with `--max-events N`, the bounded escape
hatch — see NFR-001) against it, append new events to the file from a second process mid-run, and
confirm every appended event is emitted as one JSON line, in file order, with no manual
filesystem-watch code in the consumer.

**Acceptance Scenarios**:

1. **Given** a mission with an existing `status.events.jsonl` containing N events, **When** a
   consumer runs `events tail --mission <slug> --json --once`, **Then** the command emits exactly
   the N existing events as JSON lines, one per event, in file order, and exits 0 without blocking.
2. **Given** a running `events tail --mission <slug> --json` process with no `--once`/bound, **When**
   a separate writer atomically appends a new valid event to the log, **Then** the tail process
   emits that event's JSON line within one poll interval (see NFR-002) without re-emitting any
   already-seen event.
3. **Given** a mission slug that does not resolve to an existing mission directory, **When** a
   consumer runs `events tail --mission <bad-slug> --json`, **Then** the command exits non-zero
   with a structured error on stderr and emits no JSON lines claiming success (see FR-009).

---

### User Story 2 - Consumer survives a rollback truncation without desyncing silently (Priority: P1)

A mission the consumer is tailing hits a transactional rollback mid-stream:
`BookkeepingTransaction._rollback()` truncates `status.events.jsonl` back to a smaller byte size
(or deletes it). A naive tailer that only tracks a byte offset and appends would either crash on
a now-invalid offset or, worse, silently continue as if nothing happened and never surface the
truncated events again correctly.

**Why this priority**: This is the corrected-premise finding from the Clarifications section made
concrete and testable — a P1 because an untested tolerant reader is not actually delivered, it's
asserted.

**Independent Test**: Run `events tail` against a log, then externally truncate the file to a
smaller size while the reader is paused between polls (simulating rollback), resume polling, and
assert the reader emits an explicit truncation signal (FR-005) rather than silently resuming as
if the shrink never happened.

**Acceptance Scenarios**:

1. **Given** a tailer that has read up to byte offset `O` in `status.events.jsonl`, **When** the
   file's current size on the next poll is smaller than `O`, **Then** the reader detects this as a
   truncation (never as "no new data"), emits an explicit `{"type": "log_truncated", ...}` signal
   envelope on the JSON stream (see FR-005 for the exact shape), and resynchronizes by re-reading
   from offset 0 rather than continuing to read from the stale offset `O`.
2. **Given** a truncation signal has been emitted, **When** the reader re-reads from offset 0,
   **Then** every event now present in the file (post-truncation) is (re-)emitted so the consumer
   can reconcile its own state, and no event that no longer exists in the file is fabricated or
   replayed from a stale in-memory cache.
3. **Given** a tailer that has read up to byte offset `O`, **When**, within a single poll interval,
   a rollback truncates the file below `O` and a subsequent write (locked or unlocked) grows it
   back to a size at or above `O` before the reader's next poll samples it — so the size check
   alone (`current size < O`) never observes a shrink — **Then** the reader's content-invariant
   check (FR-005) detects that the bytes at the boundary immediately preceding `O` no longer match
   what was last consumed, treats this as truncation exactly as in Scenario 1 (never as ordinary
   growth), emits the `log_truncated` signal, and resynchronizes from offset 0 — i.e. a
   truncate-then-regrow that completes within one poll interval is caught, not silently absorbed
   as new data.

---

### User Story 3 - Consumer reconnects after a disconnect and resumes without loss or duplication (Priority: P2)

An external consumer's `events tail` process is killed (network blip, host restart, manual
Ctrl-C) and restarted. It should not have to replay the entire log from the start, and it must
not silently miss events that landed while it was disconnected.

**Why this priority**: P2 — resumability matters for a long-running external consumer but is not
required for the MVP one-shot case (`--once`) to be useful; still a first-class deliverable per
the mission brief, not "future work."

**Independent Test**: Run `events tail` to completion against a fixed log, capture the last
consumed byte offset AND the FR-005 content-invariant value from its own output (mechanism defined
by FR-004 — `--from-offset`/`--from-invariant`), kill and restart the process with both supplied,
append more events while it was down, and confirm the restarted process emits only the events
appended since the last-seen offset, none of the ones already consumed, and none dropped. A
second run of this test rolls the mission back and regrows it entirely while the process is down
(so the resumed offset is structurally valid but the content invariant no longer matches) and
confirms FR-013 refuses the resume — a structured error on stderr, a non-zero exit, and no Tail
envelope emitted — per Acceptance Scenario 4 below, rather than resuming as if nothing happened.

**Acceptance Scenarios**:

1. **Given** a tailer that stops after consuming through byte offset `O`, **When** it is restarted
   and given `O` as its resume point, **Then** it does not re-emit any event fully contained before
   offset `O`, and it does not skip any event that starts at or after offset `O`.
2. **Given** the tailer reopens the file by path (never a held file descriptor) on every poll
   cycle, **When** the writer's `os.replace()` has swapped the log's inode since the last poll
   (locked-writer rename churn), **Then** the reader observes the new inode's content correctly
   at the resumed offset rather than reading stale data from the old, now-unlinked inode.
3. **Given** a consumer supplies a resume offset via `--from-offset` that is structurally invalid
   for the current file — greater than the current file size, negative, or not aligned on a line
   boundary (e.g. a persisted offset predating a rollback the consumer never saw), **When** the
   reader attempts to resume from it, **Then** it does not silently clamp the offset to file size
   or 0, does not guess the nearest line boundary, and does not proceed as if nothing were wrong;
   it treats this as data-loss/desync per FR-013 and refuses the resume — a structured error on
   stderr, a non-zero exit, and no Tail envelope emitted for the invocation — rather than starting
   from an unverifiable position.
4. **Given** a consumer supplies `--from-offset O` together with the content-invariant value
   FR-004 emitted for offset `O` in a prior run, and a rollback-then-regrow happened entirely
   while the consumer was offline such that the file's current size and offset `O` are
   structurally valid (in range, on a line boundary) but the bytes at the boundary immediately
   preceding `O` no longer match the supplied invariant, **When** the reader attempts to resume
   from `O`, **Then** it treats this as data-loss/desync per FR-013 exactly as it would a
   structural failure — it does not trust the structurally-valid offset, and refuses the resume: a
   structured error on stderr, a non-zero exit, and no Tail envelope emitted for the invocation,
   rather than starting from a position whose preceding content it cannot verify.

---

### User Story 4 - Consumer tolerates a mid-line JSON tear without dropping or crashing (Priority: P1)

`events tail` polls a log that an active writer may be mid-append to. A poll can catch the log at
exactly the moment a writer's `write(2)` for one line is only partially flushed to disk (SK-131
measured this directly: 33,389 of 4.5M concurrent stat samples caught a 610KB line mid-write).
The reader must not treat that torn trailing line as a hard read failure, and must not drop it
permanently — it must retry it on a later poll once the write completes, and then emit it exactly
once.

**Why this priority**: P1 — this is shape (a) of the two truncation/tear shapes this mission
exists to handle (User Story 2 covers shape (b), clean record-boundary truncation); an active
writer mid-append is the normal, expected concurrent case (NFR-004), not a rare edge condition,
so an untested reader here is exactly as load-bearing as User Story 2's.

**Independent Test**: Write a valid JSONL log, then append one further line in two writes with a
pause between them so a poll can land between the two writes (the trailing line is syntactically
incomplete/invalid JSON at that moment); run the reader's bounded core across that pause and
assert it does not raise, does not emit anything for the torn line, and — once the second write
completes and a later poll observes the now-complete line — emits that event exactly once, with
no error or truncation signal produced anywhere in the sequence.

**Acceptance Scenarios**:

1. **Given** a tailer polling a log while a writer's `write(2)` for one trailing line is
   mid-flight, **When** the tailer's poll reads that trailing line and it fails JSON parse, **Then**
   the reader does not raise a fatal read error, does not emit a `log_truncated` or any other
   error/truncation signal for it (per NFR-003's FR-006 exemption), and does not drop the partial
   line permanently — it treats the trailing bytes as "not yet flushed" and retries from the same
   position on the next poll.
2. **Given** the tailer retried a torn trailing line on a prior poll, **When** the writer's
   in-flight `write(2)` completes and a later poll re-reads that same region, **Then** the reader
   parses the now-complete line successfully and emits it as exactly one JSON envelope on the
   stream — never duplicated across the polls that retried it, and never silently skipped.

---

### Edge Cases

- **Mid-line JSON tear (shape a)**: the tailer polls while a writer's `write(2)` for one line is
  incomplete (SK-131 measured this directly — 33,389 of 4.5M concurrent stat samples caught a
  610KB line mid-write). The trailing partial/invalid-JSON line must be treated as "not yet
  flushed" and retried on the next poll — never a hard failure of the whole read, and never
  silently dropped. See FR-006 and User Story 4.
- **Clean record-boundary truncation (shape b)**: rollback truncates the file at a valid line
  boundary — the remaining bytes still parse as valid JSON, but whole trailing events are simply
  gone. This does **not** raise a JSON parse error, so a reader that only defends against shape
  (a) will read the shrunk file successfully and report a confidently wrong (incomplete) result.
  This is the specific failure a sibling mission's `design-status` verb was rejected at severity 4
  for today — the reviewer live-reproduced a confidently wrong answer when only shape (a) was
  handled. Detection is via the size-shrink check and the content-invariant check in FR-005/US2,
  independent of whether the remaining bytes parse. Both shapes must be named and tested
  separately — passing shape (a)'s test does not imply shape (b) is handled.
- **Log file does not exist yet** (mission created but no event has been emitted): `events tail`
  must not error as if the mission itself is missing; it should wait/poll for the file to appear
  (bounded by `--once`/`--max-events` in tests) and start streaming once it does. See FR-008.
- **Mission slug does not resolve** to any mission directory under `kitty-specs/`: exit non-zero
  with a structured error, distinct from "file not yet created." See FR-009.
- **Invalid, out-of-range, or content-mismatched resume offset supplied via `--from-offset`**
  (FR-004's resume mechanism): either structurally invalid — greater than the current file size,
  negative, or not on a line boundary — or structurally valid but content-mismatched against a
  paired `--from-invariant` value (a rollback-then-regrow that completed entirely while the
  consumer was offline, e.g. a persisted offset predating a rollback truncation the consumer never
  saw). The reader must not silently clamp it to file size or 0, must not guess the nearest line
  boundary, and must not trust a structurally-valid offset whose supplied content invariant does
  not match; it must treat either case as data-loss/desync and refuse the resume — a structured
  error on stderr, a non-zero exit, no Tail envelope emitted for the invocation — never a silent
  re-read from the wrong position. See FR-013 and User Story 3 Scenarios 3-4.
- **Consumer disconnects and reconnects mid-stream**: covered by User Story 3 — no loss, no
  duplication, offset-based resume.
- **Log rotated/replaced underneath the reader** (the writer's `os.replace()` swaps the inode on
  every locked append): the reader must reopen by path every poll and never trust a previously
  opened fd across the rename (FR-003).
- **Concurrent active writer while `events tail` runs** (the normal case — this is a live,
  currently-mutating log from day one of merge, including for the mission this spec itself lives
  in): `events tail` is a pure reader and must never write to `status.events.jsonl` or any other
  mission artifact under any code path, including error handling. See FR-010/NFR-004.
- **`--json` is the only supported output mode for MVP** — a human-readable/pretty mode is out of
  scope; note it only if a reviewer asks, do not build it.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | New `events` command group with `tail` verb | As an external consumer, I want `spec-kitty events tail --mission <slug> --json` so that I can stream a mission's event log without my own filesystem watcher. | High | Open |
| FR-002 | Byte-offset resumable reads | As a reconnecting consumer, I want the reader to resume from a supplied byte offset so that I neither re-read from the start nor lose events across a restart. | High | Open |
| FR-003 | Reopen-by-path every poll cycle | As a consumer of a log whose inode is replaced by every locked writer append, I want the reader to reopen the file by path on each poll (never follow a held fd/inode) so that I never read stale or unlinked data. | High | Open |
| FR-004 | Explicit resume mechanism exposed to the consumer, including the content invariant | As a restarting consumer, I want the command to accept a resume point (`--from-offset <N>`, optionally paired with `--from-invariant <VALUE>`) and to emit, in each envelope, both its current offset AND the FR-005 content-invariant value (a fixed-size SHA-256 hex digest — see Clarifications §5) for that offset, so that I can persist both and supply them on restart for FR-013's cross-restart content check. `--from-invariant` supplied without `--from-offset` MUST be rejected as a CLI usage error — non-zero exit, structured stderr, no Tail envelope emitted — before any read begins, consistent with FR-009's pattern for other malformed-input rejections: an invariant has no offset to anchor its check to. | High | Open |
| FR-005 | Truncation detection via size AND content invariant, with explicit resync signal | As a consumer whose mission was rolled back mid-stream, I want the reader to detect truncation two ways — the size check (current file size < last-seen offset O), and the hash check, which on EVERY poll, independent of the size check, and even when current size >= O, re-verifies that a content invariant (a SHA-256 hex digest of the last-consumed line/boundary bytes immediately preceding offset O — see Clarifications §5 for why this is a hash and not raw bytes) still matches the current file at that position before trusting anything read from O onward — treat either mismatch as truncation (never as "no new data"), and emit an explicit `log_truncated`-shaped envelope on the JSON stream before resyncing from offset 0, so that a rollback-then-regrow completing within a single poll interval (which the size check alone cannot see) is never silently desynced. | High | Open |
| FR-006 | Tolerate a mid-line JSON tear without hard-failing | As a consumer polling a log an active writer may be mid-append to, I want an incomplete/invalid trailing line to be treated as "not yet flushed" and retried next poll — never raised as a fatal read error and never silently dropped — so that a torn read never crashes or drops a legitimate in-flight event. | High | Open |
| FR-007 | Detect a clean record-boundary truncation as data loss, not as valid-and-complete | As a consumer, I want the reader to distinguish "file shrank because a whole trailing event was rolled back" (still valid JSON, but events missing) from "file shrank" being ignored — i.e. FR-005's size-shrink check must fire even when the remaining bytes parse cleanly, so that shape (b) truncation is never satisfied by only handling shape (a). | High | Open |
| FR-008 | Wait for a not-yet-created log file, then stream once it appears | As a consumer of a freshly created mission with no events yet, I want `events tail` to poll for the file's appearance rather than error, so that tailing a brand-new mission is not a special case the consumer must handle itself. | Medium | Open |
| FR-009 | Fail closed on an unresolvable mission slug | As a consumer, I want `events tail --mission <bad-slug>` to exit non-zero with a structured error distinct from "file not yet created," so that a typo or bad slug is never confused with "mission not started yet." | Medium | Open |
| FR-010 | Pure reader — no write-back to any mission artifact | As the maintainer of every other mission whose event log this command may read concurrently, I want `events tail` to never write to `status.events.jsonl`, `status.json`, or any other mission file under any code path (including error handling), so that reading never risks corrupting a live writer's state. | High | Open |
| FR-011 | Bounded-generator-core / infinite-poll-shell architectural seam | As the implementer and every downstream test author, I want the event-yielding logic separated into a pure, finite generator/iterator core (terminable via `itertools.islice`, a `max_events` cap, or a `--once` flag) wrapped by a `while True` polling Typer CLI shell, so that the core is deterministically unit-testable and no test needs to hang a `while True` loop to exercise it. | High | Open |
| FR-012 | Per-mission log scope only (MVP) | As a consumer, I want `--mission <slug>` to resolve to that mission's `status.events.jsonl` under its `kitty-specs/<slug>/` directory (per `MISSION_EVENTS_FILENAME` in `src/specify_cli/status/lifecycle_events.py`); a project-wide tail over `.kittify/canonical-events.jsonl` (`PROJECT_EVENTS_FILENAME`) is explicitly out of scope for this mission and left as a natural, separate future extension. | Medium | Open |
| FR-013 | Fail closed on an invalid, out-of-range, or content-mismatched resume offset | As a consumer supplying a resume point via FR-004's mechanism (an offset, optionally paired with the FR-005 content-invariant value FR-004 emitted for that offset) that turns out to be invalid or stale for the current file — either structurally invalid (greater than the current file size, negative, or not aligned on a line boundary) OR structurally valid but content-mismatched (the bytes at the resumed offset's boundary no longer match the supplied content invariant — e.g. a rollback-then-regrow that completed entirely while the consumer was offline, the same failure class FR-005 detects while the consumer is running) — I want the reader to treat both cases identically as data-loss/desync and REFUSE the resume: emit a structured error on stderr and exit non-zero, with no Tail envelope emitted for that invocation — the same fail-closed shape as FR-009's unresolvable-slug handling, and deliberately NOT FR-005's live resync-from-0 (that path is for an already-running process observing a live truncation; a resume request the reader has not yet trusted gets no bytes streamed at all). The reader never silently clamps the offset to file size or 0, never guesses the nearest boundary, and never trusts a structurally-valid offset whose supplied content invariant does not match, so that neither a stale/corrupt persisted offset nor an offline rollback-then-regrow is ever met with a silent re-read from the wrong position — only an explicit refusal the consumer must act on. When the consumer supplies `--from-offset` without a paired `--from-invariant`, only the structural checks apply — cross-restart content verification requires the consumer to have persisted and supplied the invariant value FR-004 emits. (See FR-004 for the inverse malformed combination — `--from-invariant` without `--from-offset` — rejected as a CLI usage error before any read begins.) | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Testability seam is explicit and bounded | The core reader MUST be implemented as a pure, finite generator/iterator (accepting a `max_events` cap or equivalent) separate from the infinite-poll CLI shell. Every test of the core MUST run against a bounded input and MUST terminate without relying on a wall-clock timeout to kill a runaway loop. The CLI shell itself is exercised only via `--once`/`--max-events`-bounded invocations in tests, never a bare unbounded `events tail` in CI. | Testability | High | Open |
| NFR-002 | Poll interval bound | The shell's poll interval MUST default to a fixed, documented value between 100ms and 1000ms (implementation picks the exact figure and documents it in code/docs — this spec fixes only the bound, not the number) so that "within one poll interval" in FR-005/US1 Scenario 2 is a testable, sub-second bound rather than an open-ended promise, and so that idle polling of a live log does not impose meaningless CPU/IO load on a fleet-scale number of concurrent tailers (a fleet-scale daemon is explicitly out of scope per C-001, but a single tailer's poll cost must still be bounded). | Performance | Medium | Open |
| NFR-003 | Silent success is prohibited (with an explicit FR-006 exemption) | No code path in `events tail` — including truncation, missing-file, or resolve-failure paths — may report success (JSON envelope implying "up to date" / "no new events") while a real event exists that was not surfaced. Every non-nominal condition covered by FR-005, FR-007, FR-008, FR-009, and FR-013 MUST produce an explicit signal (a distinguishable envelope on the stream, or a non-zero exit with structured stderr) rather than being absorbed into ordinary "no new data" output. FR-006's torn-line retry is explicitly EXEMPT from this explicit-signal requirement: no complete event exists yet at that poll, so there is nothing to silently report success about. Per FR-006, a torn-line retry MUST NOT be reported as an error or as a `log_truncated` signal, and MUST NOT be silently dropped either — it is retried transparently across polls, not signaled. | Reliability | High | Open |
| NFR-004 | Reader safety against a live, concurrently-mutating log | `events tail` MUST be safe to run from day one of merge against a `status.events.jsonl` that an active writer (any of the mission's normal write paths, locked or unlocked) is concurrently appending to or rolling back — this is the actual, expected use case, not an edge case to defend against defensively-but-untested. The writer side MUST see zero behavioral change and zero added risk from a concurrent `events tail` reader (FR-010 makes this true by construction: the reader never writes). | Reliability | High | Open |
| NFR-005 | No new red beyond the pre-existing #3284 baseline | Any acceptance criterion that implies running the test suite is satisfied by "no new red beyond the tests already red on `main` under tracked issue #3284" — it does NOT require the full suite to be all-green, and pre-existing #3284 red must not be conflated with new-mission red. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Scope-locked to Option 1 | This mission implements ONLY `spec-kitty events tail --mission <slug> --json` (a Typer command group + verb). No daemon process, no local socket/SSE endpoint, no network listener, and no fleet-level aggregation may be introduced, even as a partially-built on-ramp. This is an operator decision (see Clarifications §1), not open to re-scoping during plan/tasks/implement. | Technical | High | Open |
| C-002 | `__all__` (C-007) does not apply to this mission's new modules | Charter C-007 requires `__all__` declarations only for modules under `src/charter/` and `src/kernel/` (`.kittify/charter/charter.md:586-590`). The new `events` command module lands under `src/specify_cli/cli/commands/` (registered via `app.add_typer(events_module.app, name="events")` alongside the existing `docs`/`glossary`/`issue-matrix` registrations at `src/specify_cli/cli/commands/__init__.py:247-336`) and any new reader helper lands under `src/specify_cli/status/` (adjacent to `store.py`). Neither path is under `src/charter/` or `src/kernel/`, so C-007's `__all__` requirement does NOT apply to this mission's code. | Technical | Medium | Open |
| C-003 | No `--feature*` aliases | Per the charter's Terminology Canon (`.kittify/charter/charter.md:533-549`), the new command's CLI surface (flags, help text, error messages) MUST use `--mission`, never introduce a `--feature*` alias, route param, or flag name. Internal Python parameter names may continue to use the existing `feature_dir`/`feature` convention already used by `store.py`/`lifecycle_events.py`, matching current in-repo practice — only the user-facing surface is constrained. | Technical | High | Open |
| C-004 | No `spec-kitty-events` package or contract change | `spec_kitty_events` is a real external PyPI dependency pinned `>=6.0.0,<7.0.0` in `pyproject.toml` (line 80) — it is NOT vendored in-tree. `status.events.jsonl` rows are spec-kitty's own local `StatusEvent` dataclass (`src/specify_cli/status/models.py`), unrelated to the `spec_kitty_events.Event` sync envelope. This mission requires NO version bump and NO contract change to that package, and does not touch `pyproject.toml`'s dependency pin, `uv.lock`, or any compat manifest — so the `check-spec-kitty-events-alignment` CI gate is not expected to fire. | Technical | Medium | Open |
| C-005 | No `watchdog`/`inotify` dependency | This repo has no `watchdog`/`inotify` dependency anywhere (confirmed via grep of `pyproject.toml` and `src/`) and polling is the established idiom (see the dashboard precedent, C-006). `events tail`'s reader MUST use polling, not add a filesystem-event-notification dependency. | Technical | Medium | Open |
| C-006 | ATDD-first (C-011) applies to every implementation WP | Charter C-011 requires a failing-first ATDD test committed as its own commit before implementation for every work package. This spec does not author the plan/tasks, but states this as a binding constraint those phases must honor and not contradict. | Process | High | Open |
| C-007 | Immutable-roots hygiene (NFR-002 architectural gate) | `tests/architectural/test_archive_root_byte_identical.py` forbids modifying or deleting any pre-existing file under `kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, and `.kittify/missions/` — only new-path ADDs are permitted. This mission's new code lives under `src/specify_cli/` and does not touch any of those four roots; the plan/tasks phases MUST preserve that (no fixture or test scaffolding writes/deletes pre-existing files under those roots). | Technical | High | Open |
| C-008 | Marker discipline (SK-144 / issue #3241) | CI selects pytest tests by MARKER, not directory — a test in the right folder with the wrong or no marker is collected by zero jobs. Every test-adding work package in the later tasks phase MUST name both its pytest marker(s) (from `pytest.ini`'s `markers` list, e.g. `unit`, `fast`, `integration`, `git_repo`) and the CI job that collects it. Concretely for this mission: reader-core tests under `tests/status/` or `tests/specify_cli/status/` are collected by `fast-tests-status`/`integration-tests-status` (`.github/workflows/ci-quality.yml`, path filter `tests/status/ tests/specify_cli/status/`); CLI-shell tests for the new `events` command under `tests/cli/` or `tests/specify_cli/cli/` are collected by `fast-tests-cli`/`integration-tests-cli` (path filter `tests/cli/ tests/specify_cli/cli/`). "A test file exists" does not satisfy this spec's acceptance criteria — it must also carry a marker one of those jobs actually selects. | Process | High | Open |
| C-009 | Fixture ULID/clock freezing if fixture missions are created (SK-147) | If any acceptance test's harness creates spec-kitty missions in quick succession to generate log content for `events tail` to read, it MUST freeze `ULID` generation and `now_utc_iso()` per the pattern in ledger SK-147, to avoid a structural `mid8` collision between fixture missions created within the same ~256ms window. | Technical | Medium | Open |
| C-010 | Issue closure linkage (for the eventual PR, not actioned here) | The eventual implementation PR body must carry `Closes #3841`. Noted here for the plan/implement phases to pick up; this spec.md does not itself close the issue. | Process | Low | Open |

### Key Entities *(include if feature involves data)*

- **Tail cursor**: the reader's resumable position — a byte offset into a named mission's
  `status.events.jsonl`, plus enough state to detect truncation on the next poll: the last-seen
  file size, AND (per FR-005) a content invariant — a fixed-size SHA-256 hex digest of the
  last-consumed line/boundary bytes at that offset, never the raw bytes themselves (see
  Clarifications §5) — used to re-verify on every poll that growth at that offset is a true
  continuation and not a rollback-then-regrow that happens to land back at or above the same size.
  The cursor is **ALWAYS caller-supplied/caller-owned**: `events tail` is
  stateless across invocations and MUST NOT persist cursor or resume state to disk anywhere —
  not in a command-owned cursor file, not under `.kittify/`, not in a user cache directory, and
  not in any other mission artifact. It is never the command invocation's to own. Persisting the
  offset — and, if the consumer wants cross-restart content-invariant safety, the content invariant
  — across restarts is exclusively the calling consumer's responsibility, via the
  `--from-offset`/`--from-invariant` inputs and the per-envelope offset AND content-invariant
  outputs FR-004 defines. When both are supplied on resume, FR-013 verifies the invariant against
  the current file before trusting anything read from that offset onward and REFUSES the resume
  (structured stderr error, non-zero exit, no Tail envelope emitted) on a mismatch; if only the
  offset is supplied, FR-013 performs structural validation only — cross-restart content-invariant
  safety is opt-in by the consumer choosing to persist and supply the invariant, not automatic from
  persisting the offset alone.
- **Tail envelope**: one JSON line emitted on stdout — either a pass-through of an existing
  `StatusEvent`/`InnerStateChanged` dict as already serialized by `store.py`, or one of the two new
  signal shapes this spec requires: a truncation-resync signal (FR-005/FR-007) and a
  resolve-failure/error signal (FR-009). Per FR-004, every pass-through envelope also carries the
  offset and the FR-005 content-invariant value (a fixed-size SHA-256 hex digest, never the raw
  event bytes — see Clarifications §5) immediately past the emitted event, so a consumer
  can persist both without deriving them itself. The exact JSON schema for the two new signal
  shapes, and for the offset/content-invariant fields, is an implementation-phase decision this
  spec does not pre-empt beyond requiring they be distinguishable from a normal event envelope
  (e.g. a `"type"` discriminator absent from ordinary `StatusEvent` rows). **Distinct from the
  canonical "Event Envelope" glossary term**
  (`docs/context/system-events.md`), which names a differently-shaped wrapper (`event_id`,
  `event_type`, `aggregate_id`, `lamport_clock`, `payload`); a "Tail envelope" here is always either
  a raw `StatusEvent` JSON line or one of this mission's own signal shapes, never that canonical
  schema.
- **Mission log file**: `status.events.jsonl` at `<feature_dir>/` (per-mission,
  `MISSION_EVENTS_FILENAME`), the sole MVP target. The project-wide `canonical-events.jsonl` at
  `.kittify/` (`PROJECT_EVENTS_FILENAME`) is out of scope (FR-012).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An external consumer can replace a custom filesystem-watch loop with
  `spec-kitty events tail --mission <slug> --json` and receive every event already in the log
  followed by every newly appended event, in file order, with zero manual retry/backoff logic on
  the consumer side for the torn-read cases in FR-006/FR-007.
- **SC-002**: A rollback truncation — whether observed as a size shrink on the next poll, or as a
  truncate-then-regrow whose content invariant no longer matches (FR-005) — is detected while the
  consumer is running and produces an explicit `log_truncated`-shaped signal on the stream; 0% of
  truncation events of either shape are silently absorbed as "no new data" across the test suite
  built for this mission. A rollback-then-regrow that completes entirely while the consumer is
  offline is equally covered on resume (FR-013 / User Story 3 Acceptance Scenario 4): 0% of such
  offline content-invariant mismatches are silently resumed from — every one produces FR-013's
  refusal (structured stderr error, non-zero exit, no Tail envelope emitted) rather than a stream
  that looks like an ordinary successful resume.
- **SC-003**: 100% of the bounded-generator-core's tests (reader logic) terminate without relying
  on a wall-clock kill — i.e. every core test uses `--once`/`max_events`/`itertools.islice` or
  equivalent, never an unbounded loop under a test timeout.
- **SC-004**: Every new test added by this mission's later implementation work packages carries a
  pytest marker matched by at least one CI job in `.github/workflows/ci-quality.yml` (per C-008) —
  verified by naming the job in the WP itself, not discovered after a red CI run.
- **SC-005**: Running `events tail` concurrently against a mission's log while that mission's own
  normal write paths (emit pipeline, lifecycle/retrospective/decision writers) continue operating
  produces zero observable change to the writer side's behavior or timing (NFR-004) — validated by
  a test that runs writer operations and `events tail` (bounded) against the same mission
  directory and asserts the writer's own event count/content is unaffected by the reader's
  presence.
