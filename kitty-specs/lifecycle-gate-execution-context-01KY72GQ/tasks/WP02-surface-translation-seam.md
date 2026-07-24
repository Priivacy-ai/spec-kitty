---
work_package_id: WP02
title: Surface→filesystem translation seam (the true schema root)
dependencies:
- WP01
requirement_refs:
- C-004
- C-005
- FR-001
- NFR-001
- NFR-003
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: 'Phase 2 - Schema Root: Surface Translation Seam'
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/artifacts.py
create_intent:
- tests/integration/test_surface_translation_seam.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/mission_runtime/artifacts.py
- src/mission_runtime/resolution.py
- src/mission_runtime/__init__.py
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/cli/commands/accept.py
- tests/integration/test_surface_translation_seam.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Surface→filesystem translation seam (the true schema root)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Build the **ONE total** `TopologySurface`→filesystem translation, consuming the **existing** `probe_coord_state`/`CoordState` classifier — never a new one beside it — and declare `LANE`/`CONSOLIDATED`/`TEMP` **with** the seam. Repoint or demolish every translator it touches **in the same pass**; register any genuine survivor in the ratchet registry.

**Done** = the operator's resolvability test passes (every enum member resolves to a real location; no phantom member); no translator adds a thirteenth while twelve survive.

## Context & Constraints

- Plan IC-11 (the true schema root, ahead of IC-02). data-model.md "TopologySurface"/"ArtifactHome". Contract `gate-execution-context.md` C3/C4 (four `CoordState` answers).
- **This is the concern most likely to fail by becoming additive.** ~12 translators exist; a seam that adds a 13th while 12 survive has made the problem worse. Decided 2026-07-23: build it and repoint/demolish every translator it touches in the same pass. Prior art for the failure mode: `_resolve_review_cycle_read_dir` was itself added by a consolidation-shaped fix (#2646/#2275) and produced #2885.
- **AH-2 Totality**: flat/`SINGLE_BRANCH`/`LANES` resolve **affirmatively** to the primary mission dir (their declared home, not a fallback). Among coord states only `DELETED` raises; `EMPTY` and `UNMATERIALIZED` resolve primary **with a PRIMARY stamp**. `None` is retained for nothing.
- **AH-1 read/write symmetry** (from #2874) must not break.
- **C-004**: no member/name/branch conditioned on coordination topology.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T007 – Extend `TopologySurface`

- **Steps**: Add `LANE`, `CONSOLIDATED`, `TEMP` **with** the seam (never before — a member no caller can resolve is a phantom). Confirm the `Surface`→`TopologySurface` rename (ADR 2026-07-23-1) already landed in `mission_runtime/artifacts.py`; if not, complete it. `CONSOLIDATED` exists only from `LifecyclePhase.POST_CONSOLIDATION` onward.
- **Files**: `mission_runtime/artifacts.py`.

### Subtask T008 – Build the one total translation

- **Steps**: Implement the total `TopologySurface`→path translation in `mission_runtime/resolution.py`, **consuming** `probe_coord_state`/`CoordState` (`missions/_read_path_resolver.py:256`). Do not write a new classifier beside it.
- **Files**: `mission_runtime/resolution.py`, `missions/_read_path_resolver.py`.

### Subtask T009 – Totality/resolvability test

- **Steps**: Test that every `TopologySurface` member resolves to a real location for every topology/coord-state (the operator's acceptance signal). No phantom member. **Also pin AH-1 read/write symmetry** (`read_surface == write_surface` for every kind — established by #2874, which this total-seam rebuild is most likely to break): assert the seam resolves the same home for reads and writes of a given kind. This is the one preservation invariant with no other acceptance signal in the mission.
- **Files**: `tests/integration/test_surface_translation_seam.py` (new).

### Subtask T010 – Repoint `_acceptance_matrix_read_dir`

- **Steps**: Repoint `gates_core.py::_acceptance_matrix_read_dir` onto the seam — collapse `coord_read_dir_for(...) or feature_dir` to **affirmative** declared-home resolution. This is a **leeway** edit (`gates_core.py` is owned by WP03); touch only this translator function and record a one-line rationale.

### Subtask T011 – Repoint the accept/forecast/review translators [P]

- **Steps**: Repoint `accept.py::_coord_worktree_root` (owned here), and — under leeway — `forecast.py::feature_dir_for_preview` and `review_artifact_consistency.py::_resolve_review_cycle_read_dir` (owned by WP07; touch only their translator functions).

### Subtask T012 – Repoint/demolish remaining translators

- **Steps**: Sweep `resolution.py` and adjacent modules for remaining translators; repoint or demolish each. Register any genuine survivor in the ratchet registry (WP10's file) so it is visible and shrinking — never leave an unregistered survivor.

### Subtask T013 – C-005 compat golden

- **Steps**: If a seam symbol lands on the task-command compat surface, register it in `test_tasks_compat_surface.py` (`SYMBOL_TO_MODULE` + the `tasks.py` re-export) and move the golden **156→157 in THIS WP**. If no task-surface symbol is exported, note that explicitly.

## Test Strategy

- New: `tests/integration/test_surface_translation_seam.py` (totality/resolvability).
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/integration/test_surface_translation_seam.py -q` and the placement/partition golden-path suite.

## Risks & Mitigations

- **Additive failure mode** — mitigated by the same-pass repoint/demolish rule and survivor registration.
- Leeway edits (sequential, documented): `gates_core.py` (WP03), `forecast.py`/`review_artifact_consistency.py` (WP07). This WP touches only their translator functions.

## Review Guidance

- Confirm the seam consumes the existing `CoordState` classifier (no new classifier beside it).
- Confirm each of the four coord states has the declared answer (C3) and every member resolves (no phantom).
- Confirm no translator survived unrepointed and unregistered.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
