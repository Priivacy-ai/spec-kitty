---
work_package_id: WP08
title: Campsite Sonar (duplicate literals + suppression)
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-011
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
phase: Phase 4 - Debt
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/doctrine/drg/migration/
create_intent: []
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/doctrine/drg/migration/hand_authored_overlay.py
- src/doctrine/artifact_kinds.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP08
---

# Work Package Prompt: WP08 — Campsite Sonar

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` and apply its initialization, boundaries, directives,
and tactics. State which you applied.

## Objective

Clear the cheap, behavior-preserving Sonar debt on files this mission already classifies: hoist
the duplicate DRG-URN literals in `hand_authored_overlay.py` to named constants (FR-009), and fix
the malformed suppression at `artifact_kinds.py:118` (FR-011). Behavior-locked by WP01's golden.

## Context & Constraints

- `hand_authored_overlay.py` **writes the reference graph** — so this WP mutates
  DRG-regeneration-affecting code. Its behavior-preservation is guarded by WP01's golden
  (`regenerate-graph --check`); do not proceed without it (that is why this WP depends on WP01).
- NFR-005: fix by code, never by Sonar-UI Won't-Fix/False-Positive.

## Subtasks

### T039 — Hoist duplicate DRG-URN literals (`hand_authored_overlay.py`)
- The 36 `S1192` findings are repeated DRG URN endpoints (e.g. `"paradigm:domain-driven-design"`
  ×19, `"directive:DISCIPLINED_REFACTORING"` ×14). Hoist each to a named module constant and
  reference it. **Over-DRY hazard:** do NOT collapse two coincidentally-equal-but-independent URNs
  into one constant — that would change edge endpoints. The golden round-trip catches it.

### T040 — Fix malformed suppression (`artifact_kinds.py:118`)  [P]
- Resolve `S7632` (a malformed issue-suppression comment). Either fix the suppression syntax to
  what it intends, or remove it and address the underlying finding. No behavior change.

### T041 — Verify byte-identity
- Run `spec-kitty doctrine regenerate-graph --check` (after `pip install -e .`) → exit 0. Confirm
  `S1192` on the overlay = 0 and `S7632` resolved.

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP08 --agent <name>` (after WP01).

## Definition of Done

- [ ] URN literals hoisted to constants; `S1192` on the overlay = 0.
- [ ] `S7632` resolved by code (not UI triage).
- [ ] `regenerate-graph --check` byte-identical (WP01 golden).

## Risks & Reviewer Guidance

- **Risk**: over-DRY merging distinct URNs. Reviewer: spot-check a few hoisted constants map to
  the exact original strings; confirm the golden round-trip is green.
