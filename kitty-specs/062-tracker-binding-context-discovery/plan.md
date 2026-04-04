# Implementation Plan: Tracker Binding Context Discovery

**Branch**: `main` | **Date**: 2026-04-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/062-tracker-binding-context-discovery/spec.md`

## Summary

Replace the manual `--project-slug` SaaS bind flow with host-resolved discovery. The CLI derives local project identity, calls new SaaS resolution/inventory endpoints, presents human-labeled candidates (or auto-binds on exact match), and persists a stable `binding_ref` returned by the host. Adds `tracker discover` command, updates `tracker bind` and `tracker status --all`, evolves `TrackerProjectConfig` with dual-read backward compatibility and opportunistic upgrade.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, httpx (via SaaSTrackerClient), ruamel.yaml (config persistence)
**Storage**: Filesystem only (`.kittify/config.yaml` YAML sections)
**Testing**: pytest (TEST_FIRST directive); two-tier — workflow tests mock SaaSTrackerClient methods, client tests mock HTTP transport
**Target Platform**: CLI (macOS, Linux); must work in degraded TTY (SSH, CI, pipe)
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: < 5 seconds for discovery + selection round-trip
**Constraints**: No local provider discovery logic; no bespoke per-provider UX; no direct provider credentials; SaaS API contracts are coordinated dependencies
**Scale/Scope**: 4 new SaaS client methods, 1 new CLI command, 2 updated CLI commands, 1 config model evolution, ~6 new test modules

## Constitution Check

*No constitution file present. Governance directives: TEST_FIRST. Tools: python, pytest, mypy, ruff.*

- TEST_FIRST: All new code must have tests written before or alongside implementation. Client contract tests (HTTP-level) for new `SaaSTrackerClient` methods. Workflow tests (mock client) for service and CLI layers.
- mypy: All new code must pass strict type checking.
- ruff: All new code must pass ruff linting.

No violations anticipated. No complexity justifications needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/062-tracker-binding-context-discovery/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0: engineering decisions
├── data-model.md        # Phase 1: entity models and state transitions
├── quickstart.md        # Phase 1: developer quick reference
├── contracts/           # Phase 1: API consumer contracts (OpenAPI-style)
│   ├── resources.md
│   ├── bind-resolve.md
│   ├── bind-confirm.md
│   ├── bind-validate.md
│   └── existing-endpoint-evolution.md  # binding_ref routing on status/pull/push/run/mappings
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── tracker/
│   ├── config.py              # TrackerProjectConfig: +binding_ref, +display_label, +provider_context, +unknown field passthrough
│   ├── saas_client.py         # SaaSTrackerClient: +resources(), +bind_resolve(), +bind_confirm(), +bind_validate();
│   │                          #   enriched SaaSTrackerClientError with error_code/details;
│   │                          #   existing methods gain optional binding_ref param alongside project_slug
│   ├── saas_service.py        # SaaSTrackerService: +discover(), +resolve_and_bind(), +_maybe_upgrade_binding_ref(),
│   │                          #   +_resolve_routing_params(), stale-binding detection from enriched errors
│   ├── service.py             # TrackerService facade: +discover(), updated bind() for discovery flow, +status(all=)
│   └── discovery.py           # NEW: dataclasses (BindableResource, BindCandidate, BindResult, etc.);
│                              #   pure data helpers only (from_api parsing, candidate lookup by sort_position)
├── cli/commands/
│   └── tracker.py             # discover_command(), updated bind_command(), updated status_command(--all);
│                              #   terminal interaction (numbered display, input prompts, --json rendering)
└── sync/
    └── project_identity.py    # No changes (consumed as-is)

tests/
├── sync/tracker/
│   ├── test_config.py                 # +binding_ref roundtrip, +legacy compat, +is_configured evolution, +unknown field passthrough
│   ├── test_saas_client.py            # +enriched error tests (error_code preserved in SaaSTrackerClientError)
│   ├── test_saas_service.py           # +discover(), +resolve_and_bind(), +_maybe_upgrade_binding_ref(), +stale-binding detection
│   ├── test_service.py                # +facade discover(), +updated bind(), +status(all=)
│   ├── test_discovery.py              # NEW: dataclass parsing, candidate lookup, from_api tests
│   └── test_saas_client_discovery.py  # NEW: HTTP-level contract tests for 4 new endpoints + binding_ref routing on existing endpoints
└── agent/cli/commands/
    └── test_tracker.py                # +discover command, +updated bind scenarios, +status --all
```

