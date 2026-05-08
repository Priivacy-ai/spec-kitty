# Quickstart — Frontend API FastAPI/OpenAPI Migration

A copy-pasteable walk-through for verifying the mission's deliverables on a
local checkout of `feature/650-dashboard-ui-ux-overhaul`.

## Prerequisites

- The `feature/650-dashboard-ui-ux-overhaul` branch is checked out.
- `uv` is installed.
- Python 3.13.12 is available (the repo's `.python-version` pins 3.11 for
  ops, but tests pass on 3.13.12 too — see the test commands below).

## Step 1 — sync the environment

```bash
uv sync --frozen
```

This installs `fastapi`, `uvicorn[standard]`, and ensures Pydantic v2 is in
the resolved dep graph.

## Step 2 — run the dashboard with FastAPI transport

```bash
spec-kitty dashboard --transport fastapi
```

Expected output: the dashboard binds to `127.0.0.1:<port>` and prints the
URL. Open it in a browser. The UI should look identical to the legacy
transport.

## Step 3 — inspect the OpenAPI document

```bash
curl -s http://127.0.0.1:<port>/openapi.json | jq '.info, (.paths | keys)'
```

Expected: a JSON object with `info.title`, `info.version`, and a list of
every dashboard route under `paths`.

Open the interactive docs:

```
http://127.0.0.1:<port>/docs
http://127.0.0.1:<port>/redoc
```

## Step 4 — run the parity test suite

```bash
PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/test_transport_parity.py -q
```

Expected: every parametrized case passes — JSON output is byte-equivalent
between legacy and FastAPI for each route.

## Step 5 — run the snapshot test

```bash
PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/test_openapi_snapshot.py -q
```

Expected: the generated OpenAPI doc matches the committed snapshot at
`tests/test_dashboard/snapshots/openapi.json`.

## Step 6 — run the architectural test

```bash
PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/architectural/test_fastapi_handler_purity.py -q
```

Expected: no FastAPI route handler imports `fastapi.Response` or
`starlette.Response` directly inside the route function body.

## Step 7 — flip back to legacy

```bash
spec-kitty dashboard --transport legacy
```

Expected: the dashboard runs on the legacy `BaseHTTPServer` stack with
identical URLs and JSON shapes. (No `/docs` or `/openapi.json` available
under legacy — those are FastAPI-only.)

Set the default to `legacy` in `.kittify/config.yaml` for sticky rollback:

```yaml
dashboard:
  transport: legacy
```

The CLI flag overrides the config value when present.

## Step 8 — generate TypeScript bindings (smoke-test)

```bash
# Optional: requires Node + npx
npx -y openapi-typescript http://127.0.0.1:<port>/openapi.json -o /tmp/dashboard-types.d.ts
head -50 /tmp/dashboard-types.d.ts
```

Expected: a `.d.ts` file with TypeScript interfaces for every response
model. The script's exit code is 0.

## Troubleshooting

- **`spec-kitty dashboard` fails with `ModuleNotFoundError: fastapi`**: rerun
  `uv sync --frozen`. The lockfile may not have been refreshed after the dep
  add.
- **Snapshot test fails after a planned change**: regenerate per
  `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md`
  refresh procedure.
- **Parity test fails on a single route**: the legacy and FastAPI responses
  diverge. Inspect with the parity test fixtures; if the divergence is
  unintentional, fix the FastAPI router. If intentional and reviewer-approved,
  add an explicit ignore for that route to the parity test (don't silently
  whitelist).
- **`/docs` shows zero routes**: the FastAPI app failed to mount routers.
  Check the app factory and the order of `app.include_router(...)` calls.
