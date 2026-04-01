# Feature Specification: Ticket-First Mission Origin Binding

**Feature**: 061-ticket-first-mission-origin-binding
**Mission**: software-dev
**Status**: Draft
**Created**: 2026-04-01
**Target Branch**: main

## Overview

Spec Kitty has installation/resource mappings and tracker bindings, but no way to start a mission from an existing Jira or Linear ticket. The ticket-first workflow closes this gap by letting a developer or AI agent search for an existing external ticket through SaaS, confirm the right one, create a mission from it, and persist durable origin-ticket provenance in local metadata.

The primary consumer is the `/spec-kitty.specify` slash command and agent workflows. The normative contract is a set of service-layer methods -- no new user-facing CLI subcommands are introduced. Service methods return structured results suitable for direct agent consumption.

## Actors

| Actor | Role |
|-------|------|
| Developer | Works inside a repo with a SaaS-backed tracker binding; confirms ticket selection |
| AI Agent | Executes `/spec-kitty.specify` with a ticket-first intent; orchestrates search, confirmation, and binding |
| SaaS Control Plane | Mediates provider API access, resolves installations and resource mappings (Team B) |
| Tracker Connector | Normalizes Jira/Linear issue data into canonical shapes (Team A) |

## User Scenarios & Testing

### Scenario 1: Agent searches by free text and developer confirms

1. Agent is in the `acme/web` repo, bound to `provider=linear`, `project_slug=acme-web`.
2. Agent calls `search_origin_candidates(repo_root, query_text="Clerk auth")`.
3. Service resolves the tracker binding, delegates to `SaaSTrackerClient.search_issues()`.
4. Service returns a `SearchOriginResult` with two candidates: `WEB-123 Add Clerk auth` and `WEB-127 Clerk middleware cleanup`.
5. Agent presents candidates to the developer for confirmation.
6. Developer confirms `WEB-123`.
7. Agent calls `bind_mission_origin()` to persist provenance in `meta.json` and notify SaaS.
8. A `MissionOriginBound` event is emitted.

### Scenario 2: Agent searches by explicit ticket key

1. Agent calls `search_origin_candidates(repo_root, query_key="IAM-42")`.
2. Key-based search takes precedence; service returns exactly one candidate with `match_type="exact"`.
3. Agent still presents the single candidate for developer confirmation (confirmation is always required).
4. Developer confirms. Origin is bound as in Scenario 1.

### Scenario 3: No matching tickets found

1. Agent searches with a query that matches nothing.
2. Service returns a `SearchOriginResult` with an empty `candidates` list.
3. Agent informs the developer and offers to retry with different terms or proceed without an origin ticket.

### Scenario 4: Missing user link

1. The developer has no linked identity (`UserServiceLink`) for the tracker provider.
2. SaaS returns a user-action-required error.
3. Service raises a hard, user-facing error directing the developer to link their account in the SaaS dashboard.
4. No fallback to installation-scoped search. No silent degradation.

### Scenario 5: Full orchestrated flow via start_mission_from_ticket

1. After confirmation, agent calls `start_mission_from_ticket()`.
2. The method derives a mission slug from the candidate's ticket key and title.
3. Creates the mission via existing `create-feature` machinery.
4. Calls `bind_mission_origin()` to persist provenance locally and on SaaS.
5. Emits `MissionOriginBound` event.
6. Returns a structured result with the feature directory, slug, and origin metadata.
7. The mission is understandable offline -- `meta.json` contains the external issue key, URL, title, and routing context.

### Scenario 6: No tracker binding configured

