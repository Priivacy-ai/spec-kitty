---
work_package_id: WP06
title: Integration Testing
dependencies: [WP05]
requirement_refs:
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: feat/implement-review-skill
merge_target_branch: feat/implement-review-skill
branch_strategy: Planning artifacts for this feature were generated on feat/implement-review-skill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/implement-review-skill unless the human explicitly redirects the landing branch.
subtasks: [T031, T032, T033, T034, T035]
history:
- date: '2026-04-01'
  action: created
  by: spec-kitty.tasks
authoritative_surface: tests/sync/tracker/
execution_mode: code_change
owned_files:
- tests/sync/tracker/test_origin_integration.py
---

# WP06: Integration Testing

## Objective

Write end-to-end integration tests that wire all layers (transport, service, metadata, event) together with mocked HTTP at the httpx boundary only. Verify the full search → confirm → bind → create flow, error propagation across layers, SaaS-first write ordering invariant, and offline event queuing.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Implementation command**: `spec-kitty implement WP06 --base WP05`
- **Dependencies**: WP05 (which transitively depends on WP01-04). All must be merged.

## Context

- **Spec scenarios**: `kitty-specs/061-ticket-first-mission-origin-binding/spec.md` — Scenarios 1-6
- **Plan**: `kitty-specs/061-ticket-first-mission-origin-binding/plan.md` — "Write ordering", test strategy
- **WP05 output**: Service functions in `tracker/origin.py`

## Subtasks

### T031: End-to-end test: search → confirm → bind flow

**File**: `tests/sync/tracker/test_origin_integration.py` (new file)

**Purpose**: Test the full happy-path flow that an agent would execute.

**Setup**:
- Create a real `SaaSTrackerClient` with mocked `httpx.Client` (HTTP-layer mock only)
- Create a real `tmp_path` repo with `.kittify/config.yaml` (tracker binding: `provider=linear, project_slug=acme-web`)
- Pre-seed `kitty-specs/` and `meta.json`

**Test flow**:
1. Call `search_origin_candidates(repo_root, query_text="Clerk auth")` → mock HTTP returns candidate list
2. Extract first candidate from result
3. Call `bind_mission_origin(feature_dir, candidate, ...)` → mock HTTP returns success
4. Verify `meta.json` now contains `origin_ticket` block with all 7 required fields
5. Verify event was queued (check offline queue)

**Why integration**: This tests real config loading, real metadata writes, real event emission — only HTTP is mocked.

### T032: End-to-end test: `start_mission_from_ticket` full flow

**Purpose**: Test the orchestration method that combines creation + binding.

**Setup**: Same as T031 but without pre-seeded feature directory (it gets created).

**Test flow**:
1. Mock HTTP for both bind endpoint (success)
2. Mock `create_feature_core()` to return a `FeatureCreationResult` with a tmp feature_dir
3. Call `start_mission_from_ticket(repo_root, candidate, ...)`
4. Verify returned `MissionFromTicketResult` has correct `feature_slug`, `origin_ticket`
5. Verify `meta.json` in the created feature_dir has origin_ticket
6. Verify `event_emitted` is True

### T033: Test error propagation across layers

**Purpose**: Verify that errors from the deepest layer (HTTP) propagate correctly through service → caller.

**Test cases**:
1. **HTTP 401 → SaaSTrackerClientError → OriginBindingError**: Search with expired token → `OriginBindingError` with dashboard message
2. **HTTP 409 → SaaSTrackerClientError → OriginBindingError**: Bind with different origin → `OriginBindingError` with conflict message
3. **HTTP 404 → SaaSTrackerClientError → OriginBindingError**: Search with no mapping → `OriginBindingError`
4. **FeatureCreationError → OriginBindingError**: Invalid slug → `OriginBindingError`

**Verify**: Error messages are user-facing and actionable (not raw HTTP details).

### T034: Test SaaS-first write ordering invariant

**Purpose**: The most critical integration test — verify that local metadata is NEVER written when SaaS bind fails.

**Test flow**:
1. Set up real config, real feature_dir with meta.json
2. Mock HTTP to return 500 (or 409) for the bind endpoint
3. Call `bind_mission_origin(feature_dir, candidate, ...)`
4. Verify `OriginBindingError` raised
5. **Read meta.json and verify NO `origin_ticket` key exists** — this is the invariant
6. Repeat with 401, 403, 422 to verify ordering holds for all error classes

**Why this matters**: A bug in write ordering creates split-brain where local state claims an origin exists but SaaS has no record.

### T035: Test offline event queuing

**Purpose**: Verify `MissionOriginBound` event reaches the offline queue when SaaS WebSocket is not connected.

**Test flow**:
1. Set up emitter with no WebSocket client (offline mode)
2. Call `bind_mission_origin()` (with mocked HTTP success for the bind API)
3. Verify event was queued in `OfflineQueue`
4. Verify event `event_type` is `"MissionOriginBound"`
5. Verify event `payload` contains all 6 required fields

## Definition of Done

- [ ] All 5 integration tests pass
- [ ] SaaS-first write ordering invariant explicitly tested
- [ ] Error propagation tested for all HTTP error classes
- [ ] Offline event queuing verified
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes
- [ ] Combined coverage across WP01-WP06 is 90%+ for new code

## Risks

- **Medium**: Integration tests are complex to set up (multiple real + mocked layers). Keep fixtures focused.
- **Mitigation**: Build composable fixtures — reuse the mocked HTTP pattern from `test_saas_client.py` with real service functions.

## Reviewer Guidance

- **Most critical test**: T034 (write ordering invariant). This test MUST verify meta.json is untouched on SaaS failure.
- Verify T031 uses real config loading, real metadata writes — only HTTP is mocked
- Verify error messages in T033 are user-actionable
- Verify T035 checks the offline queue, not just that the emit call was made
