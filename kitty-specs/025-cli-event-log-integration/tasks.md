# Work Packages: CLI Event Log Integration

**Feature**: 025-cli-event-log-integration
**Target Branch**: 2.x (greenfield, no 1.x compatibility)
**Inputs**: plan.md, spec.md (7 user stories), data-model.md, contracts/, research.md, quickstart.md

**Tests**: Not explicitly requested by spec - implementation will include validation but not separate test files.

**Organization**: This feature breaks down into 8 work packages organized by dependency phases. Foundation work (WP01-WP02) enables all user stories. Core infrastructure (WP03-WP05) implements P1 user stories. Advanced features (WP06-WP08) implement P2/P3 capabilities.

**Sizing**: Work packages range from 4-7 subtasks each (~250-450 lines per prompt). This ensures focused, manageable implementation while enabling parallelization.

---

## ⚠️ CRITICAL: 2.x Branch Creation Required

**BEFORE implementing WP01**, you MUST create the 2.x branch:

```bash
# 1. Ensure you're on latest main
git checkout main
git pull origin main

# 2. Create 2.x branch (NEW parallel development track)
git checkout -b 2.x

# 3. Push to remote
git push origin 2.x

# 4. Verify you're on 2.x
git branch --show-current  # Should output: 2.x
```

**Why this is critical**:
- **2.x is a NEW branch** (not a version tag on main)
- **2.x is greenfield architecture** (events-only, no YAML activity logs)
- **Incompatible with main** (cannot coexist due to fundamental architecture differences)
- **main branch (v0.13.x) becomes 1.x** (maintenance-only, YAML logs remain)

**What NOT to do**:
- ❌ DO NOT implement on `main` branch (would break stable 1.x line)
- ❌ DO NOT modify existing YAML activity log code on main
- ❌ DO NOT add backward compatibility with 1.x (greenfield means fresh start)
- ❌ DO NOT create worktrees from main (must branch from 2.x)

**All work packages (WP01-WP08) implement on the `2.x` branch.**

See spec.md "Branch Strategy" section for full rationale and ADR-12 reference.

---

## Phase 0: Foundation & Dependency Integration (P1)

### Work Package WP01: Git Dependency Setup & Library Integration

**Goal**: Integrate spec-kitty-events library as Git dependency with commit pinning per ADR-11.
**Priority**: P0 (blocks all other work)
**User Story**: US6 - Git Dependency Integration with Commit Pinning
**Independent Test**: Fresh clone, `pip install -e .`, verify spec-kitty-events imports successfully
**Estimated Lines**: ~280 lines
**Prompt**: `tasks/WP01-git-dependency-setup-and-library-integration.md`

### Included Subtasks

- [x] T001 - Add spec-kitty-events Git dependency to pyproject.toml with commit pinning
- [x] T002 - Document SSH deploy key setup for CI/CD in development docs
- [x] T003 - Update GitHub Actions workflow to use SSH deploy key
- [x] T004 - Create import adapter layer for spec-kitty-events library
- [x] T005 - Add graceful error handling for missing library with setup instructions

### Implementation Notes

This work package establishes the foundational dependency on spec-kitty-events library. We'll use Poetry's Git dependency syntax with commit hash pinning (not `rev="main"` to avoid CI flakiness). The adapter layer (T004) provides a clean interface between the library's types and spec-kitty's CLI types.

**Critical**: Must use SSH Git URL (`git+ssh://`) not HTTPS for private repo access in CI.

### Parallel Opportunities

- T002 (documentation) can proceed in parallel with T001 (dependency config)
- T003-T005 must run sequentially after T001 completes

### Dependencies

- None (starting package)

### Risks & Mitigations

- **Risk**: SSH deploy key not configured in CI → Build fails
  - **Mitigation**: T003 includes verification step, T005 provides clear error message with setup instructions
- **Risk**: Library API changes break integration
  - **Mitigation**: Commit pinning ensures deterministic builds, update only when explicitly upgrading

---

## Phase 1: Core Event Infrastructure (P1)

### Work Package WP02: Event Storage Foundation (Entities & File I/O)

**Goal**: Implement core entities (Event, LamportClock, ClockStorage) and JSONL file operations.
**Priority**: P1 (US1 dependency)
**User Story**: US1 - Event Emission on Workflow State Changes (partial)
**Independent Test**: Emit test event, verify JSONL file created with correct structure
**Estimated Lines**: ~420 lines
**Prompt**: `tasks/WP02-event-storage-foundation.md`

