# Tracer: Approach — events-tail (`event-push-watch-channel-01M1K6W2`)

Seeded at plan phase (charter Standing Order #3, `mission-tracer-files` procedure). Appended
during implementation; assessed at close.

## The seam decision (plan.md "Architectural Seam: Core vs. Shell")

The mission's whole engineering weight lives in one seam decision, made explicit here so it
survives independently of the full plan prose:

- **Core** — `src/specify_cli/status/tail_reader.py`. Stdlib only, zero Typer/CLI imports. Three
  functions: `poll_once(path, cursor) -> PollResult` (one reopen-stat-read-parse pass, no loop, no
  sleep — the actual novel domain logic: dual truncation detection, mid-line tear tolerance,
  reopen-by-path), `validate_resume_cursor(path, offset, invariant) -> TailCursor` (the FR-013
  cold-resume refusal gate, a distinct code path from `poll_once`'s live FR-005 resync because a
  cold resume has no in-memory line-length to draw on and must backward-scan the file), and
  `tail_events(path, cursor, *, max_events, poll_interval, sleep_fn) -> Iterator[dict]` (the
  literal FR-011 "bounded generator" — built on `poll_once` plus an injectable `sleep_fn` so tests
  never actually sleep).
- **Shell** — `src/specify_cli/cli/commands/events.py`. Owns no loop construct of its own — it
  merely iterates `tail_events()` in a plain `for` loop. Owns flag parsing, `resolve_mission_handle()`
  reuse, and JSON rendering. Contains zero domain logic — it is glue by design (tiered rigour: more
  testing weight on the core than the shell).

## Why this split, concretely

`poll_once()` is callable directly against a hand-crafted file at any state (empty, torn trailing
line, size-shrunk, truncate-then-regrown with a bad hash) with **zero loop and zero sleep** — so
every truncation/tear test in the mission is a plain function call, never a generator or a CLI
invocation. This is what makes NFR-001 ("MUST terminate without relying on a wall-clock timeout
to kill a runaway loop") true by construction rather than by discipline. The alternative
(one big generator doing reopen+poll+sleep+truncation-check+parse all in one loop) would force
every truncation test to also deal with generator/sleep semantics — exactly the kind of test that
tempts an author into "well it probably passes" rather than a direct, deterministic assertion.

## Why the sibling-mission failure matters here

A sibling mission was rejected today (severity 4) for testing only the mid-line-tear shape and
never independently testing the clean-record-boundary-truncation shape — a reader that only checks
"does the tail parse" will read a cleanly-truncated file successfully and report a confidently
wrong (incomplete) result. This mission's IC-02 concern is explicitly split out and given its own
ATDD requirement (two independently-failing-first tests, not one test standing in for both shapes)
specifically because of that finding.
