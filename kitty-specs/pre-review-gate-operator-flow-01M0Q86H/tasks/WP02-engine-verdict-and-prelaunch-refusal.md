---
work_package_id: WP02
title: Engine Verdict and Pre-Launch Refusal
dependencies:
- WP01
requirement_refs:
- C-004
- C-007
- FR-002
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- NFR-003
- NFR-007
planning_base_branch: fix/pre-review-gate-operator-flow
merge_target_branch: fix/pre-review-gate-operator-flow
branch_strategy: Planning artifacts for this mission were generated on fix/pre-review-gate-operator-flow. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/pre-review-gate-operator-flow unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase 2 - Engine integration
history:
- at: '2026-08-23T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/pre_review_gate.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/pre_review_gate.py
- src/specify_cli/review/verdict_aggregation.py
- tests/review/test_pre_review_gate_engine.py
- tests/review/test_pre_review_gate_integration.py
- tests/review/test_verdict_aggregation.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2573'
---

# Work Package Prompt: WP02 – Engine Verdict and Pre-Launch Refusal

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/specify_cli/review/pre_review_gate.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Before implementing, inspect the current WP event log for `review_ref`. Address every review item and append progress chronologically to the Activity Log.

## Objective and success criteria

Make the WP01 assessment authoritative before `_launch_scoped_process` for both derived and explicit-override scopes. Oversized returns `SCOPE_OVERSIZED` with `HeadRunState.NOT_STARTED`; unknown still runs under the existing 300-second budget and, only if it times out, returns a classification-candidate diagnostic.

Done when launch spies prove refusal is pre-launch, terminal aggregation prevents transition, and current success/warning/timeout/cancellation behavior remains compatible.

## Context and constraints

- Add typed renderer-neutral `ScopeAssessed` and `Heartbeat` status events; the CLI renders them later.
- Carry budget assessment on every verdict with compatibility defaults for existing constructors.
- Record configured timeout and monotonic observed elapsed separately.
- Never auto-promote or persist a classification after timeout.
- Preserve completion/deadline precedence, cleanup machinery, baseline diff, and the canonical warn/block policy.
- Commit at least one failing-first engine acceptance test separately before production edits; review must prove it RED on this WP's `planning_base_branch` and GREEN on the final commit.
- If an operational CLI/dogfood run (not a synthetic timeout fixture) produces an unknown-budget candidate, immediately run `spec-kitty agent tracer-append --mission pre-review-gate-operator-flow-01M0Q86H --category approach --actor <actor> --entry <evidence>` with `provenance: operational`, identity, targets, budget, elapsed time, and environment. This canonical coordination write is not a hand-edit of another WP's owned file.

## Subtasks

### T005 – Red-first engine and aggregation tests

Add failing tests for pre-launch oversized refusal, unknown run-through, bounded fixture completion, unknown timeout diagnostics, non-candidate bounded timeout, and terminal aggregation. Commit the red tests before T006.

### T006 – Typed outcomes, states, events, and evidence

Add `SCOPE_OVERSIZED`, `NOT_STARTED`, status-event types/protocol, and backward-compatible budget/diagnostic fields on `GateVerdict`. Keep event payloads free of Rich/Typer objects.

### T007 – Preflight assessment on both evaluation paths

Assess immediately after scope resolution and before any launch. Emit exactly one scope-assessed event. For oversized, return promptly with no runner call; for bounded/unknown, continue through the incumbent engine.

### T008 – Unknown-timeout candidate diagnostic

Adapt the existing elapsed observer to monotonic evidence. On unknown timeout only, include scope identity, normalized targets, classification, configured budget, observed elapsed, unchanged-lane intent, and reviewed-update guidance. Do not write metadata.

### T009 – Aggregation and focused regression gate

Add oversized to the terminal set and prove no transition is permitted. Run the three owned test modules plus existing source-mismatch/baseline parity tests relevant to the touched verdict path. Run `uv run ruff check` across all owned Python files and `uv run mypy --strict src/specify_cli/review/pre_review_gate.py src/specify_cli/review/verdict_aggregation.py`; review each new public enum, dataclass, protocol, and function for a docstring.

## Test strategy

Use deterministic clocks and launch spies for performance/ordering. Run `pytest tests/review/test_gate_budget.py tests/review/test_pre_review_gate_engine.py tests/review/test_pre_review_gate_integration.py tests/review/test_verdict_aggregation.py -q`.

## Review guidance

Confirm classification is performed once at the engine seam, refusal precedes process creation, and a local timeout cannot alter WP01 policy.

## Activity Log

- 2026-08-23T15:30:00Z – system – Prompt created.
