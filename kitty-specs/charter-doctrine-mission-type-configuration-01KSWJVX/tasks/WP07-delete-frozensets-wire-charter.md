---
work_package_id: WP07
title: Delete frozensets + wire all 4 call sites to charter
dependencies:
- WP05
- WP06
requirement_refs:
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 98b55898baa5cc522a14fcee1e1f70dcfccc4ec2
created_at: '2026-05-30T20:32:00.923453+00:00'
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
- T047
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3380013"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/next/decision.py
- tests/specify_cli/next/test_runtime_bridge_dispatch.py
- tests/specify_cli/next/test_decision_dispatch.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP07 — Delete frozensets + wire all 4 call sites to charter

## Context

The hardcoded dispatch tables are the core technical debt this mission removes. Two frozensets in two files encode the same information:

- `_COMPOSED_ACTIONS_BY_MISSION` in `src/specify_cli/next/runtime_bridge.py` (~line 827)
- `_COMPOSED_ACTIONS_FOR_PROMPT` in `src/specify_cli/next/decision.py` (~line 535)

Both tables "must stay in sync" (comment at decision.py:532). After this WP, `charter.resolve_action_sequence()` is the single source of truth.

Research identified 4 call sites:
| File | Approx. Line | Context |
|---|---|---|
| `runtime_bridge.py` | 876 | `_should_dispatch_via_composition()` |
| `runtime_bridge.py` | 988 | Inline check in dispatch path |
| `runtime_bridge.py` | 2090 | `_should_dispatch_via_composition()` called from hot path |
| `decision.py` | 573 | `_build_prompt_or_error` |

**Critical**: NFR-002 requires zero regression in `spec-kitty next` behaviour for all existing software-dev missions.

## Objective

Delete both frozenset tables. Wire all 4 call sites to `charter.resolve_action_sequence()`. Verify zero regression with integration tests.

## Subtasks

### T041 — Delete _COMPOSED_ACTIONS_BY_MISSION from runtime_bridge.py

Open `src/specify_cli/next/runtime_bridge.py`.

1. Find `_COMPOSED_ACTIONS_BY_MISSION` (approximately line 827). Read the comment above it.
2. Verify you understand all 3 call sites before deleting.
3. Delete the frozenset definition.
4. Delete any import or type alias used exclusively by this table.

### T042 — Replace runtime_bridge.py line 876 call site

In `_should_dispatch_via_composition()` (line 876 region):

Before:
```python
if action in _COMPOSED_ACTIONS_BY_MISSION.get(mission, frozenset()):
    ...
```

After:
```python
sequence = charter.resolve_action_sequence(mission, repo_root)
if action in sequence:
    ...
```

The `repo_root` parameter must be threaded into `_should_dispatch_via_composition()` if it is not already present. Trace the call chain from the function's callers to find where `repo_root` is available.

### T043 — Replace runtime_bridge.py line 988 call site

Find the inline check at line 988 region:

Before:
```python
if action in _COMPOSED_ACTIONS_BY_MISSION.get(mission, frozenset()):
```

After:
```python
if action in charter.resolve_action_sequence(mission, repo_root):
```

### T044 — Replace runtime_bridge.py line 2090 call site

Find the `_should_dispatch_via_composition()` call at line 2090 (from the dispatch hot path). This is covered by T042's replacement of the function body — verify that the hot path call site now exercises the live charter lookup path.

If the hot path does a separate inline check beyond calling the function, update it similarly to T043.

### T045 — Delete _COMPOSED_ACTIONS_FOR_PROMPT from decision.py

Open `src/specify_cli/next/decision.py`.

1. Find `_COMPOSED_ACTIONS_FOR_PROMPT` (~line 535). Read the comment about sync with `runtime_bridge.py`.
2. Delete the frozenset definition.
3. Delete any import or type alias used exclusively by this table.

### T046 — Replace decision.py line 573 call site

In `_build_prompt_or_error()` (~line 573):

Before:
```python
if wp_id is None and action in _COMPOSED_ACTIONS_FOR_PROMPT.get(mission_type, frozenset()):
```

After:
```python
if wp_id is None and action in charter.resolve_action_sequence(mission_type, repo_root):
```

Thread `repo_root` into the function if not already present. Check the call chain to find where `repo_root` is available.

### T047 — Integration tests + NFR-002 regression gate

Write or extend `tests/specify_cli/next/test_runtime_bridge_dispatch.py` and `tests/specify_cli/next/test_decision_dispatch.py`:

Test cases that must pass (NFR-002 regression gate):
- `spec-kitty next` with a software-dev mission at `specify` lane dispatches `kind=step` with the specify prompt
- `spec-kitty next` with a software-dev mission at `plan` lane dispatches correctly
- `spec-kitty next` with a software-dev mission at `implement` lane dispatches correctly
- `spec-kitty next` with a software-dev mission at `review` lane dispatches correctly
- `_should_dispatch_via_composition()` returns `True` for all built-in software-dev steps
- `_build_prompt_or_error()` resolves the correct prompt for each software-dev step

These tests must use the live `charter.resolve_action_sequence()` path (not mock the frozenset tables, which no longer exist).

Also add a performance smoke test: `charter.resolve_action_sequence("software-dev", repo_root)` completes within 100ms on a warm filesystem (NFR-001: `spec-kitty next` cold-start overhead ≤100ms for built-in-only projects).

## Acceptance Criteria

- [ ] Both frozenset definitions are gone from both files
- [ ] `grep -r "_COMPOSED_ACTIONS_BY_MISSION\|_COMPOSED_ACTIONS_FOR_PROMPT" src/` returns no results
- [ ] All 4 call sites use `charter.resolve_action_sequence()`
- [ ] `spec-kitty next` integration tests for all software-dev steps pass (NFR-002)
- [ ] No `specify_cli.*` → `doctrine.*` direct imports introduced (C-004)
- [ ] `mypy --strict` clean on modified files

## References

- FR-007: Frozenset deletion requirement
- FR-008: Live action_sequence resolution
- research.md §"Research Task 1" — frozenset call site inventory
- contracts/action-sequence-dispatch-contract.md — behavioral contract
- NFR-002: Zero regression gate

## Activity Log

- 2026-05-30T20:32:01Z – claude:sonnet:python-pedro:implementer – shell_pid=3321689 – Assigned agent via action command
- 2026-05-30T20:46:32Z – claude:sonnet:python-pedro:implementer – shell_pid=3321689 – Ready for review: deleted _COMPOSED_ACTIONS_BY_MISSION and _COMPOSED_ACTIONS_FOR_PROMPT, wired all 4 call sites to charter.resolve_action_sequence, 203 tests pass
- 2026-05-30T20:47:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=3380013 – Started review via action command
