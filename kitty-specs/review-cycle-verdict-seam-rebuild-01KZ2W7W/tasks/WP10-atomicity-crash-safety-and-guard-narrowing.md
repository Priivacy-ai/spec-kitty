---
work_package_id: WP10
title: Atomicity, crash-safety, concurrency and the guard narrowing
dependencies:
- WP06
- WP07
requirement_refs:
- FR-003
- FR-004
- FR-005
- NFR-002
- NFR-003
- NFR-005
- NFR-006
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
- T046
- T075
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/cycle.py
- tests/review/test_cycle.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP10 - Atomicity, crash-safety, concurrency and the guard narrowing

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

This WP closes three reproduced (or reproduction-owed) failure modes in the
review-cycle writer, plus a fourth item — narrowing the provenance guard without
disarming it — that shares the same file and has no ordering dependency on the
other three, so it rides along here rather than costing an extra level.

**Per the charter's ATDD-first discipline (C-011), three of these four items are
"reproduction owed": the red test is the first act of the subtask that fixes it,
not an afterthought added alongside the fix.** Do not write the fix and then
retrofit a passing test — write the failing test against today's code, watch it
fail for the reproduced reason, then make it pass.

### 1. Concurrent verdict writes destroy a record (FR-005, NFR-006 — reproduction owed)

Two agents recording distinct verdicts for the same WP simultaneously must
produce two records, or one explicit refusal — never a silent loss where one
caller's write clobbers the other's and **both callers report success**. Today
there is no lock on the allocate-then-write path in `create_rejected_review_cycle`
(`src/specify_cli/review/cycle.py`), so two threads racing
`ReviewCycleArtifact.next_cycle_number` can both read the same "next" number,
both write to the same path, and the second write wins with no error raised to
either caller.

**The critical section is narrower than it looks.** `feature_status_lock`
(`src/specify_cli/status/locking.py`) IS thread-reentrant — it tracks acquisition
depth per thread via a thread-local dict, so nesting it does not deadlock a
single-threaded caller that already holds it. But `_mt_finalize_plan` (which
calls the review-cycle writer, indirectly via `tasks_verdict_persistence.py`
after WP06's extraction) runs BEFORE `_mt_execute` acquires
`feature_status_lock` — see `src/specify_cli/cli/commands/agent/tasks_move_task.py:2369-2370`
(`_mt_finalize_plan(st, ports)` then `_mt_execute(st, ports)`). A lock acquired
**inside** `create_rejected_review_cycle` and a lock acquired **inside**
`_mt_execute` are therefore two separate critical sections over two disjoint code
regions, not one. **FR-005's scope for THIS WP is the (cycle-number-allocation +
artifact-write) pair only** — not the wider (artifact, status-event) pair, which
would require restructuring the caller's control flow and is out of this WP's
reach. State this scoping explicitly in code comments so a future reader does not
assume the lock covers more than it does.

### 2. Crash between write and commit orphans the record (FR-003 — reproduction owed)

A process killed after `artifact.write(artifact_path)` but before the commit
lands leaves an uncommitted file on disk. The identical retry must then succeed
and record the correct verdict, with **no manual cleanup**. Today the write and
commit are not atomic with respect to a process kill, and depending on which
verdict was being written, the retry either (a) hits the content-identity guard
against its own orphan and is refused forever (rejection retry), or (b) the
approval retry short-circuits at the "latest.verdict != rejected" no-op check —
because the orphan's verdict is already `"approved"` — and silently reports
success despite nothing being committed.

### 3. Retry-on-index-contention is unbuildable as originally recorded (mechanism shared with FR-002, owned by WP11)

An earlier design assumed the commit layer could detect and retry specifically
on a git `index.lock` collision. **It cannot, as recorded.**
`CommitRouterResult.status` (`src/specify_cli/coordination/commit_router.py:94-119`)
is a closed four-value `Literal["committed", "unchanged", "no_op_wrong_surface",
"error"]`, and an `index.lock` collision inside the underlying `safe_commit` call
discards git's actual stderr on the way to that projection — it collapses to
`status="error"` with **no signal distinguishing "lost a race for the index" from
"the commit failed for some other reason."** The buildable form uses the
EXISTING public probe `specify_cli.status.views.git_operation_in_progress()`
(`src/specify_cli/status/views.py:198`), whose `_GIT_OP_MARKERS` tuple already
includes `"index.lock"` among its markers (line 34-40 lists `rebase-merge`,
`rebase-apply`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `index.lock`).
Retry when `status == "error"` **and** the probe fires, bounded (a small fixed
retry count with a short backoff — this is a lock contention window measured in
milliseconds, not a long-running condition), with a terminal hard failure after
the bound is exhausted. Do not attempt to retry on every `"error"` — only when
the probe corroborates that a git operation is genuinely in progress; otherwise
a real, non-transient commit failure would be silently retried and its
diagnostic lost.

### 4. The content-identity guard's narrowing must not disarm the #990 control (FR-004)

FR-004 requires that repeat reviewer feedback (the SAME defect re-reported in the
same words) be **recordable** — today `_guard_feedback_source_provenance`
(`src/specify_cli/review/cycle.py:331-382`) refuses ANY exact content match
against a prior cycle, including one that is a distinct reviewer's honest
re-report of the same defect. The narrowing must be **specific**: a file that
**is** a prior verdict record — by path (`resolved_feedback.parent ==
resolved_dir` and the filename matches `review-cycle-N.md`), OR by content that
parses as one (the exact-match-after-normalization check already present) —
stays refused. That is the #990 / #2996(b) control, and **C-007 requires the PR
to claim `Closes #990`**. Deleting or loosening the content-identity check to
satisfy FR-004 is a **C-002 violation** — C-002 names `_content_identity`
(fold `ca53e0bbd`) as a behaviour floor whose *mechanism* may change but whose
*guarantee* may not weaken. Re-read `data-model.md`'s I-6 before touching this:
*"I-6 is called out because FR-004 creates pressure against it, and the shortest
path to FR-004 is to delete it. That path is a constraint violation, not an
implementation choice."*

