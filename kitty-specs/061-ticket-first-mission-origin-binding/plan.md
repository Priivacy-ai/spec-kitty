# Implementation Plan: Ticket-First Mission Origin Binding

**Branch**: `main` | **Date**: 2026-04-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/061-ticket-first-mission-origin-binding/spec.md`

## Summary

Add a service-layer workflow in `src/specify_cli/tracker/origin.py` that lets `/spec-kitty.specify` and agent workflows search for an existing Jira or Linear ticket through SaaS, present candidates for developer confirmation, create a mission from the confirmed ticket, and persist durable origin-ticket provenance in local metadata. Extends `SaaSTrackerClient` with two new methods (`search_issues`, `bind_mission_origin`), adds a `set_origin_ticket()` mutation helper to `feature_metadata.py`, and registers a `MissionOriginBound` event type in the emitter.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, httpx, ruamel.yaml, pydantic (existing), ulid (existing)
**Storage**: Filesystem only (meta.json via atomic_write, status.events.jsonl)
**Testing**: pytest with unittest.mock (MagicMock + @patch), TEST_FIRST directive
**Target Platform**: CLI (repo-local, cross-platform)
**Project Type**: Single Python package (`specify_cli`)
**Performance Goals**: Issue search completes within 10 seconds under normal network conditions
**Constraints**: No provider credentials held locally; all Jira/Linear API access flows through SaaS
**Scale/Scope**: 3 new service functions, 2 client methods, 1 metadata helper, 1 event type

## Constitution Check

*Source: `.kittify/constitution/constitution.md` (v1.0.0, 2026-01-27)*

| Standard | Constitution Requirement | This Feature | Status |
|----------|------------------------|-------------|--------|
| Language | Python 3.11+ | Python 3.11+ | Pass |
| Testing | pytest, 90%+ coverage for new code | All new modules tested TEST_FIRST; target 90%+ coverage for `tracker/origin.py`, `set_origin_ticket()`, event registration, and client extensions | Pass |
| Type checking | mypy --strict, no type errors | All new code fully typed with strict annotations | Pass |
| Integration tests | Required for CLI commands | No new CLI commands; integration tests for service-layer orchestration (`start_mission_from_ticket` end-to-end with mocked HTTP) | Pass (adapted) |
| Unit tests | Required for core logic | Unit tests per layer: client, service, metadata, event | Pass |
| CLI performance | < 2 seconds for typical operations | Local operations (metadata write, event emit) well under 2s. Network-bound search is 10s max per spec — see justification below | Justified exception |
| Cross-platform | Linux, macOS, Windows 10+ | No platform-specific code; uses pathlib, httpx, standard library | Pass |
| Docstrings | Required for public APIs | All public functions and dataclasses will have docstrings | Pass |
| Terminology | "Mission" not "Feature" in product language | Code identifiers (`feature_dir`, `meta.json`) remain; product-facing language uses "Mission" | Pass |

**CLI performance justification**: The constitution's < 2 second target applies to local CLI operations (status display, metadata reads, dashboard rendering). The `search_origin_candidates()` method is a network-bound SaaS API call that queries external Jira/Linear providers — fundamentally different from local operations. The spec's 10-second threshold (NFR-001) is the appropriate bound for this class of operation. Local-only operations in this feature (metadata writes, event emission) complete well within 2 seconds.

## Project Structure

### Documentation (this feature)

```
kitty-specs/061-ticket-first-mission-origin-binding/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md  # Quality checklist
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   └── feature_creation.py    # NEW: create_feature_core() + FeatureCreationResult
│                              #   Extracted from cli/commands/agent/feature.py
├── tracker/
│   ├── origin.py              # NEW: ticket-first origin orchestration
│   │                          #   - OriginCandidate, SearchOriginResult, MissionFromTicketResult
│   │                          #   - search_origin_candidates()
│   │                          #   - bind_mission_origin()
│   │                          #   - start_mission_from_ticket()
│   ├── saas_client.py         # EXTEND: search_issues(), bind_mission_origin()
│   ├── saas_service.py        # (unchanged)
│   ├── service.py             # (unchanged)
│   └── config.py              # (unchanged)
├── cli/commands/agent/
│   └── feature.py             # REFACTOR: create_feature() becomes thin wrapper
│                              #   around core/feature_creation.create_feature_core()
├── feature_metadata.py        # EXTEND: set_origin_ticket() mutation helper,
│                              #   FeatureMetaOptional TypedDict update
└── sync/
    └── emitter.py             # EXTEND: MissionOriginBound event type,
                               #   emit_mission_origin_bound(), _PAYLOAD_RULES entry

