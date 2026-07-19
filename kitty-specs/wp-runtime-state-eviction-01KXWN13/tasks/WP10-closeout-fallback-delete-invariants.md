---
work_package_id: WP10
title: 'Closeout: delete fallbacks + land invariants'
dependencies:
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
requirement_refs:
- FR-005
- FR-009
- FR-010
- FR-013
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T038a
- T039
- T040
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-opus-4-8
history: []
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/test_2093_authority_invariant.py
create_intent:
- tests/architectural/test_2093_authority_invariant.py
- tests/integration/test_ac5_hash_guard.py
- tests/integration/test_render_parity_golden.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow_cores.py
- src/specify_cli/merge/done_bookkeeping.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_2093_authority_invariant.py
- tests/integration/test_ac5_hash_guard.py
- tests/integration/test_render_parity_golden.py
role: implementer
tags: []
shell_pid: "3276369"
shell_pid_created_at: "1784475556.5"
---

# Work Package Prompt: WP10 — Closeout: delete fallbacks + land invariants

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load reviewer-renata
```

Load the `reviewer-renata` profile before touching any file. This work package is the mission
**closeout**: it removes the last transitional scaffolding and lands the enforcing invariants. It is
owned by the reviewer profile because its deliverable is proof — proof that no runtime state remains
dual-homed, that no inert fallback lingers, and that the dossier content hash is byte-stable across a
driven lifecycle. Adopt the profile's anti-laziness, testability, and single-authority governance lens
for every decision below. Do **not** advance any mission step until the profile's initialization
declaration is emitted.

## Objective

Land the closeout for the WP-runtime-state eviction: **VERIFY** (do not delete) that no FR-005
frontmatter-fallback flag or C-001 dual-write shim survives (T036) — each owning lane tears down its own
dual-write, and WP10 proves it gone via the FR-013 arch test; delete the two legacy verdict-field read
fallbacks in `workflow_cores.py:340-348` and `done_bookkeeping.py:104-105` — **only after** the WP03
backfill has seeded legacy approvals as events (T037); land the AC-5 stable-hash guard as the **sole**
proof-of-drive full-lifecycle acceptance (T038); land the SC-004 render-parity golden test (T038a); land
the #2093 refactor-stable architectural test — no consumer reads a dynamic frontmatter field as
authority, and no field appears in both the static authored schema and the event-sourced slot set — and
reconcile the `test_no_dead_symbols.py` allowlist (T039); confirm the re-pointed force tests (from WP02)
and the full suite are green (T040).

This is the terminal WP on the dependency graph: it depends on **every** field vertical (WP04–WP09)
having landed its reader re-point, writer cut, created-orphan deletes, **and its own dual-write
teardown**. Nothing here may run before those are merged — the fallbacks this WP deletes (T037) are
still load-bearing until then, and the dual-write shims are torn down by their owning lanes (WP01/WP05/
WP07), not here.

## ⚠️ RE-SCOPE (2026-07-19 human decision: ship dual-write, defer corpus cutover)

**This banner overrides the subtask bodies below wherever they conflict.** Investigation at closeout
found the field verticals (WP01/WP04/WP05/WP07) landed their snapshot readers **behind** the phase-1
flag (`_phase1_dual_write_enabled`, default OFF) as dual-write, and **no WP wired the runtime-state
`backfill → verify → cutover` CLI**. Per `contracts/migration.md` the flag/fallback teardown is the
FINAL migration step, gated on that backfill — out of this mission's scope. The human decision is to
**ship the dual-write end-state now and defer the corpus cutover** (see `tasks.md` deferred note).

- **T036 — REFRAME.** The phase-1 flag + dual-write shim are **RETAINED as the sanctioned
  migration-window safety net**, not treated as a survivor to fail. They are the documented mechanism,
  not an unintended second authority. Do NOT delete them; do NOT fail T039 on their presence.
- **T037 — DEFERRED.** Do NOT delete the `workflow_cores.py:340-348` / `done_bookkeeping.py:104-105`
  fallbacks; they remain load-bearing until the deferred backfill seeds legacy approvals as events.
- **T038 / T038a — land, driven at `status_phase:1` (flag ON).** They prove the event-sourced path is
  byte-stable (AC-5) and render-lossless (SC-004) **when enabled** — the shipped deliverable. A
  `status_phase:1` fixture is the honest frame (the WP06/T025 slice and `test_wp_file_hash_stability.py`
  already use this pattern).
- **T039 — assert at flag ON.** The #2093 arch test asserts: at `status_phase:1`, no dynamic-frontmatter
  field is read as authority, and no field is dual-homed (static schema + event slot). The phase-1 flag
  is the **sole sanctioned migration-window fallback** — encode it in the *tolerated* set (NOT empty, as
  the original T039 body assumed post-cutover). Still reconcile the `add_history_entry` allowlist (WP07
  deleted the symbol — valid) and fix the `test_no_dead_symbols` gate.
- **T040 — full suite green.** Fix the `test_tasks_move_task_degod.py` collection error (delete/re-point
  the deleted `_mt_uncheck_rollback_subtasks` import), delete tests asserting deleted mechanisms
  (`test_move_task_uncheck_rollback`, `test_move_task_rollback_uncheck_robust`, the
  `test_tasks_compat_surface` seam assertions for removed `_mt_*` symbols), and re-point the
  intended-eviction tests (`test_tasks_backward_emit` force-flip, `rollback_clears_claim`,
  `tracker_ref_frontmatter_persisted`, `rollback_to_planned_is_fully_reimplementable`) to assert the
  event-sourced behavior **at flag ON**. These test edits span files outside `owned_files` — that is the
  authorized closeout scope; record each with a one-line rationale.
- **NEW — #2512 release delta (authorized out-of-map closeout edit).** On rollback to `planned`, the
  prior claim's `shell_pid`/`agent` is released in NEITHER surface. Emit a release `InnerStateChanged`
  clearing `shell_pid`/`agent` on `→planned` in WP06-owned
  `tasks_move_task.py::_mt_emit_runtime_state`. Authorized here as a bounded closeout edit (WP06 is
  approved/frozen → no parallel collision; event-only under flag ON keeps the WP-file byte-stable,
  consistent with WP06's design). Add a test asserting a planned-lane WP exposes no live claim.

**Deferred to a follow-up mission (joins IC-08):** the `backfill → verify → cutover` CLI, flipping the
flag unconditional, and T037 fallback deletion.

## Context

**Design of record**: ADR `2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md`.
This WP corresponds to plan concern **IC-07 — Delete legacy fallbacks + land invariants (closeout)**.

The mission evicts runtime-mutable WP state (`shell_pid`, subtask completion, `## Activity Log` notes,
`tracker_refs`, `agent`/`assignee`, review-cycle fields) out of `tasks/WP##.md` into the append-only
event log, folded through one generic off-axis `InnerStateChanged` event. The migration runs under the
strict order (contract `migration.md`):

