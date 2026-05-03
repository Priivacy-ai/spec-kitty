# Research: Resource-Oriented Mission API and HATEOAS-LITE

**Mission**: `resource-oriented-mission-api-01KQQRF2`
**Date**: 2026-05-03

## R-01 — WorkPackageRecord fields available for WorkPackageAssignment

**Decision**: Extend `WorkPackageRecord` with two new fields (`claimed_at`, `blocked_reason`). Do not add `review_evidence` to the frozen dataclass — surface it as a derived object built from existing event-log fields inside the router layer (or a thin registry helper).

**Rationale**: `WorkPackageRecord` already carries `last_event_id`, `last_event_at`, `lane`, `assignee`, `agent_profile`, `role`. `claimed_at` and `blocked_reason` require reading back a few events from `status.events.jsonl` during the per-WP scan that the registry already performs (it reads the JSONL to derive `lane`). Adding two fields is additive and low-risk. `review_evidence` is more complex (multi-field sub-object) and is better built from the existing event-log data in a helper or inside the router rather than embedded in the frozen dataclass.

**Alternatives considered**: Read `status.events.jsonl` on demand per request (rejected — violates the registry cache invariant; would re-introduce per-request FS reads). Embed full event history in record (rejected — too large for a frozen snapshot; registry is a summary cache, not a full event store).

## R-02 — `_links` href construction strategy

**Decision**: Build `_links` hrefs in the router layer using f-strings against the request path or the resource's `mission_id`. Do not store hrefs in the Pydantic model constructors or the registry records.

**Rationale**: Hrefs are server-context-dependent (base URL, path prefix). The registry records are path-context-free frozen dataclasses intended to be reused across transports (FastAPI, CLI, future MCP). Embedding href-building in the router layer keeps the registry transport-agnostic. Hrefs use server-relative paths (e.g. `/api/missions/{mission_id}`) so they work without knowledge of the external base URL.

**Alternatives considered**: Pass a `base_url` factory into the registry (rejected — adds transport coupling to the service layer). Use Pydantic validators to inject hrefs at model construction time (rejected — same coupling problem, plus makes models non-reusable from CLI).

## R-03 — `ResourceModel` and `_links` field naming

**Decision**: Use `model_config = ConfigDict(populate_by_name=True)` on `ResourceModel`. The `_links` field is declared as a public Pydantic field using `model_fields` alias mechanism (`Field(alias="_links")` or `model_config` with `alias_generator`). FastAPI serializes using the field alias so the JSON output contains `_links` (with underscore prefix).

**Rationale**: Pydantic v2 by default treats leading-underscore names as private attributes, not model fields. Using `Field(default_factory=dict)` with `alias="_links"` (and `serialization_alias="_links"`) exposes the field correctly in JSON output and in OpenAPI schema. The `ResourceModel` base in `src/dashboard/api/models.py` already handles this (introduced in mission 112) — the new subclasses just inherit the behaviour.

**Alternatives considered**: Using `model_fields` directly with private attribute override (fragile, version-sensitive). Using a `links` field and renaming in serialization (rejected — HATEOAS-LITE paradigm specifies `_links` as the canonical key).

## R-04 — Ambiguous `{mission_id}` selector error shape

**Decision**: Return HTTP 409 with a JSON body `{"detail": "MISSION_AMBIGUOUS_SELECTOR", "candidates": ["slug-a", "slug-b"]}` when the `mid8` prefix matches more than one mission. Return HTTP 404 with `{"detail": "Mission not found: <id>"}` for no match.

**Rationale**: Consistent with the Mission Identity Model from mission 083 (canonical ADR `2026-04-09-1`). The resolver already returns structured `MISSION_AMBIGUOUS_SELECTOR` errors in the CLI; the HTTP layer should mirror that shape so clients can programmatically distinguish "not found" from "ambiguous".

**Alternatives considered**: Return 404 for both cases (rejected — loses the "multiple candidates" signal). Return 400 (rejected — not a client input validation failure; the input is formally valid, just ambiguous).

## R-05 — OpenAPI tag set finalization

**Decision**: Use the following 11-tag set, matching the router-to-tag mapping in the plan. The `features` and `kanban` aliases both receive the `kanban` tag (they return the same shape; grouping them together signals their shared domain and deprecated status to consumers).

| Tag | Routes |
|-----|--------|
| `missions` | All `/api/missions/**` routes |
| `kanban` | `/api/features`, `/api/kanban/{id}` (deprecated aliases) |
| `research` | `/api/research/**` |
| `contracts` | `/api/contracts/**` |
| `checklists` | `/api/checklists/**` |
| `charter` | `/api/charter`, `/api/charter-lint` |
| `dossier` | `/api/dossier/**` |
| `glossary` | `/api/glossary-health`, `/api/glossary-terms`, `/glossary` |
| `health` | `/api/health`, `/api/diagnostics` |
| `sync` | `/api/sync/trigger` |
| `lifecycle` | `/api/shutdown` |

**Alternatives considered**: Separate `deprecated` tag for aliases (rejected — Swagger UI would create a confusing third group; `kanban` tag with deprecation markers in the OpenAPI operation object is cleaner). No tags on deprecated routes (rejected — consumers still need to navigate them during the transition window).

## R-06 — `WorkPackageRecord` backward compatibility

**Decision**: Add `claimed_at` and `blocked_reason` as optional fields with `None` default to `WorkPackageRecord`. Legacy missions without a `status.events.jsonl` already return `None` for `last_event_id`; the same `None` default is appropriate for the new fields.

**Rationale**: `WorkPackageRecord` is a frozen dataclass used by the registry internally. Since it is not part of any external PyPI contract package, adding optional fields is backward-compatible within the codebase. All existing test fixtures that construct `WorkPackageRecord` directly will need to be updated (or use keyword defaults), but this is straightforward.

**Alternatives considered**: A separate `WorkPackageAssignmentRecord` dataclass parallel to `WorkPackageRecord` (rejected — adds indirection with no benefit; the fields are intrinsic to WP identity).
