# Implementation Plan: SaaS-Mediated CLI Tracker Reflow

**Branch**: `main` | **Date**: 2026-03-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/059-saas-mediated-cli-tracker-reflow/spec.md`

## Summary

Migrate CLI tracker commands for SaaS-backed providers (linear, jira, github, gitlab) from direct-connector local execution to SaaS API client mode. Introduce a three-class service architecture: `TrackerService` (façade/dispatcher) → `SaaSTrackerService` (SaaS API client for linear/jira/github/gitlab) and `LocalTrackerService` (direct connector for beads/fp). Remove Azure DevOps entirely. Delete dead direct-connector code for SaaS-backed providers.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), httpx (HTTP client), ruamel.yaml (YAML config)
**Storage**: `.kittify/config.yaml` (project tracker binding); `~/.spec-kitty/credentials` (SaaS auth tokens); SQLite (local beads/fp store only)
**Testing**: pytest (90%+ coverage on new code), mypy --strict
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: Single Python package (spec-kitty CLI)
**Performance Goals**: CLI tracker operations complete within contract-defined timeouts; polling timeout at 5 minutes with exponential backoff
**Constraints**: Frozen PRI-12 wire contract is authoritative; no fallback to direct-provider execution; no new auth stores
**Scale/Scope**: ~1,375 lines in tracker module, ~15,700 lines in tracker tests. Net tracker code should decrease or remain flat.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | Already in use across codebase |
| typer for CLI | PASS | tracker.py already uses typer |
| rich for console output | PASS | Used for status/sync output |
| pytest with 90%+ coverage | PASS | Spec requires NFR-003 |
| mypy --strict | PASS | Spec requires NFR-004 |
| Integration tests for CLI commands | PASS | Will add integration tests for SaaS client paths |
| No 1.x backward compatibility required | PASS | On main (2.x active development) |
| Cross-platform | PASS | httpx + pathlib are cross-platform |

No constitution violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/059-saas-mediated-cli-tracker-reflow/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 implementer quick reference
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── tracker/
│   ├── __init__.py              # Public exports (feature flags + new service exports)
│   ├── service.py               # TrackerService façade/dispatcher (REFACTOR)
│   ├── saas_service.py          # NEW: SaaSTrackerService (SaaS API client operations)
│   ├── saas_client.py           # NEW: Low-level SaaS HTTP client (auth, polling, errors)
│   ├── local_service.py         # NEW: LocalTrackerService (beads/fp direct connector)
│   ├── config.py                # TrackerProjectConfig (MODIFY: project_slug for SaaS)
│   ├── factory.py               # build_connector() (MODIFY: remove SaaS-backed + Azure entries)
│   ├── credentials.py           # TrackerCredentialStore (KEEP: used by beads/fp only)
│   ├── store.py                 # TrackerSqliteStore (KEEP: used by beads/fp only)
│   └── feature_flags.py         # SaaS sync feature flag (KEEP)
├── sync/
│   ├── auth.py                  # CredentialStore + AuthClient (REUSE: bearer tokens)
│   └── config.py                # SyncConfig (REUSE: server URL)
└── cli/commands/
    └── tracker.py               # CLI commands (MODIFY: dispatch SaaS vs local)

tests/
├── sync/tracker/
│   ├── test_saas_client.py      # NEW: SaaS HTTP client tests
│   ├── test_saas_service.py     # NEW: SaaSTrackerService tests
│   ├── test_local_service.py    # NEW: LocalTrackerService tests
│   ├── test_service.py          # NEW: TrackerService façade dispatch tests
│   ├── test_credentials.py      # KEEP (beads/fp credential tests)
│   ├── test_store.py            # KEEP (beads/fp store tests)
│   └── test_service_publish.py  # DELETE (snapshot publish model removed)
└── agent/cli/commands/
    └── test_tracker.py          # MODIFY: test SaaS vs local CLI paths
```

**Structure Decision**: Three new modules in `specify_cli/tracker/` (`saas_client.py`, `saas_service.py`, `local_service.py`). Existing `service.py` becomes the thin façade. No new directories -- all files live in the existing `tracker/` package.

## Architecture

### Service Split Pattern

