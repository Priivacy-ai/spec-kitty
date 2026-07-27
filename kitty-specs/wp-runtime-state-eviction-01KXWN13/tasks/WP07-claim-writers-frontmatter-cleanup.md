---
work_package_id: WP07
title: Claim writers + frontmatter cleanup (FR-014)
dependencies:
- WP01
- WP03
requirement_refs:
- FR-004
- FR-006
- FR-008
- FR-010
- FR-014
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T029a
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/frontmatter.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_implement_runtime_frontmatter_claim.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/frontmatter.py
- tests/specify_cli/core/test_shell_pid_claim_baseline.py
- tests/specify_cli/cli/commands/agent/test_implement_runtime_frontmatter_claim.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py
role: implementer
tags: []
shell_pid: "2792311"
shell_pid_created_at: "1784463133.39"
---

# Work Package Prompt: WP07 – Claim writers + frontmatter cleanup (FR-014)

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro`

Load the `python-pedro` profile before touching any code. It sets the TDD (red-green-refactor)
discipline, the type-hint-on-public-API rule, and the full quality gate (pytest, ruff, mypy) you run
before handoff. Do NOT make architectural decisions here — the `InnerStateChanged` event, the reducer
fold, and the `policy_metadata`→snapshot claim path are all defined and OWNED by WP01. This WP consumes
that foundation; it does not redesign it.

## Objective

Cut the `shell_pid` claim writers over to the event log and delete the frontmatter machinery the cut
orphans. Concretely:

1. **T026/T027** — Stop writing `shell_pid` (and its baseline / `agent`) into `tasks/WP##.md`
   frontmatter at claim time. Instead, the `(shell_pid, shell_pid_created_at, agent)` triple **rides
   the real `planned→claimed` (and `for_review→in_review`) lane transition via the existing
   `policy_metadata` sidecar** — no new wire schema, no new event for the claim path (FR-004). WP01's
   reducer extracts those keys from `policy_metadata` into the snapshot slots.
2. **T028** — Delete the now-orphaned `frontmatter.py::write_shell_pid_claim` /
   `write_shell_pid_claim_to_file` and `frontmatter.py::add_history_entry` (module fn + manager
   method), remove their `__all__` exports, and re-point the orphaned baseline tests. **WP07/T028 is the
   sole owner of the `add_history_entry` deletion** (FR-010) — downstream references (e.g. WP10's
   dead-symbol allowlist reconciliation) must attribute the deletion to WP07/T028, not to WP03/IC-06.
3. **T029** — Strike `tracker_refs` from `FrontmatterManager.WP_FIELD_ORDER` so it is not dual-homed
   (dynamic-in-events per FR-006 AND static-in-frontmatter) — the #2093 no-dual-home invariant.
4. **T029a** — Refresh `shell_pid`/`shell_pid_created_at` on resume/re-claim of an already-`in_progress`
   WP via an `InnerStateChanged` emit (FR-004 / US3). The resume path in `workflow_executor.py` is a
   no-op today; this emit is **owned here**, NOT punted to WP05 (WP05 owns only the reader that consumes
   the refreshed snapshot slot).

This WP **owns the `implement.py` shell_pid-writer restructuring outright (FR-014)**. The former #2160
co-sequence is retired: #2160's writer work is `pr:deferred` and yields (C-006), so there is **no
external `blocks`/`blocked_by` gate** on this cutover. Proceed without waiting on #2160.

## Context