**Structure Decision**: All new code lives within the existing `src/specify_cli/tracker/` package. One new module (`discovery.py`) for discovery-specific dataclasses and pure data helpers (API response parsing, candidate lookup by `sort_position`). Terminal interaction (numbered display, input prompts, `--json` rendering) stays in the CLI layer (`tracker.py`). The `TrackerService` facade in `service.py` gains new dispatch methods. Tests follow the existing two-directory pattern (`tests/sync/tracker/` for service/client, `tests/agent/cli/commands/` for CLI).

**Module boundary rule for `discovery.py`**: This module contains only dataclasses and pure functions that operate on API response data (parsing, lookup, filtering). It does not import `rich`, `typer`, or any terminal I/O. All interactive behavior (numbered list rendering, user input, `--json` formatting) belongs in `cli/commands/tracker.py`.

## Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI Layer (cli/commands/tracker.py)                             │
│  discover_command() · bind_command() · status_command()          │
│  Owns: user prompts, numbered list rendering, --json output,    │
│        --bind-ref/--select flags, re-bind confirmation,         │
│        terminal I/O (rich tables, input())                      │
├─────────────────────────────────────────────────────────────────┤
│  Facade Layer (tracker/service.py — TrackerService)             │
│  discover() · bind() · status(all=) · unbind() · sync_*()      │
│  Owns: SaaS vs local dispatch, provider validation              │
│  (All CLI commands go through this facade)                      │
├─────────────────────────────────────────────────────────────────┤
│  SaaS Service Layer (tracker/saas_service.py)                   │
│  discover() · resolve_and_bind() · status() · sync_*()         │
│  Owns: orchestration, config read/write, identity derivation,   │
│        _maybe_upgrade_binding_ref(), _resolve_routing_params(), │
│        stale-binding detection (from enriched client errors)    │
├─────────────────────────────────────────────────────────────────┤
│  Discovery Module (tracker/discovery.py)                        │
│  BindableResource · BindCandidate · BindResult · etc.           │
│  Owns: dataclasses, from_api() parsing, candidate lookup        │
│  (Pure data helpers only — no terminal I/O, no rich/typer)      │
├─────────────────────────────────────────────────────────────────┤
│  Client Layer (tracker/saas_client.py)                          │
│  resources() · bind_resolve() · bind_confirm() · bind_validate()│
│  + existing: status/pull/push/run/mappings (gain binding_ref)   │
│  Owns: HTTP transport, auth injection, retry, error envelopes   │
│  SaaSTrackerClientError carries error_code + details (enriched) │
├─────────────────────────────────────────────────────────────────┤
│  Config Layer (tracker/config.py)                               │
│  TrackerProjectConfig + save/load/clear                         │
│  Owns: YAML persistence, backward-compatible from_dict()/       │
│        to_dict(), unknown field passthrough                     │
├─────────────────────────────────────────────────────────────────┤
│  Identity Layer (sync/project_identity.py)                      │
│  ProjectIdentity + ensure_identity()                            │
│  Owns: local project UUID/slug/node_id derivation               │
│  (NO CHANGES — consumed as-is)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Flows

#### Discovery Bind Flow (FR-003)

```
User: tracker bind --provider linear
  │
  ├─ CLI: ensure ProjectIdentity exists (ensure_identity)
  ├─ CLI: check existing binding → if exists, warn + confirm
  ├─ Service: resolve_and_bind(provider, project_identity)
  │   ├─ Client: bind_resolve(provider, project_identity)
  │   ├─ If match_type == "exact" + binding_ref present:
  │   │   └─ persist binding_ref + display metadata → done
  │   ├─ If match_type == "exact" + binding_ref null:
  │   │   ├─ Client: bind_confirm(candidate_token, project_identity)
  │   │   └─ persist binding_ref + display metadata → done
  │   ├─ If match_type == "candidates":
  │   │   ├─ return candidates to CLI
  │   │   ├─ CLI: display numbered list (sort_position order)
  │   │   ├─ CLI: get user selection (or --select N)
  │   │   ├─ Client: bind_confirm(selected candidate_token, project_identity)
  │   │   └─ persist binding_ref + display metadata → done
  │   └─ If match_type == "none":
  │       └─ error with actionable guidance → exit 1
  │
  └─ CLI: display bound resource label + confirmation
```

#### Opportunistic Upgrade Flow (FR-011)

```
User: tracker status (with legacy project_slug config)
  │
  ├─ Service: status()
  │   ├─ resolve routing key: binding_ref absent → use project_slug
  │   ├─ Client: status(provider, project_slug=project_slug)
  │   ├─ _maybe_upgrade_binding_ref(response)
  │   │   ├─ if response contains "binding_ref":
  │   │   │   └─ atomically write binding_ref + display metadata to config
  │   │   └─ if not: no-op (debug log)
  │   └─ return status result
  │
  └─ CLI: display status output (unchanged)
```

