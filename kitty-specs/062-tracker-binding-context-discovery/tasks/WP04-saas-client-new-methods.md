---
work_package_id: WP04
title: SaaS Client New Methods
dependencies: []
requirement_refs:
- FR-001
- FR-015
- FR-016
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: a7a223b517bd925d648cea8ac5c06666697fb8fc
created_at: '2026-04-04T10:06:35.360660+00:00'
subtasks: [T015, T016, T017, T018, T019]
shell_pid: "55866"
agent: "codex"
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: tests/sync/tracker/
execution_mode: code_change
owned_files: [tests/sync/tracker/test_saas_client_new_methods.py]
---

# WP04: SaaS Client New Methods

## Objective

Add 4 new methods to `SaaSTrackerClient` for the discovery and binding endpoints: `resources()`, `bind_resolve()`, `bind_confirm()`, `bind_validate()`. Each follows the existing `_request_with_retry` pattern.

## Context

- **Spec**: SaaS API Consumer Contract section (Endpoints 1-4)
- **Plan**: Client Layer in architecture; new methods listed
- **Contracts**: contracts/resources.md, bind-resolve.md, bind-confirm.md, bind-validate.md
- **Current code**: `src/specify_cli/tracker/saas_client.py` — existing methods like `status()`, `pull()`, etc.

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

Depends on WP02 (discovery types) and WP03 (enriched errors). Use WP03 as base since it modifies the same file.

## Subtasks

### T015: Add Path Constants

**Purpose**: Define URL path constants for the 4 new endpoints.

**Steps**:
1. In `SaaSTrackerClient`, add alongside existing `_STATUS_PATH`, `_MAPPINGS_PATH`, etc.:
   ```python
   _RESOURCES_PATH = "/api/v1/tracker/resources/"
   _BIND_RESOLVE_PATH = "/api/v1/tracker/bind-resolve/"
   _BIND_CONFIRM_PATH = "/api/v1/tracker/bind-confirm/"
   _BIND_VALIDATE_PATH = "/api/v1/tracker/bind-validate/"
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T016: Implement resources()

**Purpose**: GET /api/v1/tracker/resources/ — enumerate bindable resources.

**Steps**:
1. Add method to `SaaSTrackerClient`:
   ```python
   def resources(self, provider: str) -> dict[str, Any]:
       """GET /api/v1/tracker/resources/ -- enumerate bindable resources."""
       response = self._request_with_retry(
           "GET",
           self._RESOURCES_PATH,
           params={"provider": provider},
       )
       result: dict[str, Any] = response.json()
       return result
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T017: Implement bind_resolve()

**Purpose**: POST /api/v1/tracker/bind-resolve/ — resolve local identity to candidates.

**Steps**:
1. Add method:
   ```python
   def bind_resolve(
       self,
       provider: str,
       project_identity: dict[str, Any],
   ) -> dict[str, Any]:
       """POST /api/v1/tracker/bind-resolve/ -- resolve identity to bind candidates."""
       payload: dict[str, Any] = {
           "provider": provider,
           "project_identity": project_identity,
       }
       response = self._request_with_retry(
           "POST",
           self._BIND_RESOLVE_PATH,
           json=payload,
       )
       result: dict[str, Any] = response.json()
       return result
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T018: Implement bind_confirm()

**Purpose**: POST /api/v1/tracker/bind-confirm/ — confirm selection, create binding.

**Steps**:
1. Add method with idempotency key (matches existing `Idempotency-Key` convention):
   ```python
   def bind_confirm(
       self,
       provider: str,
       candidate_token: str,
       project_identity: dict[str, Any],
       *,
       idempotency_key: str | None = None,
   ) -> dict[str, Any]:
       """POST /api/v1/tracker/bind-confirm/ -- confirm bind selection."""
       key = idempotency_key or str(uuid.uuid4())
       payload: dict[str, Any] = {
           "provider": provider,
           "candidate_token": candidate_token,
           "project_identity": project_identity,
       }
       response = self._request_with_retry(
           "POST",
           self._BIND_CONFIRM_PATH,
           json=payload,
           headers={"Idempotency-Key": key},
       )
       result: dict[str, Any] = response.json()
       return result
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

### T019: Implement bind_validate()

**Purpose**: POST /api/v1/tracker/bind-validate/ — validate existing binding_ref.

**Steps**:
1. Add method:
   ```python
   def bind_validate(
       self,
       provider: str,
       binding_ref: str,
       project_identity: dict[str, Any],
   ) -> dict[str, Any]:
       """POST /api/v1/tracker/bind-validate/ -- validate binding ref."""
       payload: dict[str, Any] = {
           "provider": provider,
           "binding_ref": binding_ref,
           "project_identity": project_identity,
       }
       response = self._request_with_retry(
           "POST",
           self._BIND_VALIDATE_PATH,
           json=payload,
       )
       result: dict[str, Any] = response.json()
       return result
   ```

**Files**: `src/specify_cli/tracker/saas_client.py`

## Definition of Done

- [ ] 4 new methods exist on `SaaSTrackerClient`
- [ ] Each uses `_request_with_retry` (inherits auth, retry, error handling)
- [ ] `bind_confirm` sends `Idempotency-Key` header (not `X-Idempotency-Key`)
- [ ] `bind_confirm` auto-generates UUID4 if no key provided
- [ ] All 4 path constants defined
- [ ] `ruff check src/specify_cli/tracker/saas_client.py`
- [ ] `mypy src/specify_cli/tracker/saas_client.py`

## Risks

- **uuid import**: Already imported in `saas_client.py` for existing `push()` method. No new import needed.
- **Method naming**: Use snake_case matching existing convention (`bind_resolve`, not `bindResolve`).

## Reviewer Guidance

- Verify each method matches the contract in contracts/ directory (method, path, params/body)
- Verify `Idempotency-Key` header (not `X-Idempotency-Key`) on bind_confirm
- Check that no method has hardcoded response parsing — all return raw `response.json()`

## Activity Log

- 2026-04-04T10:06:35Z – coordinator – shell_pid=13966 – Started implementation via workflow command
- 2026-04-04T10:08:34Z – coordinator – shell_pid=13966 – Ready for review: 4 new methods (resources, bind_resolve, bind_confirm, bind_validate) and 4 path constants added to SaaSTrackerClient
- 2026-04-04T10:09:00Z – codex – shell_pid=22788 – Started review via workflow command
- 2026-04-04T10:14:49Z – codex – shell_pid=22788 – Moved to planned
- 2026-04-04T10:15:11Z – coordinator – shell_pid=37818 – Started implementation via workflow command
- 2026-04-04T10:17:42Z – coordinator – shell_pid=37818 – Added test_saas_client_new_methods.py per Codex review
- 2026-04-04T10:18:44Z – codex – shell_pid=55866 – Started review via workflow command
