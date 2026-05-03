# Mission Specification: Implement Review Retrospect Reliability

**Mission Slug**: `implement-review-retrospect-reliability-01KQQSCW`  
**Mission ID**: `01KQQSCWP7HAJRR93F98AESKH4`  
**Mission Type**: `software-dev`  
**Created**: 2026-05-03  
**Target Branch**: `main`  
**Status**: Draft validated for planning

## Overview

Spec Kitty agents rely on the implement-review-retrospect loop to decide what work to do next, preserve rejection feedback, and close completed missions with useful learning capture. The current 3.2.0 stabilization work has exposed several high-risk workflow bugs that can send agents to the wrong action, lose or misresolve rejection context, persist invalid review artifacts, or make completed-mission retrospectives impossible through the CLI.

This mission defines a focused reliability pass over the highest-risk control-loop bugs. It prioritizes reviewer rejection from `in_review`, canonical review feedback pointers, schema-valid review-cycle artifacts, `spec-kitty next` routing after finalized tasks, and first-class retrospective behavior for completed missions. Broader release hygiene and unrelated historical issues are explicitly out of scope.

## User Scenarios and Testing

### Primary Scenario: Reviewer Rejects a Work Package and the Agent Fixes It

A reviewer or orchestrator reviews a WP currently in `in_review`, rejects it through the normal `agent tasks move-task` surface with a feedback file, and expects Spec Kitty to persist a valid review-cycle artifact, move the WP into the correct fixable state, and guide the implementing agent back to the focused rejection context. The agent then uses fix-mode to load the persisted pointer, addresses the feedback, and returns the WP for approval without manual status repair.

**Acceptance Criteria**

1. Given a WP in `in_review`, when the reviewer rejects it with `--review-feedback-file`, then Spec Kitty records a rejected review result or fails before changing mission state.
2. Given a rejected review result is recorded, when the feedback pointer is persisted, then the pointer uses the canonical `review-cycle://<mission>/<wp-task-file-slug>/review-cycle-N.md` form.
3. Given fix-mode starts for the rejected WP, when it reads the persisted pointer, then it loads the intended focused rejection context without requiring manual path reconstruction.

### Secondary Scenario: Review Artifacts Are Valid Before They Become State

A review command writes `review-cycle-N.md` and publishes a pointer to that artifact in status or routing data. The command must ensure the artifact has required YAML frontmatter before any later command is expected to resolve it.

**Acceptance Criteria**

1. Given a review-cycle artifact is created, when it is written by Spec Kitty, then it includes frontmatter for mission identity, WP id, review cycle number, verdict, created timestamp, and artifact or feedback identity.
2. Given frontmatter validation fails, when the command would otherwise persist a pointer, then it fails closed and does not leave a dangling pointer behind.

### Secondary Scenario: Next Action Follows Finalized Work Package State

An agent asks `spec-kitty next` after tasks are finalized. The mission phase artifact may still contain stale early-phase state, but the task board and WP lanes reflect implementation progress.

**Acceptance Criteria**

1. Given tasks and WPs are finalized, when `spec-kitty next` runs, then task board and WP lane state determine whether the next action is implement, review, merge, completion, or a clear blocked state.
2. Given the mission phase artifact still says discovery or another earlier phase, when finalized task/WP state exists, then `spec-kitty next` does not route the agent back to discovery solely because of that stale phase.

### Secondary Scenario: Completed Mission Retrospective Can Be Captured

A completed mission lacks a preexisting retrospective record. An operator runs `spec-kitty agent retrospect` commands and expects a structured result rather than a bare missing-record error.

**Acceptance Criteria**

1. Given a completed mission has no `retrospective.yaml`, when retrospective synthesis or capture is requested, then Spec Kitty either initializes the missing record from available artifacts or returns an actionable command path to initialize it.
2. Given JSON output is requested, when the retrospective command completes or fails, then the output is parseable and distinguishes record-created, synthesized, insufficient-artifacts, and mission-not-found outcomes.

### Focused Smoke Scenario

A temporary mission fixture proves the loop end to end: finalized tasks exist, a WP enters review, the reviewer rejects with a feedback file, the review-cycle artifact and pointer are valid, fix-mode loads the pointer, the WP is approved or completed, `spec-kitty next` routes from task/WP state, and retrospective behavior is available for the completed mission.

## Requirements

### Functional Requirements

