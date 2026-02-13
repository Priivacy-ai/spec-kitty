# Work Packages: Identity-Aware CLI Event Sync

**Inputs**: Design documents from `/kitty-specs/032-identity-aware-cli-event-sync/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, contracts/
**Target Branch**: 2.x

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**MVP Scope (Minimum Deliverable)**: WP01 + WP02 + WP04 (identity in events + auto-start runtime).
**Post-MVP / Nice-to-have**: WP03 (team slug), WP05 (duplicate emissions), WP06 (integration tests).

---

## Work Package WP01: ProjectIdentity Module (Priority: P0, MVP) 🎯 Foundation

**Goal**: Create the ProjectIdentity dataclass with generation, atomic persistence, and graceful backfill.
**Independent Test**: `spec-kitty init` creates config.yaml with valid `project_uuid`, `project_slug`, and `node_id`.
**Prompt**: `tasks/WP01-project-identity-module.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T001 Create ProjectIdentity dataclass in `sync/project_identity.py`
- [ ] T002 Implement identity generation helpers (uuid4, slug from dir/remote, node_id)
- [ ] T003 Implement atomic config.yaml persistence (temp file + rename)
- [ ] T004 Implement graceful backfill via ensure_identity()
- [ ] T005 Add read-only fallback (in-memory identity with warning)
- [ ] T006 Write unit tests in `tests/sync/test_project_identity.py`

### Implementation Notes
1. Use `uuid.uuid4()` for `project_uuid`; use `sync.clock.generate_node_id()` for stable `node_id`
2. Derive project_slug from git remote origin URL (if available) or directory name
3. Atomic writes: write to `.kittify/config.yaml.tmp`, then `os.replace()` to final path
4. Config schema: add `project:` section with `uuid`, `slug`, `node_id` keys

### Parallel Opportunities
- T001-T002 can be developed together (dataclass + helpers)
- T006 tests can be written in parallel once API is designed

### Dependencies
- None (foundation package)

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Config corruption on write failure | Atomic write pattern (temp + rename) |
| Race condition with concurrent processes | First-write-wins; subsequent reads use persisted value |
| Read-only filesystem | Fallback to in-memory identity with warning |

---

## Work Package WP02: Emitter Identity Injection (Priority: P0, MVP)

**Goal**: Inject `project_uuid` and `project_slug` into every event envelope in `EventEmitter._emit()`.
**Independent Test**: Emit an event via `emitter.emit_wp_status_changed()` and verify event dict contains `project_uuid`.
**Prompt**: `tasks/WP02-emitter-identity-injection.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [ ] T007 Import ProjectIdentity into `sync/emitter.py`
- [ ] T008 Add identity injection in `EventEmitter._emit()`
- [ ] T009 Add validation: warn and queue-only if identity missing
- [ ] T010 Update `get_emitter()` to call `ensure_identity()` on first access
- [ ] T011 Update `tests/sync/test_event_emission.py` with identity verification

### Implementation Notes
1. Call `get_project_identity()` at start of `_emit()` (not in each emit_* method)
2. Add `project_uuid` as string, `project_slug` as optional string
3. Validation: if `project_uuid` is None, log warning and skip WebSocket send
4. Identity resolution happens once per emitter lifetime (cached in instance)

### Parallel Opportunities
- T011 tests can be written once API is designed

### Dependencies
- Depends on **WP01** (ProjectIdentity module must exist)

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Performance overhead | Cache identity in emitter; resolve once per lifetime |
| Circular import | Lazy import ProjectIdentity in emitter module |

---

## Work Package WP03: AuthClient Team Slug (Priority: P2, Post-MVP)

**Goal**: Add `get_team_slug()` method to AuthClient and store team_slug on login.
**Independent Test**: After `spec-kitty auth login`, `AuthClient().get_team_slug()` returns the team slug.
**Prompt**: `tasks/WP03-authclient-team-slug.md`
**Estimated Size**: ~250 lines

### Included Subtasks
- [ ] T012 Add `get_team_slug()` method to AuthClient
- [ ] T013 Store team_slug in credentials during login flow
- [ ] T014 Handle unauthenticated case (return "local")
- [ ] T015 Write tests for get_team_slug in `tests/sync/test_auth.py`

### Implementation Notes
1. Team slug comes from SaaS during OAuth/login flow
2. Store in same credentials file as access_token
3. If not authenticated or team_slug missing, return "local" (default)
4. EventEmitter already calls `_get_team_slug()` which expects this method

### Parallel Opportunities
- **Can run in parallel with WP02** (different files, no conflicts)

### Dependencies
- None (can start after WP01, but parallel with WP02)

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| SaaS doesn't provide team_slug | Gracefully default to "local" |
| Credentials file format change | Use versioned schema, migrate if needed |

---

## Work Package WP04: SyncRuntime Lazy Singleton (Priority: P0, MVP)

**Goal**: Create SyncRuntime with lazy startup on first `get_emitter()` call.
**Independent Test**: Call `get_emitter()` twice; verify BackgroundSyncService starts only once.
**Prompt**: `tasks/WP04-sync-runtime-lazy-singleton.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T016 Create SyncRuntime dataclass in `sync/runtime.py`
- [ ] T017 Implement lazy singleton `get_runtime()` function
- [ ] T018 Start BackgroundSyncService unconditionally in `SyncRuntime.start()`
- [ ] T019 Connect WebSocketClient only if authenticated
- [ ] T020 Add atexit handler for graceful shutdown
- [ ] T021 Write tests in `tests/sync/test_runtime.py`

