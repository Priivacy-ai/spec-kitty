# Research: Mid-Stream Change Command

**Feature**: `029-mid-stream-change-command`  
**Date**: 2026-02-09  
**Status**: Complete

## Overview

This research resolves the high-impact planning unknowns for `/spec-kitty.change` after clarification updates.

## Decisions

### Decision 1: Complexity scoring is deterministic

**Decision**: Use a fixed weighted rubric with explicit thresholds (`simple`, `complex`, `high`).

**Rationale**:
- User explicitly required deterministic behavior.
- Deterministic scoring enables stable tests and predictable command outcomes.

**Alternatives considered**:
- AI-only freeform scoring: rejected due to inconsistent outputs.
- Line-count threshold: rejected because it does not reflect structural complexity.

### Decision 2: Main stash is embedded in planning root

**Decision**: Use `kitty-specs/change-stack/main/` for main-branch change work.

**Rationale**:
- User requested embedded main stash storage, not a pseudo-feature directory.
- Keeps main small-fix changes directly visible in planning root structure.

**Alternatives considered**:
- `kitty-specs/000-main-change-stash/`: rejected as feature-style indirection.

### Decision 3: Change generation is append-only

**Decision**: Generate new change WPs and dependencies; do not rewrite existing WP task bodies.

**Rationale**:
- Better auditability and review traceability.
- Reduces accidental loss of prior implementation context.

**Alternatives considered**:
- In-place rewrite of open WPs: rejected due to history and conflict risks.

### Decision 4: Ambiguous requests fail fast

**Decision**: If target scope is unclear, stop and ask for clarification before creating WPs.

**Rationale**:
- Prevents mis-scoped change work and downstream rework.
- Aligns with clarified user requirement.

**Alternatives considered**:
- Silent inference: rejected as unsafe for review-driven changes.
- Placeholder WP creation: rejected as noise that delays real progress.

### Decision 5: Closed/done references are link-only

**Decision**: Create new change WPs linked to closed/done WPs as historical context; never auto-reopen closed/done WPs.

**Rationale**:
- Preserves workflow integrity and audit history.
- Allows corrections without mutating completed records.

**Alternatives considered**:
- Auto-reopen closed WPs: rejected due to state churn and review confusion.

### Decision 6: Stack-first execution with blocker stop

**Decision**: Implement selection uses this order:
1) any ready change WP,
2) if pending change WPs exist but none are ready, stop and report blockers,
3) only when change stack is empty, continue normal planned WPs.

**Rationale**:
- Enforces review-change priority while still allowing ready change items to progress.

**Alternatives considered**:
- Skip to normal WPs when earliest change WP is blocked: rejected by clarified behavior.

### Decision 7: Cross-type dependencies are allowed

**Decision**: Change WPs may depend on normal open WPs where ordering requires.

**Rationale**:
- Reflects real ordering constraints in in-flight implementation.
- Avoids forced duplication of prerequisite work.

**Alternatives considered**:
- Change-only dependency graph: rejected because it can violate true execution order.

### Decision 8: Access model is contributor-level

**Decision**: Any repository contributor may invoke `/spec-kitty.change`.

**Rationale**:
- Matches clarified operating model and supports review responsiveness.

**Alternatives considered**:
- Maintainer-only or assignee-only: rejected as unnecessary bottlenecks.

### Decision 9: Merge coordination is heuristic-triggered

**Decision**: Create merge coordination jobs only when deterministic risk heuristics detect cross-stream conflict risk.

**Rationale**:
- Meets requirement without adding mandatory overhead to every change.

**Alternatives considered**:
- Always create merge coordination jobs: rejected as unnecessary process load.
- Never create merge coordination jobs: rejected because it ignores explicit requirement.

## Resolved Unknowns

- Main stash location and shape: resolved.
- Ambiguous-input handling policy: resolved.
- Closed WP behavior: resolved.
- Stack-first selection behavior with blockers: resolved.
- Dependency policy between change and normal WPs: resolved.
- Access scope for command invocation: resolved.

No open clarifications remain.

---

**END OF RESEARCH**
