---
work_package_id: WP01
title: Content inventory & baseline fixture capture
dependencies: []
requirement_refs:
- FR-002
- NFR-001
planning_base_branch: feat/relocate-builtin-doctrine-packs
merge_target_branch: feat/relocate-builtin-doctrine-packs
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-builtin-doctrine-packs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-builtin-doctrine-packs unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-relocate-builtin-doctrine-packs-01KYT87F
base_commit: c490008ac05b56e27f678b0469864d4a6fa54a36
created_at: '2026-07-30T20:47:03.855683+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Foundation
history:
- at: '2026-07-30T19:45:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: tests/doctrine/fixtures/
create_intent:
- tests/doctrine/fixtures/graph-identity.baseline.json
- tests/doctrine/fixtures/content-manifest.json
- tests/doctrine/test_pack_relocation_preflight.py
execution_mode: code_change
model: ''
owned_files:
- tests/doctrine/fixtures/graph-identity.baseline.json
- tests/doctrine/fixtures/content-manifest.json
- tests/doctrine/test_pack_relocation_preflight.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP01 — Content inventory & baseline fixture capture

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter before parsing the rest.

- **Profile**: `doctrine-daphne` · **Role**: `implementer` · **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show doctrine-daphne`** (resolved lineage applied). Do not read the raw `*.agent.yaml`.

---

## Objective

Produce the two artefacts every later WP consumes: (1) the **authoritative content inventory** (which readers move vs stay) and (2) the **pre-move graph-identity baseline**. This WP is the reason the relocation can be proven behavior-preserving. **It must complete before WP03 moves any file** — a baseline captured after the move is worthless.

## Context

- The move-set (confirmed by two squads): the **9** `<kind>/built-in/` content dirs (agent_profiles, directives, procedures, tactics, paradigms, styleguides, toolguides, assets, glossary_packs) + the **14** root `*.graph.yaml` fragments. Flattened target: `packs/built-in/<kind>/`.
- **STAY** (do not move): `schemas/` (C-003, kernel-coupled), `missions/` (C-002 Phase 1b — kernel/`__file__` readers), `skills/`, `model_task_routing/`, top-level `templates/`.
- The occurrence_map.yaml already drafts these; your job is to *finalize* it against a real sweep and add the missing reader idioms.

## Subtasks

> **Ownership note**: `occurrence_map.yaml` (under `kitty-specs/`) is already authored/committed; this WP *verifies* its completeness (read) and owns the two new code-side fixtures under `tests/doctrine/fixtures/`. A small confirming edit to `occurrence_map.yaml` is an allowed out-of-map planning edit if the sweep finds a gap.

### T001 — Finalize occurrence-map dispositions (verify)
- Sweep **three** reader idioms, not one: `git grep 'files("doctrine'`, literal `"src/doctrine/…"` strings, **and `Path(__file__)`-relative** joins onto `"missions"`/kind names (these are invisible to the first two). Include `src/kernel/`, `src/charter/`, `src/specify_cli/`.
- For every reader, confirm a move/stay entry exists in `occurrence_map.yaml`; 0 unclassified (SC-004).
- **Include `src/charter/catalog.py`** — its `_scan()` reads `resolve_doctrine_root()/<kind>/built-in` via the `files("doctrine")` root (not a per-kind anchor), so it is caught by no downstream guard; classify it REPOINT (owned by WP04).
- Re-confirm `missions/` = STAY (Phase 1b) and record the kernel/`__file__` readers that make it undeferrable in Phase 1.
- Classify the two REVIEW readers: `specify_cli/migration/rewrite_opposed_by.py:192`, `core/upgrade_probe.py:8` (both docstrings → leave).
- **Completeness check** (in `tests/doctrine/test_pack_relocation_preflight.py`, FR-002): a committed test that *runs the three sweeps* over `src/{doctrine,kernel,charter,specify_cli}` and **fails if any hit path is absent from `occurrence_map.yaml`** — so "0 unclassified" is machine-verified, not asserted (catches the `__file__`-relative idiom this WP itself calls invisible).

### T002 — Capture the graph-identity baseline (BEFORE any move)
- Write `tests/doctrine/fixtures/graph-identity.baseline.json` = full-model projection of `load_built_in_graph()`:
  - `nodes`: sorted `[urn, label, sorted(tags)]`
  - `edges`: sorted `[source, relation, target, when, reason]`
- Assert it captures **324 nodes / 892 edges** (smoke). This JSON is the fixture WP07 asserts against.
- Bare URN/triple sets are insufficient — `when` gates delivery and must be pinned.
- **Fixture-integrity check** (in `tests/doctrine/test_pack_relocation_preflight.py`, DIR-005): assert the fixture is not degenerate — every edge row has exactly 5 fields, **≥1 edge has a non-null `when`** and **≥1 a non-null `reason`**, and tagged-kind nodes carry non-empty `tags`. Without this, WP07's identity test could pass vacuously against an all-null fixture.

### T003 — Enumerate the exact move-set manifest
- Write `tests/doctrine/fixtures/content-manifest.json` = the exact set of repo-relative paths under the 9 `<kind>/built-in/` dirs + the 14 fragments (the parity anchor for WP03/WP05 set-equality — NOT a `≥` count).
- Whitelist the two `.py` **asset payloads** that live inside moving trees and move as data: `assets/built-in/docs_structural_lint.py`, `toolguides/built-in/system_tools/__init__.py`. Flag that a "no .py in move-set" guard must exempt these, and that their wheel shipping-status may change (WP05).

## Branch Strategy
Planning branch & merge target: `feat/relocate-builtin-doctrine-packs`. Execution worktrees are allocated per computed lane from `lanes.json`.

## Definition of Done
- `occurrence_map.yaml` has 0 unclassified readers (all three idioms swept); missions STAY rationale recorded.
- `graph-identity.baseline.json` exists, full projection, 324/892.
- `content-manifest.json` exists, exact path set, payload `.py` whitelisted.

## Risks
- Missing a `__file__`-relative reader → silent partial move later. Sweep all three idioms.
- Capturing the baseline late → silent green. Capture in this WP, before WP03.

## Reviewer guidance
Verify the baseline is full-projection (has `when`), not bare triples; verify the manifest is a set not a count; verify no reader is unclassified.
