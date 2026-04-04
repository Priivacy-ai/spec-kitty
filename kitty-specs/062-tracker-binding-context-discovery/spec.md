# Tracker Binding Context Discovery

## Overview

Replace the manual `--project-slug` bind flow for SaaS-backed tracker providers with a host-resolved discovery and selection workflow. Users should never need to type tracker-native machine metadata (project keys, team IDs, repo paths, numeric IDs) in the normal bind path. The CLI derives local project identity, asks the SaaS host for existing mappings or bindable resource candidates, and persists a stable binding reference returned by the host.

This feature implements the `spec-kitty` CLI side of the accepted ADR `2026-04-04-1-tracker-binding-context-is-discovered-not-user-supplied.md`.

**Scope**: `spec-kitty` CLI repository only. SaaS API contracts are defined here as consumer expectations; implementation is a coordinated dependency on `spec-kitty-saas`.

## Actors

- **Developer**: The primary user who binds their local spec-kitty project to an external tracker resource. They should not need to know or type tracker-native identifiers.
- **CI/Automation Agent**: Scripts and pipelines that bind projects non-interactively using explicit flags (`--bind-ref`, `--select N`).
- **SaaS Host (spec-kitty-saas)**: The control plane that owns installation inventory, resource discovery, binding resolution, and stable binding references.
- **Tracker Provider**: External systems (Linear, Jira, GitHub, GitLab, future Azure DevOps) whose resources are discovered through the host.

## Motivation

Today the CLI requires `--project-slug` for SaaS-backed tracker binds. This forces users to know and type tracker-native metadata that the system can usually discover itself. The existing SaaS architecture already models installations, user links, and resource mappings — but the CLI bind surface does not leverage that architecture. This feature closes the gap by making binding a discovery and selection workflow instead of a memory test.

## User Scenarios & Testing

### Scenario 1: Auto-Bind (Single Confident Match)

A developer runs `tracker bind --provider linear` in a repo that has a `.kittify/config.yaml` with a `ProjectIdentity`. The CLI derives the local project identity, calls the SaaS resolution endpoint, and the host returns exactly one confident candidate. The CLI binds automatically, displays the bound resource label, and persists the `binding_ref`.

**Acceptance test**: Bind completes without any user input beyond the provider flag. Config contains `binding_ref`. No `--project-slug` was required.

### Scenario 2: Ambiguous Selection (Multiple Candidates)

A developer runs `tracker bind --provider jira`. The host returns three candidate resources (e.g., three Jira projects under the same installation). The CLI displays a numbered list with human-readable labels. The developer types `2` to select the second option. The CLI binds and persists the `binding_ref`.

**Acceptance test**: User sees labeled choices, selects by number, bind completes. Config contains `binding_ref` for the selected resource.

### Scenario 3: No Candidates Found

A developer runs `tracker bind --provider github`. The host returns zero candidates (no GitHub repos mapped to the installation, or no installation exists for this provider). The CLI displays a clear error with actionable guidance: check that the tracker is connected in the SaaS dashboard, or use `--project-slug` as a manual fallback.

**Acceptance test**: CLI exits with non-zero status and a human-readable message. No config changes.

### Scenario 4: Non-Interactive Bind (CI/Automation)

A CI pipeline runs `tracker bind --provider linear --bind-ref srm_01HXYZ`. The CLI skips discovery entirely and persists the provided binding reference directly.

**Acceptance test**: Bind completes without any interactive prompts. Config contains the exact `binding_ref` provided.

### Scenario 5: Non-Interactive Selection

A script runs `tracker bind --provider linear --select 1`. The CLI runs discovery, then auto-selects the first candidate without prompting.

**Acceptance test**: Bind completes without interactive prompts. Config contains `binding_ref` for the first candidate.

### Scenario 6: Legacy Config Backward Compatibility

A developer has an existing `.kittify/config.yaml` with `provider: linear` and `project_slug: my-project` but no `binding_ref`. They run `tracker status`. The CLI uses `project_slug` to query the SaaS host. The host response includes a `binding_ref`. The CLI opportunistically writes `binding_ref` back to config without disrupting the status output.

