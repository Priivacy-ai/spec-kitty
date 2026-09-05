---
work_package_id: WP02
title: Truncation detection — size check, hash check, FR-013 resume validation
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-007
- FR-013
- NFR-003
- NFR-005
- C-008
planning_base_branch: feat/event-push-watch-channel-3841
merge_target_branch: feat/event-push-watch-channel-3841
branch_strategy: Planning artifacts for this mission were generated on feat/event-push-watch-channel-3841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/event-push-watch-channel-3841 unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
- T015
scope: codebase-wide
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/status/
create_intent:
- src/specify_cli/status/tail_reader.py
- tests/status/test_tail_reader_truncation.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/tail_reader.py
- tests/status/test_tail_reader_truncation.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Truncation detection — size check, hash check, FR-013 resume validation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Add dual truncation detection (a cheap size check plus an independent, every-poll content-invariant
hash check) to `poll_once()`, and add the cold-resume validator `validate_resume_cursor()`, so
`events tail` never silently continues after a rollback shrinks or rollback-then-regrows
`status.events.jsonl`, and never resumes from a stale or content-mismatched offset. This closes
FR-005, FR-007, and FR-013.

## Context

**This WP edits `src/specify_cli/status/tail_reader.py`** — adding the size check, the hash check,
and `validate_resume_cursor()` to it. **This WP DOES list `tail_reader.py` in its own
`owned_files` above** (check the frontmatter a few lines up — it is there, alongside
`tests/status/test_tail_reader_truncation.py`) — do not "correct" that entry to remove it; it is
correct as written. State the real mechanism explicitly, do not simplify it into "only the creator
claims the file" (that would be false): WP01, WP02, AND WP03 all list `tail_reader.py` in
`owned_files` in `wps.yaml`. Per `tasks-finalize/prompt.md`'s Ownership Overlap guidance, two
*narrow* WPs literally claiming the same file "ALWAYS fails ownership validation... regardless of
dependency structure" — but this WP is not narrow in the sense that rule targets: `wps.yaml` also
sets `scope: codebase-wide` on this WP's frontmatter, which is `tasks-finalize`'s own sanctioned
exemption from that static overlap check, used precisely so the real overlap can stay declared
(not fabricated as disjoint) while still passing validation. The overlap itself is not incidental —
it is what correctly triggers `lanes.json`'s `write_scope_overlap` rule, which is the actual
mechanism that collapses WP01, WP02, and WP03 into one sequential lane (`lane-a`, per `lanes.json`'s
`collapse_report`); lane collapse fires only on genuine `owned_files` overlap, never on a bare
`dependencies:` edge, so removing this WP's claim on `tail_reader.py` to "clean up" the ownership
map would silently break that collapse and reopen the concurrent-write hazard on this chokepoint
file. **This is safe only because WP01 → WP02 → WP03 execute strictly sequentially in one
lane/worktree** — same file, same chokepoint, one writer at a time. This is a real constraint the
review squad checks for; do not fold it into the dependency graph silently as if
`dependencies: ["WP01"]` alone explained it — the dependency edge explains ordering, the
`owned_files` overlap plus `scope: codebase-wide` is what explains why the shared-file editing is
both declared honestly and still validator-clean.

