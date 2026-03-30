---
work_package_id: WP05
title: Façade, Factory + Dead Code Removal
dependencies: [WP03, WP04]
requirement_refs:
- FR-012
- FR-013
- FR-021
- FR-022
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Depends on WP03 and WP04. Use `spec-kitty implement WP05 --base WP03` then merge WP04 branch, or wait for both to merge to main.
subtasks: [T022, T023, T024, T025, T026, T027]
history:
- at: '2026-03-30T19:14:19+00:00'
  event: created
  actor: planner
authoritative_surface: src/specify_cli/tracker/service.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/tracker/service.py
- src/specify_cli/tracker/factory.py
- src/specify_cli/tracker/__init__.py
- tests/sync/tracker/test_service.py
- tests/sync/tracker/test_service_publish.py
---

# WP05: Façade, Factory + Dead Code Removal

## Objective

Refactor `TrackerService` in `service.py` into a thin façade that dispatches to `SaaSTrackerService` or `LocalTrackerService` based on provider. Remove all SaaS-backed and Azure DevOps entries from `factory.py`. Delete 10,526 lines of obsolete snapshot publish tests. This is where the old direct-provider model dies for SaaS-backed providers.

## Context

- `SaaSTrackerService` (WP03) handles linear/jira/github/gitlab.
- `LocalTrackerService` (WP04) handles beads/fp.
- After this WP, `service.py` is a ~60-line façade, not a ~400-line monolith.
- `factory.py` shrinks from 7 providers to 2 (beads, fp).
- `test_service_publish.py` (10,526 lines) is deleted — the snapshot publish model no longer exists.

## Implementation Command

```bash
spec-kitty implement WP05 --base WP03
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Depends on WP03 and WP04. Branch from WP03, merge WP04 branch if needed.

---

## Subtask T022: Refactor service.py into Thin Façade

**Purpose**: Replace the monolithic TrackerService with a dispatcher.

**Steps**:

1. Open `src/specify_cli/tracker/service.py`
2. **Delete all method implementations** (bind, unbind, status, sync_pull, sync_push, sync_run, sync_publish, map_add, map_list)
3. **Delete all private helpers** (_load_runtime, _build_engine, _resolve_db_path, _issue_snapshot, _project_identity, _resolve_resource_routing)
4. **Delete** `RESOURCE_ROUTING_MAP` constant
5. **Keep**: `TrackerServiceError`, `parse_kv_pairs` (used by CLI)
6. **Rewrite** `TrackerService` as:

```python
from specify_cli.tracker.config import (
    SAAS_PROVIDERS, LOCAL_PROVIDERS, REMOVED_PROVIDERS,
    TrackerProjectConfig, load_tracker_config,
)
from specify_cli.tracker.saas_service import SaaSTrackerService
from specify_cli.tracker.local_service import LocalTrackerService


