# Implementation Tasks: Glossary Semantic Integrity Runtime for Mission Framework

**Feature**: 041-mission-glossary-semantic-integrity
**Target Branch**: 2.x
**Created**: 2026-02-16
**Status**: Ready for implementation

## Overview

This feature implements a glossary semantic integrity runtime system that enforces semantic consistency in mission execution. The system uses a middleware pipeline to extract terms, resolve against a 4-tier scope hierarchy, detect conflicts, block LLM generation on high-severity issues, and prompt for interactive clarification with checkpoint/resume capability.

**Architecture**: B + D Hybrid (middleware chain + event emission)
**Dependencies**: typer, rich, ruamel.yaml, spec-kitty-events (Feature 007 contracts)
**Testing**: pytest 90%+ coverage, mypy --strict

---

## Work Package Summary

**Total Work Packages**: 11
**Total Subtasks**: 51
**Estimated Timeline**: 8-12 weeks (with parallel execution)

### MVP Scope

**MVP = WP01-WP05** (Foundation through Generation Gate)

Delivers core glossary enforcement:

- Term extraction (metadata hints + heuristics)
- Scope resolution (4-tier hierarchy)
- Conflict detection (4 types)
- Generation gate blocking (strictness modes)

**NOT in MVP**: Interactive clarification UI, checkpoint/resume, CLI commands (defer to WP06-WP11)

---

## Phase 1: Foundation & Infrastructure

### WP01: Foundation & Data Models

**Goal**: Establish package structure, core data models, and test infrastructure.

**Priority**: P1 (blocking for all other WPs)

**Independent Test**: Can create TermSurface, TermSense, SemanticConflict objects and verify serialization.

**Included Subtasks**:

- [x] **T001**: Create glossary package structure (`src/specify_cli/glossary/`)
- [x] **T002**: Define core data models (TermSurface, TermSense, GlossaryScope, SemanticConflict)
- [x] **T003**: Define exception hierarchy (BlockedByConflict, DeferredToAsync, AbortResume)
- [x] **T004**: Set up test infrastructure (fixtures, mocks for PrimitiveExecutionContext)
- [x] **T005**: Implement GlossaryScope enum with resolution order

**Implementation Notes**:

1. Create `src/specify_cli/glossary/__init__.py` with public API exports
2. Define dataclasses in `models.py` using Python 3.11+ features
3. Create exception base class `GlossaryError` with specific subclasses
4. Set up pytest fixtures in `tests/specify_cli/glossary/conftest.py`

**Dependencies**: None (foundational WP)

**Risks**: None (data model definitions are straightforward)

**Estimated Prompt Size**: ~300 lines

---

### WP02: Scope Management & Storage

**Goal**: Implement glossary scope loading, seed file parsing, and in-memory storage backed by event log.

**Priority**: P1 (blocking for WP03-WP05)

**Independent Test**: Can load seed files, activate scopes, query glossary store for terms.

**Included Subtasks**:

- [x] **T006**: Implement seed file loader (YAML parsing for team_domain.yaml, audience_domain.yaml)
- [x] **T007**: Implement scope activation (emit GlossaryScopeActivated events)
- [x] **T008**: Implement glossary store (in-memory cache backed by event log)
- [x] **T009**: Write scope resolution tests (hierarchical lookup)
- [x] **T048**: Create spec_kitty_core.yaml seed file (canonical Spec Kitty terms)

**Implementation Notes**:

1. Seed files live in `.kittify/glossaries/{scope}.yaml`
2. Use ruamel.yaml for parsing (preserve comments, order)
3. Store uses LRU cache for performance (max 10,000 terms)
4. Event log is source of truth for glossary state

**Dependencies**: WP01 (data models)

**Parallel Opportunity**: Can run in parallel with WP03 (different modules)

**Risks**: Seed file schema validation (mitigate: strict YAML schema, fail-fast)

**Estimated Prompt Size**: ~350 lines

---

## Phase 2: Term Extraction

### WP03: Term Extraction Implementation