```
CLI (tracker.py)
  │
  ▼
TrackerService (service.py) ──── thin façade/dispatcher
  │                               - resolves config
  │                               - chooses backend by provider
  │                               - exposes CLI-oriented method surface
  │
  ├──▶ SaaSTrackerService (saas_service.py) ──── for linear, jira, github, gitlab
  │      │
  │      └──▶ SaaSTrackerClient (saas_client.py) ──── HTTP transport layer
  │             │                                       - auth header injection
  │             │                                       - 202 operation polling
  │             │                                       - error envelope parsing
  │             │                                       - retry on 401 (one refresh)
  │             │                                       - retry on 429 (respect retry_after)
  │             │
  │             └──▶ CredentialStore (sync/auth.py) ──── bearer/refresh tokens
  │             └──▶ SyncConfig (sync/config.py) ──── server URL
  │
  └──▶ LocalTrackerService (local_service.py) ──── for beads, fp
         │
         └──▶ build_connector() (factory.py) ──── direct local connector
         └──▶ TrackerSqliteStore (store.py) ──── local issue cache
         └──▶ TrackerCredentialStore (credentials.py) ──── local credentials
```

### Provider Classification

```python
SAAS_PROVIDERS = frozenset({"linear", "jira", "github", "gitlab"})
LOCAL_PROVIDERS = frozenset({"beads", "fp"})
REMOVED_PROVIDERS = frozenset({"azure_devops"})  # Hard-fail with guidance
```

### Config Model Changes

Current `TrackerProjectConfig`:
```python
@dataclass
class TrackerProjectConfig:
    provider: str | None = None
    workspace: str | None = None          # legacy field
    doctrine_mode: str = "external_authoritative"
    doctrine_field_owners: dict[str, str] = field(default_factory=dict)
```

New `TrackerProjectConfig`:
```python
@dataclass
class TrackerProjectConfig:
    provider: str | None = None
    project_slug: str | None = None       # SaaS-backed: project_slug for API routing
    workspace: str | None = None          # Local-only: beads/fp workspace identifier
    doctrine_mode: str = "external_authoritative"
    doctrine_field_owners: dict[str, str] = field(default_factory=dict)
```

For SaaS-backed providers, `project_slug` is the routing key in API request bodies. `team_slug` comes from `CredentialStore.get_team_slug()` at call time and is sent as the `X-Team-Slug` header. `workspace` is only used by beads/fp.

### SaaS Tracker Client Contract

The client implements the frozen PRI-12 API surface:

| Operation | Method | Path | Idempotency Key | Async (202)? |
|-----------|--------|------|-----------------|-------------|
| pull | POST | `/api/v1/tracker/pull` | No | No |
| push | POST | `/api/v1/tracker/push` | Yes (UUID) | Yes |
| run | POST | `/api/v1/tracker/run` | Yes (UUID) | Yes |
| status | GET | `/api/v1/tracker/status` | No | No |
| mappings | GET | `/api/v1/tracker/mappings` | No | No |
| poll operation | GET | `/api/v1/tracker/operations/{id}` | No | No |

All requests carry:
- `Authorization: Bearer <access_token>` (from `CredentialStore`)
- `X-Team-Slug: <team_slug>` (from `CredentialStore.get_team_slug()`)

Push/run requests carry:
- `Idempotency-Key: <uuid4>` header

### Error Handling Strategy

1. **HTTP 200**: Parse response envelope, return structured result
2. **HTTP 202**: Extract `operation_id`, begin polling loop (exponential backoff: 1s, 2s, 4s, ..., cap 30s, timeout 5min)
3. **HTTP 401**: Attempt one token refresh via `AuthClient.refresh_tokens()`, retry original request once. If refresh fails, halt with re-login guidance.
4. **HTTP 429**: Respect `retry_after_seconds` from error envelope before retrying
5. **HTTP 400 (legacy_flow_forbidden)**: Display deterministic hard-break guidance from error envelope
6. **HTTP 4xx/5xx**: Parse error envelope, display `message` + `user_action_required`, fail deterministically
7. **Network errors**: Fail immediately with clear network error message (no fallback)

### Hard-Break Enforcement Points

| Command | SaaS-backed behavior | Local behavior |
|---------|---------------------|----------------|
| `bind --credential` | HARD FAIL: "Authenticate via spec-kitty auth login and connect provider in SaaS dashboard" | Allowed (beads/fp) |
| `map add` | HARD FAIL: "Mappings are managed in the SaaS dashboard" | Allowed (beads/fp) |
| `sync publish` | HARD FAIL: "Snapshot publish is not supported. Use tracker sync push instead" | N/A (never had publish) |
| `bind --provider azure_devops` | HARD FAIL: "Azure DevOps is no longer supported" | N/A |

