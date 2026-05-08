# Research — api-surface-completion-services-aliases-async

Mission: `api-surface-completion-services-aliases-async-01KQSXDA`
Branch: `feature/645-api-surface-completion-mission-c`

---

## A. TypedDict Migration Categorisation (FR-019)

Source file: `src/dashboard/api_types.py`
Callers confirmed via `grep -r "api_types" src/ --include="*.py" -l`:
- `src/specify_cli/dashboard/api_types.py` (shim re-exporter)
- `src/specify_cli/dashboard/handlers/lint.py`
- `src/specify_cli/dashboard/handlers/glossary.py`
- `src/dashboard/file_reader.py`
- `src/dashboard/api/models.py`
- `src/dashboard/services/project_state.py`
- `src/dashboard/services/mission_scan.py`

Additional type-specific callers from `grep -r "GlossaryHealth\|GlossaryTerm\|DecayWatch" src/ --include="*.py" -l`:
- `src/dashboard/api/routers/glossary.py`
- `src/dashboard/api/routers/lint.py`
- `src/dashboard/api/models.py`
- `src/dashboard/api_types.py`
- `src/specify_cli/dashboard/handlers/glossary.py`
- `src/specify_cli/dashboard/handlers/lint.py`

### Categorisation Table

| TypedDict | Current callers (key files) | Proposed location | Rationale |
|-----------|----------------------------|-------------------|-----------|
| `ArtifactDirectoryFile` | `dashboard/api/routers/artifacts.py`, `dashboard/api_types.py` | `src/dashboard/api/presentation_types.py` | Used only by dashboard file-browser routes (`/api/contracts/{id}`, `/api/checklists/{id}`). No domain owner outside the dashboard UI. |
| `ArtifactDirectoryResponse` | `dashboard/api/routers/artifacts.py`, `dashboard/api_types.py` | `src/dashboard/api/presentation_types.py` | Wraps `ArtifactDirectoryFile`; exclusively a dashboard file-browser shape. |
| `ArtifactInfo` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Describes per-artifact `exists`/`mtime`/`size` metadata produced by the mission scanner and embedded inside `FeatureItem`. Co-locating it with its parent keeps the missions domain self-contained. |
| `ErrorResponse` | `dashboard/api_types.py`, `dashboard/file_reader.py` | `src/kernel/api_types.py` | Generic `{"error", "detail", "status"}` envelope. No domain owner; used anywhere a JSON error payload is needed. |
| `SyncInfo` | `dashboard/api_types.py` | `src/kernel/api_types.py` | Nested sub-block of `HealthResponse`. Infrastructure-level synchronisation metadata; no domain ownership. |
| `HealthResponse` | `dashboard/api_types.py`, `dashboard/api/routers/health.py` | `src/kernel/api_types.py` | Server-health wire shape. Cross-cutting infrastructure endpoint with no domain owner. |
| `KanbanTaskData` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/status/api_types.py` | Represents a single WP card. Directly derived from work-package status lane data. |
| `KanbanStats` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/status/api_types.py` | Per-feature lane summary counts. Directly aggregates `Lane` values from the status domain. |
| `KanbanResponse` | `dashboard/api/routers/kanban.py`, `dashboard/api_types.py` | `src/specify_cli/status/api_types.py` | Top-level response for the kanban board endpoint. Status domain aggregate. |
| `ResearchArtifact` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Research artifact file metadata returned by `/api/research/{feature_id}`. Part of the mission artifact surface. |
| `ResearchResponse` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Response envelope for `/api/research/{feature_id}`. Mission artifact domain. |
| `MissionRecord` | `dashboard/services/registry.py`, `dashboard/api/routers/missions.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Per-mission wire record keyed by `mission_id`. Canonical mission identity domain. |
| `WorktreeInfo` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Worktree path/existence pair embedded in `FeatureItem`. Mission management domain. |
| `WorkflowStatus` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | `specify → plan → tasks → implement` progression flags. Mission lifecycle domain. |
| `FeatureItem` | `dashboard/services/mission_scan.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Full per-mission wire representation for list endpoints. Mission management domain; aggregates `WorktreeInfo`, `WorkflowStatus`, `KanbanStats`, `ArtifactInfo`. |
| `MissionContext` | `dashboard/services/project_state.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Active mission block in features-list/health responses. Mission management domain. |
| `FeaturesListResponse` | `dashboard/api/routers/features.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Response for deprecated `/api/features`. Mission registry domain; successor is `/api/missions`. |
| `FeaturesListErrorResponse` | `dashboard/api/routers/features.py`, `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` | Error variant of `FeaturesListResponse`. Same domain as parent. |
| `GlossaryTermRecord` | `dashboard/api/routers/glossary.py`, `specify_cli/dashboard/handlers/glossary.py`, `dashboard/api_types.py` | `src/specify_cli/glossary/types.py` | FR-016 explicit requirement. Represents a single glossary term sense; owned by the glossary domain. |
| `GlossaryHealthResponse` | `dashboard/api/routers/glossary.py`, `specify_cli/dashboard/handlers/glossary.py`, `dashboard/api_types.py` | `src/specify_cli/glossary/types.py` | FR-016 explicit requirement. Glossary health metrics for `/api/glossary-health`. Glossary domain. |
| `DecayWatchTileResponse` | `dashboard/api/routers/lint.py`, `specify_cli/dashboard/handlers/lint.py`, `dashboard/api_types.py` | `src/specify_cli/charter_lint/types.py` | FR-017 explicit requirement. Charter-lint scan summary; owned by the charter-lint domain. |
| `SyncTriggerSuccess` | `dashboard/api/routers/sync.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Thin `{"status": "scheduled"}` shape for the sync trigger endpoint. Infrastructure; no domain ownership. |
| `FileIntegrity` | `dashboard/api/routers/diagnostics.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Diagnostics file-integrity sub-section. Infrastructure-level cross-cutting shape. |
| `DiagnosticsFeatureStatus` | `dashboard/api/routers/diagnostics.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Per-feature diagnostics status sub-record. Infrastructure diagnostics; cross-cutting with no single domain owner. |
| `CurrentFeatureDetected` | `dashboard/api/routers/diagnostics.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Discriminated-union member for `current_feature` block. Infrastructure diagnostics. |
| `CurrentFeatureNotDetected` | `dashboard/api/routers/diagnostics.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Discriminated-union member for `current_feature` block. Infrastructure diagnostics. |
| `DashboardHealthInfo` | `dashboard/api/routers/diagnostics.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Dashboard process-health section within diagnostics. Infrastructure. |
| `DiagnosticsResponse` | `dashboard/api/routers/diagnostics.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Top-level `/api/diagnostics` response. Infrastructure diagnostics; cross-cutting aggregate. |
| `DiagnosticsErrorResponse` | `dashboard/api/routers/diagnostics.py`, `dashboard/api_types.py` | `src/kernel/api_types.py` | Error variant of diagnostics. Infrastructure. |

**Note:** `src/kernel/` already exists as a package (`src/kernel/__init__.py`, `atomic.py`, `paths.py`, `glossary_types.py`, `_safe_re.py`). **No new package creation is required.** Only `src/kernel/api_types.py` needs to be added to the existing package.

**Note on `src/dashboard/api/presentation_types.py`:** Only `ArtifactDirectoryFile` and `ArtifactDirectoryResponse` are justified as dashboard-presentation-only. Both are consumed exclusively by the file-browser routes that list contract/checklist markdown files — there is no equivalent concept outside the dashboard UI surface. Every other type that could be argued "dashboard-only" (e.g., `DashboardHealthInfo`) is cross-cutting infrastructure and is better placed in `kernel/` to enable future non-dashboard consumers (e.g., a CLI diagnostics command).

---

## B. GlossaryService Extraction (FR-001)

### Private helpers in `src/dashboard/api/routers/glossary.py`

| Helper | Role |
|--------|------|
| `_empty_health_response()` | Returns a zero-count health dict when project dir is unavailable |
| `_count_orphaned_terms(project_dir)` | Reads `.kittify/doctrine/graph.yaml`, counts `glossary:*` URNs with no incoming `vocabulary` edge |
| `_collect_all_senses(repo_root)` | Iterates `GlossaryScope` members, calls `load_seed_file(scope, repo_root)` for each, returns flat list of `TermSense` objects |
| `_build_glossary_health(project_dir)` | Calls `_collect_all_senses`, iterates `iter_semantic_conflicts`, produces `GlossaryHealthResponse` dict |
| `_build_glossary_terms(project_dir)` | Calls `_collect_all_senses`, maps each `TermSense` to a `GlossaryTermRecord` dict |

The legacy `BaseHTTPRequestHandler` in `src/specify_cli/dashboard/handlers/glossary.py` contains identical logic (same helpers, same field names). `GlossaryService` must wrap both handler implementations without duplicating logic.

### `specify_cli.glossary` APIs consumed by GlossaryService

| API | Import | Purpose |
|-----|--------|---------|
| `GlossaryScope` | `specify_cli.glossary.scope` | Enum of scope levels (`MISSION_LOCAL`, `TEAM_DOMAIN`, `AUDIENCE_DOMAIN`, `SPEC_KITTY_CORE`) |
| `load_seed_file(scope, repo_root)` | `specify_cli.glossary.scope` | Returns `list[TermSense]` for a given scope |
| `iter_semantic_conflicts(project_dir)` | `specify_cli.glossary.semantic_events` | Yields `SemanticConflictRecord` objects with `.severity`, `.timestamp` |

`TermSense` attributes used:
- `.status.value` → `"active"`, `"draft"`, `"deprecated"`
- `.confidence` → `float | None`
- `.surface.surface_text` → `str`
- `.definition` → `str | None`

### Chosen GlossaryService method signatures

```python
# src/specify_cli/glossary/service.py

