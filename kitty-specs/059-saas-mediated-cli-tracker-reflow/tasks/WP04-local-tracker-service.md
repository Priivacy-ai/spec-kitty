---
work_package_id: WP04
title: LocalTrackerService
dependencies: []
requirement_refs:
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 0ec9cb101d757e8411eb21e82ed90744ca8c4196
created_at: '2026-03-30T19:39:08.173782+00:00'
subtasks: [T017, T018, T019, T020, T021]
shell_pid: "49505"
agent: "orchestrator"
history:
- at: '2026-03-30T19:14:19+00:00'
  event: created
  actor: planner
authoritative_surface: src/specify_cli/tracker/local_service.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/tracker/local_service.py
- tests/sync/tracker/test_local_service.py
---

# WP04: LocalTrackerService

## Objective

Extract beads/fp direct-connector logic from the current `TrackerService` (in `service.py`) into a new `LocalTrackerService` class in `src/specify_cli/tracker/local_service.py`. This is a **mechanical extraction** — move existing working code, not a rewrite. The goal is to isolate the local execution path so it doesn't contaminate the SaaS path.

## Context

- The current `TrackerService` in `service.py` handles ALL providers. After this WP, it will only handle beads/fp.
- All the direct-connector infrastructure (`build_connector`, `TrackerSqliteStore`, `TrackerCredentialStore`, `SyncEngine`) stays intact — just moved into this class.
- The existing `test_credentials.py` (2,000 lines) and `test_store.py` (3,120 lines) must continue passing after this extraction.
- Do NOT touch `service.py` in this WP — that's WP05's job. Instead, create the new class by copying relevant methods.

## Implementation Command

