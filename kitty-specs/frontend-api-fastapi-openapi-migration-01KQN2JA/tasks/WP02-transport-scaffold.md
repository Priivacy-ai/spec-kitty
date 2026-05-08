---
work_package_id: WP02
title: Transport Scaffold (deps, app factory, deps, errors, strangler boundary, CLI flag)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-008
- FR-010
- FR-011
- FR-012
- FR-018
- NFR-003
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: python-pedro
authoritative_surface: src/dashboard/api/
execution_mode: code_change
owned_files:
- pyproject.toml
- uv.lock
- src/dashboard/api/__init__.py
- src/dashboard/api/app.py
- src/dashboard/api/deps.py
- src/dashboard/api/errors.py
- src/specify_cli/dashboard/server.py
- src/specify_cli/cli/commands/dashboard.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

You are Python Pedro. Your role is implementation — write clean, typed Python that satisfies the FRs. You do not write architectural docs in this WP (that's WP01's job).

## Objective

Stand up the FastAPI app skeleton, the strangler boundary, and the CLI flag wiring so subsequent WPs can plug routers and models in.

## Subtasks

See `tasks.md` § WP02 for the full implementation sketch. Summary:

### T005 — Add `fastapi`, `uvicorn[standard]` to `pyproject.toml`

```bash
uv add fastapi 'uvicorn[standard]'
uv sync --frozen
```

Confirm Pydantic v2 is in the lockfile (`grep '^pydantic' uv.lock`). If a Pydantic v1 conflict surfaces, resolve it (the only consumer should be the indirect dep graph).

### T006 — `src/dashboard/api/app.py` :: `create_app(project_dir, project_token) -> FastAPI`

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .errors import register_exception_handlers


def create_app(project_dir: Path, project_token: str | None) -> FastAPI:
    app = FastAPI(
        title="Spec Kitty Dashboard API",
        version="1.0.0",
        redirect_slashes=False,  # match legacy behavior
    )
    app.state.project_dir = project_dir
    app.state.project_token = project_token
    register_exception_handlers(app)
    # routers wired in WP04A/WP04B
    return app
```

### T007 — `src/dashboard/api/deps.py` :: `verify_project_token`

See `research.md` § R-2 for the exact function shape. The dependency reads `request.app.state.project_token` and compares to a `?token=` query parameter.

### T008 — `src/dashboard/api/errors.py` :: `register_exception_handlers(app)`

Map `RuntimeError("dashboard project_dir is not configured")` and any other service-layer exceptions to JSON error payloads matching the legacy format. The contract-parity test will catch divergences.

### T009 — Strangler boundary in `src/specify_cli/dashboard/server.py`

Read `dashboard.transport` from `.kittify/config.yaml`. If the value is `"fastapi"` (or unset, defaulting to fastapi), construct the FastAPI app via `create_app(...)` and run via `uvicorn.Server(uvicorn.Config(app, host=..., port=..., log_level="warning")).run()`. Otherwise fall back to the legacy `BaseHTTPServer` path.

### T010 — `--transport` flag (and `--bench-exit-after-first-byte`) on `spec-kitty dashboard`

Add Typer options in `src/specify_cli/cli/commands/dashboard.py`:

```python
@app.command()
def dashboard(
    transport: str | None = typer.Option(
        None, "--transport", help="legacy | fastapi (overrides config)"
    ),
    bench_exit_after_first_byte: bool = typer.Option(
        False, "--bench-exit-after-first-byte", hidden=True,
        help="Exit immediately after the first byte is served (used by scripts/bench_dashboard_startup.py)",
    ),
    ...,
) -> None:
    ...
```

The CLI flag overrides the config value if present. The hidden bench flag is consumed by the benchmark script in WP06; without it the benchmark cannot measure cold-start to first byte.

## Definition of Done

- [ ] `spec-kitty dashboard --transport fastapi` starts and binds without errors.
- [ ] `curl http://127.0.0.1:<port>/openapi.json` returns valid JSON (zero-route or static-only OK at this stage).
- [ ] `spec-kitty dashboard --transport legacy` still works.
- [ ] No new `# type: ignore` directives in `src/dashboard/api/`.
- [ ] `tests/test_dashboard/test_fastapi_app.py` exists with a smoke test for `create_app`.

## Reviewer guidance

- Confirm `redirect_slashes=False` is set.
- Confirm `app.state` is not over-populated — only `project_dir` and `project_token` (and any DI we add).
- Confirm the strangler boundary fails closed: an unknown `transport` value should raise a clear error, not silently default.
- Confirm the CLI flag is documented in `--help` output.

## Risks

- Dependency graph conflicts on `uv sync`. Mitigation: run the full test suite after sync.
- Uvicorn signal-handler interaction with the existing `_handle_shutdown` flow. Mitigation: WP04A's shutdown router test exercises this; if broken, surface in WP02 review.

## Activity Log

- 2026-05-02T20:00:41Z – claude – Moved to claimed
- 2026-05-02T20:00:44Z – claude – Moved to in_progress
- 2026-05-02T20:11:32Z – claude – Moved to for_review
- 2026-05-02T20:11:36Z – claude – Moved to in_review
- 2026-05-02T20:11:39Z – claude – Moved to approved
- 2026-05-02T20:11:42Z – claude – Done override: Full implement-review run inside the parent feature/650-dashboard-ui-ux-overhaul branch without per-WP lane worktrees; transport scaffold committed directly
