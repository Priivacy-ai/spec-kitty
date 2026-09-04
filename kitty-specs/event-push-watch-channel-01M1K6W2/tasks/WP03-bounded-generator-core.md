---
work_package_id: WP03
title: Bounded generator core — tail_events()
dependencies:
- WP01
- WP02
requirement_refs:
- FR-011
- NFR-001
- NFR-002
- NFR-005
- C-008
planning_base_branch: feat/event-push-watch-channel-3841
merge_target_branch: feat/event-push-watch-channel-3841
branch_strategy: Planning artifacts for this mission were generated on feat/event-push-watch-channel-3841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/event-push-watch-channel-3841 unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
scope: codebase-wide
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/status/
create_intent:
- src/specify_cli/status/tail_reader.py
- tests/status/test_tail_reader.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/tail_reader.py
- tests/status/test_tail_reader.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – Bounded generator core — tail_events()

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Implement `tail_events()`, the literal FR-011 "pure, finite generator/iterator core... terminable
via `itertools.islice`, a `max_events` cap" — a generator built on `poll_once()` (WP01/WP02) plus
an injectable `sleep_fn`, so every core-level test can bound the polling loop with zero real
wall-clock wait, and document the NFR-002 poll-interval choice in code.

## Context

- **This WP DOES list `src/specify_cli/status/tail_reader.py` and `tests/status/test_tail_reader.py`
  in its own `owned_files`** (check this file's frontmatter a few lines up — both are there) —
  do not "correct" that entry to remove them; it is correct as written. **State the real mechanism
  plainly, do not simplify it into "only the creator claims the file" — that would be false.** WP01,
  WP02, AND WP03 all list `tail_reader.py` in `owned_files` in `wps.yaml`; WP01 and WP03 additionally
  both list `tests/status/test_tail_reader.py`. Per `tasks-finalize/prompt.md`'s Ownership Overlap
  guidance, a literal claim on the same file by more than one *narrow* WP "ALWAYS fails ownership
  validation" — but this WP is exempted from that static check by `scope: codebase-wide` (set in
  this WP's own `wps.yaml` frontmatter), the doctrine's sanctioned exemption for a WP that legitimately
  overlaps another's files, used precisely so the real overlap stays declared honestly instead of
  being fabricated as disjoint. That declared overlap is not incidental — it is what correctly
  triggers `lanes.json`'s `write_scope_overlap` rule, the actual mechanism that collapses WP01,
  WP02, and WP03 into one sequential lane (`lane-a`, per `lanes.json`'s `collapse_report`); lane
  collapse fires only on genuine `owned_files` overlap, never on a bare `dependencies:` edge, so
  removing this WP's claim on either file to "clean up" the ownership map would silently break that
  collapse and reopen the concurrent-write hazard on the shared chokepoint file. **This is safe only
  because WP01 → WP02 → WP03 execute strictly sequentially in one lane/worktree.** State this
  plainly — it is a real constraint, checked explicitly by the review squad, not silently folded
  into the dependency chain (the `dependencies:` edge explains ordering; the `owned_files` overlap
  plus `scope: codebase-wide` explains why the shared-file editing is both honestly declared and
  still validator-clean). Do not begin work until WP02's final commit is present in your worktree;
  do not open a second worktree against the same files.

- **The bounded-generator seam (FR-011/NFR-001)**: `tail_events()` is a generator built on top of
  `poll_once()` (from WP01/WP02) plus an **injectable `sleep_fn: Callable[[float], None] =
  time.sleep`** parameter. Core-level tests MUST pass `sleep_fn=lambda _: None` (or a
  call-counting stub) so `max_events`/`itertools.islice` bound the generator with **zero real
  wall-clock wait** — this is the literal NFR-001 requirement ("no test needs to hang a `while
  True` loop... no test relies on a wall-clock timeout"), not just a spirit-of-the-law summary.
  **State this deterministic-termination requirement explicitly in this WP's own subtask/DoD
  text**, per the mission's own instruction that WP03 and WP04 (the two poll-loop WPs) must each
  say HOW their tests terminate without a wall-clock timeout. This WP's answer: every
  `tail_events()` test either (a) injects `sleep_fn=lambda _: None` and bounds via `max_events`, or
  (b) wraps the call in `itertools.islice(tail_events(...), N)` with a call-counting `sleep_fn`
  stub — never a bare unbounded call, never a pytest-level timeout marker used as the actual
  termination mechanism.

- **NFR-002**: the poll interval (`DEFAULT_POLL_INTERVAL_SECONDS = 0.25`, already declared in
  WP01) must sit within the documented `[100ms, 1000ms]` bound — this WP adds the doc-comment
  stating the chosen value and why.

- **ATDD precision — the part a lazy WP author gets wrong**: T016's failing-first test must fail
  against **WP03's own starting state**, i.e. WP02's final commit. At that point `tail_reader.py`
  DOES exist and DOES have `poll_once()`, the truncation checks, and `validate_resume_cursor()` —
  but `tail_events()` itself is not yet defined anywhere. Calling it raises
  `AttributeError`/`NameError` — a genuine, precise red state, not a bare "module missing" case.
  State this distinction explicitly in the T016 subtask and in your commit message: the RED you
  verify is `AttributeError: module 'specify_cli.status.tail_reader' has no attribute
  'tail_events'` (or the equivalent `NameError`/`ImportError` from a `from ... import tail_events`
  form), never a collection error from a missing module or a missing test file.

- **`__all__` (C-007) does NOT apply** — `tail_reader.py` is under `src/specify_cli/status/`, not
  `src/charter/`/`src/kernel/`.

- **Terminology canon**: no `--feature*` aliases anywhere — this WP is core-only (no CLI surface),
  but any help text, docstring, or error message you touch must still honor `--mission`
  terminology if it references the eventual CLI flag.

- **Commit discipline**: conventional-commits, every message ends with
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

- **PR-shape recommendation (plan.md's PR Shape section)**: this mission ships as ONE PR
  (spec-kitty's default), but the plan judges the aggregate diff NOT trivially reviewable in one
  sitting given the genuine engineering weight, and recommends the pre-merge adversarial squad and
  WP-level reviews budget real time proportional to a small-subsystem review — WP-level review,
  including this WP's own, must NOT be compressed or skipped.

- **Baseline-red methodology (NFR-005)**: before T016's red-first commit, run the exact targeted
  test path set from plan.md's "Baseline & Pre-existing Red" section against merge-base
  `db5014ab5`, quoting the baseline red WITH that path set:

  ```bash
  git stash   # or run from a clean worktree checked out at db5014ab5
  .venv/bin/python -m pytest tests/status/ tests/specify_cli/status/ -m "fast and not (git_repo or integration or stress)" -q
  .venv/bin/python -m pytest tests/cli/ tests/specify_cli/cli/ -m "fast" -q
  ```

  Since `tail_reader.py`/`test_tail_reader.py` are new files (added by WP01), the realistic
  baseline-red finding is "zero pre-existing red in this WP's own new test file" — the check
  matters for the SURROUNDING suite in the same path set, so you do not misattribute unrelated
  pre-existing red (tracked under #3284/#3283) as your own regression. If you find pre-existing red
  not already covered by #3284/#3283, open a GitHub issue reporting it before proceeding past it.

## Subtask T016: Failing-first ATDD test for `tail_events()` bounded termination

Write a new top-level pytest test function in `tests/status/test_tail_reader.py` (append to the
file WP01 created and WP02 extended — do not create a new file) that asserts: calling
`tail_events()` with an injected no-op `sleep_fn` and `max_events=N` (pick a small N, e.g. 3, over
a hand-crafted log file containing at least N complete `StatusEvent`-shaped JSON lines) terminates
and yields exactly N envelopes.

Assert termination is real (zero real sleep), not merely "it returned a list of length N": capture
`time.monotonic()` immediately before and immediately after fully consuming the generator (e.g.
`list(tail_events(...))`), and assert the delta is near-zero — sub-millisecond, e.g. `delta <
0.05` seconds as a generous CI-safe bound, definitely far below what even one real
`DEFAULT_POLL_INTERVAL_SECONDS` (0.25s) sleep would cost. This monotonic-clock bound is what
distinguishes this test from a weaker one that only checks the returned list length; a
`sleep_fn` that silently no-ops incorrectly (e.g. still calls the real `time.sleep` internally
before invoking the injected callable) would still return N items but would NOT pass this
timing assertion.

This is the failing-first commit, before `tail_events()` exists anywhere in `tail_reader.py`. Per
the ATDD precision note in Context above: at WP02's final commit, `poll_once()` and
`validate_resume_cursor()` already exist, so this is a precise `AttributeError`/`NameError` on the
undefined `tail_events` symbol — NOT a module-collection failure, NOT an import error on the whole
`tail_reader` module. Verify and record this exact RED (the error type and message) before writing
any implementation. Own commit: `test(status): add failing tail_events() bounded-termination test`
(or equivalent conventional-commits scope), ending with the required trailer.

## Subtask T017: Implement `tail_events()`

Implement in `src/specify_cli/status/tail_reader.py`:

```python
def tail_events(
    path: Path,
    cursor: TailCursor,
    *,
    max_events: int | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Iterator[dict[str, Any]]: ...
```

Behavior: a generator built on `poll_once()`. Maintain the advancing `TailCursor` internally,
starting from the cursor passed in. Loop: call `poll_once(path, cursor)`; for every envelope the
poll returns (both ordinary pass-through events AND `log_truncated` signal envelopes — see the
Architectural Seam / Truncation Detection Design sections of `plan.md`, which this WP does not
re-derive), `yield` it as it arrives and advance the cursor to the poll result's new position.
When a poll returns nothing new (no envelopes to yield), call `sleep_fn(poll_interval)` once
before the next poll — never sleep when a poll DID produce output, so a backlog drains at full
speed with no artificial delay between items. `max_events` is honored by the caller composing
`itertools.islice(tail_events(...), max_events)` (see T019) or, if you choose to support it as a
first-class generator parameter for convenience, by internally counting yields and returning once
`max_events` is reached — pick one approach and be consistent with what T019's tests exercise; do
not silently support both with divergent behavior.

Never let `tail_events()` sleep on the FIRST poll unconditionally — only after a poll that
produced nothing new. Never catch or suppress exceptions raised by `poll_once()`; let them
propagate (this WP does not change error-handling semantics established by WP01/WP02).

**Also update the module docstring in the same file.** WP01's shipped module docstring at the top
of `src/specify_cli/status/tail_reader.py` (lines 5-8 as of WP01) currently reads: "The **shell**
(WP04's ``src/specify_cli/cli/commands/events.py``) is the thin, infinite ``while True`` +
``time.sleep`` polling wrapper..." — that sentence becomes false the moment this subtask lands
`tail_events()` (with its injectable `sleep_fn` defaulting to `time.sleep`) beside it in the same
module: the poll-then-sleep loop is `tail_events()`, here in the core, not something the shell
owns. As part of this same commit (or a follow-up commit in this WP, before T017's work is
considered done), correct that docstring sentence to state that the **core** (`tail_events()` in
this module) owns the actual poll loop and its injectable `sleep_fn`-driven sleep, and that the
shell (`events.py`) merely iterates `tail_events()` in a plain `for` loop with no explicit
`while True` and no direct `time.sleep` call of its own — matching plan.md's corrected
"Architectural Seam: Core vs. Shell (FR-011 / NFR-001)" section. Do not leave the stale
shell-owns-the-loop claim standing once this subtask's code makes it self-contradictory.

Own commit implementing this, turning T016's RED to GREEN. Conventional-commits, trailer required.

## Subtask T018: `DEFAULT_POLL_INTERVAL_SECONDS` doc comment (NFR-002)

Add or confirm the module-level doc comment on `DEFAULT_POLL_INTERVAL_SECONDS = 0.25` (declared by
WP01) explicitly states the chosen value and why it sits within NFR-002's `[100ms, 1000ms]` bound
— e.g.:

```python
# NFR-002: poll interval MUST be a fixed, documented value in [0.1s, 1.0s]. 0.25s is chosen as a
# midpoint: fast enough that "within one poll interval" (FR-005/US1 AC2) is a sub-second,
# practically-instant bound for a human-observed consumer, while not so fast that idle polling of
# a live log imposes meaningless CPU/IO load on a single long-running tailer (NFR-004).
DEFAULT_POLL_INTERVAL_SECONDS: float = 0.25
```

If WP01 already added a doc comment here, verify it explicitly names the chosen value (0.25) and
the `[100ms, 1000ms]` bound by number — do not leave it as a bare inline comment that only repeats
the constant without the rationale. Amend it in place if it is missing either the number or the
rationale; do not duplicate a second comment block.

This may land in the same commit as T017 if the doc comment did not previously exist, or as a
small standalone commit if you are only amending WP01's existing comment. Either way, keep the
commit message accurate to what actually changed.

## Subtask T019: Deterministic-termination tests (zero real wall-clock wait)

Write tests proving deterministic termination with zero real wall-clock wait — this is the
explicit "HOW do this WP's tests terminate without a wall-clock timeout" statement the mission
requires WP03 to make in its own text (see Context above), realized as test code:

**(a) `sleep_fn` override + `max_events` bound.** Pass `sleep_fn=lambda _: None`, bound the
generator via `max_events=N` (either as a first-class kwarg per T017's choice, or via
`itertools.islice`), assert exactly N envelopes are yielded and the elapsed wall-clock time
(via `time.monotonic()` before/after, same technique as T016) is near-zero. This may extend
T016's own test or be a sibling test — do not duplicate T016 verbatim; if you extend it, make sure
the extension still names its own distinct assertion.

**(b) `itertools.islice` bound + call-counting `sleep_fn` stub — MANDATORY shape: a required,
single concrete end-to-end test of User Story 1 Acceptance Scenario 2 (a writer appending while
`events tail` is actively running, the appended event surfaced within one poll interval).** This is
the mission's P1 acceptance scenario ("the entire scope of the mission" per spec.md) and MUST be
exercised end-to-end through `tail_events()` by a required test — not offered as one optional
fixture shape among several, and never satisfiable by a degenerate zero-new-poll fixture (a
pre-written, already-complete log where every poll immediately produces output proves nothing about
mid-run appends and is NOT an acceptable substitute for the shape below).

Required test shape:
1. Write a `tmp_path`-based log with **fewer than N** events (e.g. `N-1`, or fewer) up front.
2. Bound the generator via `itertools.islice(tail_events(path, cursor, sleep_fn=counting_stub), N)`
   where `counting_stub` is a small stub (a closure or `unittest.mock.Mock` side effect) that, on
   being called (i.e. on the "nothing new yet" poll where the remaining event(s) are not yet
   present), **appends the remaining event(s) to the log file from within the stub itself** before
   returning — this is the synchronization point: the injected `sleep_fn` call stands in for "the
   writer appends between polls," with **zero real wall-clock sleeping anywhere in the test** (do
   NOT call `time.sleep`, `threading.Event.wait` with a real timeout, or any other real-time wait
   to achieve this synchronization — the stub callback itself is the only synchronization
   mechanism).
3. Fully consume the bounded `itertools.islice` (e.g. `list(...)`) and assert every one of the N
   events — the ones present up front AND the one(s) appended mid-consumption via the stub — is
   yielded exactly once, in file order, with none duplicated and none dropped.
4. Separately assert the stub's call count matches the expected number of "nothing new" polls
   exactly (at least one — the one that triggered the append) — this is what proves the generator is
   calling `sleep_fn` (not `time.sleep`) on the no-new-data path, not merely that the test finished
   quickly.

This is the required, single concrete test satisfying User Story 1 AC2 end-to-end at the core
(generator) layer — do not leave it optional, and do not accept a sibling test that only pre-writes
all N events as a replacement for it.

Never rely on a wall-clock timeout (a pytest-timeout marker, a `signal.alarm`, or similar) to kill
a runaway test anywhere in this WP — every test's own bound (`max_events`/`itertools.islice`) is
what guarantees termination, by construction, independent of any timeout infrastructure.

Add `pytestmark = [pytest.mark.fast]` at module level if not already present from WP01/WP02 (do
not duplicate the marker declaration if it already exists). Own commit(s), conventional-commits,
trailer required.

## Subtask T020: RED→GREEN verification, diff-coverage, terminology guard

Verify RED→GREEN against the merge-base for T016 specifically: re-run T016's test in isolation
against a checkout at merge-base `db5014ab5` (or `git stash`/worktree at that ref) and confirm the
precise `AttributeError`/`NameError` from the Context section fires — not a broader collection
failure — then confirm the same test passes GREEN on this WP's final commit.

Verify ≥90% diff-coverage on `tail_events()`'s new lines specifically (the `diff-coverage` CI job's
critical-path allowlist covers `src/specify_cli/status/*`, per `plan.md`'s Gate Set — load-bearing,
not advisory, on this file). Run the project's standard coverage invocation scoped to
`tests/status/test_tail_reader.py` and confirm the new/changed lines in `tail_reader.py` you
authored this WP clear the 90% floor; if any branch is uncovered (e.g. the `max_events`-reached
exit path, or the "poll produced output, do not sleep" branch), add a targeted test rather than
accepting the gap.

Run `pytest tests/architectural/test_no_legacy_terminology.py` and confirm it passes — this WP
touches no CLI-facing text, but the guard is cheap (≈0.1s) and mandatory per the charter's
pre-push guidance; do not skip it on the assumption this WP is "core only."

Also re-run the full baseline-red command set from the Context section's "Baseline-red
methodology" against your final commit (not just merge-base) and confirm no NEW red beyond
#3284/#3283 was introduced by this WP's changes, scoped to the exact path sets given there.

## Definition of Done

| WP | Test file(s) | Marker(s) | CI job |
|---|---|---|---|
| WP03 | `tests/status/test_tail_reader.py` | `fast` | `fast-tests-status` |

- T016's RED is verified against WP02's final commit specifically — a precise
  `AttributeError`/`NameError` on the undefined `tail_events` symbol, not an import/collection
  failure, and not a RED verified against some other ref.
- GREEN is verified on this WP's final commit for T016's test and all of T019's tests.
- ≥90% diff-coverage on `tail_events()`'s new/changed lines (critical-path allowlist
  `src/specify_cli/status/*`), confirmed, not assumed.
- Every `tail_events()` test in this WP uses an injected `sleep_fn` (never the real `time.sleep`)
  combined with a `max_events` bound and/or an `itertools.islice` bound — never a wall-clock
  timeout as the actual termination mechanism for any test.
- Every commit in this WP is conventional-commits-formatted and ends with the required
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailer.
- `pytest tests/architectural/test_no_legacy_terminology.py` passes.
- The WP01→WP02→WP03 sequential chokepoint is respected: this WP is the LAST of the three to touch
  the shared `tail_reader.py`/`test_tail_reader.py` files in this mission's plan — do not leave
  either file in a state that assumes a further sequential extension is still pending unless a
  later WP (per `wps.yaml`) is explicitly documented as also touching them.
- `tail_reader.py`'s module docstring no longer claims the shell owns the `while True`/`time.sleep`
  polling loop; it correctly states that `tail_events()` (core) owns the actual poll-then-sleep
  loop via its injectable `sleep_fn`, and that `events.py` (shell) merely iterates `tail_events()`
  in a plain `for` loop — per this WP's T017 subtask instruction.

## Risks

- **Core `tail_events()` test accidentally sleeps for real, making CI flaky/slow.** Mitigation:
  the injectable `sleep_fn`, always overridden to a no-op/stub in every core-level test this WP
  adds — never let a test fall back to the real `time.sleep` default. Verify by inspection: grep
  your own new test functions for `tail_events(` calls and confirm every call site passes
  `sleep_fn=`.
- **Fixture writes into a pre-existing `kitty-specs/` mission dir**, tripping
  `test_archive_root_byte_identical.py` (C-007). Mitigation: every fixture log file this WP's tests
  create MUST use `tmp_path` (pytest's built-in fixture) — never write into this mission's own
  `kitty-specs/event-push-watch-channel-01M1K6W2/` tree or any other pre-existing mission
  directory.

## Reviewer Guidance

- Verify no test in this WP ever calls `tail_events()` without BOTH a `sleep_fn` override AND a
  `max_events`/`itertools.islice` bound. A call site missing either is a defect: missing
  `sleep_fn` risks a real sleep in CI; missing the bound risks an unbounded generator being fully
  consumed (e.g. via a bare `list(...)`) with no cap.
- Verify the monotonic-clock assertion in T016/T019(a) is real — it must compare a
  `time.monotonic()` delta against a concrete sub-second (ideally sub-100ms) bound, not just assert
  "the call returned" or "no exception was raised." A test that merely checks the generator
  terminated does not, by itself, prove zero real sleep occurred — only the timing delta does.
- Verify T019(b)'s call-counting stub assertion checks an exact expected count, not merely `> 0` or
  `>= 0` — a loose assertion here would pass even if the generator called `sleep_fn` on every
  single poll (including ones that produced output), silently defeating the "only sleep when a
  poll produced nothing new" behavior T017 specifies.
- **Verify T019(b) is present in the MANDATORY shape, not a degenerate substitute.** Confirm the
  fixture starts with fewer than N events on disk, the remaining event(s) are appended from inside
  the `sleep_fn` stub itself (not before the generator starts), zero real wall-clock sleep occurs
  anywhere in the test, and the assertion covers every one of the N events including the
  mid-consumption append. Reject a test that only pre-writes all N events up front and calls that
  User Story 1 AC2 coverage — that shape never exercises a writer appending while `tail_events()`
  is actively running and is explicitly disallowed as a substitute.
- Confirm the `DEFAULT_POLL_INTERVAL_SECONDS` doc comment (T018) names both the chosen value
  (0.25s) and the `[100ms, 1000ms]` NFR-002 bound explicitly, in text — not just as a bare number
  with no rationale.
- Confirm no new file was created for these tests — WP01 created `tests/status/test_tail_reader.py`
  and this WP must extend it, per the Ownership Overlap constraint in Context.
- **Diff `tail_reader.py`'s module docstring specifically.** Confirm WP01's original "the shell...
  is the thin, infinite `while True` + `time.sleep` polling wrapper" sentence (or an equivalent
  restatement anywhere in the file) is gone, and that the docstring now correctly attributes the
  poll-then-sleep loop and its `sleep_fn` to `tail_events()` in the core, with the shell described
  as a plain `for`-loop consumer. Reject the WP if the stale sentence, or any equivalent
  restatement, is still present anywhere in the file.

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent claude
```
