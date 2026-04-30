# Research: P1 Dependency Cycle Cleanup

## Current Import Graph (verified 2026-04-30)

### P1.2 — Dossier ↔ Sync

**Offending edge** (runtime, module-level):
```
specify_cli.dossier.drift_detector  →  specify_cli.sync.project_identity  (ProjectIdentity)
```

**Reverse edges in `sync/dossier_pipeline.py`** — all lazy (function-body) or TYPE_CHECKING:
- Lines 15, 53–61: inside `if TYPE_CHECKING:` block → type-only, no runtime cycle
- Lines 53–61 inside `sync_feature_dossier()` body → lazy runtime; static scanners still flag them as `sync → dossier` (which is the allowed direction, not the forbidden one)

**All callers of `sync.project_identity`:**

| Module | Import type | Action |
|--------|-------------|--------|
| `dossier/drift_detector.py:30` | Runtime module-level | **Update to canonical path** |
| `sync/client.py:34` | Runtime module-level | Keep (sync → sync, no cycle) |
| `sync/dossier_pipeline.py:16` | TYPE_CHECKING | Keep via shim |
| `sync/dossier_pipeline.py:229` | Lazy function-body | Keep via shim |
| `sync/namespace.py:18` | TYPE_CHECKING | Keep via shim |
| `tracker/origin.py:449` | Lazy function-body | Keep via shim (tracker is not dossier) |
| `cli/commands/tracker.py:28` | Runtime module-level | Keep via shim (CLI is not dossier) |

**Single file to update:** `dossier/drift_detector.py`.

### P1.3 — Status → Sync

**Offending edges** (lazy function-body, inside try/except):
```
specify_cli.status.emit  →  specify_cli.sync.dossier_pipeline  (trigger_feature_dossier_sync_if_enabled)
specify_cli.status.emit  →  specify_cli.sync.events             (emit_wp_status_changed)
```
Both are inside `emit_status_transition()` in `status/emit.py` at lines 487 and 518.

---

## Decision: ProjectIdentity relocation

**Decision:** Move to `specify_cli/identity/project.py` inside the existing `specify_cli.identity` leaf package.

**Rationale:**
- `specify_cli.identity` already exists and is explicitly documented as "a leaf package with no dependencies on core or status". Its docstring confirms it is the right home for identity primitives.
- `ProjectIdentity` is consumed by sync, dossier, tracker, and CLI simultaneously. Owning it in any one of those domains would create a dependency from the others on that domain. A neutral leaf package avoids this.
- Moving the whole module into `identity/project.py` (rather than just the dataclass) keeps persistence helpers (`load_identity`, `ensure_identity`, `atomic_write_config`) co-located with the type they manage.

**`generate_node_id` dependency resolution:**
- `project_identity.py` currently imports `from specify_cli.sync.clock import generate_node_id`. `sync.clock` defines this as a simple 3-line hash of `hostname:username`.
- **Decision:** Inline the `generate_node_id` logic directly in `identity/project.py`. The function is trivially reproducible (`hashlib.sha256(f"{socket.gethostname()}:{getpass.getuser()}".encode()).hexdigest()[:12]`). Inlining avoids a transitive `identity → sync` dependency. `sync/clock.py` keeps its own copy unchanged (no callers outside sync/clock need to change).

**Alternatives considered:**
- *Move to `specify_cli.core`* — rejected; core already has `identity_aliases.py` that shims to `specify_cli.identity.aliases`, suggesting identity types live in `identity/`, not `core/`.
- *Dossier-owned module* — rejected; `ProjectIdentity` is used by sync and tracker, not only dossier.

**Shim location:** `specify_cli/sync/project_identity.py` — replace its content with re-exports from `specify_cli.identity.project`. All existing callers outside dossier continue to work unchanged.

---

## Decision: Fan-out adapter pattern (P1.3)

**Decision:** Create `specify_cli/status/adapters.py` with a lightweight callback registry.

**Rationale:**
- The spec requires "no new external package dependencies". A plain callback list (Python stdlib `list` + `Callable`) satisfies this.
- The existing pattern (`try: import ...; call(); except Exception: log`) already treats fan-out as best-effort. The adapter preserves this guarantee: the registry call is wrapped in a broad `try/except` in `emit.py`.
- Sync registers its two handlers (dossier-sync and SaaS fan-out) during daemon initialization, not at module import time. Before registration, the registry is empty and no callbacks fire.

**Adapter interface:**
```python
# specify_cli/status/adapters.py
from typing import Callable, Any
from pathlib import Path

# Two distinct callback types — one per side-effect
DossierSyncHandler = Callable[[Path, str, Path], None]
# (feature_dir, mission_slug, repo_root) → None

SaasFanOutHandler = Callable[..., None]
# Called with the same keyword args as emit_wp_status_changed; returns None

_dossier_handlers: list[DossierSyncHandler] = []
_saas_handlers: list[SaasFanOutHandler] = []

def register_dossier_sync_handler(cb: DossierSyncHandler) -> None: ...
def register_saas_fanout_handler(cb: SaasFanOutHandler) -> None: ...
def fire_dossier_sync(feature_dir, mission_slug, repo_root) -> None: ...
def fire_saas_fanout(**kwargs: Any) -> None: ...
```

**`status/emit.py` change:**
- Remove lazy `from specify_cli.sync.*` imports in steps 8 and 9.
- Replace with `from specify_cli.status.adapters import fire_dossier_sync, fire_saas_fanout`.
- `fire_*` functions are already in the status package — no inter-package import.

**Sync registration site:**
- In `sync/__init__.py` or the daemon startup path, import from `specify_cli.status.adapters` and call `register_dossier_sync_handler` and `register_saas_fanout_handler`. The sync package may import from status (status is the upstream package in the existing dependency graph); this is the normal allowed direction.

**Alternatives considered:**
- *Python `logging.handlers` style* — overkill, adds complexity with no benefit.
- *Pydantic events / event bus library* — rejected; adds external dependency.
- *Entry-points / plugin discovery* — rejected; requires packaging changes, over-engineering.

---

## Existing architectural test infrastructure

`tests/architectural/` contains:
- `conftest.py` — `evaluable` (session-scoped pytestarch graph) and `landscape` (4-layer C4 architecture: kernel ← doctrine ← charter ← specify_cli)
- `test_layer_rules.py` — layer-level rules (e.g., `charter` does not import `specify_cli`)
- `test_auth_transport_singleton.py` — module-level `grep`-based boundary check

**New tests approach:**
- Add `tests/architectural/test_import_boundary_cycles.py` with two `pytest.mark.architectural` test classes:
  - `TestDossierSyncBoundary` — asserts no `specify_cli.dossier` module imports `specify_cli.sync` (using `pytestarch.ModuleRule` or a `grep`-based scan)
  - `TestStatusSyncBoundary` — asserts no `specify_cli.status` module imports `specify_cli.sync`
- The test file is runnable standalone: `uv run pytest tests/architectural/test_import_boundary_cycles.py`
- Existing `tests/architectural/test_layer_rules.py` layer tests are unaffected (they operate at the `specify_cli` aggregate level, not the sub-package level).

---

## Verification commands (confirmed)

```bash
# Ruff clean across affected packages
uv run ruff check src/specify_cli/dossier src/specify_cli/sync src/specify_cli/status tests

# Full affected test suites
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest \
  tests/dossier tests/sync tests/status \
  tests/contract/test_body_sync.py tests/contract/test_tracker_bind.py \
  -q

# Architectural guard (new test)
uv run pytest tests/architectural/test_import_boundary_cycles.py -v
```
