---
work_package_id: WP06
title: Client HTTP Contract Tests
dependencies: []
requirement_refs:
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: bde753a571652244ab6f1a22b21dc2cf67181529
created_at: '2026-04-04T10:26:38.922434+00:00'
subtasks: [T024, T025, T026, T027, T028, T029]
shell_pid: '4472'
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: tests/sync/tracker/
execution_mode: code_change
owned_files: [tests/sync/tracker/test_saas_client_discovery.py]
---

# WP06: Client HTTP Contract Tests

## Objective

Write HTTP-level contract tests for all 4 new endpoints and the binding_ref routing variant on existing endpoints. These tests mock at the `httpx.Response` level using the existing `_make_response()` pattern from `test_saas_client.py`. This is the "client mocks HTTP" tier of the two-tier test strategy.

## Context

- **Plan**: Two-tier test strategy — client tests mock HTTP transport
- **Research**: Decision 1 (test architecture)
- **Contracts**: All files in contracts/ directory
- **Current tests**: `tests/sync/tracker/test_saas_client.py` — uses `_make_response()` helper, `mock_credential_store`, `mock_sync_config`, `client` fixtures
- **Pattern**: Each test patches `SaaSTrackerClient._request` to return a fake `httpx.Response`

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

Depends on WP04 (new methods) and WP05 (updated signatures).

## Subtasks

### T024: HTTP Tests for resources()

**Purpose**: Verify wire contract for GET /api/v1/tracker/resources/.

**Steps**:
1. Create `tests/sync/tracker/test_saas_client_discovery.py`
2. Copy fixtures from `test_saas_client.py` (`_make_response`, `mock_credential_store`, `mock_sync_config`, `client`)
3. Add tests:
   - `test_resources_sends_get_with_provider_param`: verify method=GET, path includes `provider=linear`
   - `test_resources_parses_response`: verify dict returned with `resources` list
   - `test_resources_empty_list`: verify empty resources is valid (not error)
   - `test_resources_403_no_installation`: verify 403 raises SaaSTrackerClientError

**Files**: `tests/sync/tracker/test_saas_client_discovery.py` (new)

### T025: HTTP Tests for bind_resolve()

**Purpose**: Verify wire contract for POST /api/v1/tracker/bind-resolve/.

**Steps**:
1. Add tests:
   - `test_bind_resolve_sends_post_with_body`: verify method=POST, body has `provider` + `project_identity`
   - `test_bind_resolve_exact_match`: verify response with `match_type=exact` parsed correctly
   - `test_bind_resolve_candidates`: verify candidates array parsed
   - `test_bind_resolve_none`: verify none match type

**Files**: `tests/sync/tracker/test_saas_client_discovery.py`

### T026: HTTP Tests for bind_confirm()

**Purpose**: Verify wire contract for POST /api/v1/tracker/bind-confirm/.

**Steps**:
1. Add tests:
   - `test_bind_confirm_sends_post_with_body`: verify body has `provider`, `candidate_token`, `project_identity`
   - `test_bind_confirm_sends_idempotency_key`: verify `Idempotency-Key` header is sent
   - `test_bind_confirm_auto_generates_key`: verify UUID4 format when no key provided
   - `test_bind_confirm_400_invalid_token`: verify raises on token rejection
   - `test_bind_confirm_409_already_bound`: verify raises on conflict

**Files**: `tests/sync/tracker/test_saas_client_discovery.py`

### T027: HTTP Tests for bind_validate()

**Purpose**: Verify wire contract for POST /api/v1/tracker/bind-validate/.

**Steps**:
1. Add tests:
   - `test_bind_validate_sends_post_with_body`: verify body has `provider`, `binding_ref`, `project_identity`
   - `test_bind_validate_valid_response`: verify `valid=true` response parsed with display metadata
   - `test_bind_validate_invalid_response`: verify `valid=false` response parsed with reason and guidance
   - `test_bind_validate_both_return_200`: verify neither raises (both are 200)

**Files**: `tests/sync/tracker/test_saas_client_discovery.py`

### T028: HTTP Tests for Existing Endpoints with binding_ref

**Purpose**: Verify existing endpoints accept binding_ref routing.

**Steps**:
1. Add tests for `status()`:
   - `test_status_with_binding_ref`: verify `binding_ref` in query params
   - `test_status_with_project_slug`: verify `project_slug` in query params (legacy)
   - `test_status_binding_ref_takes_precedence`: when both provided, only binding_ref sent
2. Add similar tests for `mappings()`, `pull()`, `push()`, `run()` (at least one representative POST test)
3. Add test for missing both:
   - `test_status_missing_both_raises`: verify SaaSTrackerClientError raised

**Files**: `tests/sync/tracker/test_saas_client_discovery.py`

### T029: Tests for Stale-Binding Error Codes

**Purpose**: Verify enriched error attributes are preserved for stale-binding codes.

**Steps**:
1. Add tests:
   - `test_binding_not_found_error_code`: mock 404 with `error_code: "binding_not_found"` → verify `e.error_code`
   - `test_mapping_disabled_error_code`: mock 403 with `error_code: "mapping_disabled"` → verify `e.error_code`
   - `test_project_mismatch_error_code`: mock 403 with `error_code: "project_mismatch"` → verify `e.error_code`
   - `test_error_code_none_when_missing`: mock 500 with no `error_code` → verify `e.error_code is None`

**Files**: `tests/sync/tracker/test_saas_client_discovery.py`

## Definition of Done

- [ ] `test_saas_client_discovery.py` exists with tests for all 4 new endpoints
- [ ] Tests for existing endpoints with binding_ref routing variant
- [ ] Tests for stale-binding error codes
- [ ] All tests pass: `python -m pytest tests/sync/tracker/test_saas_client_discovery.py -x -q`
- [ ] Uses existing `_make_response()` pattern (no new test infrastructure)

## Risks

- **Fixture duplication**: `_make_response()` and client fixtures exist in `test_saas_client.py`. Either import them or duplicate. Duplicating is acceptable to avoid cross-file test coupling. If sharing, use a conftest.py.

## Reviewer Guidance

- Verify each test asserts the HTTP method, path, and params/body shape (not just response parsing)
- Verify `Idempotency-Key` header name (not `X-Idempotency-Key`)
- Check that binding_ref precedence test verifies project_slug is NOT in the params when binding_ref is provided
