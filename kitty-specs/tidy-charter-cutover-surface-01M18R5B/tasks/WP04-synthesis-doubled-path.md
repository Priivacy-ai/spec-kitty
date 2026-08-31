---
work_package_id: WP04
title: 'Declutter: fix charter-sync doubled-path write + safe gitignore (#3819)'
dependencies: []
requirement_refs:
- FR-006
- FR-007
- C-001
planning_base_branch: spec/tidy-charter-cutover-surface
merge_target_branch: spec/tidy-charter-cutover-surface
branch_strategy: Planning artifacts for this mission were generated on spec/tidy-charter-cutover-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/tidy-charter-cutover-surface unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tidy-charter-cutover-surface-01M18R5B
base_commit: 917d2b379810fb9c8686ad32a92132f633f30deb
created_at: '2026-08-30T20:42:59.791487+00:00'
subtasks:
- T012
- T013
- T014
phase: Phase 1
history: []
authoritative_surface: src/charter/activation/synthesizer/manifest.py
create_intent:
- tests/charter/test_synthesis_provenance_paths.py
execution_mode: code_change
mission_id: 01M18R5BMJSQBT1ZN68WSR4X6Q
owned_files:
- src/charter/activation/synthesizer/manifest.py
- src/charter/bundle.py
- tests/charter/test_synthesis_provenance_paths.py
- .gitignore
tags: []
tracker_refs: []
---

# WP04 — Declutter: fix charter-sync doubled-path write + safe gitignore (#3819)

**Priority**: P2 · **Concern**: IC-04 · **Requirements**: FR-006, FR-007, C-001 (red-first)
**Owned files**: `src/charter/activation/synthesizer/manifest.py`, `src/charter/bundle.py`, `tests/charter/test_synthesis_provenance_paths.py` (new), `.gitignore`
**Dependencies**: none (independent lane)

## Goal
A charter-sync / synthesis writer emits byte-identical duplicates at a **doubled-leaf path**
(`.kittify/charter/provenance/provenance/<file>`, `.kittify/doctrine/styleguide/styleguide/<file>`)
— a path-join that appends a leaf onto a base that already ends in it. Fix the join so each
artifact is written exactly once at its canonical path, and gitignore the regenerated output
so PRs stop accreting stray files (#3807 stripped 23).

## Context
- Path anchors: `src/charter/bundle.py` (`PROVENANCE_DIR = Path(".kittify/charter/provenance")`)
  and `src/charter/activation/synthesizer/manifest.py`
  (`_PROVENANCE_PATH_PREFIX = Path(".kittify/charter/provenance")`). Trace where a relative
  path that already includes the `provenance`/`styleguide` leaf is joined onto a base that
  also ends in that leaf.
- `.gitignore` already ignores several `.kittify/**` subdirs (`.dashboard`, `derived/`, …) but
  NOT `.kittify/charter/provenance/**` or the generated `.kittify/doctrine/{directive,styleguide,tactic}/*.yaml`.
  Docs say these are "Ignored | Regenerated synthesis state".

## Subtasks
- **T012** — Red-first test (`tests/charter/test_synthesis_provenance_paths.py`): drive a
  sync/synthesis run against a `tmp_path` project and assert **no** doubled-path artifact
  (`*/provenance/provenance/*`, `*/styleguide/styleguide/*`) is produced. It must FAIL today.
- **T013** — Fix the path-join in the synthesis/manifest writer so each artifact writes once at
  its single canonical path. Behavior otherwise unchanged.
- **T014** — Add a **safe** `.gitignore` entry for the regenerated synthesis output
  (`.kittify/charter/provenance/`, `.kittify/charter/synthesis-manifest.yaml`, and the generated
  `.kittify/doctrine/{directive,styleguide,tactic}/*.yaml`) **without** ignoring tracked files
  (`DIRECTIVE_*.md`, `.provenance/*.yaml`). Verify `git status` stays clean after a sync and
  `git ls-files` still lists the tracked doctrine files.

## Acceptance (SC-004)
- A charter sync / synthesis run produces zero doubled-path artifacts.
- Clean `git status` after a sync (generated output ignored); tracked doctrine files intact.
- Red-first test fails before T013, passes after; `ruff`/`mypy` clean.
