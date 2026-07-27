---
work_package_id: WP01
title: Full-sequence parity ratchet (gate)
dependencies: []
requirement_refs:
- FR-020
- FR-021
- FR-022
- FR-023
- FR-024
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on
  feat/execution-state-strangler. During /spec-kitty.implement this WP may
  branch from a dependency-specific base, but completed changes must merge back
  into feat/execution-state-strangler unless the human explicitly redirects the
  landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Gate
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2604094"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_execution_context_parity.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_execution_context_parity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Full-sequence parity ratchet (gate)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Extend `tests/architectural/test_execution_context_parity.py` from the status read+write slice to the **full** `next → implement → move-task → review → status` sequence, proving identical results across main-checkout CWD, lane-worktree CWD, and direct-to-target mode.

- FR-020/021/022/023/024. SC-002.
- This WP is the **gate**: it must be green before WP04/06/07/08/09/10 are considered complete (C-003).
- The ratchet must be **non-vacuous** — it fails when a surface re-derives context independently.

## Context & Constraints

- Contract: [contracts/parity_ratchet.md](../contracts/parity_ratchet.md). Plan: [plan.md](../plan.md) IC-03. Spec US2.
- Existing test already proves status read (`agent tasks status`) + write (`agent status emit`) parity with injection proofs — extend, don't replace.
- Direct-to-target mode (operator ruling): no worktree; declared target branch; never mainline unauthorized (C-001/C-002).

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T001 – Lane-worktree + direct-to-target fixtures
- **Steps**: Build a real `git worktree` lane fixture and a direct-to-target (no-worktree) fixture, reusing the existing `parity_repo` factory pattern.
- **Files**: `tests/architectural/test_execution_context_parity.py`
- **Notes**: Use the real mode resolver; do not mock the branch resolution.

### Subtask T002 – Full sequence from main-checkout CWD
- **Steps**: Drive `next → implement → move-task → review → status` via subprocess with `cwd=<repo root>`; capture resolved WP identity, lane events, status JSON.
- **Files**: same test module.

### Subtask T003 – Same sequence from lane-worktree CWD [P]
- **Steps**: Repeat from `.worktrees/<mission>-<mid8>-lane-a/`; assert parity with T002 outputs.

### Subtask T004 – Direct-to-target mode
- **Steps**: Run the sequence in direct-to-target mode; assert the declared target branch is used and an unauthorized mainline write is refused.

### Subtask T005 – Non-vacuous negative control
- **Steps**: Mirror `test_ratchet_catches_divergence` for the full sequence: inject an independently re-deriving surface and assert the ratchet fails.

### Subtask T006 – Docstring + CI gate
- **Steps**: Correct the module docstring to state real coverage (FR-023). Register the ratchet as required for PRs touching `mission_runtime/`, `status/`, `runtime/next/`, `cli/commands/agent/` (FR-024).

## Test Strategy

- `pytest tests/architectural/test_execution_context_parity.py -q` green; negative control demonstrably fails when re-derivation is injected.

## Risks & Mitigations

- Fixture realism → assert against the real resolver. Flaky subprocess timing → deterministic fixtures, no sleeps.

## Review Guidance — **Persona IC: Paula Patterns (architecture-scout)** assists `reviewer-renata`

- Confirm the ratchet **bites**: temporarily revert a routed surface and prove it goes red.
- Reviewer profile: `reviewer-renata`. Verify FR-020..024 each have a concrete assertion; reject if any mode is asserted vacuously.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T04:11:52Z – claude:sonnet:python-pedro:implementer – shell_pid=2554367 – Assigned agent via action command
- 2026-06-08T04:36:31Z – claude:sonnet:python-pedro:implementer – shell_pid=2554367 – Ready for review: full-sequence parity ratchet (T001-T006) green, ruff/mypy clean, proof-of-bite demonstrated for T003 and T005
- 2026-06-08T04:48:01Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2604094 – Started review via action command
- 2026-06-08T04:56:24Z – user – shell_pid=2604094 – Review passed (reviewer-renata + paula-patterns assist): FR-020 PASS (T002 drives full sequence from main-checkout CWD with step-for-step transition identity + final lane assertions, concrete not vacuous); FR-021 PASS (T003 drives identical sequence from lane-worktree CWD via two independent repos, step-for-step parity asserted); FR-022 PASS (T004 direct-to-target: no-worktree repo on feat/direct-target, full sequence green, mainline write on main branch refused with non-zero exit); FR-023 PASS (module docstring rewritten to state real coverage: full sequence x 3 modes, CI gate, extensions correctly described); FR-024 PASS (T006 asserts execution_context CI filter includes status/**, runtime/next/**, cli/commands/agent/**, and the test file itself; mission_runtime/** deferred to WP02 - explicitly sanctioned, module does not exist yet); SC-002 PASS (T005 injection proof: drives full sequence, injects divergent approved lane in worktree-local kitty-specs/, asserts main authority != worktree surface). Bite test 1 (T003): changed expected final lane from in_review to approved - induced AssertionError on test_full_sequence_worktree_parity, reverted. Bite test 2 (T005): weakened injected divergence to in_review matching main authority - induced setup-error AssertionError on test_full_sequence_ratchet_catches_divergence, reverted. pytest exit 0 (9/9 passed, 56s), ruff exit 0, mypy exit 0. Owned file only: WP01 commit touches solely tests/architectural/test_execution_context_parity.py. Markers: architectural + git_repo + non_sandbox correct per sibling tests. --mission flag used throughout (no --feature usage). Anti-pattern checklist: Dead code N/A (test-only); no synthetic fixtures; no silent returns; all 5 FRs exercised with concrete assertions; frozen surface clean; no MUST NOT violations; no shared file ownership issues; no bare raise.
