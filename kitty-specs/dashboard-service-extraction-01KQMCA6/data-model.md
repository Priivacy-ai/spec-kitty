# Data Model: Dashboard Service Extraction

*Phase 1 design output for mission `dashboard-service-extraction-01KQMCA6`*

---

## 1. Service Object Boundaries

Three service objects are extracted from the handler layer. Each maps to a
distinct responsibility cluster identified in `research.md`. The fourth
component, `DashboardFileReader`, is a thin I/O helper that stays adjacent to
the adapter layer (per C-006 — file-serving logic does not move to the service
layer).

```
src/dashboard/
├── __init__.py
├── api_types.py                   # TypedDict shapes (moved from specify_cli)
├── file_reader.py                 # DashboardFileReader
└── services/
    ├── __init__.py
    ├── mission_scan.py            # MissionScanService
    ├── project_state.py           # ProjectStateService
    └── sync.py                    # SyncService
```

---

## 2. `MissionScanService`

**File**: `src/dashboard/services/mission_scan.py`

**Responsibility**: Scans all missions in the project directory, resolves the
active mission, assembles the kanban state with weighted progress, and returns
typed response payloads.

**Source methods extracted from**:
- `FeatureHandler.handle_features_list` — scan + active feature + mission context assembly
- `FeatureHandler.handle_kanban` — kanban scan + legacy check + weighted progress

### Interface

```python
class MissionScanService:
    def __init__(self, project_dir: Path) -> None: ...

    def get_features_list(self) -> FeaturesListResponse:
        """Scan all missions and return the full features-list payload.

        Postconditions:
          - Every FeatureItem in `features` carries an `is_legacy` flag.
          - `active_mission` is populated from the resolved active feature;
            falls back to a sentinel MissionContext when none is active.
          - `active_feature_id` is None when no active feature is resolved.
        """

    def get_kanban(self, feature_id: str) -> KanbanResponse:
        """Return kanban lanes and weighted progress for a specific feature.

        Postconditions:
          - `is_legacy` and `upgrade_needed` are derived from the feature
            directory's format detection.
          - `weighted_percentage` is None for legacy features or when the
            event log is unreadable; otherwise rounded to one decimal place.
        """
```

### Dependencies

| Dependency | Module | Usage |
|---|---|---|
| `scan_all_features` | `specify_cli.scanner` | All-feature list scan |
| `resolve_active_feature` | `specify_cli.scanner` | Active feature detection |
| `scan_feature_kanban` | `specify_cli.scanner` | Per-feature kanban lanes |
| `resolve_feature_dir` | `specify_cli.scanner` | Resolve feature directory by slug/id |
| `format_path_for_display` | `specify_cli.scanner` | Path display formatting |
| `get_mission_by_name` | `specify_cli.mission` | Mission config resolution |
| `is_legacy_format` | `specify_cli.legacy_detector` | Legacy format detection |
| `compute_weighted_progress` | `specify_cli.status.progress` | Weighted completion % |
| `materialize` | `specify_cli.status.reducer` | Snapshot from event log |

### State and invariants

- `project_dir` is resolved to an absolute path at construction time.
- `get_features_list` is a pure read; it mutates no disk state.
- `get_kanban` is a pure read; `weighted_percentage` silently degrades to
  `None` on any exception from the status subsystem.
- No HTTP concerns (`request`, `response`, `path`, status codes) appear in
  this service object.

---

## 3. `ProjectStateService`

**File**: `src/dashboard/services/project_state.py`

**Responsibility**: Assembles the health response: project path resolution,
sync daemon status query, and optional token injection.

**Source methods extracted from**:
- `APIHandler.handle_health` — project path resolution + daemon status assembly

### Interface

```python
class ProjectStateService:
    def __init__(self, project_dir: Path) -> None: ...

    def get_health(self, token: str | None = None) -> HealthResponse:
        """Return project health payload.

        Postconditions:
          - `status` is always "ok" on the happy path.
          - `project_path` is the resolved absolute path string.
          - `sync` is populated from `get_sync_daemon_status`; on exception
            the block degrades to `{"running": False, "error": "<msg>"}`.
          - `token` is included only when the caller passes a non-None token.
        """
```

### Dependencies

| Dependency | Module | Usage |
|---|---|---|
| `get_sync_daemon_status` | `specify_cli.sync.daemon` | Daemon status probe |

### State and invariants