**The Truncation Detection Design** (plan.md, section of the same name): the size check
(`current_size < O`) and the hash check (independent, run on **every** poll, even when
`current_size >= O`) both run before any line-parsing. Neither is satisfied by the other passing —
the size check alone misses a truncate-then-regrow that completes within one poll interval; the
hash check runs unconditionally regardless. The content invariant is the SHA-256 hex digest of
`[start_of_last_line, O)` — the last-consumed line's bytes, including its trailing `\n` — which is
always re-derivable on a cold resume via a backward scan from `O - 1` for the previous `\n` (or
BOF), because `O` is always guaranteed by construction to be a line boundary. `EMPTY_DIGEST`
(SHA-256 of `b""`, already defined in WP01's `tail_reader.py`) is the sentinel used when `O == 0`.

**Why `validate_resume_cursor()` is a separate function from `poll_once()`'s live resync path, not
a parameter on it**: a live, already-running poll has the last-consumed line's length sitting in
memory from the previous poll's own read — no backward scan needed, it re-reads exactly the range
it already knows. A cold resume (`validate_resume_cursor()`) has no such memory: the consumer only
ever hands it an offset and (optionally) a digest, so it MUST backward-scan the file itself to find
`start_of_last_line` before it can even compute a digest to compare. This is a genuine algorithmic
difference, not just a different outcome on mismatch (resync-from-0 vs. refuse) — that is why it is
its own function.

**FR-007**: the size check and the hash check both run BEFORE any line-parsing for this poll's new
bytes. A clean-truncation-then-regrowth whose surviving bytes happen to still parse as valid JSON
is caught by the hash check regardless of whether parsing would have "succeeded" — parsing is never
consulted to decide truncation. This is the direct fix for a sibling mission's severity-4-rejected
defect: a reader that only asks "does it parse" never sees this failure shape at all, because the
shrunk-but-still-valid-JSON file parses cleanly and confidently reports an incomplete result as
success.

**TID251**: `hashlib.sha256` is a repo-wide TID251-banned import (`pyproject.toml:317`), enforced
across `src/` AND the entire `tests/` tree — there is no blanket file exemption and no directory
exemption for `tests/`. Every `hashlib.sha256(...)` call site this WP adds — in `tail_reader.py`
AND in `tests/status/test_tail_reader_truncation.py` — needs its own inline
`# noqa: TID251 — file-integrity content invariant, not the charter hash` comment. This is a real,
easy-to-miss lint failure that only surfaces at CI if skipped; do not skip it, and do not reach for
`charter.hasher.hash_content()` instead (a different algorithm — BOM/newline-normalized charter
markdown text, prefixed `"sha256:..."` — not this mission's content invariant).

**`__all__` (charter C-007) does NOT apply** to this WP's code — `tail_reader.py` lives under
`src/specify_cli/status/`, not `src/charter/` or `src/kernel/`, the only two roots C-007 binds.

**Terminology canon**: no `--feature*` aliases anywhere in help text, error messages, or any
user-facing surface this WP's code touches. (WP02 adds no new CLI surface itself, but any test
fixture or error string it writes must still honor this.)

**Commit discipline**: conventional-commits message format; every commit message ends with
`Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

**PR-shape recommendation (plan.md's PR Shape section)**: this mission ships as ONE PR
(spec-kitty's default), but the plan judges the aggregate diff NOT trivially reviewable in one
sitting given the genuine engineering weight, and recommends the pre-merge adversarial squad and
WP-level reviews budget real time proportional to a small-subsystem review — WP-level review,
including this WP's own, must NOT be compressed or skipped.

**ATDD precision — this is the part a lazy WP author gets wrong**: T009 and T010's failing-first
tests must fail against **WP02's own starting state**, i.e. WP01's final commit — NOT because
`tail_reader.py` doesn't exist (it does; WP01 created it and it is fully green on its own scope),
but because WP01's `poll_once()` has **zero truncation detection**: no size check, no hash check,
no `validate_resume_cursor()` at all. State this explicitly in your own commit messages and test
docstrings so a reviewer does not have to reconstruct it from the diff. If your red-first run shows
a collection error ("no such attribute `validate_resume_cursor`") that is the correct, expected red
for T012's test — a `poll_once()`-only test (T009/T010) must fail on an assertion about missing
`log_truncated` behavior, not on a collection error, since `poll_once()` already exists.

**Baseline-red methodology (NFR-005)**: before committing T009/T010's red-first commits, run the
exact targeted test path set from plan.md's "Baseline & Pre-existing Red" section against
merge-base `db5014ab5` and quote the baseline red WITH that path set — not a bare count:

```bash
git stash   # or run from a clean worktree checked out at db5014ab5
.venv/bin/python -m pytest tests/status/ tests/specify_cli/status/ -m "fast and not (git_repo or integration or stress)" -q
.venv/bin/python -m pytest tests/cli/ tests/specify_cli/cli/ -m "fast" -q
```

`test_tail_reader_truncation.py` is a NEW file (does not exist on `main`), so the realistic
baseline-red finding is "zero pre-existing red in this exact new file" — the check instead matters
for the SURROUNDING suite in the same path set: if `fast-tests-status` already carries pre-existing
red unrelated to this mission, do not misattribute it as a WP02 regression, and if you find red not
already covered by tracked issue #3284, open a GitHub issue reporting it (charter's Pre-existing
Failure Reporting Rule) before proceeding past it.

## Subtask T009: Failing-first ATDD test — clean-boundary truncation detected via size check even when parseable

Write `test_clean_boundary_truncation_detected_via_size_check_even_when_parseable` as a top-level
pytest function in the NEW file `tests/status/test_tail_reader_truncation.py`. This is Edge Cases
shape-(b) / User Story 2 Acceptance Scenario 1, and it reproduces — as its own, separately-named
test — the exact scenario a sibling mission's `design-status` verb was rejected at severity 4 for
today: a reader that only tests the mid-line tear shape and never plain clean-boundary truncation.

Steps the test body must perform, in order:

1. **Create `tests/status/test_tail_reader_truncation.py` with `pytestmark = [pytest.mark.fast]`
   at module scope** (per plan.md IC-02 / the Marker Discipline recap table: WP02 row, marker
   `fast`, job `fast-tests-status`) — before any test function is written. This is required so the
   new file is actually collected by CI's `fast-tests-status` job; do not skip it or assume it is
   implied.
2. Write a valid JSONL log to a `tmp_path`-based file (never a real `kitty-specs/` path — see
   Risks) containing several complete `StatusEvent`-shaped JSON lines.
3. Consume it once (a `poll_once()` call, or hand-construct the resulting `TailCursor` — either is
   fine) to establish offset `O` at a known line boundary.
4. Truncate the file at that line boundary with **no regrow** — the file just shrinks and stays
   shrunk.
5. **Self-check the fixture itself first**: assert the remaining bytes DO parse as valid JSON (each
   remaining line round-trips through `json.loads` without error). This assertion must fail the
   test if the fixture accidentally constructs a mid-line tear instead of a clean truncation — it
   is there to prove the test is exercising shape-(b), not accidentally shape-(a).
6. Call `poll_once()` against the truncated file with the cursor from step 3, and assert
   `log_truncated` fires — specifically via the size check (`current_size < O`), independent of
   whether parsing of the remainder would have succeeded (it does, per step 5's own assertion; the
   test's whole point is that this must not matter).
7. **Recovery half of the resync (User Story 2 AC2)**: immediately after step 6's `log_truncated`
   assertion, call `poll_once()` again with the cursor `poll_once()` returned in step 6 (the
   post-signal, resynced-to-offset-0 cursor), against the file's current (post-truncation, still
   shrunk) content. Assert the events yielded exactly match what is actually present in the file
   from offset 0 onward — no more, no fewer — and that none of the pre-truncation events that no
   longer exist in the file are fabricated or replayed. This is the recovery half of AC2, not just
   the detection signal; do not stop at asserting `log_truncated` fired.

This is its own commit, made BEFORE the size check exists in `tail_reader.py` — it must fail (red)
against WP01's final commit for the reason given in the Context section above (no truncation
detection exists yet, not a missing-module error). Commit message ends with the required
`Co-Authored-By` trailer.

## Subtask T010: Failing-first ATDD test — hash check catches truncate-then-regrow within one poll

Write a second, separately-named top-level pytest function for the truncate-then-regrow race
(User Story 2 Acceptance Scenario 3) in the same new file. Do not parametrize this alongside T009's
test and do not share a function body — see plan.md's IC-02 ATDD requirement for three independent
top-level test functions, and the Reviewer Guidance section below.

Steps:

1. Write a valid JSONL log, consume it to establish offset `O` (same pattern as T009).
2. Simulate a rollback truncation followed by a regrowth that both complete within a single poll
   interval — i.e., before the reader's next `poll_once()` call samples the file: truncate below
   `O`, then write new (different) content back so the file's current size is at or above `O`
   again, such that the size check alone (`current_size < O`) would never observe a shrink.
3. **The test MUST assert its own precondition immediately before the `poll_once()`/`tail_events()`
   call under test** — e.g. `assert Path(log).stat().st_size >= O` — so that "this cannot pass by
   accident via the size check alone" is self-evident from reading the test body itself, not
   something a reviewer has to reconstruct from plan.md's prose.
4. Call `poll_once()` (or `tail_events()`, bounded) with the cursor from step 1 against the
   regrown file, and assert `log_truncated` fires via the hash check — the content-invariant
   mismatch — even though the size check alone would have reported "grew, looks fine."
5. **Recovery half of the resync (User Story 2 AC2)**: immediately after step 4's `log_truncated`
   assertion, call `poll_once()` again with the post-signal cursor (`log_truncated`'s
   resynced-to-offset-0 cursor) against the file's current (regrown) content. Assert the events
   yielded exactly match the regrown file's actual content from offset 0 onward — no more, no
   fewer — and that none of the pre-truncation events (now gone, replaced by the regrown content)
   are fabricated or replayed. This is the recovery half of AC2, not just the detection signal; do
   not stop at asserting `log_truncated` fired.

This is its own commit, made BEFORE the hash check exists in `tail_reader.py` — red on WP01's final
commit (and still red immediately after T009's implementation lands, since T009 only implements the
size check). `Co-Authored-By` trailer required.

## Subtask T011: Implement the size check and the hash check in `poll_once()`

Edit `src/specify_cli/status/tail_reader.py` (a file this WP DOES list in its own `owned_files`,
alongside WP01 and WP03 — see Context for the real ownership-overlap mechanism) to add both checks
to `poll_once()`, per FR-005/FR-007:

- **Size check**: `current_size < cursor.offset` → truncation.
- **Hash check**: independent of the size check, run on EVERY poll (even when
  `current_size >= cursor.offset`) — re-verify that the content invariant at the cursor's offset
  still matches. Both checks run BEFORE any line-parsing of new bytes this poll.
- Either mismatch emits the `log_truncated` signal envelope on the stream and resyncs from offset
  0. Cite plan.md's "Tail Envelope & Cursor Schema" section for the exact shape:

  ```json
  {"type": "log_truncated", "reason": "size_shrink" | "content_mismatch",
   "detected_at_offset": <O>, "tail_offset": 0, "tail_invariant": "<EMPTY_DIGEST>"}
  ```

  `"reason"` is `"size_shrink"` when the size check fired, `"content_mismatch"` when only the hash
  check fired (size check passed but the hash mismatched).
- Respect the fd-sharing invariant already established by WP01 (plan.md's Architectural Seam
  section, "Fd-sharing invariant" paragraph): the size check reads `os.fstat(fd)` on the ONE fd
  `poll_once()` opens per call, and the hash-check read (and the new-bytes drain read) go through
  that same fd via `seek()`+`read()` — never a fresh `Path.stat()` or a second `open()`/`Path.open()`
  call anywhere inside this function.
- Inline `# noqa: TID251 — file-integrity content invariant, not the charter hash` on every
  `hashlib.sha256` call site this subtask adds.

This is T009 and T010's GREEN-making commit for the size check and hash check respectively (T009
should go green once the size check lands; T010 should go green once the hash check lands — you may
land both in one commit if that is the natural shape, but both tests must be green after this
subtask). Commit message ends with the required `Co-Authored-By` trailer.

