---
work_package_id: WP02
title: /tmp prompt-writer namespacing
dependencies: []
requirement_refs:
- FR-003
- FR-006
tracker_refs: []
planning_base_branch: fix/session-reaper-and-tmp-leak-hygiene
merge_target_branch: fix/session-reaper-and-tmp-leak-hygiene
branch_strategy: Planning artifacts for this mission were generated on fix/session-reaper-and-tmp-leak-hygiene. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/session-reaper-and-tmp-leak-hygiene unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude"
shell_pid: "647982"
history:
- 'Created by planner for #1842 tasks phase'
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/_tmp_namespace.py
- tests/runtime/test_tmp_prompt_namespace.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/runtime/next/_tmp_namespace.py
- src/runtime/next/prompt_builder.py
- src/runtime/next/decision.py
- src/specify_cli/cli/commands/agent/workflow.py
- tests/runtime/test_tmp_prompt_namespace.py
role: implementer
tags: []
task_type: implement
---

# WP02 – /tmp prompt-writer namespacing

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-003) + `plan.md` (IC-02) first.

## Objective
Route all three flat-`/tmp` prompt writers through **one shared, per-repo/per-run-namespaced, sweepable temp-root**, defined by a **single shared constant** that WP01's reaper will import (single source of truth — no hand-copied prefixes).

## Changes
- **T001** — new `src/runtime/next/_tmp_namespace.py` (or a similarly shared, importable location): expose the namespace root/prefix as the single source of truth (e.g. `SPEC_KITTY_TMP_NAMESPACE = "spec-kitty"` + a `prompt_tmp_dir(repo_root)` helper returning a per-repo/per-run subdir under `tempfile.gettempdir()`, e.g. `<tmp>/spec-kitty-prompts/<repo-hash>/`). It MUST be importable by both `src/runtime/next/*` and `src/specify_cli/cli/commands/agent/workflow.py`, and by `tests/` (the reaper). Keep the existing filename shapes (`spec-kitty-next-*`, `spec-kitty-composed-*`, `spec-kitty-{implement,review}-*`) but rooted under the namespace dir, not flat `gettempdir()`.
- **T002** — `prompt_builder.py` (~:478-479, `spec-kitty-next-*`): write under the shared namespace dir.
- **T003** — `decision.py` (BOTH `mkstemp` sites ~:610/:657, `spec-kitty-composed-{action}-*`): pass `dir=` the shared namespace dir. These are unbounded (unique suffix) — the top target.
- **T004** — `workflow.py` (~:703-705, `spec-kitty-{implement|review}-*`): write under the shared namespace dir.
- **T005** — `tests/runtime/test_tmp_prompt_namespace.py`: assert each writer's output path is **under the shared namespace root** (drift-proof — this is what WP01's reaper sweeps); assert the return contract (consumers read the returned path) is preserved.

## Red-first / DoD
- [ ] All three writers produce paths under the shared namespace root (asserted); the flat-`gettempdir()` roots are no longer used for these prompts.
- [ ] Return contract preserved — the runtime `next` loop + workflow still consume the returned paths (run the relevant runtime tests green).
- [ ] `PWHEADLESS=1 uv run pytest tests/runtime/ tests/agent/ -q -k 'prompt or composed or workflow or next'` green (scope as needed).
- [ ] `ruff` + `mypy --strict` clean on all touched files; no new suppressions.

## Commit
`git add -A && git commit -m "fix(#1842): namespace the three /tmp prompt writers under one shared, sweepable root"`

## Reviewer Guidance
Confirm ONE shared constant is the single source of truth (grep the three writers import it — no hand-copied literals). Confirm the return contract is preserved (consumers still work). Confirm the namespace root is what WP01's reaper will sweep.

## Activity Log

- 2026-07-06T19:16:08Z – claude – shell_pid=647982 – Assigned agent via action command
- 2026-07-06T19:57:11Z – claude – shell_pid=647982 – Moved to for_review
- 2026-07-06T20:05:38Z – user – shell_pid=647982 – Moved to approved
