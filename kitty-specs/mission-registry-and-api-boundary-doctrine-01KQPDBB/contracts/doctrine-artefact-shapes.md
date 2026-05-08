# Contract — Doctrine Artefact Shapes

Three new artefacts ship in this mission. Each one is a YAML file under `src/doctrine/<layer>/shipped/` and must satisfy the existing shipped-doctrine schema (validated by `tests/doctrine/`). NFR-007 requires zero schema-suppression markers.

If the existing schema does not support a field this mission needs (e.g., `referenced_tests:`), the WP02 implementer MUST extend the schema additively in the same WP — do not introduce a free-form `metadata:` escape hatch.

## 1. `DIRECTIVE_API_DEPENDENCY_DIRECTION`

**Path**: `src/doctrine/directives/shipped/api-dependency-direction.directive.yaml`

```yaml
directive-id: "037"   # next sequential ID; check src/doctrine/directives/shipped/ for current max
name: "API Dependency Direction"
short-name: "api-dependency-direction"
schema-version: "1.0"

scope: "src/dashboard/api/routers/, src/specify_cli/cli/commands/, future MCP tool surfaces"

rule: |
  Modules under src/dashboard/api/routers/, src/specify_cli/cli/commands/dashboard.py,
  or any future MCP tool surface MUST consume mission, work-package, or
  artifact data exclusively via the canonical service-layer interface
  (dashboard.services.registry.MissionRegistry as of mission
  mission-registry-and-api-boundary-doctrine-01KQPDBB).

  Direct imports from any of the following are forbidden:
    - specify_cli.dashboard.scanner
    - specify_cli.scanner
    - any module path matching *scanner*

  Direct filesystem walks (Path.rglob, os.walk, glob.glob) on
  kitty-specs/* inside transport modules are forbidden.

forbidden-imports:
  - specify_cli.dashboard.scanner
  - specify_cli.scanner

forbidden-patterns:
  - "Path(...).rglob(...) inside route function bodies"
  - "open(...) on kitty-specs/* paths inside CLI command bodies"

referenced-tests:
  - tests/architectural/test_transport_does_not_import_scanner.py

rationale: |
  Multiple independent readers of the same kitty-specs/ data have no
  enforcement that they agree. A bugfix to one path can land silently
  with no signal that another consumer's output diverged. The registry
  is the single sanctioned reader; transports go through it.

  See ADR architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md
  and the architectural assessment at architecture/2.x/initiatives/2026-05-stable-application-api-surface/README.md.

introduced-by-mission: "mission-registry-and-api-boundary-doctrine-01KQPDBB"
introduced-at: "2026-05-03"
```

## 2. `DIRECTIVE_REST_RESOURCE_ORIENTATION`

**Path**: `src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml`

```yaml
directive-id: "038"
name: "REST Resource Orientation"
short-name: "rest-resource-orientation"
schema-version: "1.0"

scope: "Public HTTP endpoints under src/dashboard/api/routers/"

rule: |
  Public HTTP endpoints follow resource-oriented naming:
    - URL paths name the noun (the resource).
    - HTTP methods name the verb.
    - Operations on a single resource live under /api/<collection>/{id}.
    - Nested collections live under /api/<collection>/{id}/<sub-collection>.

  Action-shaped URLs (e.g., /api/sync/trigger, /api/shutdown) are
  permitted but MUST be tagged "actions" in the OpenAPI document and
  registered in the architectural test's allowlist.

  URL renames (e.g., /api/features → /api/missions) follow a deprecation
  cycle: the old path is retained for one release with a Deprecation HTTP
  header per RFC 8594 pointing at the new path. The OpenAPI snapshot test
  gates the rename.

referenced-tests:
  - tests/architectural/test_url_naming_convention.py

rationale: |
  The current API has /api/features (verb-shaped historical name) and
  /api/kanban (verb-in-URL). A resource-oriented surface (/api/missions,
  /api/missions/{id}/workpackages, etc.) is more discoverable for the
  consumer set this epic targets (UI, CLI, MCP, SDK).

introduced-by-mission: "mission-registry-and-api-boundary-doctrine-01KQPDBB"
introduced-at: "2026-05-03"
```

## 3. `HATEOAS-LITE` paradigm

**Path**: `src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml`

```yaml
paradigm-id: "hateoas-lite"
name: "HATEOAS-LITE"
schema-version: "1.0"

description: |
  Resource responses include a _links block with the canonical URL of every
  related resource the consumer might navigate to. Consumers do not need
  out-of-band knowledge of the URL scheme; they follow links.

  This is "lite" because we do not adopt full HAL or JSON:API. We add only
  the _links convention. It is the smallest step toward discoverability
  that does not over-engineer the local-dashboard scope.

shape: |
  Every Pydantic response model that represents a resource subclasses the
  marker base class dashboard.api.models.ResourceModel and declares:

      _links: dict[str, Link]

  where Link is:

      class Link(BaseModel):
          href: str
          method: str = "GET"

example: |
  GET /api/missions/01KQN2JA... →
  {
    "mission_id": "01KQN2JA...",
    "mission_slug": "frontend-api-fastapi-openapi-migration-01KQN2JA",
    "lane_counts": {"done": 6},
    "_links": {
      "self":         {"href": "/api/missions/01KQN2JA..."},
      "status":       {"href": "/api/missions/01KQN2JA.../status"},
      "workpackages": {"href": "/api/missions/01KQN2JA.../workpackages"}
    }
  }

future-graduation-triggers:
  - First public / external SDK consumer (HAL _embedded saves round-trips)
  - First paginated collection where the client needs included sub-resources
  - First multi-tenant deployment where bandwidth cost matters
  - First case where a consumer needs to discover state-transition operations

future-migration-shape: |
  When any trigger fires, file a follow-up ADR documenting the trigger,
  the chosen target (HAL vs JSON:API), and the migration plan.

  Migration is additive: new fields (_embedded for HAL; data/included for
  JSON:API) ship alongside existing _links. Both are valid for the
  deprecation period. The marker ResourceModel and the architectural test
  signature are forward-compatible.

  Detailed rationale + trigger table at
  architecture/2.x/initiatives/2026-05-stable-application-api-surface/README.md § 3.3.

referenced-tests:
  - tests/architectural/test_resource_models_have_links.py

introduced-by-mission: "mission-registry-and-api-boundary-doctrine-01KQPDBB"
introduced-at: "2026-05-03"
```

## Schema-extension fallback

If the existing shipped-doctrine schema does not accept the `referenced-tests:`, `forbidden-imports:`, `forbidden-patterns:`, `future-graduation-triggers:`, or `future-migration-shape:` fields, WP02 must:

1. Identify the rejecting field via `pytest tests/doctrine/ -v`.
2. Extend the schema additively (new optional field, default None / empty list).
3. Land the schema extension in the same WP02 commit.
4. Verify all existing shipped artefacts still validate after the extension.

This is documented as an expected sub-task of WP02 in the spec's Phase 0 research § R-4.

## Cross-reference back from the artefact

Each new artefact references the architectural test that enforces it. Each architectural test references the directive/paradigm in its module docstring. Both directions of the cross-link are required so a future doctrine reader can navigate from rule to enforcement (or vice versa) without out-of-band knowledge.
