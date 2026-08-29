# Contract: sync_active() arming seam

**Location**: `src/specify_cli/core/saas_sync_config.py` (NOT `core/env.py` — post-plan
lens found a real import cycle: `saas_sync_config` already imports `is_truthy` from
`env`, so defining `sync_active()` in `env.py` with a top-level `saas_sync_config`
import creates `env → saas_sync_config → env` and fails at first import. Place it in
`saas_sync_config.py`, which depends one-way on `env` and can import
`first_set_sync_disable_env`.)

```python
# in core/saas_sync_config.py
def sync_active() -> bool:
    """True iff the legacy sync surface is armed. Machine-level arming only —
    NOT per-project egress consent (see sync/egress.py). Disable/minimal-import wins."""
    return is_saas_sync_enabled() and first_set_sync_disable_env() is None
```

## Consumers (route through here; REPLACE prior scattered checks)
| Site | Prior gate | New gate |
|------|-----------|----------|
| `sync/__init__.py:455/458` register_default_handlers | MINIMAL_IMPORT only | gate the **function body (call-time)**, not import-time, so the function stays unconditionally callable and the late-bind seam (C-006) holds |
| `sync/daemon.py:1131/1154` implicit spawn | disable-first + `is_saas_sync_enabled()` | `sync_active()` (name the implicit-spawn fn for the spy) |
| `sync/events.py:109/182` emit/publish | `is_saas_sync_enabled()` | `sync_active()` |
| `sync/emitter.py` `_emit` (top, after envelope construction) | (ungated, #1072) | **`if not sync_active(): return envelope`** — BEFORE `_capture_to_journal` (~2280), the missing-uuid branch (~2308), `_route_event` (2633), and `_queue_event_locally` (2651). Gating `_route_event` alone MISSES the direct `get_emitter().emit_*()` path. Returning the constructed envelope keeps `tests/contract/test_event_envelope.py` (asserts emit_* non-None) green while enqueue/persist/warn are skipped. |
| `sync/dossier_pipeline.py:471` body-capture | (unconditional) | short-circuit on `not sync_active()` |

## Invariants
- **INV-1**: `sync_active()` false ⇒ no registration, no daemon, no emit, no local-capture, no body-capture. (SC-001)
- **INV-2**: `sync_active()` is strictly upstream of `sync/egress.py` consent; consent semantics unchanged. (C-007)
- **INV-3**: truth table (data-model.md) holds for all 8 toggle combinations. (spec truth table)
- **INV-4**: NO other module re-implements the predicate; all sites import `sync_active`. (DIR-044)