### Implementation Notes
1. Module-level `_runtime: SyncRuntime | None = None`
2. `get_runtime()` creates and starts on first call (idempotent)
3. Check `sync.auto_start` in `.kittify/config.yaml`; default True if missing/invalid
4. Use `atexit.register()` to call `runtime.stop()` on process exit
5. Wire into `get_emitter()`: call `get_runtime()`, create emitter, then `runtime.attach_emitter(emitter)`

### Parallel Opportunities
- T021 tests can be developed alongside implementation

### Dependencies
- Depends on **WP02** (emitter must call runtime on get_emitter)

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Runtime not stopping cleanly | atexit handler + explicit stop() API |
| Startup latency | Keep startup async-light; defer WebSocket connect |

---

## Work Package WP05: Fix Duplicate Emissions (Priority: P2, Post-MVP)

**Goal**: Remove duplicate WPStatusChanged events from `implement.py` and `accept.py`.
**Independent Test**: Run `spec-kitty implement WP01`; verify exactly ONE WPStatusChanged event emitted.
**Prompt**: `tasks/WP05-fix-duplicate-emissions.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [ ] T022 Audit implement.py on 2.x branch for emission points
- [ ] T023 Consolidate to single emission in implement.py
- [ ] T024 Audit accept.py on 2.x branch for emission points
- [ ] T025 Consolidate to single emission in accept.py
- [ ] T026 Add test verifying single emission per command

### Implementation Notes
1. **Work on 2.x branch** - these files have event emissions that main doesn't have
2. Find all `emit_wp_status_changed()` calls in each file
3. Keep the most appropriate one (usually end of successful flow)
4. Remove or guard duplicates (some may be in error paths)
5. Test by mocking emitter and counting calls

### Parallel Opportunities
- T022-T023 (implement.py) and T024-T025 (accept.py) can run in parallel

### Dependencies
- Depends on **WP04** (runtime must be working for proper testing)

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Removing wrong emission | Audit carefully; keep emission at success point |
| Breaking error reporting | Ensure error paths still emit ErrorLogged if needed |

---

## Work Package WP06: Integration Tests (Priority: P2, Post-MVP)

**Goal**: End-to-end tests validating the full identity-aware sync flow.
**Independent Test**: Full test suite passes with identity in all events.
**Prompt**: `tasks/WP06-integration-tests.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T027 Create `tests/integration/test_sync_e2e.py` with fixtures
- [ ] T028 Test: init -> implement -> event contains project_uuid
- [ ] T029 Test: unauthenticated graceful degradation (queue only)
- [ ] T030 Test: config backfill on existing project without identity
- [ ] T031 Test: read-only repo fallback (in-memory identity)
- [ ] T032 Test: single emission per command (no duplicates)

