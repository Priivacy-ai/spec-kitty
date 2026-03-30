---
work_package_id: WP01
title: SaaS Tracker Client
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-015
- FR-016
- FR-017
- FR-018
- FR-019
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: c5ece9e6b5bd8040663586949c076f2d98f0763d
created_at: '2026-03-30T19:25:37.017619+00:00'
subtasks: [T001, T002, T003, T004, T005, T006, T007]
shell_pid: "48023"
agent: "codex"
history:
- at: '2026-03-30T19:14:19+00:00'
  event: created
  actor: planner
authoritative_surface: src/specify_cli/tracker/saas_client.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/tracker/saas_client.py
- tests/sync/tracker/test_saas_client.py
---

# WP01: SaaS Tracker Client

## Objective

Create `src/specify_cli/tracker/saas_client.py` — the low-level HTTP transport layer for all SaaS tracker API communication. This module encapsulates authenticated requests, error envelope parsing, retry behaviors (401/429), and 202 operation polling. Every SaaS-backed tracker operation flows through this client.

## Context

- **Frozen contract**: All endpoint paths, request/response schemas, and error codes come from the PRI-12 contract (see `spec-kitty-planning/kitty-specs/024-control-plane-contract-freeze/contracts/openapi.yaml`).
- **Auth reuse**: Bearer tokens come from `specify_cli.sync.auth.CredentialStore`. Server URL comes from `specify_cli.sync.config.SyncConfig`. Do not create duplicate auth/config plumbing.
- **No fallbacks**: If a SaaS call fails, the CLI fails. No silent fallback to direct-provider execution.

## Implementation Command