from __future__ import annotations

from pathlib import Path

from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord


class GlossaryService:
    """Read-only domain service for glossary data. No FastAPI/Pydantic imports."""

    def __init__(self, project_dir: Path) -> None: ...

    def get_health(self) -> GlossaryHealthResponse:
        """Aggregate glossary health metrics across all scopes.

        Returns a GlossaryHealthResponse with total_terms, active_count,
        draft_count, deprecated_count, high_severity_drift_count,
        orphaned_term_count, entity_pages_generated, entity_pages_path,
        last_conflict_at.
        """
        ...

    def get_terms(self) -> list[GlossaryTermRecord]:
        """Return all glossary terms across all scopes.

        Each entry contains surface, definition, status, confidence.
        """
        ...
```

**Constraint (C-003):** `GlossaryService` must not import `fastapi`, `starlette`, or `pydantic`. The service works with plain dicts and TypedDicts only.

---

## C. LintService Extraction (FR-003)

### What the current handler does

`_build_charter_lint(project_dir)` in `src/dashboard/api/routers/lint.py` (and its mirror in `src/specify_cli/dashboard/handlers/lint.py`):

1. Reads `.kittify/lint-report.json` if it exists
2. Parses `data["findings"]` — a list of dicts
3. Counts findings by `category` field: `"orphan"`, `"contradiction"`, `"staleness"`, `"reference_integrity"`
4. Counts `high_severity_count` where `severity in {"high", "critical"}`
5. Reads top-level fields: `scanned_at`, `feature_scope`, `duration_seconds`
6. Returns `DecayWatchTileResponse` (or the zero-count empty response if the file is absent)

### `.kittify/lint-report.json` schema (inferred from handler code)

```json
{
  "scanned_at": "2026-01-18T10:00:00+00:00",
  "feature_scope": "083-my-mission",
  "duration_seconds": 0.42,
  "findings": [
    {
      "category": "orphan",
      "severity": "high",
      ...
    },
    {
      "category": "contradiction",
      "severity": "low",
      ...
    }
  ]
}
```

No other top-level fields are read by the current handler.

### Chosen LintService method signatures

```python
# src/specify_cli/charter_lint/service.py