- `project_dir` is resolved at construction time.
- `get_health` is a pure read; it starts no process and writes no state.
- Daemon status uses a 0.2 s timeout; timeout exceptions are caught and
  result in the degraded `sync` block.
- No HTTP concerns appear in this object.

---

## 4. `SyncService`

**File**: `src/dashboard/services/sync.py`

**Responsibility**: Orchestrates sync daemon startup and issues a trigger
request to the running daemon.

**Source methods extracted from**:
- `APIHandler.handle_sync_trigger` — three-step orchestration:
  1. `ensure_sync_daemon_running`
  2. `get_sync_daemon_status`
  3. Build + send loopback HTTP trigger request

### Interface

```python
@dataclass
class SyncTriggerResult:
    status: str                  # "scheduled" | "skipped" | "unavailable" | "failed"
    http_status: int             # 202, 503, 500
    manual_mode: bool = False    # True when skipped due to policy_manual / rollout_disabled
    reason: str | None = None    # skipped_reason from daemon, error reason on failure
    error: str | None = None     # error key string for JSON serialisation

class SyncService:
    def trigger_sync(self, token: str | None = None) -> SyncTriggerResult:
        """Ensure the daemon is running and ask it to flush soon.

        Preconditions:
          - `token` is the per-project token used to authenticate the trigger
            request to the daemon; may be None when the project has no token.

        Postconditions:
          - Returns SyncTriggerResult with `http_status` 202 on success or skip.
          - Returns 503 when the daemon is unavailable after startup.
          - Returns 500 on unexpected exception.
          - The loopback safety check (localhost/127.0.0.1 only) is enforced
            inside this method, not in the caller.
        """
```

### Dependencies

| Dependency | Module | Usage |
|---|---|---|
| `ensure_sync_daemon_running` | `specify_cli.sync.daemon` | Start daemon if not running |
| `get_sync_daemon_status` | `specify_cli.sync.daemon` | Health check post-start |
| `DaemonIntent.REMOTE_REQUIRED` | `specify_cli.sync.daemon` | Intent signal to daemon |
| `DaemonStartOutcome` | `specify_cli.sync.daemon` | Return type from ensure |

### State and invariants

- `SyncService` holds no mutable state; all orchestration is in `trigger_sync`.
- The URL validation (`http` scheme, `localhost`/`127.0.0.1` hostname only) is
  an invariant enforced before building the trigger request.
- No HTTP server concerns appear in this object; the `urllib.request.Request`
  and `urlopen` are internal implementation details of the trigger, not exposed
  to callers.

---

## 5. `DashboardFileReader` (adapter-adjacent, not in service layer)

**File**: `src/dashboard/file_reader.py`

**Responsibility**: Locates feature-specific files and returns their content
or directory listings. This component performs file I/O only and contains no
business logic — it stays adjacent to the adapter layer per C-006. It is
extracted here to remove the repeated path-resolution and encoding-error
handling pattern from the handler methods.

**Source methods refactored from**:
- `FeatureHandler.handle_research`
- `FeatureHandler._handle_artifact_directory`
- `FeatureHandler.handle_artifact`

### Interface

```python
@dataclass
class FileReadResult:
    content: str | None
    found: bool
    encoding_error: bool = False

@dataclass
class DirectoryListResult:
    files: list[ArtifactDirectoryFile]

class DashboardFileReader:
    def __init__(self, project_dir: Path) -> None: ...

    def read_research(self, feature_id: str) -> ResearchResponse:
        """Return research.md text + artifact listing for a feature."""

    def read_artifact_file(self, feature_id: str, relative_path: str) -> FileReadResult:
        """Read a single file within a feature directory (path-traversal safe)."""

    def read_artifact_directory(
        self, feature_id: str, directory_name: str
    ) -> ArtifactDirectoryResponse:
        """Return a file listing for a named subdirectory (contracts, checklists)."""

    def read_named_artifact(self, feature_id: str, artifact_name: str) -> FileReadResult:
        """Read a well-known artifact (spec, plan, tasks, research, quickstart, data-model)."""
```

---

## 6. Responsibility Allocation Summary

