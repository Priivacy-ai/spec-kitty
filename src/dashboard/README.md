# Dashboard API

FastAPI-based dashboard API for Spec Kitty. Serves the web dashboard and exposes REST endpoints for missions, work packages, artifacts, and events.

## API Codegen

### Regenerating the OpenAPI Snapshot

After changing dashboard API routes, regenerate the snapshot:

```bash
cd src
python -c "
from dashboard.api import create_app
import json, pathlib
app = create_app(project_dir='/tmp/test_proj', project_token=None)
schema = app.openapi()
serialized = json.dumps(schema, sort_keys=True, indent=2) + '\n'
pathlib.Path('../tests/test_dashboard/snapshots/openapi.json').write_text(serialized)
print('Snapshot written')
"
```

Then verify:

```bash
cd src
python -c "
import json
schema = json.load(open('../tests/test_dashboard/snapshots/openapi.json'))
paths = schema.get('paths', {})
assert '/api/features' not in paths, 'FAIL: /api/features should not be in schema'
assert '/api/kanban/{feature_id}' not in paths, 'FAIL: /api/kanban should not be in schema'
assert '/api/events/missions' in paths, 'FAIL: /api/events/missions should be in schema'
print('Snapshot verification PASSED')
print('All paths:', sorted(paths.keys()))
"
```

### Generating TypeScript Types

Requires Node.js and npx:

```bash
npx openapi-typescript tests/test_dashboard/snapshots/openapi.json \
  -o src/dashboard/static/ts/api.d.ts
```

The generated file is committed at `src/dashboard/static/ts/api.d.ts` and kept in sync with the OpenAPI snapshot. Regenerate it whenever the snapshot changes.
