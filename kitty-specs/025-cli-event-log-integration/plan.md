# Implementation Plan: CLI Event Log Integration

**Branch**: `025-cli-event-log-integration` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Target Branch**: 2.x (greenfield, no 1.x backward compatibility)

## Summary

Integrate the completed spec-kitty-events library into the CLI to replace primitive YAML activity logs with structured event log using Lamport clocks and CRDT merge rules. This feature provides causal ordering, conflict detection, and deterministic merge rules to serve as the foundation for CLI ↔ Django sync protocol (Dependency 0 for SaaS platform).

**Key Technical Decisions** (validated during planning interrogation):
- Events-only on 2.x branch (no YAML logs, migration script deferred)
- AOP-style middleware for event emission integration
- AOP decorator pattern for EventStore dependency injection (`@with_event_store`)
- Synchronous event writes (JSONL + SQLite index, ~15ms overhead acceptable for CLI)
- Git dependency on spec-kitty-events with commit pinning per ADR-11

**Planning Status**: ✅ Phase 0 (Research) and Phase 1 (Design) COMPLETE
**Next Command**: `/spec-kitty.tasks` (user must invoke to generate work packages)

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement per constitution)
**Primary Dependencies**:
- spec-kitty-events (Git dependency: `git+https://github.com/Priivacy-ai/spec-kitty-events.git@<commit>`)
- pathlib (event log file operations)
- sqlite3 (query index)
- typer (CLI framework, existing)
- ruamel.yaml (frontmatter parsing, existing)

**Storage**:
- JSONL files (`.kittify/events/YYYY-MM-DD.jsonl`) - append-only, source of truth
- JSON file (`.kittify/clock.json`) - Lamport clock state
- SQLite database (`.kittify/events/index.db`) - query optimization index
- JSONL files (`.kittify/errors/YYYY-MM-DD.jsonl`) - error logging (Manus pattern)

**Testing**: pytest with 90%+ coverage (constitution requirement)

**Target Platform**: Cross-platform (Linux, macOS, Windows 10+) per constitution

**Project Type**: Single Python CLI application (spec-kitty existing codebase)

**Performance Goals**:
- Event write latency: <15ms per event (synchronous JSONL + index)
- CLI command completion: <2 seconds (constitution requirement - 15ms event overhead trivial)
- Index query: <500ms for 1000+ events (user story 3 acceptance criteria)

**Constraints**:
- File locking required (POSIX advisory locks for atomic appends)
- Daily file rotation (Git merge-friendly, manageable file sizes)
- JSONL as source of truth (index is derived state, rebuilds on corruption)
- Immutable events (append-only, no updates/deletes)

**Scale/Scope**:
- Expected event volume: <100k events/month per project (research: adequate for Postgres JSONL)
- Deployment: 2.x branch only (no 1.x migration until 2.x nears completion)
- Integration: Foundation for CLI ↔ Django sync protocol (future feature)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Alignment with Constitution

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **Python 3.11+** | ✅ PASS | Using existing spec-kitty codebase (Python 3.11+) |
| **90%+ test coverage** | ✅ PLANNED | pytest integration + unit tests in Phase 2 implementation |
| **mypy --strict** | ✅ PLANNED | Type annotations for all new modules |
| **CLI < 2 seconds** | ✅ PASS | 15ms event overhead trivial vs 2000ms budget |
| **Cross-platform** | ✅ PASS | POSIX file locking available on Linux/macOS/Windows WSL |
| **Git dependency pattern (ADR-11)** | ✅ PASS | spec-kitty-events via `git+https://...@<commit>` with commit pinning |
| **2.x branch strategy (ADR-12)** | ✅ PASS | Feature targets 2.x only, no 1.x compatibility |
| **SSH deploy key for CI** | ✅ PLANNED | Use existing `SPEC_KITTY_EVENTS_DEPLOY_KEY` secret (already configured per constitution) |

### New Patterns Introduced

| Pattern | Justification | Constitution Impact |
|---------|---------------|---------------------|
| **AOP Middleware** | Event emission integrated via decorators (non-invasive to command logic) | Complements existing Typer CLI patterns |
| **Synchronous Event Writes** | Prioritizes reliability over latency (15ms acceptable for CLI use case) | Aligns with "< 2 seconds" performance requirement |
| **JSONL + SQLite Dual Storage** | JSONL = source of truth, SQLite = derived index (research-validated pattern) | Adds new storage convention to `.kittify/` directory |

