# OpenAPI Stability Contract

The committed snapshot at `tests/test_dashboard/snapshots/openapi.json` is
the canonical OpenAPI document. Any code change that alters the snapshot
must be intentional and explicitly approved by reviewer signoff.

## Allowed changes (snapshot bump expected)

| Change | Reviewer signoff required | Notes |
|--------|---------------------------|-------|
| Add a new route | ✅ yes | New entry under `paths`. PR description must name the route. |
| Add a new optional field on an existing model | ✅ yes | Optional means `Field(default=None)` or absent in `required`. |
| Add a new response status code on an existing route | ✅ yes | E.g., adding a 503 branch. |
| Add a new tag / description / summary on an existing route | ✅ yes | Documentation-only change. |
| Bump FastAPI version | ✅ yes | If the snapshot diff is mechanical (format-only), call it out in the PR. |
| Bump Pydantic version | ✅ yes | Same as above. |

## Prohibited changes (must be a separate redesign mission)

| Change | Reason |
|--------|--------|
| Rename a field on an existing model | C-004 — no contract redesign in this mission. |
| Change a field type on an existing model | C-004 — would break existing consumers. |
| Remove a field from an existing model | C-004. |
| Remove a route | Would break existing consumers; needs deprecation cycle. |
| Change a path parameter name | Path-breaking. |
| Change a status code on an existing branch | Breaking. |

The snapshot test fails on any change. The test message points the developer
back to this document.

## Refresh procedure (when an allowed change is made)

```bash
# 1. Make the FastAPI / model change
# 2. Regenerate the snapshot
PYENV_VERSION=3.13.12 uv run --no-sync python -c "
from dashboard.api.app import create_app
import json, sys
from pathlib import Path
app = create_app(project_dir=Path('.'), project_token=None)
spec = app.openapi()
out = Path('tests/test_dashboard/snapshots/openapi.json')
out.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n', encoding='utf-8')
"
# 3. Inspect the diff carefully — the snapshot test would catch it; the
#    refresh script just makes it easy to update once the change is approved.
git diff tests/test_dashboard/snapshots/openapi.json
```

## How the snapshot test enforces this contract

```python
# tests/test_dashboard/test_openapi_snapshot.py
def test_openapi_snapshot_matches() -> None:
    from dashboard.api.app import create_app
    app = create_app(project_dir=tmp_project, project_token=None)
    actual = json.dumps(app.openapi(), sort_keys=True, indent=2) + "\n"
    expected = SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "OpenAPI snapshot drift detected. If this change is intentional, "
        "regenerate the snapshot per "
        "kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/"
        "contracts/openapi-stability.md and obtain reviewer signoff."
    )
```

A second test asserts the document is valid OpenAPI 3.x via
`openapi_spec_validator.validate_spec`. Any structurally invalid output
(e.g., missing `responses` block) fails this test independently.