1. Agent calls `search_origin_candidates()` in a repo without a tracker binding.
2. Service raises a hard error: "No tracker bound. Run `spec-kitty tracker bind` first."
3. No fallback.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The system shall provide a `search_origin_candidates()` service method that accepts a free-text query or explicit ticket key and returns a structured list of candidate external issues | Proposed |
| FR-002 | When `query_key` is provided, it shall take precedence over `query_text` | Proposed |
| FR-003 | Candidate results shall include `external_issue_id`, `external_issue_key`, `title`, `status`, `url`, and `match_type` | Proposed |
| FR-004 | The system shall provide a `bind_mission_origin()` service method that persists an additive `origin_ticket` block in the mission's `meta.json` using the canonical metadata writer (`write_meta`) | Proposed |
| FR-005 | The `origin_ticket` block shall store only stable external identifiers and routing context -- no SaaS database primary keys | Proposed |
| FR-006 | The system shall provide a `start_mission_from_ticket()` orchestration method that combines mission creation, origin binding, and event emission in a single call | Proposed |
| FR-007 | `SaaSTrackerClient` shall expose a `search_issues()` method as the client-level dependency boundary for provider-backed issue search | Proposed |
| FR-008 | `SaaSTrackerClient` shall expose a `bind_mission_origin()` method for notifying the SaaS control plane of the origin binding | Proposed |
| FR-009 | Search results shall be scoped to the Jira project or Linear team resolved by the repo's bound Spec Kitty project | Proposed |
| FR-010 | Search shall use the acting user's linked identity (user-scoped search) | Proposed |
| FR-011 | A developer confirmation step shall always be required before binding, even when search returns exactly one result | Proposed |
| FR-012 | The system shall emit a `MissionOriginBound` event when an origin ticket is successfully bound to a mission | Proposed |
| FR-013 | Service methods shall return structured result objects suitable for direct agent consumption without CLI `--json` wrappers | Proposed |
| FR-014 | A single Jira project or Linear team may serve as the origin scope for many missions without changing the one-to-one resource mapping invariant | Proposed |
| FR-015 | The `origin_ticket` block shall include: `provider`, `resource_type`, `resource_id`, `external_issue_id`, `external_issue_key`, `external_issue_url`, and `title` | Proposed |
| FR-016 | A mission may have at most one origin ticket in v1 (one-to-one binding) | Proposed |
| FR-017 | The canonical metadata writer (`feature_metadata.py`) shall gain a `set_origin_ticket()` mutation helper following existing patterns (`record_acceptance`, `record_merge`, etc.) | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Issue search shall complete within a bounded time under normal network conditions | 10 seconds | Proposed |
| NFR-002 | Service methods shall be importable and callable without triggering side effects (no global state on import) | Zero side effects | Proposed |
| NFR-003 | The `origin_ticket` metadata shall remain human-readable and comprehensible when the repo is disconnected from SaaS | Offline intelligibility | Proposed |
| NFR-004 | The `MissionOriginBound` event shall be queued locally when SaaS is unreachable, following existing offline-queue behavior | Zero event loss | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Only Jira and Linear providers are supported in v1 | Confirmed |
| C-002 | The CLI shall never hold or request provider credentials for Jira or Linear -- all API access flows through SaaS | Confirmed |
| C-003 | The product term is "Tracker Authority Policy"; "doctrine" is legacy code vocabulary only | Confirmed |
| C-004 | The product term is "Mission"; "Feature" is prohibited in canonical product language (code-level identifiers like `feature_dir` and `meta.json` remain as implementation terms) | Confirmed |
| C-005 | No new user-facing CLI subcommands are introduced in this feature -- service-layer methods are the normative API surface | Confirmed |
| C-006 | The SaaS HTTP wire format is owned by Team B; this spec defines only the Python client-level contract | Confirmed |
| C-007 | Candidate/result shape coordination with Team A is required before implementation | Confirmed |
| C-008 | Existing resource mappings remain project-scoped routing records and shall not be modified to carry mission provenance | Confirmed |

## Service-Layer API Contract

The following service methods are the normative dependency boundary for this feature. They are the primary contract that `/spec-kitty.specify` and agent workflows consume.

### search_origin_candidates()

Primary search method. Resolves the tracker binding from repo config and delegates to `SaaSTrackerClient.search_issues()`.

**Signature:**
```
search_origin_candidates(
    repo_root: Path,
    query_text: str | None = None,
    query_key: str | None = None,
    limit: int = 10,
) -> SearchOriginResult
```

**Behavior:**
- Loads tracker config from `.kittify/config.yaml`
- Validates provider is Jira or Linear (hard error otherwise)
- Delegates to `SaaSTrackerClient.search_issues()` with resolved provider and project_slug
- Returns structured `SearchOriginResult`
- `query_key` takes precedence over `query_text` when both are provided
- Raises hard error when no tracker binding exists
- Raises hard error when user has no linked identity for the provider

**Result shape -- `SearchOriginResult`:**

| Field | Type | Description |
|-------|------|-------------|
| `candidates` | `list[OriginCandidate]` | Matching issues, ordered by relevance |
| `provider` | `str` | Resolved provider name (e.g., `"linear"`, `"jira"`) |
| `resource_type` | `str` | Resource type (e.g., `"linear_team"`, `"jira_project"`) |
| `resource_id` | `str` | Resource identifier used for scoping |
| `query_used` | `str` | The query that was actually executed |

