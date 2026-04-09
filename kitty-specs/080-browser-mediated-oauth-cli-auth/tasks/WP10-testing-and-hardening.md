---
work_package_id: WP10
title: Testing & Hardening - Concurrency, Integration, Error Recovery
dependencies:
- WP05
- WP06
- WP07
- WP08
- WP09
requirement_refs:
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Work in execution worktree; merge to main via finalized lanes
subtasks:
- T074
- T075
- T076
- T077
- T078
- T079
- T080
history: []
authoritative_surface: tests/auth/
execution_mode: code_change
owned_files:
- tests/auth/integration/**.py
- tests/auth/concurrency/**.py
- tests/auth/stress/**.py
status: pending
tags: []
---

# WP10: Testing & Hardening

**Objective**: Comprehensive testing of all features under concurrent load, error scenarios, and edge cases. Ensures robustness before staging validation.

**Context**: Final QA before WP11 (cutover). Depends on all previous WPs.

**Acceptance Criteria**:
- [ ] Full end-to-end integration tests pass
- [ ] 10+ concurrent token refreshes = 1 /oauth/token call (single-flight)
- [ ] Concurrent 401s handled correctly
- [ ] File lock coordination under concurrent CLI instances
- [ ] Error recovery (network timeout, 500, 429) works
- [ ] All tests pass (100% coverage)

---

## Subtask Guidance

### T074-T080: Integration & Stress Tests

**Integration Tests** (`tests/auth/integration/`):
- [ ] Browser login → API call → logout (full journey)
- [ ] Headless login → background sync task → auto-refresh
- [ ] WebSocket pre-connect → connect → receive messages

**Concurrency Tests** (`tests/auth/concurrency/`):
- [ ] 10+ concurrent token refreshes (verify single-flight)
- [ ] Concurrent 401s on same token (verify 1 refresh)
- [ ] Concurrent WebSocket provisioning (independent tokens)

**Stress Tests** (`tests/auth/stress/`):
- [ ] File storage under concurrent access (file lock coordination)
- [ ] Network timeout recovery (retry with backoff)
- [ ] 500 server error handling (retry)
- [ ] 429 rate limit handling (respect Retry-After)

**Files**: `tests/auth/integration/`, `tests/auth/concurrency/`, `tests/auth/stress/` (~300 lines total)

---

## Definition of Done

- [ ] All integration tests pass
- [ ] Concurrency tests verify single-flight refresh
- [ ] File lock coordination works under load
- [ ] Error recovery mechanisms tested
- [ ] Performance acceptable (token provisioning <2s)

