---
work_package_id: WP03
title: Protection input reroute (non-deadlock sites)
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-009
- NFR-003
tracker_refs: []
planning_base_branch: fix/specify-protected-primary-coherence
merge_target_branch: fix/specify-protected-primary-coherence
branch_strategy: Planning artifacts for this mission were generated on fix/specify-protected-primary-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/specify-protected-primary-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 2 - Routing
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3118003"
history:
- timestamp: '2026-06-21T06:45:34Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
mission_id: 01KVMBD6HTBP3A9Y5T4EQ80RA9
owned_files:
- src/specify_cli/coordination/policy.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/agent/test_implement_command.py
- tests/specify_cli/cli/commands/agent/test_move_task_guard.py
role: implementer
tags: []
wp_code: WP03
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Route the protection **decision input** through `ProtectionPolicy` (WP01) at the non-deadlock-class
callsites, feeding the existing `commit_guard.evaluate(ProtectionState)` seam — replace, not parallel.
This makes `coordination/policy.py` the real chokepoint it already claims to be (FR-007/FR-009).

## Context & Constraints

- These sites do NOT change behavior (they keep refusing) — only the *provenance* of the protection set
  moves to the resolver. The deadlock-class behavior change lives in WP04.
- **Vacuous-mock hazard (P1/P2)**: existing tests `monkeypatch`/`patch("…implement.protected_branches")`
  and `"…tasks.protected_branches")`. After the reroute the patched name survives but is off the decision
  path — the mock silently does nothing. Re-point each patch at the resolver and add the NFR-003 spy so a
  moved decision cannot hide green.
- `commit_helpers.py` is OWNED BY WP01 — do not edit it here.

## Subtasks & Detailed Guidance

### Subtask T010 — Route `coordination/policy.py:214`
- Replace `protected = protected_branches(repo_root)` + `ref in protected` with the policy:
  `ProtectionPolicy.resolve(repo_root).is_protected(ref)` (or feed `ProtectionState(is_protected=…)` into
  the existing `commit_guard.evaluate`). Resolve at this function's boundary.
- **Files**: `src/specify_cli/coordination/policy.py`.

### Subtask T011 — Route `implement.py:59`; fix P1; NFR-003 spy
- Re-point `implement.py:59` (`branch not in protected_branches(repo_root)`) through the policy.
- Update `tests/agent/test_implement_command.py:428` — patch the resolver, not the now-vacuous
  `implement.protected_branches`. Add a spy asserting the resolver was actually invoked.
- **Files**: `src/specify_cli/cli/commands/implement.py`, `tests/agent/test_implement_command.py`.

### Subtask T012 — Route `tasks.py:882/916`; fix P2
- Re-point both `tasks.py` protection reads through the policy.
- Update `tests/specify_cli/cli/commands/agent/test_move_task_guard.py:163/210/222` patch targets.
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`, `tests/specify_cli/cli/commands/agent/test_move_task_guard.py`.

### Subtask T013 — NFR-003 spy test
- A focused test that drives a protected-decision through a converted path and asserts:
  `ProtectionPolicy.resolve`'s `.kittify`/remote read happens **once** at the boundary and **zero** reads
  occur inside `is_protected`/`commit_guard.evaluate`. Spy the loader + `_remote_default_branch`.
- **Files**: add to `tests/agent/test_implement_command.py` (or a sibling in the owned test set).

## Branch Strategy
- Planning base / merge target: `fix/specify-protected-primary-coherence`. Work in this WP's lane worktree.

## Definition of Done
- `policy.py`/`implement.py`/`tasks.py` read protection from the resolver; no residual direct read.
- P1/P2 mocks re-pointed; NFR-003 spy green. ruff + mypy clean; complexity ≤ 15.

## Risks & Reviewer Guidance
- Reviewer: grep the three files for any surviving `protected_branches(` call — there must be none (the
  WP05 guard will enforce this repo-wide). Confirm the spy fails if a callsite re-reads at decision time.

## Activity Log

- 2026-06-21T09:38:09Z – claude:sonnet:python-pedro:implementer – shell_pid=3104987 – Assigned agent via action command
- 2026-06-21T09:49:30Z – claude:sonnet:python-pedro:implementer – shell_pid=3104987 – WP03 (lane-c): policy/implement/tasks rerouted through ProtectionPolicy (protected_branches(=0); P1/P2 mocks fixed; NFR-003 spy; 86 green
- 2026-06-21T09:49:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=3118003 – Started review via action command
- 2026-06-21T09:56:31Z – user – shell_pid=3118003 – Review passed cycle-2 (reviewer-renata): reroute verified, unused-import fixed, ruff clean
