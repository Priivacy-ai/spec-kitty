---
work_package_id: WP02
title: Sync daemon honors the disable env (#2573b)
dependencies: []
requirement_refs:
- FR-003
- NFR-003
- C-003
tracker_refs:
- '#2573'
- '#2555'
planning_base_branch: fix/loop-reliability-ci-red-burndown
merge_target_branch: fix/loop-reliability-ci-red-burndown
branch_strategy: Planning artifacts for this mission were generated on fix/loop-reliability-ci-red-burndown. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/loop-reliability-ci-red-burndown unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/sync/daemon.py
- tests/sync/test_daemon_sync_disable_env.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2446076"
shell_pid_created_at: "1784458242.68"
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` via `/ad-hoc-profile-load`. Load the YAML.

## Objective
Teach the sync daemon to honor `SPEC_KITTY_SYNC_DISABLE` / `SPEC_KITTY_SYNC_MINIMAL_IMPORT` so setting either
prevents the background daemon from spawning (closes #2573b + #2555 point 2). Independent of WP03 (LM-11 — the
repro sets its own env).

**Authoritative grounding**: [`research.md` §2](../research.md), [`data-model.md` LM-3, LM-10, LM-11](../data-model.md).

## Context / grounding (verified on main)
- Fix site: **`_daemon_start_skip_reason`** in `src/specify_cli/sync/daemon.py` — it checks
  `rollout_disabled`/`intent_local_only`/`policy_manual` then returns `None` (proceed to spawn); it never
  consults the disable envs. It is the **sole** spawn gate — `ensure_sync_daemon_running` is its only caller, and
  all external spawn paths (dashboard, events, restart) route through it, so one check covers every path.
- Repro `tests/sync/test_daemon_sync_disable_env.py::test_sync_disable_env_skips_daemon_spawn` is RED
  (`started=True, skipped_reason=None` despite `SPEC_KITTY_SYNC_DISABLE=1`). It asserts `outcome.started is False`,
  the locked spawn helper `assert_not_called()`, and `skipped_reason is not None`.
- Reuse `is_truthy` from `specify_cli.core.env`; mirror the pre-review-gate grammar
  `_PRE_REVIEW_GATE_DISABLE_ENV_VARS = ("SPEC_KITTY_SYNC_DISABLE", "SPEC_KITTY_SYNC_MINIMAL_IMPORT")` so both call
  sites agree.

## Subtasks
### T003 — Honor the disable envs
In `_daemon_start_skip_reason`, add an early check: if either `SPEC_KITTY_SYNC_DISABLE`/`MINIMAL_IMPORT` is
`is_truthy`, return a non-`None` skip reason (e.g. `"sync_disabled_env"`). ~3-6 lines + `from specify_cli.core.env
import is_truthy`. Resolve by symbol (LM-10). Any position before the spawn returns non-None → skip.

### T004 — Verify (behavior-preserving)
- `PWHEADLESS=1 uv run --extra test pytest tests/sync/test_daemon_sync_disable_env.py -q` → green.
- Confirm the **unset-env path is unchanged**: when neither env is truthy the new branch returns `None` (falls
  through). Run a couple of sibling daemon tests to confirm no regression (INV-2).
- ruff + mypy --strict on `daemon.py` → clean.

## Definition of Done
`_daemon_start_skip_reason` honors both disable envs; repro green; unset path unchanged; ruff + mypy clean.

## Reviewer guidance
Confirm the check fires ONLY on a truthy env (INV-2); confirm it's the sole spawn gate (no bypass); confirm the
env grammar matches the pre-review-gate constant.

## Activity Log

- 2026-07-19T10:44:49Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Assigned agent via action command
- 2026-07-19T10:49:52Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Ready for review: _daemon_start_skip_reason now honors SPEC_KITTY_SYNC_DISABLE/SPEC_KITTY_SYNC_MINIMAL_IMPORT via is_truthy, checked before the spawn decision; unset-env path unchanged; repro green; ruff+mypy --strict clean.
- 2026-07-19T10:50:45Z – claude:opus:reviewer-renata:reviewer – shell_pid=2446076 – Started review via action command
