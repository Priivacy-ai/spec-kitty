---
work_package_id: WP06
title: setup-plan branch-match honesty
dependencies:
- WP01
requirement_refs:
- FR-006
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
phase: Phase 1 - Fail-closed adopters
history:
- at: '2026-08-18T21:17:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/mission_setup_plan.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_setup_plan_branch_match.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/cli/commands/agent/mission_branch_context.py
- tests/specify_cli/cli/commands/agent/test_setup_plan_branch_match.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – setup-plan branch-match honesty

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Fix the **read-side false-green** in `setup-plan`: `branch_matches_target` must reflect the **invoking checkout / mission `meta.json`**, not the **primary checkout's HEAD**. Today a lane invocation reports `branch_matches_target: true` by reading primary's current branch (issue #3124).

Done when:
- A red-first regression proves the false-green on base: from a lane worktree on a lane branch, `setup-plan` reports `branch_matches_target: true` reflecting primary's HEAD — RED on `upstream/main`.
- After the fix, `branch_matches_target` is computed from the invoking checkout / mission `meta.json`; a lane on a divergent branch reports honest disagreement.
- **Target-branch resolution stays primary-anchored** — that is deliberate (`_resolve_planning_branch:310-316`, "current checkout branch intentionally never consulted"). Only the *match computation* is corrected.
- `ruff` + `mypy` clean; complexity ≤15.

## Context & Constraints

- #3129 investigation lists #3124 as the *"read-side analogue"* of #2613/#3051: *"reports the primary checkout's branch as the mission's target, `branch_matches_target: true`."*
- Prereq **WP01** provides `resolve_checkout_identity`. Use it to obtain the invoking checkout; do not re-derive `.git` classification.
- Supporting docs: `spec.md` (FR-006), `contracts/…` (C-3), `research.md` (Decision 2).
- Anchors (verify at implement time): `agent/mission_setup_plan.py:914` `locate_project_root()` (primary), `:934` `current_branch = get_current_branch(repo_root=primary)` — reads **primary's** HEAD. `mission_branch_context.py:99` `_inject_branch_contract` sets `branch_matches_target = resolved_current_branch == target_branch`. The `_resolve_planning_branch:310-316` deliberate-target docstring covers **target** resolution only.

## Branch Strategy

- **Strategy**: lane-per-WP (coord topology)
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T018 – Red-first: branch_matches_target:true from primary HEAD in a lane

- **Purpose**: Prove the read-side false-green on base (NFR-001).
- **Steps**:
  1. In `tests/specify_cli/cli/commands/agent/test_setup_plan_branch_match.py`, build a primary checkout on branch `main`-like plus a linked lane worktree checked out on a distinct lane branch, with a mission whose `meta.json` `target_branch` differs from primary's HEAD.
  2. Invoke `setup-plan --json` from the lane worktree.
  3. Assert the **current** behavior: `branch_matches_target` is `true` because it reflects primary's HEAD, not the lane. `@pytest.mark.regression`, pin #3124.
  4. Confirm RED on `upstream/main`.
- **Files**: `tests/specify_cli/cli/commands/agent/test_setup_plan_branch_match.py` (new, ~100 lines).
- **Parallel?**: [P].
- **Notes**: Drive the real CLI entry (`spec-kitty agent mission setup-plan --json`) or its direct function so this is a genuine regression-through-CLI.

### Subtask T019 – Compute branch_matches_target from the invoking checkout / meta.json

- **Purpose**: Make the guard honest without disturbing deliberate target resolution.
- **Steps**:
  1. In `mission_setup_plan.py`, obtain the invoking checkout via WP01's `resolve_checkout_identity` (`intent=WRITE` for the plan write) and read *its* current branch for the match computation, or read the mission `meta.json` `target_branch` and compare against the invoking checkout's HEAD.
  2. Keep `_resolve_planning_branch` target resolution primary-anchored (do not flip it). Only the value fed into `branch_matches_target` changes.
  3. In `mission_branch_context.py:99`, ensure `_inject_branch_contract` receives the invoking-checkout branch (not primary HEAD) for the match, threading a parameter if needed.
  4. Preserve owner-invocation behavior exactly (from the primary checkout the result is unchanged).
- **Files**: `src/specify_cli/cli/commands/agent/mission_setup_plan.py`, `src/specify_cli/cli/commands/agent/mission_branch_context.py`.
- **Notes**: This WP is in the FR-008 spirit — do NOT flip the deliberate primary target-branch read; a characterization test (owned by WP01) pins that. Keep them green.

## Test Strategy

- `test_setup_plan_branch_match.py`: red-first (T018) + green-after **both directions** (mirror WP08 T025 discipline, so a hardcoded `false` cannot pass):
  - lane on a branch that **diverges** from `meta.json` target → honest `branch_matches_target: false`;
  - **lane on a branch that MATCHES `meta.json` target → `branch_matches_target: true`** (the positive case — without it an implementer could hardcode `false` for any non-owner invocation and pass);
  - owner-invocation unchanged.
- Run: `pytest tests/specify_cli/cli/commands/agent/test_setup_plan_branch_match.py -n0 -q`.

## Risks & Mitigations

- **Risk**: accidentally flipping the deliberate target-branch resolution → regresses #3328. **Mitigation**: only touch the match value; keep `_resolve_planning_branch` primary-anchored; rely on WP01's must-not-flip characterization tests.
- **Risk**: coord-worktree missing `meta.json`. **Mitigation**: fall back to the invoking checkout's HEAD explicitly; test the coord case.

## Review Guidance

- Confirm target-branch resolution is untouched; only the match value reflects the invoking checkout.
- Confirm the red-first test is red on base and exercises the real CLI path.

## Activity Log

- 2026-08-18T21:17:24Z – system – Prompt created.