class TrackerService:
    """Thin façade dispatching to SaaS or local backend by provider."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def _resolve_backend(self) -> SaaSTrackerService | LocalTrackerService:
        config = load_tracker_config(self._repo_root)
        if not config.provider:
            raise TrackerServiceError("No tracker bound. Run `spec-kitty tracker bind` first.")
        if config.provider in SAAS_PROVIDERS:
            return SaaSTrackerService(self._repo_root, config)
        if config.provider in LOCAL_PROVIDERS:
            return LocalTrackerService(self._repo_root, config)
        if config.provider in REMOVED_PROVIDERS:
            raise TrackerServiceError(
                f"Provider '{config.provider}' is no longer supported. "
                "See the Spec Kitty documentation for supported providers."
            )
        raise TrackerServiceError(f"Unknown provider: {config.provider}")

    @staticmethod
    def supported_providers() -> tuple[str, ...]:
        return tuple(sorted(SAAS_PROVIDERS | LOCAL_PROVIDERS))

    # --- Delegating methods ---

    def bind(self, **kwargs: Any) -> TrackerProjectConfig:
        # Pre-dispatch: determine provider from kwargs to pick backend
        provider = kwargs.get("provider", "")
        if provider in SAAS_PROVIDERS:
            return SaaSTrackerService(self._repo_root, TrackerProjectConfig()).bind(**kwargs)
        if provider in LOCAL_PROVIDERS:
            return LocalTrackerService(self._repo_root, TrackerProjectConfig()).bind(**kwargs)
        if provider in REMOVED_PROVIDERS:
            raise TrackerServiceError(f"Provider '{provider}' is no longer supported.")
        raise TrackerServiceError(f"Unknown provider: {provider}")

    def unbind(self) -> None:
        return self._resolve_backend().unbind()

    def status(self) -> dict[str, Any]:
        return self._resolve_backend().status()

    def sync_pull(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_pull(**kwargs)

    def sync_push(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_push(**kwargs)

    def sync_run(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_run(**kwargs)

    def sync_publish(self, **kwargs: Any) -> dict[str, Any]:
        return self._resolve_backend().sync_publish(**kwargs)

    def map_add(self, **kwargs: Any) -> None:
        return self._resolve_backend().map_add(**kwargs)

    def map_list(self) -> list[dict[str, Any]]:
        return self._resolve_backend().map_list()
```

**Files**: `src/specify_cli/tracker/service.py` (rewrite to ~80 lines from ~400)

---

## Subtask T023: Remove Old Direct-Provider Code

**Purpose**: Delete everything in service.py that only existed for the direct-provider flow.

**Steps**:

This is incorporated into T022 — when rewriting service.py, the following are all deleted:
- `RESOURCE_ROUTING_MAP` (lines ~27-30)
- `_load_runtime()` (moved to LocalTrackerService in WP04)
- `_build_engine()` (moved to LocalTrackerService)
- `_resolve_db_path()` (moved to LocalTrackerService)
- `_issue_snapshot()` (snapshot model dead)
- `_project_identity()` (snapshot model dead)
- `_resolve_resource_routing()` (snapshot model dead)
- `sync_publish()` method body (hard-fail in SaaS, never existed for local)
- All `asyncio.run()` patterns (moved to LocalTrackerService)
- `httpx` import (moved to saas_client.py)

**Verification**: After rewrite, `service.py` should have NO imports from:
- `specify_cli.tracker.credentials` (local-only)
- `specify_cli.tracker.store` (local-only)
- `specify_cli.tracker.factory` (local-only)
- `hashlib` (was for DB path hashing)
- `httpx` (was for sync_publish)

---

## Subtask T024: Remove SaaS-Backed + Azure Entries from factory.py

**Purpose**: factory.py should only know about beads and fp.

**Steps**:

1. Open `src/specify_cli/tracker/factory.py`
2. Remove from `SUPPORTED_PROVIDERS`: `"jira"`, `"linear"`, `"azure_devops"`, `"github"`, `"gitlab"`
3. Keep only: `("beads", "fp")`
4. Remove from `build_connector()`:
   - The `jira` branch (imports `JiraConnector`, `JiraConfig`)
   - The `linear` branch (imports `LinearConnector`, `LinearConfig`)
   - The `azure_devops` branch (imports `AzureDevOpsConnector`, `AzureDevOpsConfig`)
   - The `github` branch (imports `GitHubConnector`, `GitHubConfig`)
   - The `gitlab` branch (imports `GitLabConnector`, `GitLabConfig`)
5. Keep: `beads` and `fp` branches
6. Remove from `normalize_provider()`: Azure DevOps aliases (`"azure-devops"` → `"azure_devops"`, `"azure"` → `"azure_devops"`)
7. Remove the `_require()` helper if it's only used by removed providers (check if beads/fp use it)

**Files**: `src/specify_cli/tracker/factory.py` (reduce from ~133 lines to ~40 lines)

---

## Subtask T025: Update SUPPORTED_PROVIDERS, normalize_provider(), __init__.py

**Purpose**: Ensure module exports and utility functions reflect the new provider landscape.

**Steps**:

1. **factory.py**: `SUPPORTED_PROVIDERS` should now be `("beads", "fp")`
   - This constant is used by the old `TrackerService.supported_providers()` — the façade now uses `config.ALL_SUPPORTED_PROVIDERS` instead
   - Keep `SUPPORTED_PROVIDERS` in factory.py for local-only context (what the factory can build)

2. **tracker/__init__.py**: Update exports:
   ```python
   from specify_cli.tracker.feature_flags import (
       SAAS_SYNC_ENV_VAR,
       is_saas_sync_enabled,
       saas_sync_disabled_message,
   )
   from specify_cli.tracker.config import (
       SAAS_PROVIDERS,
       LOCAL_PROVIDERS,
       REMOVED_PROVIDERS,
       ALL_SUPPORTED_PROVIDERS,
   )
   ```

3. **normalize_provider()**: Should still normalize aliases for beads/fp if any exist. Remove all Azure aliases.

**Files**: `src/specify_cli/tracker/factory.py` (~5 lines), `src/specify_cli/tracker/__init__.py` (~10 lines)

---

## Subtask T026: Delete test_service_publish.py

**Purpose**: Remove 10,526 lines of tests for the obsolete snapshot publish model.

**Steps**:

1. Delete `tests/sync/tracker/test_service_publish.py`
2. Verify no other test file imports from it
3. Run the test suite to ensure nothing depends on it

**Files**: `tests/sync/tracker/test_service_publish.py` (DELETE, -10,526 lines)

**Rationale**: Every test in this file tests `TrackerService.sync_publish()`, `_issue_snapshot()`, `_project_identity()`, `_resolve_resource_routing()`, and related helpers. All of that code is deleted in this WP. The replacement coverage is in `test_saas_client.py` (WP01) and `test_saas_service.py` (WP03).

---

## Subtask T027: Write test_service.py for Façade Dispatch

**Purpose**: Test that the façade correctly dispatches to the right backend.

**Steps**:

1. Create `tests/sync/tracker/test_service.py`
2. Write tests:

   a. **SaaS provider dispatches to SaaSTrackerService**:
   ```python
   def test_resolve_backend_saas(tmp_path):
       save_tracker_config(tmp_path, TrackerProjectConfig(provider="linear", project_slug="p"))
       service = TrackerService(tmp_path)
       backend = service._resolve_backend()
       assert isinstance(backend, SaaSTrackerService)
   ```

   b. **Local provider dispatches to LocalTrackerService**:
   ```python
   def test_resolve_backend_local(tmp_path):
       save_tracker_config(tmp_path, TrackerProjectConfig(provider="beads", workspace="w"))
       service = TrackerService(tmp_path)
       backend = service._resolve_backend()
       assert isinstance(backend, LocalTrackerService)
   ```

   c. **Removed provider raises error**:
   ```python
   def test_resolve_backend_removed(tmp_path):
       save_tracker_config(tmp_path, TrackerProjectConfig(provider="azure_devops", workspace="w"))
       service = TrackerService(tmp_path)
       with pytest.raises(TrackerServiceError, match="no longer supported"):
           service._resolve_backend()
   ```

   d. **No binding raises error**:
   ```python
   def test_resolve_backend_no_binding(tmp_path):
       service = TrackerService(tmp_path)
       with pytest.raises(TrackerServiceError, match="No tracker bound"):
           service._resolve_backend()
   ```

   e. **supported_providers() returns correct list**:
   ```python
   def test_supported_providers():
       providers = TrackerService.supported_providers()
       assert "linear" in providers
       assert "beads" in providers
       assert "azure_devops" not in providers
   ```

   f. **bind dispatches by provider**:
   - Bind with "linear" → dispatches to SaaS backend
   - Bind with "beads" → dispatches to local backend
   - Bind with "azure_devops" → raises error

**Files**: `tests/sync/tracker/test_service.py` (new, ~120 lines)

---

## Definition of Done

- [ ] `service.py` is a thin façade (~80 lines) dispatching by provider
- [ ] All old direct-provider code removed from `service.py`
- [ ] `factory.py` only contains beads + fp (no SaaS-backed, no Azure)
- [ ] `__init__.py` exports provider classification constants
- [ ] `test_service_publish.py` deleted (10,526 lines)
- [ ] `test_service.py` covers façade dispatch (SaaS/local/removed/unbound)
- [ ] Net code deletion: ~400 (service.py) + ~90 (factory.py) + ~10,526 (tests) - ~80 (new service) - ~120 (new tests) ≈ **-10,816 net lines removed**
- [ ] Existing `test_credentials.py` and `test_store.py` still pass
- [ ] `mypy --strict` passes

## Risks

- **Import cycles**: The façade imports both SaaS and local services. Ensure no circular dependencies.
- **Method signature drift**: If WP03 or WP04 used slightly different method signatures, the façade's `**kwargs` forwarding will mask the issue at call time. Tests must verify actual delegation.

## Reviewer Guidance

- This is the biggest impact WP in terms of code deletion. Verify the old code is genuinely dead, not just moved.
- Verify `parse_kv_pairs` is preserved (CLI uses it for `--credential` parsing)
- Verify `TrackerServiceError` is preserved (used throughout CLI)
- Count net lines: this WP should produce the largest net reduction in the feature
- Verify `factory.py` has no remaining imports from `spec_kitty_tracker` for jira/linear/github/gitlab/azure_devops
