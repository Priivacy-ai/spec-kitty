# Implementation Plan: Mission Collaboration CLI with Soft Coordination

**Branch**: `2.x` | **Date**: 2026-02-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/kitty-specs/040-mission-collaboration-cli-soft-coordination/spec.md`

**Sprint Context**: S1/M1 Step 1 - Observe+Decide behavior with canonical event emission and advisory warnings

## Summary

This feature implements mission collaboration commands for the spec-kitty CLI, enabling multiple developers to work concurrently with advisory collision warnings (soft coordination, not hard locks). The system provides 6 CLI commands (join, focus set, drive set, status, comment, decide) that emit 14 canonical collaboration event types to a local durable queue with offline replay support. Integration with feature 006 (spec-kitty-events) provides event schemas, while integration with SaaS provides participant identity management and event ingestion.

**Core Technical Approach:**
- **Parallel development with feature 006**: Pin to spec-kitty-events prerelease, strict contract ownership (006: schemas/payloads, 040: emission/queue/replay)
- **Module organization**: Command handlers in `mission/` package, domain logic in `collaboration/`, adapter interface in `adapters/`, event queue in `events/`
- **Session state**: Per-mission isolation in `~/.spec-kitty/missions/<mission_id>/session.json` with active mission pointer
- **Testing**: Unit + integration tests on every PR (mock SaaS, pin 006 prerelease), E2E gate against real SaaS dev for S1/M1 exit

## Technical Context

**Language/Version**: Python 3.11+ (spec-kitty codebase requirement)

**Primary Dependencies**:
- **typer** - CLI framework (existing)
- **rich** - Console output for warnings/prompts (existing)
- **ruamel.yaml** - YAML parsing (existing)
- **spec-kitty-events** - Event schemas, canonical envelope (feature 006 prerelease, Git dependency pinned to commit)
- **httpx** - SaaS API client (join, replay)
- **ulid-py** - ULID generation for event_id and participant_id

**Storage**:
- Filesystem only (no database)
- Event queue: `~/.spec-kitty/events/<mission_id>.jsonl` (newline-delimited JSON, ULID-ordered)
- Session state: `~/.spec-kitty/missions/<mission_id>/session.json` (per-mission isolation) + `~/.spec-kitty/session.json` (active mission pointer)

**Testing**:
- **pytest** with 90%+ test coverage for new code (constitution requirement)
- **mypy --strict** must pass (no type errors)
- **Unit tests**: Command handlers, collision detection, queue append/replay ordering, adapter compliance (no network)
- **Integration tests**: Pin to feature 006 prerelease, mock SaaS join/replay APIs, validate canonical envelope compatibility
- **E2E test**: Real SaaS dev environment, 3-participant scenario (concurrent drive, warning+ack, offline replay) - S1/M1 exit gate

**Target Platform**:
- Cross-platform: Linux, macOS, Windows 10+ (constitution requirement)
- Python 3.11+ required
- Git required (existing spec-kitty constraint)

**Performance Goals**:
- CLI commands must complete in < 2 seconds for typical operations (constitution requirement)
- Offline queue append: < 50ms per event (no network wait)
- Replay: < 5 seconds for batches up to 100 events (spec requirement)
- Collision detection: < 500ms warning latency p99 (success criterion #2)

**Constraints**:
- **SaaS-authoritative participation**: Must join mission online (SaaS mints participant_id), offline commands fail if not joined
- **Contract ownership**: Feature 006 owns event schemas/payloads, feature 040 owns emission/queue/replay (parallel development)
- **Soft coordination only**: No hard locks, warnings are advisory (S1/M1 scope, full policy matrix deferred)
- **Local-first event queue**: CLI local queue authoritative for ordering (SaaS eventual consistency replica)
- **Single active mission**: One mission focus per CLI context (S1/M1 scope, multi-mission deferred)

**Scale/Scope**:
- 6 CLI commands (join, focus set, drive set, status, comment, decide)
- 14 collaboration event types (ParticipantJoined, DriveIntentSet, FocusChanged, CollisionWarning, etc.)
- 4 join roles (developer, reviewer, observer, stakeholder) + 3 participant types (human, llm_context, service)
- 5 adapter operations (normalize_actor_identity, parse_observation, detect_decision_request, format_decision_answer, healthcheck)
- 2 adapter implementations (Gemini, Cursor - baseline stubs for S1/M1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Technical Standards Compliance

| Standard | Requirement | Feature 040 Compliance |
|----------|-------------|------------------------|
| Python Version | 3.11+ required | ✅ Uses existing Python 3.11+ codebase |
| Key Dependencies | typer, rich, ruamel.yaml, pytest | ✅ Uses existing + adds httpx, ulid-py, spec-kitty-events |
| Testing Coverage | 90%+ for new code | ✅ Planned: unit tests + integration tests + E2E test |
| Type Checking | mypy --strict must pass | ✅ All new modules will have type annotations |
| CLI Performance | < 2 seconds typical operations | ✅ Offline commands < 50ms, online < 2s (with SaaS latency) |
| Cross-Platform | Linux, macOS, Windows 10+ | ✅ Python + filesystem only (no OS-specific features) |

### ✅ Architecture: Private Dependency Pattern Compliance

| Requirement | Feature 040 Compliance |
|-------------|------------------------|
| spec-kitty-events integration | ✅ Uses Git dependency pinned to feature 006 prerelease commit |
| Commit pinning (not `rev = "main"`) | ✅ Will pin to specific 006 branch commit during development, update to main commit hash after 006 merge |
| CI/CD authentication | ✅ Uses existing `SPEC_KITTY_EVENTS_DEPLOY_KEY` secret (no changes needed) |
| Vendoring for PyPI | ✅ Follows existing vendor_and_release.py process (no changes needed) |
| Testing integration changes | ✅ Pin to 006 feature branch during parallel development, update after 006 merge |

**Development workflow:**
1. Feature 006 team develops collaboration event schemas in `spec-kitty-events` feature branch
2. Feature 040 pins to 006 feature branch commit: `spec-kitty-events = { git = "...", rev = "abc1234" }`
3. Iterate: 006 updates schemas → 040 updates pin → test integration
4. Merge 006 feature → main
5. Update 040 to pin to 006 main commit hash
6. Merge 040 feature → 2.x

### ✅ Architecture: Two-Branch Strategy Compliance

| Requirement | Feature 040 Compliance |
|-------------|------------------------|
| Target branch | ✅ 2.x branch (active development, SaaS transformation) |
| 1.x compatibility | ✅ N/A (2.x greenfield, no backward compatibility required) |
| Event sourcing | ✅ Uses spec-kitty-events library, emits canonical events with ULID/Lamport clocks |
| Breaking changes | ✅ Allowed (pre-release 2.x development) |

### ✅ Code Quality Compliance

| Requirement | Feature 040 Compliance |
|-------------|------------------------|
| PR approval | ✅ Standard 1 approval process |
| CI checks | ✅ Tests, type checking, pre-commit hooks (UTF-8 encoding) |
| Docstrings | ✅ All public APIs will have docstrings with parameter types |
| Security | ✅ No credentials in code, SaaS session tokens stored in `~/.spec-kitty/` with restricted permissions |
| CHANGELOG.md | ✅ Will document new commands and breaking changes (2.x) |

### ⚠️ Constitution Exceptions

**None required.** This feature aligns with all constitution requirements.

## Project Structure

### Documentation (this feature)

```
kitty-specs/040-mission-collaboration-cli-soft-coordination/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (N/A - no research needed)
├── data-model.md        # Phase 1 output (entities, state machine)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (event schemas reference, adapter protocols)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command)
```

### Source Code (repository root)

**Structure Decision**: Single project (Option 1) with enhanced CLI and new domain modules. Feature 040 extends the existing spec-kitty CLI structure with new mission command package and collaboration domain logic.

```
src/specify_cli/
├── cli/
│   └── commands/
│       ├── mission/                        # NEW: Mission command handlers (thin)
│       │   ├── __init__.py
│       │   ├── join.py                     # mission join <mission_id> --role <role>
│       │   ├── focus.py                    # mission focus set <wp_id|step_id>
│       │   ├── drive.py                    # mission drive set --state <active|inactive>
│       │   ├── status.py                   # mission status
│       │   ├── comment.py                  # mission comment --text "..."
│       │   ├── decide.py                   # mission decide --text "..."
│       │   └── discovery.py                # mission list/current/info (move existing behavior)
│       └── mission.py                      # TRANSITION: Thin shim (re-exports, remove after migration)
│
├── collaboration/                          # NEW: Domain logic (use-cases, warnings, state)
│   ├── __init__.py
│   ├── service.py                          # Use-cases: join_mission, set_focus, set_drive, etc.
│   ├── warnings.py                         # Advisory checks: detect_collision, check_stale_context
│   └── state.py                            # Local materialized view/cache (mission roster, participant state)
│
├── adapters/                               # NEW: Adapter interface + implementations
│   ├── __init__.py
│   ├── observe_decide.py                   # ObserveDecideAdapter protocol (5 operations)
│   ├── gemini.py                           # GeminiObserveDecideAdapter (baseline stub)
│   └── cursor.py                           # CursorObserveDecideAdapter (baseline stub)
│
├── events/                                 # ENHANCED: Event queue + transport
│   ├── __init__.py
│   ├── store.py                            # ENHANCE: Durable queue (JSONL append, ULID ordering)
│   └── replay.py                           # NEW: Transport/replay logic (batch send to SaaS)
│
├── models/                                 # EXISTING: Keep existing models
└── ...                                     # Other existing modules (unchanged)

