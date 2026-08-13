---
work_package_id: WP01
title: Checkout-ownership validation primitive
dependencies: []
requirement_refs:
- FR-003
- FR-005
- FR-006
- FR-011
- NFR-004
- C-006
planning_base_branch: fix/worktree-owned-root-3328-v2
merge_target_branch: fix/worktree-owned-root-3328-v2
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-owned-root-3328-v2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-owned-root-3328-v2 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- at: '2026-08-11T13:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: ''
authoritative_surface: src/specify_cli/core/checkout_ownership.py
create_intent:
- src/specify_cli/core/checkout_ownership.py
- tests/core/test_checkout_ownership.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/checkout_ownership.py
- tests/core/test_checkout_ownership.py
- src/specify_cli/git/commit_helpers.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 - Checkout-ownership validation primitive

## Objective

Add ONE shared, git-topology-validated primitive — `resolve_ownership_claim()` in a new module `src/specify_cli/core/checkout_ownership.py` — that turns an explicit "treat this path as my owned checkout" request into a structured `OwnershipClaim` with a five-way `OwnershipValidationResult` (`OWNED`, `UNOWNED_NO_OPT_IN`, `NESTED`, `FOREIGN_OR_MISMATCHED`, `BROKEN_POINTER`). This is the foundation WP01/02/03/04/05 all build on (plan.md IC-01).

## Context

