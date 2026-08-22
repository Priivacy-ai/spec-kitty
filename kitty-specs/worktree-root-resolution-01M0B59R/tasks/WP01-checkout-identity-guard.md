---
work_package_id: WP01
title: Checkout-identity guard foundation
dependencies: []
requirement_refs:
- FR-001
- FR-008
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
history:
- at: '2026-08-18T20:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/core/checkout_identity.py
create_intent:
- src/specify_cli/core/checkout_identity.py
- tests/specify_cli/core/test_checkout_identity.py
- tests/specify_cli/core/test_must_not_flip_anchors.py
- tests/architectural/test_write_refusal_single_channel.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/checkout_identity.py
- tests/specify_cli/core/test_checkout_identity.py
- tests/specify_cli/core/test_must_not_flip_anchors.py
- tests/architectural/test_write_refusal_single_channel.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Checkout-identity guard foundation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

This is the **foundation** WP. It introduces one additive **checkout-identity guard** that every in-scope write command (WP02–WP06) later adopts, and it locks in two governance invariants the mission rests on.

Done when:
- `src/specify_cli/core/checkout_identity.py` exposes `resolve_checkout_identity(cwd, intent) -> CheckoutIdentity` plus the `FailClosedRefusal` value object (the **single** refusal seam).
- The guard decides ownership from **decidable** local git state (worktree-pointer topology + ownership claim) — **never** a clone-vs-primary guess (spec C-005).
- `intent=PRIMARY_READ` returns `canonical_target` unchanged (deliberate anchors are never flipped — FR-008).
- Unit tests cover {owner-primary, foreign-lane-worktree, nested-clone} × {WRITE, PRIMARY_READ}.
- A must-not-flip **characterization** test suite keeps the deliberate primary-read anchors GREEN (#2320/#3328).
- An **architectural** test proves no in-scope write-refusal is constructed outside the `FailClosedRefusal` seam (makes NFR-003's "100%" enforced).

## Context & Constraints

- Read: `.kittify/charter/charter.md`, [plan.md](../plan.md) (Structure Decision + reframe note), [data-model.md](../data-model.md) (`CheckoutIdentity`, `FailClosedRefusal`, INV-1…INV-6), [contracts/resolver-and-verdict-contracts.md](../contracts/resolver-and-verdict-contracts.md) (C-1, C-2), [research.md](../research.md) (Decision 0/1).
- **CRITICAL — additive only.** This WP MUST NOT edit `src/specify_cli/core/paths.py`. The `get_main_repo_root` primitive there has ~130 callers; flipping it would regress the deliberate anchors. The nested-clone boundary fix in `paths.py`/`support.py` belongs to **WP07**.
- The reframe (post-plan squad): standalone clones already resolve to self; the clone/primary split is undecidable and moot. The real distinction is **invocation ownership** (owns target checkout vs foreign lane worktree). The remediation is the **#3128 fail-closed refusal**, not a checkout-local write redirect.
- Prior art to generalize, not move: `is_worktree_context` (`core/paths.py:281`, used at `core/mission_creation.py:483`) already refuses worktree contexts for `specify`. Reuse its worktree-pointer parsing approach; do not relocate it.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Populated by finalize-tasks. Execution worktrees are allocated per computed lane from `lanes.json`.

## Subtasks & Detailed Guidance

### Subtask T001 – Create `core/checkout_identity.py` with the value objects

- **Purpose**: Establish the single canonical authority for invocation ownership + the refusal shape.
- **Steps**:
  1. Define `CheckoutIdentity` (dataclass, frozen): `invoking_root: Path`, `canonical_target: Path`, `is_owner: bool`, `intent: Intent`.
  2. Define `Intent` enum: `WRITE`, `PRIMARY_READ`.
  3. Define `FailClosedRefusal` (frozen): `refusal_path: Path`, plus a `message() -> str` that embeds `refusal_path` verbatim (NFR-003). This is the ONLY constructor of a write-refusal in the codebase.
  4. Define `resolve_checkout_identity(cwd: Path, intent: Intent) -> CheckoutIdentity`.
- **Files**: `src/specify_cli/core/checkout_identity.py` (new).
- **Notes**: Keep the module dependency-light (stdlib + existing `core` helpers). No import of `paths.get_main_repo_root` mutation.

### Subtask T002 – Ownership decision from decidable git state

- **Purpose**: Decide `is_owner` without an undecidable clone guess (C-005).
- **Steps**:
  1. Resolve the invoking checkout root from `cwd` by **parsing `.git` DIRECTLY** — read `cwd`'s own `.git` (a directory ⇒ this checkout is its own root; a `gitdir:` pointer file with `.git/worktrees/<name>` topology ⇒ the worktree the pointer names). **MUST NOT** route through `locate_project_root` / `resolve_canonical_root` / `get_main_repo_root` — those re-anchor a nested clone / linked worktree to the outer primary, which is exactly the WP07 defect; calling them here would make T004's nested-clone ownership assertion unsatisfiable until WP07 lands and would couple this foundation WP to WP07.
  2. Determine `canonical_target` for the command's intent — for `WRITE` it is where the command's canonical write deliberately lives (often the primary for status/repair; the invoking checkout for checkout-local writes).
  3. `is_owner = True` when `invoking_root` owns/equals `canonical_target`, OR the invocation legitimately owns the worktree per an ownership claim (reuse `core/checkout_ownership.resolve_ownership_claim` where applicable). Foreign lane worktree → `is_owner = False`.
  4. Use worktree-pointer topology (`.git/worktrees/<name>`) to detect a linked worktree; a bare `.git` directory is its own checkout (do NOT attempt to classify it as a secondary clone).
- **Files**: `src/specify_cli/core/checkout_identity.py`.
- **Notes**: INV-4 — decidable inputs only. The direct-`.git`-parse rule is what keeps this WP genuinely independent of WP07.

### Subtask T003 – `PRIMARY_READ` intent never flips

- **Purpose**: Preserve deliberate primary-read anchors (#2320/#3328) — FR-008.
- **Steps**: For `intent == PRIMARY_READ`, return `canonical_target` unchanged regardless of `invoking_root`; `is_owner` is informational only and MUST NOT redirect the target.
- **Files**: `src/specify_cli/core/checkout_identity.py`.
- **Notes**: INV-2. This is what stops the "merge into wrong branch" regression (#3328).

### Subtask T004 – Unit tests for the guard [P]

- **Purpose**: Lock the ownership matrix.
- **Steps**: Build fixtures for {owner-primary, foreign-lane-worktree, nested-clone}. Assert `is_owner`/`canonical_target` for each × {WRITE, PRIMARY_READ}. Assert a foreign-lane WRITE yields a `FailClosedRefusal` whose message contains the target path.
- **Files**: `tests/specify_cli/core/test_checkout_identity.py` (new).
- **Validation**: nested-clone WRITE is owner (writes self); foreign-lane WRITE is non-owner (refuses); PRIMARY_READ target never differs from `canonical_target`.

### Subtask T005 – Must-not-flip characterization tests [P]

- **Purpose**: Pin the deliberate anchors GREEN so later WPs cannot regress them (SC-003).
- **Steps**: Characterize the current behavior of `get_feature_target_branch`, `resolve_merge_target_branch` (`core/paths.py`) and the `mission_runtime/resolution.py` primary-read closures — assert they still anchor on primary. These are GREEN on base and MUST stay green.
- **Files**: `tests/specify_cli/core/test_must_not_flip_anchors.py` (new).
- **Notes**: Read-only characterization — do not modify the anchors.

### Subtask T006 – NFR-003 single-channel architectural test [P]

- **Purpose**: Make "100% of refusals name the path" an enforced invariant.
- **Steps**: AST/grep architectural test asserting that no in-scope write command raises an ad-hoc refusal string — every write-refusal routes through `FailClosedRefusal`. Scope the allowlist to the seam module.
- **Files**: `tests/architectural/test_write_refusal_single_channel.py` (new).
- **Validation**: adding a stray `raise ... "refuse"` in an in-scope command makes this test red.

## Test Strategy (required)

- Run: `pytest tests/specify_cli/core/test_checkout_identity.py tests/specify_cli/core/test_must_not_flip_anchors.py tests/architectural/test_write_refusal_single_channel.py -q`.
- The guard's own tests are not red-first (the unit is new); the red-first regressions live in WP02–WP07 which adopt the guard.
- Keep `ruff`/`mypy` clean; complexity ≤15.

## Risks & Mitigations

- **Risk**: touching `paths.get_main_repo_root` blasts ~130 callers. **Mitigation**: additive module; WP07 owns the paths.py boundary fix.
- **Risk**: over-broad ownership → owner invocations wrongly refuse. **Mitigation**: T004 asserts owner-primary always proceeds.

## Review Guidance

- Confirm no edit to `core/paths.py`.
- Confirm PRIMARY_READ path is provably non-flipping (T003 + T005).
- Confirm the refusal seam is the sole channel (T006).

## Activity Log

- 2026-08-18T20:00:00Z – system – Prompt created.
