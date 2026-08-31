---
work_package_id: WP05
title: Traceability Retrospective Handoff and Release Gate
dependencies:
- WP03
- WP04
requirement_refs:
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- C-007
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- NFR-003
- NFR-005
- NFR-006
- NFR-007
planning_base_branch: fix/pre-review-gate-operator-flow
merge_target_branch: fix/pre-review-gate-operator-flow
branch_strategy: Planning artifacts for this mission were generated on fix/pre-review-gate-operator-flow. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/pre-review-gate-operator-flow unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
phase: Phase 4 - Evidence and release closeout
history:
- at: '2026-08-23T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: kitty-specs/pre-review-gate-operator-flow-01M0Q86H/traceability.md
create_intent:
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/traceability.md
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/release-readiness.md
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/retrospective-handoff.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/traceability.md
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/release-readiness.md
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/retrospective-handoff.md
role: curator
tags: []
task_type: implement
tracker_refs:
- '#2573'
- '#3127'
---

# Work Package Prompt: WP05 – Traceability, Retrospective Handoff, and Release Gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: kitty-specs/pre-review-gate-operator-flow-01M0Q86H/traceability.md`.

---

## ⚠️ IMPORTANT: Review Feedback

Before implementing, inspect the current WP event log for `review_ref`. Address every review item and append progress chronologically to the Activity Log.

## Objective and success criteria

Close the pre-accept evidence loop without impersonating post-merge authorities. Map every acceptance scenario, precedence combination, and named race to exact pytest node IDs and assertions; audit immediate operational-candidate tracer entries; prepare the canonical retrospective handoff; define the executable #3127/rebase/checks release resume point.

Done when traceability has no blank evidence cells, the retrospective handoff inventories durable operational entries or explicit absence, and release readiness has an explicit `ready` or `waiting_upstream` verdict with a concrete resume command sequence. `waiting_upstream` completes this evidence WP but never means #2573 is release-ready.

## Context and constraints

- Earlier WPs append operational candidates immediately only through `spec-kitty agent tracer-append --category approach`; WP05 audits the durable tracer and never reconstructs it from terminal scrollback.
- Each operational entry includes provenance, scope identity, normalized targets, configured budget, observed elapsed, and environment context. Synthetic fixtures are traceability evidence only.
- `retrospective-handoff.md` requires the automatic post-merge terminus or `spec-kitty retrospect create --mission pre-review-gate-operator-flow-01M0Q86H --json` to produce canonical `retrospective.yaml` with follow-up owner, explicit no action, or explicit absence.
- Async redesign remains deferred. No CI log backfill, CI topology change, background lane, or pending-review state.
- #2573 cannot be release-ready until #3127 is merged, this branch is rebased on resulting `main`, and trustworthy checks are rerun.

## Subtasks

### T020 – Exact-node traceability matrix

Create `traceability.md` with one row per FR-001–FR-010 acceptance scenario, precedence combination, and interruption race. Columns: exact pytest node ID, human assertion, structured assertion, launch assertion, and lane/event assertion. Use `N/A — reason` rather than blank cells.

### T021 – Trustworthy verification evidence

Run focused policy/engine/public/process suites, ruff, strict mypy, public-docstring review, and relevant broader review/agent-command regressions. Record commands, commit/base, platform, pass/fail/skip counts, and limitations in `release-readiness.md`. Record the actual `ci-windows` job/check and exact `@pytest.mark.windows_ci` node result; if the job truly does not exist, cite repository/branch evidence and record an explicit N/A without changing CI.

### T022 – Durable candidate capture

Read the durable `traces/approach.md` from the canonical coordination surface and cross-check WP evidence/activity logs for every operational candidate. Fail the audit if an operational candidate was not appended immediately. Exclude synthetic controlled-clock/process fixtures from the metadata-review queue and inventory durable operational entries—or explicit absence—in `retrospective-handoff.md`.

### T023 – Retrospective decision

Create `retrospective-handoff.md` with an acceptance item for every operational candidate requiring the canonical post-merge `retrospective.yaml` to record `follow_up` with owner/reference or `no_action` with rationale; if none exist, require `no candidates observed`. Name the automatic merge/close retrospective terminus and the recovery command `spec-kitty retrospect create --mission pre-review-gate-operator-flow-01M0Q86H --json`. Do not create or claim the post-merge retrospective inside this pre-accept WP.

### T024 – Issue and release boundary

Re-evaluate #2573 against shipped evidence and keep async redesign durably deferred. In `release-readiness.md`, if #3127 is merged, record the resulting `main` SHA, rebase evidence, and rerun checks; otherwise set `waiting_upstream` and record an executable resume sequence: verify #3127 merged, fetch resulting `main`, rebase this branch, rerun required checks including Windows evidence, then reassess #2573. Never close/mark #2573 release-ready from `waiting_upstream`.

## Test strategy

The matrix is executable evidence: every named node must collect. Treat missing/renamed nodes or blank columns as failure. Verify tracer writes landed in the canonical mission partition and that `retrospective-handoff.md` is consumable after merge.

## Review guidance

Reject estimated/backfilled budget classifications, automatic promotion, synthetic fixture pollution, claims unsupported by exact node IDs, pre-merge retrospective conclusions, or a release-ready statement made before the #3127/rebase/check sequence.

## Activity Log

- 2026-08-23T15:30:00Z – system – Prompt created.
