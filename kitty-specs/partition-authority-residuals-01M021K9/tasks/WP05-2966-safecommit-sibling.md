---
work_package_id: WP05
title: '#2966 part-2: the 4th safe-commit sibling routes through the shared helper'
dependencies: []
requirement_refs:
- FR-008
planning_base_branch: fix/partition-authority-residuals
merge_target_branch: fix/partition-authority-residuals
branch_strategy: Planning artifacts for this mission were generated on fix/partition-authority-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/partition-authority-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Scope A (partition)
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/safe_commit_cmd.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 – #2966 part-2: the 4th safe-commit sibling routes through the shared helper

**Concern**: IC-05 · **Requirements**: FR-008 · **Priority**: P2

## Purpose
Three of four write-target committers route through `resolve_write_target_or_degrade`; `_resolve_mission_aware_target` still calls `resolve_placement_only` directly.

## Files / changes
- `cli/commands/safe_commit_cmd.py:278-307` — route through `resolve_write_target_or_degrade` (+ pre-gate + caught-set), PRESERVING `CONSOLIDATED_CONTENT_ABSENT → MissionAwareCommitRefused` and benign `FileNotFoundError`/`ValueError` → `None` degrade.

## Coordination & guardrails
Assert refusal-parity (both the raise and the degrade paths), not just that the helper is called.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope A**: a live coord-topology e2e (NFR-001) that is red-before/green-after, with the coord worktree registered.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
