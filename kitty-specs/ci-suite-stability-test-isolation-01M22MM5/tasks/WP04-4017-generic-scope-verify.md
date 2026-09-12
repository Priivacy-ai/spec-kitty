---
work_package_id: WP04
title: '#4017 generic-scope verification (non-runtime owner + merge nesting)'
dependencies:
- WP03
requirement_refs:
- FR-004
planning_base_branch: issue-4017-ci-suite-stability
merge_target_branch: issue-4017-ci-suite-stability
branch_strategy: Planning artifacts for this mission were generated on issue-4017-ci-suite-stability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-4017-ci-suite-stability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-suite-stability-test-isolation-01M22MM5
base_commit: c790f73394333ca1f6c4b4eae2f99b7e055a9654
created_at: '2026-09-09T14:08:03.482588+00:00'
subtasks: []
phase: Phase 3 - Lane A generic verify
history:
- at: '2026-09-09T09:10:03Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/runtime/
create_intent:
- tests/runtime/test_generic_asset_scope.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/runtime/test_generic_asset_scope.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer). Read the mission [spec.md](../spec.md), [plan.md](../plan.md), and [research.md](../research.md) — they carry the grounded mechanism + squad dispositions.

## Objective
Prove the HiC "Generic — all owners" ruling ships VERIFIED: the fix covers the generic check_assets path for all owners, and the separate command-completion recheck is addressed. (FR-004, SC-006)

## Subtasks
### T012 — Non-runtime owner + merge.py nesting
In tests/runtime/test_generic_asset_scope.py drive the real global_assets batch path (ensure_runtime/init) through at least one NON-runtime owner (agent_commands/agent_skills/managed_skills) and exercise the merge.py:94 recheck nesting; assert no "Global asset input changed"/"File exists" under concurrent shared-home for those owners.
### T013 — Verify-or-exclude _recheck_command_completion
_recheck_command_completion (managed_skills.py:165) is a SEPARATE recheck (#4082 added recheck_applied()) not calling check_assets. Drive it under the concurrent scenario: confirm its #4082 idempotency already makes it race-safe (document evidence) OR record a scoped follow-up if it races. State the verdict in the Activity Log — do not silently assume coverage.

## Validation
PWHEADLESS=1 SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/python -m pytest tests/runtime/test_generic_asset_scope.py -p no:cacheprovider ; ruff+mypy clean.
## Definition of Done
- Non-runtime owner + merge.py nesting driven green; _recheck_command_completion verdict recorded (safe or scoped follow-up filed).
## Shard-map
Record any NEW tests/runtime/* file you create in your Activity Log for WP05's `tests/_next_shard_map.py` registration (tests/runtime is a shard-map root).

## Reviewer guidance
- A genuinely non-runtime owner is exercised; the command-completion recheck was actually driven, not assumed.
