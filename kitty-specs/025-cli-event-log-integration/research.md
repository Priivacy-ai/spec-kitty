# Phase 0 Research: CLI Event Log Integration

**Date**: 2026-01-27
**Phase**: Planning Phase 0
**Status**: Complete (research pre-exists from external sources)

## Executive Summary

This feature integrates event sourcing patterns into the spec-kitty CLI using the completed spec-kitty-events library. Research validates the technical approach through three foundational areas:

1. **Event Sourcing Patterns** - Confirmed JSONL + SQLite adequate for CLI scale (<100k events/month)
2. **Sync Protocols** - Validated Last-Write-Wins (LWW) sufficient for workflow state (no CRDTs needed)
3. **Workflow State Machines** - Adopted Jira's three-phase transition model (Conditions → Validators → Post-Functions)

**Key Research Findings**:
- ✅ Postgres JSONL adequate for MVP scale (Martin Fowler, Marten case study)
- ✅ CQRS unnecessary for Phase 1 (read/write ratio insufficient to justify complexity)
- ✅ Snapshotting deferred until WPs exceed 1000 events (performance optimization)
- ✅ LWW for entity-level conflict resolution (Linear, Figma case studies)
- ✅ OT/CRDTs overkill for structured workflow data (not collaborative text editing)
- ✅ Synchronous writes appropriate for CLI use case (reliability > latency)

**Sources**: All research sourced from `/Users/robert/ClaudeCowork/SpecKitty/research/best-practices/`:
- `event-sourcing.md` (650 lines, 7 sources, HIGH confidence)
- `sync-protocols.md` (439 lines, 9 sources, MEDIUM-HIGH confidence)
- `workflow-state-machines.md` (849 lines, 5 sources, HIGH confidence)

---

## Research Area 1: Event Sourcing Best Practices

**Source**: `/Users/robert/ClaudeCowork/SpecKitty/research/best-practices/event-sourcing.md`
**Confidence**: HIGH (Martin Fowler, Greg Young authoritative sources)

### Key Findings

**1. Storage Strategy: Postgres JSONB Adequate for MVP**

From research (lines 148-176):
> **Postgres JSONB Approach (Marten Pattern)**:
> - Cost-effective for MVP (<100k events/month)
> - JSONB indexing supports flexible event queries
> - Built-in ACID transactions for consistency

**Decision**: Use JSONL files for CLI (lighter than Postgres, no database dependency). SQLite index provides query optimization similar to Postgres JSONB indexing.

**Rationale**: CLI is even lower volume than web MVP (<100k events/month). File-based storage eliminates database setup complexity for users.

**2. CQRS Unnecessary for Phase 1**

From research (lines 100-109):
> Fowler emphasizes caution: **"You should be very cautious about using CQRS."**
> Most systems fit standard CRUD patterns where sharing models proves simpler. CQRS introduces significant mental and architectural overhead.

**Decision**: Skip CQRS in Phase 1. Query event log directly for status reconstruction.

**3. Event Schema Versioning Required from Day 1**

From research (lines 205-237):
> **Critical Insight**: *"Changing schemas was harder, not easier with event sourcing"* - Design versioning from day 1!

**Decision**: All events include `event_version: 1` field. Use weak schema initially (flexible JSON, tolerate missing fields).

**4. Snapshotting Deferred Until Needed**

From research (lines 52-62):
> **Snapshot Strategy**:
> - Cache aggregate state at periodic intervals (e.g., every 100 events)
> - Production evidence suggests snapshots become critical when aggregates exceed ~1000 events

**Decision**: Defer snapshotting to Phase 2. WorkPackages unlikely to exceed 1000 events in MVP.

### Patterns Applied to Spec Kitty

| Pattern | Research Source | Application |
|---------|----------------|-------------|
| **Event Schema Design** | Lines 399-428 | All events include: event_id (ULID), event_version, lamport_clock, entity_id, event_type, payload |
| **Weak Schema Versioning** | Lines 210-216 | Tolerate missing fields with defaults, add event_version from day 1 |
| **Inline Projections** | Lines 182-189 | WorkPackage.current_status derived from events during read |
| **Append-Only Log** | Lines 21-30 | JSONL files are immutable, events never updated/deleted |
| **Idempotency** | Lines 574-582 | Event emission checks for duplicate causation_id |

