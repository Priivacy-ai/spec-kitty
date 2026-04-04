# Tracker Binding Context Discovery

## Overview

Replace the manual `--project-slug` bind flow for SaaS-backed tracker providers with a host-resolved discovery and selection workflow. Users should never need to type tracker-native machine metadata (project keys, team IDs, repo paths, numeric IDs) in the normal bind path. The CLI derives local project identity, asks the SaaS host for existing mappings or bindable resource candidates, and persists a stable binding reference returned by the host.

This feature implements the `spec-kitty` CLI side of the accepted ADR `2026-04-04-1-tracker-binding-context-is-discovered-not-user-supplied.md`.

**Scope**: `spec-kitty` CLI repository only. SaaS API contracts are defined here as consumer expectations; implementation is a coordinated dependency on `spec-kitty-saas`.

## Actors

- **Developer**: The primary user who binds their local spec-kitty project to an external tracker resource. They should not need to know or type tracker-native identifiers.
- **CI/Automation Agent**: Scripts and pipelines that bind projects non-interactively using explicit flags (`--bind-ref` with host validation, `--select N` with deterministic ordering).
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

A developer runs `tracker bind --provider github`. The host returns zero candidates (no GitHub repos mapped to the installation, or no installation exists for this provider). The CLI displays a clear error with actionable guidance: verify the tracker is connected in the SaaS dashboard and that the installation has discoverable resources for this provider.

**Acceptance test**: CLI exits with non-zero status and a human-readable message. No config changes. The error message does not suggest typing raw tracker metadata.

### Scenario 4: Non-Interactive Bind (CI/Automation)

A CI pipeline runs `tracker bind --provider linear --bind-ref srm_01HXYZ`. The CLI calls the bind-validate endpoint to confirm the ref is valid on the host. If valid, it persists the `binding_ref` and cached display metadata from the validation response. If invalid, the CLI exits with non-zero status and the host-provided guidance message.

**Acceptance test**: Bind completes without interactive prompts. Config contains the validated `binding_ref` plus display metadata. If the ref is invalid, CLI exits non-zero with no config changes.

### Scenario 5: Non-Interactive Selection

A script runs `tracker bind --provider linear --select 1`. The CLI runs discovery, then auto-selects the first candidate without prompting.

**Acceptance test**: Bind completes without interactive prompts. Config contains `binding_ref` for the first candidate.

### Scenario 6: Legacy Config Backward Compatibility

A developer has an existing `.kittify/config.yaml` with `provider: linear` and `project_slug: my-project` but no `binding_ref`. They run `tracker status`. The CLI uses `project_slug` to query the SaaS host. The host response includes a `binding_ref`. The CLI opportunistically writes `binding_ref` back to config without disrupting the status output.

**Acceptance test**: Status works with legacy config. After the call, config now also contains `binding_ref`. If the host does not return a `binding_ref`, the config is left unchanged.

### Scenario 7a: Opportunistic Upgrade Skipped (Upgrade Metadata Unavailable)

A developer with a legacy config runs `tracker status`. The status endpoint succeeds and returns tracker status normally, but the response does not include a `binding_ref` (the resolution metadata is unavailable or the host has not yet computed it). The CLI displays status normally and does not modify the config.

**Acceptance test**: Status output is produced using legacy `project_slug` routing. No config changes. No warning displayed (debug-level log only).

### Scenario 7b: Host Unavailable (Status Fails)

A developer runs `tracker status` and the SaaS host is unreachable (network error, 5xx). The CLI reports the connection failure. It does not silently produce stale or fabricated output.

**Acceptance test**: CLI exits with non-zero status and a clear error message about host unavailability. No config changes. No fallback output.

### Scenario 8: Installation-Wide Discovery

A developer runs `tracker discover --provider linear`. The CLI calls the SaaS host for the full resource inventory under their installation. It displays all bindable resources with human-readable labels, provider-specific context, and whether each is already bound to a local project.

**Acceptance test**: All resources from the installation are listed. Already-bound resources are visually distinguished.

### Scenario 9: Installation-Wide Status

A developer runs `tracker status --all`. The CLI displays a summary of all tracked projects/resources across the installation, not just the locally-bound one.

