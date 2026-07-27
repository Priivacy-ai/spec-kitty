# Lens B — Rollback & Resume Coherence (issue #2711)

> **CORRECTION (post-spec squad, reviewer-renata):** the failure-injection patch
> target cited later in this file — `specify_cli.merge.executor.integrate_mission_into_target`
> — is WRONG and will never fire: `executor.py` imports that symbol as a *lazy local
> import* (executor.py:470), so the module-level name does not exist to patch. The
> canonical target is the source module: **`specify_cli.lanes.merge.integrate_mission_into_target`**
> (as used in spec.md and lens-d). Do NOT copy this file's patch target.

**Bug:** Merge rollback and resume leave committed `done` events opposed to a
reverted working status; `--resume` then reports `0/N already done` and
DUPLICATES transitions.

**Verdict:** This is a transactionality defect. The merge writes to THREE
independent durable/working surfaces that are never bound into a single atomic
unit. The rollback path only knows how to undo ONE of them (a byte-snapshot of
working-tree files), so a failure between "done committed" and "target
advanced" leaves the durable git commit standing while the working copy and the
resume progress ledger are byte-reverted underneath it. Resume then trusts the
reverted copies.

READ-ONLY investigation. No product code or tests were modified.

---

## 1. The three states and where they diverge

The merge moves three things that MUST move together but do not:

- **(a) Durable git commits of `done` events** — on the **coordination branch**
  (`destination_ref`). Emitted per-WP through `BookkeepingTransaction`, which
  commits via `safe_commit` immediately, one commit per WP.
- **(b) The working-tree status snapshot** — the on-disk `status.events.jsonl`
  / `status.md` bytes, PLUS `merge-state.json` (`completed_wps`). Captured and
  restored by a plain byte-snapshot mechanism with **no git awareness**.
- **(c) Target-branch advancement** — the mission→target integration.

### Where (a) is durably committed

`src/specify_cli/merge/done_bookkeeping.py:335` — `_mark_wp_merged_done` emits
the `done` transition:

```python
emit_status_transition_transactional(
    TransitionRequest(... to_lane="done", actor="merge", force=_force_done, ...),
    ensure_sync_daemon=False, sync_dossier=False,
)
```

That call routes into `src/specify_cli/coordination/status_transition.py:859-894`
(`BookkeepingTransaction.acquire(...)` → `txn.append_event(event)`), and the
transaction's `__exit__` commits on the happy path:
`src/specify_cli/coordination/transaction.py:918-923` (implicit `self.commit(msg)`
→ `safe_commit`, `transaction.py:1106`). **Each `done` event is an immediate,
durable git commit on the coordination branch.**

### Where (b) is reverted — but NOT (a)

The rollback is a byte-restore of working-tree files only:
`src/specify_cli/merge/bookkeeping_projection.py:217-233`
(`_restore_final_bookkeeping_snapshots`) → `_restore_optional_bytes`
(`bookkeeping_projection.py:170-175`) rewrites/unlinks file bytes. There is **no
`git reset` / `git revert`** of the coordination-branch commit created in (a).

For a coordination-topology mission the pre-target path is taken
(`done_marked_before_target = is_under_worktrees_segment(status_surface_path)`,
`src/specify_cli/merge/executor.py:341-343`). The rollback trigger for the
described repro (target advancement fails) is
`_restore_pre_target_if_at_baseline`,
`src/specify_cli/merge/executor.py:399-412`, invoked from
`_phase_mission_to_target` on failure (`executor.py:455`, `executor.py:490`).

**Net divergence:** the coordination-branch commit from
`done_bookkeeping.py:335` survives; the working `status.events.jsonl` and
`merge-state.json` are byte-restored to their pre-`done` snapshot →
committed = `done`, working = `approved`. Exactly the repro.

---

## 2. Resume progress-derivation defect

Resume does **not** derive progress from durable committed events. It derives
it from `MergeState.completed_wps` — a field that the rollback just byte-reverted
to empty — and its dedup guard reads a working tree the rollback also reverted.

### Why `0/N already done`

The pre-target snapshot is captured at
`src/specify_cli/merge/executor.py:374-381` **before**
`_record_merged_wps_done_for_merge` runs (`executor.py:384-393`). That done-loop
is what populates `completed_wps` (`done_bookkeeping.py:568-575` via
`mark_wp_complete` + `save_state`). So the captured `merge-state.json` snapshot
predates every completion. When the mission→target step fails and
`_restore_pre_target_if_at_baseline` restores that snapshot
(`executor.py:399-412` → `bookkeeping_projection.py:217-233`),
`merge-state.json.completed_wps` is reset to `[]`.

