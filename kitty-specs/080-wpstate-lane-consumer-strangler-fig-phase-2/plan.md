# Implementation Plan: WPState/Lane Consumer Strangler Fig Migration — Phase 2 (Amended)

**Mission**: 080-wpstate-lane-consumer-strangler-fig-phase-2  
**Branch**: `main` | **Date**: 2026-04-09 (Amended) | **Spec**: [spec.md](spec.md)

---

## Summary

Migrate 7 verified WP lane consumers from raw lane-string comparisons toward typed lane semantics using the Strangler Fig pattern. Introduce two new interfaces (`WPState.is_run_affecting`, `AgentAssignment`, `WPMetadata.resolved_agent()`), then sequentially replace consumers in 4 independently-mergeable slices while maintaining strict backward compatibility. Each slice completes with tests passing and leaves `main` in a releasable state.

**Scope Amendment**: Trimmed from 15 consumers to 7 verified lane-string leaks via Path A. Removed broadened consumers without validated lane-string issues. Fixed slice dependencies (AgentAssignment introduced before workflow migration). Corrected is_terminal/approved conflation (merge validation preserved separately).

---

## Branch Contract (CONFIRMED)

- **Current branch**: main
- **Planning base**: main
- **Merge target**: main
- **Status**: ✓ branch_matches_target = true

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)  
**Primary Dependencies**: pytest, mypy, ruamel.yaml, rich, typer (existing)  
**Testing**: pytest with 90%+ coverage; mypy --strict enforcement  
**Constraints**: Backward compatibility required; sequential slicing  
**Scale/Scope**: 7 verified consumer files, 4 slices, 7 work packages, 2 new interfaces

**Key Dependencies on Existing Code**:
- WPState.is_terminal already exists; only is_run_affecting is new
- AgentAssignment and WPMetadata.resolved_agent() are new
- Lane enum and status module are authoritative
- All 7 consumers currently use raw lane-string logic; all need migration

---

## Charter Check: ✅ PASSED

**Governance Compliance**:
- ✓ Type safety: mypy --strict enforced (WPState.is_run_affecting, AgentAssignment, WPMetadata)
- ✓ Test coverage: 90%+ for new code
- ✓ Integration tests: Required for Slice 2 (workflow) and Slice 4 (merge)
- ✓ Decision documentation: This plan captures scope amendment + rationale

**Scope Decisions Documented**:
- Why trim to 7 consumers: Only these 7 have verified lane-string leaks in discovery
- Why exclude dashboard/scanner.py: Requires separate design to preserve approved/for_review distinction
- Why exclude tasks.py: Already uses typed Lane enums; not a lane-string consumer
- Why exclude others: Not validated as lane-string leaks; follow-up scope

---

## 7 Verified Consumers

1. `src/specify_cli/agent_utils/status.py` — Display/kanban (Slice 1)
2. `src/specify_cli/next/runtime_bridge.py` — Runtime routing (Slice 2)
3. `src/specify_cli/cli/commands/agent/workflow.py` — Agent resolution (Slice 2)
4. `src/specify_cli/review/arbiter.py` — Review arbiter (Slice 3)
5. `src/specify_cli/scripts/tasks/tasks_cli.py` — Task scripts (Slice 3)
6. `src/specify_cli/cli/commands/merge.py` — Merge validation (Slice 4)
7. `src/specify_cli/lanes/recovery.py` — Recovery mode (Slice 4)

---

## Phase 0: Research (Minimal)

All critical decisions resolved in discovery and specification amendment.

**Pre-Phase-1 Verification**:
1. Confirm WPState.is_terminal already exists (no WP01 needed for intro)
2. Verify 7-consumer list is exhaustive for lane-string leaks (grep check)
3. Document AgentAssignment fallback order

**Output**: Checklist (no separate research.md; spec is complete)

---

## Phase 1: Design & Contracts (Updated)

### 1.1 Data Model

**WPState (NEW addition)**
- `is_run_affecting` property: True for planned/claimed/in_progress/for_review/in_review/approved; False for done/blocked/canceled

**AgentAssignment (NEW value object)**
- Frozen dataclass: tool, model, profile_id (Optional), role (Optional)
- Represents resolved agent assignment

**WPMetadata (NEW method)**
- `resolved_agent()` → AgentAssignment with legacy coercion + fallback

