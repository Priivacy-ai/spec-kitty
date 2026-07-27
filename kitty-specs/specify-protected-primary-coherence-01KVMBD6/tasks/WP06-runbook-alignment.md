---
work_package_id: WP06
title: Specify runbook alignment
dependencies:
- WP02
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: fix/specify-protected-primary-coherence
merge_target_branch: fix/specify-protected-primary-coherence
branch_strategy: Planning artifacts for this mission were generated on fix/specify-protected-primary-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/specify-protected-primary-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T021
phase: Phase 4 - Runbook
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3164997"
history:
- timestamp: '2026-06-21T06:45:34Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/mission-steps/software-dev/specify/
create_intent: []
execution_mode: code_change
mission_id: 01KVMBD6HTBP3A9Y5T4EQ80RA9
owned_files:
- src/doctrine/missions/mission-steps/software-dev/specify/prompt.md
role: implementer
tags: []
wp_code: WP06
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Eliminate the runbook↔guard contradiction (FR-011 / SC-005): re-point the `software-dev` specify prompt's
spec-commit instruction from the mission-blind `spec-kitty safe-commit <feature_dir>/spec.md` (which the
guard refuses on a protected primary) to the **new mission-aware spec-commit entrypoint** from WP02.

## Context & Constraints

- **SOURCE template only**: edit `src/doctrine/missions/mission-steps/software-dev/specify/prompt.md`. Do NOT
  edit agent copies under `.claude/`, `.codex/`, etc. — they regenerate via `spec-kitty upgrade`.
- A reviewer following the runbook on a protected primary must never be told to run a refused command.
- **Terminology canon**: use "Mission" (not feature); no `feature*` aliases. Run the terminology guard.
- If the runbook mentions the generic `safe-commit --to-branch` flow, do NOT silently drop the `--to-branch`
  v3.3-deprecation guidance (release-gated, deferred — no version prescription here).

## Subtasks & Detailed Guidance

### Subtask T021 — Re-point the runbook
- Update the specify prompt's commit-boundary lines (the ones that instruct `safe-commit … <feature_dir>/spec.md`)
  to invoke the new entrypoint (e.g. `spec-kitty commit-spec --mission <handle> <feature_dir>/spec.md`, matching
  WP02's actual command name/signature).
- State the protected-primary behavior plainly (the commit materializes the coordination worktree and lands on
  the coordination branch; on an unprotected primary it commits directly).
- Run `pytest tests/architectural/test_no_legacy_terminology.py -q` (CI-only gate — run it locally before push).
- **Files**: `src/doctrine/missions/mission-steps/software-dev/specify/prompt.md`.

## Branch Strategy
- Planning base / merge target: `fix/specify-protected-primary-coherence`. Work in this WP's lane worktree.

## Definition of Done
- The runbook instructs the new entrypoint; no refused-command instruction remains; terminology guard green.

## Risks & Reviewer Guidance
- Confirm SOURCE-only edit (no agent-dir changes) and that the command name/signature matches WP02 exactly
  (bidirectional coupling — verify against the implemented entrypoint, not this prompt's example).

## Activity Log

- 2026-06-21T10:31:46Z – claude:sonnet:python-pedro:implementer – shell_pid=3161350 – Assigned agent via action command
- 2026-06-21T10:34:47Z – claude:sonnet:python-pedro:implementer – shell_pid=3161350 – WP06 (lane-f): specify runbook re-pointed to spec-commit entrypoint; terminology guard green; source-only
- 2026-06-21T10:34:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=3164997 – Started review via action command
- 2026-06-21T10:37:10Z – user – shell_pid=3164997 – Review passed (reviewer-renata): runbook re-pointed to spec-commit; signature matches WP02; source-only; terminology green
