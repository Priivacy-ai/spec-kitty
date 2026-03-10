# Feature Specification: Tracker Publish Resource Routing

**Feature Branch**: `048-tracker-publish-resource-routing`
**Created**: 2026-03-10
**Status**: Draft
**Input**: Add `external_resource_type` and `external_resource_id` to CLI tracker snapshot publish payloads so SaaS can resolve `ServiceResourceMapping` records from the ADR's Layer 3 model.

## User Scenarios & Testing

### User Story 1 - Jira Snapshot Publish Includes Resource Routing Keys (Priority: P1)

A developer has bound their spec-kitty project to a Jira instance (`spec-kitty tracker bind --provider jira ...`) with a `project_key` in their credentials. When they run `spec-kitty tracker publish`, the snapshot payload sent to the SaaS includes `external_resource_type: "jira_project"` and `external_resource_id: "ACME"` (the configured project key). The SaaS can use these fields to resolve which `ServiceResourceMapping` record this snapshot belongs to, without any additional CLI round-trips.

**Why this priority**: Jira is the most common tracker integration. Without routing keys, the SaaS must invent its own heuristic to match incoming snapshots to installations and resource mappings — a fragile approach the ADR explicitly rejects.

**Independent Test**: Can be fully tested by binding a Jira tracker with a known project key, calling `sync_publish()`, and asserting the payload contains the correct routing keys.

**Acceptance Scenarios**:

1. **Given** a project bound to Jira with `project_key = "ACME"` in credentials, **When** `sync_publish()` is called, **Then** the HTTP payload includes `"external_resource_type": "jira_project"` and `"external_resource_id": "ACME"`.
2. **Given** a project bound to Jira where `project_key` is missing from credentials, **When** `sync_publish()` is called, **Then** both `external_resource_type` and `external_resource_id` are `null` in the payload (graceful degradation, not a crash).

---

### User Story 2 - Linear Snapshot Publish Includes Resource Routing Keys (Priority: P1)

A developer has bound their spec-kitty project to a Linear workspace with a `team_id` in their credentials. When they run `spec-kitty tracker publish`, the snapshot payload includes `external_resource_type: "linear_team"` and `external_resource_id: "abc-123-def"` (the configured team ID). The SaaS uses these fields identically to the Jira case.

**Why this priority**: Linear is the second supported tracker. Both providers must ship together to avoid a partial contract.

**Independent Test**: Can be fully tested by binding a Linear tracker with a known team ID, calling `sync_publish()`, and asserting the payload contains the correct routing keys.

**Acceptance Scenarios**:

1. **Given** a project bound to Linear with `team_id = "abc-123-def"` in credentials, **When** `sync_publish()` is called, **Then** the HTTP payload includes `"external_resource_type": "linear_team"` and `"external_resource_id": "abc-123-def"`.
2. **Given** a project bound to Linear where `team_id` is missing from credentials, **When** `sync_publish()` is called, **Then** both `external_resource_type` and `external_resource_id` are `null` in the payload.

---

### User Story 3 - Git Event Envelope Unchanged (Priority: P1)

A developer syncs events via the batch event pipeline (`/api/v1/events/batch/`). The event envelope fields — `git_branch`, `head_commit_sha`, `repo_slug` — remain exactly as specified in the event-envelope contract. No new fields are added to the event envelope, and no existing fields are modified.

**Why this priority**: The event envelope is a cross-team contract. Any change would break SaaS ingestion and require coordinated rollout — explicitly out of scope for this mission.

**Independent Test**: Can be tested by emitting events via `EventEmitter` and asserting the envelope schema matches the existing contract exactly, with no new keys.

**Acceptance Scenarios**:

1. **Given** the existing event envelope contract, **When** events are emitted after this feature ships, **Then** the envelope contains exactly the same 15 fields as before — no additions, no removals, no type changes.
2. **Given** the batch API contract fixtures (Section 7 of `contracts/batch-api-contract.md`), **When** those fixtures are validated after this feature ships, **Then** all fixtures pass without modification.

---

### User Story 4 - SaaS Consumes Routing Keys Without Follow-Up (Priority: P2)

The SaaS team (Mission D) receives a tracker snapshot at `/api/v1/connectors/trackers/snapshots/`. The payload now contains `external_resource_type` and `external_resource_id` alongside the existing `provider` and `workspace` fields. The SaaS can resolve the correct `TeamServiceInstallation` + `ServiceResourceMapping` combination using `(provider, workspace, external_resource_type, external_resource_id)` without needing to query the CLI for additional routing data.

**Why this priority**: This is the downstream consumption story. The CLI emits; the SaaS consumes. The CLI's job is to emit correct data — validating SaaS consumption is out of scope but the payload must be sufficient.

**Independent Test**: Can be tested by inspecting the published payload structure and confirming it contains all fields the SaaS needs for resource resolution.

**Acceptance Scenarios**:

1. **Given** a tracker snapshot payload with `provider`, `workspace`, `external_resource_type`, and `external_resource_id` all populated, **When** the SaaS receives this payload, **Then** the four fields together provide a unique resource routing key.

---

### Edge Cases

- What happens when credentials lack the required resource identifier (`project_key` for Jira, `team_id` for Linear)? Both routing fields are `null`. The publish still succeeds — the SaaS falls back to its current resolution path.
- What happens for an unsupported provider (not Jira or Linear)? Both routing fields are `null`. No error is raised. This is forward-compatible — new providers add their own mapping in the derivation logic.
- What happens when `workspace` is configured but credentials are present with no routing keys? `_load_runtime()` succeeds (it does not validate credential completeness), `sync_publish()` runs, and `_resolve_resource_routing()` returns `(null, null)`. The publish still succeeds with null routing fields.
- What happens if a Jira credential has `project_key = ""` (empty string)? Treated as missing — both routing fields are `null`.

