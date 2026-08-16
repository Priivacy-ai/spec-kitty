---
work_package_id: WP03
title: next explicit-ownership integration and per-checkout runtime state
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-004
- FR-007
- C-001
- C-002
planning_base_branch: fix/worktree-owned-root-3328-v2
merge_target_branch: fix/worktree-owned-root-3328-v2
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-owned-root-3328-v2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-owned-root-3328-v2 unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
history:
- at: '2026-08-11T13:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: ''
authoritative_surface: tests/agent/test_context_validation_unit.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/agent/test_context_validation_unit.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 - next explicit-ownership integration and per-checkout runtime state

## Objective

Add the same `--owned-checkout` affordance to `spec-kitty next`, validated through WP01's primitive, and root per-checkout runtime state (`feature-runs.json`-equivalent, merge-lock directory resolution) at the owned checkout instead of the ambiently-resolved primary when ownership is `OWNED` — while leaving `next`'s existing behavior for non-opted-in callers (including generic linked worktrees that today ambiently resolve to primary) completely unchanged (FR-004, spec.md User Story 2 Acceptance Scenario #4).

## Context

`next` (`src/specify_cli/cli/commands/next_cmd.py:60-94`) is gated by `@require_main_repo` (a DIFFERENT, `.worktrees`-literal-only detector than `mission create`'s — research D-1) and always resolves `repo_root = locate_project_root()` (line 91), which collapses any worktree caller to the primary. This WP does not change `require_main_repo`'s existing detection scope — it adds a parallel, explicit path that is consulted first.

Read `plan.md` IC-03 and `contracts/checkout-ownership-cli-contract.md` ("CLI Surface: spec-kitty next" section) in full before starting. Pay particular attention to the open design point flagged in plan.md IC-03's Risks: whether `@require_main_repo` needs a narrow, explicit bypass ONLY when a validated `OwnershipClaim.OWNED` is present. Resolve this during implementation and document the decision in this WP's Activity Log — do not silently choose without recording the reasoning, since #3128 (the sibling issue) will build on whichever shape you land on.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### Subtask T010 - Add `--owned-checkout` to `next` and resolve the ownership claim

- **Purpose**: Mirror WP02's CLI addition on the `next` surface.
- **Steps**:
  1. In `src/specify_cli/cli/commands/next_cmd.py`, add `owned_checkout: Path | None = typer.Option(None, "--owned-checkout", ...)` to `next_step` (currently decorated `@require_main_repo` at line 60).
  2. Immediately after entry (before or coordinated with the `@require_main_repo` decorator per your T010 design decision above), call `resolve_ownership_claim(owned_checkout, resolved_primary=locate_project_root())`.
  3. When `owned_checkout is None`: behavior is unchanged — `@require_main_repo` fires exactly as today for `.worktrees`-literal paths; generic linked worktrees ambiently resolve to primary exactly as today (do NOT add a new refusal for this case — spec.md explicitly forbids retrofitting a refusal here).
  4. When `owned_checkout` is provided and validation is NOT `OWNED`: refuse with the same structured error codes WP02 established (reuse, do not reinvent).
- **Files**: `src/specify_cli/cli/commands/next_cmd.py` (~35 line diff)

### Subtask T011 - Root per-checkout runtime state at the owned checkout

- **Purpose**: Satisfy FR-007.
- **Steps**:
  1. When `OwnershipClaim.validation_result == OWNED`, pass `owned_checkout` (not the ambiently-resolved primary) as the `repo_root` argument to `_feature_runs_path()` (`src/runtime/next/runtime_bridge_io.py:143-145`) and to `get_merge_runtime_dir()` (`src/specify_cli/merge/workspace.py:32-34`) for every call site reachable from `next_step`'s body.
  2. Confirm neither of those two functions needs a signature change — they already accept `repo_root: Path` as a plain parameter (research D-6); this subtask is about WHAT next_cmd.py passes as that argument, not about changing their signatures.
  3. Do NOT touch `status/locking.py`'s cross-worktree status lock — it stays rooted at the shared git common-dir by design (data-model.md's explicit exclusion). Confirm no code path in this subtask accidentally reroutes it.
- **Files**: `src/specify_cli/cli/commands/next_cmd.py` (~25 line diff, same file as T010)
- **Validation**: After creating a mission with WP02's `--owned-checkout` flag, run `next --owned-checkout <path> ...` and inspect `<path>/.kittify/runtime/feature-runs.json` — the run record must appear there, and NOT under the primary checkout's `.kittify/runtime/feature-runs.json`.

### Subtask T012 - Tests for unchanged default behavior + new opted-in path

- **Purpose**: Regression net for FR-004 (unchanged non-opt-in behavior) and new coverage for FR-002/FR-007.
- **Steps**:
  1. In `tests/agent/test_context_validation_unit.py`, confirm existing `detect_execution_context`/`require_main_repo` tests pass unmodified.
  2. Add a new test: `next --owned-checkout <real-linked-worktree>` succeeds, and the resulting runtime-state file is written under that worktree, not the primary.
  3. Add a test: `next` from a generic (non-`.worktrees`) linked worktree WITHOUT `--owned-checkout` behaves identically before and after this WP's changes (byte-comparable decision output, aside from timestamps/run IDs) — this is the explicit regression proof for spec.md User Story 2 Acceptance Scenario #4.
- **Files**: `tests/agent/test_context_validation_unit.py` (~60 line diff)

## Test Strategy

- `.venv/bin/pytest tests/agent/test_context_validation_unit.py tests/runtime/ -q`
- Manually run `quickstart.md` step 5 against a local build.

## Risks & Mitigations

- **Risk**: The `@require_main_repo` decorator wraps `next_step` at the function-definition level (line 60) — a naive "check the flag inside the function body" approach runs AFTER the decorator's refusal already fired for `.worktrees`-literal paths. **Mitigation**: either (a) have `require_main_repo` itself accept/check a resolved `OwnershipClaim` passed via a context object before its own comparison, or (b) restructure so ownership resolution happens before the decorator is invoked (e.g., a thin undecorated dispatcher that checks ownership first, then calls the decorated implementation only on the non-opted-in path). Document which you chose and why in this WP's Activity Log — this is the one open architectural decision this plan deliberately left to implementation (plan.md IC-03 Risks).
- **Risk**: Merge/implement also use `@require_main_repo` (research D-1) — this WP does NOT extend `--owned-checkout` to those commands (out of scope; spec.md is scoped to `mission create`/`next` only). Confirm no accidental scope creep.

## Definition of Done

- [ ] `next --owned-checkout <path>` succeeds for a real linked worktree and roots runtime state there.
- [ ] `next` without `--owned-checkout` is behaviorally unchanged for both `.worktrees`-literal and generic linked-worktree callers.
- [ ] The status-lock relocation exclusion is respected (verified by a test asserting the lock path is unchanged).
- [ ] Architectural decision on the decorator-vs-ownership-check ordering is documented in the Activity Log below.

## Reviewer Guidance

- Verify the regression proof for generic-linked-worktree-without-opt-in explicitly (this is the easiest requirement to accidentally regress, since it requires proving a NEGATIVE — that nothing changed).
- Verify `merge`/`implement` were not touched (scope discipline).

**Implementation command**: `spec-kitty agent action implement WP03 --agent <name>`

## Activity Log

- 2026-08-11T13:37:00Z - system - Prompt created.
- 2026-08-11T18:14:51Z – python-pedro – shell_pid=28365 – Design: next uses a command-local dispatcher. Without --owned-checkout it invokes the existing require_main_repo wrapper unchanged. With the explicit flag it bypasses only that syntactic .worktrees guard, then immediately validates the claim via resolve_ownership_claim before runtime notice, charter preflight, mission lookup, or writes; only OWNED selects the claimed checkout as the effective root. Shared decorator, merge, and implement remain unchanged.
