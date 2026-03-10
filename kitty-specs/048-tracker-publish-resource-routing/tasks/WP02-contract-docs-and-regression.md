---
work_package_id: WP02
title: Contract Documentation and Regression Validation
lane: "doing"
dependencies: [WP01]
base_branch: 048-tracker-publish-resource-routing-WP01
base_commit: 401b0ba0d7da501680053933014d4cef89fcafab
created_at: '2026-03-10T10:16:58.089572+00:00'
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 2 - Documentation and Validation
assignee: ''
agent: "claude-opus"
shell_pid: "44035"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-10T09:49:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs: [FR-009, FR-010]
---

# Work Package Prompt: WP02 – Contract Documentation and Regression Validation

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- `contracts/batch-api-contract.md` documents the tracker snapshot publish payload extension (new Section or Appendix).
- All existing event envelope tests pass unchanged (`tests/contract/test_handoff_fixtures.py`).
- All existing tracker tests pass unchanged (`tests/specify_cli/tracker/test_credentials.py`, `tests/specify_cli/tracker/test_store.py`).
- `docs/reference/event-envelope.md` confirmed unmodified (the Git event envelope is untouched by this feature).

**Implementation command** (depends on WP01):
```bash
spec-kitty implement WP02 --base WP01
```

## Context & Constraints

- **Spec**: `kitty-specs/048-tracker-publish-resource-routing/spec.md` — FR-009, FR-010 require regression confirmation
- **Plan**: `kitty-specs/048-tracker-publish-resource-routing/plan.md`
- **Feature contract**: `kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md` — detailed payload schema
- **Existing contract**: `contracts/batch-api-contract.md` — the repo-root contract document covering the batch event API

**Constraints**:
- Do NOT modify `docs/reference/event-envelope.md` — this feature does not touch the Git event envelope.
- Do NOT modify any existing test fixtures — they must pass as-is.
- The tracker snapshot publish endpoint (`/api/v1/connectors/trackers/snapshots/`) is a separate endpoint from the batch event API (`/api/v1/events/batch/`). Keep the documentation clear about which endpoint each contract covers.

## Subtasks & Detailed Guidance

### Subtask T006 – Update contracts/batch-api-contract.md

**Purpose**: Add documentation about the tracker snapshot publish payload to the repo-root contract document so the SaaS team has a single reference for all CLI-to-SaaS contracts.

**Steps**:
1. Open `contracts/batch-api-contract.md`.
2. Add a new section (e.g., "Section 8: Tracker Snapshot Publish Payload" or "Appendix C") that:
   - States the endpoint: `POST {server_url}/api/v1/connectors/trackers/snapshots/`
   - Lists the new fields: `external_resource_type` (string|null) and `external_resource_id` (string|null)
   - Documents the canonical wire values: `"jira_project"`, `"linear_team"`
   - Documents null semantics (both atomically null when routing unavailable)
   - References the detailed contract: `kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md`
   - Includes one example payload (Jira with routing fields populated)
3. Do NOT modify existing sections 1-7 (authentication, event envelope, batch format, event types, lanes, errors, fixtures).

**Example addition**:
```markdown
## 8. Tracker Snapshot Publish Payload (Feature 048)

The CLI publishes tracker snapshots to a separate endpoint from the batch event API:

```
POST {server_url}/api/v1/connectors/trackers/snapshots/
Authorization: Bearer <jwt_access_token>
Content-Type: application/json
Idempotency-Key: <sha256-hash>
```

### 8.1 New Routing Fields (2.1.0+)

| Field | Type | Description |
|-------|------|-------------|
| `external_resource_type` | `string \| null` | Canonical wire value: `"jira_project"` or `"linear_team"` |
| `external_resource_id` | `string \| null` | Provider resource identifier (Jira project key or Linear team ID) |

Both fields are atomically null when routing is unavailable (unsupported provider or missing credentials).

See [tracker-snapshot-publish.md](../kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md) for full payload schema and examples.
```

**Files**: `contracts/batch-api-contract.md`
**Parallel?**: No — should reference WP01's implementation to verify accuracy.

