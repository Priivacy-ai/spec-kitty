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

## Decision 8: Client Error Enrichment

**Decision**: Enrich `SaaSTrackerClientError` with `error_code`, `status_code`, and `details` attributes extracted from the PRI-12 error envelope. The `_request_with_retry` method populates these on non-2xx responses.

**Rationale**: The current client collapses all non-2xx responses into string-only `SaaSTrackerClientError(message)` at `saas_client.py:209`. The service layer needs to inspect error codes like `binding_not_found` and `mapping_disabled` for reactive stale-binding detection (FR-018). Without structured error data crossing the client boundary, the service would have to parse error strings or call a separate validation endpoint on every failure — both are fragile. The enriched exception is backward-compatible: existing `except SaaSTrackerClientError as e: str(e)` patterns still work because `__init__` still calls `super().__init__(message)`.

**Alternatives considered**:
- Parse error strings in the service layer: Rejected — brittle, breaks when message wording changes.
- Call `bind-validate` on every client error: Rejected — adds latency and couples read paths to a validation endpoint.
- Return structured error dicts instead of raising: Rejected — would require changing the entire client error-handling contract.

## Decision 9: TrackerService Facade Evolution

**Decision**: Add `discover()`, update `bind()`, and add `status(all=)` to the `TrackerService` facade in `service.py`.

**Rationale**: Every CLI command goes through `TrackerService._resolve_backend()` for provider dispatch. The plan initially omitted this file, but the facade is the integration seam between CLI commands and backend services. `discover()` is SaaS-only and raises `TrackerServiceError` for local providers. The updated `bind()` routes SaaS providers to `SaaSTrackerService.resolve_and_bind()`. Without explicit facade methods, implementers would have to bypass the facade or invent the integration mid-stream.

**Alternatives considered**:
- Bypass the facade for new commands: Rejected — breaks the dispatch pattern and couples CLI directly to SaaSTrackerService.
- Merge facade into SaaSTrackerService: Rejected — the facade exists specifically to dispatch between SaaS and local backends.

## Decision 10: Existing Endpoint Wire Evolution

**Decision**: All 5 existing `SaaSTrackerClient` methods (`status`, `pull`, `push`, `run`, `mappings`) gain an optional `binding_ref` keyword parameter alongside the existing `project_slug`. When provided, `binding_ref` is sent instead of `project_slug` in query params (GET) or body (POST).

**Rationale**: The plan specifies `binding_ref` as the primary routing key and `_resolve_routing_params()` in the service, but the client methods currently take `project_slug` as a required positional. Without updating the client signatures, the service layer cannot pass `binding_ref` through to the wire. This is a coordinated SaaS contract change: the host must accept `binding_ref` on existing endpoints alongside `project_slug`.

**Alternatives considered**:
- New endpoint variants (e.g., `status_v2`): Rejected — creates unnecessary API surface duplication.
- Generic routing dict parameter: Rejected — loses type safety and makes the API harder to use.

## Decision 11: Config Unknown Field Passthrough

**Decision**: `TrackerProjectConfig.from_dict()` captures unrecognized keys into a private `_extra` dict. `to_dict()` merges them back, with known fields taking precedence.

**Rationale**: The current serializer only materializes known fields (`config.py:48-57`). The deserializer only reads known fields (`config.py:59-88`). Any YAML keys not in the dataclass are silently dropped on round-trip. This is a data-loss risk when a newer CLI version writes fields (e.g., a future `binding_metadata`) that an older version doesn't recognize. The `save_tracker_config()` function already preserves non-`tracker` YAML sections; this extends the guarantee within the `tracker` section.

**Alternatives considered**:
- Full YAML preservation (don't use dataclass, use raw dict): Rejected — loses type safety and validation.
- Accept data loss: Rejected — the spec explicitly promises forward-compatible config evolution.

## Decision 12: Idempotency Header Convention

**Decision**: Use `Idempotency-Key` (no `X-` prefix) for the bind-confirm endpoint, matching the existing convention.

**Rationale**: The existing `saas_client.py` uses `Idempotency-Key` in `push()` (line 410), `run()` (line 443), and `bind_mission_origin()` (line 381). The initial contract specified `X-Idempotency-Key`, which is a needless divergence. The `X-` prefix convention was deprecated by IETF RFC 6648 in 2012 and the existing codebase already follows the non-prefixed convention.
