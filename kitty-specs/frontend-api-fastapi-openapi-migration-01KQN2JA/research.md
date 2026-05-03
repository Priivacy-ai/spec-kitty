# Research — Frontend API FastAPI/OpenAPI Migration

## R-1 — Pydantic v1 vs v2 compatibility

**Decision**: Pydantic v2 (≥ 2.5).

**Rationale**: FastAPI 0.115.x requires Pydantic v2. The repo currently has no top-level Pydantic pin (`grep -n "^pydantic" pyproject.toml` returns nothing). `pydantic` is a transitive dep through other libraries; we add `fastapi` and `uvicorn` and let Pydantic resolve as v2.

**Alternatives considered**:
- Pin Pydantic v1 + `fastapi==0.99.x` (the last v1-compatible series): rejected — v1 EOL, v2 has been stable for 2+ years, OpenAPI generation is more correct in v2.

**Risk**: any indirect Pydantic v1 user in the dep graph. Mitigation: `uv lock --upgrade` then `uv sync --frozen` and run the full test suite. The architectural test for shared-package boundaries already exists; nothing in `src/` directly imports `pydantic.v1`.

## R-2 — Token validation as `Depends`

**Decision**: A single `Depends(verify_project_token)` declared on routes that need it (`POST /api/sync/trigger`, `POST /api/shutdown`).

**Function shape**:

```python
def verify_project_token(
    token: str | None = Query(default=None),
    request: Request = ...,
) -> str | None:
    expected = request.app.state.project_token
    if expected and token != expected:
        raise HTTPException(status_code=403, detail="invalid_token")
    return token
```

**Rationale**: keeps the route handler body free of HTTP-only side effects (FR-009), satisfies MCP-friendly invariant. Token comparison happens before the route function runs, so the route handler can trust its inputs.

**Alternatives considered**: middleware (rejected — runs for every request even on routes that don't need it; can't easily attach typed inputs); `BackgroundTasks` (irrelevant — wrong primitive).

## R-3 — Static file serving

**Decision**: `StaticFiles(directory=str(static_path), html=False)` mounted at `/static/`, plus an explicit `/` route that returns the dashboard HTML shell via `FileResponse` (matching legacy behavior — current root returns rendered HTML, not directory listing).

**Audit**: `src/specify_cli/dashboard/handlers/static.py` (50 LOC) serves `dashboard.css` + `dashboard.js` + the rendered HTML at `/`. The HTML is rendered by `get_dashboard_html_bytes()` in `templates.py`. The new app reuses that helper unchanged.

**Risk**: subtle URL routing differences — FastAPI's StaticFiles is HTTP-spec strict and may serve `404` where the legacy custom handler returned `200` for missing files. Parity test will catch any divergence.

## R-4 — WSGI/ASGI co-existence

**Decision**: Process-level switch. The strangler boundary in `src/specify_cli/dashboard/server.py` reads `dashboard.transport` config (or `--transport` CLI flag), and the chosen stack runs alone. No simultaneous mount.

**Rationale**: cleaner rollback story (one stack at a time); FastAPI on Uvicorn requires an event loop, while `BaseHTTPServer` is sync/threaded — mixing them in one process would require an a2wsgi shim and a shared port adapter. Not worth the complexity for a dual-stack period that lasts at most one release.

**Alternatives considered**:
- `a2wsgi`-mounted FastAPI inside the legacy `BaseHTTPServer`: rejected — adds a dep just for the transition window.
- Run FastAPI on a different port and reverse-proxy: rejected — operator-visible behavior change.

## R-5 — Trailing-slash redirects

**Decision**: Set `redirect_slashes=False` on the FastAPI app to match `BaseHTTPServer`'s lack of redirects. Document this in the migration runbook.

**Rationale**: by default FastAPI emits 308 redirects from `/api/features/` to `/api/features` (or vice versa). The legacy router does not. The parity test would fail without this setting; better to explicitly turn it off and accept that operators using a trailing slash get a 404 (the same as legacy).

## R-6 — OpenAPI determinism

**Decision**: Generate the OpenAPI doc via `app.openapi()` (returns a `dict`); serialize with `json.dumps(spec, sort_keys=True, indent=2)` to make the snapshot byte-deterministic.

**Risk**: FastAPI may reorder dict iteration if upstream Pydantic / FastAPI changes its model walk order. `sort_keys=True` mitigates this — if a key appears, it appears in sorted order.

**Alternatives considered**: pin FastAPI version exactly (rejected — friction during minor version bumps); use a schema diff tool instead of byte-equivalence (rejected — adds a dep, byte-equivalent is simpler).

## R-7 — Test client lifecycle

**Decision**: Tests instantiate `TestClient(create_app(project_dir=tmp_path, project_token=None))` once per test class via a fixture. Service-layer mocks reuse the existing `dashboard.services.*` patch points (FastAPI's DI doesn't change how those mocks work).

**Rationale**: `TestClient` is the FastAPI-canonical pattern; reuses the existing fixture style; integrates with `pytest` cleanly.

## R-8 — Charter / dossier / glossary handlers

**Inventory** (run `wc -l src/specify_cli/dashboard/handlers/*.py`):

- `glossary.py` — 176 LOC, holds inline business logic
- `lint.py` — 78 LOC, holds inline business logic
- `charter` (in api.py) — `handle_charter` reads via `resolve_project_charter_path`; thin wrapper
- `dossier` (in api.py) — `handle_dossier` instantiates `DossierAPIHandler(repo_root)` and routes; thin wrapper that calls the dossier subsystem
- `diagnostics` (in api.py) — `handle_diagnostics` calls `run_diagnostics()`; thin wrapper

**Decision**: charter, dossier, diagnostics migrate cleanly (already thin). Glossary and lint migrate transport-only — the FastAPI router for those families calls into the existing handler-layer logic via small adapter functions, with a `# TODO: extract glossary service in follow-up mission #YYY` marker. File a follow-up issue at mission close to track service-extraction.

## R-9 — Configuration storage

**Decision**: `dashboard.transport` lives under `dashboard:` in `.kittify/config.yaml`, e.g.:

```yaml
dashboard:
  transport: fastapi  # or 'legacy'; default is 'fastapi' once shipped
```

`spec-kitty dashboard --transport legacy` overrides via Typer flag. The CLI flag wins over the config value.

**Storage mechanism**: existing `.kittify/config.yaml` reader — no new persistence layer needed.

## R-10 — Benchmark methodology

**Decision**: A small script committed at `scripts/bench_dashboard_startup.py` measures cold-start by spawning `spec-kitty dashboard --transport <legacy|fastapi> --bench-exit-after-first-byte`, timing process spawn → first byte. Run 5× per stack, report p50.

**Rationale**: NFR-001 (≤25 % cold-start regression) needs a reproducible measurement. The script is part of mission deliverables (not CI-gated due to platform variance, but the numbers are committed in the mission's release-checklist artifact alongside the SC-006 verification record).

## Open questions

None blocking. All clarifications are resolved by the decisions above; any deeper investigation (e.g., a2wsgi viability) would be premature optimisation given the chosen process-level switch.
