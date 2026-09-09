---
work_package_id: WP01
title: '#4017 red-first capture (deterministic interleave + exact-signal snapshot)'
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: issue-4017-ci-suite-stability
merge_target_branch: issue-4017-ci-suite-stability
branch_strategy: Planning artifacts for this mission were generated on issue-4017-ci-suite-stability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-4017-ci-suite-stability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-suite-stability-test-isolation-01M22MM5
base_commit: 6995025a02a0ab26c4fd845c177a8388dc32e6a2
created_at: '2026-09-09T09:20:45.312761+00:00'
subtasks: []
phase: Phase 1 - Lane A red-first
history:
- at: '2026-09-09T09:10:03Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/runtime/
create_intent:
- tests/runtime/test_ensure_runtime_concurrency.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/runtime/test_ensure_runtime_concurrency.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer). Read the mission [spec.md](../spec.md), [plan.md](../plan.md), and [research.md](../research.md) — they carry the grounded mechanism + squad dispositions.

## Objective
Capture the #4017 race RED-FIRST before any code change, because the role-tag enabler (WP02) flips the crash signal from "Global asset input changed" to "global_asset_write_failed: File exists" — after which the original signal is unreproducible. (FR-006)

## Subtasks
### T001 — Deterministic apply-interleave test (RED)
Author tests/runtime/test_ensure_runtime_concurrency.py with a DETERMINISTIC interleave: force a loser to observe the winner mid-materialize (a seam/barrier: winner populates the cold home, then the loser runs ensure_runtime against its stale empty-home plan). Assert it currently RAISES the bug, asserting on the emitted SIGNAL text (not just exception type) per OPERATOR_SIGNAL_CONTRACT. Structural red-first, not a dice-roll repeat-N.
### T002 — Snapshot the exact installed-CLI signal
Locally un-skip tests/e2e/test_worktree_owned_root_concurrency.py::test_installed_cli_keeps_two_owned_worktrees_isolated, run it, RECORD the exact "Global asset input changed: <home>" traceback in the Activity Log as the pre-fix witness, then re-skip (WP03 owns the permanent un-skip). Do NOT commit an un-skip here.

## Validation
PWHEADLESS=1 SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/python -m pytest tests/runtime/test_ensure_runtime_concurrency.py -q -p no:cacheprovider → RED with the exact signal. ruff+mypy clean.
## Definition of Done
- Deterministic interleave test committed, RED, with the signal emitted ORGANICALLY through the real ensure_runtime/check_assets path (NO test-authored raise of the message); the asserted text is pinned to the exact T002-recorded witness string.
- Installed-CLI signal recorded; e2e files unchanged (still skipped). Record the new test filename for WP05's shard-map registration.
## Reviewer guidance
- Confirm DETERMINISTIC forced interleave (not flaky repeat-N) and that it asserts the signal text.
