# Quickstart: SaaS-Mediated CLI Tracker Reflow

## What This Feature Does

Migrates CLI tracker commands for `linear`, `jira`, `github`, `gitlab` from direct-connector local execution to SaaS API client mode. Removes Azure DevOps. Preserves `beads` and `fp` as local-only providers.

## Architecture At a Glance

```
TrackerService (façade)
  ├── SaaSTrackerService → SaaS HTTP client → spec-kitty SaaS
  └── LocalTrackerService → build_connector() → beads/fp
```

## Key Files

| File | Role |
|------|------|
| `src/specify_cli/tracker/saas_client.py` | NEW: HTTP transport (auth, polling, errors) |
| `src/specify_cli/tracker/saas_service.py` | NEW: SaaS-backed operations (pull/push/run/status/mappings) |
| `src/specify_cli/tracker/local_service.py` | NEW: beads/fp direct-connector operations |
| `src/specify_cli/tracker/service.py` | REFACTORED: thin façade dispatching by provider |
| `src/specify_cli/tracker/config.py` | MODIFIED: added `project_slug` for SaaS binding |
| `src/specify_cli/tracker/factory.py` | MODIFIED: beads/fp only, removed SaaS-backed + Azure |
| `src/specify_cli/cli/commands/tracker.py` | MODIFIED: SaaS vs local dispatch in all commands |

## Provider Classification

```python
SAAS_PROVIDERS = frozenset({"linear", "jira", "github", "gitlab"})
LOCAL_PROVIDERS = frozenset({"beads", "fp"})
REMOVED_PROVIDERS = frozenset({"azure_devops"})
```

## SaaS API Endpoints (Frozen PRI-12 Contract)

| Operation | Method | Path | Async? |
|-----------|--------|------|--------|
| pull | POST | `/api/v1/tracker/pull` | No |
| push | POST | `/api/v1/tracker/push` | Yes (202) |
| run | POST | `/api/v1/tracker/run` | Yes (202) |
| status | GET | `/api/v1/tracker/status` | No |
| health | GET | `/api/v1/tracker/health` | No |
| mappings | GET | `/api/v1/tracker/mappings` | No |
| poll | GET | `/api/v1/tracker/operations/{id}` | No |

All requests carry `Authorization: Bearer <token>` and `X-Team-Slug: <slug>`.
Push/run also carry `Idempotency-Key: <uuid4>`.

## Hard-Break Rules

For SaaS-backed providers:
- `--credential` flags on bind → hard fail
- `map add` → hard fail (mappings read-only from CLI)
- `sync publish` → hard fail (snapshot model removed)
- `azure_devops` provider → hard fail (removed)

No fallback to direct-provider execution. Ever.

## Auth Reuse

The SaaS tracker client reuses:
- `sync/auth.py:CredentialStore` for bearer tokens + team_slug
- `sync/config.py:SyncConfig` for server URL
- `sync/auth.py:AuthClient.refresh_tokens()` for 401 retry

No new auth stores. No duplicate config.

## Error Handling

| HTTP | Action |
|------|--------|
| 200 | Parse response envelope, return |
| 202 | Poll `operations/{id}` (exponential backoff, 5min timeout) |
| 401 | One refresh + retry; if still 401, halt with re-login guidance |
| 429 | Wait `retry_after_seconds`, retry |
| 400 `legacy_flow_forbidden` | Display hard-break guidance |
| 4xx/5xx | Parse error envelope, display message + user_action_required |

## Implementation Order

```
A: saas_client.py    ← foundation, no deps
B: config.py update  ← no deps
C: saas_service.py   ← needs A + B
D: local_service.py  ← needs B
E: service.py façade ← needs C + D
F: tracker.py CLI    ← needs E
G: Azure removal     ← needs E + F
H: tests             ← needs all
```

## Testing

- `test_saas_client.py`: Mock httpx; test all 7 endpoints, 200/202/401/429/error paths
- `test_saas_service.py`: Mock client; test service operations + hard-fails
- `test_local_service.py`: Test beads/fp preserved behavior
- `test_service.py`: Test façade dispatch
- DELETE `test_service_publish.py` (10,526 lines of obsolete snapshot publish tests)
