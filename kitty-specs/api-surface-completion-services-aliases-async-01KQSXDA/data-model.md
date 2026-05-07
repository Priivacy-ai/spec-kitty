# Data Model — api-surface-completion-services-aliases-async

Mission: `api-surface-completion-services-aliases-async-01KQSXDA`

---

## 1. `src/specify_cli/glossary/types.py` (FR-016)

These TypedDicts move from `src/dashboard/api_types.py` → `specify_cli/glossary/types.py`.
The file does not yet exist and must be created.

```python
from __future__ import annotations

from typing import NotRequired, TypedDict


class GlossaryTermRecord(TypedDict):
    """Single glossary term returned by ``GET /api/glossary-terms``.

    Canonical home: specify_cli/glossary/types.py (FR-016).
    """

    surface: str          # normalised surface text of the term
    definition: str       # definition prose (empty string if not set)
    status: str           # "active" | "draft" | "deprecated"
    confidence: float     # 0.0–1.0


class GlossaryHealthResponse(TypedDict, total=False):
    """Response from ``GET /api/glossary-health``.

    Canonical home: specify_cli/glossary/types.py (FR-016).
    total=False: all keys are optional to allow partial/empty responses
    when glossary data is unavailable.
    """

    total_terms: int
    active_count: int
    draft_count: int
    deprecated_count: int
    high_severity_drift_count: int
    orphaned_term_count: int
    entity_pages_generated: bool
    entity_pages_path: str | None
    last_conflict_at: str | None   # ISO-8601 timestamp or None
```

---

## 2. `src/specify_cli/charter_lint/types.py` (FR-017)

New file. Does not yet exist.

```python
from __future__ import annotations

from typing import TypedDict


class DecayWatchTileResponse(TypedDict, total=False):
    """Response from ``GET /api/charter-lint``.

    Canonical home: specify_cli/charter_lint/types.py (FR-017).
    Populated by reading .kittify/lint-report.json.
    total=False: all keys are optional to represent the "no data" variant
    where the lint report file does not yet exist.
    """

    has_data: bool
    scanned_at: str | None        # ISO-8601 timestamp or None
    orphan_count: int
    contradiction_count: int
    staleness_count: int
    reference_integrity_count: int
    high_severity_count: int      # findings with severity "high" or "critical"
    total_count: int
    feature_scope: str | None     # mission slug scoped to, or None
    duration_seconds: float | None
```

---

## 3. `src/kernel/api_types.py` — Cross-cutting types

`src/kernel/` already exists as a package. Only `src/kernel/api_types.py` needs to be added.

TypedDicts moved here have no single domain owner — they are used by infrastructure endpoints (health, diagnostics, sync) or are generic error envelopes.

```python
from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class ErrorResponse(TypedDict):
    """Generic error envelope returned on failure paths."""

    error: str
    detail: NotRequired[str]
    status: NotRequired[int]


class SyncInfo(TypedDict, total=False):
    """Nested sync block inside HealthResponse."""

    running: bool
    last_sync: str | None
    consecutive_failures: int
    error: str


class HealthResponse(TypedDict, total=False):
    """Response from ``GET /api/health``."""

    status: str
    project_path: str
    sync: SyncInfo
    websocket_status: str
    token: str


class SyncTriggerSuccess(TypedDict):
    """Successful response from ``POST /api/sync/trigger``."""

    status: str   # "scheduled"


class FileIntegrity(TypedDict):
    """File-integrity section of the diagnostics response."""

    total_expected: int
    total_present: int
    total_missing: int
    missing_files: list[str]


class DiagnosticsFeatureStatus(TypedDict):
    """Per-feature status record in diagnostics all_features list."""

    name: str
    state: str
    branch_exists: bool
    branch_merged: bool
    worktree_exists: bool
    worktree_path: str | None
    artifacts_in_main: bool
    artifacts_in_worktree: bool


class CurrentFeatureDetected(TypedDict):
    """current_feature block when detection succeeds."""

    detected: bool   # always True
    name: str
    state: str
    branch_exists: bool
    branch_merged: bool
    worktree_exists: bool
    worktree_path: str | None
    artifacts_in_main: bool
    artifacts_in_worktree: bool


class CurrentFeatureNotDetected(TypedDict):
    """current_feature block when detection fails."""

    detected: bool   # always False
    error: str


class DashboardHealthInfo(TypedDict, total=False):
    """Dashboard health section of the diagnostics response."""

    metadata_exists: bool
    can_start: bool | None
    startup_test: str | None
    url: str
    port: int
    pid: int | None
    has_pid: bool
    responding: bool
    parse_error: str
    test_url: str
    test_port: int
    startup_error: str


class DiagnosticsResponse(TypedDict):
    """Response from ``GET /api/diagnostics``."""

    project_path: str
    current_working_directory: str
    git_branch: str | None
    in_worktree: bool
    worktrees_exist: bool
    active_mission: str | None
    file_integrity: FileIntegrity
    worktree_overview: dict[str, Any]
    current_feature: CurrentFeatureDetected | CurrentFeatureNotDetected
    all_features: list[DiagnosticsFeatureStatus]
    dashboard_health: DashboardHealthInfo
    observations: list[str]
    issues: list[str]


class DiagnosticsErrorResponse(TypedDict):
    """Error variant of the diagnostics response (HTTP 500)."""

    error: str
    traceback: str
```

