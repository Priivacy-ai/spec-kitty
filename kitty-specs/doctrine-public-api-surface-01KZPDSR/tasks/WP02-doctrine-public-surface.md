---
work_package_id: WP02
title: Doctrine public surface + negative guard
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-007
- FR-008
- NFR-004
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase 2 - Surface
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent:
- src/doctrine/api.py
- tests/architectural/test_doctrine_public_surface.py
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/doctrine/api.py
- src/doctrine/__init__.py
- tests/architectural/test_doctrine_public_surface.py
- tests/architectural/test_doctrine_wheel_closure.py
- tests/architectural/test_no_dead_symbols.py
- CHANGELOG.md
role: implementer
tags: []
tracker_refs: []
wp_code: WP02
---

# Work Package Prompt: WP02 — Doctrine public surface + negative guard

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and apply its initialization, boundaries, directives,
and tactics before reading further. State which you applied.

## Objective

Create the single curated public surface `src/doctrine/api.py` (explicit `__all__`), pin it in
the wheel-closure test, add the INTERNAL negative guard, resolve the dead-symbol interaction,
and record the contract change (CHANGELOG + charter C-007 extension). This is the manifest the
future `spec-kitty-doctrine` wheel exports (FR-001/FR-008/FR-007).

## Context & Constraints

- Consumes WP01's finalized disposition table (which paths are PUBLIC vs INTERNAL).
- **Dead-symbol wiring (critical):** the charter facades (WP03) will re-export PUBLIC symbols
  **from `doctrine.api`**, so `doctrine.api` gets live callers and `test_no_dead_symbols.py`
  does real work. Only genuinely caller-less wheel-only exports use its `_SYMBOL_ALLOWLIST` with
  a tracker ref — do NOT blanket-allowlist the whole surface.
- C-001: `doctrine/api.py` exists for charter + the wheel, NOT for direct runtime import. Do not
  advertise it as a runtime door.
- DIR-006/007: `mypy --strict` clean + docstrings on every public symbol.

## Subtasks

### T005 — Create `src/doctrine/api.py` with curated `__all__`
- Import and re-export the PUBLIC symbols from their origin submodules; declare `__all__`
  explicitly. Keep `doctrine/__init__.py` minimal (its current 3 symbols) — the api surface is
  the enumerable one. Docstring each symbol or the module.

### T006 — Update `test_doctrine_wheel_closure.py`
- Make it pin the real `doctrine.api.__all__` (not just the manifest shape), so the wheel would
  export exactly this surface.

### T007 — New `test_doctrine_public_surface.py`
- Positive: every name in `doctrine.api.__all__` is importable + non-None.
- **Negative (FR-007):** the truly-INTERNAL set from WP01 appears in neither `doctrine.api.__all__`
  nor any `charter.*` facade `__all__`. **Discover facade modules dynamically** (glob
  `src/charter/*.py`), so the guard stays valid as WP03 adds `charter.missions`/`model_routing`/
  `assets` — do NOT hard-code a facade list (it would run before WP03 and go stale).
- **Live-caller assertion (post-tasks squad):** assert every `doctrine.api.__all__` symbol has ≥1
  in-repo importer that is a `charter.*` facade (i.e. PUBLIC `_FACADE_TABLE` rows literally name
  `doctrine.api`). Without this, an implementer can route PUBLIC symbols through the origin
  submodule (identity still passes) and `doctrine.api` gets no live caller — the manifest's whole
  point is lost while both existing gates stay green.

### T008 — No-dead-symbol allowlist for wheel-only exports ONLY
- Allowlist entries are permitted **only** for genuine wheel-only exports (a symbol external
  consumers need that has no in-repo caller even after facades exist), each with a tracker
  reference. **Forbid allowlisting a PUBLIC symbol that a facade should front** — those must get a
  live `doctrine.api` caller via T007's assertion, not a silenced gate. No blanket escape.

### T009 — CHANGELOG + charter C-007 extension  [P]
- Add a consumer-facing `CHANGELOG.md` entry (DIR-009) describing the new doctrine public surface
  and the strengthened boundary. Cross-reference the C-007-mission extension note from WP01.

## Branch Strategy

Base and merge target: `feat/doctrine-public-api-surface`. Worktree per lane from `lanes.json`.
Implement via `spec-kitty agent action implement WP02 --agent <name>` (after WP01).

## Definition of Done

- [ ] `doctrine/api.py` exists with explicit, docstringed `__all__`; `mypy --strict` clean.
- [ ] wheel-closure pins the real surface; public-surface positive + INTERNAL-negative tests green.
- [ ] dead-symbol interaction resolved via facade-callers (coordinate w/ WP03) + ticketed allowlist only where needed.
- [ ] CHANGELOG + C-007-mission note recorded.

## Risks & Reviewer Guidance

- **Risk**: collapsing the dead-symbol gate into a blanket allowlist (defeats its value).
  Reviewer: confirm the allowlist holds only genuine wheel-only exports with tickets, and that
  WP03's `_FACADE_TABLE` points PUBLIC symbols at `doctrine.api`.
- **Reviewer**: confirm `doctrine/__init__.py` did not silently grow a runtime door (C-001).
