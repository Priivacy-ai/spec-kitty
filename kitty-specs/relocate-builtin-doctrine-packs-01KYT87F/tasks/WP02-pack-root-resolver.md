---
work_package_id: WP02
title: Shared pack-root resolver
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- NFR-005
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T19:45:00Z'
subtasks:
- T004
- T005
- T006
phase: Phase 1 - Foundation
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent:
- src/doctrine/pack_paths.py
- tests/doctrine/test_pack_root_resolver.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/pack_paths.py
- tests/doctrine/test_pack_root_resolver.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP02 — Shared pack-root resolver

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for the frontmatter profile before parsing further.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`
Resolve with **`spec-kitty agent profile show python-pedro`**. Do not read the raw `*.agent.yaml`.

---

## Objective
Create the single resolution seam `resolve_pack_root(tier)` in `src/doctrine/pack_paths.py`, correct in **both** an editable checkout and an installed wheel, fail-closed. This is the seam WP04 and WP06 repoint onto. Empirically confirmed feasible by the post-plan squad (build+install).

## Context (contract: contracts/resolve-pack-root.md)
- `packs/built-in/` is NOT a Python package (hyphen in `built-in`), so package-relative `files()` cannot address it — a filesystem resolver is required.
- Resolution order (built-in): (1) `SPEC_KITTY_PACKS_ROOT` env; (2) editable — nearest ancestor of `__file__` containing `packs/built-in/`; (3) installed — `files("doctrine").parent/"packs"/"built-in"` (verified: hatch `force-include` lands `packs/` as a site-packages sibling of `doctrine`); (4) else `PackRootNotFound`.
- Layer: doctrine — must NOT import charter/specify_cli (C-004). `files("doctrine")` is an in-layer self-reference, fine; call it **lazily inside the function** to avoid an import cycle with `doctrine/__init__.py`.

## Subtasks
### T004 — Implement `resolve_pack_root(tier, *, org_root=None, project_root=None) -> Path`
- Built-in: the 4-step order above. `org`/`project`: return the caller-supplied root (shared seam, tier-specific inputs).
- **`Path(__file__).resolve()` BEFORE** iterating `.parents` (symlinked editable installs otherwise miss repo-root `packs/`).
- Pure/idempotent; no mutation.

### T005 — `PackRootNotFound` + layer purity
- Define `PackRootNotFound(tier)`; raise on no-match (never fall open to a wrong tree).
- Confirm module imports only `os`, `pathlib`, `importlib.resources.files` — nothing upward. `test_layer_rules` must stay green.

### T006 — Two-layout + symlink test matrix (`tests/doctrine/test_pack_root_resolver.py`)
- **Editable**: from a repo checkout, resolves repo-root `packs/built-in/`.
- **Installed**: build a wheel, install into a clean venv (no repo `src/`), resolve to the site-packages `packs/built-in/`.
- **Symlinked-checkout** case (the pedro sub-risk): a dir-symlinked package still resolves repo-root `packs/` via `.resolve()`.
- **Fail-closed**: with no `packs/` anywhere and no env, raises `PackRootNotFound` (does not return a `src/doctrine` path).

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Worktrees per `lanes.json` lane.

## Definition of Done
- `resolve_pack_root` implemented per contract; `.resolve()` walk-up; fail-closed.
- Resolver test matrix green (editable + installed + symlink + fail-closed).
- `mypy --strict` + `ruff` clean; `test_layer_rules` green (no upward import).

## Risks
- Import cycle if `files("doctrine")` is called at module top level — keep it lazy.
- Symlinked editable installs — the `.resolve()` + symlink test is the guard.

## Reviewer guidance
Confirm the installed-layout test actually installs a wheel into a clean venv (not just `PYTHONPATH`), and that fail-closed is asserted (no silent fallback).
