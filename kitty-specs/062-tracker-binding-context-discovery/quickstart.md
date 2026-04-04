# Quickstart: Tracker Binding Context Discovery

**Feature**: 062-tracker-binding-context-discovery

## What Changed

The `tracker bind` flow for SaaS providers no longer requires `--project-slug`. Instead, the CLI discovers bindable resources from the SaaS host and lets you select one.

## New Commands

### `tracker discover`

Browse all bindable resources under your installation:

```bash
spec-kitty tracker discover --provider linear
```

Output:
```
  #  Resource                      Provider  Workspace     Status
  1  My Project (LINEAR-123)       linear    Acme Corp     ● bound
  2  Backend API (LINEAR-456)      linear    Acme Corp     ○ available
  3  Mobile App (LINEAR-789)       linear    Acme Corp     ○ available
```

JSON output for scripting:
```bash
spec-kitty tracker discover --provider linear --json
```

### `tracker bind` (updated)

Bind with auto-discovery:
```bash
spec-kitty tracker bind --provider linear
# → resolves identity, auto-binds or shows candidates
```

Non-interactive (CI/automation):
```bash
# By bind-ref (validated against host):
spec-kitty tracker bind --provider linear --bind-ref srm_01HXYZ

# By selection number:
spec-kitty tracker bind --provider linear --select 1
```

### `tracker status --all`

Installation-wide status:
```bash
spec-kitty tracker status --all
```

## Config Changes

### Before (pre-062)
```yaml
tracker:
  provider: linear
  project_slug: my-project
```

### After (post-062)
```yaml
tracker:
  provider: linear
  binding_ref: srm_01HXYZ...
  project_slug: my-project          # kept for legacy compat
  display_label: "My Project (LINEAR-123)"
  provider_context:
    team_name: Engineering
    workspace_name: Acme Corp
```

**Backward compatibility**: Existing configs with only `project_slug` continue to work. The CLI opportunistically writes `binding_ref` on successful SaaS calls.

## Key Concepts

| Concept | Description |
|---------|-------------|
| `candidate_token` | Pre-bind opaque token from discovery. Passed to bind-confirm. Never persisted. |
| `binding_ref` | Post-bind stable reference from host. Primary routing key. Persisted in config. |
| Opportunistic upgrade | Successful SaaS calls silently write `binding_ref` to legacy configs. |
| Stale binding | Host-side deletion/disable of mapping. CLI errors with re-bind instructions. |

## Testing

Run the full tracker test suite:
```bash
python -m pytest tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py -x -q
```

Run only the new discovery tests:
```bash
python -m pytest tests/sync/tracker/test_discovery.py tests/sync/tracker/test_saas_client_discovery.py -x -q
```

## Files Changed

| File | What |
|------|------|
| `src/specify_cli/tracker/config.py` | +binding_ref, +display_label, +provider_context |
| `src/specify_cli/tracker/discovery.py` | NEW: dataclasses + selection logic |
| `src/specify_cli/tracker/saas_client.py` | +resources(), +bind_resolve(), +bind_confirm(), +bind_validate() |
| `src/specify_cli/tracker/saas_service.py` | +discover(), +resolve_and_bind(), +_maybe_upgrade_binding_ref() |
| `src/specify_cli/cli/commands/tracker.py` | +discover command, updated bind, +status --all |
