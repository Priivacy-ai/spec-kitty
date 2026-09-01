---
work_package_id: WP06
title: Regression + gate-integrity harness
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- NFR-001
- NFR-002
planning_base_branch: fix/mission-completion-terminal-state
merge_target_branch: fix/mission-completion-terminal-state
branch_strategy: Planning artifacts for this mission were generated on fix/mission-completion-terminal-state. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-completion-terminal-state unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
phase: Phase 4 - Regression safety net
history:
- at: '2026-08-28T04:51:39Z'
  actor: system
  action: Authored from plan.md WP-F after post-spec squad (F7 baseline + gate integrity)
- at: '2026-08-28T05:30:00Z'
  actor: system
  action: Reworked after post-tasks squad — parity as committed golden not live checkout, pytestmark (renata/pedro)
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/
create_intent:
- tests/specify_cli/test_terminal_state_gate_integrity.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/test_canonical_acceptance.py
- tests/specify_cli/test_acceptance_regressions.py
- tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py
- tests/specify_cli/test_terminal_state_gate_integrity.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/2945
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Apply its initialization, boundaries, directives, and tactics. State which you applied, then begin.

## Objective

Pin the regression baseline and prove the change relaxes nothing beyond the canceled case
(post-spec squad **F7**). "0 regressions" is meaningless without a named baseline; and the
canceled-terminal change lives in the same `_check_lane_gates`/`_evaluate_acceptance_matrix` path
that classifies lanes, so a gate-integrity test is required to prove sibling gates still bite.

## Context

- Evidence: F7 (reviewer). Decisions: [../research.md](../research.md) R7. Spec NFR-001/NFR-002/SC-004,
  and the SC-005 gate-integrity face. Baseline commit: **`a59460ec15`**.
- Depends on WP01–WP04 (this is the safety net over their combined behavior).

## Subtasks

### T021 — Gate-integrity test
`tests/specify_cli/test_terminal_state_gate_integrity.py` (new; declare `pytestmark`): a mission with a canceled-with-
provenance WP still **runs** the acceptance-matrix and issue-matrix verdict gates and can still
**fail** on them (canceled-terminal must not short-circuit sibling gates). Assert a deliberately
failing matrix blocks acceptance even when the only non-approved WP is an acceptable cancellation.

### T022 — "Every WP canceled → not complete" guard
Add coverage (extend `test_finalize_canceled_work_packages.py` or the gate-integrity file) proving a
mission where **all** WPs are canceled is NOT reported complete — the "delivered nothing" guard is an
explicit check, not an accident of terminal-lane classification (spec Edge Case).

### T023 — Pinned-baseline regression + NFR-002 parity
Extend `tests/specify_cli/test_canonical_acceptance.py` and `test_acceptance_regressions.py` with the
approved+canceled→eligible and canceled(synthetic)→blocker cases at command level, and a NFR-002
parity assertion. **Express parity in-diff (renata/pedro): assert the canceled-free golden fixtures
in `test_reducer.py`/`test_canonical_acceptance.py` are byte-unchanged in this diff — NOT by a live
`git checkout a59460ec15`** (a live checkout is an out-of-diff dependency, the #3590 anti-trap in
miniature). Document (in a test docstring or module header) that "0 regressions" is measured against
baseline `a59460ec15` for the suites named in NFR-001, honoring the repo's baseline-red gotcha.

## Branch Strategy

Planning + merge target: `fix/mission-completion-terminal-state`. Worktree per `lanes.json`.

## Definition of Done

- Gate-integrity test fails if a matrix is bypassed for a canceled WP; passes with the correct fix.
- "All-canceled → not complete" covered; NFR-002 parity asserted.
- Named baseline suites green vs `a59460ec15`; `ruff` clean.

## Risks / Reviewer guidance

- The gate-integrity test must genuinely exercise a *failing* matrix — a test that only checks the
  happy path does not prove non-short-circuiting.
- Classify any red per the baseline-red gotcha; known-P0 reds are not this mission's.