from __future__ import annotations

from pathlib import Path

from specify_cli.charter_lint.types import DecayWatchTileResponse


class LintService:
    """Read-only domain service for charter-lint data. No FastAPI/Pydantic imports."""

    def __init__(self, project_dir: Path) -> None: ...

    def get_decay_tile(self) -> DecayWatchTileResponse:
        """Read .kittify/lint-report.json and return the decay watch tile payload.

        Returns the zero-count empty response when the report file is absent
        or cannot be parsed.
        """
        ...
```

**Constraint (C-003):** `LintService` must not import `fastapi`, `starlette`, or `pydantic`.

---

## D. SSE Implementation Approach (FR-009–FR-012)

### Decision: Starlette built-in `StreamingResponse` with `text/event-stream`

**Chosen approach:** Use `starlette.responses.StreamingResponse` (available as a transitive dep of `fastapi>=0.136.1`) with `media_type="text/event-stream"` and an async generator body.

**Why not `sse-starlette`?**
- `sse-starlette` is not listed in `pyproject.toml` and adding it would require pyproject + uv.lock changes (C-008).
- Starlette's `StreamingResponse` provides everything needed without a new dependency: async generator body, correct content-type, header control.
- `sse-starlette` adds keepalive ping machinery and `EventSourceResponse` convenience class, but both are straightforward to implement manually (< 30 lines).

**Why not FastAPI `BackgroundTasks` or WebSocket?**
- C-004 mandates read-only. SSE is the correct unidirectional push primitive.
- WebSocket is bidirectional and heavier; clients need only a standard `EventSource`.

**Alternatives considered:**
| Approach | Verdict |
|----------|---------|
| `sse-starlette` package | ❌ New dep; not justified given trivial manual implementation |
| Starlette `StreamingResponse` (chosen) | ✅ Zero new dep; fully async; correct wire format |
| FastAPI `StreamingResponse` alias | Same as Starlette; either import path is fine |
| WebSocket | ❌ Overkill; bidirectional; wrong tool for read-only push |

### `Last-Event-ID` resumption against the status event log

- Client sends `Last-Event-ID: <event_id>` header on reconnect.
- `event_id` is the ULID from `StatusEvent.event_id` (26-char `[0-9A-HJKMNP-TV-Z]{26}`).
- On connection the handler reads the request's `Last-Event-ID` header.
- If present: call `read_events(feature_dir)` (from `specify_cli.status.store`) and skip events whose `event_id` is lexicographically ≤ the given ULID (ULIDs are monotonically sortable by time).
- Then stream only the unseen events before entering the live-tail loop.
- If absent: stream only the `connected` heartbeat; future events are pushed as they are appended.

**Read loop strategy (polling):**
Because status events are appended to a JSONL file on disk there is no in-process pub/sub bus. The SSE generator will poll `status.events.jsonl` on a configurable interval (default 2 s) using `asyncio.sleep`, tracking the last event position it has already dispatched. This avoids `inotify`/`fsevents` (new dep) and works cross-platform.

### Keepalive

SSE clients disconnect if no data arrives for ~30–60 s (browser timeout varies by vendor). The generator sends a comment line (`:keepalive\n\n`) every 15 seconds when no real events are available:

```
: keepalive