tests/
├── specify_cli/
│   ├── cli/
│   │   └── commands/
│   │       └── mission/                    # NEW: Command handler unit tests
│   │           ├── test_join.py
│   │           ├── test_focus.py
│   │           ├── test_drive.py
│   │           ├── test_status.py
│   │           ├── test_comment.py
│   │           └── test_decide.py
│   │
│   ├── collaboration/                      # NEW: Domain logic unit tests
│   │   ├── test_service.py
│   │   ├── test_warnings.py
│   │   └── test_state.py
│   │
│   ├── adapters/                           # NEW: Adapter tests
│   │   ├── test_observe_decide.py          # Protocol compliance
│   │   ├── test_gemini.py                  # Contract tests (recorded fixtures)
│   │   └── test_cursor.py                  # Contract tests (recorded fixtures)
│   │
│   ├── events/                             # ENHANCED: Event queue + replay tests
│   │   ├── test_store.py                   # Queue append, ordering, durability
│   │   └── test_replay.py                  # Batch send, retry, validation
│   │
│   └── integration/                        # NEW: Integration tests
│       ├── test_006_event_schemas.py       # Pin to 006 prerelease, validate envelope
│       ├── test_saas_join_mock.py          # Mock SaaS join API
│       ├── test_saas_replay_mock.py        # Mock SaaS replay API
│       └── test_offline_queue_replay.py    # End-to-end offline → online flow
│
└── e2e/                                    # NEW: E2E test (S1/M1 exit gate)
    └── test_collaboration_scenario.py      # 3 participants, real SaaS dev
