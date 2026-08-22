---
work_package_id: WP05
title: FR-007 verify-and-sequence + ADR + changelog + gate closeout
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-007
- FR-010
planning_base_branch: rc3-canonical-mission-type-reader-01M0GGWM
merge_target_branch: rc3-canonical-mission-type-reader-01M0GGWM
branch_strategy: Planning artifacts for this mission were generated on rc3-canonical-mission-type-reader-01M0GGWM. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-canonical-mission-type-reader-01M0GGWM unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
phase: Phase 3 - Governance & closeout
history:
- at: '2026-08-22T04:16:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: docs/adr/
create_intent:
- docs/adr/3.x/2026-08-22-1-canonical-mission-type-reader-legacy-retirement.md
- tests/specify_cli/test_backfill_mission_type_ac5.py
execution_mode: code_change
model: ''
owned_files:
- docs/adr/3.x/2026-08-22-1-canonical-mission-type-reader-legacy-retirement.md
- CHANGELOG.md
- tests/specify_cli/test_backfill_mission_type_ac5.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – FR-007 verify-and-sequence + ADR + changelog + gate closeout

## Objectives & Success Criteria

- **Verify** (do not rebuild) that M0's `backfill-mission-type` maps legacy
  `mission` → `mission_type` and never manufactures an M3-breaker (AC-5);
  document the `backfill-identity` coverage gap (it mints `mission_id` only).
- Author the **legacy-retirement ADR** naming the blast radius, the M3↔M5
  compounding, and the M0-backfill-first sequencing.
- Add a `[Unreleased]` **CHANGELOG** entry per user-visible surface
  (dashboard / retrospective / interview) now showing the true type or typeless.
- Confirm the **FR-010 structural gate is fully green** and the architectural +
  terminology suites pass.

## Context & Constraints

- Depends on **WP02, WP03, WP04** (documents the landed change).
- **No new backfill** — `src/specify_cli/migration/backfill_mission_type.py`
  (M0) is correct; this WP verifies and sequences it. Load `../research.md`
  §Landed-mission deltas.
- Any `__init__.py` change requires a `pyproject.toml` version bump + CHANGELOG
  entry (this WP touches CHANGELOG regardless).

## Branch Strategy

- **Merge target branch**: `rc3-canonical-mission-type-reader-01M0GGWM`

## Subtasks & Detailed Guidance

### Subtask T024 – FR-007 backfill verify (AC-5)
- **Steps**: `tests/specify_cli/test_backfill_mission_type_ac5.py` — given a
  mission whose `meta.json` carries only `{"mission":"research"}`, running
  `backfill_mission_type_repo` writes `{"mission_type":"research"}` and the
  mission resolves `research` via `read_mission_type` afterward; a legacy value
  with no resolving profile yields `needs_manual_resolution` (never written).
  Reuse M0's helpers; do not duplicate the backfill.

### Subtask T025 – Legacy-retirement ADR
- **Steps**: `docs/adr/3.x/2026-08-22-1-canonical-mission-type-reader-legacy-retirement.md`
  following `docs/architecture/README.md`. Record: the operator ruling (drop
  legacy `{"mission":…}` resolution, remove silent `software-dev` defaults);
  convergence *downward* to canonical-only closes #3598; the **M3↔M5
  compounding** (silently-resolving → typeless (M5) → hard-fail (M3)); the
  program gate — **M0 backfill runs before either reaches real projects**; the
  per-surface user-visible impact.

### Subtask T026 [P] – Per-surface changelog
- **Steps**: `CHANGELOG.md` `[Unreleased]` — one line each: dashboard now shows
  the true `mission_type` (or `Unknown`) instead of a `software-dev` default;
  retrospective records the true type / typeless; interview/other surfaces per
  the converged readers. Note the deliberate behavior change + the backfill.

### Subtask T027 – FR-010 gate green + suites
- **Steps**: Run `pytest tests/architectural/test_mission_type_reader_invariants.py
  tests/architectural/test_no_legacy_terminology.py tests/architectural/ -q`.
  The parity + no-fallback/no-legacy invariants are fully green; every reader is
  converged / equivalent / encoded-exempt (AC-7). Do **not** edit the FR-010 test
  (owned by WP01) — only run it.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/test_backfill_mission_type_ac5.py tests/architectural/ -q`

## Risks & Mitigations

- Rebuilding M0's backfill — explicitly avoid; verification only.
- ADR must name the compounding so neither M3 nor M5 ships the compound break unguarded.

## Review Guidance

- ADR present and names compounding + M0-first sequencing; changelog has a line
  per visible surface; AC-5 test passes; FR-010 gate fully green; terminology guard green.

## Activity Log

- 2026-08-22T04:16:17Z – system – Prompt created.
