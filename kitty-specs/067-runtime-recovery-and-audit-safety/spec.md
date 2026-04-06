# Runtime Recovery And Audit Safety

**Mission**: 067-runtime-recovery-and-audit-safety
**Priority**: P1 stabilization
**Type**: software-dev
**Target branch**: main
**Validated against**: commit 1b01760e (2026-04-06)

## Feature Overview

Spec Kitty's runtime currently cannot survive interruption gracefully, routes canonical workflows through a misapplied generic abstraction, lacks support for codebase-wide audit work, and misreports mission progress. This mission makes the runtime recoverable, removes the wrong shim abstraction, enables realistic audit and bulk-edit workflows, and ensures every operator-facing surface tells the truth about mission progress.

## Background & Motivation

### Problem Statement

Five categories of stabilization debt remain on `main` after the prior review-loop tranche:

1. **Merge fragility**: `spec-kitty merge` is non-idempotent. If interrupted mid-operation, it leaves incomplete cleanup with no supported recovery path. Operators must guess at manual Git state repair.

2. **Implementation crash exposure**: When the implementation phase crashes (process kill, network drop, OOM), existing branches and worktrees survive but Spec Kitty's state does not. There is no supported way to reconcile or resume — only manual Git escape hatches.

3. **Wrong abstraction for canonical commands**: The generic `agent shim` runtime resolves WP context before dispatching, which blocks non-WP commands (like `accept`) behind unnecessary context resolution. The `accept` action has shim support but is rejected by the canonical action resolver, creating an inconsistent dead path.

4. **No audit-mode or bulk-edit safety**: Audit and cutover work packages need to operate across the entire codebase, but the current WP ownership model forces fake narrow scope. Template and documentation directories are invisible to audit validation. Bulk rename/cutover edits have no guardrail for distinguishing string occurrence categories (identifiers vs. prose vs. comments), leading to silent breakage.

5. **Dishonest progress reporting**: The CLI dashboard and downstream sync surfaces compute progress as `done / total`. Work packages that are `claimed`, `in_progress`, `for_review`, or `approved` contribute 0% — operators see 0% progress even when most WPs are nearly complete.

### Scope

**In scope** (8 issues):

