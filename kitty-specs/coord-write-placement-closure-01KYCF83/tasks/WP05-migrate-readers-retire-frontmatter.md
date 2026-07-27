---
work_package_id: WP05
title: Migrate frontmatter readers to the snapshot, then retire the frontmatter write
dependencies:
- WP04
requirement_refs:
- FR-008
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
created_at: '2026-07-25T12:00:00+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
phase: Phase 2 - Event-source authoring
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/stale_detection.py
create_intent:
- tests/regression/test_stale_sweep_snapshot.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/stale_detection.py
- src/specify_cli/task_metadata_validation.py
- src/specify_cli/frontmatter.py
- tests/regression/test_stale_sweep_snapshot.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Migrate frontmatter readers, then retire the frontmatter write

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

Complete FR-008's retirement leg. WP04 event-sourced the claim (dual-write retained). This WP migrates the two frontmatter **readers** to consume the reduced snapshot, and **only then** retires the frontmatter `shell_pid`/`agent` write in `frontmatter.py`. Order is load-bearing: migrate readers → prove stale-sweep on the snapshot → retire the write.

- **FR-008 (reader + retire side)**: migrate `stale_detection.py:230` (`_is_claiming_process_alive` reads `shell_pid`) and `task_metadata_validation.py` to read `shell_pid` from the reduced snapshot; then retire the frontmatter authoring write.

**Done** = both readers consume the snapshot; a red-first stale-sweep test proves liveness off the event log; the frontmatter `shell_pid`/`agent` write is retired with no liveness regression.

## Context & Constraints

- Spec: [spec.md](../spec.md) US2, FR-008. Plan: [plan.md](../plan.md) IC-07-readers + the folded reader-coupling finding. Research D-03.
- **Depends on WP04**: the claim event must already be emitted (so the snapshot carries `shell_pid`) before readers can rely on it.
- **Ordering invariant (folded squad finding)**: migrate readers BEFORE retiring the write. Retiring first would break claim-liveness / stale-sweep. The red-first stale-sweep test (T021) must pass on the snapshot *before* T023 removes the write.
- **Write-location seam (post-tasks squad)**: the claim `shell_pid`/`agent` frontmatter write is authored in **`frontmatter.py`** (constants at `frontmatter.py:71`/`:288`) — NOT in WP04's `status_transition.py`. So T023 retires the dual-write by editing **`frontmatter.py` alone**; you do NOT need to (and must not) re-touch `status_transition.py`. This keeps owned_files disjoint from WP04.
- **CAUTION — `stale_detection.py` may already be half-migrated (post-tasks squad); verify the LIVE read path before editing**: `stale_detection.py` already carries snapshot-reader machinery (`_read_wp_runtime_snapshot_state:263`) and may be **transitionally half-migrated** from a prior FR-005 mission. Before rewriting T021, grep the **live** `shell_pid` read path (`:230` region) and confirm whether it still reads frontmatter or already routes through the snapshot helper. The real delta may be **smaller than the prompt implies** — possibly just wiring `_is_claiming_process_alive` to the existing `_read_wp_runtime_snapshot_state`. Do not re-introduce a snapshot reader that already exists.
- **C-002 scope**: only these two readers + the one write retirement. No broader frontmatter retirement.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T020 – RED-first stale-sweep off the snapshot

- **Purpose**: DIRECTIVE_041 — prove the stale-sweep can determine claim-liveness from the reduced snapshot, not frontmatter.
- **Steps**: Write `tests/regression/test_stale_sweep_snapshot.py` that seeds a claim event (via the real claim path), materializes the snapshot, and asserts `_is_claiming_process_alive` resolves `shell_pid` from the snapshot. It must fail while the reader still reads frontmatter-only.
- **Files**: `tests/regression/test_stale_sweep_snapshot.py` (new).
- **Validation**: red before T021.

### Subtask T021 – Migrate `stale_detection.py` reader

- **Purpose**: FR-008 — `_is_claiming_process_alive` reads `shell_pid` from the snapshot.
- **Steps**: At `stale_detection.py:230`, replace the frontmatter `shell_pid` read with a reduced-snapshot read (`materialize`/reducer). Preserve the liveness semantics exactly (same alive/dead decision). **First verify the live read path** (see CAUTION above): `_read_wp_runtime_snapshot_state:263` may already exist — if so, the delta is to route `_is_claiming_process_alive` through it, not to build a new snapshot reader.
- **Files**: `src/specify_cli/core/stale_detection.py`.
- **Validation**: T020 turns green; existing stale-sweep suites stay green.
- **Edge cases**: a mission with no claim event → treat as not-claimed (no false "alive").

### Subtask T022 – Migrate `task_metadata_validation.py` reader

- **Purpose**: FR-008 — the second frontmatter reader consumes the snapshot.
- **Steps**: Migrate the `shell_pid`/claim-field reads in `task_metadata_validation.py` to the reduced snapshot. Keep validation semantics identical.
- **Files**: `src/specify_cli/task_metadata_validation.py`.
- **Validation**: metadata-validation suites green off the snapshot.

### Subtask T023 – Retire the frontmatter `shell_pid`/`agent` write

- **Purpose**: FR-008 — close the drift source now that readers are migrated.
- **Steps**: In `frontmatter.py`, remove the `shell_pid`/`agent` authoring write (the dual-write half WP04 retained). Confirm nothing un-seeded accrues to frontmatter for these fields.
- **Files**: `src/specify_cli/frontmatter.py`.
- **Validation**: after a claim, frontmatter no longer carries `shell_pid`/`agent`; snapshot still does; stale-sweep green.
- **Edge cases**: legacy missions with frontmatter `shell_pid` already present — the reader must tolerate their absence in the snapshot for pre-migration missions (fall through to not-claimed, not crash). Confirm this does not resurrect a frontmatter read.

### Subtask T024 – Full liveness regression + parity

- **Purpose**: prove no liveness regression after retirement (this is what WP09/WP10 build on).
- **Steps**: Run the claim/stale/metadata suites; confirm `has_evictable_state()` no longer becomes true from these two authoring paths (the drift source is closed). Record the observable that WP10 will key its re-keyed lock on (independent event-log evidence), NOT `has_evictable_state()`.
- **Files**: none (verification + tracer note).
- **Validation**: all liveness suites green; drift source closed.

## Test Strategy

- New: `tests/regression/test_stale_sweep_snapshot.py`.
- Run stale-detection, task-metadata-validation, and claim suites.

## Definition of Done

- Both readers consume the reduced snapshot.
- Frontmatter `shell_pid`/`agent` write retired; no liveness regression.
- Stale-sweep red-first green; `ruff` + `mypy` clean.
- Drift source (`has_evictable_state()` via these paths) closed — noted for WP10.

## Risks & Mitigations

- **Retire-before-migrate** → forbidden; T021/T022 precede T023, gated by T020.
- **Legacy frontmatter missions** → T023 edge case: tolerate snapshot absence, do not re-read frontmatter.

## Review Guidance

- Verify readers migrated BEFORE the write retirement (commit order / test evidence).
- Verify no residual frontmatter `shell_pid` read remains.
- Verify liveness semantics are byte-identical to pre-migration.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