### Included Subtasks

- [x] T006 - Create Event dataclass with ULID, Lamport clock, entity metadata
- [x] T007 - Create LamportClock dataclass with tick() and persistence methods
- [x] T008 - Implement ClockStorage for loading/saving clock state to JSON
- [x] T009 - Implement JSONL append with POSIX file locking (atomic writes)
- [x] T010 - Implement daily file rotation logic (YYYY-MM-DD.jsonl)
- [x] T011 - Add clock corruption recovery (rebuild from event log max)
- [x] T012 - Create `.kittify/events/` and `.kittify/errors/` directory initialization

### Implementation Notes

**File Structure**: All new modules go in `src/specify_cli/events/`:
- `types.py` - Event and LamportClock dataclasses (T006, T007)
- `clock_storage.py` - ClockStorage class (T008, T011)
- `file_io.py` - JSONL append with locking (T009, T010)

**Critical Implementation Details**:
- T009: Use `fcntl.flock()` for POSIX file locking (atomic appends)
- T010: Daily rotation checks current date vs filename, creates new file if date changed
- T011: Rebuild clock by reading all JSONL files, taking max(lamport_clock) + 1

### Parallel Opportunities

- T006-T008 (dataclasses) can be implemented in parallel
- T009-T012 must run sequentially (file operations depend on each other)

### Dependencies

- Depends on WP01 (spec-kitty-events library must be available)

### Risks & Mitigations

- **Risk**: File locking not available on Windows (non-WSL)
  - **Mitigation**: T009 includes platform check, falls back to best-effort (development mode only)
- **Risk**: Concurrent writes from multiple processes corrupt JSONL
  - **Mitigation**: File locking ensures atomic appends per ADR decision

---

### Work Package WP03: EventStore & AOP Middleware

**Goal**: Implement EventStore adapter and AOP decorators for transparent event emission.
**Priority**: P1 (US1 core capability)
**User Story**: US1 - Event Emission on Workflow State Changes (complete)
**Independent Test**: Run `move_task` command, verify `WPStatusChanged` event emitted to JSONL
**Estimated Lines**: ~350 lines
**Prompt**: `tasks/WP03-eventstore-and-aop-middleware.md`

### Included Subtasks

- [x] T013 - Create EventStore class wrapping spec-kitty-events library
- [x] T014 - Implement `emit()` method with automatic clock increment and JSONL write
- [x] T015 - Create `@with_event_store` AOP decorator for dependency injection
- [x] T016 - Integrate event emission into `move_task` command (WPStatusChanged)
- [x] T017 - Integrate event emission into `setup-spec` command (SpecCreated)
- [x] T018 - Integrate event emission into `finalize-tasks` command (WPCreated events)

### Implementation Notes

**AOP Pattern**: The `@with_event_store` decorator (T015) provides clean dependency injection:
```python
@with_event_store
def move_task(wp_id: str, lane: str, event_store: EventStore):
    # event_store automatically injected
```

**Event Emission Points**:
- T016: After frontmatter update in `spec-kitty agent tasks move-task`
- T017: After spec.md creation in `spec-kitty agent feature setup-spec`
- T018: After each WP file creation in `spec-kitty agent feature finalize-tasks`

### Parallel Opportunities

- T016-T018 (command integrations) can proceed in parallel after T013-T015 complete

### Dependencies

- Depends on WP02 (Event, LamportClock, file I/O must exist)

### Risks & Mitigations

- **Risk**: Event emission adds >15ms latency (violates performance goal)
  - **Mitigation**: T014 implements synchronous writes (already validated as acceptable)
- **Risk**: Commands fail silently if event emission fails
  - **Mitigation**: T014 raises IOError on write failure, command propagates error to user

---

### Work Package WP04: SQLite Query Index

**Goal**: Implement SQLite index for fast event queries (US3 requirement).
**Priority**: P1 (US3)
**User Story**: US3 - SQLite Query Index for Fast Aggregates
**Independent Test**: Generate 1000 events, query with filter, verify <500ms completion
**Estimated Lines**: ~380 lines
**Prompt**: `tasks/WP04-sqlite-query-index.md`

### Included Subtasks

