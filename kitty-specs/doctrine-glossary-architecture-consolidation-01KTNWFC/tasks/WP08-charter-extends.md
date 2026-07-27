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
base_branch: kitty/mission-doctrine-glossary-architecture-consolidation-01KTNWFC
base_commit: 7e8ba507b05d4a38ba4edf81f11008a583d0bc29
created_at: '2026-06-11T14:48:41.422868+00:00'
subtasks:
- T023
- T024
- T025
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "795622"
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

## Activity Log

- 2026-06-11T15:06:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=795622 – Started review via action command
- 2026-06-11T15:10:20Z – user – shell_pid=795622 – Review passed: FR-008 canonical extends resolver. Verified prior parallel DFS (specify_cli.doctrine.org_charter._resolve_chain) existed pre-WP at base and is now DELETED, delegating to canonical charter.org_extends.resolve_extends_order (sole chain-walk in codebase). Charter-layer purity confirmed (zero specify_cli import; delegation specify_cli->charter only). Fail-closed proven: cycle-of-2/self-ref/missing-base each reject BEFORE any order returned; legacy OrgCharterCycleError/OrgCharterExtensionError contract preserved via re-raise. Legacy test_org_charter*.py UNCHANGED and green. Gates: 216 charter+doctrine tests pass (10 new), 163 architectural (charter/layer/boundary/facade) pass, ruff+mypy clean on 4 files. Out-of-map edit to org_charter.py justified (C-005). Clean status lifecycle (no force). Reframe legitimate: activation_engine has no extends-topology to host; contract phrasing denotes validate-before-mutate discipline, which the new module follows.