## Subtask T012: Implement `validate_resume_cursor()`

Add `validate_resume_cursor(path: Path, offset: int, invariant: str | None) -> TailCursor` to
`tail_reader.py`, implementing FR-013's structural-then-content refusal sequence:

1. **Structural checks first**, each raising `ResumeRefused` with the matching `reason` on failure:
   - `offset < 0` → `ResumeRefused(reason="negative")`.
   - `offset > current_file_size` → `ResumeRefused(reason="out_of_range")`.
   - `offset` not on a line boundary — i.e. `offset != 0` and the byte immediately before `offset`
     is not `\n` → `ResumeRefused(reason="misaligned")`.
2. **If structurally valid AND `invariant` was supplied** (not `None`): backward-scan from
   `offset - 1` for the previous `\n` (or BOF) to find `start_of_last_line`; hash
   `[start_of_last_line, offset)` (with the required TID251 noqa); compare to the supplied
   `invariant`; on mismatch raise `ResumeRefused(reason="content_mismatch")`.
3. **If only `offset` was supplied** (`invariant is None`): only the structural checks apply — this
   is FR-013's explicit "opt-in" clause for cross-restart content verification. Return a
   `TailCursor` built from the structural result alone (compute/store its own content invariant at
   `offset` for future live-polling use, but do not compare it against anything).
