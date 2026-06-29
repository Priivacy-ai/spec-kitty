# Implementation Plan: Enforce the Integration/Core Boundary Inside specify_cli

**Branch**: `feat/integration-boundary` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/integration-boundary-01KW0PBE/spec.md`

## Summary

Enforce the one-directional CORE→INTEGRATION boundary inside `src/specify_cli`
**in-place** (no module moves): invert three verified import leaks so that
`core/`, `status/`, `readiness/`, and `invocation/` communicate with
`sync/`, `tracker/`, `saas/`, `orchestrator_api/`, and `saas_client/` only
through the existing adapter/observer registry, then add an AST-based
architectural test that permanently prevents new leaks and update documentation.

Leaks fixed:
- **Leak #1**: `core/mission_creation.py` direct imports of `sync.events`,
  `sync.dossier_pipeline`, and `tracker.*` — inverted via `status/adapters.py`
  fan-out + a new `core/adapters.py` pending-origin consumer registry.
- **Leak #2**: `readiness/coordinator.py → saas.rollout.is_saas_sync_enabled`
  — exempted in the enforcement test with a documented rationale and
  follow-up reference (shared-config v1, planned relocation).
- **Leak #3**: `invocation/propagator.py` direct imports of `sync.routing`
  (module-level) and `sync.client` (function-body lazy) — inverted via a new
  `invocation/adapters.py` resolver/factory registry, mirroring
  `status/adapters.py`.

All three leaks are fixed before the enforcement test is switched on (WP
ordering invariant). Physical extraction to `src/orchestrator/` is deferred per
ADR `architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `specify_cli.status.adapters` (fan-out registry pattern); `specify_cli.status.lifecycle_events.emit_mission_created_local`; `specify_cli.sync.__init__.register_default_handlers`; `spec_kitty_events.lifecycle.MissionCreatedPayload`; stdlib `ast` (enforcement test)
**Storage**: `status.events.jsonl` (append-only lifecycle log, single-write invariant); `OfflineQueue` (SaaS queue, separate from lifecycle log)
**Testing**: pytest — `tests/architectural/` (enforcement test, NFR-001); `tests/invocation/`, `tests/status/`, `tests/core/` (adapter registration unit tests, NFR-004); `tests/sync/` (observer wiring regression)
**Target Platform**: Linux/macOS developer CLI
**Project Type**: single (Python CLI / library)
**Performance Goals**: enforcement test completes within existing `tests/architectural/` 30 s budget (NFR-001)
**Constraints**: enforce-in-place only — no module moves (C-001); CORE-cannot-import-INTEGRATION direction only (C-002/C-003); `invocation/adapters.py` MUST follow `status/adapters.py` idiom exactly — non-raising, idempotent by qualified name, no new third-party imports (C-007); `saas/rollout.py` not relocated — Leak #2 allowlisted (C-005); test carries `pytest.mark.architectural` and path-existence sub-test (C-008)
**Scale/Scope**: 3 leak inversions + 1 new test file + 2 new adapter modules (`invocation/adapters.py`, `core/adapters.py`) + 1 updated architectural doc

## Charter Check

Charter context is `compact` (no project charter file). Standard doctrine applies.
No charter gates to evaluate. Section satisfied.

## Project Structure

### Documentation (this mission)

```
kitty-specs/integration-boundary-01KW0PBE/
├── plan.md              # This file
├── research.md          # Phase 0 output — caller audit + ambiguity resolutions
├── data-model.md        # Phase 1 output — CORE/INTEGRATION sets + allowlist
├── quickstart.md        # Phase 1 output — verify the boundary is enforced
├── contracts/           # Phase 1 output
│   ├── integration-boundary-rule.md
│   └── invocation-adapters-registry-contract.md
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   ├── mission_creation.py   # Remove 3 INTEGRATION import edges (Leak #1 fix)
│   └── adapters.py           # NEW — PendingOriginConsumer registry + fire fn
├── invocation/
│   ├── adapters.py           # NEW — sync-routing resolver + saas-client factory registries
│   └── propagator.py         # Remove module-level sync.routing + lazy sync.client (Leak #3 fix)
├── status/
│   └── adapters.py           # EXTEND — no new INTEGRATION imports; existing fan-out fires
├── tracker/
│   └── origin_consumer.py    # NEW — implements PendingOriginConsumer; registered at startup
└── sync/
    └── __init__.py           # EXTEND register_default_handlers(): add invocation adapter registrations

tests/
├── architectural/
│   └── test_integration_boundary.py  # NEW (FR-001/002/003/007/008, C-008)
├── invocation/
│   └── test_adapters.py              # NEW unit tests for invocation/adapters.py (NFR-004)
└── core/
    └── test_adapters.py              # NEW unit tests for core/adapters.py (NFR-004)
```

