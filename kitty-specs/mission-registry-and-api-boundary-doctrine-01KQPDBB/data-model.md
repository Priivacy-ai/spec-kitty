# Data Model — Mission Registry and API Boundary Doctrine

The registry layer introduces three Python types — two public records and one private cache primitive — plus two registry classes that own the cache and the public methods. The records are Pydantic-free `dataclass` types: the registry is the **service layer**; the FastAPI Pydantic models in `src/dashboard/api/models.py` belong to the **transport layer** and are mapped from these records by the routers.

This separation matters: the records are stable internal Python contracts that CLI / MCP / future SDK consumers can depend on without pulling Pydantic. The Pydantic models are the wire shape for HTTP consumers only.

## `MissionRecord`

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass(frozen=True)
class MissionRecord:
    """One mission's identity + summary state. Immutable snapshot from the cache."""
    mission_id: str               # ULID, canonical identity
    mission_slug: str             # human-readable directory name
    display_number: int | None    # numeric prefix for display sort; None pre-merge
    mid8: str                     # first 8 chars of mission_id
    feature_dir: Path             # absolute path to kitty-specs/<slug>/
    friendly_name: str            # title from meta.json
    mission_type: str             # software-dev, research, etc.
    target_branch: str            # branch the mission lands on
    created_at: datetime          # from meta.json
    lane_counts: LaneCounts       # see below
    weighted_percentage: float | None  # progress.compute_weighted_progress(); None for legacy missions
    is_legacy: bool               # missions without status.events.jsonl
```

## `WorkPackageRecord`

```python
@dataclass(frozen=True)
class WorkPackageRecord:
    """One WP's identity + assignment + lane state. Immutable snapshot."""
    wp_id: str                    # "WP01"
    title: str
    lane: str                     # planned | claimed | in_progress | for_review | in_review | approved | done | blocked | canceled
    subtasks_done: int
    subtasks_total: int
    agent: str | None             # e.g. "claude:opus-4-7"
    agent_profile: str | None     # e.g. "python-pedro"
    role: str | None              # e.g. "implementer"
    assignee: str | None          # free-form; usually equals `agent`
    phase: str | None             # mission phase the WP belongs to
    prompt_path: Path             # absolute path to tasks/WP##-*.md
    dependencies: tuple[str, ...] # other WP IDs this one depends on
    requirement_refs: tuple[str, ...]   # FR / NFR / SC references from frontmatter
    last_event_id: str | None     # most recent status.events.jsonl entry
    last_event_at: datetime | None
```

## `LaneCounts` — value object

```python
@dataclass(frozen=True)
class LaneCounts:
    total: int
    planned: int
    claimed: int
    in_progress: int
    for_review: int
    in_review: int
    approved: int
    done: int
    blocked: int
    canceled: int
```

## `CacheEntry` — private

```python
from typing import Generic, TypeVar
T = TypeVar("T")

@dataclass(frozen=True)
class CacheEntry(Generic[T]):
    value: T
    cache_key: tuple[int, int, str]   # (mtime_ns, total_size, sorted_dirent_names_hash)
    cached_at: datetime
```

## `MissionRegistry` — public service-layer interface

```python
class MissionRegistry:
    """Single sanctioned reader for mission-level data.

    Per DIRECTIVE_API_DEPENDENCY_DIRECTION (introduced by this mission), no
    transport-side module (FastAPI router, CLI command body, MCP tool) may
    import from `specify_cli.dashboard.scanner` directly. They go through
    this class instead.
    """

    def __init__(self, project_dir: Path) -> None: ...

    def list_missions(self) -> list[MissionRecord]:
        """Return every mission under kitty-specs/ in display order."""

    def get_mission(self, mission_id_or_slug: str) -> MissionRecord | None:
        """Resolve a mission by mission_id (ULID), mid8 (8-char prefix), or
        mission_slug. Returns None on miss; never raises.
        """

    def workpackages_for(self, mission_id_or_slug: str) -> "WorkPackageRegistry":
        """Return a WorkPackageRegistry scoped to one mission. The returned
        registry has its own cache; mission-level mtime changes do not
        invalidate WP-level cache entries unless the WP files actually changed.
        """

    def invalidate_all(self) -> None:
        """Force a full cache flush. For test use; production consumers should
        rely on mtime-based invalidation."""
```

## `WorkPackageRegistry` — public service-layer interface

```python
class WorkPackageRegistry:
    """Per-mission WP reader. Constructed via MissionRegistry.workpackages_for(...)."""

    def list_work_packages(self) -> list[WorkPackageRecord]: ...

    def get_work_package(self, wp_id: str) -> WorkPackageRecord | None:
        """Returns None on miss; never raises."""

    def lane_counts(self) -> LaneCounts:
        """Aggregate lane counts across all WPs in this mission. This is the
        same data that appears in MissionRecord.lane_counts but accessed via
        the WP-scoped cache (cheaper if the caller already has a
        WorkPackageRegistry handle)."""
```

## `ResourceModel` — Pydantic marker (transport layer)

```python
# src/dashboard/api/models.py
from pydantic import BaseModel

class Link(BaseModel):
    href: str
    method: str = "GET"

class ResourceModel(BaseModel):
    """Marker base class. Subclasses MUST declare a `_links` field of type
    `dict[str, Link]`. Enforced by tests/architectural/test_resource_models_have_links.py.

    No actual subclass exists in this mission (per spec C-006); the marker
    lands here so mission B (resource-oriented endpoints) can subclass it.
    """
    pass
```

## Invariants

- **`MissionRecord` and `WorkPackageRecord` are immutable** (`frozen=True`). A consumer that holds a record after a mtime change still sees the snapshot from the cache time. This is intentional — protecting against TOCTOU between a registry read and a follow-up access.
- **The cache key is content-aware enough to catch identical-mtime drift** (R-1 in research.md). The `dirent_names_hash` covers file additions/removals; `file_size` covers same-mtime rewrites that change content length.
- **`get_mission` and `get_work_package` never raise on miss.** Callers handle `None`. This is the FastAPI `HTTPException(404)` boundary, not a registry exception.
- **Mtime-based invalidation is poll-on-read.** No background thread. No TTL. Each public method begins with a stat-call; cache miss triggers re-scan; cache hit returns the snapshot.
- **Cache scope is per-mission for WPs, project-global for the mission list.** A change to one mission's `tasks/` does not invalidate other missions' WP caches.

## State transitions

The registry itself has no state machine — it is read-only on the filesystem and write-only on the cache. The records it returns reflect the lane state from `status.events.jsonl`'s reducer (already documented in `CLAUDE.md` § "Status Model Patterns"). The registry does not duplicate that state machine; it consumes its output.

## Externally visible events

None. The registry is read-only. Future async-update transport (Step 6 of epic #645) will introduce a publish-on-invalidate mechanism, but this mission does not.