**Acceptance test**: Status works with legacy config. After the call, config now also contains `binding_ref`. If the host does not return a `binding_ref`, the config is left unchanged.

### Scenario 7: Opportunistic Upgrade Fails Gracefully

A developer with a legacy config runs `tracker status`. The SaaS host is temporarily unavailable, or the resolution is ambiguous. The CLI falls back to legacy `project_slug` routing and does not modify the config.

**Acceptance test**: Status output is produced using legacy routing. No config changes. No error displayed (only a debug-level log).

### Scenario 8: Installation-Wide Discovery

A developer runs `tracker discover --provider linear`. The CLI calls the SaaS host for the full resource inventory under their installation. It displays all bindable resources with human-readable labels, provider-specific context, and whether each is already bound to a local project.

**Acceptance test**: All resources from the installation are listed. Already-bound resources are visually distinguished.

### Scenario 9: Installation-Wide Status

A developer runs `tracker status --all`. The CLI displays a summary of all tracked projects/resources across the installation, not just the locally-bound one.

**Acceptance test**: Output includes multiple projects. Output format is clearly different from project-scoped `tracker status`.

### Scenario 10: Re-Bind to Different Resource

A developer with an existing binding runs `tracker bind --provider linear`. The CLI warns that a binding already exists, shows the current binding label, and asks for confirmation before proceeding with discovery and re-bind.

**Acceptance test**: Warning is displayed. If confirmed, new binding replaces old. If declined, no changes.

## Functional Requirements

| ID | Requirement | Status |
|----|------------|--------|
| FR-001 | `tracker discover --provider <provider>` calls the SaaS resource inventory endpoint and displays all bindable resources under the user's installation with human-readable labels | Proposed |
| FR-002 | `tracker discover` output distinguishes resources already bound to a spec-kitty project from unbound resources | Proposed |
| FR-003 | `tracker bind --provider <provider>` for SaaS providers invokes discovery, resolves local project identity against the host, and either auto-binds (single candidate) or presents numbered selection (multiple candidates) | Proposed |
| FR-004 | `tracker bind --provider <provider> --bind-ref <ref>` skips discovery and persists the provided binding reference directly | Proposed |
| FR-005 | `tracker bind --provider <provider> --select N` runs discovery and auto-selects the Nth candidate without interactive prompting | Proposed |
| FR-006 | `tracker bind --provider <provider> --project-slug <slug>` continues to work as a deprecated manual fallback for backward compatibility | Proposed |
| FR-007 | When discovery returns zero candidates, the CLI exits with a non-zero status and displays actionable guidance | Proposed |
| FR-008 | When a binding already exists and the user runs `tracker bind`, the CLI warns and requires confirmation before re-binding | Proposed |
| FR-009 | `TrackerProjectConfig` stores `binding_ref` as the primary binding key, with `project_slug` retained as cached display/legacy context | Proposed |
| FR-010 | Config read precedence: `binding_ref` first; fall back to `project_slug` if `binding_ref` is absent | Proposed |
| FR-011 | On successful SaaS API responses that include a `binding_ref`, the CLI opportunistically writes it back to local config | Proposed |
| FR-012 | If opportunistic upgrade fails (ambiguous resolution, API unavailable), the CLI continues in legacy mode without modifying config | Proposed |
| FR-013 | `tracker status` remains project-scoped by default, using the bound project's `binding_ref` (or legacy `project_slug`) | Proposed |
| FR-014 | `tracker status --all` displays installation-wide summary of all tracked resources when the SaaS API supports it | Proposed |
| FR-015 | The CLI derives local project identity from `ProjectIdentity` (UUID, slug, node_id) in `.kittify/config.yaml` and sends it to the resolution endpoint | Proposed |
| FR-016 | The SaaS bind confirmation endpoint is called after selection, and its response provides the stable `binding_ref` that is persisted locally | Proposed |
| FR-017 | Cached display metadata (resource label, provider-specific context) is persisted alongside `binding_ref` for offline display | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|------------|-----------|--------|
| NFR-001 | Discovery and bind operations complete within a single user-perceived interaction | < 5 seconds for discovery + selection round-trip (excluding user think time) | Proposed |
| NFR-002 | Legacy configs without `binding_ref` continue to work for all existing CLI operations without user intervention | 100% backward compatibility for read paths | Proposed |
| NFR-003 | All new SaaS API calls follow existing retry and authentication patterns | Same retry/backoff as existing SaaSTrackerClient methods | Proposed |
| NFR-004 | The bind workflow works in degraded TTY contexts (SSH, CI, pipe) | Numbered selection + `--bind-ref`/`--select` flags work without TTY | Proposed |
| NFR-005 | Config migration is convergent: repeated operations eventually populate `binding_ref` without user action | Opportunistic upgrade succeeds on any successful host response containing `binding_ref` | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | No provider discovery logic implemented locally; discovery is a SaaS host responsibility | Active |
| C-002 | No bespoke per-provider bind UX; all providers use the same discovery-selection-bind flow | Active |
| C-003 | No direct provider credentials for SaaS-backed providers; authentication flows through `spec-kitty auth login` and `CredentialStore` | Active |
| C-004 | Scope limited to `spec-kitty` CLI repo; SaaS API implementation is a coordinated dependency | Active |
| C-005 | `project_slug` field is not removed from `TrackerProjectConfig`; deprecation happens in a future release after rollout and telemetry | Active |
| C-006 | The same binding contract must accommodate future providers (e.g., Azure DevOps) without architectural changes | Active |

