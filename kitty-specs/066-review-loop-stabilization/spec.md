# Review Loop Stabilization

**Mission**: 066-review-loop-stabilization
**Priority**: P1 stabilization
**Mission Type**: software-dev
**Target Branch**: main
**Created**: 2026-04-06

## Problem Statement

The implement/review loop in Spec Kitty is operationally unreliable. After tranche 1 (#449) stabilized the planning/tasks control plane, the remaining friction is execution ergonomics in the review cycle:

- **Rejection waste**: When a WP is rejected, the system regenerates the full 400-500 line implement prompt instead of producing a focused fix prompt that centers the delta. This burns tokens, confuses the implementing agent, and slows iteration.
- **Ephemeral feedback**: Review feedback is written to `.git/spec-kitty/feedback/` — a git-internal location that is not committed, not versioned, and not visible across clones or sessions. Feedback is effectively disposable state.
- **Broken external handoff**: External reviewers have no writable in-repo feedback path. The review handoff commands block on any dirty file in the worktree or feature directory, with `--force` as the only escape (which disables all validation). There is no middle ground that classifies dirtiness by ownership and relevance.
- **False review churn**: Reviewers cannot distinguish pre-existing test failures from newly introduced regressions because review prompts lack baseline context. Concurrent review agents sharing a worktree collide on shared test databases.
- **Ad hoc arbiter decisions**: When an arbiter must override a false-positive rejection, there is no structured rationale model — every override is freeform operator judgment.

## Motivation

Fix these six friction points and the multi-agent sprint loop becomes materially faster (focused fix prompts instead of full re-sends), cheaper (fewer wasted tokens per rejection cycle), and more trustworthy (reviewers can separate signal from noise, arbiters leave auditable rationale).

## Scope

### In Scope

| Issue | Summary |
|-------|---------|
| [#430](https://github.com/Priivacy-ai/spec-kitty/issues/430) | Generate focused fix-mode prompts on rejection cycles |
| [#432](https://github.com/Priivacy-ai/spec-kitty/issues/432) | Persist review feedback as versioned sub-artifacts |
| [#433](https://github.com/Priivacy-ai/spec-kitty/issues/433) | Link fix-mode prompt generation to persisted review sub-artifacts |
| [#439](https://github.com/Priivacy-ai/spec-kitty/issues/439) | Make review handoff self-contained for external reviewers |
| [#440](https://github.com/Priivacy-ai/spec-kitty/issues/440) | Concurrent review agents sharing a worktree collide on test databases |
| [#441](https://github.com/Priivacy-ai/spec-kitty/issues/441) | Add structured arbiter checklist for false-positive review rejections |
| [#444](https://github.com/Priivacy-ai/spec-kitty/issues/444) | Include baseline test results in review prompts |

### Out of Scope

Explicitly excluded — do not widen into these areas:

- [#406](https://github.com/Priivacy-ai/spec-kitty/issues/406), [#417](https://github.com/Priivacy-ai/spec-kitty/issues/417), [#422](https://github.com/Priivacy-ai/spec-kitty/issues/422), [#423](https://github.com/Priivacy-ai/spec-kitty/issues/423) — planning/finalization (tranche 1)
- [#438](https://github.com/Priivacy-ai/spec-kitty/issues/438), [#434](https://github.com/Priivacy-ai/spec-kitty/issues/434), [#443](https://github.com/Priivacy-ai/spec-kitty/issues/443), [#442](https://github.com/Priivacy-ai/spec-kitty/issues/442) — operator/dashboard and audit-mode work
- [#241](https://github.com/Priivacy-ai/spec-kitty/issues/241) — broader architectural work

If implementation reveals a missing prerequisite, file a follow-on issue instead of silently widening scope.

## Actors

| Actor | Description |
|-------|-------------|
| Implementing agent | AI coding agent that receives WP prompts and produces code changes |
| Review agent | AI or human agent that evaluates WP output against acceptance criteria |
| External reviewer | Human reviewer outside the orchestrator who receives handoff context |
| Arbiter | Operator or senior reviewer who resolves disputes on false-positive rejections |
| Orchestrator | The spec-kitty runtime that coordinates the implement/review loop |

## User Scenarios & Testing

### Scenario 1: Focused rejection recovery

**Given** WP02 has been rejected with specific findings (3 affected files, 2 test failures, 1 style issue)
**When** the orchestrator generates the next prompt for the implementing agent
**Then** the prompt contains only the review findings, affected file paths with line ranges, requested corrections, and reproduction commands — not the full original WP implement prompt
**And** the prompt size is proportional to the review findings, not the original WP scope

### Scenario 2: Review feedback persists across sessions

**Given** a reviewer rejects WP03 with detailed feedback
**When** the orchestrator persists the feedback
**Then** a versioned artifact `review-cycle-1.md` is created at `kitty-specs/<feature>/tasks/WP03-slug/review-cycle-1.md`
**And** the artifact has machine-parseable frontmatter including `affected_files` (with paths and line ranges), `cycle_number`, `reviewer_agent`, and `verdict`
**And** a second rejection creates `review-cycle-2.md` with incremented cycle number
**And** the artifacts are committed to the repo and visible across clones

### Scenario 3: External reviewer completes reject-with-feedback

**Given** a human external reviewer receives a review handoff for WP04
**When** the reviewer writes feedback to the designated in-repo path
**Then** the feedback is stored as a versioned review-cycle artifact (same format as agent feedback)
**And** the review handoff does not block due to unrelated dirty files (status artifacts, other WPs' task files, generated metadata)
**And** only files owned by the current WP and uncommitted source changes in the worktree are treated as blocking

### Scenario 4: Reviewer distinguishes regressions from pre-existing failures

**Given** the project has 3 pre-existing test failures on the base branch
**When** a review agent evaluates WP05 output
**Then** the review prompt includes baseline test results showing which failures existed before this WP
**And** the reviewer can identify that 2 of the 3 failures are pre-existing and 1 is newly introduced
**And** only newly introduced failures are flagged as WP regressions

### Scenario 5: Concurrent review agents do not collide

**Given** two review agents are reviewing WP03 and WP04 in the same worktree
**When** both agents attempt to run tests
**Then** either the system provides isolated execution environments (separate test DB instances) or explicitly blocks the second review with a clear message explaining that concurrent review in the same worktree is not supported

### Scenario 6: Arbiter uses structured checklist

**Given** a reviewer rejects WP06 and the implementing agent disputes the finding
**When** the arbiter evaluates the dispute
**Then** the arbiter selects from a standard rationale model (pre-existing failure, wrong-context review, cross-scope finding, infra/environmental issue, or custom with explanation)
**And** the structured rationale is persisted in the review history alongside the override decision

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The system shall generate a focused fix-mode prompt when a WP is rejected, containing only review findings, affected file paths with line ranges, requested corrections, and reproduction commands | Proposed |
| FR-002 | Fix-mode prompts shall reference the persisted review-cycle artifact by path so the implementing agent can read the full feedback | Proposed |
| FR-003 | Review feedback shall be persisted as versioned markdown artifacts at `kitty-specs/<feature>/tasks/<WP-slug>/review-cycle-{N}.md` | Proposed |
| FR-004 | Review-cycle artifacts shall include machine-parseable YAML frontmatter with fields: `affected_files` (paths and line ranges), `cycle_number`, `reviewer_agent`, `verdict`, and `reviewed_at` timestamp | Proposed |
| FR-005 | Each rejection cycle shall increment the cycle number and create a new artifact (append-only, no overwriting) | Proposed |
| FR-006 | Review-cycle artifacts shall be committed to the repository so they survive across sessions and clones | Proposed |
| FR-007 | The fix-mode prompt generator shall read from the latest persisted review-cycle artifact to construct the fix prompt | Proposed |
| FR-008 | External reviewers shall have a writable in-repo feedback path that follows the same review-cycle artifact format | Proposed |
| FR-009 | The review handoff validation shall classify dirty files as blocking or benign based on path patterns and WP ownership | Proposed |
| FR-010 | Blocking dirty files: uncommitted changes to files owned by the current WP (source files in the worktree, the WP's own task file) | Proposed |
| FR-011 | Benign dirty files: status artifacts (status.events.jsonl, status.json), other WPs' task files, generated metadata — these shall not block review handoff | Proposed |
| FR-012 | Review prompts shall include baseline test results from the base branch to enable distinguishing pre-existing failures from newly introduced regressions | Proposed |
| FR-013 | The system shall either provide isolated test execution for concurrent review agents or explicitly serialize/block concurrent reviews in the same worktree with a clear explanation | Proposed |
| FR-014 | Arbiter override decisions shall use a structured rationale model with standard categories: pre-existing failure, wrong-context review, cross-scope finding, infra/environmental issue, and custom (with mandatory explanation) | Proposed |
| FR-015 | Arbiter rationale and override decisions shall be persisted in the review history and visible in subsequent review-cycle artifacts | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Fix-mode prompts shall be proportional to review findings, not original WP scope | Fix prompt size < 25% of original implement prompt size for single-file findings | Proposed |
| NFR-002 | Review-cycle artifact creation shall not block the rejection workflow | Artifact write + commit completes within 5 seconds | Proposed |
| NFR-003 | Dirty-state classification shall complete without user-visible delay | Classification of up to 100 dirty paths completes within 1 second | Proposed |
| NFR-004 | Baseline test result capture shall not add significant overhead to review setup | Baseline capture completes within 30 seconds for projects with up to 500 tests | Proposed |
| NFR-005 | All new review artifacts shall be human-readable without special tooling | Artifacts are plain markdown with YAML frontmatter, viewable in any text editor or GitHub UI | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Review-cycle artifacts must live inside `kitty-specs/<feature>/tasks/` — not in `.git/` or other git-internal locations | Proposed |
| C-002 | The dirty-state classification must partition `git status --porcelain` output by path pattern and WP ownership — not use a flag that disables all checks | Proposed |
| C-003 | The existing `--force` flag behavior (skip all validation) must be preserved as an escape hatch but must not be the recommended path for benign dirtiness | Proposed |
| C-004 | Concurrent review isolation must not require changes to the project's test infrastructure — the solution must work at the orchestrator/worktree level | Proposed |
| C-005 | Arbiter rationale categories must be extensible (new categories can be added) but the initial set must include the four standard categories | Proposed |

## Work Package Decomposition

| WP | Name | Issues | Depends On | Description |
|----|------|--------|------------|-------------|
| WP01 | Persisted review artifact model | #432, storage side of #433 | — | Define the review-cycle artifact schema, storage location, versioning model, and read/write operations. Move feedback persistence from `.git/spec-kitty/feedback/` to committed `kitty-specs/` artifacts. |
| WP02 | Focused rejection recovery | #430 | WP01 | Generate fix-mode prompts from persisted review-cycle artifacts. The prompt generator reads the structured frontmatter (affected files, line ranges, verdict) to produce focused fix instructions. |
| WP03 | Wire fix-mode to persisted artifacts | Integration side of #433 | WP01, WP02 | Thin integration layer ensuring the end-to-end path — rejection, persisted feedback, focused fix prompt — works as a single coherent flow. |
| WP04 | External reviewer handoff | #439 | — | Implement dirty-state classification (blocking vs. benign by path pattern and WP ownership). Provide writable in-repo feedback path for external reviewers. |
| WP05 | Review correctness under real execution | #444, #440 | — | Add baseline test result capture to review prompts. Implement concurrent review isolation or explicit serialization/blocking. |
| WP06 | Arbiter ergonomics | #441 | — | Add structured arbiter checklist with standard rationale categories. Persist arbiter decisions in review history. |

**Execution ordering**: WP01 -> WP02 -> WP03 (strict chain). WP04, WP05, WP06 are independent of this chain and can execute in parallel with each other and with WP02/WP03.

## Dependencies & Assumptions

### Dependencies

- Tranche 1 (#449) planning/tasks control plane repair is merged and stable
- The status model (event-log authority, phase 2) is operational
- `kitty-specs/<feature>/tasks/` directory structure exists from task finalization

### Assumptions

- The current `_persist_review_feedback()` in tasks.py writing to `.git/spec-kitty/feedback/` can be replaced without backward compatibility — no external consumers depend on that location
- Review-cycle artifact frontmatter schema can be defined fresh — there is no existing schema to migrate from
- Baseline test results can be captured by running the test suite on the base branch or reading cached CI results
- The arbiter rationale categories (pre-existing failure, wrong-context review, cross-scope finding, infra/environmental issue) cover the majority of false-positive rejection scenarios observed in practice

## Success Criteria

1. A rejected WP produces a focused fix prompt that is proportional to the review findings — operators observe prompt sizes reduced by 75%+ for single-file findings compared to full WP re-sends
2. Review feedback survives across sessions, clones, and agent restarts because it is committed to the repository as versioned artifacts
3. External reviewers can complete the reject-with-feedback flow using only in-repo paths without orchestrator file babysitting
4. Review handoff commands succeed without `--force` when only benign status/metadata files are dirty
5. Reviewers correctly classify 90%+ of test failures as pre-existing vs. newly introduced because baseline context is present in review prompts
6. Concurrent review attempts either succeed safely or fail with a clear, actionable message — no silent data corruption or mysterious test failures
7. Arbiter override decisions are auditable — every override has a structured rationale visible in the review history

## Issue Hygiene

- Update each in-scope issue with concrete root cause and implementation notes as work proceeds
- If #430, #432, and #433 collapse into one implementation spine, keep the issue boundaries clear in comments and closing notes
- If any WP reveals a missing prerequisite, file a follow-on issue instead of widening scope

## Definition of Done

This mission is complete when a real reject/revise/re-review loop can be run with external reviewers using repo-local feedback artifacts, focused fix prompts, baseline-aware review context, and materially less orchestrator intervention than today.
