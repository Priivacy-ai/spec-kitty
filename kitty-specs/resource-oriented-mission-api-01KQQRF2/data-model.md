# Data Model: Resource-Oriented Mission API and HATEOAS-LITE

**Mission**: `resource-oriented-mission-api-01KQQRF2`
**Date**: 2026-05-03

## Layer Boundary

```
Transport (FastAPI routers)
    │  calls get_mission_registry() Depends
    ▼
Service Layer (MissionRegistry / WorkPackageRegistry)
    │  returns frozen dataclasses (MissionRecord, WorkPackageRecord)
    ▼
Pydantic response models (ResourceModel subclasses)
    │  serialized to JSON with _links
    ▼
HTTP response body
```

Registry records are **transport-agnostic frozen dataclasses** (`registry.py`). Pydantic response models are **transport-facing serialization shapes** (`models.py`). The mapping between them is done in the router layer. Neither layer imports from the other.

---

## Registry Record Extensions (src/dashboard/services/registry.py)

### WorkPackageRecord — new fields

Two fields added to the existing frozen dataclass. All other fields unchanged.

```python
@dataclass(frozen=True)
class WorkPackageRecord:
    # ... existing fields ...
    claimed_at: datetime | None       # NEW — timestamp of most recent →claimed event; None if never claimed
    blocked_reason: str | None        # NEW — reason from most recent →blocked event; None otherwise
```

**Population logic** (inside registry scan):
- `claimed_at`: scan `status.events.jsonl` for events with `to_lane == "claimed"`, take the `at` field of the most recent such event.
- `blocked_reason`: scan events for `to_lane == "blocked"`, take the `reason` field of the most recent such event.
- Both fields are `None` for legacy missions (no `status.events.jsonl`).

---

## New Pydantic Response Models (src/dashboard/api/models.py)

All new resource models inherit from `ResourceModel` and declare `_links: dict[str, Link]`.

### Link (pre-existing)

```python
class Link(BaseModel):
    href: str  # server-relative path, e.g. "/api/missions/01KQQRF2..."
```

### ResourceModel (pre-existing, vacuous arch test activated by WP01)

```python
class ResourceModel(BaseModel):
    _links: dict[str, Link] = Field(default_factory=dict, alias="_links")
    model_config = ConfigDict(populate_by_name=True, ser_alias="_links")
```

### ReviewEvidence (new)

```python
class ReviewEvidence(BaseModel):
    reviewed_by: str
    reviewed_at: datetime
    verdict: Literal["approved", "rejected"]
    notes: str | None = None
```

**Population**: Populated from the most recent `in_review → approved` or `in_review → rejected` event in `status.events.jsonl`. Only present when `lane` is `in_review`, `approved`, or `done`.

### WorkPackageAssignment (new)

```python
class WorkPackageAssignment(BaseModel):
    wp_id: str
    lane: str
    assignee: str | None = None
    agent_profile: str | None = None
    role: str | None = None
    claimed_at: datetime | None = None
    last_event_id: str | None = None
    blocked_reason: str | None = None
    review_evidence: ReviewEvidence | None = None
```

**Built from**: `WorkPackageRecord` fields. `review_evidence` is built by the router from event-log data (router calls a thin helper or reads from a derived registry field).

### MissionSummary (new — list endpoint payload)

```python
class MissionSummary(ResourceModel):
    mission_id: str
    mission_slug: str
    mission_number: int | None = None
    mid8: str
    friendly_name: str
    mission_type: str
    target_branch: str
    lane_counts: LaneCounts       # pre-existing model
    weighted_percentage: float | None = None
    is_legacy: bool
    _links: dict[str, Link]       # keys: self, status, workpackages
```

### Mission (new — detail endpoint payload)

```python
class Mission(ResourceModel):
    mission_id: str
    mission_slug: str
    mission_number: int | None = None
    mid8: str
    friendly_name: str
    mission_type: str
    target_branch: str
    created_at: datetime | None = None
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    is_legacy: bool
    _links: dict[str, Link]       # keys: self, status, workpackages
```

### MissionStatus (new — status sub-resource)

```python
class MissionStatus(ResourceModel):
    mission_id: str
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    done_count: int
    total_count: int
    current_phase: int
    _links: dict[str, Link]       # keys: self, mission
```

### WorkPackageSummary (new — WP list payload)

```python
class WorkPackageSummary(ResourceModel):
    wp_id: str
    title: str
    assignment: WorkPackageAssignment
    _links: dict[str, Link]       # keys: self, mission
```

### WorkPackage (new — WP detail payload)

```python
class WorkPackage(ResourceModel):
    wp_id: str
    title: str
    assignment: WorkPackageAssignment
    subtasks_done: int
    subtasks_total: int
    dependencies: list[str]
    requirement_refs: list[str]
    prompt_ref: str | None = None   # relative path to WP*.md prompt file, if exists
    _links: dict[str, Link]         # keys: self, mission, workpackages
```

---

## URL and _links Shape Reference

| Endpoint | Response model | `_links` keys | href pattern |
|----------|---------------|---------------|--------------|
| `GET /api/missions` | `list[MissionSummary]` | `self`, `status`, `workpackages` per item | `/api/missions/{mission_id}`, `/api/missions/{mission_id}/status`, `/api/missions/{mission_id}/workpackages` |
| `GET /api/missions/{id}` | `Mission` | `self`, `status`, `workpackages` | same as above |
| `GET /api/missions/{id}/status` | `MissionStatus` | `self`, `mission` | `/api/missions/{mission_id}/status`, `/api/missions/{mission_id}` |
| `GET /api/missions/{id}/workpackages` | `list[WorkPackageSummary]` | `self`, `mission` per item | `/api/missions/{mission_id}/workpackages/{wp_id}`, `/api/missions/{mission_id}` |
| `GET /api/missions/{id}/workpackages/{wp_id}` | `WorkPackage` | `self`, `mission`, `workpackages` | `/api/missions/{mission_id}/workpackages/{wp_id}`, `/api/missions/{mission_id}`, `/api/missions/{mission_id}/workpackages` |

All hrefs use the canonical `mission_id` (ULID), never `mid8` or `mission_slug`, so links are stable regardless of how the resource was fetched.

---

## Invariants

1. `ResourceModel` subclasses always have a non-empty `_links` dict. The arch test `test_resource_models_have_links.py` enforces this.
2. `_links` hrefs are server-relative paths. Never absolute URLs.
3. `WorkPackageAssignment.lane` is the current lane from the registry; it is consistent with `MissionStatus.lane_counts`.
4. `review_evidence` is non-null only for lanes `in_review`, `approved`, `done`.
5. `claimed_at` is non-null only for lanes `claimed`, `in_progress`, `for_review`, `in_review`, `approved`, `done` (i.e., any lane reachable after claiming).
6. The `{id}` path parameter resolves via `registry.get_mission()`: `mission_id` → `mid8` → `mission_slug`. Ambiguous `mid8` returns HTTP 409; not found returns HTTP 404.
