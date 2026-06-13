---
work_package_id: WP02
title: 'Accept gate idempotency seam (FR-002, #1883 ROOT-β)'
dependencies: []
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T006
- T007
- T008
phase: Phase 1 - Independent lanes
assignee: ''
agent: ''
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/acceptance/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/acceptance/**
- src/specify_cli/cli/commands/accept.py
- tests/specify_cli/acceptance/**
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Accept gate idempotency

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
- **T006 (ATDD FIRST):** convergence test — run accept twice on an unchanged accepted-mission fixture, in BOTH committing and `--no-commit`/diagnose modes: second run must converge with no `git_dirty` trip. Expect RED on current code (the #1883 repro: snapshot at `acceptance/__init__.py:934` precedes the non-idempotent writes at `:753-754`; `_commit_residual_acceptance_artifacts` gated on `commit_required` at `accept.py:365`).
- **T007:** the seam — define the ACCEPT_OWNED_PATHS model (data-model.md §4): take the dirty snapshot BEFORE any accept-owned write of the current run AND exclude accept-owned paths left dirty by prior non-committing runs. Choose the minimal mechanics that satisfies C-GATE-2; document the ownership set as a module constant.
- **T008:** mode matrix test (commit / --no-commit / diagnose × clean / prior-run-dirty trees) + ensure mission-131's operator-workaround commits (upstream) are unaffected.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
Convergence property holds in every mode; the original #1883 loop fixture passes; acceptance suites green; ruff/mypy clean.

## Review Guidance
reviewer-renata. Adversarial: craft a tree where a NON-accept-owned file is dirty → gate must STILL trip (the exclusion must not over-exclude).

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
