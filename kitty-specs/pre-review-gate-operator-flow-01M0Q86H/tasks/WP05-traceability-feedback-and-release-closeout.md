---
work_package_id: WP05
title: Traceability Diagnostic Feedback and Release Closeout
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
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/traces/approach.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/traceability.md
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/release-readiness.md
- kitty-specs/pre-review-gate-operator-flow-01M0Q86H/traces/approach.md
role: curator
tags: []
task_type: implement
tracker_refs:
- '#2573'
- '#3127'
---

# Work Package Prompt: WP05 – Traceability, Diagnostic Feedback, and Release Closeout

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

Close the evidence loop without turning observations into automatic policy. Map every acceptance scenario, precedence combination, and named race to exact pytest node IDs and assertions; inspect candidate diagnostics during retrospective; enforce the #3127/rebase/checks boundary before #2573 is called release-ready.

Done when traceability has no blank evidence cells and release readiness has an explicit, auditable verdict.

## Context and constraints

- Append observed candidates only through `spec-kitty agent tracer-append --category approach`; do not hand-edit runtime policy from a timeout.
- Each candidate record includes scope identity, normalized targets, configured budget, observed elapsed, and environment context.
- Retrospective records a follow-up owner, explicit no action, or explicit absence of candidates.
- Async redesign remains deferred. No CI log backfill, CI topology change, background lane, or pending-review state.
- #2573 cannot be release-ready until #3127 is merged, this branch is rebased on resulting `main`, and trustworthy checks are rerun.

## Subtasks

### T020 – Exact-node traceability matrix

Create `traceability.md` with one row per FR-001–FR-010 acceptance scenario, precedence combination, and interruption race. Columns: exact pytest node ID, human assertion, structured assertion, launch assertion, and lane/event assertion. Use `N/A — reason` rather than blank cells.

### T021 – Trustworthy verification evidence

Run focused policy/engine/public/process suites and the relevant broader review/agent-command regressions. Record commands, commit/base, platform, pass/fail/skip counts, and any limitations in `release-readiness.md`.

### T022 – Durable candidate capture

Inspect delivery output for unknown-budget timeout candidates. Append each through the canonical tracer command with all required fields; if none occurred, record explicit absence in the retrospective evidence.

### T023 – Retrospective decision

Review `traces/approach.md` and record for each candidate either a named owner for a reviewed source update or an explicit no-action rationale. Reassert that observations never mutate deterministic metadata automatically.

### T024 – Issue and release boundary

Re-evaluate #2573 against shipped evidence and keep async redesign durably deferred. Verify #3127 merge state; only after it is merged, rebase onto resulting `main` and rerun required checks. Otherwise record the release-ready verdict as blocked by that external dependency without bypassing it.

## Test strategy

The matrix is executable evidence: every named node must collect. Treat missing/renamed nodes or blank columns as failure. Verify tracer writes landed in the canonical mission partition.

## Review guidance

Reject estimated/backfilled budget classifications, automatic promotion, claims unsupported by exact node IDs, or a release-ready statement made before the #3127/rebase/check sequence.

## Activity Log

- 2026-08-23T15:30:00Z – system – Prompt created.
