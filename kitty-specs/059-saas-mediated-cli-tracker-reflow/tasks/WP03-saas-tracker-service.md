---
work_package_id: WP03
title: SaaSTrackerService
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-006
- FR-007
- FR-008
- FR-009
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: c01335ad449c86efb90a36513a244feb4e816bdf
created_at: '2026-03-30T19:53:03.125065+00:00'
subtasks: [T012, T013, T014, T015, T016]
shell_pid: "51531"
agent: "orchestrator"
history:
- at: '2026-03-30T19:14:19+00:00'
  event: created
  actor: planner
authoritative_surface: src/specify_cli/tracker/saas_service.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/tracker/saas_service.py
- tests/sync/tracker/test_saas_service.py
---

# WP03: SaaSTrackerService

## Objective

Create `src/specify_cli/tracker/saas_service.py` — the service layer for SaaS-backed tracker providers (linear, jira, github, gitlab). This class delegates all tracker operations to `SaaSTrackerClient` and hard-fails operations that are not supported for SaaS-backed providers.

## Context

- `SaaSTrackerClient` (WP01) provides the HTTP transport layer.
- `TrackerProjectConfig` (WP02) provides config with `project_slug` and provider classification constants.
- This service does NOT hold provider-native credentials. It reads `project_slug` from config and derives `team_slug` from the auth credential store at call time (via the SaaS client).
- `map_add` and `sync_publish` are hard-fails — the CLI cannot write mappings or publish snapshots for SaaS-backed providers.

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Depends on WP01 (SaaS client) and WP02 (config model). Branch from WP01, merge WP02 if both are ready.

---

## Subtask T012: Create SaaSTrackerService Class

**Purpose**: Define the class structure with proper dependency injection.

**Steps**:

1. Create `src/specify_cli/tracker/saas_service.py`
2. Define `SaaSTrackerService`:
   ```python
   class SaaSTrackerService:
       def __init__(self, repo_root: Path, config: TrackerProjectConfig) -> None:
           self._repo_root = repo_root
           self._config = config
           self._client = SaaSTrackerClient()  # Uses default CredentialStore + SyncConfig

       @property
       def provider(self) -> str:
           assert self._config.provider is not None
           return self._config.provider

       @property
       def project_slug(self) -> str:
           assert self._config.project_slug is not None
           return self._config.project_slug
   ```

**Files**: `src/specify_cli/tracker/saas_service.py` (new, ~25 lines)

---

## Subtask T013: Implement bind/unbind

**Purpose**: Bind stores provider + project_slug only. Unbind clears the config. No credentials involved.

**Steps**:

1. **bind(provider, project_slug)**:
   ```python
   def bind(self, *, provider: str, project_slug: str) -> TrackerProjectConfig:
       config = TrackerProjectConfig(
           provider=provider,
           project_slug=project_slug,
       )
       save_tracker_config(self._repo_root, config)
       self._config = config
       return config
   ```
   - No `credentials` parameter. SaaS-backed providers never accept provider-native secrets from CLI.
   - No doctrine_mode or field_owners needed for SaaS bind (SaaS owns doctrine).

2. **unbind()**:
   ```python
   def unbind(self) -> None:
       clear_tracker_config(self._repo_root)
       self._config = TrackerProjectConfig()
   ```
   - Does NOT call `TrackerCredentialStore.clear_provider()` — no secrets exist for SaaS providers.

**Files**: `src/specify_cli/tracker/saas_service.py` (~20 lines)

---

## Subtask T014: Implement Operations via SaaS Client

**Purpose**: Delegate all tracker operations to the SaaS client with proper parameter forwarding.

**Steps**:

1. **status() -> dict**:
   ```python
   def status(self) -> dict[str, Any]:
       return self._client.status(self.provider, self.project_slug)
   ```

2. **pull(limit=100) -> dict**:
   ```python
   def sync_pull(self, *, limit: int = 100) -> dict[str, Any]:
       return self._client.pull(self.provider, self.project_slug, limit=limit)
   ```

3. **push() -> dict**:
   ```python
   def sync_push(self) -> dict[str, Any]:
       # Items come from the local context — for now, empty.
       # The SaaS owns the push payload construction in this model.
       return self._client.push(self.provider, self.project_slug, items=[])
   ```

4. **run(limit=100) -> dict**:
   ```python
   def sync_run(self, *, limit: int = 100) -> dict[str, Any]:
       return self._client.run(self.provider, self.project_slug, limit=limit)
   ```

5. **map_list() -> list[dict]**:
   ```python
   def map_list(self) -> list[dict[str, Any]]:
       result = self._client.mappings(self.provider, self.project_slug)
       return result.get("mappings", [])
   ```

**Files**: `src/specify_cli/tracker/saas_service.py` (~40 lines)

**Note**: Method names should match the existing `TrackerService` API surface (`sync_pull`, `sync_push`, `sync_run`, `map_list`) so the façade can dispatch without translation.

---