```

**Key Points:**
- **Thin command handlers**: Commands delegate to `collaboration.service` use-cases
- **Domain logic isolation**: `collaboration/` contains all business logic (collision detection, state management)
- **Adapter pattern**: `adapters/` provides protocol + implementations (Gemini, Cursor stubs)
- **Event infrastructure**: `events/` handles durable queue + SaaS replay transport
- **Transition shim**: `mission.py` re-exports from `mission/` package during migration, removed after

## Complexity Tracking

*No constitution violations - this section is not applicable.*

## Phase 0: Research

**Status:** No research required.

All planning questions were resolved during planning interrogation:
1. ✅ Feature 006 dependency model (parallel dev, contract ownership)
2. ✅ Module organization (mission/, collaboration/, adapters/, events/)
3. ✅ Testing strategy (unit + integration PR checks, E2E gate)
4. ✅ Session state management (per-mission + active pointer)

**No outstanding clarifications** - all technical decisions documented in Technical Context section above.

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for detailed entity definitions, relationships, and state machines.

**Core Entities:**
- **MissionRun**: Runtime collaboration container (mission_id, status, participant_count)
- **Participant**: Developer/reviewer/observer/stakeholder (participant_id ULID, role, participant_type, drive_intent, focus, capabilities)
- **WorkPackage**: Mission-local execution unit (wp_id, status, dependencies)
- **PromptStep**: Atomic execution step (step_id, parent_wp_id, status)
- **CollaborationEvent**: Canonical event envelope (event_id ULID, event_type, aggregate_id=mission_id, payload, timestamp, lamport_clock, causation_id ULID)
- **SessionState**: Per-mission runtime state (mission_id, participant_id ULID, role, joined_at)

**State Machines:**
- **Drive Intent**: inactive → active (with collision check) → inactive
- **Focus**: none → wp:<id> | step:<id> → none (implicit release on change)
- **Participant Status**: joining → joined → active → inactive → left

**Key Invariants:**
- participant_id is SaaS-minted ULID (mission-scoped, bound to auth principal)
- event_id and causation_id are ULIDs (26 chars)
- aggregate_id = mission_id, correlation_id = mission_run_id (feature 006 extension)
- Collision warnings do not block execution (advisory only)

### API Contracts

See [contracts/](contracts/) directory for detailed schemas.

**CLI Commands** (6 total):
```bash
spec-kitty mission join <mission_id> --role <developer|reviewer|observer|stakeholder>
spec-kitty mission focus set <wp_id|step_id>
spec-kitty mission drive set --state <active|inactive>
spec-kitty mission status [--verbose]
spec-kitty mission comment --text "..." [--stdin]
spec-kitty mission decide --text "..." [--stdin]
```

**SaaS API Integration** (2 endpoints):
- `POST /api/v1/missions/{mission_id}/participants` - Join mission (SaaS mints participant_id)
- `POST /api/v1/events/batch/` - Replay queued events (batch upload)

**Adapter Protocol** (`ObserveDecideAdapter`, 5 operations):
```python
class ObserveDecideAdapter(Protocol):
    def normalize_actor_identity(self, runtime_ctx: dict) -> ActorIdentity: ...
    def parse_observation(self, output: str | dict) -> list[ObservationSignal]: ...
    def detect_decision_request(self, observation: ObservationSignal) -> DecisionRequestDraft | None: ...
    def format_decision_answer(self, answer: str) -> str: ...
    def healthcheck(self) -> AdapterHealth: ...