### Implementation Notes
1. Use pytest fixtures for temporary repos and config files
2. Mock WebSocket for isolation; verify queue contents
3. Test both fresh init and migration (existing config without identity)
4. For read-only test, use `os.chmod()` to make config.yaml read-only

### Parallel Opportunities
- Tests are independent; can split across multiple test files if needed

### Dependencies
- Depends on **WP01, WP02, WP04, WP05** (all modules must be working)

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Flaky tests from timing | Use proper async waits; avoid sleeps |
| Test isolation issues | Each test gets fresh temp directory |

---

## Dependency & Execution Summary

```
WP01: ProjectIdentity (foundation)
  ↓
WP02: Emitter injection ─┬─ WP03: AuthClient team_slug (parallel)
                         ↓
WP04: SyncRuntime lazy singleton
  ↓
WP05: Fix duplicate emissions
  ↓
WP06: Integration tests
```

**Execution Order**:
1. WP01 (foundation, must complete first)
2. WP02 + WP03 (parallel wave)
3. WP04 (depends on WP02)
4. WP05 (depends on WP04)
5. WP06 (depends on all)

**MVP Scope**: WP01 + WP02 + WP04 (identity in events, auto-start runtime)

**Full Scope**: All 6 WPs (includes team_slug, duplicate fixes, integration tests)

---

## Subtask Index (Reference)

| ID | Summary | WP | Priority | Parallel? |
|----|---------|-----|----------|-----------|
| T001 | Create ProjectIdentity dataclass | WP01 | P0 | No |
| T002 | Implement identity generation helpers | WP01 | P0 | No |
| T003 | Implement atomic config persistence | WP01 | P0 | No |
| T004 | Implement graceful backfill | WP01 | P0 | No |
| T005 | Add read-only fallback | WP01 | P0 | No |
| T006 | Write project_identity tests | WP01 | P0 | Yes |
| T007 | Import ProjectIdentity into emitter | WP02 | P0 | No |
| T008 | Add identity injection in _emit() | WP02 | P0 | No |
| T009 | Add validation for missing identity | WP02 | P0 | No |
| T010 | Update get_emitter() for identity | WP02 | P0 | No |
| T011 | Update emission tests with identity | WP02 | P0 | Yes |
| T012 | Add get_team_slug() to AuthClient | WP03 | P1 | Yes |
| T013 | Store team_slug on login | WP03 | P1 | No |
| T014 | Handle unauthenticated case | WP03 | P1 | No |
| T015 | Write get_team_slug tests | WP03 | P1 | Yes |
| T016 | Create SyncRuntime dataclass | WP04 | P1 | No |
| T017 | Implement lazy singleton get_runtime() | WP04 | P1 | No |
| T018 | Start BackgroundSyncService | WP04 | P1 | No |
| T019 | Connect WebSocketClient if auth | WP04 | P1 | No |
| T020 | Add atexit handler | WP04 | P1 | No |
| T021 | Write runtime tests | WP04 | P1 | Yes |
| T022 | Audit implement.py emissions | WP05 | P2 | Yes |
| T023 | Consolidate implement.py emission | WP05 | P2 | No |
| T024 | Audit accept.py emissions | WP05 | P2 | Yes |
| T025 | Consolidate accept.py emission | WP05 | P2 | No |
| T026 | Test single emission per command | WP05 | P2 | Yes |
| T027 | Create e2e test fixtures | WP06 | P2 | No |
| T028 | Test init -> implement flow | WP06 | P2 | Yes |
| T029 | Test unauthenticated degradation | WP06 | P2 | Yes |
| T030 | Test config backfill | WP06 | P2 | Yes |
| T031 | Test read-only fallback | WP06 | P2 | Yes |
| T032 | Test no duplicate emissions | WP06 | P2 | Yes |