4. On success, return the resulting `TailCursor(offset=offset, content_invariant=<derived digest>)`.

Respect the same fd-sharing commitment plan.md requires for this function (Architectural Seam,
"Same commitment for `validate_resume_cursor()`" paragraph): open exactly one fd per call; the
structural check (via `os.fstat(fd)`), the backward scan, and the hash-check read all go through
that same fd — never re-resolve the path mid-call. This is its own commit; `Co-Authored-By` trailer
required.

## Subtask T013: Fd-sharing invariant test — `poll_once()`'s hash-check read

Add a test that re-runs WP01's **CORRECTED** fd-sharing pattern — NOT the original "after initial
open" guard, which the plan's own named lazy pattern (`path.stat()` then a separate
`path.open("rb")`) defeats, since `Path.stat()` fires before the one `open()` call in that pattern
(see WP01's T007 for the full derivation). Give `Path.stat` and `Path.open` the same DIFFERENT
tolerance semantics WP01's T007 uses:
- Monkeypatch `pathlib.Path.stat` to raise UNCONDITIONALLY on ANY invocation from within
  `poll_once()` — no "after initial open" carve-out. The design mandates `os.fstat(fh.fileno())`
  exclusively for the size check, including the hash check's own size-adjacent bookkeeping; zero
  legitimate `Path.stat()` calls exist anywhere in the function. (The separate FR-008
  missing-file/existence check is a distinct mechanism — `try`/`except FileNotFoundError` around
  the single `path.open("rb")` call, per WP01 T006 — not `os.fstat()`; see below.)
- Separately, spy on `pathlib.Path.open` (**never `os.open`**, which does not intercept
  `Path.open()` calls and would silently record zero calls, per plan.md's IC-01 "Also required"
  paragraph) and assert it is called **exactly ONE** time total for the whole `poll_once()`
  invocation.

Run this against a `poll_once()` invocation that actually exercises the hash check — reuse T010's
truncate-then-regrow fixture, or any poll where `current_size >= cursor.offset` so the hash check
definitely runs. This closes the gap WP01's own test could not close (the hash check did not exist
yet in WP01) — it now covers all three reads the Architectural Seam paragraph names together: size,
hash-check, and drain, with the corrected asymmetric guard that actually catches the plan's named
lazy pattern. `Co-Authored-By` trailer required on this commit.

