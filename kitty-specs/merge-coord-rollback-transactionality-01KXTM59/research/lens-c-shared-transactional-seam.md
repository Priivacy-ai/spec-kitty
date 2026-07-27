# Lens C — Is there ONE transactional seam that closes both #2786 and #2367?

**Scout:** Paula Patterns (architecture-scout). **Mode:** framing → synthesis.
**Directives applied:** 001 (owning-boundary-first), 003 (record the ownership call),
030 (release action carries the minimum regression), 032 (conceptual/ownership alignment).
**Tactics:** domain-event-capture (durable failure marker), anti-corruption-layer
(VCS-lock leaking into coord logic), review-intent-and-risk-first (does the fix close the
class + blast radius). **Charter:** single canonical authority — reconcile, do not duplicate.

READ-ONLY pre-spec research. No product code edited.

---

## 1. Ownership map (who owns each concern + boundary leaks)

| Concern | Owning module / symbol | Verdict |
|---|---|---|
| Coord-branch **commit** of `done` | `coordination/transaction.py::BookkeepingTransaction` (append→materialize→**safe_commit**→outbound→release; surgical-truncate + byte-snapshot rollback on exception, NEVER `git checkout --`), invoked per-WP via `coordination/status_transition.py::emit_status_transition_transactional` | **Canonical single owner** of coord-branch writes. Correct. |
| Coord-branch **revert** on merge rollback | `merge/executor.py::_capture_pre_target_coord_ref_sha` + `_revert_coord_done_commit` + `_restore_pre_target_if_at_baseline` | **BOUNDARY LEAK.** A second, home-grown compensation that `git revert`s what the canonical txn already committed. |
| Coord **status writes** (per-WP `done`) | `merge/done_bookkeeping.py::_mark_wp_merged_done` / `_record_merged_wps_done_for_merge` → routes through the transactional emit (good) | Write leg is canonical; the **rollback leg is not**. |
| Byte snapshot/restore + target projection | `merge/bookkeeping_projection.py::_capture_bookkeeping_snapshots` / `_restore_final_bookkeeping_snapshots` / `_project_status_bookkeeping_to_target` | A **third** rollback mechanism (raw byte restore) layered outside the txn. |
| Coord-worktree cleanliness / resync | `git/ref_advance.py::advance_branch_ref` (`_dirty_entries`, `RefAdvanceDirtyWorktreeError`, `coord_owned_filenames` #1878 exclusion) — the #1826 guard | Correctly refuses `reset --hard` over uncommitted churn (NFR-002). It is the *victim*, not the defect. |
| Merge state (resumable) | `merge/state.py::MergeState` | Resume/dedup depends on committed==working coherence, which the leak breaks. |
| Doctor / repair | `status/doctor.py` | **GAP.** Checks uninitialized/stale-claims/orphan/drift/self-approval/issue-matrix/sparse-checkout — **no coord split-brain / reconcile-marker repair path.** |

**Core leak:** two competing transaction owners for one concern. `BookkeepingTransaction`
commits each `done` atomically; the merge executor then tries to *un-commit* via an OUTER
`git revert` (`_revert_coord_done_commit`) + raw byte restore that are **not** inside any
transaction. No single merge-scoped transaction wraps `{all done emits + target advance +
worktree resync}` with one rollback — compensation is scattered across every failure exit
via `_restore_pre_target_if_at_baseline`.

## 2. Shared-root verdict

**One seam closes #2786 AND #2367-B — but NOT #2367-A.** Strongest evidence:

- **#2786** (`executor.py:500-514`): on a failed `git revert`, the code runs `revert --abort`
  then `logger.warning("…coherence may be degraded…")` — **no raise, no durable marker.** The
  merge proceeds; committed reduction (`done`) diverges from the rolled-back working tree
  (`approved`) → the #2711 split-brain re-opens; resume dedup/idempotency break.
- **#2367-B** (roadmap `docs/plans/3-2-x-milestone-roadmap.md:125,151`, changelog:609): "rollback
  stale status … lives in the merge-snapshot path." The non-transactional rollback leaves the
  coord worktree dirty; `advance_branch_ref`'s #1826 dirty guard then **refuses to resync**,
  blocking the merge. Same root: the merge's coord-write **rollback** is not owned by the
  canonical transaction, so it strands uncommitted churn.
- The single missing boundary: a **merge-scoped coordination transaction** (delegate the merge's
  `done` write+rollback to `BookkeepingTransaction`'s ownership) whose rollback (a) reverses
  committed-`done` + working-bytes + worktree resync **coherently and atomically**, (b) writes a
  **durable reconcile marker** when rollback cannot complete (closes the #2786 swallow), (c) is
  consumed by a **doctor-repair path**. Route the rollback through the txn → it never leaves
  uncommitted churn → the #1826 guard has nothing to refuse (#2367-B dissolves).

**#2367-A (vcs-lock at claim) is FENCED OUT.** The roadmap is explicit: #2367 is
"one-invariant-**three**-seams, not one code fix"; #2367-A is a *deliberate* stop-gap for the
#2222 / C-003 race, and "committing it would reverse that call." Folding it into the transaction
seam reverses a standing decision — the exact Paula over-reach boundary. So: **partially** shared —
one seam for #2786 + #2367-B; #2367-A stays a distinct concern.

**This is the completion of the #2711 Option-A arc.** Option-A added the coherent-revert leg
(`_revert_coord_done_commit`) but left it *best-effort*; #2786 is precisely that incompleteness.

## 3. Recurrence signature

"Merge leaves coord state partial/incoherent on failure" has been patched per-site and regressed:
`#1826` (dirty-guard + worktree resync, CLOSED) → `#1878` (coord-residue exclusion so the guard
does not over-refuse) → `#2711` Option-A (PARTIAL transactional revert) → **`#2786`** (that revert
swallows failure). Each landed as a new guard at one call site rather than one boundary.
**Class-closing construction (vs whack-a-site):** (1) a transactional context manager owning the
merge's coord write+rollback — **reuse `BookkeepingTransaction`, do not duplicate** (charter
single-canonical-authority); (2) a **durable reconcile marker** persisted on any incomplete
rollback; (3) a **doctor-repair path** that detects + repairs the marker. Regression already fired
once (#2711 → #2786); a fourth per-site patch will recur.

## 4. Scope boundary + WP slicing hint

**IN:** the shared seam. WP-A — fail-loud + durable reconcile marker in `_revert_coord_done_commit`
(closes #2786; flips the already-red `tests/regression/test_issue_2786_revert_failure_split_brain.py`
green — the minimum required regression, directive 030). WP-B — `status/doctor.py` check + repair
that consumes the marker. WP-C — #2367-B: make the merge coord-status **rollback** leave zero
uncommitted churn (commit/rollback within the canonical txn) so the #1826 guard never trips at
merge-rollback time.
**Deferred (architecture issue, needs compatibility justification — resume/idempotency blast
radius):** collapse the executor's home-grown `_capture/_restore_final_bookkeeping_snapshots` +
`_revert_coord_done_commit` into `BookkeepingTransaction` ownership (retire the parallel owner).
**OUT (do not touch):** #2367-A vcs-lock stop-gap (#2222 / C-003 race — reversing it is a
regression); the broader #2392 upgrade-worktree-coherence epic; any non-merge coord write path.

**Overlap risk:** `merge-squash-provenance-and-rollback-coherence-01KXRRB7` is the just-landed
#2709/#2711 mission that *authored* `_revert_coord_done_commit`; its kitty branch worktree is still
checked out (`+` in `git branch`). **Confirm it is closed before editing the same executor rollback
code — shared-file collision.** #2367 is held by the HiC/operator, not a dedicated agent session; no
`2367` code branch exists (only roadmap doc refs), so no agent-session collision — but confirm with
the operator since they own it. Adjacent low-collision surfaces: `merge-base-diff-ssot-01KX44SD`,
`coord-shadows-followups-01KXBCZ1`.
