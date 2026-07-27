# Data Model: Integration/Core Boundary Sets and Allowlist

**Mission**: `integration-boundary-01KW0PBE`
**ADR**: `architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md`

---

## CORE Set

Modules that implement canonical mission lifecycle and governance logic.
These modules MUST NOT import from the INTEGRATION set.

| Package | Root path | Description |
|---------|-----------|-------------|
| `core` | `src/specify_cli/core/` | Mission creation, contract gate, dependency graph |
| `status` | `src/specify_cli/status/` | State machine, event log, adapter registry |
| `readiness` | `src/specify_cli/readiness/` | Readiness checks and coordinator |
| `invocation` | `src/specify_cli/invocation/` | Op lifecycle propagation and registry |

**Enforcement**: `tests/architectural/test_integration_boundary.py` scans all four
directories with `Path.rglob("*.py")` and `ast.walk`. Any new `.py` file added to
these directories is automatically covered without any test change (FR-001, C-008).

**Path constants in test** (sanity-checked to prevent vacuous passes):

```python
CORE_PACKAGES = [
    SRC / "specify_cli" / "core",
    SRC / "specify_cli" / "status",
    SRC / "specify_cli" / "readiness",
    SRC / "specify_cli" / "invocation",
]
```

---

## INTEGRATION Set

Modules that connect spec-kitty to external systems.
These modules MAY import from the CORE set (allowed direction).

| Package | Root path | Description |
|---------|-----------|-------------|
| `orchestrator_api` | `src/specify_cli/orchestrator_api/` | Orchestrator HTTP client |
| `sync` | `src/specify_cli/sync/` | Real-time SaaS sync, WebSocket, OfflineQueue |
| `tracker` | `src/specify_cli/tracker/` | Issue-tracker origin binding |
| `saas` | `src/specify_cli/saas/` | SaaS-specific feature flags and rollout |
| `saas_client` | `src/specify_cli/saas_client/` | SaaS REST client |

**Pattern constant in test**:

```python
INTEGRATION_PREFIXES = [
    "specify_cli.orchestrator_api",
    "specify_cli.sync",
    "specify_cli.tracker",
    "specify_cli.saas",
    "specify_cli.saas_client",
]
```

---

## Out-of-Scope Modules (C-004)

The following modules are NOT classified in either set for this mission.
Their import patterns are NOT checked by `test_integration_boundary.py`.

| Package | Root path | Reason for exclusion |
|---------|-----------|----------------------|
| `coordination` | `src/specify_cli/coordination/` | Deferred (C-004) |
| `lanes` | `src/specify_cli/lanes/` | Deferred (C-004) |
| `runtime` | `src/specify_cli/runtime/` and `src/runtime/` | Deferred (C-004) |

---

## Allowlist Exemptions

The enforcement test includes a controlled allowlist. Each entry permits one
specific (source_module, imported_module) pair and carries a written rationale.

### Exemption 1 — Leak #2 (the only entry)

| Field | Value |
|-------|-------|
| **Source module** | `src/specify_cli/readiness/coordinator.py` |
| **Imported module** | `specify_cli.saas.rollout` |
| **Import form** | Lazy function-body: `from specify_cli.saas.rollout import is_saas_sync_enabled` at line 237 |
| **Rationale** | `saas/rollout.py` acts as a shared-config module (shared-config v1). `is_saas_sync_enabled` is a pure feature-flag read with no side effects; it is not a structural SaaS dependency. The flag will be relocated to a core/kernel config module in a follow-up mission. Exempted until that relocation lands. |
| **Follow-up** | Planned relocation of `is_saas_sync_enabled` to a core config module (no issue number yet; tracked in `architecture/` docs). |

**No other exemptions exist after WP01–WP03 fix all three leaks.** If a new
exemption is needed, it must be added via an explicit edit to `test_integration_boundary.py`
with a written rationale, not by broadening the allowlist entry above.

---

## New Modules Introduced

### `src/specify_cli/invocation/adapters.py`

Registry for sync-routing resolver and SaaS-client factory, following the
`status/adapters.py` idiom exactly.

```
_sync_routing_resolver: Callable[[Path], bool | None] | None
_saas_client_factory:   Callable[[Path], Any | None]  | None

register_sync_routing_resolver(fn)  → idempotent by qualified name
register_saas_client_factory(fn)    → idempotent by qualified name
resolve_sync_routing(path: Path) → bool | None   # None = no preference registered
get_saas_client(path: Path) → Any | None          # None = no client available
reset_adapters()                    → test-only
```

Invariants:
- Non-raising: both dispatch functions catch all exceptions and return None on error.
- Idempotent: re-registration of same qualified name replaces existing entry.
- No third-party imports (C-007).
- No imports from INTEGRATION set (C-007 / one-directional rule).

### `src/specify_cli/core/adapters.py`

Registry for the pending-origin consumer, exposing a result-bearing callable slot
(needed because `origin_binding_*` fields in `MissionCreationResult` must be
preserved for CLI output).

```
PendingOriginConsumer = Callable[
    [Path, Path, dict[str, Any]],
    tuple[bool, bool, str | None, dict[str, Any]]
]
# Signature: (repo_root, feature_dir, meta) -> (attempted, succeeded, error_msg, updated_meta)

_origin_consumer: PendingOriginConsumer | None

register_pending_origin_consumer(fn: PendingOriginConsumer)  → idempotent
consume_pending_origin(repo_root, feature_dir, meta) → tuple[bool, bool, str|None, dict]
  # Returns (False, False, None, meta) when no consumer is registered (no-op default)
reset_origin_consumer()  → test-only
```

Invariants:
- Non-raising: failure in the consumer is caught; returns `(True, False, str(exc), meta)`.
- No imports from INTEGRATION set.

### `src/specify_cli/tracker/origin_consumer.py`

Concrete implementation of `PendingOriginConsumer`. Contains the logic extracted
from `core/mission_creation.py::_consume_pending_origin_if_present` verbatim.
Registered in `tracker/__init__.py` startup hook.

```
def consume_pending_origin_impl(
    repo_root: Path,
    feature_dir: Path,
    meta: dict[str, Any],
) -> tuple[bool, bool, str | None, dict[str, Any]]:
    """Implementation of PendingOriginConsumer — moves tracker imports here."""
    from specify_cli.tracker.origin import OriginBindingError, bind_mission_origin
    from specify_cli.tracker.origin_models import OriginCandidate
    from specify_cli.tracker.ticket_context import clear_pending_origin, read_pending_origin
    # ... (extracted logic, identical behaviour)
```

---

## Adapter Registry Comparison

| Registry | Module | Handler type | Registration site | Non-raising | Idempotent |
|----------|--------|-------------|-------------------|-------------|------------|
| Dossier-sync | `status/adapters.py` | `DossierSyncHandler` | `sync/__init__.py` | Yes | Yes |
| SaaS fanout | `status/adapters.py` | `SaasFanOutHandler` | `sync/__init__.py` | Yes | Yes |
| Lifecycle SaaS fanout | `status/adapters.py` | `LifecycleSaasFanOutHandler` | `sync/__init__.py` | Yes | Yes |
| Sync-routing resolver | `invocation/adapters.py` | `Callable[[Path], bool|None]` | `sync/__init__.py` | Yes | Yes |
| SaaS-client factory | `invocation/adapters.py` | `Callable[[Path], Any|None]` | `sync/__init__.py` | Yes | Yes |
| Pending-origin consumer | `core/adapters.py` | `PendingOriginConsumer` | `tracker/__init__.py` | Yes | Yes |
