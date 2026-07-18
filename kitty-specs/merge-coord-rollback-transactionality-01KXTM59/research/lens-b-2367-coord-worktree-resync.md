# Lens B — #2367: `spec-kitty merge` blocked by the coordination worktree

**Author:** Architect Alphonso (architect-alphonso profile)
**Mode:** READ-ONLY pre-spec research. No product code edited.
**Directives applied:** 001 (Architectural Integrity — component boundaries/ownership), 003 (Decision Documentation), 031 (Context-Aware Design — the coord worktree is a bounded context with its own write authority), 043 (Close Defect Classes by Construction — the fix must make partial coord state *unrepresentable*, not remind an operator to hand-fix), 044 (Canonical Sources and Unification — one classifier for "spec-kitty-owned churn", one transactional boundary).

Issue: `Priivacy-ai/spec-kitty#2367` (P0, child of #2392, sibling of CLOSED #1826). Two distinct mechanisms, both real-witnessed on mission `ci-suite-map-bind-01KWNPMP`.

---

## 1. The coord-worktree resync guard (#1826 / NFR-002)

**Canonical site:** `src/specify_cli/git/ref_advance.py` — `advance_branch_ref()` is *the single sanctioned way* the merge pipeline advances a branch ref (an architectural ratchet, `tests/architectural/test_merge_pipeline_ratchets.py` AC-B3, forbids raw `update-ref` anywhere else in `src/specify_cli`).

**How it decides "dirty" and refuses:** `_dirty_entries()` (lines 167–211) runs `git status --porcelain --ignored` in every worktree that has the advanced branch checked out, BEFORE the ref moves (atomic refusal, lines 284–301). Any staged/unstaged entry against a *tracked* path is unconditionally treated as local state and appended to `dirty`; untracked/ignored entries are dirty only if they obstruct a target-tree path. If `dirty` is non-empty it raises `RefAdvanceDirtyWorktreeError` (lines 66–100) — the exact "uncommitted local changes that a resync (`git reset --hard`) would destroy (#1826 / NFR-002)" message from the issue. Nothing is mutated on refusal.

**The one escape hatch that already exists:** `advance_branch_ref(..., coord_owned_filenames=frozenset)` → passed to `_dirty_entries(excluded_filenames=...)` (lines 203–204). Merge callers in `src/specify_cli/lanes/merge.py:675` and `:710` pass `COORD_OWNED_STATUS_FILES`. **Critically, that set is only `{status.events.jsonl, status.json}`** (`src/specify_cli/status/__init__.py:210`) — and the exclusion (line 203) applies **only to untracked/ignored `??`/`!!` lines**, not to *tracked-file* modifications. This is the seam both mechanisms fall through.

---

## 2. Mechanism A — uncommitted VCS-lock at claim (tool-churn, not user work)

**Write site:** `src/specify_cli/cli/commands/implement.py:1009` — on first claim, if `"vcs" not in meta`, `set_vcs_lock(feature_dir, vcs_type="git", locked_at=now_iso)` (`src/specify_cli/mission_metadata.py:512`) writes `vcs` + `vcs_locked_at` into `meta.json` via `write_meta`. This is a one-time **VCS-TYPE** lock (which VCS backend), NOT the concurrency mutex — pure tool-generated metadata. It is **not auto-committed** at claim; under `auto_commit=False` it lingers as an uncommitted tracked-file diff.

**Why it trips the resync guard:** `meta.json` is a tracked file. At merge time `advance_branch_ref` → `_dirty_entries` sees the modified `meta.json` and, because the exclusion set contains only the two status filenames (and only excludes untracked lines anyway), lists it as dirty → refusal → merge blocked. The operator had to hand-commit `meta.json` in the coord worktree to unblock.

**The canonical classifier already exists — but only on the claim side.** `src/specify_cli/cli/commands/implement_cores.py` already solved the *symmetric* problem for the next claim's dirty-tree guard: `_is_vcs_lock_only_meta_diff()` (line 216) is a pure predicate — "is every changed key a member of `_VCS_LOCK_META_FIELDS = {vcs, vcs_locked_at}`?" — and `_drop_vcs_lock_only_meta()` (line 315, #2222 / C-003) drops a lock-only diff from the claim guard while keeping any genuine meta edit blocking. **The merge-side resync guard does not know about this classifier.** That is the directive-044 gap: two guards (claim vs merge) over the *same* tool-churn class, only one of which recognizes it.

**Architectural options (for the spec, not decided here):** (a) auto-commit the VCS-TYPE lock at claim onto the coord/planning surface (it is tool metadata — commit it the moment it is written, closing the class by construction, directive 043); OR (b) teach `advance_branch_ref` to recognize spec-kitty-owned churn by threading a *classifier*, not a *filename set* — reuse `_is_vcs_lock_only_meta_diff` as the single canonical "is this a lock-only meta diff" authority so a genuine user meta edit still blocks. (a) is structurally stronger (no uncommitted tool state ever exists); (b) generalizes the escape hatch from "filenames" to "owned-churn predicate".

---

## 3. Mechanism B — non-transactional rollback of the coord status write-set

**Write path (per-WP, N independent commits):** `src/specify_cli/merge/done_bookkeeping.py::_record_merged_wps_done_for_merge` (line 611) loops every WP and calls `_mark_wp_merged_done` (line 229), which calls `emit_status_transition_transactional` (up to twice per WP: an `approved` replay + the `done`). Each such call opens its **own** `BookkeepingTransaction.acquire(...)` and **commits to the coordination branch** (`coordination/status_transition.py:859,948`; `coordination/transaction.py::commit`). So the merge's "coord write set" is a **sequence of N separate committed transactions**, not one atomic unit.

**Rollback path (parallel, hand-rolled — NOT the canonical transaction):** the executor rolls back via a *separate* mechanism in `src/specify_cli/merge/bookkeeping_projection.py` — `_capture_bookkeeping_snapshots` / `_restore_final_bookkeeping_snapshots` (byte snapshot+restore of the working-tree status files) — invoked at ~6 exception exits in `src/specify_cli/merge/executor.py` (`_restore_pre_target_if_at_baseline`, lines 517–536, and the `_phase_*` handlers). **This is a second, parallel rollback engine that duplicates `BookkeepingTransaction._rollback`'s job** (directive 044 violation): the transaction already owns surgical truncate + byte-snapshot restore, but the merge cannot use it because the writes were committed by N *already-closed* transactions.

**Relation to the just-merged #2711 (Option A):** #2711 added `_revert_coord_done_commit` (`executor.py:458`) + `_capture_pre_target_coord_ref_sha` (line 411): it captures the coord-branch tip BEFORE the pre-target `done` emit and, on a target-advance rollback, `git revert`s `{captured}..HEAD` on the coord worktree so the *committed* `done` is coherently reversed in lockstep with the working-byte restore (avoiding the "committed `done` vs rolled-back `approved`" split-brain). **#2367 is the same non-transactional root, one level up.** #2711 makes the *committed done commit(s)* revertible; it does **not** make the *whole coord write-set* one atomic boundary. The residue the issue witnessed — stale `status.events.jsonl`/`status.json` emissions left in the coord worktree after an aborted run, forcing a manual `git checkout --` before `--resume` — is exactly what a per-write-set transaction (open once, commit once, roll back once) would prevent. #2711 patched the symptom for the `done` commit; the class stays open for the rest of the set (`approved` replays, partial mid-loop failures, the working-tree emissions before the coord commit).

---

## 4. Ownership / seam verdict

- **Coord status-write transactionality is ALREADY OWNED** by `src/specify_cli/coordination/transaction.py::BookkeepingTransaction` — self-described as "the single owner of writes that target the coordination branch … acquire → policy gate → append → materialize → commit → outbound → release" with surgical-truncate + byte-snapshot rollback (C-009: never `git checkout --`). **The merge does not route its multi-WP coord write-set through a single instance of it.** It opens N short-lived transactions (one per emit) and then bolts a *parallel* snapshot/revert engine (`bookkeeping_projection.py` + `_revert_coord_done_commit`) on top to undo them. That parallel engine is the architectural smell (044).

- **Coord-worktree cleanliness is owned by** `src/specify_cli/git/ref_advance.py::advance_branch_ref`, whose dirty-vs-clean decision is a **filename-exclusion set** (`COORD_OWNED_STATUS_FILES`), not a **tool-churn classifier**. It has no knowledge of `_is_vcs_lock_only_meta_diff` (the claim-side authority for the same question). Two guards, one class of churn — the 044 gap for Mechanism A.

- **Is there ONE transactional boundary that makes coord writes + resync atomic and tool-churn-aware? Today: no.** The pieces exist but are not composed: (1) `BookkeepingTransaction` (real transaction, but per-emit and not spanning the merge loop); (2) `bookkeeping_projection` snapshots (parallel rollback); (3) `_revert_coord_done_commit` (#2711 point-fix for the committed `done`); (4) `advance_branch_ref` filename exclusion (cleanliness gate). The architecturally coherent target is a **single merge-scoped coordination transaction** that (a) spans the entire done/approved write-set for the mission (open once, commit once, roll back once — folding #2711's revert and the projection snapshots into `BookkeepingTransaction`'s own rollback so the parallel engine is retired, 044), and (b) shares ONE "spec-kitty-owned churn" classifier with `advance_branch_ref`'s dirty gate (retiring the filename-set escape hatch in favor of the `_is_vcs_lock_only_meta_diff`-style predicate, so tool-churn is auto-resolved while genuine user edits still refuse — 043 + 044). That single boundary is the seam #2367 is really asking for; #2711 is a down-payment on it, not the whole thing.

### Key code sites (absolute paths)
- Resync guard: `/home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine/src/specify_cli/git/ref_advance.py` (`_dirty_entries` 167–211; `advance_branch_ref` 214–320; `RefAdvanceDirtyWorktreeError` 66–100)
- Exclusion set: `/home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine/src/specify_cli/status/__init__.py:210` (`COORD_OWNED_STATUS_FILES`)
- Merge callers of the guard: `/home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine/src/specify_cli/lanes/merge.py:675,710`
- VCS-lock write: `/home/stijn/.../src/specify_cli/cli/commands/implement.py:1009`; `/home/stijn/.../src/specify_cli/mission_metadata.py:512`
- Claim-side tool-churn classifier: `/home/stijn/.../src/specify_cli/cli/commands/implement_cores.py:216` (`_is_vcs_lock_only_meta_diff`), `:315` (`_drop_vcs_lock_only_meta`), `:51` (`_VCS_LOCK_META_FIELDS`)
- Canonical coord transaction: `/home/stijn/.../src/specify_cli/coordination/transaction.py` (`BookkeepingTransaction`; `_rollback` 1145–1212)
- Merge done write-set: `/home/stijn/.../src/specify_cli/merge/done_bookkeeping.py:611` (`_record_merged_wps_done_for_merge`), `:229` (`_mark_wp_merged_done`)
- Parallel rollback engine: `/home/stijn/.../src/specify_cli/merge/bookkeeping_projection.py` (`_capture_bookkeeping_snapshots` 202, `_restore_final_bookkeeping_snapshots` 217)
- #2711 Option-A point-fix: `/home/stijn/.../src/specify_cli/merge/executor.py:411` (`_capture_pre_target_coord_ref_sha`), `:458` (`_revert_coord_done_commit`), `:517` (`_restore_pre_target_if_at_baseline`)
