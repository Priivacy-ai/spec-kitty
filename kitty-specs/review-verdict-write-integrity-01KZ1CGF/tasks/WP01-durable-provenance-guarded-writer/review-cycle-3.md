---
affected_files: []
cycle_number: 3
mission_slug: review-verdict-write-integrity-01KZ1CGF
reproduction_command:
reviewed_at: '2026-08-02T20:50:46Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

---
affected_files: []
cycle_number: 2
mission_slug: review-verdict-write-integrity-01KZ1CGF
reproduction_command:
reviewed_at: '2026-08-02T21:10:00Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP01
---

# WP01 Review Feedback — Cycle 2 Rejection

## Verdict: REJECTED (one finding, otherwise strong)

## What's correct (re-verified independently, not just re-read)

- **The cycle-1 fix is real and complete.** `_guard_rejected_verdict`
  (`tasks_transition_core.py`) now only refuses an unparseable verdict or
  `--skip-review-artifact-check` without `--note`; the ordinary
  rejected→approved path falls through to `Emit` with
  `authorize_review_override=False`. `_authorize_review_override` itself, the
  guard ordering (`_GUARDS` tuple), and `override_persist_signal`/
  `arbiter_persist_signal`'s OLD-timing slicing are byte-for-byte unchanged —
  confirmed by diff, not just docstring claims.
- `_mt_finalize_plan` now takes `ports: TasksPorts` and calls
  `_persist_approved_review_cycle()` whenever `st.target_lane in (APPROVED,
  DONE)`, gated correctly on `latest.verdict == "rejected"` (no-op on
  first-cycle or already-approved). Real `reviewer_agent`, never `"unknown"`.
- T003's provenance guard (`_guard_feedback_source_provenance`) genuinely
  implements path-identity and content-identity as two **independent**
  checks, confirmed by all three tests: exact self-reference
  (`test_self_referential_feedback_source_is_rejected`), content-only
  duplicate at a different path
  (`test_new_cycle_body_never_duplicates_a_prior_cycle_file`, correctly
  rewritten to `pytest.raises` per cycle 1's own remediation, asserting
  `latest()` stays cycle 1 with the real `reviewer_agent`), and the new
  path-only case with hand-edited, non-duplicate content
  (`test_hand_edited_own_path_feedback_source_is_still_rejected`). Deleting
  either check independently would fail one of these three — genuine
  coverage, not a shortcut.
- T004's commit step is real on the happy path:
  `test_create_rejected_review_cycle_commits_the_written_artifact` uses a
  real `git init` fixture and the real `RealCoordCommitRouter` (no stub),
  and asserts via `git status --porcelain` / `git log --name-only` — not
  "no exception raised".
- Backward compatibility (C-002/NFR-001) holds: the only two pre-existing
  callers of `create_rejected_review_cycle`
  (`tasks_move_task.py`'s rejection branch, `tasks_materialization.py`'s
  `_persist_review_feedback`) both omit `verdict`/`commit_router` and are
  untouched by this diff (confirmed: `tasks_materialization.py` has zero
  diff lines). `validate_review_artifact` has exactly one other call site
  (inside `create_rejected_review_cycle` itself) — no ripple.
- All 9 target-scoped test files pass (88/88 across
  `tests/review/test_cycle.py`,
  `tests/post_merge/test_review_artifact_consistency.py`,
  `tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py`,
  `tests/integration/test_review_cycle_rejection_only.py`), plus
  `tests/specify_cli/cli/commands/agent/test_tasks.py` and
  `test_tasks_cli_contract_coord.py` (39/39). `mypy --strict` on the four
  target files has exactly one error
  (`tasks_move_task.py:1933`, `_mt_shell_pid_baseline`, `no-any-return`) —
  confirmed pre-existing on the merge-base
  (`kitty/mission-review-verdict-write-integrity-01KZ1CGF`) via
  `PYTHONPATH=<repo>/src mypy --strict` against the base file; not
  introduced by this WP.
- No scope creep beyond what cycle 1's own finding required:
  `tasks_transition_core.py` + its test files were touched only to fix the
  guard bug the WP's own activity log flagged, and no other WP touches those
  files (WP02's `owned_files` are `agent_utils/status.py` and a new
  regression test — zero overlap).

## Why this is rejected

**Anti-pattern checklist item 3 (silent empty return) fails.** The new
`_commit_review_cycle_artifact` (`src/specify_cli/review/cycle.py`) calls
`commit_router.commit_artifact(...)` and **discards the returned
`CommitArtifactResult` entirely** — no `.status` check, no `.diagnostic`
surfaced, nothing:

