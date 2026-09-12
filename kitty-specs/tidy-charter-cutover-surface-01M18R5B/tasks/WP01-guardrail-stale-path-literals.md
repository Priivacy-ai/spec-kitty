---
work_package_id: WP01
title: 'Guardrail: arch-gate for stale moved-module path literals (#3818)'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-002
- C-002
planning_base_branch: spec/tidy-charter-cutover-surface
merge_target_branch: spec/tidy-charter-cutover-surface
branch_strategy: Planning artifacts for this mission were generated on spec/tidy-charter-cutover-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/tidy-charter-cutover-surface unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tidy-charter-cutover-surface-01M18R5B
base_commit: 917d2b379810fb9c8686ad32a92132f633f30deb
created_at: '2026-08-30T20:41:33.448955+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1
history: []
authoritative_surface: tests/architectural/test_no_stale_charter_path_literals.py
create_intent:
- tests/architectural/test_no_stale_charter_path_literals.py
execution_mode: code_change
mission_id: 01M18R5BMJSQBT1ZN68WSR4X6Q
owned_files:
- tests/architectural/test_no_stale_charter_path_literals.py
tags: []
tracker_refs: []
---

# WP01 — Guardrail: arch-gate for stale moved-module path literals (#3818)

**Priority**: P1 · **Concern**: IC-01 · **Requirements**: FR-001, FR-002, NFR-002, C-002
**Owned files**: `tests/architectural/test_no_stale_charter_path_literals.py` (new)
**Dependencies**: none (independent lane)

## Goal
Add an architectural gate that fails when any `src/`, `tests/`, or live `docs/` file
names a **moved** `charter` module by its **old top-level path** as a string literal or
relative link — the straggler class the import-rewrite misses (arch-gate path-literal
allowlist tuples, `patch("charter.<old>...")` mock targets, and
`[..](../../src/charter/<old>.py)` doc links). Complements the C-004 import gate.

## Context
The M2b split (#3807) relocated the activation-side modules to `src/charter/activation/`.
Relocations keep leaving stale *string* references that only surface as a red CI shard
post-move (#3800/#3806/#3807 each paid a landing fold). This gate catches them at
construction time. The maintainer already wrote the census logic during the #3807
landing — reuse that shape: derive the moved-module set from the modules physically under
`src/charter/activation/` (top-level `.py` minus `__init__` + subpackage dirs), then scan
for `charter.<moved>` deep-path references NOT under `charter.activation.` in string
literals and markdown links.

## Subtasks
- **T001** — Write the gate: compute the moved-module set from `src/charter/activation/`;
  scan `src/`, `tests/`, and live `docs/` for `charter.<moved>` string literals and
  `src/charter/<moved>.py` relative links that should now be `charter.activation.<moved>` /
  `src/charter/activation/<moved>.py`. Use word-boundary matching so `context` never
  false-matches `context_state`; exclude same-name-different-package
  (`specify_cli.cli.commands.charter.*`).
- **T002** — Non-vacuity self-test: seed a `tmp_path` fixture that names an old
  `src/charter/<moved>.py` path and assert the gate flags it (file, line, token); assert it
  passes on the real merged tree (0 findings). Mirror the committed-`tmp_path` shape of
  `tests/architectural/test_charter_offering_does_not_import_activation.py`.
- **T003** — Exclude historical archives: `kitty-specs/**`, `docs/adr/**`, `docs/plans/**`
  (immutable snapshots) — assert an archived stale reference is NOT flagged.
- **T004** — Join the completeness baselines for the new test file: `tests/_arch_shard_map.py`,
  `tests/architectural/marker_baseline.txt`, and the golden test-count baseline. Declare
  `pytestmark = pytest.mark.architectural`. (These baseline edits are shared across lanes —
  they are reconciled by union at integration; make your additions minimal and additive.)

## Acceptance (SC-001)
- Gate fails the seeded synthetic stale-path fixture; passes (0 findings) on the merged tree.
- Green on the `tests/architectural/` shard within its time budget (NFR-002, no new >5s outlier).
- `ruff` + `mypy` clean; marker-convention + shard-map + golden-count gates pass.

## Notes
- Read `docs/development/how-to/pr-landing.md` census discussion and the #3818 body.
- This is the keystone guardrail — keep it strict but false-positive-free (the word-boundary
  and archive-exclusion cases are the ones to get right).
