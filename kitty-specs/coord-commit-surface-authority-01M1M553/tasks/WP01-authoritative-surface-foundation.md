---
work_package_id: WP01
title: Authoritative-surface foundation
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-007
planning_base_branch: fix/coord-commit-surface-authority
merge_target_branch: fix/coord-commit-surface-authority
branch_strategy: Planning artifacts for this mission were generated on fix/coord-commit-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/coord-commit-surface-authority unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-commit-surface-authority-01M1M553
base_commit: 0b5e619d5956f9e3f6c5b62e12e521ab5425b391
created_at: '2026-09-03T18:17:16.219876+00:00'
subtasks:
- T001
- T002
- T003
- T004
history:
- at: '2026-09-03T00:00:00+00:00'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- src/specify_cli/coordination/surface_authority.py
- tests/coordination/test_surface_authority.py
- tests/coordination/test_surface_authority_goldens.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/surface_authority.py
- tests/coordination/test_surface_authority.py
- tests/coordination/test_surface_authority_goldens.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). Apply the resolved initialization, boundaries, directives, and tactics, then state which you applied. You implement inside `owned_files`; a small out-of-map edit is acceptable only with a one-line rationale.

## Objective

Create the **single canonical rule** for commit-surface authority as a pure, dependency-light module that BOTH the `cli` layer (`mission_create`, task commands) and the `coordination` layer (`commit_router`) can import without a cycle. This WP adds no consumers — it defines the rule and freezes today's behavior in goldens so the consumer WPs (WP02/03/04) can refactor safely.

**Why `coordination/` and not `cli/`**: `coordination/` currently imports zero symbols from `cli.commands.agent`; homing the helper in `cli` would force a `coordination→cli` inversion when `commit_router` consumes it (squad-architect finding, verified). Every dependency the rule needs (`MissionTopology`/`resolve_topology`, `ProtectionPolicy`, primary-target resolution) sits at or below the coordination layer.

Read first: [contracts/authoritative-surface.md](../contracts/authoritative-surface.md) (the authoritative spec for this module), [research.md](../research.md) D-001/D-003, [data-model.md](../data-model.md).

## Subtasks

### T001 — `coord_topology_reachable` (pure)
Add to `src/specify_cli/coordination/surface_authority.py`:
```python
def coord_topology_reachable(pr_bound: bool, primary_protected: bool, current_is_primary: bool) -> bool:
    """Coordination routing is reachable iff pr_bound and (primary_protected or current_is_primary)."""
    return pr_bound and (primary_protected or current_is_primary)
```
- Pure boolean; no I/O. `primary_protected` is the protection of the **primary target branch** (caller resolves via `ProtectionPolicy`), never the checkout.
- This is the predicate WP02 inserts into `_resolve_default_topology_phase`'s `pr_bound` arm.

### T002 — `resolve_surface_authority` (kind-aware verdict)
Add the `SurfaceVerdict` type and function per contract §2. Verdict rules (kind-aware):
- coord/lifecycle-kind + COORD/LANES_WITH_COORD + protected primary → `RouteToCoord` (surface=coordination; exit 0; redundant primary commit suppressed).
- coord-kind + unprotected primary → surface=primary (coord routing inert).
- primary/planning-kind + protected primary → `Refuse(remedy=<constant>)` (exit 1).
- primary-kind + unprotected → surface=primary.
- genuine no-op → `NoOp(reason)` (exit 0); wrong-surface → `Refuse` (NEVER NoOp) — map the router's `no_op_wrong_surface` label to Refuse.
- Define the remedy as a module constant (Sonar S1192): `--start-branch <feature-branch>` or `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1`.
- `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1` folds into `primary_protected=False` at the caller boundary (document in the docstring; the function takes the already-resolved bool).

### T003 — Unit tests (full matrix) `[P]`
`tests/coordination/test_surface_authority.py`: exhaustively cover `{artifact_kind ∈ (coordination, primary)} × {topology ∈ (SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD)} × {primary_protected ∈ (T,F)} × {current_is_primary ∈ (T,F)}` for both functions. Assert the RouteToCoord / Refuse / NoOp verdict and the surface/ref for each cell. Include the wrong-surface→Refuse and no-op→NoOp cases explicitly.

### T004 — Golden characterization harness `[P]`
Add the harness at **`tests/coordination/test_surface_authority_goldens.py`** (owned by this WP); keep all fixtures/expected-JSON **inline or under `tests/coordination/`** — do NOT place fixtures under `tests/specify_cli/cli/commands/agent/` (that collides with WP03's scope). WP03 (T013) and WP04 (T017) re-run this exact file, so its path is the shared contract surface. It freezes the CURRENT observable behavior of the six ledger rows in [contracts/authoritative-surface.md](../contracts/authoritative-surface.md) §ledger, BEFORE any consumer change:
- move-task lifecycle coord+protected → exit 0 (RouteToCoord)
- map-requirements planning coord+protected → exit 1
- mark-status coord+protected → no commit, exit 0
- move-task/map-requirements genuine no-op unprotected → exit 0 (typed reason)
- spec-commit `unchanged` → exit 0 + reason (#2739 regression guard)
- any commit-bearing wrong-surface → exit 1
Store expectations so WP03/WP04 can re-run them to prove no unintended drift. Assert JSON-mode exit codes, not only human output.

## Branch Strategy
Planning/base and merge target: `fix/coord-commit-surface-authority`. Execution worktrees are allocated per computed lane from `lanes.json` at implement time (one lane for this WP). Do not create branches manually.

## Definition of Done
- `surface_authority.py` exists with both pure functions + docstrings; `ruff` + `mypy` clean, zero suppressions.
- Full-matrix unit tests pass (T003).
- Golden harness (T004) captures the six ledger rows and passes against the CURRENT code (no consumer edits in this WP).
- No import from `cli.*` in the new module (assert the layering: `coordination/` stays cli-free).

## Reviewer Guidance (WP01 is the wave gate — verify before releasing WP02/03/04)
- Verify the module has NO `cli` imports (layering).
- Verify the kind-aware rule matches the contract exactly (especially wrong-surface→Refuse, and coord-kind-on-unprotected→primary).
- Verify goldens freeze CURRENT behavior (they must pass before WP02/03/04 touch anything), cover **all six** ledger rows, and assert **JSON-mode** exit codes.
- **Signature-diff gate (planner-priti):** diff the frozen `coord_topology_reachable` and `resolve_surface_authority` signatures + `SurfaceVerdict` shape against all three consumer call-shapes in [contracts/authoritative-surface.md](../contracts/authoritative-surface.md) §Consumers (mission_create rule-5 call, the two task-command shell helpers, commit_router `_commit_partition_group`). Only release the A/B/C wave once they fit — this avoids a later out-of-lane edit to this WP's file.
- **Pre-authorized exception:** if a consumer WP later finds a genuine contract gap, a *small, documented* out-of-map edit to `surface_authority.py` (with a one-line rationale) is acceptable rather than an unplanned lane violation.
