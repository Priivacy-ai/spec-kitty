---
work_package_id: WP08
title: Campsite — split transaction.py before the owner opens it
dependencies:
- WP01
requirement_refs:
- NFR-007
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
phase: 'Phase 6 - Owner: Campsite & Generalization'
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/transaction.py
create_intent:
- src/specify_cli/coordination/atomic_write.py
- src/specify_cli/coordination/legacy_resolution.py
- src/specify_cli/coordination/transaction_errors.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/coordination/transaction.py
- src/specify_cli/coordination/atomic_write.py
- src/specify_cli/coordination/legacy_resolution.py
- src/specify_cli/coordination/transaction_errors.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Campsite: split transaction.py

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

**Behaviour-free** extraction so the owner generalisation (WP09) lands in a module with room. Measured clusters, all pure or import-only. Net **1345 → ~914 LOC**.

**Done** = the extraction is behaviour-preserving and `tests/specify_cli/coordination/test_transaction.py` (1046 LOC) stays green **unchanged**.

## Context & Constraints

- Plan IC-12; owner contract C10 (size). NFR-007.
- **Keep this a separate WP from WP09**: a behaviour-free refactor inside a behaviour-changing diff is unreviewable.
- The final module name choices (`atomic_write.py`, `legacy_resolution.py`, `transaction_errors.py`) are indicative — confirm against the codebase's existing coordination-module naming at implement time and adjust `owned_files`/`create_intent` if renamed.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T041 – Extract confined-atomic-write (~170 LOC)

- **Steps**: Move the confined-atomic-write cluster into a sibling module; no behaviour change.

### Subtask T042 – Extract legacy-mission resolution (~189 LOC)

- **Steps**: Move legacy-mission resolution into a sibling module; while doing so, fold the **3 redundant `load_meta` reads on the same path into 1** (the only permitted micro-cleanup — still behaviour-preserving).

### Subtask T043 – Extract the error hierarchy (~67 LOC)

- **Steps**: Move the transaction error classes into a sibling module; keep import paths working.

### Subtask T044 – Delete the dead `threading.local()` sentinel (~5 LOC)

- **Steps**: Remove the sentinel — confirm zero repo-wide references first (`grep -rn`).

### Subtask T045 – Verify size + oracle green

- **Steps**: Confirm net ~914 LOC. Run `test_transaction.py` — it must pass **unchanged**. Do **NOT** remove the 6 `flattened` references here (separate track R-005).

## Test Strategy

- Oracle: `tests/specify_cli/coordination/test_transaction.py` green unchanged.
- Run: `PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/coordination/test_transaction.py -q`.

## Risks & Mitigations

- Low by construction. The main risk is scope creep into behaviour — resist it; anything non-trivial belongs to WP09.

## Review Guidance

- Confirm zero behaviour change (oracle unchanged and green).
- Confirm the `flattened` references were left alone.

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
