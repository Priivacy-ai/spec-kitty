---
work_package_id: WP15
title: Retire RUNTIME_STATE_ALLOWLIST (IC-07e)
dependencies:
- WP09
- WP10
requirement_refs:
- C-010
- FR-009
- NFR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T076
- T077
- T078
phase: Phase 8 - Exemption Retirements
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/bulk_edit/diff_check.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/bulk_edit/diff_check.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP15 – Retire RUNTIME_STATE_ALLOWLIST (IC-07e)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

Retire `RUNTIME_STATE_ALLOWLIST` / `_runtime_state_exemption` — single file, fully isolated. Delete its registry row.

**Done** = both symbols absent from `src/`; behaviour migrated to the owner/canonical classifier (C6/C-010).

## Context & Constraints

- Owner contract C5 (registry row #7). Plan IC-07(e): "single file, fully isolated."
- **Consumer (grep-confirmed)**: `src/specify_cli/bulk_edit/diff_check.py` only. Genuinely parallel with the rest of the retirement chain.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T076 – Retire the symbols

- **Steps**: Remove `RUNTIME_STATE_ALLOWLIST` and `_runtime_state_exemption` from `bulk_edit/diff_check.py`; route the behaviour through the owner/canonical churn classifier.

### Subtask T077 – Delete the registry row

- **Steps**: Delete this mechanism's row in the WP10 registry.

### Subtask T078 – Migrate tests; preserve behaviour

- **Steps**: Migrate any mechanism-asserting tests; no previously-succeeding operation now fails.

## Test Strategy

- Run: `PWHEADLESS=1 uv run --extra test pytest tests/architectural/ tests/specify_cli/bulk_edit/ -q`.

## Risks & Mitigations

- Owns `bulk_edit/diff_check.py` only — no leeway edits, fully isolated, parallel.

## Review Guidance

- Confirm per-symbol absence; behaviour preserved.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
