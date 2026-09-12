---
work_package_id: WP09
title: Birth-time runtime cutover (born-reconciled missions)
dependencies:
- WP02
- WP04
- WP05
- WP06
requirement_refs:
- C-004
- FR-009
- NFR-003
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
created_at: '2026-07-25T12:00:00+00:00'
subtasks:
- T042
- T043
- T044
- T045
- T046
- T047
- T048
phase: Phase 4 - Repair & birth
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/runtime_state_cutover.py
create_intent:
- tests/regression/test_birth_cutover.py
execution_mode: code_change
owned_files:
- src/specify_cli/migration/runtime_state_cutover.py
- src/specify_cli/merge/ordering.py
- src/specify_cli/merge/executor.py
- tests/regression/test_birth_cutover.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – Birth-time runtime cutover

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objective

Make new missions **born runtime-reconciled**: stamp `status_phase` and reconcile residual runtime at land via `cutover_mission` (the sole `status_phase` writer), routed through WP02's placement port. This is the **plan's weakest seam** — the design decisions below MUST be resolved in the subtasks, not deferred.

- **FR-009 / NFR-003 / C-004**: at the merge bake stage, `cutover_mission` reconciles residual runtime and stamps `status_phase`, `meta.json`/`status_phase` → PRIMARY and seed events → COORD via the port; idempotent; sole-writer preserved.

**Done** = a red-first create→implement→merge lands `status_phase>=1` + `verify_backfill().ok` + non-empty snapshot with NO manual backfill; the two-partition split and two-write atomicity are resolved; idempotent with the one-time migration; satisfies WP06's whole-tree gate.

## Context & Constraints

- Spec: [spec.md](../spec.md) US2 (all AS), FR-009, NFR-003, C-004. Plan: [plan.md](../plan.md) IC-08 (read the four risk items — they are load-bearing). Contract: [contracts/birth-cutover-and-repair.md](../contracts/birth-cutover-and-repair.md) "Birth-cutover". Data model "State transitions". Research D-02.
- **Depends on WP02** (port meta routing), **WP04+WP05** (event-source authoring complete — C-001: FR-008 before FR-009, else a flipped-but-unseeded mission recurs — the "12's shape"), and **WP06** (the birth-write must satisfy the whole-tree gate — IC-08→IC-02).
- **Sole writer (C-004)**: reuse `cutover_mission`/`_flip_phase`. A two-target form **extends** the spine; it does NOT fork it. No parallel `status_phase` writer.
- **bookkeeping_projection.py ownership**: WP03 owns it. Prefer the **two-target cutover-spine form** (edit `runtime_state_cutover.py`, which you own) to avoid co-editing WP03's file. If you MUST delegate the COORD seed to `_phase_record_done_and_project`, that is a leeway edit made after WP03 lands (WP03 is transitively upstream via WP02) — record the rationale; do not add it to `owned_files`.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T042 – RED-first: create→implement→merge lands reconciled

- **Purpose**: DIRECTIVE_041 — the birth repro drives the real entry points, not a fixture. **The coord-topology two-partition split is part of THIS red-first anchor, not a soft afterthought (post-tasks squad)**: the base asserts (`status_phase>=1` + `verify_backfill().ok` + non-empty snapshot) all pass on a *single-partition* write, so they do NOT prove the split — the anchor must also assert on the resolved partition surfaces.
- **Steps**: Write `tests/regression/test_birth_cutover.py` that creates a **coord-topology** mission through the real entry points, claims a WP + completes a subtask, merges it, and asserts it lands `status_phase>=1` + `verify_backfill().ok` + a non-empty snapshot with NO migration invocation **AND** (the load-bearing split assertions) seed events are **PRESENT on the COORD surface and ABSENT from PRIMARY**, while `meta.json`/`status_phase` land on **PRIMARY**. It must fail before T044 — and specifically fail on the split assertions for a single-partition implementation, not merely on the phase stamp.
- **Files**: `tests/regression/test_birth_cutover.py` (new).
- **Validation**: red before implementation, including the resolved-partition split assertions (a single-partition birth reds this anchor).

### Subtask T043 – Resolve the pre-target timing decision

- **Purpose**: IC-08 risk 1 — `_bake_mission_number` is **pre-target** (`executor.py:1319` before `_phase_mission_to_target:1320`).
- **Steps**: DECIDE and record in `tracers/design-decisions.md`: (a) keep the bake hook and rely on merge-atomicity for the PRIMARY leg (abort ⇒ never reaches target ⇒ consistent), OR (b) relocate the stamp to a post-`_phase_commit_and_assert` phase. Justify the choice against the atomicity requirement.
- **Files**: `src/specify_cli/merge/executor.py` (phase order), `tracers/design-decisions.md`.
- **Validation**: the chosen timing is implemented and justified.