**Candidate shape -- `OriginCandidate`:**

| Field | Type | Description |
|-------|------|-------------|
| `external_issue_id` | `str` | Provider-native ID (e.g., Linear issue UUID, Jira issue ID) |
| `external_issue_key` | `str` | Human-readable key (e.g., `"WEB-123"`, `"IAM-42"`) |
| `title` | `str` | Issue title / summary |
| `status` | `str` | Current issue status in the provider |
| `url` | `str` | Deep link to the issue in the provider UI |
| `match_type` | `str` | `"exact"` (key match) or `"text"` (free-text search) -- aligned with upstream tracker/SaaS contract |

### bind_mission_origin()

Persists the origin binding locally (meta.json) and notifies SaaS.

**Signature:**
```
bind_mission_origin(
    feature_dir: Path,
    candidate: OriginCandidate,
    provider: str,
    resource_type: str,
    resource_id: str,
) -> dict
```

**Behavior:**
- Writes additive `origin_ticket` block to `meta.json` via canonical `write_meta()`
- Calls `SaaSTrackerClient.bind_mission_origin()` to create the control-plane record (authoritative write)
- Emits `MissionOriginBound` event via the event emitter (observational telemetry only)
- Returns the updated metadata dict

**Re-bind semantics:**
- **Same origin** (same `external_issue_id`): no-op success -- local write overwrites identically, SaaS returns success without creating a duplicate
- **Different origin** (different `external_issue_id` for an already-bound mission): hard error -- one origin per mission in v1, the caller must unbind first or create a new mission

### start_mission_from_ticket()

Orchestration method combining mission creation + origin binding.

**Signature:**
```
start_mission_from_ticket(
    repo_root: Path,
    candidate: OriginCandidate,
    provider: str,
    resource_type: str,
    resource_id: str,
    mission_key: str = "software-dev",
) -> MissionFromTicketResult
```

**Behavior:**
- Derives mission slug from candidate's `external_issue_key` and `title`
- Creates mission via existing feature-creation machinery
- Calls `bind_mission_origin()` to persist provenance
- Returns structured result

**Result shape -- `MissionFromTicketResult`:**

| Field | Type | Description |
|-------|------|-------------|
| `feature_dir` | `Path` | Path to the created feature directory |
| `feature_slug` | `str` | The assigned feature slug (e.g., `"061-add-clerk-auth"`) |
| `origin_ticket` | `dict` | The persisted `origin_ticket` metadata block |
| `event_emitted` | `bool` | Whether the `MissionOriginBound` event was successfully emitted |

## SaaSTrackerClient Extensions

These methods extend the existing `SaaSTrackerClient` class. They define the Python-level dependency boundary. The HTTP wire format behind them is owned by Team B.

### search_issues()

**Signature:**
```
search_issues(
    provider: str,
    project_slug: str,
    *,
    query_text: str | None = None,
    query_key: str | None = None,
    limit: int = 10,
) -> dict[str, Any]
```

**Expected success semantics:**
- Returns a dict with `candidates` list matching the `OriginCandidate` shape
- Includes `resource_type` and `resource_id` for routing context

**Expected error semantics:**

| HTTP Status | Meaning | CLI Behavior |
|-------------|---------|-------------|
| 401/403 + `user_action_required` | Missing or expired user link | Hard error directing to SaaS dashboard |
| 404 | No mapped resource for this project | Hard error: "No resource mapping found" |
| 422 | Invalid query parameters | Hard error with validation details |
| 429 | Rate limited | Retry with backoff (existing `_request_with_retry` behavior) |

### bind_mission_origin()

**Signature:**
```
bind_mission_origin(
    provider: str,
    project_slug: str,
    *,
    feature_slug: str,
    external_issue_id: str,
    external_issue_key: str,
    external_issue_url: str,
    title: str,
) -> dict[str, Any]
```

**Expected success semantics:**
- Returns confirmation dict with `origin_link_id` and `bound_at` timestamp
- Same-origin re-bind (same `external_issue_id`): returns success with existing `origin_link_id` (no-op, no duplicate)

**Expected error semantics:**

