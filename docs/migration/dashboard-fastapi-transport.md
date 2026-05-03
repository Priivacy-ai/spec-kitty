# Dashboard Transport Migration — FastAPI / OpenAPI

**Mission**: `frontend-api-fastapi-openapi-migration-01KQN2JA`
**ADR**: [`2026-05-02-2-fastapi-openapi-transport`](../../architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md)
**Effective in**: spec-kitty release ≥ 4.0.0 (final version pinned at release time)

This document is the operator runbook for the dashboard's transport migration
from the legacy `BaseHTTPServer` + hand-rolled router to FastAPI / Uvicorn.

## What changed

The `spec-kitty dashboard` command now serves the same URLs and the same
JSON response shapes through a FastAPI app instead of a hand-rolled HTTP
server. The change is **transport-only** — no endpoint shape, status code,
header semantics, or operator-visible behavior changed unless explicitly
documented in the "Known behavior differences" section below.

Three new operator-facing surfaces exist on the FastAPI transport:

- `GET /openapi.json` — the auto-generated OpenAPI 3.x document
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc UI

These do not exist on the legacy stack.

## Default

After this mission ships:

```yaml
# .kittify/config.yaml
dashboard:
  transport: fastapi   # default
```

If the config key is absent, the default is `fastapi`.

## How to roll back

There are two ways to switch back to the legacy stack:

### 1. Per-invocation (CLI flag)

```bash
spec-kitty dashboard --transport legacy
```

The CLI flag overrides the config value. Use this when you need a one-off
test of the legacy stack without changing the config.

### 2. Sticky (config file)

```yaml
# .kittify/config.yaml
dashboard:
  transport: legacy
```

Subsequent `spec-kitty dashboard` invocations (without `--transport`) use
the legacy stack until the config is changed.

## Verifying a rollback

After flipping to legacy:

```bash
# 1. Confirm the dashboard starts without errors
spec-kitty dashboard --transport legacy

# 2. Confirm legacy-only behavior: /docs returns 404
curl -i http://127.0.0.1:<port>/docs   # expect: 404

# 3. Confirm response parity for a representative route
curl -s http://127.0.0.1:<port>/api/health | jq

# 4. Run the parity test suite to prove byte-equivalence
PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/test_transport_parity.py -q
```

## Known behavior differences

The migration aims for byte-equivalent JSON across stacks. The following
deltas are documented and intentional; the parity test suite validates
that no other deltas exist.

### Trailing-slash redirects

The FastAPI app is configured with `redirect_slashes=False` to match the
legacy stack. Both transports return `404` for trailing-slash mismatches
(e.g., `/api/features/` vs `/api/features`). Consumers must use the
canonical path.

### Header casing

HTTP header field names are case-insensitive per RFC 7230. The two stacks
may emit different casings (e.g., `Content-Type` vs `content-type`). Any
consumer that relies on a specific casing is out of spec.

### Error response wrapping

Both transports return JSON error payloads with the same top-level keys
(`error`, optional `reason`, optional `detail`). The parity test asserts
this; any divergence is a bug.

### `/openapi.json`, `/docs`, `/redoc`

These exist only on the FastAPI transport. The legacy stack returns `404`
for all three. This is by design — there is no OpenAPI document to serve
under the legacy stack.

## Troubleshooting

### `spec-kitty dashboard` fails with `ModuleNotFoundError: fastapi`

Run `uv sync --frozen` from the repo root. The lockfile may not have been
refreshed after a `git pull` that introduced the FastAPI dependency.

### `/openapi.json` returns 404 even though I'm on the FastAPI stack

Confirm the active transport:

```bash
# from the running process logs (the dashboard prints its transport at startup)
# or:
ps aux | grep "spec-kitty dashboard"   # confirm which command was invoked
```

If the process was started without `--transport` and the config has
`transport: legacy`, the legacy stack is active.

### Snapshot test fails after a planned change

Regenerate the snapshot per
[`kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md`](../../kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md)
refresh procedure. Reviewer signoff is required before merging the snapshot
change.

### Parity test fails on a single route

The legacy and FastAPI responses diverge for that route. Inspect with the
parity test fixtures; if the divergence is unintentional, fix the FastAPI
router. If intentional and reviewer-approved, add an explicit ignore to the
parity test (do not silently whitelist).

## Mission convention notes

This mission ran **lane-less** on `feature/650-dashboard-ui-ux-overhaul`:

- No worktrees were created. Every WP edited the parent branch directly.
- Every `approved → done` transition used the `--done-override-reason`
  flag because the canonical state machine expects lane branches that
  did not exist for this mission.
- No `spec-kitty merge` step was run; the parent branch IS the merge
  target (spec C-001).

This is the documented exception path for missions where the spec
explicitly chooses a single-branch strategy. Future post-merge reviewers
auditing the `status.events.jsonl` for this mission will see consistent
override reasons referencing the lane-less convention — that is the
intended pattern, not a process violation.

If you are reviewing this mission and find the override pattern
surprising, see ADR
[`2026-05-02-2-fastapi-openapi-transport.md`](../../architecture/2.x/adr/2026-05-02-2-fastapi-openapi-transport.md)
§ Consequences for the trade-off rationale.

## MissionRegistry as canonical reader

Mission `mission-registry-and-api-boundary-doctrine-01KQPDBB` (2026-05-03)
introduced the `MissionRegistry` (`src/dashboard/services/registry.py`) as
the single sanctioned reader for mission and work-package data. Every
transport — FastAPI dashboard routers, the CLI `spec-kitty dashboard --json`,
and (when introduced) MCP tools — consumes the registry. Direct imports of
`specify_cli.dashboard.scanner` or `specify_cli.scanner` from any transport
module are forbidden by `DIRECTIVE_API_DEPENDENCY_DIRECTION`
(`src/doctrine/directives/shipped/api-dependency-direction.directive.yaml`),
enforced in CI by `tests/architectural/test_transport_does_not_import_scanner.py`.

If you are adding a new transport (a new FastAPI route, a new CLI subcommand,
a new MCP tool):

1. Construct a `MissionRegistry` with the project root, OR pull one from
   `Depends(get_mission_registry)` if you are inside FastAPI.
2. Call `registry.list_missions()`, `registry.get_mission(handle)`,
   `registry.workpackages_for(handle).list_work_packages()`, etc.
3. Do not import the scanner. The architectural test will fail your PR
   if you do.

### Why this exists

Before this mission, every dashboard request walked `kitty-specs/*/` from
disk. With ~144 missions and a 1-Hz client poll, a single open browser tab
generated ~720 file `open()` syscalls per second. The registry mtime-caches
its filesystem reads; warm-cache requests cost ≤ 5 stat syscalls per request.

See ADR
[`architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md`](../../architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md)
for the architectural decision and rejected alternatives.

## Future deprecation

The legacy `BaseHTTPServer` stack stays in tree for the duration of one
release after FastAPI default-on. A separate retirement mission will:

1. Confirm via metrics / smoke tests that no operator depends on the
   `transport: legacy` path.
2. Remove `src/specify_cli/dashboard/handlers/`, `server.py` legacy branch,
   the `--transport legacy` CLI flag value, and the corresponding config key.
3. Update this runbook to a "history" note.

Until that mission ships, the legacy code remains the sanctioned rollback
target.
