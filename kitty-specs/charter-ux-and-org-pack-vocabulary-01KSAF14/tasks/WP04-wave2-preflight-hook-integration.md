---
work_package_id: WP04
title: 'Wave 2: preflight hook integration into next/implement/dashboard'
dependencies:
- WP03
requirement_refs:
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ux-and-org-pack-vocabulary-01KSAF14
base_commit: 8996612d01cc53bede0a9b4fe144bf0240ae8279
created_at: '2026-05-24T09:31:16.561096+00:00'
subtasks:
- T022
- T023
- T024
- T025
- T026
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1146153"
history:
- by: claude
  at: '2026-05-23T13:30:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
mission_id: 01KSAF14K8FZ56MHYT45EGWHHC
mission_slug: charter-ux-and-org-pack-vocabulary-01KSAF14
owned_files:
- src/specify_cli/cli/commands/next.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/dashboard.py
- src/specify_cli/config/schema.py
- tests/agent/cli/commands/test_next_preflight.py
- tests/agent/cli/commands/test_implement_preflight.py
- tests/test_dashboard/test_dashboard_preflight.py
priority: P0
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Pedro's typer + subprocess + pydantic-config background covers the hook wire-ups. The dashboard SPA banner is deferred to a follow-up frontend WP.

## Objective

Wire `run_charter_preflight` (from WP03) into three governed entry points — `spec-kitty next`, `spec-kitty implement`, and the dashboard launch — per the caller contract in `contracts/charter-preflight-json.md`. Add a `preflight.auto_refresh` config flag (default `false`) so operators opt in to the auto-refresh path without surprising existing behaviour.

## Branch strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Execution worktree: allocated by `finalize-tasks`.

## Context

- `contracts/charter-preflight-json.md` § "Hook caller contract" — the binding table for this WP
- WP03's `run_charter_preflight(repo_root, auto_refresh, strict)` callable
- Existing entry points: `src/specify_cli/cli/commands/next.py`, `implement.py`, `dashboard.py`
- Existing config schema: `src/specify_cli/config/schema.py` (consult for the right add-flag pattern)

## Subtask details

### T022 — Config flag `preflight.auto_refresh`

**Files**: `src/specify_cli/config/schema.py`, `src/specify_cli/config/loader.py` (if separate)

Add a new optional section to `.kittify/config.yaml`:
```yaml
preflight:
  auto_refresh: false  # default
```

Pydantic model field:
```python
class PreflightConfig(BaseModel):
    auto_refresh: bool = False
```

Hang it off the top-level config model. Existing projects without the section continue to work (default).

### T023 — Wire into `spec-kitty next`

**Files**: `src/specify_cli/cli/commands/next.py`

At the start of the command (after argument parsing, before any state mutation):
```python
from specify_cli.charter_preflight import run_charter_preflight
from specify_cli.config import load_config

cfg = load_config(repo_root)
result = run_charter_preflight(repo_root, auto_refresh=cfg.preflight.auto_refresh, strict=False)
if not result.passed:
    typer.echo(f"[red]Charter preflight failed:[/red] {result.blocked_reason}")
    raise typer.Exit(code=1)
logger.info("charter preflight passed")
```

Per caller contract: log+continue on success, abort with exit 1 on failure; do NOT perform any state mutation before the check returns.

### T024 — Wire into `spec-kitty implement`

**Files**: `src/specify_cli/cli/commands/implement.py`

Same pattern as T023, but the abort must happen **before any worktree allocation or `.kittify/` modification**. Place the check immediately after CLI arg validation.

### T025 — Wire into dashboard launch

**Files**: `src/specify_cli/cli/commands/dashboard.py`

The dashboard's launch entry point (`dashboard serve` / `dashboard start`) MUST:
- Call `run_charter_preflight(repo_root, auto_refresh=cfg.preflight.auto_refresh, strict=False)`.
- On `passed=False`: still start the server (do not block dashboard launch — operators need to access the dashboard to diagnose), BUT render a top-of-page banner. The banner is delivered by injecting `result.blocked_reason` into the dashboard config / settings endpoint so the SPA renders a critical-severity notification.
- On `passed=True`: continue silently.

Coordinate with the existing dashboard settings handler (search for `dashboard/api/settings.py` or similar) to add a `preflight_warning` field.

### T026 — Tests for each consumer

**Files**: NEW `tests/agent/cli/commands/test_next_preflight.py`, `test_implement_preflight.py`, `tests/test_dashboard/test_dashboard_preflight.py`

Cases per consumer:
1. Preflight passes → command proceeds normally.
2. Preflight fails → `next` and `implement` exit 1 with the blocked_reason printed; dashboard starts but `preflight_warning` is populated.
3. With `cfg.preflight.auto_refresh = true` and clean worktree → refresh runs, preflight passes, command proceeds.

Use mocked `run_charter_preflight` for these tests (the unit tests for the runner itself live in WP03's tests).

## Definition of Done

- [ ] `preflight.auto_refresh` config flag honoured by all three consumers.
- [ ] `spec-kitty next` and `spec-kitty implement` abort cleanly on preflight failure (no worktree/`.kittify` mutation).
- [ ] Dashboard launch renders the banner via `preflight_warning` API field.
- [ ] All consumer tests pass with mocked runner.
- [ ] `mypy --strict` and `ruff check` pass.

## Risks

- **`implement` is the user's most-used command**: a regression here is painful. Mitigation: tests cover both pass and fail paths; the abort is mocked so we don't accidentally execute a real refresh.
- **Dashboard SPA contract**: the `preflight_warning` API field is new and the SPA must surface it. If the dashboard team hasn't shipped UI support, the banner won't appear — coordinate or land the SPA change as a follow-up.

## Reviewer guidance

1. Verify the preflight check runs BEFORE any worktree allocation in `implement.py`.
2. Verify the dashboard continues to start on preflight failure (it's a diagnostic surface).
3. Confirm the config default is `false` so existing user behaviour is unchanged.

## Activity Log

- 2026-05-24T09:31:17Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1121569 – Assigned agent via action command
- 2026-05-24T09:41:08Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1121569 – Ready for review: hooks wired per caller contract, config flag added, 3 consumer test files
- 2026-05-24T09:41:38Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1146153 – Started review via action command
- 2026-05-24T09:44:02Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1146153 – Review passed: preflight hooks wired into next/implement/dashboard, PreflightConfig added, 13/13 + 95/95 smoke green, abort-before-mutation order verified
- 2026-05-24T11:46:51Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1146153 – Done override: Feature merged to main as squash commit 37407a3b2; status carried through from mission branch