```

**Event Schemas** (14 types, feature 006 ownership):
- ParticipantInvited, ParticipantJoined, ParticipantLeft, PresenceHeartbeat
- DriveIntentSet, FocusChanged
- PromptStepExecutionStarted, PromptStepExecutionCompleted
- ConcurrentDriverWarning, PotentialStepCollisionDetected, WarningAcknowledged
- CommentPosted, DecisionCaptured, SessionLinked

**Event Envelope** (spec-kitty-events base model):
```python
{
  "event_id": "01HQRS8ZMBE6XYZABC0123DEFG",  # ULID (26 chars)
  "event_type": "DriveIntentSet",
  "aggregate_id": "mission-abc-123",          # mission_id
  "payload": { ... },                         # Event-specific data
  "timestamp": "2026-02-15T10:30:00Z",
  "node_id": "cli-alice-macbook",
  "lamport_clock": 42,
  "causation_id": "01HQRS8ZMBE6XYZABC0123ABCD"  # ULID (26 chars)
}
```

### Quickstart Guide

See [quickstart.md](quickstart.md) for developer onboarding.

**Developer Setup:**
```bash
# 1. Clone spec-kitty repository
git clone https://github.com/Priivacy-ai/spec-kitty.git
cd spec-kitty

# 2. Checkout 2.x branch
git checkout 2.x

# 3. Install dependencies (includes pinned spec-kitty-events via Git)
poetry install

# 4. Run tests to verify setup
pytest tests/specify_cli/cli/commands/mission/ -v
pytest tests/specify_cli/collaboration/ -v
pytest tests/specify_cli/integration/ -v
```

**Integration with Feature 006:**
```bash
# Check current pinned commit
grep "spec-kitty-events" pyproject.toml

# Update to new 006 commit (during parallel development)
poetry remove spec-kitty-events
poetry add "spec-kitty-events @ git+https://github.com/Priivacy-ai/spec-kitty-events.git@<new-commit-hash>"
poetry lock --no-update
poetry install

# Verify integration
pytest tests/specify_cli/integration/test_006_event_schemas.py -v
```

**Running Tests:**
```bash
# Unit tests (fast, no network)
pytest tests/specify_cli/cli/commands/mission/ -v
pytest tests/specify_cli/collaboration/ -v
pytest tests/specify_cli/adapters/ -v

# Integration tests (mock SaaS, pin 006)
pytest tests/specify_cli/integration/ -v

# E2E test (requires SaaS dev environment)
export SAAS_DEV_URL=https://dev.spec-kitty-saas.com
export SAAS_DEV_API_KEY=<api-key>
pytest tests/e2e/test_collaboration_scenario.py -v

# Type checking
mypy src/specify_cli/cli/commands/mission/ --strict
mypy src/specify_cli/collaboration/ --strict
mypy src/specify_cli/adapters/ --strict

# Coverage report
pytest --cov=src/specify_cli --cov-report=html
open htmlcov/index.html
```

**Common Development Tasks:**
```bash
# Add new command handler
# 1. Create src/specify_cli/cli/commands/mission/new_command.py
# 2. Add route in mission/__init__.py
# 3. Add use-case in collaboration/service.py
# 4. Add tests in tests/specify_cli/cli/commands/mission/test_new_command.py

# Add new adapter
# 1. Create src/specify_cli/adapters/new_adapter.py
# 2. Implement ObserveDecideAdapter protocol
# 3. Add contract tests with recorded fixtures

# Update event schemas (feature 006 dependency)
# 1. Coordinate with 006 team on schema changes
# 2. Update pinned commit after 006 merge
# 3. Run integration tests to verify compatibility
```

## Next Steps

**This command is COMPLETE after generating planning artifacts.**

**Generated Files:**
- ✅ `plan.md` - This file (implementation plan)
- ⏭️ `data-model.md` - Phase 1 output (entities, state machines) - TO BE GENERATED
- ⏭️ `quickstart.md` - Phase 1 output (developer guide) - TO BE GENERATED
- ⏭️ `contracts/` - Phase 1 output (event schemas reference, adapter protocols) - TO BE GENERATED

**DO NOT PROCEED TO:**
- ❌ `tasks.md` generation (requires explicit `/spec-kitty.tasks` command)
- ❌ Work package creation (requires `/spec-kitty.tasks` command)
- ❌ Implementation (requires work packages from tasks command)

**Next Command:** `/spec-kitty.tasks` (user must invoke explicitly to generate work packages)

---

## Phase 1 Artifact Generation

Now generating Phase 1 design artifacts...
