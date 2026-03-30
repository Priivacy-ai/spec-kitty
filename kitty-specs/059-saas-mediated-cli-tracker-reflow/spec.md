# SaaS-Mediated CLI Tracker Reflow

## Overview

Migrate all CLI tracker commands for SaaS-backed providers (`linear`, `jira`, `github`, `gitlab`) from direct-connector local execution to SaaS API client mode. The CLI becomes a thin client that talks exclusively to Spec Kitty SaaS for these providers, using the frozen PRI-12 control-plane contract. Local/native providers (`beads`, `fp`) retain their direct execution paths unchanged. Azure DevOps support is removed entirely from the CLI tracker surface.

This is a hard break. Zero live users exist on the current direct-provider model. No compatibility shims, no fallback logic, no provider-secret smuggling.

## Problem Statement

The current CLI tracker implementation holds provider-native credentials locally and builds direct API connectors to Linear, Jira, GitHub, and GitLab. This model:

- Requires users to manage provider API keys/tokens in their local credential store
- Runs sync logic client-side, creating inconsistent state between CLI instances
- Uses a snapshot-publish model to push local state to SaaS, which is architecturally backwards
- Maintains Azure DevOps support that has no SaaS-side backing and no active users
- Splits authority over mappings, identity, and transport between CLI and SaaS

The SaaS control plane (PRI-14, complete) now provides the runtime for all tracker operations. The tracker SDK (PRI-15) is being repositioned as a SaaS-hosted engine. PRI-16 completes the chain by making the CLI a proper SaaS client.

## Actors

| Actor | Description |
|-------|-------------|
| CLI User | Developer or project lead using `spec-kitty tracker` commands to sync work packages with external trackers |
| Spec Kitty SaaS | The server-side control plane that owns provider transport, identity resolution, and sync execution |

## User Scenarios & Acceptance

### Scenario 1: Bind a SaaS-Backed Tracker

**Given** a user has authenticated via `spec-kitty auth login`
**When** they run `tracker bind --provider linear --project-slug my-project`
**Then** the CLI stores only SaaS-facing routing context (provider name and project slug). The team slug is derived from the existing auth credential store at call time, not stored redundantly in the binding. No provider-native API keys, tokens, or secrets are requested or stored.

### Scenario 2: Pull Issues Through SaaS

**Given** a bound SaaS-backed tracker
**When** the user runs `tracker sync pull`
**Then** the CLI calls `POST /api/v1/tracker/pull` on the SaaS, receives a `PullResultEnvelope` with normalized issues, and displays the results. The CLI never constructs a direct provider connector.

### Scenario 3: Push Changes Through SaaS (Sync or Async)

**Given** a bound SaaS-backed tracker with local changes
**When** the user runs `tracker sync push`
**Then** the CLI calls `POST /api/v1/tracker/push` with an `Idempotency-Key` header. If the SaaS returns 200, results are displayed immediately. If 202, the CLI polls `GET /api/v1/tracker/operations/{operation_id}` until terminal state (`completed` or `failed`), then displays the result.

### Scenario 4: Full Bidirectional Sync (Run)

**Given** a bound SaaS-backed tracker
**When** the user runs `tracker sync run`
**Then** the CLI calls `POST /api/v1/tracker/run` with an `Idempotency-Key` header, handling 200/202 as in push. The run is a single fixed full bidirectional sync operation.

### Scenario 5: Rejected Legacy Operations

**Given** a bound SaaS-backed tracker
**When** the user attempts `tracker map add`, `tracker sync publish`, or passes `--credential` flags to `tracker bind`
**Then** the CLI immediately fails with deterministic hard-break guidance: for credential flags, direct the user to authenticate via SaaS and connect the provider through the SaaS dashboard (not just "run auth login"); for `map add` and `sync publish`, state that the operation is not available for SaaS-backed providers and describe the replacement path.

### Scenario 6: Local Provider (Beads/FP) Unaffected

**Given** a project bound to `beads` or `fp`
**When** the user runs any tracker command
**Then** the existing direct local execution path is used. No SaaS calls are made.

### Scenario 7: Azure DevOps Removed

