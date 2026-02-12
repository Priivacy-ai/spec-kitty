# Implementation Plan: CLI 2.x Readiness Sprint

**Branch**: `2.x` (delivery branch) | **Date**: 2026-02-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/039-cli-2x-readiness/spec.md`

## Summary

Close all CLI-side readiness gaps for spec-kitty 2.x by fixing the planning workflow blocker, hardening the authenticated sync path with actionable diagnostics, converging global runtime resolution, testing the 7-to-4 lane collapse mapping, and producing a SaaS handoff contract document. All work targets the 2.x branch (588 commits diverged from main). The sync infrastructure (13 modules in `src/specify_cli/sync/`) already exists on 2.x — this sprint is "debug, fix, and harden," not greenfield.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, ruamel.yaml, httpx (sync client), pydantic (event models), spec-kitty-events (vendored)
**Storage**: SQLite (event queue via `sync/queue.py`), TOML (credentials via `~/.spec-kitty/credentials`), filesystem (YAML frontmatter, JSON metadata)
**Testing**: pytest (93+ existing green sync/auth tests on 2.x), typer.testing.CliRunner
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI)
**Project Type**: Single CLI project
**Performance Goals**: CLI operations < 2 seconds; batch sync < 5 seconds for 1000 events
**Constraints**: Offline-capable (queue events when disconnected), JWT auth (username/password -> access+refresh tokens)
**Scale/Scope**: ~2000+ tests total, 13 sync modules, 85+ sync-specific tests passing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | All code targets Python 3.11+ |
| pytest with 90%+ coverage for new code | PASS | Will maintain; 93+ sync tests already pass |
| mypy --strict | PASS | Will maintain strict typing in new/modified code |
| Cross-platform (Linux, macOS, Windows) | PASS | No platform-specific changes planned |
| Git required | PASS | All worktree features depend on Git |
| 2.x branch for SaaS features | PASS | All work targets 2.x per constitution's two-branch strategy |
| spec-kitty-events via Git pinning | PASS | Using vendored copy at `src/specify_cli/spec_kitty_events/` |
| No 1.x compatibility constraints | PASS | 2.x is greenfield per constitution |
| CLI < 2 seconds | WATCH | `sync now` may exceed for large queues — document as expected |

No constitution violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/039-cli-2x-readiness/
├── spec.md               # Feature specification
├── plan.md               # This file
├── meta.json             # Feature metadata
├── research.md           # Phase 0: research findings
├── data-model.md         # Phase 1: entity model
├── quickstart.md         # Phase 1: implementation guide
├── contracts/            # Phase 1: API contracts
│   ├── batch-ingest.md   # SaaS batch endpoint contract
│   └── lane-mapping.md   # 7→4 lane collapse specification
├── checklists/
│   └── requirements.md   # Spec quality checklist
└── tasks.md              # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (2.x branch, repository root)

```
src/specify_cli/
├── sync/                      # Existing sync infrastructure (13 modules)
│   ├── __init__.py
│   ├── auth.py                # JWT auth: login, token refresh, credential storage
│   ├── background.py          # Background sync service with periodic flush
│   ├── batch.py               # Batch HTTP client → POST /api/v1/events/batch/
│   ├── client.py              # HTTP/WS client base
│   ├── clock.py               # Lamport clock persistence bridge
│   ├── config.py              # Sync config (server_url, intervals)
│   ├── emitter.py             # Event emission: status transitions → queue/sync
│   ├── events.py              # Event type definitions
│   ├── git_metadata.py        # Git metadata resolver for event enrichment
│   ├── project_identity.py    # Project UUID/slug resolution
│   ├── queue.py               # SQLite offline event queue
│   └── runtime.py             # SyncRuntime lazy singleton
├── cli/commands/
│   ├── sync.py                # VCS workspace sync CLI (separate from event sync)
│   └── agent/
│       ├── feature.py         # setup-plan command (NameError fix target)
│       └── tasks.py           # move-task, list-tasks, validate-workflow
├── core/
│   └── project_resolver.py    # resolve_template_path (global runtime fix target)
├── events/
│   ├── adapter.py             # spec_kitty_events ↔ CLI bridge
│   └── store.py               # Event storage stub
├── spec_kitty_events/         # Vendored event library (7-lane status model)
│   ├── models.py              # Event envelope (Pydantic)
│   ├── status.py              # Lane enum, StatusTransitionPayload
│   ├── lifecycle.py           # Mission lifecycle events
│   ├── storage.py             # Storage abstractions (ABC)
│   ├── clock.py               # LamportClock
│   └── conflict.py            # Concurrent event detection
└── task_helpers_shared.py     # LANES 4-tuple, ensure_lane()