## Requirements

### Functional Requirements

| ID | Status | Requirement |
|----|--------|-------------|
| FR-001 | Draft | `sync_publish()` payload MUST include `external_resource_type` field (string or null) |
| FR-002 | Draft | `sync_publish()` payload MUST include `external_resource_id` field (string or null) |
| FR-003 | Draft | For Jira provider, `external_resource_type` MUST be the canonical wire value `"jira_project"` |
| FR-004 | Draft | For Jira provider, `external_resource_id` MUST be the value of `credentials["project_key"]` |
| FR-005 | Draft | For Linear provider, `external_resource_type` MUST be the canonical wire value `"linear_team"` |
| FR-006 | Draft | For Linear provider, `external_resource_id` MUST be the value of `credentials["team_id"]` |
| FR-007 | Draft | For unsupported providers, both routing fields MUST be `null` |
| FR-008 | Draft | When the required credential key is missing or empty, both routing fields MUST be `null` |
| FR-009 | Draft | The Git event envelope (15 fields) MUST NOT be modified |
| FR-010 | Draft | The batch API contract fixtures MUST continue to pass without modification |
| FR-011 | Draft | The routing field derivation logic MUST be a pure function of `(provider, credentials)` with no network calls |
| FR-012 | Draft | The `sync_publish()` idempotency key MUST include `external_resource_type` and `external_resource_id` so that a routing change after rebind is not discarded as a duplicate |

### Non-Functional Requirements

| ID | Status | Requirement | Threshold |
|----|--------|-------------|-----------|
| NFR-001 | Draft | Adding routing fields MUST NOT increase `sync_publish()` latency | < 1ms additional overhead (pure dictionary lookup) |
| NFR-002 | Draft | The canonical wire values MUST be treated as stable contract strings | Breaking changes require a versioned migration |

### Constraints

| ID | Status | Constraint |
|----|--------|------------|
| C-001 | Draft | `external_resource_type` values `"jira_project"` and `"linear_team"` are locked canonical wire values — not display labels |
| C-002 | Draft | The Git event envelope (`git_branch`, `head_commit_sha`, `repo_slug`) MUST remain unchanged |
| C-003 | Draft | No new cross-repo event-contract work in `spec-kitty-events` |
| C-004 | Draft | SaaS ingestion logic changes are out of scope |
| C-005 | Draft | GitHub/GitLab issue-tracker mode is out of scope |
| C-006 | Draft | Tracker resource discovery library changes are out of scope |

### Key Entities

- **Tracker Snapshot Payload**: The JSON body sent to `/api/v1/connectors/trackers/snapshots/` by `sync_publish()`. Extended with two new top-level fields: `external_resource_type` and `external_resource_id`.
- **Resource Routing Key**: The tuple `(provider, workspace, external_resource_type, external_resource_id)` that uniquely identifies a provider resource for `ServiceResourceMapping` resolution on the SaaS side.
- **Canonical Wire Value**: A stable string identifier (`"jira_project"`, `"linear_team"`) used in the publish contract. Not a display label. Breaking changes require explicit migration.

## Success Criteria

### Measurable Outcomes

- **SC-001**: CLI snapshot publish payloads include `external_resource_type` and `external_resource_id` for all configured Jira and Linear bindings
- **SC-002**: All existing Git event envelope tests pass without modification (zero regressions)
- **SC-003**: All existing batch API contract fixture tests pass without modification
- **SC-004**: New unit tests cover both Jira and Linear derivation, missing credentials, empty strings, and unsupported providers
- **SC-005**: The SaaS team (Mission D) can resolve `ServiceResourceMapping` from the published payload without inventing additional CLI-side fields

## Assumptions

- The credential keys `project_key` (Jira) and `team_id` (Linear) are already present in production credential stores for all active bindings. If not, the graceful `null` fallback handles legacy credentials without breakage.
- The SaaS snapshot ingest endpoint tolerates new top-level fields in the payload without rejecting the request (standard forward-compatible JSON handling).
- No other provider besides Jira and Linear is in scope for this mission. Future providers will add their own `(external_resource_type, credential_key)` mapping.

## Scope Boundaries

### In Scope

- Extending `sync_publish()` payload in `src/specify_cli/tracker/service.py`
- Provider-to-resource-type mapping logic (pure function)
- Unit tests for all derivation paths
- Updating `contracts/batch-api-contract.md` or tracker publish contract docs
- Regression tests confirming Git event envelope is untouched

### Out of Scope

- SaaS ingestion logic for the new fields
- Tracker resource discovery library changes
- GitHub/GitLab issue-tracker mode
- New cross-repo event-contract work in `spec-kitty-events`
- UI changes on the SaaS side

## Dependencies

- **ADR**: [Connector Installation, User Link, and Resource Mapping Separation](../../docs/architecture/adr-connector-auth-binding-separation.md) — defines the Layer 3 `ServiceResourceMapping` model that these routing keys enable
- **Gap Analysis**: [Migrating to Installation-Link-Mapping-Override Model](../../docs/architecture/gap-analysis-connector-installation-model.md) — identifies tracker ingest as a critical migration gap (Section 8)
- **Existing Code**: `src/specify_cli/tracker/service.py` (`sync_publish()` method), `src/specify_cli/tracker/config.py`, `src/specify_cli/tracker/credentials.py`, `src/specify_cli/tracker/factory.py`
- **Contracts**: `contracts/batch-api-contract.md` (event envelope), `docs/reference/event-envelope.md`
