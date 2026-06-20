---
work_package_id: WP01
title: Extract the guarded read-side seam (foundation)
dependencies: []
requirement_refs:
- FR-001
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: feat/read-side-surface-resolver-adoption
merge_target_branch: feat/read-side-surface-resolver-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/read-side-surface-resolver-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-side-surface-resolver-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2344320"
history:
- at: '2026-06-20T14:30:00Z'
  actor: claude
  note: WP authored from plan IC-01 (FR-001/FR-004/FR-005-invariant). Foundation.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/
create_intent:
- tests/specify_cli/missions/test_resolve_handle_to_read_path.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/missions/test_resolve_handle_to_read_path.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` (`src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`); acknowledge its initialization declaration.

## Objective
Extract the ONE guarded read-side seam `resolve_handle_to_read_path(repo_root, handle, *, require_exists: bool = False) -> Path` in `src/specify_cli/missions/_read_path_resolver.py`, **lifted from the working prototype** `orchestrator_api/commands.py:_resolve_mission_dir` (≈285-347) + `_read_primary_meta` (≈251). This is the foundation every migration WP depends on. (IC-01; FR-001, FR-004, FR-005-invariant)

## Context (all verified by the anti-laziness squad — NOT phantom)
- The prototype already implements the exact pattern: read primary meta → `resolve_declared_mid8(meta, slug)` (`coordination/surface_resolver.py:453`, signature `(meta: dict, mission_slug: str) -> str`) → fail-closed coord-declared gate → `resolve_mission_read_path`.
- **THE #1718 TRAP (binding):** `resolve_mission_read_path` chooses coord ONLY when the coord worktree directory EXISTS on disk (`_read_path_resolver.py:240-245`). So deriving a non-empty mid8 is ORTHOGONAL to the create-window→primary contract — a declared-but-unmaterialized coord still resolves PRIMARY. The seam MUST route through `resolve_mission_read_path` (existence-gated), **NEVER** `resolve_status_surface_with_anchor` (which composes + returns the coord path for an unmaterialized coord → would regress #1718).
- `assert_safe_path_segment` is at `core/paths.py:40` and is already called in this module (`:510`).

## Subtasks
### T001 — Extract the seam + the shared `_read_primary_meta`/gate
- Add `resolve_handle_to_read_path(repo_root, handle)` to `_read_path_resolver.py`. Factor `_read_primary_meta(repo_root, handle) -> (meta, declares_coordination)` + the topology gate OUT of `orchestrator_api/commands.py` into a shared helper the seam uses (so the orchestrator becomes a consumer, not a 7th cascade). Body: `assert_safe_path_segment` → primary-meta probe → `resolve_declared_mid8` → fail-closed gate → `resolve_mission_read_path`.
### T002 — Routing invariant (FR-005) + `require_exists` passthrough
- The seam returns `resolve_mission_read_path(repo_root, handle, mid8, require_exists=require_exists)`. It MUST NOT call `resolve_status_surface_with_anchor`. Add an inline comment citing #1718 + the existence-gate rationale. **The `require_exists` passthrough is load-bearing for WP04:** the equivalence matrix observes the read leg with `require_exists=True` (so coord-empty/coord-deleted RAISE a typed error); when WP04 re-points that leg to the seam it passes `require_exists=True`, and the seam MUST forward it unchanged so the out-of-scope `*/slug-mid8` aggregate cells' raise-on-missing observation is preserved (WP04 must not disturb them).
### T003 — Guard the segment (FR-004)
- `assert_safe_path_segment(handle)` BEFORE any `KITTY_SPECS_DIR` join / `_read_primary_meta`. A traversal handle is rejected before composition.
### T004 — Re-point the orchestrator
- `orchestrator_api/commands.py:_resolve_mission_dir` consumes the seam (or the shared helper) — eliminate its now-duplicate cascade. Behavior-preserving (the orchestrator's M5 fail-closed semantics are exactly the seam's).
### T005 — Seam unit tests
- `tests/specify_cli/missions/test_resolve_handle_to_read_path.py`: (a) `<slug>-<mid8>`/full-id resolves the same dir as `resolve_mission_read_path` directly; (b) bare-slug + coord-fresh → coord dir (mid8 derived from primary meta); (c) **declared-but-unmaterialized coord + bare slug → PRIMARY** (the #1718 cell — derive mid8 but still primary because no worktree); (d) traversal handle → raises at `assert_safe_path_segment`; (e) declared-coord + no derivable mid8 → fail-closed raise. Realistic fixtures (26-char ULID, real `.worktrees/<slug>-<mid8>-coord/` layout).

## Branch Strategy
Planning/base + merge target: `feat/read-side-surface-resolver-adoption`. Worktree per lane.

## Definition of Done
- [ ] `resolve_handle_to_read_path(repo_root, handle, *, require_exists=False)` exists in `_read_path_resolver.py`, lifted from the prototype; one definition (NFR-004); `require_exists` forwarded to `resolve_mission_read_path` (WP04 depends on it).
- [ ] Routes through `resolve_mission_read_path`, NEVER the surface (mutation: route via surface → the create-window test FAILS).
- [ ] Segment guarded (FR-004); traversal rejected.
- [ ] Orchestrator re-pointed to the seam; its duplicate cascade gone; behavior-preserving.
- [ ] All 5 seam unit-test cases pass; ruff + mypy --strict clean.

## Risks / Reviewer guidance
- **Risk**: re-introducing the #1718 trap by routing through the surface. The create-window→PRIMARY unit test (with a NON-empty derived mid8) is the guard — insist it bites.
- **Reviewer**: confirm the seam never references `resolve_status_surface_with_anchor`; confirm the orchestrator's old cascade is gone (not just duplicated); confirm `<slug>-<mid8>` resolution is unchanged.

## Activity Log

- 2026-06-20T16:21:58Z – claude:opus:python-pedro:implementer – shell_pid=2334548 – Assigned agent via action command
- 2026-06-20T16:30:35Z – claude:opus:python-pedro:implementer – shell_pid=2334548 – Seam + orchestrator re-point + 6 unit tests; ruff+mypy clean; lane commit 1e11738f7
- 2026-06-20T16:30:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=2344320 – Started review via action command
- 2026-06-20T16:35:06Z – user – shell_pid=2344320 – reviewer-renata APPROVE: seam single+guarded, existence-gated routing (#1718 mutation confirmed), orchestrator cascade removed, require_exists forwarded, 6 tests+ruff+mypy green
