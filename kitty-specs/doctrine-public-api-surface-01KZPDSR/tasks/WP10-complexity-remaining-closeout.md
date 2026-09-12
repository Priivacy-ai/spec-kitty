---
work_package_id: WP10
title: 'Complexity refactor: remaining S3776 + regression closeout'
dependencies:
- WP01
requirement_refs:
- FR-010
- NFR-001
- NFR-003
- NFR-005
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T045
- T046
- T047
- T048
- T049
phase: Phase 4 - Debt
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/doctrine/versioning.py
- src/doctrine/base.py
- src/doctrine/agent_profiles/repository.py
- src/doctrine/drg/validator.py
- src/doctrine/drg/merge.py
- src/doctrine/drg/org_pack_loader.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP10
---

# Work Package Prompt: WP10 — Complexity refactor: remaining S3776 + regression closeout

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and apply its initialization, boundaries, directives, and
tactics. **Also load the semantic-compression / disciplined-refactoring doctrine**
(`spk-doctrine-semantic-compression`) — it governs this behavior-preserving refactor. State which
you applied.

## Objective

Reduce the remaining 6 S3776 doctrine functions to ≤ 15, behavior-preserving (FR-010, NFR-003),
with per-helper tests; then confirm the mission's regression-delta gate (NFR-001) and no-Sonar-UI-
triage rule (NFR-005) in the PR body.

## Context & Constraints

- Behavior lock: WP01's golden `regenerate-graph --check` must stay exit-0 for the `drg/*` files
  (validator/merge/org_pack_loader feed DRG). `versioning.py`, `base.py`,
  `agent_profiles/repository.py` are not DRG-emitting — guard them with focused unit tests instead.
- No complexity-shuffling; every extracted helper has its own test. No suppressions / no UI triage.
- **Golden-first for non-DRG files (post-tasks squad):** `versioning.py`, `base.py`,
  `agent_profiles/repository.py` have no `regenerate-graph` lock. Capture their behavior test
  (or output snapshot) **before** refactoring and commit it green against pre-refactor behavior —
  a characterization test written after the change only proves self-consistency, not equivalence.
- **Preserve charter-re-exported symbols:** `charter.drg` imports `OrgDRGConflict`,
  `OrgDRGConflictError`, `merge_three_layers`, and the private `_bridge_org_edge_to_drg_edge` from
  `doctrine.drg.merge`. Do NOT rename/inline these — refactor inside function bodies only, or
  WP03's identity test breaks.

## Subtasks

### T045 — Refactor `versioning.py:316` (cc 65) + `base.py:227` (cc 28)  [P]
- Decompose into tested helpers; ≤ 15 each.

### T046 — Refactor `agent_profiles/repository.py:365` (cc 36)  [P]
- Decompose the loader; ≤ 15; focused tests for the extracted branches.

### T047 — Refactor `drg/validator.py:35` (cc 24), `drg/merge.py:941` (cc 16), `drg/org_pack_loader.py:746` (cc 16)  [P]
- Decompose; ≤ 15 each. These feed DRG — verify with `regenerate-graph --check`.

### T048 — Per-helper tests + verify
- Every extracted helper has a focused test; `ruff check` clean on all 6 files; every touched
  function ≤ 15; `regenerate-graph --check` byte-identical.

### T049 — Regression-delta + no-triage closeout (PR body)
- Confirm no merge-base-green test goes red on this branch (classify any pre-existing reds per
  DIR-013 / the Pre-existing Failure Reporting Rule); confirm zero doctrine CRITICAL Sonar issues
  were resolved via Won't-Fix/False-Positive during the mission window. Record both in the PR body
  (per the charter's Sonar-UI-work callout).

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP10 --agent <name>` (after WP01). Independently revertable.

## Definition of Done

- [ ] All 6 functions ≤ 15; per-helper tests green; no suppressions.
- [ ] `regenerate-graph --check` byte-identical for the DRG-feeding files.
- [ ] SC-004: zero open doctrine CRITICAL Sonar smells; SC-005/NFR-001 regression-delta documented in PR body.

## Risks & Reviewer Guidance

- **Risk**: a non-DRG file's refactor changes resolution behavior with no golden to catch it.
  Reviewer: confirm `versioning.py`/`base.py`/`repository.py` carry behavior tests, not just cc numbers.
- **Reviewer**: verify the PR body's regression-delta + no-triage statements are true, not boilerplate.
