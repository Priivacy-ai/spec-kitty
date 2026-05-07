# ADR: FastAPI / OpenAPI Transport for the Dashboard API

**Date**: 2026-05-02
**Status**: Accepted
**Mission**: `frontend-api-fastapi-openapi-migration-01KQN2JA`
**Epic**: [#645 — Frontend Decoupling and Application API Platform](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Replaces transport from**: ADR `2026-05-02-1-dashboard-service-extraction.md` (handler-to-service extraction)

## Context

The Spec Kitty dashboard ships a hand-rolled `BaseHTTPServer` + multi-inheritance
router (`src/specify_cli/dashboard/server.py`, `handlers/router.py`) that has
served the local-development surface well but blocks the next two steps in the
frontend platform epic ([#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)):

- **#459** — TypedDict → typed-client codegen: requires a stable contract surface
  whose machine-readable description is published alongside the runtime.
- **#460** — FastAPI / OpenAPI transport migration: previously held pending two
  prerequisites (handler-to-service extraction and the charter bundle chokepoint).

Both prerequisites are now satisfied:

- Handler-to-service extraction shipped in mission
  `dashboard-service-extraction-01KQMCA6` (#111). Every UI-facing read/command
  is a Pydantic-free service object in `src/dashboard/services/*.py` and
  `src/dashboard/file_reader.py`. The handler layer in
  `src/specify_cli/dashboard/handlers/` is a thin single-call adapter (post
  follow-up `dashboard-extraction-followup-01KQMNTW`).
- Charter bundle chokepoint shipped in mission
  `unified-charter-bundle-chokepoint-01KP5Q2G`. `ensure_charter_bundle_fresh()`
  is the single read chokepoint for every charter-derivative reader.

The post-merge mission review of #111 explicitly named the FastAPI transport
as the next step. The dashboard has the right shape now to receive a
framework-backed transport without a "two refactors layered on the same
files" merge cost.

## Decision

Adopt **FastAPI** (with **Uvicorn** as the ASGI server and **Pydantic v2**
as the validation / serialization layer) as the dashboard's HTTP transport.
Mount the application at `src/dashboard/api/` as a new subpackage. Keep the
legacy `BaseHTTPServer` stack in tree until a separate retirement mission
removes it; route requests through one stack or the other via a strangler
boundary in `src/specify_cli/dashboard/server.py` controlled by a config flag
(`dashboard.transport: fastapi | legacy`, default `fastapi` once shipped).

Auto-publish an OpenAPI 3.x document at `/openapi.json` plus FastAPI's
default `/docs` (Swagger) and `/redoc` UIs. Commit a golden snapshot of the
OpenAPI document at `tests/test_dashboard/snapshots/openapi.json` so future
schema drift is caught in CI.

Every FastAPI route handler is written as a **plain Python callable** whose
return value is either a Pydantic model or a `PlainTextResponse` /
`HTMLResponse` for non-JSON content. Route bodies do not write to
`Response`, mutate headers, or perform other HTTP-only side effects. This
"MCP-friendly" invariant is enforced by an architectural test
(`tests/architectural/test_fastapi_handler_purity.py`).

## Rationale

- **Auto-generated OpenAPI** — the document the codegen consumers in #459
  need is a build artifact of the framework, not a hand-rolled file.
- **Pydantic v2 response models** — feed both the runtime serialization and
  the OpenAPI schema; one source of truth for backend + clients.
- **Native async story** — Step 5 of the epic (WebSocket / SSE for live
  updates) becomes cheap on FastAPI. ASGI is a one-line addition rather than
  a transport rewrite.
- **MCP-friendly handler shape** — FR-009 lets a future MCP server adapter
  re-use each FastAPI route function as a plain Python callable. See
  Future Work.
- **Wide ecosystem** — `openapi-typescript`, `openapi-python-client`, MCP
  servers, etc. all consume the same OpenAPI surface FastAPI emits.
- **Clean rollback** — the strangler boundary lets us flip transports at the
  process level. No half-migrated state.

## Consequences

- New top-level dependencies: `fastapi`, `uvicorn[standard]`. Pydantic v2
  resolves transitively (FastAPI's hard requirement); no separate top-level
  Pydantic pin is required.
- The legacy `BaseHTTPServer` stack stays in tree for the duration of one
  release after FastAPI default-on. A separate retirement mission removes
  it.
- `src/dashboard/api/` is a new owned subtree under the existing `dashboard`
  ownership slice. Boundary rules extend the existing FR-010 invariant: no
  imports from `src/specify_cli/dashboard/` inside `src/dashboard/`.
- The OpenAPI snapshot becomes a governance artifact in CI. Drift requires
  reviewer signoff per `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md`.
- TypedDicts in `src/dashboard/api_types.py` remain importable for any
  consumer that uses them. Pydantic models live in `src/dashboard/api/models.py`
  and reuse the canonical names (file split disambiguates).
- `redirect_slashes=False` on the FastAPI app preserves legacy behavior:
  trailing slash mismatches return 404 rather than 308 redirects.

## Rejected Alternatives

- **Keep `BaseHTTPServer` and hand-roll OpenAPI** — high maintenance burden
  for the OpenAPI side; no async story for Step 5; the codegen consumers
  would still need a non-runtime-derived spec, which is a fragile contract.
- **Starlette without FastAPI** — Starlette is the same ASGI engine FastAPI
  builds on, but FastAPI's automatic OpenAPI generation, parameter parsing,
  and Pydantic integration is exactly the value-add we need. Stripping it
  back to Starlette means hand-rolling the OpenAPI generator.
- **aiohttp** — less ergonomic Pydantic integration; smaller OpenAPI
  ecosystem; team has more FastAPI familiarity.
- **Mount FastAPI inside `BaseHTTPServer` via `a2wsgi`** — adds a
  shim dependency (a2wsgi) just for the transition window. The complexity
  is not justified for a one-release dual-stack period; the process-level
  switch is simpler and equally rollback-friendly.

## Future Work — MCP Exposure

The MCP-friendly invariant (FR-009) ensures every route handler can be
invoked outside the HTTP layer. A future MCP server adapter would re-use
the route function bodies directly:

```python
# Future MCP adapter (sketch — NOT in scope of this mission)
from mcp.server import Server
from dashboard.api.routers.features import list_features
from dashboard.api.deps import build_dependencies_for_mcp_invocation

server = Server("spec-kitty-dashboard-mcp")

@server.tool()
async def get_features(project_dir: str) -> dict:
    """List all features in the given Spec Kitty project."""
    deps = build_dependencies_for_mcp_invocation(project_dir=project_dir)
    response_model = list_features(project_dir=deps.project_dir)
    return response_model.model_dump()
```

The route handler `list_features` is the same function FastAPI mounts on
`GET /api/features`. The MCP adapter calls it as a plain Python callable.
The response model serializes to the same JSON the dashboard returns.

The `build_dependencies_for_mcp_invocation` helper is hypothetical — that
adapter is out of scope for this mission and would be filed as a separate
mission once an MCP integration target exists. This ADR documents the
shape so the FastAPI route handlers are written with that future in mind.

## Cross-references

- Ownership map: `architecture/2.x/05_ownership_map.md` § Dashboard
  → `current_state` adds `src/dashboard/api/`; `adapter_responsibilities`
  updated to reflect the FastAPI transport.
- Manifest: `architecture/2.x/05_ownership_manifest.yaml` →
  `dashboard.current_state` mirrors the map.
- Migration runbook: `docs/migration/dashboard-fastapi-transport.md`.
- Stability contract: `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md`.
- Route inventory: `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/route-inventory.md`.
- Parent mission ADR: `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md`.
