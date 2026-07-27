---
work_package_id: WP04
title: Placement adoption (core/worktree.py)
dependencies:
- WP01
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "3023663"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/worktree.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/core/worktree.py
- tests/git_ops/test_worktree.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read: `spec.md` **FR-002** (placement) + **C-008**; `plan.md` **IC-WT** + the brownfield note (the
orthogonal `:304` DeprecationWarning); `contracts/behavioral-contracts.md` **C-PLACEMENT** (compose from the
factory placement projection, naming via `mission_dir_name`, MUST NOT change the on-disk placement path);
`research/pre-refactor/pedro-feasibility.md` **PR-5** (collapse the two-arm join first).

## Objective

Replace the two `feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name` placement joins
(`core/worktree.py:384` reuse arm, `:396` create arm) with the factory's placement projection
(`CommitTarget` / `resolve_placement_only` / `ArtifactPlacementFragment`). Naming stays via the
`mission_dir_name` seam (unchanged). **Idempotency is the hard gate (NFR-004): the on-disk placement path MUST
be byte-identical before/after.**

## Subtask guidance

### T017 — PR-5 pre-refactor (behavior-preserving)
Collapse the duplicated `:384`/`:396` join into ONE local compose helper first, both arms call it. WP01 net +
`test_worktree.py` stay green. This makes T018 a one-line swap at one site.

### T018 — Adopt the factory placement projection
Route the single compose helper to the factory placement projection instead of the ad-hoc join. Read the
projection from the context; do not re-derive `mid8`/root inline (boundary contract). Keep `mission_dir_name`
as the naming seam.

### T019 — Idempotency
Add/extend a test asserting the resolved `feature_dir` (reuse-arm == create-arm) is **byte-identical** to the
pre-adoption value for a given `(worktree_path, branch_name)` — no on-disk worktree churn (NFR-004/C-PLACEMENT).

### T020 — Clean
`ruff`/`mypy` clean ≤15. The orthogonal `DeprecationWarning` at `core/worktree.py:304` is unrelated to
placement; under C-008, if you touch its code or it is trivially due, fix it in-change (don't litigate) — do
not use "it's out of scope" as an escape to leave adjacent breakage you actually hit.

## Definition of Done
- [ ] The two placement joins compose from the factory placement projection; `mission_dir_name` seam intact.
- [ ] On-disk placement path byte-identical before/after (idempotency, NFR-004); WP01 net + `test_worktree.py` green.
- [ ] `ruff`/`mypy` clean ≤15, no suppressions. **C-008**: adjacent breakage fixed in-change.

## Reviewer guidance
The single most important check: the placement PATH did not change (idempotency). Confirm via the before/after
assertion, not by inspection. Confirm naming still flows through `mission_dir_name`, not a re-derived join.

## Activity Log

- 2026-06-17T06:21:26Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – Assigned agent via action command
- 2026-06-17T06:39:08Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – WP04 placement complete (compose seam, idempotency byte-identical, 60 pass). FORCE: flattened-mission guard. Orchestrator-driven.
- 2026-06-17T06:39:10Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3023663 – Started review via action command
- 2026-06-17T06:42:21Z – user – shell_pid=3023663 – APPROVE. FR-002 determination: Case (a) — resolve_placement_only genuinely does NOT apply. That function resolves which branch/ref planning artifacts commit to (CommitTarget with ref+topology), operating on repo_root+mission_slug. The worktree.py join composes a filesystem path WITHIN an already-known worktree_path (worktree_path/kitty-specs/branch_name) — a different operation that cannot be delegated to resolve_placement_only. The docstring correctly captures 'aligned with' (same naming seam, not a delegation). No mid8/root re-derivation inline; branch_name flows from mission_dir_name. Adoption is genuine. NFR-004 idempotency: test_idempotency_before_after_byte_identical captures before/after independently and asserts equality with a descriptive error message — not a tautology; test_reuse_arm_equals_create_arm additionally asserts expected path, preventing vacuous equality. Boundary contract: both former inline joins (:411 reuse, :423 create) call the single helper. str(KITTY_SPECS_DIR) cast is redundant (KITTY_SPECS_DIR is already str) but benign — no masking, mypy clean. C-008: 38 test methods received -> None + MonkeyPatch annotation. ruff+mypy clean, complexity <=15, no suppressions. 60/60 tests pass.
