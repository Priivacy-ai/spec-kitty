---
work_package_id: WP03
title: Route residual writers through the placement port
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-006
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
created_at: '2026-07-25T12:00:00+00:00'
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 1 - Placement foundation
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/bookkeeping_projection.py
create_intent:
- tests/specify_cli/coordination/test_residual_writer_routing.py
execution_mode: code_change
owned_files:
- src/specify_cli/merge/bookkeeping_projection.py
- src/specify_cli/git/bookkeeping_commit.py
- src/specify_cli/events/decision_log.py
- tests/specify_cli/coordination/test_residual_writer_routing.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Route residual writers through the placement port

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

Route the three residual mission-artifact writers through the placement port so their writes resolve their partition via the classifier (from WP02) instead of an ambient `feature_dir`. These are the writers the whole-tree gate (WP06) will scan — route them **before** the gate tightens so it lands green.

- **FR-003**: route `bookkeeping_projection` (`merge/bookkeeping_projection.py:247`), `bookkeeping_commit` (`git/bookkeeping_commit.py`), and `decision_log` (`events/decision_log.py:209`) through the port.
- **FR-006**: `traces/` writers route to their now-COORD classification (from WP02).

**Done** = each writer derives its target from `resolve_placement_only` / `placement_seam.write_target(kind)` via `kind_for_mission_file`; no writer classifies inline; a routing test proves each lands on the classified partition.

## Context & Constraints

- Spec: [spec.md](../spec.md) US3 AS4, FR-003, FR-006, SC-006. Plan: [plan.md](../plan.md) IC-04-routing. Contract: [contracts/placement-enforcement.md](../contracts/placement-enforcement.md) "Routing coverage".
- **Depends on WP02**: the classifier (`kind_for_mission_file`) and the `decisions.events.jsonl` / `traces/` classifications must already exist. Call the classifier — never re-classify.
- **CAUTION — both target writers are ALREADY partially seam-adopted (post-tasks squad finding); do NOT no-op**: `git/bookkeeping_commit.py:66` already passes `target=CommitTarget(ref=branch)` and `events/decision_log.py` already **accepts an injected `target`**. The seam call *shape* is therefore already present — so the **real delta is NOT "introduce a target arg"**. The delta is to **swap the ambient/`branch` ref for a `kind_for_mission_file`-classifier-derived target**. Warn: an implementer who sees the existing `target=CommitTarget(ref=branch)` / injected-`target` fallback and leaves it in place has **no-op'd the WP**. The commit must derive `ref` from the classifier partition, not from the ambient current branch.
- **bookkeeping_projection.py ownership note**: WP09 (birth-cutover) may need to write the COORD seed events. It is steered to the **two-target cutover-spine form** (editing `runtime_state_cutover.py`, which it owns) precisely so it does NOT co-edit this file. If WP09 must instead delegate to `_phase_record_done_and_project` here, that is a documented leeway edit made after this WP lands (WP09 depends transitively on WP02 and lands much later) — no concurrent ownership.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T010 – Route `bookkeeping_projection` (coord→target projection writer)

- **Purpose**: FR-003 — the coord→target projection at `bookkeeping_projection.py:247` must resolve its partition through the port.
- **Steps**: Replace the ambient `feature_dir`-derived target with a `resolve_placement_only(kind)` / `placement_seam.write_target(kind)` derivation, where `kind` comes from `kind_for_mission_file(basename)`. Preserve the existing projection semantics (coord→target); only the target derivation changes.
- **Files**: `src/specify_cli/merge/bookkeeping_projection.py`.
- **Validation**: the projection write targets the classified partition; existing projection tests stay green.
- **Edge cases**: a projection over multiple basenames must classify per-file, not once.

### Subtask T011 – Route `bookkeeping_commit`

- **Purpose**: FR-003 — `git/bookkeeping_commit.py` must be seam-derived.
- **Steps**: Derive the commit target from the placement seam via the classifier. Confirm it satisfies the widened write gate's `target=CommitTarget(...)` seam-derivation shape (WP06 asserts this syntactically). **Real delta (see CAUTION above)**: `:66` already reads `target=CommitTarget(ref=branch)` — the fix is to replace the ambient `branch` ref with a `kind_for_mission_file`-classifier-derived partition ref, NOT to add the `target=` arg (already present). Do not leave the ambient-`branch` fallback in place.
- **Files**: `src/specify_cli/git/bookkeeping_commit.py`.
- **Validation**: the commit target's `ref` is a `resolve_placement_only`/`write_target` classifier derivation, not the ambient current branch.

### Subtask T012 – Route `decision_log` + confirm `decisions.events.jsonl` lands COORD

- **Purpose**: FR-003 / SC-006 — `decision_log` writes `decisions.events.jsonl` to its COORD classification.
- **Steps**: At `events/decision_log.py:209`, route the write through the port using `kind_for_mission_file("decisions.events.jsonl")` (COORD, from WP02). Confirm the file lands on the COORD surface. **Real delta (see CAUTION above)**: `decision_log.py` already **accepts an injected `target`** — so wiring an arg is not the work. The work is to make the *default/derived* target come from the classifier partition (COORD), not the ambient `feature_dir`/injected fallback. Do not no-op on the existing injected-`target` path.
- **Files**: `src/specify_cli/events/decision_log.py`.
- **Validation**: a decision-log write resolves to COORD via the classifier-derived port target (not the ambient fallback).

### Subtask T013 – Routing regression test (red-first)

- **Purpose**: prove all three writers route (FR-003/FR-006, SC-006 "0 residual unclassified writers for these paths"). **Red-first (DIRECTIVE_041)**: this test must fail on the *pre-routing* writers, not be green-on-arrival.
- **Steps**: Write `tests/specify_cli/coordination/test_residual_writer_routing.py` driving each writer against a coord-topology fixture and asserting the write lands on the **classified COORD** partition surface. **Author the assertions BEFORE the T010–T012 edits and confirm they red**: pre-routing, the ambient-`feature_dir`/`branch` writers land the write on the *primary/ambient* surface, so a "must land COORD" assertion fails; it goes green only after each writer swaps the ambient ref for the classifier-derived target. Use realistic mission fixtures (production-shaped ids), not stubs that bypass the port.
- **Files**: `tests/specify_cli/coordination/test_residual_writer_routing.py` (new).
- **Validation**: red on the pre-routing (ambient-ref) writers — asserting the COORD target before the edit; green after T010–T012; bypassing the classifier in any writer re-reds.

## Test Strategy

- New: `tests/specify_cli/coordination/test_residual_writer_routing.py`.
- Run the three writers' existing suites plus the new routing test.

## Definition of Done

- All three writers seam-derive their targets via the classifier.
- No inline classification at any writer site.
- `decisions.events.jsonl` + `traces/` land COORD.
- Routing regression green; `ruff` + `mypy` clean.

## Risks & Mitigations

- **Emit fallback interaction** → the `_current_branch` HEAD fallback is owned by WP04; do not touch `status_transition.py` here.
- **traces/ moved writes** → verify existing `traces/` consumers read from COORD after WP02's reclassification (WP07 owns read enforcement).

## Review Guidance

- Verify writers CALL `kind_for_mission_file` and never classify inline.
- Verify the routing test uses real fixtures and asserts on the resolved partition surface.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
