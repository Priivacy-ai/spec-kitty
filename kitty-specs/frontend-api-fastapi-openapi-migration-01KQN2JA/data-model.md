# Data Model — Pydantic Response Models

Each existing TypedDict in `src/dashboard/api_types.py` gets an equivalent
Pydantic v2 `BaseModel` in `src/dashboard/api/models.py`. The Pydantic model
name matches the TypedDict name (file split is sufficient to disambiguate);
fields keep the same name and type, with `Optional[T]` rendered as `T | None`.

## Core models (every consumer migrates)

```python
# src/dashboard/api/models.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any


class MissionContext(BaseModel):
    name: str
    domain: str
    version: str
    slug: str
    description: str
    path: str
    feature: str | None = None


class Feature(BaseModel):
    id: str
    name: str
    path: str
    is_legacy: bool = False
    # ... full field list mirrors api_types.Feature exactly


class FeaturesListResponse(BaseModel):
    features: list[Feature]
    active_feature_id: str | None
    project_path: str
    worktrees_root: str | None
    active_worktree: str | None
    active_mission: MissionContext


class KanbanResponse(BaseModel):
    lanes: dict[str, list[Any]]
    is_legacy: bool
    upgrade_needed: bool
    weighted_percentage: float | None


class HealthResponse(BaseModel):
    status: str
    project_path: str
    sync: dict[str, Any]
    websocket_status: str
    token: str | None = None
```

## Sync trigger response (4 variants)

`SyncTriggerResult.body()` already produces the right dict per status. The
FastAPI route uses `response_model=SyncTriggerResponse` where
`SyncTriggerResponse` is a discriminated union:

```python
class SyncTriggerScheduledResponse(BaseModel):
    status: Literal["scheduled"]


class SyncTriggerSkippedResponse(BaseModel):
    status: Literal["skipped"]
    manual_mode: bool
    reason: str


class SyncTriggerUnavailableResponse(BaseModel):
    error: str
    reason: str | None = None


class SyncTriggerFailedResponse(BaseModel):
    error: str


SyncTriggerResponse = SyncTriggerScheduledResponse | SyncTriggerSkippedResponse | SyncTriggerUnavailableResponse | SyncTriggerFailedResponse
```

The route function returns `JSONResponse(status_code=result.http_status, content=result.body())`. (FR-009 allows JSONResponse because it is the model-equivalent return — alternatively, we declare `response_model=SyncTriggerResponse` and return the dict, letting FastAPI build the JSONResponse. The architectural test for handler purity treats `JSONResponse` as a borderline case; the implementation uses `response_model=` + dict-return so handlers stay pure.)

## Diagnostics, charter, dossier — model hierarchy mirrors existing TypedDicts

| Model | Source TypedDict | Notes |
|-------|------------------|-------|
| `DiagnosticsResponse` | `DiagnosticsResponse` (api_types.py) | full field list copied |
| `CharterResponse` | n/a (legacy returns `text/plain`) | route returns `PlainTextResponse`; no Pydantic model required |
| `DossierOverviewResponse` | `DossierOverviewResponse` | exists; copied |
| `DossierArtifactsResponse` | `DossierArtifactsResponse` | exists; copied |
| `DossierArtifactDetailResponse` | `DossierArtifactDetailResponse` | exists; copied |
| `DossierSnapshotExportResponse` | `DossierSnapshotExportResponse` | exists; copied |
| `ArtifactDirectoryResponse` | `ArtifactDirectoryResponse` | exists; copied |
| `ResearchResponse` | `ResearchResponse` | exists; copied |
| `ShutdownResponse` | n/a (legacy returns `{"status": "stopping"}`) | small ad-hoc model |

## Compatibility shim

`src/dashboard/api_types.py` continues to export every TypedDict at its
existing name. Any consumer that imports `from dashboard.api_types import
FeaturesListResponse` still gets the TypedDict (good for type-hinting in
service classes that don't depend on Pydantic). The Pydantic models live
under `dashboard.api.models` to avoid a name collision; both representations
have the same shape, verified by a small adapter test (`test_typeddict_to_pydantic_parity.py`)
that constructs a Pydantic instance from a TypedDict literal and asserts the
serialised JSON matches.

## Model evolution policy

The OpenAPI snapshot test (see `contracts/openapi-stability.md`) is the
runtime gate. The data model is allowed to grow additively — new optional
fields on existing models are permitted within this mission. Field removals,
renames, and type changes are explicitly prohibited (C-004) and require a
separate mission.
