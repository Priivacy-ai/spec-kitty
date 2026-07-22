---
work_package_id: WP04
title: Unconditional reader/writer cutover (flip flag, delete predicate)
dependencies:
- WP03
requirement_refs:
- FR-004
- FR-005
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
agent: "claude"
shell_pid: "3914998"
shell_pid_created_at: "1784555187.93"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/emit.py
create_intent:
- tests/specify_cli/status/test_cutover_byte_stability.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/status/emit.py
- src/specify_cli/status/__init__.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/tasks_transition_core.py
- src/specify_cli/cli/commands/agent/tasks_shared.py
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/core/stale_detection.py
- src/specify_cli/task_utils/support.py
- src/specify_cli/frontmatter.py
- src/specify_cli/task_metadata_validation.py
- tests/specify_cli/core/test_shell_pid_claim_baseline.py
- tests/specify_cli/cli/commands/test_implement_runtime_frontmatter_claim.py
- tests/specify_cli/status/test_cutover_byte_stability.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Unconditional reader/writer cutover (flip flag, delete predicate)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the **`python-pedro`** agent profile (role: `implementer`) **before doing any work**, and behave according to its guidance for the whole WP. This is a heterogeneous per-site refactor across production runtime paths plus a writer cutover — hold an implementer's rigour on every collapse: each site is read for its exact intent, not pattern-matched, and every deleted branch is proven dead by a test in this same WP (ATDD-first, C-011).

## Objective

Make the reduced event-log snapshot the **unconditional** authority for work-package runtime state. Concretely:

- **Delete** the phase-1 predicate `_phase1_snapshot_authority_active` (`status/emit.py`) and its status-facade export (`status/__init__.py`) — C-002 / FR-005 (T013).
- **Collapse the flag-OFF (legacy / dual-write) branch** at every call site so the snapshot path is the only path — FR-004, a heterogeneous per-site refactor (T014).
- **Cut over the runtime WRITER** so a runtime-state transition writes **zero bytes** to `tasks/WP##.md` — NFR-003 / SC-004 (T015).
- **Prove** the kept lane mirror's activation is behaviour-neutral (T016) and byte-stability holds (T017).

This is IC-03 (plan lines 237–259). It runs **after** WP03 has committed this repo's seed events (C-001 order) — without those seeds, unconditional readers hit an empty snapshot and local main goes red the instant this lands. WP04 is the "flip reader+writer + delete predicate" step of the contract `backfill → verify(FAIL-CLOSED) → flip reader+writer → delete fallbacks → reduce`; the *fallback deletion* + bypass-reader reroute is WP05 (IC-04), the *invariant hardening* is a later WP (IC-05).

**Why the writer cutover is not optional (NFR-003).** Deleting the *readers'* flag alone does not make `tasks/WP##.md` byte-stable: the claim path still writes `shell_pid`/`agent`/activity-log lines into the WP file behind the `_shell_pid_dual_write_active` gate (itself `not _phase1_...`). With the predicate gone that gate must be **removed**, not defaulted — otherwise a runtime transition still mutates the WP file and SC-004 fails. Readers and writer cut over together.

**In scope:** the 11 WP04 sites + the one out-of-map `wp_metadata.py` flag branch, the predicate + facade deletion, the three dual-write writer blocks, the template-emitter writer, the two proofs.
**Out of scope (WP05 / later):** `tasks_move_task.py` and `workflow_cores.py` (their flag/fallback removal is coupled to the ownership/verdict reroute), `merge/done_bookkeeping.py` fallback deletion, the #2093 invariant hardening, the split-suite reconciliation.

## Context & grounding