### Files to Delete

| File | Reason |
|------|--------|
| `tests/sync/tracker/test_service_publish.py` (10,526 lines) | Snapshot publish model removed for SaaS-backed providers |

### Files to Modify

| File | Change |
|------|--------|
| `src/specify_cli/tracker/service.py` | Gut to thin façade; move local logic to `local_service.py` |
| `src/specify_cli/tracker/config.py` | Add `project_slug` field; keep `workspace` for beads/fp |
| `src/specify_cli/tracker/factory.py` | Remove jira/linear/github/gitlab/azure_devops entries; keep beads/fp only |
| `src/specify_cli/tracker/__init__.py` | Update exports |
| `src/specify_cli/cli/commands/tracker.py` | Update all commands to dispatch SaaS vs local; remove Azure DevOps; update help text |

### Files to Create

| File | Purpose |
|------|---------|
| `src/specify_cli/tracker/saas_client.py` | Low-level HTTP client for SaaS tracker endpoints |
| `src/specify_cli/tracker/saas_service.py` | `SaaSTrackerService` -- SaaS-backed tracker operations |
| `src/specify_cli/tracker/local_service.py` | `LocalTrackerService` -- beads/fp direct connector operations |
| `tests/sync/tracker/test_saas_client.py` | SaaS client tests (auth, polling, errors) |
| `tests/sync/tracker/test_saas_service.py` | SaaS service integration tests |
| `tests/sync/tracker/test_local_service.py` | Local service tests (beads/fp preserved behavior) |
| `tests/sync/tracker/test_service.py` | Façade dispatch tests |

## Implementation Phases

### Phase A: SaaS Tracker Client (Foundation)

Create the low-level HTTP transport layer that all SaaS tracker operations will use.

**Module**: `src/specify_cli/tracker/saas_client.py`

Responsibilities:
- Authenticated HTTP requests to SaaS tracker endpoints
- Bearer token injection from `CredentialStore`
- `X-Team-Slug` header injection from `CredentialStore.get_team_slug()`
- `Idempotency-Key` header generation for push/run
- Error envelope parsing (frozen schema)
- 401 → one refresh + retry
- 429 → respect `retry_after_seconds`
- 202 → operation polling with exponential backoff
- Network error → fail immediately, no fallback

Dependencies: `sync/auth.py`, `sync/config.py` (both exist and are stable)

### Phase B: Config Model Update

Update `TrackerProjectConfig` in `config.py` to support `project_slug` for SaaS-backed bindings while keeping `workspace` for beads/fp.

**Module**: `src/specify_cli/tracker/config.py`

Changes:
- Add `project_slug: str | None = None` field
- Update `to_dict()` / `from_dict()` for serialization roundtrip
- Keep `workspace` for beads/fp backward compatibility
- Update `is_configured` property to check `project_slug` OR `workspace` based on provider

### Phase C: SaaSTrackerService

Create the SaaS-backed service that implements pull/push/run/status/mappings via the SaaS client.

**Module**: `src/specify_cli/tracker/saas_service.py`

Methods:
- `bind(provider, project_slug)` → store config (no credentials)
- `unbind()` → clear config
- `status()` → GET `/api/v1/tracker/status`
- `pull(limit)` → POST `/api/v1/tracker/pull`
- `push()` → POST `/api/v1/tracker/push` (200/202 handling)
- `run(limit)` → POST `/api/v1/tracker/run` (200/202 handling)
- `map_list()` → GET `/api/v1/tracker/mappings`
- `map_add()` → HARD FAIL
- `sync_publish()` → HARD FAIL

Note: The SaaS client exposes `/api/v1/tracker/health` at the HTTP layer for internal diagnostics, but no CLI-facing `health` command is in scope for PRI-16 (no user scenario or FR in the spec). If a CLI health command is needed later, it can be added without changing the service architecture.

### Phase D: LocalTrackerService

Extract beads/fp direct-connector logic from current `TrackerService` into a dedicated class.

**Module**: `src/specify_cli/tracker/local_service.py`

This is a mechanical extraction -- move existing working code, not a rewrite. Methods:
- `bind(provider, workspace, credentials)` → store config + credentials
- `unbind()` → clear config + credentials
- `status()` → local config + SQLite counts
- `pull(limit)` → direct connector sync
- `push(limit)` → direct connector sync
- `run(limit)` → direct connector sync
- `map_add(wp_id, external_id, ...)` → SQLite mapping
- `map_list()` → SQLite mapping list

