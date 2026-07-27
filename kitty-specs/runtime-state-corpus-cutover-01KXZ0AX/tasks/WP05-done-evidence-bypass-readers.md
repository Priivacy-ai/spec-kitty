---
work_package_id: WP05
title: Snapshot done-evidence + delete fallbacks + route bypass readers
dependencies:
- WP04
requirement_refs:
- FR-006
- FR-007
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
agent: "claude"
shell_pid: "4043644"
shell_pid_created_at: "1784558926.96"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/done_bookkeeping.py
create_intent:
- tests/specify_cli/merge/test_done_evidence_snapshot.py
- tests/specify_cli/dashboard/test_scanner_snapshot_reads.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/merge/done_bookkeeping.py
- src/specify_cli/cli/commands/agent/workflow_cores.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/dashboard/scanner.py
- tests/specify_cli/merge/test_done_evidence_snapshot.py
- tests/specify_cli/dashboard/test_scanner_snapshot_reads.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `python-pedro` implementer profile via the
`/ad-hoc-profile-load` skill. Adopt its identity, governance scope, boundaries, and the
initialization declaration it prints. Everything below is authored for that profile: TDD-first,
type-safe Python 3.11+, complexity ≤15, zero suppressions. Do not begin editing until the profile
is loaded and its init declaration is on the record.

## Objective

Complete the **IC-04** step of the cutover contract: move done-evidence / review-verdict / ownership
reads onto the reduced-snapshot seam and delete the T037 frontmatter fallbacks — but in the
**C-001 order**. The load-bearing subtlety (found by the post-planning review): the event-sourced
done-evidence read **does not exist today** — neither `merge/done_bookkeeping._extract_done_evidence`
nor the `_mark_wp_merged_done` `:295-304` fallback reads the snapshot `review` slot where the backfill
puts the approval evidence. So this WP **BUILDS** that snapshot-sourced read **first** (implemented as a
**shared review-slot reader** consumed by both the merge gate and the CLI — campsite D-14), proves it
with an event-only-mission test, and **only then** deletes the frontmatter synthesis. It also deletes
the `workflow_cores` verdict/review-field fallback and routes the ungated `agent`/`assignee`/subtask
bypass readers (`tasks_move_task`, `dashboard/scanner`) onto the snapshot accessor. Two flag branches
deferred from WP04 (IC-03) land here because they are coupled with the reroute in the **same block**.

## Context & grounding