tests/
├── specify_cli/core/
│   └── test_feature_creation.py  # NEW: tests for create_feature_core()
├── sync/tracker/
│   ├── test_origin.py         # NEW: service-layer tests for origin.py
│   ├── test_saas_client.py    # EXTEND: tests for search_issues(), bind_mission_origin()
│   └── test_saas_service.py   # (unchanged)
├── specify_cli/
│   └── test_feature_metadata.py  # EXTEND: tests for set_origin_ticket()
└── sync/
    └── test_emitter.py        # EXTEND: tests for MissionOriginBound event
```

**Structure Decision**: New module `tracker/origin.py` follows existing tracker package conventions. Client extensions stay in `saas_client.py`. Metadata helper stays in `feature_metadata.py`. Event registration stays in `emitter.py`. No new packages created.

## Module Layering

```
/spec-kitty.specify (agent workflow)
        │
        ▼
tracker/origin.py  ◄── normative service-layer API
   │         │         │
   │         │         ▼
   │         │    feature_metadata.py  (set_origin_ticket → write_meta)
   │         │
   │         ▼
   │    sync/emitter.py  (emit_mission_origin_bound — observational telemetry)
   │
   ▼
tracker/saas_client.py  (search_issues, bind_mission_origin — transport)
   │
   ▼