### Phase E: TrackerService Façade + Factory Cleanup

Refactor `service.py` into the thin façade and clean up `factory.py`.

**service.py** becomes:
```python
class TrackerService:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        # Lazy init backends

    def _resolve_backend(self) -> SaaSTrackerService | LocalTrackerService:
        config = load_tracker_config(self.repo_root)
        if config.provider in SAAS_PROVIDERS:
            return SaaSTrackerService(self.repo_root, config)
        if config.provider in LOCAL_PROVIDERS:
            return LocalTrackerService(self.repo_root, config)
        if config.provider in REMOVED_PROVIDERS:
            raise TrackerServiceError("Azure DevOps is no longer supported.")
        raise TrackerServiceError(f"Unknown provider: {config.provider}")

    # Each method delegates to backend
    def pull(self, *, limit: int = 100) -> dict[str, Any]:
        return self._resolve_backend().pull(limit=limit)
    # ... etc
```

**factory.py** cleanup:
- Remove `jira`, `linear`, `github`, `gitlab`, `azure_devops` entries from `build_connector()`
- Remove `SUPPORTED_PROVIDERS` entries for removed/SaaS providers
- Keep only `beads` and `fp`
- Delete Azure DevOps aliases from `normalize_provider()`

### Phase F: CLI Command Updates

Update `tracker.py` to use the refactored service surface.

Changes:
- `tracker bind`: Accept `--project-slug` for SaaS-backed providers, `--workspace` for local. Hard-fail `--credential` for SaaS-backed.
- `tracker unbind`: Dispatch through façade (no change needed beyond what façade handles)
- `tracker status`: Dispatch through façade
- `tracker sync pull/push/run`: Dispatch through façade; display SaaS envelope results for SaaS-backed
- `tracker sync publish`: Hard-fail for SaaS-backed providers; remove for all (was only used with SaaS-backed)
- `tracker map add`: Hard-fail for SaaS-backed
- `tracker map list`: Dispatch through façade
- `tracker providers`: Update list (remove azure_devops)
- Help text: Distinguish SaaS-backed vs local behavior

### Phase G: Azure DevOps Removal + Dead Code Cleanup

- Remove all Azure DevOps entries from factory, config routing, help text, tests
- Delete `test_service_publish.py` (10,526 lines of snapshot publish tests)
- Remove `RESOURCE_ROUTING_MAP` and `_resolve_resource_routing()` from old service.py
- Remove `_issue_snapshot()`, `_project_identity()`, `sync_publish()` from old service.py
- Remove Azure DevOps connector imports and config from factory.py
- Clean up any orphaned helpers that only served the direct-provider path

### Phase H: Tests

New test files:
- `test_saas_client.py`: Mock httpx responses for all 7 endpoints; test 200/202/401/429/4xx/5xx handling; test polling timeout; test auth refresh
- `test_saas_service.py`: Test SaaSTrackerService methods with mocked client; test hard-fails (map_add, sync_publish, credential bind)
- `test_local_service.py`: Test LocalTrackerService preserves existing beads/fp behavior
- `test_service.py`: Test façade dispatch (SaaS vs local vs removed provider)

Modified tests:
- `test_tracker.py` (CLI integration): Test SaaS-backed and local command paths; test hard-break messages

Deleted tests:
- `test_service_publish.py`: Snapshot publish model no longer exists

## Dependency Order

```
Phase A (saas_client) ← no internal deps
Phase B (config) ← no internal deps
Phase C (saas_service) ← depends on A, B
Phase D (local_service) ← depends on B
Phase E (façade + factory) ← depends on C, D
Phase F (CLI commands) ← depends on E
Phase G (cleanup) ← depends on E, F
Phase H (tests) ← depends on all above
```

Parallelization opportunities:
- A and B can run in parallel
- C and D can run in parallel (after A+B)
- G can overlap with F (independent deletion work)

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking beads/fp during extraction | Phase D is mechanical extraction; test_credentials.py and test_store.py must continue passing |
| SaaS endpoints not available for manual testing | Feature flag gates all commands; mock-based tests validate contract compliance |
| Config migration for existing bindings | Stale config is inert; PRI-17 handles migration tooling |
| Large test file deletion (10,526 lines) | Tests cover obsolete snapshot publish model; replacement tests in Phase H cover the new SaaS path |