**Given** a user attempts to bind `azure_devops` or any Azure alias
**When** they run `tracker bind --provider azure_devops`
**Then** the CLI fails immediately with guidance that Azure DevOps is no longer supported.

### Scenario 8: Read-Only Mappings from SaaS

**Given** a bound SaaS-backed tracker
**When** the user runs `tracker map list`
**Then** the CLI calls `GET /api/v1/tracker/mappings` and displays the SaaS-authoritative mappings.

### Scenario 9: Tracker Status from SaaS

**Given** a bound SaaS-backed tracker
**When** the user runs `tracker status`
**Then** the CLI calls `GET /api/v1/tracker/status` and displays SaaS-backed binding state, not just local config.

### Scenario 10: Auth Refresh on 401

**Given** a SaaS-backed tracker operation
**When** the SaaS returns 401
**Then** the CLI attempts exactly one token refresh via `POST /api/v1/token/refresh/`, retries the original request once. If the refresh also fails, the CLI halts and instructs re-login.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | For SaaS-backed providers (linear, jira, github, gitlab), `tracker bind` stores only provider name and project slug. The team slug is derived from the auth credential store at call time, not stored in the binding. No provider-native credentials are requested, accepted, or stored. | Proposed |
| FR-002 | For SaaS-backed providers, `tracker sync pull` calls `POST /api/v1/tracker/pull` with the bound provider and project slug in the request body, plus `X-Team-Slug` header from the credential store, using the stored SaaS bearer token. | Proposed |
| FR-003 | For SaaS-backed providers, `tracker sync push` calls `POST /api/v1/tracker/push` with an `Idempotency-Key` header (UUID). | Proposed |
| FR-004 | For SaaS-backed providers, `tracker sync run` calls `POST /api/v1/tracker/run` with an `Idempotency-Key` header (UUID). | Proposed |
| FR-005 | When `push` or `run` returns HTTP 202, the CLI polls `GET /api/v1/tracker/operations/{operation_id}` at reasonable intervals until the operation reaches `completed` or `failed` state. | Proposed |
| FR-006 | For SaaS-backed providers, `tracker status` calls `GET /api/v1/tracker/status` and displays SaaS-backed binding/sync state. | Proposed |
| FR-007 | For SaaS-backed providers, `tracker map list` calls `GET /api/v1/tracker/mappings` and displays read-only mappings from SaaS. | Proposed |
| FR-008 | `tracker map add` fails immediately with clear guidance for SaaS-backed providers. Mappings are read-only from the CLI in this phase. | Proposed |
| FR-009 | `tracker sync publish` fails immediately with clear guidance for SaaS-backed providers. The snapshot-publish model is not a supported execution path. | Proposed |
| FR-010 | `tracker bind` with `--credential` flags for a SaaS-backed provider fails immediately with deterministic hard-break guidance: the user must authenticate via `spec-kitty auth login` and connect the provider through the SaaS dashboard. The guidance must not assume the user is unauthenticated -- they may already be logged in but attempting a forbidden legacy path. | Proposed |
| FR-011 | `tracker unbind` for SaaS-backed providers removes the local SaaS-facing routing context (provider, project slug). It does not attempt to clear provider-native secrets (none exist). | Proposed |
| FR-012 | `tracker providers` list reflects only currently supported providers: `linear`, `jira`, `github`, `gitlab`, `beads`, `fp`. Azure DevOps is removed. | Proposed |
| FR-013 | `tracker bind --provider azure_devops` (and aliases `azure-devops`, `azure`) fails with a clear message that Azure DevOps is no longer supported. | Proposed |
| FR-014 | For `beads` and `fp`, all existing direct local execution paths (bind with credentials, sync pull/push/run via local connector, map add/list via local SQLite) continue to work unchanged. | Proposed |
| FR-015 | All SaaS tracker API calls include the `X-Team-Slug` header derived at call time from the team slug in the auth credential store. The team slug is never redundantly stored in the tracker binding. | Proposed |
| FR-016 | On HTTP 401 from any SaaS tracker endpoint, the CLI attempts exactly one token refresh and retries the original request. If refresh fails, the CLI halts with re-login guidance. | Proposed |
| FR-017 | SaaS error responses are parsed using the frozen error envelope schema (`code`, `category`, `message`, `retryable`, `user_action_required`, `source`). The CLI displays the `message` and `user_action_required` fields to the user. | Proposed |
| FR-018 | On HTTP 429, the CLI respects `retry_after_seconds` from the error envelope before retrying. | Proposed |
| FR-019 | A dedicated SaaS tracker client module is introduced in `specify_cli/tracker/` that encapsulates all SaaS API communication, auth header injection, error parsing, and operation polling. | Proposed |
| FR-020 | The SaaS tracker client reuses the existing `CredentialStore` from `sync/auth.py` for bearer tokens and `SyncConfig` from `sync/config.py` for server URL. No duplicate auth/config plumbing is created. | Proposed |
| FR-021 | All Azure DevOps-specific code is removed from: `factory.py` (connector building), `tracker.py` (CLI help text, provider lists), `service.py` (routing/config), and any associated tests. | Proposed |
| FR-022 | The `build_connector()` factory function is retained only for `beads` and `fp`. All SaaS-backed provider entries are removed from it. | Proposed |
| FR-023 | `TrackerService` is refactored to dispatch SaaS-backed providers to the SaaS tracker client and local providers to the existing direct connector path. The split is explicit, not conditional wrapping. | Proposed |
| FR-024 | JSON output (`--json` flag) for all tracker commands remains coherent, with response shapes reflecting SaaS envelope structures for SaaS-backed providers. | Proposed |
| FR-025 | Help text for all tracker commands clearly distinguishes SaaS-backed provider behavior from local provider behavior. | Proposed |
| FR-026 | The `SPEC_KITTY_ENABLE_SAAS_SYNC` feature flag continues to gate the tracker command surface for stealth development. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | Operation polling for async 202 responses completes or times out within a bounded period. | Timeout after 5 minutes of polling with exponential backoff (1s, 2s, 4s, ..., cap at 30s). |
| NFR-002 | SaaS tracker client error messages are actionable and human-readable. | Every error displayed to the user includes the SaaS-provided `message` and, when present, `user_action_required` guidance. |
| NFR-003 | New code has test coverage for the SaaS client path. | 90%+ line coverage on new modules (SaaS tracker client, refactored service dispatch, CLI command changes). |
| NFR-004 | Type checking passes on all new and modified code. | `mypy --strict` produces zero errors on changed files. |

