# Implementation Plan: Events Tail — Push/Watch Channel for External Consumers

**Branch**: `feat/event-push-watch-channel-3841` | **Date**: 2026-09-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/event-push-watch-channel-01M1K6W2/spec.md`
**Ruling honored**: [reviews/spec.ruling.md](./reviews/spec.ruling.md) — content invariant is a SHA-256
hex digest, no raw-bytes branch. This plan does not re-open that decision.
**Status**: Ready for `/spec-kitty.tasks`.

## Summary

`spec-kitty events tail --mission <slug> --json` (Option 1 only, C-001) replaces an external
consumer's own filesystem-watcher with a single Typer command that streams `status.events.jsonl`
as JSON lines. The issue's premise that the writer's own guarantees are "inherited for free" is
false (spec Clarifications §2, verified against `transaction.py`/`store.py` in this checkout): the
log is truncatable (rollback), only 2 of 6+ writers take the feature status lock (`SK-131`), the
inode is replaced on every locked write, and the existing `read_events_raw()` is one-shot,
non-resumable, and hard-fails on the first bad line. **This mission is therefore a new small
reader subsystem** — a resumable, tolerant, dual-truncation-detecting cursor and poll primitive —
not a thin CLI wrapper over existing store functions.

The architecture splits into a **pure, finite core** (`src/specify_cli/status/tail_reader.py`) that
does one reopen-stat-read-parse pass per call with zero internal sleeping, and a **thin, infinite
CLI shell** (`src/specify_cli/cli/commands/events.py`) that owns the `while True` + `time.sleep`
polling loop and all mission-slug/flag resolution. This split is what makes FR-006 (mid-line tear
tolerance) and FR-005/FR-007/FR-013 (dual truncation detection: size-shrink AND content-invariant,
independently) unit-testable with zero wall-clock risk — the exact defect class a sibling mission
was rejected at severity 4 for today (only testing the tear shape, not the clean-truncation shape).

## Technical Context

**Language/Version**: Python 3.11+ (spec-kitty CLI internals; repo requires 3.11+, CI runs 3.12).
**Primary Dependencies**: `typer`, `rich` (`err_console`/`CliConsole`), stdlib `hashlib`, `json`,
`pathlib`, `time`, `itertools`. No new third-party dependency (C-005: no `watchdog`/`inotify`).
**Storage**: reads only — `<feature_dir>/status.events.jsonl` (`MISSION_EVENTS_FILENAME`,
`src/specify_cli/status/lifecycle_events.py:124`). Never writes (FR-010).
**Testing**: `pytest`; ATDD-first per C-006/charter C-011; markers `fast` (core + CLI-shell unit
tests) and `integration`+`git_repo` (real-writer concurrency proof), per C-008/SK-144.
**Target Platform**: same as the rest of the CLI — Linux/macOS/Windows 10+.
**Project Type**: single project (existing `spec-kitty` CLI package).
**Performance Goals**: poll interval fixed in `[100ms, 1000ms]` (NFR-002); CLI startup/resolve
under the charter's general `<2s` CLI budget.
**Constraints**: C-001 (Option 1 only, no daemon/socket/fleet), C-003 (`--mission`, no
`--feature*` alias on the user-facing surface), C-004 (no `spec-kitty-events` package/contract
change), C-005 (polling only), C-007 (immutable-roots hygiene — no fixture writes under
`kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, `.kittify/missions/`),
C-009 (freeze ULID/clock if fixture missions are minted, per SK-147).
**Scale/Scope**: single-process, single-consumer, single-mission-log tail (FR-012 — project-wide
`canonical-events.jsonl` out of scope).

## Charter Check

*GATE: must pass before design; re-checked after design below.*

- **Single canonical authority**: mission-slug resolution reuses the existing
  `resolve_mission_handle()` (`src/specify_cli/cli/selector_resolution.py:183`) rather than a new
  resolver — this is the canonical FR-009 mechanism already used across the CLI, verified to
  already emit a JSON-mode `{"error": "mission_not_found", "handle": ...}` on stderr with
  `SystemExit(2)` when called with `json_mode=True`. ✅ No new mission-resolution logic.
- **Architectural alignment**: new reader core lands in `src/specify_cli/status/` (adjacent to
  `store.py`, the module it reads bytes alongside but does not import write helpers from — it
  reads raw bytes itself, see Truncation Detection Design below for why). New CLI shell lands in
  `src/specify_cli/cli/commands/`, registered the same way every other command group is. Neither
  path is `src/charter/` or `src/kernel/`. ✅
- **ATDD-first (C-011)**: every WP below gets a failing-first test as its own commit, RED verified
  on the merge-base `db5014ab5` (== current `main` tip == this mission's `planning_base_branch`
  fork point), GREEN on the WP's final commit. ✅ (see Test Strategy / Implementation Concern Map)
- **Domain-driven splits + tiered rigour**: MORE rigour on the core (the actual domain logic —
  truncation/tear discrimination) than on the CLI shell (glue). Reflected in WP granularity below:
  3 of 5 WPs are core-only. ✅
- **Terminology adherence**: `--mission`, never `--feature*`, on the new command surface (C-003);
  internal Python params may keep `feature_dir` (existing convention, e.g. `store.py`,
  `lifecycle_events.py`). ✅
- **Campsite cleaning**: see "Campsite-Clean Scope" below — no debt found on the touched surface
  that warrants a preceding behaviour-preserving commit.

No charter violations → Complexity Tracking is empty (template section retained, marked N/A).

## Corrected Premise & Closed Decisions (do not re-derive)

Recap only — full rationale lives in `spec.md` Clarifications §1–§5 and `reviews/spec.ruling.md`:

1. **Scope is Option 1 only** (C-001) — no daemon, socket, or fleet aggregation, even as a
   partial on-ramp.
2. **The event log is not append-only** — `BookkeepingTransaction._rollback()`
   (`src/specify_cli/coordination/transaction.py:921`, truncate at `:938`, unlink at `:940` —
   verified against this checkout) can shrink or delete the file. This is why User Story 2 (dual
   truncation detection) is P1, not an edge polish item.
3. **The content invariant is a SHA-256 hex digest, never raw bytes** (operator ruling, spec
   Clarifications §5). This plan's Truncation Detection Design section below states precisely
   *what bytes* get hashed — that is the one genuinely open implementation question the ruling
   left for the plan phase, not the hash-vs-raw-bytes choice itself.
4. **`spec-kitty-events` needs no change** (C-004) — see Contracts section below.

## Project Structure

### Documentation (this mission)

```
kitty-specs/event-push-watch-channel-01M1K6W2/
├── plan.md                        # this file
├── tracer-approach.md             # seeded this phase (see Tracer Files below)
├── tracer-design-decisions.md     # seeded this phase
├── tracer-tooling-friction.md     # seeded empty this phase, appended during implementation
└── tasks.md / tasks/*.md          # Phase 2 output (/spec-kitty.tasks — NOT this command)
```

### Source Code (repository root — real paths, verified against this checkout)

```
src/specify_cli/status/
├── store.py                # UNCHANGED — read only, never imported for write helpers by the new reader
├── lifecycle_events.py      # UNCHANGED — MISSION_EVENTS_FILENAME (:124) is the only symbol consumed
└── tail_reader.py           # NEW (this mission) — the bounded core: TailCursor, poll_once(),
                              # validate_resume_cursor(), tail_events(). No CLI/typer imports.

src/specify_cli/cli/commands/
├── __init__.py               # ONE narrow edit: add `events` import + app.add_typer(...) between
                              # the existing `docs` (line ~273) and `glossary` (line ~274)
                              # registrations — shared file, see Write-Scope Disjointness below.
└── events.py                 # NEW (this mission) — the thin shell: Typer app, `tail` command,
                              # flag parsing/validation, resolve_mission_handle() reuse, the
                              # while True + time.sleep poll loop, stdout/stderr JSON rendering.

docs/api/cli-commands.md      # NEW section `## spec-kitty events` + `## spec-kitty events tail`,
                              # inserted between the existing `doctrine validate` and `glossary`
                              # sections (alphabetical slot, verified against the current file).
docs/context/system-events.md # candidate glossary entries for Tail cursor / resume token /
                              # log_truncated / Tail envelope (see Contracts + Gate Set below).
src/specify_cli/.contextive/system-events.yml # GENERATED — regenerate via
                              # `generate_contextive_glossaries.py generate` and commit in the same
                              # commit as the docs/context/system-events.md edit above (see
                              # Contracts, Glossary candidates, for the verified file path).

