---
work_package_id: WP01
title: ADRs + Glossary — Domain Model Gate
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: claude
history:
- date: '2026-06-03'
  event: created
  author: spec-kitty
agent_profile: architect-alphonso
authoritative_surface: architecture/3.x/adr/
execution_mode: planning_artifact
owned_files:
- architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md
- architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md
- architecture/3.x/adr/2026-06-03-3-effector-actor-model.md
- src/specify_cli/glossary/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load` and specify profile `architect-alphonso` before reading further. This profile configures your role as an architecture decision author.

---

## Objective

Author three Architecture Decision Records (ADRs) and update five glossary entries, then commit all to `main`. This is the mandatory gate (C-001, DIRECTIVE_032): **no implementation PR for WP02–WP06 may merge before this WP is committed and green in CI.**

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: assigned from `lanes.json` after `finalize-tasks`; do not guess the worktree path.
- Start with: `spec-kitty agent action implement WP01 --agent claude`

## Context

The execution-state remediation (#1619) requires vocabulary and architectural decisions to be locked in ADRs before code. Three ADRs are needed (from issue #1674):

1. Domain model + status ownership
2. ExecutionContext OHS owner + CommitTarget atomicity
3. Effector/Actor model

**Existing ADR to use as format reference**: `architecture/3.x/adr/2026-04-25-1-shared-package-boundary.md`
— read this file first to match the format (Status, Context, Decision, Consequences sections).

**Glossary location**: Find the project glossary by searching `src/specify_cli/glossary/` for existing term files. Match the format of existing entries.

---

## Subtask T001 — ADR 1: Domain Model + Status Ownership

**File**: `architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md`

**Decision to record**:
- Four bounded modules: Governance (Charter + Doctrine), Mission Management (owns status/kanban), Execution/Runtime, Shared Kernel
- Status/Kanban is owned exclusively by Mission Management — it publishes an OHS facade; all other modules are consumers
- Context is per-domain: GovernanceContext / ExecutionContext / InfraContext
- Keepers: Mission ≠ MissionRun (1:many); MissionType ∈ Governance
- Glossary entries: GovernanceContext, ExecutionContext, InfraContext, Effector, communication-artefact
- This is the baseline for all implementation issues in #1619

**Structure**:
```markdown
# ADR 2026-06-03-1: Execution-State Domain Model

**Status**: Accepted
**Date**: 2026-06-03
**Author**: @robertDouglass