## SaaS API Consumer Contract

The following API shapes are defined as the consumer contract from the CLI's perspective. The `spec-kitty-saas` team implements these endpoints.

### Endpoint 1: Resource Inventory

**Purpose**: Enumerate all bindable tracker resources under the user's installation for a given provider.

```
GET /api/v1/tracker/resources/
  Query params:
    provider: str (required) — normalized provider name
```

**Response** (200):
```json
{
  "resources": [
    {
      "resource_ref": "srm_01HXYZ...",
      "display_label": "My Project (LINEAR-123)",
      "provider": "linear",
      "provider_context": {
        "team_name": "Engineering",
        "workspace_name": "Acme Corp"
      },
      "bound_project_slug": "my-project" | null,
      "bound_at": "2026-03-01T10:00:00Z" | null
    }
  ],
  "installation_id": "inst_01HXYZ...",
  "provider": "linear"
}
```

**Notes**:
- `resource_ref` is a stable SaaS-issued identifier for the `ServiceResourceMapping` or equivalent.
- `display_label` is a human-readable string the CLI displays directly.
- `provider_context` contains provider-specific metadata for display only (not used for routing by the CLI).
- `bound_project_slug` indicates whether this resource is already bound to a spec-kitty project (null if unbound).
- Existing `GET /api/v1/tracker/status/` (which already accepts optional `project_slug`) may partially serve this role, but a dedicated resources endpoint provides a cleaner contract.

### Endpoint 2: Binding Resolution

**Purpose**: Given a local project identity, resolve it to an existing mapping or rank bindable candidates.

```
POST /api/v1/tracker/bind-resolve/
  Body (JSON):
    provider: str (required)
    project_identity: {
      uuid: str (project UUID from ProjectIdentity),
      slug: str (project slug from ProjectIdentity),
      node_id: str (node ID from ProjectIdentity),
      repo_slug: str | null (user override if set)
    }
```

**Response** (200):
```json
{
  "match_type": "exact" | "candidates" | "none",
  "binding_ref": "srm_01HXYZ..." | null,
  "candidates": [
    {
      "resource_ref": "srm_01HXYZ...",
      "display_label": "My Project (LINEAR-123)",
      "confidence": "high" | "medium" | "low",
      "match_reason": "project_slug matches existing mapping"
    }
  ],
  "display_label": "My Project (LINEAR-123)" | null
}
```