```bash
spec-kitty implement WP01
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- No dependencies — branch directly from `main`.

---

## Subtask T001: Create SaaSTrackerClient Class Skeleton

**Purpose**: Establish the module structure and constructor that wires up auth and config dependencies.

**Steps**:
1. Create `src/specify_cli/tracker/saas_client.py`
2. Define `SaaSTrackerClientError(RuntimeError)` for client-level failures
3. Define `SaaSTrackerClient` class with constructor:
   ```python
   class SaaSTrackerClient:
       def __init__(
           self,
           credential_store: CredentialStore | None = None,
           sync_config: SyncConfig | None = None,
       ) -> None:
   ```
   - If `credential_store` is None, create a default `CredentialStore()`
   - If `sync_config` is None, create a default `SyncConfig()`
   - Store both as instance attributes
   - Resolve `self._base_url` from `sync_config.get_server_url()` once at construction

**Files**: `src/specify_cli/tracker/saas_client.py` (new, ~30 lines for skeleton)

**Imports needed**:
```python
from specify_cli.sync.auth import AuthClient, CredentialStore
from specify_cli.sync.config import SyncConfig
```

---

## Subtask T002: Implement _request() Base Method

**Purpose**: Single entry point for all HTTP calls. Handles auth header injection, team slug header, server URL resolution, and response parsing.

**Steps**:
1. Implement `_request(self, method: str, path: str, *, json: dict | None = None, headers: dict | None = None, params: dict | None = None) -> httpx.Response`
2. Build headers:
   - `Authorization: Bearer {self._credential_store.get_access_token()}` — call `get_access_token()` at request time (not at construction)
   - `X-Team-Slug: {self._credential_store.get_team_slug()}` — derived at call time per FR-015
   - Merge any additional headers from caller
3. Build full URL: `{self._base_url}{path}` (path starts with `/api/v1/tracker/...`)
4. Use `httpx.Client` (synchronous) with a reasonable timeout (30s default, configurable)
5. Return the raw `httpx.Response` — callers handle status-specific logic

**Important**: Do not use `httpx.AsyncClient`. CLI operations are sequential; sync httpx is simpler.

**Files**: `src/specify_cli/tracker/saas_client.py` (~40 lines)

---

## Subtask T003: Implement Retry Behaviors

**Purpose**: Handle 401 (auth refresh), 429 (rate limit), and network errors per the frozen contract.

**Steps**:

1. **401 refresh + retry** (FR-016):
   - Wrap `_request()` in a method `_request_with_retry()` that:
     - Calls `_request()`
     - If response is 401, call `AuthClient(self._credential_store).refresh_tokens()`
     - Retry the original request exactly once
     - If the retry also returns 401, raise `SaaSTrackerClientError` with re-login guidance: "Session expired. Run `spec-kitty auth login` to re-authenticate."
     - If refresh itself fails, raise with same guidance

2. **429 rate limit** (FR-018):
   - If response is 429, parse error envelope for `retry_after_seconds`
   - `time.sleep(retry_after_seconds)` then retry once
   - If still 429 after retry, raise with the error message

3. **Network errors**:
   - Catch `httpx.ConnectError`, `httpx.TimeoutException`
   - Raise `SaaSTrackerClientError` with clear message: "Cannot connect to Spec Kitty SaaS at {url}. Check your network connection."
   - No fallback. No retry for network errors.

4. **Error envelope parsing** (FR-017):
   - Define `_parse_error_envelope(response: httpx.Response) -> dict` that extracts:
     - `code`, `category`, `message`, `retryable`, `user_action_required`, `source`
     - `retry_after_seconds` (optional, for 429)
   - For non-2xx responses (except 401/429 handled above), parse the envelope and raise `SaaSTrackerClientError` with `message` and `user_action_required` fields

**Files**: `src/specify_cli/tracker/saas_client.py` (~80 lines)

**Edge cases**:
- 401 on refresh call itself → halt, don't loop
- Malformed error envelope (not JSON) → generic error with status code
- Missing `retry_after_seconds` on 429 → default to 5 seconds

---

## Subtask T004: Implement Synchronous Endpoints

**Purpose**: Implement pull(), status(), and mappings() — the three endpoints that always return 200 (never 202).

**Steps**:

1. **pull(provider, project_slug, *, limit=100, cursor=None, filters=None) -> dict**:
   - POST `/api/v1/tracker/pull`
   - Request body: `{"provider": provider, "project_slug": project_slug, "limit": limit}`
   - Add optional `cursor` and `filters` (updated_since, status[], issue_type[]) if provided
   - Parse 200 response as `PullResultEnvelope` (return raw dict)
   - No Idempotency-Key needed

2. **status(provider, project_slug) -> dict**:
   - GET `/api/v1/tracker/status`
   - Query params: `provider`, `project_slug`
   - Parse 200 response (return raw dict)

3. **mappings(provider, project_slug) -> dict**:
   - GET `/api/v1/tracker/mappings`
   - Query params: `provider`, `project_slug`
   - Parse 200 response (return raw dict)

**Files**: `src/specify_cli/tracker/saas_client.py` (~60 lines)

**Contract reference**: All request/response shapes from PRI-12 OpenAPI. Return raw dicts — the service layer or CLI can interpret them.

---

## Subtask T005: Implement _poll_operation() with Exponential Backoff

**Purpose**: Poll an async operation until terminal state per FR-005 and NFR-001.

**Steps**:

1. Implement `_poll_operation(self, operation_id: str) -> dict`:
   - Poll `GET /api/v1/tracker/operations/{operation_id}`
   - Exponential backoff: initial=1s, factor=2, cap=30s
   - Add jitter: `delay * (0.8 + 0.4 * random.random())`
   - Total timeout: 300 seconds (5 minutes)
   - On each poll:
     - `pending` or `running` → continue polling
     - `completed` → return `result` field (the envelope)
     - `failed` → raise `SaaSTrackerClientError` from the `error` field
   - On timeout → raise `SaaSTrackerClientError("Operation {id} timed out after 5 minutes")`

2. Use `time.monotonic()` for timeout tracking (not wall clock)

**Files**: `src/specify_cli/tracker/saas_client.py` (~50 lines)

**Testing note**: Mock `time.sleep` in tests to avoid real delays. Use `time.monotonic` mock to control timeout.

---

## Subtask T006: Implement Async-Capable Endpoints (push, run)

**Purpose**: Implement push() and run() which may return 200 (sync) or 202 (async) per the frozen contract.

**Steps**:

1. **push(provider, project_slug, items, *, idempotency_key=None) -> dict**:
   - POST `/api/v1/tracker/push`
   - Request body: `{"provider": provider, "project_slug": project_slug, "items": items}`
   - Generate `Idempotency-Key: {uuid4()}` header (or use provided key)
   - If 200 → return response as `PushResultEnvelope` dict
   - If 202 → extract `operation_id`, call `_poll_operation()`, return result

2. **run(provider, project_slug, *, pull_first=True, limit=100, idempotency_key=None) -> dict**:
   - POST `/api/v1/tracker/run`
   - Request body: `{"provider": provider, "project_slug": project_slug, "pull_first": pull_first, "limit": limit}`
   - Generate `Idempotency-Key: {uuid4()}` header (or use provided key)
   - If 200 → return response as `RunResultEnvelope` dict
   - If 202 → extract `operation_id`, call `_poll_operation()`, return result

**Files**: `src/specify_cli/tracker/saas_client.py` (~50 lines)

**Important**: The idempotency key must be a UUID string. Use `str(uuid.uuid4())`.

---

## Subtask T007: Write test_saas_client.py

**Purpose**: Comprehensive test coverage for the SaaS tracker client.

**Steps**:

1. Create `tests/sync/tracker/test_saas_client.py`
2. Use `unittest.mock.patch` to mock `httpx.Client` responses
3. Mock `CredentialStore` to return test tokens and team slug
4. Mock `SyncConfig` to return test server URL

**Test categories**:

a. **Auth injection tests**:
   - Verify `Authorization: Bearer <token>` header on every request
   - Verify `X-Team-Slug: <slug>` header on every request
   - Verify token is fetched at request time, not at construction

b. **Synchronous endpoint tests** (pull, status, mappings):
   - Test 200 response returns parsed dict
   - Test correct HTTP method and path for each
   - Test request body/params match contract

c. **Async endpoint tests** (push, run):
   - Test 200 sync response returns envelope dict
   - Test 202 → polls operation → completed → returns result
   - Test 202 → polls operation → failed → raises error
   - Test Idempotency-Key header is UUID format

d. **Polling tests**:
   - Test exponential backoff intervals (1s, 2s, 4s, ...)
   - Test timeout after 5 minutes
   - Test pending → running → completed progression

e. **Error handling tests**:
   - Test 401 → refresh → retry → success
   - Test 401 → refresh → 401 again → halt with re-login
   - Test 429 → wait retry_after → retry → success
   - Test 4xx error envelope parsing (code, category, message)
   - Test 5xx error envelope parsing
   - Test network error (ConnectError) → fail with message
   - Test malformed error response → generic error

**Files**: `tests/sync/tracker/test_saas_client.py` (new, ~400 lines)

---

## Definition of Done

- [ ] `SaaSTrackerClient` class created in `src/specify_cli/tracker/saas_client.py`
- [ ] All 6 endpoint methods implemented (pull, push, run, status, mappings, poll_operation)
- [ ] Auth injection uses `CredentialStore` (Bearer token + X-Team-Slug at call time)
- [ ] Error envelope parsing handles all frozen error codes
- [ ] 401 → one refresh + retry → halt on second failure
- [ ] 429 → respect retry_after_seconds
- [ ] 202 → exponential backoff polling (1s, 2s, 4s, cap 30s, timeout 5min)
- [ ] Network errors fail immediately with clear message
- [ ] No fallback logic anywhere
- [ ] `test_saas_client.py` covers all error paths and endpoint behaviors
- [ ] `mypy --strict` passes on new files
- [ ] No new dependencies added (httpx already in tree)

## Risks

- **httpx version compatibility**: Use `httpx.Client` (sync). Avoid async features.
- **Token expiry during polling**: The 5-minute polling window could outlast token expiry. The `_request_with_retry` handles 401 refresh, so polling requests are also protected.
- **Mock complexity**: Testing polling requires mocking time.sleep and time.monotonic. Use `unittest.mock.patch` carefully.

## Reviewer Guidance

- Verify all endpoint paths match PRI-12 contract exactly
- Verify error envelope parsing uses `code` and `category` as separate fields (not combined)
- Verify `ExternalRef` in request/response includes `workspace` field
- Verify no fallback paths exist — every error raises, never silently succeeds
- Verify `Idempotency-Key` is only on push and run, not on other endpoints
- Check that `X-Team-Slug` comes from `CredentialStore.get_team_slug()` at request time

## Activity Log

- 2026-03-30T19:25:37Z – orchestrator – shell_pid=46234 – lane=doing – Started implementation via workflow command
- 2026-03-30T19:31:21Z – orchestrator – shell_pid=46234 – lane=for_review – Ready for review: SaaS tracker client with 6 endpoints, auth/retry/polling, 37 passing tests, mypy strict clean
- 2026-03-30T19:32:35Z – codex – shell_pid=48023 – lane=doing – Started review via workflow command
- 2026-03-30T19:38:23Z – codex – shell_pid=48023 – lane=planned – Moved to planned
