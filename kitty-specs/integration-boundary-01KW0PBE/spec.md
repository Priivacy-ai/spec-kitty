# Mission Specification: Enforce the Integration/Core Boundary Inside specify_cli

**Mission slug**: `integration-boundary-01KW0PBE`
**Mission type**: software-dev
**Target / merge branch**: `feat/integration-boundary`
**Status**: Draft

## Purpose

`src/specify_cli` contains two classes of modules that must not depend on each
other in the same direction: **core** modules (lifecycle governance, status,
readiness, invocation) that implement the canonical mission state machine, and
**integration** modules (orchestrator API, sync, tracker, SaaS client) that
connect spec-kitty to external systems. Today three verified import edges cross
from core into integration, violating the intended one-directional rule and
coupling the governance heart of the product to its outbound adapter tier.

This mission enforces the boundary **in-place** — no physical package moves — by
(a) inverting the three verified leaks so core modules communicate with
integration via the existing adapter/observer registry, (b) adding an
AST-based architectural test that will permanently prevent new leaks from
reaching `main`, and (c) updating documentation so every contributor knows which
modules belong to each tier and why.

Physical extraction to `src/orchestrator/` is explicitly deferred per ADR
`architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md`
and the ownership manifest `architecture/2.x/05_ownership_manifest.yaml`.

## User Scenarios & Testing

**Primary actor**: a spec-kitty contributor making a change that touches a
module in the core set.

**Primary scenario (happy path)**: The contributor adds new logic inside
`status/`, `core/`, `readiness/`, or `invocation/`. Their CI run shows the
architectural boundary test passing. They confirm they have not introduced a
dependency on `sync/`, `tracker/`, `saas/`, `orchestrator_api/`, or
`saas_client/`.

**Violation scenario (must fail closed)**: A contributor adds a direct import
of `specify_cli.sync.something` inside `status/emit.py`. The architectural
test detects the import — including if it is written as a lazy function-body
import or inside an `if TYPE_CHECKING:` block — and the CI run fails with a
message that names the violating file, the offending import path, and the
expected corrective action (route through the adapter registry).

**Exemption scenario**: A contributor reads the enforcement test and finds the
allowlist. They see that `readiness/coordinator.py → saas.rollout` is listed
with a documented rationale (shared-config v1, planned follow-up to relocate).
They understand the exemption is deliberate and not a pattern to copy.

**Edge cases**:
- A new core module is added without a corresponding test update — the boundary
  test scans the whole CORE set, so new files are automatically included without
  any test change.
- An exemption entry becomes stale after a follow-up mission relocates the
  flag — the allowlist entry must be removed alongside the relocation diff.

## Domain Language

