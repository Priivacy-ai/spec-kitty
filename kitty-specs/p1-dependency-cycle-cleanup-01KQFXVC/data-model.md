# Data Model: P1 Dependency Cycle Cleanup

This refactor moves two artifacts and introduces one new module. No new persistent
data structures are added. The "data model" here is the module ownership map and
the callback interface contract.

---

## P1.2 — Module relocation: `ProjectIdentity`

### Current ownership

```
specify_cli/sync/project_identity.py
  ├── class ProjectIdentity          (dataclass — owned here today)
  ├── def generate_project_uuid()
  ├── def generate_build_id()
  ├── def derive_project_slug()
  ├── def generate_node_id()         (re-exported from sync.clock)
  ├── def is_writable()
  ├── def atomic_write_config()
  ├── def load_identity()
  ├── def ensure_identity()
  └── def _warn_in_memory()
```

### Target ownership (post-change)

```
specify_cli/identity/project.py      ← NEW FILE (canonical home)
  ├── class ProjectIdentity          (moved, unchanged)
  ├── def generate_project_uuid()    (moved)
  ├── def generate_build_id()        (moved)
  ├── def derive_project_slug()      (moved)
  ├── def generate_node_id()         (INLINED — no longer imported from sync.clock)
  ├── def is_writable()              (moved)
  ├── def atomic_write_config()      (moved)
  ├── def load_identity()            (moved)
  ├── def ensure_identity()          (moved)
  └── def _warn_in_memory()          (moved)

specify_cli/sync/project_identity.py ← SHIM (replaces existing file)
  ├── from specify_cli.identity.project import ProjectIdentity
  ├── from specify_cli.identity.project import ensure_identity
  ├── from specify_cli.identity.project import load_identity
  └── # ... re-export all public names
```

### Invariants

- `specify_cli.identity.project` must not import from `specify_cli.sync`.
- `specify_cli.identity.project` must not import from `specify_cli.dossier`.
- `specify_cli.identity.project` must not import from `specify_cli.status`.
- The shim at `specify_cli.sync.project_identity` exports all names that existed before the move. No caller outside `dossier` needs to change.
- `dossier/drift_detector.py` is updated to import directly from `specify_cli.identity.project`.

### `generate_node_id` dependency

| Module | Before | After |
|--------|--------|-------|
| `specify_cli.sync.clock` | defines `generate_node_id()` | unchanged |
| `specify_cli.sync.project_identity` | imports `generate_node_id` from `sync.clock` | becomes shim; no logic |
| `specify_cli.identity.project` | (new) | inlines `generate_node_id()` using `hashlib` + `socket` + `getpass` |

The inlined implementation is identical to `sync.clock.generate_node_id`.

---

## P1.3 — New module: `specify_cli.status.adapters`

### Module layout

```
specify_cli/status/adapters.py       ← NEW FILE
  ├── DossierSyncHandler             (type alias)
  ├── SaasFanOutHandler              (type alias)
  ├── _dossier_handlers              (module-level registry list)
  ├── _saas_handlers                 (module-level registry list)
  ├── def register_dossier_sync_handler(cb) → None
  ├── def register_saas_fanout_handler(cb) → None
  ├── def fire_dossier_sync(feature_dir, mission_slug, repo_root) → None
  └── def fire_saas_fanout(**kwargs) → None
```

### Callback types

```python
from pathlib import Path
from typing import Callable, Any

DossierSyncHandler = Callable[[Path, str, Path], None]
# Positional: feature_dir: Path, mission_slug: str, repo_root: Path

SaasFanOutHandler = Callable[..., None]
# Called with keyword args matching the existing emit_wp_status_changed signature:
#   wp_id, from_lane, to_lane, actor, mission_slug, mission_id,
#   causation_id, policy_metadata, force, reason, review_ref,
#   execution_mode, evidence, ensure_daemon
```

### Invariants

- `status/adapters.py` must not import from `specify_cli.sync`.
- `fire_*` functions wrap each callback call in a broad `try/except Exception` and log failures; they never raise.
- Before any handler is registered, `fire_*` calls are no-ops (empty list, no iterations).
- Registration is not thread-safe by design (handlers are registered once at startup, before concurrent access).

### sync registration site

```
specify_cli/sync/__init__.py  (or daemon startup module)
  # The sync package may import from status (sync → status is the
  # allowed direction). Registration happens here:
  from specify_cli.status.adapters import (
      register_dossier_sync_handler,
      register_saas_fanout_handler,
  )
  from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
  from specify_cli.sync.events import emit_wp_status_changed

  register_dossier_sync_handler(trigger_feature_dossier_sync_if_enabled)
  register_saas_fanout_handler(emit_wp_status_changed)
```

### `status/emit.py` change

Steps 8 and 9 in `emit_status_transition()`:

| Before | After |
|--------|-------|
| `from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled` | removed |
| `from specify_cli.sync.events import emit_wp_status_changed` | removed |
| Direct calls to the imported functions | `fire_dossier_sync(...)` / `fire_saas_fanout(...)` |

Import added at top of `status/emit.py`:
```python
from specify_cli.status.adapters import fire_dossier_sync, fire_saas_fanout
```

---

## Architectural boundary map (post-change)

```
specify_cli.identity.project
    ↑ imported by:
    ├── specify_cli.dossier.drift_detector   (no longer cycles through sync)
    ├── specify_cli.sync.project_identity    (shim re-export)
    └── (all existing callers unchanged via shim)

specify_cli.status.adapters
    ↑ imported by:
    ├── specify_cli.status.emit              (replaces lazy sync imports)
    └── specify_cli.sync                    (registration at startup)

FORBIDDEN edges (enforced by new architectural test):
    specify_cli.dossier  →  specify_cli.sync    ✗
    specify_cli.status   →  specify_cli.sync    ✗
```