## Constraints

| ID | Constraint |
|----|------------|
| C-001 | The frozen PRI-12 control-plane contract (openapi.yaml, contract-narrative.md) is authoritative. No endpoint paths, request/response schemas, or error codes may be invented or modified. |
| C-002 | No new auth families or credential stores. Reuse `sync/auth.py:CredentialStore` and `sync/config.py:SyncConfig`. |
| C-003 | No mapping write operations from the CLI. Mappings are read-only in this phase. |
| C-004 | No direct-provider execution for SaaS-backed providers. The CLI must not construct connectors to Linear, Jira, GitHub, or GitLab. |
| C-005 | No fallback logic. If the SaaS path fails, the CLI fails -- it does not silently fall back to direct-provider execution. |
| C-006 | No new SaaS runtime behavior. This feature is CLI-only. Server-side changes belong in spec-kitty-saas. |
| C-007 | No restoration of the snapshot-publish model for SaaS-backed providers. |
| C-008 | Azure DevOps removal is intentional cleanup, not "out of scope" deferral. All CLI tracker surface for Azure DevOps must be removed. |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | For SaaS-backed providers, the CLI operates without provider-native credentials anywhere in the tracker command path. |
| SC-002 | `tracker sync pull/push/run` for SaaS-backed providers make HTTP calls to the SaaS control plane, not to provider APIs. |
| SC-003 | `tracker sync publish` and `tracker map add` fail immediately for SaaS-backed providers with actionable guidance. |
| SC-004 | `push` and `run` correctly handle both synchronous (200) and asynchronous (202 + polling) responses. |
| SC-005 | `beads` and `fp` direct local paths work identically to before this change. |
| SC-006 | Azure DevOps is fully removed from the CLI tracker surface (provider lists, factory, bind, help text, tests, config routing). |
| SC-007 | The SaaS tracker client reuses existing auth/config infrastructure with zero duplication. |
| SC-008 | The codebase is simpler after this change, not more compatibility-wrapped. Net lines of tracker code decrease or remain flat despite adding SaaS client logic. |
| SC-009 | All tests pass, including new tests covering SaaS client paths, hard-break rejections, and operation polling. |

