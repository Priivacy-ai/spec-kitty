---
work_package_id: WP05
title: Single-resolver architectural guard
dependencies:
- WP03
- WP04
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: fix/specify-protected-primary-coherence
merge_target_branch: fix/specify-protected-primary-coherence
branch_strategy: Planning artifacts for this mission were generated on fix/specify-protected-primary-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/specify-protected-primary-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
phase: Phase 4 - Guard
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3177109"
history:
- timestamp: '2026-06-21T06:45:34Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_protection_resolver_call_sites.py
execution_mode: code_change
mission_id: 01KVMBD6HTBP3A9Y5T4EQ80RA9
owned_files:
- tests/architectural/test_protection_resolver_call_sites.py
role: implementer
tags: []
wp_code: WP05
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Enforce the single-authority property (FR-010 / #1868): a repo-wide architectural guard that fails CI if a
protected-branch **decision** is made anywhere outside the resolver + delegate allowlist.

## Context & Constraints

- Clone the AST pattern from `tests/architectural/test_guard_capability_call_sites.py` (repo-wide
  `_SRC_ROOT.rglob("*.py")` scan — NEVER mission-diff-scoped; a diff-scoped assertion can't catch offenders
  in its own merge and bites main post-merge).
- **Allowlist**: exactly `git/protection_policy.py` (`resolve`) + `git/commit_helpers.py:protected_branches`
  (the demoted delegate).
- **MUST scope-exclude the classification sets** in the SAME commit, or the guard is red day one:
  `_WELL_KNOWN_INTEGRATION_BRANCHES` (`acceptance/__init__.py:1193`) and `common_primary_branches`
  (`mission.py:598`) are integration/primary *detection*, not protection *decisions*.
- Mark `pytestmark = pytest.mark.architectural` so the gate auto-collects it (no CI wiring needed; it rides
  `integration-tests-core-misc` → `quality-gate`).

## Subtasks & Detailed Guidance

### Subtask T019 — Write the guard
- New `tests/architectural/test_protection_resolver_call_sites.py`. AST-walk `src/` and match the **precise
  FR-010 target: the `protected_branches(` CALL form** (only ~7 callsites exist, all rerouted by WP01/WP03/WP04)
  — assert the discovered call set ⊆ allowlist (`git/protection_policy.py:resolve`, `git/commit_helpers.py`
  internal). Do NOT write a bare `{"main","master"}` literal scanner (Paula SF-2): it false-positives on ~6
  legitimate default-branch **detection** sites (`core/git_ops.py:313`, `core/stale_detection.py:113`,
  `core/vcs/git.py:966`, `verify_enhanced.py:143/437`) plus the two classification sets
  `_WELL_KNOWN_INTEGRATION_BRANCHES` (`acceptance/__init__.py:1193`) and `common_primary_branches`
  (`mission.py:598` — a **local variable in a function body**, not a module constant, so any literal-based
  exclusion must match the in-body tuple, not a symbol). Matching the `protected_branches(` call sidesteps all
  of these cleanly. If a literal protection comparison must also be flagged, scope it to a refusal context
  (`branch in {…}` feeding a guard), never a `for branch in [...]` detection loop.
- **Files**: `tests/architectural/test_protection_resolver_call_sites.py`.

### Subtask T020 — Verify gate-collection + rationale
- Confirm the guard is collected by the `architectural` marker into `integration-tests-core-misc`.
- Run it locally (it is NOT in fast-tests): `PWHEADLESS=1 pytest tests/architectural/ -m architectural -q`.
- Document the allowlist + exclusion rationale inline.

## Branch Strategy
- Planning base / merge target: `fix/specify-protected-primary-coherence`. Work in this WP's lane worktree.

## Definition of Done
- Guard green on the collapsed tree; red if a direct protection decision is reintroduced (verify by a local
  temporary offending edit, then revert).
- Classification-set exclusions present with rationale. ruff + mypy clean.

## Risks & Reviewer Guidance
- **Over-broad guard** is the main risk: confirm the classification sets are excluded and the guard is
  repo-wide. Pre-push: run the architectural shard locally — it does not run in fast-tests.

## Activity Log

- 2026-06-21T10:37:32Z – claude:sonnet:python-pedro:implementer – shell_pid=3168913 – Assigned agent via action command
- 2026-06-21T10:44:48Z – claude:sonnet:python-pedro:implementer – shell_pid=3168913 – WP05 (lane-e): FR-010 single-resolver guard (call-form match, allowlist=resolver+delegate); green on collapsed tree, mutation-verified RED, no false-positives
- 2026-06-21T10:44:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=3177109 – Started review via action command
- 2026-06-21T10:49:35Z – user – shell_pid=3177109 – Review passed (reviewer-renata): FR-010 guard mutation-verified RED, not over-broad, call-form match, auto-collected