---

## 4. `src/specify_cli/status/api_types.py` — WP/Kanban status domain

New file. Does not yet exist.

```python
from __future__ import annotations

from typing import Any, TypedDict


class KanbanTaskData(TypedDict, total=False):
    """Single work-package card on the kanban board."""

    id: str
    title: str
    lane: str
    subtasks: list[Any]
    agent: str
    model: str
    agent_profile: str
    role: str
    assignee: str
    phase: str
    prompt_markdown: str
    prompt_path: str
    encoding_error: bool   # present only on decode-failure variant


class KanbanStats(TypedDict, total=False):
    """Per-feature kanban summary counts.

    ``error`` is present only when the event log is missing or unreadable.
    """

    total: int
    planned: int
    doing: int
    for_review: int
    approved: int
    done: int
    error: str


class KanbanResponse(TypedDict):
    """Response from ``GET /api/kanban/{feature_id}`` (deprecated alias)."""

    lanes: dict[str, list[KanbanTaskData]]
    is_legacy: bool
    upgrade_needed: bool
    weighted_percentage: float | None
```

---

## 5. `src/specify_cli/missions/api_types.py` — Mission management domain

New file. Does not yet exist.

```python
from __future__ import annotations

from typing import Any, TypedDict

from specify_cli.status.api_types import KanbanStats   # cross-domain reference allowed


class ArtifactInfo(TypedDict):
    """Per-artifact existence / stat metadata produced by the mission scanner."""

    exists: bool
    mtime: float | None
    size: int | None


class WorktreeInfo(TypedDict):
    """Per-feature worktree metadata."""

    path: str | None
    exists: bool


class WorkflowStatus(TypedDict):
    """Workflow progression status (specify → plan → tasks → implement)."""

    specify: str
    plan: str
    tasks: str
    implement: str


class FeatureItem(TypedDict):
    """Single feature/mission entry produced by the mission scanner."""

    id: str
    name: str
    display_name: str
    path: str
    artifacts: dict[str, ArtifactInfo]
    workflow: WorkflowStatus
    kanban_stats: KanbanStats
    meta: dict[str, Any]
    worktree: WorktreeInfo
    is_legacy: bool


class MissionContext(TypedDict, total=False):
    """Active mission context block in the features-list response.

    ``feature`` is absent when no active feature is detected.
    """

    name: str
    domain: str
    version: str
    slug: str
    description: str
    path: str | None
    feature: str


class FeaturesListResponse(TypedDict):
    """Response from deprecated ``GET /api/features``."""

    features: list[FeatureItem]
    active_feature_id: str | None
    project_path: str | None
    worktrees_root: str | None
    active_worktree: str | None
    active_mission: MissionContext


class FeaturesListErrorResponse(TypedDict):
    """Error variant of the features-list response (HTTP 500)."""

    error: str
    detail: str


class MissionRecord(TypedDict, total=False):
    """Single mission record from the mission registry.

    Keyed by mission_id (ULID) or pseudo-key (``legacy:<slug>`` / ``orphan:<name>``).
    """

    mission_id: str          # ULID or pseudo-key
    mission_slug: str        # directory name
    display_number: int | None
    mid8: str | None         # first 8 chars of mission_id
    feature_dir: str         # absolute path as string


class ResearchArtifact(TypedDict):
    """Single artifact entry in the research response."""

    name: str
    path: str
    icon: str


class ResearchResponse(TypedDict):
    """Response from ``GET /api/research/{feature_id}``."""

    main_file: str | None
    artifacts: list[ResearchArtifact]
```

