---
work_package_id: WP09
title: Review-cycle eviction (both halves)
dependencies:
- WP01
- WP03
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-opus-4-8
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/artifacts.py
create_intent:
- tests/regression/test_2684_review_override_recognition.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_materialization.py
- src/specify_cli/review/artifacts.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- tests/regression/test_2684_review_override_recognition.py
role: implementer
tags: []
shell_pid: "2715927"
shell_pid_created_at: "1784462196.63"
---

# Work Package Prompt: WP09 – Review-cycle eviction (both halves)

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro`

Load the `python-pedro` profile before touching any code. TDD (red-green-refactor), type hints on all
public APIs, pytest/ruff/mypy quality gate. Do NOT redesign the event, the delta, or the `review`
snapshot slot — those are OWNED by WP01. This WP is a **consumer** that migrates BOTH halves of the
`review_artifact_override_*` state as a matched pair.

## Objective

Evict `review_artifact_override_*` review-cycle state from artifact frontmatter into the event log **as
a matched write+read pair** (FR-009). The critical correctness property: migrating only the write while
the merge gate still reads artifact frontmatter would silently stop recognizing overrides and **falsely
block merge**. Both halves move together, into the `review` snapshot slot (owned by WP01).

1. **T033** — Event-source the **write** half (`tasks_materialization.py`
   `_persist_review_artifact_override` at `:46-67` and the coord mirror
   `_persist_review_artifact_override_in_coord` at `:70-135`): emit one `InnerStateChanged` `review`
   delta instead of stamping frontmatter, and **collapse the primary/coord mirror duplication into that
   single emit**.
2. **T034** — Migrate the **read** half (`review/artifacts.py` — the `ReviewCycleArtifact` override
   fields `:104-136,:181-194` and `has_complete_override` `:108-115`) **and the merge-gate override
   recognition** (`latest_review_artifact_verdict` `has_override` `:318`;
   `rejected_review_artifact_for_terminal_lane` `:322-340`; consumed by
   `find_rejected_review_artifact_conflicts`, read by the merge lane gate
   `cli/commands/review/_lane_gate.py:54`) to resolve the override from the `review` snapshot slot. This
   also includes the **orphaned post-merge reader** `post_merge/review_artifact_consistency.py` (now
   **owned** by this WP — OWNERSHIP CHANGE), which reads `has_complete_override` from frontmatter and
   must migrate to the `review` snapshot slot as part of the same both-halves pair (otherwise it becomes
   a stranded second read path).
3. **T035** — Override-recognition regression as a **net-new owned test**
   `tests/regression/test_2684_review_override_recognition.py` (added to `owned_files` + `create_intent`;
   it was homeless in the original slice): a rejected artifact carrying a complete approval override does
   **not** falsely block merge — the terminal-lane consistency gate honors the event-sourced override
   exactly as it honored the frontmatter one (#1924 preserved).

## Context

**Design of record**: ADR 2026-07-19-1 (see also IC-05 in `plan.md`). **Requirements**: FR-009 (evict
all review-cycle state; `review_artifact_override_*` as a matched both-halves pair; collapse the coord
mirror; the legacy verdict-field fallbacks `workflow_cores.py:340-348` / `done_bookkeeping.py:104-105`
are deleted only **after** WP03's backfill seeds legacy approvals — those deletes are WP10, NOT here).
**Constraints**: C-002 (typed `review` delta, never a free dict), C-001 (write↔read switch atomic per
field — for review this is *intrinsic*: the pair MUST switch together or the merge gate breaks), C-006.
**Success criteria**: SC-004 (review render matches a golden, covers verdict/ref/result classes).

This both-halves requirement is the **randy-reducer HIGH blocker** folded into the spec (spec.md
post-spec review): "FR-009 now migrates the `review_artifact_override_*` read half + merge gate, not
just the write." The plan (IC-05) makes this WP depend on **WP01** specifically for the `review`
snapshot slot — "otherwise a second read path = #2093 violation." Do not create a parallel event-read
path; the merge gate reads the reduced snapshot.

**Key facts (grounded):**

- **Write half.** `_persist_review_artifact_override` (`tasks_materialization.py:46-67`) stamps four
  scalars onto artifact frontmatter: `review_artifact_override_at` (`:58`), `_actor` (`:59`), `_wp_id`
  (`:60`), `_reason` (`:61`), then `write_text_within_directory(...)`. The coord mirror
  `_persist_review_artifact_override_in_coord` (`:70-135`) resolves the coord-worktree artifact via the
  SAME `_artifact_dirs_for_wp` and stamps the identical four scalars (`:125-128`) — pure duplication to
  keep the primary and coord copies in sync for the merge gate. **Event-sourcing collapses this
  mirror**: one emit is authoritative for both worktrees (the snapshot is topology-resolved), so the
  coord-stamp helper is deleted, not ported.
- **Read half.** `ReviewCycleArtifact` carries `override_actor`/`override_reason` (`:104-105`), parses
  them tolerantly from frontmatter (`:181-194`), round-trips them on write (`:133-136`), and exposes
  `has_complete_override` (`:108-115`, truthy iff both actor and reason are non-blank).
- **Merge-gate recognition.** `latest_review_artifact_verdict` sets `has_override=
  artifact.has_complete_override` (`:318`); `rejected_review_artifact_for_terminal_lane` (`:322-340`)
  treats a rejected artifact as **NOT a conflict** when `state.has_override` is true (`:338`, the #1924
  honor-the-override rule). `find_rejected_review_artifact_conflicts` aggregates these, and the merge
  lane gate consumes it at `cli/commands/review/_lane_gate.py:54`. **This is the recognition that must
  read the event-sourced override, or merge falsely blocks.**
- **WP01 owns the `review` snapshot slot + fold.** The `WPInnerStateDelta.review: ReviewOverride?`
  field (replace rule, data-model.md) and the snapshot `review` slot are landed by WP01. The
  `ReviewOverride` shape is exactly **`ReviewOverride {at, actor, wp_id, reason}`** (all four fields),
  and its **`complete` predicate is true iff all four are present/non-blank** — use these exact WP01
  names, not `reviewer`/synonyms. Call `emit_inner_state_changed` with a `review` delta carrying that
  shape.
- **WP03 owns backfill.** Legacy on-disk approvals are seeded as events by WP03's backfill; the fallback
  deletes that depend on that seeding are WP10. Here you migrate the live read to the snapshot with the
  frontmatter fallback retained behind the FR-005 flag until WP03's verify passes (C-001).

### Subtask T033 — Event-source `review_artifact_override_*` write half + collapse coord mirror

**Purpose**: Replace the two frontmatter-stamping helpers with a single `InnerStateChanged` `review`
emit; the coord mirror duplication disappears because the snapshot is the single topology-resolved
authority.

**Steps**:
1. In `tasks_materialization.py::_persist_review_artifact_override` (`:46-67`), replace the
   `set_scalar(...)` frontmatter stamps (`:58-61`) + `write_text_within_directory(...)` (`:62-67`) with
   a call to WP01's `emit_inner_state_changed` carrying a `review` delta
   (the `ReviewOverride {at, actor, wp_id, reason}` shape — all four fields). Resolve the emit's `destination_ref`
   from the stored-topology target (the same `repo_root`/feature-dir the caller already resolves), never
   `Path.cwd()` (C-003).
2. **Delete** `_persist_review_artifact_override_in_coord` (`:70-135`) entirely. Its sole purpose was to
   mirror the stamp into the coord worktree so the merge gate (which reads coord artifacts) would see the
   override; once the override is event-sourced and the merge gate reads the snapshot (T034), the mirror
   is dead. Remove its call site in the approval handler. Grep for any other caller first.
3. Preserve the approval-handler behavior: the override still records "a rejected latest review was
   superseded" — only the *storage* changes from artifact frontmatter to an event. Do not change *when*
   the override fires.

**Files**: `src/specify_cli/cli/commands/agent/tasks_materialization.py`.

**Validation**: drive an approval-override; assert (a) the artifact file is byte-unchanged (no
`review_artifact_override_*` frontmatter written), (b) a `review` `InnerStateChanged` event is
persisted, (c) the reduced snapshot's `review` slot carries the override, (d) no coord-mirror write
occurs. This subtask MUST land together with T034 — a write-only landing breaks the merge gate.

**Edge cases**: The override may fire when only a coord artifact (not a primary) exists, or vice versa —
the old mirror existed exactly to cover both. The event-sourced override is topology-resolved and
authoritative for both, so this asymmetry vanishes; assert the override is recognized regardless of which
worktree the approval ran from. Do NOT leave a half-collapsed mirror (primary emit + coord stamp) — that
reopens the duplication.

### Subtask T034 — Migrate read half + merge-gate override recognition → `review` snapshot slot

**Purpose**: Make override recognition read the event-sourced `review` slot so the merge gate honors
event-sourced overrides. This is the half that, if omitted, causes false merge blocks.

**Steps**:
1. Re-point `latest_review_artifact_verdict` (`review/artifacts.py`, `:318`) so `has_override` derives
   from the reduced snapshot's `review` slot for the WP, not `artifact.has_complete_override` (the
   frontmatter parse). Keep the frontmatter parse behind the FR-005 fallback flag until WP03's verify
   passes (C-001 migration window) — a snapshot-first read with a tolerated legacy fallback, not a hard
   cutover that strands un-migrated on-disk artifacts.
2. `rejected_review_artifact_for_terminal_lane` (`:322-340`) already gates on `state.has_override`
   (`:338`) — once `has_override` is snapshot-sourced, this gate honors event-sourced overrides with no
   further change. Confirm the data flow: `find_rejected_review_artifact_conflicts` → the merge lane gate
   (`cli/commands/review/_lane_gate.py:54`) now sees the event-sourced override.
3. The `ReviewCycleArtifact` override fields (`:104-105`) and `has_complete_override` (`:108-115`) may
   remain as a **legacy-parse fallback** during the migration window, but they are no longer the
   authority. Once WP10 deletes the fallbacks (post-backfill), these become dead — do not delete them
   here (that is gated on WP03 backfill + WP10). Do NOT keep them as a *second authority* — the snapshot
   is the single authority; the frontmatter parse is a tolerated migration-window fallback only (FR-013:
   distinguish authority-read from migration-window fallback-read).
4. **Migrate the newly-owned post-merge reader** `post_merge/review_artifact_consistency.py`: it reads
   `has_complete_override` off artifact frontmatter today. Re-point its override recognition to the
   `review` snapshot slot (same snapshot-first-with-flagged-fallback posture as `artifacts.py`), so the
   post-merge consistency check honors event-sourced overrides. This reader is the **third leg of the
   both-halves pair** — leaving it on the frontmatter parse strands a second read path (#2093) and can
   surface a post-merge false-inconsistency. Use the same `ReviewOverride` shape and `complete` predicate
   as the merge-gate migration (step 1-2); do not introduce a parallel event-read path.

**Files**: `src/specify_cli/review/artifacts.py`,
`src/specify_cli/post_merge/review_artifact_consistency.py` (now owned).

**Validation**: with an event-sourced override in the snapshot and NO override in artifact frontmatter,
assert `latest_review_artifact_verdict(...).has_override` is true and
`rejected_review_artifact_for_terminal_lane(...)` returns `None` (not a conflict) for a terminal lane —
i.e. the merge gate does not block. Two-sided: a rejected artifact with **no** override (neither
frontmatter nor snapshot) still IS a conflict.

**Edge cases**: `post_merge/review_artifact_consistency.py` also references `has_complete_override` (grep
hit) — it is **now owned** by this WP (OWNERSHIP CHANGE) and is migrated to the `review` snapshot slot in
step 4 as the third leg of the both-halves pair; it is no longer a "do-not-edit / WP10 follow-up" — do
the migration here so no stranded frontmatter read survives. The merge lane gate `_lane_gate.py:54`
remains NOT owned — confirm it consumes `find_rejected_review_artifact_conflicts` unchanged (you change
the recognition *inside* `artifacts.py` / `review_artifact_consistency.py`, not the gate's call).

### Subtask T035 — Override-recognition regression (no false merge block)

**Purpose**: Pin the both-halves property: an event-sourced complete override on a rejected latest
review does NOT falsely block merge, exactly as a frontmatter override did (#1924 preserved).

**Steps**:
1. Author a regression that: drives a review to `rejected`, then an approval-override (T033 emit), then
   evaluates the terminal-lane merge gate for an approved/done lane; assert the WP is **not** flagged as
   a review-artifact conflict (merge is not blocked) and that the resolution came from the `review`
   snapshot slot, not an artifact-frontmatter read.
2. Negative control: a `rejected` review with **no** override → the gate DOES flag it (merge blocked) —
   proving the test can fail and the gate still refuses genuinely-unresolved rejections.
3. Mark it `regression` (and `git_repo`/`integration` as the fixture requires).

**Files**: `tests/regression/test_2684_review_override_recognition.py` (**create** — now an owned test
file, added to both `owned_files` and `create_intent`). This regression was homeless in the original
slice; it is now a **net-new owned test**. Author the assertions here — do NOT scatter them into an
existing review module.

**Validation**: red before T033/T034 (frontmatter-only recognition ignores the event override → false
block), green after (snapshot recognition honors it); the negative control stays red-refuses.

**Edge cases**: An override that is *incomplete* (missing any of `at`/`actor`/`wp_id`/`reason`) must NOT
be honored — WP01's `ReviewOverride` **`complete` predicate is all-four-present**, mirroring the legacy
`has_complete_override` (`:108-115`); preserve that predicate on the `ReviewOverride`/snapshot side. A
partial override still blocks merge.

## Branch Strategy

`lane-per-wp`. Planning artifacts were generated on
`mission-prep/2684-wp-runtime-state-eviction`; completed changes merge back into
`mission-prep/2684-wp-runtime-state-eviction`. Depends on **WP01** (the `review` snapshot slot, the
`ReviewOverride` delta + replace fold — IC-05 requires this or the read half becomes a #2093 second
read path) and **WP03** (backfill seeds legacy approvals; the fallback deletes it enables are WP10, not
here). Rebase onto both before starting. Runs in the parallel band with {WP05, WP06, WP07, WP08} after
WP01+WP02+WP03. The legacy verdict-field fallback deletes (`workflow_cores.py:340-348`,
`done_bookkeeping.py:104-105`) are **WP10**, gated on WP03 backfill — do NOT delete them here.

## Definition of Done

- [ ] The write half emits one `InnerStateChanged` `review` delta; `_persist_review_artifact_override`
      no longer stamps frontmatter; `_persist_review_artifact_override_in_coord` is **deleted** (mirror
      collapsed to the single topology-resolved emit).
- [ ] The read half + merge-gate recognition (`has_override`,
      `rejected_review_artifact_for_terminal_lane`) **and the now-owned post-merge reader**
      `post_merge/review_artifact_consistency.py` resolve the override from the `review` snapshot slot
      (`ReviewOverride {at, actor, wp_id, reason}`, `complete` = all-four), with the frontmatter parse
      retained ONLY as an FR-005-flagged migration-window fallback (single authority, not dual). No
      stranded frontmatter override-read survives across the both-halves pair.
- [ ] Regression lands as the **net-new owned** `tests/regression/test_2684_review_override_recognition.py`
      (added to `owned_files` + `create_intent`) and proves an event-sourced complete override does NOT
      falsely block merge; the negative control (no override) still blocks; an incomplete override
      (missing any of the four fields) still blocks.
- [ ] `destination_ref` for the review emit resolves from stored topology, never `Path.cwd()` (C-003).
- [ ] Full quality gate green: `pytest`, `ruff`, `mypy`; no dead imports; both halves land together.

## Risks

- **Write-only eviction breaks the merge gate (the headline FR-009 risk).** If T033 lands without T034,
  the merge gate keeps reading artifact frontmatter, no longer finds the override, and falsely blocks
  merge. Mitigate: land both halves in one WP/PR; the regression T035 pins it.
- **Second read path = #2093 violation.** If the read half reads a parallel event stream instead of the
  reduced `review` snapshot slot, it reintroduces a second authority. Mitigate: read the snapshot only;
  the frontmatter parse is a *fallback*, not a co-authority.
- **Coord mirror half-collapse.** Emitting the primary but still stamping the coord artifact leaves the
  duplication FR-009 targets. Mitigate: delete `_persist_review_artifact_override_in_coord` outright and
  confirm no caller remains.
- **Non-owned consumers.** `post_merge/review_artifact_consistency.py` is **now owned** (OWNERSHIP
  CHANGE) and migrated in T034 step 4 — do not leave it on the frontmatter parse. Only `_lane_gate.py`
  remains non-owned; confirm it consumes `find_rejected_review_artifact_conflicts` unchanged rather than
  editing it.
- **Test ownership gap — RESOLVED.** The regression was homeless in the original slice; ownership is now
  extended: `tests/regression/test_2684_review_override_recognition.py` is a net-new owned test in both
  `owned_files` and `create_intent`. Author it there; do not scatter assertions elsewhere.

## Reviewer guidance

- Verify **both halves landed together** — the single most important property. A diff that changes the
  write without the read is a hard reject (false-merge-block regression).
- Confirm `_persist_review_artifact_override_in_coord` is deleted, not ported — the mirror collapse is a
  named FR-009 deliverable.
- Confirm the read half reads the `review` snapshot slot as the single authority; the frontmatter parse
  survives only as an FR-005-flagged, WP03-verify-gated migration-window fallback (and is deleted by
  WP10, not here).
- Check the regression is two-sided (honors an event override; still blocks with no override; still
  blocks an incomplete override) — proof-of-drive, not proof-of-absence.
- Confirm the regression landed as the net-new owned
  `tests/regression/test_2684_review_override_recognition.py` (ownership extended deliberately in this
  triage — it is in `owned_files` + `create_intent`), not scattered into an existing module.
- Confirm `post_merge/review_artifact_consistency.py` (now owned) was migrated to the `review` snapshot
  slot as the third leg of the both-halves pair — no stranded frontmatter override-read. Only
  `_lane_gate.py` remains out of scope; confirm it consumes `find_rejected_review_artifact_conflicts`
  unchanged rather than being edited.
- Confirm the `ReviewOverride {at, actor, wp_id, reason}` shape and its `complete` = all-four predicate
  are used by the exact WP01 names on both the write and every read leg.

## Activity Log

- 2026-07-19T11:21:41Z – claude:opus:python-pedro:implementer – shell_pid=2548429 – Assigned agent via action command
- 2026-07-19T11:54:59Z – claude:opus:python-pedro:implementer – shell_pid=2548429 – Ready: review override both-halves event-sourced, coord mirror collapsed, override-recognition regression green
- 2026-07-19T11:56:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=2715927 – Started review via action command
- 2026-07-19T12:04:00Z – user – shell_pid=2715927 – Review passed (reviewer-renata): both-halves invariant satisfied. Write half (T033) is a single topology-resolved InnerStateChanged review emit (feature_dir=parents[2], repo_root passed, never Path.cwd()); _persist_review_artifact_override_in_coord DELETED with call site+import removed. Read half (T034): zero live frontmatter override writers remain (only WP03 strip/backfill tooling + FR-005 round-trip fallback reader); all three read legs resolve from the review snapshot slot snapshot-first with flagged frontmatter fallback: artifacts.py (has_override=snapshot_complete or frontmatter), review_artifact_consistency.py (_snapshot_review_override -> rejected_review_artifact_for_terminal_lane), and _lane_gate.py:54 unchanged via find_rejected_review_artifact_conflicts which materializes the snapshot per-WP. T035 regression is three-sided and non-vacuous (positive asserts artifact carries NO override frontmatter so recognition must be snapshot-sourced; genuine-absent blocks; incomplete/blank-reason blocks via all-four complete predicate). 39+74 tests green, ruff+mypy clean. MERGE-COORDINATION NOTE FOR WP06: WP09 edited _mt_fire_override_persist (tasks_move_task.py ~L574-595, removed dead coord call+import); WP06 T022 cuts _mt_persist_wp_file (~L1751) - distinct functions ~1150 lines apart, and WP06 task has zero mention of _mt_fire_override_persist/override_persist. Only textual overlap is the tasks_materialization import block at file top (routine 3-way merge, no semantic collision). Deleted WP07 test_approve_over_rejected_coord_artifact.py is legitimate: its subject is the FR-008 coord frontmatter mirror FR-009 evicts (imports the now-deleted _persist_review_artifact_override_in_coord); coverage migrated to T035.