The resume banner reads that reverted field directly:
`src/specify_cli/merge/executor.py:224-228`
(`len(run.state.completed_wps)/len(run.state.wp_order)`) → prints `0/N`. The CLI
resume banner does the same: `src/specify_cli/cli/commands/merge.py:363-364`.

### Why DUPLICATE transitions

Two dedup layers both fail because both read reverted surfaces, not the durable
commit:

1. **State-level reconcile short-circuits.**
   `_reconcile_completed_wps_for_resume`,
   `src/specify_cli/merge/done_bookkeeping.py:525`:
   ```python
   if not merge_state.completed_wps:
       return set()
   ```
   `completed_wps` is `[]` (reverted), so the reconcile returns an empty
   confirmed-set and never consults the event log. No WP is skipped.

2. **Event-log dedup reads the reverted worktree, not the committed branch.**
   `_mark_wp_merged_done` guards with
   `_has_transition_to(... "done" ...)`, `done_bookkeeping.py:285`. That resolves
   the read contract via `status_transition.py:680-681`:
   ```python
   if worktree_root.exists():
       return EventLogReadContract.coordination_worktree(transaction_feature_dir)
   ```
   i.e. it reads the coordination **worktree working tree** — which the rollback
   reverted to `approved`. The committed `done` on the coordination branch ref is
   NOT consulted while the worktree exists. Dedup misses → `done_bookkeeping.py:335`
   re-emits → a SECOND `done` commit is appended to the coordination branch.
   **Duplicated transition.**

So resume re-runs the entire done-loop from scratch, appending duplicate `done`
events on top of the ones (a) already committed.

---

## 3. Structural root cause (the non-transactional seam)

**One-liner:** The merge commits `done` events to the coordination branch as an
independent, immediately-durable git transaction (a), but rolls back only a
byte-snapshot of the working-tree copies + `merge-state.json` (b) — there is no
single atomic unit spanning (a) durable status commit, (b) working snapshot, and
(c) target advancement, and no git-level revert of (a).

Operations and their (non-)atomicity:

| Surface | Written by | Undo on failure | Git-aware? |
|---|---|---|---|
| (a) coord-branch `done` commit | `BookkeepingTransaction` (`done_bookkeeping.py:335`) | **none** | commit is durable, never reverted |
| (b) working `events`/`status` + `merge-state.json` | `_capture_bookkeeping_snapshots` snapshot | `_restore_final_bookkeeping_snapshots` byte-restore | no (raw file bytes) |
| (c) target ref | `integrate_mission_into_target` | guard `_target_branch_still_at_baseline` | ref check only |

**The producing ordering:**
`_capture_bookkeeping_snapshots` (executor.py:374-381) →
`_record_merged_wps_done_for_merge` commits `done` to coord branch, durable
(done_bookkeeping.py:335; completed_wps saved) →
`_phase_mission_to_target` attempts (c), FAILS (executor.py:465-494) →
`_restore_pre_target_if_at_baseline` byte-restores (b) INCLUDING the
pre-completion `merge-state.json` (executor.py:399-412) → `typer.Exit(1)`.

Result: (a) committed, (b) reverted, (c) never happened. The charter states the
append-only event log is the **sole authority** and snapshots are materialized —
but this rollback mutates the *working copy* of that "authority" (and the resume
ledger) by byte-restore, while the true durable authority (the branch commit) is
untouched. Resume then trusts the mutated working copy over the durable commit.

**Structural fix direction (for the spec, not implemented here):** bind (a)+(b)+(c)
into one unit — either defer the durable `done` commit until AFTER target
advancement + bookkeeping commit succeed, OR make rollback git-aware (revert the
coordination-branch `done` commit when target did not advance), AND make resume
DERIVE progress from the durable committed events (dedup against the committed
branch ref, `status_transition.py:682-693`, not the revertible worktree) rather
than from the byte-restored `MergeState.completed_wps`.

---

## 4. Shared root with #2709?

**Verdict: same architectural family, two distinct defects at two distinct code
sites. Fix them together as one "reconciling, transactional merge core," but they
are not one bug.**

- **#2709** (squash overwrites target-newer artifacts) lives in the integration
  strategy: `src/specify_cli/lanes/merge.py:400-402`
  ```python
  ["git", "merge", "--squash", "-X", "theirs", source_branch]
  ```
  `-X theirs` makes the mission branch unconditionally authoritative, blindly
  clobbering any target-side-newer `kitty-specs/` content. This is a **content
  merge that refuses to reconcile with current target state** — it treats the
  target as a passive overwrite destination.