**Goal**: Implement term extraction using metadata hints + deterministic heuristics, with scope-aware normalization and confidence scoring.

**Priority**: P1 (blocking for WP04)

**Independent Test**: Can extract terms from sample step inputs, verify confidence scores, validate normalization.

**Included Subtasks**:

- [x] **T010**: Implement metadata hints extraction (glossary_watch_terms, aliases, exclude, fields)
- [x] **T011**: Implement deterministic heuristics (quoted phrases, acronyms, casing patterns, repeats)
- [x] **T012**: Implement scope-aware normalization (lowercase, trim, stem-light)
- [x] **T013**: Implement confidence scoring (metadata > pattern > weak heuristic)
- [x] **T014**: Implement GlossaryCandidateExtractionMiddleware
- [x] **T015**: Write extraction tests (unit + integration with mocked context)

**Implementation Notes**:

1. Extraction logic in `extraction.py` (pure functions, no side effects)
2. Heuristic patterns: `r'"([^"]+)"'` (quoted), `r'\b[A-Z]{2,5}\b'` (acronyms), `r'\b[a-z]+_[a-z]+\b'` (snake_case)
3. Stem-light: simple plural→singular (workspaces→workspace), no full stemming
4. Middleware emits TermCandidateObserved for each extracted term

**Dependencies**: WP01 (data models), WP02 (scope definitions)

**Parallel Opportunity**: Can run in parallel with WP02 after WP01 completes

**Risks**: False positives from heuristics (mitigate: confidence scoring, low-confidence terms auto-add as draft)

**Estimated Prompt Size**: ~400 lines

---

## Phase 3: Semantic Check & Conflict Detection

### WP04: Semantic Check & Conflict Detection

**Goal**: Implement term resolution against scope hierarchy, conflict classification, and severity scoring.

**Priority**: P1 (blocking for WP05)

**Independent Test**: Can resolve terms, detect all 4 conflict types, score severity correctly.

**Included Subtasks**:

- [x] **T016**: Implement term resolution against scope hierarchy (mission_local → team_domain → audience_domain → spec_kitty_core)
- [x] **T017**: Implement conflict classification (unknown, ambiguous, inconsistent, unresolved_critical)
- [x] **T018**: Implement severity scoring (step criticality + confidence → low/medium/high)
- [x] **T019**: Implement SemanticCheckMiddleware
- [x] **T020**: Write semantic check tests (all conflict types, severity edge cases)

**Implementation Notes**:

1. Resolution logic in `resolution.py` (hierarchical lookup with fallback)
2. Conflict types: no match (unknown), 2+ matches (ambiguous), contradictory usage (inconsistent), critical + low confidence (unresolved_critical)
3. Severity: high (critical step + low confidence OR ambiguous), medium (non-critical + ambiguous), low (inconsistent OR unknown + high confidence)
4. Middleware emits SemanticCheckEvaluated with findings

**Dependencies**: WP02 (scope store), WP03 (extracted terms)

**Parallel Opportunity**: None (sequential after WP03)

**Risks**: Severity calibration (mitigate: start conservative, tune based on test corpus)

**Estimated Prompt Size**: ~350 lines

---

## Phase 4: Generation Gate

### WP05: Generation Gate & Strictness Policy

**Goal**: Implement generation gate that blocks LLM generation on unresolved high-severity conflicts, with configurable strictness policy.

**Priority**: P1 (MVP blocker)

**Independent Test**: Can block generation in medium/max modes, pass in off mode, respect precedence.

**Included Subtasks**:

- [x] **T021**: Implement StrictnessPolicy (precedence resolution: global → mission → step → runtime)
- [x] **T022**: Implement gate decision logic (off: pass, medium: block high-severity, max: block all)
- [x] **T023**: Implement GenerationGateMiddleware
- [x] **T024**: Write gate tests (strictness modes, blocking behavior, precedence)

**Implementation Notes**:

1. Strictness enum in `strictness.py`: off, medium, max
2. Precedence: runtime override > step metadata > mission config > global default
3. Gate raises BlockedByConflict exception if should block
4. Middleware emits GenerationBlockedBySemanticConflict when blocking

