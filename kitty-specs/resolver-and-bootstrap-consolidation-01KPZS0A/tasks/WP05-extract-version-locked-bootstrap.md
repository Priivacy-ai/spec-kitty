---
work_package_id: WP05
title: Extract version-locked bootstrap helper
dependencies: []
requirement_refs:
- FR-004
- NFR-001
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-resolver-and-bootstrap-consolidation-01KPZS0A
base_commit: 657a57ca4d2da4278c47f9466d3040005f9c598c
created_at: '2026-04-24T13:51:42.514098+00:00'
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
phase: Phase 2 - Runtime delegation
shell_pid: "1602547"
agent: "opencode:unknown:reviewer-renata:reviewer"
history:
- timestamp: '2026-04-24T12:56:30Z'
  agent: planner-priti
  action: WP created from mission plan
agent_profile: python-pedro
authoritative_surface: src/runtime/orchestration/bootstrap.py
execution_mode: code_change
owned_files:
- src/runtime/orchestration/bootstrap.py
- src/runtime/agents/commands.py
- src/runtime/agents/skills.py
role: implementer
tags: []
---

# Work Package Prompt: WP05 – Extract version-locked bootstrap helper

## Goal

Add `_run_version_locked_bootstrap(version_filename, lock_filename, work)` to `src/runtime/orchestration/bootstrap.py`. Refactor `runtime.agents.commands.ensure_global_agent_commands` and `runtime.agents.skills.ensure_global_agent_skills` to call the helper instead of re-implementing the version-lock dance. Behaviour preserved bit-for-bit.

## Why

FR-004. Removes the 18/19-line duplicate block Sonar flags between the two `ensure_global_agent_*` entry points, and makes it obvious where the pattern belongs for future ensure-global-X helpers.

## In-scope files

- `src/runtime/orchestration/bootstrap.py` (ADD `_run_version_locked_bootstrap`)
- `src/runtime/agents/commands.py` (REFACTOR `ensure_global_agent_commands`)
- `src/runtime/agents/skills.py` (REFACTOR `ensure_global_agent_skills`)

## Out of scope

- Block 1 (resolver consolidation) — fully independent.
- Changing `_get_cli_version` or `_lock_exclusive` signatures — reuse as-is.

## Subtasks (mirror tasks.md §WP05)

- T029 Add `_run_version_locked_bootstrap(version_filename: str, lock_filename: str, work: Callable[[], None]) -> None` to `src/runtime/orchestration/bootstrap.py`. Reuse `_get_cli_version` and `_lock_exclusive`. The helper owns:
  - `kittify_home.mkdir`
  - `cache_dir = kittify_home / "cache"; cache_dir.mkdir`
  - fast-path version check
  - exclusive lock acquisition
  - post-lock re-check
  - `work()` invocation
  - version-file write
  - lock release
- T030 Refactor `ensure_global_agent_skills()` in `src/runtime/agents/skills.py` — body becomes: early-return if registry is None, then call `_run_version_locked_bootstrap(_VERSION_FILENAME, _LOCK_FILENAME, work=...)` passing a closure that iterates `_unique_global_roots()` and calls `_sync_skill_root(root, registry)`.
- T031 Refactor `ensure_global_agent_commands()` in `src/runtime/agents/commands.py` — body becomes: early-return if `templates_dir` is None, then call `_run_version_locked_bootstrap(_VERSION_FILENAME, _LOCK_FILENAME, work=...)` passing a closure that iterates `AGENT_COMMAND_CONFIG` and calls `_sync_agent_commands(agent_key, templates_dir, script_type)` (preserve the per-agent-key `try / except Exception: logger.warning(...)` pattern).
- T032 `ruff check src/runtime/orchestration/bootstrap.py src/runtime/agents/commands.py src/runtime/agents/skills.py` — clean.
- T033 Run `PYTHONPATH=src pytest tests/runtime/test_agent_skills.py tests/specify_cli/runtime/test_agent_commands_routing.py -x -q`. If `tests/runtime/test_bootstrap_unit.py` exists, include it.
- T034 Sanity-check CPD — the duplicated block between the two agent files should be gone after this WP. Verify informally by diffing the two `ensure_global_agent_*` bodies side-by-side; they should now share no scaffolding.

## Implementation notes

- `work` is side-effect-only — no return value. Exceptions inside `work()` must propagate through `_run_version_locked_bootstrap` but NOT prevent the `lock_fd.close()` — use `try`/`finally` around the lock acquisition.
- Closure-captured variables (`templates_dir`, `script_type`, `registry`) are stable locals in each caller; nothing mutable.
- Preserve the write-version-last ordering: if `work()` fails, no version file is written and the next call will retry the full sync (FR-004 success criterion).

## Acceptance

- All tests in T033 pass.
- `ruff` clean on the three files.
- `ensure_global_agent_commands` and `ensure_global_agent_skills` bodies ≤ 12 lines each (count the function body only).
- The Sonar CPD duplicated block between `commands.py` and `skills.py` is removed.

## Commit message template

```
refactor(runtime/bootstrap): share version-locked bootstrap helper across agent surfaces

Add _run_version_locked_bootstrap to runtime/orchestration/bootstrap.py and
route ensure_global_agent_commands / ensure_global_agent_skills through it.
Eliminates the duplicated version-check-lock-work-write sequence both
entry points re-implemented separately. Behaviour preserved.
```

## Activity Log

- 2026-04-24T13:51:43Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1571472 – Assigned agent via action command
- 2026-04-24T14:44:32Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1571472 – WP05 complete: _run_version_locked_bootstrap helper extracted; both ensure_global_agent_* route through it; ruff clean, 37+6 tests green.
- 2026-04-24T14:46:13Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1602547 – Started review via action command
- 2026-04-24T14:46:33Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1602547 – Review passed (reviewer-renata): _run_version_locked_bootstrap extracted to bootstrap.py (+44); ensure_global_agent_commands body reduced 26→2 effective lines, ensure_global_agent_skills 28→2; behaviour preserved (fast-path, lock, re-check, work, write-version-last, finally-close). 43 tests green (test_bootstrap_unit 37 + test_agent_skills 1 + test_agent_commands_routing 5); ruff clean. FR-004 and NFR-001 met.
- 2026-04-24T15:00:09Z – opencode:unknown:reviewer-renata:reviewer – shell_pid=1602547 – Done override: Mission merged to runtime-extraction parent branch (commit 4bd65d1a4) — post-merge done transition