**This test's unconditional `Path.stat` raise applies to the WHOLE `poll_once()` call — including
WP01 T006's missing-file check.** Per WP01 T006's corrected constraint, that check must be
implemented as a `try`/`except FileNotFoundError` around the single `path.open("rb")` call, never
via `Path.exists()`/`Path.is_file()`/`Path.is_dir()` (which call `Path.stat()` internally on Python
3.11/3.12 — this repo's required and CI-pinned versions). If WP01's implementation regressed to one
of those pathlib convenience methods, this test would fail on every `poll_once()` invocation, not
just missing-file ones — confirm `tail_reader.py` has no such call before trusting this test's green
result.

## Subtask T014: Fd-sharing invariant test — `validate_resume_cursor()`

Add the analogous test for `validate_resume_cursor()`'s own fd-sharing commitment, using the SAME
corrected asymmetric pattern as T013 (not the original "after initial open" guard): `Path.stat`
raises unconditionally on ANY invocation (the structural in-range check must go through
`os.fstat(fd)` exclusively, per plan.md's "Same commitment for `validate_resume_cursor()`"
paragraph — zero legitimate `Path.stat()` calls), and `Path.open` (never `os.open`) is separately
asserted to be called exactly ONE time total — across all of: the structural (in-range) check, the
backward scan for `start_of_last_line`, AND the hash-check read. No operation inside a single
`validate_resume_cursor()` call may re-resolve the path mid-call, and the unconditional `Path.stat`
raise is what actually catches a lazy implementation that reaches for `path.stat()` before its one
`path.open()` call — the same TOCTOU pattern T013/WP01's T007 name. `Co-Authored-By` trailer
required.

**The same constraint applies here.** `validate_resume_cursor()`'s unconditional `Path.stat` raise
likewise depends on nothing in the function — including any existence or structural check —
routing through `Path.exists()`/`Path.is_file()`/`Path.is_dir()`. If a future change adds a
missing-file guard to `validate_resume_cursor()`, it must use the same
`try`/`except FileNotFoundError`-around-`path.open()` pattern as WP01 T006, not those pathlib
convenience methods, for the identical reason: they call `Path.stat()` internally on Python
3.11/3.12 (this repo's required and CI-pinned versions) and would make this test fail
unconditionally rather than only on the case it's meant to catch.

## Subtask T015: Remaining IC-02 GREEN tests, RED→GREEN verification, coverage, terminology guard

1. Write one assertion per FR-013 structural refusal shape — each of `"negative"`, `"out_of_range"`,
   `"misaligned"` gets its own test (or its own clearly-separated assertion block naming the
   shape), plus a fourth test for the `"content_mismatch"` refusal shape (structurally valid offset,
   invariant supplied and mismatched).
2. **The SUCCESS path of a resume (User Story 3 Acceptance Scenario 1) — every test so far in this
   WP exercises only `validate_resume_cursor()`'s REFUSAL branches; this step is the mission's
   headline P2 resumability guarantee and MUST have its own positive-path test.** Write
   `test_validate_resume_cursor_accepts_structurally_valid_offset_and_resumes_correctly` (or an
   equivalently precise name) as its own top-level pytest function:
   - Write a valid JSONL log to a `tmp_path`-based file and consume it (via `poll_once()`) to a
     known offset `O` at a line boundary, recording the content invariant at `O` (from the returned
     `TailCursor`).
   - Call `validate_resume_cursor(path, O, <that invariant>)` and assert it returns SUCCESSFULLY —
     no `ResumeRefused` raised — with a `TailCursor(offset=O, content_invariant=<that invariant>)`
     (or field-equivalent).
   - Append `M` more events to the file. Feed the `TailCursor` `validate_resume_cursor()` returned
     into `poll_once()` (or `tail_events()`, bounded), and assert exactly the `M` new events are
     yielded — none of the pre-`O` events re-emitted, none skipped. This is the literal contract
     spec.md's User Story 3 AC1 states; a test that stops at "no exception was raised" does not
     prove it.
3. Verify RED→GREEN for T009 and T010 specifically against the merge-base (`db5014ab5`) — i.e.
   confirm both tests are red when run against WP01's final commit (per the ATDD precision note in
   Context) and green against this WP's final commit.
4. Verify ≥90% diff-coverage on this WP's new/changed lines in `tail_reader.py` — it is a listed
   `critical_paths` entry (`'src/specify_cli/status/*'`, `ci-quality.yml:3374`), so the 90% floor is
   load-bearing, not advisory.
5. Run `pytest tests/architectural/test_no_legacy_terminology.py` and confirm it passes (guards
   against any `--feature*` slip anywhere this WP touched, including test docstrings/fixture
   strings).

`Co-Authored-By` trailer required on this commit.

## Definition of Done

| WP | Test file(s) | Marker(s) | CI job |
|---|---|---|---|
| WP02 | `tests/status/test_tail_reader*.py` | `fast` | `fast-tests-status` |

- T009 and T010 verified RED on WP01's final commit specifically — not merely "the module is
  missing" — and GREEN on this WP's final commit.
- ≥90% diff-coverage on this WP's new/changed lines in `tail_reader.py` (critical-path allowlist
  `src/specify_cli/status/*`).