**Dependencies**: WP04 (semantic check)

**Parallel Opportunity**: None (sequential after WP04)

**Risks**: Precedence edge cases (mitigate: exhaustive test matrix)

**Estimated Prompt Size**: ~250 lines

---

## Phase 5: Interactive Clarification

### WP06: Interactive Clarification UI

**Goal**: Implement interactive clarification prompts using Typer + Rich, with ranked candidates and async defer option.

**Priority**: P2 (enhances UX, not blocking MVP)

**Independent Test**: Can render conflicts with Rich, prompt for user input, handle all choices (candidate, custom, defer).

**Included Subtasks**:

- [x] **T025**: Implement conflict rendering with Rich (term, context, ranked candidates by confidence)
- [x] **T026**: Implement Typer prompts (select candidate 1..N, C for custom, D for defer)
- [x] **T027**: Implement non-interactive mode (auto-defer all conflicts)
- [x] **T028**: Implement ClarificationMiddleware
- [x] **T029**: Write clarification tests (interactive mocking, non-interactive mode)

**Implementation Notes**:

1. Rich tables for candidate display (term | scope | definition | confidence)
2. typer.prompt() for choice input with validation
3. Non-interactive detection: `sys.stdin.isatty()` or `CI` env var
4. Middleware emits: GlossaryClarificationRequested (defer), GlossaryClarificationResolved (candidate), GlossarySenseUpdated (custom)

**Dependencies**: WP05 (conflicts exist)

**Parallel Opportunity**: Can run in parallel with WP07 (different concerns)

**Risks**: Terminal rendering issues (mitigate: test in CI, provide plain-text fallback)

**Estimated Prompt Size**: ~350 lines

---

## Phase 6: Checkpoint/Resume

### WP07: Checkpoint/Resume Mechanism

**Goal**: Implement event-sourced checkpoint/resume with input hash verification for cross-session recovery.

**Priority**: P2 (enhances UX, enables async workflow)

**Independent Test**: Can checkpoint before gate, resume after resolution, detect context changes.

**Included Subtasks**:

- [x] **T030**: Implement StepCheckpoint data model (mission/run/step IDs, strictness, scope refs, input hash, cursor, retry token)
- [x] **T031**: Implement checkpoint emission (before generation gate, minimal payload)
- [x] **T032**: Implement checkpoint loading from event log (latest for step_id)
- [x] **T033**: Implement input hash verification (SHA256, detect context changes, prompt for confirmation)
- [x] **T034**: Implement ResumeMiddleware
- [x] **T035**: Write checkpoint/resume tests (happy path, context changed, cross-session)

**Implementation Notes**:

1. Checkpoint emitted as StepCheckpointed event (may need to add to Feature 007 contracts)
2. Input hash: SHA256 of sorted JSON dump of step inputs
3. Resume flow: load checkpoint → verify hash → restore context → resume from cursor
4. typer.confirm() for context change confirmation

**Dependencies**: WP06 (clarification resolution)

**Parallel Opportunity**: Can run in parallel with WP06

**Risks**: StepCheckpointed event not in Feature 007 yet (mitigate: stub adapter, gate on package update)

**Estimated Prompt Size**: ~400 lines

---

## Phase 7: Event Integration

### WP08: Event Integration

**Goal**: Implement event emission adapters that import Feature 007 canonical contracts and emit at middleware boundaries.

**Priority**: P2 (enables replay, audit, SaaS sync)

**Independent Test**: Can emit all 7 canonical events + StepCheckpointed, events serialize correctly, persist to JSONL.

**Included Subtasks**:

- [x] **T036**: Create event emission adapters (import from spec_kitty_events.glossary.events)
- [x] **T037**: Implement event emission at middleware boundaries (extraction → check → gate → clarification → resume)
- [x] **T038**: Implement event log persistence (JSONL via spec-kitty-events)
- [x] **T039**: Write event emission tests (verify payloads, ordering, persistence)