**Acceptance test**: Output includes multiple projects. Output format is clearly different from project-scoped `tracker status`.

### Scenario 10: Re-Bind to Different Resource

A developer with an existing binding runs `tracker bind --provider linear`. The CLI warns that a binding already exists, shows the current binding label, and asks for confirmation before proceeding with discovery and re-bind.

**Acceptance test**: Warning is displayed. If confirmed, new binding replaces old. If declined, no changes.

### Scenario 11: Stale Binding (Mapping Deleted on Host)

A developer has a valid `binding_ref` in local config but the corresponding `ServiceResourceMapping` was deleted or disabled on the SaaS side. They run `tracker status`. The host returns a `binding_not_found` or `mapping_disabled` error for the `binding_ref`. The CLI displays a clear error explaining the binding is stale and instructs the user to re-bind with `tracker bind --provider <provider>`. The stale `binding_ref` is not automatically removed from config (the user must explicitly re-bind).

**Acceptance test**: CLI exits with non-zero status and an actionable error message. Config is not modified. The error message names the stale `binding_ref` and the re-bind command.

### Scenario 12: Stale Binding with Legacy Fallback

A developer has both `binding_ref` and `project_slug` in local config. The `binding_ref` is stale (host returns invalid). The CLI does not silently fall back to `project_slug` routing. It reports the stale binding and requires explicit re-bind.

**Acceptance test**: CLI exits with non-zero status. It does not silently degrade to `project_slug`. The error message is the same as Scenario 11.

## Functional Requirements

| ID | Requirement | Status |
|----|------------|--------|
| FR-001 | `tracker discover --provider <provider>` calls the SaaS resource inventory endpoint and displays all bindable resources under the user's installation with human-readable labels | Proposed |
| FR-002 | `tracker discover` output distinguishes resources already bound to a spec-kitty project from unbound resources | Proposed |
| FR-003 | `tracker bind --provider <provider>` for SaaS providers invokes discovery, resolves local project identity against the host, and either auto-binds (single candidate) or presents numbered selection (multiple candidates) | Proposed |
| FR-004 | `tracker bind --provider <provider> --bind-ref <ref>` validates the ref against the host via bind-validate before persisting; rejects invalid or stale refs with non-zero exit | Proposed |
| FR-005 | `tracker bind --provider <provider> --select N` runs discovery and auto-selects the candidate at `sort_position = N - 1` without interactive prompting; the host guarantees stable candidate ordering for a given installation state | Proposed |
| FR-006 | `--project-slug` is not accepted as a `tracker bind` flag; legacy `project_slug` values in existing configs are supported for read-path compatibility only | Proposed |
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
| FR-018 | When the SaaS host returns an error indicating a `binding_ref` is stale (deleted, disabled, or recreated), the CLI reports the stale binding with an actionable re-bind message and exits non-zero; it does not silently fall back to `project_slug` | Proposed |
| FR-019 | The bind-validate endpoint is called to verify host-supplied or CI-supplied `binding_ref` values before they are persisted locally | Proposed |
| FR-020 | Candidate lists returned by bind-resolve include a `sort_position` ordinal assigned by the host; `--select N` maps deterministically to `sort_position = N - 1` | Proposed |
| FR-021 | The host guarantees stable candidate ordering (confidence descending, then display_label ascending within the same tier) for a given installation state; reordering only occurs when installation state changes | Proposed |

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
      "candidate_token": "cand_01HXYZ...",
      "display_label": "My Project (LINEAR-123)",
      "provider": "linear",
      "provider_context": {
        "team_name": "Engineering",
        "workspace_name": "Acme Corp"
      },
      "binding_ref": "srm_01HXYZ..." | null,
      "bound_project_slug": "my-project" | null,
      "bound_at": "2026-03-01T10:00:00Z" | null
    }
  ],
  "installation_id": "inst_01HXYZ...",
  "provider": "linear"
}
```

**Notes**:
- `candidate_token` is a pre-bind opaque token issued by the host for this discoverable resource. It identifies the resource for the purpose of bind-confirm, regardless of whether a `ServiceResourceMapping` already exists. The host may issue a fresh token per inventory call; it is not persisted locally.
- `binding_ref` is non-null only for resources that already have a `ServiceResourceMapping` (i.e., already bound). For unbound resources it is null — the `binding_ref` is created by bind-confirm.
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
  "candidate_token": "cand_01HXYZ..." | null,
  "binding_ref": "srm_01HXYZ..." | null,
  "candidates": [
    {
      "candidate_token": "cand_01HABC...",
      "display_label": "My Project (LINEAR-123)",
      "confidence": "high" | "medium" | "low",
      "match_reason": "project_slug matches existing mapping",
      "sort_position": 0
    }
  ],
  "display_label": "My Project (LINEAR-123)" | null
}
```

