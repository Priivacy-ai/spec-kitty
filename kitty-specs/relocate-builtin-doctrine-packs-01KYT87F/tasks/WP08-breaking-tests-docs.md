---
work_package_id: WP08
title: Breaking tests, docs and CHANGELOG
dependencies:
- WP04
- WP05
- WP06
requirement_refs:
- FR-010
- FR-011
- FR-012
- NFR-003
- NFR-004
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T19:45:00Z'
subtasks:
- T023
- T024
- T025
phase: Phase 1 - Closeout
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- docs/migrations/relocate-builtin-doctrine-packs.md
execution_mode: code_change
model: ''
owned_files:
- tests/doctrine/drg/test_builtin_graph_seam.py
- tests/doctrine/test_wheel_packaging.py
- tests/architectural/test_no_dead_doctrine_paths.py
- docs/migrations/relocate-builtin-doctrine-packs.md
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP08 — Breaking tests, docs and CHANGELOG

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for the frontmatter profile first.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`
Resolve with **`spec-kitty agent profile show python-pedro`**. Do not read the raw `*.agent.yaml`.

---

## Objective
Update the tests the move breaks (that aren't owned by WP06), sweep live references, and communicate the breaking path change. Closeout.

## Subtasks
### T023 — Update the three breaking tests — FR-010
- `tests/doctrine/drg/test_builtin_graph_seam.py`: `built_in_graph_source().name == "doctrine"` → `"built-in"`; no-`graph.yaml`/fragments-present assertions point at `packs/built-in/`.
- `tests/doctrine/test_wheel_packaging.py`: hardcoded `doctrine/<kind>/built-in/…` wheel paths → **flattened** `packs/built-in/<kind>/…` (NO naive `doctrine/`→`packs/built-in/` replace — the inner `built-in` is dropped); invert the "legacy absent" assertion.
- `tests/architectural/test_no_dead_doctrine_paths.py`: its `_SRC_ROOT`-scoped scan + the pinned exact discriminator (`doctrine-daphne.agent.yaml`, `graph.yaml`) go red on the move. Update the pinned list; **record the justification in this commit** (NFR-003 discipline). This interacts with #3036 — note it, do NOT attempt #3036's full reframing here.

### T024 — Live-reference sweep + committed guard + docs regen — FR-011
- Sweep live (non-ADR) docs/prose for moved `src/doctrine/<kind>/built-in` / fragment paths; update to `packs/built-in/`. Leave historical ADR snapshots immutable.
- **Committed guard** (extend `test_no_dead_doctrine_paths.py`): assert `git grep` of live `docs/` (excluding `docs/adr/`) for `src/doctrine/<kind>/built-in` and `src/doctrine/*.graph.yaml` returns **0** — so the sweep is observable, not eyeballed.
- Regenerate the docs retrieval-index + completion-manifest (name the exact `spec-kitty docs …` regen command). Audit `.gitignore` didn't swallow anything.

### T025 — Migration note + CHANGELOG + follow-on tracking — FR-012 / DIR-009 / DIR-012
- `docs/migrations/relocate-builtin-doctrine-packs.md` mirroring `shared-package-boundary-cutover.md` (what moved, new paths, no runtime shim, rollback note).
- `CHANGELOG.md` Unreleased entry (breaking path change).
- **Follow-on tracking**: the migration note must record two follow-ons so deferred work isn't lost — (a) the **Phase 1b `missions/` relocation** (first task: cross-layer missions-reader inventory), and (b) Phase 2 loader/schema convergence.
- PR-body notes (out of scope to fix here): CLAUDE.md's "Deferred Items" still lists **#1624 (already closed)**; and confirm the **DIR-012 sub-issue under #2467** was filed before implement (pre-implement checklist item, tasks.md header).

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Worktrees per `lanes.json` lane.

## Definition of Done
- The three breaking tests updated + green; discriminator change justified in-commit.
- Live refs swept; retrieval-index/completion-manifest regenerated; ADR snapshots untouched.
- Migration note + CHANGELOG added; full `tests/doctrine` + `tests/architectural` + `test_no_legacy_terminology` green; `mypy`/`ruff` clean.

## Risks
- Naive find/replace on `test_wheel_packaging` (flatten off-by-one) — update to the flattened paths explicitly.
- Editing an immutable ADR snapshot — only live docs.

## Reviewer guidance
Confirm flattened paths (no inner `built-in`), the #3036 note (not a fix attempt), and that ADR snapshots are untouched.
