---
work_package_id: WP13
title: Retire COORD_OWNED_STATUS_FILES + advance_branch_ref param + coord-staging skip (IC-07c)
dependencies:
- WP12
requirement_refs:
- C-001
- C-010
- FR-009
- FR-012
- NFR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T067
- T068
- T069
- T070
- T071
phase: Phase 8 - Exemption Retirements
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/__init__.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/status/__init__.py
- src/specify_cli/merge/ordering.py
- src/specify_cli/lanes/merge.py
- src/specify_cli/coordination/commit_router.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP13 – Retire COORD_OWNED_STATUS_FILES (IC-07c)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

Retire the ONE mechanism with 8 consumer sites (inseparable by owner contract C5): `COORD_OWNED_STATUS_FILES`, its `advance_branch_ref` parameter, and the coord-staging skip of the same set. Migrate to the owner/canonical classifier. **Scheduled late** — two consumers are in the `merge/` package.

**Done** = `COORD_OWNED_STATUS_FILES` and its `advance_branch_ref` parameter are absent from `src/`; behaviour preserved (C6/C-010).

## Context & Constraints

- Owner contract C5 (registry rows #3+#4, one mechanism), C-001↔IC-07(c) tension resolution: **schedule the whole of group (c) after the `merge/`-package rebase point, as one work package** — do NOT split it (C5 forbids). C-001's precondition is discharged; the residual is only "re-fetch before starting".
- **Consumers (grep-confirmed, 8 sites)**: `status/__init__.py`, `merge/ordering.py`, `coordination/coherence.py`, `coordination/commit_router.py`, `cli/commands/implement.py`, `cli/commands/implement_cores.py`, `git/ref_advance.py`, `lanes/merge.py`.
- Retiring one consumer leaves the set alive — retire **atomically** across all 8 sites (C5).

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T067 – Re-fetch, then retire the mechanism (8 sites)

- **Steps**: Re-fetch `upstream/main` first (C-001 residual). Retire `COORD_OWNED_STATUS_FILES` + `advance_branch_ref` param + the coord-staging skip across all 8 sites in one pass.

### Subtask T068 – Migrate to owner/canonical classifier (FR-012)

- **Steps**: Route the retired behaviour through the canonical churn classifier / owner (WP09).

### Subtask T069 – Delete the registry row

- **Steps**: Delete this mechanism's row in the WP10 registry.

### Subtask T070 – Preserve behaviour; merge/ care (C-010)

- **Steps**: No previously-succeeding operation now fails; take care in the `merge/`-package consumers.

### Subtask T071 – Migrate mechanism tests

- **Steps**: Migrate mechanism-asserting tests to the owner/classifier.

## Test Strategy

- Run: `PWHEADLESS=1 uv run --extra test pytest tests/architectural/ tests/merge/ -q`.

## Risks & Mitigations

- Owns `status/__init__.py`, `merge/ordering.py`, `lanes/merge.py`, `coordination/commit_router.py`. Leeway (serial): `coherence.py` (WP09), `implement.py`/`git/ref_advance.py` (WP01), `implement_cores.py` (WP14).

## Review Guidance

- Confirm the full 8-site set is retired atomically (no consumer left consulting the set).
- Confirm merge-package behaviour preserved.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