**Structure Decision**: Single Python CLI/library. Changes are additive (two new
adapter modules) plus leak-fix edits at three call sites. No module moves.

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — invocation/adapters.py new registry module

- **Purpose**: Create `src/specify_cli/invocation/adapters.py` following the
  `status/adapters.py` idiom exactly: idempotent-by-qualified-name registration,
  non-raising dispatch, no third-party dependencies. Expose
  `register_sync_routing_resolver` and `register_saas_client_factory` with safe
  None-returning defaults when no implementation is registered.
- **Relevant requirements**: FR-008, C-007
- **Affected surfaces**: `src/specify_cli/invocation/adapters.py` (new file);
  `src/specify_cli/invocation/__init__.py` (re-export); `tests/invocation/test_adapters.py` (new)
- **Sequencing/depends-on**: none — purely additive
- **Risks**: If `propagator.py` is edited before this module exists, the import
  will fail. Always create `adapters.py` first in the same WP as the propagator fix.

### IC-02 — Leak #3 fix: invocation/propagator.py

- **Purpose**: Remove the two INTEGRATION imports from `invocation/propagator.py`
  (module-level `sync.routing` line 39; function-body lazy `sync.client` line 66)
  and route both through `invocation/adapters.py`. Register concrete
  implementations in `sync/__init__.py::register_default_handlers()`. Establish the
  safe-degradation guarantee: resolver/factory absent → returns None → propagator
  falls back cleanly (no crash).
- **Relevant requirements**: FR-008, NFR-003, NFR-004, C-007
- **Affected surfaces**: `src/specify_cli/invocation/propagator.py` (edit);
  `src/specify_cli/sync/__init__.py` (extend `register_default_handlers`);
  `tests/invocation/test_adapters.py` (NFR-004 coverage)
- **Sequencing/depends-on**: IC-01
- **Risks**: The resolver now returns `bool | None` (not `CheckoutSyncRouting | None`);
  `propagator.py` only needs `routing.effective_sync_enabled` — the resolver lambda
  in sync reads `CheckoutSyncRouting` and returns just the `bool | None` result.
  Ensure the lambda in sync captures `resolve_checkout_sync_routing` correctly to
  avoid import-time cycles.

### IC-03 — core/adapters.py new pending-origin consumer registry

- **Purpose**: Create `src/specify_cli/core/adapters.py` with a
  `PendingOriginConsumer` callable registry: `register_pending_origin_consumer` +
  `consume_pending_origin(repo_root, feature_dir, meta) -> (bool, bool, str|None,
  dict)`. Default when no consumer is registered: `(False, False, None, meta)`.
  This is the injection point that removes the tracker imports from `core/`.
- **Relevant requirements**: FR-004, FR-006, NFR-003
- **Affected surfaces**: `src/specify_cli/core/adapters.py` (new file);
  `tests/core/test_adapters.py` (new)
- **Sequencing/depends-on**: none — purely additive; safe before IC-04
- **Risks**: The callable signature must exactly match the current
  `_consume_pending_origin_if_present` return tuple so `MissionCreationResult`
  fields (`origin_binding_*`) are preserved without any CLI output change.

### IC-04 — Leak #1 fix: core/mission_creation.py

- **Purpose**: Remove all three INTEGRATION import edges from
  `core/mission_creation.py`:
  (a) Line 30 module-level `from specify_cli.sync.events import emit_mission_created`
      — removed entirely; the `emit_mission_created_local` call (already at ~line 468)
      triggers `fire_lifecycle_saas_fanout` automatically via `append_lifecycle_event`,
      which is the single SaaS fan-out path.
  (b) Line 540 lazy `from specify_cli.sync.dossier_pipeline import ...`
      — replaced with `fire_dossier_sync(feature_dir, mission_slug, repo_root)`
      imported from `specify_cli.status.adapters`.
  (c) Lines 593–595 lazy `from specify_cli.tracker.* import ...`
      — `_consume_pending_origin_if_present` body replaced with a call to
      `consume_pending_origin(...)` from `core/adapters.py`.