```

Comment lines (starting with `:`) are part of the SSE spec; they reset the reconnect timer without triggering `onmessage`.

---

## E. Alias Retirement (FR-007, FR-008)

### Routes to retire

| Route | Current behaviour | New behaviour |
|-------|------------------|---------------|
| `GET /api/features` | Returns `FeaturesListResponse` with `Deprecation: true` header | HTTP 410 Gone |
| `GET /api/kanban/{feature_id}` | Returns `KanbanResponse` with `Deprecation: true` header | HTTP 410 Gone |

### Pattern chosen for 410 response

A module-level `_gone_response()` helper returns a `JSONResponse` with status 410 and a body that follows the existing `ErrorResponse` shape. This keeps the route body clean (no inline `Response` construction, per FR-009):

```python
def _gone_response(deprecated_path: str, successor_path: str) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={
            "error": "endpoint_retired",
            "detail": (
                f"{deprecated_path!r} was retired. "
                f"Use {successor_path!r} instead."
            ),
        },
    )
```

### Router strategy: keep handler, exclude from OpenAPI schema

The retired paths **keep their route handlers** (so existing callers receive a proper 410
rather than a silent 404), but are excluded from the OpenAPI document via
`include_in_schema=False`. This satisfies FR-007/FR-008 ("removed from the OpenAPI
document") while being safe for legacy callers.

```python
@router.get("/api/features", include_in_schema=False)
async def retired_features() -> JSONResponse:
    return _gone_response("/api/features", "/api/missions")