- [x] T019 - Create EventIndex class with SQLite schema (events table + indices)
- [x] T020 - Implement `update()` method for inline index updates during emit
- [x] T021 - Implement `query()` method with filters (entity_id, event_type, since_clock)
- [x] T022 - Implement `rebuild()` method for corruption recovery
- [x] T023 - Integrate index updates into EventStore.emit() (synchronous for MVP)
- [x] T024 - Add automatic index rebuild on missing/corrupted database

### Implementation Notes

**SQL Schema** (T019):
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    lamport_clock INTEGER NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    date TEXT NOT NULL,
    INDEX idx_entity ON events(entity_id, lamport_clock),
    INDEX idx_type ON events(event_type, lamport_clock)
);
```

**Index Update Strategy**: Synchronous (T023) for MVP. Async background worker deferred to Phase 2.

### Parallel Opportunities

- T019-T022 (EventIndex implementation) can proceed in parallel
- T023-T024 (integration) must run sequentially after EventIndex complete

### Dependencies

- Depends on WP03 (EventStore.emit() must exist to integrate index updates)

### Risks & Mitigations

- **Risk**: SQLite index updates add latency >5ms (total >15ms violates goal)
  - **Mitigation**: Measured and acceptable per planning decision (synchronous writes prioritize reliability)
- **Risk**: Index corruption causes read failures
  - **Mitigation**: T024 auto-rebuilds index from JSONL source of truth

---

### Work Package WP05: Event Reading & State Reconstruction

**Goal**: Implement event reading with Lamport clock ordering and state reconstruction.
**Priority**: P1 (US2)
**User Story**: US2 - Reading Workflow State from Event Log
**Independent Test**: Emit several `WPStatusChanged` events, run `status`, verify kanban board reflects events
**Estimated Lines**: ~320 lines
**Prompt**: `tasks/WP05-event-reading-and-state-reconstruction.md`

### Included Subtasks

- [x] T025 - Implement EventStore.read() with optional filters (delegates to index)
- [x] T026 - Implement event sorting by Lamport clock (causal ordering)
- [x] T027 - Implement graceful degradation (skip invalid JSON lines with warnings)
- [x] T028 - Create state reconstruction logic (replay events to derive current status)
- [x] T029 - Integrate event reading into `spec-kitty status` command
- [x] T030 - Add fallback to direct JSONL reading when index unavailable

### Implementation Notes

**Reading Flow**:
1. T025: EventStore.read() checks if filters provided → use index query, else read all JSONL
2. T026: Sort events by `lamport_clock` field (causal order, not timestamp)
3. T027: Wrap JSON parsing in try/except, log warning, continue on failure
4. T028: Apply events in order to reconstruct WorkPackage status (state-machine pattern)

**Integration** (T029): Modify `spec-kitty status` to call EventStore.read(event_type="WPStatusChanged") instead of reading YAML activity logs.

### Parallel Opportunities

- T025-T028 (reading logic) can proceed in parallel
- T029-T030 (integration) must run sequentially after reading logic complete

### Dependencies

- Depends on WP04 (EventIndex.query() must exist for filtered reads)

### Risks & Mitigations

- **Risk**: Large event logs (10k+ events) cause slow status command
  - **Mitigation**: T030 uses index filtering (only reads relevant events), T026 sorts in memory
- **Risk**: Corrupted JSONL file blocks all reads
  - **Mitigation**: T027 graceful degradation (skip bad lines, warn user)

---

## Phase 2: Advanced Features & Edge Cases (P2/P3)

### Work Package WP06: Conflict Detection & Merge Rules

**Goal**: Implement concurrent operation detection and deterministic conflict resolution.
**Priority**: P2 (US4)
**User Story**: US4 - Conflict Detection for Concurrent Operations
**Independent Test**: Simulate concurrent events (same clock), verify conflict detected and resolved via LWW
**Estimated Lines**: ~290 lines
**Prompt**: `tasks/WP06-conflict-detection-and-merge-rules.md`

### Included Subtasks

- [x] T031 - Implement conflict detection (group events by Lamport clock, find duplicates)
- [x] T032 - Implement Last-Write-Wins merge rule (lexicographic ULID sorting)
- [x] T033 - Integrate conflict detection into state reconstruction (T028 enhancement)
- [x] T034 - Add conflict warning output to `spec-kitty status` command
- [x] T035 - Log conflict resolutions to stderr with explanation

### Implementation Notes

**Conflict Detection Flow** (T031):
```python
events_by_clock = group_by_lamport_clock(events)
for clock, clock_events in events_by_clock.items():
    if len(clock_events) > 1:
        # Conflict detected!
        apply_merge_rule(clock_events)
