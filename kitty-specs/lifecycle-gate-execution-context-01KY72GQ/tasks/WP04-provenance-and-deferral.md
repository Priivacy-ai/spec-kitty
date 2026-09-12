---
work_package_id: WP04
title: Negative-invariant provenance, deferral & single home (folds IC-09)
dependencies:
- WP03
requirement_refs:
- FR-002
- FR-003
- FR-010
- NFR-003
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 4 - Provenance, Deferral & Migration
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/matrix.py
create_intent:
- tests/acceptance/test_provenance_and_deferral.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/acceptance/matrix.py
- tests/acceptance/test_provenance_and_deferral.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Negative-invariant provenance, deferral & single home

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Every recorded judgement states the surface and ref it was established against; a `pending` invariant whose subject cannot exist in the current surface records `deferred_to_consolidation` with a reason instead of a false `still_present`; and the acceptance record is authored **once** to its declared home. This folds IC-09 (single-home) — it owns `matrix.py`, the same file, and co-lands to stop the two copies diverging on the new fields.

**Done** = contract `negative-invariant-provenance.md` C1–C5, C8, C9 pass; provenance round-trips; `validate_matrix_evidence` enforces NI-1.

## Context & Constraints

- Contract `negative-invariant-provenance.md`. data-model.md `NegativeInvariant` (NI-1..NI-6), `overall_verdict` fourth value.
- **NI-2 is load-bearing**: the landed guard predicates on `result != "pending"` (`matrix.py:351`). Once `deferred_to_consolidation` exists as a non-`pending` value, that predicate would **freeze it**, making NI-4/C6 impossible. Move the guard from "not pending" to **terminal-set membership** — in THIS WP, the same one that adds the fourth value.
- **NI-1 typed legacy escape**: `recorded` requires `verified_ref` + `verified_surface_kind`; `legacy_unrecorded` permits both null. `legacy_unrecorded` is a `provenance_origin` value, **never** a `TopologySurface` member (anti-phantom rule).
- **NI-5**: `overall_verdict` gains `pass_pending_consolidation` — acceptance not blocked; `done` unreachable while any invariant is deferred. The three-value vocabulary has no assignment satisfying both (allow→silent pass; disallow→fail; group-with-pending→reproduces the block).
- **NFR-004**: the non-`pending` preservation branch must survive (it is NI-2, explicitly NOT on the retirement list). Do not regress it.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T020 – Provenance fields + fourth Result

- **Steps**: Add `verified_ref`, `verified_surface_kind` (`TopologySurface | null`), `deferred_reason`, `deferred_to_phase`, `provenance_origin` (`recorded | legacy_unrecorded`) to `NegativeInvariant`; add `deferred_to_consolidation` to `Result`. Ensure `to_dict`/`from_dict` round-trip all fields (C2).

### Subtask T021 – NI-1 validation (typed legacy escape)

- **Steps**: In `validate_matrix_evidence`, a non-`pending` `recorded` result without both `verified_ref` and `verified_surface_kind` is a validation error; a `legacy_unrecorded` result with both null is accepted (that origin only). Keep C1 and data-model NI-1 stating the same rule.

### Subtask T022 – NI-2 terminal-set guard change

- **Steps**: Change the preservation guard (`matrix.py:351`) from `result != "pending"` to **membership in the terminal set** (`confirmed_absent` / `still_present` / `verification_error`), so `deferred_to_consolidation` is not frozen. This belongs to THIS WP, not a later one. **Also pin provenance-contract C3** here (a recorded terminal judgement is never overwritten from a different surface, and no re-execution occurs): the landed preserve guard `b918e66df` already provides this — add/keep an assertion that a recorded terminal result + its provenance survive a later gate run verbatim, so C3 has an explicit acceptance signal and cannot silently regress.

### Subtask T023 – NI-3/C4/C9 defer semantics

- **Steps**: A `pending` invariant whose subject cannot exist in the current `GateExecutionContext.surface` transitions to `deferred_to_consolidation` with a `deferred_reason` and `deferred_to_phase = POST_CONSOLIDATION` — never to `still_present`. A `grep_absence` scoped to a source dir that already exists on the primary surface is judged normally pre-consolidation (C9), not deferred.

### Subtask T024 – NI-5 `pass_pending_consolidation`

- **Steps**: Add `pass_pending_consolidation` to `overall_verdict`; acceptance is not blocked on deferred invariants (C5) and is not blocked by "criteria or invariants have not been verified"; `done` unreachable while any invariant is deferred.

### Subtask T025 – FR-010 / C8 / AH-3 single home

- **Steps**: The acceptance matrix is written directly to its declared home with **no** primary-scaffold second copy (the `finalize-tasks` scaffolder must not create one). Edit the scaffolder under leeway if needed, with rationale.

### Subtask T026 – Tests

- **Steps**: Provenance round-trip, NI-1 validation (both origins), NI-3 deferral, NI-5 verdict-neutrality, C8 single-copy — on realistic fixtures.

## Test Strategy

- New: `tests/acceptance/test_provenance_and_deferral.py`.
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/acceptance/ -q`.

## Risks & Mitigations

- `pending` is the scaffolded default — the deferral path is the common one, not the edge.
- Leeway: `gates_core.py` (deferral wiring; owned WP03) and the finalize-tasks scaffolder — document each.

## Review Guidance

- Confirm the NI-2 guard now keys on the terminal set (deferred not frozen).
- Confirm `pass_pending_consolidation` unblocks acceptance without silently passing.
- Confirm NFR-004's preservation branch is intact.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