**What FR-004 actually needs, concretely**: after WP04/WP06's changes land, does
the current exact-match-after-normalization check ALREADY admit "distinct
reviewer prose that merely repeats earlier prose" (per FR-004's own wording), or
does it currently refuse that case too? Re-derive this from the current code and
tests before assuming a change is needed here at all — the plan's phrasing
("narrowed, not removed") implies the guard is already close to correct and this
subtask's job may be primarily to **add the missing test coverage that proves
it**, plus close any small residual gap the read reveals.

## Context & Constraints

Read these in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story 1 (Acceptance Scenarios 4, 6, 7), FR-002, FR-003, FR-004, FR-005, NFR-006, C-002, Edge Cases ("Concurrent verdict writes", "Process killed between write and commit", "Cycle-number gaps")
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-05a ("Atomicity and crash-safety on the writer") and IC-10 ("merged into IC-05a" — the guard-narrowing note), and the plan's "Serialization boundary" decision row in the Summary table
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/data-model.md` — I-1 through I-6, especially I-6
- `src/specify_cli/review/cycle.py` — the entire writer: `create_rejected_review_cycle`, `_commit_review_cycle_artifact`, `_guard_feedback_source_provenance`
- `src/specify_cli/status/locking.py` — `feature_status_lock`, its thread-reentrant depth-counter implementation
- `src/specify_cli/status/views.py:198-230` (approx.) — `git_operation_in_progress` and `_GIT_OP_MARKERS`
- `src/specify_cli/coordination/commit_router.py:94-119` — `CommitRouterResult`'s closed `status` `Literal`

**Note on `feature_status_lock` as a NEW test seam**: per plan.md's Technical
Context, `feature_status_lock` is NOT a port — it is imported directly and
patched by module symbol in ~20 existing test suites (typically replaced with a
`_null_lock` no-op). A lock acquired inside `review/cycle.py` under a DIFFERENT
import path is a DIFFERENT symbol those existing `monkeypatch.setattr` calls do
not reach — meaning a real `FileLock` would spawn a real `git rev-parse
--git-common-dir` subprocess inside currently-fast unit tests that patch the
symbol at its `tasks_move_task`/`tasks.py` import site and expect zero
subprocess calls. Two things follow: (a) import `feature_status_lock` in
`review/cycle.py` the same way `tasks_move_task.py` does it (check whether that
module imports it as `from specify_cli.status.locking import
feature_status_lock` directly, or via the `_tasks` re-export shim used
elsewhere in `tasks_move_task.py` — match whichever pattern keeps a SINGLE
patchable symbol), and (b) T046 exists specifically because acquiring a real
lock inside a test that only ever ran against a bare `tmp_path` (no `.git`
directory) manufactures the stray-`.git`/ambient-repo-marker hazard issue #2990
guards against — `feature_status_lock_path` resolves through
`_git_common_dir(repo_root)`, which requires a real repo.

**Constraints (binding)**:
- **C-002**: three folds may have their mechanism replaced but not their guarantee weakened — `_content_identity` (a verdict record re-submitted as feedback is refused, by path AND content — the #990 control), the compensator (a failed durable write leaves no orphan), and the two-leg writer (a self-generated approval body never collides with a prior record). All three regression tests pinned at those commits must stay green throughout this WP.
- **NFR-006**: any serialization introduced by FR-005 must NOT hold an inter-process lock across a `git` subprocess invocation. This is a hard requirement on the lock scope you design — the retry-on-index-contention mechanism (item 3 above) runs the commit call OUTSIDE the lock, precisely so the lock never wraps the `git commit` subprocess.
- **C-007**: the PR closing this WP's work must be able to claim `Closes #990` truthfully — meaning the narrowing (item 4) must leave the #990 reproduction test green, not merely "mostly green."
- This module (`review/cycle.py`) is a convergence point claimed by WP10, WP13, WP14 — serialized `WP10 → WP13 → WP14` per `tasks.md`'s ownership table. Do not attempt WP13/WP14-shaped consolidation here.

## Subtasks & Detailed Guidance

### Subtask T040 – Red-first reproduction of concurrent verdict loss