---

## 6. `src/dashboard/api/presentation_types.py` — Dashboard-presentation-only

New file. Contains only types that are unambiguously specific to the dashboard file-browser UI.

```python
from __future__ import annotations

from typing import TypedDict


class ArtifactDirectoryFile(TypedDict):
    """Single file entry in a contracts or checklists artifact directory listing."""

    name: str
    path: str
    icon: str


class ArtifactDirectoryResponse(TypedDict):
    """Response from ``/api/contracts/{id}`` and ``/api/checklists/{id}``."""

    files: list[ArtifactDirectoryFile]
```

**Justification:** Both types are consumed exclusively by the file-browser endpoints (`/api/contracts/{id}`, `/api/checklists/{id}`, and `GET /api/artifact/{feature_id}/{name}`). No equivalent concept exists outside the dashboard UI. They have no meaningful domain model in `specify_cli`, `status`, `missions`, or `kernel`.

---

## 7. SSE Event Payload Schema (FR-009–FR-011)

### `connected` event

Sent immediately on connection establishment.

```
event: connected
data: {"version": "1", "ts": "2026-07-01T12:00:00+00:00"}
id: <server-generated-ulid>

```

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | Protocol version, always `"1"` for this mission |
| `ts` | `str` | ISO-8601 server timestamp at connection time |

### `mission_status` event

Emitted when a `StatusEvent` is appended to any mission's `status.events.jsonl` that the server is watching.

```
event: mission_status
data: {"mission_id": "01J6XW9K...", "mission_slug": "083-my-mission", "wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress", "actor": "claude", "at": "2026-07-01T12:01:00+00:00", "event_id": "01KQSXDA..."}
id: 01KQSXDA...

```

TypedDict for the `mission_status` data payload:

```python
class MissionStatusEventPayload(TypedDict):
    """JSON payload for the ``mission_status`` SSE event."""

    mission_id: str          # ULID (canonical identity)
    mission_slug: str        # human slug (display)
    wp_id: str               # e.g. "WP01"
    from_lane: str           # source lane value
    to_lane: str             # target lane value
    actor: str               # agent/user that triggered the transition
    at: str                  # ISO-8601 timestamp from StatusEvent
    event_id: str            # ULID — also used as the SSE ``id:`` field
```

The SSE `id:` field is set to `StatusEvent.event_id` so that `Last-Event-ID` resumption maps 1:1 to event log entries.

### Keepalive comment

```
: keepalive

```

Sent every 15 seconds when no real events have been dispatched. Comments are not delivered to `onmessage` handlers; they only reset the browser reconnect timer.

### Wire format example (full session)

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no

event: connected
data: {"version": "1", "ts": "2026-07-01T12:00:00+00:00"}
id: 01KQSXDAAAAAAAAAAAAAAAAAA

event: mission_status
data: {"mission_id": "01J6XW9KABCDE01234567890AB", "mission_slug": "083-my-mission", "wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress", "actor": "claude", "at": "2026-07-01T12:01:00+00:00", "event_id": "01KQSXDB0000000000000000AB"}
id: 01KQSXDB0000000000000000AB

: keepalive

: keepalive

event: mission_status
data: {"mission_id": "01J6XW9KABCDE01234567890AB", "mission_slug": "083-my-mission", "wp_id": "WP01", "from_lane": "in_progress", "to_lane": "for_review", "actor": "claude", "at": "2026-07-01T12:02:00+00:00", "event_id": "01KQSXDC0000000000000000CD"}
id: 01KQSXDC0000000000000000CD
```

---

## 8. `GlossaryService` Interface

```python
# src/specify_cli/glossary/service.py

from __future__ import annotations

from pathlib import Path

from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord


class GlossaryService:
    """Read-only domain service for glossary data.

    Constraints (C-003, C-005):
    - Must not import fastapi, starlette, or pydantic.
    - All return types are plain TypedDicts or built-in Python types.
    """

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def get_health(self) -> GlossaryHealthResponse:
        """Aggregate glossary health metrics across all scopes.

        Returns an empty-count GlossaryHealthResponse on any error rather
        than raising. The router layer logs and swallows domain exceptions.
        """
        ...

    def get_terms(self) -> list[GlossaryTermRecord]:
        """Return all glossary terms across all scopes as GlossaryTermRecord dicts.

        Returns empty list on any error.
        """
        ...