**Notes**:
- `match_type: "exact"` + non-null `candidate_token`: The host found an existing mapping with high confidence. If a `ServiceResourceMapping` already exists, `binding_ref` is also populated and the CLI can skip bind-confirm. If `binding_ref` is null, the CLI must still call bind-confirm with the `candidate_token`.
- `match_type: "candidates"`: Multiple possible matches. CLI presents selection using `sort_position` ordering. `sort_position` is a zero-based stable ordinal assigned by the host; `--select N` maps to `sort_position = N - 1`.
- `match_type: "none"`: No matches found. CLI shows error with guidance.
- `candidates` list is returned in `sort_position` order. The host guarantees stable ordering for a given installation state: confidence descending, then display_label ascending within the same confidence tier.

### Endpoint 3: Bind Confirmation

**Purpose**: Confirm a binding selection and return the stable binding reference. This is the only endpoint that creates or updates a `ServiceResourceMapping` and issues a `binding_ref`.

```
POST /api/v1/tracker/bind-confirm/
  Body (JSON):
    provider: str (required)
    candidate_token: str (required) — the pre-bind token from resolution or inventory
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
- `candidate_token` is the pre-bind token from resource inventory or bind-resolve. The host resolves it to the underlying tracker resource and creates or updates the `ServiceResourceMapping`.
- `binding_ref` is the stable post-bind reference the CLI persists locally. It is only issued by this endpoint (or returned alongside an exact match in bind-resolve when a mapping already exists).
- Idempotency key prevents duplicate bindings on retry.

### Endpoint 4: Binding Validation

**Purpose**: Validate that an existing `binding_ref` is still valid on the host. Used by `--bind-ref` to verify a CI-supplied ref before persisting, and by stale-binding detection.

```
POST /api/v1/tracker/bind-validate/
  Body (JSON):
    provider: str (required)
    binding_ref: str (required)
    project_identity: {
      uuid: str,
      slug: str,
      node_id: str,
      repo_slug: str | null
    }
