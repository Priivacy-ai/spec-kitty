---
work_package_id: WP07
title: Service Layer – Routing & Upgrade
dependencies: []
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-018
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 61417a958f7ca801be5944c4f7dcb7cf4a7a52df
created_at: '2026-04-04T10:26:57.221664+00:00'
subtasks: [T030, T031, T032, T033, T034, T035]
shell_pid: "89919"
agent: "coordinator"
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/
execution_mode: code_change
owned_files: [src/specify_cli/tracker/saas_service.py, tests/sync/tracker/test_saas_service.py]
---

# WP07: Service Layer – Routing & Upgrade

## Objective

Add core service infrastructure to `SaaSTrackerService`: routing key resolution (`_resolve_routing_params`), opportunistic binding_ref upgrade (`_maybe_upgrade_binding_ref`), and reactive stale-binding detection. This WP touches all existing delegated methods.

## Context

- **Spec**: FR-010 (read precedence), FR-011 (opportunistic upgrade), FR-012 (upgrade failure graceful), FR-018 (stale binding detection)
- **Plan**: Routing Key Resolution, Opportunistic Upgrade Flow, Stale Binding Detection, Error Classification sections
- **Research**: Decision 2 (explicit helper), Decision 4 (reactive detection), Decision 8 (error enrichment)
- **Current code**: `src/specify_cli/tracker/saas_service.py` — all methods currently use `self.project_slug` directly
- **Depends on**: WP01 (config has binding_ref), WP03 (enriched errors), WP05 (client accepts binding_ref)

## Implementation Command

```bash
spec-kitty implement WP07 --base WP05
```

## Subtasks

### T030: Add _resolve_routing_params()

**Purpose**: Centralize routing key resolution: binding_ref-first, project_slug-fallback.

**Steps**:
1. Add private method to `SaaSTrackerService`:
   ```python
   def _resolve_routing_params(self) -> dict[str, str]:
       """Resolve which routing key to send to the client.
       
       Returns dict with either binding_ref or project_slug key.
       binding_ref takes precedence. Raises if neither available.
       """
       if self._config.binding_ref:
           return {"binding_ref": self._config.binding_ref}
       if self._config.project_slug:
           return {"project_slug": self._config.project_slug}
       raise TrackerServiceError(
           "No tracker binding configured. Run `spec-kitty tracker bind` first."
       )
   ```

**Files**: `src/specify_cli/tracker/saas_service.py`

### T031: Update Existing Delegated Methods

**Purpose**: All methods use `_resolve_routing_params()` instead of `self.project_slug`.

**Steps**:
1. Update `status()`:
   ```python
   def status(self) -> dict[str, Any]:
       routing = self._resolve_routing_params()
       result = self._client.status(self.provider, **routing)
       self._maybe_upgrade_binding_ref(result)
       return result
   ```
2. Update `sync_pull()`, `sync_push()`, `sync_run()`, `map_list()` with same pattern
3. Remove the `project_slug` property (or make it optional — needed for backward compat check)

**Files**: `src/specify_cli/tracker/saas_service.py`

### T032: Add _maybe_upgrade_binding_ref() Helper

**Purpose**: Opportunistically write binding_ref to config from successful SaaS responses.

**Steps**:
1. Add helper:
   ```python
   def _maybe_upgrade_binding_ref(self, response: dict[str, Any]) -> None:
       """Opportunistically persist binding_ref from response if available.
       
       Silent on failure (debug log only). Never modifies config if
       response doesn't contain binding_ref.
       """
       binding_ref = response.get("binding_ref")
       if not binding_ref:
           return
       if self._config.binding_ref == binding_ref:
           return  # Already up to date
       
       import logging
       logger = logging.getLogger(__name__)
       
       try:
           self._config.binding_ref = binding_ref
           display_label = response.get("display_label")
           if display_label:
               self._config.display_label = display_label
           provider_context = response.get("provider_context")
           if isinstance(provider_context, dict):
               self._config.provider_context = provider_context
           save_tracker_config(self._repo_root, self._config)
           logger.debug("Opportunistically upgraded binding_ref to %s", binding_ref)
       except Exception:
           logger.debug("Failed to upgrade binding_ref", exc_info=True)
   ```

**Files**: `src/specify_cli/tracker/saas_service.py`