```bash
spec-kitty implement WP04 --base WP02
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Depends on WP02 (config model). Can run in parallel with WP03 (SaaS service).

---

## Subtask T017: Create LocalTrackerService Class Skeleton

**Purpose**: Define the class with the same method surface as the current `TrackerService` for local operations.

**Steps**:

1. Create `src/specify_cli/tracker/local_service.py`
2. Define `LocalTrackerService`:
   ```python
   class LocalTrackerService:
       def __init__(self, repo_root: Path, config: TrackerProjectConfig) -> None:
           self._repo_root = repo_root
           self._config = config
   ```

3. Import the same dependencies that `service.py` currently uses for local operations:
   ```python
   from specify_cli.tracker.config import TrackerProjectConfig, save_tracker_config, clear_tracker_config, load_tracker_config
   from specify_cli.tracker.credentials import TrackerCredentialStore
   from specify_cli.tracker.factory import build_connector, normalize_provider
   from specify_cli.tracker.store import TrackerSqliteStore, default_tracker_db_path
   ```

**Files**: `src/specify_cli/tracker/local_service.py` (new, ~20 lines skeleton)

---

## Subtask T018: Extract bind/unbind

**Purpose**: Move bind and unbind logic for local providers from current TrackerService.

**Steps**:

1. **bind(provider, workspace, doctrine_mode, doctrine_field_owners, credentials) -> TrackerProjectConfig**:
   - Copy the existing `TrackerService.bind()` method logic
   - Normalize provider name
   - Create `TrackerProjectConfig(provider=provider, workspace=workspace, ...)`
   - Save config via `save_tracker_config()`
   - Store credentials via `TrackerCredentialStore.set_provider()`
   - Return the config

2. **unbind()**:
   - Copy existing `TrackerService.unbind()` logic
   - Load config to get provider name
   - Clear credentials via `TrackerCredentialStore.clear_provider()`
   - Clear config via `clear_tracker_config()`

**Files**: `src/specify_cli/tracker/local_service.py` (~40 lines)

**Reference**: Copy from `src/specify_cli/tracker/service.py` lines ~60-90 (bind) and ~95-110 (unbind).

---

## Subtask T019: Extract status + sync_pull/push/run

**Purpose**: Move the direct-connector sync operations for local providers.

**Steps**:

1. **_load_runtime() -> tuple[TrackerProjectConfig, dict, TrackerSqliteStore]**:
   - Copy from current `TrackerService._load_runtime()`
   - Loads config, credentials, resolves DB path, creates SQLite store
   - This is the private helper that all sync operations depend on

2. **_build_engine() -> tuple[connector, engine]**:
   - Copy from current `TrackerService._build_engine()`
   - Calls `build_connector()` with provider credentials
   - Creates `SyncEngine(connector, store, policy)`

3. **status() -> dict**:
   - Copy from current `TrackerService.status()`
   - Reports local config, DB path, issue count, mapping count, credentials presence

4. **sync_pull(limit=100) -> dict**:
   - Copy from current `TrackerService.sync_pull()`
   - Uses `_build_engine()`, runs `asyncio.run()` on connector pull

5. **sync_push(limit=100) -> dict**:
   - Copy from current `TrackerService.sync_push()`

6. **sync_run(limit=100) -> dict**:
   - Copy from current `TrackerService.sync_run()`

**Files**: `src/specify_cli/tracker/local_service.py` (~120 lines)

**CRITICAL**: This is a copy, not a rewrite. Preserve the exact logic to avoid breaking beads/fp.

---

## Subtask T020: Extract map_add/map_list

**Purpose**: Move mapping operations for local providers.

**Steps**:

1. **map_add(wp_id, external_id, external_key=None, external_url=None) -> None**:
   - Copy from current `TrackerService.map_add()`
   - Uses `_load_runtime()` to get SQLite store
   - Calls `store.upsert_mapping()`

2. **map_list() -> list[dict]**:
   - Copy from current `TrackerService.map_list()`
   - Uses `_load_runtime()` to get SQLite store
   - Calls `store.list_mappings()`

**Files**: `src/specify_cli/tracker/local_service.py` (~30 lines)

---

## Subtask T021: Write test_local_service.py

**Purpose**: Verify beads/fp behavior is preserved after extraction.

**Steps**:

1. Create `tests/sync/tracker/test_local_service.py`
2. Write tests that verify the extracted service works identically to the original:

   a. **bind stores config and credentials**:
   ```python
   def test_bind_stores_config_and_credentials(tmp_path):
       service = LocalTrackerService(tmp_path, TrackerProjectConfig())
       config = service.bind(
           provider="beads", workspace="my-ws",
           doctrine_mode="external_authoritative",
           doctrine_field_owners={},
           credentials={"command": "beads"},
       )
       assert config.provider == "beads"
       assert config.workspace == "my-ws"
   ```

   b. **unbind clears config and credentials**:
   - After unbind, config is empty and credential store has no provider entry

   c. **status returns local state**:
   - Mock the SQLite store to verify status reports local counts

   d. **map_add/map_list roundtrip**:
   - Add a mapping, list it, verify it appears
   - (May require mocking the SQLite store or using a temp DB)

   e. **sync operations delegate to connector**:
   - Mock `build_connector` to verify sync_pull/push/run call the direct connector
   - Verify no SaaS calls are made

**Files**: `tests/sync/tracker/test_local_service.py` (new, ~150 lines)

**Important**: Do NOT test beads/fp connectors themselves — those are tested in the spec_kitty_tracker package. Test that LocalTrackerService correctly wires up config → credentials → connector → store.

---

## Definition of Done

- [ ] `LocalTrackerService` created in `src/specify_cli/tracker/local_service.py`
- [ ] All methods copied from current `TrackerService` (bind, unbind, status, sync_pull/push/run, map_add, map_list)
- [ ] Private helpers copied (_load_runtime, _build_engine)
- [ ] Tests verify local provider behavior is preserved
- [ ] Existing `test_credentials.py` and `test_store.py` still pass (run full test suite)
- [ ] No SaaS imports in this file (no SaaSTrackerClient, no CredentialStore from sync/auth)
- [ ] `mypy --strict` passes

## Risks

- **Subtle behavioral differences**: Copying code can introduce bugs through missed context. Run the full tracker test suite after extraction.
- **Import dependencies**: The current `service.py` imports from `factory.py` which imports from `spec_kitty_tracker` package. Ensure the same imports work from `local_service.py`.

## Reviewer Guidance

- Verify this is a pure extraction — no new logic, no behavior changes for beads/fp
- Verify no SaaS-related imports leak into this file
- Verify method signatures match the current TrackerService (needed for façade dispatch in WP05)
- Run existing tracker tests to verify no regression

## Activity Log

- 2026-03-30T19:39:08Z – orchestrator – shell_pid=49505 – lane=doing – Started implementation via workflow command