### Constitution Violations

**NONE** - All requirements satisfied.

### Post-Design Re-Check

*To be completed after Phase 1 design artifacts generated. Will validate:*
- Data model entities don't introduce unexpected complexity
- Event schema versioning strategy documented
- Error handling patterns align with constitution quality gates

## Project Structure

### Documentation (this feature)

```
kitty-specs/[###-feature]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

**Structure Decision**: Single Python CLI project (existing spec-kitty codebase). Event log functionality integrated into existing structure.

```
src/specify_cli/
├── events/                    # NEW: Event log integration (this feature)
│   ├── __init__.py
│   ├── middleware.py         # AOP decorators (@with_event_store)
│   ├── store.py              # EventStore adapter wrapping spec-kitty-events
│   ├── emitter.py            # Event emission helpers
│   ├── reader.py             # Event reading and projection
│   ├── index.py              # SQLite index management
│   └── types.py              # Event type definitions
├── cli/
│   └── commands/
│       ├── agent.py          # MODIFIED: Add event emission to status commands
│       └── status.py         # MODIFIED: Read from event log instead of YAML
├── core/
│   └── config.py             # MODIFIED: Add event log config paths
└── ...                        # Existing modules

tests/
├── events/                    # NEW: Event log tests
│   ├── test_middleware.py
│   ├── test_store.py
│   ├── test_emitter.py
│   ├── test_reader.py
│   ├── test_index.py
│   └── test_integration.py   # End-to-end workflow tests
├── integration/
│   └── test_event_workflow.py  # NEW: Workflow state changes via events
└── ...                        # Existing tests