- Every `hashlib.sha256` call site added by this WP — in `tail_reader.py` and in
  `tests/status/test_tail_reader_truncation.py` — carries its own inline
  `# noqa: TID251 — file-integrity content invariant, not the charter hash` comment; no blanket or
  directory-level exemption used.
- Every commit message follows conventional-commits format and ends with the required
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailer.
- The WP01 → WP02 → WP03 sequential chokepoint on `tail_reader.py` is respected: this WP does not
  begin until WP01's final commit is in place. (This WP DOES list `tail_reader.py` in its own
  `owned_files`, alongside `scope: codebase-wide` — that is correct and required for lane collapse;
  see Context. Do not remove it.)
- `pytest tests/architectural/test_no_legacy_terminology.py` passes.

## Risks

- **The severity-4-defect class this WP directly closes**: a reader that tests only the mid-line
  tear shape and never plain clean-boundary truncation reports a confidently wrong (incomplete)
  result on a rollback that lands exactly at a line boundary. T009 is the test that closes this gap
  by name — its own self-check (step 5) is what keeps it from silently regressing back into a tear
  test. Mitigation: T009 and T010 are separate, independently-invokable top-level pytest functions,
  never parametrize cases sharing one body (see plan.md's Risks table, first row).
- **TID251 lint trap**: `hashlib.sha256` is banned repo-wide with no blanket or `tests/`-wide
  exemption; a call site added without its own inline noqa passes locally and fails only at CI's
  `lint` job. Mitigation: every call site gets its own noqa, verified before the final commit (see
  Definition of Done).
- **Fixture-writes-into-real-`kitty-specs/` risk**: `tests/architectural/test_archive_root_byte_identical.py`
  forbids modifying or deleting any pre-existing file under `kitty-specs/` (among other immutable
  roots) — a fixture that reuses a real mission directory instead of a synthetic `tmp_path` one
  would trip this architectural gate. Mitigation: every fixture in
  `tests/status/test_tail_reader_truncation.py` MUST use `tmp_path`-based synthetic files, never
  this mission's own `kitty-specs/event-push-watch-channel-01M1K6W2/` tree or any other real mission
  directory.

## Reviewer Guidance

- Verify the THREE truncation test shapes named across the mission are three separate top-level
  pytest functions — not `parametrize` cases, not asserts sharing one function body — split as:
  WP01 owns shape-(a) (the mid-line tear-is-not-truncation case); this WP (WP02) owns shape-(b)
  (T009, plain clean-boundary truncation via the size check) and the hash-check-catches-regrow shape
  (T010). Confirm each is independently nameable in a CI failure's test node ID.
- Confirm T010's self-asserting precondition (`assert Path(log).stat().st_size >= O` or equivalent)
  is actually present in the test body, immediately before the `poll_once()`/`tail_events()` call
  under test — not merely described in a docstring or comment.
- Confirm the fd-sharing tests (T013, T014) use the CORRECTED asymmetric pattern: `Path.stat`
  raises UNCONDITIONALLY on any call (never `os.open`, which does not intercept `Path(...).open()`
  calls and would silently record zero calls), and `Path.open` is SEPARATELY asserted to be called
  exactly once total — not a shared "after initial open" condition applied to both, and not the
  open-count check alone. A test using the old shared-condition form would silently pass against
  the plan's own named lazy `path.stat()`-then-second-`open()` pattern; verify these tests would
  actually fail against that specific bug, not merely that they patch the right two targets.
- Confirm T015's resume-success-path test (User Story 3 AC1) actually calls
  `validate_resume_cursor()` with a structurally valid offset and asserts SUCCESS (a returned
  `TailCursor`, no exception), then feeds that cursor into a subsequent `poll_once()`/
  `tail_events()` call and asserts exactly the newly-appended events are yielded — not merely that
  no exception was raised.
- Confirm T009 and T010 each include the recovery-half follow-up (post-`log_truncated`
  `poll_once()` call) asserting events yielded after resync match current file content from offset
  0, not just that the `log_truncated` signal fired.
- Confirm T009's own fixture self-check (the remaining bytes DO parse as valid JSON before the
  truncation assertion) is present and would actually fail if the fixture were changed to produce a
  mid-line tear instead — this is what proves the test exercises shape-(b), not shape-(a).
- Confirm every `hashlib.sha256` call site added by this WP carries its own inline TID251 noqa with
  the exact justification text (or an equivalent-in-substance one), not a bare `# noqa: TID251`.
- Confirm no test in this WP writes into a real `kitty-specs/` mission directory — grep the new test
  file for `tmp_path` usage on every fixture.

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent claude
```
