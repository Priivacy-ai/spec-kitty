---
work_package_id: WP02
title: Time-dependent test rot
dependencies:
- WP01
requirement_refs:
- FR-014
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T006
- T007
- T008
- T009
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/status/
create_intent:
- tests/architectural/test_no_absolute_event_timestamp_mixture.py
execution_mode: code_change
model: ''
owned_files:
- tests/status/test_work_package_lifecycle.py
- tests/architectural/test_no_absolute_event_timestamp_mixture.py
- tests/regression/test_2646_stale_verdict_closes_via_fr001.py
- tests/_arch_shard_map.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 - Time-dependent test rot

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

**The product code is correct.** #3157's failure is a test defect, not a
runtime one: `test_real_implement_and_review_claims_persist_structured_latest_
binding` in `tests/status/test_work_package_lifecycle.py` hard-codes an event
timestamp — `at="2026-08-01T10:00:00+00:00"` (line 252) — authored 2026-07-21,
when that date was safely in the future. The reducer sorts events by `(e.at,
e.event_id)` (see `status/reducer.py`), and every other event in this test's
fixture is stamped with the real wall-clock `now()` by the production helpers
(`start_implementation_status`, `start_review_status`) it calls. As real time
has moved past 2026-08-01, `now()` at test-run time now sorts *after* the
hard-coded 2026-08-01 event that is supposed to represent the reviewer's
`IN_PROGRESS → FOR_REVIEW` transition — which was appended to the log **before**
the later `start_review_status` call in the test body. This is confirmed live on
this branch today: run the file and `test_real_implement_and_review_claims_
persist_structured_latest_binding` fails with `WorkPackageStartRejected: WP WP01
is in 'in_progress', cannot start review` — because the reducer now computes the
current lane from the *later-sorting* real-`now()` event emitted by the
preceding `start_implementation_status` call, not from the hard-coded
2026-08-01 transition the test assumed would always sort first.

**Do not fix this by touching product code.** `status/work_package_lifecycle.py`
and `status/reducer.py` are explicitly out of this mission's scope (plan.md:
"Deliberately NOT in scope... IC-02's finding is that the product code there is
correct; touching it is a defect, not a fix") — neither module is in this WP's
`owned_files`, and a fix that edits either is a defect, whatever test it makes
pass.

**The 28-file figure is not reproducible.** An earlier design pass claimed "218
files carry absolute event timestamps, but only 28 also emit `now()` events" and
budgeted a 28-file allowlist. Candidate classifier rules independently re-run
against this repository yield 12, 10, 48, or 64 depending on exactly what counts
as a "hard-coded event timestamp" and what counts as a "`now()`-generated" one
in the *same event log*. **Deriving and recording the classifier rule is this
WP's deliverable** — report the true denominator your rule produces; do not
inherit or re-assert 28.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story
  6 ("Time-dependent tests cannot rot"), FR-014, SC-013, and the Edge Cases
  section's timestamp-mixture note
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-02
  ("Time-dependent test rot")
