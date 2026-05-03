---
work_package_id: WP01
title: Governance Artifacts (ADR, ownership map, manifest, migration runbook)
dependencies: []
requirement_refs:
- FR-015
- FR-016
- FR-017
- FR-020
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: architect-alphonso
authoritative_surface: architecture/2.x/
execution_mode: planning_artifact
owned_files:
- architecture/2.x/05_ownership_map.md
- architecture/2.x/05_ownership_manifest.yaml
- architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md
- docs/migration/dashboard-fastapi-transport.md
role: architect
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load architect-alphonso
```

You are Architect Alphonso. Your role is precise architectural documentation. You do not write source code in this WP.

## Objective

Land the governance artifacts before any code change so DIRECTIVE_024 (Locality of Change) compliance is auditable from the start of the migration.

## Subtasks

### T001 — ADR `2026-05-02-2-fastapi-openapi-transport.md`

Follow the existing ADR template structure (see `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md` for the canonical shape):

- **Context**: dashboard transport currently `BaseHTTPServer` + hand-rolled router; service extraction is done; charter chokepoint is done; epic #645 sequencing places transport migration as Step 4.
- **Decision**: adopt FastAPI + Pydantic v2 + Uvicorn for the dashboard transport, with a strangler boundary in `src/specify_cli/dashboard/server.py` and a `dashboard.transport` config flag.
- **Rationale**: auto-generated OpenAPI; native async support for future Step 5 (WebSocket / SSE); MCP-friendly handler shape; widely adopted ecosystem; clean rollback story via the strangler.
- **Consequences**:
  - new top-level deps (`fastapi`, `uvicorn`, transitively Pydantic v2)
  - the legacy stack stays in tree until a separate retirement mission removes it
  - `src/dashboard/api/` is a new owned subtree; its boundary rules extend the existing `src/dashboard/` package boundary
  - OpenAPI snapshot becomes a governance artifact in CI
- **Rejected Alternatives**:
  - keep `BaseHTTPServer` + hand-roll OpenAPI: high maintenance burden, no async story
  - Starlette without FastAPI: still need to hand-roll OpenAPI generation
  - aiohttp: less ergonomic Pydantic integration; smaller ecosystem
  - mounted FastAPI inside `BaseHTTPServer` via a2wsgi: complexity not justified for a one-release transition
- **Future Work**: 10-line worked example showing how a FastAPI route handler is invoked as a plain Python callable from an MCP tool definition. Reference `FR-009` and `FR-020`.

Cross-link the ADR from `architecture/adrs/README.md` if there is an index file.

### T002 — `architecture/2.x/05_ownership_map.md` Dashboard slice

Locate the `## Dashboard` section. Add to `current_state` (or whatever field captures the migration target):

- `src/dashboard/api/` — FastAPI app subpackage (new, this mission)
- `src/dashboard/api/models.py` — Pydantic v2 response models (new, this mission)

Update `adapter_responsibilities` to reflect the transport change:

- HTTP dispatch and request routing — was `router.py`; will be `fastapi.FastAPI` with `APIRouter` per family
- Token validation via `Depends(verify_project_token)` — was inline guards in handler methods
- Static asset serving via `StaticFiles` mount — was custom `static.py`

Cross-link the ADR (FR-015) from this section.

### T003 — `architecture/2.x/05_ownership_manifest.yaml`

Mirror T002 in the YAML manifest. Schema-validate with the existing schema test (`tests/architectural/test_ownership_manifest_schema.py`) before committing.

### T004 — `docs/migration/dashboard-fastapi-transport.md` (parallelizable)

Migration runbook for operators. Contents:

1. **What changed**: transport implementation under the hood; all external behavior unchanged.
2. **Default**: `dashboard.transport: fastapi` is the default after this mission ships.
3. **How to roll back**: set `.kittify/config.yaml` → `dashboard.transport: legacy` OR run `spec-kitty dashboard --transport legacy`.
4. **Known behavior diffs** (audit during implementation; document any that surface):
   - trailing-slash redirects: FastAPI default OFF in this mission to match legacy
   - header casing: HTTP header field names are case-insensitive; some clients are picky — document any observed regression
   - 404 vs 503 ordering on combined token+path errors
5. **`/openapi.json`, `/docs`, `/redoc`**: only available under FastAPI transport; document the URLs.
6. **Rollback verification**: how to run the parity test suite to prove rollback is functional.

## Definition of Done

- [ ] ADR file exists and reads as a self-contained decision record.
- [ ] Ownership map entries land before any code WP starts.
- [ ] Manifest entries match the map; schema test passes.
- [ ] Migration runbook is operator-ready.
- [ ] All commits land on `feature/650-dashboard-ui-ux-overhaul`.

## Reviewer guidance

- Confirm the ADR's Future Work § contains a concrete MCP-handler-reuse example (not just a vague reference).
- Confirm the runbook's rollback procedure is the actual procedure (config flag value + CLI flag both verified).
- Confirm the ownership map entries align exactly with the manifest (text-only drift is also a finding).

## Risks

- ADR drift between the file and the actual decision (low — single author per WP).
- Manifest schema drift (caught by existing schema test).

## Activity Log

- 2026-05-02T19:56:48Z – claude – Moved to claimed
- 2026-05-02T19:56:51Z – claude – Moved to in_progress
- 2026-05-02T20:00:01Z – claude – Moved to for_review
- 2026-05-02T20:00:04Z – claude – Moved to in_review
- 2026-05-02T20:00:07Z – claude – Moved to approved
- 2026-05-02T20:00:16Z – claude – Moved to done