SaaS control plane  (Team B — HTTP wire format, upstream dependency)
```

**Authority chain:**
- `SaaSTrackerClient.bind_mission_origin()` API call = authoritative write for SaaS-side `MissionOriginLink`
- `MissionOriginBound` event = observational telemetry only (offline audit, analytics)
- `set_origin_ticket()` = authoritative local write for `meta.json` origin provenance

**Write ordering (prevents split-brain):**
The `bind_mission_origin()` service method must use **SaaS-first, local-second** ordering:
1. Call `SaaSTrackerClient.bind_mission_origin()` — if this fails, stop and raise. No local state written.
2. Call `set_origin_ticket()` to write `meta.json` — if this fails (unlikely with atomic_write), the SaaS record exists but local does not. The next retry will see the same-origin no-op from SaaS and succeed locally.
3. Emit `MissionOriginBound` event — fire-and-forget (queued offline if SaaS unreachable).

This ensures local metadata can never be ahead of the authoritative SaaS state. The only possible inconsistency is SaaS-ahead-of-local (step 2 failure), which self-heals on retry.

## Key Design Decisions

### D1: Dataclasses for origin models

`OriginCandidate`, `SearchOriginResult`, and `MissionFromTicketResult` use `@dataclass(slots=True)` — consistent with `TrackerProjectConfig` and `MergeState` in the tracker/merge packages. Pydantic is reserved for mission schema validation; these are simple value objects.

### D2: create-feature integration via extracted core function

The existing `create_feature()` in `cli/commands/agent/feature.py` is a 300+ line typer command that returns `None`, emits JSON to stdout, and uses `typer.Exit()` for control flow. That is not a stable service seam, and the service layer should not depend on CLI-command internals.

**Approach**: Extract the core feature-creation logic into a neutral module:
- New module: `src/specify_cli/core/feature_creation.py`
- New public function: `create_feature_core(repo_root, feature_slug, mission, target_branch) -> FeatureCreationResult`
- `FeatureCreationResult` is a dataclass with `feature_dir`, `feature_slug`, `feature_number`, `meta`, `target_branch`
- Raises domain exceptions (e.g., `FeatureCreationError`) instead of `typer.Exit()`
- The existing typer command in `cli/commands/agent/feature.py` becomes a thin wrapper that calls `create_feature_core()` and formats output

This placement in `core/` (alongside `paths.py`, `atomic.py`, `worktree.py`) makes the function importable from any layer without creating a dependency on CLI-command modules. `tracker/origin.py` imports from `core/feature_creation.py`, not from `cli/commands/`.

This extraction is a prerequisite work package. It is a contained refactor that does not change external CLI behavior.

### D3: Re-bind semantics

- **Same origin** (same `external_issue_id`): SaaS returns no-op success, local overwrites identically
- **Different origin**: SaaS returns 409, service raises hard error (one origin per mission in v1)

The service layer always calls SaaS first — it does not inspect local `meta.json` to short-circuit. SaaS is the sole authority for deciding whether a bind is a no-op or a conflict. This is consistent with the SaaS-first write ordering defined above.

### D4: match_type enum aligned with upstream

Values are `"exact"` and `"text"` — aligned with the tracker/SaaS contract. The CLI spec does not invent its own enum.

### D5: SaaS endpoint paths are not defined here

The `SaaSTrackerClient` extensions define method signatures and behavioral semantics. URL paths and HTTP methods are Team B's decision. The client methods will use `self._request_with_retry()` to call whatever paths Team B implements. Placeholder paths (e.g., `_SEARCH_ISSUES_PATH`, `_BIND_ORIGIN_PATH`) will be defined as class constants, following the existing pattern (`_STATUS_PATH`, `_PULL_PATH`, etc.).

## Dependencies

### Internal (within spec-kitty)

| Dependency | Module | Usage |
|-----------|--------|-------|
| Tracker config | `tracker/config.py` | Load provider + project_slug from `.kittify/config.yaml` |
| SaaS client transport | `tracker/saas_client.py` | HTTP transport with auth, retry, polling |
| Metadata writer | `feature_metadata.py` | `write_meta()` atomic writes, `load_meta()` reads |
| Event emitter | `sync/emitter.py` | Event creation, validation, offline queue routing |
| Feature creation | `core/feature_creation.py` | `create_feature_core()` for mission scaffolding (extracted from CLI command) |
| Project root | `core/paths.py` | `locate_project_root()` |

### Upstream (external teams)

| Dependency | Owner | Status | Notes |
|-----------|-------|--------|-------|
| Issue-search SaaS endpoint | Team B | Not yet implemented | CLI codes to client method contract; wire format is Team B's |
| Bind SaaS endpoint | Team B | Not yet implemented | Same approach — client method contract only |
| Candidate shape normalization | Team A | Coordination required | `OriginCandidate` fields must align with tracker-connector output |

### Risk: SaaS endpoints not ready

If Team B's endpoints are not available when CLI implementation begins, the `SaaSTrackerClient` methods can be implemented with the correct signatures and error handling, tested against mocked HTTP responses, and wired to real endpoints later by updating path constants only. No architecture changes required.

## Test Strategy

Following the TEST_FIRST directive and existing patterns in the tracker test suite.

### Layer 1: SaaSTrackerClient methods (HTTP transport)

**File**: `tests/sync/tracker/test_saas_client.py` (extend)
**Pattern**: `@patch("specify_cli.tracker.saas_client.httpx.Client")` + `_make_response()` helper
**Coverage**:
- `search_issues()`: 200 with candidates, 200 empty, 401/403 user-action-required, 404, 422, 429 retry
- `bind_mission_origin()`: 200 success, 200 same-origin no-op, 409 different-origin, 401/403

### Layer 2: Service-layer functions (origin.py)

**File**: `tests/sync/tracker/test_origin.py` (new)
**Pattern**: MagicMock `SaaSTrackerClient` injected into service functions
**Coverage**:
- `search_origin_candidates()`: happy path, no binding, wrong provider, empty results, user-link error
- `bind_mission_origin()`: happy path, same-origin no-op, different-origin error, meta.json written correctly
- `start_mission_from_ticket()`: full flow, create-feature failure handling, slug derivation

### Layer 3: Metadata helper

**File**: `tests/specify_cli/test_feature_metadata.py` (extend)
**Pattern**: tmp_path with pre-seeded meta.json
**Coverage**:
- `set_origin_ticket()`: writes origin_ticket block, preserves existing fields, validates via write_meta

### Layer 4: Event emission

**File**: `tests/sync/test_emitter.py` (extend)
**Pattern**: Existing emitter test patterns
**Coverage**:
- `emit_mission_origin_bound()`: payload validation, event routing, offline queue

## Implementation Sequence

The implementation follows a bottom-up dependency order:

1. **Foundation** — Data models (`OriginCandidate`, `SearchOriginResult`, `MissionFromTicketResult`) + metadata helper (`set_origin_ticket`) + event type (`MissionOriginBound`). No external dependencies.

2. **Transport** — `SaaSTrackerClient.search_issues()` and `.bind_mission_origin()`. Depends on foundation data models for result shape. Can be fully tested with mocked HTTP.

3. **create-feature extraction** — Extract `create_feature_core()` into `src/specify_cli/core/feature_creation.py`. Returns `FeatureCreationResult` dataclass, raises `FeatureCreationError`. Existing typer command becomes thin wrapper. Prerequisite for orchestration layer.

4. **Orchestration** — `tracker/origin.py` service functions (`search_origin_candidates`, `bind_mission_origin`, `start_mission_from_ticket`). Depends on transport + foundation + extracted create-feature API. Uses SaaS-first write ordering. This is the normative API surface.

5. **Integration testing** — End-to-end flow tests with all layers wired together (mocked HTTP only at the httpx boundary). Covers full search → confirm → bind → create flow.

Layers 1-2 can proceed in parallel. Layer 3 is an independent prerequisite. Layer 4 depends on 1, 2, and 3. Layer 5 depends on all.