---

## Research Area 2: Sync Protocols & Conflict Resolution

**Source**: `/Users/robert/ClaudeCowork/SpecKitty/research/best-practices/sync-protocols.md`
**Confidence**: MEDIUM (company blogs), HIGH (technical analysis)

### Key Findings

**1. Last-Write-Wins Sufficient for Workflow State**

From research (lines 295-319):
> **Phase 1 (MVP): Last-Write-Wins**
> **Rationale**:
> - Workflow state = structured entities (WorkPackage, Task, Status)
> - Not collaborative text editing (no need for character-level CRDTs)
> - Conflicts rare in workflow management (agents work on separate WPs)

**Decision**: Use LWW with Lamport clock ordering for conflict resolution. spec-kitty-events library provides `is_concurrent()` for conflict detection.

**2. CRDTs Overkill for Structured Entities**

From research (lines 161-170):
> **CRDT Trade-Offs**:
> **Disadvantages**:
> - **Payload bloat**: 16-32 bytes metadata per character
> - **Memory overhead**: 2-3x more bandwidth than actual data
> - **Bundle size**: 100-200KB for CRDT libraries

From Linear case study (lines 75-77):
> Linear proves that **structured workflow data doesn't need CRDTs**. Last-Write-Wins is pragmatic and sufficient for issue tracking.

**Decision**: No CRDTs for entity-level state. Use CRDT sets only for tags (future feature, spec-kitty-events library already provides).

**3. Synchronous Writes Appropriate for CLI**

From research (lines 249-278):
> **Offline Buffer Pattern** (from Linear):
> 1. Queue operations locally in IndexedDB
> 2. Optimistic UI: Apply changes immediately
> 3. Background sync: Resend queued operations when reconnected

**Decision**: CLI is different from web apps. Synchronous writes prioritize reliability (no lost events on crash). 15ms overhead acceptable vs 2-second budget.

### Patterns Applied to Spec Kitty

| Pattern | Research Source | Application |
|---------|----------------|-------------|
| **Entity-Level LWW** | Lines 308-319 | WorkPackage status conflicts resolved by Lamport clock comparison |
| **Lamport Clocks** | Lines 295-310 | Causal ordering without wall-clock dependency (spec-kitty-events provides) |
| **Conflict Detection** | Lines 295-310 | Use `is_concurrent()` from spec-kitty-events library |
| **Offline Buffer** | Lines 275-285 | Deferred to Phase 2 (CLI ↔ Django sync), not needed for local-only Phase 1 |

---

## Research Area 3: Workflow State Machines & Gate Enforcement

**Source**: `/Users/robert/ClaudeCowork/SpecKitty/research/best-practices/workflow-state-machines.md`
**Confidence**: HIGH (official documentation: AWS, Temporal, Jira, GitHub)

### Key Findings

**1. Jira's Three-Phase Transition Model is Gold Standard**

From research (lines 193-246):
> Jira implements the most explicit gate enforcement pattern through a three-phase transition sequence:
> ```
> 1. CONDITIONS (Access Control) → who can transition
> 2. VALIDATORS (Input Validation) → gate checks
> 3. POST-FUNCTIONS (Enforcement Actions) → state updates + event emission
> ```

**Decision**: Adopt this pattern for WorkPackage state transitions. Validators are gates.

**2. GitHub Actions Dependency Pattern Maps to WP Dependencies**

From research (lines 326-365):
> **Job Dependency Pattern**: `needs` keyword creates dependency graph
> **Cascade-on-Failure Pattern**: *"If a job fails or is skipped, all jobs that need it are skipped"*

**Decision**: WorkPackage.dependencies field checked by validator. Failed/rejected WP blocks dependents.

**3. Event Sourcing Enables Audit Trail**

From research (lines 136-145):
> Temporal's event sourcing: *"Every workflow execution maintains an Event History recording all Commands and Events. This enables... Workflow state automatically reconstructed"*

**Decision**: WorkPackage state transitions emit events. Current state derived from event history (temporal queries supported).

### Patterns Applied to Spec Kitty