**Notes**:
- `match_type: "exact"` + non-null `binding_ref`: The host found an existing mapping. CLI can auto-bind.
- `match_type: "candidates"`: Multiple possible matches ranked by confidence. CLI presents selection.
- `match_type: "none"`: No matches found. CLI shows error with guidance.
- When `match_type` is `"exact"`, `binding_ref` and `display_label` are populated directly.

### Endpoint 3: Bind Confirmation

**Purpose**: Confirm a binding selection and return the stable binding reference.

```
POST /api/v1/tracker/bind-confirm/
  Body (JSON):
    provider: str (required)
    resource_ref: str (required) — the selected resource_ref from resolution or inventory
    project_identity: {
      uuid: str,
      slug: str,
      node_id: str,
      repo_slug: str | null
    }
  Headers:
    X-Idempotency-Key: str (required)
```

**Response** (200):
```json
{
  "binding_ref": "srm_01HXYZ...",
  "display_label": "My Project (LINEAR-123)",
  "provider": "linear",
  "provider_context": {
    "team_name": "Engineering",
    "workspace_name": "Acme Corp"
  },
  "bound_at": "2026-04-04T08:32:00Z"
}
```

**Notes**:
- `binding_ref` is the stable reference the CLI persists locally.
- Idempotency key prevents duplicate bindings on retry.
- The host creates or updates the `ServiceResourceMapping` and returns the canonical binding state.

### Existing Endpoints (Reused)

- `GET /api/v1/tracker/status/?provider=<provider>` (without `project_slug`): Already works for installation-level status in the SaaS backend. The CLI client should be updated to call it without requiring `project_slug`.
- `GET /api/v1/tracker/mappings/`: Already provider-scoped without `project_slug`. Reusable for installation-wide mapping inspection.

## Config Model Evolution

### Current Shape (Pre-062)

```yaml
tracker:
  provider: linear
  project_slug: my-project
  workspace: null
  doctrine:
    mode: external_authoritative
    field_owners: {}
```

### New Shape (Post-062)

```yaml
tracker:
  provider: linear
  binding_ref: srm_01HXYZ...
  project_slug: my-project          # Retained as cached legacy/display context
  display_label: "My Project (LINEAR-123)"  # Cached from host response
  provider_context:                  # Cached from host response, display only
    team_name: Engineering
    workspace_name: Acme Corp
  workspace: null
  doctrine:
    mode: external_authoritative
    field_owners: {}
```

### Read Precedence

1. If `binding_ref` is present: use it for all SaaS API routing.
2. If `binding_ref` is absent but `project_slug` is present: use legacy `project_slug` routing.
3. `is_configured` property updated to reflect: SaaS binding is configured if `provider` is set AND (`binding_ref` is set OR `project_slug` is set).

### Opportunistic Upgrade Behavior

- On any successful SaaS API response that includes a `binding_ref` field, the CLI atomically writes it (plus `display_label` and `provider_context` if present) to the local config.
- If the API response does not include `binding_ref`, or if the write fails, the CLI continues without modifying config.
- Opportunistic upgrade is silent (debug-level logging only).

## Success Criteria

1. A normal SaaS-backed bind completes without the user typing a tracker prefix, project key, repo path, or numeric external resource ID.
2. Users with existing `project_slug`-only configs experience no disruption — all existing CLI operations continue to work.
3. The CLI can represent zero, one, or many host-returned bind candidates with human-readable labels and deterministic selection.
4. Non-interactive workflows (CI, scripting) can bind using `--bind-ref` or `--select N` without any prompts.
5. Installation-wide resource discovery is available as a first-class CLI command (`tracker discover`).
6. The config model converges toward `binding_ref`-primary storage through opportunistic upgrade without forced migration.

## Key Entities