tests/status/
└── test_tail_reader.py       # NEW — core tests (poll_once, validate_resume_cursor, tail_events)

tests/cli/
└── test_events_tail.py       # NEW — CLI-shell tests (bounded CliRunner invocations only)
```

**Structure Decision**: single project, no new top-level package. The core lands beside `store.py`
because it is domain logic over the same file format (`status.events.jsonl`) but is deliberately
NOT added to `store.py` itself — `store.py`'s existing readers (`read_events_raw`,
`read_events`) are one-shot, whole-file, hard-fail-on-bad-JSON by design and are used
by code paths (materialize, doctor, migrate) that legitimately want "fail loud on any corruption."
Merging the tolerant/resumable/truncation-aware reader into the same functions would either
weaken those callers' correctness guarantees or force a parameterized dual-mode API on a module
that is already large. A new sibling module keeps `store.py`'s existing contract untouched
(Locality of Change) while giving the new reader its own focused surface (smallest-viable-diff
picks the file set: one new file, not an edit to a stable one).

## Architectural Seam: Core vs. Shell (FR-011 / NFR-001)

**Core** — `src/specify_cli/status/tail_reader.py`, zero Typer/CLI imports, stdlib only:

```python
DEFAULT_POLL_INTERVAL_SECONDS: float = 0.25          # NFR-002: within [0.1s, 1.0s]
EMPTY_DIGEST: str = hashlib.sha256(b"").hexdigest()   # noqa: TID251 — file-integrity content
                                                        # invariant, not the charter hash (see
                                                        # Truncation Detection Design)

@dataclass(frozen=True)
class TailCursor:
    offset: int
    content_invariant: str   # 64-char lowercase hex SHA-256, or EMPTY_DIGEST at offset 0

class ResumeRefused(Exception):
    reason: str   # "negative" | "out_of_range" | "misaligned" | "content_mismatch"