| Canonical term | Meaning | Avoid |
|----------------|---------|-------|
| CORE set | The modules `core/`, `status/`, `readiness/`, `invocation/` inside `src/specify_cli/` — implement canonical mission lifecycle and governance logic | "internal modules", "kernel" |
| INTEGRATION set | The modules `orchestrator_api/`, `sync/`, `tracker/`, `saas/`, `saas_client/` inside `src/specify_cli/` — connect spec-kitty to external systems | "adapter modules", "external modules" |
| adapter registry | The observer/callback pattern in `status/adapters.py`; integration modules register handlers at startup; core modules fire events without knowing who listens | "event bus", "plugin system" |
| enforce-in-place | Adding the boundary rule and fixing leaks without moving any module to a different package | "in-place refactor" |
| verified leak | An import edge from CORE to INTEGRATION confirmed present in source (not hypothetical) | "violation", "bug" |
| allowlist exemption | A documented entry in the enforcement test that permits a specific crossing for a stated, time-bounded reason | "whitelist", "ignore" |
| one-directional rule | CORE must not import INTEGRATION; INTEGRATION may import CORE facades — this direction is allowed | "unidirectional dependency" |

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A new test file `tests/architectural/test_integration_boundary.py` MUST exist and pass on `feat/integration-boundary`, enforcing that no module inside the CORE set (`src/specify_cli/core/`, `src/specify_cli/status/`, `src/specify_cli/readiness/`, `src/specify_cli/invocation/`) imports any module in the INTEGRATION set (`src/specify_cli/orchestrator_api/`, `src/specify_cli/sync/`, `src/specify_cli/tracker/`, `src/specify_cli/saas/`, `src/specify_cli/saas_client/`). | Draft |
| FR-002 | The enforcement test MUST use Python `ast` module scanning — the same idiom as `tests/architectural/test_status_sync_boundary.py` — to walk every `.py` file in the CORE set, detecting module-level imports, imports inside `if TYPE_CHECKING:` blocks, and lazy function-body imports. pytestarch alone is insufficient and MUST NOT be used as the sole mechanism. | Draft |
| FR-003 | The enforcement test MUST include a documented exemption allowlist. Each entry MUST carry: the source module, the imported module, and a written rationale. Entries are controlled by editing the test file directly (no separate config). A sanity-check sub-test MUST verify that a known non-exempted violation causes the test to fail, confirming the allowlist cannot be bypassed silently. | Draft |
| FR-004 | **Leak #1** MUST be resolved: `src/specify_cli/core/mission_creation.py` line 30 (`from specify_cli.sync.events import emit_mission_created`), line 540 (lazy import of `specify_cli.sync.dossier_pipeline`), and lines 593–595 (lazy imports of `specify_cli.tracker.origin`, `specify_cli.tracker.origin_models`, `specify_cli.tracker.ticket_context`) MUST be removed. The fix MUST route mission-creation lifecycle events through the existing `status/adapters.py` observer registry by calling `emit_mission_created_local` (already in `src/specify_cli/status/lifecycle_events.py:533`); integration-side observers register at startup to receive the event. | Draft |
| FR-005 | **Leak #1 corollary — collapse duplicates**: The two `emit_mission_created` implementations in `src/specify_cli/sync/events.py` (line 354) and `src/specify_cli/sync/emitter.py` (line 1190) MUST be collapsed to a single canonical implementation in the sync package. The surviving version becomes the registered observer invoked via the `status/adapters.py` fan-out. | Draft |
| FR-006 | **Leak #1 corollary — tracker observer**: Mission-origin binding (`src/specify_cli/tracker/origin.py`, `src/specify_cli/tracker/origin_models.py`, `src/specify_cli/tracker/ticket_context.py`) MUST remain in the tracker module and MUST be wired as a registered observer on the mission-created event. After this fix, `core/mission_creation.py` MUST contain zero direct imports of tracker modules. | Draft |
| FR-007 | **Leak #2** MUST be addressed by an allowlist entry in `test_integration_boundary.py`: `src/specify_cli/readiness/coordinator.py` (line 237: lazy import of `specify_cli.saas.rollout.is_saas_sync_enabled`) is exempted with the rationale: "`saas/rollout.py` acts as a shared-config module (shared-config v1); `is_saas_sync_enabled` will be relocated to a core/kernel config module in a follow-up mission. Exempted until that relocation lands." The import MUST NOT be removed or relocated in this mission. | Draft |
| FR-008 | **Leak #3** MUST be resolved: `src/specify_cli/invocation/propagator.py` line 39 (module-level `from specify_cli.sync.routing import resolve_checkout_sync_routing`) and line 66 (function-body `from specify_cli.sync.client import WebSocketClient`) MUST be removed. The fix MUST introduce `src/specify_cli/invocation/adapters.py` exposing `register_sync_routing_resolver(fn: Callable[[Path], bool | None])` and `register_saas_client_factory(fn: Callable[[Path], Any | None])`, following the non-raising, idempotent-by-qualified-name registration pattern of `status/adapters.py`. The sync package MUST register concrete implementations at startup; `propagator.py` MUST call the resolver and factory through `invocation/adapters.py` instead of importing from the INTEGRATION set directly. | Draft |
| FR-009 | Architectural documentation MUST be updated to record: (a) the CORE and INTEGRATION set definitions, (b) the one-directional rule and its rationale, (c) all allowlist exemptions with justifications and planned follow-up actions, and (d) deferred scope items (physical extraction, bidirectional enforcement, coordination/lanes/runtime). The update MUST be committed on the mission branch alongside the code changes. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The boundary enforcement test MUST complete as part of `pytest tests/architectural/` within the existing suite time budget, so it does not materially slow CI. | Full `tests/architectural/` suite finishes in under 30 s on CI | Draft |
| NFR-002 | A violation report from the enforcement test MUST name the violating source file, the offending import path, and a corrective action, enabling a contributor to diagnose the issue without reading the test implementation. | Violation message includes ≥ 3 diagnostic fields | Draft |
| NFR-003 | No currently-passing test in `tests/` may be broken by the Leak #1 or Leak #3 inversion changes. | 0 newly failing tests | Draft |
| NFR-004 | Each inversion (Leak #1 and Leak #3) MUST be covered by at least one narrow unit or integration test that exercises the new observer/adapter registration path directly, so the Sonar new-code coverage gate does not regress. | ≥ 1 targeted test per inversion | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | No module may be physically moved to a different package in this mission. Physical extraction to `src/orchestrator/` is deferred per ADR `architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md` and the module ownership manifest `architecture/2.x/05_ownership_manifest.yaml`. | Active |
| C-002 | The one-directional rule is CORE-cannot-import-INTEGRATION only. INTEGRATION importing CORE facades (`core.*`, `status.*`, `invocation.*` where INTEGRATION is the caller) is allowed and MUST NOT be broken by any change in this mission. | Active |
| C-003 | Bidirectional boundary enforcement (preventing INTEGRATION from importing CORE) is out of scope for this mission; deferred. | Deferred |
| C-004 | The modules `coordination/`, `lanes/`, and `runtime/` (under `src/specify_cli/` and `src/runtime/`) are not members of either set defined here. Their import patterns are out of scope for this mission's enforcement test. | Active |
| C-005 | `src/specify_cli/saas/rollout.py` and `is_saas_sync_enabled` are not relocated in this mission. The Leak #2 allowlist entry documents the planned follow-up. | Active |
| C-006 | The shim-registry and removal-contract defined in issue #615 are out of scope. Any compatibility notes for this mission are documented as follow-ups only, without creating #615 registry entries. | Active |
| C-007 | `invocation/adapters.py` MUST follow the `status/adapters.py` idiom exactly: non-raising handlers, idempotent registration by qualified name, no new third-party library imports. | Active |
| C-008 | The enforcement test MUST carry `pytest.mark.architectural` and MUST include a path-existence sanity check for every CORE-set directory, ensuring the test fails loudly if a directory is renamed rather than passing vacuously. | Active |

## Success Criteria

1. `pytest tests/architectural/test_integration_boundary.py` passes green on `feat/integration-boundary`, with no CORE-set module carrying a non-exempted import of any INTEGRATION-set module — including lazy and `TYPE_CHECKING` imports.
2. `pytest tests/` is green or at pre-mission parity — zero regressions introduced by the Leak #1 and Leak #3 inversion changes.
3. The allowlist contains exactly one exemption entry (`readiness/coordinator.py → saas.rollout`) with a written rationale and follow-up reference; no other crossing imports remain.
4. A contributor reading the updated architectural documentation can identify the CORE and INTEGRATION sets, the one-directional rule, and the current exemption list in a single read.
5. `git grep` across CORE-set source directories (`src/specify_cli/core/`, `src/specify_cli/status/`, `src/specify_cli/readiness/`, `src/specify_cli/invocation/`) finds zero imports of INTEGRATION-set modules, other than the one allowlisted line.

## Assumptions

1. `status/lifecycle_events.py:emit_mission_created_local` (line 533) already exists with a stable signature. No new core function needs to be created for the Leak #1 inversion — only the call-site in `core/mission_creation.py` changes.
2. The sync package's startup path already registers dossier and SaaS fan-out handlers with `status/adapters.py`; the Leak #1 fix extends this pattern to register a mission-created handler without introducing circular imports.
3. The `invocation/` package's startup path can be extended with a registration call so that `sync` registers its routing resolver and client factory with `invocation/adapters.py` without introducing circular imports.
4. No external consumer of `specify_cli.sync.events.emit_mission_created` outside the `src/specify_cli/` package exists; confirmed by in-repo search before the collapse WP is started.
5. The `tests/architectural/test_status_sync_boundary.py` AST-scan idiom is the approved pattern for this codebase; no architectural-tests working group approval is needed to follow it.

## Out of Scope

- **Physical extraction**: Moving modules to `src/orchestrator/` or any other top-level package. Deferred to a dedicated follow-up mission (ADR 2026-05-11-1).
- **Bidirectional enforcement**: Preventing INTEGRATION from importing CORE is not part of this mission.
- **`coordination/`, `lanes/`, `runtime/` boundary**: These modules are not classified in this mission's CORE or INTEGRATION sets.
- **Relocation of `saas.rollout.is_saas_sync_enabled`**: The shared-config flag stays in place; relocation is a documented follow-up only.
- **Issue #615 shim-registry contract**: No registry entries are created or removed in this mission.
- **New lint tooling or third-party static-analysis frameworks**: The enforcement is purely an AST-scan test; no new tool dependencies are introduced.
