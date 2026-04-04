# Data Model: Tracker Binding Context Discovery

**Feature**: 062-tracker-binding-context-discovery
**Date**: 2026-04-04

## Entities

### TrackerProjectConfig (evolved)

**Location**: `src/specify_cli/tracker/config.py`
**Persistence**: `.kittify/config.yaml` → `tracker` section

| Field | Type | Default | New? | Description |
|-------|------|---------|------|-------------|
| `provider` | `str \| None` | `None` | No | Normalized provider name (linear, jira, github, gitlab) |
| `binding_ref` | `str \| None` | `None` | **Yes** | Stable SaaS-issued reference for the ServiceResourceMapping. Primary routing key. |
| `project_slug` | `str \| None` | `None` | No | Legacy SaaS routing identifier. Retained for backward compatibility. |
| `display_label` | `str \| None` | `None` | **Yes** | Cached human-readable label from host (e.g., "My Project (LINEAR-123)"). |
| `provider_context` | `dict[str, str] \| None` | `None` | **Yes** | Cached provider-specific display metadata (e.g., team_name, workspace_name). |
| `workspace` | `str \| None` | `None` | No | Local provider workspace/team/project identifier. |
| `doctrine_mode` | `str` | `"external_authoritative"` | No | Ownership mode. |
| `doctrine_field_owners` | `dict[str, str]` | `{}` | No | Field → owner mappings. |

**Validation rules**:
- `is_configured` (SaaS): `provider is not None AND (binding_ref is not None OR project_slug is not None)`
- `is_configured` (Local): `provider is not None AND workspace is not None`
- `binding_ref` and `project_slug` can coexist (post-upgrade state)
- `display_label` and `provider_context` are cached; absence is not an error

**Serialization** (`to_dict()`):
```yaml
tracker:
  provider: linear
  binding_ref: srm_01HXYZ...
  project_slug: my-project
  display_label: "My Project (LINEAR-123)"
  provider_context:
    team_name: Engineering
    workspace_name: Acme Corp
  workspace: null
  doctrine:
    mode: external_authoritative
    field_owners: {}
```

**Deserialization** (`from_dict()`):
- Gracefully handles missing `binding_ref`, `display_label`, `provider_context` (pre-062 configs)
- Unknown fields preserved (forward compatibility)
- `provider_context` parsed as `dict[str, str]` or `None`

### BindableResource (new)

**Location**: `src/specify_cli/tracker/discovery.py`
**Persistence**: Transient (returned by SaaS API, display fields cached in config after bind)

| Field | Type | Description |
|-------|------|-------------|
| `candidate_token` | `str` | Pre-bind opaque token. Identifies this resource for bind-confirm. Not persisted locally. |
| `display_label` | `str` | Human-readable label for CLI display. |
| `provider` | `str` | Normalized provider name. |
| `provider_context` | `dict[str, str]` | Provider-specific display metadata (team_name, workspace_name, etc.). |
| `binding_ref` | `str \| None` | Non-null if resource is already bound (has existing ServiceResourceMapping). |
| `bound_project_slug` | `str \| None` | Spec-kitty project slug if already bound. |
| `bound_at` | `str \| None` | ISO timestamp of binding. |

**Factory method**: `BindableResource.from_api(data: dict[str, Any]) -> BindableResource`
- Parses a single resource entry from the `GET /api/v1/tracker/resources/` response.

**Properties**:
- `is_bound: bool` → `binding_ref is not None`

### BindCandidate (new)

**Location**: `src/specify_cli/tracker/discovery.py`
**Persistence**: Transient (returned by SaaS API bind-resolve, never persisted)

| Field | Type | Description |
|-------|------|-------------|
| `candidate_token` | `str` | Pre-bind opaque token. Passed to bind-confirm. |
| `display_label` | `str` | Human-readable label for selection display. |
| `confidence` | `str` | `"high"`, `"medium"`, or `"low"`. |
| `match_reason` | `str` | Why this candidate matched (e.g., "project_slug matches existing mapping"). |
| `sort_position` | `int` | Zero-based stable ordinal from host. `--select N` maps to `sort_position = N - 1`. |

**Factory method**: `BindCandidate.from_api(data: dict[str, Any]) -> BindCandidate`
- Parses a single candidate entry from the `POST /api/v1/tracker/bind-resolve/` response.

### BindResult (new)

**Location**: `src/specify_cli/tracker/discovery.py`
**Persistence**: Transient (returned by bind-confirm or bind-validate, fields cached in config)

