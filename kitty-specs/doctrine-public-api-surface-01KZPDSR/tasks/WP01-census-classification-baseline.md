---
work_package_id: WP01
title: Census, classification & behavior baseline
dependencies: []
requirement_refs:
- FR-002
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Foundation
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_doctrine_
create_intent:
- tests/architectural/test_doctrine_census.py
- tests/architectural/test_doctrine_regenerate_graph_roundtrip.py
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- tests/architectural/test_doctrine_census.py
- tests/architectural/test_doctrine_regenerate_graph_roundtrip.py
role: implementer
tags: []
tracker_refs:
- '3179'
wp_code: WP01
---

# Work Package Prompt: WP01 — Census, classification & behavior baseline

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: run `/ad-hoc-profile-load python-pedro`
(or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`)
and apply its initialization, boundaries, directives, and tactics. State which you applied.

## Objective

Establish the foundation every other WP consumes: (a) the authoritative per-path disposition
table (re-censused, not trusting the snapshot), (b) a census gate that fails if any
non-exempt-reached doctrine path lacks a disposition, and (c) the golden behavior-lock used by
WP08–10. **This WP is the SOLE owner of the management-surface enumeration** — no later WP
reclassifies a module into the exempt surface.

## Context & Constraints

- Read `spec.md` (FR-002, the 6 gaps), `plan.md` (IC-01), `data-model.md` (the disposition
  taxonomy + snapshot table), `contracts/public-api-contract.md` (C7, C8).
- The snapshot counts (26 paths / 34 files / 5 raw sites / 45 CRITICAL) are **expected
  magnitudes** — re-run and record the real numbers.
- The golden already exists in-repo: `packs/built-in/**/*.graph.yaml` (14 files). The CLI ships
  `spec-kitty doctrine regenerate-graph --check` (regenerates to a tempdir, byte-compares). Reuse
  it — do not build a bespoke fixture.
- Reinstall (`pip install -e .`) before shelling out to `spec-kitty` to avoid the stale-install
  false-red gotcha.

## Subtasks

### T001 — Re-run the reach-through census + finalize the disposition table
- Sweep `src/specify_cli/` (excluding the exempt `src/specify_cli/doctrine/`) for direct + lazy
  `from doctrine`/`import doctrine` (`ImportFrom.level == 0`), and for consumers of laundered
  `specify_cli.doctrine.*` doctrine symbols. Record exact file/line/symbol.
- Reconcile every non-exempt-reached path to exactly one disposition (PUBLIC / FACADE-ONLY /
  MANAGEMENT / ticketed-baseline / INTERNAL) and write the finalized table into `data-model.md`
  (replace the snapshot table; this is an intentional planning-doc update, recorded with a
  one-line rationale in the WP history).
- For the four "decide IC-01" rows (`override_policy`, `hand_authored_overlay`,
  `mission_step_repository`, `step_projection`): prefer FACADE-ONLY where a clean door exists;
  a MANAGEMENT tag requires explicit per-instance justification (it widens exemptions).

### T002 — Census gate test (`tests/architectural/test_doctrine_census.py`)
- Emit the disposition as a **machine-readable manifest** (e.g. a checked-in
  `doctrine_surface_manifest.yaml` or an inline constant) that this test, WP04's ratchet baseline,
  and WP02's INTERNAL-negative test all import directly — not prose in data-model.md that can
  drift from what tests read.
- Assert every non-exempt runtime module reaching doctrine has a disposition entry, so a
  newly-reached undoored path fails CI (machine-checkable FR-002 / SC-002).
- **Pin the MANAGEMENT allowlist**: assert the exempt/management set exactly equals a frozen
  constant, so any growth is a deliberate reviewed diff — not a silent per-path judgment.
- **Reconciliation (post-tasks squad):** assert the union of WP05/WP06/WP07 `owned_files` equals
  the re-run lazy-import census set; any remainder must have a named owner (fail otherwise) so no
  reached file is orphaned (SC-001).

### T003 — Golden round-trip test (`tests/architectural/test_doctrine_regenerate_graph_roundtrip.py`)  [P]
- Invoke `spec-kitty doctrine regenerate-graph --check` (subprocess) and assert exit 0 →
  byte-identity of the committed `packs/built-in/**/*.graph.yaml`. This is the behavior-lock
  WP08/WP09/WP10 rely on.
- **Hard precondition, not skip (post-tasks squad):** in CI, CLI unavailability must **fail**, not
  `xfail`/skip — a skipped golden makes WP08–10's "byte-identical" DoD vacuously green. Add
  "golden actually ran (not skipped)" to the WP08/WP09/WP10 acceptance.

**Late-bound row resolution (part of T004):**
- `drg.override_policy` (consumed by `_doctrine_collect.py`) and
  `drg.migration.hand_authored_overlay.write_reference_graph_with_overlay` (consumed by
  `cli/commands/doctrine.py`) have **no clean charter door** and are doctrine-management internals.
  Resolve both to **ticketed-baseline** (a documented, tracker-referenced permanent ratchet
  allowlist entry) rather than MANAGEMENT (which would widen the exempt surface) — so WP03 owes no
  door and WP05 keeps them allowlisted, not stranded.

### T004 — Record management-surface enumeration + charter C-007 extension note
- Write the explicit inbound-only management-surface allowlist (the modules permitted to import
  doctrine directly) into `data-model.md`.
- Add a short note (in `data-model.md` or a charter sidecar) recording the per-mission decision
  to extend the charter C-007 `__all__` convention to `src/doctrine/` (C-007-mission).

## Branch Strategy

Planning base and final merge target are both `feat/doctrine-public-api-surface`. Execution
worktrees are allocated per computed lane from `lanes.json` (do not hand-create worktrees).
Implement via `spec-kitty agent action implement WP01 --agent <name>`.

## Definition of Done

- [ ] Census re-run; `data-model.md` disposition table finalized with real numbers; every
      non-exempt-reached path has exactly one disposition (no undoored reach-through).
- [ ] `test_doctrine_census.py` green and fails on an injected undoored path.
- [ ] `test_doctrine_regenerate_graph_roundtrip.py` green (`regenerate-graph --check` exit 0).
- [ ] Management-surface allowlist + C-007-mission note recorded.

## Risks & Reviewer Guidance

- **Risk**: MANAGEMENT chosen by default widens exemptions — the mission's opposite. Reviewer:
  confirm each MANAGEMENT tag carries a per-instance justification and FACADE-ONLY was not the
  cleaner option.
- **Reviewer**: verify the census script/test is reusable (WP04's baseline + WP05–07 shrink
  proofs consume it), and the golden test truly regenerates + compares (not a no-op).