## Key Entities

| Entity | Description |
|--------|-------------|
| SaaS Tracker Client | New module that encapsulates HTTP communication with the SaaS tracker endpoints, including auth header injection, error envelope parsing, and 202 operation polling. |
| Tracker Binding (SaaS) | Local config storing provider name and project slug for SaaS-backed providers. Team slug is derived from the auth credential store at call time. No secrets. |
| Tracker Binding (Local) | Existing local config with optional credentials for `beads` and `fp`. |
| NormalizedIssue | Standard issue representation from the SaaS contract (ref, title, status, type, priority, assignees, labels, etc.). |
| PullResultEnvelope | SaaS response for pull operations (status, summary, items, identity_path, pagination). |
| PushResultEnvelope | SaaS response for push operations (status, summary, items with outcomes, identity_path). |
| RunResultEnvelope | SaaS response for run operations (composite pull + push phases, identity_path). |
| OperationAccepted | Async response (202) with operation_id for polling. |
| ErrorEnvelope | Normalized SaaS error (code, category, message, retryable, user_action_required, source). |
| IdentityPath | SaaS-resolved identity context (installation or user_link scope, provider account). |

## Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| PRI-12: Control Plane Contract Freeze | Complete | Provides the frozen API contract this feature implements against. |
| PRI-14: SaaS Control Plane Runtime | Complete | Server-side implementation of all tracker endpoints. |
| PRI-15: Tracker SDK Repositioning | In Progress | Aligns the tracker SDK as SaaS-hosted engine. Not a hard blocker for CLI work -- the CLI talks to SaaS, not the SDK directly. |
| Existing `sync/auth.py` auth stack | Available | Bearer/refresh token management, credential store. |
| Existing `sync/config.py` server config | Available | SaaS server URL configuration. |

## Assumptions

| # | Assumption |
|---|------------|
| A-001 | The SaaS control plane endpoints (`/api/v1/tracker/*`) are deployed and functional before this CLI work ships. |
| A-002 | The `SPEC_KITTY_ENABLE_SAAS_SYNC` feature flag is sufficient to gate all tracker commands during stealth development. |
| A-003 | The SaaS handles all provider OAuth/installation setup out of band (via web UI). The CLI's role is to authenticate the user to SaaS, not to set up provider connections. |
| A-004 | Local SQLite cache (`TrackerSqliteStore`) is no longer needed for SaaS-backed providers since the SaaS owns all state. Local cache may be retained for `beads`/`fp` only. |
| A-005 | The `TrackerCredentialStore` section for provider-native secrets (`[tracker.providers.*]`) can be left in place for `beads`/`fp` but is never written to for SaaS-backed providers. |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SaaS endpoints not ready when CLI ships | Low | High | Feature flag gates all tracker commands. CLI can be merged before SaaS is production-ready. |
| Network-dependent operations degrade CLI UX | Medium | Medium | Clear timeout behavior, actionable error messages, and the error envelope's `retryable` + `user_action_required` fields. |
| Users have existing Azure DevOps bindings in local config | Low | Low | Zero live users confirmed. Stale local config is inert -- the CLI will not recognize the provider. Migration tooling, if needed, belongs to PRI-17. |

## Out of Scope

- Server-side changes to spec-kitty-saas (belongs to PRI-14/PRI-15)
- Mapping write operations from CLI (deferred to future phase)
- New auth families or OAuth flows in the CLI
- WebSocket-based real-time tracker sync
- Migration tooling for existing direct-provider bindings (belongs to PRI-17)
- Canonical event expansion beyond existing contract