| # | Issue | Summary |
|---|-------|---------|
| 1 | [#416](https://github.com/Priivacy-ai/spec-kitty/issues/416) | Merge is non-idempotent; leaves incomplete cleanup after interruption |
| 2 | [#415](https://github.com/Priivacy-ai/spec-kitty/issues/415) | No crash recovery for the implementation phase |
| 3 | [#414](https://github.com/Priivacy-ai/spec-kitty/issues/414) | `accept` action not registered in context resolver despite shim support |
| 4 | [#412](https://github.com/Priivacy-ai/spec-kitty/issues/412) | Generic agent shim runtime should be replaced with direct canonical commands |
| 5 | [#442](https://github.com/Priivacy-ai/spec-kitty/issues/442) | No codebase-wide audit WP mode; template/doc coverage missing from validation |
| 6 | [#447](https://github.com/Priivacy-ai/spec-kitty/issues/447) | Completion percentage only counts WPs in `done` |
| 7 | [#443](https://github.com/Priivacy-ai/spec-kitty/issues/443) | Duplicate/smaller framing of progress bug; consolidated into #447 |
| 8 | [#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) | No guardrail for distinguishing string occurrence categories in bulk edits |

**Explicitly not in scope**:

- [#401](https://github.com/Priivacy-ai/spec-kitty/issues/401) — Revalidated as stale; current emitter already writes top-level `from_lane`/`to_lane`
- Review-loop issues from the prior tranche: #430, #432, #433, #439, #440, #441, #444

## Actors

| Actor | Description |
|-------|-------------|
| Operator | Human developer or CI system running `spec-kitty` CLI commands |
| Agent | AI coding agent (Claude, Codex, Gemini, etc.) executing WP workflows via slash commands |
| Reviewer | Human or agent performing review and acceptance of completed WPs |
| Auditor | Agent or human conducting codebase-wide audit/cutover work |

## User Scenarios & Testing

### Scenario 1: Merge Recovery After Interruption

**Actor**: Operator
**Trigger**: `spec-kitty merge` is interrupted by process kill, network failure, or Ctrl-C during a multi-WP merge sequence.
**Flow**: Operator reruns `spec-kitty merge` (or `spec-kitty merge --resume`). The system detects the partial state, identifies which WPs completed and which did not, and resumes from the last incomplete WP without requiring manual Git cleanup.
**Success**: All WPs eventually merge successfully. No duplicate status events are emitted for already-completed WPs. State is consistent.

### Scenario 2: Implementation Crash and Reconciliation

**Actor**: Agent
**Trigger**: Agent process dies during `spec-kitty implement WP03`. The Git branch and worktree exist, but Spec Kitty's internal state (lane transitions, workspace tracking) is inconsistent.
**Flow**: Operator or agent runs a recovery/reconciliation command. The system detects existing branches and worktrees, reconciles them with the expected state, and allows implementation to continue without starting over.
**Success**: The WP resumes from its last consistent state. No work is lost. No manual `git worktree` commands needed.

### Scenario 3: Direct Canonical Command Execution

**Actor**: Agent
**Trigger**: Agent invokes a slash command (e.g., `/spec-kitty.accept`) or CLI command that was previously routed through the generic `agent shim` runtime.
**Flow**: The command executes directly against the canonical command surface without intermediate WP context resolution that would block non-WP-scoped commands.
**Success**: `accept` and all other canonical actions resolve and execute consistently. No "action not registered" errors for actions that have shim support.

### Scenario 4: Codebase-Wide Audit Work Package

**Actor**: Auditor
**Trigger**: A mission includes a WP whose job is repo-wide leak detection, terminology audit, or template coverage validation.
**Flow**: The auditor defines an audit-scoped WP that operates across the entire codebase. Validation explicitly checks command template directories and documentation files. Template/doc coverage gaps produce warnings or errors.
**Success**: The audit WP runs without being forced into fake narrow file ownership. All template and doc directories are surfaced as audit targets.

### Scenario 5: Bulk Rename with Occurrence Classification

**Actor**: Agent performing terminology cutover
**Trigger**: A cutover WP requires renaming a term across the codebase.
**Flow**: Before bulk edits proceed, the system requires classification of each occurrence category (identifier, prose, comment, path, configuration). After edits, a verification step confirms no unintended changes leaked across categories.
**Success**: Identifiers are renamed correctly. Prose mentions are updated appropriately. No silent breakage in paths, configs, or unrelated string matches.

### Scenario 6: Truthful Progress Dashboard

**Actor**: Operator
**Trigger**: Operator runs `spec-kitty status` or views the dashboard during an active mission where 3 of 5 WPs are `for_review` and 1 is `in_progress`.
**Flow**: The progress display shows a percentage reflecting the weighted contribution of all in-flight states, not just `done`.
**Success**: Progress shows a meaningful non-zero percentage (e.g., ~70%) rather than 0% because no WP has reached `done` yet.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The merge operation shall detect and recover from partial completion state when rerun after interruption | Proposed |
| FR-002 | The merge operation shall track per-WP completion state persistently so that completed WPs are not re-merged on retry | Proposed |
| FR-003 | The merge operation shall guard against duplicate status events on retry by checking for existing event_ids before emitting transitions for already-completed WPs | Proposed |
| FR-004 | The implementation workflow shall provide a reconciliation command that detects existing branches and worktrees and aligns internal state with filesystem reality | Proposed |
| FR-005 | Implementation recovery shall allow continuation of a WP from its last consistent state without requiring the operator to manually repair Git state | Proposed |
| FR-006 | Generated CLI-driven command files shall invoke canonical commands directly, without routing through a generic shim runtime | Proposed |
| FR-007 | The `accept` action shall be registered in the action resolver and shall execute successfully when invoked | Proposed |
| FR-008 | All canonical actions that have shim support shall have corresponding entries in the action resolver | Proposed |
| FR-009 | Audit-scoped work packages shall be definable with codebase-wide ownership rather than narrow file-set ownership | Proposed |
| FR-010 | Audit validation shall explicitly include command template directories and documentation files as coverage targets | Proposed |
| FR-011 | Bulk rename/cutover workflows shall require occurrence classification before edits proceed | Proposed |
| FR-012 | Bulk rename/cutover workflows shall include a post-edit verification step that confirms no unintended cross-category changes | Proposed |
| FR-013 | A single canonical progress formula shall be used across CLI, dashboard, and downstream sync surfaces | Proposed |
| FR-014 | The progress formula shall assign weighted contributions to `claimed`, `in_progress`, `for_review`, and `approved` states, not only `done` | Proposed |
| FR-015 | Issue #443 shall be closed or cross-linked as consolidated into #447 when the progress fix ships | Proposed |
| FR-016 | Audit validation shall produce warnings or errors when command templates or documentation have coverage gaps relative to the audit scope | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Merge recovery shall complete within 2x the wall-clock time of a clean merge for the same WP set | ≤ 2x clean merge time | Proposed |
| NFR-002 | Implementation reconciliation shall detect and report stale state within 5 seconds for a feature with up to 20 WPs | ≤ 5 seconds | Proposed |
| NFR-003 | Progress computation shall produce identical results across CLI, dashboard, and sync surfaces for the same event log input | 100% consistency | Proposed |
| NFR-004 | Occurrence classification output shall be human-reviewable (structured, not opaque) | Structured categories visible to operator | Proposed |
| NFR-005 | New code shall maintain 90%+ test coverage | ≥ 90% line coverage | Proposed |
| NFR-006 | All new code shall pass strict type checking with no errors | 0 type errors | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Merge recovery must work with the existing event-log-based status model (Phase 2); no regression to frontmatter-based state | Confirmed |
| C-002 | Implementation recovery must operate through Spec Kitty's workflow commands, not require manual Git-only escape hatches | Confirmed |
| C-003 | The shim removal must preserve compatibility with all 12 supported AI agents' command file formats | Confirmed |
| C-004 | Audit-mode changes must not break the existing narrow-ownership WP model for non-audit work packages | Confirmed |
| C-005 | Progress formula changes must not break existing SaaS sync or downstream API consumers | Confirmed |
| C-006 | Issue #401 is excluded — the current emitter already handles `from_lane`/`to_lane` correctly | Confirmed |
| C-007 | Review-loop issues from the prior tranche (#430, #432, #433, #439, #440, #441, #444) are excluded | Confirmed |

## Success Criteria

1. An operator whose merge was interrupted at WP03 of 5 can rerun the merge command and have it complete WP03–WP05 without manual Git intervention, achieving full merge in one additional invocation.
2. An agent whose implementation session crashed can invoke a recovery command and resume coding on the same WP within 30 seconds, with no lost commits.
3. Every slash command across all 12 agent surfaces executes its canonical action directly — no command routes through a generic shim runtime for dispatch.
4. An auditor can define and execute a WP that scans the entire repository, including all command template and documentation directories, without fabricating narrow file ownership.
5. A mission with 5 WPs where 3 are `for_review` and 1 is `in_progress` shows progress of approximately 60–75% (not 0%) across all operator-facing surfaces.
6. A bulk rename of a term produces a structured classification report before any files are modified, and a verification report afterward confirming category-correct changes.

## Suggested Work Package Decomposition

| WP | Title | Issues | Summary |
|----|-------|--------|---------|
| WP01 | Merge interruption and recovery | #416 | Make merge idempotent or resumable; prevent half-written state |
| WP02 | Implementation crash recovery | #415 | Reconcile existing branches/worktrees after interruption |
| WP03 | Canonical execution surface cleanup | #412, #414 | Remove generic shim runtime; register `accept` in action resolver |
| WP04 | Audit-mode and bulk-edit safety | #442, #393 | Codebase-wide WP scope; occurrence classification for bulk edits. **Planning note**: contains two distinct concerns (audit scope relaxation vs. occurrence classification workflow) — consider splitting during `/spec-kitty.plan` |
| WP05 | Canonical progress reporting | #447, #443 | Single weighted progress formula across all surfaces |

### Suggested Execution Order

Based on risk, dependency, and operator impact analysis:

1. **WP05 first** — lowest risk, highest operator impact; the weighted progress module already exists and is tested; this is a callsite-replacement task
2. **WP03 + WP01 in parallel** — independent of each other; WP03 is a shim removal + migration, WP01 is merge state extension
3. **WP02 next** — builds on understanding from WP01's merge state work; can reference recovery patterns established there
4. **WP04 last** — hardest WP, benefits from all prior stabilization being in place

## Dependencies

| Dependency | Impact |
|------------|--------|
| Existing merge state model (`MergeState`, mission-scoped at `.kittify/runtime/merge/<mission_id>/state.json`) | WP01 extends this; must understand current mission-scoped persistence format |
| Event-log status model (Phase 2) | WP01 and WP05 interact with event log; must not regress |
| Agent directory configuration (`get_agent_dirs_for_project`) | WP03 must generate direct command files for all configured agents |
| Lane/worktree resolution | WP02 must reconcile against existing lane-based worktree paths |

## Assumptions

1. The existing `MergeState` persistence model (mission-scoped at `.kittify/runtime/merge/<mission_id>/state.json`) is the right foundation for merge recovery (extend, not replace).
2. Implementation recovery targets the lane-based worktree model (2.x+); legacy per-WP worktrees are not a recovery target.
3. After shim removal, `accept` becomes a direct canonical command (like `implement` and `review`), invoked directly rather than through shim dispatch.
4. Weighted progress values for intermediate lanes are a design decision for planning phase (not specified here).
5. Occurrence classification is a workflow step (prompt/template guidance + structured output), not a fully automated NLP classifier.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Merge recovery introduces new race conditions in concurrent agent scenarios | Medium | High | Test with simulated interruption at each WP boundary; ensure atomic state transitions |
| Merge retry emits duplicate status events for already-completed WPs | High | Medium | FR-003 requires event_id dedup check before emitting; JSONL is line-atomic so partial writes are unlikely, but duplicates on retry are the real risk |
| Removing the shim runtime breaks agent command files that depend on shim-resolved context | Low | High | C-003 requires 12-agent compatibility; test at least claude, codex, opencode |
| Weighted progress formula disagreements across surfaces if formula is not truly shared | Medium | Medium | FR-013 mandates single formula; test all three surfaces against same input |
| Audit-mode WPs create overly broad blast radius for changes | Low | Medium | Audit scope is read-only validation + classification; actual edits still require per-file review |

## Issue Hygiene

- Each in-scope issue shall be updated with current-main root cause findings during implementation.
- #401 is explicitly documented as revalidated-stale and excluded.
- #443 shall be closed or cross-linked as consolidated into #447 when the progress fix implementation fully subsumes it.
- This mission shall not silently widen into long-horizon redesign work (JSON-canonical planning, doctrine architecture).

## Verification Expectations

- Targeted tests for interrupted merge/retry or merge recovery behavior
- Tests for recovery/reconciliation of existing implementation branches/worktrees
- Tests proving generated command surfaces use direct canonical commands after shim cleanup
- Tests covering `accept` action resolution consistency
- Tests for audit-mode validation behavior around template/doc coverage and codebase-wide scope
- Tests for occurrence classification or equivalent guardrail enforcement in bulk-edit workflows
- Tests for shared weighted-progress calculation across CLI/dashboard surfaces

## Definition of Done

This mission is done when Spec Kitty can survive interruption better, stop routing canonical workflows through the wrong shim abstraction, support realistic audit/cutover work, and report mission progress truthfully across its operator-facing surfaces.
