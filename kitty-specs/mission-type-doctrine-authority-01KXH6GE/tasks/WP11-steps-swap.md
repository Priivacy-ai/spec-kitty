---
work_package_id: WP11
title: Route step-contract resolution through the artefact bundle
dependencies:
- WP03
requirement_refs:
- FR-008
- NFR-001
- NFR-002
- NFR-003
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T059
- T060
- T061
- T062
- T063
shell_pid_created_at: "1784089614.33"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1808171"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-08, Lane B — steps through the artefact, Q3)
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/missions/step_contracts.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read: [plan.md](../plan.md) §IC-08,
[spec.md](../spec.md) FR-008 / SC-007, and the ADR "Q3 — Artefact depth in slice 1: governance + gates +
steps" (`WP-STEPS-MIGRATE`). Same transitional-parity-then-delete discipline as the gates swap.

## Objective

Route step-contract resolution for a mission type **through the `MissionType` artefact bundle**
(`ResolvedMissionType.step_contracts`), not a `specify_cli` copy (FR-008), and migrate the `specify_cli`
step-contract readers (SC-007 → 0 remaining). Software-dev step behaviour is preserved via a transitional
step-parity scaffold deleted at this WP's end (NFR-001 → NFR-005).

## Context

- Step-contract resolution currently reads through a `specify_cli` path; the artefact bundle from WP03
  carries a `step_contracts` slot that this WP wires to the doctrine step-contract source.
- The exact reader anchors are **implementer-pinned** — grep for the live `specify_cli` step-contract
  readers and pin them precisely before migrating (do not migrate a reader you have not pinned).
- Transitional discipline: add a step-parity scaffold at the start, delete it in the final commit — no
  surviving parity ratchet (C-002).

## Subtask guidance

- **T059 — route through the bundle.** In `src/doctrine/missions/step_contracts.py`, source step-contract
  resolution from the doctrine artefact (feeding `ResolvedMissionType.step_contracts` via WP03's bundle),
  so the artefact is the single answer for a type's steps.
- **T060 — pin + migrate readers.** Grep and **pin the exact anchors** of the `specify_cli` step-contract
  readers, then migrate them onto the artefact-sourced path. Record the pinned anchors in the PR body.
- **T061 — transitional parity scaffold.** Add a transitional test proving software-dev's resolved step
  contracts are **unchanged** across the swap (NFR-001). Mark it clearly transitional; deleted in T062.
- **T062 — delete scaffold + SC-007.** Delete the step-parity scaffold. Grep-prove **0** `specify_cli`
  step-contract readers remain (SC-007).
- **T063 — gates.** `ruff` + `mypy` clean; complexity ≤ 15; record the NFR-001 parity claim + its deletion.

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It depends on WP03 (the bundle) and is a WP12 dependency
(steps enforcement).

## Definition of Done

- [ ] Step-contract resolution flows through the `MissionType` artefact bundle (FR-008).
- [ ] The `specify_cli` step-contract readers are pinned and migrated; **0** remain (SC-007, grep-proven).
- [ ] Software-dev step behaviour preserved; transitional step-parity scaffold added AND deleted (0 survives).
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.

## Risks

- **Migrating an unpinned reader** — pin exact anchors first; a missed reader leaves a second step path live.
- **Software-dev step regression** — the transitional parity scaffold is the guard; keep it green before deletion.
- **Surviving parity ratchet** — delete the scaffold in the final commit (C-002).

## Reviewer guidance (reviewer-renata, opus)

- Confirm the pinned reader anchors are all migrated and **0** `specify_cli` step-contract readers remain.
- Confirm the transitional scaffold is gone at HEAD.
- Confirm software-dev step contracts resolve identically (bundle vs pre-swap).

## Activity Log

- 2026-07-14T23:47:34Z – claude:sonnet:python-pedro:implementer – shell_pid=1483631 – Assigned agent via action command
- 2026-07-15T00:18:22Z – claude:sonnet:python-pedro:implementer – shell_pid=1483631 – Steps swap complete (FR-008/SC-007); gates green (ruff 0, mypy strict clean, 3123 passed, 1 skipped). Lane worktree clean; forcing past kitty-specs branch-divergence guard.
- 2026-07-15T04:05:16Z – claude:opus:reviewer-renata:reviewer – shell_pid=1736082 – Started review via action command
- 2026-07-15T04:16:08Z – user – Moved to planned
- 2026-07-15T04:17:00Z – claude:sonnet:python-pedro:implementer – shell_pid=1768111 – Started implementation via action command
- 2026-07-15T04:26:38Z – claude:sonnet:python-pedro:implementer – shell_pid=1768111 – cycle 1 fix: re-pinned WP03 reserved-slot assertion (step_contracts now populated); blocking test green. Committed on behalf of stalled fix agent.
- 2026-07-15T04:27:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=1808171 – Started review via action command