**Where this sits in the contract (C-001).** The migration spine is `backfill → verify(FAIL-CLOSED) → flip reader+writer → delete fallbacks → reduce`. WP03 did the backfill+verify+flip on this repo's corpus; **WP04 is the "flip reader+writer + delete predicate" step**; WP05 (IC-04) does the fallback deletion + bypass-reader reroute; IC-05 hardens the invariant. WP04 must not reach into WP05's territory (`tasks_move_task.py`, `workflow_cores.py`, `merge/done_bookkeeping.py`, the #2093 invariant test) — it only removes the flag and cuts the writer.

**Plan IC-03 (plan lines 237–259) — the governing concern.** Relevant requirements:

- **FR-004** — remove the flag-OFF (legacy / dual-write) branch across **all 12 call sites in 11 files** (the brief's "~10" was undersized; the real surface adds `tasks_status_cmd.py` and the double site in `support.py`); remove each paired local `from specify_cli.status import …` import too.
- **FR-005** — delete `_phase1_snapshot_authority_active` (`status/emit.py`) and its status-facade export (`status/__init__.py` alias `phase1_snapshot_authority_active` + `__all__` entry). `_legacy_lane_mirror_enabled` is **kept** (C-004).
- **NFR-003** — after cutover a runtime-state transition writes **0 bytes** to `tasks/WP##.md` (byte-identical before/after).
- **C-002** — the end-state is a genuine unconditional flip: the predicate is **deleted**, not merely defaulted ON; no residual runtime toggle remains.
- **C-004** — `_legacy_lane_mirror_enabled` is retained (the `lane` field is still frontmatter-authored; evicting it is a separate follow-up).

**Spec US2 (spec lines 73–96) — the headline outcome.** After cutover the snapshot is the authority for WP runtime state everywhere; the phase-1 flag and its flag-OFF (dual-write / frontmatter-authority) branch no longer exist; a runtime transition writes to the event log only and never mutates `tasks/WP##.md`. Success criteria:

- **SC-002** — `_phase1_snapshot_authority_active` and its facade export have **zero** occurrences after this mission.
- **SC-004** — a runtime-state transition writes **0 bytes** to `tasks/WP##.md` (byte-identical) with the flag removed.

**research D-02 — `status_phase` is NOT inert (corrected post-planning).** Deleting the *reader-authority* predicate does **not** make `status_phase` inert:

- The kept `_legacy_lane_mirror_enabled` (`emit.py:413-424`, retained by C-004) **still reads `status_phase`** via `_read_status_phase`.
- Today every mission was `status_phase=0` → lane mirror OFF; WP03 flipped this repo's corpus to `status_phase>=1`, which **activates** the lane mirror for those missions.
- Therefore the flip has a **live consequence**, and WP04 must carry a regression proving lane behaviour is unchanged by the activation (T016). This is the load-bearing subtlety of the whole WP.

**research D-06 — this is NOT a DIRECTIVE_035 bulk edit.** No `occurrence_map.yaml`. Each site collapses its `if predicate: … else: …` **differently** — some keep the snapshot branch, some are early-returns, `support.py` has two distinct sites, two sites sit inside `_shell_pid_dual_write_active` wrapper helpers, one (`stale_detection`) uses a module-level import. It is a heterogeneous per-site refactor, not a mechanical same-string replacement.

**research D-14 — campsite discipline (fold, don't defer).** At each collapsed site:

- remove the now-orphan paired local `from specify_cli.status import phase1_snapshot_authority_active …` import (local at most sites; module-level at `stale_detection.py:29`);
- delete the orphan flag-wrapper functions `_shell_pid_dual_write_active` (`implement.py` + `workflow_executor.py`);
- scrub dead docstring / comment refs to `_phase1_snapshot_authority_active` — after deletion they name a gone symbol;
- do **not** let this bleed into a god-module degod (`implement.py` 1863 / `workflow_executor.py` 2044 are surgical-only per D-14).

**data-model — deleted / inert table (data-model lines 44–58) + invariants:**

- `_phase1_snapshot_authority_active` (predicate) → **deleted** + facade alias/`__all__` dropped (IC-03).
- `_legacy_lane_mirror_enabled` → **kept** (`lane` still frontmatter-authored) — C-004, out of scope.
- **INV-2 (single authority)** — after cutover no code path reads WP runtime slots from frontmatter for authority; every read resolves the snapshot.
- **INV-3 (byte-stability)** — a runtime-state transition writes 0 bytes to `tasks/WP##.md`.

**Behaviours the collapse must PRESERVE (not the flag — do not delete these):**

- The `feature_dir is None` early return in `tasks_transition_core._snapshot_unchecked_subtasks` (the WP02 runtime-window guard).
- The "snapshot slot silent → legacy `tasks.md` roster" fallbacks in `tasks_shared.py` and `WorkPackage` — the C-001 symmetric window so an untouched WP's already-checked rows are not misread as incomplete.
- The `total == 0 → True` ("nothing to block on") branch in the subtask-completion readers.
- Fail-closed semantics: an absent snapshot entry still returns the conservative state (`False`/`None`/`{}`) the site already used — the collapse changes *which* source, never the fail-closed posture.

### Exact site list (from `grep -rn "_phase1_snapshot_authority_active\|phase1_snapshot_authority_active" src/`)

FR-004's **12 call sites across 11 files** = the 12 invocations of the predicate. WP04 owns **11**; the 12th (`tasks_move_task.py`) is WP05's.

| # | File | Site | Owner |
|---|------|------|-------|
| 1 | `status/emit.py:325` | `_infer_subtasks_complete` — flag branch **+ delete the predicate def (401-410) + the 390-400 comment block** | **WP04** |
| 2 | `status/__init__.py:80,237` | facade `_phase1_snapshot_authority_active as phase1_snapshot_authority_active` import **+ `__all__` entry** | **WP04** |
| 3 | `cli/commands/implement.py:1489-1503` | `_shell_pid_dual_write_active` wrapper (writer gate) | **WP04** |
| 4 | `cli/commands/agent/tasks_transition_core.py:461` | `_snapshot_unchecked_subtasks` early-return | **WP04** |
| 5 | `cli/commands/agent/tasks_shared.py:503` | subtask-completion re-source | **WP04** |
| 6 | `cli/commands/agent/tasks_mark_status.py:283` | `legacy_checkbox_write` gate | **WP04** |
| 7 | `cli/commands/agent/tasks_status_cmd.py:191` | `_st_gated_runtime_fields` (agent/shell_pid) | **WP04** |
| 8 | `cli/commands/agent/workflow_executor.py:122-137` | `_shell_pid_dual_write_active` wrapper (writer gate) | **WP04** |
| 9 | `core/stale_detection.py:307` | shell_pid liveness gate (**module-level import at :29**) | **WP04** |
| 10 | `task_utils/support.py:354` | activity-log fold gate (site A) | **WP04** |
| 11 | `task_utils/support.py:412` | `WorkPackage._snapshot_wp_state` gate (site B) | **WP04** |
| 12 | `cli/commands/agent/tasks_move_task.py:1962` | ownership read + flag branch | **WP05 (IC-04) — do NOT touch** |
| — | `status/wp_metadata.py:622-626` | flag branch (imports the predicate **directly from `emit`**) — **owned by WP07, but its flag branch is yours to remove here** (out-of-map, see Risks) | **WP04 edit** |

- **Deferred to WP05 (do NOT edit):**
  - `tasks_move_task.py` (site #12) — its `_phase1_snapshot_authority_active` branch (1962) is coupled with the `agent`/`current_agent` ownership reroute onto the snapshot accessor; WP05 removes both together (and extracts, not inlines, because `_mt_emit_runtime_state` is already at cx 15 — D-14).
  - `workflow_cores.py` — a *separate* frontmatter verdict / `review_status` / `review_feedback` fallback in `resolve_review_feedback_context` (**not** a `_phase1` flag site, so not in the grep). WP05 deletes the fallback and reroutes it in one block (FR-006a + FR-007 are the same code).
  - Both are IC-04 / WP05. WP04 leaves them entirely alone.
- **`status/wp_metadata.py` is the load-bearing out-of-map edit:** it does `from specify_cli.status.emit import _phase1_snapshot_authority_active` (line 622) — importing the **private predicate directly from `emit`**, not the facade. Deleting the predicate therefore *breaks this import* unless its flag branch is removed in the same change. WP07 owns the file's broader inert-field work; WP04 must remove **only** the flag branch (622-626) here so the deletion lands atomically. Record it in Risks.

### Verified code facts (grep + inspection, post-#2817 tree)

These are the exact mechanics you are editing — confirmed against source, not inferred:

- **The reader predicate** is `_phase1_snapshot_authority_active(feature_dir) -> bool` (`emit.py:401-410`): `phase = _read_status_phase(feature_dir); return phase is not None and phase >= 1`.
- **The kept twin** `_legacy_lane_mirror_enabled` (`emit.py:413-424`) is byte-for-byte the same predicate body — it also does `phase is not None and phase >= 1` via `_read_status_phase`. Identical behaviour today; the split exists so the lane mirror can be retired independently later. **This is why the flip activates the mirror** (research D-02).
- **The facade** re-exports it as a public alias: `status/__init__.py:80` (`_phase1_snapshot_authority_active as phase1_snapshot_authority_active`) + `status/__init__.py:237` (`__all__`).
- **The writer gate** `_shell_pid_dual_write_active(feature_dir)` (`implement.py:1489-1503`, `workflow_executor.py:122-137`) is literally `return not _phase1_snapshot_authority_active(feature_dir)`. So with the predicate deleted, the dual-write mirror must be **removed**, not defaulted — otherwise the WP file is still mutated on a claim.
- **The writer call sites** are `write_shell_pid_claim(...)` at `implement.py:1787`, `workflow_executor.py:754` (implement-claim), `workflow_executor.py:1526` (review-claim) — all inside `if _shell_pid_dual_write_active(...)` blocks. The **only** other caller is `tasks_move_task.py:1442/1973` (WP05).
- **The template-emitter writer** is `task_metadata_validation.repair_lane_mismatch` (MIGRATION-ONLY) which writes `shell_pid: "…"` into the activity-log history at `:141` and the parsed-list dict at `:156` (param default `:86`).
- **`wp_metadata.py:622`** imports the predicate **directly from `emit`** (bypassing the facade) — the reason its flag branch must be removed in this same change.
- **The snapshot helper `_infer_subtasks_complete_from_snapshot` (`emit.py:338-360`) stays** — it is the branch you keep; only its caller `_infer_subtasks_complete` loses the flag gate. Do not fold the two together unless it keeps complexity ≤15 and preserves the `total == 0 → True` branch.
- **The grep also lists pure docstring/comment refs** (`stale_detection.py:11-13`, `tasks_transition_core.py:138/442`, `emit.py:305/393/416`, `task_utils/support.py:341/392`, `wp_metadata.py:607`) — these are D-14 campsite scrubs, not code branches, but they must all go so no surviving line names the deleted symbol.
- **`stale_detection.py` imports TWO names on adjacent lines** (`:29` the predicate, `:30` `wp_snapshot_state as _wp_snapshot_state`) — remove only `:29`; `:30` is still used by the snapshot read you keep.

## Subtasks

Work them in order: **T013** (delete the predicate) makes every un-collapsed site a compile/import error, which is a *feature* — it surfaces any site you missed. **T014** collapses all 11. **T015** cuts the writer. **T016/T017** prove the result. Do not merge a tip where T013 is done but a site is left calling the deleted symbol.

- [ ] **T013 [FR-005 / C-002 / C-004] Delete the predicate + facade export.**
  - `status/emit.py`: delete the `_phase1_snapshot_authority_active` function (401-410) **and** the 390-400 comment block that frames the "two distinct migration concerns" split (that framing is obsolete once one of the two is gone — re-point any surviving prose to the kept lane-mirror gate).
  - **KEEP `_legacy_lane_mirror_enabled` (413-424) and `_read_status_phase` (368-387) verbatim** — C-004. They still gate the lane mirror and read `status_phase`; deleting or altering either silently disables the mirror corpus-wide.
  - Scrub the dead cross-ref to `_phase1_snapshot_authority_active` inside `_legacy_lane_mirror_enabled`'s docstring (416) so the kept function does not name a deleted symbol.
  - `status/__init__.py`: drop the aliased import line (80, `_phase1_snapshot_authority_active as phase1_snapshot_authority_active`) and the `__all__` entry (237, `"phase1_snapshot_authority_active"`).
  - Acceptance: `grep -rn "_phase1_snapshot_authority_active\|phase1_snapshot_authority_active" src/` returns **only** WP05's `tasks_move_task.py` (which WP05 removes in the same merge unit) — zero occurrences in WP04's owned files (SC-002). C-002: the predicate is **deleted**, never defaulted to `True`; no residual runtime toggle remains.
- [ ] **T014 [FR-004 / D-06 / D-14] Collapse the flag-OFF branch at each of your 11 sites.** For each site (all EXCEPT `tasks_move_task.py`), **keep the snapshot branch, delete the legacy branch**, then campsite-clean: remove the now-orphan paired `from specify_cli.status import phase1_snapshot_authority_active …` local import, delete orphan wrapper functions, and scrub dead docstring/comment refs. Each collapse is **bespoke** (D-06) — read each site for its exact intent, do not pattern-match:

  - **`emit.py::_infer_subtasks_complete` (325).**
    - Collapse: delete the `tasks.md`-counting else (328-335); the body becomes an unconditional call to `_infer_subtasks_complete_from_snapshot(feature_dir, wp_id)`.
    - Campsite: rewrite the two-path docstring (303-323) to describe the single snapshot path; drop the "flag ON / flag OFF" framing.
  - **`tasks_transition_core.py::_snapshot_unchecked_subtasks` (461).**
    - Collapse: delete the "not phase-1 → return `None`" early-return; the `feature_dir is None → return None` guard (452-454) **stays** (that is the WP02 runtime-window guard, not the flag).
    - Campsite: remove the local predicate import (458); re-point the docstring bullet (442-443).
  - **`tasks_shared.py` (503).**
    - Collapse: delete the "flag OFF → legacy `tasks.md` roster" return (503-506); the snapshot read with its legacy *silent-slot* fallback tail (508-527) **stays** (C-001 symmetric window — an untouched WP's already-checked rows must not read as incomplete).
    - Campsite: remove the local predicate import (501); rewrite the flag-ON/flag-OFF docstring block (440-458).
  - **`tasks_mark_status.py` (283).**
    - Collapse: `legacy_checkbox_write` becomes constant-False semantics — the CHECKBOX resolver always runs against the **throwaway** `list(lines)` copy so the checkbox byte is event-sourced-only and never persisted to `tasks.md` (a **writer-relevant** collapse, reinforcing T015).
    - Campsite: remove the module-body predicate import (265); rewrite the dual-write comment (276-282).
  - **`tasks_status_cmd.py::_st_gated_runtime_fields` (191).**
    - Collapse: delete the `extract_scalar(front, "agent")` / `extract_scalar(front, "shell_pid")` frontmatter fallback (199-202); resolve agent/shell_pid from `wp_snapshot_state` unconditionally. A `wp_id`-present guard may remain (an unidentifiable WP has no snapshot key).
    - Campsite: remove the local predicate import (189); rewrite the docstring (181-187).
  - **`workflow_executor.py` (122-137) + `implement.py` (1489-1503).**
    - Collapse: delete each `_shell_pid_dual_write_active` **wrapper function** entirely (it is `return not _phase1_snapshot_authority_active(...)`) and every call site — the actual dual-write block deletion is T015.
    - Campsite: remove the local predicate imports inside those wrappers; scrub the WP07-referencing docstrings (they describe a teardown that WP04 now performs).
    - Note: these two wrappers are duplicated by design (lower-layer/agent-package boundary) — delete **both**, do not consolidate into a shared import (that would recreate the boundary crossing the duplication avoids).
  - **`stale_detection.py` (307).**
    - Collapse: reduce `if feature_dir is None or not _phase1_snapshot_authority_active(feature_dir):` to `if feature_dir is None:`; the snapshot read below becomes the sole authority for shell_pid/baseline.
    - Campsite: **remove the module-level import at line 29** (this is a top-level import, not a local one — distinct from every other site); re-point the module docstring (11-17).
  - **`task_utils/support.py` — TWO distinct sites (354 and 412).**
    - Site A (354, `_activity_log_rows`): the activity-log fold no longer gates on the flag — snapshot transition/`note` entries are folded whenever `feature_dir`/`wp_id` are supplied; the `feature_dir is None or wp_id is None → return entries` guard (349-350) stays. Remove the local predicate import (352, carries `# noqa: PLC0415` — the noqa goes with it).
    - Site B (412, `WorkPackage._snapshot_wp_state`): delete the "flag OFF → cache `None`, return `None`" fallback (412-415); an absent snapshot entry is now authoritative `{}` (never a signal to fall back to frontmatter). Remove the local predicate import (407, `# noqa: PLC0415`).
  - **`wp_metadata.py` (622-626) — OUT-OF-MAP (see Risks).**
    - Collapse: remove the flag branch (625-626) and the **direct-from-`emit` import** (622, `from specify_cli.status.emit import _phase1_snapshot_authority_active`) so the snapshot re-source runs unconditionally; keep the rest of the function for WP07.
- [ ] **T015 [NFR-003 / SC-004] Writer cutover — stop writing runtime fields to `tasks/WP##.md`.** Byte-stability needs the WRITER cut over, not just the readers. Today the dual-write mirror is gated behind `_shell_pid_dual_write_active` (which is `not _phase1_snapshot_authority_active`); with the predicate deleted the mirror must be **removed**, not left dangling.

  - **`implement.py:1781-1788` (the `spec-kitty implement` pre-write).** The `if _shell_pid_dual_write_active(feature_dir):` block reads the WP file, `write_shell_pid_claim(_wp_front, os.getppid())`, and writes it back. **Delete the whole block** — after this, `implement` mutates no WP-file runtime bytes; the claim rides the event/`policy_metadata` sidecar only.
  - **`workflow_executor.py:751-...` (implement-claim).** The `if _shell_pid_dual_write_active(feature_dir):` block does `set_scalar(wp.frontmatter, "agent", agent)` + `write_shell_pid_claim(...)` + `append_activity_log(...)` and writes the WP file. **Delete the whole block** so the claim is a byte-identical no-op on the WP file (the WP07 comment at 744-750 already anticipates this teardown).
  - **`workflow_executor.py:1521-...` (review-claim).** The parallel `if _shell_pid_dual_write_active(feature_dir):` block (re-reads the file, mirrors `agent`/shell_pid, appends the "Started review" history entry, writes back). **Delete the whole block** — the review claim writes 0 bytes to the WP file.
  - **`frontmatter.py::write_shell_pid_claim` (321) — RETIRE IT IN THIS WP.** ⚠️ **Post-tasks gate correction:** the earlier claim that `tasks_move_task.py::_mt_persist_wp_file` still calls this is a **phantom**. A live `grep -n 'write_shell_pid_claim('` returns **only** `implement.py:1787`, `workflow_executor.py:754`, `workflow_executor.py:1526` (all WP04-owned) plus test callers; `tasks_move_task.py:1442/1973` are **docstrings**, not calls, and `_mt_persist_wp_file` does not call it. So once WP04 deletes its three dual-write blocks, `write_shell_pid_claim` has **zero** non-test src callers → it is a callerless exported symbol (`frontmatter.py:401 __all__`) → `test_no_dead_symbols` **reds** it. WP04 owns `frontmatter.py` (WP05 does not), so **WP04 must fully retire it here**: delete the `write_shell_pid_claim` def, remove it from `__all__` (401), and rewrite the caller-inventory docstring (334-339) to state **zero remaining callers**. Do **NOT** defer to WP05 (it has no caller to drop). Reconcile its test callers in the same WP (see T017.5).
  - **`task_metadata_validation.py:86,141,156` (MIGRATION-ONLY `repair_lane_mismatch`).** This legacy-repair path bakes a `shell_pid: "…"` line into the activity-log history entry it writes into WP frontmatter (141) and the parsed-list dict (156), with the `shell_pid: str = ""` param at 86. Stop emitting the `shell_pid` field into that generated template so no repair/template path can re-introduce a runtime field into `tasks/WP##.md`. (It is MIGRATION-ONLY, not an active runtime write — but it is in `owned_files` and completes the writer sweep.)
- [ ] **T016 [C-004 / research D-02] Lane-mirror activation regression (non-vacuous).**
  - The load-bearing subtlety: deleting the reader predicate does not make `status_phase` inert. The kept `_legacy_lane_mirror_enabled` still reads it, so flipping a mission `0 → 1` (WP03 did this to the dogfood corpus) **activates the lane mirror** for it — a live consequence of the cutover, not a no-op.
  - Prove that this activation **does not change lane behaviour**: the canonical lane still comes from the event log; the mirror only writes the transitional frontmatter `lane` field and never changes what a lane *read* resolves to.
  - The test must actually exercise **both** `status_phase=0` (mirror OFF) and `status_phase=1` (mirror ON) for the same mission fixture and assert the **resolved lane is identical** across them — a non-vacuous guard that would fail if activation silently altered a lane read.
  - Do **NOT** touch `_legacy_lane_mirror_enabled` or `_read_status_phase` (C-004). If activation proves genuinely problematic, record a decoupling **follow-up** (lane-mirror eviction is a separate concern, still out of scope here) — do not fix it in this WP.
- [ ] **T017 [ATDD / SC-002 / SC-004] Tests.** ATDD-first (C-011) — each deleted branch is proven dead by a test in this WP. In `tests/specify_cli/status/test_cutover_byte_stability.py` (new):
  1. **Byte-stability (SC-004 / NFR-003) — the headline.** Build a fixture mission whose `status_phase` is cut over (seeded snapshot, `status_phase >= 1`). Capture the exact bytes of `tasks/WP##.md` **before**, drive a **real** runtime transition (claim / move-task / mark-status), then assert the file is **byte-identical after** — while the event log gains the event and the snapshot reflects it. Use a real before/after file read (`path.read_bytes()` compare), **not a mock** (the reviewer checks this explicitly).
  2. **Predicate gone (SC-002).** An in-test assertion that `_phase1_snapshot_authority_active` / `phase1_snapshot_authority_active` have **0 occurrences** in WP04's owned source files (scope the grep to WP04's files so the assertion is green on the WP04 tip even before WP05 removes `tasks_move_task.py`), and that `from specify_cli.status import phase1_snapshot_authority_active` now raises `ImportError`, and `"phase1_snapshot_authority_active"` is not in `specify_cli.status.__all__`.
  3. **Per-site unconditional-read behaviour.** Representative assertions that each of these reads the snapshot with **no** flag branch:
     - `emit._infer_subtasks_complete` → resolves from the snapshot `subtasks` slot regardless of `status_phase`.
     - `tasks_status_cmd._st_gated_runtime_fields` → returns snapshot agent/shell_pid, never the frontmatter `extract_scalar` values.
     - `task_utils.support.WorkPackage` runtime properties (`agent`/`assignee`/`shell_pid`) → snapshot-sourced; an absent snapshot entry is authoritative empty, not a frontmatter fallback.
     - `core.stale_detection` shell_pid liveness → snapshot-sourced when a `feature_dir` is supplied.
     - `tasks_shared` / `tasks_transition_core` subtask readers → snapshot-sourced, with the C-001 symmetric-window legacy fallback still firing only when the snapshot slot is *silent* (not when the flag is off — there is no flag).
     - `tasks_mark_status` → a `mark-status` flip does not persist the checkbox byte to `tasks.md` (event-sourced only) — assert the file bytes are unchanged.
  4. **Lane-mirror regression (T016).** Co-located here or in the status suite — both `status_phase=0` and `=1` exercised, resolved lane identical.
  5. **`write_shell_pid_claim` retirement reconciliation (post-tasks gate fix).** Because T015 retires `write_shell_pid_claim`, reconcile its test callers so the WP04 tip is green: **delete** `tests/specify_cli/core/test_shell_pid_claim_baseline.py` (dedicated to the retired symbol); **rework** `tests/specify_cli/cli/commands/test_implement_runtime_frontmatter_claim.py` from "implement writes shell_pid into WP frontmatter" to "implement writes 0 runtime bytes to the WP file" (byte-stability); **replace** the single fixture call at `tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py:337` (`write_shell_pid_claim(original_front, live_pid)`) with an inline frontmatter literal (one-line out-of-map edit, unowned test). Assert `test_no_dead_symbols` is green on the WP04 tip.
  - **Fixture shape (guidance).** Build a mission dir with `meta.json` (`status_phase: "1"`), a `tasks/WP01.md`, and a seeded `status.events.jsonl` (claim transition + an `InnerStateChanged` carrying `shell_pid`/`agent`/`subtasks`) — mirror how WP03's committed corpus looks so the test exercises the real post-cutover regime. Reuse existing `status` suite fixtures/helpers where they exist rather than hand-rolling event JSON.
  - Run each file with `uv run --extra test python -m pytest -p no:cacheprovider <FILE>` (bare `python` resolves a sibling checkout → false greens). **Never** run the whole `tests/architectural/` directory (it hangs).

## Branch Strategy

- **Strategy:** Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed changes merge back into `feat/runtime-state-corpus-cutover`.
- **Planning base branch:** `feat/runtime-state-corpus-cutover`
- **Merge target branch:** `feat/runtime-state-corpus-cutover`
- **⚠️ MERGE-UNIT with WP03 & WP05 (BLOCKER-fix, non-negotiable).** The dependency spine is `WP03 → WP04 → WP05`:
  - **WP03 lands before WP04.** WP03's seed events + `status_phase` flips **must be merged to local main BEFORE** WP04 — if the unconditional readers reach local main before WP03's seeds, every dogfood mission reads an empty snapshot and the suite goes red instantly (research D-07). This WP's `dependencies: ["WP03"]` frontmatter encodes exactly that edge.
  - **WP04 lands before WP05.** WP05 deletes the T037 fallbacks and reroutes `tasks_move_task.py`/`workflow_cores.py` — safe only after WP04's flip. (`write_shell_pid_claim` is retired **in WP04**, not WP05 — see T015.)
  - **One merge unit.** The mission PR carries all three together; do not split WP04 out of the cutover unit, and do not let WP04 reach local main on its own tip (it would strand the writer-retirement half done).
- **Local main only.** `spec-kitty merge` targets **local main only**; never `git push origin main`. Publishing is the operator's explicit, separate step.
- **Byte-stability on the WP04 tip.** WP04 deletes all three dual-write blocks **and** retires `write_shell_pid_claim`, so `tasks/WP##.md` byte-stability holds on the WP04 tip itself. (`tasks_move_task.py`'s own runtime write is WP05's separate `_mt_dual_write_wp_file` teardown — it does not call `write_shell_pid_claim`.)

## Test strategy

- **Per-file only.** Run tests with `uv run --extra test python -m pytest -p no:cacheprovider <FILE>`. Bare `python` resolves a sibling checkout → false greens (research `uv run` discipline).
- **NEVER run the whole `tests/architectural/` directory** — it hangs (research risks). If an architectural guard must be exercised, run the single file with a timeout.
- **New coverage** lands in `tests/specify_cli/status/test_cutover_byte_stability.py` (the one `create_intent` file).
- **Split-suite reconciliation is out of scope here.** The broad flag-ON/flag-OFF split-suite reconciliation (FR-009) is IC-05 / a later WP. Do **not** pre-empt it. But do **not** leave a test red because it still expects a flag-OFF branch you deleted — re-point the **minimum** needed (a test that imports the deleted predicate, or asserts the flag-OFF path, on a file you touched). Prefer moving flag-ON assertions to unconditional; note anything larger for IC-05.
- **Byte-stability** is proven by a **real** before/after file compare (`read_bytes()`), never a mock (SC-004).
- **The lane-mirror regression (T016)** must be **non-vacuous** — it must fail if the flip silently changed a lane read.
- **Pre-existing reds are not yours.** The phantom `SYNC_DISABLE_ENV_VARS` arch-adversarial red and the known-P0 reds (#2736/#2772/#1834) are pre-existing on main (research risks) — attribute against merge-base before folding any red into this WP.
- **Run at minimum** the files backing the sites you touched: `tests/specify_cli/status/` (emit/infer-subtasks), the `agent tasks` command tests for the sites you collapse, and the new byte-stability file.

## Definition of Done

**T013 — predicate + facade deleted (FR-005 / C-002 / C-004):**
- [ ] `_phase1_snapshot_authority_active` function **deleted** from `emit.py` (401-410) + the 390-400 "two concerns" comment block removed/re-pointed.
- [ ] `status/__init__.py` aliased import (80) and `__all__` entry (237) dropped.
- [ ] `_legacy_lane_mirror_enabled` (413-424) and `_read_status_phase` (368-387) **kept** verbatim; only the dead cross-ref in the lane-mirror docstring scrubbed (C-004).

**T014 — flag-OFF branch collapsed (FR-004 / D-06 / D-14):**
- [ ] All **11 WP04 sites** collapsed (incl. both `support.py` sites and the out-of-map `wp_metadata.py` flag branch); each keeps the snapshot branch, drops the legacy branch.
- [ ] Every orphan paired import removed (local at 10 sites; module-level at `stale_detection.py:29`); both `_shell_pid_dual_write_active` wrappers deleted; dead docstring/comment refs scrubbed.
- [ ] `tasks_move_task.py` and `workflow_cores.py` **untouched**; C-001 symmetric-window guards preserved.

**T015 — writer cutover (NFR-003):**
- [ ] The three dual-write blocks deleted (`implement.py:1781-1788`, `workflow_executor.py` implement-claim + review-claim).
- [ ] `task_metadata_validation.repair_lane_mismatch` no longer bakes `shell_pid` into generated WP templates (86/141/156).
- [ ] `write_shell_pid_claim` **fully retired in this WP**: def deleted, removed from `frontmatter.py:401 __all__`, caller-inventory docstring says zero remaining callers; its 4 test callers reconciled (T017.5); `test_no_dead_symbols` green on the WP04 tip (no orphaned `__all__` symbol).

**T016 — lane-mirror regression (C-004):**
- [ ] Regression proves `status_phase 0→1` activates `_legacy_lane_mirror_enabled` **without** changing any lane read; both `=0` and `=1` exercised; `_legacy_lane_mirror_enabled` not modified.

**T017 — tests (SC-002 / SC-004):**
- [ ] Byte-stability test (real before/after `read_bytes()` compare) green (SC-004 / NFR-003).
- [ ] Grep/import assertion: `_phase1_snapshot_authority_active` + facade export gone from WP04's owned files (SC-002); `import` raises `ImportError`.
- [ ] Per-site unconditional-read assertions + the lane-mirror regression present.

**Cross-cutting:**
- [ ] **SC-002** predicate + facade export have zero occurrences (WP04 scope); **SC-004** a runtime transition writes 0 bytes to `tasks/WP##.md`.
- [ ] **INV-2 / INV-3** honoured: no WP04 code path reads a runtime slot from frontmatter for authority; a runtime transition writes 0 bytes to the WP file.
- [ ] `ruff` + `mypy` clean with **no** new `# noqa` / `# type: ignore` / per-file ignores (fix the code, do not suppress); every touched function stays at complexity **≤15**.
- [ ] No edits outside `owned_files` **except** the one sanctioned out-of-map edit to `status/wp_metadata.py` (flag branch only — see Risks).

**Per-owned-file expected change (quick self-audit):**
- [ ] `status/emit.py` — predicate deleted; `_infer_subtasks_complete` flag branch collapsed; kept twins intact.
- [ ] `status/__init__.py` — alias import + `__all__` entry removed.
- [ ] `cli/commands/implement.py` — `_shell_pid_dual_write_active` wrapper + its dual-write block deleted.
- [ ] `cli/commands/agent/tasks_transition_core.py` — flag early-return removed; `feature_dir is None` guard kept.
- [ ] `cli/commands/agent/tasks_shared.py` — flag return removed; silent-slot fallback kept.
- [ ] `cli/commands/agent/tasks_mark_status.py` — `legacy_checkbox_write` collapsed to event-sourced-only.
- [ ] `cli/commands/agent/tasks_status_cmd.py` — `_st_gated_runtime_fields` frontmatter fallback removed.
- [ ] `cli/commands/agent/workflow_executor.py` — wrapper + two dual-write blocks (implement- & review-claim) deleted.
- [ ] `core/stale_detection.py` — flag guard collapsed; module-level import (:29) removed; docstring re-pointed.
- [ ] `task_utils/support.py` — both sites (activity-log fold + `WorkPackage._snapshot_wp_state`) collapsed; both `# noqa` imports removed.
- [ ] `frontmatter.py` — `write_shell_pid_claim` def deleted + removed from `__all__` (401) + caller-inventory docstring says zero callers (retired here, not deferred).
- [ ] `task_metadata_validation.py` — `shell_pid` no longer baked into generated templates.
- [ ] `tests/specify_cli/status/test_cutover_byte_stability.py` — created with the four test groups.
- [ ] `status/wp_metadata.py` (out-of-map) — flag branch + direct import removed only.

## Risks & out-of-map edits

- **`status/wp_metadata.py` (owned by WP07) — sanctioned out-of-map edit.** Its flag branch (622-626) imports `_phase1_snapshot_authority_active` **directly from `emit`**, so the predicate deletion (T013) is only atomic if this branch is removed in the same change; leaving it would break the import and red the tree. Remove **only** the flag branch + the direct import here — leave the rest of the function (the inert-field reduction) for WP07. Rationale: it is one of the 12 cutover sites; WP07 runs later, so a sequential out-of-map edit is the only way to keep the deletion self-consistent. This is a deliberate, minimal, recorded exception to `owned_files`.
- **THE load-bearing subtlety — `status_phase` → lane-mirror activation (research D-02).** Deleting the reader predicate does **not** make `status_phase` inert: `_legacy_lane_mirror_enabled` still reads it (C-004). WP03 flipped the dogfood corpus to `status_phase=1`, so the lane mirror is now **active** on those missions. T016 exists precisely to prove that activation does not change any lane read. Treat a lane-behaviour change under activation as a real defect surfaced by this WP, not noise.
- **`write_shell_pid_claim` is fully orphaned by WP04 (post-tasks gate fix, was a phantom WP05 dependency).** `tasks_move_task.py:1442/1973` are docstrings, not calls; `grep 'write_shell_pid_claim('` shows only WP04-owned production callers. WP04 therefore **retires the symbol itself** (def + `__all__:401` + docstring) and reconciles its 4 test callers (T017.5): delete the dedicated `tests/specify_cli/core/test_shell_pid_claim_baseline.py`; rework `tests/specify_cli/cli/commands/test_implement_runtime_frontmatter_claim.py` (it asserts the now-removed dual-write frontmatter claim) into a byte-stability assertion; replace the single fixture call at `tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py:337` with inline frontmatter (one-line out-of-map edit — that test is unowned). Deleted-test node-ID churn in `tests/architectural/baselines/fast-tests-core-misc-nodeids.txt` is regenerated by WP06 in the same merge unit.
- **God-modules are surgical-only (D-14).** `implement.py` (1863) and `workflow_executor.py` (2044) are large; make the minimal collapse/delete edits only — no opportunistic degod. If a collapse pushes a touched function over cx 15, extract a small named helper (with a focused test), do not suppress.
- **Do NOT touch the two deferred sites.** `tasks_move_task.py` (site #12) and `workflow_cores.py` (verdict/review fallback) are WP05's — their flag/fallback removal is coupled to the ownership + verdict reroute. Editing them here would collide with WP05's diff and strand the reroute.
- **The site count is honest, but nuanced.** FR-004's "12 sites" = the 12 `_phase1_snapshot_authority_active` *invocations*. WP04 does 11 (including the out-of-map `wp_metadata.py` branch and both `support.py` sites); the 12th (`tasks_move_task.py`) is WP05's. `workflow_cores.py` is a **separate** frontmatter fallback (not a `_phase1` flag site) — also WP05's, but not one of the 12. Do not miscount it as an untouched flag site.
- **Symmetric-window fallbacks are NOT the flag — keep them.** `tasks_transition_core.py`'s `feature_dir is None` guard, and the "snapshot slot silent → legacy `tasks.md` roster" fallbacks in `tasks_shared.py`, are C-001 symmetric-window guards, not the phase-1 flag. Collapsing the flag must not delete them, or an untouched WP's already-checked rows read as incomplete.
- **`stale_detection.py` uses a module-level import (line 29), not a local one.** Every other site imports the predicate locally inside the function; this one imports at module scope. Removing the branch without removing the module-level import leaves an unused import (ruff F401).
- **Complexity may move under collapse.** Removing a branch usually *lowers* complexity, but the writer-block deletions restructure functions in `implement.py`/`workflow_executor.py` — confirm each touched function stays ≤15 and did not accidentally rise; extract a helper (with a test) rather than suppress.
- **The two `# noqa: PLC0415` imports in `support.py` (352, 407) go WITH their branches.** When you remove the local predicate imports, remove their trailing `# noqa: PLC0415` too — do not leave a `noqa` on a deleted line, and do not migrate the noqa onto a surviving import that does not need it.
- **`emit.py` carries a tracked `# NOSONAR` on `emit_status_transition`.** Do not let any incidental edit inflate that function or move the marker — WP04 does not touch it; keep the diff surgical.
- **Empty tolerated-set / invariant test is NOT this WP.** If a collapse makes the #2093 invariant test go red (e.g. it imports the deleted predicate), do the **minimum** re-point to keep it importable and note the full hardening for IC-05 — do not empty `_SANCTIONED_READER_MODULES` or rewrite the detector here (that is a later WP's owned change).

## Reviewer guidance

Focus the review on the five load-bearing checks below — each maps to a way this cutover fails silently.

- **Predicate truly gone:** `grep -rn "_phase1_snapshot_authority_active\|phase1_snapshot_authority_active" src/` returns only `tasks_move_task.py` (WP05's, pending) — nothing in WP04's owned files; `from specify_cli.status import phase1_snapshot_authority_active` raises `ImportError`; `__all__` no longer lists it (SC-002).
- **No orphans left:** no dangling local `from specify_cli.status import phase1_snapshot_authority_active …` imports; both `_shell_pid_dual_write_active` wrappers deleted; no docstring/comment still names the deleted predicate; `stale_detection.py`'s module-level import (was :29) removed.
- **Byte-stability is REAL, not mocked:** the test reads the actual `tasks/WP##.md` bytes before and after a real transition and asserts identity — confirm it is a genuine file compare, and that the three dual-write blocks are gone so no `shell_pid`/`agent`/activity-log line is written to the WP file.
- **Lane-mirror regression is non-vacuous:** T016 exercises both `status_phase=0` and `=1`, and would fail if the flip changed a resolved lane; `_legacy_lane_mirror_enabled` / `_read_status_phase` are unmodified (C-004).
- **Deferred sites untouched:** `tasks_move_task.py` and `workflow_cores.py` carry **no** WP04 changes; the only out-of-map edit is the single flag-branch removal in `wp_metadata.py`.
- **Kept symbols intact:** `_legacy_lane_mirror_enabled` and `_read_status_phase` are byte-for-byte unchanged except the one dead cross-ref scrubbed from the lane-mirror docstring (C-004).
- **Symmetric-window guards survive:** the `feature_dir is None` guard and the "snapshot slot silent → legacy roster" fallbacks are still present where the plan says they belong — the collapse removed the flag branch, not the C-001 guards.
- **Writer sweep is complete:** confirm no remaining WP04-owned path calls `write_shell_pid_claim` into a WP file, and `task_metadata_validation.repair_lane_mismatch` no longer emits a `shell_pid` line into generated templates.
- **All 11 sites collapsed:** walk the site table and confirm each of WP04's 11 sites has its flag branch gone and its orphan import removed — none silently skipped.
- **`wp_metadata.py` edit is minimal:** only the flag branch (625-626) + the direct-from-`emit` import (622) removed — the rest of the function is untouched and left for WP07.
- **Fail-closed posture unchanged:** spot-check that a WP with no snapshot entry still yields the conservative result the site used before (the collapse changed the *source*, not the fail-closed behaviour).
- **Split-suite not pre-empted:** confirm the reviewer sees only *minimal* re-points to tests that broke on the deleted symbol — not a wholesale flag-ON/flag-OFF reconciliation (that is IC-05).
- **Quality:** `ruff` + `mypy` clean, no new suppressions, touched functions ≤15 complexity.
- **CI gate awareness:** the diff-coverage critical-path gate (≥90% on changed lines in `status/`) bites here — the new byte-stability test + per-site assertions must actually execute the collapsed branches, not just import them.

## Activity Log

- 2026-07-20T12:53:18Z – claude – shell_pid=3802160 – Assigned agent via action command
- 2026-07-20T13:44:40Z – claude – shell_pid=3802160 – Ready for review
- 2026-07-20T13:46:41Z – claude – shell_pid=3914998 – Started review via action command
- 2026-07-20T13:59:38Z – user – shell_pid=3914998 – Approved: headline cutover, byte-stability non-vacuous, predicate deleted, write_shell_pid_claim retired, zero regressions; WP04+WP05 merge-unit
