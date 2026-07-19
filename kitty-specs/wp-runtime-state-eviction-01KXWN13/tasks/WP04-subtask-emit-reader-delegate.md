---
work_package_id: WP04
title: Subtask emit + reader delegate (turns the red test green)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
model: claude-sonnet-5
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_mark_status.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_check_unchecked_subtasks_snapshot_source.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- src/specify_cli/cli/commands/agent/tasks_shared.py
- tests/specify_cli/cli/commands/agent/test_check_unchecked_subtasks_snapshot_source.py
role: implementer
tags: []
shell_pid_created_at: "1784463844.46"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2819582"
---

# Work Package Prompt: WP04 – Subtask emit + reader delegate (turns the red test green)

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and adopt that profile before touching any
code. You are Python Pedro: TDD (red-green-refactor), type hints on every public
API, and the full quality gate (`pytest`, `ruff`, `mypy`) before handoff. You do
**not** make architectural decisions — the reducer contract, the `InnerStateChanged`
wire shape, and the `emit_inner_state_changed` API are delivered by WP01 and are
authoritative; the `_guard_subtasks` re-source is delivered by WP02. Consume them,
do not redesign them.

## Objective

Make subtask completion event-sourced end to end on the two files this WP owns:
`mark-status` **emits** an `InnerStateChanged` `subtasks` delta instead of writing the
`tasks.md` checkbox surface (T015), and `_check_unchecked_subtasks` **reads** the
reduced-snapshot `subtasks` slot instead of parsing `tasks.md` bytes (T016). Together
with WP02's `_guard_subtasks` re-source, this flips the already-merged P0 red test
`tests/regression/test_issue_2684_subtask_completion_event_sourced.py` from red to
green **for the right mechanism** (T017). This WP is the MVP headline: `move-task WP01
--to for_review` must succeed on log-recorded completion with `tasks.md` checkboxes
still unchecked at the instant of success (SC-003 / AC-3 / US1).

## Context

- **Design of record**: ADR 2026-07-19-1 (`InnerStateChanged` off-axis event).
- **FR-003**: subtask completion is an `InnerStateChanged` `subtasks` delta (single or
  batch); `_guard_subtasks` (`tasks_transition_core.py:384` via `tasks_shared.py:412`)
  and `_infer_subtasks_complete` (`status/emit.py:279`) resolve from the reduced
  snapshot, not `tasks.md` bytes. WP04 owns the `tasks_shared.py:412` half
  (`_check_unchecked_subtasks`); WP02 owns the `_guard_subtasks` half; WP01 owns
  `_infer_subtasks_complete`.
- **FR-008**: no `mark-status` action writes the `tasks.md` subtask surface.
- **C-001**: reader↔writer switch atomically per field — once `mark-status` stops
  writing the checkbox and starts emitting, the snapshot-first reader
  (`_check_unchecked_subtasks`) must already resolve from the log, or a fresh
  completion is invisible. Both live in this WP → switch them together.
- **SC-003 (AC-3)**: `move-task --to for_review` succeeds on log-recorded completion
  with checkboxes **still unchecked at the instant of success**; a genuinely-incomplete
  WP is refused (both branches); and **the resolution source is the reduced-snapshot
  `subtasks` slot, not a `HistoryAdded` read** — the merged red test flips green for
  the right mechanism.
- **Key facts**: WP04 turns the merged red test green. WP04 **owns one net-new test
  file** — `tests/specify_cli/cli/commands/agent/test_check_unchecked_subtasks_snapshot_source.py`
  (in both `create_intent` and `owned_files`) — an owned unit test asserting the gate
  follows the reduced-snapshot `subtasks` slot, NOT the pre-existing `HistoryAdded` emit
  that `_ms_emit_history` already fires, and NOT `tasks.md` bytes (T017). The already-merged
  regression test `test_issue_2684_subtask_completion_event_sourced.py` is NOT owned and
  NOT edited here — it is run, not modified.