- **Relevant requirements**: FR-004, FR-006, NFR-003, NFR-004
- **Affected surfaces**: `src/specify_cli/core/mission_creation.py` (3 edit sites)
- **Sequencing/depends-on**: IC-02 (invocation/adapters.py must exist), IC-03 (core/adapters.py must exist)
- **Risks**: The dossier-sync `fire_dossier_sync` call already exists for WP
  status transitions; it should behave identically here since
  `_dossier_sync_handler` is registered in `sync/__init__.py`. Verify the handler
  is registered before mission creation can occur (startup-ordering analysis in
  research.md). Also verify no double-write: `emit_mission_created_local` already
  calls `fire_lifecycle_saas_fanout` internally; removing the direct
  `emit_mission_created(...)` call (line 525) does not add a second write.

### IC-05 — Collapse emit_mission_created duplicate SaaS path (FR-005) + tracker observer wiring

- **Purpose**: Wire the tracker's `PendingOriginConsumer` implementation at startup
  (new `src/specify_cli/tracker/origin_consumer.py` + registration in
  `tracker/__init__.py` or equivalent startup hook). Confirm the single surviving
  SaaS path for MissionCreated is `emit_mission_created_local → fire_lifecycle_saas_fanout
  → _lifecycle_saas_fanout_handler`. If the daemon/WebSocket path for MissionCreated
  needs to be preserved, extend `_lifecycle_saas_fanout_handler` in `sync/__init__.py`
  to also call `_publish_event_via_sync_daemon` and `_request_dashboard_sync` for
  `MissionCreated` envelopes — keeping it inside the registered observer so zero
  direct INTEGRATION imports re-enter core. Write targeted test for the new
  observer registration (NFR-004).
- **Relevant requirements**: FR-005, FR-006, NFR-004
- **Affected surfaces**: `src/specify_cli/tracker/origin_consumer.py` (new);
  `src/specify_cli/tracker/__init__.py` (extend); `src/specify_cli/sync/__init__.py`
  (optionally extend `_lifecycle_saas_fanout_handler`)
- **Sequencing/depends-on**: IC-03 (consumer registry), IC-04 (removal in mission_creation.py)
- **Risks**: Tracker startup registration runs only when `tracker/` is imported.
  Verify that the main CLI entrypoints import `tracker/` before `core/mission_creation.py`
  is called. If not, add explicit import in the `cli/commands/` mission-create path.

### IC-06 — test_integration_boundary.py enforcement test (FR-001/002/003/007/008, C-008)

- **Purpose**: AST-scan test that walks every `.py` file in the CORE set and fails
  if any non-exempted import of the INTEGRATION set is found (module-level,
  `if TYPE_CHECKING:` blocks, and function-body lazy imports all caught).
  Carries `pytest.mark.architectural`. Includes path-existence sub-test for all
  CORE-set directories. Includes one allowlist entry (Leak #2) with source module,
  imported module, and written rationale. Includes sanity sub-test to prove the
  allowlist cannot be bypassed silently.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-007, FR-008, C-008, NFR-001, NFR-002
- **Affected surfaces**: `tests/architectural/test_integration_boundary.py` (new)
- **Sequencing/depends-on**: IC-01, IC-02, IC-03, IC-04, IC-05 — all leaks FIXED before this test is added so it passes green immediately
- **Risks**: The sanity sub-test requires injecting a synthetic violation that is not
  in the allowlist. Implement it by directly invoking `_collect_imports` on a
  constructed source string (no on-disk file needed) and asserting the test would
  catch it.

### IC-07 — Architectural documentation (FR-009)

- **Purpose**: Add or update an architectural doc that records the CORE and
  INTEGRATION set definitions, the one-directional rule and its rationale, all
  allowlist exemptions with follow-up references, and deferred items (physical
  extraction, bidirectional enforcement, `coordination/`/`lanes/`/`runtime/`).
- **Relevant requirements**: FR-009
- **Affected surfaces**: `architecture/` (new or updated doc per `architecture/README.md` template)
- **Sequencing/depends-on**: IC-06 (finalized allowlist known)
- **Risks**: None. Additive documentation only.

## Strictly-Linear WP Sequence

```
WP01 (IC-01 + IC-02): invocation/adapters.py + Leak #3 fix
  → WP02 (IC-03 + IC-04): core/adapters.py + Leak #1 fix in mission_creation.py
    → WP03 (IC-05): tracker observer + emit_mission_created collapse / daemon path
      → WP04 (IC-06): test_integration_boundary.py — all leaks fixed, test passes green
        → WP05 (IC-07): architectural documentation
```

**Invariant**: WP04 (enforcement test) is never introduced before WP01–WP03 have
removed all three leaks. If any WP is rolled back, the test WP must also be
rolled back.