- **#2711** (this lens) lives in the rollback/resume coherence path
  (`executor.py:399-412`, `bookkeeping_projection.py:217-233`,
  `done_bookkeeping.py:285/525`, `status_transition.py:680-681`). This is a
  **status/state transaction that refuses to reconcile with the durable committed
  branch** — it reverts and re-derives from working copies instead of the git
  authority.

**Shared root:** both stem from a merge core that treats the target/committed
branch as passive and non-authoritative — it neither reconciles content against
target-newer state (#2709) nor reconciles status/progress against the durable
committed event log (#2711). There is no reconciliation boundary that reads
"what is actually committed on the branch" as the source of truth.

**Evidence they are distinct, not one symptom:**
- Different modules/functions with no shared call path (`lanes/merge.py`
  strategy vs `merge/executor.py` rollback + `coordination/status_transition.py`
  read contract).
- #2709 reproduces on a *successful* squash (data loss on the happy path);
  #2711 reproduces only on a *failed* target advancement + resume.
- Fixing `-X theirs` does nothing for the committed-vs-working `done` divergence,
  and making rollback git-aware does nothing for the content clobber.

---

## 5. Red-first repro entry point (ATDD)

**Pre-existing entry point to drive:** `_run_lane_based_merge(...)` — the same
seam the merge command and every recovery test already use.
`from specify_cli.cli.commands.merge import _run_lane_based_merge`
(re-exported from `executor.py` via `cli/commands/merge.py:142-143`). Resume is
driven by re-invoking `_run_lane_based_merge` with a pre-seeded `MergeState`
(auto-detect at `cli/commands/merge.py:476-478`) or `--resume` via
`_dispatch_resume` (`cli/commands/merge.py:350-383`).

**How to inject the post-commit target-advancement failure deterministically:**
The `done` commit happens in `_phase_bake_and_pre_target_done`
(coord-topology pre-target path); the failure must land in the very next phase,
`_phase_mission_to_target`. Patch the target-integration call to raise AFTER the
`done` events are committed:

```python
with patch(
    "specify_cli.merge.executor.integrate_mission_into_target",
    side_effect=RuntimeError("injected target-side collision"),
):
    with pytest.raises(typer.Exit):
        _run_lane_based_merge(repo, slug, push=False, delete_branch=False,
                              remove_worktree=False, strategy=MergeStrategy.SQUASH)
```

This forces the `executor.py:490` `_restore_pre_target_if_at_baseline` rollback
after the coord-branch `done` commit already landed. The test then asserts the
COHERENCE contract that currently fails:

1. **Committed vs working coherence** — `git show <coord-branch>:...status.events.jsonl`
   (committed) must NOT contain `done` while the working `status.events.jsonl`
   shows `approved`. (This is the divergence in §1.)
2. **Resume derives from durable events** — re-invoke `_run_lane_based_merge`
   and assert the banner does NOT print `0/N` and that NO duplicate `done`
   event is appended to the coordination branch (`git log`/event-count on the
   branch ref, not the worktree).

To assert coord-topology (so `done_marked_before_target` is True) the fixture
must materialize a coordination worktree / `coordination_branch` in `meta.json`,
not just a flat mission — the flat path takes the post-target branch instead.

**Existing harness/fixtures to extend (do not hand-roll):**
- `tests/integration/test_merge_resume.py` — drives `_run_lane_based_merge`
  against a real git repo (`@pytest.mark.git_repo`, `@pytest.mark.non_sandbox`),
  builds `MagicMock` lane manifests via `_make_manifest`, seeds state with
  `save_state(MergeState(...))`, and already pins the resume idempotence /
  partial-progress contracts. Best home for the resume-no-duplicate assertion.
- `tests/merge/test_merge_recovery.py` — MergeState lifecycle, the
  `_mark_wp_merged_done` dedup guard (T003), and the resume/abort CLI paths (T004).
- `tests/lane_test_utils.py` — `write_mission_meta` helper for seeding
  `meta.json` (needed to declare coordination topology).
- `tests/merge/test_merge_done_recording.py` and
  `tests/merge/test_merge_post_merge_invariant.py` — closest existing coverage
  of the done-recording + post-merge invariant surfaces this bug crosses.

Gap: none of these currently inject a *post-done-commit target failure* and then
assert committed-vs-working coherence + no-duplicate-on-resume — that is the
missing red test.