**Implementation Notes**:

1. Events module: `src/specify_cli/glossary/events.py`
2. Import canonical events: GlossaryScopeActivated, TermCandidateObserved, SemanticCheckEvaluated, etc.
3. If StepCheckpointed not in package: stub adapter, document as pending Feature 007
4. Event log path: `.kittify/events/glossary/{mission_id}.events.jsonl`

**Dependencies**: WP01-WP07 (all middleware components)

**Parallel Opportunity**: Can run in parallel with WP09

**Risks**: Feature 007 package not yet published (mitigate: stub adapters, gate implementation)

**Estimated Prompt Size**: ~300 lines

---

## Phase 8: Middleware Pipeline Integration

### WP09: Middleware Pipeline Integration

**Goal**: Integrate middleware pipeline into mission primitive execution, with metadata-driven attachment.

**Priority**: P2 (connects all pieces)

**Independent Test**: Can attach pipeline to primitive, execute full flow (extract → check → gate → clarify → resume), verify events.

**Included Subtasks**:

- [x] **T040**: Implement PrimitiveExecutionContext extension (add glossary fields: extracted_terms, conflicts, strictness)
- [x] **T041**: Implement middleware pipeline composition (GlossaryMiddlewarePipeline class)
- [x] **T042**: Implement middleware attachment to primitives (read glossary_check metadata from mission.yaml)
- [x] **T043**: Write full pipeline integration tests (end-to-end: spec-kitty specify with conflict)

**Implementation Notes**:

1. Context extension: add `extracted_terms`, `conflicts`, `strictness`, `checkpoint` fields
2. Pipeline: ordered list of middleware, execute sequentially, catch BlockedByConflict
3. Attachment: mission primitive base class hook or decorator (depends on 2.x architecture)
4. Metadata: `glossary_check: enabled` in mission.yaml step definitions

**Dependencies**: WP01-WP08 (all components)

**Parallel Opportunity**: None (integrates everything)

**Risks**: Primitive architecture changes in 2.x (mitigate: validate during WP implementation)

**Estimated Prompt Size**: ~300 lines

---

## Phase 9: Glossary Management CLI (Optional)

### WP10: Glossary Management CLI

**Goal**: Provide CLI commands for glossary inspection, conflict viewing, and async resolution.

**Priority**: P3 (nice-to-have, not blocking MVP)

**Independent Test**: Can list terms, view conflicts, resolve conflicts via CLI.

**Included Subtasks**:

- [x] **T044**: Implement `spec-kitty glossary list --scope <scope>` command (table output with Rich)
- [x] **T045**: Implement `spec-kitty glossary conflicts --mission <mission>` command (conflict history)
- [x] **T046**: Implement `spec-kitty glossary resolve <conflict_id>` command (async resolution)
- [x] **T047**: Write CLI command tests (mocked event log, Rich output verification)

**Implementation Notes**:

1. Commands in `src/specify_cli/cli/commands/glossary.py`
2. Use Typer @app decorators
3. Rich tables for output formatting
4. Read from event log (no separate state)

**Dependencies**: WP08 (events), WP09 (pipeline)

**Parallel Opportunity**: Can run in parallel with WP11

**Risks**: None (CLI commands are isolated)

**Estimated Prompt Size**: ~250 lines

---

## Phase 10: Polish & Documentation

### WP11: Type Safety & Integration Tests

**Goal**: Ensure mypy --strict compliance, write comprehensive integration tests, update user docs.

**Priority**: P3 (quality gate before release)

**Independent Test**: mypy passes with no errors, pytest coverage >90%, quickstart examples work.

**Included Subtasks**:

- [x] **T049**: Update type annotations (mypy --strict compliance for all glossary modules)
- [x] **T050**: Write integration tests (end-to-end workflows: specify with conflict, clarify, resume)
- [x] **T051**: Update user documentation (quickstart examples, troubleshooting guide)

**Implementation Notes**:

1. Add type stubs for any untyped dependencies
2. Use pytest-cov for coverage reporting
3. Integration tests: simulate full mission runs with conflicts
4. Update `quickstart.md` with real-world examples

**Dependencies**: WP01-WP10 (all code complete)

**Parallel Opportunity**: None (final validation)

**Risks**: None (polish work)

**Estimated Prompt Size**: ~250 lines

---

## Dependency Graph

```
WP01 (Foundation)
  ├─> WP02 (Scope Management)
  │     ├─> WP03 (Term Extraction)
  │     │     └─> WP04 (Semantic Check)
  │     │           └─> WP05 (Generation Gate) [MVP END]
  │     │                 ├─> WP06 (Clarification) [P]
  │     │                 └─> WP07 (Checkpoint) [P]
  │     │                       └─> WP08 (Events)
  │     │                             └─> WP09 (Pipeline)
  │     │                                   ├─> WP10 (CLI) [P]
  │     │                                   └─> WP11 (Polish)
```

**[P] = Parallel opportunities**

---

## Parallelization Strategy

**Wave 1** (after WP01):

- WP02 (Scope Management)
- WP03 (Term Extraction) - can start after WP01

**Wave 2** (after WP05):

- WP06 (Clarification)
- WP07 (Checkpoint) - can run in parallel

**Wave 3** (after WP09):

- WP10 (CLI)
- WP11 (Polish) - must wait for all code

**Maximum parallelization**: 2-3 agents simultaneously (Waves 1-2)

---

## Risk Matrix

| WP | Risk | Severity | Mitigation |
|----|------|----------|------------|
| WP01 | None | - | Data models are straightforward |
| WP02 | Seed file schema validation | Low | Strict YAML schema, fail-fast |
| WP03 | False positives from heuristics | Medium | Confidence scoring, draft terms |
| WP04 | Severity calibration | Medium | Start conservative, tune with corpus |
| WP05 | Precedence edge cases | Low | Exhaustive test matrix |
| WP06 | Terminal rendering issues | Low | Test in CI, plain-text fallback |
| WP07 | StepCheckpointed not in Feature 007 | Medium | Stub adapter, gate on package |
| WP08 | Feature 007 package not published | High | Stub adapters, defer integration |
| WP09 | Primitive architecture unknown | High | Validate during implementation |
| WP10 | None | - | CLI commands isolated |
| WP11 | Coverage gaps | Low | Run pytest-cov, fill gaps |

---

## Acceptance Criteria (from spec.md)

**AC-001**: `medium` strictness warns broadly and blocks only unresolved high severity
**AC-002**: `off` mode allows mission execution without glossary enforcement
**AC-003**: Step metadata can enable glossary checks for any custom primitive
**AC-004**: Replay reproduces glossary evolution and generation gate outcomes

All acceptance criteria are covered across WP01-WP11.

---

## Next Steps

**MVP Implementation**:

```bash
spec-kitty implement WP01  # Foundation (no dependencies)
spec-kitty implement WP02 --base WP01  # Scope Management
spec-kitty implement WP03 --base WP01  # Term Extraction (parallel with WP02)
spec-kitty implement WP04 --base WP03  # Semantic Check
spec-kitty implement WP05 --base WP04  # Generation Gate [MVP COMPLETE]
```

**Full Feature**:

```bash
# After MVP:
spec-kitty implement WP06 --base WP05  # Clarification (parallel with WP07)
spec-kitty implement WP07 --base WP05  # Checkpoint (parallel with WP06)
spec-kitty implement WP08 --base WP07  # Events
spec-kitty implement WP09 --base WP08  # Pipeline
spec-kitty implement WP10 --base WP09  # CLI (parallel with WP11)
spec-kitty implement WP11 --base WP09  # Polish
```

---

## Estimated Timeline

**With 1 agent (sequential)**: 11-15 weeks
**With 2 agents (parallel)**: 8-10 weeks
**With 3 agents (max parallel)**: 6-8 weeks

**MVP only (WP01-WP05)**: 4-6 weeks (1 agent), 3-4 weeks (2 agents)
