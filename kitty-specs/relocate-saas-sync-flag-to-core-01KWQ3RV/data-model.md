# Data Model: Relocate SaaS-Sync Flag to Core

No data entities, schemas, or persisted state. The "model" is the moved symbol set and the re-export graph.

## Moved symbols (INTEGRATION `saas/rollout.py` → CORE `core/saas_sync_config.py`)

| Symbol | Kind | Note |
|--------|------|------|
| `SAAS_SYNC_ENV_VAR` | `str` constant | `"SPEC_KITTY_ENABLE_SAAS_SYNC"` |
| `_TRUTHY_VALUES` | `frozenset[str]` (private) | `{"1","true","yes","on"}` |
| `_DISABLED_MESSAGE` | `str` (private) | byte-frozen (contract) |
| `is_saas_sync_enabled` | `() -> bool` | pure env read |
| `saas_sync_disabled_message` | `() -> str` | returns `_DISABLED_MESSAGE` |

## Re-export graph after the move (single definition, many delegating surfaces)

```
core/saas_sync_config.py   ← the ONE definition (CORE authority)
   ▲ imported by
   ├─ readiness/coordinator.py          (CORE caller — repointed, FR-002)
   └─ saas/rollout.py                   (retained shim: re-exports, FR-003/D-02)
         ▲ re-exported by
         ├─ saas/__init__.py
         ├─ sync/feature_flags.py  → sync/__init__ facade
         └─ tracker/feature_flags.py → tracker/__init__ facade
```

**Invariant**: exactly one `def is_saas_sync_enabled` / `def saas_sync_disabled_message` (NFR-002); every arrow above is a re-export, not a redefinition. Object identity is preserved end-to-end (so `test_rollout.py`'s `is` assertions hold).