```

**LWW Rule** (T032): Sort conflicting events by `event_id` (ULIDs are lexicographically sortable), take last event as winner.

### Parallel Opportunities

- T031-T032 (detection & resolution logic) can proceed in parallel
- T033-T035 (integration) must run sequentially after logic complete

### Dependencies

- Depends on WP05 (state reconstruction must exist to enhance with conflict detection)

### Risks & Mitigations

- **Risk**: Conflicts are common in practice (performance hit from detection)
  - **Mitigation**: Conflicts rare in CLI use case (validated by research), detection is lightweight O(n) pass
- **Risk**: LWW rule loses important state changes
  - **Mitigation**: Both events preserved in log (audit trail), warning shown to user

---

### Work Package WP07: Error Logging (Manus Pattern)

**Goal**: Implement error event logging for agent learning and debugging.
**Priority**: P3 (US7)
**User Story**: US7 - Error Logging with Manus Pattern
**Independent Test**: Trigger invalid state transition, verify error logged to `.kittify/errors/YYYY-MM-DD.jsonl`
**Estimated Lines**: ~250 lines
**Prompt**: `tasks/WP07-error-logging-manus-pattern.md`

### Included Subtasks

- [x] T036 - Create ErrorEvent dataclass (error_id ULID, error_type, entity_id, reason, context)
- [x] T037 - Create ErrorStorage class with daily JSONL logging (parallel to EventStore)
- [x] T038 - Create `@with_error_storage` AOP decorator
- [x] T039 - Integrate error logging into validation failures (state transition errors)
- [x] T040 - Add best-effort error handling (don't block operations if error log fails)

### Implementation Notes

**ErrorEvent Structure** (T036):
```python
@dataclass
class ErrorEvent:
    error_id: str
    error_type: str  # "ValidationError", "StateTransitionError", "GateFailure"
    entity_id: str
    attempted_operation: str  # Command that failed
    reason: str  # Human-readable explanation
    timestamp: str
    context: dict  # Debugging metadata
```

**Integration** (T039): Wrap validation logic in try/except, log to ErrorStorage on ValidationError.

### Parallel Opportunities

- T036-T038 (error infrastructure) can proceed in parallel
- T039-T040 (integration) must run sequentially after infrastructure complete

### Dependencies

- Depends on WP03 (AOP pattern established, can reuse for error storage)

### Risks & Mitigations

- **Risk**: Error logging adds latency to failing operations
  - **Mitigation**: T040 implements best-effort (fire-and-forget), doesn't block on error write
- **Risk**: Error logs grow unbounded
  - **Mitigation**: Daily rotation (same as events), users can archive/delete old error logs

---

### Work Package WP08: pyproject.toml Update & CI Configuration

**Goal**: Finalize Git dependency configuration and validate CI/CD pipeline.
**Priority**: P1 (completes US6)
**User Story**: US6 - Git Dependency Integration (completion)
**Independent Test**: GitHub Actions build succeeds with SSH deploy key, installs spec-kitty-events
**Estimated Lines**: ~220 lines
**Prompt**: `tasks/WP08-pyproject-toml-update-and-ci-configuration.md`

### Included Subtasks

- [x] T041 - Pin spec-kitty-events to specific commit hash in pyproject.toml
- [x] T042 - Update GitHub Actions workflow with SSH setup steps
- [x] T043 - Test CI build end-to-end (trigger workflow, verify library installs)
- [x] T044 - Document dependency update process in CONTRIBUTING.md
- [x] T045 - Add spec-kitty-events version to `spec-kitty --version` output

### Implementation Notes

**Commit Pinning** (T041):
```toml
[tool.poetry.dependencies]
spec-kitty-events = { git = "ssh://git@github.com/Priivacy-ai/spec-kitty-events.git", rev = "abc1234" }
```

**CI Setup** (T042):
```yaml
- name: Setup SSH for private repo
  run: |
    mkdir -p ~/.ssh
    echo "${{ secrets.SPEC_KITTY_EVENTS_DEPLOY_KEY }}" > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
    ssh-keyscan github.com >> ~/.ssh/known_hosts
