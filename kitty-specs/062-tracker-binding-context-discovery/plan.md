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
│   └── bind-validate.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── tracker/
│   ├── config.py              # TrackerProjectConfig: +binding_ref, +display_label, +provider_context
│   ├── saas_client.py         # SaaSTrackerClient: +resources(), +bind_resolve(), +bind_confirm(), +bind_validate()
│   ├── saas_service.py        # SaaSTrackerService: +discover(), +resolve_and_bind(), +_maybe_upgrade_binding_ref()
│   └── discovery.py           # NEW: BindableResource, BindCandidate dataclasses; selection logic
├── cli/commands/
│   └── tracker.py             # discover_command(), updated bind_command(), updated status_command(--all)
└── sync/
    └── project_identity.py    # No changes (consumed as-is)

tests/
├── sync/tracker/
│   ├── test_config.py                 # +binding_ref roundtrip, +legacy compat, +is_configured evolution
│   ├── test_saas_client.py            # +contract tests for resources(), bind_resolve(), bind_confirm(), bind_validate()
│   ├── test_saas_service.py           # +discover(), +resolve_and_bind(), +_maybe_upgrade_binding_ref()
│   ├── test_discovery.py              # NEW: BindableResource/BindCandidate dataclass tests, selection logic
│   └── test_saas_client_discovery.py  # NEW: HTTP-level contract tests for 4 new endpoints
└── agent/cli/commands/
    └── test_tracker.py                # +discover command, +updated bind scenarios, +status --all
```

**Structure Decision**: All new code lives within the existing `src/specify_cli/tracker/` package. One new module (`discovery.py`) for discovery-specific dataclasses and selection logic, keeping it separate from config persistence and SaaS transport. Tests follow the existing two-directory pattern (`tests/sync/tracker/` for service/client, `tests/agent/cli/commands/` for CLI).

## Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI Layer (tracker.py)                                         │
│  discover_command() · bind_command() · status_command()          │
│  Owns: user prompts, numbered selection, --json output,         │
│        --bind-ref/--select flags, re-bind confirmation          │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer (saas_service.py)                                │
│  discover() · resolve_and_bind() · status() · sync_*()         │
│  Owns: orchestration, config read/write, identity derivation,   │
│        _maybe_upgrade_binding_ref(), stale-binding detection    │
├─────────────────────────────────────────────────────────────────┤
│  Discovery Module (discovery.py)                                │
│  BindableResource · BindCandidate · select_candidate()          │
│  Owns: dataclasses, candidate parsing, selection-by-position    │
├─────────────────────────────────────────────────────────────────┤
│  Client Layer (saas_client.py)                                  │
│  resources() · bind_resolve() · bind_confirm() · bind_validate()│
│  Owns: HTTP transport, auth injection, retry, error envelopes   │
├─────────────────────────────────────────────────────────────────┤
│  Config Layer (config.py)                                       │
│  TrackerProjectConfig + save/load/clear                         │
│  Owns: YAML persistence, binding_ref read precedence,           │
│        backward-compatible from_dict()/to_dict()                │
├─────────────────────────────────────────────────────────────────┤
│  Identity Layer (project_identity.py)                           │
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

All existing delegated methods (`status`, `sync_pull`, `sync_push`, `sync_run`, `map_list`) are updated to use `_resolve_routing_params()` instead of directly accessing `self.project_slug`. The client methods gain an optional `binding_ref` parameter alongside the existing `project_slug`.

### Error Classification

Stale-binding errors are detected reactively from PRI-12 error envelopes:

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
| New discovery module | `tracker/discovery.py` for dataclasses + selection | Keeps config.py focused on persistence; keeps service.py focused on orchestration |

## Dependency Graph (Implementation Order)

```
WP01: Config model evolution (TrackerProjectConfig)
  │
  ├── WP02: Discovery dataclasses (discovery.py)
  │
  ├── WP03: SaaS client new methods (saas_client.py)
  │     │
  │     └── WP04: Client HTTP contract tests
  │
  ├── WP05: Service layer (saas_service.py)
  │     ├── depends on WP01, WP02, WP03
  │     │
  │     └── WP06: Service workflow tests
  │
  ├── WP07: CLI discover command
  │     ├── depends on WP05
  │     │
  │     └── WP08: CLI bind command update
  │           ├── depends on WP05
  │           │
  │           └── WP09: CLI status --all
  │                 └── depends on WP05
  │
  └── WP10: Integration / acceptance tests
        └── depends on all above
```

### Parallelization Opportunities

- WP01, WP02 can run in parallel (no dependencies between config model and discovery dataclasses)
- WP03 depends on WP02 (client methods return discovery types) but not WP01
- WP04 depends only on WP03
- WP07, WP08, WP09 can run in parallel (all depend on WP05, independent of each other)

## Complexity Tracking

No constitution violations. No complexity justifications needed.
