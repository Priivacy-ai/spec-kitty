---
work_package_id: WP03
title: Content relocation (git mv, flatten)
dependencies:
- WP01
- WP02
requirement_refs:
- C-001
- FR-001
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T19:45:00Z'
subtasks:
- T007
- T008
- T009
phase: Phase 1 - Relocation
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: packs/built-in/
create_intent:
- packs/built-in/
execution_mode: code_change
model: ''
owned_files:
- packs/built-in/**
- src/doctrine/agent_profiles/built-in/**
- src/doctrine/directives/built-in/**
- src/doctrine/procedures/built-in/**
- src/doctrine/tactics/built-in/**
- src/doctrine/paradigms/built-in/**
- src/doctrine/styleguides/built-in/**
- src/doctrine/toolguides/built-in/**
- src/doctrine/assets/built-in/**
- src/doctrine/glossary_packs/built-in/**
- src/doctrine/*.graph.yaml
- .gitignore
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP03 — Content relocation (git mv, flatten)

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for the frontmatter profile first.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`
Resolve with **`spec-kitty agent profile show python-pedro`**. Do not read the raw `*.agent.yaml`.

---

## Objective
Physically relocate the built-in **content** to `packs/built-in/` via `git mv` (history preserved), flattening `<kind>/built-in/` → `packs/built-in/<kind>/`. Content/data only — **no `.py` import code moves** (the two asset-payload `.py` from WP01's whitelist move as data). Do NOT touch `missions/` or `schemas/` (deferred/stay).

## Context
- Use `content-manifest.json` (WP01) as the exact source set. The move is complete iff the moved set == the manifest.
- The loader/repositories are NOT repointed here (that is WP04) — after this WP the graph will fail to load until WP04 lands; that is expected within the lane sequence.

## Subtasks
### T007 — `git mv` the 9 kind dirs (flatten)
- For each of the 9 kinds: `git mv src/doctrine/<kind>/built-in/  packs/built-in/<kind>/` — **drop the inner `built-in/` level**. The sibling `repository.py` STAYS.
- Preserve history (`git mv`, not copy+delete).

### T008 — `git mv` the 14 fragments
- `git mv src/doctrine/*.graph.yaml  packs/built-in/` (all 14; authoritative glob).

### T009 — gitignore audit + move-set verification
- Confirm no `.gitignore` pattern (`packs/`, `built-in/`, `*.yaml` under a broad ignore) swallows the new tree — `git status --ignored` on `packs/`.
- Assert the moved set equals `content-manifest.json` exactly; assert **no dual-home** (nothing left under `src/doctrine/<kind>/built-in/` or `src/doctrine/*.graph.yaml`).

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Worktrees per `lanes.json` lane.

## Definition of Done
- `packs/built-in/<kind>/…` populated (flattened) for all 9 kinds + 14 fragments at `packs/built-in/`.
- **Every** move-set path is a rename, not copy+delete: `git diff --name-status -M` shows `R` for each, and the rename count equals the manifest count (not a single sampled file).
- Moved set == manifest; no dual-home; gitignore clean.
- (Do NOT gate on "graph loads" — that requires WP04's loader repoint.)

## Risks
- Naive flatten mistakes (`packs/built-in/<kind>/built-in/`) — drop the inner level exactly.
- Accidentally moving `missions/`/`schemas/` — they STAY.

## Reviewer guidance
Verify `git mv` (history), the flatten (no inner `built-in/`), manifest set-equality, and that `missions/`+`schemas/` are untouched.