| ID | Status | Requirement |
| --- | --- | --- |
| FR-001 | Confirmed | #960: Reviewers or orchestrators MUST be able to reject a WP in `in_review` through the normal `agent tasks move-task` surface. |
| FR-002 | Confirmed | #960: When rejection uses `--review-feedback-file`, Spec Kitty MUST derive or supply a structured rejected review result, or fail before writing partial mission state. |
| FR-003 | Confirmed | #962: Persisted rejection feedback references MUST use canonical `review-cycle://<mission>/<wp-task-file-slug>/review-cycle-N.md` URIs. |
| FR-004 | Confirmed | #962: Legacy or accidental `feedback://` references MUST be normalized before persistence or resolved at read time with a deprecation warning. |
| FR-005 | Confirmed | #962: Fix-mode MUST load the intended focused rejection context from the persisted canonical pointer. |
| FR-006 | Confirmed | #963: Every `review-cycle-N.md` artifact written by Spec Kitty MUST include YAML frontmatter with mission identity, WP id, review cycle number, verdict, created timestamp, and artifact or feedback identity. |
| FR-007 | Confirmed | #963: Review artifact writes MUST validate required frontmatter before persisting status references, and MUST fail closed without dangling pointers when validation fails. |
| FR-008 | Confirmed | #961: Once tasks and WPs are finalized, `spec-kitty next` MUST route from task board and WP lane state instead of stale mission discovery-phase state. |
| FR-009 | Confirmed | #965: Completed missions MUST have a first-class `spec-kitty agent retrospect` path when `retrospective.yaml` does not already exist. |
| FR-010 | Confirmed | #965: Retrospective JSON output MUST distinguish retrospective record created, retrospective synthesized, insufficient mission artifacts, and mission not found. |
| FR-011 | Confirmed | The spec MUST document whether #967, #966, #964, and #968 are included or explicitly deferred, with a reason and follow-up issue reference. |

### Non-Functional Requirements

| ID | Status | Requirement |
| --- | --- | --- |
| NFR-001 | Confirmed | Each core issue #960, #962, #963, #961, and #965 MUST have at least one targeted regression test before mission acceptance. |
| NFR-002 | Confirmed | The focused CLI smoke path MUST cover reject, pointer validation, fix-mode context load, approval or completion, next routing, and retrospective behavior in one temporary mission fixture. |
| NFR-003 | Confirmed | All JSON-producing paths added or changed by this mission MUST emit parseable JSON for success and documented failure outcomes in 100% of regression cases. |
| NFR-004 | Confirmed | Review artifact validation MUST reject missing required frontmatter fields in 100% of targeted validation cases. |
| NFR-005 | Confirmed | Local fixture tests that explicitly disable SaaS sync MUST state why hosted sync is out of scope for that test. |
| NFR-006 | Confirmed | Any verification path that touches hosted auth, tracker, SaaS sync, or sync finalization on this computer MUST be run with the explicit sync environment requested for that run. |

### Constraints

| ID | Status | Constraint |
| --- | --- | --- |
| C-001 | Confirmed | Do not duplicate PR #959 scope unless the relevant fix is absent from the current base branch. |
| C-002 | Confirmed | Do not take on broad 3.2.0 release hygiene issues such as #662, #825, #595, #740, or #644. |
| C-003 | Confirmed | Do not redesign the entire mission runtime or replace the event log. |
| C-004 | Confirmed | Do not make #967 a broad concurrency or test-runner rewrite unless a small, proven root cause is found. |
| C-005 | Confirmed | Treat #966, #964, and #968 as lower-priority cleanup unless naturally adjacent to the core changes. |
| C-006 | Confirmed | Do not schedule #303 or #317 without a current reproduction. |
| C-007 | Confirmed | Mission work MUST preserve canonical product terminology: Mission/Missions, not Feature/Features, for active user-facing systems. |

## Included and Deferred Issue Scope

| Issue | Decision | Reason |
| --- | --- | --- |
| #960 | Included | Core rejection transition bug; directly blocks normal reviewer workflow. |
| #962 | Included | Core pointer canonicalization bug; directly affects fix-mode context resolution. |
| #963 | Included | Core review artifact validity bug; invalid artifacts make later routing and review state unreliable. |
| #961 | Included | Core next-action routing bug; can send agents to discovery after task finalization. |
| #965 | Included | Core retrospective capture bug; completed missions need a first-class CLI path. |
| #967 | Deferred unless bounded root cause is found | Status test hangs are secondary unless a small, proven timeout or isolation fix is discovered. Follow-up remains #967. |
| #966 | Deferred unless naturally adjacent | Progress headline consistency is a papercut compared with control-loop correctness. Follow-up remains #966. |
| #964 | Deferred unless naturally adjacent | Skill frontmatter validation may be included only if the same artifact/frontmatter validation path can be reused without broadening scope. Follow-up remains #964. |
| #968 | Deferred unless naturally adjacent | Retired-checklist cleanup should remain separate unless command or skill registry test changes expose a small adjacent cleanup. Follow-up remains #968. |

