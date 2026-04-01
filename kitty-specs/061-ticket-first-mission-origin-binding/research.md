# Research: Ticket-First Mission Origin Binding

**Feature**: 061-ticket-first-mission-origin-binding
**Date**: 2026-04-01

## R1: Programmatic feature creation

**Question**: Can `start_mission_from_ticket()` create a mission via Python API, or does it need a subprocess call to the CLI?

**Decision**: Extract a reusable core function from `create_feature()`, then call it from `start_mission_from_ticket()`.

**Rationale**: The `create_feature()` function in `src/specify_cli/cli/commands/agent/feature.py` (line 512) is a 300+ line typer command that handles number allocation, directory creation, meta.json scaffolding, git commit, and event emission. However, it returns `None`, emits JSON to stdout, and uses `typer.Exit()` for control flow — making it unsuitable as a service-layer dependency.

**Approach**: Extract the core logic into a neutral module `src/specify_cli/core/feature_creation.py`:
- Public function: `create_feature_core(repo_root, feature_slug, mission, target_branch) -> FeatureCreationResult`
- `FeatureCreationResult` dataclass with `feature_dir`, `feature_slug`, `feature_number`, `meta`, `target_branch`
- Raises domain exceptions (`FeatureCreationError`) instead of `typer.Exit()`
- The existing typer command becomes a thin wrapper
- Placed in `core/` (alongside `paths.py`, `atomic.py`) so any layer can import it without depending on CLI-command modules

**Alternatives considered**:
- Direct function call with SystemExit catching: Fragile, couples service layer to CLI control flow. Rejected.
- Private helper inside `cli/commands/agent/feature.py`: Still makes service layer depend on CLI-command internals. Rejected.
- Subprocess call (`spec-kitty agent feature create-feature --json`): Higher overhead, stdout parsing, harder to test. Rejected.
- Skip extraction, accept fragility: Violates the service-layer contract this spec establishes. Rejected.

## R2: SaaSTrackerClient test patterns

**Question**: What mocking approach should origin.py tests use?

**Decision**: Three-layer mocking strategy consistent with existing tracker tests.

**Rationale**: The test suite uses `unittest.mock.MagicMock` as the dominant pattern across all layers:

1. **HTTP layer** (`test_saas_client.py`): `@patch("specify_cli.tracker.saas_client.httpx.Client")` with `_make_response()` helper to build fake `httpx.Response` objects. Tests auth headers, retry logic, error envelope parsing.

2. **Service layer** (`test_saas_service.py`): Full `MagicMock()` of `SaaSTrackerClient` injected via constructor. Tests service orchestration logic in isolation.

3. **CLI layer** (`test_tracker.py`): `@patch("specify_cli.cli.commands.tracker._service")` with `CliRunner`. Tests command argument parsing and output formatting.

For origin.py, layers 1 and 2 are relevant. Layer 3 is not needed (no CLI commands in this feature).

**Key fixtures to replicate**:
- `mock_credential_store`: MagicMock with `get_access_token()`, `get_team_slug()`, `get_refresh_token()`
- `mock_sync_config`: MagicMock with `get_server_url()`
- `_make_response(status_code, json_body)`: Factory for fake httpx.Response

**Alternatives considered**:
- httpx MockTransport: Not used anywhere in the test suite. Rejected for consistency.
- pytest-httpx: Not a project dependency. Rejected.

## R3: Event type registration

**Question**: How to register `MissionOriginBound` in the emitter?

**Decision**: Extend `_PAYLOAD_RULES` dict and `VALID_EVENT_TYPES` frozenset in `sync/emitter.py`, add `emit_mission_origin_bound()` method to `EventEmitter`.

**Rationale**: All existing event types follow the same registration pattern:
1. Add entry to `_PAYLOAD_RULES` dict with `required` fields set and `validators` dict
2. `VALID_EVENT_TYPES` is derived from `_PAYLOAD_RULES.keys()` — automatically picks up new entries
3. Add `emit_*` method to `EventEmitter` class following the pattern of `emit_feature_created()`

The `MissionOriginBound` event uses `aggregate_type="Feature"` and `aggregate_id=feature_slug`, matching `FeatureCreated` and `FeatureCompleted`.

**Validators needed**:
- `feature_slug`: non-empty string matching feature slug pattern
- `provider`: string in `{"jira", "linear"}`
- `external_issue_id`: non-empty string
- `external_issue_key`: non-empty string
- `external_issue_url`: non-empty string
- `title`: non-empty string

## R4: Metadata mutation helper pattern

**Question**: How should `set_origin_ticket()` be structured?

**Decision**: Follow the pattern of `set_documentation_state()` in `feature_metadata.py`.

**Rationale**: `set_documentation_state()` (line 279) is the closest analogue — it sets a nested dict subtree in meta.json:
```python
def set_documentation_state(feature_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")
    meta["documentation_state"] = state
    write_meta(feature_dir, meta)
    return meta
```

`set_origin_ticket()` will follow the same pattern, accepting the origin_ticket dict and writing it as `meta["origin_ticket"]`.

The `FeatureMetaOptional` TypedDict should also be extended with `origin_ticket: dict[str, Any]` for static type checking documentation.

## R5: Slug derivation from ticket

**Question**: How should `start_mission_from_ticket()` derive a feature slug from the ticket?

**Decision**: Use `external_issue_key` lowercased as the slug base, falling back to a sanitized title.

**Rationale**:
- `WEB-123` → `web-123` (clean, short, unique within a project)
- `IAM-42` → `iam-42`
- If the key contains characters invalid for kebab-case, sanitize with the same rules as `create_feature()` (which enforces `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`)
- The feature number prefix (e.g., `061-`) is added by `create_feature()`, so the slug input is just the kebab-case key

This keeps slugs short, recognizable, and traceable back to the originating ticket.