---

### Subtask T007 – Run event envelope regression tests

**Purpose**: Confirm that the Git event envelope (15 fields) is completely untouched by the WP01 changes.

**Steps**:
1. Run: `python -m pytest tests/contract/test_handoff_fixtures.py -v`
2. If the file does not exist, check for alternative fixture test paths:
   - `python -m pytest tests/contract/ -v`
   - `python -m pytest tests/ -k "handoff" -v`
3. All tests must pass without modification.
4. If any test fails, investigate — WP01 should NOT have touched the event envelope. A failure here indicates a bug in WP01.

**Files**: `tests/contract/test_handoff_fixtures.py` (read-only — do not modify)
**Parallel?**: Yes — independent of T006 and T008.

---

### Subtask T008 – Run existing tracker tests

**Purpose**: Confirm that existing tracker subsystem tests (credentials, store) are unaffected.

**Steps**:
1. Run: `python -m pytest tests/specify_cli/tracker/test_credentials.py tests/specify_cli/tracker/test_store.py -v`
2. All tests must pass without modification.
3. Also run the new WP01 tests to confirm they coexist:
   - `python -m pytest tests/specify_cli/tracker/ -v`

**Files**: `tests/specify_cli/tracker/test_credentials.py`, `tests/specify_cli/tracker/test_store.py` (read-only — do not modify)
**Parallel?**: Yes — independent of T006 and T007.

---

### Subtask T009 – Verify event-envelope.md unchanged

**Purpose**: Confirm that `docs/reference/event-envelope.md` does not need any updates — the Git event envelope is completely unaffected by this feature.

**Steps**:
1. Read `docs/reference/event-envelope.md`.
2. Confirm it documents the 15-field envelope (9 core + 3 identity + 3 git correlation).
3. Confirm no references to `external_resource_type` or `external_resource_id` are needed — these fields live in the tracker snapshot payload, not the event envelope.
4. If the document is already correct, no changes needed. Document this confirmation in the activity log.

**Files**: `docs/reference/event-envelope.md` (read-only — do not modify)
**Parallel?**: Yes — independent of all other subtasks.

## Test Strategy

This WP is primarily a validation WP. The "tests" are the regression runs themselves:

```bash
# Event envelope regression
python -m pytest tests/contract/test_handoff_fixtures.py -v

# Tracker subsystem regression
python -m pytest tests/specify_cli/tracker/test_credentials.py tests/specify_cli/tracker/test_store.py -v

# Full tracker test suite (includes WP01's new tests)
python -m pytest tests/specify_cli/tracker/ -v
```

All must pass with zero failures, zero modifications to existing test files.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Contract fixture tests don't exist yet | Low | Cannot validate regression | Check for alternative test paths; document gap if none found |
| Existing tracker tests are flaky | Low | False regression signal | Re-run 2-3 times to confirm; check for known flaky tests in CI |
| batch-api-contract.md has merge conflicts | Low | Cannot update cleanly | Resolve conflicts favoring latest 2.x content |

## Review Guidance

- Verify `contracts/batch-api-contract.md` new section does NOT modify sections 1-7.
- Verify the new section correctly references the tracker snapshot endpoint (not the batch event endpoint).
- Verify all regression test runs passed (check activity log for test output confirmation).
- Verify `docs/reference/event-envelope.md` was NOT modified.

## Activity Log

- 2026-03-10T09:49:14Z – system – lane=planned – Prompt created.
- 2026-03-10T10:16:58Z – claude-opus – shell_pid=43426 – lane=doing – Assigned agent via workflow command
- 2026-03-10T10:18:43Z – claude-opus – shell_pid=43426 – lane=for_review – Ready for review: Section 8 added to batch-api-contract.md with resource routing fields. All regression tests pass: 32/32 event envelope fixtures, 22/22 tracker tests. event-envelope.md confirmed unchanged.
- 2026-03-10T10:19:12Z – claude-opus – shell_pid=44035 – lane=doing – Started review via workflow command