- `tests/status/test_work_package_lifecycle.py:245-282` — the exact failing
  test and its fixture shape; also read `tests/status/test_work_package_
  lifecycle.py:57` (`_event(...)`'s default `at=at or f"2026-04-26T10:00:0
  {event_id[-1]}+00:00"`) for the module's other hard-coded-timestamp helper —
  confirm whether it needs the same ban-the-mixture treatment or is already
  safe (it is all-hard-coded within any one test that uses only `_event(...)`
  defaults, which SC-013's second acceptance scenario explicitly says must
  **not** be flagged).
- `tests/regression/test_2646_stale_verdict_closes_via_fr001.py` — an earlier
  mission revision claimed this file was a second live instance of the #3157
  defect; that claim was checked by running it (`2 passed`) and withdrawn — its
  events are all hard-coded, so its relative order is stable forever. This
  file **passes today and is not a baseline failure**; it must never be
  classified as one. Confirm this for yourself by reading its fixture
  (`at="2026-08-02T12:00:00+00:00"` at line 186 and its siblings) before
  touching it; it is in this WP's `owned_files` only so its passing status can
  be reconfirmed after your classifier lands, not because it needs a code
  change.
- `tests/_arch_shard_map.py` — read the module docstring for the `register()`/
  `default_fallback=True` seam (the same one WP01 uses); this WP's new
  architectural check follows the same registration convention.

**Dependency**: WP01 must land first — both WPs touch
`tests/_arch_shard_map.py`, and the file-granularity ownership rule requires a
strict sequence rather than concurrent edits to the same shard tuples.

**Constraints (binding)**:
- **Ban the mixture, never the literal.** A test file with an all-hard-coded
  event log (like `_event(...)`'s defaults, or `test_2646_...py`'s fixture)
  has a stable relative order forever and must not be flagged — banning every
  hard-coded timestamp outright would flag roughly 580 sites (spec.md's own
  measured false-positive estimate, ~87%) including files that are not broken
  and never will be.
- **No product-code changes.** `status/work_package_lifecycle.py`,
  `status/reducer.py`, `status/emit.py` are out of scope for this WP.
- **Report your own denominator.** Do not carry forward "28" from planning
  documents into your PR description or the new check's docstring — state the
  count your derived rule actually produces, and show the rule.

## Subtask T006 — Fix #3157's dated fixture without touching product code

- **Purpose**: Make `test_real_implement_and_review_claims_persist_structured_
  latest_binding` pass at any future date, closing #3157 for good rather than
  buying a few more years.
- **Steps**:
  1. In `tests/status/test_work_package_lifecycle.py`, change the hard-coded
     `append_event(..., at="2026-08-01T10:00:00+00:00")` call at line 252 so it
     no longer race-conditions against the real `now()` timestamps the
     surrounding `start_implementation_status`/`start_review_status` calls
     produce. The house-preferred fix (confirmed against the reducer's `(e.at,
     e.event_id)` sort) is to stop hard-coding an absolute date entirely and
     derive `at` relative to real time — e.g. `(datetime.now(UTC) -
     timedelta(seconds=1)).isoformat()` so it always sorts immediately before
     the subsequent real-`now()` call, regardless of what "now" is when the
     suite runs.
  2. Do not simply bump the literal forward (e.g. to `2027-08-01`) — that
     reproduces the identical defect with a longer fuse, which spec.md's
     Revision History explicitly calls out as the wrong fix ("Changing it to
     2027-08-01 passes with zero product code touched" is offered there as
     *proof the product is correct*, not as the recommended remediation).
  3. Confirm the test passes when run today, and re-derive (do not just assert)
     that it would still pass at an arbitrarily later date by inspecting that
     the new `at` value is computed relative to the call's own execution time,
     not a second absolute literal.
- **Files**: `tests/status/test_work_package_lifecycle.py`
- **Validation checklist**:
  - [ ] `pytest tests/status/test_work_package_lifecycle.py -q` passes in full.
  - [ ] No absolute-date string literal remains in the fixed test.
  - [ ] `status/work_package_lifecycle.py` and `status/reducer.py` are
        byte-identical to before this WP (`git diff` shows no change).
- **Edge Cases**: If another test in the same file relies on this test's
  fixture ordering via shared module-level state (unlikely — check for module-
  level fixtures before assuming isolation), verify it independently after the
  change.

## Subtask T007 — Derive and record the mixture classifier rule; report the true denominator

- **Purpose**: The "28-file" figure this mission's design leaned on is not
  reproducible — this subtask is where the actual, checkable rule gets written
  down, so WP17's mission-exit verification and any future maintainer can
  re-derive the same number from the same rule.
- **Steps**:
  1. Define "hard-coded event timestamp" precisely: a string literal matching
     an ISO-8601 timestamp pattern passed as (or defaulting to) an event's `at`
     field in a call that ultimately reaches `append_event`/`_event`-style
     construction — not any ISO-8601-shaped string anywhere in a test file
     (that would sweep in unrelated fixture data, comments, and docstrings).
  2. Define "`now()`-generated" precisely: an `at` value computed from
     `datetime.now()`, `datetime.utcnow()`, or an equivalent live-clock call —
     directly, or via a production helper (`start_implementation_status`,
     `start_review_status`, etc.) that defaults `at` to the current time when
     the caller does not supply one.
  3. Define "mixture": **both** kinds of `at` value are appended to the **same**
     event log (i.e., the same `feature_dir`/`status.events.jsonl` target)
     within one test — not merely both patterns appearing anywhere in the same
     file. A file with two independent tests, one all-hard-coded and one
     all-`now()`, is not a mixture; a single test appending both kinds to one
     log is.
  4. Run your rule against the full `tests/` tree and record the resulting file
     count and the file list. Compare against the four candidate counts already
     observed (12, 10, 48, 64) — your rule will likely land near one of them;
     state which, and why the others are wrong for this rule's definition.
  5. Record the rule **and** the exact measured file list as a real, checked-in
     artifact in T008's file (`tests/architectural/test_no_absolute_event_
     timestamp_mixture.py`) — a module-level constant (e.g. a `frozenset[str]`
     of the matched file paths and a derived `len(...)` for the count) that a
     test asserts the live derivation still produces today. This is
     deliberately **not** only a narrative description in the module
     docstring: a docstring is prose a reviewer must take on faith, while a
     literal constant is reviewable as a diff — a reviewer can re-run the
     rule and confirm the constant matches, or see exactly which file
     entered or left the set when it next changes. The docstring should still
     explain the rule in words, but the denominator itself must live in code,
     not only in comments.
- **Files**: `tests/architectural/test_no_absolute_event_timestamp_mixture.py`
  (this subtask's own deliverable is the rule definition plus the recorded
  file-list constant landed in that file, not a number quoted only in this
  WP's Activity Log or module docstring prose).
- **Validation checklist**:
  - [ ] The rule is written down precisely enough that a different engineer
        running it against the same tree gets the same file count.
  - [ ] The reported count is the one your own rule measures — not 28, unless
        your rule happens to independently reproduce it (state that
        coincidence explicitly if it occurs).
  - [ ] The measured file list is recorded as a literal, checked-in constant
        (not only prose) in `test_no_absolute_event_timestamp_mixture.py`,
        and a test asserts the live derivation matches it — so the rule's
        actual output is reviewable as a diff of that constant.
  - [ ] `test_2646_stale_verdict_closes_via_fr001.py` is confirmed **not**
        matched by the rule (all-hard-coded fixture, per its own file).
- **Edge Cases**: A test using a helper that sometimes defaults to `now()` and
  sometimes accepts an explicit hard-coded `at` (e.g. `_event(...)`'s optional
  `at` parameter) is a mixture **only** in the specific test invocations that
  exercise both branches within one log — the helper's mere existence is not
  itself a violation.

## Subtask T008 — Author the absolute-event-timestamp mixture check

- **Purpose**: Turn T007's derived rule into a standing architectural check so
  the class of defect #3157 exemplifies cannot recur silently.
- **Steps**:
  1. Create `tests/architectural/test_no_absolute_event_timestamp_mixture.py`
     implementing T007's precise rule as an AST or regex-over-source scan (AST
     is more robust against string-formatting variance; prefer it if the
     existing architectural checks in this repo lean AST — confirm by skimming
     `test_2093_authority_invariant.py`'s approach for the house convention).
  2. The check must fail when a **new** test appends a hard-coded absolute
     timestamp into an event log that, within the same test, also receives a
     `now()`-generated event (SC-013's acceptance scenario 2, verbatim).
  3. The check must **not** fail on a fixture whose events are all hard-coded
     (SC-013's own explicit carve-out) — prove this against
     `test_2646_stale_verdict_closes_via_fr001.py` and against `_event(...)`'s
     own default-timestamp helper used with no override.
  4. Scope the scan to test files under the `tests/` tree that construct or
     append `StatusEvent`-shaped objects (or call `append_event`/the `_event`
     helper pattern) — do not scan production code; this is a test-authoring
     hygiene check, not a runtime invariant.
  5. Include the T007 rule definition and measured file count in the module
     docstring, verbatim, as the recorded classifier.
  6. Prove the check catches the defect it was derived from, not just a
     fixture written to satisfy it after the fact: run the check against this
     WP's **parent commit** (before T006's fixture fix lands) and confirm it
     flags `tests/status/test_work_package_lifecycle.py::
     test_real_implement_and_review_claims_persist_structured_latest_binding`.
     A rule that only reds on a hand-authored temporary fixture and not on
     the real, historical #3157 case has not actually been validated against
     the defect this WP exists to close.
  7. Prove the rule matches the **indirect** shape #3157 actually took: its
     `now()`-generated leg arrives via a production helper
     (`start_implementation_status`), not via a direct `datetime.now()` call
     written inline in the test body. A rule matching only a literal
     `datetime.now()`/`datetime.utcnow()` call site in the same function body
     would miss #3157 entirely, since its `now()` events are produced inside
     the called helper, several frames away from the test's own hard-coded
     `at=` literal. Prove this with a fixture whose `now()` leg is produced
     exactly that way (via a helper call, not an inline `datetime.now()`
     literal) and confirm the check still flags it.
- **Files**: `tests/architectural/test_no_absolute_event_timestamp_mixture.py`
- **Validation checklist**:
  - [ ] The check passes against the current `tests/` tree with T006's fix
        landed.
  - [ ] Introducing a temporary test that mixes a hard-coded `at` and a
        `now()`-generated event in one log makes the check fail (prove it,
        then remove the temporary test).
  - [ ] The check, run against this WP's parent commit (before T006's fix),
        flags `test_work_package_lifecycle.py::
        test_real_implement_and_review_claims_persist_structured_latest_binding`
        — the historical case, not only a synthetic one.
  - [ ] The check flags a fixture whose `now()` leg arrives via a production
        helper such as `start_implementation_status`, not only via a direct
        `datetime.now()` call written inline in the test body.
  - [ ] `test_2646_stale_verdict_closes_via_fr001.py` and any other
        all-hard-coded fixture do not trip the check.
  - [ ] `mypy --strict` / `ruff` clean on the new file.
- **Edge Cases**: A test parametrized across multiple cases where only one
  parametrization mixes timestamp kinds must still be caught — do not let
  parametrize collapse the check's granularity to "the test function exists",
  it must inspect the actual constructed event sequence per case.

## Subtask T009 — Register the shard-map row for the new check

- **Purpose**: Keep CI shard ownership complete and balanced, following the
  same convention WP01 uses for its own new architectural check.
- **Steps**:
  1. In `tests/_arch_shard_map.py`, append
     `"tests/architectural/test_no_absolute_event_timestamp_mixture.py"` to
     whichever `_ARCH_SHARD_N_FILES` tuple is lightest by `def test_` count
     **after** WP01's own append has landed (this WP depends on WP01; do not
     recompute shard weights against a stale pre-WP01 snapshot).
  2. Confirm the append does not collide with WP01's edit — both WPs touch this
     file, which is why WP01 → WP02 is a sequenced dependency rather than a
     concurrent pair (per plan.md's ownership table).
  3. Run the shard-completeness guard (`tests/architectural/
     test_arch_shard_marker_completeness.py`, GC-1, referenced in this file's
     docstring) locally to confirm the new file is correctly assigned rather
     than relying solely on the `default_fallback` hash bucket.
- **Files**: `tests/_arch_shard_map.py`
- **Validation checklist**:
  - [ ] The new file appears in exactly one `_ARCH_SHARD_N_FILES` tuple.
  - [ ] `test_arch_shard_marker_completeness.py` passes.
  - [ ] The diff to this file contains only the new append, not a reshuffle of
        existing rows.
- **Edge Cases**: If WP01's merge already rebalanced the shards such that a
  different shard is now lightest, use the post-WP01 weights, not the ones you
  might have observed before WP01 landed.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP depends on WP01 and
branches from WP01's landed base; worktrees are allocated per lane from
`lanes.json` at `spec-kitty implement WP02` time. Completed changes merge back
into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- `test_real_implement_and_review_claims_persist_structured_latest_binding`
  passes today and is structurally immune to the passage of real time (T006).
- `status/work_package_lifecycle.py` and `status/reducer.py` show zero diff
  from this WP.
- The mixture classifier rule is precisely defined, recorded in the new check's
  docstring **and** as a literal, checked-in file-list constant (not prose
  alone), and the true denominator it measures is reported (not 28 unless
  independently reproduced) (T007).
- The check, run against this WP's **parent commit** (i.e. before T006's
  fixture fix lands), flags
  `tests/status/test_work_package_lifecycle.py::
  test_real_implement_and_review_claims_persist_structured_latest_binding` —
  proving the rule actually catches the defect it was derived from, not merely
  a fixture authored to satisfy the rule after the fact (T007/T008).
- The check flags a fixture whose `now()` leg arrives via a production helper
  such as `start_implementation_status` (an *indirect* `now()` call), not only
  via a direct `datetime.now()` call in the test body itself — this is the
  exact shape #3157's own fixture takes, and a rule that only matches direct
  calls would silently pass over it (T007/T008).
- `tests/architectural/test_no_absolute_event_timestamp_mixture.py` exists,
  passes on the current tree, fails on a deliberately mixed fixture, and does
  not flag an all-hard-coded one (T008).
- `test_2646_stale_verdict_closes_via_fr001.py` passes (2 passed) before and
  after this WP; it is **not** a baseline failure and may never be classified
  as one.
- The new check is registered in `tests/_arch_shard_map.py` (T009).
- `mypy --strict` and `ruff` clean on every touched file.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Reaching for the product code out of habit.** The natural instinct when a
  test fails with a lane-transition error is to "fix" the state machine.
  Mitigate by re-reading the Objective's root-cause trace before writing any
  line — the defect is entirely in the test's own fixture, and a diff touching
  `status/work_package_lifecycle.py` or `status/reducer.py` is itself the
  failure mode this WP exists to avoid.
- **Re-asserting an unverified denominator.** Mitigate by actually running your
  derived rule against the tree (T007) and reporting what it measures, not
  what planning documents assumed.
- **A classifier so broad it flags legitimate all-hard-coded fixtures**, which
  would make the new check itself a source of test rot. Mitigate by testing the
  check against `test_2646_...py` and the `_event(...)` default-only case as
  explicit negative fixtures before considering T008 done.

## Reviewer Guidance

- Confirm `git diff` shows zero change to `status/work_package_lifecycle.py`
  and `status/reducer.py` — any change there is an automatic rejection,
  regardless of whether it happens to make tests pass.
- Confirm the fixed test does not simply push the hard-coded date further into
  the future — ask how the fix behaves if the whole suite is run with the
  system clock advanced by ten years.
- Confirm the reported denominator is the reviewer's own re-derivation of the
  stated rule, not a trust of the PR description's number.
- Confirm `test_2646_stale_verdict_closes_via_fr001.py` was read and reasoned
  about, not just left alone by omission.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP02 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