| Route cluster | Stays in adapter | Delegated to |
|---|---|---|
| `GET /` (HTML shell) | `APIHandler.handle_root` | — |
| `GET /api/health` | thin dispatch | `ProjectStateService.get_health` |
| `POST /api/sync/trigger` | thin dispatch + token check | `SyncService.trigger_sync` |
| `GET /api/features` | thin dispatch | `MissionScanService.get_features_list` |
| `GET /api/kanban/{id}` | thin dispatch | `MissionScanService.get_kanban` |
| `GET /api/research/{id}[/{file}]` | thin dispatch | `DashboardFileReader.read_research` / `read_artifact_file` |
| `GET /api/contracts/{id}[/{file}]` | thin dispatch | `DashboardFileReader.read_artifact_directory` / `read_artifact_file` |
| `GET /api/checklists/{id}[/{file}]` | thin dispatch | `DashboardFileReader.read_artifact_directory` / `read_artifact_file` |
| `GET /api/artifact/{id}/{name}` | thin dispatch | `DashboardFileReader.read_named_artifact` |
| `GET /api/diagnostics` | thin dispatch | `specify_cli.diagnostics.run_diagnostics` (not extracted; stays in adapter per C-006) |
| `GET /api/charter` | thin dispatch | `specify_cli.charter_path.resolve_project_charter_path` (not extracted) |
| `GET /api/dossier/*` | thin dispatch + routing | `specify_cli.dossier.api.DossierAPIHandler` (not extracted) |
| Glossary routes | unchanged | `GlossaryHandler` (not in extraction scope) |
| `GET /api/charter-lint` | unchanged | `LintTileHandler` (not in extraction scope) |
| `GET /static/*` | unchanged | `StaticHandler` (not in extraction scope) |
| `POST /api/shutdown` | unchanged | token-validated shutdown (stays in adapter) |

---

## 7. `api_types.py` Relocation

`api_types.py` moves from `src/specify_cli/dashboard/api_types.py` to
`src/dashboard/api_types.py`. The old path becomes a shim:

```python
# src/specify_cli/dashboard/api_types.py  (shim — removal_release: FastAPI milestone)
from dashboard.api_types import *  # noqa: F401, F403
```

All existing imports in `src/specify_cli/` resolve through the shim
transparently. No shape or field name changes (C-002 frozen).

### Type inventory (unchanged)

| Type | Used by |
|---|---|
| `HealthResponse`, `SyncInfo` | `ProjectStateService`, `APIHandler` |
| `FeaturesListResponse`, `FeatureItem`, `MissionContext`, `WorkflowStatus`, `WorktreeInfo`, `KanbanStats`, `ArtifactInfo` | `MissionScanService`, `FeatureHandler` |
| `KanbanResponse`, `KanbanTaskData` | `MissionScanService`, `FeatureHandler` |
| `ResearchResponse`, `ResearchArtifact` | `DashboardFileReader`, `FeatureHandler` |
| `ArtifactDirectoryResponse`, `ArtifactDirectoryFile` | `DashboardFileReader`, `FeatureHandler` |
| `SyncTriggerSuccess` | `SyncService`, `APIHandler` |
| `DiagnosticsResponse` (+ nested) | `APIHandler` (diagnostics not extracted) |
| `GlossaryHealthResponse`, `GlossaryTermRecord` | `GlossaryHandler` |
| `DecayWatchTileResponse` | `LintTileHandler` |
| `ErrorResponse` | all handlers (error path) |
| `MissionRecord` | `MissionScanService` (scanner internal) |

---

## 8. Seam Contract

Each route has exactly one seam — the single call from adapter to service
object. The seam tests (`tests/test_dashboard/test_seams.py`) exercise the
adapter through its HTTP interface and assert the service object returns the
expected typed response.

```
┌──────────────────────────────────┐
│  BaseHTTPRequestHandler (stdlib) │
│  DashboardRouter (MRO dispatch)  │
│  ─── SEAM ───────────────────── │
│  FeatureHandler / APIHandler /   │  ← adapter layer (specify_cli)
│  GlossaryHandler / LintTile...   │
└──────────────┬───────────────────┘
               │ single typed call per route
               ▼
┌──────────────────────────────────┐
│  MissionScanService              │
│  ProjectStateService             │  ← service layer (src/dashboard/)
│  SyncService                     │
│  DashboardFileReader             │
└──────────────────────────────────┘
```

No HTTP-layer symbols (`BaseHTTPRequestHandler`, status codes, `send_response`,
`wfile`) cross the seam boundary. The adapter is responsible for all HTTP I/O;
service objects receive plain Python types and return TypedDicts.
