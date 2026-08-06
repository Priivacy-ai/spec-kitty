---
affected_files: []
cycle_number: 1
mission_slug: verdict-seam-write-unification-01KZ9Q35
reproduction_command:
reviewed_at: '2026-08-06T03:25:26Z'
reviewer_agent: user
verdict: rejected
wp_id: WP05
---

---
work_package_id: WP05
review_cycle: 1
reviewer: reviewer-renata
verdict: changes_requested
---

# WP05 Review — Reader Collapse (cycle 1)

## Summary

The safety core of this WP is **excellent** and every mission-critical guarantee
holds, non-vacuously and empirically. There is **one blocking finding**: a new
safety-relevant helper introduced by this WP (`_wp_id_from_stem`) has **no test
covering the exact branch it was added to fix** — the non-hyphen-separator
extraction path. That path guards a *fail-open* keying error at the approval
guard, and the commit message itself states a regression exercising it is
needed. Add that regression and this WP is approvable as-is (no production
change required).

Everything else PASSES. Details below so the fix cycle is trivial.

---

## BLOCKING — Issue 1: `_wp_id_from_stem` non-hyphen path is untested (new safety-relevant branch)

`tasks_verdict_persistence.py` adds `_wp_id_from_stem` (regex
`^(WP\d+)(?=$|[-_.])`) to fix a real bug where the prior naive
`stem.split("-")[0]` returned the *whole stem* for an underscore/dot-separated
WP filename. The regex is **correct by inspection**, and the hyphen/bare-stem
path is exercised (`test_tasks_move_task_seam.py::test_resolve_review_verdict_facts_picks_highest_cycle`
uses `WP01-do-a-thing`). But **no test in the repo exercises the distinguishing
input** — a stem containing `.` or `_` before the id boundary (e.g.
`WP05.foo` from a file `WP05.foo.md`, or `WP05_foo`). Verified: `grep -rn
_wp_id_from_stem tests/` and a scan for non-hyphen WP stems both return nothing
relevant.

Why this matters (and why it is not merely cosmetic): in
`resolve_review_verdict_facts`, `wp_id = _wp_id_from_stem(wp_path.stem)` keys the
event-authority lookup. If extraction yields a wrong key (`WP05.foo`), the lookup
returns `slot_present=False` → the function returns `(None, None, None)` → the
approval guard treats it as "no rejection to refuse on" → **the approve move
proceeds even when the event log recorded `changes_requested` under the real key
`WP05`.** At the approval guard, "verdict reads as absent" is **fail-OPEN** for a
rejected WP — the exact class this mission exists to close. (Note: the commit
message labels this "fail-CLOSED-shaped"; at the safety gate the consequence is
fail-open, which strengthens the need for the regression, not weakens it.)

Real-world exposure is limited (FR-018 rejects underscore slugs; canonical WP
files are `WP<n>-<kebab>.md`), so this is not a live incident — but it is a new
branch on a safety path, on the mission's most safety-critical WP, and the
charter binds "every new branch/helper needs tests in the same PR."

**Fix (test-only, no production change needed):** add a parametrized regression
that drives `_wp_id_from_stem` (and ideally `resolve_review_verdict_facts` end to
end) with non-hyphen stems — at minimum `"WP05.foo"` and `"WP05_foo"` — asserting
(a) the extracted id is `"WP05"`, and (b) an event-recorded `changes_requested`
under `"WP05"` is resolved (proving the approval guard refuses, i.e. the fail-open
is closed). A red-first form (asserting the old `split("-")[0]` would have
returned the whole stem and missed the verdict) makes the non-vacuity explicit.

---

## Non-blocking observations (no action required for approval)

