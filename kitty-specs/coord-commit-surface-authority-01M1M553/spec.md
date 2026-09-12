# Mission Specification: Coord Commit-Surface Authority

**Mission Branch**: `fix/coord-commit-surface-authority`
**Created**: 2026-09-03
**Status**: Draft
**Input**: Unify which branch/worktree is the authoritative commit surface for coord-topology missions across create-time (`mission create`), `spec-commit`, and the three task commands (`move-task` / `mark-status` / `map-requirements`). Seeds: #2533, #2300, #2739-B16-clause-2. Parent epic: #2160. Target milestone: 3.2.7.

## Context & Problem Statement

On a **coord-topology** mission, mission artifacts are partitioned between a **primary** surface (stable planning: spec / plan / WP outlines) and a **coordination** surface (lifecycle state: status, notes, trace, issue-matrix, `move-task`). Three independent layers decide *where a named path commits and how that outcome is reported*, and today they do not agree:

1. **Create-time** (`core/mission_creation.py`): a PR-bound mission started on an unprotected feature branch via `--start-branch` is still assigned `topology: coord` plus a coordination branch, even though `spec-commit` will then commit everything directly to the feature branch. The coordination worktree is stranded empty at the pre-mission primary tip, and a later `spec-commit` warns "materialized but carries no mission dir" and falls back to the primary checkout — a latent split-brain status surface. (#2533)
2. **Runtime placement** (`coordination/commit_router` + coord worktree materialization): concurrently-active on-`main` coord missions are suspected to cross-contaminate — `spec-commit` reports a `placement_ref` coordination branch that lacks the committed path and holds a *different* mission's commits. **Unconfirmed** since the July 2026 dogfooding note; must be reproduced before a fix is scoped. (#2739-B16-clause-2)
3. **Command reporting** (`tasks_transition_core.py` + the three command wrappers): under coord + protected-primary, `move-task` **skips the primary commit and exits 0**, while `mark-status` and `map-requirements` **refuse and exit 1**. Three commands, one condition, divergent observable behavior. (#2300)

The shared root is the absence of a single, stated **authoritative-surface rule** that all three layers consult. This mission establishes that rule and reconciles the three layers to it.

This is a **research-first** mission: the load-bearing design decision and the unconfirmed defect are settled in the research phase before any fix WP is sliced.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create-time topology matches the real commit surface (Priority: P1)

A mission operator creates a PR-bound mission from the primary branch using `--start-branch fix/my-work`. They expect the mission's commit surface to be internally consistent: wherever `spec-commit` lands artifacts is the surface the mission's status is read from.

**Why this priority**: This is the reproducible data-integrity defect users hit today (#2533); it produces a split-brain status surface and a stranded, confusing coordination worktree on the most common PR-bound flow.

**Independent Test**: Create a PR-bound `--start-branch` mission; assert the resulting topology and any coordination worktree are consistent with where `spec-commit` actually commits — no "materialized but carries no mission dir" fallback warning, no coordination branch stranded at the pre-mission primary tip.

**Acceptance Scenarios**:

1. **Given** a repo on the primary branch, **When** an operator runs `mission create --pr-bound --start-branch fix/x`, **Then** the mission's authoritative commit surface is unambiguous and `spec-commit` of a planning artifact commits there without a primary-fallback warning.
2. **Given** the mission created above, **When** the operator inspects `git worktree list`, **Then** there is no coordination worktree stranded empty at the pre-mission primary tip.
3. **Given** the mission created above, **When** status is materialized, **Then** it is read from the same surface the artifacts were committed to (no split-brain).

### User Story 2 - Concurrent coord missions never cross-contaminate (DROPPED — superseded by #2533)

**DROPPED (research D-002, 2026-09-03).** Reproduction disproved the premise: coord worktree/branch are strictly per-mission keyed (`slug+mid8`), no write is misrouted, no false success. The "cross-contamination appearance" is a stranded-coord-branch labelling artifact whose root cause is #2533 (redundant coord topology). Absorbed into User Story 1 / WP-A (which asserts a `--pr-bound --start-branch <unprotected>` mission mints no coord branch, closing the appearance by construction). No standalone work.

### User Story 3 - The three task commands agree under coord + protected-primary (Priority: P1)

An operator on a coord-topology mission with a protected primary runs `move-task`, `mark-status`, and `map-requirements`. They expect the same class of situation (a change that cannot commit to the protected primary) to produce the *same* observable behavior across all three commands.

**Why this priority**: The divergence (skip-exit-0 vs refuse-exit-1) makes scripts and operators unable to reason about outcomes; it is a P1 consistency defect deferred out of the #2116 degod because reconciling it is a deliberate behavior change.

**Independent Test**: Freeze today's per-command behavior in a golden characterization harness, then land the unified rule as an enumerated, reviewed delta re-frozen in the same change; assert all three commands share one decision path (`tasks_transition_core.py`) and one observable outcome.

**Acceptance Scenarios**:

1. **Given** a coord + protected-primary mission, **When** any of `move-task` / `mark-status` / `map-requirements` cannot commit to the protected primary, **Then** all three produce the same exit code and the same commit/skip behavior per the unified rule.
2. **Given** the unified rule, **When** the decision is exercised, **Then** it is computed once in the shared pure core and the three wrappers consume it (no per-command re-derivation).

### Edge Cases

- A mission created `--pr-bound` on an *already*-unprotected branch (no `--start-branch`) — does it get coord topology, and is that consistent?
- A flattened mission (`coordination_branch` key removed from `meta.json`) — the primary checkout is authoritative; all three layers must honor the flatten.
- `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1` set — the "cannot commit to protected primary" precondition disappears; the unified rule must degrade correctly.
- A genuine no-op (nothing to commit / already committed) must remain distinguishable from a wrong-surface refusal (`no_op_already_committed` / `no_op_no_changes` vs `no_op_wrong_surface`), preserving the contract shipped in #2739.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Author the authoritative-surface rule | As a maintainer, I want one stated rule mapping `{topology × protected-primary × start-branch}` to the authoritative commit surface, so create-time, spec-commit, and the task commands can all consult a single source of truth. | High | Open |
| FR-002 | Decide the kind-aware non-committable verdict | As a maintainer, I want one rule that, given `{artifact_kind, topology, primary_protected}`, yields the verdict — RouteToCoord (coord-kind, exit 0), Refuse+remedy (planning-kind on protected primary, exit 1), or typed NoOp (exit 0) — so commands share the rule (not necessarily an exit code) and no requested write is silently dropped or misrouted. | High | Open |
| FR-003 | Reproduce or disprove B16-clause-2 | As a maintainer, I want the concurrent-coord cross-contamination defect either reproduced with a red-first test or documented as non-reproducing on the current build, so scope is grounded in evidence. | High | Open |
| FR-004 | Create-time topology honors start-branch | As an operator, I want `mission create --pr-bound --start-branch` to produce a topology whose coordination surface (if any) is consistent with where `spec-commit` actually commits — no stranded empty coord worktree, no primary-fallback split-brain. | High | Open |
| FR-005 | Unify the commit-bearing task commands on the shared rule | As an operator, I want `move-task` (lifecycle-kind) and `map-requirements` (planning-kind) to consult the same authoritative-surface helper via their shell helpers, and `mark-status` frozen as event-log-only (no commit, per #2816), so the divergence is one shared rule not three hardcoded arms. Verified by characterize-then-diff (JSON-mode exit codes). | High | Open |
| FR-006 | ~~Fix concurrent-coord placement~~ | **DROPPED** — B16-c2 disproven (research D-002); root cause folds into #2533 / FR-004. Kept for traceability. | — | Dropped |
| FR-007 | Preserve the shipped no-op reason contract | As an operator, I want genuine no-ops to stay distinguishable from wrong-surface refusals, so the machine-readable `reason` contract from #2739 is not regressed. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior-change traceability | Every observable change to an exit code or commit behavior is frozen in a golden characterization test before and after the change; the diff between them is enumerated in the PR. Zero un-characterized behavior changes. | Reliability | High | Open |
| NFR-002 | No silent false success | 100% of "cannot land" paths return a non-zero exit or a machine-readable non-success result; no path reports `success` for a write that did not land on the reported ref. | Correctness | High | Open |
| NFR-003 | Quality gates clean | All changed source files pass `ruff` and `mypy` with zero issues and zero new suppressions; new branches/helpers carry focused tests in the same PR (Sonar new-code coverage). | Maintainability | High | Open |
| NFR-004 | No regression of shipped #2739 contract | The full existing spec-commit / commit-router / coordination test surface stays green (baseline: the 4,862 shared-surface tests referenced by PR #3851). | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Reuse the extracted pure core | The task-command unification must build on the existing `tasks_transition_core.py` extracted by the #2116 degod; do not reintroduce per-command decision logic. | Technical | High | Open |
| C-002 | Canonical seams only | Reconciliation must go through the canonical placement/commit seams (`commit_router`, `commit_for_mission`, `resolve_workspace_for_wp`); no improvised branch/worktree manipulation. | Technical | High | Open |
| C-003 | Characterize-then-diff for behavior changes | Behavior changes (#2300 especially) must follow characterize-then-intentionally-diff: freeze current divergence, then land the unified rule as a reviewed, re-frozen delta. | Process | High | Open |
| C-004 | Research gates fix scope | No fix WP for B16-clause-2 is opened until WP0 reproduces it; if it does not reproduce, the finding is documented and the WP is dropped. | Process | High | Open |
| C-005 | PRs only | Changes land via a PR branch; the operator merges. No direct push to origin/main. | Process | High | Open |

### Key Entities

- **Authoritative commit surface**: the branch/worktree that owns a mission's commits for a given artifact kind, resolved from `{topology, protected-primary, start-branch}`. The single concept this mission makes explicit and consistent.
- **Coord topology**: a mission mode that partitions artifacts between a primary and a coordination surface; minted at create-time and recorded in `meta.json` (`coordination_branch`).
- **Placement decision** (placement-sense routing): kind + topology → surface. Lives in `commit_router`.
- **Transition decision core**: `tasks_transition_core.py` — the pure decision shared (post-#2116) by `move-task` / `mark-status` / `map-requirements`.
- **Skip-vs-refuse outcome**: the observable result (exit 0 + skip, or exit 1 + refuse, or a typed no-op `reason`) when a command cannot commit to the authoritative surface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The authoritative-surface rule is documented as a single decision table covering every `{topology × protected-primary × start-branch}` combination, and each of the three layers is traceable to a row in it.
- **SC-002**: A PR-bound `--start-branch` mission produces zero stranded-empty coordination worktrees and zero primary-fallback split-brain warnings across the create → spec-commit → status flow (down from 1 reproducible occurrence today).
- **SC-003**: for the same `{artifact_kind, topology, primary_protected}`, `move-task` and `map-requirements` produce the verdict dictated by the one shared rule (shared `reason` code + remedy constant), and `mark-status` is frozen event-log-only — moving from three hardcoded, drifted behaviors today (move-task skip-0, map-requirements refuse-1, mark-status no-commit) to one shared-rule consultation, proven by a JSON-mode characterization diff. (Exit codes may legitimately differ by kind; the *rule* is identical.)
- **SC-004**: B16-clause-2 is resolved to a binary evidence state — either a red-first reproduction test now green after a fix, or a documented non-reproduction with the probe recorded — with no ambiguous "suspected" status remaining.
- **SC-005**: Zero un-characterized observable behavior changes and zero regressions in the existing shared-surface test suite.
