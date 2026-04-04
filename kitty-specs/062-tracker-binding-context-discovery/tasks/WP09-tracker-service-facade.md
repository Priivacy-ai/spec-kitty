---
work_package_id: WP09
title: TrackerService Facade
dependencies: [WP07, WP08]
requirement_refs:
- FR-001
- FR-003
- FR-006
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning branch is main. Merge target is main. Actual base_branch may differ for stacked WPs during /spec-kitty.implement.
subtasks: [T042, T043, T044, T045, T046]
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/
execution_mode: code_change
owned_files: [src/specify_cli/tracker/service.py, tests/sync/tracker/test_service.py]
---

# WP09: TrackerService Facade

## Objective

Add `discover()`, update `bind()`, and add `status(all=)` to the `TrackerService` dispatch facade in `src/specify_cli/tracker/service.py`. Guard local providers against SaaS-only operations.

## Context

- **Spec**: FR-001 (discover), FR-003 (bind with discovery), FR-014 (status --all)
- **Plan**: TrackerService Facade Evolution section
- **Research**: Decision 9 (facade evolution)
- **Current code**: `src/specify_cli/tracker/service.py` — TrackerService class with `_resolve_backend()`, `bind()`, `status()`, etc.
- **Depends on**: WP07 (SaaS service routing/upgrade), WP08 (SaaS service discovery/bind)

## Implementation Command

```bash
spec-kitty implement WP09 --base WP08
```

## Subtasks

### T042: Add discover() to Facade

**Purpose**: Installation-wide resource discovery, SaaS-only.

**Steps**:
1. Add to `TrackerService`:
   ```python
   def discover(self, *, provider: str) -> list:
       """List bindable resources for the given provider (SaaS only)."""
       if provider in LOCAL_PROVIDERS:
           raise TrackerServiceError(
               f"Discovery is not available for local provider '{provider}'."
           )
       if provider in REMOVED_PROVIDERS:
           raise TrackerServiceError(f"Provider '{provider}' is no longer supported.")
       if provider not in SAAS_PROVIDERS:
           raise TrackerServiceError(f"Unknown provider: {provider}")
       
       from specify_cli.tracker.saas_service import SaaSTrackerService
       config = load_tracker_config(self._repo_root)
       service = SaaSTrackerService(self._repo_root, config)
       return service.discover(provider)
   ```

**Files**: `src/specify_cli/tracker/service.py`

### T043: Update bind() for SaaS Discovery Flow

**Purpose**: SaaS bind now uses resolve_and_bind() instead of old bind(project_slug=).

**Steps**:
1. Update the SaaS path in `bind()`:
   ```python
   def bind(self, **kwargs) -> Any:
       provider = kwargs.get("provider", "")
       if provider in SAAS_PROVIDERS:
           from specify_cli.tracker.saas_service import SaaSTrackerService
           service = SaaSTrackerService(self._repo_root, TrackerProjectConfig())
           
           bind_ref = kwargs.get("bind_ref")
           select_n = kwargs.get("select_n")
           project_identity = kwargs.get("project_identity")
           
           if bind_ref:
               # Validate and persist directly
               return service.validate_and_bind(
                   provider=provider, bind_ref=bind_ref,
                   project_identity=project_identity,
               )
           
           return service.resolve_and_bind(
               provider=provider,
               project_identity=project_identity,
               select_n=select_n,
           )
       # ... existing local path unchanged
   ```

**Files**: `src/specify_cli/tracker/service.py`

### T044: Add status(all=) Parameter

**Purpose**: Installation-wide status when --all is passed.

**Steps**:
1. Update `status()`:
   ```python
   def status(self, *, all: bool = False) -> dict[str, Any]:
       if all:
           config = load_tracker_config(self._repo_root)
           if not config.provider or config.provider not in SAAS_PROVIDERS:
               raise TrackerServiceError(
                   "Installation-wide status (--all) is only available for SaaS providers."
               )
           from specify_cli.tracker.saas_service import SaaSTrackerService
           service = SaaSTrackerService(self._repo_root, config)
           return self._client.status(config.provider)  # No project_slug, no binding_ref
       return self._resolve_backend().status()
   ```

**Files**: `src/specify_cli/tracker/service.py`

### T045: Guard Local Providers

**Purpose**: Clear errors for SaaS-only operations on local providers.

**Steps**:
1. Already handled in T042 (discover) and T044 (status --all)
2. Verify error messages are clear and actionable
3. Test that `discover(provider="beads")` raises TrackerServiceError
4. Test that `status(all=True)` with local provider raises TrackerServiceError

**Files**: `src/specify_cli/tracker/service.py`

### T046: Write Facade Tests

**Purpose**: Test dispatch to correct backend and SaaS-only guards.

**Steps**:
1. Add to `tests/sync/tracker/test_service.py`:
   - `test_discover_saas_delegates`: mock SaaSTrackerService.discover → verify called
   - `test_discover_local_raises`: provider="beads" → TrackerServiceError
   - `test_discover_unknown_raises`: provider="unknown" → TrackerServiceError
   - `test_bind_saas_delegates_to_resolve_and_bind`: verify resolve_and_bind called
   - `test_bind_saas_with_bind_ref`: verify validate_and_bind called
   - `test_status_all_saas`: verify installation-wide call
   - `test_status_all_local_raises`: local provider + all=True → TrackerServiceError

**Files**: `tests/sync/tracker/test_service.py`

## Definition of Done

- [ ] `discover()` on facade delegates to SaaSTrackerService, guards local
- [ ] `bind()` SaaS path uses resolve_and_bind() (no more project_slug in bind flow)
- [ ] `status(all=True)` works for SaaS, raises for local
- [ ] All facade tests pass: `python -m pytest tests/sync/tracker/test_service.py -x -q`
- [ ] `ruff check src/specify_cli/tracker/service.py`

## Reviewer Guidance

- Verify local provider guards produce clear, actionable error messages
- Verify the bind kwargs pattern passes through bind_ref, select_n, project_identity correctly
- Check that existing unbind(), sync_pull(), etc. are unchanged