```

**Response** (200 — valid):
```json
{
  "valid": true,
  "binding_ref": "srm_01HXYZ...",
  "display_label": "My Project (LINEAR-123)",
  "provider": "linear",
  "provider_context": {
    "team_name": "Engineering",
    "workspace_name": "Acme Corp"
  }
}
```

**Response** (200 — invalid):
```json
{
  "valid": false,
  "binding_ref": "srm_01HXYZ...",
  "reason": "mapping_deleted" | "mapping_disabled" | "project_mismatch",
  "guidance": "The bound tracker resource no longer exists. Run `tracker bind --provider linear` to rebind."
}
```

**Notes**:
- Returns 200 in both valid and invalid cases (the request itself succeeded; the binding state is the payload).
- `reason` provides machine-readable classification for CLI error handling.
- `guidance` provides a human-readable message the CLI can display directly.

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

1. If `binding_ref` is present: use it for all SaaS API routing. If the host reports it as stale, fail with an actionable error — do not silently fall back to `project_slug`.
2. If `binding_ref` is absent but `project_slug` is present: use legacy `project_slug` routing (pre-062 compatibility only).
3. `is_configured` property updated to reflect: SaaS binding is configured if `provider` is set AND (`binding_ref` is set OR `project_slug` is set).
4. There is no silent fallback from `binding_ref` to `project_slug`. If a `binding_ref` exists and is stale, the user must explicitly re-bind.

### Opportunistic Upgrade Behavior

- On any successful SaaS API response that includes a `binding_ref` field, the CLI atomically writes it (plus `display_label` and `provider_context` if present) to the local config.
- If the API response does not include `binding_ref`, or if the write fails, the CLI continues without modifying config.
- Opportunistic upgrade is silent (debug-level logging only).

## Success Criteria

1. A normal SaaS-backed bind completes without the user typing a tracker prefix, project key, repo path, or numeric external resource ID.
2. Users with existing `project_slug`-only configs experience no disruption — all existing read-path CLI operations continue to work.
3. The CLI can represent zero, one, or many host-returned bind candidates with human-readable labels and deterministic, stable-ordered selection.
4. Non-interactive workflows (CI, scripting) can bind using `--bind-ref` or `--select N` without any prompts, with host validation ensuring refs are valid before persistence.
5. Installation-wide resource discovery is available as a first-class CLI command (`tracker discover`).
6. The config model converges toward `binding_ref`-primary storage through opportunistic upgrade without forced migration.
7. A stale `binding_ref` (host-side mapping deleted, disabled, or recreated) produces a clear error with re-bind instructions rather than silent failure or silent fallback.

## Key Entities

| Entity | Description | Persistence |
|--------|------------|-------------|
| `ProjectIdentity` | Local project UUID, slug, node_id — derived from repo | `.kittify/config.yaml` (`project` section) |
| `TrackerProjectConfig` | Provider, binding_ref, project_slug, display metadata | `.kittify/config.yaml` (`tracker` section) |
| `BindableResource` | A discovered tracker resource with candidate_token, label, and provider context | Returned by SaaS API; display fields cached in local config after bind |
| `BindCandidate` | A ranked binding candidate with confidence, match reason, and sort_position | Returned by SaaS resolution API; transient (not persisted) |
| `candidate_token` | Pre-bind opaque token identifying a discoverable resource; issued per inventory/resolution call | Transient; passed to bind-confirm to create a binding; never persisted locally |
| `binding_ref` | Post-bind stable identifier for a `ServiceResourceMapping`; issued only by bind-confirm (or returned by bind-resolve when mapping already exists) | Persisted in local config; primary routing key |

## Dependencies

| Dependency | Type | Notes |
|-----------|------|-------|
| `spec-kitty-saas` resource inventory endpoint | Coordinated | Implements `GET /api/v1/tracker/resources/` |
| `spec-kitty-saas` bind resolution endpoint | Coordinated | Implements `POST /api/v1/tracker/bind-resolve/` |
| `spec-kitty-saas` bind confirmation endpoint | Coordinated | Implements `POST /api/v1/tracker/bind-confirm/` |
| `spec-kitty-saas` bind validation endpoint | Coordinated | Implements `POST /api/v1/tracker/bind-validate/` |
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
| SaaS endpoints not ready when CLI ships | CLI discovery features are non-functional | Gate new bind path behind SaaS API availability check; legacy configs with `project_slug` continue to work for read paths only |
| Resolution confidence is too low for auto-bind in practice | Users always see multi-candidate selection, defeating the purpose | Ensure `ProjectIdentity` sends enough context (UUID, slug, node_id, repo_slug) for high-confidence matching |
| Config migration edge cases with hand-edited configs | Unexpected config states after opportunistic upgrade | Defensive parsing in `from_dict()`; unknown fields preserved; write-back only adds fields, never removes |
| Stale `binding_ref` after host-side mapping deletion/disable | Previously working project becomes broken with no recovery path | Explicit stale-binding detection via bind-validate; clear error message with re-bind instructions (FR-018) |
| `candidate_token` expiry or invalidation between discovery and confirmation | User selects a candidate but bind-confirm rejects the token | CLI retries discovery once on token-rejected error; surfaces clear message if retry also fails |

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
| `src/specify_cli/tracker/saas_client.py` | New methods: `resources()`, `bind_resolve()`, `bind_confirm()`, `bind_validate()`; updated `status()` to allow optional `project_slug` |
| `src/specify_cli/tracker/saas_service.py` | New `discover()`, `resolve_binding()`, `confirm_binding()` methods; updated `bind()` to use discovery flow |
| `src/specify_cli/sync/project_identity.py` | No changes expected; consumed as-is for identity derivation |