```

### Parallel Opportunities

- All subtasks must run sequentially (dependencies on each other)

### Dependencies

- Depends on WP01-WP07 (all implementation complete, ready to finalize CI)

### Risks & Mitigations

- **Risk**: SSH key secret not configured in repository settings
  - **Mitigation**: T043 validates CI end-to-end, T044 documents setup process
- **Risk**: Commit hash becomes stale (library updated but pyproject.toml not)
  - **Mitigation**: T044 documents update process (update commit, run `poetry lock`)

---

## Parallelization Strategy

**Wave 1** (no dependencies):
- WP01 (Git Dependency Setup) - foundational

**Wave 2** (depends on WP01):
- WP02 (Event Storage Foundation)

**Wave 3** (depends on WP02):
- WP03 (EventStore & AOP Middleware)

**Wave 4** (depends on WP03):
- WP04 (SQLite Query Index) [P]
- WP07 (Error Logging) [P]

**Wave 5** (depends on WP04):
- WP05 (Event Reading & State Reconstruction)

**Wave 6** (depends on WP05):
- WP06 (Conflict Detection) [P]
- WP08 (CI Configuration) [P]

**Parallelization Opportunities**: 6 of 8 WPs can run in parallel waves (WP04/WP07, WP06/WP08). Sequential dependency chain is 6 deep (WP01 → WP02 → WP03 → WP04 → WP05 → WP06).

---

## MVP Scope Recommendation

**Minimum Viable Product**: WP01 + WP02 + WP03 + WP04 + WP05 (5 work packages)

**Rationale**:
- WP01-WP03: Core event emission (US1 satisfied)
- WP04-WP05: Event reading with index (US2, US3 satisfied)
- Omits: Conflict detection (US4), Error logging (US7), CI finalization (US6 partial)

**MVP delivers**: Events emitted on workflow changes, status command reads from event log, query performance optimized with SQLite index.

**Defer to Phase 2**: Conflict resolution (US4), error logging (US7), full CI validation (US6 completion).

---

## Subtask Summary

**Total Subtasks**: 45 (T001-T045)
**Work Packages**: 8 (WP01-WP08)
**Average Subtasks per WP**: 5.6 (within ideal 3-7 range)
**Estimated Prompt Sizes**: 220-420 lines (all within 700-line maximum)

**Subtask Distribution**:
- WP01: 5 subtasks (~280 lines)
- WP02: 7 subtasks (~420 lines) ⚠️ (upper limit, but manageable)
- WP03: 6 subtasks (~350 lines)
- WP04: 6 subtasks (~380 lines)
- WP05: 6 subtasks (~320 lines)
- WP06: 5 subtasks (~290 lines)
- WP07: 5 subtasks (~250 lines)
- WP08: 5 subtasks (~220 lines)

**Validation**: ✓ All WPs within 3-10 subtask range, all estimated prompts <700 lines.

---

## Implementation Sequence

**Recommended order for single-agent implementation**:
1. WP01 (foundation) → 2. WP02 (storage) → 3. WP03 (emission) → 4. WP04 (index) → 5. WP05 (reading) → 6. WP06 (conflicts) → 7. WP07 (errors) → 8. WP08 (CI)

**Recommended order for multi-agent parallelization**:
- Agent 1: WP01 → WP02 → WP03 → WP05 (sequential critical path)
- Agent 2: Wait for WP03 → WP04 (index, parallel with Agent 1's WP05)
- Agent 3: Wait for WP03 → WP07 (errors, parallel with WP04/WP05)
- Agent 4: Wait for WP05 → WP06 (conflicts) + WP08 (CI)

**Timeline Estimate** (single agent):
- WP01-WP05 (MVP): ~5-7 implementation sessions
- WP06-WP08 (polish): ~3-4 implementation sessions
- **Total**: ~8-11 sessions for complete feature

---

## Success Metrics

**Coverage**:
- ✅ US1 (Event Emission): WP02 + WP03
- ✅ US2 (Event Reading): WP05
- ✅ US3 (SQLite Index): WP04
- ✅ US4 (Conflict Detection): WP06
- ✅ US5 (Daily File Rotation): WP02 (T010)
- ✅ US6 (Git Dependency): WP01 + WP08
- ✅ US7 (Error Logging): WP07

**Functional Requirements Coverage**: 27/28 FRs (FR-028 explicitly deferred as migration to future feature)

**Quality Gates**:
- Event write latency: <15ms (T014, T023 implementation targets)
- Query performance: <500ms for 1000+ events (T021 optimization target)
- CLI command completion: <2 seconds (validated as trivial overhead)