**Note**: `TrackerProjectConfig` uses `slots=True` and `frozen` is NOT set (it's mutable). Direct attribute assignment works.

### T033: Wire Upgrade into Call Sites

**Purpose**: Call `_maybe_upgrade_binding_ref` after each successful client call.

**Steps**:
1. Already shown in T031 for `status()`. Ensure ALL delegated methods follow the pattern:
   ```python
   result = self._client.method(self.provider, **routing)
   self._maybe_upgrade_binding_ref(result)
   return result
   ```
2. Methods to update: `status`, `sync_pull`, `sync_push`, `sync_run`, `map_list`

**Files**: `src/specify_cli/tracker/saas_service.py`

### T034: Create StaleBindingError + Detection

**Purpose**: Detect stale bindings reactively from enriched client errors.

**Steps**:
1. Add subclass in `src/specify_cli/tracker/service.py` (alongside TrackerServiceError):
   ```python
   class StaleBindingError(TrackerServiceError):
       """Raised when binding_ref is stale (deleted/disabled on host)."""
       def __init__(self, message: str, *, binding_ref: str, error_code: str) -> None:
           super().__init__(message)
           self.binding_ref = binding_ref
           self.error_code = error_code
   ```
2. In `SaaSTrackerService`, add stale-binding detection wrapper. After each client call that uses binding_ref, catch enriched errors:
   ```python
   _STALE_BINDING_CODES = {"binding_not_found", "mapping_disabled", "project_mismatch"}
   
   def _call_with_stale_detection(
       self, method, *args, **kwargs
   ) -> dict[str, Any]:
       try:
           return method(*args, **kwargs)
       except SaaSTrackerClientError as e:
           if e.error_code in self._STALE_BINDING_CODES and self._config.binding_ref:
               raise StaleBindingError(
                   f"Tracker binding is stale: {e}. "
                   f"Run `spec-kitty tracker bind --provider {self.provider}` to rebind.",
                   binding_ref=self._config.binding_ref,
                   error_code=e.error_code or "unknown",
               ) from e
           raise
   ```
3. Wrap client calls in delegated methods with stale detection when routing by binding_ref

**Files**: `src/specify_cli/tracker/saas_service.py`, `src/specify_cli/tracker/service.py`

### T035: Write Service Tests

**Purpose**: Test routing, upgrade, and stale detection.

**Steps**:
1. Add to `tests/sync/tracker/test_saas_service.py`:
   - `test_resolve_routing_binding_ref_first`: config with both → returns binding_ref
   - `test_resolve_routing_project_slug_fallback`: config with only project_slug → returns project_slug
   - `test_resolve_routing_neither_raises`: config with neither → TrackerServiceError
   - `test_maybe_upgrade_writes_binding_ref`: mock response with binding_ref → verify config saved
   - `test_maybe_upgrade_no_binding_ref_noop`: mock response without → config unchanged
   - `test_maybe_upgrade_already_current_noop`: same binding_ref → no save call
   - `test_maybe_upgrade_failure_silent`: save throws → no exception propagated
   - `test_stale_binding_detection`: mock client raises with error_code=binding_not_found → StaleBindingError
   - `test_stale_binding_no_false_positive`: mock client raises with other error_code → original error

**Files**: `tests/sync/tracker/test_saas_service.py`

## Definition of Done

- [ ] `_resolve_routing_params()` returns binding_ref-first, project_slug-fallback
- [ ] All 5 existing delegated methods use routing params + upgrade helper
- [ ] `_maybe_upgrade_binding_ref()` writes atomically, silent on failure
- [ ] `StaleBindingError` raised for known stale-binding error codes
- [ ] No silent fallback from binding_ref to project_slug on stale detection
- [ ] All tests pass: `python -m pytest tests/sync/tracker/test_saas_service.py -x -q`
- [ ] `ruff check src/specify_cli/tracker/saas_service.py`
- [ ] `mypy src/specify_cli/tracker/saas_service.py`

## Risks

- **Config mutability**: `TrackerProjectConfig` uses `slots=True` but is NOT frozen. Direct attribute assignment works. Verify by checking dataclass definition.
- **Import cycle**: `StaleBindingError` goes in `service.py`, imported by `saas_service.py`. This matches the existing import direction.

## Reviewer Guidance

- Verify `_maybe_upgrade_binding_ref` is called at EVERY call site (status, sync_pull, sync_push, sync_run, map_list)
- Verify stale detection only fires when routing by binding_ref (not project_slug)
- Check that upgrade helper handles partial responses (e.g., display_label present but provider_context missing)

## Activity Log

- 2026-04-04T10:26:57Z – coordinator – shell_pid=6535 – Started implementation via workflow command
- 2026-04-04T10:32:16Z – coordinator – shell_pid=6535 – Ready for review: routing resolution, opportunistic upgrade, stale-binding detection - all 52 tests pass
- 2026-04-04T10:32:54Z – codex – shell_pid=35148 – Started review via workflow command
- 2026-04-04T10:38:06Z – codex – shell_pid=35148 – Moved to planned
- 2026-04-04T10:38:37Z – coordinator – shell_pid=89919 – Started implementation via workflow command
