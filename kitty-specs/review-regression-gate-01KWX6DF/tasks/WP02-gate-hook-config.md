---
work_package_id: WP02
title: for_review gate hook + config/override precedence
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
tracker_refs: []
planning_base_branch: fix/review-regression-gate
merge_target_branch: fix/review-regression-gate
branch_strategy: Planning artifacts for this mission were generated on fix/review-regression-gate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/review-regression-gate unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
agent: "claude"
shell_pid: "2235397"
history:
- 'Created by planner for #572/#1979/#2283 tasks phase'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/review/test_pre_review_gate_integration.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/review/test_pre_review_gate_integration.py
role: implementer
tags: []
task_type: implement
---

# WP02 – `for_review` gate hook + config/override precedence

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-001, FR-004, NFR-001) + `plan.md` (IC-02). **Depends on WP01** (the verdict engine `review/pre_review_gate.py`) — that must be approved/done first.

## Objective
Wire WP01's new-failure verdict into the `move-task --to for_review` transition (`cli/commands/agent/tasks_move_task.py`) — warn-default, opt-in block, override precedence — without breaking the existing transition.

## Changes
- **T004 — gate hook (FR-001/NFR-001)**: in the `for_review` path, before emitting the status event, call `pre_review_gate` for the WP's changed files. **Warn by default** — surface the new failures + the affected-shard count, allow the transition. **Opt-in block** when config `review.fail_on_pre_review_regression` is true (block the transition on new failures). A **`--force`** flag bypasses the block and is **recorded in the transition evidence**. If the baseline is uncomputable → warn (never hard-block). Keep the hook cheap when there are no changed files; but an **empty affected set (empty-cone composite or excluded-only) is a `no_coverage` WARN, NOT a clean pass** (per WP01 / SC-007) — do NOT short-circuit an empty scope into "verified".
- **T005 — override precedence (FR-004)**: resolve the test scope by precedence **frontmatter `pre_review_test_scope` > config `review.pre_review_test_command` > the WP01 census-derived default**. Document + test each level.
- **T006 — integration + non-vacuity (SC-001/002, FR-005)** in `tests/review/test_pre_review_gate_integration.py` — the test must invoke the **REAL `pre_review_gate`** (NOT a stubbed/mocked verdict):
  - a WP that **introduces a new failure** in a consuming shard (outside `owned_files`) → surfaced (warn) / blocked (block-on) at `for_review`. **Live-evidence / red-first (mandatory):** use a fixture repo whose consuming-shard test **genuinely fails at head but not at base**, and assert the surfaced/blocked output **contains that specific failing test's nodeid**. Record the red-first artifact — the breakage reaches `for_review` with the hook disabled, and is caught with it enabled — in the lane evidence.
  - a **pre-existing base failure** in an affected shard → does NOT block (baseline diff);
  - **bounded scope**: a `status/emit.py`-shaped change resolves to the `status` shard, NOT the `core_misc` whole-tree cone (assert the affected set excludes the catch-alls);
  - **empty-cone composite** (`validators/**`-shaped) → `no_coverage` warn, NOT a clean pass (SC-007);
  - `--force` bypasses + is recorded.

## DoD
- The `for_review` transition runs the gate: warn-default, opt-in block, `--force` recorded; baseline-uncomputable → warn.
- Override precedence (frontmatter > config > default) works + is tested.
- Integration proof: new-failure surfaced/blocked; pre-existing red does not block; bounded scope asserted.
- Existing `move-task` behavior intact (no regression); `PWHEADLESS=1 uv run pytest tests/review/ -q` green; `ruff` + `mypy --strict` clean; no new suppressions.

## Report back
The hook (warn/block/--force + evidence); the override-precedence resolution; the integration cases — especially the new-failure-surfaced + pre-existing-red-does-not-block + bounded-scope (status→status not core_misc); pytest counts; ruff+mypy; lane commit SHA. If wiring the hook into `tasks_move_task.py` risks breaking the transition, STOP and report.

## Activity Log

- 2026-07-07T04:08:24Z – claude – shell_pid=2235397 – Assigned agent via action command
