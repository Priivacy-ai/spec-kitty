---
work_package_id: WP01
title: Land the consumer-repo pre-review-gate calm-degrade (#2534)
dependencies: []
requirement_refs:
- FR-002
- NFR-003
- C-002
- C-003
tracker_refs:
- '#2534'
planning_base_branch: fix/loop-reliability-ci-red-burndown
merge_target_branch: fix/loop-reliability-ci-red-burndown
branch_strategy: Planning artifacts for this mission were generated on fix/loop-reliability-ci-red-burndown. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/loop-reliability-ci-red-burndown unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/review/pre_review_gate.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/review/test_pre_review_gate_engine.py
- tests/review/test_pre_review_gate_integration.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2450756"
shell_pid_created_at: "1784458275.52"
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile via `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML — do not act on the persona name alone.

## Objective
**LAND (rebase), do NOT re-derive (C-002).** Land the ready `fix/2534` consumer-repo calm-degrade fix so a
consumer repo's `move-task --to for_review` degrades to a non-blocking `no_coverage` warn instead of the alarming
"gate authorities unavailable — unverified: tests.architectural._gate_coverage …" message.

**Authoritative grounding**: [`research.md` §1](../research.md), [`data-model.md` LM-1, LM-10](../data-model.md).

## Context / grounding (verified on main)
- The fix is commit **`0153934f9`** (branch `fix/2534-pre-review-gate-consumer-repo`, worktree
  `.worktrees/fix-2534-pre-review-gate`), **4 files, +142/−3**: adds `GateAuthoritiesUnavailable.__init__(…, *,
  is_consumer_repo)` + `_is_spec_kitty_source_repo(repo_root)` (checks `tests/architectural/_gate_coverage.py`
  exists) in `pre_review_gate.py`; adds `_PRE_REVIEW_CONSUMER_REPO_REASON` (calm, no internal-module name) + the
  `except GateAuthoritiesUnavailable` branch in `tasks_move_task.py`; 2 red-first test files.
- Bug still reproduces on main: `GateAuthoritiesUnavailable` is a plain RuntimeError (no `is_consumer_repo`);
  the message embeds `_GATE_COVERAGE_MODULE_NAME`.
- **Rebase profile (verified `git apply --check`):** `pre_review_gate.py` + both test files apply CLEAN; only
  `tasks_move_task.py` conflicts — **positional drift only** (its two hunks target byte-identical text that moved
  ~110 lines, partly from #2573's `_PRE_REVIEW_GATE_DISABLE_ENV_VARS` insertion).

## Subtasks
### T001 — Rebase/apply the fix
Bring `0153934f9`'s change onto the mission branch: cherry-pick or `git apply --3way`. `pre_review_gate.py` +
both tests land clean; `tasks_move_task.py` needs `--3way` (or hand-place the two hunks — the constant near the
other `_PRE_REVIEW_*` constants, the `except GateAuthoritiesUnavailable` branch in `_mt_pre_review_gate_verdict`
picking `_PRE_REVIEW_CONSUMER_REPO_REASON if exc.is_consumer_repo`). **Resolve by SYMBOL, not line (LM-10).**
If a raw apply genuinely fights, PORT THE INTENT per research §1 — but never re-derive a different fix (C-002).

### T002 — Verify
- Confirm the bug still reproduces on main BEFORE trusting the fix, then that the fix silences it. **Repro recipe:**
  the alarming path requires a repo WITHOUT `tests/architectural/_gate_coverage.py` (a `spec-kitty init` consumer
  checkout) — the integration red-first test builds exactly this fixture, so the 2 red-first tests ARE the gate;
  a manual consumer-repo check is optional confirmation, not the primary proof.
- `PWHEADLESS=1 uv run --extra test pytest tests/review/test_pre_review_gate_engine.py tests/review/test_pre_review_gate_integration.py -q` → green.
- `uv run ruff check` + `uv run mypy --strict` on the 2 src files → clean.

## Definition of Done
The `is_consumer_repo` seam + calm reason landed; both red-first tests green; consumer-repo calm-degrade verified;
spec-kitty-repo gate behavior unchanged (NFR-003); ruff + mypy clean.

## Reviewer guidance
Confirm the landed diff matches `0153934f9`'s intent (not a re-derivation); confirm the calm message never names
the internal module or `src/specify_cli/`; confirm the spec-kitty-repo path is unchanged.

## Activity Log

- 2026-07-19T10:44:29Z – claude:sonnet:python-pedro:implementer – shell_pid=2408084 – Assigned agent via action command
- 2026-07-19T10:49:46Z – claude:sonnet:python-pedro:implementer – shell_pid=2408084 – Ready for review: landed 0153934f9 (consumer-repo pre-review-gate calm-degrade, #2534) via cherry-pick with a positional-only conflict in tasks_move_task.py, resolved by keeping both #2573's and this fix's constant additions side by side; 58/58 tests green, ruff+mypy --strict clean
- 2026-07-19T10:51:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=2450756 – Started review via action command
