---
work_package_id: WP04
title: Routers — Migrate Every Dashboard Route to FastAPI APIRouter + Wire-up
dependencies:
- WP02
- WP03
requirement_refs:
- FR-002
- FR-005
- FR-008
- FR-009
- FR-012
- NFR-005
- NFR-007
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
- T021
- T022
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: python-pedro
authoritative_surface: src/dashboard/api/routers/
execution_mode: code_change
owned_files:
- src/dashboard/api/routers/__init__.py
- src/dashboard/api/routers/features.py
- src/dashboard/api/routers/kanban.py
- src/dashboard/api/routers/artifacts.py
- src/dashboard/api/routers/health.py
- src/dashboard/api/routers/sync.py
- src/dashboard/api/routers/shutdown.py
- src/dashboard/api/routers/charter.py
- src/dashboard/api/routers/diagnostics.py
- src/dashboard/api/routers/dossier.py
- src/dashboard/api/routers/glossary.py
- src/dashboard/api/routers/lint.py
- src/dashboard/api/routers/static_mount.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

You are Python Pedro. Implementation specialist. Every route handler is a thin adapter: one service call, one return.

## Objective

Migrate every dashboard route from legacy handlers to FastAPI `APIRouter`s and wire them all into the FastAPI app from WP02. After this WP, `/openapi.json` enumerates every route in `contracts/route-inventory.md` and `/docs` shows the full Swagger UI.

This WP is large (9 subtasks, ~13 router files). Resist the temptation to split: the routers share the same shape (single service call, one Pydantic return), so once one is right the rest follow the same pattern.

## Subtasks

See `tasks.md` § WP04A and WP04B (the original tasks.md split this into A/B; this consolidated WP combines both). Reference `contracts/route-inventory.md` for the canonical route table.

### Primary route family (T014–T017)

- **T014 — `routers/features.py`** (GET /api/features). Calls `MissionScanService.get_features_list()`. Returns `FeaturesListResponse`.
- **T015 — `routers/kanban.py`** (GET /api/kanban/{feature_id}). FastAPI path param replaces `path.split("/")`. Returns `KanbanResponse`.
- **T016 — `routers/artifacts.py`** (research, contracts, checklists, artifact — 7 routes). Mostly returns `PlainTextResponse` for file content (allowed under FR-009).
- **T017 — `routers/health.py` + `routers/sync.py` + `routers/shutdown.py`**. `sync` and `shutdown` use `Depends(verify_project_token)`. `sync` calls `service.trigger_sync()`, returns the discriminated union response.

### Secondary route family (T018–T022)

- **T018 — `routers/charter.py` + `routers/diagnostics.py`**. Both thin: `charter` returns `PlainTextResponse`; `diagnostics` returns `DiagnosticsResponse`.
- **T019 — `routers/dossier.py`** (4 sub-routes). `mission_slug` is a typed `Query` parameter. Calls into existing `DossierAPIHandler(repo_root)`.
- **T020 — `routers/glossary.py` + `routers/lint.py`** (transport-only). Copy legacy logic into a private function in the router file. Add `# TODO(follow-up): extract glossary/lint service object — see issue #YYY` markers and file two follow-up issues at mission close.
- **T021 — `routers/static_mount.py`**. `app.mount("/static", StaticFiles(directory=...))` + `GET /` returning `HTMLResponse(content=get_dashboard_html_bytes())`.
- **T022 — Wire all routers into `app.py`**. Co-edit with the WP02 author. `app.include_router(...)` calls in alphabetical order so the snapshot is deterministic.

## Implementation invariants (apply to every route)

1. **One service call per handler body.** No path parsing, no result interpretation, no header writes inside the route function body.
2. **Token validation lives in `Depends(verify_project_token)`.** Never inline.
3. **Path parameters use FastAPI's typed path parser** (`feature_id: str`), never `request.path.split("/")` inside the body.
4. **Query parameters are typed** (`token: str | None = Query(default=None)`), never `parse_qs` inside the body.
5. **Return value is a Pydantic model OR a `PlainTextResponse` / `HTMLResponse`** for non-JSON content.
6. **Status codes** match `contracts/route-inventory.md` § "Status code table".
7. **Each handler ≤ 15 lines** (NFR-007). If a handler exceeds this, extract a module-level helper (NOT a service method — service extraction for glossary/lint/etc. is out of scope for this mission).

## Definition of Done

- [ ] Every route in `contracts/route-inventory.md` is registered on the FastAPI app.
- [ ] `/openapi.json` enumerates every route.
- [ ] `/docs` shows the full Swagger UI.
- [ ] Every route handler body is ≤ 15 lines.
- [ ] No FastAPI `Response` / `JSONResponse` / `starlette.Response` writes inside route function bodies.
- [ ] Token validation happens in `Depends`, not inline.
- [ ] Glossary and lint routes carry `# TODO(follow-up)` markers; two follow-up issues filed.

## Reviewer guidance

- Eyeball every route handler: does it look like `return service.method(...)` or does it do plumbing?
- Confirm `app.include_router(...)` calls are in alphabetical order in `app.py`.
- Confirm no `path.split("/")` patterns remain inside route bodies.

## Risks

- Path-param vs query-param mismatch with legacy URL structure. Mitigation: parity test.
- Dossier sub-route regex divergence between legacy `path.split("/")` and FastAPI's path parser. Mitigation: parity test.
- Shutdown semantics under Uvicorn vs `BaseHTTPServer` (signal handling, port unbind). Mitigation: parity test.
- Glossary / lint passthrough may surface latent bugs the legacy handler swallowed. Mitigation: parity test asserts byte-equivalent output, including 404 / 500 paths.

## Activity Log

- 2026-05-02T20:16:04Z – claude – Moved to claimed
- 2026-05-02T20:16:07Z – claude – Moved to in_progress
- 2026-05-02T20:25:10Z – claude – Moved to for_review
- 2026-05-02T20:25:13Z – claude – Moved to in_review
- 2026-05-02T20:25:16Z – claude – Moved to approved
- 2026-05-02T20:25:19Z – claude – Done override: Lane-less mission run on parent feature/650-dashboard-ui-ux-overhaul branch