## Subtask T015: Implement Hard-Fails

**Purpose**: `map_add` and `sync_publish` must fail immediately for SaaS-backed providers with actionable guidance.

**Steps**:

1. **map_add()**:
   ```python
   def map_add(self, **kwargs: Any) -> None:
       raise TrackerServiceError(
           "Mappings for SaaS-backed providers are managed in the Spec Kitty dashboard. "
           "Use the web interface to create or edit mappings."
       )
   ```

2. **sync_publish()**:
   ```python
   def sync_publish(self, **kwargs: Any) -> dict[str, Any]:
       raise TrackerServiceError(
           "Snapshot publish is not supported for SaaS-backed providers. "
           "Use `spec-kitty tracker sync push` to push changes through the SaaS control plane."
       )
   ```

**Files**: `src/specify_cli/tracker/saas_service.py` (~15 lines)

**Import**: `from specify_cli.tracker.service import TrackerServiceError` (or define a local error class if the import creates circular dependency — resolve at implementation time)

---

## Subtask T016: Write test_saas_service.py

**Purpose**: Test all SaaSTrackerService operations with a mocked SaaS client.

**Steps**:

1. Create `tests/sync/tracker/test_saas_service.py`
2. Create a mock fixture for `SaaSTrackerClient` that returns canned responses
3. Write tests:

   a. **bind stores config correctly**:
   ```python
   def test_bind_stores_project_slug(tmp_path):
       service = SaaSTrackerService(tmp_path, TrackerProjectConfig())
       config = service.bind(provider="linear", project_slug="my-proj")
       assert config.provider == "linear"
       assert config.project_slug == "my-proj"
       assert config.workspace is None  # No workspace for SaaS
       # Verify persisted to disk
       loaded = load_tracker_config(tmp_path)
       assert loaded.project_slug == "my-proj"
   ```

   b. **unbind clears config**:
   - After unbind, `load_tracker_config` returns empty config

   c. **pull delegates to client**:
   - Mock client.pull → verify called with correct provider + project_slug
   - Verify return value is client response

   d. **push delegates to client**:
   - Mock client.push → verify called with Idempotency-Key handling

   e. **run delegates to client**:
   - Mock client.run → verify delegation

   f. **status delegates to client**:
   - Mock client.status → verify delegation

   g. **map_list delegates to client**:
   - Mock client.mappings → verify delegation

   h. **map_add hard-fails**:
   ```python
   def test_map_add_hard_fails():
       service = SaaSTrackerService(tmp_path, config)
       with pytest.raises(TrackerServiceError, match="managed in the Spec Kitty dashboard"):
           service.map_add(wp_id="WP01", external_id="LIN-123")
   ```

   i. **sync_publish hard-fails**:
   ```python
   def test_sync_publish_hard_fails():
       with pytest.raises(TrackerServiceError, match="not supported for SaaS-backed"):
           service.sync_publish(server_url="https://example.com")
   ```

**Files**: `tests/sync/tracker/test_saas_service.py` (new, ~200 lines)

---

## Definition of Done

- [ ] `SaaSTrackerService` created in `src/specify_cli/tracker/saas_service.py`
- [ ] `bind()` stores provider + project_slug, no credentials
- [ ] `unbind()` clears config only (no credential cleanup)
- [ ] `sync_pull/push/run/status/map_list` delegate to `SaaSTrackerClient`
- [ ] `map_add()` raises `TrackerServiceError` with dashboard guidance
- [ ] `sync_publish()` raises `TrackerServiceError` with push guidance
- [ ] Tests cover all operations including hard-fails
- [ ] Method names match existing TrackerService API surface
- [ ] `mypy --strict` passes

## Risks

- **Push items**: The `sync_push` method sends `items=[]` in this phase. The SaaS control plane handles push payload construction. If the contract requires CLI-supplied items, this will need adjustment — but the contract spec shows the SaaS owns item collection.
- **Circular imports**: `TrackerServiceError` may need to be defined in a shared location if importing from `service.py` causes cycles.

## Reviewer Guidance

- Verify no provider-native credentials appear anywhere in this file
- Verify `map_add` and `sync_publish` are unconditional hard-fails, not conditional
- Verify method signatures match the existing `TrackerService` so the façade can dispatch without translation
- Verify no `TrackerCredentialStore` usage (that's local-only)

## Activity Log

- 2026-03-30T19:53:03Z – orchestrator – shell_pid=51531 – lane=doing – Started implementation via workflow command
- 2026-03-30T19:56:28Z – orchestrator – shell_pid=51531 – lane=for_review – Ready for review: SaaSTrackerService with client delegation, bind/unbind, and hard-fails for map_add/sync_publish. 26 tests pass, mypy strict clean, ruff clean.
- 2026-03-30T19:56:59Z – orchestrator – shell_pid=51531 – lane=approved – Review passed: 128-line service, 26 tests, no credential references, method signatures match facade surface, hard-fails unconditional. Approved.