| Field | Type | Description |
|-------|------|-------------|
| `binding_ref` | `str` | Stable post-bind reference. Persisted in local config. |
| `display_label` | `str` | Human-readable label. Cached in config. |
| `provider` | `str` | Normalized provider name. |
| `provider_context` | `dict[str, str]` | Provider-specific display metadata. Cached in config. |
| `bound_at` | `str` | ISO timestamp. |

**Factory method**: `BindResult.from_api(data: dict[str, Any]) -> BindResult`
- Parses the response from `POST /api/v1/tracker/bind-confirm/` or the valid case from `POST /api/v1/tracker/bind-validate/`.

### ValidationResult (new)

**Location**: `src/specify_cli/tracker/discovery.py`
**Persistence**: Transient

| Field | Type | Description |
|-------|------|-------------|
| `valid` | `bool` | Whether the binding_ref is still valid on the host. |
| `binding_ref` | `str` | The ref that was validated. |
| `reason` | `str \| None` | Machine-readable reason if invalid (mapping_deleted, mapping_disabled, project_mismatch). |
| `guidance` | `str \| None` | Human-readable message if invalid. |
| `bind_result` | `BindResult \| None` | Populated if valid; contains display metadata for config caching. |

**Factory method**: `ValidationResult.from_api(data: dict[str, Any]) -> ValidationResult`

### ResolutionResult (new)

**Location**: `src/specify_cli/tracker/discovery.py`
**Persistence**: Transient

| Field | Type | Description |
|-------|------|-------------|
| `match_type` | `str` | `"exact"`, `"candidates"`, or `"none"`. |
| `candidate_token` | `str \| None` | Non-null for exact match. |
| `binding_ref` | `str \| None` | Non-null if exact match already has a ServiceResourceMapping. |
| `display_label` | `str \| None` | Non-null for exact match. |
| `candidates` | `list[BindCandidate]` | Populated for `match_type == "candidates"`. |

**Factory method**: `ResolutionResult.from_api(data: dict[str, Any]) -> ResolutionResult`

### ProjectIdentity (unchanged)

**Location**: `src/specify_cli/sync/project_identity.py`
**Persistence**: `.kittify/config.yaml` → `project` section

No changes. Consumed as-is. The `uuid`, `slug`, `node_id`, and `repo_slug` fields are sent to the bind-resolve and bind-confirm endpoints.

## State Transitions

### Binding Lifecycle

```
                    ┌─────────┐
                    │ unbound │  (no tracker section, or provider-only)
                    └���───┬────┘
                         │
                    tracker bind
                    (discovery flow)
                         │
                         ▼
              ┌──────────────────┐
              │  legacy-bound    │  (provider + project_slug only, pre-062)
              │  (read compat)   │
              └────────┬─────────┘
                       │
              opportunistic upgrade
              (on any successful SaaS call)
                       │
                       ▼
              ┌──────────────────┐
              │  fully-bound     │  (binding_ref + cached display metadata)
              │  (primary state) │
              └────────┬─────────┘
                       │
              host-side deletion/disable
              (detected reactively)
                       │
                       ▼
              ┌──────────────────┐
              │  stale-bound     │  (binding_ref exists but host rejects it)
              │  (error state)   │  → user must run tracker bind to re-bind
              └────────┬─────────┘
                       │
                  tracker bind
                  (re-bind flow)
                       │
                       ▼
              ┌──────────────────┐
              │  fully-bound     │  (new binding_ref replaces old)
              └──────────────────┘
```

### Config Read Precedence (state machine)

```
has_binding_ref? ──yes──▶ use binding_ref for routing
       │                        │
       no                  host rejects? ──yes──▶ StaleBindingError (exit 1)
       │                        │
       ▼                       no
has_project_slug? ──yes──▶ use project_slug (legacy compat)
       │                        │
       no                  response has binding_ref? ──yes──▶ write to config (opportunistic)
       │                        │
       ▼                       no
  not configured               ▼
  (error)                  return result unchanged
```

## Relationships

```
ProjectIdentity ────────────────────────��────────────────┐
  (uuid, slug, node_id, repo_slug)                       │
                                                         │ sent to
TrackerProjectConfig ────────────────────────────┐       │
  (provider, binding_ref, project_slug,          │       │
   display_label, provider_context)              │       │
                                                 │       │
                                    persisted ◀──┘       │
                                    in config            │
                                                         │
SaaS API ◀───────────────────────────────────────────────┘
  │
  ├─ resources/ ──▶ list[BindableResource]
  ├─ bind-resolve/ ──▶ ResolutionResult
  │                     ├─ exact: candidate_token + optional binding_ref
  │                     ├─ candidates: list[BindCandidate]
  │                     └─ none: error
  ├─ bind-confirm/ ──▶ BindResult (binding_ref created)
  └─ bind-validate/ ──▶ ValidationResult (binding_ref still valid?)
```
