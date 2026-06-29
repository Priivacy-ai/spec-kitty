# Contract: invocation/adapters.py Registry

**Contract ID**: invocation-adapters-registry
**Version**: 1.0.0
**Mission**: `integration-boundary-01KW0PBE`
**Reference spec constraint**: FR-008, C-007

---

## Module: `src/specify_cli/invocation/adapters.py`

Mirrors `src/specify_cli/status/adapters.py` exactly. No deviation from the pattern.

### Public API

```python
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Resolver: given repo_root, returns True/False/None (None = no preference)
SyncRoutingResolver = Callable[[Path], bool | None]

# Factory: given repo_root, returns a connected client or None
SaasClientFactory = Callable[[Path], Any | None]

def register_sync_routing_resolver(fn: SyncRoutingResolver) -> None: ...
def register_saas_client_factory(fn: SaasClientFactory) -> None: ...
def resolve_sync_routing(repo_root: Path) -> bool | None: ...
def get_saas_client(repo_root: Path) -> Any | None: ...
def reset_adapters() -> None: ...  # test-only
```

### Invariants

| Invariant | Specification |
|-----------|--------------|
| Non-raising | `resolve_sync_routing` and `get_saas_client` catch all exceptions; return None on any error |
| Idempotent registration | Re-registering a handler with the same `__module__.__qualname__` replaces the existing entry; no duplicates |
| Empty registry is no-op | `resolve_sync_routing` returns None when no resolver registered; `get_saas_client` returns None when no factory registered |
| No third-party imports | The module imports only stdlib and `specify_cli.invocation.*` (C-007) |
| No INTEGRATION imports | The module MUST NOT import from `specify_cli.sync.*`, `specify_cli.tracker.*`, etc. |

### Registration Site

Concrete implementations MUST be registered in
`src/specify_cli/sync/__init__.py::register_default_handlers()` using the same
`contextlib.suppress(ImportError)` guard pattern.

```python
# Resolver lambda — reads CheckoutSyncRouting, returns just effective_sync_enabled
# The lambda is defined in sync/__init__.py where sync.routing is a legal import.
def _sync_routing_resolver(repo_root: Path) -> bool | None:
    from specify_cli.sync.routing import resolve_checkout_sync_routing
    routing = resolve_checkout_sync_routing(repo_root)
    if routing is None:
        return None
    return routing.effective_sync_enabled

# Factory — returns connected WebSocketClient or None
def _saas_client_factory(repo_root: Path) -> Any | None:
    # ... mirrors _get_saas_client logic from propagator.py, moved here
    ...
```

### Degradation Contract

| State | `resolve_sync_routing` returns | `get_saas_client` returns | Propagator behaviour |
|-------|-------------------------------|--------------------------|----------------------|
| No resolver registered | `None` | N/A | Sync-enabled check skipped; propagator continues — same as `resolve_checkout_sync_routing` returning None |
| No factory registered | N/A | `None` | `_get_saas_client` returns None; propagator returns early — existing fast-path |
| Factory registered, not authenticated | N/A | `None` | Same as above |
| Import error on resolve call | `None` (caught) | N/A | Safe fallback |

This contract ensures that if `invocation/` is imported before `sync/` has run
`register_default_handlers()`, the propagator degrades safely — no crash, no data loss.
