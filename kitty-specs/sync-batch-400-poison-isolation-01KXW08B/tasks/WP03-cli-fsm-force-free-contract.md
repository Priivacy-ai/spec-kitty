---
work_package_id: WP03
title: CLI FSM force-free contract test
dependencies: []
requirement_refs:
- FR-007
- C-003
tracker_refs: []
planning_base_branch: fix/2736-batch-400-poisoning-isolation
merge_target_branch: fix/2736-batch-400-poisoning-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/2736-batch-400-poisoning-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2736-batch-400-poisoning-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
phase: Phase 2 - independent
assignee: ''
agent: "claude"
shell_pid: "1604460"
shell_pid_created_at: "1784429585.61"
history:
- at: '2026-07-19T02:11:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/status/
create_intent:
- tests/status/test_wp_state_force_free_contract.py
execution_mode: code_change
model: ''
owned_files:
- tests/status/test_wp_state_force_free_contract.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – CLI FSM force-free contract test

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Pin the CLI transition FSM's authoritative contract for the backward review edges: `in_progress → planned`
(reason-only) and the review-rejection edges (review_ref-only) are **legal force-free** per `wp_state.py`.
This encodes question-2's decision (the CLI FSM is authoritative; forcing would stamp a false guard-bypass
override and corrupt provenance). The server matrix is the drift and aligns via SaaS#509.

**Done when**: `pytest tests/status/test_wp_state_force_free_contract.py` is green, asserting via the PUBLIC
transition API that these edges are legal with a reason-only context and that the guard does not consult
`ctx.force`.

## Context & Constraints

- **Plan**: IC-07. **Spec**: FR-007, C-003.
- Contract test ONLY — `wp_state.py` already allows these edges force-free; this WP does not change
  production code. If a production change turns out to be needed, STOP and report (the premise is the FSM is
  already correct).
- Assert against the PUBLIC API (`WPState.check_transition` / `can_transition_to`), NOT by reaching into
  `guard_for` internals (pedro).

## Branch Strategy

- **Strategy**: per computed lane from `lanes.json`
- **Planning base branch**: `fix/2736-batch-400-poisoning-isolation`
- **Merge target branch**: `fix/2736-batch-400-poisoning-isolation`

## Subtasks & Detailed Guidance

### Subtask T012 [red] – `in_progress → planned` is force-free legal

- **Purpose**: Pin the core review-rejection backward edge.
- **Steps**: New `tests/status/test_wp_state_force_free_contract.py`. Build a reason-only, no-force context
  and assert `wp_state_for("in_progress").check_transition(Lane.PLANNED, ctx) == (True, None)`.
- **Files**: `tests/status/test_wp_state_force_free_contract.py`.

### Subtask T013 – Review-rejection edges force-free; guard ignores `force`

- **Purpose**: Cover the review_ref-only backward edges and the force-independence.
- **Steps**: Assert the `for_review`/`in_review` → earlier-lane edges are legal with a `review_ref`-only
  context and no force. Assert the guard verdict is identical whether `ctx.force` is unset or `False`
  (the guard does not consult force on these edges).
- **Files**: `tests/status/test_wp_state_force_free_contract.py`.

### Subtask T014 – Pin force-independence; document SaaS#509

- **Purpose**: Make the "no force needed" invariant an objective, in-file assertion (renata: the owned
  status-test file cannot observe the CLI command layer, so "the CLI never emits force" would be un-checkable
  prose here).
- **Steps**: Assert **force-independence** on these edges — the guard verdict is IDENTICAL with `ctx.force`
  unset vs `ctx.force=False` (`check_transition(...)` returns the same `(True, None)` either way). In the
  module docstring, note SaaS#509 as the server-matrix alignment (the server, not the CLI, is the drift). If a
  caller-side "CLI never emits `force=true`" check is wanted, it belongs in an explicitly-named CLI-command-
  layer test, not asserted from this status-FSM file — leave it as a docstring note here, not an assertion.
- **Files**: `tests/status/test_wp_state_force_free_contract.py`.

## Test Strategy

- `pytest tests/status/test_wp_state_force_free_contract.py -q` green at close. `ruff`/`mypy` clean.

## Risks & Mitigations

- **Over-reaching into private guards** → assert on `check_transition` / `can_transition_to` only.
- **Discovering the FSM actually forbids the edge** → STOP and report; do not paper it with `force`.

## Review Guidance

- Confirm the assertions use the public transition API and that force-independence is explicitly tested.

## Activity Log

- 2026-07-19T02:11:31Z – system – Prompt created.
- 2026-07-19T02:53:17Z – claude – shell_pid=1604460 – Assigned agent via action command
- 2026-07-19T03:01:07Z – claude – shell_pid=1604460 – Moved to for_review
- 2026-07-19T03:04:42Z – user – shell_pid=1604460 – Approved: 13 tests green (reviewer adjudicated FSM from source; reading correct — pinned real graph, a superset of the imprecise prose), test-only diff, no production change. Nits: T014 force-independence framing tautological (legality assertion carries it); WP prose to refine.
