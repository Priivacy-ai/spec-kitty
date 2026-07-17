---
work_package_id: WP07
title: YAML cutover + parity scaffold lifecycle + aggregate gate
dependencies:
- WP04
- WP06
requirement_refs:
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
phase: Phase 4 - Cutover
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1632951"
shell_pid_created_at: "1784242753.23"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission_types/
create_intent:
- tests/doctrine/missions/test_softwaredev_parity_scaffold.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/mission_types/documentation.yaml
- src/doctrine/missions/mission_types/research.yaml
- src/doctrine/missions/mission_types/plan.yaml
- src/doctrine/missions/mission_types/software-dev.yaml
- tests/doctrine/missions/test_softwaredev_parity_scaffold.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – YAML cutover + scaffold lifecycle

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (`implementer`, `claude`).

---

## Objective

Perform the final cutover: prove software-dev parity, remove `action_sequence`/`template_set` from the 4
`mission_types/*.yaml`, then delete the transitional scaffold — and run the full aggregate gate locally (this is
the ONLY merge-readiness signal; there is no PR/CI per WP). Depends on WP04 (extractor on projection) + WP06
(consumers on the seam) — both must be green so the fields are safe to remove.

## Intra-WP commit ordering (LOAD-BEARING — do NOT collapse)
1. **Add the parity scaffold, prove it green WHILE the YAML is still authored.** `tests/doctrine/missions/test_softwaredev_parity_scaffold.py` asserts `project_action_sequence`/`project_template_set` for software-dev equal the still-present authored `mission_types/software-dev.yaml` values, byte-for-byte (NFR-001a). This is the disposable swap check (C-006).
2. **Remove `action_sequence` + `template_set`** from all 4 `mission_types/*.yaml` + reconcile anything that referenced them. Re-run the full suite — projection now sources everything.
3. **Delete the parity scaffold** (`test_softwaredev_parity_scaffold.py`). Its job is done; the enduring proofs live upstream (WP02 module tests, WP03 round-trip, WP05 referential-integrity).

Do NOT collapse this into one commit that removes the YAML before the scaffold ran green — that defeats red-first.

## Subtasks

### T021 — Add scaffold, prove green (YAML still authored)
Author the parity scaffold; run it green against the still-present YAML.

### T022 — Remove the flat fields + reconcile
Delete `action_sequence`/`template_set` from documentation/research/plan/software-dev `mission_types/*.yaml`.
Reconcile any residual reader (should be none after WP04/WP06). Re-run doctrine + runtime suites.

### T023 — Delete scaffold + full aggregate gate (local)
Delete the scaffold. Run the complete local gate — **this is the merge signal**:
- `spec-kitty doctrine regenerate-graph --check` → fresh; DRG **280 / 757 / 10** (0 delta).
- `pytest tests/architectural/` (incl. `test_no_legacy_terminology.py`) → green.
- `pytest tests/doctrine tests/runtime tests/charter` (the touched surfaces) → green.
- `ruff check` + `mypy --strict` on the diff → clean, zero new suppressions.

## Branch Strategy
Base/merge: `feat/mission-step-authority` (stacked on S-A; lands together, no PR). Lanes base on the S-A-bearing
HEAD. Implement: `spec-kitty agent action implement WP07 --agent <name>`.

## Definition of Done
- [ ] Parity scaffold ran green while YAML authored, THEN YAML removed, THEN scaffold deleted (3 ordered commits).
- [ ] All 4 `mission_types/*.yaml` no longer carry `action_sequence`/`template_set`.
- [ ] DRG **280 / 757 / 10** fresh; full arch/doctrine/runtime suites green; ruff/mypy clean.
- [ ] No parity scaffold remains in the tree.

## Risks / Reviewer guidance
- Removing the YAML before the projection sources it = breakage. Reviewer confirms WP04/WP06 landed first and the commit ordering held.
- This WP carries the aggregate-gate burden (no CI safety net) — reviewer treats the local gate output as the merge gate.

## Requirements: FR-002, FR-003

## Activity Log

- 2026-07-16T20:39:52Z – claude:sonnet:python-pedro:implementer – shell_pid=1388883 – Assigned agent via action command
- 2026-07-16T22:58:58Z – claude:sonnet:python-pedro:implementer – shell_pid=1388883 – Cutover complete: 3 ordered commits (scaffold->remove YAML+narrow CLI consumers->retire scaffold). Aggregate gate GREEN: DRG 280/757/10 fresh; architectural 1016 passed; doctrine+runtime+charter+cli pass; ruff clean; mypy S-B clean. Reconciled 2 residual YAML-readers + arch campsite. Pre-existing-main reds (template-not-found/sphinx/flaky-sync) documented, NOT S-B.
- 2026-07-16T22:59:16Z – claude:opus:reviewer-renata:reviewer – shell_pid=1632951 – Started review via action command