## Context
[Describe the current state — independent context re-derivation, #1619 root cause]

## Decision
[Record the four-module model, status ownership, context types, keepers]

## Consequences
[What changes downstream, what stays the same, what is now explicit]
```

**Validation**: File exists at correct path. Follows the format of `2026-04-25-1-shared-package-boundary.md`. All four modules named. Status ownership explicitly declared.

---

## Subtask T002 — ADR 2: ExecutionContext Owner + CommitTarget Atomicity

**File**: `architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md`

**Decision to record** (two related decisions from doc 06):

**ExecutionContext owner**:
- `resolve_action_context` in `src/specify_cli/core/execution_context.py` is the canonical OHS entry point
- It is the single resolver that fuses planning + execution context
- Execution context is resolved once per operation and passed down
- Migration path: Strangler Fig via existing `resolve_action_context` OHS (Option C → B from design doc 06 §5)

**CommitTarget atomicity**:
- `(worktree_root, destination_ref)` is a single self-validating `CommitTarget` value type owned by the operation
- Gate cleared: forensic pass of `safe_commit` call graph confirms the invariant is structurally enforced by `safe_commit` itself; 7 direct call sites, all clean
- `CommitTarget` is ergonomic hardening of clean code
- Implementation is Strangler step 7; no design risk to steps 1–6

**Validation**: File exists. Both sub-decisions documented. `resolve_action_context` named as canonical. Strangler strategy referenced.

---

## Subtask T003 — ADR 3: Effector/Actor Model

**File**: `architecture/3.x/adr/2026-06-03-3-effector-actor-model.md`

**Decision to record**:
- **Effector** = the Actor realized inside the Execution domain (Effector = Actor ∩ Execution)
- **Decision: named in docs only** — no code type until actor-kind fragmentation causes a concrete bug
- Rationale: concept is modeling vocabulary; materializing as a code type risks over-engineering
- Trigger to materialize: first concrete actor-kind-mismatch bug, OR a feature needing to join status/decision/retrospective logs on actor identity
- When materialized: low-layer shared type (`kernel/` or `actor.py`) so three existing vocabularies converge without an illegal up-import

**Validation**: File exists. Effector defined. "Docs only" decision explicit. Materialization trigger described.

---

## Subtask T004 — Update Glossary Entries

**Where**: `src/specify_cli/glossary/` — find existing term files and match their format.

**Five terms to add or update**:

| Term | Definition |
|------|-----------|
| `GovernanceContext` | The resolved set of Charter and Doctrine artifacts active for an operation. Owned by the Governance bounded module. |
| `ExecutionContext` | The resolved set of workspace, branch, feature-dir, and WP identity for an operation. Owned by `core/execution_context.py` (OHS). |
| `InfraContext` | The resolved set of infrastructure credentials and endpoints for an operation (git remote, CI, etc.). |
| `Effector` | The Actor realized inside the Execution domain — the execution-bound realization of an Actor. Named concept in docs; no code type until a concrete actor-kind-mismatch bug triggers materialization. |
| `communication artefact` | A durable artifact produced or consumed by an Effector during a mission run (e.g., a commit, a PR, a comment). Distinct from planning artifacts (spec, plan, tasks). |

**Steps**:
1. `ls src/specify_cli/glossary/` — understand the file format (YAML? Markdown?)
2. Check if any of these terms already exist; update if so, add if not
3. Match the exact format of existing entries

**Validation**: All five terms present in glossary. Format matches existing entries.

---

## Subtask T005 — Commit and Verify CI

**Steps**:
1. Stage all three ADR files and any modified glossary files
2. Commit with a message referencing the three ADRs and #1674:
   ```
   docs(adr): domain model, ExecutionContext owner, Effector model — #1674

   ADR 1: four-bounded-module domain model; Mission Management owns status.
   ADR 2: resolve_action_context is the canonical OHS; CommitTarget atomicity.
   ADR 3: Effector named in docs only; materialization trigger defined.
   Glossary: GovernanceContext, ExecutionContext, InfraContext, Effector,
   communication-artefact.
   ```
3. Push branch and verify CI passes
4. Note: This must be merged before WP02 can start

**Validation**: Three ADR files committed. Glossary updated. CI green. PR or commit visible on main.

---

## Definition of Done

- [ ] `architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md` exists and follows ADR format
- [ ] `architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md` exists and follows ADR format
- [ ] `architecture/3.x/adr/2026-06-03-3-effector-actor-model.md` exists and follows ADR format
- [ ] All five glossary terms added or updated
- [ ] All files committed and CI green
- [ ] No `[NEEDS CLARIFICATION]` or placeholder text in any ADR

## Risks

- ADR format may differ from the reference — read `2026-04-25-1-shared-package-boundary.md` carefully before writing
- Glossary file format unknown until inspected — do not assume

## Reviewer Guidance

Check that each ADR has concrete decisions (not just problem descriptions), that the four module names match those in `spec.md`, and that the Effector "docs only" decision is unambiguous.

## Activity Log

- 2026-06-03T11:25:59Z – claude – Claiming WP01 for planning artifact implementation
- 2026-06-03T11:29:18Z – claude – Implementation complete. Three ADRs authored (domain model, ExecutionContext owner, Effector model) and five glossary terms added (GovernanceContext, ExecutionContext, InfraContext, Effector, communication artefact). All committed to coordination branch. No Python changes; no tests or ruff required for planning_artifact WP.
- 2026-06-03T11:31:41Z – claude – Review cycle 1 starting by reviewer-renata
- 2026-06-03T11:36:17Z – claude – Review passed (cycle 1): All three ADRs exist at correct paths with Status/Context/Decision/Consequences sections, no placeholder text. All five glossary terms (GovernanceContext, ExecutionContext, InfraContext, Effector, communication artefact) added to glossary/contexts/execution.md. ADR 1 names all four bounded modules and status ownership; ADR 2 names resolve_action_context as canonical OHS; ADR 3 declares Effector as docs-only with clear materialization trigger.