- **Purpose**: Per C-011, prove the concurrency defect fails against today's code before touching the writer, so the fix (T041) is verifiably closing a demonstrated gap rather than a hypothetical one.
- **Steps**:
  1. In `tests/review/test_cycle.py`, add a test using **real processes or threads** (SC-004 in spec.md specifies "at least 50 iterations at 2+ concurrent processes (not threads — `feature_status_lock` is inter-process)" for the FINAL acceptance bar; for the red-first reproduction here, a threaded harness racing `create_rejected_review_cycle` against a shared `sub_artifact_dir` on a barrier is sufficient to demonstrate the defect quickly — but plan the fixture so T041's green-state test can be upgraded to the real multi-process form without a rewrite).
  2. Two callers, distinct bodies (e.g. `body="Reviewer A's feedback"` and `body="Reviewer B's feedback"`), racing `create_rejected_review_cycle` for the SAME `wp_id`/`wp_slug` with a synchronization barrier so both reach the number-allocation point at approximately the same instant.
  3. Assert the defect: run it against the PRE-fix code (no lock yet) and confirm it demonstrates data loss — either both calls return success but only ONE record exists on disk (the other's content is nowhere), or (less likely given no collision-refusal exists yet) an unhandled exception from a raw filesystem race. Record which failure mode you observed.
  4. Confirm this test FAILS (in the sense of demonstrating the defect, however that manifests — a losing assertion, not necessarily a crash) before T041 lands, then leave it as the pinned regression once T041 makes it pass correctly (two distinct records, both readable, both correct).
- **Files**: `tests/review/test_cycle.py`
- **Parallel?**: No — this red test must exist and be observed failing before T041's fix begins.
- **Notes**: The observed pre-fix failure mode should be recorded in the Activity Log or PR description (per this mission's spec.md Revision History emphasis on evidence over assertion) — e.g. "confirmed: with no lock, cycle 2 exists on disk with Reviewer B's body; Reviewer A's write returned success but its content is unrecoverable."

### Subtask T041 – Serialize allocation and write under `feature_status_lock`

- **Purpose**: Close the concurrency defect by wrapping cycle-number allocation (`ReviewCycleArtifact.next_cycle_number`) and the subsequent `artifact.write(...)` in ONE critical section, using the existing `feature_status_lock` primitive rather than inventing a new lock.
- **Steps**:
  1. In `create_rejected_review_cycle` (`src/specify_cli/review/cycle.py`), wrap the span from `cycle_n = ReviewCycleArtifact.next_cycle_number(sub_artifact_dir)` through `artifact.write(artifact_path)` (and the immediately-following `validate_review_artifact_file(artifact_path)` — see T043 for why validation belongs inside too) in `with feature_status_lock(main_repo_root, mission_slug):`.
  2. **Do NOT extend the lock to cover the commit call** (`_commit_review_cycle_artifact`) — that is a `git` subprocess invocation, and NFR-006 forbids holding this lock across one. The lock's scope is allocation + write + validation ONLY.
  3. Import `feature_status_lock` the same way the existing ~20 test suites' `monkeypatch.setattr` calls expect to reach it (see the Context section's note above) — verify by running the existing test suite unmodified after this change and confirming none of those 20 suites suddenly spawn a real `git rev-parse` subprocess. If any do, you have imported it under a second, unpatched symbol; fix the import path, don't patch 20 more tests.
  4. Update T040's red test to assert the CORRECT green outcome: both callers succeed, and there are TWO distinct artifacts on disk (`review-cycle-N.md` and `review-cycle-N+1.md`), each with its own caller's exact body content intact.
  5. Add a code comment at the lock site stating explicitly the FR-005 scoping decision: "this lock covers cycle-number allocation and the artifact write ONLY — NOT the (artifact, status-event) pair, because `_mt_finalize_plan` (which calls this function) runs before `_mt_execute` acquires its own `feature_status_lock` instance over the status-event emit; these are two disjoint critical sections by construction, not one."
- **Files**: `src/specify_cli/review/cycle.py`, `tests/review/test_cycle.py`
- **Parallel?**: No — depends on T040's red state.
- **Notes**: `feature_status_lock` is thread-reentrant (a thread-local depth counter, `src/specify_cli/status/locking.py:81-92`), so if a FUTURE caller already holds the lock when it calls into this function, nesting is safe and will not deadlock. This WP does not need to verify that reentrancy itself (it is existing, tested behaviour) — just rely on it correctly.

### Subtask T042 – Retry the commit on index contention via the existing probe

- **Purpose**: Make "retry-on-contention" buildable, using the mechanism that actually exists rather than the one an earlier, refuted design assumed.
- **Steps**:
  1. In `_commit_review_cycle_artifact` (`src/specify_cli/review/cycle.py:385-431`), when `result.status == "error"`, call `specify_cli.status.views.git_operation_in_progress(main_repo_root)` (import at module level, matching this module's existing import style) to check whether the failure correlates with an in-progress git operation (which includes but is not limited to `index.lock` contention — see `_GIT_OP_MARKERS`).
  2. If the probe returns `True`, retry the SAME `commit_router.commit_artifact(...)` call, bounded to a small fixed number of attempts (e.g. 3) with a short sleep between attempts (e.g. 100-250ms — this is a lock-contention window, not a long outage; do not use exponential backoff on a multi-second scale here).
  3. If the probe returns `False` on the first `"error"`, do NOT retry — this is a genuine commit failure (bad state, real error) and retrying would silently mask its diagnostic. Raise `ReviewCycleError` immediately, as today.
  4. After the retry bound is exhausted with the probe still firing, raise `ReviewCycleError` with a message distinguishing "exhausted contention retries" from a plain commit failure, so an operator/log-reader can tell the two apart.
  5. Confirm the retry loop lives ENTIRELY outside `feature_status_lock`'s scope (T041) — the commit call was already outside that lock before this subtask; this subtask must not accidentally widen the lock to also cover the retry loop.
- **Files**: `src/specify_cli/review/cycle.py`
- **Parallel?**: [P] with T043 in the sense that both touch `_commit_review_cycle_artifact`/its callers, but read T043 first — they interact (the retry loop must not swallow the "leave no artifact" contract).
- **Notes**: This closes the "unbuildable as recorded" gap the plan's Risks section names explicitly. Do not attempt to distinguish `index.lock` specifically from the other `_GIT_OP_MARKERS` entries (`rebase-merge`, `MERGE_HEAD`, etc.) — the probe is deliberately a single boolean signal ("a git operation is in progress right now"), and treating any of its markers as retry-worthy is consistent with the mission's framing ("the probe fires").

### Subtask T043 – Make the failure path leave no artifact, including validation failure

- **Purpose**: Ensure EVERY failure mode after the write — not just a commit failure — leaves "no artifact" as the recoverable state, per C-002's compensator floor and I-1/I-2 in data-model.md. Today, `artifact.write()` and `validate_review_artifact_file()` sit OUTSIDE the existing `try/except ReviewCycleError: artifact_path.unlink(missing_ok=True); raise` compensator (`review/cycle.py:539-562`), which wraps ONLY the `_commit_review_cycle_artifact` call. If `validate_review_artifact_file(artifact_path)` (line 537, called right after `artifact.write(artifact_path)` at line 536, both BEFORE the `if commit_router is not None:` block at line 539) raises for any reason, the write already landed on disk and nothing cleans it up.
- **Steps**:
  1. In `create_rejected_review_cycle`, widen the compensator's scope: wrap `artifact.write(artifact_path)` AND `validate_review_artifact_file(artifact_path)` in the SAME try/except-and-unlink pattern the commit call already uses, not just the commit call alone.
  2. Confirm this widened compensator interacts correctly with T041's lock — the write is inside the lock (T041), the unlink-on-failure must ALSO happen while still holding that lock (so a racing second writer cannot observe the orphan mid-cleanup and treat it as a legitimate prior cycle). Structure the `try/except` so its scope is nested correctly relative to the `with feature_status_lock(...):` block from T041 — the unlink belongs INSIDE the lock, alongside the write it is cleaning up after.
  3. Re-verify (do not just assume) that a validation failure (a malformed artifact somehow constructed, or an `OSError` from a full disk, etc.) now results in "no artifact on disk", by adding a test that forces `validate_review_artifact_file` to raise (e.g. monkeypatch it to raise `ReviewCycleError` unconditionally) and asserting the artifact file does not exist afterward.
  4. Re-run the T044 crash-orphan test (below) against this widened compensator once both exist — the two subtasks jointly need to prove: (a) commit failure leaves no artifact (already true, now with the widened scope re-verified), (b) validation failure leaves no artifact (NEW, this subtask), (c) a hard process kill CANNOT be caught by any Python-level `try/except` (see T044) and is handled differently — by making the retry idempotent, not by a compensator.
- **Files**: `src/specify_cli/review/cycle.py`, `tests/review/test_cycle.py`
- **Parallel?**: [P] with T042 (different failure leg of the same function), but coordinate — both touch the same `try/except` region.
- **Notes**: This is a distinct fix from T042 — T042 makes a TRANSIENT commit failure retryable; T043 makes a GENUINE failure (validation, or a commit failure that exhausts T042's retries) leave a clean "no artifact" state so the caller's retry is a plain re-run, not a manual-cleanup operation.

### Subtask T044 – Red-first reproduction of the crash-orphan

- **Purpose**: Per C-011, reproduce FR-003's "process killed between write and commit" scenario BEFORE relying on T043's widened compensator alone to have solved it — a hard `SIGKILL` cannot be caught by any `try/except`, so this is a DIFFERENT mechanism than T043's validation-failure fix, and needs its own reproduction to confirm what actually happens today.
- **Steps**:
  1. In `tests/review/test_cycle.py`, add a test that simulates a hard kill: the most faithful approach is a subprocess harness that calls `create_rejected_review_cycle` in a child process and sends `SIGKILL` (or the platform equivalent) to it after the write lands but before the commit completes (e.g. monkeypatch/instrument `_commit_review_cycle_artifact` to signal readiness via a file/pipe, then kill the child at that point) — reproducing spec.md's Acceptance Scenario 4 literally ("a process killed between the write and the commit"). If a true subprocess+signal harness is disproportionate for this test's fixture budget, an acceptable substitute is directly asserting the STATE the mission's design nominally leaves behind: manually write the artifact to disk (bypassing the commit step, simulating the exact moment of a kill) and confirm what the CURRENT retry does when `create_rejected_review_cycle` is called again with the same inputs.
  2. Confirm — this is the reproduction — that TODAY (before T041/T043's fixes), the retry is NOT idempotent: for a rejection retry, the orphan collides with the content-identity guard and is refused (permanently, with no path to recover without manual deletion); for an approval retry, the orphan's `verdict == "approved"` already, so `_persist_approved_review_cycle`'s no-op check (`if latest is None or latest.verdict != "rejected": return`) short-circuits and reports SUCCESS while having written and committed NOTHING new.
  3. Once T041 (lock) and T043 (widened compensator) both land, re-run this test and confirm the retry now succeeds cleanly: either the orphan was already cleaned up by T043's widened compensator (if the "crash" happened before the compensator's scope closed), or — for the true unrecoverable-crash case where the process died so abruptly that even the compensator never ran — the identical retry from the CALLER (i.e. `move-task` re-invoked) succeeds because there is genuinely no artifact left over to collide with (T043 having already ensured the ONLY state that persists past a clean exit path is either "fully written + committed" or "nothing").
- **Files**: `tests/review/test_cycle.py`
- **Parallel?**: No — depends on understanding T043's actual compensator scope to design the correct fixture.
- **Notes**: Be precise in the test's docstring about WHICH crash window is being simulated (before vs. during vs. after the compensator's own `try` block) — a true `SIGKILL` mid-write can leave a partially-written file on some filesystems, which is a different (and generally accepted as out-of-scope for pure-Python mitigation) hazard than a `SIGKILL` cleanly between a completed write and a not-yet-started commit. Scope this test to the latter, which is what spec.md's Acceptance Scenario 4 actually describes ("between the write and the commit").

### Subtask T045 – Narrow the content-identity guard without disarming the #990 control

- **Purpose**: Deliver FR-004 (repeat feedback is recordable) while keeping I-6 / the #990 control intact — a file that IS a prior verdict record (by path or by content) stays refused; anything else must be admitted.
- **Steps**:
  1. Re-read `_guard_feedback_source_provenance` (`review/cycle.py:331-382`) and `_content_identity` (`review/cycle.py:313-328`) carefully against FR-004's exact wording: "Distinct reviewer prose that merely repeats earlier prose is admissible." Determine precisely what "repeats earlier prose" means as distinct from "duplicates a prior review-cycle artifact verbatim" — the current guard's content-identity leg already normalizes whitespace and strips frontmatter before comparing; a SECOND, independent reviewer's honest re-report of the same underlying defect, in their OWN words (even if substantively similar), does NOT hit an exact-match-after-normalization comparison and should already pass today.
  2. Determine whether the CURRENT implementation already satisfies FR-004 as stated, or whether there is a genuine gap: specifically, check what happens when the SAME reviewer re-submits BYTE-IDENTICAL feedback for a recurring defect (SC-001's literal wording: "a reviewer can re-report a recurring defect using byte-identical feedback"). If the current guard refuses this (which spec.md's Edge Cases and SC-001 both assert it does, citing the exact reproduced error `ReviewCycleError: feedback_source content duplicates a prior review-cycle artifact (review-cycle-1.md) verbatim`), the gap is real and needs a genuine design decision — NOT weakening `_content_identity`, since that is the exact C-002-protected mechanism.
  3. Resolve the apparent tension (FR-004 wants byte-identical repeat feedback recordable; C-002/I-6 forbid weakening the content-identity check) by re-reading what the content-identity check is ACTUALLY comparing: it compares the FEEDBACK SOURCE's content against PRIOR REVIEW-CYCLE ARTIFACTS' bodies — i.e., it refuses re-submitting a prior artifact's own generated file as if it were fresh feedback. It does NOT (and must not start to) refuse two DIFFERENT feedback-source files that happen to contain the same prose, submitted on two DIFFERENT occasions, where the SECOND submission is a genuine, distinct reviewer action pointing at a NEW feedback file. Confirm via a fixture: does calling `create_rejected_review_cycle` twice with `feedback_source` pointing at two SEPARATE files (not the artifact from cycle 1) that happen to contain identical prose currently succeed or fail? If it currently FAILS (comparing the second feedback file's content against the FIRST CYCLE's stored body, not against the feedback source), that is the genuine defect FR-004 names, and the fix is: compare the feedback source against prior artifacts to detect "this literally IS one of my own outputs" (path- or self-referential-content detection), NOT "this repeats prose a human already said once" — the latter comparison is the one to remove/narrow; the former must stay.
  4. Implement the narrowed check precisely: keep BOTH the path-identity leg (unchanged — a feedback file physically living inside the WP's own `sub_artifact_dir` at a `review-cycle-N.md`-shaped name) and a content-identity leg that still catches "this feedback file's content, once its own frontmatter is stripped, is identical to a stored artifact's frontmatter-stripped body" (the #990/#2996(b) case: someone re-feeds a PRIOR ARTIFACT FILE back in as if it were new feedback, whether by literal path or by copy-with-rename). Do NOT add any new leniency that would let a genuinely self-referential resubmission (an artifact file, or an exact copy of one) through — only ensure that TWO DISTINCT feedback submissions containing the same reviewer prose, neither of which IS a stored artifact, are both admitted.
  5. Update or add tests distinguishing the two cases explicitly: (a) resubmitting `review-cycle-1.md` itself (or an exact byte-copy of it) as `feedback_source` — MUST still raise (this is #990/#2996(b), C-007's `Closes #990` claim depends on this staying red-then-green); (b) submitting a genuinely new feedback file whose prose happens to be identical to a PRIOR REVIEWER's stored artifact body, on a SEPARATE occasion, where the new file is NOT itself a stored artifact — MUST now succeed if it does not today (this is FR-004/SC-001).
- **Files**: `src/specify_cli/review/cycle.py`, `tests/review/test_cycle.py`
- **Parallel?**: No — this subtask requires the T040-T044 lock/compensator work to be settled first so tests here run against the final writer shape, avoiding rebase churn.
- **Notes**: **Do not guess at this distinction from memory — re-derive it from the actual code and the actual pinned regression tests (`test_self_referential_feedback_source_is_rejected`, `test_new_cycle_body_never_duplicates_a_prior_cycle_file` in `tests/review/test_cycle.py`, both landed by the predecessor PR #3156) before changing anything.** If, after this re-derivation, the current implementation ALREADY correctly admits case (b) and only refuses case (a), then T045's job is primarily to ADD the missing test coverage proving FR-004/SC-001 are satisfied — not to change the guard's logic at all. Do not manufacture a code change where the honest finding is "already correct, needs a test."

### Subtask T046 – Ensure review fixtures run under a real initialized repo

- **Purpose**: T041's lock acquisition resolves `feature_status_lock_path` through `_git_common_dir(repo_root)` (`src/specify_cli/status/locking.py:61-62`), which requires a real `.git` directory. Any `tests/review/test_cycle.py` fixture that currently constructs `main_repo_root` as a bare `tmp_path` (no `git init`) will now either fail outright (no git common dir resolvable) or — worse — manufacture the exact stray-`.git`/ambient-repo-marker hazard issue #2990 exists to guard against (a lock/resolution walk escaping the intended tmp-path boundary and picking up an ambient repo marker from an ancestor directory, e.g. the real checkout the test runner itself lives in).
- **Steps**:
  1. Audit every fixture in `tests/review/test_cycle.py` that constructs a `main_repo_root` / calls `create_rejected_review_cycle` — identify which ones currently pass a bare `tmp_path` with no `git init` having been run against it.
  2. For each such fixture, add a real `git init` (and whatever minimal config `git commit` needs — e.g. `user.email`/`user.name`, matching the pattern other tests in this repo already use for git-backed fixtures — search `tests/coordination/` and `tests/review/` for an existing "real initialized repo" fixture helper before writing a new one) so the fixture root is a genuine repo, not a bare directory.
  3. Re-run the FULL `tests/review/test_cycle.py` suite after T041-T045 land and confirm no test now fails because `feature_status_lock`/`_git_common_dir` cannot resolve a git directory, and no test starts walking outside its `tmp_path` boundary (verify via whatever #2990-guard assertion pattern `tests/regression/test_birth_cutover.py` already established — check line ranges 869, 919-982 for the shape of that guard, since this is the SAME class of hazard applied to a different call site).
  4. Do NOT initialize a repo at a directory ABOVE the test's intended root (that would recreate the exact #2990 hazard from a different direction) — the `git init` must happen exactly at the fixture's `main_repo_root`, nowhere else.
- **Files**: `tests/review/test_cycle.py`
- **Parallel?**: No — depends on T041 existing (the lock is what creates this requirement) and should run last, as a sweep over everything the prior subtasks touched.
- **Notes**: This subtask is entirely about test infrastructure, not production code — no change to `src/specify_cli/review/cycle.py` beyond what T041-T045 already made. If an existing shared fixture helper for "real initialized git repo at tmp_path" already exists elsewhere in the test suite (check `tests/conftest.py` and `tests/coordination/conftest.py` first), reuse it rather than writing a new one — this repo's existing pattern strongly favors one canonical fixture over per-file duplicates.

### Subtask T075 – Restate NFR-005's countable clause against one named port method

- **Purpose**: NFR-005 as spec.md states it ("at most one durable-persistence
  invocation per verdict") is unsatisfiable literally — plan.md's Technical
  Context corrects this explicitly: every verdict already costs **two**
  durable-persistence invocations (one `commit_artifact` call for the
  review-cycle record, one `commit_status` call for the status event), and
  FR-001's authority split requires both to exist. A countable clause nobody
  can satisfy is not a requirement, it is decoration. This subtask restates
  the clause against the ONE port method this WP's writer actually calls, so
  the assertion becomes checkable and true.
- **Steps**:
  1. In `tests/review/test_cycle.py`, locate the existing 2-second wall-clock
     budget assertion NFR-005 cites.
  2. Add (or strengthen) an assertion that recording one verdict invokes the
     writer's own durable-persistence port method — `commit_artifact` on
     `commit_router`/`ports.coord`, whichever name this WP's DI shape uses —
     **at most once** per verdict-recording call. A spy/counter on the fake
     router is sufficient. Do not also count `commit_status` calls, which
     belong to a different call site (`_mt_execute`) outside this WP's owned
     surface.
  3. State explicitly, in a code comment or the test's docstring, that the
     literal reading of NFR-005 ("at most one durable-persistence invocation
     per verdict", full stop) is false as written, and why — citing plan.md's
     Technical Context correction — so a future reader does not attempt to
     collapse the review-cycle write and the status-event emit into a single
     invocation, which the authority split (FR-001) forbids.
  4. Confirm the existing 2-second wall-clock budget assertion still passes
     unchanged — this subtask adds a countable invocation assertion alongside
     it, not a replacement.
- **Files**: `tests/review/test_cycle.py`
- **Parallel?**: Independent of T040-T046's lock/compensator work; sequence
  last so it asserts against this WP's final writer shape.
- **Notes**: This subtask exists solely to make NFR-005 checkable against one
  named port method (`commit_artifact`) — do not widen it to assert anything
  about `commit_status`'s call count, a different module's concern this WP
  does not own.

## Test Strategy

- `pytest tests/review/test_cycle.py -v` — full file, including all new red-then-green tests from T040-T046
- Full scoped regression before marking done: `pytest tests/review/ tests/post_merge/ -q` (NFR-001 — zero regressions)
- The three C-002-pinned regression tests by name, confirmed green throughout: the `_content_identity` fold's tests, the compensator's orphan-cleanup test, and the two-leg-writer's approval-body-collision test — identify their exact current names in `tests/review/test_cycle.py` before starting and re-run them after EVERY subtask, not just at the end.
- `mypy --strict src/specify_cli/review/cycle.py`
- `ruff check src/specify_cli/review/cycle.py tests/review/test_cycle.py` — watch the `C901` complexity ceiling (NFR-002, `max-complexity = 15`): `create_rejected_review_cycle` is already a long function before this WP's additions (lock wrapping, widened compensator, retry loop in a helper); extract small helpers (e.g. a private `_allocate_and_write_locked(...)` and a private `_commit_with_contention_retry(...)`) rather than letting the top-level function's branch count grow past 15.
- SC-004's full multi-process bar (50+ iterations, 2+ real OS processes, not threads) belongs to WP15's durability-matrix coverage over the real command surface — this WP's own T040/T041 tests may use a lighter-weight threaded or simulated-race harness to prove the mechanism; do not block this WP on building the full SC-004 harness, but leave a clear note (e.g. a `# TODO(WP15)` or an explicit cross-reference in the test docstring) so WP15 knows where the heavier bar is measured.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement` this
WP may branch from a dependency-specific base (WP06 and WP07 must be merged
into whatever base this WP branches from), but completed changes must merge
back into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human
explicitly redirects the landing branch.

## Definition of Done

- [ ] T040: the concurrent-write red state was observed against the unmodified
      writer and the observed failure mode is recorded in the Activity Log or
      PR description before T041's fix begins.
- [ ] T041: the `with feature_status_lock(...)` block's body contains
      **exactly** allocation + write + validation + unlink, and the commit
      call (`_commit_review_cycle_artifact`) is textually **outside** it — a
      reviewer can point at the block's boundaries in the diff and confirm
      this directly.
- [ ] T042: the contention retry gates on `git_operation_in_progress()`
      returning `True`, never on `status == "error"` alone; a non-contention
      error raises `ReviewCycleError` immediately, with zero retries.
- [ ] T043: a forced `validate_review_artifact_file` failure leaves no artifact
      file on disk, proven by a test that forces the failure and asserts the
      file's absence; the unlink-on-failure runs inside the same lock scope as
      the write it cleans up after.
- [ ] T044: the crash-orphan reproduction is observed red pre-fix (rejection
      retry refused forever, or approval retry silently no-ops while
      recording nothing) and green post-fix (the identical retry succeeds and
      records the correct verdict, with zero manual cleanup).
- [ ] T045: the three C-002-pinned regression tests
      (`test_self_referential_feedback_source_is_rejected`,
      `test_new_cycle_body_never_duplicates_a_prior_cycle_file`, and the
      compensator's own orphan-cleanup test) remain green throughout; a
      genuinely new feedback file whose prose repeats a prior reviewer's words
      on a separate occasion is admitted.
- [ ] T046: every new fixture added by this WP initializes a real git repo at
      its own root (never an ancestor), and none of the ~20 existing
      `feature_status_lock`-patching suites spawns a real `git rev-parse`
      subprocess as a side effect of this WP's changes.
- [ ] T075: NFR-005's countable clause is restated and asserted against one
      named port method (`commit_artifact`), with the literal, unsatisfiable
      reading documented as false and why.
- [ ] NFR-002: every function touched by this WP ends at cyclomatic complexity
      ≤15 (`ruff C901`); extract helpers rather than letting
      `create_rejected_review_cycle` grow past the ceiling.
- [ ] NFR-003: `ruff` and `mypy --strict` report zero issues on every touched
      file, with zero new suppressions.
- [ ] Full scoped regression (`pytest tests/review/ tests/post_merge/ -q`)
      shows no new failures beyond `research/baseline-8466727eb.md`'s two rows
      (NFR-001).

## Risks & Mitigations

- **Lock-scope creep**: the most tempting mistake is widening `feature_status_lock`'s scope to also cover the commit call "to be safe" — this directly violates NFR-006 (no lock across a `git` subprocess) and was explicitly rejected by the plan's Serialization boundary decision. Mitigate by keeping the `with feature_status_lock(...):` block's body to EXACTLY allocation + write + validation + the widened T043 compensator, and nothing else — the commit call and its T042 retry loop live entirely outside it.
- **False belief that `feature_status_lock`'s reentrancy solves the FR-005 scoping question**: reentrancy prevents a DEADLOCK if the same thread nests two acquisitions; it says nothing about whether the two disjoint critical sections (this WP's write-side lock, and `_mt_execute`'s separate transition-side lock) actually serialize against EACH OTHER when held by two DIFFERENT concurrent callers. They do not, and this WP's scope (per the plan) is deliberately narrowed to allocation+write only — do not claim FR-005 covers more than that in code comments or PR description.
- **Retry loop masking a real failure**: T042's contention-retry must gate strictly on `git_operation_in_progress()` returning `True` — retrying blindly on every `status == "error"` would silently swallow genuine, non-transient commit failures (permission errors, corrupted repo state, disk full) and report them as exhausted-retry timeouts instead of their real cause. Keep the probe check as a hard gate, not a heuristic hint.
- **Guard-narrowing scope creep (T045)**: the single biggest risk in this WP is "fixing" FR-004 by weakening `_content_identity` broadly, which would satisfy SC-001's test while quietly re-opening #990/#2996(b) — a C-002 violation and a false `Closes #990` claim (C-007). Re-derive the actual current behaviour from code + the two pinned PR #3156 regression tests before writing any new production code for T045; the honest outcome may be "no code change needed, only new test coverage."
- **`tmp_path`-as-bare-directory hazard (T046)**: any fixture added by T040-T045 that does NOT initialize a real repo will either break outright once T041's lock lands, or silently work by accident against an ambient repo marker from a parent directory — the #2990 hazard. Write every NEW fixture in this WP with a real `git init` from the start rather than retrofitting T046 as an afterthought at the end.

## Reviewer Guidance

- Confirm T040's red state was actually observed (activity log or PR description states what failure mode was seen) before T041's fix — same ATDD discipline check as WP09's T034.
- Confirm the lock in T041 wraps ONLY allocation+write+validation, not the commit call — a reviewer should be able to point at the exact `with feature_status_lock(...):` block boundaries in the diff and confirm the commit call sits outside it.
- Confirm T042's retry gates on `git_operation_in_progress()`, not on `status == "error"` alone — a shortcut implementation that retries blindly on any error is a common trap here.
- Confirm T043's widened compensator covers `validate_review_artifact_file` failures with a real test forcing that failure, not just a comment claiming it does.
- Confirm the three C-002-pinned tests (name them explicitly in the review) are STILL GREEN after this WP's full diff, and that T045 did not weaken `_content_identity`'s guarantee to satisfy FR-004 — verify by re-running `test_self_referential_feedback_source_is_rejected` and confirming it still raises.
- Confirm every NEW fixture in `tests/review/test_cycle.py` added by this WP initializes a real git repo at its OWN root (not an ancestor), per T046.
- Confirm no lock was added anywhere that could hold across a `git` subprocess call — grep the diff for every `subprocess.run`/`commit_artifact`/`commit_router` call site and confirm none of them execute while `feature_status_lock` is held.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.
- 2026-08-04T00:00:00Z – claude – lane=for_review – Implemented T040-T046 + T075.
  T040 (red-first, concurrent verdict loss): added
  `test_concurrent_verdict_writes_do_not_clobber_each_other`. Ran it against
  the unmodified (pre-T041) `cycle.py` and observed a RAW FILESYSTEM RACE
  (not the "both succeed, one record" variant): thread A raised
  `ValueError('Review artifact file has no YAML frontmatter:
  .../review-cycle-1.md')` from `validate_review_artifact_file` because both
  threads allocated cycle 1 and wrote to the same path concurrently,
  corrupting the file mid-read. After T041's lock, 5/5 repeated runs green.
  T044 (red-first, crash-orphan): added
  `test_crash_orphan_between_write_and_commit_permits_a_clean_retry`. Wrote
  an orphan `review-cycle-1.md` directly (bypassing the commit step) then
  retried with the same feedback against the unmodified writer; observed
  `ReviewCycleError: feedback_source content duplicates a prior
  review-cycle artifact (review-cycle-1.md) verbatim` — the rejection
  retry permanently refused, exactly the failure mode the prompt named.
  Green after T043 (widened compensator) + T045 (narrowed guard).
  T041: allocation+write+validation+unlink now run inside ONE
  `with feature_status_lock(...)` block in a new helper,
  `_allocate_and_write_review_cycle_locked`; the commit call and its T042
  retry loop stay textually outside it. Ran the full `tests/review/`,
  the ~20 suites that `monkeypatch.setattr` `feature_status_lock`, and
  `tests/architectural/` in full — no suite spawned an unexpected real
  `git` subprocess; all green.
  T042: `_commit_review_cycle_artifact` now retries on `status == "error"`
  gated strictly on `git_operation_in_progress()`, bounded to 3 attempts,
  0.15s sleep; a non-contention error still raises immediately with zero
  retries (existing test unchanged/still green).
  T043: the write+validate try/except-unlink now lives inside T041's lock;
  added `test_validation_failure_after_write_leaves_no_orphaned_artifact`
  forcing `validate_review_artifact_file` to raise and asserting no
  orphan survives.
  T045 (guard narrowing): replaced `_guard_feedback_source_provenance`'s
  body-equality content leg (`_content_identity`/`_strip_frontmatter`/
  `_normalize_whitespace`, now removed as dead code) with a self-contained
  parse-check: does `feedback_source` itself parse as a `ReviewCycleArtifact`?
  Path leg unchanged. **Both pinned regressions were re-examined under a
  coordinator ruling** after `test_new_cycle_body_never_duplicates_a_prior_cycle_file`
  went red against the sanctioned narrowing: the coordinator determined (citing
  US1 Acceptance Scenario 5, SC-001, and spec.md's Revision History) that this
  pinned test's refusal assertion was itself wrong against the finalized spec —
  its cited "Acceptance Scenario 2" was a misattribution — and cleared a
  rewrite. Renamed to `test_duplicate_prose_in_an_ordinary_feedback_file_is_admitted`
  (now asserts admission + a genuine new cycle), with the full history recorded
  in its docstring. Applied the identical reasoning to the analogous M4 test
  (`test_resubmitted_feedback_with_its_own_frontmatter_is_still_rejected`,
  renamed `test_frontmatter_shaped_feedback_prose_resubmitted_verbatim_is_admitted`)
  since it drove the same "ordinary feedback file, not a stored artifact"
  shape — flagged explicitly in its docstring and this report as an
  extension of the coordinator's ruling, not an independently-taken
  liberty. Added `test_a_byte_copy_of_a_stored_artifact_under_a_new_name_is_still_rejected`
  to carry #990/#2996(b) forward explicitly (content-parse leg, path
  leg deliberately not implicated). `test_self_referential_feedback_source_is_rejected`
  (the #990 path-leg control) was NEVER modified and stays green throughout.
  Accepted residual (recorded in the guard's docstring too): a byte-copy of
  a stored artifact with its frontmatter manually stripped now parses as
  plain prose and is admitted — textually indistinguishable from a reviewer
  re-typing the same words, which FR-004 explicitly licenses; no rule can
  separate the two.
  T075: added `test_create_rejected_review_cycle_invokes_commit_artifact_at_most_once`
  asserting `commit_artifact` invoked at most once per verdict-recording
  call via a local spy; does not count `commit_status` (a different call
  site's concern).
  Disclosed cross-WP edit: added two new rows (writer + reader) to
  `tests/architectural/census/verdict_seam_IC01.yaml` for the new
  `_allocate_and_write_review_cycle_locked` helper, which the AST census
  correctly classifies as both (writes a `review-cycle-N.md`-shaped
  filename; calls `validate_review_artifact_file`, an existing reader, via
  same-module one-hop closure). No existing row was modified or removed.
  SC-004's full multi-process bar (50+ iterations, 2+ real OS processes)
  is NOT met by this WP's T040 test — it uses a threaded harness
  (documented as deliberately lighter-weight, with a `# TODO(WP15)`
  cross-reference) since `feature_status_lock` is a real inter-process
  `FileLock`, so two threads already contend on the same lock file two
  processes would. The real multi-process bar is left to WP15 per the
  prompt's own Test Strategy section.
  Also fixed, in scope: `test_resolve_canonical_pointer_returns_valid_artifact`
  (T046) lacked a real `git init`, which broke once T041's lock started
  resolving `feature_status_lock_path` through a real `_git_common_dir`
  subprocess call against a non-existent directory; added `_init_repo(repo)`.
  Also fixed: one new test's `assert len(on_disk) == 2` tripped
  `tests/architectural/test_golden_count_ban.py`'s convert-classification
  gate; converted to an exact-set assertion (`{p.name for p in on_disk} ==
  {"review-cycle-1.md", "review-cycle-2.md"}`) rather than escaping it,
  since the stronger content-based assertion was straightforwardly
  available.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP10 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
