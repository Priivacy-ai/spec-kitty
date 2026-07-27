---
work_package_id: WP08
title: map-requirements + external activity-log writer
dependencies:
- WP01
- WP03
requirement_refs:
- FR-006
- FR-007
- FR-012
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/orchestrator_api/commands.py
create_intent:
- tests/integration/test_sc008_topology_resolution.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_map_requirements.py
- src/specify_cli/orchestrator_api/commands.py
- tests/integration/test_sc008_topology_resolution.py
role: implementer
tags: []
shell_pid: "2711717"
shell_pid_created_at: "1784462120.46"
---

# Work Package Prompt: WP08 – map-requirements + external activity-log writer

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro`

Load the `python-pedro` profile before touching any code. TDD (red-green-refactor), type hints on all
public APIs, and the pytest/ruff/mypy quality gate apply. Do NOT redesign the event or the emit API —
`InnerStateChanged`, `WPInnerStateDelta`, and the `emit_inner_state_changed` API are OWNED by WP01. This
WP is a **consumer**: it replaces two frontmatter/WP-file writers with emit calls.

## Objective

Evict two remaining runtime writers into the event log:

1. **T030** — `map-requirements` (`tasks_map_requirements.py`) stops writing `tracker_refs` into WP
   frontmatter and instead emits an `InnerStateChanged` `tracker_refs` **union** delta (FR-006). The
   union/replace semantics currently computed inline must move onto the emit: the reducer applies
   `union` to the `tracker_refs` field on the default path, and `--replace` uses **WP01's dedicated
   `tracker_refs_replace` delta field** (set-replace) — it must NOT degrade to union.
2. **T031** — The **external** Activity-Log writer in `orchestrator_api/commands.py:1563` (a
   cross-package writer behind the ACL boundary) stops writing a `## Activity Log` line into the WP
   file and emits an `InnerStateChanged` `note` **append** delta instead (FR-007).
