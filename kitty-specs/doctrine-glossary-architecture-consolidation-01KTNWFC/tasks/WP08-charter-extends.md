---
work_package_id: WP08
title: 'Charter extends: additive multi-org config'
dependencies: []
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
agent: claude
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: python-pedro
authoritative_surface: src/charter/
execution_mode: code_change
owned_files:
- src/charter/**
- tests/charter/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load python-pedro`.

## Objective
Implement `org-charter.yaml` **`extends:`** — additive multi-org charter config with base-org precedence and cycle detection, resolved through the existing `charter.activation_engine` (plan/commit) + `charter.cascade`. **No parallel resolver** (FR-008, R-10, C-005). Non-destructive (C-004).

## Context
- Contract: `contracts/charter-extends-and-drg-regen.md` §C1.
- Code lives in `src/charter/` (`activation_engine.py`, `cascade.py`, `resolver.py`, `reference_resolver.py`, `schemas.py`, org-charter loader). Extend these — do not fork a second resolution path.

## Subtasks
### T023 — `extends:` additive merge
Add the optional `extends:` field to the org-charter schema; implement additive layering with the extending org taking precedence on conflict.
### T024 — Cycle detection + engine integration
Reject `extends:` cycles fail-closed with a structured error; resolve through `activation_engine` plan→commit + cascade (reuse, don't duplicate).
### T025 — Tests
Cover: additive merge, precedence-on-conflict, cycle rejection, non-destructive (existing single-org charters unchanged). `ruff` + `mypy` clean on changed paths (NFR-002).

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`. **No dependencies — start immediately (parallel code lane).**

## Ownership & out-of-map edits
Owned: `src/charter/**`, `tests/charter/**`. **Out-of-map edits allowed with a recorded one-line rationale.**

## Review / Sign-off (R-07)
Doctrine/charter sign-off + reviewer profile (reviewer-renata). Reviewer verifies: single resolution mechanism (no parallel path), non-destructive.

## Definition of Done
- `extends:` resolves additively + validates; cycles rejected; uses activation/cascade only; existing charters unchanged; tests + ruff + mypy green.

## Risks
- Forking a parallel resolver (C-005 violation) — explicitly reuse activation_engine/cascade.
