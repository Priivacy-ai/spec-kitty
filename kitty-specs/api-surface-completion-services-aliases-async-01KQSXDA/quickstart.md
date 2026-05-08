# Quickstart — api-surface-completion-services-aliases-async

Mission: `api-surface-completion-services-aliases-async-01KQSXDA`

All commands assume you are at the repo root unless stated otherwise.

---

## Running Existing Tests

```bash
cd src
pytest tests/
```

Run only the fast-marked subset (no browser, no network):
```bash
cd src
pytest tests/ -m fast
```

Run only dashboard tests:
```bash
cd src
pytest tests/test_dashboard/
```

---

## Running mypy

```bash
cd src
mypy --strict specify_cli/ dashboard/ kernel/
```

**Note:** `src/kernel/` does not exist until this mission creates it. Before WP completion, scope mypy to the files you have changed:

```bash
cd src
mypy --strict specify_cli/glossary/ specify_cli/charter_lint/ dashboard/api/
```

---

## Running the Dashboard Locally for Manual SSE Testing

```bash
cd src
# Option 1: via spec-kitty CLI (preferred — reads project config)
spec-kitty dashboard start

# Option 2: direct uvicorn invocation against a project directory
PYTHONPATH=. uvicorn dashboard.api.app:create_app \
  --factory \
  --host 127.0.0.1 \
  --port 8765

# The factory signature requires project_dir and project_token.
# Use the wrapper script instead:
PYTHONPATH=. python - <<'EOF'
import uvicorn
from pathlib import Path
from dashboard.api import create_app

app = create_app(project_dir=Path(".").resolve(), project_token=None)
uvicorn.run(app, host="127.0.0.1", port=8765)
EOF
```

The dashboard UI is then available at `http://localhost:8765/`.
The SSE endpoint (once implemented) is at `http://localhost:8765/api/events/missions`.

---

## Regenerating the OpenAPI Snapshot

The snapshot is at `tests/test_dashboard/snapshots/openapi.json`.

**Method: run the regeneration script from `src/`:**

```bash
cd src
python - <<'EOF'
import json
from pathlib import Path

# Create a throwaway temp dir for the app factory (not read during openapi())
tmp = Path("_openapi_regen_tmp")
tmp.mkdir(exist_ok=True)

from dashboard.api import create_app
app = create_app(project_dir=tmp.resolve(), project_token=None)
spec_json = json.dumps(app.openapi(), sort_keys=True, indent=2) + "\n"

snapshot_path = Path("../tests/test_dashboard/snapshots/openapi.json")
snapshot_path.write_text(spec_json, encoding="utf-8")

tmp.rmdir()
print(f"Snapshot written to {snapshot_path.resolve()}")
EOF
```

**After regeneration, verify the snapshot test passes:**

```bash
cd src
pytest tests/test_dashboard/test_openapi_snapshot.py -v
```

---

## Running `npx openapi-typescript` Against the Snapshot

Requires Node.js >= 18 with `npx` available.

```bash
# From repo root:
npx openapi-typescript \
  tests/test_dashboard/snapshots/openapi.json \
  --output src/dashboard/static/ts/api.d.ts
```

Inspect the generated types:
```bash
head -40 src/dashboard/static/ts/api.d.ts
```

Verify no drift between snapshot and generated types (CI-style check):
```bash
git diff --exit-code src/dashboard/static/ts/api.d.ts
```

---

## Verifying Alias Retirement Returns HTTP 410

Once the alias retirement WP is complete, verify with `curl`:

```bash
# /api/features should return 410 Gone
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/features
# Expected output: 410

# /api/kanban/<id> should return 410 Gone
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/kanban/some-mission-id
# Expected output: 410

# Inspect the JSON error body
curl -s http://localhost:8765/api/features | python3 -m json.tool
# Expected:
# {
#   "error": "endpoint_retired",
#   "detail": "'/api/features' was retired. Use '/api/missions' instead."
# }

curl -s http://localhost:8765/api/kanban/some-id | python3 -m json.tool
# Expected:
# {
#   "error": "endpoint_retired",
#   "detail": "'/api/kanban/{feature_id}' was retired. Use '/api/missions/{mission_id}/status' instead."
# }
```

Verify the successor endpoints still work:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/missions
# Expected: 200
```

---

## Connecting to the SSE Endpoint Manually

```bash
# Basic connection — streams events until Ctrl-C
curl -N -H "Accept: text/event-stream" \
  http://localhost:8765/api/events/missions

# Resumption from a known event ID (replace with a real ULID from a previous session)
curl -N \
  -H "Accept: text/event-stream" \
  -H "Last-Event-ID: 01KQSXDB0000000000000000AB" \
  http://localhost:8765/api/events/missions
```

Expected output when the endpoint is idle (no transitions in flight):

```
event: connected
data: {"version": "1", "ts": "2026-07-01T12:00:00+00:00"}
id: 01KQSXDAAAAAAAAAAAAAAAAAA

: keepalive

: keepalive
```

Expected output when a WP transition occurs during the stream:

```
event: mission_status
data: {"mission_id": "01J6XW9KABCDE01234567890AB", "mission_slug": "083-my-mission", "wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress", "actor": "claude", "at": "2026-07-01T12:01:00+00:00", "event_id": "01KQSXDB0000000000000000AB"}
id: 01KQSXDB0000000000000000AB
```

To verify keepalive comments arrive every ~15 s:
```bash
curl -N -H "Accept: text/event-stream" \
  http://localhost:8765/api/events/missions \
  | ts '[%H:%M:%S]'   # requires moreutils
```

---

## Running the OpenAPI Validity Test

```bash
cd src
pytest tests/test_dashboard/test_openapi_validity.py -v
```

This test validates that the snapshot is well-formed JSON and conforms to the OpenAPI 3.x schema. Run it after regenerating the snapshot.