| HTTP Status | Meaning | CLI Behavior |
|-------------|---------|-------------|
| 409 | Different origin already bound for this mission | Hard error (one origin per mission in v1; caller must unbind first or create a new mission) |
| 401/403 | Auth failure | Same handling as `search_issues()` |

## Local Metadata Shape

The `origin_ticket` block persisted in `meta.json`:

```json
{
  "origin_ticket": {
    "provider": "linear",
    "resource_type": "linear_team",
    "resource_id": "team-uuid",
    "external_issue_id": "issue-uuid",
    "external_issue_key": "WEB-123",
    "external_issue_url": "https://linear.app/acme/issue/WEB-123/add-clerk-auth",
    "title": "Add Clerk auth"
  }
}
```

**Invariants:**
- Written via `write_meta()` (canonical atomic writer) through a new `set_origin_ticket()` mutation helper
- Additive -- does not replace or interfere with existing metadata fields
- No SaaS database primary keys stored
- Contains enough context to remain intelligible offline
- A mission may have at most one `origin_ticket` in v1

## Event Emission

A new `MissionOriginBound` event type shall be added to the event emitter system.

**Payload fields:**

| Field | Type | Required |
|-------|------|----------|
| `feature_slug` | `str` | Yes |
| `provider` | `str` | Yes |
| `external_issue_id` | `str` | Yes |
| `external_issue_key` | `str` | Yes |
| `external_issue_url` | `str` | Yes |
| `title` | `str` | Yes |

**Aggregate:** `Feature` (aggregate_id = feature_slug)

**Authority rule:** The `SaaSTrackerClient.bind_mission_origin()` API call is the authoritative write path for creating the SaaS-side `MissionOriginLink`. The `MissionOriginBound` event is **observational telemetry only** -- it does not create or replace the control-plane record. Its purposes are:
- Offline audit trail (queued locally when SaaS is unreachable)
- Downstream analytics and lifecycle egress triggers (Phase 2, out of scope for this feature)
- Enabling SaaS to correlate the binding with other telemetry events

## Assumed Upstream API Dependencies

> **Non-authoritative.** Team B owns the HTTP endpoint and wire format. The CLI depends on SaaS exposing semantics equivalent to the client contract defined above.

- SaaS must expose an issue-search capability accepting provider, project_slug, query_text/query_key, and limit
- SaaS must resolve the correct installation and mapped resource from the project context
- SaaS must scope search results to the acting user's linked identity
- SaaS must expose a bind capability for creating a `MissionOriginLink` from the confirmed issue
- Wire format, URL paths, and HTTP methods are Team B's decision
- Team A owns the candidate/result shape normalization on the tracker-connector side

## Key Entities

| Entity | Description |
|--------|-------------|
| `OriginCandidate` | A candidate external issue from search, containing stable provider identifiers |
| `SearchOriginResult` | Structured result from `search_origin_candidates()` with candidates and routing context |
| `MissionFromTicketResult` | Result of `start_mission_from_ticket()` with feature_dir, slug, and origin metadata |
| `origin_ticket` | Additive metadata block in `meta.json` binding a mission to its originating external issue |
| `MissionOriginBound` | New event type emitted when an origin binding is established |

## Assumptions

1. The repo already has a valid SaaS-backed tracker binding (`.kittify/config.yaml` with `provider` and `project_slug`).
2. The developer has authenticated via `spec-kitty auth login` with a valid access token.
3. The developer has a `UserServiceLink` for the bound provider (required for user-scoped search).
4. The existing feature-creation machinery can be called programmatically from `start_mission_from_ticket()`.
5. The `FeatureMetaOptional` TypedDict in `feature_metadata.py` will be extended to include `origin_ticket`.
6. The event emitter's `VALID_EVENT_TYPES` and `_PAYLOAD_RULES` will be extended with `MissionOriginBound`.

## Success Criteria

1. An agent executing `/spec-kitty.specify` can find and bind an originating Jira or Linear ticket in under 30 seconds (search + confirm + bind).
2. After binding, `meta.json` contains an `origin_ticket` block that a human can read and understand without SaaS access.
3. Multiple missions can originate from issues in the same Jira project or Linear team without modifying resource mappings.
4. A `MissionOriginBound` event is emitted and reaches the offline queue for every successful binding.
5. Missing user-link errors clearly direct the user to the SaaS dashboard with no silent fallback or degraded behavior.
6. All service methods are testable in isolation with mocked `SaaSTrackerClient` responses.
