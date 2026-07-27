# Quickstart: P1 Dependency Cycle Cleanup

## Verify the current cycles exist (pre-fix)

```bash
# Confirm dossier → sync edge exists today
grep -r "from specify_cli.sync" src/specify_cli/dossier/ --include="*.py"
# Expected: drift_detector.py line 30 shows sync.project_identity import

# Confirm status → sync edges exist today
grep -r "from specify_cli.sync" src/specify_cli/status/ --include="*.py"
# Expected: emit.py lines 487 and 518 show lazy sync imports
```

## Run the full affected test suite (baseline — must be green before starting)

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest \
  tests/dossier tests/sync tests/status \
  tests/contract/test_body_sync.py tests/contract/test_tracker_bind.py \
  -q
```

All tests must pass on `main` before any implementation begins.

## P1.2: Move ProjectIdentity

### 1. Create `specify_cli/identity/project.py`

Copy all content from `src/specify_cli/sync/project_identity.py` to
`src/specify_cli/identity/project.py`.

Change the `generate_node_id` function — remove the import and inline the logic:

```python
# In identity/project.py — replace the import line:
#   from specify_cli.sync.clock import generate_node_id as generate_machine_node_id
# With this standalone function:

import getpass
import hashlib
import socket

def generate_node_id() -> str:
    """Generate stable machine identifier (hostname + username hash)."""
    hostname = socket.gethostname()
    username = getpass.getuser()
    raw = f"{hostname}:{username}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
```

All other imports in `identity/project.py` are stdlib or third-party — no sync deps.

### 2. Replace `sync/project_identity.py` with a shim

```python
"""Backward-compatible shim. Canonical home: specify_cli.identity.project."""
from specify_cli.identity.project import (
    ProjectIdentity,
    atomic_write_config,
    derive_project_slug,
    ensure_identity,
    generate_build_id,
    generate_node_id,
    generate_project_uuid,
    is_writable,
    load_identity,
)

__all__ = [
    "ProjectIdentity",
    "atomic_write_config",
    "derive_project_slug",
    "ensure_identity",
    "generate_build_id",
    "generate_node_id",
    "generate_project_uuid",
    "is_writable",
    "load_identity",
]
```

### 3. Update `dossier/drift_detector.py`

Change line 30:
```python
# Before
from specify_cli.sync.project_identity import ProjectIdentity
# After
from specify_cli.identity.project import ProjectIdentity
```

### 4. Verify P1.2

```bash
# No dossier → sync imports
grep -r "from specify_cli.sync" src/specify_cli/dossier/ --include="*.py"
# Expected: empty output

# All tests still pass
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/dossier tests/sync -q
```

---

## P1.3: Fan-out adapter

### 1. Create `specify_cli/status/adapters.py`

See `contracts/fan-out-adapter.md` for the full interface. Implement:
- Two `list` registries at module level
- `register_*` functions appending to the registries
- `fire_*` functions iterating with try/except around each call

### 2. Update `status/emit.py`

Add at the top (with other status imports):
```python
from specify_cli.status.adapters import fire_dossier_sync, fire_saas_fanout
```

In `emit_status_transition()`, replace step 8:
```python
# Before (Step 8):
if sync_dossier and repo_root is not None:
    try:
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
        trigger_feature_dossier_sync_if_enabled(feature_dir, mission_slug, repo_root)
    except Exception:
        logger.debug("Dossier sync failed; never blocks status transitions", exc_info=True)

# After (Step 8):
if sync_dossier and repo_root is not None:
    fire_dossier_sync(feature_dir, mission_slug, repo_root)
```

Replace `_saas_fan_out()`:
```python
# Before: lazy import + call to emit_wp_status_changed
# After: delegate to adapter
def _saas_fan_out(event, mission_slug, _repo_root, *, policy_metadata=None, ensure_sync_daemon=True):
    fire_saas_fanout(
        wp_id=event.wp_id,
        from_lane=str(event.from_lane),
        to_lane=str(event.to_lane),
        actor=event.actor,
        mission_slug=mission_slug,
        mission_id=event.mission_id,
        causation_id=event.event_id,
        policy_metadata=policy_metadata,
        force=event.force,
        reason=event.reason,
        review_ref=event.review_ref,
        execution_mode=event.execution_mode,
        evidence=event.evidence.to_dict() if event.evidence else None,
        ensure_daemon=ensure_sync_daemon,
    )
```

### 3. Register sync handlers at startup

In `src/specify_cli/sync/__init__.py` (or the daemon startup path):
```python
from specify_cli.status.adapters import (
    register_dossier_sync_handler,
    register_saas_fanout_handler,
)
from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
from specify_cli.sync.events import emit_wp_status_changed

register_dossier_sync_handler(trigger_feature_dossier_sync_if_enabled)
register_saas_fanout_handler(emit_wp_status_changed)
```

### 4. Verify P1.3

```bash
# No status → sync imports
grep -r "from specify_cli.sync" src/specify_cli/status/ --include="*.py"
# Expected: empty output

# All tests still pass
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/status tests/sync \
  tests/contract/test_body_sync.py tests/contract/test_tracker_bind.py -q
```

---

## Add architectural guard tests

Create `tests/architectural/test_import_boundary_cycles.py`:

```python
"""Architectural guard: no dossier → sync or status → sync import edges."""
import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
pytestmark = pytest.mark.architectural


def _collect_imports(package_path: Path) -> list[tuple[str, str]]:
    """Return (source_file, imported_module) for all imports in a package."""
    edges = []
    for py_file in package_path.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    edges.append((str(py_file), node.module))
    return edges


class TestDossierSyncBoundary:
    def test_dossier_does_not_import_sync(self):
        dossier_path = SRC / "specify_cli" / "dossier"
        edges = _collect_imports(dossier_path)
        violations = [
            (src, mod)
            for src, mod in edges
            if mod.startswith("specify_cli.sync") or mod == "specify_cli.sync"
        ]
        assert not violations, (
            f"specify_cli.dossier must not import specify_cli.sync. "
            f"Violations: {violations}"
        )


class TestStatusSyncBoundary:
    def test_status_does_not_import_sync(self):
        status_path = SRC / "specify_cli" / "status"
        edges = _collect_imports(status_path)
        violations = [
            (src, mod)
            for src, mod in edges
            if mod.startswith("specify_cli.sync") or mod == "specify_cli.sync"
        ]
        assert not violations, (
            f"specify_cli.status must not import specify_cli.sync. "
            f"Violations: {violations}"
        )
```

### Run the guard

```bash
uv run pytest tests/architectural/test_import_boundary_cycles.py -v
```

This test would fail today (pre-fix) and must pass after both P1.2 and P1.3 are complete.

---

## Final verification (run after both fixes)

```bash
# Ruff clean
uv run ruff check src/specify_cli/dossier src/specify_cli/sync src/specify_cli/status tests

# Full suite
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest \
  tests/dossier tests/sync tests/status \
  tests/contract/test_body_sync.py tests/contract/test_tracker_bind.py \
  tests/architectural/ \
  -q
```

Expected: all pass, zero ruff violations.