| Entity | Description | Persistence |
|--------|------------|-------------|
| `ProjectIdentity` | Local project UUID, slug, node_id — derived from repo | `.kittify/config.yaml` (`project` section) |
| `TrackerProjectConfig` | Provider, binding_ref, project_slug, display metadata | `.kittify/config.yaml` (`tracker` section) |
| `BindableResource` | A discovered tracker resource with stable ref, label, and provider context | Returned by SaaS API; cached fields in local config |
| `BindCandidate` | A ranked binding candidate with confidence and match reason | Returned by SaaS resolution API; transient (not persisted) |
| `binding_ref` | Stable SaaS-issued identifier for a `ServiceResourceMapping` | Persisted in local config; primary routing key |

## Dependencies

| Dependency | Type | Notes |
|-----------|------|-------|
| `spec-kitty-saas` resource inventory endpoint | Coordinated | Implements `GET /api/v1/tracker/resources/` |
| `spec-kitty-saas` bind resolution endpoint | Coordinated | Implements `POST /api/v1/tracker/bind-resolve/` |
| `spec-kitty-saas` bind confirmation endpoint | Coordinated | Implements `POST /api/v1/tracker/bind-confirm/` |
| Existing `ProjectIdentity` module | Internal | Already implemented in `src/specify_cli/sync/project_identity.py` |
| Existing `SaaSTrackerClient` | Internal | Extended with new API methods |
| Existing `TrackerProjectConfig` | Internal | Extended with `binding_ref` and display metadata fields |
| Existing `CredentialStore` / auth flow | Internal | No changes needed; reused as-is |

## Assumptions

- The SaaS host can resolve local `ProjectIdentity` (UUID + slug + node_id) to existing mappings or candidates with sufficient confidence for auto-bind in the common case.
- The `binding_ref` value is stable across SaaS deployments and will not change for a given `ServiceResourceMapping`.
- The SaaS resource inventory endpoint returns human-readable display labels that are suitable for direct CLI display without client-side formatting.
- The existing PRI-12 error envelope contract applies to all new endpoints.
- Rate limiting and retry behavior for new endpoints follows the same contract as existing tracker endpoints.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SaaS endpoints not ready when CLI ships | CLI discovery features are non-functional | Feature-flag new bind path; legacy `--project-slug` path remains fully operational |
| Resolution confidence is too low for auto-bind in practice | Users always see multi-candidate selection, defeating the purpose | Ensure `ProjectIdentity` sends enough context (UUID, slug, node_id, repo_slug) for high-confidence matching |
| Config migration edge cases with hand-edited configs | Unexpected config states after opportunistic upgrade | Defensive parsing in `from_dict()`; unknown fields preserved; write-back only adds fields, never removes |

## Related ADRs

- `2026-04-04-1-tracker-binding-context-is-discovered-not-user-supplied.md` (primary)
- `2026-02-11-5-task-tracker-agnostic-connector-architecture.md`
- `2026-02-27-2-host-owned-tracker-persistence-boundary.md`
- `2026-02-27-3-saas-tracker-integration-via-existing-connectors-journey.md`
- `architecture/adrs/2026-03-09-1-prompts-do-not-discover-context-commands-do.md`

## Affected Code

| File | Change |
|------|--------|
| `src/specify_cli/cli/commands/tracker.py` | New `discover` command; updated `bind` command with discovery flow, `--bind-ref`, `--select` flags; updated `status` with `--all` flag |
| `src/specify_cli/tracker/config.py` | `TrackerProjectConfig` gains `binding_ref`, `display_label`, `provider_context` fields; updated `is_configured`, `to_dict`, `from_dict` |
| `src/specify_cli/tracker/saas_client.py` | New methods: `resources()`, `bind_resolve()`, `bind_confirm()`; updated `status()` to allow optional `project_slug` |
| `src/specify_cli/tracker/saas_service.py` | New `discover()`, `resolve_binding()`, `confirm_binding()` methods; updated `bind()` to use discovery flow |
| `src/specify_cli/sync/project_identity.py` | No changes expected; consumed as-is for identity derivation |