### 1.2 Consumer Migration Contracts

See `contracts/consumer-interfaces.md` (updated for 7 consumers only):
- Slice 1: progress_bucket() bucketing instead of manual
- Slice 2: is_run_affecting for routing; resolved_agent() for workflow
- Slice 3: typed Lane enum for arbiter + tasks
- Slice 4: merge validation (approved|done distinct from is_terminal); typed lane boundaries for recovery

### 1.3 Quickstart

Developer guide with before/after patterns for all 7 consumers (updated).

---

## Implementation Strategy: 4 Sequential Slices

### Slice 1: Status Display (1 consumer, 1 WP)

**Consumer**: `agent_utils/status.py`

**Changes**:
- Delegate to existing `state.progress_bucket()` instead of manual lane bucketing
- Preserve display semantics (no regressions)

**Backward Compat**: Old progress_bucket() still works; unchanged API

**Testing**: Regression tests for kanban output; all existing tests pass

---

### Slice 2: Runtime Routing & Agent Resolution (2 consumers, 2 WPs)

**Consumers**: `next/runtime_bridge.py`, `cli/commands/agent/workflow.py`

**Changes**:
- Introduce AgentAssignment, WPMetadata.resolved_agent() (WP02)
- runtime_bridge.py: Replace lane tuple checks with `state.is_run_affecting`
- workflow.py: Use `WPMetadata.resolved_agent()` for agent assignment; remove Lane.IN_PROGRESS → "doing" round-trip

**Backward Compat**: State methods provide same information as old tuple checks; resolved_agent() unifies legacy coercion

**Testing**: Behavior tests for is_run_affecting; integration tests for workflow CLI; regression tests for routing

**Critical**: AgentAssignment MUST be introduced in WP02 (before WP03) so workflow can use it

---

### Slice 3: Review & Tasks (2 consumers, 1 WP)

**Consumers**: `review/arbiter.py`, `scripts/tasks/tasks_cli.py`

**Changes**:
- Replace raw string/enum comparisons with typed Lane access via WPState
- Use state for lane queries instead of hardcoded lane sets

**Backward Compat**: Lane enum values unchanged; state wraps them safely

**Testing**: Behavior tests for arbiter logic; regression tests for task script output

---

### Slice 4: Merge Validation & Recovery (2 consumers, 1 WP)

**Consumers**: `cli/commands/merge.py`, `lanes/recovery.py`

**Changes**:
- merge.py: Preserve approved|done distinction explicitly (NOT delegated to is_terminal); use typed Lane enum
- recovery.py: Use transition validation from status module instead of hardcoded tuples

**Backward Compat**: Merge behavior unchanged; recovery transitions preserved

**Testing**: Behavior tests for gate validation; integration tests for merge command; regression tests for recovery

**Critical Clarification**: is_terminal (done|canceled) ≠ merge-ready (approved|done). This is NOT conflated in the implementation.

---

## Work Packages (7 total)

```
WP01: Introduce WPState.is_run_affecting property
      - Add to src/specify_cli/status/wp_state.py
      - Behavior tests: all 9 lanes
      - Verify is_terminal already exists (no new work)
      - Status: Design + tests only

WP02: Introduce AgentAssignment, WPMetadata.resolved_agent()
      - Add AgentAssignment dataclass to src/specify_cli/status/models.py
      - Add resolved_agent() method to WPMetadata
      - Behavior tests: string/dict/None inputs + fallback scenarios
      - Status: Design + tests; enables Slice 2 consumer migrations

WP03: Migrate Slice 1 consumer (agent_utils/status.py)
      - Use state.progress_bucket() instead of manual bucketing
      - Regression tests for kanban output
      - Status: Single file, high-confidence migration

WP04: Migrate Slice 2 consumers (runtime_bridge.py, workflow.py)
      - runtime_bridge.py: Use state.is_run_affecting
      - workflow.py: Use WPMetadata.resolved_agent(); remove Lane.IN_PROGRESS → "doing"
      - Integration tests for workflow CLI
      - Status: Two files; workflow depends on WP02

WP05: Migrate Slice 3 consumers (arbiter.py, tasks_cli.py)
      - Replace raw lane comparisons with typed Lane enum via state
      - Regression tests for both consumers
      - Status: Two files, tightly scoped

WP06: Migrate Slice 4 consumers (merge.py, recovery.py)
      - merge.py: Preserve approved|done distinction; use typed Lane enum
      - recovery.py: Use transition validation from status module
      - Integration tests for merge command; regression tests for recovery
      - Status: Two files; merge validation especially critical

WP07: Final cleanup & verification
      - Verify no remaining lane-string comparisons in 7 consumers (grep pass)
      - mypy --strict: all code passes
      - Run full test suite: all integration + unit tests pass
      - Status: Verification and sign-off
```

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| merge.py regression (approved/done handling) | Explicit Lane enum check; NOT delegated to is_terminal; careful testing |
| Slice dependencies broken | AgentAssignment in WP02 (before WP04); no other cross-slice dependencies |
| is_terminal/approved confusion | Documented clearly: is_terminal for cleanup logic only; merge uses explicit check |
| Backward compat breaks | Each slice leaves main releasable; full test suite after each |
| Type safety regression | mypy --strict enforced; CI blocks merges if fails |

