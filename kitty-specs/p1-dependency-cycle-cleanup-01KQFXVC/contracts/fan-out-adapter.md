# Contract: Fan-Out Adapter Interface

**Module:** `specify_cli.status.adapters`
**Purpose:** Decouple `status/emit.py` from `specify_cli.sync` at the import level while preserving existing SaaS fan-out and dossier-sync behavior.

---

## Public API

### Type aliases

```python
from pathlib import Path
from typing import Callable, Any

DossierSyncHandler = Callable[[Path, str, Path], None]
"""
Handler signature for dossier-sync callbacks.

Args:
    feature_dir:   Absolute path to the mission feature directory.
    mission_slug:  Canonical mission slug string.
    repo_root:     Absolute path to the repository root.
Returns:
    None. Must never raise (handlers are wrapped by fire_dossier_sync).
"""

SaasFanOutHandler = Callable[..., None]
"""
Handler signature for SaaS fan-out callbacks.

Called with keyword arguments matching emit_wp_status_changed:
    wp_id, from_lane, to_lane, actor, mission_slug, mission_id,
    causation_id, policy_metadata, force, reason, review_ref,
    execution_mode, evidence, ensure_daemon
Returns:
    None. Must never raise (handlers are wrapped by fire_saas_fanout).
"""
```

### Registration functions

```python
def register_dossier_sync_handler(cb: DossierSyncHandler) -> None:
    """Append cb to the dossier-sync handler list.

    Idempotency: not guaranteed. Callers must call this exactly once
    at startup (typically at sync daemon initialization).
    """

def register_saas_fanout_handler(cb: SaasFanOutHandler) -> None:
    """Append cb to the SaaS fan-out handler list.

    Same idempotency caveat as register_dossier_sync_handler.
    """
```

### Fire functions (called by `status/emit.py`)

```python
def fire_dossier_sync(
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path,
) -> None:
    """Call all registered dossier-sync handlers.

    Guarantees:
    - Each handler is called in registration order.
    - Exceptions from any handler are caught, logged at DEBUG level,
      and do NOT propagate to the caller.
    - If no handlers are registered, this is a no-op.
    """

def fire_saas_fanout(**kwargs: Any) -> None:
    """Call all registered SaaS fan-out handlers with **kwargs.

    Guarantees:
    - Each handler is called with **kwargs in registration order.
    - Exceptions from any handler are caught, logged at WARNING level,
      and do NOT propagate to the caller.
    - If no handlers are registered, this is a no-op.
    """
```

---

## Behavioral guarantees (unchanged from current implementation)

| Guarantee | Current impl | Post-change impl |
|-----------|-------------|-----------------|
| Canonical status persistence cannot be blocked by fan-out failure | try/except in step 8 and `_saas_fan_out` | `fire_*` wraps each handler in try/except |
| SaaS fan-out fires after canonical persistence (step ordering) | Steps 7 → 8 → 9 in `emit_status_transition` | Steps 7 → fire_saas_fanout → fire_dossier_sync |
| Dossier sync is fire-and-forget | Yes | Yes (no return value inspected) |
| Fan-out disabled = no-op | `is_saas_sync_enabled()` check inside `trigger_feature_dossier_sync_if_enabled` | Handler is registered conditionally (sync package responsibility) or checked inside the handler |

---

## Contract: `specify_cli.identity.project` public API (shim compatibility)

All names currently exported from `specify_cli.sync.project_identity` must be
re-exported by the shim without modification:

| Name | Type |
|------|------|
| `ProjectIdentity` | dataclass |
| `generate_project_uuid` | function |
| `generate_build_id` | function |
| `derive_project_slug` | function |
| `generate_node_id` | function |
| `is_writable` | function |
| `atomic_write_config` | function |
| `load_identity` | function |
| `ensure_identity` | function |

The shim at `specify_cli.sync.project_identity` re-exports all of the above
from `specify_cli.identity.project`. Callers that import from the old path
receive the identical objects with no runtime behavior change.
