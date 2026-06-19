---
work_package_id: WP04
title: Load-bearing architectural regression guard (IC-03)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: automation/sonar-security-20260619
merge_target_branch: automation/sonar-security-20260619
branch_strategy: Planning artifacts for this mission were generated on automation/sonar-security-20260619. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into automation/sonar-security-20260619 unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: claude
history:
- at: '2026-06-19T12:26:42Z'
  actor: claude
  note: WP authored from plan IC-03 (FR-005/SC-006).
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_untrusted_path_containment.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/architectural/test_untrusted_path_containment.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (or read
`src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it), and
acknowledge its initialization declaration.

## Objective

Add a `tests/architectural/` regression guard, anchored on WP01's audited-surface
inventory, that FAILS when a new unvalidated untrusted-segment join is introduced on
an audited surface — and prove it is **load-bearing** (not vacuous). (FR-005, SC-006)

Runs after WP02/WP03 fixes land so the guard is green on the fixed tree.

## Context

- WP01 produced `audit/audited-surfaces.md` (the inventory of untrusted→FS sinks +
  dispositions). This guard's matched-surface set is THAT inventory, not a heuristic
  over every `Path /` join (which would be high-false-positive).
- Existing architectural guards live in `tests/architectural/` (e.g.
  `test_no_legacy_terminology.py`) and run in the `integration-tests-core-misc` CI job.

## Subtasks

### T018 — implement the guard
- Add `tests/architectural/test_untrusted_path_containment.py`. For each audited
  surface in WP01's inventory, assert that the untrusted segment reaching its sink is
  routed through the canonical seam (`assert_safe_path_segment` / `safe_mission_slug` /
  `ensure_within_any`). Use AST or a precise source scan keyed on the inventory's
  source symbols + sink predicate — NOT a blanket `Path /` matcher.
- Keep it ruff/mypy-clean and reasonably fast (architectural tests run in CI core-misc).

### T019 — guard self-test (load-bearing proof)
- Add a self-test fixture: a synthetic snippet (in a tmp file or an inline AST sample)
  that introduces an unvalidated untrusted-segment join on an audited surface MUST make
  the guard report a violation; and the guard's logic removed/neutralized MUST make
  that fixture assertion pass. This proves the guard fires (SC-006) and is not vacuous.
  Document the mutation result in the WP history.

### T020 — gate placement + full run
- Confirm the guard is collected by the architectural suite and would run in CI's
  core-misc job. Run `PWHEADLESS=1 python -m pytest tests/architectural/ -p no:cacheprovider -q`
  and the broader status/merge suites — all green on the post-WP02/WP03 tree.

## Branch Strategy

Planning/base + merge target: `automation/sonar-security-20260619` (rides PR #2036; flattened). Worktree per `lanes.json` lane at implement time. **Depends on WP01, WP02, WP03** — the guard asserts the fixed state, so it must run after the fixes.

## Definition of Done

- [ ] Guard added, anchored on WP01's inventory (not a blanket `Path /` heuristic).
- [ ] Self-test proves the guard FAILS on a new unvalidated join and PASSES only with the guard present (load-bearing, SC-006).
- [ ] Guard is green on the post-WP02/WP03 tree; collected by the architectural suite.
- [ ] ruff + mypy clean.

## Risks / Reviewer guidance

- **Risk**: false positives if the matcher is too broad — anchor strictly on the inventory's source symbols/sinks.
- **Risk**: false negatives if the matcher is too narrow — the self-test (T019) is the antidote; insist it actually fails without a real guard.
- **Reviewer**: run the self-test mutation yourself; try adding a deliberate unvalidated join on an audited surface and confirm the guard catches it.