### Subtask T044 – Resolve the two-partition single-`feature_dir` split

- **Purpose**: IC-08 risk 2 — `cutover_mission(feature_dir)` is single-`feature_dir` and cannot natively split meta→PRIMARY / seed events→COORD.
- **Steps**: Implement EITHER a **two-target spine form** on `cutover_mission` (preferred; edit `runtime_state_cutover.py`) OR delegate the COORD seed write to `_phase_record_done_and_project` (leeway on WP03's file). Route the meta→PRIMARY leg through WP02's port; route seed events→COORD through the port. Do NOT conflate a single `feature_dir`.
- **Files**: `src/specify_cli/migration/runtime_state_cutover.py`, `src/specify_cli/merge/ordering.py`.
- **Validation**: `meta.json`/`status_phase` land PRIMARY; seed events land COORD; both via the port.

### Subtask T045 – Two-write atomicity / resume-heal

- **Purpose**: IC-08 risk 3 — a crash between the COORD seed commit and the PRIMARY flip must not half-birth a mission.
- **Steps**: Wrap the two writes in a transactional envelope OR add a resume-heal (`_heal_pending_coord_reconcile`) that completes a half-done birth on `merge --resume`. Test the crash-in-between path.
- **Files**: `src/specify_cli/merge/executor.py`, `src/specify_cli/migration/runtime_state_cutover.py`.
- **Validation**: a simulated crash between the two writes heals to a consistent state on resume.

### Subtask T046 – Idempotency with the one-time migration

- **Purpose**: NFR-003 / IC-08 risk 4 — deterministic seeds; re-run is a no-op.
- **Steps**: Ensure the birth seeds use the same `mission_id`-namespaced deterministic ids as `m_zz_runtime_state_backfill`, so a mission that hits both the birth seam and the one-time migration seeds 0 the second time and leaves the event log byte-identical.
- **Files**: `src/specify_cli/migration/runtime_state_cutover.py`.
- **Validation**: birth-then-migration (and migration-then-birth) both idempotent.

### Subtask T047 – Coord vs flat topology

- **Purpose**: US2 AS3 — the two-partition write for coord topology, and the flat degenerate case. This subtask **hardens** the split assertions the red-first anchor (T042) already carries — it is the exhaustive partition-surface proof, not the first place the split is checked.
- **Steps**: For coord topology, assert on the **resolved partition surfaces** (not just "reconciled"): seed events are **PRESENT on COORD** and **ABSENT from PRIMARY**; `meta.json`/`status_phase` are **PRESENT on PRIMARY** (and not on COORD). For flat/single-branch, verify the single-partition degenerate case still lands reconciled (both legs collapse to the one partition). Extend `test_birth_cutover.py` with both topologies and assert the surface split explicitly.
- **Files**: `tests/regression/test_birth_cutover.py`.
- **Validation**: coord topology — seed events on COORD only, meta/status_phase on PRIMARY only (a single-partition write reds); flat topology — single-partition reconciled.

### Subtask T048 – Whole-tree gate + green

- **Purpose**: IC-08→IC-02 — the birth-write must satisfy WP06's gate.
- **Steps**: Confirm every write the birth seam performs is seam-derived (WP06 gate green). Turn `test_birth_cutover.py` green. Run the merge suites for non-regression.
- **Files**: verification.
- **Validation**: WP06 gate green with the birth-write present; birth repro green.

## Test Strategy

- New: `tests/regression/test_birth_cutover.py` (coord + flat).
- Run merge/executor/ordering suites + the whole-tree write gate.

## Definition of Done

- Birth repro green: create→implement→merge lands reconciled with no manual backfill; the red-first anchor (T042) asserts the resolved-partition split (seed events COORD-only, meta/status_phase PRIMARY-only), not just the phase stamp.
- Timing, two-partition split, atomicity, idempotency all resolved + recorded.
- `cutover_mission` is the sole `status_phase` writer (two-target form extends, not forks).
- WP06 gate green; `ruff` + `mypy` clean.

## Risks & Mitigations

- **Half-born mission on crash** → T045 transactional envelope / resume-heal.
- **Forked writer** → reuse `cutover_mission`; two-target form extends the spine.
- **Co-editing WP03's file** → prefer the two-target spine form; delegate only via documented leeway.

## Review Guidance

- Verify the timing/split/atomicity/idempotency decisions are recorded in tracers.
- Verify no parallel `status_phase` writer was introduced.
- Verify the birth-write satisfies WP06's whole-tree gate.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
