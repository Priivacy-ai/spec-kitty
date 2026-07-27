---
work_package_id: WP03
title: SaaS Client Transport Extensions
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
planning_base_branch: feat/implement-review-skill
merge_target_branch: feat/implement-review-skill
branch_strategy: Planning artifacts for this feature were generated on feat/implement-review-skill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/implement-review-skill unless the human explicitly redirects the landing branch.
subtasks: [T013, T014, T015, T016, T017]
history:
- date: '2026-04-01'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/saas_client.py
execution_mode: code_change
owned_files:
- src/specify_cli/tracker/saas_client.py
- tests/sync/tracker/test_saas_client_origin.py
---

# WP03: SaaS Client Transport Extensions

## Objective

Add `search_issues()` and `bind_mission_origin()` methods to `SaaSTrackerClient` in `src/specify_cli/tracker/saas_client.py`. These define the Python-level dependency boundary for provider-backed issue search and origin binding. HTTP wire format is Team B's responsibility — use placeholder endpoint paths.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Implementation command**: `spec-kitty implement WP03`
- No dependencies — can run in parallel with WP01, WP02, WP04.

## Context

- **Spec**: `kitty-specs/061-ticket-first-mission-origin-binding/spec.md` — "SaaSTrackerClient Extensions" section
- **Plan**: `kitty-specs/061-ticket-first-mission-origin-binding/plan.md` — D5 (placeholder paths)
- **Existing code**: `src/specify_cli/tracker/saas_client.py` — study `pull()`, `push()`, `status()` for patterns
- **Test patterns**: `tests/sync/tracker/test_saas_client.py` — `_make_response()` helper, `@patch("httpx.Client")`

## Subtasks

### T013: Add path constants

**File**: `src/specify_cli/tracker/saas_client.py`

Add to the class constants section (after `_OPERATIONS_PATH`):

```python
_SEARCH_ISSUES_PATH = "/api/v1/tracker/issues/search/"
_BIND_ORIGIN_PATH = "/api/v1/tracker/origin/bind/"
```

These are placeholder paths. Team B will define the actual wire format. When they do, only these constants need updating.

### T014: Implement `search_issues()`

**File**: `src/specify_cli/tracker/saas_client.py`

```python
def search_issues(
    self,
    provider: str,
    project_slug: str,
    *,
    query_text: str | None = None,
    query_key: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """POST search endpoint — find candidate issues for origin binding.

    Returns a dict with 'candidates' list and routing context
    ('resource_type', 'resource_id').

    query_key takes precedence over query_text when both provided.
    """
    payload: dict[str, Any] = {
        "provider": provider,
        "project_slug": project_slug,
        "limit": limit,
    }
    if query_key is not None:
        payload["query_key"] = query_key
    if query_text is not None:
        payload["query_text"] = query_text

    response = self._request_with_retry("POST", self._SEARCH_ISSUES_PATH, json=payload)
    result: dict[str, Any] = response.json()
    return result
```

**Key points**:
- Uses `_request_with_retry()` for automatic 401 refresh and 429 retry
- `query_key` takes precedence (both may be present in the payload — SaaS decides)
- Returns raw dict — the service layer in `origin.py` converts to typed dataclasses
- Error handling (401/403 user-action-required, 404, 422) is handled by `_request_with_retry()` existing logic

### T015: Implement `bind_mission_origin()`

**File**: `src/specify_cli/tracker/saas_client.py`

```python
def bind_mission_origin(
    self,
    provider: str,
    project_slug: str,
    *,
    feature_slug: str,
    external_issue_id: str,
    external_issue_key: str,
    external_issue_url: str,
    title: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """POST bind endpoint — create MissionOriginLink on SaaS.

    This is the authoritative write for the control-plane record.
    Same-origin re-bind returns success (no-op). Different-origin
    returns 409.
    """
    key = idempotency_key or str(uuid.uuid4())
    payload: dict[str, Any] = {
        "provider": provider,
        "project_slug": project_slug,
        "feature_slug": feature_slug,
        "external_issue_id": external_issue_id,
        "external_issue_key": external_issue_key,
        "external_issue_url": external_issue_url,
        "title": title,
    }
    response = self._request_with_retry(
        "POST",
        self._BIND_ORIGIN_PATH,
        json=payload,
        headers={"Idempotency-Key": key},
    )
    result: dict[str, Any] = response.json()
    return result
```

**Key points**:
- Uses `Idempotency-Key` header (same pattern as `push()`)
- Does NOT handle 202/polling — bind is expected to be synchronous
- 409 (different-origin conflict) is raised as `SaaSTrackerClientError` by `_request_with_retry()`

### T016: Write tests for `search_issues()`

**File**: `tests/sync/tracker/test_saas_client_origin.py` (new file)

Use the existing test pattern: `@patch("specify_cli.tracker.saas_client.httpx.Client")` + `_make_response()`.

**Test cases**:
1. **200 with candidates**: Returns dict with `candidates` list
2. **200 empty**: Returns dict with empty `candidates` list
3. **query_key precedence**: Both query_key and query_text sent in payload
4. **401/403 user_action_required**: Raises `SaaSTrackerClientError` after refresh attempt
5. **404 no mapping**: Raises `SaaSTrackerClientError`
6. **422 invalid query**: Raises `SaaSTrackerClientError`
7. **429 rate limited**: Retries once, then raises on second 429
8. **Auth headers**: Verify `Authorization` and `X-Team-Slug` headers sent

**Fixtures**: Reuse `mock_credential_store`, `mock_sync_config`, `client` fixture pattern from existing tests.

### T017: Write tests for `bind_mission_origin()`

**Test cases**:
1. **200 success**: Returns confirmation with `origin_link_id` and `bound_at`
2. **200 same-origin no-op**: Returns success with existing `origin_link_id`
3. **409 different-origin**: Raises `SaaSTrackerClientError`
4. **401/403**: Raises after refresh attempt
5. **Idempotency-Key header**: Verify header is sent (auto-generated or provided)

## Definition of Done

- [ ] `_SEARCH_ISSUES_PATH` and `_BIND_ORIGIN_PATH` constants defined
- [ ] `search_issues()` method implemented with correct signature
- [ ] `bind_mission_origin()` method implemented with idempotency key
- [ ] All HTTP-layer tests pass (200, 401, 404, 409, 422, 429)
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes

## Risks

- **Medium**: SaaS endpoints are placeholders. If Team B's wire format diverges significantly from the payload shape, the method bodies may need adjustment. However, the method signatures and error semantics are the stable contract — only the internal HTTP details change.

## Reviewer Guidance

- Verify `search_issues()` uses `_request_with_retry()` (not raw `_request()`)
- Verify `bind_mission_origin()` sends `Idempotency-Key` header
- Verify no async/polling logic in bind (unlike `push()`, bind is synchronous)
- Verify error semantics match the spec's error table

## Activity Log

- 2026-04-01T18:00:04Z – unknown – Implementation complete: 17 tests passing, 42 existing tests still green. Ready for review.
- 2026-04-01T18:03:47Z – unknown – Done override: Code merged to feat/implement-review-skill from worktree branches; all tests passing; review approved by Codex reviewer