#### Stale Binding Detection (FR-018)

```
User: tracker status (with stale binding_ref)
  │
  ├─ Service: status()
  │   ├─ resolve routing key: binding_ref present → use binding_ref
  │   ├─ Client: status(provider, binding_ref=binding_ref)
  │   ├─ Host returns error: binding_not_found / mapping_disabled
  │   ├─ Service: detect stale-binding error code in PRI-12 envelope
  │   └─ raise TrackerServiceError with re-bind guidance
  │
  └─ CLI: display stale-binding error → exit 1
     (does NOT fall back to project_slug)
```

### Client Error Enrichment (prerequisite for FR-018)

The current `SaaSTrackerClientError` is string-only (`saas_client.py:209`). The service layer needs structured error data to detect stale-binding codes reactively. This is a prerequisite change:

**Current** (string-only):
```python
class SaaSTrackerClientError(Exception):
    pass  # message is the only payload
```

**Required** (enriched):
```python
class SaaSTrackerClientError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        user_action_required: bool = False,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_action_required = user_action_required
```

The `_request_with_retry` method at line 208-216 is updated to populate these fields from the PRI-12 envelope instead of collapsing to a string. The service layer inspects `error.error_code` for stale-binding classification. This is backward-compatible: existing `except SaaSTrackerClientError as e: str(e)` patterns still work.

### TrackerService Facade Evolution

All CLI commands go through `TrackerService` (`service.py`), which dispatches to `SaaSTrackerService` or `LocalTrackerService`. New methods needed on the facade:

```python
class TrackerService:
    def discover(self, *, provider: str) -> list[BindableResource]:
        """Installation-wide resource discovery (SaaS only)."""
        # Validates provider is SaaS, instantiates SaaSTrackerService, delegates

    def bind(self, **kwargs) -> TrackerProjectConfig:
        """Updated: for SaaS, uses discovery flow (resolve_and_bind).
        --bind-ref and --select are passed through as kwargs."""

    def status(self, *, all: bool = False) -> dict[str, Any]:
        """Updated: --all delegates to installation-wide status."""
```

`discover()` is SaaS-only — it raises `TrackerServiceError` for local providers. The updated `bind()` routes SaaS providers to `SaaSTrackerService.resolve_and_bind()` instead of the old `bind(project_slug=...)`. The facade's dispatch logic in `_resolve_backend()` is unchanged for existing operations.

### Existing Endpoint Wire Evolution

The 5 existing client methods (`status`, `pull`, `push`, `run`, `mappings`) currently take `project_slug` as a required positional parameter. They need to support `binding_ref` as an alternative routing key:

**Current signature** (e.g., `status`):
```python
def status(self, provider: str, project_slug: str) -> dict[str, Any]:
```

**Updated signature**:
```python
def status(
    self,
    provider: str,
    project_slug: str | None = None,
    *,
    binding_ref: str | None = None,
) -> dict[str, Any]:
```

**Wire change**: When `binding_ref` is provided, the request sends `binding_ref` instead of `project_slug` in the query params (GET) or body (POST). The SaaS host accepts either key for routing. This is a coordinated contract change: the SaaS team must accept `binding_ref` on existing endpoints alongside `project_slug`.

**Affected methods** (all in `saas_client.py`):
- `status(provider, project_slug, *, binding_ref)` — GET query param
- `mappings(provider, project_slug, *, binding_ref)` — GET query param
- `pull(provider, project_slug, *, binding_ref, limit, cursor, filters)` — POST body
- `push(provider, project_slug, items, *, binding_ref, idempotency_key)` — POST body
- `run(provider, project_slug, *, binding_ref, pull_first, limit, idempotency_key)` — POST body

**Contract test requirement**: HTTP-level tests must verify both `project_slug` and `binding_ref` routing variants for each existing endpoint.

### Routing Key Resolution

The service layer needs a consistent way to resolve which routing key to send to the client. This is a method on the service, not the config:

```
_resolve_routing_params() -> dict[str, str]:
    if config.binding_ref:
        return {"binding_ref": config.binding_ref}
    elif config.project_slug:
        return {"project_slug": config.project_slug}
    else:
        raise TrackerServiceError("No tracker binding configured")
```

All existing delegated methods (`status`, `sync_pull`, `sync_push`, `sync_run`, `map_list`) are updated to use `_resolve_routing_params()` instead of directly accessing `self.project_slug`. The result is spread into each client call as keyword arguments.

### Error Classification

Stale-binding errors are detected reactively from PRI-12 error envelopes (using the enriched `SaaSTrackerClientError`):