3. **T032** — Land the **SC-008** cross-package topology-resolution test as a **net-new owned test**
   `tests/integration/test_sc008_topology_resolution.py` (added to `owned_files` + `create_intent`; it was
   homeless in the original slice): an off-axis emit run from a cwd **different from the mission root**
   lands its write at the stored-topology target branch, **never** a `Path.cwd()`-derived location (the
   #2647 invariant, FR-012 / C-003).
- 2026-07-19T11:19:49Z – claude:opus:python-pedro:implementer – shell_pid=2536901 – Assigned agent via action command
- 2026-07-19T11:54:25Z – claude:opus:python-pedro:implementer – shell_pid=2536901 – Ready: tracker_refs union/replace emit, external writer event-sourced, SC-008 green
- 2026-07-19T11:55:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=2711717 – Started review via action command
- 2026-07-19T12:03:06Z – user – shell_pid=2711717 – Review passed: T030 tracker_refs union emit + --replace via WP01 tracker_refs_replace channel (never degraded to union, both paths asserted); T031 append_history emits note InnerStateChanged via coord-aware STATUS seam (_resolve_mission_dir_or_fail), no WP-file write, structured HISTORY_COMMIT_FAILED envelope preserved, no Path.cwd() destination; T032 SC-008 uses real git worktree, non-vacuous (independent emit-neutralization mutation goes red; honest two-sided proof isolates WP01 canonicalize defense-in-depth). Out-of-map test edits (test_orchestrator_append_history_coord, test_orchestrator_commands_integration, test_commands_fail_closed) legitimately re-pin WP08's own source (orchestrator_api/commands.py) contract and are owned by no other WP. Tests green (7+70), ruff clean, no new --feature flag. Non-blocking follow-up: _resolve_history_commit_args now a new orphan (production caller removed), track for removal before WP10 test_no_dead_symbols runs.

## Context

**Design of record**: ADR 2026-07-19-1. **Requirements**: FR-006 (`tracker_refs` event-sourced union
from `map-requirements`), FR-007 (Activity-Log notes from all writers incl. the external
`orchestrator_api/commands.py:1563`), FR-012 (every new emit site resolves its write target from stored
topology/target branch, never `Path.cwd()`). **Constraints**: C-002 (typed delta — emit the typed
`tracker_refs: list[str]` / `note: str` fields, never a free dict), C-003 (`destination_ref` from
stored topology; #2647 invariant), C-006 (deferred PRs rebase onto this mission). **Success criteria**:
SC-008 is this WP's **dedicated acceptance evidence** — the plan (IC-04 orchestrator_api sub-concern)
explicitly carves this cross-package writer as its own WP precisely so SC-008 pins its topology
resolution.

**Key facts (grounded):**

- `map-requirements` today computes the merged `tracker_refs` inline and writes frontmatter:
  `tasks_map_requirements.py:421-432` — `existing_trackers = list(wp_meta.tracker_refs or [])`;
  `merged_trackers = sorted(set(existing_trackers) | set(st.tracker_ref_values))` (union) or
  `sorted(set(st.tracker_ref_values))` when `st.replace`; then `update_kwargs["tracker_refs"] =
  merged_trackers` and `write_frontmatter(wp_file, updated_meta.model_dump(...), body)` at `:433`.
  The existing-refs read is documented as "the ONE read feeding BOTH the union-merge base and the
  coverage projection" (`:323`). The **union is now the reducer's job**; the emit carries the *new*
  refs (or the full replacement set on `--replace`), not a pre-merged list.
- The external Activity-Log writer: `orchestrator_api/commands.py:1552-1566` reads the WP file,
  `append_activity_log(body, entry_text)` (`:1563`) with
  `entry_text = f"- [{timestamp}] {actor}: {note}"` (`:1562`), then `wp_path.write_text(...)` (`:1566`)
  and `safe_commit(...)`. This is the seam to replace with a `note`-append emit.
- **Topology already resolved here (reuse it).** `orchestrator_api` resolves its write dir through
  `_planning_read_dir(main_repo_root, mission)` (`:1546`) — documented as "the primary `target_branch`
  for EVERY topology" (`:337-359`) — and `_get_main_repo_root()` (`:252`) derives `main_repo_root` from
  `Path.cwd()` (`:256`). **The emit site MUST resolve `destination_ref` from the stored-topology target
  branch (the `_planning_read_dir` / merge-target resolution), NOT from `Path.cwd()`.** SC-008 is the
  guard that this holds when the process cwd differs from the mission root.
- **WP01 owns `emit_inner_state_changed`.** Call it; do not reimplement the fold. Confirm the exact API
  signature (feature_dir / mission_slug / wp_id / actor / delta / repo_root / topology target) from
  WP01's landed `status/emit.py`.
- **WP03 owns backfill + fail-closed verify.** Do not activate the `tracker_refs` reader cutover ahead
  of WP03's per-field verify (C-001). The `map-requirements` existing-refs read at `:426` is a
  frontmatter read that becomes a snapshot read only after backfill verify — coordinate the atomic
  switch, or dual-write behind the FR-005 flag during the bounded window.

### Subtask T030 — `tracker_refs` union emit from `map-requirements`

**Purpose**: Replace the inline frontmatter `tracker_refs` write with an `InnerStateChanged`
`tracker_refs` union delta, so `tracker_refs` is authored dynamically in the event log (never dual-homed
after WP07 strikes it from `WP_FIELD_ORDER`).

**Steps**:
1. In `tasks_map_requirements.py` (the WP-writing loop around `:410-433`), stop putting `tracker_refs`
   into `update_kwargs` / `write_frontmatter`. Instead, when `st.tracker_ref_values` is present and the
   target WP matches (`wp_id == st.wp.upper()`, `:422`), emit an `InnerStateChanged` `tracker_refs`
   delta via WP01's `emit_inner_state_changed`.
2. Move the merge semantics onto the emit correctly: the reducer applies **union**, so on the default
   (non-`--replace`) path emit the **new** `st.tracker_ref_values` on the `tracker_refs` field (the
   reducer unions them with the snapshot's existing set — do NOT pre-union from a frontmatter read). On
   `--replace`, use **WP01's dedicated `tracker_refs_replace` delta field** to carry the full replacement
   set — the reducer's `tracker_refs_replace` rule performs the set-**replace**. Do NOT degrade `--replace`
   to a union emit, and do NOT emulate it with clear-then-union or a second invented reducer rule; the
   sanctioned mechanism is the `tracker_refs_replace` field WP01 exposes.
3. Keep `requirement_refs` handling (`:418-419`) as-is — that field is NOT evicted by this mission; only
   `tracker_refs` moves. If `update_kwargs` ends up empty after removing `tracker_refs`, skip the
   frontmatter write for that WP (do not write an unchanged file — SC-001 hash stability).
4. Resolve the emit's `destination_ref` from the map-requirements feature dir / target branch
   (`_map_requirements_feature_dir`, `:649`), never `Path.cwd()` (C-003).

**Files**: `src/specify_cli/cli/commands/agent/tasks_map_requirements.py`.

**Validation**: existing map-requirements tests stay green for `requirement_refs`; add/extend a case
asserting a `tracker_refs` invocation emits an `InnerStateChanged` union delta and leaves the WP file
byte-unchanged (no `tracker_refs:` frontmatter line written). Assert the reduced snapshot's
`tracker_refs` slot equals the union of prior + new (and the replacement set on `--replace`).

**Edge cases**: `--replace` semantics must NOT silently degrade to union (that would resurrect stale
refs) — it MUST route through WP01's `tracker_refs_replace` delta field. The `_mr_stale_gate` post-write
hard-fail (`:433+`) currently runs after the frontmatter write
and reads refs across ALL WPs — confirm it re-sources from the snapshot (or the tolerated fallback)
after the write becomes an emit, so a pre-existing stale ref on an untouched WP still refuses. The
move-task `tracker_refs` emit (`tasks_move_task.py:1721`, FR-006) is WP06's — do not touch it here; the
reducer union means both emitters compose correctly.

### Subtask T031 — External activity-log writer → `InnerStateChanged` (`orchestrator_api`)

**Purpose**: The cross-package Activity-Log writer stops mutating the WP file and emits a `note`-append
delta, closing the last off-`specify_cli.cli` write seam for FR-007.

**Steps**:
1. In `orchestrator_api/commands.py` (the history-append command around `:1546-1585`), replace the
   `append_activity_log(body, entry_text)` (`:1563`) + `wp_path.write_text(...)` (`:1566`) +
   `safe_commit(...)` (`:1569-1577`) sequence with a call to WP01's `emit_inner_state_changed` carrying
   a `note` delta (`note = entry_text`, or the `{actor, note}` pair the emit API expects).
2. **Resolve the write target from stored topology, not cwd.** The emit's `destination_ref`/feature_dir
   MUST come from the resolved mission target branch (the `_planning_read_dir` / merge-target
   resolution, `:1546` / `_resolve_merge_target_branch` `:421`), **never** the `Path.cwd()`-derived
   `_get_main_repo_root()` value used as a bare write root. This is the SC-008 invariant.
3. Preserve the command's error envelope shape: the current path emits typed `SafeCommitError` /
   `SafeCommitBackstopError` envelopes (`:1580+`). The emit API has its own commit/rollback; ensure a
   failed emit still surfaces a structured error envelope through `_fail(...)` (`:230`) rather than a
   bare exception — do not regress the orchestrator-api contract.
4. Remove the now-unused local imports (`append_activity_log`, `split_frontmatter`, `build_document`,
   `safe_commit`) on this path if nothing else uses them — ruff confirms.

**Files**: `src/specify_cli/orchestrator_api/commands.py`.

**Validation**: drive the history-append command; assert the WP file is byte-unchanged and a `note`
`InnerStateChanged` event is persisted with the exact rendered entry text. Assert the rendered Activity
Log (sourced from events, WP01/render surface) contains the appended entry (FR-007 no-content-loss,
SC-004 class coverage).

**Edge cases**: This writer is behind the ACL boundary (`orchestrator_api` is the external-automation
surface). Its `actor`/`note` come from an external caller — keep the same input validation. A concurrent
emit from the host CLI and the orchestrator-api must both append (the reducer `note` rule is append, so
ordering is by `(at, event_id)` within the annotation partition — no lost note).

### Subtask T032 — SC-008 cross-package topology-resolution test

**Purpose**: Prove the #2647 invariant for the cross-package emit: an off-axis emit run from a cwd
different from the mission root lands at the stored-topology target, never a `Path.cwd()` location.

**Steps**:
1. Author an integration test that: sets up a mission with a distinct stored-topology target branch;
   `chdir`s the process to a directory **outside** the mission root; drives the T031 orchestrator-api
   history-append (and, where reachable, the T030 `tracker_refs` emit); asserts the persisted event and
   any resulting write landed under the **stored-topology target**, and that **no** file was created or
   mutated under the unrelated cwd.
2. Add a negative control: point `Path.cwd()` at a decoy directory and assert nothing is written there
   (a `Path.cwd()`-derived resolution would fail this — proof-of-drive, not proof-of-absence).
3. Mark it `integration` (and `git_repo` if it needs a repo fixture) per the marker registry.

**Files**: `tests/integration/test_sc008_topology_resolution.py` (**create** — now an owned test file,
added to both `owned_files` and `create_intent`). This SC-008 test was homeless in the original slice;
it is now a **net-new owned test** that is this WP's dedicated SC-008 acceptance evidence. Author the
assertions here — do NOT scatter them into an unrelated existing module.

**Validation**: the test is red against a `Path.cwd()`-derived resolution and green against the
stored-topology resolution (both branches — it must be able to fail).

**Edge cases**: `_get_main_repo_root()` uses `Path.cwd()` (`:256`) as the *repo-root discovery* anchor,
which is legitimate for locating the repo; the invariant is that the **emit destination** derives from
stored topology, not that cwd is never read. Assert on the write destination, not on whether `Path.cwd`
is called at all — otherwise the test rots against a legal cwd read.

## Branch Strategy

`lane-per-wp`. Planning artifacts were generated on
`mission-prep/2684-wp-runtime-state-eviction`; completed changes merge back into
`mission-prep/2684-wp-runtime-state-eviction`. Depends on **WP01** (the event, the delta, the
`emit_inner_state_changed` API, the `tracker_refs` union / `note` append reducer rules) and **WP03**
(the `tracker_refs` per-field backfill + fail-closed verify that gates the reader cutover). Rebase onto
both before starting. Runs in the parallel band with {WP05, WP06, WP07, WP09} after WP01+WP02+WP03 land.
This is a **cross-package** writer (ACL boundary) — coordinate with WP06 (which owns the move-task
`tracker_refs` emit) only via the reducer's union composition, not by touching each other's files.

## Definition of Done

- [ ] `map-requirements` emits an `InnerStateChanged` `tracker_refs` union delta (and a correct
      set-replace on `--replace` via WP01's `tracker_refs_replace` delta field — never degraded to
      union); no `tracker_refs` frontmatter write; unchanged WP files are not rewritten.
- [ ] The external `orchestrator_api/commands.py:1563` Activity-Log writer emits a `note`-append delta;
      no WP-file write; the structured error-envelope contract is preserved.
- [ ] Every new emit site resolves `destination_ref` from stored topology/target branch, never
      `Path.cwd()` (C-003).
- [ ] SC-008 test lands as the **net-new owned** `tests/integration/test_sc008_topology_resolution.py`
      (added to `owned_files` + `create_intent`), two-sided (fails against a cwd-derived resolution),
      and green.
- [ ] Full quality gate green: `pytest`, `ruff`, `mypy`; no dead imports; C-001 honored for the
      `tracker_refs` reader/writer switch (atomic or FR-005-flagged dual-write).

## Risks

- **Cross-package coupling / SC-008.** The orchestrator-api writer is the highest #2647 re-open risk:
  it runs from arbitrary external cwds. A `Path.cwd()`-derived write destination silently reopens #2647.
  Mitigate: derive `destination_ref` from stored topology and pin it with the two-sided SC-008 test.
- **`--replace` degrading to union.** The reducer's `tracker_refs` rule is union; a naive port drops
  the replace semantics and resurrects stale refs. Mitigate: route `--replace` through WP01's dedicated
  `tracker_refs_replace` delta field (set-replace); assert both paths.
- **Reader/writer split-brain (C-001).** `map-requirements` reads existing refs to compute coverage; if
  the writer emits but the read still consults frontmatter (or vice versa) across the window, coverage
  projection drifts. Mitigate: gate on WP03 verify; dual-read behind the FR-005 flag if not atomic.
- **Test ownership gap — RESOLVED.** The SC-008 test was homeless in the original slice; ownership is
  now extended: `tests/integration/test_sc008_topology_resolution.py` is a net-new owned test in both
  `owned_files` and `create_intent`. Author it there; do not scatter SC-008 assertions elsewhere.

## Reviewer guidance

- Verify the emit destinations are topology-resolved, not cwd-derived — this is the whole point of
  carving orchestrator_api as its own WP. Inspect the actual `destination_ref`/feature_dir passed to
  `emit_inner_state_changed`.
- Confirm the SC-008 test genuinely fails against a `Path.cwd()`-based resolution (proof-of-drive); a
  test that only asserts the happy path does not gate the invariant.
- Check the `--replace` vs union semantics are preserved exactly — this is a correctness trap, not a
  style point.
- Confirm the orchestrator-api error-envelope contract is intact: a failed emit still returns a
  structured `_fail(...)` envelope, not a bare traceback.
- Confirm the SC-008 test landed as the net-new owned `tests/integration/test_sc008_topology_resolution.py`
  (ownership was extended deliberately in this triage — it is in `owned_files` + `create_intent`), not
  scattered into an unrelated module.
- Confirm `--replace` routes through WP01's `tracker_refs_replace` delta field (set-replace), never a
  degraded union or a clear-then-union emulation.
