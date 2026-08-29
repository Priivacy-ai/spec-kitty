---
work_package_id: WP04
title: Seam repointing
dependencies:
- WP02
- WP03
requirement_refs:
- FR-003
- FR-004
- NFR-005
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T19:45:00Z'
subtasks:
- T010
- T011
- T012
phase: Phase 1 - Relocation
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent:
- tests/doctrine/test_loader_fail_closed.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/loader.py
- src/doctrine/agent_profiles/repository.py
- src/doctrine/directives/repository.py
- src/doctrine/procedures/repository.py
- src/doctrine/tactics/repository.py
- src/doctrine/paradigms/repository.py
- src/doctrine/styleguides/repository.py
- src/doctrine/toolguides/repository.py
- src/doctrine/assets/repository.py
- src/doctrine/glossary_packs/repository.py
- src/charter/activation/catalog.py
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
- tests/doctrine/test_loader_fail_closed.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP04 — Seam repointing

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for the frontmatter profile first.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`
Resolve with **`spec-kitty agent profile show python-pedro`**. Do not read the raw `*.agent.yaml`.

---

## Objective
Repoint every reader of the moved content to resolve via `resolve_pack_root("built-in")` (WP02), so the graph and all per-kind content load from `packs/built-in/`. After this WP `load_built_in_graph()` returns 324/892 again.

## Subtasks
### T010 — Repoint `built_in_graph_source()` (`src/doctrine/drg/loader.py:115`)
- Return `resolve_pack_root("built-in")` instead of `Path(str(files("doctrine")))`.
- **Make it fail-closed**: drop the silent `except → Path(__file__).parent.parent` fallback (which would now point at the wrong, emptied tree). Let `PackRootNotFound` propagate.

### T011 — Repoint the 9 repository `built_in_dir` defaults `[P]`
- Each `<kind>/repository.py` `_default_built_in_dir()` currently does `files("doctrine.<kind>"); hasattr(...,"joinpath"); Path(str(resource.joinpath("built-in")))`. Replace with `resolve_pack_root("built-in") / "<kind>"`.
- **Drop the now-dead `hasattr`/`Path(str(...))` Traversable dance** — the resolver returns a real `Path`. Don't leave dead code.

### T012 — Repoint the string reader + the charter catalog + enumerated readers
- **`src/charter/activation/catalog.py` `_scan()`/`load_doctrine_catalog()` (line ~276)** — a SECOND, independent reader of the moved content: it scans `resolve_doctrine_root()/<kind>/"built-in"` for paradigms/directives/tactics/styleguides/toolguides/procedures/agent_profiles (30+ callers). Repoint onto `resolve_pack_root("built-in")/<kind>` (charter is above doctrine — importing the resolver is layer-legal). **If missed, charter activation/generation silently breaks build-green** (post-tasks squad BLOCKER).
- `specify_cli/cli/commands/agent/tasks_status_cmd.py:708,813` — replace the literal `"src/doctrine/agent_profiles/built-in"` with `resolve_pack_root("built-in")/"agent_profiles"`. Use a **module-level** `from doctrine.pack_paths import resolve_pack_root` (NOT function-local — #2986's shrink-only import ratchet fails on new function-local `from doctrine…`).
- Repoint any live-path reader flagged REVIEW in WP01 (`rewrite_opposed_by.py:192`, `upgrade_probe.py:8` are docstrings → leave).

- **Fail-closed loader test** (`tests/doctrine/test_loader_fail_closed.py`, part of T012, DIR-005): assert `load_built_in_graph()` **raises** (does not return an empty/partial graph) when `resolve_pack_root` cannot find `packs/built-in/` — proving the loader propagates `PackRootNotFound` rather than re-swallowing it.

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Worktrees per `lanes.json` lane.

## Definition of Done
- `load_built_in_graph()` returns 324/892 resolved from `packs/built-in/` (full identity gate is WP07).
- `charter/catalog.py` repointed; a charter selection (e.g. `load_doctrine_catalog()`) returns non-empty built-in sets (the BLOCKER guard — WP07 T022 adds the assertion).
- Anchor grep enumerating **all 9 kinds** returns 0: `git grep -E 'files\("doctrine\.(agent_profiles|directives|procedures|tactics|paradigms|styleguides|toolguides|assets|glossary_packs)"\)' src/` (NFR-005).
- Fail-closed loader test green (loader raises on `PackRootNotFound`, not empty graph).
- No function-local `from doctrine…` added (module-level only, #2986).
- `mypy --strict` + `ruff` clean.

## Risks
- A missed reader returns `[]` build-green — WP07 adds the exists-and-non-empty guard, but sweep thoroughly here.
- Function-local import regressing #2986 — keep module-level.

## Reviewer guidance
Verify fail-closed loader (no `__file__` fallback), dead Traversable guards removed, module-level import, and 0 remaining per-kind anchors.