| Error code | Meaning | CLI behavior |
|-----------|---------|-------------|
| `binding_not_found` | ServiceResourceMapping deleted | Error + re-bind guidance |
| `mapping_disabled` | Mapping exists but disabled | Error + re-bind guidance |
| `project_mismatch` | binding_ref doesn't match project identity | Error + re-bind guidance |
| Other 4xx/5xx | Standard errors | Existing error handling |

These are detected in the service layer after each client call that uses `binding_ref`. The service raises a specific `StaleBindingError(TrackerServiceError)` subclass so the CLI can format the message appropriately.

## Engineering Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test strategy | Two-tier: workflow mocks client methods; client mocks HTTP | Keeps CLI tests focused on flow/config; client tests validate wire contract |
| Opportunistic upgrade | Explicit `_maybe_upgrade_binding_ref()` helper in service, called at each call site | Visible side effect, no decorator magic, DRY via shared helper |
| `tracker discover` output | Rich table default + `--json` flag | Matches CLI patterns; both human and automation audiences |
| Stale-binding detection | Reactive from endpoint error responses | No extra round-trip; `bind-validate` reserved for `--bind-ref` |
| `--project-slug` on bind | Removed as user-facing flag | Legacy read compat only; no user-facing fallback per ADR |
| New discovery module | `tracker/discovery.py` for dataclasses + selection | Keeps config.py focused on persistence; keeps service.py focused on orchestration; pure data only (no I/O) |
| Client error enrichment | `SaaSTrackerClientError` gains `error_code`, `status_code`, `details` attrs | Prerequisite for reactive stale-binding detection; backward-compatible with existing `str(e)` callers |
| Facade evolution | `TrackerService` gains `discover()`, updated `bind()`, `status(all=)` | All CLI commands go through this facade; omitting it would leave the integration seam undefined |
| Existing endpoint evolution | All 5 client methods gain optional `binding_ref` param | Required for `binding_ref`-primary routing; coordinated SaaS contract change |
| Config unknown field passthrough | `from_dict()`/`to_dict()` preserve unrecognized keys | Prevents data loss when future config fields are added by newer CLI versions |
| Idempotency header | `Idempotency-Key` (not `X-Idempotency-Key`) | Matches existing convention in `saas_client.py` push/run/bind_mission_origin |

## Dependency Graph (Implementation Order)

```
Wave 1 (parallel, no inter-dependencies):
  WP01: Config model evolution (TrackerProjectConfig + unknown field passthrough)
  WP02: Discovery dataclasses (discovery.py — pure data helpers)
  WP03: Client error enrichment (SaaSTrackerClientError + _request_with_retry update)

Wave 2 (depends on Wave 1):
  WP04: SaaS client new methods (resources, bind_resolve, bind_confirm, bind_validate)
  │     depends on WP02 (discovery types), WP03 (enriched errors)
  │
  WP05: Existing endpoint evolution (status/pull/push/run/mappings gain binding_ref param)
        depends on WP03 (enriched errors for stale-binding detection)

Wave 3 (depends on Waves 1-2):
  WP06: Client HTTP contract tests (new endpoints + binding_ref variants on existing endpoints)
        depends on WP04, WP05

  WP07: SaaS service layer (saas_service.py — discover, resolve_and_bind,
        _maybe_upgrade_binding_ref, _resolve_routing_params, stale-binding detection)
        depends on WP01, WP02, WP04, WP05

Wave 4 (depends on Wave 3):
  WP08: TrackerService facade (service.py — discover, updated bind, status(all=))
        depends on WP07

  WP09: Service workflow tests (mock client boundary)
        depends on WP07

Wave 5 (depends on Wave 4; parallel within wave):
  WP10: CLI discover command (tracker.py — rich table, --json, numbered display)
        depends on WP08

  WP11: CLI bind command update (discovery flow, --bind-ref, --select, re-bind confirm)
        depends on WP08

  WP12: CLI status --all (installation-wide summary)
        depends on WP08

Wave 6:
  WP13: Integration / acceptance tests (end-to-end scenarios 1-12)
        depends on all above
```

### Parallelization Opportunities

- Wave 1: WP01, WP02, WP03 are fully independent (config model, discovery types, error enrichment)
- Wave 2: WP04, WP05 can run in parallel (different files, both depend on Wave 1)
- Wave 3: WP06, WP07 can run in parallel (tests vs service implementation)
- Wave 5: WP10, WP11, WP12 are fully independent (three CLI commands, all depend on facade)
- Maximum parallelization: 6 waves instead of 13 sequential steps

## Complexity Tracking

No constitution violations. No complexity justifications needed.