| Pattern | Research Source | Application |
|---------|----------------|-------------|
| **Three-Phase Transitions** | Lines 193-246 | Conditions → Validators (gates) → Post-Functions (event emission) |
| **Dependency Blocking** | Lines 326-387 | Validator checks dependencies complete before transition |
| **Post-Function Events** | Lines 247-271 | Emit WPStatusChanged after every successful transition |
| **Choice State Pattern** | Lines 48-84 | Conditional branching (e.g., CI fail → rejected, CI pass → done) |
| **Event Sourcing** | Lines 136-183 | State reconstructable from event log replay |

---

## Decisions Summary

### Technology Choices

| Decision | Research Evidence | Alternatives Rejected |
|----------|-------------------|----------------------|
| **JSONL + SQLite** | event-sourcing.md lines 148-176 | Postgres (overkill for CLI), EventStoreDB (too complex) |
| **Synchronous Writes** | sync-protocols.md lines 249-278 | Async (risk of lost events), write-through cache (unnecessary) |
| **Last-Write-Wins** | sync-protocols.md lines 295-319 | CRDTs (overkill), OT (not text editing) |
| **Lamport Clocks** | spec-kitty-events library | Vector clocks (overkill for single-CLI use case) |
| **No CQRS** | event-sourcing.md lines 100-109 | CQRS (read/write ratio insufficient) |
| **Three-Phase Transitions** | workflow-state-machines.md lines 193-246 | Custom validation (reinventing wheel) |

### Validation Against User Stories

| User Story | Research Validation | Implementation Pattern |
|------------|-------------------|------------------------|
| **US1: Event Emission** | event-sourcing.md (append-only log) | JSONL files, daily rotation |
| **US2: State Reading** | event-sourcing.md (inline projections) | Replay events, reconstruct status |
| **US3: SQLite Index** | event-sourcing.md (query optimization) | Background index updates |
| **US4: Conflict Detection** | sync-protocols.md (LWW + Lamport) | `is_concurrent()` from spec-kitty-events |
| **US5: Daily Rotation** | sync-protocols.md (offline buffer) | ISO date filenames |
| **US6: Git Dependency** | constitution ADR-11 | Commit pinning in pyproject.toml |
| **US7: Error Logging** | workflow-state-machines.md (Manus pattern) | Separate JSONL files in .kittify/errors/ |

### Confidence Assessment

**HIGH Confidence** (authoritative sources):
- Event sourcing patterns (Martin Fowler)
- CQRS guidance (Martin Fowler)
- Jira transition model (Atlassian official docs)
- GitHub Actions patterns (GitHub official docs)

**MEDIUM Confidence** (case studies):
- Linear LWW approach (reverse engineering)
- Figma fractional indexing (company blog)
- Postgres JSONL scale (Marten case study)

**Areas Requiring Runtime Validation**:
- Exact event write latency (15ms estimate, needs profiling)
- SQLite index update performance (assumed <5ms, needs measurement)
- File locking behavior on Windows (POSIX locks availability needs testing)

---

## Next Steps (Phase 1)

With research complete, proceed to Phase 1 design:

1. **data-model.md**: Define Event, LamportClock, EventStore, EventIndex entities
2. **contracts/**: Define event schema contracts (EventV1.json schema)
3. **quickstart.md**: Basic usage examples (emit event, read status, query history)
4. **Agent context update**: Update `.claude/commands/` with event log context

---

## References

**Primary Research Documents**:
- event-sourcing.md - 650 lines, 7 sources ([WEB-001] through [WEB-007])
- sync-protocols.md - 439 lines, 9 sources ([WEB-007] through [WEB-015])
- workflow-state-machines.md - 849 lines, 5 sources ([WEB-014] through [WEB-018])

**Authoritative Sources**:
- Martin Fowler - Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
- Martin Fowler - CQRS: https://www.martinfowler.com/bliki/CQRS.html
- Atlassian Jira Workflows: https://support.atlassian.com/jira-cloud-administration/docs/configure-advanced-issue-workflows/
- GitHub Actions Syntax: https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions
- Temporal Workflows: https://docs.temporal.io/workflows

**Case Studies**:
- Linear Sync Engine: https://github.com/wzhudev/reverse-linear-sync-engine
- Figma Multiplayer: https://www.figma.com/blog/how-figmas-multiplayer-technology-works/
- Marten (Postgres JSONB): https://martendb.io/events/
- NeuroChain (Fintech at Scale): Event Sourcing in 2026 blog