def poll_once(path: Path, cursor: TailCursor) -> PollResult: ...
def validate_resume_cursor(path: Path, offset: int, invariant: str | None) -> TailCursor: ...
def tail_events(
    path: Path, cursor: TailCursor, *,
    max_events: int | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Iterator[dict[str, Any]]: ...
```

- **`poll_once()`** is the true engineering core: ONE reopen-by-path → stat → dual-truncation-check
  → drain-available-complete-lines → parse pass. It never sleeps and never loops internally, so it
  always terminates by construction — no `itertools.islice`/bound is even needed to test it
  directly. It is called with hand-crafted files at every state (empty, mid-write, truncated,
  truncate-then-regrown, normal growth) for FR-002/003/005/006/007/008 coverage. **This is the
  piece that does the actual novel domain work**; everything else composes it.
- **`validate_resume_cursor()`** is the FR-013 resume-time gate — called exactly once, before any
  streaming begins, when `--from-offset` is supplied. Deliberately a SEPARATE function from
  `poll_once()`'s live FR-005 resync path (see Truncation Detection Design — the two paths differ
  in what state they have available, not just in what they do on mismatch).
- **`tail_events()`** is the literal "pure, finite generator/iterator core... terminable via
  `itertools.islice`, a `max_events` cap" FR-011 names: a generator built on top of `poll_once()`
  plus an **injectable `sleep_fn`**. Core-level tests pass `sleep_fn=lambda _: None` (or a
  call-counting stub) so `max_events`/`itertools.islice` bound the generator with **zero real
  wall-clock wait**, satisfying NFR-001 ("no test needs to hang a `while True` loop... no test
  relies on a wall-clock timeout") literally, not just in spirit.

**Shell** — `src/specify_cli/cli/commands/events.py`, registered via
`app.add_typer(events_module.app, name="events")` in
`src/specify_cli/cli/commands/__init__.py` (narrow insertion between the `docs` and `glossary`
registrations, matching spec C-002's citation):

```python
app = typer.Typer(help="Event log tailing commands")

@app.command("tail")
def tail_command(
    mission: str = typer.Option(..., "--mission", ...),
    json_output: bool = typer.Option(True, "--json", ...),   # see "CLI Surface" below
    once: bool = typer.Option(False, "--once", ...),
    max_events: int | None = typer.Option(None, "--max-events", ...),
    from_offset: int | None = typer.Option(None, "--from-offset", ...),
    from_invariant: str | None = typer.Option(None, "--from-invariant", ...),
) -> None: ...
```

The shell does exactly four things, none of them novel domain logic: (1) FR-004's own-flag-combo
usage check (`--from-invariant` without `--from-offset`); (2) resolve the mission slug via the
existing `resolve_mission_handle()` (FR-009 — zero new code); (3) if `--from-offset` given, call
`validate_resume_cursor()` and turn a `ResumeRefused` into the FR-013 stderr envelope + non-zero
exit; (4) drive the core — `--once` calls `poll_once()` **directly, once, no generator, no sleep**
(this is why User Story 1 AC1's "exits 0 without blocking" is trivially true, not something the
polling machinery has to special-case); otherwise it iterates `tail_events()` (optionally wrapped
in `itertools.islice(..., max_events)`), printing one `json.dumps(envelope)` line per item via
plain `print` (never Rich markup on stdout, matching `docs.py`'s existing `--json` convention).

**How this avoids ever exercising the shell's infinite loop in tests**:
- Core (`poll_once`, `validate_resume_cursor`) tests: zero loop, zero sleep, zero generator —
  direct function calls against crafted files.
- Core (`tail_events`) tests: real generator, but `sleep_fn` injected as a no-op/counting stub and
  bounded by `max_events`/`itertools.islice` — deterministic, sub-millisecond.
- Shell (CLI) tests: `CliRunner` invocations pass **only** `--once` or `--max-events N` (small N,
  e.g. 1–3) — the process always terminates, and at the shell's real `time.sleep(0.25)` default
  this costs well under a second per test even across a few polls. NFR-001's "never a bare
  unbounded `events tail` in CI" is honored by construction: nothing in the test suite ever
  invokes the command without one of these two bounds.

**Reopen-by-path composability (FR-003)**: `poll_once()` reopens the file **by path, inside
itself**, on every call — the shell never holds or threads a file handle. This is a deliberate
choice over the alternative (shell reopens, hands bytes/fh to the core each poll): keeping
reopen-by-path inside the core means `poll_once()`'s own unit tests can directly exercise
"os.replace() swapped the inode between two poll calls" (write a file, call `poll_once`, replace
the file with a different inode via `os.replace`, call `poll_once` again, assert the new inode's
content is observed) with **no CLI/Typer plumbing at all**. Putting reopen in the shell would push
FR-003's actual test coverage up into the CLI-shell test tier for no benefit — the core is the
natural owner of "the thing that must never trust a stale handle," matching Domain-driven-splits
(more rigour on the domain logic than the glue).

**Fd-sharing invariant (closes the INTRA-call race, distinct from the inter-call reopen above)**:
reopening by path once per `poll_once()` call closes the race BETWEEN calls, but says nothing
about races WITHIN a single call unless the call also commits to using that one fd throughout.
This plan makes that commitment explicit: `poll_once()` opens exactly one file descriptor per
call; the size check reads `os.fstat(fd)` on that same descriptor (never a fresh `Path.stat()` or
a second `open()`), and the hash-check read and the new-bytes drain read both read through that
same fd via `seek()`+`read()` — no operation inside a single `poll_once()` call re-resolves the
path after the initial open. Without this, a plausible-but-lazy implementation (e.g.
`path.stat().st_size` for the cheap size check, then a separate `path.open("rb")` for the
hash-check read) would leave a window, narrower than one poll interval, in which a writer's
rollback-truncate (`transaction.py:938`, an in-place `fh.truncate` on the SAME inode) or a
locked-writer `os.replace()` inode swap (`store.py:392`) lands between the two operations — the
size check would observe one snapshot and the hash check a different, later one, silently
defeating User Story 2 Scenario 3's guarantee even though both checks individually "ran." Every
read inside `poll_once()` — size, hash-check, and drain — must therefore share the one fd opened
at the top of the call.

**Same commitment for `validate_resume_cursor()` (FR-013, the cold-resume sibling)**:
`validate_resume_cursor()` performs an analogous multi-step sequence against the same
live-writer-mutable file to reach its fail-closed accept/refuse decision — a structural (in-range)
check against the file's current size, then (per Truncation Detection Design below) a backward
scan from `O - 1` to find `start_of_last_line`, then a hash-check read of
`[start_of_last_line, O)`. The identical TOCTOU window applies here: `path.stat()` for the
structural check followed by a fresh `path.open("rb")` for the backward-scan-and-hash read would
let a concurrently running writer's rollback-truncate or `os.replace()` inode swap land between
the two operations, so the structural check and the hash check observe two different snapshots —
exactly the race the paragraph above closes for `poll_once()`, just on the resume path (FR-013
explicitly makes this a normal, not edge-case, race per NFR-004). `validate_resume_cursor()`
therefore makes the same single-fd commitment: it opens exactly one file descriptor per call, and
the structural check (via `os.fstat(fd)`), the backward scan, and the hash-check read all go
through that same fd — no operation inside a single `validate_resume_cursor()` call re-resolves
the path after the initial open.

## Truncation Detection Design (FR-005, FR-007, FR-013)

The spec's FR-005 names two independent checks; to avoid re-using the spec's own overloaded (a)/(b)
lettering (which FR-005 uses for its two *checks* while the Edge Cases section uses (a)/(b) for the
two *failure shapes*), this plan names them distinctly:

- **the size check** (FR-005's mechanism (a)): `current_size < O` (byte size on this poll is
  smaller than the last-consumed offset).
- **the hash check** (FR-005's mechanism (b)): re-verify, on **every** poll, independent of the
  size check and even when `current_size >= O`, that the content immediately preceding `O` still
  hashes to the previously-recorded content invariant.

Both feed the same signal: `log_truncated`, resync from offset 0 (FR-005/FR-007). Neither is ever
satisfied by the other passing — the size check alone misses a truncate-then-regrow that completes
within one poll interval (User Story 2 Scenario 3); the hash check alone would be needlessly
expensive on every ordinary growth-only poll if it were the only check, so both run every poll
(size check first, cheap; hash check always, per FR-005's explicit "independent of (a)").

**What exactly gets hashed** (the one genuinely open question the operator's ruling deliberately
left to plan phase — the ruling fixed *hash, not raw bytes*; it did not fix *hash of what byte
range*): the content invariant is the SHA-256 hex digest of **the bytes of the single most-recently-
consumed complete line, including its trailing `\n`, i.e. the byte range `[start_of_last_line, O)`**
where `O` is guaranteed by construction to be a line boundary (every `poll_once()`/
`validate_resume_cursor()` call that advances or accepts an offset first confirms the byte
immediately before it is `\n`, or that `offset == 0`). This is precisely "the last-consumed
line/boundary bytes immediately preceding offset O" from FR-005/the Tail cursor Key Entity — the
two phrasings in the spec describe the same range, not an either/or.

**Why this range, not a fixed last-N-bytes window**: `--from-offset`/`--from-invariant` is the
ONLY state a cold-resuming consumer supplies (FR-004) — no line-length parameter exists on the
CLI surface, and the Tail cursor Key Entity deliberately keeps the external contract to just
offset + invariant. Because `O` is always a line boundary, "the last consumed line" can always be
re-derived purely from the file and `O`, with no persisted length: scan backward from `O - 1` for
the previous `\n` (or beginning-of-file) to find `start_of_last_line`. `EMPTY_DIGEST` (SHA-256 of
`b""`) is the canonical sentinel for `O == 0` (nothing consumed yet) — this is a plan-authored
implementation choice (not spec-mandated) needed to make `--from-offset 0 --from-invariant <x>`
well-defined rather than a silently-ignored no-op check.

**Why this is a distinct code path from the live path, not just distinct in outcome**: a
**live, already-running** `tail_events()`/`poll_once()` call has the last-consumed line's length
sitting in memory (it just read and hashed those bytes last poll) — no backward scan needed, it
re-reads exactly `[O - L, O)` using the `L` it already knows. A **cold resume**
(`validate_resume_cursor()`) has no such memory — the consumer only handed it `O` and a digest — so
it MUST backward-scan the file to find `start_of_last_line` before it can even compute a digest to
compare. This is a genuine algorithmic difference (not just "resync-from-0 vs. refuse" semantics),
which is why `validate_resume_cursor()` is its own function rather than a parameter on
`poll_once()`.

**FR-007 (clean truncation must fire even when the remainder still parses)**: the size check and
hash check both run **before** any line-parsing happens on the new bytes for this poll. A
clean-truncation-then-regrowth where the surviving bytes happen to still be valid JSON is caught by
the hash check regardless of whether parsing would have "succeeded" — parsing is never consulted to
decide truncation, only the two byte-level checks are. This is the direct fix for the sibling
mission's rejected defect (a reader that only checks "does it parse" never sees shape-b at all).

**`hashlib.sha256` is a repo-wide TID251-banned import** (`pyproject.toml:317`) — enforced across
`src/` and the entire `tests/` tree (no directory-level exemption for `tests/`, per the ADR comment
at `pyproject.toml:283`). The banned-API message explicitly names "file-integrity checksums" as a
sanctioned non-charter use requiring only an inline `# noqa: TID251 — <justification>` at each call
site — this mission's content invariant is exactly that use, and must NOT call
`charter.hasher.hash_content()` (a different algorithm: BOM/newline-normalized charter markdown
text, prefixed `"sha256:..."`) instead. **Every `hashlib.sha256(...)` call site in `tail_reader.py`
and in this mission's own tests needs its own inline noqa** — this is a real, easy-to-miss TID251
lint failure a WP author would otherwise only discover at CI, not at plan time.

**FR-013 vs. FR-005 as distinct code paths**: `poll_once()`'s truncation detection (size+hash) is
the FR-005 **live resync-from-0** path — it always has a next action (resync and keep streaming).
`validate_resume_cursor()` is the FR-013 **refuse-before-streaming** path — on any mismatch
(structural: negative, out-of-range, misaligned; or content: hash mismatch) it raises
`ResumeRefused` and the shell never calls `tail_events()`/`poll_once()` at all for that invocation —
zero Tail envelopes emitted, matching every User Story 3 acceptance scenario's "no Tail envelope
emitted for the invocation" language precisely.

## Mid-Line JSON Tear Tolerance (FR-006)

The discriminating question is: **does the byte range that failed to parse extend to the current
end of file (no trailing `\n`), or is it `\n`-terminated?**

Reasoning, verified against the actual writers: the **locked** pipeline
(`store.py:358` `_append_serialized_atomic`) builds the full new content in a temp file, `fsync`s
it, then `os.replace()`s — POSIX guarantees a reader sees either the fully-old or fully-new file,
never a partial write mid-rename. The **unlocked** writers (`store.py:292` `append_event`, and the
retrospective/decision/lifecycle writers) do a single `open(path, "a")` + one `write()` call for
one line — SK-131 measured this non-atomic for large lines (610KB). Because appends only ever
extend the file at the end, a torn write can only ever manifest as an incomplete **trailing**
sequence of bytes with no terminating `\n` yet. Any interior, already-`\n`-terminated line that
fails to parse is not a tear by construction — those bytes were already stable and previously
either unread (first time seen) or already successfully parsed (impossible to un-parse without a
truncation, which the size/hash checks catch first, ahead of any parsing).

`poll_once()`'s per-poll parse step therefore: reads all new bytes from `O` to `current_size`,
splits on `\n`, and for every chunk **except** a possible non-`\n`-terminated final remainder,
requires successful `json.loads`. The trailing non-terminated remainder (if any) is never parsed
this poll — it is left unconsumed (offset does not advance past it), retried next poll once more
bytes (and, presumably, its terminating `\n`) have arrived. No signal is emitted for it (NFR-003's
explicit FR-006 exemption). If an interior, `\n`-terminated chunk fails `json.loads`, that is
treated as a fatal condition distinct from both `log_truncated` and the tear-retry path — this case
is not named by any FR (it would indicate corruption the mission is not scoped to auto-recover
from) and mirrors `read_events_raw()`'s existing "raise on bad JSON" precedent rather than
inventing new silent-tolerance behavior NFR-003 would then have to justify.

## Tail Envelope & Cursor Schema (plan-authored, within the spec's declared open space)

The spec explicitly leaves "the exact JSON schema for the two new signal shapes, and for the
offset/content-invariant fields... an implementation-phase decision" (Key Entities, Tail envelope),
requiring only that they be distinguishable from an ordinary `StatusEvent` row. This plan commits
to:

- **Pass-through envelope** (stdout): the existing `StatusEvent` JSON dict, unmodified, plus two
  reader-injected sibling keys — `tail_offset: int` (byte offset immediately after this line) and
  `tail_invariant: str` (the SHA-256 hex digest that offset now represents). The `tail_` prefix
  avoids any collision with existing/future `StatusEvent` fields (verified: no `offset` or
  `*invariant*` field exists on `StatusEvent` today) and self-documents these as reader-added, not
  writer-authored.
- **Truncation signal** (stdout): `{"type": "log_truncated", "reason": "size_shrink" |
  "content_mismatch", "detected_at_offset": <O>, "tail_offset": 0, "tail_invariant":
  "<EMPTY_DIGEST>"}` — the discriminator (`"type"` absent from ordinary rows) satisfies the Key
  Entity's distinguishability requirement.
- **Resolve-failure / usage-error / resume-refused signal**: **stderr only, never on the stdout
  Tail-envelope stream** — this plan resolves a soft imprecision in the spec's Key Entities prose
  (which loosely groups this under "Tail envelope" shapes) in favor of the literal, repeated,
  unambiguous language in FR-009/FR-004/FR-013 and every related acceptance scenario ("a structured
  error on stderr... no Tail envelope emitted"). Modeled on the existing
  `agent_retrospect.py:593` (equivalently `:600`) pattern: `_err_console.print_json(json.dumps({
  "error": <code>, "detail": <message>}))` + `raise typer.Exit(<n>)`, not `typer.BadParameter`
  (which renders Typer's own usage text, not this mission's JSON shape) — codes:
  `"mission_not_found"` (delegates entirely to `resolve_mission_handle`'s own JSON-mode output),
  `"usage_error"` (FR-004's invariant-without-offset case), `"invalid_resume_offset"` (FR-013
  structural), and `"resume_content_mismatch"` (FR-013 content). **Do NOT copy the same file's
  `mission_not_found` branch (~lines 408-419) as the model** — that branch prints via
  `_console.print_json` (the STDOUT console, `specify_cli.cli.console.console`, imported as
  `_console`; `agent_retrospect.py:21`), not `_err_console` (the STDERR console,
  `agent_retrospect.py:22` — two distinct `CliConsole` instances, `src/specify_cli/cli/console.py:
  126-127`), and uses a different, richer schema (`schema_version`/`command`/`status`/`outcome`/
  `error`/`handle`/`next_action`). Copying it verbatim would both leak onto stdout and use the
  wrong envelope shape, contradicting Design Decision #3 below.

## CLI Surface

- `--mission <slug>` (required) — resolved via `resolve_mission_handle(mission, repo_root,
  json_mode=True)`. No new resolution code (Charter Check above).
- `--json` (boolean, default `True`) — every User Story/acceptance scenario shows `--json` on the
  invocation, and Edge Cases states "`--json` is the only supported output mode for MVP... do not
  build" a human mode. This plan therefore makes JSON the command's **only** behavior; `--json` is
  accepted (for literal parity with the issue's invocation and consistency with `docs query
  --json`) but currently has no observable effect either way — no `if not json_output: ...`
  branch is built, since no FR requires one and building one would be speculative surface for a
  mode that does not exist yet.
- `--once` (boolean) — single `poll_once()` call, print what's there, exit 0. No sleep, no
  generator involved at all.
- `--max-events N` (int) — bounds `tail_events()` via `itertools.islice`.
- `--from-offset N` / `--from-invariant HEX` — FR-004's resume mechanism; `--from-invariant`
  without `--from-offset` is rejected before any read (FR-004, ruling item SPEC-FRESH2-003).

## Generated Docs (`docs/api/cli-commands.md`)

This is a NEW user-facing command (`events`, `events tail`), so `docs/api/cli-commands.md` DOES
need an update — omitting it would leave the canonical CLI reference silently out of sync, which
`tests/architectural/test_docs_cli_reference_parity.py` (run by the `fast-tests-docs` job whenever
`docs/` changes, confirmed present in `.github/workflows/ci-quality.yml`) would then fail on.

`scripts/docs/build_cli_reference.py:123`'s `capture_help()` hardcodes
`cmd_runner: Sequence[str] = ("uv", "run", "spec-kitty")` — calling it as shipped re-syncs the
environment via `uv run`, which this repo's own `AGENTS.md` documents as destructive to a
hand-built `.venv` (cost a prior mission four rebuilds). **Do not run the generator as a
subprocess.** The sanctioned, independently-confirmed-byte-identical workaround: monkeypatch
`cmd_runner` to `(".venv/bin/spec-kitty",)` and call the script's own `main()` in-process, then
hand-scope the resulting diff to **only** the new `events`/`events tail` sections — commit that
diff alone, not a full regen sweep (a full regen would pull in unrelated drift from other commands
whose help text may have changed for unrelated reasons since the doc was last generated, which is
explicitly out of this mission's Locality of Change).

## Contracts

- **`spec-kitty-events` needs no change.** It is a real external PyPI dependency
  (`>=6.0.0,<7.0.0`, pinned in `pyproject.toml`), not vendored — this mission does not touch
  `pyproject.toml`, `uv.lock`, or any compat manifest. `status.events.jsonl` rows are spec-kitty's
  own local `StatusEvent` dataclass (`src/specify_cli/status/models.py`), structurally unrelated
  to `spec_kitty_events.Event`. The `check-spec-kitty-events-alignment` workflow
  (`.github/workflows/check-spec-kitty-events-alignment.yml`, confirmed present, path-filtered on
  package/lock changes) is not expected to fire on this mission's diff.
- **No doctrine schema, mission step contract, or orchestrator-api surface moves.** This mission
  adds a CLI command and a status-package reader module; it does not touch `src/doctrine/`,
  `src/specify_cli/orchestrator_api/`, or any mission-type/step-contract YAML.
- **Glossary candidates (spec Clarifications §4)**: `docs/context/system-events.md` today defines
  the canonical **Event Envelope** term (`event_id`/`event_type`/`aggregate_id`/`lamport_clock`/
  `payload`) but has no entries for Tail cursor / resume token / `log_truncated` / Tail envelope
  (verified: grepped the file's headings). Spec Clarifications §4 leaves both *whether* and *when*
  to register these terms open — "to be resolved at plan/implement time, not decided unilaterally
  by this document" — so this plan must decide, and must route that decision through the charter's
  own `RECONCILE_CHANGE_SCOPE_TENSIONS` policy (`.kittify/charter/charter.md`, "Reconciling
  change-scope tensions" section) rather than an implicit call.

  **Verified correction (this plan's earlier draft was wrong here)**: the Contextive
  glossary-freshness step (`scripts/generate_contextive_glossaries.py check`, invoked by the
  `lint` job at `.github/workflows/ci-quality.yml:851`) does **not** require these entries to
  exist. `cmd_check()` (`scripts/generate_contextive_glossaries.py:329`) only diffs the
  already-generated `src/specify_cli/.contextive/*.yml` / scope `.contextive.yml` files against
  what `generate()` would produce from the *already-committed* `docs/context/*.md` — it has no
  notion of code-introduced terms at all. If IC-04 makes zero changes to
  `docs/context/system-events.md`, the check step stays green regardless (nothing in `docs/context`
  changed, so nothing is stale); registering the terms is orthogonal to that gate, not a
  precondition for it. An earlier draft of this section claimed the glossary commit "is what keeps
  that gate green" — that claim is retracted as false.

  **Decision (a Locality-of-Change judgment call, not a CI mandate)**: this plan still
  chooses to **register the terms now, in IC-04's own final commit**, because they land in shipped,
  user-facing envelope JSON and CLI help text the moment this mission merges — per Locality of
  Change's own extension clause, capturing them alongside the surface that introduces them is
  directly connected to the goal and proportional (this paragraph is the required one-line
  rationale; see the reconciliation walk-through immediately below). This is consistent in spirit
  with the repo's general tidy-first/terminology-capture convention (charter Standing Order #2,
  campsite/Boy-Scout discipline), cited here only as color/precedent — **not** as licensing
  authority, since the walk-through below is explicit that Boy-Scout itself cannot license this
  addition. Reconciling the three change-scope rules per `RECONCILE_CHANGE_SCOPE_TENSIONS`: smallest-viable-diff would not put
  `docs/context/system-events.md` in IC-04's file set on its own (no gate requires it, unlike
  `docs/api/cli-commands.md` — genuinely required by
  `tests/architectural/test_docs_cli_reference_parity.py`, confirmed present in this checkout); the
  Boy-Scout Rule **cannot** license adding it — the charter's own reconciliation order (`.kittify/
  charter/charter.md`, "Reconciling change-scope tensions", step 2) is explicit that Boy-Scout
  governs cleanup strictly *inside* the file set step 1 already chose, "without adding files to the
  set chosen in step 1"; the addition is licensed **solely** by step 3, Locality of Change's
  extension clause — it is directly connected to the goal (the terms exist only because this WP's
  own envelope/CLI surface introduces them), proportional (four terms, one file), and this
  paragraph is its required one-line rationale.

  The entries must explicitly cross-reference and distinguish from the existing "Event Envelope"
  term (spec's own instruction), not silently reuse similar wording. **Because registering the
  terms DOES make the generated Contextive files stale relative to `docs/context/system-events.md`,
  IC-04's task description must include the regeneration step this plan's earlier draft omitted
  entirely** (confirmed: zero occurrences of `generate_contextive_glossaries.py generate` existed
  anywhere in this plan before this fix): after editing `docs/context/system-events.md`, run
  `python scripts/generate_contextive_glossaries.py generate` and commit the resulting diff.

  **Verified exact file(s) affected** (empirically checked in this checkout by adding then
  reverting a probe entry and running `generate`): per `.kittify/traceability/contextive-map.yaml`,
  `docs/context/system-events.md` renders to exactly one context-level file,
  `src/specify_cli/.contextive/system-events.yml` — that file's content changes and is the one that
  must be committed alongside the markdown edit. `generate()` also rewrites every scope-level
  `<scope>/.contextive.yml` file (they are `import:` lists keyed off the traceability map, not off
  term content), but confirmed byte-identical output for all of them on this edit — including
  `src/specify_cli/status/.contextive.yml`, which does **not** import the `system-events` context at
  all (its scope entry lists only `orchestration`); the one scope that *does* import
  `system-events` is `src/glossary/.contextive.yml`, and even that file produces no diff from a
  term-content-only change, since its content is the import path list, not the terms. So the
  load-bearing regenerated-file obligation is exactly `src/specify_cli/.contextive/system-events.yml`
  — otherwise `scripts/generate_contextive_glossaries.py check` (the actual enforced step) fails on
  exactly this change, on the next PR that touches `src/specify_cli/**`.

## Campsite-Clean Scope

Read `src/specify_cli/status/store.py` and `src/specify_cli/coordination/transaction.py` in full
for this plan (not just the cited line ranges) looking for domain-matched debt on the surfaces
this mission touches (reads, in `store.py`'s case; nothing, in `transaction.py`'s case — this
mission never calls into `transaction.py`, it only cites it as evidence for the corrected premise).
**No campsite-clean debt found in the touched surface.** `store.py`'s existing functions
(`read_events_raw`, `append_event`, `_append_serialized_atomic`) are internally consistent with
their own documented one-shot/hard-fail contracts — this mission does not modify them, so there is
no "about to change" method to tidy first. The new module (`tail_reader.py`) is new code with no
prior debt to inherit.

## Gate Set

Chosen from the candidate list, each explicitly included or excluded with a reason:

| Gate | Applies? | Why |
|---|---|---|
| `lint` job — ruff (incl. `C901`/mccabe ≤15) | **Yes** | All new code passes through the standard lint job. |
| `lint` job — TID251 banned-API | **Yes, load-bearing** | Every `hashlib.sha256` call site (production AND test) needs an inline `# noqa: TID251 — <justification>`; see Truncation Detection Design. No blanket file exemption. |
| `lint` job — commitlint | **Yes** | Every commit message (conventional-commits, per Mechanics). |
| `lint` job — markdownlint | **Yes** | `docs/api/cli-commands.md`, `docs/context/system-events.md`, and the three tracer `.md` files are touched. |
| `lint` job — Contextive glossary check | **Yes** | `src/specify_cli/**` changes trigger the check step regardless of the glossary decision (verified: `cmd_check()` never inspects code). IC-04's own `docs/context/system-events.md` edit (a Locality-of-Change judgment call, not a gate requirement — see Contracts) makes the paired `generate` run + committed `src/specify_cli/.contextive/system-events.yml` diff load-bearing: skip it and this step fails on that specific edit. |
| `lint` job — Bandit (`S`) | **Yes, advisory** | File I/O only, no shell/eval/pickle/network; no findings expected, but the step runs as part of `lint` regardless. |
| `lint` job — pip-audit | **N/A** | No dependency added; runs anyway as part of `lint` but has nothing new to flag. |
| `fast-tests-status` | **Yes** | Reader-core tests under `tests/status/`, marker `fast` (and not `git_repo`/`integration`/`stress`) — confirmed selector at `ci-quality.yml:1321`. |
| `integration-tests-status` | **Yes** | The real-writer concurrency proof (WP05), marker `integration`+`git_repo`, same path filter, confirmed at `ci-quality.yml:2664`. |
| `fast-tests-cli` | **Yes** | CLI-shell tests under `tests/cli/`, marker `fast`, confirmed at `ci-quality.yml:1559`. |
| `integration-tests-cli` | **Yes, if any WP04 test needs `git_repo`/`integration`** | A real mission-directory fixture for the CLI shell (not a pure-mock resolve) needs this marker; confirmed selector at `ci-quality.yml:2892`. |
| `kernel-tests` | **No** | Covers `src/kernel/` only (confirmed: coverage flag is `--cov` scoped to that package in the reusable `module-kernel.yml`). This mission's code is entirely under `src/specify_cli/`. |
| `mission-loader-coverage` | **No** | Covers `src/specify_cli/mission_loader/` + `tests/unit/mission_loader/`/`tests/integration/test_mission_run_command.py` only (confirmed at `ci-quality.yml:1448`). Unrelated to this mission's surface. |
| `diff-coverage` (job `ci-quality.yml:3308`, `--fail-under=90` on changed lines under a `critical_paths` allowlist) | **Yes, load-bearing on `tail_reader.py`** | `'src/specify_cli/status/*'` is a listed critical path (`ci-quality.yml:3374`, verified) and this mission adds `src/specify_cli/status/tail_reader.py` there — its new/changed lines need ≥90% coverage on the diff specifically, not merely "highest-rigour tier" prose. `src/specify_cli/cli/commands/events.py` is NOT in the critical-path list, so only the advisory full-diff step (not the 90% floor) applies to the CLI shell. This is distinct from, and additive to, the two per-package floors above; `quality-gate`'s `needs:` list includes `diff-coverage` (`ci-quality.yml:4276-4331`), so it is part of the required aggregate check. IC-01/IC-02/IC-03 (the `tail_reader.py` tests) must be written with this floor in mind, not just "be thorough." |
| `arch-adversarial` (tests/architectural, tests/adversarial, tests/architecture, tests/lint) | **Yes, always runs** | Not gated by path-filter; in particular `test_archive_root_byte_identical.py` (C-007) and the dead-code/dead-symbol sweeps run over the whole tree regardless. This mission's fixtures must use `tmp_path`, never real `kitty-specs/` paths (see Constraints). |
| Doctrine schema freshness | **No** | No `.yaml` doctrine artifact touched; this mission adds Python + docs only. |
| `uv-lock-check` | **No** | No dependency added; `pyproject.toml`/`uv.lock` untouched. |
| `check-spec-kitty-events-alignment` | **No** | See Contracts — package/lock untouched, not expected to trigger. |
| `patch()` target validator | **Conditional** | Only relevant if a test patches `time.sleep`/`resolve_mission_handle` — if WP03/WP04's tests mock either, the patch target must be the **importing** module's path (`specify_cli.status.tail_reader.time.sleep`, `specify_cli.cli.commands.events.resolve_mission_handle`), never the defining module's path. Flagged here so a WP author doesn't discover this at CI. |
| Typer JSON error surface | **Yes** | FR-009/FR-004/FR-013's stderr shape is validated against the existing pattern (`agent_retrospect.py:593`/`:600`, `docs.py`'s `--json` plain-print convention) — see Tail Envelope & Cursor Schema above. |
| **SonarCloud** | **Excluded per instruction** | Does not run on pull requests in this repo. |

**Kernel/mission-loader confirmation basis**: `kernel-tests` job (`ci-quality.yml:1085`) delegates
to `module-kernel.yml`, gated on `needs.changes.outputs.kernel`, scoped to `src/kernel/` per its
own docstring comment ("validates the zero-dependency shared utilities in src/kernel"). No file
this mission creates or edits falls under `src/kernel/`.

## Baseline & Pre-existing Red

Per NFR-005 and the charter's baseline-red gotcha: `main` (`db5014ab5`) carries known-red under
tracked issue #3284 (~23 untracked failures + 2 errors per the review-overlay) and a shared
test-venv lock that can time out under concurrency (#3283). **Every WP below must, before its own
red-first commit, run its EXACT targeted test path set against the merge-base
(`db5014ab5`/`upstream main`) and quote the baseline red WITH that path set** — not a bare count —
before treating anything as pre-existing:

```bash
git stash   # or run from a clean worktree checked out at db5014ab5
.venv/bin/python -m pytest tests/status/ tests/specify_cli/status/ -m "fast and not (git_repo or integration or stress)" -q
.venv/bin/python -m pytest tests/cli/ tests/specify_cli/cli/ -m "fast" -q
```

Since `tail_reader.py`/`events.py`/their tests are all NEW files, the realistic baseline-red
finding for this mission is "zero pre-existing red in the exact new test files" (they don't exist
on `main` yet) — the check instead matters for the SURROUNDING suite in the same path set (e.g. if
`fast-tests-status` already has pre-existing red unrelated to this mission, a WP must not
misattribute it as its own regression). If a WP does find pre-existing red not already covered by
#3284/#3283, it must open a GitHub issue reporting it (charter's Pre-existing Failure Reporting
Rule) before proceeding past it.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs; this
> section previews the intended 5-WP shape so the tasks phase has real granularity to slice
> against, not just the requirement table.

### IC-01 — Core primitives: `TailCursor`, `poll_once()`, tear tolerance, missing-file wait

- **Covers**: FR-002 (offset-resumable reads), FR-003 (reopen-by-path), FR-006 (mid-line tear),
  FR-008 (wait for not-yet-created file), NFR-003 (silent success prohibited), NFR-005 (all
  ICs, no new red beyond the #3284 baseline).
- **Tests**: `tests/status/test_tail_reader.py`, `pytestmark = [pytest.mark.fast]`. Collected by
  `fast-tests-status`.
- **ATDD**: failing-first test for "torn trailing line retried, never signaled, emitted exactly
  once once complete" (User Story 4 AC1/AC2) as its own commit before `poll_once()` exists.
- **Also required**: a test enforcing the fd-sharing invariant (see Architectural Seam above) for
  the reads IC-01 exercises — size check and drain read (the hash-check read does not exist until
  IC-02; see IC-02's "Also required" below for its half of this assertion). Give `Path.stat` (or
  `pathlib.Path.stat`) and `pathlib.Path.open` **DIFFERENT tolerance semantics — do NOT apply the
  same "after initial open" condition to both** (see the insufficiency argument below for why a
  shared condition fails). Monkeypatch `pathlib.Path.stat` to raise **UNCONDITIONALLY on ANY
  invocation** from within `poll_once()` — no "after the initial open" carve-out: the design
  mandates `os.fstat(fh.fileno())` exclusively for the size check, so there is zero legitimate call
  to `Path.stat()` anywhere inside `poll_once()`, at any point in the call, meaning any invocation
  at all — first or otherwise — is a defect. Separately, spy on `pathlib.Path.open` and assert it is
  called **exactly ONE** time total per `poll_once()` invocation — a plain call-count assertion, not
  an "after the first call" guard. **Patch `pathlib.Path.open` specifically — do NOT patch `os.open`
  instead**: `Path.open()` does not route through the `os` module's Python-level `os.open()`;
  patching `os.open` alone records ZERO calls when a real file is opened via `Path(...).open("rb")`
  (verified empirically, Python 3.14.6: `unittest.mock.patch("os.open", ...)` around a
  `Path(...).open("rb")` read shows a call count of 0), so a WP author who treats `Path.open` and
  `os.open` as interchangeable mock targets writes a test that silently never fires. If the
  implementation is meant to be free to choose between `os.open`/`io.open`/`Path.open`, spy on all
  three simultaneously instead and assert the combined call count across all three is exactly one.
  **A same-condition "after initial open" guard applied to both patches — or the `Path.open`
  call-count check alone — is NOT sufficient**: the plan's own named lazy implementation
  (`path.stat().st_size` for the cheap size check, then a separate `path.open("rb")` for a later
  read) calls `Path.stat()` **before** the one `Path.open()` call, so an "after initial open"
  condition applied to `Path.stat` never triggers for it (it fires first, not after anything), and
  the open-call-count check also still passes unchanged (there is still only one `open()` call
  total) — a test built this way silently passes against this exact bug. What actually closes the
  gap is the ASYMMETRIC pairing above: `Path.stat` raising unconditionally on ANY call (which
  catches the lazy pattern's `Path.stat()` call regardless of ordering), combined separately with
  the `Path.open` exactly-once-total count (which independently catches a genuinely duplicated
  `open()`). This turns the invariant into a failing test, not an implementation-discipline reminder
  a reviewer has to re-derive.
- **FR-008's missing-file check must go through that same single `Path.open()` call, never through
  a separate existence probe.** `poll_once()` detects "log file does not exist yet" by wrapping its
  one `path.open("rb")` call in `try`/`except FileNotFoundError` — it must NOT call
  `Path.exists()`, `Path.is_file()`, or `Path.is_dir()` anywhere to implement this check. Reason:
  on the CPython versions this repo requires and CI pins (3.11/3.12), those pathlib convenience
  methods are implemented as `try: self.stat() ... except OSError: return False` — i.e. they call
  `Path.stat()` internally — which would both spuriously trip the unconditional-raise `Path.stat`
  fd-sharing test above on every `poll_once()` call (not just missing-file ones) and, more
  fundamentally, would be a second path-resolution/open the single-fd-per-call commitment already
  forbids.

### IC-02 — Truncation detection: size check + hash check + FR-013 resume validation

- **Covers**: FR-005 (both checks, independently, every poll), FR-007 (clean truncation fires even
  when remainder parses, detected via the size check specifically), FR-013
  (`validate_resume_cursor`, structural + content refusal), NFR-003 (silent success prohibited),
  NFR-005 (all ICs, no new red beyond the #3284 baseline).
- **Tests**: `tests/status/test_tail_reader.py` (same file as IC-01, distinct test classes/module
  section — or a second file `test_tail_reader_truncation.py` if IC-01's file grows past a
  reasonable single-file size; WP author's call), `pytestmark = [pytest.mark.fast]`. Collected by
  `fast-tests-status`.
- **ATDD**: THREE separate, independently-invokable **top-level pytest test functions** — not
  `parametrize` cases sharing one function body, not multiple asserts inside one function — named
  separately per the mission brief's explicit warning, so a CI failure names the specific broken
  shape in the test node ID:
  1. shape-(a) tear-is-not-truncation (already IC-01's: a mid-line, non-`\n`-terminated tear is
     retried, never signaled).
  2. **shape-(b) plain clean-boundary truncation, size check only** (Edge Cases shape (b) / User
     Story 2 AC1, literally — this is the test the sibling mission's rejected `design-status` verb
     lacked): truncate a log at a line boundary with **no regrow**, assert the remaining bytes DO
     parse as valid JSON (so the test itself fails if the fixture accidentally constructs a
     mid-line tear instead), and assert `log_truncated` fires anyway via the size check
     specifically (`current_size < O`), independent of whether parsing of the remainder would have
     succeeded. Name this test explicitly (e.g.
     `test_clean_boundary_truncation_detected_via_size_check_even_when_parseable`) as reproducing
     the sibling mission's exact rejected scenario.
  3. shape-clean-truncation-detected-via-hash-even-when-size-regrows (User Story 2 AC3, the
     truncate-then-regrow-within-one-poll race) — committed before the hash check exists, so this
     test cannot pass by accident via the size check alone. The test itself must **assert its own
     precondition** immediately before the `poll_once()`/`tail_events()` call under test — e.g.
     `assert Path(log).stat().st_size >= O` — so "cannot pass by accident via the size check alone"
     is self-evident from the test body, not something a reviewer must reconstruct from the
     Truncation Detection Design section's prose.
- **Also required**: two further fd-sharing-invariant tests (see Architectural Seam above) that
  IC-01 alone cannot exercise, because the hash check and `validate_resume_cursor()` both land in
  this WP. Both re-run IC-01's CORRECTED asymmetric pattern — **not** the "raise if called after the
  initial open" form: that shared condition is defeated by the plan's own named lazy
  `path.stat().st_size`-then-second-`path.open("rb")` implementation, since `Path.stat()` fires
  BEFORE the one `Path.open()` call and therefore never falls "after" it, so a same-condition guard
  (or the open-call-count check alone) silently passes against exactly that bug (see IC-01's "Also
  required" above for the full derivation). The corrected pattern is asymmetric: `Path.stat` raises
  UNCONDITIONALLY on ANY invocation (no "after initial open" carve-out), and `Path.open` is
  separately spied on and asserted to be called exactly ONE time total.
  1. **`poll_once()`'s hash-check read**: re-run IC-01's corrected assertion (monkeypatch
     `Path.stat` to raise unconditionally on any call, and separately spy on `Path.open` — **not
     `os.open`, which does not intercept `Path.open()` calls**, see IC-01's "Also required" above —
     asserting exactly ONE total call) against a poll that actually exercises the hash check — e.g.
     shape 3 above, or any poll where `current_size >= O` — so the assertion now covers all three
     reads the Architectural Seam paragraph names (size, hash-check, drain), not just size and
     drain.
  2. **`validate_resume_cursor()`**: the analogous test for its own fd-sharing commitment (see
     Architectural Seam above) — monkeypatch `Path.stat` to raise unconditionally on ANY invocation
     from within `validate_resume_cursor()` (never only "after its initial open"), and separately
     spy on `Path.open` (**not `os.open`**, per the same caveat above) asserting exactly ONE total
     call, covering the structural (in-range) check, the backward scan, and the hash-check read
     together.
- **Depends-on**: IC-01 (shares `TailCursor`/`PollResult` shapes).

### IC-03 — Bounded generator core: `tail_events()`

- **Covers**: FR-011, NFR-001, NFR-002 (poll interval constant + doc comment stating the chosen
  value and why it's within bounds), NFR-005 (all ICs, no new red beyond the #3284 baseline).
- **Tests**: `tests/status/test_tail_reader.py` (generator-specific tests), `pytestmark =
  [pytest.mark.fast]`. Collected by `fast-tests-status`.
- **ATDD**: failing-first test asserting `tail_events()` with an injected no-op `sleep_fn` and
  `max_events=N` terminates and yields exactly N envelopes with zero real sleep (assert on a
  monotonic-clock delta bound, not just "it returned").
- **Depends-on**: IC-01, IC-02.

### IC-04 — CLI shell: `events tail` command + registration + generated docs + glossary

- **Covers**: FR-001 (command group), FR-004 (resume flags + usage-error rejection), FR-009
  (unresolvable slug — delegates to `resolve_mission_handle`), FR-010 (never writes — a test
  asserts no write syscall path is reachable, e.g. via a read-only bind or a spy on `Path.open`
  mode), FR-012 (per-mission scope only — `--mission` resolves via `MISSION_EVENTS_FILENAME`, no
  project-wide flag exists on the surface at all), NFR-003 (silent success prohibited), NFR-005
  (all ICs, no new red beyond the #3284 baseline).
- **Tests**: `tests/cli/test_events_tail.py`. Fast/mocked-resolution tests: `pytestmark =
  [pytest.mark.fast]`, collected by `fast-tests-cli`. Any test using a real mission fixture
  directory: `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`, collected by
  `integration-tests-cli`.
- **Also lands in this WP's commits**: the `docs/api/cli-commands.md` new-command section (via the
  monkeypatched `capture_help`/`main()` procedure, hand-scoped diff) and the
  `docs/context/system-events.md` glossary candidate entries — both are consequences of this WP
  making the command real and user-facing, not separate functional scope. **The glossary edit is
  NOT complete without a regeneration step**: after editing `docs/context/system-events.md`, run
  `python scripts/generate_contextive_glossaries.py generate` and commit the resulting
  `src/specify_cli/.contextive/system-events.yml` diff in the SAME commit as the markdown edit —
  see Contracts (Glossary candidates) for the verified file path and why this step is load-bearing,
  not optional.
- **ATDD**: failing-first CLI test for User Story 1 AC1 (`--once` against a pre-populated log,
  exits 0, emits exactly N lines) before `events.py` exists.
- **Depends-on**: IC-01, IC-02, IC-03.

### IC-05 — Concurrency / end-to-end proof

- **Covers**: NFR-004 (writer sees zero behavioral change from a concurrent reader), SC-005 (a
  real writer + a real `events tail --max-events N` running against the same mission directory),
  NFR-005 (all ICs, no new red beyond the #3284 baseline).
- **Tests**: real-git/real-writer fixture, freezing `ULID`/`now_utc_iso()` per SK-147 if any
  fixture mission is minted in quick succession (C-009). `pytestmark = [pytest.mark.integration,
  pytest.mark.git_repo]`, likely under `tests/status/` (the interaction under test is
  reader-vs-writer, not the CLI surface) — collected by `integration-tests-status`.
- **ATDD**: failing-first test that runs the emit pipeline (`status.emit.emit_status_transition`)
  concurrently with a bounded `tail_events()` call against the same `feature_dir` and asserts the
  writer's own event count/content is byte-identical to a control run with no reader present.
- **Depends-on**: IC-01 through IC-04 (needs the real command/core to exist to run concurrently).

**Total: 5 WPs.**

## Marker Discipline (recap table, per C-008/SK-144)

| WP | Test file(s) | Marker(s) | CI job |
|---|---|---|---|
| WP01 (IC-01) | `tests/status/test_tail_reader.py` | `fast` | `fast-tests-status` |
| WP02 (IC-02) | `tests/status/test_tail_reader*.py` | `fast` | `fast-tests-status` |
| WP03 (IC-03) | `tests/status/test_tail_reader.py` | `fast` | `fast-tests-status` |
| WP04 (IC-04) | `tests/cli/test_events_tail.py` | `fast` (mocked resolution) / `integration`+`git_repo` (real fixture) | `fast-tests-cli` / `integration-tests-cli` |
| WP05 (IC-05) | `tests/status/test_events_tail_concurrency.py` (new file, distinct from WP01–03's) | `integration`+`git_repo` | `integration-tests-status` |

A WP naming only a directory (not both marker AND job) is incomplete per C-008 — this table is the
binding reference for `/spec-kitty.tasks` to carry forward verbatim into each WP prompt's
validation section.

## `__all__` (charter C-007) Applicability

Confirmed against `.kittify/charter/charter.md` ("`__all__` Declaration Convention" section,
binding per C-007): the requirement applies **only** to modules under `src/charter/` and
`src/kernel/`. This mission's new modules land under `src/specify_cli/cli/commands/` and
`src/specify_cli/status/` — neither path. **C-007's `__all__` requirement does NOT apply.**

## Tracer Files

Seeded this phase (not merely referenced) — see `tracer-approach.md`,
`tracer-design-decisions.md`, `tracer-tooling-friction.md` alongside this plan. `tracer-approach.md`
captures the Core/Shell seam decision from the Architectural Seam section above;
`tracer-design-decisions.md` captures the hash-invariant ruling plus this plan's own byte-range and
stderr-vs-stream resolutions; `tracer-tooling-friction.md` starts near-empty, to be appended during
implementation.

## Write-Scope Disjointness From Concurrently Open Work

This mission's new/touched files — `src/specify_cli/cli/commands/events.py` (new),
`src/specify_cli/status/tail_reader.py` (new), `tests/status/test_tail_reader*.py` (new),
`tests/cli/test_events_tail.py` (new), `docs/api/cli-commands.md` (new section only),
`docs/context/system-events.md` (new entries only), **`src/specify_cli/.contextive/system-events.yml`
(generated, regenerated diff — see Contracts, Glossary candidates, for why this is the one
generated file the glossary registration actually touches)** — do **not** overlap, **with one
verified exception** (`docs/api/cli-commands.md`, called out below):

- **PR #3842**: `src/charter/activation/evidence/orchestrator.py`, `cli/commands/charter/*`,
  `core/agent_config.py`, `git/protection_policy.py`, `cli/commands/_command_surface_doctor.py`,
  **and `docs/api/cli-commands.md`** (see the shared-file callout below). **Checked**
  (`gh pr diff 3842 --name-only`): no `.contextive` path appears in its file list.
- **PR #3845**: `cli/commands/dispatch.py`, `invocation/{executor,router,empty_charter}.py`,
  **and `docs/api/cli-commands.md`** (see the shared-file callout below). **Checked**
  (`gh pr diff 3845 --name-only`): no `.contextive` path appears in its file list.
- **`feat/design-phase-orchestrator-api-3837`** (unpushed): `orchestrator_api/commands.py`,
  `runtime/next/next_invocation_lifecycle.py`, `cli/commands/next_cmd.py`. **Not independently
  checkable from this checkout** — the branch is unpushed and not fetchable here — but its
  previously-stated file scope (three `orchestrator_api`/`runtime`/`cli` files, none under
  `.contextive/`) does not include the generated glossary path either; re-confirm this against the
  branch directly before merging if it has moved since this plan was written.

**Two shared files**:

- `src/specify_cli/cli/commands/__init__.py` — this mission adds exactly one import line and one
  `app.add_typer(...)` call, both narrowly scoped (a new `events` entry, not a reorder of existing
  registrations). None of the three concurrent efforts above touch this same file per their listed
  scopes, so the edit is additive and low-conflict, but it is called out explicitly here as one
  genuinely shared surface.
- `docs/api/cli-commands.md` — both PR #3842 and PR #3845 already modify this file (verified live:
  `gh pr diff 3842 --name-only` and `gh pr diff 3845 --name-only` both list
  `docs/api/cli-commands.md`; both PRs confirmed OPEN via `gh pr view 3842/3845 --json
  state,mergedAt`), which is a real overlap the disjointness claim above does not otherwise account
  for. Re-derived against the live file in this checkout (`docs/api/cli-commands.md`, 5515 lines):
  PR #3842's edit lands at lines 540-548, inside the `## spec-kitty charter list` section
  (528-547); PR #3845's edit lands at lines 1112-1115, inside the `## spec-kitty dispatch` section
  (1096-1118). This mission's own insertion point — IC-04's new `events tail` command section,
  placed alphabetically — falls between `## spec-kitty doctrine validate` (line 2138, the last
  `## spec-kitty doctrine *` heading) and `## spec-kitty glossary` (line 2163), roughly 1000-1600
  lines away from either PR's edit. No textual conflict is expected at that separation, but IC-04's
  implementer must re-diff `docs/api/cli-commands.md` immediately before generating/hand-scoping
  its own docs edit (per the existing "monkeypatch `capture_help`/`main()`, hand-scope the diff"
  procedure), in case the alphabetical insertion point has shifted by the time this mission merges.

## Design Decisions (key, from this plan)

1. **Two-function core split** (`poll_once` vs. `tail_events`) rather than one generator that does
   everything — `poll_once` is the actually-novel domain logic and the thing every FR-005/006/007
   test needs to call directly with zero loop/sleep machinery.
2. **Content invariant = hash of the last-consumed line's bytes (incl. trailing `\n`), range
   `[start_of_last_line, O)`**, re-derivable by backward newline scan on cold resume, kept as a
   digest (not raw bytes) even in the core's own in-memory state for live runs — one verification
   routine serves both the live and cold-resume paths.
3. **Resolve-failure/usage-error/resume-refused signals are stderr-only**, never on the stdout
   Tail-envelope stream — resolves a soft imprecision in the spec's Key Entities prose in favor of
   the literal, repeated FR/AC language.
4. **`--json` is accepted but currently a no-op** — JSON is the only mode; no speculative
   `if not json_output` branch built for a mode that doesn't exist.
5. **`resolve_mission_handle()` reuse for FR-009** — zero new mission-resolution code.
6. **New sibling module (`tail_reader.py`), not an edit to `store.py`** — keeps `store.py`'s
   existing hard-fail-on-corruption contract for its current callers untouched.

## Risks & Mitigations

| Risk | Mitigation | IC |
|---|---|---|
| A WP reproduces the sibling mission's severity-4 defect (tests only shape-tear or only the regrow race, never the plain size-check-alone case) | IC-02's ATDD requires THREE separate, independently-invokable top-level test functions (not parametrize/shared-body), one of which self-asserts it cannot pass via the size check alone, and one of which is the plain shape-(b) size-check case itself | IC-02 |
| `hashlib.sha256` TID251 lint failure discovered only at CI | Flagged explicitly in this plan (Truncation Detection Design + Gate Set) with the exact noqa convention | IC-01/IC-02 |
| Core `tail_events()` test accidentally sleeps for real, making CI flaky/slow | Injectable `sleep_fn`, always overridden to a no-op/stub in core-level tests | IC-03 |
| CLI-shell test invokes `events tail` unbounded, hangs CI | Every CLI test passes `--once` or `--max-events`; no other invocation shape exists in the test suite | IC-04 |
| Fixture test writes into a pre-existing `kitty-specs/` mission dir, tripping `test_archive_root_byte_identical.py` | All fixtures use `tmp_path`-based synthetic mission dirs; never this mission's own `kitty-specs/event-push-watch-channel-01M1K6W2/` tree | IC-01–IC-05 |
| Rapid fixture-mission creation in IC-05 collides on `mid8` (SK-147) | Freeze `ULID`/`now_utc_iso()` per SK-147's pattern if any fixture mission is minted | IC-05 |
| `docs/api/cli-commands.md` regen pulls in unrelated drift | Monkeypatch `cmd_runner`, call `main()` in-process, hand-scope the commit to only the new sections | IC-04 |
| Glossary entries introduce term drift vs. existing "Event Envelope" | Entries explicitly cross-reference and distinguish, per spec's own Key Entity instruction | IC-04 |

## Test Strategy (ATDD, red-first)

- **Red-first, per WP, verified on the merge-base.** Every WP's first commit is a failing test on
  `db5014ab5` (this mission's `planning_base_branch` fork point — the `spec-kitty plan --json`
  output's own `planning_base_branch` field resolves to the current branch name itself, since this
  IS the mission branch; the operative git ref for RED verification is the merge-base commit,
  `db5014ab5`, confirmed identical to `origin/main`'s tip at plan time).
- **Core tests are the highest-rigour tier** (IC-01/IC-02/IC-03) — direct function calls, crafted
  byte-level fixtures (a normal file, a truncated file, a truncate-then-regrown file with a
  crafted hash mismatch, a file with a deliberately un-terminated trailing line).
- **CLI-shell tests are glue-tier** (IC-04) — `CliRunner`, asserting flag parsing, exit codes,
  stderr JSON shape, and the boundary where the shell hands off to the core (mocked core calls are
  acceptable here for the pure-flag-validation tests; at least one test per WP must exercise the
  real core end-to-end, not an all-mocked core).
- **IC-05 is the only true integration/concurrency tier** — real writer, real reader, real git
  fixture, asserting NFR-004/SC-005's "writer sees zero change" property.
- **Guardrail**: run `pytest tests/architectural/test_no_legacy_terminology.py` before push (any
  `--feature*` slip in help text/error messages is exactly the regression class the charter warns
  about); the full `tests/architectural/`/`tests/adversarial/` suite runs in CI via
  `arch-adversarial` regardless.

## PR Shape

**5 WPs, one PR** (spec-kitty's default convention, per charter's Code Quality / "readable and
consistent PRs" section — not tk's per-WP-PR rule). Given the engineering weight established in
this plan's Summary — a genuinely new small subsystem (dual truncation detection, tear tolerance,
a bounded-generator seam, a resumable cursor with a non-trivial backward-scan verification path) —
**this plan judges the aggregate diff is NOT trivially reviewable in one sitting as a single
undifferentiated diff.** Per-WP review during implementation (the standard spec-kitty
implement-review loop) already absorbs most of this burden — each of the 5 WPs above is
independently reviewable at a normal size — but this plan explicitly **recommends** (not decides,
per the task's own instruction that this belongs to the orchestrator/operator) that the pre-merge
adversarial squad and the operator's final PR review budget real time proportional to a
small-subsystem review, not a typical single-command CLI addition, and that the WP-level reviews
not be compressed or skipped even though the final artifact is one PR.

## Complexity Tracking

*No Charter Check violations were found (see Charter Check above) — this section intentionally
has no rows.*

## Parallel Work Analysis

Single-agent sequential mission (no explicit multi-agent parallelization requested). Dependency
order is linear: IC-01 → IC-02 → IC-03 → IC-04 → IC-05, as stated in each IC's "Depends-on" line
above. IC-01 and IC-02 could in principle be split across two agents (IC-02 only needs IC-01's
`TailCursor`/`PollResult` shapes, not its implementation), but this plan does not recommend that
split given the mission's modest total WP count (5) and the value of one author's consistent
mental model across the truncation-detection logic, which is the mission's actual hard part.