## Key Entities

| Entity | Description |
| --- | --- |
| Mission | A Spec Kitty work container with lifecycle artifacts, task board state, and retrospective state. |
| Work Package | A task-board unit that moves through planned, doing, review, rejected/fix, and done-style lanes. |
| Review Cycle Artifact | A `review-cycle-N.md` record containing verdict, feedback, and required frontmatter for one WP review cycle. |
| Feedback Pointer | A canonical URI that lets commands resolve the review-cycle artifact for focused fix-mode context. |
| Retrospective Record | The captured or synthesized completed-mission learning record used by retrospective commands. |
| Task Board State | The finalized tasks and WP lane state that should guide implement-review routing. |

## Domain Language

| Canonical Term | Meaning | Avoid |
| --- | --- | --- |
| Mission | The active Spec Kitty unit of work. | Feature in active user-facing language. |
| Work Package or WP | A parallelizable unit of mission work tracked in the task board. | Moving task files between lane folders. |
| Review Cycle Artifact | The persisted markdown artifact for a review verdict and feedback. | Unstructured feedback note. |
| Feedback Pointer | The persisted resolvable URI for review feedback. | Raw filesystem path as canonical state. |
| Retrospective Capture | First-class creation or initialization of completed-mission retrospective state. | Manual precreation of `retrospective.yaml`. |

## Assumptions

1. The current base branch is `main`; `git log` shows PR #959 (`Release 3.2.0 workflow reliability`) is present on this branch, so planning should avoid duplicating that merged scope unless a relevant fix is still absent.
2. The normal reviewer surface is `spec-kitty agent tasks move-task`; lower-level status repair is not acceptable as the primary user path.
3. The mission can use local fixture tests for most regression coverage; hosted sync is only in scope when a verification path explicitly touches hosted auth, tracker, SaaS sync, or sync finalization.
4. #968 is a retired-checklist cleanup issue and is lower priority than the core implement-review-retrospect reliability bugs.

## Edge Cases

1. A review feedback file exists but cannot be converted into a structured rejected review result.
2. A command writes a review artifact successfully but validation fails before pointer persistence.
3. Existing state contains a legacy `feedback://` pointer that fix-mode must still resolve.
4. Mission phase state says discovery while finalized WPs already exist.
5. A completed mission has insufficient artifacts to initialize a retrospective record.
6. A mission selector is invalid or ambiguous when retrospective JSON output is requested.

## Success Criteria

| ID | Metric | Target |
| --- | --- | --- |
| SC-001 | Core bug coverage | #960, #962, #963, #961, and #965 each have at least one targeted regression test. |
| SC-002 | Rejection workflow reliability | 100% of targeted `in_review` rejection tests either complete with structured rejected state or fail before mutation with an actionable diagnostic. |
| SC-003 | Pointer reliability | 100% of persisted rejection feedback pointers in targeted tests are canonical `review-cycle://` URIs or are normalized/resolved with a deprecation warning. |
| SC-004 | Artifact validity | 100% of review-cycle artifacts written in targeted tests include required frontmatter before being referenced. |
| SC-005 | Next routing correctness | The finalized-task fixture routes to implement, review, merge, completion, or blocked state and never to discovery because of stale phase state. |
| SC-006 | Retrospective usability | Completed-mission retrospective JSON tests return one of the documented structured outcomes without a bare `record_not_found` failure. |

## Verification Requirements

At minimum, the implementation mission must require targeted tests for:

- `agent tasks move-task` rejection from `in_review` with `--review-feedback-file`.
- Review-cycle artifact schema and frontmatter validation.
- Canonical `review-cycle://` pointer persistence and resolver behavior.
- Fix-mode loading the focused rejection context from the canonical pointer.
- `spec-kitty next` routing after task finalization.
- Completed-mission retrospective capture, initialization, or synthesis when `retrospective.yaml` is missing.

The focused command-line smoke path must:

1. Create or load a temporary mission fixture with finalized tasks.
2. Move a WP into review.
3. Reject it with a review feedback file.
4. Verify the artifact frontmatter and canonical pointer.
5. Verify fix-mode can load that pointer.
6. Approve or complete the WP.
7. Verify `spec-kitty next` routes from task/WP state.
8. Verify `agent retrospect` has a first-class path on the completed mission.

For this run, the operator explicitly requested this mission be run with `SPEC_KITTY_ENABLE_SAAS_SYNC=0`. Any later verification path that deliberately tests hosted auth, tracker, SaaS sync, or sync finalization must call out the environment choice and rationale.