```

---

## 9. `LintService` Interface

```python
# src/specify_cli/charter_lint/service.py

from __future__ import annotations

from pathlib import Path

from specify_cli.charter_lint.types import DecayWatchTileResponse


class LintService:
    """Read-only domain service for charter-lint tile data.

    Constraints (C-003, C-005):
    - Must not import fastapi, starlette, or pydantic.
    - Return type is a plain TypedDict.
    """

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def get_decay_tile(self) -> DecayWatchTileResponse:
        """Read .kittify/lint-report.json and return the decay tile payload.

        Returns the zero-count empty DecayWatchTileResponse when the file is
        absent or unreadable. Never raises.
        """
        ...
```

---

## 10. Pydantic Model Alignment Notes (FR-018)

`src/dashboard/api/models.py` Pydantic classes mirror the TypedDicts. After the TypedDict migration, the import paths in `models.py` must be updated to point to the new canonical locations. The Pydantic class definitions themselves do **not** change — only their import dependencies.

| Pydantic class in `models.py` | Current TypedDict source | New TypedDict source |
|-------------------------------|--------------------------|----------------------|
| `GlossaryTermRecord` | `dashboard.api_types` | `specify_cli.glossary.types` |
| `GlossaryHealthResponse` | `dashboard.api_types` | `specify_cli.glossary.types` |
| `DecayWatchTileResponse` | `dashboard.api_types` | `specify_cli.charter_lint.types` |
| `ErrorResponse` | `dashboard.api_types` | `kernel.api_types` |
| `SyncInfo` | `dashboard.api_types` | `kernel.api_types` |
| `HealthResponse` | `dashboard.api_types` | `kernel.api_types` |
| `KanbanTaskData` | `dashboard.api_types` | `specify_cli.status.api_types` |
| `KanbanStats` | `dashboard.api_types` | `specify_cli.status.api_types` |
| `KanbanResponse` | `dashboard.api_types` | `specify_cli.status.api_types` |
| `MissionRecord` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `WorktreeInfo` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `WorkflowStatus` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `FeatureItem` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `MissionContext` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `FeaturesListResponse` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `FeaturesListErrorResponse` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `ResearchArtifact` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `ResearchResponse` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `ArtifactInfo` | `dashboard.api_types` | `specify_cli.missions.api_types` |
| `FileIntegrity` | `dashboard.api_types` | `kernel.api_types` |
| `DiagnosticsFeatureStatus` | `dashboard.api_types` | `kernel.api_types` |
| `CurrentFeatureDetected` | `dashboard.api_types` | `kernel.api_types` |
| `CurrentFeatureNotDetected` | `dashboard.api_types` | `kernel.api_types` |
| `DashboardHealthInfo` | `dashboard.api_types` | `kernel.api_types` |
| `DiagnosticsResponse` | `dashboard.api_types` | `kernel.api_types` |
| `DiagnosticsErrorResponse` | `dashboard.api_types` | `kernel.api_types` |
| `SyncTriggerSuccess` | `dashboard.api_types` | `kernel.api_types` |
| `ArtifactDirectoryFile` | `dashboard.api_types` | `dashboard.api.presentation_types` |
| `ArtifactDirectoryResponse` | `dashboard.api_types` | `dashboard.api.presentation_types` |

**Note on `SyncTriggerSuccess`:** The Pydantic models file uses a discriminated union (`SyncTriggerScheduledResponse`, `SyncTriggerSkippedResponse`, etc.) that supersedes the simple `SyncTriggerSuccess` TypedDict. The TypedDict moves to `kernel/api_types.py`; the Pydantic discriminated-union classes stay in `models.py` unchanged.

**FR-018 constraint:** The field names and types of the Pydantic models must stay identical to the TypedDicts. The models use `ConfigDict(extra="allow")` to tolerate scanner evolution; this must be preserved.

**Dependency direction (C-009):** `dashboard/api → domain (specify_cli/*, kernel) → never reversed`. `models.py` is allowed to import from `specify_cli.glossary.types`, `specify_cli.charter_lint.types`, `kernel.api_types`, etc. The reverse is prohibited.