@router.get("/api/kanban/{feature_id}", include_in_schema=False)
async def retired_kanban(feature_id: str) -> JSONResponse:
    return _gone_response(f"/api/kanban/{feature_id}", f"/api/missions/{feature_id}/status")
```

**Why not keep with `deprecated=True`?** Marking as deprecated keeps the path visible in
the OpenAPI spec and the generated TypeScript types — exactly what the FR forbids. The
goal is that new consumers cannot discover or depend on the retired paths.

### 410 response body

The body must match the spec precisely (FR-007, FR-008):

```python
def _gone_response(deprecated_path: str, successor_path: str) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={
            "error": "endpoint_retired",
            "successor": successor_path,
        },
    )
```

The `successor` key (not `detail`) is the wire format mandated by the spec.

### OpenAPI impact

- Both routes have `include_in_schema=False`; they are **absent** from the OpenAPI document and the generated `.d.ts`.
- The OpenAPI snapshot (`tests/test_dashboard/snapshots/openapi.json`) must be regenerated after retirement; paths `/api/features` and `/api/kanban/{feature_id}` must be absent.
- `Deprecation` and `Link` headers are removed (the endpoint is gone, not merely deprecated).

---

## F. openapi-typescript Codegen (FR-013)

### Existing OpenAPI snapshot location

```
tests/test_dashboard/snapshots/openapi.json
```

The snapshot is generated by `test_openapi_snapshot.py` via:
```python
from dashboard.api import create_app
app = create_app(project_dir=tmp_path, project_token=None)
spec = app.openapi()
```

### Command to regenerate the snapshot

```bash
cd src
python - <<'EOF'
import json
from pathlib import Path
from unittest.mock import MagicMock

tmp = Path("/tmp/ok")  # dummy; app.state.project_dir is not read during openapi()
tmp.mkdir(exist_ok=True)

from dashboard.api import create_app
app = create_app(project_dir=tmp, project_token=None)
spec = json.dumps(app.openapi(), sort_keys=True, indent=2) + "\n"
Path("../tests/test_dashboard/snapshots/openapi.json").write_text(spec, encoding="utf-8")
print("Snapshot written.")
EOF
```

Or equivalently, update the snapshot from the failing test output:
```bash
cd src && pytest tests/test_dashboard/test_openapi_snapshot.py --snapshot-update 2>/dev/null
# (if pytest-snapshot plugin is present — it is not; use the python snippet above instead)
```

### `npx openapi-typescript` invocation

```bash
npx openapi-typescript tests/test_dashboard/snapshots/openapi.json \
  --output src/dashboard/static/ts/api.d.ts
```

Or from repo root:
```bash
npx openapi-typescript \
  tests/test_dashboard/snapshots/openapi.json \
  --output src/dashboard/static/ts/api.d.ts
```

### Output path for `.d.ts`

```
src/dashboard/static/ts/api.d.ts
```

This keeps the generated types co-located with the dashboard frontend assets without polluting the Python source tree.

### How to run in CI without a live server

`openapi-typescript` accepts a local JSON file (not just a URL). The regeneration step reads `tests/test_dashboard/snapshots/openapi.json` directly, so no running server is needed. The CI step is:

```yaml
- name: Generate TypeScript API types
  run: |
    npx openapi-typescript \
      tests/test_dashboard/snapshots/openapi.json \
      --output src/dashboard/static/ts/api.d.ts
```

The `test_openapi_snapshot.py` test already validates that the snapshot is fresh. Adding a `git diff --exit-code src/dashboard/static/ts/api.d.ts` check after the codegen step will catch drift between snapshot and generated types.
