---
work_package_id: WP03
title: Public Operator Output and Observer Wiring
dependencies:
- WP02
requirement_refs:
- C-002
- C-003
- C-004
- C-005
- C-006
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-007
- FR-008
- FR-009
- FR-010
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-006
- NFR-007
planning_base_branch: fix/pre-review-gate-operator-flow
merge_target_branch: fix/pre-review-gate-operator-flow
branch_strategy: Planning artifacts for this mission were generated on fix/pre-review-gate-operator-flow. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/pre-review-gate-operator-flow unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - Public operator flow
history:
- at: '2026-08-23T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/gate_registry.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/review/test_gate_registry.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2573'
---

# Work Package Prompt: WP03 – Public Operator Output and Observer Wiring

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Before implementing, inspect the current WP event log for `review_ref`. Address every review item and append progress chronologically to the Activity Log.

## Objective and success criteria

Wire the engine's typed observer through `TransitionGateContext`, registered handlers, and the explicit-override path. Human mode receives assessment/start/continuing heartbeat/final output; JSON mode emits exactly one final document whose top-level `transition_applied` remains authoritative.

Done when the exact public Typer entry proves the timing and all skip/disable/warn/block/refusal/timeout framing requirements.

## Context and constraints

- Construct rendering only at the CLI boundary; `gate_registry.py` carries an optional protocol.
- Use the same observer for registered and explicit-override evaluation.
- Scope assessment must be visible before launch; heartbeat interval is at most 30 seconds while active and stops after the terminal result.
- Oversized refusal names bounded scope and explicit skip. Unknown timeout names reviewed metadata follow-up, not automatic learning.
- Preserve flag-over-env precedence, canonical env order, explicit daemon-management exception, and warn-by-default.
- Commit at least one failing-first exact public-entry test separately before production edits. It must be RED on this WP's post-WP02 `planning_base_branch`; if already green, strengthen it before touching production. Review must verify the red and green commits.
- If an operational CLI/dogfood run (not a synthetic controlled-clock fixture) produces an unknown-budget candidate, append it immediately through the canonical `tracer-append` command with `provenance: operational` and full diagnostic/environment data. Never enqueue synthetic fixture evidence for metadata review.

## Subtasks

### T010 – Red-first exact-entry contracts

Replace the existing comment-only liveness gap with controlled-clock exact Typer-entry tests parameterized over (a) the explicit `pre_review_test_scope` override fixture and (b) an unpinned active registered binding. Capture the observer passed down each route and prove equivalent identity/behavior, scope assessment before the lowest launch seam, start within one second, at least two heartbeats with deltas no greater than 30 seconds over a run exceeding 60 seconds, no heartbeat after finalization, and no intermediate JSON. Commit these red tests before T011.

### T011 – Registry context wire

Add the optional typed observer to `TransitionGateContext`, delegate it unchanged from the registered pre-review handler, and extend registry parity tests.

### T012 – Both public evaluation paths

Build one human-only observer in `tasks_move_task.py` and pass it through registry-bound and explicit-override paths. Do not build a second classification or rendering authority.

### T013 – Human rendering

Render the scope assessment before launch, continuing elapsed heartbeats, oversized refusal recovery choices, and unknown-timeout candidate evidence. Ensure final success/warning/block/cancel wording stays coherent.

### T014 – Structured metadata and transition authority

Extend the existing `pre_review_gate` metadata object with budget and candidate fields. Assert one final JSON document for every named outcome and keep top-level `transition_applied` authoritative over nested evidence.

### T015 – Compatibility matrix

Re-prove normal default run, default warning admission, configured blocking refusal, timeout/cancellation non-transition, and ordinary success exactly once. Add exact human and single-document JSON collision cases for skip+blocking, skip+both disables, and both disables without skip; assert `SPEC_KITTY_SYNC_DISABLE` wins canonical env ordering and neither validation nor implicit daemon startup occurs. Separately prove explicit daemon-management still runs under each disable variable. Finish with `uv run ruff check` on every owned Python file and `uv run mypy --strict src/specify_cli/review/gate_registry.py src/specify_cli/cli/commands/agent/tasks_move_task.py`; review all new public observer/context surfaces for docstrings.

## Test strategy

Run the two owned tests first, then related escape-hatch, baseline-read, gate-binding, and orchestration tests. Use in-process controlled clocks; do not sleep for 60 seconds.

## Review guidance

Inspect stdout framing byte-for-byte in JSON cases. Reject mixed/NDJSON progress, nested transition authority, duplicated observer paths, or any default severity change.

## Activity Log

- 2026-08-23T15:30:00Z – system – Prompt created.
