---
work_package_id: WP09
title: Reconcile expected-artifacts upward into the doctrine tree
dependencies: []
requirement_refs:
- FR-007
- NFR-002
- NFR-003
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T048
- T049
- T050
- T051
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1338834"
shell_pid_created_at: "1784067763.7"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-07a, Lane D detachable — reconcile before flip)
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/missions/software-dev/expected-artifacts.yaml
- src/doctrine/missions/documentation/expected-artifacts.yaml
- src/doctrine/missions/research/expected-artifacts.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read: [plan.md](../plan.md) §IC-07 (esp.
"Reconcile deltas (upward)" + "detachable, non-blocking lane"), [spec.md](../spec.md) FR-007,
[contracts/resolution-and-enforcement.md](../contracts/resolution-and-enforcement.md) C4, and the ADR
"The dossier migration is a gated, isolated swap" (step 1). Source of the deltas: **#2628**.

## Objective

Reconcile the drifted `expected-artifacts.yaml` **upward** into the doctrine tree so the doctrine copies
carry every entry the `specify_cli` copies are ahead on (FR-007). This is step 1 of the detachable Lane-D
swap and the **hard predecessor** of the WP10 reader flip — never flip before the doctrine tree is
reconciled. This WP does **not** touch any reader; it only brings the doctrine tree up to parity.

## Context

- The two `expected-artifacts.yaml` trees have drifted **specify_cli-ahead** (no parity guard, #2628):
  the `specify_cli` copies carry `runtime.charter-lint.decay` → `lint-report.json`, a `blocking: false`
  flag, and the `occurrence_map.yaml` bulk-edit NOTE comment block that the doctrine copies lack.
- This is a **detachable, non-blocking** lane — it must NOT gate the enforcement join (WP12). The reader
  flip (WP10) may defer to slice 2 on deep drift, but this reconciliation still lands regardless.
- Reconcile direction is **upward only** (specify_cli → doctrine); do not edit the `specify_cli` copies
  here (WP10 deletes them after the flip).

## Subtask guidance

- **T048 — port `charter-lint.decay`/`lint-report`.** Port the `runtime.charter-lint.decay` →
  `lint-report.json` entry from each `specify_cli/missions/<type>/expected-artifacts.yaml` upward into the
  doctrine `src/doctrine/missions/<type>/expected-artifacts.yaml` (software-dev, documentation, research).
- **T049 — port `blocking: false`.** Port the `blocking: false` flag upward for the affected entries.
- **T050 — port the occurrence_map NOTE block.** Port the `occurrence_map.yaml` bulk-edit **NOTE comment
  block** upward — it is behaviourally load-bearing docs, not decoration; preserve it verbatim.
- **T051 — parity baseline.** Diff each doctrine `<type>/expected-artifacts.yaml` against its `specify_cli`
  counterpart and confirm content parity post-reconcile (this is the pre-flip baseline WP10's transitional
  scaffold asserts against). Record any residual drift explicitly — if deep, WP10's flip may defer, but the
  deferral is recorded, never silent. `ruff`/`mypy` are N/A for YAML; run the terminology guard.

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It is a Lane-D **root** (no deps) and the hard predecessor
of WP10. This lane is **non-blocking** for WP12.

## Definition of Done

- [ ] `charter-lint.decay`/`lint-report.json`, `blocking: false`, and the occurrence_map NOTE block are
      ported upward into the three doctrine `expected-artifacts.yaml` copies.
- [ ] Each doctrine `<type>/expected-artifacts.yaml` is content-equivalent to its `specify_cli` counterpart
      (pre-flip parity baseline established), or residual drift is explicitly recorded.
- [ ] No `specify_cli` copy edited (upward-only); no reader touched (that is WP10).
- [ ] Terminology guard green.

## Risks

- **Silent deferral** — if reconciliation reveals deep drift, record it; the deferral must never be silent
  (NFR-004).
- **Editing downward** — reconcile is upward-only; the `specify_cli` copies stay until WP10 deletes them.
- **Dropping the NOTE block** — the occurrence_map comment is load-bearing; port it verbatim.

## Reviewer guidance (reviewer-renata, opus)

- Diff doctrine vs specify_cli `expected-artifacts.yaml` per type; confirm the three deltas landed upward.
- Confirm no `specify_cli` copy or reader was modified in this WP.
- Confirm any residual drift is explicitly recorded for WP10's flip decision.

## Activity Log

- 2026-07-14T22:12:48Z – claude:sonnet:python-pedro:implementer – shell_pid=1313647 – Assigned agent via action command
- 2026-07-14T22:18:50Z – user – shell_pid=1313647 – WP09 advance to claimed
- 2026-07-14T22:18:56Z – user – shell_pid=1313647 – WP09 advance to in_progress
- 2026-07-14T22:21:54Z – claude:sonnet:python-pedro:implementer – shell_pid=1313647 – Ready: doctrine expected-artifacts reconciled upward to specify_cli parity (charter-lint.decay/lint-report/blocking/NOTE). software-dev + research byte-identical to specify_cli; documentation retains a doctrine-ahead accept-phase delta (out of scope for upward reconcile) recorded for WP10.
- 2026-07-14T22:22:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=1338834 – Started review via action command
- 2026-07-14T22:27:35Z – user – shell_pid=1338834 – Review passed: upward-only reconcile verified. 3 doctrine expected-artifacts.yaml got runtime.charter-lint.decay->lint-report.json + blocking:false (all 3) and the sw-dev occurrence_map NOTE block. sw-dev+research byte-identical to specify_cli; documentation's only residual diff is pre-existing doctrine-ahead accept-phase block, correctly NOT stripped (recorded for WP10). No specify_cli copy or reader edited. YAML valid; 87 tests pass.
