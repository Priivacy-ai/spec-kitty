# Research: SaaS-Mediated CLI Tracker Reflow

## R-001: Frozen PRI-12 Wire Contract

**Decision**: Use the PRI-12 OpenAPI contract as the authoritative source for all SaaS tracker API calls.

**Rationale**: The contract was frozen in PRI-12 and implemented server-side in PRI-14. No contract redesign is permitted in PRI-16.

**Key findings**:
- 7 tracker endpoints: pull, push, run, status, health, mappings, operations/{id}
- Auth: Bearer JWT with one-refresh retry on 401
- Async: push and run may return 202 with `operation_id` for polling
- Headers: `Authorization`, `X-Team-Slug` (optional), `Idempotency-Key` (push/run only)
- Error envelope: `code`, `category`, `message`, `retryable`, `user_action_required`, `source`
- Providers: `linear`, `jira`, `github`, `gitlab` (enum, not extensible in this phase)

**Alternatives considered**: None. The contract is frozen.

## R-002: Auth Stack Reuse

**Decision**: Reuse `sync/auth.py:CredentialStore` for bearer tokens and `sync/config.py:SyncConfig` for server URL. Do not create a second auth store.

**Rationale**: Both modules are stable, tested, and already manage exactly the state the SaaS tracker client needs: JWT access/refresh tokens, team slug, and server URL.

**Key findings**:
- `CredentialStore` stores tokens at `~/.spec-kitty/credentials` (TOML, file-locked, 0o600)
- `CredentialStore.get_access_token()` checks expiry
- `CredentialStore.get_team_slug()` returns the team slug from auth session
- `CredentialStore.get_server_url()` returns the configured SaaS server URL
- `AuthClient.refresh_tokens()` handles the refresh flow
- `SyncConfig.get_server_url()` defaults to `https://spec-kitty-dev.fly.dev`

**Alternatives considered**: Creating a dedicated `TrackerAuthClient` -- rejected because it would duplicate token management already handled by `CredentialStore`.

## R-003: httpx for SaaS Tracker Client

**Decision**: Use httpx (synchronous mode) for the SaaS tracker client HTTP calls.

**Rationale**: httpx is already a dependency (used in `sync/auth.py:AuthClient`). It supports both sync and async modes. Since CLI tracker commands are inherently sequential (user waits for result), synchronous httpx is simpler than async.

**Key findings**:
- `AuthClient` in `sync/auth.py` uses `httpx.Client` for token endpoints
- httpx supports connection pooling, timeouts, and response streaming
- The existing `TrackerService.sync_publish()` already uses `httpx.post()` directly
- No need for `aiohttp` or `requests` -- httpx covers the requirement

**Alternatives considered**: `requests` -- rejected because httpx is already in the dependency tree and offers a more modern API with built-in timeout support.

## R-004: TrackerProjectConfig Binding Model

**Decision**: Add `project_slug` field to `TrackerProjectConfig` for SaaS-backed providers. Keep `workspace` for beads/fp only.

**Rationale**: The PRI-12 contract uses `provider` + `project_slug` as the routing key in request bodies, with `team_slug` from the auth session as the `X-Team-Slug` header. The current `workspace` field maps to a provider-native concept, not a SaaS routing concept.

**Key findings**:
- Current config: `provider`, `workspace`, `doctrine_mode`, `doctrine_field_owners`
- SaaS-backed binding: `provider` + `project_slug` (team_slug from auth store at call time)
- Local binding: `provider` + `workspace` (existing behavior for beads/fp)
- Config stored in `.kittify/config.yaml` under `tracker:` section
- `from_dict()` / `to_dict()` handle serialization -- need update for new field

**Alternatives considered**: Renaming `workspace` to `project_slug` globally -- rejected because beads/fp legitimately use `workspace` as a local concept.

## R-005: Operation Polling Strategy

**Decision**: Exponential backoff with jitter: 1s, 2s, 4s, 8s, 16s, 30s (cap), timeout at 5 minutes total.

**Rationale**: The PRI-12 contract specifies that push and run may return 202 with an `OperationAccepted` response. The CLI must poll until terminal state. Exponential backoff prevents hammering the server while keeping latency reasonable.

**Key findings**:
- Poll endpoint: `GET /api/v1/tracker/operations/{operation_id}`
- States: `pending` → `running` → `completed` (with result envelope) or `failed` (with error envelope)
- Completed operations return the same envelope shape as synchronous 200 responses
- The contract narrative does not mandate a specific polling interval -- implementation choice

**Alternatives considered**: Fixed 2s interval -- rejected because it wastes requests for long-running operations and provides no backpressure.

## R-006: Azure DevOps Removal Scope

**Decision**: Full removal of all Azure DevOps CLI surface: factory entries, config aliases, help text, tests.

**Rationale**: Azure DevOps is not in the frozen SaaS contract provider enum. Zero live users. The user confirmed removal is intentional cleanup, not "out of scope" deferral.

**Key findings**:
- `factory.py` has Azure DevOps connector building (imports `AzureDevOpsConnector`, `AzureDevOpsConfig`)
- `factory.py:normalize_provider()` handles aliases: `azure-devops` → `azure_devops`, `azure` → `azure_devops`
- No dedicated Azure DevOps tests found in the tracker test suite
- Azure DevOps connector comes from the `spec_kitty_tracker` external package -- the import just needs to be removed from factory.py

**Alternatives considered**: Keeping Azure DevOps as a direct-connector alongside beads/fp -- rejected per user direction.

## R-007: Test File Deletion Impact

**Decision**: Delete `test_service_publish.py` (10,526 lines). Replace coverage with new SaaS client and service tests.

**Rationale**: The snapshot publish model (`sync_publish()` method) is being removed for SaaS-backed providers. The test file exclusively tests that model. New tests will cover the SaaS client path which replaces it.

**Key findings**:
- `test_service_publish.py` tests: publish payload construction, resource routing, auth token handling, error cases
- All tested behavior maps to the old `TrackerService.sync_publish()` method which is being deleted
- No test in this file covers beads/fp or general service behavior
- Replacement coverage: `test_saas_client.py` (HTTP transport), `test_saas_service.py` (service operations)

**Alternatives considered**: Keeping a subset of tests -- rejected because the entire publish model is being removed, not modified.
