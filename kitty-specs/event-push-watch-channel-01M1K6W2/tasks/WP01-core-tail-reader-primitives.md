---
work_package_id: WP01
title: Core tail reader primitives — TailCursor, poll_once(), tear tolerance, missing-file wait
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-006
- FR-008
- NFR-003
- NFR-005
- C-002
- C-004
- C-005
- C-006
- C-007
- C-008
planning_base_branch: feat/event-push-watch-channel-3841
merge_target_branch: feat/event-push-watch-channel-3841
branch_strategy: Planning artifacts for this mission were generated on feat/event-push-watch-channel-3841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/event-push-watch-channel-3841 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-event-push-watch-channel-01M1K6W2
base_commit: c269cad808059ad513f3942fd24eec2de2ace0d6
created_at: '2026-09-03T12:04:13.660400+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
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

# WP01: Core Tail Reader Primitives

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Create `src/specify_cli/status/tail_reader.py`, the pure/finite reader core the rest of this
mission (WP02's truncation detection, WP03's bounded generator, WP04's CLI shell) builds on: the
`TailCursor` dataclass, `poll_once()` (single reopen-by-path, offset-resumable, mid-line-JSON-tear
tolerant, missing-file-tolerant), the `ResumeRefused` exception stub, and the fd-sharing invariant
that everything downstream depends on for correctness.

## Context

This WP delivers the seam the whole mission's architecture hangs off. Per plan.md's
"Architectural Seam: Core vs. Shell (FR-011 / NFR-001)" section: the **core**
(`src/specify_cli/status/tail_reader.py`) is zero-Typer/CLI-import, stdlib-only domain logic —
`TailCursor`, `poll_once()`, (later) `validate_resume_cursor()`, (later) `tail_events()`. The
**shell** (WP04's `src/specify_cli/cli/commands/events.py`) holds no loop construct of its
own — it merely iterates `tail_events()`'s poll-then-sleep loop (owned by the core, per plan.md's
corrected Architectural Seam section) in a plain `for` loop, and owns Typer flags, mission-slug
resolution, and stdout/stderr JSON rendering. This split is what makes FR-006 (mid-line tear
tolerance) and FR-005/FR-007 (dual truncation detection) unit-testable with zero wall-clock risk —
the exact defect class a sibling mission was rejected at severity 4 for (only testing the tear
shape, not the clean-truncation shape).

**Note:** the analogous docstring in the actual shipped `tail_reader.py` module is corrected by
WP03's T017 subtask.

**The chokepoint — read this before touching the file.** `src/specify_cli/status/tail_reader.py`
is **created by this WP (WP01)** and then **extended by BOTH WP02** (truncation detection +
`validate_resume_cursor()`) **and WP03** (`tail_events()`) — the same file, edited by three work
packages in total. Per `packs/built-in/missions/mission-steps/software-dev/tasks-finalize/prompt.md`'s
Ownership Overlap guidance, two *narrow* WPs claiming the same file in `owned_files`
"ALWAYS fails ownership validation... regardless of whether they sit in different lanes or are
linked in a dependency hierarchy" — dependency/lane structure never bypasses the overlap check.
**State the actual mechanism plainly, do not simplify it into "only WP01 claims the file" — that
claim is false and must not be repeated.** WP01, WP02, AND WP03 all list `tail_reader.py` in
`owned_files` in `wps.yaml` (verify this directly against `wps.yaml` before trusting this
sentence — do not take it on faith). This deliberate three-way overlap is what correctly triggers
`lanes.json`'s `write_scope_overlap` collapse rule, which merges WP01+WP02+WP03 into one sequential
lane (`lane-a`, per `lanes.json`'s `collapse_report`) — lane collapse fires ONLY on genuine
`owned_files` overlap, never on a bare `dependencies:` edge alone, so the overlap has to be real
and declared for the safe sequential lane to exist at all. `scope: codebase-wide` (set on WP02 and
WP03 in `wps.yaml`, not on WP01) is a separate, additional flag: it is what lets WP02/WP03 pass
`tasks-finalize`'s static ownership-overlap validator (the "two narrow WPs claiming the same file
ALWAYS fails" rule quoted above) *without* misrepresenting `owned_files` as disjoint — it is not a
substitute for removing the file from `owned_files`, and it is not itself what triggers lane
collapse. **Do NOT "clean up" this WP or WP02/WP03 by removing `tail_reader.py` from `owned_files`
to make the ownership map look disjoint** — doing so would silently break the `write_scope_overlap`
lane collapse above and reopen the concurrent-write hazard on this shared chokepoint file, with the
mission's own lane computation then producing wrong (parallel, unsafe) lanes instead of the
sequential one it produces today. State this plainly so it is never silently absorbed into the
dependency chain without comment: **WP01 → WP02 → WP03 MUST execute strictly sequentially** — same
file, same worktree/lane, WP01 fully landed and reviewed before WP02 starts, WP02 fully landed and
reviewed before WP03 starts. Do not let WP02 or WP03 begin against an in-flight, unreviewed WP01.

**`__all__` (charter C-007) does NOT apply here.** Per plan.md's "`__all__` (charter C-007)
Applicability" section and `.kittify/charter/charter.md`'s "`__all__` Declaration Convention"
section (binding per C-007): the requirement applies only to modules under `src/charter/` and
`src/kernel/`. `tail_reader.py` lands under `src/specify_cli/status/` — neither path. Do not add
an `__all__` declaration to this module on the assumption it's required; it is not, and adding one
speculatively is scope this WP does not need.

**Terminology canon.** This WP has no CLI surface of its own (that's WP04), so there is no
`--feature*` flag risk directly — but any internal naming, docstrings, error messages, or test
names you write must still avoid using "feature" to mean "Mission" (per the charter's Terminology
Canon, `.kittify/charter/charter.md:529-549`: canonical term is **Mission**; internal Python
parameter names may keep the existing `feature_dir`/`feature` convention already used by
`store.py`/`lifecycle_events.py` — that specific existing convention is not what's prohibited, but
never introduce new *user-facing* "feature" language).

**Commit discipline.** Every commit message follows conventional-commits (commitlint-enforced per
plan.md's Gate Set — `lint` job) and MUST end with the trailer:
```
Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

**PR-shape recommendation (plan.md's PR Shape section).** This mission ships as ONE PR
(spec-kitty's default), but the plan judges the aggregate diff NOT trivially reviewable in one
sitting given the genuine engineering weight, and recommends the pre-merge adversarial squad and
WP-level reviews budget real time proportional to a small-subsystem review — WP-level review,
including this WP's own (arguably the highest-risk of the five, since it is the chokepoint file's
creator), must NOT be compressed or skipped.

**Baseline-red methodology (NFR-005).** Before this WP's own red-first commit, run its exact
targeted test path set against the merge-base `db5014ab5` and quote the baseline red WITH that
path set — a bare count is not sufficient. Per plan.md's "Baseline & Pre-existing Red" section, run
exactly:
```bash
git stash   # or run from a clean worktree checked out at db5014ab5
.venv/bin/python -m pytest tests/status/ tests/specify_cli/status/ -m "fast and not (git_repo or integration or stress)" -q
```
`tests/status/test_tail_reader.py` does not exist on `main` at all, so the realistic finding for
this specific new file is "zero pre-existing red in this file" (there is nothing there yet to be
red). That is not a reason to skip the check: the command above still runs against the SURROUNDING
suite (`tests/status/`, `tests/specify_cli/status/`, marker `fast and not (git_repo or integration
or stress)`), and any pre-existing red found there must be recorded and never misattributed to this
WP's own diff (per the charter's baseline-red gotcha and NFR-005 — pre-existing red under tracked
issue #3284/#3283 is not this WP's to fix or hide).

## Subtask T001: Failing-first ATDD test for User Story 4 (mid-line JSON tear)

**Purpose**: Establish the RED commit for this WP before any implementation exists, per charter
C-011/C-006 ATDD-first discipline. This test pins User Story 4's exact contract: a torn trailing
line is retried, never signaled as an error or truncation, and once complete is emitted exactly
once.

**Steps**:
1. Create `tests/status/test_tail_reader.py` with `pytestmark = [pytest.mark.fast]` at module
   scope (per plan.md IC-01: "Collected by `fast-tests-status`").
2. Write `test_torn_trailing_line_retried_then_emitted_once` (or equivalently precise name): build
   a `tmp_path`-based synthetic log file (never a real `kitty-specs/` mission dir — see Risks below,
   C-007 immutable-roots hygiene) containing one complete, valid JSON line. Append a second,
   deliberately non-`\n`-terminated partial-JSON fragment simulating a writer's `write(2)` caught
   mid-flight (spec User Story 4: SK-131 measured 33,389 of 4.5M concurrent stat samples catching a
   610KB line mid-write).
3. Call `poll_once()` (imported from the not-yet-existing `specify_cli.status.tail_reader`) against
   the torn file. Assert it does not raise, emits nothing for the torn tail, and does not advance
   the cursor's offset past the last complete `\n`-terminated line.
4. Complete the torn line (append the missing bytes + `\n`) and call `poll_once()` again with the
   cursor returned from step 3. Assert the now-complete line is parsed and emitted exactly once —
   never duplicated, never dropped.
5. Commit this test **as its own commit**, before any implementation commit.

**Files**: `tests/status/test_tail_reader.py` (new).

**Validation**: Run the test and confirm it is RED. **State precisely why it is RED, and flag the
distinction explicitly**: `src/specify_cli/status/tail_reader.py` does not exist at all on current
`main` — the import `from specify_cli.status.tail_reader import poll_once` fails with
`ModuleNotFoundError`/`ImportError`. This is the legitimate trivial "import fails" ATDD case. This
is **unlike WP02 and WP03**, whose own red-first tests must fail against a state where the module
already exists (WP01 has landed by then) — their RED comes from a missing *symbol* or *behavior*
within an existing module, not a missing *module*. Do not let this WP's easy "module doesn't exist"
RED set a false expectation for how WP02/WP03's RED should read.

## Subtask T002: Core primitives — `TailCursor`, `EMPTY_DIGEST`, `ResumeRefused`

**Purpose**: Define the shared shapes every later poll/resume function in this file (this WP's
`poll_once()`, WP02's `validate_resume_cursor()`, WP03's `tail_events()`) is built on, per plan.md's
"Architectural Seam" code sketch.

**Steps**:
1. In new `src/specify_cli/status/tail_reader.py`, add module-level imports: stdlib only
   (`hashlib`, `json`, `os`, `time`, `dataclasses.dataclass`, `pathlib.Path`, plus whatever typing
   imports you need) — zero Typer/CLI imports, per the Architectural Seam's "core... zero Typer/CLI
   imports, stdlib only" commitment.
2. Define:
   ```python
   DEFAULT_POLL_INTERVAL_SECONDS: float = 0.25
   ```
   NFR-002 requires this within `[0.1s, 1.0s]`; 0.25s satisfies that bound. Add an inline code
   comment stating the chosen value and that it is within the NFR-002 bound (WP03 also names this
   requirement — this WP only needs to define the constant and its rationale comment; WP03 is the
   one that actually threads it into `tail_events()`'s default).
3. Define:
   ```python
   EMPTY_DIGEST: str = hashlib.sha256(b"").hexdigest()  # noqa: TID251 — file-integrity content
                                                          # invariant, not the charter hash (see
                                                          # plan.md Truncation Detection Design)
   ```
   `hashlib.sha256` is a repo-wide TID251-banned import (`pyproject.toml:317`, enforced across
   `src/` AND all of `tests/`, no directory-level exemption). The banned-API message names
   "file-integrity checksums" as a sanctioned non-charter use requiring only an inline
   `# noqa: TID251 — <justification>` at each call site — do NOT call
   `charter.hasher.hash_content()` instead (a different algorithm: BOM/newline-normalized charter
   markdown text, prefixed `"sha256:..."` — wrong shape for this mission's content invariant).
   `EMPTY_DIGEST` is the canonical sentinel for "offset 0, nothing consumed yet" (plan.md's
   Truncation Detection Design section) — this WP only needs the constant to exist so `TailCursor`
   has a well-defined zero value; WP02 is where it becomes load-bearing in the hash-check logic.
4. Define:
   ```python
   @dataclass(frozen=True)
   class TailCursor:
       offset: int
       content_invariant: str   # 64-char lowercase hex SHA-256, or EMPTY_DIGEST at offset 0
   ```
   Frozen because the cursor is caller-supplied/caller-owned per the spec's Tail cursor Key Entity
   — `events tail` never persists cursor state itself; each poll returns a *new* `TailCursor`
   rather than mutating one in place.
5. Define:
   ```python
   class ResumeRefused(Exception):
       reason: str   # "negative" | "out_of_range" | "misaligned" | "content_mismatch"
   ```
   This WP only needs the shape (a raiseable exception with a `.reason` attribute) to exist —
   `TailCursor`/`ResumeRefused` are consumed by WP02's `validate_resume_cursor()`, which supplies
   the actual structural/content-mismatch logic. Give `ResumeRefused.__init__` a `reason: str`
   parameter that sets `self.reason` (and forwards a human-readable message to `Exception.__init__`
   so `str(exc)` is useful in stderr rendering later).
6. Also define whatever `PollResult` shape `poll_once()` (T003–T006) returns — plan.md's code
   sketch names `poll_once(path: Path, cursor: TailCursor) -> PollResult` without fully specifying
   `PollResult`'s fields; at minimum it must carry the new cursor to resume from, the list/iterator
   of newly parsed event dicts, and a flag/reason communicating "file not yet present" (T006) versus
   "no new complete data yet" versus "events found." Keep it a small dataclass alongside
   `TailCursor` in this same file — WP02 will add truncation-signal fields to it.

**Files**: `src/specify_cli/status/tail_reader.py` (new).

**Validation**: `python -c "from specify_cli.status.tail_reader import TailCursor, EMPTY_DIGEST, ResumeRefused"` succeeds; `ruff check src/specify_cli/status/tail_reader.py` passes with zero TID251 findings (the inline noqa is present and correctly scoped to the one line).

## Subtask T003: Single-fd reopen-by-path plumbing (FR-003)

**Purpose**: Implement the reopen-by-path half of `poll_once()` — the mechanism the whole mission's
FR-003 guarantee (never trust a stale fd/inode across a writer's `os.replace()`) rests on.

**Steps**:
1. Begin `poll_once(path: Path, cursor: TailCursor) -> PollResult` by opening the file **exactly
   once per call**: `fh = path.open("rb")` (binary — the content invariant hashes raw bytes, and
   line-splitting must be byte-exact, not decoded-then-re-encoded).
2. Read the current size via `os.fstat(fh.fileno()).st_size` — **never** a second `Path.stat()` call
   and **never** a second `path.open()`/`open()` call anywhere else in the function body. This is
   the commitment plan.md's Architectural Seam section names as the "Fd-sharing invariant" and it is
   verified mechanically by T007's test in this same WP — do not treat it as a style preference.
3. Structure the rest of `poll_once()` (T004–T006) so every subsequent read inside this call goes
   through the same `fh` via `seek()`/`read()` — no `path.open()` call anywhere else inside
   `poll_once()`.
4. Close `fh` (via `with path.open("rb") as fh:` or an explicit `try/finally`) before returning.

**Files**: `src/specify_cli/status/tail_reader.py`.

**Validation**: Manual/code-review check at this point (T007 turns this into an automated test)
that grep of the function body shows exactly one `path.open(` / `open(path` call site and every
size/read operation after it goes through `fh`.

## Subtask T004: Offset-resumable reads (FR-002)

**Purpose**: Implement the core resumability contract: `poll_once()` never re-emits an
already-consumed event and never skips a boundary-adjacent one.

**Steps**:
1. `poll_once()` accepts `cursor: TailCursor` and uses `cursor.offset` as the starting read
   position: `fh.seek(cursor.offset)` before reading new bytes.
2. Only bytes from `cursor.offset` onward are read/parsed this call — bytes before `cursor.offset`
   are never touched (an already-consumed event is never re-emitted).
3. The `PollResult`/new `TailCursor` returned reflects the new offset (advanced past every
   complete, successfully-parsed line consumed this call) so the next `poll_once()` call picks up
   exactly where this one left off.
4. At `cursor.offset == 0` (nothing consumed yet), `content_invariant` should be treated as
   `EMPTY_DIGEST` — do not special-case a `None`/missing invariant separately from the sentinel;
   `EMPTY_DIGEST` IS the well-defined "nothing consumed" value (see T002).

**Files**: `src/specify_cli/status/tail_reader.py`.

**Validation**: Covered by T008's offset-resume-across-two-calls test.

## Subtask T005: Mid-line JSON tear tolerance (FR-006)

**Purpose**: Implement the exact tear-tolerance behavior T001's ATDD test pins, per plan.md's
"Mid-Line JSON Tear Tolerance" section.

**Steps**:
1. Read all new bytes from `cursor.offset` to the current size (T003/T004) in one `fh.read()` call
   through the shared fd.
2. Split on `\n`. For every chunk **except** a possible non-`\n`-terminated final remainder, require
   successful `json.loads(chunk)`. A `\n`-terminated chunk that parses successfully is added to the
   emitted events; the offset advances past it (including its trailing `\n`).
3. If the final chunk (after the last `\n` in the newly-read bytes) is **not** itself
   `\n`-terminated (i.e. it's a genuine trailing remainder with no newline yet), leave it
   **unconsumed**: do not attempt to `json.loads` it, do not advance the offset past it, and emit no
   signal for it (NFR-003's explicit FR-006 exemption — "no complete event exists yet at that poll,
   so there is nothing to silently report success about"). It will be retried from the same starting
   position on the next `poll_once()` call once more bytes (presumably including the terminating
   `\n`) have arrived.
4. If an **interior**, already-`\n`-terminated chunk fails `json.loads`, this is a **distinct fatal
   condition** — not a tear (by construction, per plan.md's reasoning: appends only ever extend the
   file at the end, so a torn write can only ever manifest as an incomplete *trailing* sequence; an
   already-`\n`-terminated interior chunk that fails to parse indicates corruption, not an in-flight
   write). This mission is not scoped to auto-recover from that — raise, mirroring
   `read_events_raw()`'s existing "raise on bad JSON" precedent at `src/specify_cli/status/store.py:554`
   (`raise StoreError(f"Invalid JSON on line {line_number}: {exc}") from exc`). Do not invent new
   silent-tolerance behavior here that NFR-003 would then have to justify.

**Files**: `src/specify_cli/status/tail_reader.py`.

**Validation**: T001's ATDD test goes GREEN; T008 adds further coverage.

## Subtask T006: Wait for not-yet-created log file (FR-008)

**Purpose**: Let `poll_once()` (or the CLI shell in WP04) tolerate a mission whose log file does not
exist yet, without treating that as an error.

**Steps**:
1. **Do NOT perform a separate existence check before the T003 open, and do NOT implement it with
   `Path.exists()`, `Path.is_file()`, or `Path.is_dir()` anywhere in `poll_once()`.** On CPython
   3.11 and 3.12 — the versions this repo requires (`pyproject.toml` `requires-python = ">=3.11"`)
   and the version CI actually runs (`.github/workflows/ci-quality.yml` pins `python-version:
   "3.12"` throughout) — `Path.exists()`/`Path.is_file()`/`Path.is_dir()` are implemented as `try:
   self.stat() ... except OSError: return False`, i.e. they call `pathlib.Path.stat()` internally.
   T007's fd-sharing test patches `pathlib.Path.stat` to raise UNCONDITIONALLY on ANY invocation
   inside `poll_once()` — so a `Path.exists()`-based check here would make every single
   `poll_once()` call, not just missing-file ones, spuriously fail T007 (and WP02's T013, which
   reuses the same pattern against a call that exercises the hash check). This is version-dependent
   in a way that hides on a newer local interpreter (Python 3.13+ changed `exists()` to route
   through `os.path.exists()` instead) while still breaking the CI-pinned 3.12 run.
2. Instead, fold the existence check into the T003 open itself: wrap the single
   `fh = path.open("rb")` call in `try`/`except FileNotFoundError`. This is still exactly ONE
   `path.open()` call site — it does not add a second one — and it closes the TOCTOU window a
   separate existence-check-then-open sequence would otherwise leave open between the check and the
   open, consistent with plan.md's Architectural Seam fd-sharing reasoning (never re-resolve the
   path more than once per call). On catching `FileNotFoundError`, return a `PollResult` (or
   equivalent) that reports "no data yet — file not present" distinctly from "file present, no new
   complete lines yet" — the caller (WP04's CLI shell) needs to be able to distinguish these two
   states so it can keep polling for the file's *appearance* without ever treating a missing file as
   a hard error.
3. Do not let `FileNotFoundError` propagate out of `poll_once()` for this case — it's an expected,
   normal state per Edge Cases ("Log file does not exist yet... must not error as if the mission
   itself is missing; it should wait/poll for the file to appear"). Catching it per step 2 and
   converting it to a `PollResult` is the whole mechanism; there is no separate exception-suppression
   step.
4. When called again with the same cursor after the file has since been created, `poll_once()`
   should behave exactly as if this had been the first-ever call against a freshly-created empty (or
   populated) file — no special "was missing" state needs to survive across calls.

**Files**: `src/specify_cli/status/tail_reader.py`.

**Validation**: T008 adds a dedicated missing-file-then-appears test. T007's fd-sharing test (this
same WP) additionally verifies, as a side effect of its unconditional `Path.stat` raise, that this
subtask's implementation does not route through `Path.exists()`/`Path.is_file()`/`Path.is_dir()` —
if it did, T007 would fail on every `poll_once()` call, not just missing-file ones.

## Subtask T007: Fd-sharing invariant test

**Purpose**: Turn the T003 commitment ("exactly one open, one fd shared by every read in the call")
into an automated, mechanically-enforced test — not just an implementation-discipline reminder a
reviewer has to re-derive. This is plan.md's Architectural Seam "Fd-sharing invariant" paragraph and
IC-01's "Also required" bullet, made concrete.

**Steps**:
1. In `tests/status/test_tail_reader.py`, write a test that gives `pathlib.Path.stat` and
   `pathlib.Path.open` **DIFFERENT tolerance semantics** — do NOT apply the same "after its initial
   open" condition to both; that shared condition is what makes the assertion miss the exact bug
   this test exists to catch (see step 3):
   - Monkeypatch `pathlib.Path.stat` to raise (e.g. `AssertionError("unexpected Path.stat() call")`)
     **UNCONDITIONALLY on ANY invocation** from within `poll_once()` — no "after the initial open"
     carve-out. The design mandates `os.fstat(fh.fileno())` exclusively for the size check (T003);
     there is zero legitimate call to `Path.stat()` anywhere inside `poll_once()`, at any point in
     the call, so any invocation at all — first or otherwise — is a defect.
   - Separately, spy on `pathlib.Path.open` (e.g. `unittest.mock.patch.object(Path, "open",
     wraps=Path.open)` or a counting wrapper) and assert it is called **exactly ONCE** per
     `poll_once()` invocation, total. This is a plain call-count assertion, not an "after the first
     call" guard.
2. **Explicitly do NOT patch `os.open` instead of `pathlib.Path.open`.** State and follow this
   warning in the test's own comment: `Path.open()` does not route through the `os` module's
   Python-level `os.open()` — verified empirically in plan.md (Python 3.14.6:
   `unittest.mock.patch("os.open", ...)` wrapped around a `Path(...).open("rb")` read shows a call
   count of **zero**). A test that only patches `os.open` silently never fires and gives false
   confidence.
3. **State precisely why the unconditional-stat-raise + open-count-of-one COMBINATION is required,
   and why a same-condition "after initial open" guard on both (or the open-count check alone) is
   NOT sufficient.** The plan's own named lazy-implementation bug is `path.stat().st_size` for the
   cheap size check, followed by a *separate* `path.open("rb")` call for the actual read. In that
   exact pattern, `Path.stat()` fires **before** the one `Path.open()` call — so an "after initial
   open" condition applied to `Path.stat` never triggers for it (it is called first, not after
   anything), and the open-call-count check also still passes unchanged (there is still only one
   `open()` call total). A test built on a shared "after initial open" condition for both patches —
   or one that treats the `Path.open`-call-count assertion alone as sufficient — silently passes
   against this exact bug. Do NOT claim the open-call-count assertion by itself "closes that gap" —
   it does not, for the exact lazy pattern named here. What actually closes it is the ASYMMETRIC
   pairing from step 1: `Path.stat` raising unconditionally on ANY call (which catches the lazy
   pattern's `Path.stat()` call, since it fires regardless of ordering), combined separately with
   the `Path.open` exactly-once-total count (which independently catches a genuinely duplicated
   `open()`).
4. This test covers the reads this WP's `poll_once()` performs: the size check (`os.fstat` via T003)
   and the drain read (T004/T005). It does **not** yet cover a hash-check read — that read doesn't
   exist until WP02 implements the hash check. Flag this explicitly: WP02 re-runs this same
   CORRECTED pattern (unconditional `Path.stat` raise + `Path.open` exactly-once count — never the
   old same-condition "after initial open" guard) against a poll that actually exercises its new
   hash-check code path, so the full three-read invariant (size, hash-check, drain) is only fully
   covered once WP02 lands; this WP's test is the size+drain half.
5. **This test's unconditional `Path.stat` raise applies to the ENTIRE `poll_once()` call, including
   T006's missing-file check** — so it also mechanically verifies that T006's implementation follows
   its own constraint (no `Path.exists()`/`Path.is_file()`/`Path.is_dir()` internally, per T006 step
   1). If T006 were implemented as `Path.exists()`-then-open instead of the required
   open()-wrapped-`try`/`except FileNotFoundError`, this test would fail on every `poll_once()`
   invocation — not only the missing-file ones — because `Path.exists()` itself calls `Path.stat()`
   on Python 3.11/3.12 (this repo's CI-pinned interpreter). Confirm this test still passes when run
   against a call where the file DOES exist (the common case) and note that its pass here is
   evidence T006 was implemented correctly, not merely evidence the test compiles.

**Files**: `tests/status/test_tail_reader.py`.

**Validation**: Sketch (mentally or in a scratch branch, not committed) the lazy
`path.stat().st_size`-then-second-`path.open("rb")` alternative and confirm this test would catch
it specifically via the unconditional `Path.stat` raise (that call happens before the one
legitimate `open()`, so it is the `Path.stat` guard — not the open-count check — that fires first
against this pattern). Confirm the test passes, unchanged, against the real T003-built
`poll_once()`. This is a design check to perform and record, not something to leave as dead code in
the PR.

## Subtask T008: Remaining IC-01 GREEN tests, RED→GREEN verification, diff coverage, terminology guard

**Purpose**: Round out this WP's test suite to IC-01's full scope, verify the red-first discipline
against the merge-base, hit the diff-coverage floor, and run the terminology guardrail.

**Steps**:
1. **Offset-resume correctness across two `poll_once()` calls**: write a log with N events, call
   `poll_once()` once with a fresh `TailCursor(offset=0, content_invariant=EMPTY_DIGEST)`, append M
   more events, call `poll_once()` again with the cursor returned from the first call, and assert
   the second call yields exactly the M new events — none of the original N re-emitted, none
   dropped.
2. **`os.replace()`-swapped-inode correctness (FR-003)**: write a file, call `poll_once()`, then
   replace the file with a *different* inode via `os.replace()` (write new content to a temp path in
   the same directory, then `os.replace(tmp_path, original_path)` — this mirrors the writer's own
   `store.py:392` locked-append idiom), call `poll_once()` again, and assert the new inode's content
   is observed correctly (not stale data from the old, now-unlinked inode). This directly exercises
   the reopen-by-path guarantee T003 built.
3. **Missing-file wait (FR-008)**: call `poll_once()` against a `tmp_path` that does not exist yet;
   assert it reports "no data yet" (per T006's `PollResult` shape) without raising. Then create the
   file with content and call `poll_once()` again with the same cursor; assert it now behaves as an
   ordinary first poll against a populated file.
4. **RED→GREEN verification against the merge-base**: confirm (and record in the WP's own
   commit/PR notes) that T001's test was RED on `db5014ab5` for the reason stated in T001's
   Validation (module does not exist), and that the full `tests/status/test_tail_reader.py` suite is
   GREEN on this WP's final commit.
5. **Diff coverage**: verify ≥90% diff-coverage on this WP's new lines in `tail_reader.py` — per
   plan.md's Gate Set, `'src/specify_cli/status/*'` is a listed critical path for the `diff-coverage`
   job (`--fail-under=90` on changed lines), and `quality-gate`'s `needs:` list includes
   `diff-coverage`, making it part of the required aggregate check, not merely advisory. Every new
   function/branch you wrote (the tear-retry branch, the interior-bad-JSON raise branch, the
   missing-file branch, the reopen-per-call path) needs a test that **directly** exercises it — not
   incidental coverage from one broad end-to-end test. If you find a branch only reachable
   incidentally, add a narrow test for it specifically.
6. **Terminology guardrail**: run `pytest tests/architectural/test_no_legacy_terminology.py` and
   confirm it passes — this catches any accidental `feature`-as-Mission slip in docstrings, error
   messages, or test names before it reaches CI (per the charter's Terminology Canon and the
   repo-wide pre-push guidance in `CLAUDE.md`/`AGENTS.md`).

**Files**: `tests/status/test_tail_reader.py`, `src/specify_cli/status/tail_reader.py` (if coverage
gaps require small fixes/additional branches to be reachable/testable).

**Validation**: `pytest tests/status/test_tail_reader.py -m fast -q` is fully GREEN; diff-coverage
tool reports ≥90% on `src/specify_cli/status/tail_reader.py`'s new lines; the terminology guard test
passes; `ruff check` and `mypy` report zero issues on both new files with zero suppressions added.

## Definition of Done

- [ ] T001's failing-first ATDD test for User Story 4 (torn trailing line retried, never signaled,
      emitted exactly once) is committed as its own commit, before any implementation commit, and
      was verified RED on the merge-base `db5014ab5` for the stated reason (module does not exist —
      the legitimate trivial "import fails" case, distinct from WP02/WP03's RED, which must fail
      against a state where the module already exists).
- [ ] `src/specify_cli/status/tail_reader.py` exists with `DEFAULT_POLL_INTERVAL_SECONDS` (0.25,
      documented in-code as within NFR-002's `[0.1s, 1.0s]` bound), `EMPTY_DIGEST` (with its own
      inline `# noqa: TID251` justification), a frozen `TailCursor` dataclass, a `ResumeRefused`
      exception stub with a `.reason` attribute, and a `PollResult` (or equivalent) shape.
- [ ] `poll_once()` opens the file exactly once per call via `path.open("rb")`, reads size via
      `os.fstat(fh.fileno())`, and every read inside the call (size, drain) shares that one fd — no
      second `Path.stat()`/`open()` call anywhere in the function body.
- [ ] `poll_once()` is offset-resumable (FR-002): reads/parses only from `cursor.offset` onward,
      never re-emits an already-consumed event.
- [ ] `poll_once()` tolerates a mid-line JSON tear (FR-006): a non-`\n`-terminated trailing
      remainder is left unconsumed, offset does not advance past it, no signal is emitted, and it is
      retried on the next call. An interior `\n`-terminated chunk that fails to parse raises (mirroring
      `store.py:554`'s precedent), distinct from the tear-retry path.
- [ ] `poll_once()` tolerates a not-yet-created file (FR-008): reports "no data yet" rather than
      raising, and behaves normally once the file appears. The check is implemented as
      `try`/`except FileNotFoundError` around the single `path.open("rb")` call (T006) — NOT via
      `Path.exists()`/`Path.is_file()`/`Path.is_dir()` (which call `Path.stat()` internally on
      Python 3.11/3.12 and would break T007's fd-sharing test).
- [ ] The fd-sharing invariant test (T007) gives `Path.stat` and `Path.open` DIFFERENT tolerance
      semantics: `Path.stat` raises UNCONDITIONALLY on any invocation (never `os.open`, which does
      not intercept `Path.open()` calls), and `Path.open` is separately spied on to assert exactly
      ONE total call — and it is confirmed to actually catch the plan's named lazy
      `Path.stat()`-then-second-`open()` implementation (a same-condition "after initial open" guard
      on both, or the open-count check alone, is confirmed insufficient and is not relied on).
- [ ] All remaining IC-01 GREEN tests (T008: offset-resume across two calls, `os.replace()`-swapped
      inode correctness, missing-file wait) pass.
- [ ] RED verified on merge-base `db5014ab5` (with the exact targeted path set from the Context
      section's Baseline & Pre-existing Red methodology, not a bare count), GREEN on this WP's final
      commit.
- [ ] ≥90% diff-coverage on this WP's new `tail_reader.py` lines (critical-path floor, per the
      `diff-coverage` job in the Gate Set).
- [ ] Every commit message is conventional-commits and ends with the
      `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailer.
- [ ] No `--feature*` terminology introduced anywhere in this WP's code, docstrings, or test names;
      `pytest tests/architectural/test_no_legacy_terminology.py` passes.
- [ ] No `__all__` declaration added to `tail_reader.py` — C-007 does not apply to this path
      (`src/specify_cli/status/`, not `src/charter/` or `src/kernel/`).
- [ ] Marker/CI discipline (C-008/SK-144 — CI selects tests by MARKER, not directory):

  | WP | Test file(s) | Marker(s) | CI job |
  |---|---|---|---|
  | WP01 | `tests/status/test_tail_reader.py` | `fast` | `fast-tests-status` |

## Risks

- **`hashlib.sha256` TID251 lint trap.** Every `hashlib.sha256(...)` call site in `tail_reader.py`
  AND in `tests/status/test_tail_reader.py` needs its own inline `# noqa: TID251 — <justification>`
  — there is no directory-level exemption for `tests/` (`pyproject.toml:280-317`). Mitigation:
  T002 places the one production call site's noqa correctly; if T008's tests construct any
  hand-verification hashes for assertions, give each its own inline noqa too. Do not add a blanket
  file-level ignore.
- **Fixture writes into real `kitty-specs/` tree.** `tests/architectural/test_archive_root_byte_identical.py`
  forbids modifying or deleting any pre-existing file under `kitty-specs/` (among other immutable
  roots), per C-007 immutable-roots hygiene (plan.md Risks table: "Fixture test writes into a
  pre-existing `kitty-specs/` mission dir, tripping `test_archive_root_byte_identical.py`").
  Mitigation: every fixture in `tests/status/test_tail_reader.py` MUST use `tmp_path` (pytest's
  built-in fixture) for its synthetic log file — never write into, or point `poll_once()` at, this
  mission's own `kitty-specs/event-push-watch-channel-01M1K6W2/` tree or any other real mission
  directory.
- **`os.open` vs `pathlib.Path.open` mock-target confusion (T007).** Patching `os.open` instead of
  `pathlib.Path.open` silently never fires (verified empirically in plan.md, Python 3.14.6: call
  count of zero). Mitigation: T007's steps state this explicitly; double-check the patch target
  before trusting the test's green result.
- **A same-condition "after initial open" guard on both `Path.stat` and `Path.open` (or the
  `Path.open`-call-count check alone) gives false confidence.** A lazy
  `path.stat().st_size`-then-second-`open()` implementation calls `Path.stat()` BEFORE the one
  `Path.open()` call, so an "after initial open" condition never fires for it, and the open-count
  stays at one either way — both weaker guards pass this exact bug unchanged. Mitigation: T007
  requires the asymmetric pairing instead — `Path.stat` raises unconditionally on ANY call, and
  `Path.open` is separately asserted to be called exactly once total.
- **`Path.exists()`/`Path.is_file()`/`Path.is_dir()` internally call `Path.stat()` on Python
  3.11/3.12 (T006).** T006's missing-file check must not use these pathlib convenience methods: on
  the CPython versions this repo requires and CI actually runs (3.11/3.12 — 3.13+ changed the
  internal implementation to route through `os.path.exists()` instead, so this is invisible on a
  newer local interpreter), they call `self.stat()` internally, which T007's unconditional
  `Path.stat` raise then catches on EVERY `poll_once()` call, not just missing-file ones — silently
  breaking T007 (and WP02's T013, which reuses the same pattern) for anyone developing locally on
  3.13+ while still failing in CI. Mitigation: T006 mandates folding the existence check into the
  `path.open("rb")` call via `try`/`except FileNotFoundError` instead (see T006 steps 1-2) — no
  separate `Path.stat()`-routing call exists at all.
- **Pre-existing red misattribution (NFR-005).** A broad local `pytest` run can show red that is not
  this WP's — pre-existing tracked issue #3284/#3283 red, or CI-environment-only failures.
  Mitigation: run the exact targeted baseline command from the Context section against the
  merge-base first and quote it with its path set before treating anything found later as this WP's
  regression; if genuinely new pre-existing red is found outside this WP's own new files, file it
  per the charter's Pre-existing Failure Reporting Rule rather than silently working around or
  hiding it.
- **WP02/WP03 starting before this WP is fully landed and reviewed.** Because `tail_reader.py` is a
  single shared file across WP01→WP02→WP03, all three of which list it in `owned_files` (the
  deliberate overlap that triggers `lanes.json`'s sequential `write_scope_overlap` lane collapse —
  see Context), an early or parallel start on WP02/WP03 against an unreviewed WP01 risks rework and
  merge conflicts within one file. Mitigation: this WP must be complete, reviewed, and landed before
  WP02's implementer opens the file.

## Reviewer Guidance

- **Verify the fd-sharing invariant test's correctness first.** Confirm `Path.stat` is patched to
  raise UNCONDITIONALLY on any call (never only "after initial open") and `Path.open` is
  SEPARATELY spied on for an exactly-one-total-call assertion — NOT `os.open` (which does not
  intercept `Path.open()` calls) and NOT a shared "after initial open" condition applied to both. A
  test using the shared-condition form would silently pass against the plan's own named lazy
  `path.stat()`-then-second-`open()` implementation, since `Path.stat()` fires before the one
  `open()` call in that pattern — confirm the test as written would actually fail against that
  specific bug, not just that it patches the right two targets.
- **Confirm T001 was genuinely committed before any implementation commit.** Check the commit
  history: the ATDD test commit's SHA must predate the first commit that adds any code to
  `tail_reader.py` beyond the test file itself. Also confirm the RED was verified against the
  merge-base `db5014ab5` and the reason recorded (module absent) matches the actual failure mode
  (an `ImportError`/`ModuleNotFoundError`, not some other unrelated collection error).
- **Confirm the WP01→WP02→WP03 sequential chokepoint on `tail_reader.py` is respected.** This WP
  must land completely, reviewed, before WP02 begins editing the same file. If WP02/WP03 work is
  already visible in the same branch/worktree ahead of this WP's approval, flag it — that violates
  the sequencing this prompt's Context section establishes.
- **Check for scope creep into WP02/WP03 territory.** This WP should NOT implement the hash check,
  `validate_resume_cursor()`, or `tail_events()` — those are WP02/WP03's explicit, separately-owned
  scope (plan.md IC-02/IC-03). If `poll_once()`'s truncation handling here does anything beyond the
  size-check-adjacent plumbing T003/T004 describe, that's WP02 scope leaking in early.
- **Confirm T006's missing-file check does not use `Path.exists()`/`Path.is_file()`/`Path.is_dir()`.**
  Grep `tail_reader.py` for these calls — none should appear. The correct implementation wraps the
  single `path.open("rb")` call (T003) in `try`/`except FileNotFoundError`. This is easy to miss
  locally on Python 3.13+ (where `Path.exists()` no longer routes through `Path.stat()`) but will
  break T007's fd-sharing test in CI, which is pinned to Python 3.12.
- **Confirm no `__all__` was added** and no `--feature*` terminology slipped into docstrings, error
  messages, or test names.
- **Confirm the TID251 noqa is present, correctly scoped (one line, not a file-level ignore), and
  carries a real justification** — not a bare `# noqa: TID251` with no comment.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent claude
```
