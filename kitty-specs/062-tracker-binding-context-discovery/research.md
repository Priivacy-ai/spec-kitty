# Research: Tracker Binding Context Discovery

**Feature**: 062-tracker-binding-context-discovery
**Date**: 2026-04-04

## Decision 1: Test Architecture

**Decision**: Two-tier testing — workflow tests mock `SaaSTrackerClient` method boundary; client tests mock HTTP transport.

**Rationale**: The existing codebase already follows this pattern. `test_saas_service.py` uses `MagicMock` for the client. `test_saas_client.py` builds fake `httpx.Response` objects. Extending both test suites with the same patterns avoids introducing a new testing paradigm. The CLI/service layer owns user flow, config writes, and prompt logic — those tests should not assert HTTP details. The client layer owns wire format, auth injection, retry, and error envelopes — those tests should validate request/response shapes.

**Alternatives considered**:
- HTTP-level mocking everywhere: Rejected — makes workflow tests brittle to transport changes.
- Client-level mocking everywhere: Rejected — would not validate the new endpoint wire shapes, which are a key risk since the endpoints don't exist yet.
- Integration tests against a running SaaS instance: Out of scope — endpoints are coordinated dependencies not yet implemented.

## Decision 2: Opportunistic Upgrade Implementation

**Decision**: Explicit private helper `_maybe_upgrade_binding_ref(response: dict[str, Any]) -> None` in `SaaSTrackerService`, called deliberately after each successful client call.

**Rationale**: The service layer already holds `repo_root` and `_config`, which are needed for the config write. There are only 5-6 service methods that make client calls (`status`, `sync_pull`, `sync_push`, `sync_run`, `map_list`, and the new bind/discovery methods). Explicit calls at each site make the side effect visible without duplicating the upgrade logic. A decorator would hide a real write operation on read paths like `status()`.

**Alternatives considered**:
- Decorator/wrapper: Rejected — hides side effects, makes test setup harder, requires introspection of response format per endpoint.
- Copy-pasted inline logic: Rejected — DRY violation across 6+ call sites.
- Client-layer upgrade: Rejected — client should not know about local config mutation.

## Decision 3: Discovery Output Format

**Decision**: Rich table as default, `--json` flag for automation. Table row numbering matches `--select N`.

**Rationale**: The CLI already uses `rich` for panels and tables in other commands. The `tracker discover` command serves both interactive (developer browsing resources) and automation (CI extracting bind refs) audiences. Numbered rows aligning with `--select N` creates a consistent mental model between interactive and scripted flows.

**Alternatives considered**:
- JSON only: Rejected — poor interactive experience.
- Rich table only: Rejected — unusable for scripting/CI.
- Custom formatting: Rejected — unnecessary when rich table + JSON covers both audiences.

## Decision 4: Stale Binding Detection Strategy

**Decision**: Reactive detection from real endpoint error responses. `bind-validate` reserved for `--bind-ref` validation and optional error-sharpening.

**Rationale**: Stale bindings surface naturally when the CLI tries to use the `binding_ref` for a real operation. The PRI-12 error envelope already carries structured error codes. Adding a proactive validation call on every command would add latency and couple read paths to a new endpoint. The `bind-validate` endpoint exists for explicit ref verification (CI `--bind-ref` flow) and can optionally be called to sharpen ambiguous error messages from other endpoints.

**Alternatives considered**:
- Proactive on every call: Rejected — extra round-trip, unnecessary in steady state.
- Proactive on `tracker status` only: Rejected — makes `status` special without architectural justification.
- No validation at all for `--bind-ref`: Rejected — allows CI to persist arbitrary/stale refs without any check.

## Decision 5: New Module vs. Inline

**Decision**: New `tracker/discovery.py` module for `BindableResource`, `BindCandidate` dataclasses and selection logic.

**Rationale**: `config.py` is focused on YAML persistence. `saas_service.py` is focused on orchestration. `saas_client.py` is focused on HTTP transport. Discovery-specific dataclasses (`BindableResource`, `BindCandidate`) and selection logic (`select_candidate()`) are a distinct concern that doesn't fit cleanly in any existing module. A new module keeps each file focused.

**Alternatives considered**:
- Inline in `saas_service.py`: Rejected — service is already growing with new methods; dataclass definitions would bloat it.
- Inline in `config.py`: Rejected — config.py is about persistence, not transient API response types.
- Inline in `saas_client.py`: Rejected — client should return dicts (matching existing pattern); structured parsing happens in the service/discovery layer.

## Decision 6: Routing Key Resolution

**Decision**: `_resolve_routing_params()` method on `SaaSTrackerService` that returns the appropriate routing parameters based on config state (binding_ref-first, project_slug-fallback).

**Rationale**: All existing service methods currently access `self.project_slug` directly. After 062, routing can use either `binding_ref` or `project_slug`. Centralizing this in a single resolution method ensures consistent read precedence (FR-010) and makes the stale-binding detection path consistent. Each delegated method calls `_resolve_routing_params()` and spreads the result into the client call.

**Alternatives considered**:
- Resolution in config.py: Rejected — config should not know about routing semantics, only about field presence.
- Resolution in client.py: Rejected — client should accept explicit parameters, not make config decisions.
- Property on TrackerProjectConfig: Partially viable but conflates persistence with routing logic.

## Decision 7: --project-slug Removal

**Decision**: `--project-slug` is not accepted as a user-facing `tracker bind` flag. Legacy `project_slug` values in existing configs are supported for read-path compatibility only.

**Rationale**: The ADR explicitly removes raw metadata prompts from the normal bind path. Keeping `--project-slug` as a documented fallback would encourage the exact behavior the ADR is trying to eliminate. Legacy read compatibility is necessary (users with existing configs should not be broken), but bind-time fallback is not. If a maintainer needs emergency repair, an undocumented `--force-legacy-slug` could be added later, but it is not part of this feature.

**Alternatives considered**:
- Deprecated `--project-slug` flag: Rejected — deprecation warnings signal "this still works," which undermines the architectural direction.
- Hidden `--project-slug` flag: Rejected for now — adds dead code and test surface for a path we're actively moving away from.