- **Plan IC-04** (`plan.md:261-300`): the exact surface list — (a) `merge/done_bookkeeping.py`
  (`_extract_done_evidence` 95-113 **and** the `:295-304` fallback both read frontmatter, **neither**
  reads the snapshot `review` slot → wire the snapshot read **first**, then delete the synthesis —
  "real implementation, not delete + verify"); (b) `workflow_cores.resolve_review_feedback_context`
  (the verdict fallback FR-006a and the `review_status`/`review_feedback` bypass reader FR-007 are the
  **same block** → ONE edit); (c) `tasks_move_task.py` `agent`/`current_agent` ownership read; (d) the
  **MISSED** `dashboard/scanner.py::_process_wp_file` reader (`agent` :937, `assignee` :978, subtask
  checkbox count :954-965 via `read_wp_frontmatter(...).<attr>` — typed attribute access, not
  `extract_scalar`, so it escaped the #2093 debt list); plus the **reader/writer surface sweep**
  (`stale_detection._is_claiming_process_alive`, `ownership/frontmatter_source.py`, `context/resolver.py`).
- **Spec FR-006** (delete fallbacks — **(b) requires BUILDING the event-sourced done-evidence read
  first**; event-only mission, no frontmatter review → correct `DoneEvidence` before the synthesis is
  deleted), **FR-006a** (the `workflow_cores` verdict fallback), **FR-007** (route bypass readers onto
  the snapshot accessor — and the `workflow_cores` read is the **same code block** as FR-006a, ONE edit).
- **Spec C-001** (`backfill → verify → flip → delete fallbacks → reduce`; **no step precedes its
  predecessor** — deleting a fallback before the snapshot read is wired+verified strands the merge gate).
  The T018-first / T020-after ordering **inside this WP** is the local expression of C-001.
- **Key entity "Bypass readers"** (`spec.md:287`): the ungated frontmatter authority reads
  (`tasks_move_task.py`, `workflow_cores.py`, `dashboard/scanner.py`, `tasks_status_cmd.py`) routed onto
  the snapshot seam. `tasks_status_cmd.py` is IC-07/WP11's third-gate scope, **not** this WP.
- **Research D-05** (fallback-deletion order — verify the event-sourced replacement exists first;
  `done_bookkeeping` feeds the **merge** gate, so the replacement read must be exercised by a test before
  the synthesis is deleted). **D-09** (the dashboard is a bypass reader the #2093 invariant is blind to;
  IC-04 reroutes its runtime reads, keeping `agent_profile`/`role` frontmatter-sourced authored intent).
  **D-14 campsite** (this WP's tidy-firsts + consolidation seams — see below).
- **Data-model** deleted/inert table (`data-model.md:44-58`): `workflow_cores` frontmatter fallback →
  **deleted** (one block w/ bypass reader); `_extract_done_evidence` synthesis → **deleted** (after the
  event-sourced replacement is confirmed); `tasks_move_task` `agent` ownership read → **rerouted**. Snapshot
  `review` slot is a `ReviewOverride` (`{at, actor, wp_id, reason}`), reached via `wp_snapshot_state`.
- **D-14 campsite (all in-scope here):** (1) a **shared review-slot reader** across
  `done_bookkeeping._extract_done_evidence` and `workflow_cores.resolve_review_feedback_context` — both
  interpret the review slot with **different fallbacks** today, so merge-gate vs CLI can diverge on
  reviewer attribution; one seam fixes that. (2) narrow the broad `except Exception:` in
  `workflow_cores.py:299` (`read_wp_events`) to the concrete status-store exception(s). (3) delete the
  dead `frontmatter-migration:` synth branch in `done_bookkeeping` (it lives inside `_extract_done_evidence`).
  (4) keep `_mt_emit_runtime_state` (cx **15**) ≤15 by **EXTRACTING** the ownership read into a helper —
  never inline it. (5) `_process_wp_file` (cx 13) breaches on the reroute → extract a `_wp_runtime_view`
  helper (tidy-first in the SAME WP).
- **Verified surfaces** (post-#2817 tree):
  - `wp_snapshot_state(feature_dir, wp_id) -> Mapping[str, Any] | None` (`status/reducer.py:333`; exported
    from the `status` facade) — the ungated snapshot accessor; slots `agent`/`assignee`/`shell_pid`/
    `subtasks`/`review`. `ReviewOverride` (`status/models.py:329`). WP04 already made
    `wp_metadata._resolve_runtime_fields_from_snapshot` (`status/wp_metadata.py:598`) **unconditional**, so
    `read_wp_frontmatter(...).agent`/`.assignee` are transitively snapshot-sourced — but an **attribute read
    on `WPMetadata` is still a bypass** the extended #2093 detector (IC-05) flags, so route via
    `wp_snapshot_state` directly.
  - `done_bookkeeping._extract_done_evidence` reads `meta.review_status == "approved"` + `meta.reviewed_by`
    → `DoneEvidence(review=ReviewApproval(reviewer, verdict="approved", reference="frontmatter-migration:<wp>"))`;
    the `:295-304` fallback builds `ReviewApproval(reviewer=(metadata.agent or "unknown"), reference="lane-approved:<wp>")`.
  - `workflow_cores.resolve_review_feedback_context` (328-348): canonical event read via
    `latest_review_feedback_reference` (source `"canonical"`) is the snapshot-sourced path that **stays**;
    the frontmatter fallback (`extract_scalar(wp_frontmatter, "review_status"/"review_feedback")`, lines
    340-346, source `"frontmatter"`) is **deleted**. There is **no** `_phase1` predicate here — the
    "flag branch" is that frontmatter fallback itself.
  - `tasks_move_task`: ownership read `st.current_agent = extract_scalar(st.wp.frontmatter, "agent")`
    (`:313`, in `_mt_resolve_targets`); `_mt_emit_runtime_state` (`:1845`, cx 15); the flag branch
    `_mt_persist_wp_file` (`:1931-1964`, `if _phase1_snapshot_authority_active(...): return` else
    `_mt_dual_write_wp_file`) + its import `phase1_snapshot_authority_active` (`:1958`).

## Subtasks

### T018 — BUILD the event-sourced done-evidence read from the snapshot `review` slot (shared reader)

**Purpose**: The replacement is a **gap, not a given**. Build the snapshot-sourced done-evidence read in
`merge/done_bookkeeping.py` (feeding `_mark_wp_merged_done`) and implement it as a **shared review-slot
reader** also consumed by `workflow_cores` (T019), so the merge gate and the CLI can never diverge on
reviewer attribution (D-14 seam). This is **real implementation** — it does not exist today.

**Steps**:
1. Add a canonical shared reader for the snapshot `review` slot. Put it where **both** consumers can
   import one seam without a new cross-package cycle — the `status` package (alongside `wp_snapshot_state`,
   e.g. `status/wp_review.py` or a small function in `status/wp_metadata.py`) is the natural home since the
   `ReviewOverride` model and the accessor already live there. Signature:
   `resolve_snapshot_review(feature_dir, wp_id) -> ReviewOverride | None` (reduce → `wp_snapshot_state` →
   `.get("review")` → `ReviewOverride.from_dict(...)`), returning `None` when the WP carries no review slot.
2. In `done_bookkeeping`, build `DoneEvidence` **from that snapshot slot**: a present `ReviewOverride`
   yields `DoneEvidence(review=ReviewApproval(reviewer=<override.actor>, verdict="approved",
   reference=f"snapshot-review:{wp_id}"))`. The reviewer identity comes from the reduced snapshot's
   `review.actor` (the backfill seeds the historical approval there), **never** `metadata.reviewed_by`.
3. Keep the merge-path decision structure intact: `_mark_wp_merged_done` still needs an `evidence` object
   before it emits the `approved`/`done` transitions. Wire the snapshot read as the **first** evidence
   source (ahead of the lane-approved `:297-304` fallback), so an event-only mission (no frontmatter
   review) produces correct `DoneEvidence` through the merge path. Do **not** delete the `:295-304`
   frontmatter path yet — that is T020, after this read is confirmed by a test (C-001 / D-05).

**Edge cases**: a WP with no `review` slot → `resolve_snapshot_review` returns `None`, the merge path
falls through to the existing lane-approved evidence (unchanged for now); a WP with a snapshot review slot
but an empty `actor` → treat as absent (do not emit a `reviewer=""` approval).

**Validation**: the new shared reader is pure w.r.t. the snapshot (reduce → slot → typed view), cx ≤15;
a merge-path test (T023) shows an event-only mission producing a correct `DoneEvidence` **before** any
frontmatter synthesis is deleted; `ruff` + `mypy` clean.

### T019 — `workflow_cores`: delete the verdict/review-field fallback + route the bypass reader (ONE block)

**Purpose**: FR-006a (verdict/review-field fallback) and FR-007 (the `review_status`/`review_feedback`
bypass reader) are the **same block** in `resolve_review_feedback_context` — delete-and-reroute as ONE
edit. Also narrow the broad `except Exception:` (campsite).

**Steps**:
1. In `resolve_review_feedback_context` (328-348), delete the frontmatter fallback block (lines 340-346):
   the `extract_scalar(wp_frontmatter, "review_status")` / `"review_feedback")` reads and the
   `if fm_review_status == "has_feedback": ... return ..., "frontmatter"` branch. The canonical event read
   `latest_review_feedback_reference(feature_dir, wp_id)` (source `"canonical"`) is the snapshot-sourced
   authority that **stays** — post-cutover the review feedback pointer lives on `event.review_ref`, so the
   frontmatter path is dead. With the fallback gone, the function returns `(False, None, None, None)` when
   no canonical reference exists.
2. Route reviewer-attribution through the **shared reader** from T018 where `workflow_cores` needs the
   resolved reviewer/verdict, so the CLI and the merge gate interpret the snapshot `review` slot
   identically (D-14). Do not re-derive a second interpretation of the slot here.
3. `wp_frontmatter` may become unused by this function — if so, either drop the parameter (updating callers
   within owned files) or keep it only if another retained branch still needs it; do **not** leave a dead
   `extract_scalar` import or an unused-arg lint.
4. **Narrow the broad `except Exception:`** at `workflow_cores.py:299` (`read_wp_events`) to the concrete
   status-store exception(s) `read_events` actually raises (e.g. `StoreError` / `CanonicalStatusNotFoundError`
   from the `status` facade) — confirm the raised set against `status.read_events`. An empty-log read must
   still return `[]`; a genuinely-unexpected exception must propagate, not be swallowed (Sonar: no
   effect-free broad handler).

**Edge cases**: a mission with frontmatter `review_status: has_feedback` but **no** canonical
`review_ref` event → now correctly returns "no feedback present" (the frontmatter is no longer authority);
a legacy mission with neither → `(False, None, None, None)` (unchanged).

**Validation**: `grep` shows no `extract_scalar(... "review_status" / "review_feedback")` in
`workflow_cores.py`; the `except` at :299 names concrete exception types (no bare `Exception`); the
frontmatter-only-feedback case returns not-present (T023); `ruff` + `mypy` clean.

### T020 — Delete the `_extract_done_evidence` frontmatter synthesis + the dead `frontmatter-migration:` branch

**Purpose**: Remove the T037 legacy done-evidence synthesis in `done_bookkeeping` **after** T018's
snapshot-sourced replacement is confirmed by a test (C-001 / D-05). This is the delete half of FR-006(b).

**Steps**:
1. Delete `_extract_done_evidence` (95-113) — the whole frontmatter synthesis reading
   `meta.review_status`/`meta.reviewed_by`, including the dead `reference=f"frontmatter-migration:{wp}"`
   synth branch (campsite: the `frontmatter-migration:` reference is the dead branch to remove).
2. Update `_mark_wp_merged_done` (`:295`) to consume T018's snapshot-sourced evidence in place of
   `_extract_done_evidence(metadata, wp_id)`. Decide the fate of the `:297-304` lane-approved fallback:
   it may remain as a **lane-derived** last resort (it does not read the evicted review frontmatter — it
   uses `metadata.agent`, which WP04 already snapshot-sources via `read_wp_frontmatter`, and the resolved
   `lane`), OR be folded into the shared reader path. Keep merge behaviour intact for lane-approved
   missions with no review slot; the acceptance guard is "event-only mission with no frontmatter review
   still reaches `done` with correct evidence" (T023).
3. Remove any now-unused imports in `done_bookkeeping` left by the deletion (e.g. an unreferenced
   `ReviewApproval`/`DoneEvidence` local import path) so `ruff` stays clean.

**Edge cases**: the merge gate must not regress for a mission whose only evidence is the lane state
(`lane == APPROVED`, no review slot) — that path stays; the deletion removes only the **frontmatter
review synthesis**, not the lane-derived fallback.

**Validation**: `grep` shows no `_extract_done_evidence`, no `review_status`/`reviewed_by` read, and no
`frontmatter-migration:` string in `done_bookkeeping.py`; the T023 merge-path test (written first, T018)
still passes; `ruff` + `mypy` clean.

### T021 — Route `tasks_move_task` ownership read onto the snapshot + remove its flag branch

**Purpose**: Route the `agent`/`current_agent` ownership bypass reader onto the snapshot accessor and
remove the `tasks_move_task` flag branch (deferred from WP04/IC-03 because it is coupled with this reroute
in the same surface). Keep `_mt_emit_runtime_state` (cx 15) ≤15 by **extracting** — never inlining.

**Steps**:
1. Replace the ownership read `st.current_agent = extract_scalar(st.wp.frontmatter, "agent")` (`:313`, in
   `_mt_resolve_targets`) with a snapshot resolution. **Extract a small helper** (e.g.
   `_mt_resolve_current_agent(st) -> str | None`) that reads `wp_snapshot_state(st.feature_dir,
   st.task_id).get("agent")` — do **not** inline it into `_mt_emit_runtime_state` (D-14: it is at cx 15;
   inlining would push it >15). The extracted helper is the unit-testable seam.
2. Remove the flag branch: in `_mt_persist_wp_file` (`:1931-1964`) delete the
   `from specify_cli.status import phase1_snapshot_authority_active` import (`:1958`) and the
   `if _phase1_snapshot_authority_active(st.feature_dir): return` gate, making the emit path unconditional
   event-only; delete the now-dead `_mt_dual_write_wp_file` legacy god-write (`:1967+`) it guarded (WP04
   deletes the predicate + facade export; this is the last consumer — see Risks for the merge-unit
   coupling). Keep `_mt_emit_runtime_state` (the off-axis emit) unchanged in behaviour.
3. Confirm `_mt_emit_runtime_state` and `_mt_persist_wp_file` are each cx ≤15 after the edit (flag removal
   lowers the persist path; the ownership reroute lives in its own helper).

**Edge cases**: an unclaimed WP has no snapshot `agent` slot → helper returns `None` (matching the
pre-reroute "no agent in frontmatter" result); an explicit `--agent`/reassign override still flows through
the existing `st.agent` path, unaffected by the `current_agent` (prior-owner) resolution.

**Validation**: `grep` shows no `_phase1_snapshot_authority_active` / `phase1_snapshot_authority_active`
and no `_mt_dual_write_wp_file` in `tasks_move_task.py`; `st.current_agent` resolves via `wp_snapshot_state`;
both touched functions cx ≤15; `ruff` + `mypy` clean.

### T022 — Route `dashboard/scanner._process_wp_file` runtime reads onto the snapshot (+ surface sweep)

**Purpose**: Route the MISSED dashboard bypass reader's **runtime** fields (`agent`, `assignee`, subtask
completion) onto the snapshot; keep the **authored** `role`/`agent_profile`/`model` frontmatter-sourced;
extract a helper to keep `_process_wp_file` ≤15 (D-14). Then run the read-only surface sweep.

**Steps**:
1. In `_process_wp_file` (`:864`), resolve the runtime fields from the snapshot via `wp_snapshot_state`
   (not the `wp_meta_dict.<attr>` attribute reads the extended #2093 detector flags):
   - `agent` (`:937`) and `assignee` (`:978`) → the snapshot `agent`/`assignee` slots.
   - subtask completion (`:954-965`, the `count_wp_section_subtask_rows` / `count_subtask_rows` checkbox
     counting) → the snapshot `subtasks` slot (id → status; done = count of completed statuses, total =
     len). This lays the seam IC-10 (checkbox removal) later depends on; here it is the reroute of the
     dashboard reader off checkbox counting.
2. **Keep AUTHORED intent frontmatter-sourced**: `model` (`:940-946`), `agent_profile` (`:976`), and
   `role` (`:977`) stay as they are (frontmatter). Do **NOT** reroute the **resolved** `role`/`agent_profile`/
   `model` here — the resolved-actual reconstruction is WP11/IC-07 (FR-012/FR-013). `lane` already comes
   from the event log (`get_wp_lane`, `:918`) — leave it.
3. **Tidy-first extract (D-14)**: `_process_wp_file` is cx 13 and the reroute breaches 15 — extract a
   `_wp_runtime_view(feature_dir, wp_id) -> {...}` helper holding the snapshot reads (agent/assignee/
   subtasks) so `_process_wp_file` stays ≤15. WP11 later replaces this helper's body with the canonical
   `reconstruct_wp_view` reader and adds the resolved identity — this WP lays the seam, WP11 generalizes it.
4. **Surface sweep (read-only — these three are NOT in `owned_files`; do NOT edit them here):**
   - `core/stale_detection.py` — confirm `_is_claiming_process_alive` (`:231`) receives a **snapshot**-sourced
     `shell_pid` from its callers (the module already has `_read_wp_runtime_snapshot_state` at `:264`), not a
     partial/conditional frontmatter read.
   - `ownership/frontmatter_source.py` and `context/resolver.py` — confirm their `read_wp_frontmatter`-based
     reads carry **no** runtime-field (`agent`/`assignee`/`shell_pid`) authority read that survives WP04's
     unconditional `_resolve_runtime_fields_from_snapshot` reroute.
   If a genuine surviving frontmatter-authority runtime read is found in any of the three, **record it as a
   finding for the owning WP** (WP04's `read_wp_frontmatter` reroute most likely already covers the
   WPMetadata-attribute path); do not silently work around it or edit an unowned file.

**Edge cases**: a WP with no snapshot entry → `agent`/`assignee` render empty and `subtasks_done/total` = 0
(the same "no runtime state yet" result the frontend already tolerates); the encoding-error early return
(`:876-890`) is untouched.

**Validation**: `grep` shows the dashboard runtime fields resolve via `wp_snapshot_state`, not
`wp_meta_dict.agent`/`.assignee` attribute reads or checkbox counting; `model`/`agent_profile`/`role` still
frontmatter; `_process_wp_file` cx ≤15; the sweep is recorded (confirm-only); `ruff` + `mypy` clean.

### T023 — Tests (ATDD): event-only merge evidence, bypass readers on the snapshot, scanner reads

**Purpose**: Prove — **non-vacuously** — that the built read works before the fallback is deleted, that
every rerouted reader resolves the snapshot (not `extract_scalar(front, …)`), and that the dashboard shows
snapshot runtime state. Two new owned/create-intent test files.

**`tests/specify_cli/merge/test_done_evidence_snapshot.py`** (merge + non-dashboard bypass readers):
1. **Event-only merge evidence (C-001 guard, write FIRST — T018):** on a mission whose approval lives
   **only** in the snapshot `review` slot (seeded as events, **no** frontmatter `review_status`/`reviewed_by`),
   `_mark_wp_merged_done` produces a correct `DoneEvidence` and the WP reaches `done` **through the merge
   path**. This test must pass with T018 wired and **before** T020 deletes the synthesis (the C-001 proof).
2. **Shared review-slot reader unit**: `resolve_snapshot_review` returns the typed `ReviewOverride` for a
   seeded slot and `None` for a WP with no review slot; assert both `done_bookkeeping` and `workflow_cores`
   consume the **same** reader (import identity / one interpretation).
3. **`workflow_cores` frontmatter path is dead (FR-006a/FR-007):** a mission with frontmatter
   `review_status: has_feedback` but **no** canonical `review_ref` event → `resolve_review_feedback_context`
   returns `(False, None, None, None)` (frontmatter is no longer authority). A mission with a canonical
   `review_ref` → returns it with source `"canonical"`.
4. **`tasks_move_task` ownership read on the snapshot:** the extracted `_mt_resolve_current_agent` helper
   returns the snapshot `agent` slot value, and returns `None` for an unclaimed WP — not a frontmatter read.

**`tests/specify_cli/dashboard/test_scanner_snapshot_reads.py`** (dashboard reader):
1. **Snapshot authority for runtime fields:** a WP whose frontmatter `agent`/`assignee` **diverge** from
   the snapshot slots renders the **snapshot** values via `_process_wp_file` (proves snapshot authority,
   not the WPMetadata attribute).
2. **Subtask completion from the snapshot slot:** a WP with a snapshot `subtasks` slot renders
   `subtasks_done`/`subtasks_total` from that slot (not `tasks.md` checkbox counting).
3. **Authored intent unchanged:** `model`/`agent_profile`/`role` still render the frontmatter (authored)
   values — the resolved identity is explicitly **out of scope** here (WP11).

**Validation**: both files pass per-file (commands below); test 1 of the merge file **fails** if the
snapshot read is removed and would-pass only via frontmatter (non-vacuous — assert on an event-only mission
with no frontmatter review); no test mocks the reducer/`wp_snapshot_state` to force a pass (exercise real
seeded event logs over real fixtures).

## Branch Strategy

Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; this WP's completed changes merge
back into `feat/runtime-state-corpus-cutover` (both `planning_base_branch` and `merge_target_branch`).
Execute in the workspace `spec-kitty implement WP05` prepares — the execution worktree/branch is the
computed lane from `lanes.json` (consume the resolved workspace path; do not reconstruct it by hand).

**MERGE-UNIT atomicity (with WP03/WP04):** IC-01b (WP03 — dogfood corpus backfill/seeds), IC-03 (WP04 —
unconditional flip + predicate deletion), and IC-04 (**this WP**) MUST land in **one merge unit** with the
edges `WP03 → WP04 → WP05` honoured during WP-by-WP merge to local main. If WP05's fallback deletion
reaches local main before WP03 has committed this repo's seed events **or** before WP04 has flipped the
readers, the merge gate reads an **empty snapshot** → degraded/absent done-evidence and the suite goes red.
The C-001 order + the T018-first / T020-after sequencing **inside** this WP is the local guard; the
merge-unit edges are the cross-WP guard.

## Test strategy

Run each owned test file **individually** with a timeout — never the whole `tests/architectural/`
directory (it hangs). Use `uv run` (bare `python` resolves a sibling checkout → false greens). Because
`done_bookkeeping` is a **merge-path** change, the event-sourced done-evidence read (T018) must be
exercised by the merge-path test **before** T020 deletes the synthesis (D-05):

```bash
timeout 600 uv run --extra test python -m pytest -p no:cacheprovider tests/specify_cli/merge/test_done_evidence_snapshot.py
timeout 600 uv run --extra test python -m pytest -p no:cacheprovider tests/specify_cli/dashboard/test_scanner_snapshot_reads.py
```

Also run the existing merge / move-task / dashboard suites that touch these surfaces per-file to catch a
behaviour regression (e.g. the merge done-bookkeeping tests and the move-task tests) before declaring done.

Quality gates (must be clean, no suppressions):

```bash
uv run ruff check src/specify_cli/merge/done_bookkeeping.py src/specify_cli/cli/commands/agent/workflow_cores.py src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/dashboard/scanner.py
uv run mypy src/specify_cli/merge/done_bookkeeping.py src/specify_cli/cli/commands/agent/workflow_cores.py src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/dashboard/scanner.py
```

## Definition of Done

- [ ] **The event-sourced done-evidence read is BUILT** (T018) — `done_bookkeeping` synthesizes
  `DoneEvidence` from the snapshot `review` slot via a **shared review-slot reader**, and an event-only
  mission (no frontmatter review) reaches `done` with correct evidence through the merge path (FR-006,
  C-001, D-05).
- [ ] **C-001 order honoured**: the snapshot read (T018) is confirmed by a test **before** the frontmatter
  synthesis is deleted (T020) — `_extract_done_evidence` + the dead `frontmatter-migration:` branch are
  gone, with no `review_status`/`reviewed_by` authority read left in `done_bookkeeping.py`.
- [ ] **FR-006a + FR-007 as ONE block**: the `workflow_cores` frontmatter `review_status`/`review_feedback`
  fallback is deleted and reviewer attribution routes through the shared reader; the canonical `review_ref`
  event read remains the authority; frontmatter-only feedback now returns not-present (FR-006a/FR-007).
- [ ] The broad `except Exception:` in `workflow_cores.py:299` is narrowed to the concrete status-store
  exception(s) (campsite; Sonar — no effect-free broad handler).
- [ ] `tasks_move_task` ownership read (`agent`/`current_agent`) resolves `wp_snapshot_state`, via an
  **extracted** helper; its flag branch (`_phase1` gate + `_mt_dual_write_wp_file` + the facade import) is
  removed; `_mt_emit_runtime_state` and `_mt_persist_wp_file` are each cx ≤15 (FR-007, D-14).
- [ ] `dashboard/scanner._process_wp_file` runtime reads (`agent`, `assignee`, subtask completion) are
  snapshot-sourced via an extracted `_wp_runtime_view` helper (`_process_wp_file` cx ≤15); **authored**
  `role`/`agent_profile`/`model` remain frontmatter-sourced; `lane` still from the event log (FR-007, D-09,
  D-14).
- [ ] The surface sweep (`stale_detection`, `ownership/frontmatter_source`, `context/resolver`) is recorded
  as confirm-only; any surviving authority read is filed as a finding, not worked around (no unowned edits).
- [ ] Both owned test files exist and pass per-file; the merge-path event-only test is non-vacuous (fails
  if the snapshot read is removed); `ruff` + `mypy` clean with zero new `# noqa` / `# type: ignore` /
  per-file ignores.

## Risks & out-of-map edits

- **`dashboard/scanner.py` is ALSO edited later by WP11 (IC-07)** — WP11 does the tidy-first extract +
  reader reroute to the canonical `reconstruct_wp_view` and adds the resolved `role`/`agent_profile`/`model`
  identity. **This WP owns `scanner.py`**; WP11's later touch is a **noted out-of-map** future edit, not this
  WP's. Lay the `_wp_runtime_view` seam so WP11 replaces its body rather than re-plumbing the reader.
- **Deleting done-evidence synthesis before the snapshot read is wired drops the merge gate to degraded
  attribution** (`metadata.agent → "unknown"` once `agent` is snapshot-sourced). The **C-001 order** +
  the **T018-first / T020-after** sequencing + the non-vacuous event-only merge test are the guard — do NOT
  reorder T020 ahead of T018/T023.
- **Merge-unit coupling with WP04:** WP04 (IC-03) deletes the `_phase1_snapshot_authority_active` predicate
  and drops the `status/__init__.py` facade export. The **last consumer** of that export is
  `tasks_move_task.py` (`phase1_snapshot_authority_active` import, `:1958`) — removed **here** (T021).
  Because WP05 depends on WP04 and both land in one merge unit, sequence the predicate deletion and this
  consumer removal so no intermediate branch imports a deleted symbol; WP04 does **not** touch
  `tasks_move_task`'s flag branch (deferred here). WP05 does **not** touch `emit.py`, the other 11 flag
  sites, `_legacy_lane_mirror_enabled`, or `tasks_status_cmd.py` (IC-03/IC-05/IC-07 scope).
- **Do NOT reroute the resolved identity here** — authored `role`/`agent_profile`/`model` stay
  frontmatter-sourced; the resolved-actual event-sourcing is WP11/IC-07. Touching it here is scope creep.

## Reviewer guidance (adversarial)

- **Was the replacement actually BUILT and exercised through the merge gate?** Confirm the snapshot-sourced
  done-evidence read exists (not just the deletion), and that a **real event-only mission** (seeded review
  slot, no frontmatter `review_status`/`reviewed_by`) reaches `done` with correct `DoneEvidence` via
  `_mark_wp_merged_done`. Reject a test that mocks `wp_snapshot_state` / the reducer to force a pass, or that
  only exercises `_extract_done_evidence` in isolation instead of the merge path.
- **Is C-001 honoured inside the WP?** Verify the merge-path test would pass with T018 wired **before** T020
  deletes the synthesis (the deletion is not what makes the test green). Confirm no `frontmatter-migration:`
  string, no `review_status`/`reviewed_by` read, and no `_extract_done_evidence` remain in `done_bookkeeping.py`.
- **Is the FR-006a/FR-007 change ONE edit, not two?** In `workflow_cores.resolve_review_feedback_context`,
  confirm the frontmatter `review_status`/`review_feedback` fallback is deleted as a single block (not two
  separate edits to the same lines) and that reviewer attribution flows through the **shared** reader — the
  merge gate and the CLI must interpret the review slot identically. Confirm the `:299` `except` names
  concrete exception types.
- **Do any evicted-field frontmatter authority reads remain in these four files?** `grep` each owned source
  for `extract_scalar(... "agent" / "assignee" / "review_status" / "review_feedback")` and for
  `wp_meta_dict.agent`/`.assignee` attribute reads — every runtime read must resolve `wp_snapshot_state`.
  Authored `role`/`agent_profile`/`model` are the **only** frontmatter reads allowed to survive.
- **Complexity + tidy-first:** confirm the ownership read is in an extracted helper (not inlined into the
  cx-15 `_mt_emit_runtime_state`), `_process_wp_file` is ≤15 behind `_wp_runtime_view`, and no `# noqa` /
  `# type: ignore` was added to pass ruff/mypy.

## Activity Log

- 2026-07-20T14:00:09Z – claude – shell_pid=3956467 – Assigned agent via action command
- 2026-07-20T14:46:56Z – claude – shell_pid=3956467 – Ready for review: IC-04 snapshot done-evidence + T037 fallback deletions + bypass reader reroutes (T018-T023). 14/14 owned tests green; ruff+mypy clean; cx<=15.
- 2026-07-20T14:48:51Z – claude – shell_pid=4043644 – Started review via action command
- 2026-07-20T14:50:33Z – user – shell_pid=4043644 – Approved: C-001 done-evidence order, workflow_cores one-edit, WP04 site fixed, 14 tests green