.kittify/                      # Project-local state (per-project)
├── events/                    # NEW: Event storage
│   ├── 2026-01-27.jsonl      # Daily event log (append-only)
│   └── index.db              # SQLite query index (derived state)
├── errors/                    # NEW: Error logging (Manus pattern)
│   └── 2026-01-27.jsonl      # Daily error log
├── clock.json                 # NEW: Lamport clock state
└── ...                        # Existing config files
```

**Integration Points**:
- `spec-kitty agent tasks move-task` → Emits `WPStatusChanged` event
- `spec-kitty status` → Reads events, reconstructs kanban board
- `spec-kitty agent feature setup-spec` → Emits `SpecCreated` event
- `spec-kitty agent feature finalize-tasks` → Emits `WPCreated` events

## Complexity Tracking

**No constitution violations** - This section is not applicable.

All design decisions align with existing constitution requirements. New patterns (AOP middleware, dual storage) are justified by research and don't violate complexity constraints.

---

## Phase 0: Research (✅ COMPLETE)

**Status**: Complete (research pre-existed from external sources)
**Artifacts**: `research.md`

### Research Summary

Three foundational research areas validated the technical approach:

1. **Event Sourcing Patterns** (`event-sourcing.md`, 650 lines, 7 sources)
   - JSONL + SQLite adequate for CLI scale (<100k events/month)
   - CQRS unnecessary for MVP (Fowler guidance)
   - Snapshotting deferred until WPs exceed 1000 events
   - Weak schema versioning from day 1

2. **Sync Protocols** (`sync-protocols.md`, 439 lines, 9 sources)
   - Last-Write-Wins sufficient for workflow state (Linear, Figma case studies)
   - CRDTs overkill for structured entities (not text editing)
   - Synchronous writes appropriate for CLI (reliability > latency)

3. **Workflow State Machines** (`workflow-state-machines.md`, 849 lines, 5 sources)
   - Jira's three-phase transition model (Conditions → Validators → Post-Functions)
   - GitHub Actions dependency pattern maps to WP dependencies
   - Event sourcing enables audit trail (Temporal pattern)

**Key Decisions**:
- ✅ JSONL + SQLite (not Postgres or EventStoreDB)
- ✅ Synchronous writes (not async or write-through cache)
- ✅ Last-Write-Wins with Lamport clocks (not CRDTs or OT)
- ✅ No CQRS in Phase 1 (query event log directly)
- ✅ Three-phase transition validation (Jira pattern)

All decisions validated with HIGH or MEDIUM confidence research evidence. See `research.md` for detailed analysis.

---

## Phase 1: Design & Contracts (✅ COMPLETE)

**Status**: Complete
**Artifacts**: `data-model.md`, `contracts/`, `quickstart.md`

### Data Model Design

**Core Entities** (defined in `data-model.md`):
1. **Event**: Immutable record with ULID, Lamport clock, entity_id, event_type, payload
2. **LamportClock**: Logical clock providing causal ordering (stored in `clock.json`)
3. **EventStore**: Storage adapter wrapping spec-kitty-events library
4. **EventIndex**: SQLite query index for fast filtering (derived state)
5. **ClockStorage**: Persistence adapter for Lamport clock state
6. **ErrorStorage**: Error logging for Manus pattern (agent learning)

**Event Types** (7 types defined):
- Workflow: `WPStatusChanged`, `SpecCreated`, `WPCreated`, `WorkspaceCreated`, `SubtaskCompleted`
- Gates: `GateCreated`, `GateResultChanged`

**State Reconstruction**: Current state derived from event replay (Lamport clock ordering)

### Contracts

**JSON Schemas** (in `contracts/`):
- `EventV1.json`: Base event schema with required fields (event_id ULID, lamport_clock, entity_id, payload)
- `WPStatusChangedPayload.json`: Payload schema for workflow transitions (feature_slug, old_status, new_status, gate_results)

**Event Versioning**: All events include `event_version: 1` field from day 1 (enables evolution)

**Validation**: JSON Schema validation on write (strict mode), weak schema tolerance on read (backward compatibility)

### Quickstart Guide

**Usage Examples** (in `quickstart.md`):
1. Emit event on status change (`move_task` command)
2. Read status from event log (`status` command)
3. Query event history (Python API)
4. Handle conflicts (concurrent operations)
5. Error logging (invalid transitions)
6. Rebuild index (corruption recovery)

**Integration Points**: `/spec-kitty.specify` → `SpecCreated`, `/spec-kitty.tasks` → `WPCreated`, `/spec-kitty.implement` → `WorkspaceCreated`

**Testing Strategy**: Unit tests (event serialization, clock atomicity, JSONL append), integration tests (full workflow), performance tests (write latency <15ms)

### Agent Context Update

**Status**: NOT REQUIRED

Event log integration is **internal infrastructure** - it happens behind the scenes via AOP middleware decorators. The command interfaces (`/spec-kitty.implement`, `/spec-kitty.status`, `/spec-kitty.specify`, etc.) remain unchanged from the user's perspective.

**No template updates needed** because:
- Event emission is automatic (via `@with_event_store` decorator)
- Commands don't expose event log operations directly to users
- Event log is transparent to agents (they use existing commands as before)

**Future consideration**: If explicit event log commands are added (e.g., `/spec-kitty.events query`, `/spec-kitty.events rebuild-index`), those would require new command template files in `src/specify_cli/missions/software-dev/command-templates/`.

---

## Post-Design Constitution Re-Check (✅ PASS)

**Re-validation after Phase 1 design**:

| Requirement | Phase 1 Status | Evidence |
|-------------|----------------|----------|
| **Event Schema Versioning** | ✅ PASS | All events include `event_version: 1` field (data-model.md) |
| **Error Handling** | ✅ PASS | ErrorStorage entity provides structured error logging (data-model.md) |
| **Data Model Complexity** | ✅ PASS | 6 entities (Event, Clock, Store, Index, ClockStorage, ErrorStorage) - reasonable complexity |
| **Contract Clarity** | ✅ PASS | JSON schemas in `contracts/` provide unambiguous validation rules |
| **Performance Targets** | ✅ PASS | Event write <15ms, status reconstruction <50ms (within <2s budget) |

**New Architectural Patterns Introduced**:
1. **AOP Middleware**: `@with_event_store` decorator for event emission (non-invasive integration)
2. **Dual Storage**: JSONL (source of truth) + SQLite index (derived state for queries)
3. **Weak Schema Versioning**: Tolerate missing fields on read, validate strictly on write

**No violations introduced**. Design aligns with constitution requirements.