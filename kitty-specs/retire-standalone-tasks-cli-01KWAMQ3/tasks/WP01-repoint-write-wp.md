---
work_package_id: WP01
title: Repoint shared write_wp helper to canonical
dependencies: []
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: mission/retire-standalone-tasks-cli
merge_target_branch: mission/retire-standalone-tasks-cli
branch_strategy: Planning artifacts for this mission were generated on mission/retire-standalone-tasks-cli. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/retire-standalone-tasks-cli unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 1 - De-risk shared helper
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "768704"
history:
- at: '2026-06-29T22:08:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/utils.py
create_intent:
- tests/utils.py
execution_mode: code_change
model: ''
owned_files:
- tests/utils.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Repoint shared `write_wp` helper to canonical

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

De-risk the largest blast radius in this mission *first*, in isolation. The shared test helper `tests/utils.py::write_wp` currently imports from the standalone, soon-to-be-deleted `task_helpers` module (made importable by a `sys.path` injection in the same file). `write_wp` is used by **40 test files**. This WP repoints that import to the canonical `specify_cli.task_utils.support` — whose helpers are behaviorally equivalent — so that when the standalone surface is deleted in WP04, `write_wp` is already independent of it.

**Scope discipline**: this WP touches `tests/utils.py` and nothing else. Do **not** remove the `sys.path` injection or `run_tasks_cli` here — other test files still need them until WP04 deletes those consumers. Removing them now would break collection.

## Context

- `tests/utils.py` today (verify live):
  - `:9-13` — appends `REPO_ROOT/scripts/tasks` to `sys.path` (`TASKS_DIR`). **Leave intact.**
  - `:35-36` — `run_tasks_cli(...)` subprocess helper. **Leave intact.**
  - `:109` (inside `write_wp`) — `from task_helpers import set_scalar, split_frontmatter, build_document, append_activity_log`. **This is the only line to change.**
- Canonical home: `src/specify_cli/task_utils/support.py` exports all four names (`set_scalar:154`, `split_frontmatter:175`, `build_document:194`, `append_activity_log:205`; all in `__all__:426`).
- Equivalence (verified at plan time): `split_frontmatter` / `build_document` / `append_activity_log` are byte-identical to the standalone copy; `set_scalar` produces identical output (the only diff is cosmetic — `re.search(...)` vs `re.compile(...).search(...)` and line-wrapping). The standalone `task_helpers.py:13` even carries a stale "keep in sync" comment, confirming it was always a parallel copy.

## Subtasks

### T001 — Repoint the import
In `tests/utils.py`, change the in-function import inside `write_wp` from:
```python
from task_helpers import set_scalar, split_frontmatter, build_document, append_activity_log
```
to:
```python
from specify_cli.task_utils.support import (
    append_activity_log,
    build_document,
    set_scalar,
    split_frontmatter,
)
```
Keep the import at the same location (in-function is fine if that is how it is written today; do not hoist it to module scope if that would create an import cycle — `tests/utils.py` is imported very early). Make no other change to the file.

### T002 — Prove the 40 dependents stay green
Run the full suite (these helpers feed WP fixtures across many areas):
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q
PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_orphan_sweep.py -n0 -q
```
Spot-check 2–3 `write_wp` consumers directly (e.g. a lanes/status test that builds WP fixtures) to confirm the produced WP files are byte-identical to before (frontmatter ordering, activity-log format). Any pre-existing/unrelated failure must be reported per the charter Pre-existing Failure Reporting Rule, not silenced.

### T003 — Confirm equivalence; confirm scope untouched
- Confirm `git diff tests/utils.py` shows **only** the import line changed — the `sys.path` injection (`:9-13`) and `run_tasks_cli` (`:35-36`) are untouched.
- If any `write_wp` output differs, stop and investigate the specific helper (most likely `set_scalar`); do not paper over a real behavioral diff.

## Definition of Done
- `tests/utils.py::write_wp` imports the four helpers from `specify_cli.task_utils.support`.
- `grep -n "from task_helpers" tests/utils.py` → only inside `write_wp`'s replaced line is gone; no `task_helpers` import remains in `write_wp`.
- The `sys.path` injection + `run_tasks_cli` remain present (removed in WP04).
- Full suite green (modulo reported pre-existing failures); `ruff` clean on `tests/utils.py`.

## Risks
- **Import cycle**: if hoisting the import breaks early collection, keep it in-function. Mitigation: change only the module path, not the import location.
- **Hidden behavioral diff** in `set_scalar`: mitigated by T002 spot-check; if found, it is a real finding — surface it.

## Reviewer guidance
Confirm the diff is a one-line import path swap, sys.path/run_tasks_cli untouched, and the full suite is green. Reject if the WP removed the sys.path injection or run_tasks_cli (that belongs to WP04 and would break collection of the still-present DELETE-class files).

## Activity Log

- 2026-06-29T22:26:31Z – claude:sonnet:python-pedro:implementer – shell_pid=636156 – Assigned agent via action command
- 2026-06-29T22:55:10Z – claude:sonnet:python-pedro:implementer – shell_pid=636156 – Repoint complete (tests/utils.py committed; import-only swap). 35 write_wp-consumer tests pass; ruff clean. Force: blocker is auto-generated charter synthesis-manifest churn, not WP work.
- 2026-06-29T23:45:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=768704 – Started review via action command
- 2026-06-29T23:48:29Z – user – shell_pid=768704 – Review passed (reviewer-renata): import-only repoint; sys.path/run_tasks_cli intact; consumers green; ruff clean.
