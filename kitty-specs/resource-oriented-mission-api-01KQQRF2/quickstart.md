# Quickstart: Resource-Oriented Mission API and HATEOAS-LITE

**Mission**: `resource-oriented-mission-api-01KQQRF2`

## For Implementers

### Key files to read before starting

| File | Why |
|------|-----|
| `src/dashboard/services/registry.py` | `MissionRecord`, `WorkPackageRecord`, `MissionRegistry.list_missions()`, `get_mission()`, `list_work_packages()`, `get_work_package()` |
| `src/dashboard/api/models.py` lines 394–461 | `ResourceModel`, `Link` base classes |
| `src/dashboard/api/deps.py` | `get_mission_registry()` Depends helper |
| `src/dashboard/api/app.py` | Router registration pattern |
| `tests/architectural/test_resource_models_have_links.py` | Arch test that activates in WP01 |
| `tests/architectural/test_transport_does_not_import_scanner.py` | Must stay green throughout |
| `tests/architectural/test_url_naming_convention.py` | Must stay green throughout |
| `tests/test_dashboard/snapshots/openapi.json` | Snapshot to regenerate in WP06 |

### How to run the relevant tests

```bash
# Architectural tests (must stay green after each WP)
cd /path/to/spec-kitty
.venv/bin/python -m pytest tests/architectural/ -q --timeout=60

# Dashboard API tests
.venv/bin/python -m pytest tests/test_dashboard/ -q --timeout=60

# Full suite (run before WP06 snapshot regen)
.venv/bin/python -m pytest tests/test_dashboard/ tests/architectural/ -q --timeout=120
```

### How to regenerate the OpenAPI snapshot (WP06 only)

```bash
# Start the FastAPI dashboard in test mode, fetch /openapi.json, write to snapshot
.venv/bin/python -c "
import json
from dashboard.api.app import create_app
app = create_app('.')
schema = app.openapi()
with open('tests/test_dashboard/snapshots/openapi.json', 'w') as f:
    json.dump(schema, f, indent=2, sort_keys=True)
    f.write('\n')
print('Snapshot written')
"
```

### Deprecation header pattern (WP05)

```python
from fastapi import Response

@router.get("/api/features")
async def list_features_deprecated(response: Response, ...):
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/missions>; rel="successor-version"'
    # ... existing handler body ...
```

### _links construction pattern (WP03, WP04)

```python
from src.dashboard.api.models import Link, MissionSummary

def _mission_links(mission_id: str) -> dict[str, Link]:
    return {
        "self": Link(href=f"/api/missions/{mission_id}"),
        "status": Link(href=f"/api/missions/{mission_id}/status"),
        "workpackages": Link(href=f"/api/missions/{mission_id}/workpackages"),
    }

# In a route handler:
summary = MissionSummary(
    mission_id=record.mission_id,
    ...
    **{"_links": _mission_links(record.mission_id)},
)
```

### Registry 404 / 409 pattern (WP03, WP04)

```python
from fastapi import HTTPException
from dashboard.services.registry import MissionRegistry

async def get_or_404(registry: MissionRegistry, mission_id: str):
    record = registry.get_mission(mission_id)
    if record is None:
        raise HTTPException(404, detail=f"Mission not found: {mission_id}")
    # The registry raises AmbiguousMissionSelector (or similar) for mid8 conflicts;
    # catch that and raise HTTPException(409, ...) instead.
    return record
```

## Definition of Done (per WP)

All WPs must satisfy:
- `pytest tests/architectural/ tests/test_dashboard/ -q` exits 0
- No `# type: ignore` added
- No direct scanner imports in new or modified router files

WP06 additionally requires:
- OpenAPI snapshot matches the running app's `/openapi.json`
- `test_resource_models_have_links.py` is green and non-vacuous (≥5 `ResourceModel` subclasses verified)
- ADR, ownership map, issue-matrix present and committed