tests/
├── integration/
│   ├── test_planning_workflow.py   # 5 tests (1 xfail)
│   ├── test_task_workflow.py       # 18 tests
│   └── test_sync_e2e.py           # 3 tests (existing on 2.x)
├── specify_cli/
│   ├── sync/                       # 85+ sync unit tests (existing on 2.x)
│   └── cli/commands/agent/
│       ├── test_planning_workflow.py
│       └── test_task_workflow.py
└── e2e/
    └── test_cli_smoke.py           # NEW: full workflow smoke test
```

**Structure Decision**: Existing 2.x structure. No new directories except `tests/e2e/` for the smoke test and `kitty-specs/039-cli-2x-readiness/contracts/` for handoff docs.

## Work Packages

### Dependency Graph

```
WP01 (setup-plan fix) ──────────────────────────────────┐
WP02 (batch error surfacing) ──┐                         │
WP03 (sync status --check) ───┤                          │
WP04 (sync diagnose) ─────────┤── WP07 (handoff doc) ──── WP09 (E2E smoke)
WP05 (sync status extend) ────┘                          │
WP06 (lane mapping tests) ────────────────────────────────┤
WP08 (global runtime) ────────────────────────────────────┘
```

### WP01: Fix setup-plan NameError on 2.x (P0)

**Owner**: Any agent
**Dependencies**: None
**Effort**: Small (surgical fix)

**What**: Add missing `from specify_cli.mission import get_feature_mission_key` import to `src/specify_cli/cli/commands/agent/feature.py` on the 2.x branch (same fix already applied on main at commit 5332408f).

**Acceptance**:
- `spec-kitty agent feature setup-plan` completes without NameError
- `test_planning_workflow.py::test_setup_plan_in_main` passes
- `test_planning_workflow.py::test_full_planning_workflow_no_worktrees` xfail reason investigated and either fixed or re-documented

**Files changed**:
- `src/specify_cli/cli/commands/agent/feature.py` (add import)

---

### WP02: Fix batch error surfacing and diagnostics (P0)

**Owner**: Any agent
**Dependencies**: None (parallel with WP01)
**Effort**: Medium

**What**: Fix `batch.py` to surface the server's `details` field from 400 responses and per-event `results[]` statuses. Currently `batch.py:135` only reads the top-level `error` field, discarding per-event failure reasons.

**Changes**:
1. Parse per-event results from successful batch responses (HTTP 200 with `results[]`)
2. Parse `details` field from 400 error responses (not just `error`)
3. Group failures by reason category (schema_mismatch, auth_expired, server_error, unknown)
4. Print actionable summary: `Synced: N, Duplicates: N, Failed: N (schema_mismatch: X, auth_expired: Y)`
5. Support `--report <file.json>` flag for large failure sets (JSON dump of per-event details)
6. On partial success, remove synced + duplicate events from queue, retain failures with incremented retry_count

**Acceptance**:
- Existing 85+ sync tests still pass (no regressions)
- New tests: batch response parsing for 200 with mixed results, 400 with details, partial success
- User sees grouped error reasons, not bare count

**Files changed**:
- `src/specify_cli/sync/batch.py` (error parsing, summary formatting)
- `src/specify_cli/sync/queue.py` (selective removal of synced events)
- `tests/specify_cli/sync/test_batch.py` (new test cases)

---

### WP03: Fix sync status --check to use real token (P0)

**Owner**: Any agent
**Dependencies**: None (parallel with WP01, WP02)
**Effort**: Small

**What**: Replace the hardcoded test token in `sync.py:531` (`sync status --check`) with the user's actual auth token from `~/.spec-kitty/credentials`. The current test token probe produces misleading 403 errors that don't reflect real auth state.

**Changes**:
1. Load real access token from credentials store
2. If token is expired, attempt refresh first
3. If no credentials exist, report "Not authenticated — run `spec-kitty auth login`" instead of a misleading 403
4. Probe actual batch endpoint with real token (not a synthetic test path)

**Acceptance**:
- `sync status --check` reports accurate auth state
- No false 403 errors from test tokens
- Clear "not authenticated" message when no credentials stored

**Files changed**:
- `src/specify_cli/cli/commands/sync.py` or `src/specify_cli/sync/` (status check path)
- `tests/specify_cli/sync/test_sync_status.py` (new/updated tests)

---

### WP04: Add sync diagnose command (P1)

**Owner**: Any agent
**Dependencies**: WP02 (uses same error categorization)
**Effort**: Medium

**What**: Add `spec-kitty sync diagnose` that validates queued events locally against the event schema before attempting to send them, enabling self-service debugging.

**Changes**:
1. New CLI command `sync diagnose` under the sync command group
2. Read all pending events from SQLite queue
3. Validate each event against the Pydantic `Event` model from `spec_kitty_events.models`
4. Validate payloads against `StatusTransitionPayload` for WPStatusChanged events
5. Report per-event validation results: valid count, invalid count, specific field errors
6. Optionally validate against `events.schema.json` if available

**Acceptance**:
- `spec-kitty sync diagnose` reports schema mismatches for intentionally malformed events
- Valid events pass without false positives
- Output is actionable (shows which field, expected type, actual value)

**Files changed**:
- `src/specify_cli/sync/diagnose.py` (new module)
- `src/specify_cli/cli/commands/` (register command)
- `tests/specify_cli/sync/test_diagnose.py` (new tests)

---

### WP05: Extend sync status with queue health (P1)

**Owner**: Any agent
**Dependencies**: None (parallel)
**Effort**: Medium

**What**: Extend `spec-kitty sync status` to show queue depth, oldest event age, retry-count distribution, and top failing event types — beyond the current connection/auth-only output.

**Changes**:
1. Query SQLite queue for aggregate stats (COUNT, MIN(created_at), retry_count distribution)
2. Group pending events by `event_type` to show top failing types
3. Show retry-count histogram (e.g., "0 retries: 50, 1-3 retries: 30, 4+ retries: 25")
4. Show oldest event age in human-readable format (e.g., "oldest event: 3 hours ago")
5. Format output with Rich tables/panels

**Acceptance**:
- `sync status` shows queue depth, oldest age, retry distribution, top event types
- Output is clear and actionable
- Existing sync status tests still pass

**Files changed**:
- `src/specify_cli/sync/queue.py` (add aggregate query methods)
- `src/specify_cli/cli/commands/` (extend status output)
- `tests/specify_cli/sync/test_queue.py` (new aggregate query tests)

---

### WP06: Test and document 7→4 lane collapse mapping (P2)

**Owner**: Any agent
**Dependencies**: None (parallel)
**Effort**: Small

**What**: The 7→4 lane mapping exists at `emitter.py:46` but lacks explicit tests and documentation. Add comprehensive tests and produce a specification document.

**Current mapping** (from `emitter.py`):
- PLANNED → planned
- CLAIMED → doing
- IN_PROGRESS → doing
- FOR_REVIEW → for_review
- DONE → done
- BLOCKED → doing
- CANCELED → done

**Changes**:
1. Add parametrized tests covering all 7 input lanes with expected 4-lane outputs
2. Add test for unknown lane value handling (should raise ValueError)
3. Extract mapping to a named constant/function if not already (for documentation and reuse)
4. Write `contracts/lane-mapping.md` with mapping table, rationale, and edge case behavior

**Acceptance**:
- All 7 lanes tested with correct 4-lane output
- Unknown lane input raises clear error
- `contracts/lane-mapping.md` exists with complete mapping specification

**Files changed**:
- `tests/specify_cli/sync/test_lane_mapping.py` (new test file)
- `src/specify_cli/sync/emitter.py` (extract mapping if needed)
- `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md` (new doc)

---

### WP07: SaaS handoff contract document (P0)

**Owner**: Any agent
**Dependencies**: WP02 (error format), WP06 (lane mapping)
**Effort**: Medium

**What**: Produce a contract document that the `spec-kitty-saas` team can use to validate their batch endpoint against CLI payloads, without consulting CLI source code.

**Contents**:
1. Event envelope fields (all fields from `Event` model with types, constraints, examples)
2. Batch request format: `POST /api/v1/events/batch/`, headers (`Authorization: Bearer <token>`, `Content-Type: application/json`, `Content-Encoding: gzip`), body `{"events": [...]}`
3. Batch response format: HTTP 200 with `{"results": [{"event_id": "...", "status": "success|duplicate|rejected", "error": "..."}]}`, HTTP 400 with `{"error": "...", "details": "..."}`
4. Authentication: JWT flow (login endpoint, token refresh endpoint, header format)
5. Lane mapping table (from WP06)
6. Event types and their payload schemas (WPStatusChanged, MissionStarted, etc.)
7. Fixture data: 3-5 complete batch request examples with expected responses
8. Required SaaS changes (from spec.md "Required SaaS Changes/Dependencies" section)

**Acceptance**:
- SaaS team can construct valid batch request from doc alone
- Fixture data validates against CLI-side Pydantic models
- All event types documented with payload schemas

**Files changed**:
- `kitty-specs/039-cli-2x-readiness/contracts/batch-ingest.md` (new)
- `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md` (cross-ref from WP06)

---

### WP08: Converge global runtime resolution on 2.x (P1)

**Owner**: Any agent
**Dependencies**: None (parallel)
**Effort**: Medium

**What**: 2.x has partial `~/.kittify` global runtime bootstrap but still shows legacy project fallback warnings. Make resolution deterministic: global `~/.kittify` is canonical after `spec-kitty migrate`, with clear error (not silent fallback) if migration hasn't run.

**Changes**:
1. Audit current resolution chain in `core/project_resolver.py` on 2.x (already has home resolver logic)
2. Ensure `resolve_template_path()` includes `~/.kittify/` in the chain: project `.kittify/missions/{key}/templates/` → project `.kittify/templates/` → `~/.kittify/missions/{key}/templates/` → `~/.kittify/templates/` → package defaults
3. Eliminate legacy fallback warnings after migration (if `~/.kittify/` exists, no warnings)
4. If `~/.kittify/` doesn't exist and project-level fallback is used, emit a one-time "run `spec-kitty migrate` for global runtime" message (not a warning flood)
5. Ensure `spec-kitty migrate` is idempotent (running twice produces same state)
6. Address credential path split: document whether `~/.spec-kitty/credentials` stays or moves to `~/.kittify/credentials`

**Decision needed (captured, not blocking)**: Keep `~/.spec-kitty/credentials` separate from `~/.kittify/` for now. Credentials are auth-specific; runtime is template-specific. Merging them is a follow-on.

**Acceptance**:
- After `spec-kitty migrate`, zero fallback warnings during normal operation
- Resolution chain includes `~/.kittify/` between project and package defaults
- `spec-kitty migrate` is idempotent
- Credential path decision documented

**Files changed**:
- `src/specify_cli/core/project_resolver.py` (resolution chain)
- `src/specify_cli/cli/commands/migrate.py` (idempotency, global install)
- `tests/specify_cli/core/test_project_resolver.py` (new resolution tests)

---

### WP09: End-to-end CLI smoke test (P0)

**Owner**: Any agent
**Dependencies**: WP01 (setup-plan must work), WP02 (sync must surface errors correctly)
**Effort**: Medium

**What**: Add a new E2E smoke test that exercises the full `create-feature → setup-plan → implement → review` sequence against a temporary repository on the 2.x branch.

**Changes**:
1. Create `tests/e2e/test_cli_smoke.py`
2. Fixture: create temp git repo, initialize spec-kitty, set up `.kittify/`
3. Test sequence:
   a. `spec-kitty agent feature create-feature "smoke-test" --json`
   b. Write a minimal `spec.md` to the feature directory
   c. `spec-kitty agent feature setup-plan --feature <slug> --json`
   d. `spec-kitty agent tasks finalize-tasks --feature <slug> --json` (with pre-written tasks.md)
   e. `spec-kitty implement WP01` (create workspace)
   f. Make a code change in workspace, commit
   g. `spec-kitty agent tasks move-task WP01 --to for_review --feature <slug> --json`
   h. Verify final state: WP01 in for_review lane, all artifacts exist
4. Mark as `pytest.mark.e2e` for optional CI separation

**Acceptance**:
- Full sequence completes without errors
- All intermediate artifacts verified (spec.md, plan.md, tasks/, worktree)
- Test is self-contained (creates and cleans up its own temp repo)
- Passes locally and in CI on 2.x

**Files changed**:
- `tests/e2e/test_cli_smoke.py` (new file)
- `tests/e2e/__init__.py` (new file)
- `pyproject.toml` (add `e2e` pytest marker if needed)

## Test Matrix

| Layer | What | Where | Count |
|-------|------|-------|-------|
| Unit | Batch error parsing, queue aggregates, lane mapping, diagnose validation | `tests/specify_cli/sync/` | ~20 new |
| Unit | Template resolution with `~/.kittify` | `tests/specify_cli/core/` | ~5 new |
| Integration | Planning workflow (existing + fix) | `tests/integration/test_planning_workflow.py` | 5 existing |
| Integration | Task workflow (existing) | `tests/integration/test_task_workflow.py` | 18 existing |
| Integration | Sync E2E (existing) | `tests/integration/test_sync_e2e.py` | 3 existing |
| E2E | Full CLI smoke test | `tests/e2e/test_cli_smoke.py` | 1 new |
| Contract | Fixture data validates against Pydantic models | `tests/contract/test_handoff_fixtures.py` | ~3 new |
| **Baseline** | **Existing sync/auth tests** | **2.x test suite** | **93+ existing** |
| **Target** | **Zero regressions + ~30 new tests** | | **~123+ total sync-related** |

## Sequencing and Parallelization

**Wave 1** (independent, can run in parallel):
- WP01: Fix setup-plan NameError
- WP02: Fix batch error surfacing
- WP03: Fix sync status --check
- WP05: Extend sync status queue health
- WP06: Lane mapping tests + docs
- WP08: Global runtime convergence

**Wave 2** (depends on Wave 1 outputs):
- WP04: Sync diagnose command (depends on WP02 error categorization)
- WP07: SaaS handoff contract doc (depends on WP02 error format + WP06 lane mapping)

**Wave 3** (integration):
- WP09: E2E smoke test (depends on WP01 + WP02)

## Rollout / Backward Compatibility

**For 2.x users (pre-release alpha)**:
- All changes ship as part of 2.0.0a4+ on the 2.x branch
- No backward compat concerns within 2.x (pre-release, per constitution)
- `spec-kitty migrate` is the migration path from 1.x project state

**For main branch users**:
- No changes to main in this sprint
- Main remains offline-only, sync-free
- Post-stabilization decision: promote 2.x to mainline or keep split

**Credential path**:
- `~/.spec-kitty/credentials` stays for now (auth-specific)
- `~/.kittify/` is for runtime (templates, missions)
- Future consolidation is a follow-on decision

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 2.x divergence makes fixes harder than expected | Schedule slip | Medium | Each WP is scoped to specific files; use `git show 2.x:<file>` to pre-read before branching |
| Batch ingest failures are server-side, not CLI-side | WP02 incomplete | Medium | WP07 handoff doc captures required SaaS changes; CLI-side diagnostics still valuable even if server needs fixes |
| `~/.kittify` migration breaks existing 2.x alpha users | User disruption | Low | Make `spec-kitty migrate` idempotent; test with existing 2.x project state |
| E2E smoke test is flaky in CI | False failures | Medium | Use `pytest.mark.e2e` marker for optional separation; ensure test cleanup is robust |
| Lane mapping has edge cases not covered by current emitter | Sync data corruption | Low | WP06 adds parametrized tests for all 7 lanes + unknown input; explicitly test BLOCKED and CANCELED |
