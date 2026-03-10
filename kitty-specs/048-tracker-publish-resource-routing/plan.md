# Implementation Plan: Tracker Publish Resource Routing

**Branch**: `048-tracker-publish-resource-routing` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/048-tracker-publish-resource-routing/spec.md`

## Summary

Add `external_resource_type` and `external_resource_id` to the tracker snapshot publish payload so the SaaS can resolve `ServiceResourceMapping` records (ADR Layer 3) without CLI follow-up fields. The derivation is a pure function of `(provider, credentials)` using a static mapping dict. Jira maps to `("jira_project", credentials["project_key"])`, Linear maps to `("linear_team", credentials["team_id"])`. Unsupported or missing credentials yield `(null, null)`.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: httpx (HTTP client in `sync_publish`), ruamel.yaml (config loading)
**Storage**: N/A (no new persistence — fields derived at publish time)
**Testing**: pytest
**Target Platform**: CLI (cross-platform)
**Project Type**: Single project (Python package)
**Performance Goals**: < 1ms overhead (pure dict lookup, no I/O)
**Constraints**: Must not modify the 15-field Git event envelope; must not add cross-repo contract work
**Scale/Scope**: 2 new payload fields, 1 new private method, ~15 lines of derivation logic, ~80 lines of tests

## Constitution Check

*Constitution file absent — check skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/048-tracker-publish-resource-routing/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal — no unknowns)
├── data-model.md        # Payload extension schema
├── quickstart.md        # Quick reference
├── contracts/           # Updated tracker publish contract
│   └── tracker-snapshot-publish.md
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/tracker/
├── service.py           # sync_publish() — ADD routing fields to payload
│                        #   ADD _resolve_resource_routing() private method
│                        #   ADD RESOURCE_ROUTING_MAP module-level constant
├── config.py            # TrackerProjectConfig — NO CHANGES
├── credentials.py       # TrackerCredentialStore — NO CHANGES
├── factory.py           # build_connector() — NO CHANGES (read-only reference)
└── store.py             # TrackerSqliteStore — NO CHANGES

tests/specify_cli/tracker/
├── test_service_publish.py   # NEW — unit tests for routing derivation + payload
├── test_credentials.py       # EXISTING — NO CHANGES
└── test_store.py             # EXISTING — NO CHANGES
```

**Structure Decision**: All changes land in `src/specify_cli/tracker/service.py` (production code) and a new test file `tests/specify_cli/tracker/test_service_publish.py`. No new modules, no new packages.

## Design

### Resource Routing Map

A module-level constant in `service.py`:

```python
# Canonical wire values — stable contract strings, not display labels.
# Keys: normalized provider name (from normalize_provider()).
# Values: (external_resource_type, credential_key_for_resource_id).
RESOURCE_ROUTING_MAP: dict[str, tuple[str, str]] = {
    "jira": ("jira_project", "project_key"),
    "linear": ("linear_team", "team_id"),
}
```

### Derivation Method

New private method on `TrackerService`:

```python
@staticmethod
def _resolve_resource_routing(
    provider: str,
    credentials: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Derive (external_resource_type, external_resource_id) from provider and credentials.

    Returns (None, None) if the provider has no routing mapping or
    the required credential key is missing/empty.
    """
    entry = RESOURCE_ROUTING_MAP.get(provider)
    if entry is None:
        return None, None
    resource_type, credential_key = entry
    resource_id = credentials.get(credential_key)
    if resource_id is None or not str(resource_id).strip():
        return None, None
    return resource_type, str(resource_id).strip()
```

### Payload Integration

In `sync_publish()`, after the existing payload construction (line ~197), add:

```python
resource_type, resource_id = self._resolve_resource_routing(provider, credentials)

payload = {
    # ... existing fields ...
    "external_resource_type": resource_type,
    "external_resource_id": resource_id,
}
```

### Idempotency Key Update

The current idempotency key in `sync_publish()` (service.py line 215) hashes:
```
f"{provider}|{workspace}|{len(issues)}|{len(mappings)}|{checkpoint_cursor}"
```

This must be extended to include the routing fields. If a user rebinds to a different `project_key` but the issue/mapping/cursor state is unchanged, the hash would be identical and the SaaS would discard the second publish as a duplicate:

```python
idempotency_key = hashlib.sha256(
    f"{provider}|{workspace}|{resource_type}|{resource_id}|{len(issues)}|{len(mappings)}|{payload['checkpoint']['cursor']}".encode("utf-8")
).hexdigest()
```

`resource_type` and `resource_id` may be `None`, which is fine — `str(None)` is stable and deterministic.

### What Does NOT Change

1. **Git event envelope** — `git_branch`, `head_commit_sha`, `repo_slug` in `EventEmitter._emit()` are untouched
2. **Batch API contract** — `/api/v1/events/batch/` request/response format unchanged
3. **TrackerProjectConfig** — no new fields in `.kittify/config.yaml`
4. **TrackerCredentialStore** — no new credential keys; existing `project_key` and `team_id` are already stored by `tracker bind`
5. **Snapshot endpoint URL** — still `POST /api/v1/connectors/trackers/snapshots/`

### Test Matrix

| Test Case | Provider | Credentials | Expected `external_resource_type` | Expected `external_resource_id` |
|-----------|----------|-------------|-----------------------------------|--------------------------------|
| Jira happy path | `"jira"` | `{"project_key": "ACME", ...}` | `"jira_project"` | `"ACME"` |
| Linear happy path | `"linear"` | `{"team_id": "abc-123", ...}` | `"linear_team"` | `"abc-123"` |
| Jira missing key | `"jira"` | `{"base_url": "...", ...}` (no project_key) | `null` | `null` |
| Linear missing team_id | `"linear"` | `{"api_key": "...", ...}` (no team_id) | `null` | `null` |
| Jira empty string | `"jira"` | `{"project_key": "", ...}` | `null` | `null` |
| Jira whitespace-only | `"jira"` | `{"project_key": "  ", ...}` | `null` | `null` |
| Unsupported provider | `"beads"` | `{...}` | `null` | `null` |
| Unknown provider | `"notion"` | `{...}` | `null` | `null` |
| Jira creds present but no routing key | `"jira"` | `{"base_url": "...", "email": "...", "api_token": "..."}` (present but no project_key) | `null` | `null` |
| Idempotency key changes on rebind | `"jira"` | First: `{"project_key": "ACME"}`, Second: `{"project_key": "BETA"}` | Different idempotency keys | — |

### Regression Tests

- Existing `tests/contract/test_handoff_fixtures.py` must continue to pass (validates event envelope schema)
- Existing tracker tests (`test_credentials.py`, `test_store.py`) must pass without modification

## Complexity Tracking

No constitution violations. No complexity justifications needed.
