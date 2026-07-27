---
work_package_id: WP03
title: next Fail-Closed Query Mode
dependencies: []
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "11664"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/runtime_bridge.py
- src/specify_cli/cli/commands/next.py
- tests/specify_cli/test_next_fail_closed.py
priority: P2-High
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Replace the silent exit-0 `"unknown"` stub in `query_current_state` with a structured `MISSION_NOT_FOUND` error that exits non-zero in both human and JSON modes. Fix the `StatusReadPathNotFound` swallow in `_resolve_mission_slug` and the advancing-mode `--result` not-found path.

**CRITICAL before starting**: Review PR #1895 (`stijn-dejongh/spec-kitty`, mission `name-vs-authority-remediation-01KTYGTE`). It may already contain a partial implementation of this fix. If it has landed, scope this WP to harden rather than re-implement.

---

## Context

### The Bug (Issue #1885)

Two branches in `runtime_bridge.py:3074–3097` return:
```python
return Decision(state="unknown", ...)  # exit 0
```
when a mission handle cannot be resolved. JSON consumers cannot distinguish "mission not found" from "mission in an unknown state". CI scripts get exit 0 on a bad handle and silently proceed.

Additionally, `_resolve_mission_slug` at `next.py:331–357` swallows `StatusReadPathNotFound` and returns `None`, which collapses into the same "unknown" exit path.

### Target Error Shape

**Human output (stderr)**:
```
Error: Mission not found: '<handle>'
No mission matching '<handle>' exists in this repository.
Run 'spec-kitty mission list' to see available missions.
```

**JSON output (stdout, exit 1)**:
```json
{
  "result": "error",
  "error_code": "MISSION_NOT_FOUND",
  "handle": "<handle>",
  "remediation": "Run 'spec-kitty mission list' to see available missions.",
  "spec_kitty_version": "3.2.0rc43"
}
```

Exit code: **1** in all modes.

---

## Subtasks

### T011 — Replace `"unknown"` branches in `query_current_state` with `MISSION_NOT_FOUND`

1. Read `src/specify_cli/next/runtime_bridge.py` lines 3060–3110.
2. Identify both "unknown" branches (around :3074 and :3087–3097).
3. Create or reuse a `MissionNotFoundError` exception (or structured return type) that carries:
   - `handle: str` — the attempted handle
   - `error_code: str = "MISSION_NOT_FOUND"`
4. Replace both branches with either:
   - `raise MissionNotFoundError(handle=handle)` (preferred, if exception-based), or
   - `return ErrorDecision(error_code="MISSION_NOT_FOUND", handle=handle, exit_code=1)`
5. Ensure the calling CLI surface (step T013) catches this and emits the correct human/JSON output before exiting 1.
6. `mypy --strict` zero issues on modified file.

### T012 — Fix `StatusReadPathNotFound` swallow in `_resolve_mission_slug`

1. Read `src/specify_cli/cli/commands/next.py` lines 325–360.
2. Find the `except StatusReadPathNotFound` (or equivalent) that returns `None`.
3. Replace the silent return with a raised `MissionNotFoundError` or a propagated error that the top-level CLI handler turns into a non-zero exit.
4. Do NOT catch and suppress: the path-not-found condition IS the "mission not found" condition.

### T013 — Fix advancing-mode `--result` not-found path

1. In the same `next.py` CLI command handler, find the advancing-mode path where `--result` is passed.
2. If the mission handle doesn't resolve, the advancing-mode path must also emit `MISSION_NOT_FOUND` and exit 1.
3. Confirm both `--json` and human modes produce the correct output (see Target Error Shape above).

### T014 — CLI tests: non-zero exit + named error in both modes

File: `tests/specify_cli/test_next_fail_closed.py` (new)

Write pytest tests that:
1. Invoke `spec-kitty next --mission no-such-mission-xyz` in a temp repo.
2. Assert exit code 1.
3. Assert stderr contains `"Mission not found"` and the handle in human mode.
4. Invoke with `--json` and parse stdout JSON.
5. Assert `json["error_code"] == "MISSION_NOT_FOUND"`.
6. Assert `json["handle"] == "no-such-mission-xyz"`.
7. Assert exit code 1 in JSON mode.

Use `subprocess.run` or the `typer.testing.CliRunner` — whichever matches existing test patterns in the test suite.

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
spec-kitty agent action implement WP03 --agent <name>
```

---

## Definition of Done

- [ ] Both `"unknown"` branches in `runtime_bridge.py` replaced with `MISSION_NOT_FOUND`
- [ ] `_resolve_mission_slug` `StatusReadPathNotFound` no longer swallowed
- [ ] Advancing-mode `--result` not-found path patched
- [ ] `test_next_fail_closed.py` passes (exit 1, human + JSON modes)
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **PR #1895 conflict**: If #1895 is in-flight, coordinate to avoid duplicate implementations. Review its diff before writing any code.
- **Two separate branches**: Both `:3074` and `:3087-3097` must be replaced — do not fix only one.
- **`spec_kitty_version` field**: The JSON shape requires a version field. Import the version constant from `src/specify_cli/__init__.py` — do not hardcode.

## Activity Log

- 2026-06-13T07:59:13Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Assigned agent via action command
- 2026-06-13T08:10:23Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Ready for review: fail-closed next implemented — MissionNotFoundError raised in query_current_state and _resolve_mission_slug, both modes exit 1 with structured error, 13 tests passing
- 2026-06-13T08:10:51Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=11664 – Started review via action command
- 2026-06-13T08:15:29Z – user – shell_pid=11664 – Review passed: MissionNotFoundError raised and propagated correctly in both query and advancing modes, exit 1 enforced, JSON envelope has error_code/result/handle/remediation, human mode emits to stderr, 13/13 tests pass, ruff clean, pre-existing mypy issues in unmodified planner.py are not attributable to WP03