```python
def _commit_review_cycle_artifact(
    commit_router: CoordCommitRouter,
    *, ... ,
) -> None:
    commit_router.commit_artifact(
        MissionHandle(repo_root=main_repo_root, mission_slug=mission_slug),
        (artifact_path,),
        f"chore: Record review-cycle-{cycle_number} ({verdict}) for {wp_id} on {mission_slug}",
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        policy=ProtectionPolicy.resolve(main_repo_root),
    )
```

This is a real, reachable failure mode, not a theoretical one. Trace:
`commit_artifact` → `commit_for_mission` (`coordination/commit_router.py`)
wraps `safe_commit` in:

```python
except subprocess.CalledProcessError as exc:
    ...
    return CommitRouterResult(status=_STATUS_ERROR, ..., diagnostic=str(exc))
except RuntimeError as exc:
    if _is_empty_changeset_error(exc):
        return CommitRouterResult(status=_STATUS_UNCHANGED, ...)
    return CommitRouterResult(status=_STATUS_ERROR, ..., diagnostic=str(exc))
```

and `safe_commit`'s own `ProtectedBranchRefused` is declared as
`class ProtectedBranchRefused(SafeCommitError)` where
`class SafeCommitError(RuntimeError)` (`src/specify_cli/git/commit_helpers.py`).
So a protected-destination refusal, or any other `SafeCommitError`/
`CalledProcessError` during the commit, is caught **inside**
`commit_for_mission` and converted to a plain `status="error"` return value
— it never raises out to the caller. Because
`_commit_review_cycle_artifact` never inspects that return value,
`create_rejected_review_cycle` reports success (returns
`CreatedRejectedReviewCycle` normally) even though the artifact was **never
committed** — it silently reverts to exactly the pre-mission bug (#2697:
"the writer's output was never git-committed... lands untracked in whatever
branch happens to be checked out") with zero signal to the caller or the
operator.

This isn't a hypothetical hardening request — it's the WP's own stated
purpose. Per T004's note: *"This was the single highest-severity finding
from the post-plan squad... Do not skip it or treat it as optional."* SC-003
says "every write is committed... verified by a regression test asserting
`git status` shows it tracked" — the happy path is correctly tested, but
there is **no test at all** exercising what happens when the commit fails,
and the production code path has no defined behavior for that case either
(compare with the two existing callers this WP was told to mirror —
`tasks_mark_status.py:239` and `tasks_map_requirements.py:553` — both check
`router_result.status == "committed"` and at minimum print a `[yellow]
Warning[/yellow]` when it isn't; this WP's version checks nothing).

## What to fix (cycle 2)

1. In `_commit_review_cycle_artifact` (`src/specify_cli/review/cycle.py`),
   capture the `CommitArtifactResult` and act on `.status`. Given this WP's
   premise is a *durability guarantee* (stronger than the "best-effort,
   warn-only" bar the subtask-marking/requirement-mapping call sites accept
   for their own artifacts), the correct behavior is almost certainly to
   `raise ReviewCycleError(...)` carrying `.diagnostic` when `.status` is not
   `"committed"` (treat `"unchanged"` as acceptable if you can show it's a
   legitimate no-op for this call shape — it likely can't occur here since
   `cycle_n` is always a freshly written file, so it's fine to fold it into
   the same failure branch, or to leave a one-line comment on why it's safe
   to treat as success if you determine otherwise). Whichever behavior you
   choose, document why in a short docstring note, matching this codebase's
   "no effect-free exception handling" standard.
2. Add a regression test that drives this failure path with a fake/stub
   `CoordCommitRouter` whose `commit_artifact` returns a non-`"committed"`
   `CommitArtifactResult` (no real git needed), and asserts
   `create_rejected_review_cycle` raises (or otherwise surfaces the failure)
   rather than returning success while the artifact sits uncommitted on
   disk.
3. Re-run `tests/review/test_cycle.py tests/post_merge/
   test_review_artifact_consistency.py
   tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py
   tests/integration/test_review_cycle_rejection_only.py` plus
   `test_tasks.py`/`test_tasks_cli_contract_coord.py`, and re-confirm
   `mypy --strict` stays at the one pre-existing, unrelated
   `_mt_shell_pid_baseline` error.
4. Update the Activity Log describing this fix.

Everything else in this WP — the guard fix, the writer generalization, the
provenance guard, the wiring into `_mt_finalize_plan`, and the test rewrites
— is correct and does not need to change. This is cycle 2 of a max-3
rejection budget.