---

## Planning Answers (Locked In)

| # | Question | Answer |
|---|----------|--------|
| P1 | Slice Sequencing | Strictly sequential, independently mergeable |
| P2 | Testing Strategy | Hybrid: behavior tests + focused regression; snapshot-optional |
| P3 | Compatibility Window | Until final slice, then cleanup in WP07 |

---

## Success Criteria

1. ✓ Lane semantics fully encapsulated (no raw lane-string comparisons in 7 consumers)
2. ✓ All 7 verified consumers migrated in 4 independent slices
3. ✓ 90%+ test coverage for WPState.is_run_affecting, AgentAssignment, WPMetadata.resolved_agent()
4. ✓ mypy --strict passes on all new code
5. ✓ All existing tests pass after each slice + final cutover
6. ✓ Merge validation (approved|done distinction) preserved and tested
7. ✓ Grep pass: no raw lane-string comparisons remain in 7 consumer files

---

## Scope Amendment Summary

**Original Plan**: 15 consumers, 6 slices, 9 WPs, 3 new interfaces (is_run_affecting, is_terminal, AgentAssignment)

**Amended Plan** (Path A): 7 consumers, 4 slices, 7 WPs, 2 new interfaces (is_run_affecting, AgentAssignment)

**Changes**:
- Removed 8 broadened consumers without validated lane-string issues
- Removed FR-002 (is_terminal already exists)
- Reordered: AgentAssignment now in WP02 (before workflow migration in WP04)
- Fixed: is_terminal ≠ merge-ready (preserved explicit approved|done check)
- Fixed: dashboard/scanner.py excluded (requires separate column semantics design)
- Added explicit constraints for merge validation and slice dependencies

---

## Artifacts Generated (Phase 1)

| Artifact | Location | Status |
|----------|----------|--------|
| plan.md | kitty-specs/080-wpstate-lane-consumer-strangler-fig-phase-2/plan.md | ✓ Updated (this document) |
| data-model.md | kitty-specs/080-wpstate-lane-consumer-strangler-fig-phase-2/data-model.md | → To be updated |
| contracts/consumer-interfaces.md | kitty-specs/080-wpstate-lane-consumer-strangler-fig-phase-2/contracts/consumer-interfaces.md | → To be updated |
| quickstart.md | kitty-specs/080-wpstate-lane-consumer-strangler-fig-phase-2/quickstart.md | → To be updated |
| spec.md | kitty-specs/080-wpstate-lane-consumer-strangler-fig-phase-2/spec.md | ✓ Amended |

---

## ⛔ STOP POINT: AMENDED PLAN READY

**Phase 1 complete for amended 7-consumer scope.**

### Next Steps

1. User reviews amended plan (this document)
2. If acceptable: I update data-model.md, contracts/, quickstart.md to match 7-consumer scope
3. Commit all amendments to git
4. User runs `/spec-kitty.tasks` to generate 7 work packages

### Do NOT

❌ Create tasks.md  
❌ Create work package files  
❌ Proceed to implementation  

**Confirm plan acceptable before I update supporting artifacts.**

---

## Change Log

- **2026-04-09 (Initial)**: Full plan for 15 consumers, 6 slices, 9 WPs
- **2026-04-09 (Amendment)**: Trimmed to 7 verified consumers, 4 slices, 7 WPs. Fixed scope creep, slice dependencies, and is_terminal/approved conflation.