Issue [#3328](https://github.com/Priivacy-ai/spec-kitty/issues/3328) requires `mission create`/`next` to accept an explicit, validated worktree-ownership declaration instead of either refusing unconditionally or silently trusting ambient location. Research (`kitty-specs/worktree-owned-root-3328-01KZRG01/research.md`, D-1 through D-4) found:

- `is_worktree_context()` (`src/specify_cli/core/paths.py:281-328`) is the existing generic (gitdir-pointer-aware) worktree detector — reuse its approach, do not duplicate the gitdir-file parsing.
- `_is_worktree_of()` (`src/specify_cli/git/commit_helpers.py:609-634`) is the existing fail-closed common-dir comparator used by `safe_commit`. It is module-private (`_`-prefixed). This WP must expose it for reuse WITHOUT widening its existing contract or changing `safe_commit`'s behavior — prefer adding a public wrapper function in `commit_helpers.py` (e.g. `is_worktree_of(repo_root, worktree_root) -> bool`) that the private function delegates to internally, or vice versa (thin public alias). Read the existing function fully before deciding which minimizes diff.
- `read_worktree_registry()` (`src/specify_cli/coordination/surface_resolver.py:231-262`) shells `git worktree list --porcelain` and fails closed (raises `WorktreeRegistryUnavailable` on git failure). Its raw entries (each has a worktree path) are what the nested-worktree check in this WP must consume — do NOT use `_enclosing_worktree_root()` (same file, `.worktrees`-literal only — C-006 gap).

Read `kitty-specs/worktree-owned-root-3328-01KZRG01/data-model.md` in full before starting — it defines the exact entities (`Checkout`, `OwnershipClaim`, `OwnershipValidationResult`, `PerCheckoutRuntimeState`) and validation rules (6 numbered rules) this WP must implement precisely.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### Subtask T001 - Define `OwnershipValidationResult` and `OwnershipClaim`

- **Purpose**: Establish the typed vocabulary every other subtask and every downstream WP depends on.
- **Steps**:
  1. In `src/specify_cli/core/checkout_ownership.py`, define `OwnershipValidationResult` as a `str`-backed `Enum` (or `StrEnum` if the repo's Python baseline supports it) with exactly the five values from data-model.md: `OWNED`, `UNOWNED_NO_OPT_IN`, `NESTED`, `FOREIGN_OR_MISMATCHED`, `BROKEN_POINTER`.
  2. Define a frozen `@dataclass` `OwnershipClaim` with fields `claimed_checkout: Path`, `resolved_primary: Path`, `validation_result: OwnershipValidationResult`, `opted_in: bool`, and a `detail: str | None` field for the human-readable reason (feeds FR-011's structured errors).
  3. Define one exception class per non-`OWNED` outcome (or a single `CheckoutOwnershipError` carrying the `OwnershipValidationResult` as an attribute) — confirm which shape WP02/WP03 will consume most cleanly by re-reading `contracts/checkout-ownership-cli-contract.md`'s error-code table before committing to a shape.
- **Files**: `src/specify_cli/core/checkout_ownership.py` (new, ~60 lines for this subtask)
- **Parallel?**: No — foundation for T002-T005.
- **Notes**: Follow the repo's existing dataclass/enum conventions (grep `core/paths.py` and `core/context_validation.py` for house style before inventing a new one).

### Subtask T002 - Implement `resolve_ownership_claim()` for the `OWNED` and `UNOWNED_NO_OPT_IN` paths

- **Purpose**: The core entry point every caller (WP02, WP03) invokes.
- **Steps**:
  1. Signature: `resolve_ownership_claim(claimed_checkout: Path | None, *, resolved_primary: Path) -> OwnershipClaim`. When `claimed_checkout is None`, return immediately with `opted_in=False, validation_result=UNOWNED_NO_OPT_IN` — no git subprocess calls (NFR-001: zero added subprocess cost for non-opted-in callers).
  2. When `claimed_checkout` is provided, resolve both paths with `.resolve()` and compare via the reused `_is_worktree_of`-equivalent comparator (T001's public wrapper). If common-dirs match and `claimed_checkout == resolved_primary`, this is the trivial self-ownership case (spec.md Edge Cases) — return `OWNED` directly without invoking the nested-worktree check (a primary checkout cannot be "nested").
  3. If common-dirs match and `claimed_checkout != resolved_primary`, proceed to T003's nested check before finalizing `OWNED`.
- **Files**: `src/specify_cli/core/checkout_ownership.py` (+~50 lines)
- **Validation**: Unit test both branches directly (no subprocess mocking needed for the `None` branch; use a real temp git repo fixture for the checkout-provided branch — see T005).

### Subtask T003 - Implement the nested-worktree check

- **Purpose**: Satisfy FR-005 using the GENERIC registry data (C-006), not the `.worktrees`-literal helper.
- **Steps**:
  1. Call `read_worktree_registry(resolved_primary)` (import from `specify_cli.coordination.surface_resolver`). Handle `WorktreeRegistryUnavailable` by returning `BROKEN_POINTER` (fail-closed, NFR-004) — do NOT let the exception propagate uncaught.
  2. For each registry entry's worktree path (excluding the claimed checkout's own entry), check whether `claimed_checkout` is a strict descendant (`Path.is_relative_to()` or equivalent, resolved) of that entry's path. If yes, return `NESTED` with `detail` naming both paths.
  3. Otherwise, finalize `OWNED`.
- **Files**: same file (+~40 lines)
- **Parallel?**: Can be written alongside T004 (different branches of the same function, but touch the same file — coordinate via sequential commits, not literal parallel edits).

### Subtask T004 - Implement `FOREIGN_OR_MISMATCHED` and `BROKEN_POINTER` paths

- **Purpose**: Cover the remaining two refusal classes.
- **Steps**:
  1. When the common-dir comparator returns `False` (mismatch) rather than raising, return `FOREIGN_OR_MISMATCHED` with `detail` naming both common-dirs (spec.md Acceptance Scenario, User Story 2 #3).
  2. When any underlying `git rev-parse`/`git worktree list` subprocess fails (non-zero exit, `FileNotFoundError` for missing git binary, or a corrupted/unreadable `.git` file per spec.md Edge Cases), catch and return `BROKEN_POINTER` — never let a raw `KeyError`/`FileNotFoundError` escape `resolve_ownership_claim()`.
- **Files**: same file (+~30 lines)
- **Validation**: Test with a real second, unrelated `git init` temp repo (foreign case) and a temp worktree whose `.git` file is hand-corrupted after creation (broken-pointer case).

### Subtask T005 - Unit test suite

- **Purpose**: Prove all five `OwnershipValidationResult` outcomes against REAL git repositories (not mocks) — this is the regression net WP04/WP05 build on.
- **Steps**:
  1. In `tests/core/test_checkout_ownership.py`, use `tmp_path` + real `git init`/`git worktree add` subprocess calls (mirror the fixture style already used by `tests/runtime/test_paths_unit.py`'s worktree tests — read that file first for the house pattern).
  2. Cover: primary-self-ownership (`OWNED`), valid linked worktree (`OWNED`), no-opt-in (`UNOWNED_NO_OPT_IN`, assert ZERO git subprocess calls via a spy/mock on `subprocess.run` for this one case only), nested worktree (`NESTED`), foreign repo (`FOREIGN_OR_MISMATCHED`), corrupted gitdir pointer (`BROKEN_POINTER`).
  3. Assert `detail` is non-empty and names the actual paths for every non-`OWNED` case (FR-011).
- **Files**: `tests/core/test_checkout_ownership.py` (new, ~150-200 lines)

## Test Strategy

- All tests use real temporary git repositories (`tmp_path`, `subprocess.run(["git", ...])`) — no mocked git output, consistent with the repo's existing `tests/runtime/test_paths_unit.py` pattern and the mission's ATDD-first charter directive.
- Run: `.venv/bin/pytest tests/core/test_checkout_ownership.py -q`

## Risks & Mitigations

- **Risk**: Exposing `_is_worktree_of` changes its effective visibility/contract. **Mitigation**: add a public wrapper, keep the private function's body untouched; run the full `tests/git_ops/test_safe_commit_helper_integration.py` suite after the change to confirm zero behavior drift.
- **Risk**: `read_worktree_registry` import from `coordination.surface_resolver` could introduce a layering violation (`core/` importing from `coordination/`). **Mitigation**: check `tests/architectural/` for any existing import-direction fence before adding the import; if one exists and forbids this direction, raise it as a finding rather than silently violating it (do not add a bypass).

## Definition of Done

- [ ] `OwnershipValidationResult`, `OwnershipClaim`, and `resolve_ownership_claim()` exist in `src/specify_cli/core/checkout_ownership.py` and match data-model.md's entities exactly.
- [ ] All five validation outcomes are covered by real-git-repository unit tests, all passing.
- [ ] No existing test in `tests/git_ops/`, `tests/runtime/`, or `tests/architectural/` regresses.
- [ ] `ruff check` and `mypy --strict` pass with zero issues on the new file (DIR-006).

## Reviewer Guidance

- Confirm the nested-worktree check genuinely uses the generic registry data, not a `.worktrees`-literal shortcut (C-006 is the whole point of this WP).
- Confirm `UNOWNED_NO_OPT_IN` performs zero git subprocess calls (NFR-001).
- Confirm no raw, unstructured exception can escape `resolve_ownership_claim()` (NFR-004 fail-closed).

**Implementation command**: `spec-kitty agent action implement WP01 --agent <name>`

## Activity Log

- 2026-08-11T13:37:00Z - system - Prompt created.