- **Snapshot API (from WP01)**: the reduced snapshot exposes a per-WP `subtasks`
  slot (`Mapping[str, Status]`) and an `emit_inner_state_changed(...)` API on
  `status/emit.py`. Import the reducer/snapshot the same way `status/emit.py` already
  does (`_reducer.reduce(read_events(...))` / `reducer.materialize(feature_dir)`);
  do not invent a second read path (#2093).

### Subtask T015 — `mark-status` emits subtask `InnerStateChanged` (stop writing the `tasks.md` checkbox)

**Purpose**: Move the authority for subtask completion out of the `tasks.md` checkbox
byte surface into an `InnerStateChanged` `subtasks` delta emitted through the WP01 API.

**Steps** (file:line-grounded in `tasks_mark_status.py`):
1. `_ms_apply_updates` (`:245`) currently resolves each task id via `_resolve_checkbox`
   / `_resolve_pipe_table` / `_resolve_inline_subtasks` (`:264-268`), sets
   `artifact_mutated`, and at `:302` does `st.tasks_md.write_text("\n".join(lines),
   ...)` then auto-commits (`:304-306`). **Cut the checkbox byte-write for the
   canonical subtask surface**: stop mutating `tasks.md` for the `CHECKBOX` /
   `INLINE_SUBTASKS` completion path. Keep task-id resolution (you still need to map a
   task id → its owning WP and its target `Status`), but the durable write becomes an
   emit, not a `write_text`.
2. Add a batch `emit_inner_state_changed` call carrying a `subtasks` delta
   (`Mapping[task_id, Status]`) for every resolved+updated task, grouped by owning WP
   (reuse the `resolved_tasks_by_wp` grouping pattern already in `_ms_emit_history`,
   `:309-341`). The `Status` is derived from `st.status` exactly as the checkbox
   resolution derived checked/unchecked today.
3. Resolve the emit's write target (`destination_ref`) from stored topology / target
   branch — **never `Path.cwd()`** (C-003/FR-012). Mirror how `_ms_commit` (`:212`) and
   `status/emit.py` already resolve the coord-routed target; do not re-derive from cwd.
4. `_ms_emit_history` (`:309`) already emits a `HistoryAdded` `note` per WP — leave it
   as-is (it is the Activity-Log render feed, a *different* concern from the authority
   slot). The new `subtasks` delta is the authority; the `HistoryAdded` note is
   render-only. T017 asserts the gate reads the former, not the latter.

**Files**: `src/specify_cli/cli/commands/agent/tasks_mark_status.py`.

**Validation**: after `mark-status WP01 T001 --status complete`, the reduced snapshot's
`work_packages["WP01"].subtasks["T001"]` is the completed `Status`; the `tasks.md`
bytes are unchanged (hash-stable); a persisted `annotation`-kind event exists in
`status.events.jsonl`. `ruff` + `mypy` clean; the `--help` byte-frozen surface in
`tasks.py` is untouched (this WP does not change the Typer wrapper).

**Edge cases**: batch marks (multiple task ids in one invocation) emit one delta with
all entries — never one event per id if the API supports batch (FR-003 "single or
batch"). Unresolved task ids (no owning WP) keep today's warning path
(`_ms_emit_history` `:335-340`) — do not emit a partial/garbage delta for them.
`--json` output shape must not change (`_mark_status_json_payload`). The
`feature_status_lock` span (`_ms_apply_updates` `:252`) still wraps resolve→emit so
concurrent marks serialize.

### Subtask T016 — `_check_unchecked_subtasks` re-source to the reduced snapshot

**Purpose**: The pre-transition gate that lists a WP's unchecked subtasks must read the
event-sourced `subtasks` slot, not `tasks.md` rows — otherwise a log-recorded
completion (T015) is invisible and the gate falsely blocks.

**Steps** (file:line-grounded in `tasks_shared.py`):
1. `_check_unchecked_subtasks(repo_root, mission_slug, wp_id, _force)` (`:412`)
   currently: resolves `feature_dir`, reads `tasks_md` (`:440-445`), and builds the
   unchecked list from `iter_wp_section_subtask_rows(content, wp_id)` (`:456-460`,
   returning task ids where `checked is False`). **Re-source**: reduce the event log
   for `feature_dir`, read `snapshot.work_packages[wp_id].subtasks`, and return the
   task ids whose `Status` is not the completed status.
2. Keep the canonical subtask *roster* (which task ids belong to the WP) coming from
   the authored `tasks.md` section — the roster is static design-intent (the WP's
   declared subtasks), only the **completion state** is event-sourced. Concretely:
   enumerate the WP's declared subtask ids from `iter_wp_section_subtask_rows` (or the
   frontmatter `subtasks` list) for the roster, then decide checked/unchecked from the
   snapshot slot. This preserves the "which rows count" close of #2062 while moving the
   completion authority to the log.
3. Gate the snapshot-first re-source behind the shared dual-write flag
   `status/emit.py::_phase1_dual_write_enabled` (the flag already exists — do not fork a
   second one). During the window before WP03's fail-closed `verify` has run, the flag
   resolves to **legacy read by default**: retain the `tasks.md`-checkbox read as the
   *tolerated fallback* (not authority) while dual-write is enabled. Only when
   `_phase1_dual_write_enabled` is off (post-verify cutover) does the reader resolve
   **purely** from the snapshot. This matches the migration order (`backfill →
   verify(pre-strip) → reader cutover`) — the reader must not front-run WP03's verify.
   Do not introduce a second permanent read path (#2093 / FR-013).
4. Preserve the primary-partition resolution (`TASKS_INDEX`, `:432-440`) for locating
   `feature_dir` so a coord-topology `-coord` husk cannot shadow the real primary.

**Files**: `src/specify_cli/cli/commands/agent/tasks_shared.py`.

**Validation**: with `WP01`'s subtasks recorded complete via T015 and `tasks.md`
checkboxes left `- [ ]`, `_check_unchecked_subtasks(..., "WP01", False)` returns `[]`;
with a genuinely-incomplete WP (no completion emitted) it returns the incomplete ids.
Unit-level: feed a synthetic snapshot and assert the two branches.

**Edge cases**: a WP with zero declared subtasks returns `[]` (unchanged — `:442-443`
early return when no `tasks.md`). A subtask present in the snapshot but absent from the
authored roster is ignored (roster is authority for membership). Missing/empty snapshot
(pre-backfill) falls to the flagged fallback, never crashes.

### Subtask T017 — Owned unit test: `_check_unchecked_subtasks` follows the snapshot, not `tasks.md`/`HistoryAdded`

**Purpose**: Prove the headline outcome fired for the *right mechanism* — the reduced
`subtasks` slot, not a `HistoryAdded` read and not `tasks.md` bytes — with an **owned
unit test** (not inspection-only), so the invariant has a local guard.

**Steps**:
1. Create the net-new owned test
   `tests/specify_cli/cli/commands/agent/test_check_unchecked_subtasks_snapshot_source.py`
   (in both `create_intent` and `owned_files`). This is an **ownership change** for this
   WP — the file is new and owned here.
2. **Discriminating assertion (the crux)**: feed `_check_unchecked_subtasks` a scenario
   where the sources **contradict** — a reduced snapshot whose `subtasks` slot records
   the WP's subtasks **complete**, WHILE a contradicting `HistoryAdded` note and an
   **unchecked** `tasks.md` (`- [ ]`) surface say otherwise. Assert the gate follows the
   **snapshot** (returns `[]` — complete), NOT `tasks.md` and NOT the `HistoryAdded`
   read. Add the mirror case: snapshot says incomplete while `tasks.md` shows `- [x]`
   checked → assert the gate follows the snapshot and returns the incomplete ids. Only a
   contradiction proves the source; a concordant fixture would pass off either surface.
3. Run `pytest tests/regression/test_issue_2684_subtask_completion_event_sourced.py -x`
   as a companion check. With T015 (emit) + T016 (reader) + WP02's `_guard_subtasks`
   re-source landed, both acceptance branches pass: log-recorded completion → `move-task
   WP01 --to for_review` succeeds with checkboxes unchecked; genuinely-incomplete WP →
   refused. **Do not edit that regression test** — it is already merged and is NOT in this
   WP's `owned_files`. If it still fails, the defect is in T015/T016 (or a WP01/WP02 API
   mismatch) — fix your owned files, escalate an API gap to the orchestrator; never patch
   the test to pass.
4. The gate path is `_guard_subtasks` (WP02) → `_check_unchecked_subtasks`
   (`tasks_shared.py:412`, T016) → snapshot. The `HistoryAdded` note emitted by
   `_ms_emit_history` must play **no** role in the gate decision. The permanent assertion
   of this invariant is the FR-013 architectural test (WP10); T017's owned unit test
   verifies the wiring locally so WP10 has a green substrate.

**Files**:
`tests/specify_cli/cli/commands/agent/test_check_unchecked_subtasks_snapshot_source.py`
(new, owned).

**Validation**: the new owned test is green and *fails* if `_check_unchecked_subtasks` is
reverted to read `tasks.md`/`HistoryAdded` (non-vacuous — the contradiction fixture is the
proof); the merged regression test is green; grepping the gate call-graph confirms no
`HistoryAdded` read on the authority path.

**Edge cases**: run the discriminating assertion with `_phase1_dual_write_enabled`
resolving to the snapshot (post-verify cutover), so the pass is "the right mechanism" and
not the tolerated `tasks.md` fallback. A concordant (non-contradicting) fixture is
insufficient — it would pass off either surface; the test MUST contradict the sources.

## Branch Strategy

`lane-per-wp`. Planning base and merge target are both
`mission-prep/2684-wp-runtime-state-eviction`. This WP rebases onto WP01 (event
foundation + `emit_inner_state_changed` + snapshot slots) and WP02 (`_guard_subtasks`
re-source + force fix) — land after both. WP02 lands early specifically so `mark-status`
/ gate logic does not race `tasks_transition_core.py`; do not touch that file here.

## Definition of Done

- T015: `mark-status` emits an `InnerStateChanged` `subtasks` delta; the `tasks.md`
  checkbox byte-write for the canonical subtask surface is cut; the emit target is
  resolved from stored topology, never `Path.cwd()`.
- T016: `_check_unchecked_subtasks` resolves completion from the reduced-snapshot
  `subtasks` slot (roster still from the authored section); `tasks.md`-checkbox fallback
  only behind `status/emit.py::_phase1_dual_write_enabled` (default legacy read until
  WP03 verify).
- T017: net-new owned test
  `tests/specify_cli/cli/commands/agent/test_check_unchecked_subtasks_snapshot_source.py`
  lands and is green — feeds a snapshot-complete vs contradicting `HistoryAdded`/unchecked
  `tasks.md` fixture and asserts the gate follows the **snapshot**; the merged
  `test_issue_2684_subtask_completion_event_sourced.py` is green (unedited); resolution
  source confirmed as the snapshot slot.
- `pytest` (this WP's touched paths + the regression test), `ruff`, `mypy` all clean.
- No change to the byte-frozen `--help` surface; `--json` payload shape unchanged.

## Risks

- **Silent invisibility (C-001)**: cutting the writer (T015) without landing the reader
  (T016) makes fresh completions invisible → false gate blocks. They are in the same WP
  — land atomically, test the round-trip.
- **Wrong-mechanism green**: the test could pass off the `HistoryAdded` note or a
  lingering checkbox write. Assert the snapshot slot is the source (T017).
- **cwd leak (#2647)**: a new emit site resolving its target from `Path.cwd()` reopens
  #2647. Resolve from stored topology (SC-008 covered by WP06/WP08, but this emit site
  must honor the same rule).
- **Roster vs completion conflation**: moving *membership* to the log (instead of only
  completion) would drop authored subtasks. Keep the roster static.

## Reviewer guidance

- Verify `tasks.md` is byte-stable across a `mark-status` invocation (hash before/after).
- Confirm a persisted `annotation`-kind event with a `subtasks` delta exists after
  `mark-status`, and that `_check_unchecked_subtasks` returns `[]` for a
  log-completed-but-checkbox-unchecked WP.
- Confirm the emit `destination_ref` derivation contains no `Path.cwd()` call.
- Confirm the merged `test_issue_2684_subtask_completion_event_sourced.py` is unmodified;
  the diff shows only the two owned source files plus the net-new owned test
  `tests/specify_cli/cli/commands/agent/test_check_unchecked_subtasks_snapshot_source.py`.
- Confirm the new owned test is non-vacuous: it contradicts the snapshot against
  `tasks.md`/`HistoryAdded` and asserts the gate follows the snapshot (it would fail if
  the reader reverted to `tasks.md`).
- Confirm no second reducer/read path was introduced — the snapshot is read via the
  same reducer entry `status/emit.py` uses.

## Activity Log

- 2026-07-19T11:26:44Z – claude:sonnet:python-pedro:implementer – shell_pid=2579940 – Assigned agent via action command
- 2026-07-19T12:06:38Z – claude:sonnet:python-pedro:implementer – shell_pid=2579940 – Ready: mark-status emits InnerStateChanged, gate reads snapshot; merged red test GREEN
- 2026-07-19T12:10:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=2788122 – Started review via action command
- 2026-07-19T12:15:01Z – user – Moved to planned
- 2026-07-19T12:15:48Z – claude:sonnet:python-pedro:implementer – shell_pid=2799316 – Started implementation via action command
- 2026-07-19T12:23:23Z – claude:sonnet:python-pedro:implementer – shell_pid=2799316 – Cycle2: flag aligned to WP01 (ON->snapshot); merged red test flag-on green
- 2026-07-19T12:24:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=2819582 – Started review via action command
- 2026-07-19T12:28:34Z – user – shell_pid=2819582 – Cycle2 review passed: _check_unchecked_subtasks flag aligned to WP01/WP02 (ON->snapshot, OFF->legacy) at tasks_shared.py:503; red test runs status_phase=1 (flag ON) green with genuinely-incomplete control still refusing; T017 fixtures realigned; T015 untouched; 8/8 tests pass. Supersedes cycle-1 flag-inversion rejection.