1. **Stale test *names* under the baseline-floor lock.** Several pinned tests were
   correctly repointed to the new event-authority behavior but keep names that now
   read backwards, e.g.
   `test_malformed_review_artifact_frontmatter_becomes_schema_diagnostic` and
   `test_forced_null_review_result_defers_to_frontmatter_and_still_refuses` now
   assert `findings == []` (the frontmatter/schema-diagnostic legs are retired).
   This is the *right* call given `mission_exit_baseline.txt` forbids renaming them
   (a rename would red the floor — a hard reject). Docstrings document the
   inversion. Flagging only so a future reader is not confused; do not change.

2. **`mypy --strict src/specify_cli/status` reports 7 `no-any-return` errors** in
   `progress.py`, `uninitialized_hint.py`, `lifecycle_events.py`, `emit.py`,
   `aggregate.py`, `work_package_lifecycle.py` — **none touched by WP05**, the
   `review` package is clean. Pre-existing batch artifact (per CLAUDE.md's
   "batch has a known pre-existing false positive"). Not this WP's.

3. **`tests/status/test_reducer.py::...::test_event_sourced_review_result_this_missions_own_meta_json_fixture`
   is red** — this is the pre-existing #3220 self-referential meta.json fixture.
   WP05 did not touch this test or its class; it is present and red on the mission
   base. Leave it.

---

## What was verified GREEN (for the record)

- **SC-002 single-authority (non-vacuous):** real disagreement fixtures in
  `test_verdict_seam_reader_collapse.py` prove the approval guard and status
  display resolve the EVENT verdict over a contradicting `.md` in *both*
  directions; the merge gate is pure-event; `test_2093` arm 4 enforces
  structurally with a poison non-vacuity control that correctly leaves the kept
  `.latest`/`.from_file` content loaders GREEN.
- **SC-004 fail-closed (parametrized over readers):** approval guard damaged →
  synthetic non-None name → caller refuses; status display → damaged entry; merge
  gate damaged → G2 no-block via the REAL reducer catch (malformed snapshot, not
  mocked). Layering is sound (approval guard fail-closes upstream of the gate).
- **`.latest`/`.from_file` KEPT:** both present, used by `arbiter.py:461`
  (cycle_number) and `workflow_executor.py:1132/1134` (prose); `verdict` field and
  `from_dict` intact; only the two genuine verdict-parser functions retired. No
  surviving import/call of the retired functions in `src/` (comments only).
- **Demote correctness (D-PLAN-11):** `_commit_review_cycle_artifact` → `bool`,
  non-committed = WARNING + `return False`, never raises; single live caller;
  lands in the SAME commit as the reader flip; event append remains authoritative.
- **Allowlist EMPTY:** `_UNSWEPT_ALLOWLIST == frozenset()`,
  `test_allowlist_is_empty_after_wp05` asserts it; both sweep sites route through
  `verdict_vocab` (`cycle.py` emission bridge, `review_artifact_consistency.py`
  `is_changes_requested`).
- **Census shrink:** `test_verdict_seam_census` GREEN (derived == fixture); reader
  rows retired with `retiring_fr`.
- **Baseline intact:** `test_mission_exit_baseline` GREEN — every at-risk pinned
  node-id present under its original name, repointed (not deleted).
- **Reducer product logic UNCHANGED** (docstring-only diff) — no `(at, event_id)`
  tie-break product change, no conflict with WP04's reducer sweep.
- **Out-of-map collateral all justified:** `status/__init__.py` 2-name facade
  promotion (contract's named public API); `verdict_provenance_backfill.py`
  resolves its own `TODO(WP04)` onto canonical `verdict_vocab`;
  `tasks_status_cmd.py` signature consequence (`tasks_dir`→`feature_dir`);
  fixture repairs in `test_move_task_*` hand-seed the `review_result` event the
  fake router never appended. Nothing weakened or deleted to go green.
- **Gates:** `ruff` clean; `mypy --strict review` clean; test_2093 +
  vocab-single-source + census + baseline + `tests/review/` + `tests/post_merge/`
  = 618 passed / 1 skipped; durability matrix `-n0` = 36 passed (negative control
  reds on a dropped event); terminology guard 10 passed.

Resolve Issue 1 (one added test) and re-request review.
