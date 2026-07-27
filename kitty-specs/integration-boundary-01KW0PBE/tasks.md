# Tasks: Enforce the Integration/Core Boundary Inside specify_cli

**Mission**: integration-boundary-01KW0PBE
**Branch**: `feat/integration-boundary`
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [data-model.md](./data-model.md) · [contracts/integration-boundary-rule.md](./contracts/integration-boundary-rule.md) · [contracts/invocation-adapters-registry-contract.md](./contracts/invocation-adapters-registry-contract.md) · [research.md](./research.md)

Enforce the one-directional CORE→INTEGRATION boundary inside `src/specify_cli`
**in-place** (no module moves). The three verified import leaks are inverted via
the existing adapter/observer registry. An AST-based architectural test permanently
prevents new leaks. Documentation is updated so every contributor knows which
modules belong to each tier. WP ordering is load-bearing: WP04 (enforcement test)
is introduced only after WP01–WP03 have removed all three leaks, so the test passes
green from its first commit.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `src/specify_cli/invocation/adapters.py` with `register_sync_routing_resolver`, `register_saas_client_factory`, `resolve_sync_routing`, `get_saas_client`, `reset_adapters` following `status/adapters.py` idiom | WP01 | — |
| T002 | Re-export from `invocation/__init__.py` (public API surface) | WP01 | — |
| T003 | Remove module-level `sync.routing` import (line 39) and lazy `sync.client` import (line 66) from `propagator.py`; call through `invocation/adapters.py` instead | WP01 | — |
| T004 | Extend `sync/__init__.py::register_default_handlers` to register sync-routing resolver and SaaS-client factory with `invocation/adapters.py`; unit tests for registration + safe-degrade (None when unregistered) | WP01 | — |
| T005 | Create `src/specify_cli/core/adapters.py` with `PendingOriginConsumer` type alias, `register_pending_origin_consumer`, `consume_pending_origin`, `reset_origin_consumer`; non-raising, result-bearing | WP02 | — |
| T006 | Re-export from `core/__init__.py` (public API surface) | WP02 | — |
| T007 | Remove line 30 (`from specify_cli.sync.events import emit_mission_created`) and line 525 call from `core/mission_creation.py`; verify `emit_mission_created_local` already triggers `fire_lifecycle_saas_fanout` so no double-write is introduced | WP02 | — |
| T008 | Remove lazy `sync.dossier_pipeline` import (line 540) from `core/mission_creation.py`; replace with `fire_dossier_sync(feature_dir, mission_slug, repo_root)` from `status/adapters.py` | WP02 | — |
| T009 | Remove lazy `tracker.*` imports (lines 593–595) from `core/mission_creation.py`; replace `_consume_pending_origin_if_present` body with `consume_pending_origin(...)` from `core/adapters.py`; preserve `MissionCreationResult.origin_binding_*` fields | WP02 | — |
| T010 | Unit tests for `core/adapters.py`: no-consumer default returns `(False, False, None, meta)`, registered consumer is called, exception in consumer returns `(True, False, str(exc), meta)` | WP02 | — |
| T011 | Create `src/specify_cli/tracker/origin_consumer.py` with `consume_pending_origin_impl` — logic extracted verbatim from `_consume_pending_origin_if_present` in `mission_creation.py`; keeps tracker imports local | WP03 | — |
| T012 | Register `consume_pending_origin_impl` with `core/adapters.py` in `tracker/__init__.py` startup hook; confirm CLI entrypoints import tracker before mission creation is called | WP03 | — |
| T013 | In `sync/__init__.py::register_default_handlers`, add `invocation/adapters.py` registration calls (resolver + factory) inside the existing `contextlib.suppress(ImportError)` guard at lines 290–294 | WP03 | — |
| T014 | Verify single surviving `emit_mission_created` path: `emit_mission_created_local → fire_lifecycle_saas_fanout → _lifecycle_saas_fanout_handler`; if MissionCreated daemon/WebSocket path is needed extend `_lifecycle_saas_fanout_handler` in sync to cover it — zero direct INTEGRATION imports re-enter core | WP03 | — |
| T015 | Targeted regression test: observer registration fires the origin consumer, dossier sync, and lifecycle SaaS fanout on a mission-created event (NFR-004 per inversion) | WP03 | — |
| T016 | Create `tests/architectural/test_integration_boundary.py`: `_collect_imports` AST walker catches module-level, `if TYPE_CHECKING:` block, and lazy function-body imports; scan all CORE-set directories with `Path.rglob("*.py")` | WP04 | — |
| T017 | Add path-existence sub-test for all four CORE-set directories (`core/`, `status/`, `readiness/`, `invocation/`); fail loudly if any directory is renamed (C-008) | WP04 | — |
| T018 | Add allowlist with exactly one entry (Leak #2: `readiness/coordinator.py → specify_cli.saas.rollout`) with source module, imported module, and written rationale; add sanity sub-test that proves the allowlist cannot be bypassed silently | WP04 | — |
| T019 | Carry `@pytest.mark.architectural`; violation message includes ≥ 3 diagnostic fields (violating file, offending import, corrective action); test completes within 30 s (NFR-001, NFR-002, C-008) | WP04 | — |
| T020 | Add/update architectural doc under `architecture/` (per `architecture/README.md` template): CORE and INTEGRATION set definitions, one-directional rule and rationale, allowlist exemptions with follow-up references, deferred scope (physical extraction, bidirectional enforcement, `coordination/`/`lanes/`/`runtime/`) | WP05 | — |

---

## WP01 — invocation/adapters.py + Leak #3 fix in propagator.py

**Prompt**: [tasks/WP01-invocation-adapters-leak3-fix.md](tasks/WP01-invocation-adapters-leak3-fix.md)

**Summary**
- **Goal**: Create `src/specify_cli/invocation/adapters.py` (sync-routing resolver + SaaS-client factory registry, mirroring `status/adapters.py` idiom) and immediately remove the two INTEGRATION imports from `propagator.py` that constitute Leak #3.
- **Priority**: P0 — chain root; all subsequent WPs depend on this.
- **Requirements**: FR-008, C-007, NFR-003, NFR-004
- **Subtasks**: T001, T002, T003, T004

---

## WP02 — core/adapters.py + Leak #1 fix in mission_creation.py

**Prompt**: [tasks/WP02-core-adapters-leak1-fix.md](tasks/WP02-core-adapters-leak1-fix.md)

**Summary**
- **Goal**: Create `src/specify_cli/core/adapters.py` (pending-origin consumer registry) and remove all three INTEGRATION import edges from `core/mission_creation.py`. Preserve the single `status.events.jsonl` write invariant and the SaaS fan-out path.
- **Priority**: P0 — depends on WP01 (invocation/adapters.py must exist before propagator is edited).
- **Requirements**: FR-004, FR-006, NFR-003, NFR-004
- **Dependencies**: WP01
- **Subtasks**: T005, T006, T007, T008, T009, T010

---

## WP03 — tracker/origin_consumer.py + observer wiring + emit_mission_created collapse

**Prompt**: [tasks/WP03-tracker-observer-wiring.md](tasks/WP03-tracker-observer-wiring.md)

**Summary**
- **Goal**: Create `src/specify_cli/tracker/origin_consumer.py`, register it with `core/adapters.py` at startup, wire invocation adapter registrations into `sync/__init__.py::register_default_handlers`, and confirm the single surviving SaaS fan-out path for MissionCreated. All three leaks are now fully inverted.
- **Priority**: P0 — must complete before WP04 so the enforcement test passes green on first introduction.
- **Requirements**: FR-005, FR-006, NFR-003, NFR-004
- **Dependencies**: WP02
- **Subtasks**: T011, T012, T013, T014, T015

---

## WP04 — test_integration_boundary.py enforcement test

**Prompt**: [tasks/WP04-enforcement-test.md](tasks/WP04-enforcement-test.md)

**Summary**
- **Goal**: Add `tests/architectural/test_integration_boundary.py` — AST-scan test that permanently prevents CORE→INTEGRATION leaks from reaching `main`. Introduced only after WP01–WP03 have fixed all three leaks so it passes green from its first commit.
- **Priority**: P1 — gating; must follow WP01–WP03.
- **Requirements**: FR-001, FR-002, FR-003, FR-007, C-008, NFR-001, NFR-002
- **Dependencies**: WP03
- **Subtasks**: T016, T017, T018, T019

---

## WP05 — Architectural documentation

**Prompt**: [tasks/WP05-architectural-docs.md](tasks/WP05-architectural-docs.md)

**Summary**
- **Goal**: Update/add an architectural doc under `architecture/` recording the CORE and INTEGRATION set definitions, the one-directional rule, all allowlist exemptions, and deferred scope items.
- **Priority**: P2 — follows WP04 (allowlist finalised).
- **Requirements**: FR-009
- **Dependencies**: WP04
- **Subtasks**: T020