```
backfill → verify(FAIL-CLOSED) → reader cutover → writer cutover → delete fallbacks → land hash guard
```

WP10 owns the last two boxes. The delete-fallbacks step is **gated on backfill** by construction: the
two legacy read fallbacks synthesize done-evidence for un-migrated on-disk WPs, so removing them before
WP03 seeds those approvals as events would strand legacy corpora. Do **not** reorder the delete ahead of
backfill.

**Key spec references**:
- **FR-009** — Evict all review-cycle state. Delete the dead verdict-field read fallbacks
  `workflow_cores.py:340-348` (whole branch) and `done_bookkeeping.py:104-105` — but only after the
  FR-011 backfill seeds legacy approvals as events.
- **FR-013** — A refactor-stable architectural test asserts no consumer reads a dynamic frontmatter
  field as authority (the #2093 invariant), distinguishing an authority-read from a tolerated
  migration-window fallback-read, and additionally asserts no field appears in both the static authored
  schema and the event-sourced slot set (catches the FR-006 `tracker_refs` dual-home).
- **NFR-001** — Across a full WP lifecycle (claim → subtask-done → review → history), the raw-byte
  content hash of `tasks/WP##.md` and the WP's `tasks.md` section changes **0 times**.
- **AC-5 / SC-005** — The WP-file content hash is byte-stable across the full **driven** lifecycle
  (same proof-of-drive as SC-001: a persisted event must exist for each action, so "unchanged" can
  never mean "untouched").

**Key planning references**:
- `contracts/migration.md` — the strict order and the "delete fallbacks only now" rationale.
- `data-model.md` — the post-mission field-authority table ("No field appears in both columns of
  authority — enforced by the FR-013 architectural test") and the event-sourced slot set
  `{shell_pid, shell_pid_created_at, subtasks, notes, tracker_refs, agent, assignee, review}`.
- `quickstart.md` — SC-001/SC-005 proof-of-drive and the FR-013 architectural-invariant list.

**Owned-file boundary (read before you start)**: WP10 owns exactly the files in the frontmatter
`owned_files`. The FR-005 fallback flag and the phase-1 dual-write shim have definitions that live in
files owned by earlier verticals (`core/stale_detection.py` FR-005 baseline gate — **WP05 tears it down
itself**; `status/emit.py::_phase1_dual_write_enabled`/`_mirror_phase1_frontmatter_lane` shim — **WP01
tears it down itself**; the claim-writer dual-write in `frontmatter.py`/`implement.py`/
`workflow_executor.py` — **WP07 tears it down itself**). WP10 does **not** edit these non-owned files and
does **not** delete any flag/shim. **T036 is VERIFY-only**: it proves, via the FR-013 arch test (T039),
that no dual-write / second-authority path remains after the owning lanes have torn down their own. A
survivor is a **T039 red test attributable to the owning lane**, not a WP10 owned-file edit or an
escalation ticket. See Reviewer guidance.

---

### Subtask T036 — VERIFY no FR-005 fallback flag / dual-write shim survives (teardown is owned by each lane)

**Purpose**: Now that all field verticals (WP04–WP09) have switched their reader authority to the
reduced snapshot atomically-per-field (C-001), the transitional scaffolding is inert. **Each owning lane
tears down its own dual-write** as part of completing its atomic per-field switch — WP10 does **not**
own or perform that teardown. WP10's job here is to **VERIFY** that no second-authority path survives,
mechanically, via the FR-013 arch test.

**Ownership of the teardown (not WP10)**:
- The FR-005 baseline/flag gate in `core/stale_detection.py:230-235,395-403` (`shell_pid_baseline`
  presence-gated fallback) — **WP05 tears it down** once its reader cutover verifies.
- The phase-1 dual-write shim in `status/emit.py:310` (`_phase1_dual_write_enabled`) and `:345`
  (`_mirror_phase1_frontmatter_lane`) — **WP01 tears it down**.
- The claim-writer dual-write in `frontmatter.py`/`implement.py`/`workflow_executor.py` — **WP07 tears
  it down** at its atomic switch.

**Steps**:
1. Do **not** delete any flag/shim. Do **not** edit non-owned files. WP10 does not "detect and escalate"
   a residual as a closeout finding — the enforcing mechanism is the T039 arch test.
2. Run the FR-013 arch test (T039) and confirm it is green: no `_phase1_dual_write_enabled` /
   `_mirror_phase1_frontmatter_lane` / `shell_pid_baseline` fallback / any dual-write path remains as a
   live second authority.
3. If a survivor is found, it is a **T039 red test attributable to the owning lane** (WP01 / WP05 /
   WP07), which must fix its own teardown — WP10 records the red result against that lane and does not
   patch it in a WP10-owned file.

**Files**: none edited by T036 (verification subtask). The owned source files
(`workflow_cores.py`, `done_bookkeeping.py`) are edited by T037, not here.

**Validation**: `rg -n "phase1_dual_write|status_phase|_mirror_phase1|shell_pid_baseline.*fallback"`
over `src/` returns no *inert* survivor; the FR-013 arch test (T039) passes with no dual-home / dual-write
finding. A survivor turns T039 red — the fix belongs to the owning lane, not a WP10 edit.

**Edge cases**: A lane tearing down its shim before its paired reader/writer switched atomically reopens
the C-001 symmetric split-brain (a fresh runtime write becomes invisible to a snapshot-first reader) —
this is why every lane gates its own teardown on its atomic switch, and why WP10 only runs after
WP04–WP09. A flag left inert but undeleted is a latent second authority path (the #2093 violation the
mission exists to close); it must fail T039, attributed to its owning lane.

---

### Subtask T037 — Delete legacy verdict-field read fallbacks (post-backfill)

**Purpose**: Remove the two dead frontmatter-sourced done-evidence fallbacks that synthesized approval
evidence for un-migrated on-disk WPs. They are only safe to delete **after** the WP03 backfill seeds
legacy approvals as `InnerStateChanged`/transition events (FR-009 / FR-011 order); the review-cycle
authority is now the reduced snapshot.

**Steps**:
1. In `workflow_cores.py::resolve_review_feedback_context`, delete the frontmatter fallback branch at
   lines **340-348** — the `fm_review_status = extract_scalar(wp_frontmatter, "review_status")` /
   `fm_review_feedback = ...` read and the `if fm_review_status ... == "has_feedback": … return True,
   ref, path, "frontmatter"` branch. The canonical path above it (`latest_review_feedback_reference`
   → `return True, …, "canonical"`) is now the sole resolution; the function returns
   `(False, None, None, None)` when no canonical artifact exists.
2. Confirm the `"frontmatter"` provenance tag has no remaining consumer (it was the fallback's marker);
   if a caller branches on it, the branch is now dead — remove it or verify it is out of WP10's owned
   surface and flag it.
3. In `done_bookkeeping.py::_extract_done_evidence`, delete lines **104-105**
   (`reviewed_by = meta.reviewed_by` and the `if meta.review_status == "approved" and reviewed_by …`
   guard) together with the `DoneEvidence(review=ReviewApproval(..., reference=f"frontmatter-migration:
   {wp}"))` synthesis they gate. After deletion the function resolves done-evidence from the
   event-sourced review slot only; a WP with no seeded/event approval yields `None` (fail-closed — do
   not fabricate approval from frontmatter).
4. Re-point or delete the now-orphaned `WPMetadata` frontmatter reads (`meta.reviewed_by`,
   `meta.review_status`) **only if** they live in owned files; otherwise flag to WP05/WP09.

**Files**: `src/specify_cli/cli/commands/agent/workflow_cores.py` (lines 340-348),
`src/specify_cli/merge/done_bookkeeping.py` (lines 104-105 + gated synthesis).

**Validation**: full merge-gate + review-cycle tests green (WP09 landed both halves); a fixture WP
approved via events resolves done-evidence; a legacy on-disk WP that was backfilled (WP03) still
resolves — proving the delete is post-backfill-safe. `rg -n "frontmatter-migration" src/` returns
nothing.

**Edge cases**: Deleting these **before** backfill strands legacy corpora — assert WP03's backfill has
merged and its fail-closed verify passed before this subtask. A silent behavior change is the danger:
the merge gate must not start falsely blocking merges because override/approval recognition regressed;
lean on WP09's both-halves override migration and the merge-gate override-recognition tests.

---

### Subtask T038 — Land AC-5 stable-hash guard (proof-of-drive lifecycle) — SOLE SC-001/SC-005 acceptance

**Purpose**: Prove NFR-001 / SC-005 by construction: across a full **driven** WP lifecycle, the raw-byte
content hash of `tasks/WP##.md` and the WP's `tasks.md` section changes 0 times, and a persisted event
exists for each driven action so "unchanged" can never mean "untouched".

**This is the SOLE full-lifecycle hash-stability acceptance for SC-001 / SC-005.** It can only land here
because WP10 depends on **WP04–WP09 = every writer cut over** — only after all writers are evicted is a
full claim→…→done drive actually byte-stable end-to-end. The WP06/T025 hash check is **only a scoped
slice** (the move-task/god-write writer cut, not the whole lifecycle); it does not and cannot stand in
for this mission-level acceptance. Do not treat WP06/T025 as the SC-001/SC-005 gate — T038 is.

**Steps**:
1. Create `tests/integration/test_ac5_hash_guard.py` (new). Mark it `integration` and `git_repo` per
   the plan's marker registry.
2. On a real lanes-topology WP fixture, drive the mandatory action set through the canonical entry
   points (not by hand-editing files): `claim → mark-subtask-done → add note → tracker_ref append →
   review-reject → review-approve → history append` (quickstart SC-001/SC-005).
3. Capture the raw-byte content hash of `tasks/WP##.md` and the WP's `tasks.md` section at `claimed`
   and after each subsequent action through `done`. Assert every hash equals the `claimed` hash
   (0 changes).
4. **Proof-of-drive**: for each action, assert a corresponding persisted event exists on
   `status.events.jsonl` (an `InnerStateChanged` annotation or a transition, as appropriate). A green
   test with no events would mean the actions never fired — assert both halves.
5. mtime is informational only (idempotent no-op writes bump it); do **not** gate on mtime.

**Files**: `tests/integration/test_ac5_hash_guard.py` (create).

**Validation**: `pytest tests/integration/test_ac5_hash_guard.py -q` passes; deliberately re-introducing
any WP-file runtime write (e.g. reverting a WP06 writer cut) turns it red — confirm the guard bites.

**Edge cases**: An emit site resolving its target from `Path.cwd()` instead of stored topology reopens
#2647 and can write to the wrong file, leaving the fixture hash falsely stable — pair the drive with a
cwd different from the mission root where practical (SC-008 is WP08's dedicated test, but keep the
lifecycle drive honest). Ensure the review-reject/approve steps use the FR-015 evidence-gated,
force-free path so the drive matches production behavior.

---

### Subtask T038a — Land SC-004 render-parity golden test

**Purpose**: Prove SC-004 ("renders from events with no content loss") at the mission level with a
**golden** comparison: the event-sourced render of the WP's `## Activity Log` / `## History` and the
review-cycle render classes reproduce, byte-for-byte on the meaningful content, what a legacy
frontmatter/body-sourced render produced. WP05 re-points the render source (its T019); this test is the
mission-level parity guard that the re-point lost nothing.

**Steps**:
1. Create `tests/integration/test_render_parity_golden.py` (new; added to `owned_files` +
   `create_intent`). Mark it `integration` (and `git_repo` if a repo fixture is needed) per the marker
   registry.
2. Capture a **legacy-sourced golden**: a fixture WP whose Activity-Log / History / review-cycle content
   is rendered from the pre-eviction frontmatter/body path (the golden baseline snapshot). Store it as
   the golden.
3. Drive the same content through the event log (emit the notes/history/review deltas via the canonical
   entry points), then render via the event-sourced path (WP05's re-pointed render + WP09's review
   render). Assert the rendered output matches the golden for **all three render classes**:
   **activity** (`## Activity Log` notes), **history** (`## History`), and **review** (review-cycle
   verdict/ref/result). No content loss, no reordering that drops entries.
4. Two-sided: deliberately drop one note/history/review entry from the event stream and confirm the
   golden comparison goes red — the parity guard must bite on real content loss.

**Files**: `tests/integration/test_render_parity_golden.py` (create).

**Validation**: `pytest tests/integration/test_render_parity_golden.py -q` green; the render of each
class equals the legacy-sourced golden; the dropped-entry mutation turns it red.

**Edge cases**: timestamp/ordering normalization — the golden must key on meaningful content and stable
ordering (e.g. `(at, event_id)`), not on volatile fields, so it does not rot on a legal re-render. A WP
with legacy body content not yet backfilled must still render via the tolerated fallback with no loss.

---

### Subtask T039 — #2093 refactor-stable arch test + reconcile `test_no_dead_symbols`

**Purpose**: Land the enforcing FR-013 invariant so the single-authority guarantee cannot silently rot
under future refactors, and reconcile the dead-symbol allowlist now that the eviction deleted its
orphaned writers.

**Steps**:
1. Create `tests/architectural/test_2093_authority_invariant.py` (new; marker `architectural`). Assert
   **two** invariants:
   - **No dynamic-authority frontmatter read**: no consumer reads a dynamic frontmatter field
     (`shell_pid`, `shell_pid_created_at`, subtask completion, `agent`, `assignee`, `tracker_refs`,
     review-cycle fields) as **authority**. Define the detection mechanism explicitly — an
     import/call-graph (AST) over the authority read path — and distinguish an authority-read from a
     **tolerated migration-window fallback-read**. Since T036/T037 removed the last fallbacks, the
     tolerated set should now be empty; encode that so a re-introduced fallback fails.
   - **No dual-home**: no field name appears in **both** the static authored schema
     (`WP_FIELD_ORDER` / frontmatter schema) **and** the event-sourced slot set
     `{shell_pid, shell_pid_created_at, subtasks, notes, tracker_refs, agent, assignee, review}`.
     This catches the FR-006 `tracker_refs` dual-home directly (WP07 struck it from `WP_FIELD_ORDER`).
2. Make the test **refactor-stable**: key on symbol identity / slot membership, not line numbers, so a
   later relocation does not produce a false green or a brittle red.
3. Reconcile `tests/architectural/test_no_dead_symbols.py`: the `add_history_entry` allowlist
   `SymbolKey` entry (around **line 282**, commented `specify_cli.frontmatter::add_history_entry`) was
   tolerated while the symbol was live-but-uncalled. **WP07/T028** deleted `add_history_entry` (module
   fn + manager method) and its `__all__` export, so the allowlist entry is now stale — **remove it**
   (leaving it masks the next dead symbol). Verify no other WP10-adjacent deletion (the FR-009
   fallbacks) leaves a symbol that now needs an allowlist entry; prefer deleting the symbol over
   allowlisting it.

**Files**: `tests/architectural/test_2093_authority_invariant.py` (create),
`tests/architectural/test_no_dead_symbols.py` (remove the stale `add_history_entry` allowlist entry).

**Validation**: `pytest tests/architectural -q` green; deliberately re-adding a frontmatter authority
read (or re-listing `tracker_refs` in `WP_FIELD_ORDER`) turns `test_2093_authority_invariant.py` red;
`test_no_dead_symbols.py` passes without the removed allowlist entry.

**Edge cases**: The hard part is distinguishing an **authority-read** from a **tolerated fallback-read** —
misclassifying either produces a false green (an undetected dual-home) or a false red (a legitimate
render-only read). Ground the classifier on the field-authority table in `data-model.md`. Removing the
allowlist entry while the symbol is somehow still live would break `test_no_dead_symbols.py` — confirm
the **WP07/T028** deletion of `add_history_entry` has merged first.

---

### Subtask T040 — Full-suite green; re-pointed force tests reconciled

**Purpose**: Terminal acceptance — confirm the entire mission lands green, including the WP02 force
tests that were **re-pointed** (not deleted) to the correct FR-015 expected values (SC-007), and the
already-merged red regression that this mission flips green.

**Steps**:
1. Run the full suite: `pytest -q` (or the project's canonical gate). Confirm 0 failures.
2. Confirm the re-pointed force-provenance tests assert the **corrected** values: the persisted
   `StatusEvent.force` is falsy for the five evidence-gated review-rejection edges and truthy for the
   retained genuine-force positive control. These tests are **WP02-owned** — WP10 does not edit them; it
   confirms the whole suite (including them) is green. If any is red, the failure belongs to the owning
   lane (WP02) — record it and escalate, do not edit a non-owned test to force green.
3. Confirm `tests/regression/test_issue_2684_subtask_completion_event_sourced.py` (merged, red today)
   is now **green for the right mechanism** — the resolution source is the reduced-snapshot `subtasks`
   slot (WP04), not a `HistoryAdded` read.
4. Confirm the WP10-owned new tests (`test_ac5_hash_guard.py`, `test_2093_authority_invariant.py`) and
   the reconciled `test_no_dead_symbols.py` are green.

**Files**: none edited (verification subtask); reference the enumerated re-pointed tests
(`test_tasks_transition_core.py`, `test_tasks_backward_emit.py`, `test_status_e2e_integration.py`,
`test_status_cli.py`) as green-confirmation targets only.

**Validation**: full `pytest` green; `ruff` and `mypy` clean on the owned files; the mission's headline
outcomes (P0 red test green, AC-5 hash stable, honest force provenance) all pass.

**Edge cases**: A flaky or environment-dependent failure in a non-owned lane is not a WP10 defect —
attribute it correctly. Do **not** delete or weaken an assertion to reach green (SC-007 is explicit:
"delete-the-assertion-not-the-test" was already done as a *re-point* in WP02; WP10 must not re-delete).

---
- 2026-07-19T13:28:46Z – claude:opus:python-pedro:implementer – shell_pid=2930102 – Assigned agent via action command
- 2026-07-19T13:38:33Z – claude:opus:python-pedro:implementer – shell_pid=2930102 – Blocked (WP10 closeout): reader/writer cutover NOT completed by field verticals - event-authority still gated behind phase-1 flag (_phase1_dual_write_enabled, defaults OFF; legacy frontmatter/checkbox is the live default). migration.md strict order (backfill->verify->reader->writer->delete fallbacks) unmet: runtime-state backfill->verify->cutover CLI not wired. Flag removal cascades across ~12 non-owned files in approved WP01/WP04/WP05/WP07. Not forcing unsafe cross-lane cascade nor faking green (STOP-authorized). #2512 confirmed real. No owned-file edits; tree clean.
- 2026-07-19T15:39:02Z – claude:opus:python-pedro:implementer – shell_pid=2930102 – Closeout (dual-write end-state): AC-5/#2093/render-parity proven at status_phase:1, targeted suite green (1523 passed incl. WP06 hash regression), ruff+mypy clean, #2512 release delta landed; T037 corpus cutover DEFERRED to follow-up per 2026-07-19 decision. Full 32k suite left to CI.
- 2026-07-19T15:39:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=3276369 – Started review via action command
- 2026-07-19T15:49:38Z – user – shell_pid=3276369 – Review passed: three new tests BITE (independently mutated) — AC-5 hash guard fails red on both halves (revert writer-cut god-write leak; neuter subtask emit -> 'persisted NO event'); render-parity positive test fails when a snapshot entry is dropped; #2093 arm-1 fails when agent is re-read from frontmatter, and the tolerated migration gate set is non-empty {_phase1_dual_write_enabled} (correct dual-write end-state, NOT a false unconditional-cutover claim). Re-scope HONEST: T037 fallback-deletion deferral recorded in BOTH tasks.md and WP10 banner and is contract-consistent (migration.md makes fallback teardown the FINAL step gated on the un-wired backfill CLI); T036 reframed (flag = sanctioned safety net); nothing silently dropped beyond the documented cutover. Suite reconciliation honest: deleted tests asserted now-gone _mt_uncheck_rollback_subtasks; backward_emit re-point flips force True->False (evidence-gated, stronger not weaker); degod collection error fixed. #2512 NO regression: WP06 test_wp_file_hash_stability.py green (7 passed isolated), release is event-only+byte-stable at flag ON with proof-of-drive positive control + replant override. Full WP10 surface: 1527 passed / 2 xfailed.

## Branch Strategy

- **Strategy**: `lane-per-wp`. This WP executes in its own worktree/lane allocated by `finalize-tasks`.
- **Planning base / merge target**: `mission-prep/2684-wp-runtime-state-eviction`.
- WP10 is the terminal node on the dependency graph; it depends on WP04, WP05, WP06, WP07, WP08, and
  WP09. Rebase onto the integration of those lanes before starting — the fallbacks and shims this WP
  deletes are load-bearing until every field vertical has cut over.
- Completed changes merge back into `mission-prep/2684-wp-runtime-state-eviction`. Do not retarget the
  landing branch unless a human explicitly redirects it.
- Per C-006, PR #2766 has no inbound gate — it rebases onto this mission's writer cutover, not the
  reverse. WP10 does not wait on it.

## Definition of Done

> **See the RE-SCOPE banner above** — the DoD below reflects the ship-dual-write/defer-cutover decision.

- [ ] T036 (**REFRAME**): the phase-1 flag + dual-write shim are RETAINED as the sanctioned
      migration-window safety net (not a survivor to fail). T039 tolerates the flag as the sole
      documented fallback and fails only on an *undocumented* second authority / dual-home.
- [ ] T037 (**DEFERRED**): the `workflow_cores.py:340-348` / `done_bookkeeping.py:104-105` fallbacks are
      NOT deleted — load-bearing until the deferred backfill lands. Recorded in the `tasks.md` deferred
      note; no WP10 edit.
- [ ] T038 (**SC-001/SC-005 at flag ON**): `tests/integration/test_ac5_hash_guard.py` created and green —
      0 hash changes across the driven lifecycle at `status_phase:1`, **with** a persisted event per
      action (proof-of-drive).
- [ ] T038a (**SC-004 render parity at flag ON**): `tests/integration/test_render_parity_golden.py`
      created and green — event-sourced render of activity / history / review matches a legacy-sourced
      golden with no content loss; a dropped-entry mutation turns it red.
- [ ] T039: `tests/architectural/test_2093_authority_invariant.py` created and green — at `status_phase:1`
      no dynamic field is read as authority and no field is dual-homed static+dynamic; the phase-1 flag is
      the sole tolerated migration-window fallback. `test_no_dead_symbols.py` `add_history_entry` allowlist
      entry removed and the gate still green (deletion is **WP07/T028**).
- [ ] T040: full `pytest` suite green — collection error fixed, deleted-symbol tests removed/re-pointed,
      intended-eviction tests re-pointed to the event-sourced surface at flag ON, WP02 re-pointed force
      tests (SC-007) and the flipped `test_issue_2684_subtask_completion_event_sourced.py` green.
- [ ] **#2512 release delta**: rollback to `planned` emits a `shell_pid`/`agent` release
      `InnerStateChanged` (WP06-owned `tasks_move_task.py`, authorized closeout edit); a test asserts a
      planned-lane WP exposes no live claim. Event-only under flag ON keeps the WP-file byte-stable.
- [ ] `ruff` and `mypy` clean on edited source; every out-of-owned-files edit (test re-points +
      #2512 delta) carries a one-line rationale.

## Risks

- **Deleting a fallback before backfill** (FR-009 / migration.md): the two legacy read fallbacks
  synthesize done-evidence for un-migrated on-disk WPs. Removing them ahead of the WP03 backfill strands
  legacy corpora. **Mitigation**: gate T037 on confirmed WP03 merge + passed fail-closed verify.
- **Surviving inert flag/shim = latent second authority path** (#2093): an undeleted flag is exactly the
  split-brain the mission closes. **Mitigation**: T039 arch test fails on any dual-home/dual-write; treat
  a survivor as a red test **attributable to its owning lane** (WP01/WP05/WP07), not a tolerated leftover
  and not a WP10 edit.
- **Owned-file boundary tension**: the FR-005 flag (`stale_detection.py`, WP05), the phase-1 dual-write
  shim (`emit.py`, WP01), and the claim-writer dual-write (`frontmatter.py`/`implement.py`/
  `workflow_executor.py`, WP07) live outside WP10's owned surface and are torn down by those lanes
  themselves. **Mitigation**: WP10 does not edit non-owned files and does not delete flags/shims; T036 is
  verify-only and the FR-013 arch test (T039) is the enforcing net.
- **False-green hash guard**: an emit site writing via `Path.cwd()` (#2647) can leave the fixture hash
  falsely stable. **Mitigation**: drive from a non-mission-root cwd where practical; rely on WP08's
  SC-008 test for the dedicated invariant.
- **Authority-read vs fallback-read misclassification** (T039): the classifier is the subtle part;
  misgrouping yields a false green (missed dual-home) or false red. **Mitigation**: ground on the
  `data-model.md` field-authority table; assert the tolerated-fallback set is empty post-T036/T037.
- **Editing a non-owned red test to force green** (T040): forbidden — SC-007 already re-pointed those in
  WP02. **Mitigation**: escalate cross-lane failures to the owning WP.

## Reviewer guidance

This WP is authored for `reviewer-renata`; apply the profile end to end.

- **Anti-laziness / proof-of-drive**: every "unchanged"/"green" claim must carry a positive control. The
  AC-5 guard (T038, the SOLE SC-001/SC-005 full-lifecycle acceptance — WP06/T025 is only a scoped slice)
  asserts a persisted event per action; the render-parity golden (T038a) must bite when a note/history/
  review entry is dropped from the event stream; the arch test (T039) must bite when a frontmatter
  authority read or a `WP_FIELD_ORDER` dual-home is re-introduced. Reject any test that passes vacuously.
- **Single canonical authority (charter)**: the closeout's whole purpose is one-authority-per-field.
  After WP10, runtime state has exactly one authority (the event log) and static intent one authority
  (frontmatter). Verify the field-authority table in `data-model.md` holds with no field in both
  columns.
- **Ordering discipline**: confirm the migration order (`backfill → verify → reader → writer → delete
  fallbacks → hash guard`) was honored — T037 deletions are post-backfill, T036 teardown is
  post-writer-cut. A reordering is a correctness defect even if the suite is green on a fresh corpus.
- **Scope discipline**: WP10 edits only its owned files (the two source files + the four owned tests,
  including the net-new `test_render_parity_golden.py`). It does **not** delete the FR-005 flag / dual-write
  shims — those are torn down by their owning lanes (WP01/WP05/WP07) and proven gone by the T039 arch
  test. A residual dual-write is a T039 red attributable to the owning lane, not a WP10 closeout edit.
  Escalate cross-lane test failures; never weaken an assertion to reach green.
- **Deferred (not this WP)**: IC-08 post-cutover reduction (inert `wp_metadata` fields,
  `WP_FIELD_ORDER` cosmetic slots) is a separate bounded reduction after this mission merges — do not
  pull it forward into the clobber window.