**Design of record**: ADR 2026-07-19-1 (`docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md`).
**Requirements**: FR-004 (claim rides `policy_metadata`), FR-008 (no claim action writes the WP file;
delete the orphaned `write_shell_pid_claim*` tail), FR-014 (this mission owns the `implement.py`
restructuring, no #2160 gate), FR-006 (strike `tracker_refs` from the static schema / `WP_FIELD_ORDER`),
FR-013 (no field dual-homed static+dynamic). **Constraints**: C-002 (typed delta, never a free dict —
you are not defining the delta here, but the `policy_metadata` keys you emit must match WP01's typed
extraction), C-006 (deferred PRs rebase onto this cutover, not the reverse). **Success criteria**:
SC-001 / SC-005 (WP-file content-hash byte-stable across claim), SC-002 (liveness resolves from the
snapshot — this WP removes the frontmatter `shell_pid` that liveness used to read).

**Key facts (grounded):**

- The `planned→claimed` claim transition is emitted by `start_implementation_status(...)` inside
  `workflow_executor.py::_implement_start_claim` (`workflow_executor.py:640`). The review claim
  (`for_review→in_review`) is emitted by `start_review_status(...)` at `workflow_executor.py:1349`.
  **These transition emitters are where the `policy_metadata` sidecar must carry the claim triple.**
- The `policy_metadata` sidecar already exists on the transactional transition API — see the
  BLOCKED-emit precedent `implement.py:1329` (`policy_metadata={"evidence": str(exc)}` on a
  `TransitionRequest`). You are adding `policy_metadata={"shell_pid": ..., "shell_pid_created_at": ...,
  "agent": ...}` to the **claim** transition, which WP01's reducer folds into the snapshot slots.
- **WP01 owns the fold.** Do not implement snapshot extraction here. Confirm with WP01's landed API
  what exact `policy_metadata` key names its `planned→claimed` extraction reads (data-model.md: the
  claim transition "extracts `shell_pid`/`shell_pid_created_at`/`agent` from its `policy_metadata`
  sidecar into the snapshot slots"). Emit those exact keys.
- **WP03 owns backfill + fail-closed verify.** Do not activate the reader cutover for `shell_pid`
  ahead of WP03's per-field verify (C-001). This WP's reader side (`stale_detection`, `WorkPackage.
  shell_pid`) is NOT owned here — it is WP05. WP07 is the **writer** half: it stops the frontmatter
  write and routes the value into `policy_metadata`. Coordinate the atomic switch per C-001; if the
  reader (WP05) has not yet cut over when this lands, keep a bounded dual-write (frontmatter + event)
  rather than stranding a fresh claim write invisible to a snapshot-first reader.

**Path note (read before editing):** `tasks.md` lists the `implement` writer under
`src/specify_cli/cli/commands/agent/implement.py`; the live file is actually
`src/specify_cli/cli/commands/implement.py` (the `agent/` module re-exports the workflow via
`workflow_executor.py`). The frontmatter-writing claim path that `spec-kitty implement` actually drives
is `workflow_executor.py::_implement_write_claim_and_commit` (`:660-709`). Ground your edits in the
live code; the `owned_files` list is reproduced verbatim from `tasks.md` and MUST NOT be widened.

### Subtask T026 — `shell_pid` claim → `policy_metadata` on `planned→claimed` (implement.py, FR-014)

**Purpose**: Route the implementation-claim `(shell_pid, shell_pid_created_at, agent)` triple onto the
`planned→claimed` transition's `policy_metadata` sidecar and stop writing it into WP frontmatter. This
is the FR-014 restructuring this mission owns.

**Steps**:
1. In `workflow_executor.py::_implement_start_claim` (`:596-655`), extend the
   `start_implementation_status(...)` call (`:640`) to pass the claim triple through
   `policy_metadata`. Capture `shell_pid = os.getppid()` (already at `:617`) and a truthful
   `shell_pid_created_at` (use the same creation-time baseline helper the old writer used —
   `specify_cli.core.process_liveness.capture_creation_time_baseline`, best-effort per C-007: omit the
   key when it cannot be captured, never fail the claim). Pass `agent` (the `actor`) as the third key.
2. In `_implement_write_claim_and_commit` (`:660-709`), **delete the frontmatter-writing lines**:
   `set_scalar(updated_front, "agent", agent)` (`:694`), `write_shell_pid_claim(updated_front, ...)`
   (`:695`), and the `history_entry` / `append_activity_log` block (`:697-705`). The lane is already
   event-log-only; after this WP the operational metadata is too. If the helper becomes a pure no-op,
   remove it and its call site rather than leaving a dead shell (extreme campsiting).
3. Verify the claim transition still commits its status artifacts; only the **WP-file mutation** is
   removed. Do not touch the commit/rollback bookkeeping (`_commit_workflow_change`).
4. Honor C-001: if WP05's reader half has not cut over yet, gate the frontmatter-write removal behind
   the FR-005 fallback flag (dual-write) so a fresh claim is never invisible; otherwise cut atomically.

**Files**: `src/specify_cli/cli/commands/agent/workflow_executor.py` (live claim path);
`src/specify_cli/cli/commands/agent/implement.py` (owned per `tasks.md`; the live import at
`cli/commands/implement.py:27` of `write_shell_pid_claim_to_file` and its call at `:1730` are removed
in T028 — reconcile the re-export surface).

**Validation**:
- New/updated `test_implement_runtime_frontmatter_claim.py` (create — see `create_intent`): drive the
  implementation claim through the real entry point; assert the WP file's frontmatter has **no**
  `shell_pid` written by the claim, and that the persisted `claimed` transition carries the
  `shell_pid`/`shell_pid_created_at`/`agent` keys in its `policy_metadata`.
- Content-hash proof-of-drive (SC-001/SC-005): the `tasks/WP##.md` byte hash is unchanged across the
  claim (the WP06 lifecycle-hash test is the mission-level guard; assert the claim-local slice here).

**Edge cases**: `capture_creation_time_baseline` returns `None` (unsupported platform / race) → omit
`shell_pid_created_at`, claim still succeeds (legacy-claim semantics, D3a). A re-claim / resume of an
already-`in_progress` WP is NOT a `planned→claimed` transition — its PID refresh is an
`InnerStateChanged` annotation, **owned here in T029a** (NOT WP05), and is emitted separately from the
`policy_metadata` claim path; do not route a resume through `policy_metadata`.

### Subtask T027 — `workflow_executor` claim writers (`:695`/`:1370`) → `policy_metadata`

**Purpose**: Apply the same cutover to the **review-claim** path so no claim writer remains that mutates
the WP file.

**Steps**:
1. In the review-claim block (`workflow_executor.py:1349` `start_review_status(...)`), pass the claim
   triple via `policy_metadata` on that transition (mirror T026). `shell_pid` is captured at `:1339`.
2. Delete the post-emit frontmatter mutation block `:1366-1374`:
   `set_scalar(updated_front, "agent", agent)`, `write_shell_pid_claim(updated_front, int(shell_pid))`
   (`:1370`), the `history_entry` construction (`:1372-1374`), and the `append_activity_log`
   (`:1376-1377`). Keep the status-artifact commit (`_commit_workflow_change`, `:1384-1399`); it should
   no longer receive the WP file as a changed path if the file is unmutated.
3. Remove the now-unused imports (`write_shell_pid_claim` at `:65`, and `append_activity_log`/
   `set_scalar`/`build_document` if they become unused on this path) — let ruff confirm no dead import.

**Files**: `src/specify_cli/cli/commands/agent/workflow_executor.py`.

**Validation**: repoint/extend `test_tasks_move_task_authority_staging.py` (owned) to assert the review
claim commits **no** WP-file change; the review claim's `in_review` transition carries the claim triple
in `policy_metadata`. Run the full `workflow_executor` claim suite green.

**Edge cases**: The review claim currently also writes an activity-log line — that note is FR-007
Activity-Log content and is owned by other writers (WP08 covers the external writer). Here you are only
removing the WP-file write; do not silently drop the *record* — the claim transition itself is the
provenance, and the reviewer-claim note, if still required, is emitted as a `note` delta by the
owning writer, not re-added to frontmatter.

### Subtask T028 — Delete `write_shell_pid_claim*` + `add_history_entry` + `__all__`; re-point orphaned baseline tests

**Purpose**: Once T026/T027 remove the only callers, the claim-write helpers and the history-append
helper are dead. Delete them and their exports (extreme campsiting — no stub that masks the next dead
symbol).

**Steps**:
1. Delete `frontmatter.py::write_shell_pid_claim` (`:357-390`) and `write_shell_pid_claim_to_file`
   (`:393-408`). Remove their `__all__` entries (`:448-449`). Grep for any surviving caller first
   (`rg 'write_shell_pid_claim'`) — the live caller `cli/commands/implement.py:1730` and its import
   `:27` are removed as part of this cut.
2. Delete `add_history_entry`: the module-level function (`frontmatter.py:347-349`), the
   `FrontmatterManager.add_history_entry` method (`:176-...`), and the `__all__` entry (`:445`). This
   is FR-010's history-writer deletion, and **WP07/T028 is its sole owner** — confirm the
   zero-reader/zero-writer verification (WP03 owns only the migration-side check) before deleting; there
   must be no live caller. WP10 does NOT delete this symbol; it only reconciles the now-stale dead-symbol
   allowlist entry after this deletion merges (so WP10's T039 must reference WP07/T028 as the deleter,
   not WP03/IC-06).
3. Update the module docstring reference at `frontmatter.py:23` that names `write_shell_pid_claim` so
   the surviving doc does not describe a deleted symbol.
4. Re-point the orphaned baseline tests: `test_shell_pid_claim_baseline.py` (owned, 187L) asserts on
   the deleted helpers — re-point (delete-the-assertion-not-the-test where the behavior moved) so it now
   asserts the claim triple lands in `policy_metadata` and the baseline is captured on that path. If the
   entire file is testing only the deleted mechanism, migrate its meaningful cases to
   `test_implement_runtime_frontmatter_claim.py` and reduce this file to what still holds.

**Files**: `src/specify_cli/frontmatter.py`; `tests/specify_cli/core/test_shell_pid_claim_baseline.py`;
`tests/specify_cli/cli/commands/agent/test_implement_runtime_frontmatter_claim.py`.

**Validation**: `rg 'write_shell_pid_claim|add_history_entry' src/ tests/` returns only intentional
references (none in `src/`). WP10's `test_no_dead_symbols.py` reconciliation depends on this deletion +
the allowlist entry removal (WP10 owns the allowlist; do not edit `test_no_dead_symbols.py` here — it
is not in `owned_files`). ruff + mypy clean.

**Edge cases**: `SHELL_PID_BASELINE_FIELD` and `WP_RUNTIME_FIELDS` stay exported (still referenced by
`stale_detection`/`wp_metadata`) — do NOT delete them. Only the two write helpers + `add_history_entry`
go. If `capture_creation_time_baseline` was imported only by `write_shell_pid_claim`, it is now imported
at the claim emit site (T026) instead — verify the import moved, not vanished.

### Subtask T029 — Strike `tracker_refs` from `WP_FIELD_ORDER`

**Purpose**: `tracker_refs` becomes event-sourced (FR-006, emitted by WP08's map-requirements + WP06's
move-task). Leaving it in the static authored schema `WP_FIELD_ORDER` would dual-home it
(dynamic-in-events AND static-in-frontmatter) — the exact #2093 violation FR-013's arch test catches.

**Steps**:
1. Remove `"tracker_refs"` from `FrontmatterManager.WP_FIELD_ORDER` (`frontmatter.py:54`).
2. Trace the derived surfaces: `WP_FIELD_ORDER` feeds the field-ordering loop at `:226`, the
   `remaining` computation at `:231`, and the derived `_RUNTIME_FIELD_NAMES`/runtime-field projection
   at `:303-319`. Confirm removing `tracker_refs` from the canonical list flows correctly through all
   derivations (it should — they read the list, not a hard-coded copy).
3. Do NOT delete the `_mt_persist_tracker_refs` writer here — that is FR-006's move-task tail, owned by
   WP06. This WP only strikes the static-schema slot.

**Files**: `src/specify_cli/frontmatter.py`.

**Validation**: existing frontmatter round-trip / field-order tests stay green (a struck field must not
re-appear on write). WP10's FR-013 no-dual-home arch test (`test_2093_authority_invariant.py`) is the
mission-level guard that `tracker_refs` appears in the event-sourced slot set but NOT the static schema;
it lands in WP10.

**Edge cases**: A legacy WP file on disk that still carries an authored `tracker_refs:` line must not
crash the reader — striking it from `WP_FIELD_ORDER` moves it into the `remaining` (sorted trailing)
bucket on read, which is tolerant. Confirm no reader treats a struck-but-present field as an error.

### Subtask T029a — Resume/re-claim PID-refresh emit (`InnerStateChanged`, FR-004 / US3) — HIGH

**Purpose**: On resume/re-claim of an already-`in_progress` WP, the `shell_pid` (and its baseline) must
be **refreshed** so a resumed WP's liveness is decided by the *current* shell, not a stale/dead PID from
the original claim (US3 — a resumed WP is never falsely flagged stale). Today the resume path in
`workflow_executor.py` is a **no-op**: it does not refresh `shell_pid` anywhere (it never wrote
frontmatter on resume, and it does not yet emit an event). This gap is **owned here** (WP07 owns
`workflow_executor.py`), NOT punted to WP05. WP05 owns the *reader* that consumes the refreshed
snapshot PID (its T021 resume-window control asserts a resumed WP whose snapshot PID was refreshed via an
`InnerStateChanged` delta stays live) — but the *emit* that produces that refreshed slot is this subtask.

**Steps**:
1. Locate the resume / re-claim path in `workflow_executor.py` (the branch that re-enters an
   already-`in_progress` WP without a fresh `planned→claimed` transition). Confirm it currently performs
   **no** `shell_pid` refresh.
2. Add an `InnerStateChanged` emit (via WP01's `emit_inner_state_changed`) carrying a `shell_pid` /
   `shell_pid_created_at` refresh delta for the resumed WP. Capture the current PID (`os.getppid()`) and
   a truthful `shell_pid_created_at` via `capture_creation_time_baseline` (best-effort per C-007: omit the
   baseline key when it cannot be captured, never fail the resume). Because resume is **not** a lane
   transition, this rides the generic off-axis `InnerStateChanged` annotation — NOT the `policy_metadata`
   claim path (that is FR-004's *transition*-ride, reserved for `planned→claimed` / `for_review→in_review`).
3. Resolve the emit's `destination_ref` from stored topology / the resolved target branch the resume path
   already knows, never `Path.cwd()` (C-003).
4. Honor C-001: while WP05's `shell_pid` reader has not cut over, keep the resume refresh consistent with
   the same FR-005 dual-write flag posture as the claim writers (T026/T027) so a refreshed PID is never
   invisible to a still-frontmatter-reading liveness check.

**Files**: `src/specify_cli/cli/commands/agent/workflow_executor.py`.

**Validation**: extend the owned claim/executor suite (e.g. `test_shell_pid_claim_baseline.py` or
`test_implement_runtime_frontmatter_claim.py`) to drive a resume of an `in_progress` WP and assert an
`InnerStateChanged` `shell_pid`/`shell_pid_created_at` refresh event is persisted, the reduced snapshot's
`shell_pid` slot reflects the current PID, and the WP-file byte hash is unchanged (no frontmatter write).
This is the emit half of WP05/T021's resume-window control — the two must compose (WP07 emits, WP05 reads).

**Edge cases**: a resume where `capture_creation_time_baseline` returns `None` still refreshes
`shell_pid` (baseline omitted, D3a). Do not emit a spurious refresh when the WP was never claimed (no
`in_progress` state → no resume). Avoid double-emitting on a resume that also drives a genuine lane
transition — the transition claim path (T026) owns that case.

## Branch Strategy

`lane-per-wp`. Planning artifacts were generated on
`mission-prep/2684-wp-runtime-state-eviction`; completed changes merge back into
`mission-prep/2684-wp-runtime-state-eviction`. This WP depends on **WP01** (the `InnerStateChanged`
event, the reducer's `policy_metadata`→snapshot claim fold, and the snapshot slot set) and **WP03**
(the per-field backfill + fail-closed verify that gates the `shell_pid` reader cutover). Rebase onto
both before starting. **No inbound gate from #2160 or #2766** — per C-006 those deferred PRs rebase
onto *this* writer cutover, not the reverse. Land after WP02 has settled `tasks_transition_core.py` /
`tasks_move_task.py` / `emit.py` to avoid writer-file merge races (see `tasks.md` land-order note).

## Definition of Done

- [ ] The claim triple `(shell_pid, shell_pid_created_at, agent)` rides the claim transition's
      `policy_metadata` with the exact keys WP01's reducer extracts (both the `planned→claimed` and
      `for_review→in_review` claim paths).
- [ ] **"No claim path writes `shell_pid`/baseline/`agent` into `tasks/WP##.md`" holds only AFTER the
      atomic switch with WP05's reader.** Until WP05's `shell_pid` reader cuts over, the FR-005 dual-write
      (via `status/emit.py::_phase1_dual_write_enabled`, **default ON**) is **MANDATORY** — the claim
      MUST write both the frontmatter and the event so a fresh claim is never invisible to the still
      frontmatter-reading liveness check. This resolves the apparent contradiction with the item above:
      the frontmatter write is removed **at** the atomic switch, not before it.
- [ ] **Flag-teardown ownership**: WP07 OWNS the teardown of its **own** dual-write in `frontmatter.py`
      / `implement.py` / `workflow_executor.py` once the atomic switch with WP05's reader completes (WP03
      verify passed + WP05 reader cut over). WP10 does **not** tear down WP07's dual-write — it only
      verifies via the FR-013 arch test that no dual-write path remains.
- [ ] `write_shell_pid_claim`, `write_shell_pid_claim_to_file`, and `add_history_entry` (module fn +
      manager method) are deleted, with their `__all__` entries removed and the module docstring
      reference reconciled; `rg` finds no live caller in `src/`. **WP07/T028 is the sole owner of the
      `add_history_entry` deletion** (not WP03/IC-06).
- [ ] `tracker_refs` is struck from `WP_FIELD_ORDER`; derived surfaces flow correctly.
- [ ] Resume/re-claim of an already-`in_progress` WP refreshes `shell_pid`/`shell_pid_created_at` via an
      `InnerStateChanged` emit (T029a, FR-004/US3) — owned here, not WP05; the WP-file hash is unchanged
      across the resume.
- [ ] Orphaned baseline tests re-pointed (not deleted); the new
      `test_implement_runtime_frontmatter_claim.py` proves the claim triple lands in `policy_metadata`
      and the WP-file hash is unchanged across the claim.
- [ ] Full quality gate green: `pytest` (owned + adjacent suites), `ruff`, `mypy`. No dead imports.

## Risks

- **Reader/writer split-brain (C-001).** If this writer cut lands before WP05's `shell_pid` reader
  cutover and without the FR-005 dual-write flag, a fresh claim becomes invisible to the still
  frontmatter-reading liveness check → false-stale. Mitigate: gate on WP03's per-field verify and
  coordinate the atomic switch, or dual-write behind the flag.
- **`policy_metadata` key drift.** If the keys you emit do not exactly match WP01's reducer extraction,
  the claim silently produces an empty snapshot slot. Mitigate: read WP01's landed extraction code /
  data-model.md and assert on the persisted keys in test.
- **Over-deletion.** `SHELL_PID_BASELINE_FIELD` / `WP_RUNTIME_FIELDS` and the baseline-capture helper
  are still live — deleting them breaks `stale_detection`/`wp_metadata`. Delete only the two write
  helpers + `add_history_entry`.
- **`test_no_dead_symbols.py` allowlist** is NOT owned here (WP10). Deleting the symbols without WP10's
  allowlist reconciliation will red that arch test at the mission level — expected; WP10 closes it.

## Reviewer guidance

- Confirm the claim triple is on the **transition's** `policy_metadata`, not a separate
  `InnerStateChanged` (the claim path is FR-004's transition-ride; only the *resume* refresh is an
  annotation, and that resume refresh is **T029a here in WP07**, not WP05 — WP05 owns only the reader
  that consumes the refreshed snapshot slot).
- Confirm the resume PID-refresh emit (T029a) actually fires on re-claim of an `in_progress` WP (the
  path was a no-op before this WP) and that its snapshot slot composes with WP05/T021's resume-window
  reader control.
- Confirm WP07 tears down its **own** `_phase1_dual_write_enabled` dual-write in `frontmatter.py` /
  `implement.py` / `workflow_executor.py` at the atomic switch — this teardown is owned here, not
  deferred to WP10 (WP10 only verifies via the FR-013 arch test).
- Verify the deletions are total: symbol body + `__all__` + docstring reference + no live caller. A
  surviving stub is a campsiting failure.
- Check C-001 sequencing explicitly: is there a moment where a fresh `shell_pid` write is invisible to
  a snapshot-first reader? If WP05 has not landed, the FR-005 dual-write flag MUST be present.
- Note the `owned_files` tension: `tasks.md` does not grant this WP a review-claim test module beyond
  the three listed; the new-test creation is bounded to
  `test_implement_runtime_frontmatter_claim.py`. If a review-claim assertion needs a home, place it in
  the owned `test_tasks_move_task_authority_staging.py` rather than widening ownership.
- The live `implement.py` path divergence (`cli/commands/implement.py` vs the `tasks.md`
  `cli/commands/agent/implement.py`) is a known grounding note — verify the edit landed on the code
  that actually drives `spec-kitty implement`.

## Activity Log

- 2026-07-19T11:19:43Z – claude:opus:python-pedro:implementer – shell_pid=2536901 – Assigned agent via action command
- 2026-07-19T12:09:52Z – claude:opus:python-pedro:implementer – shell_pid=2536901 – Ready: claim rides policy_metadata, orphan tails deleted, tracker_refs struck, resume refresh emitted
- 2026-07-19T12:12:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=2792311 – Started review via action command
- 2026-07-19T12:18:53Z – user – shell_pid=2792311 – Review passed: claim triple rides policy_metadata on both planned->claimed (implement.py + workflow_executor _implement_start_claim) and for_review->in_review; flag semantics CONSISTENT with WP01 read side (flag OFF=dual-write+read legacy, flag ON=event-only+read snapshot) via _shell_pid_dual_write_active=not _phase1_dual_write_enabled; review-claim emit_inner_state_changed annotation genuinely reduces to snapshot shell_pid slot (live, not dead); write_shell_pid_claim_to_file + add_history_entry deleted+struck from __all__ with zero live callers, write_shell_pid_claim correctly KEPT (tasks_move_task.py _mt_persist_wp_file WP06 caller); tracker_refs struck from WP_FIELD_ORDER; T029a resume refresh fires on real IN_PROGRESS resume path without touching WP file. 22 owned tests pass, ruff clean, owned files mypy-clean, changes confined to owned_files.
