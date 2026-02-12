---
work_package_id: WP07
title: SaaS handoff contract document
lane: planned
dependencies:
- WP02
subtasks:
- T029
- T030
- T031
- T032
- T033
phase: Wave 2 - Dependent
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-12T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – SaaS handoff contract document

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP07 --base WP02
```

Depends on WP02 (error format). Use WP02 as base; pull in lane mapping notes from the already-shipped 2.x `status/emit.py` mapping.

---

## Objectives & Success Criteria

- Handoff contract document enables the SaaS team to validate their batch endpoint against CLI payloads without consulting CLI source code
- Fixture data (3-5 complete batch requests/responses) validates against CLI-side Pydantic `Event` model
- All event types documented with payload schemas
- Lane mapping table included and verified against implementation
- Contract test proves fixtures are valid

## Context & Constraints

- **Delivery branch**: 2.x
- **Existing docs**: `contracts/batch-ingest.md` and `contracts/lane-mapping.md` were created during Phase 1 planning as initial drafts. This WP extends them with validated fixtures and cross-references current 2.x implementation.
- **Event types to document**: WPStatusChanged, WPCreated, WPAssigned, FeatureCreated, FeatureCompleted, HistoryAdded, ErrorLogged, DependencyResolved
- **Pydantic models/rules**: `src/specify_cli/spec_kitty_events/models.py` (Event envelope), `src/specify_cli/sync/emitter.py` (`_PAYLOAD_RULES` for payload validation)
- **Reference**: `spec.md` (User Story 6, FR-014), `plan.md` (WP07), `data-model.md`

## Subtasks & Detailed Guidance

### Subtask T029 – Document complete event envelope fields

- **Purpose**: Provide the SaaS team with an authoritative field reference for the event envelope.
- **Steps**:
  1. Read the Pydantic `Event` model in `src/specify_cli/spec_kitty_events/models.py` on 2.x
  2. For each field, document: name, type, required/optional, constraints, example value
  3. Update or extend `contracts/batch-ingest.md` with the complete field reference table
  4. Verify the table matches the actual model — no fields missing, no extra fields
  5. Include ULID format specification for `event_id` and `correlation_id` (26 chars, Crockford Base32)
  6. Include UUID v4 format for `project_uuid`
- **Files**: `kitty-specs/039-cli-2x-readiness/contracts/batch-ingest.md` (extend)
- **Parallel?**: No — foundation for T030-T032
- **Notes**: The Phase 1 draft already has a field reference table. Verify it against the actual 2.x model and correct any discrepancies.

### Subtask T030 – Document batch request/response format

- **Purpose**: Enable the SaaS team to implement the batch endpoint with exact request/response structures.
- **Steps**:
  1. Document the request format:
     - URL: `POST /api/v1/events/batch/`
     - Headers: `Authorization: Bearer <token>`, `Content-Type: application/json`, `Content-Encoding: gzip`
     - Body: `{"events": [<Event>, <Event>, ...]}`
     - Batch size: up to 1000 events
     - Ordering: FIFO (timestamp ASC, id ASC)
  2. Document response formats:
     - HTTP 200 (success): `{"results": [{"event_id": "...", "status": "success|duplicate|rejected", "error": "..."}]}`
     - HTTP 400 (validation): `{"error": "...", "details": "..."}`
     - HTTP 401 (auth): `{"error": "Token expired or invalid"}`
     - HTTP 403 (permissions): `{"error": "Insufficient permissions..."}`
  3. Document per-event status values: `success`, `duplicate`, `rejected`
  4. Include error categorization from WP02 (schema_mismatch, auth_expired, server_error)
- **Files**: `kitty-specs/039-cli-2x-readiness/contracts/batch-ingest.md` (extend)
- **Parallel?**: Yes — can proceed alongside T031
- **Notes**: The Phase 1 draft already covers most of this. Verify against WP02's implementation and add error categorization.

### Subtask T031 – Document authentication flow

- **Purpose**: Enable the SaaS team to understand the complete auth flow the CLI uses.
- **Steps**:
  1. Document the full JWT flow:
     - Login: `POST /api/v1/token/` with `{"username": "...", "password": "..."}`
     - Response: `{"access": "<jwt>", "refresh": "<jwt>"}`
     - Refresh: `POST /api/v1/token/refresh/` with `{"refresh": "<jwt>"}`
     - Response: `{"access": "<new_jwt>"}`
  2. Document credential storage: `~/.spec-kitty/credentials` (TOML, chmod 600)
  3. Document automatic token refresh behavior:
     - CLI checks access token expiry before each request
     - If expired, refreshes using stored refresh token
     - If refresh fails, prompts user to re-authenticate
  4. Document the `Authorization: Bearer <access_token>` header format
- **Files**: `kitty-specs/039-cli-2x-readiness/contracts/batch-ingest.md` (extend)
- **Parallel?**: Yes — can proceed alongside T030

### Subtask T032 – Create fixture request/response examples

- **Purpose**: Provide concrete, copy-pasteable examples the SaaS team can use for integration testing.
- **Steps**:
  1. Create 5 fixture examples:
     - **Fixture 1**: Single WPStatusChanged event (happy path) → success response
     - **Fixture 2**: Batch of 3 events (WPStatusChanged, WPCreated, FeatureCreated) → mixed success
     - **Fixture 3**: Duplicate event (same event_id sent twice) → duplicate response
     - **Fixture 4**: Malformed event (missing required field) → rejected response
     - **Fixture 5**: 400 error response with details field
  2. For each fixture, include:
     - Complete request body (JSON, uncompressed for readability)
     - Expected response body
     - Which fields to pay attention to
  3. Use realistic values:
     - Valid ULIDs for event_id/correlation_id
     - Valid UUID for project_uuid
     - Realistic timestamps
     - 4-lane sync values (not 7-lane) in WPStatusChanged payloads
  4. Add fixtures to `contracts/batch-ingest.md` in a "Fixture Data" section
- **Files**: `kitty-specs/039-cli-2x-readiness/contracts/batch-ingest.md` (extend)
- **Parallel?**: No — depends on T029/T030 for field definitions
- **Notes**: Fixtures must use collapsed 4-lane values (e.g., "doing" not "IN_PROGRESS") in sync payloads.

### Subtask T033 – Write contract test validating fixtures

- **Purpose**: Prove that the fixture data is valid according to the CLI's Pydantic models.
- **Steps**:
  1. Create `tests/contract/test_handoff_fixtures.py`:
     ```python
     import pytest
     import json
     from specify_cli.spec_kitty_events.models import Event

     # Fixture data matching the examples in batch-ingest.md
     FIXTURE_EVENTS = [
         # Fixture 1: Single WPStatusChanged
         {
             "event_id": "01HXYZ1234567890ABCDEFGH",
             "event_type": "WPStatusChanged",
             "aggregate_id": "039-cli-2x-readiness/WP01",
             # ... all fields
         },
         # ... more fixtures
     ]

     @pytest.mark.parametrize("event_data", FIXTURE_EVENTS, ids=lambda e: e.get("event_id", "unknown"))
     def test_fixture_validates_against_event_model(event_data):
         """Fixture data from handoff doc validates against Pydantic Event model."""
         event = Event(**event_data)
         assert event.event_id == event_data["event_id"]

     def test_all_event_types_covered():
         """Fixtures cover all documented event types."""
         types = {e["event_type"] for e in FIXTURE_EVENTS}
         expected = {"WPStatusChanged", "WPCreated", "WPAssigned", "FeatureCreated", "FeatureCompleted", "HistoryAdded", "ErrorLogged", "DependencyResolved"}
         assert types == expected, f"Missing types: {expected - types}"
     ```
  2. Create `tests/contract/__init__.py`
  3. Run: `python -m pytest tests/contract/test_handoff_fixtures.py -v`
- **Files**: `tests/contract/test_handoff_fixtures.py` (new), `tests/contract/__init__.py` (new)
- **Parallel?**: No — depends on T032 fixture data

## Test Strategy

- **New tests**: ~3-5 parametrized contract tests
- **Run command**: `python -m pytest tests/contract/test_handoff_fixtures.py -v`
- **Purpose**: Guarantee that fixture data in the handoff doc is actually valid

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Event model on 2.x has different fields than documented | Read actual model first; update doc to match |
| Fixture data becomes stale as models evolve | Contract tests catch staleness automatically |
| SaaS team needs different format | Keep fixtures as plain JSON (universally parseable) |

## Review Guidance

- Verify all emitted event types have payload schemas documented
- Verify fixture data passes the contract test
- Verify lane mapping table references `_SYNC_LANE_MAP` in `src/specify_cli/status/emit.py`
- Check that the SaaS team can construct a valid batch request using only the contract doc
- Run `python -m pytest tests/contract/ -v` — all green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
