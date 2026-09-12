---
work_package_id: WP08
title: agent mission repair (Gap-2 cure for pre-existing split-brain)
dependencies: []
requirement_refs:
- FR-005
- NFR-005
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-write-placement-closure-01KYCF83
base_commit: 5b3c0b5b3e56cc43af611a677ad5b71b44130dd0
created_at: '2026-07-25T14:22:11.773257+00:00'
subtasks:
- T037
- T038
- T039
- T040
- T041
phase: Phase 4 - Repair & birth
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission_repair.py
create_intent:
- src/specify_cli/cli/commands/agent/mission_repair.py
- tests/specify_cli/cli/commands/test_mission_repair.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_repair.py
- src/specify_cli/cli/commands/agent/mission.py
- tests/specify_cli/cli/commands/test_mission_repair.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – agent mission repair (Gap-2 cure)

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

Add a new `spec-kitty agent mission repair` command that detects a **pre-existing content split-brain** across partitions and **forward-only** repairs it — fast-forward under strict-ancestor + clean worktree, refuse-with-diff otherwise. This is independent of the structural work (no deps).

- **FR-005 / NFR-005**: forward-only repair under strict-ancestor + clean worktree; refuse + emit unified diff on genuine divergence; never force-overwrite.

**Done** = the command reuses the existing FF/ancestor machinery, is adjudicated distinct from the two existing repair surfaces, and has red-first tests for both the FF and refuse paths.

## Context & Constraints

- Spec: [spec.md](../spec.md) US5, FR-005, NFR-005, SC-004. Plan: [plan.md](../plan.md) IC-06. Contract: [contracts/birth-cutover-and-repair.md](../contracts/birth-cutover-and-repair.md) "agent mission repair". Data model: repair state machine (`clean`/`ff-candidate`/`divergent`). Research D-04.
- **Reuse, do not reimplement**: reuse `_coordination_doctor._is_ff_candidate:341` and `_fast_forward_finding:362` for the FF/ancestor machinery. Import them — do NOT own or fork `_coordination_doctor.py`.
- **Three-surface adjudication (folded squad finding)**: a THIRD repair surface exists — `doctor mission-state --fix` → `repair_repo` (`_mission_state_doctor.py:213`, `migration/mission_state.py:518`). The tasks MUST explicitly adjudicate why cross-partition *content* cure is a distinct Gap-2 concern, not an extension of `repair_repo` (which repairs repo/state structure, not cross-partition content divergence). Record the adjudication in `tracers/design-decisions.md`.
- **C-002/C-003 boundary**: `doctor coordination --fix` stays minimized (FF-only, Gap-1). This is a NEW distinct command, not `--fix` growth.
- **NFR-005**: never force-overwrite divergent content; emit a specific unified diff and exit non-zero.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T037 – Adjudicate distinctness vs `repair_repo` (design-first)

- **Purpose**: FR-005 — justify a new command over extending the third surface.
- **Steps**: Inspect `_mission_state_doctor.py:213` `repair_repo` and `migration/mission_state.py:518`. Document why cross-partition content divergence (coord vs primary bookkeeping content) is a distinct Gap-2 concern from repo/state-structure repair. Record in `tracers/design-decisions.md`.
- **Files**: read-only + tracer note.
- **Validation**: a written adjudication citing both surfaces.

### Subtask T038 – RED-first: FF and refuse paths

- **Purpose**: DIRECTIVE_041 — drive both branches through the real command entry point.
- **Steps**: Write `tests/specify_cli/cli/commands/test_mission_repair.py` with two fixtures: (a) strict-ancestor + clean worktree → expects a zero-loss fast-forward; (b) non-ancestor divergence → expects refuse + a unified diff + non-zero exit + zero mutation. Both fail before T039.
- **Files**: `tests/specify_cli/cli/commands/test_mission_repair.py` (new).
- **Validation**: red before implementation.

### Subtask T039 – Implement the repair command

- **Purpose**: FR-005 — the command logic.
- **Steps**: Create `mission_repair.py` implementing the `clean → no-op`, `ff-candidate → forward`, `divergent → refuse+diff` state machine. Use `_is_ff_candidate` / `_fast_forward_finding` for ancestor/FF detection. Detect content divergence across the coord/primary partitions.
- **Files**: `src/specify_cli/cli/commands/agent/mission_repair.py` (new).
- **Validation**: T038 fixtures turn green.
- **Edge cases**: dirty worktree → not an FF candidate → refuse; clean + strict-ancestor → forward.

### Subtask T040 – Register the subcommand

- **Purpose**: expose `spec-kitty agent mission repair`.
- **Steps**: Register the new command on the `mission` Typer app in `mission.py` (a single `@app.command` registration + re-export edge if the god-module convention requires it — follow the module's existing pattern; do NOT add business logic to `mission.py`).
- **Files**: `src/specify_cli/cli/commands/agent/mission.py`.
- **Validation**: `spec-kitty agent mission repair --help` resolves.

### Subtask T041 – Diff quality + no-mutation-on-refuse

- **Purpose**: NFR-005 — refuse emits a specific diff, mutates nothing.
- **Steps**: Assert the divergent path emits a unified diff naming the diverged content and leaves both partitions byte-identical (no mutation). Assert the FF path is zero-loss.
- **Files**: extend `tests/specify_cli/cli/commands/test_mission_repair.py`.
- **Validation**: refuse path mutates nothing; FF path loses nothing.

## Test Strategy

- New: `tests/specify_cli/cli/commands/test_mission_repair.py`.
- Run the new test + the doctor suites to confirm no interaction with the other repair surfaces.

## Definition of Done

- New `agent mission repair` command; FF-forward + refuse-with-diff.
- Reuses `_is_ff_candidate`/`_fast_forward_finding`; distinctness vs `repair_repo` adjudicated.
- Never force-overwrites; refuse mutates nothing.
- `ruff` + `mypy` clean.

## Risks & Mitigations

- **Overlap with `repair_repo`** → T037 adjudication.
- **Force-overwrite on divergence** → T041 no-mutation assertion.
- **god-module registration** → follow `mission.py`'s existing re-export pattern; no business logic there.

## Review Guidance

- Verify FF machinery is REUSED, not reimplemented.
- Verify the refuse path emits a diff and mutates nothing.
- Verify the distinctness adjudication vs the third surface is recorded.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
