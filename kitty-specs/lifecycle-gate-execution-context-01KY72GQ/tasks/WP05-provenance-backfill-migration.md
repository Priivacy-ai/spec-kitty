---
work_package_id: WP05
title: FR-014 provenance backfill migration
dependencies:
- WP04
requirement_refs:
- FR-014
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 4 - Provenance, Deferral & Migration
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/migrate/backfill_provenance.py
create_intent:
- src/specify_cli/cli/commands/migrate/backfill_provenance.py
- tests/migration/test_backfill_provenance.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/migrate/backfill_provenance.py
- tests/migration/test_backfill_provenance.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – FR-014 provenance backfill migration

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

A one-time migration bringing all existing on-disk acceptance matrices onto the provenance schema, writing `provenance_origin: legacy_unrecorded` for pre-schema non-`pending` results, its own write **enrolled in a commit-or-revert transaction**.

**Done** = the migration oracle test passes: every non-`pending` result ends with a valid `provenance_origin` and `validate_matrix_evidence` passes on the migrated corpus.

## Context & Constraints

- FR-014; contract `negative-invariant-provenance.md` C1; data-model NI-1.
- Current corpus: **153 matrices, 40 non-`pending`, 0 with provenance** — confirm at implement time.
- **The migration's ~153-file write is a toolchain-generated write like any other** — the mission's thesis forbids it being an exception. The generalized owner (IC-06/WP09) is in half 2, so enrol under an **explicit one-off transaction** with the same commit-or-revert guarantee (reuse `BookkeepingTransaction`'s existing primitives). If instead you must depend on the generalized owner, add a `WP09` dependency and this becomes half-2 work — default is the one-off transaction.
- **AM-4**: the migration never auto-archives; its failure path never reaches archive.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T027 – Migration walk

- **Steps**: Walk existing on-disk matrices; for each non-`pending` result lacking provenance, write `provenance_origin: legacy_unrecorded`, leaving `verified_ref`/`verified_surface_kind` null. Use the WP04 schema's `from_dict`/`to_dict`.
- **Files**: `cli/commands/migrate/backfill_provenance.py` (new).

### Subtask T028 – Commit-or-revert enrolment

- **Steps**: Enrol the whole-corpus write in a commit-or-revert transaction — on success committed to home, on failure fully reverted, no partial state.

### Subtask T029 – AM-4 guard

- **Steps**: Ensure the migration cannot auto-archive and its failure path never reaches the archive operation.

### Subtask T030 – Migration oracle test

- **Steps**: Over a fixture matrix corpus, assert every non-`pending` result ends with a valid `provenance_origin` and `validate_matrix_evidence` passes on the migrated corpus. **The "153 matrices / 40 non-`pending` / 0 provenance" figures are UNVERIFIED at tasking time** — re-measure the real on-disk corpus (`find kitty-specs -name acceptance-matrix.json` + count non-`pending`) and build the fixture from the measured shape before asserting the oracle; do not hard-code 153/40.
- **Files**: `tests/migration/test_backfill_provenance.py` (new).

## Test Strategy

- New: `tests/migration/test_backfill_provenance.py` (oracle over the fixture corpus).
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/migration/test_backfill_provenance.py -q`.

## Risks & Mitigations

- Use realistic corpus shapes (not toy placeholders) so the oracle tests real behaviour.

## Review Guidance

- Confirm the write is transactional (commit-or-revert), and `legacy_unrecorded` leaves both provenance fields null.
- Confirm no auto-archive path (AM-4).

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
