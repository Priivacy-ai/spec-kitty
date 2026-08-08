# Implementation Plan: Docs Quality Gate Hardening

**Branch**: `docs/3253-docs-gaps` | **Date**: 2026-08-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/docs-gate-hardening-01KZGAG2/spec.md`

## Summary

Harden three docs quality-gate surfaces so silent failures become loud at PR time: (1) a bidirectional, registry-anchored gate + backfill for `docs/api/slash-commands.md`; (2) a per-include-glob, pre-exclusion non-vacuity guard in the published-page resolver; (3) a repo-readable safety-structure test for the docs-freshness workflow. Approach and seams were validated by a pre-spec grounding squad and a post-spec adversarial squad (which corrected item 2 from per-content-entry to per-include-glob and reframed item 3 from an unobservable required-check tripwire to an in-repo structure assertion). No new runtime dependencies; all three surfaces already exist.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib (`json`, `re`, `pathlib`); `pytest` for tests; reuses existing `scripts/docs/` helpers (`_published_pages.resolve_published_pages`, the `check_cli_reference_freshness.py` *shape*). No new third-party dependencies.
**Storage**: N/A — operates on repo files (`docs/`, `docs/docfx.json`, `.github/workflows/`, `src/specify_cli/shims/registry.py`).
**Testing**: `pytest` under `tests/docs/`; mirror the harnesses in `tests/docs/test_check_cli_reference_freshness.py` (gate shape) and `tests/docs/test_published_pages.py` (`_write_config`/`synthetic_docs`). ATDD red-first per C-006; each gate ships a committed negative test (NFR-001).
**Target Platform**: CI (GitHub Actions docs jobs, invoked via `docs-freshness.yml`) and local dev (`.venv/bin/python`).
**Project Type**: single (Python scripts + tests; no frontend/backend split).
**Performance Goals**: gates are pure in-process operations (set-diff / glob resolution); NFR-004 is an architectural property (no subprocess/network/app-import beyond the registry), inspection-verified rather than timed.
**Constraints**: no new dependencies; every new/changed function ≤15 cyclomatic complexity (NFR-002); gates non-vacuous (NFR-001, DIRECTIVE_043); per-glob guard evaluated **pre-exclusion** and additive to the 500 floor (C-002); terminology canon `<mission>` not `<feature>` (C-004).
**Scale/Scope**: 3 gate surfaces + backfill 3 doc sections + ~4 new/changed test modules. ~675 published pages, 15 consumer commands, 19 docfx include globs, 2 docfx content entries.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`). Applicable gates and status:

- **DIRECTIVE_044 (canonical sources / single authority)** — PASS by design: the slash gate imports `CONSUMER_SKILLS` (C-001), no forked registry.
- **DIRECTIVE_043 (close defect class by construction) + non-vacuity** — PASS: each gate ships a committed negative/self-mutation test (NFR-001, SC-006).
- **DIRECTIVE_034 / 041 (test-first, red-first; tests as scaffold)** — PASS: C-006 pins red-first with captured evidence for co-introduced test+gate.
- **DIRECTIVE_025 (Boy Scout / tidy-first) + RECONCILE_CHANGE_SCOPE_TENSIONS** — PASS: tidy-first steps are scoped and additive (see IC risks); OUT-of-scope cleanups tracked as #3264/#3265.
- **Writing-comms doctrine (divio-type-discipline, publication-authority, plain-language, DIRECTIVE_047)** — applies to FR-002 backfill prose (mirror existing per-command section style; code is source of truth).
- **Terminology Canon (Mission not Feature)** — PASS: C-004; new doc prose uses `<mission>`.

No violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/docs-gate-hardening-01KZGAG2/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions consolidated from the squads)
├── data-model.md        # Phase 1 output (authorities, structures, invariants)
├── quickstart.md        # Phase 1 output (run + red-first verification)
├── contracts/
│   └── gate-contracts.md  # Phase 1 output (each gate's input/exit/message contract)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
scripts/docs/
├── _published_pages.py            # MODIFY: add per-include-glob pre-exclusion non-vacuity; extract _vacuity_error() (tidy-first)
├── check_slash_command_freshness.py  # NEW: bidirectional heading-set vs CONSUMER_SKILLS gate (new heading extractor)
└── description_length_check.py    # UNCHANGED code; exercised by FR-004 propagation test

docs/
├── api/slash-commands.md          # MODIFY: backfill tasks-outline / tasks-packages / tasks-finalize (<mission> placeholders)
└── docfx.json                     # READ-ONLY reference (2 content entries, 19 globs)

.github/workflows/
├── docs-freshness.yml             # MODIFY: add slash-gate step; hoist PYTHONPATH to job-level (tidy-first); cross-ref invariant comment
└── docs-pages.yml                 # MODIFY (comment only): FR-007 note that seo_verify is push-only (main/2.x)

tests/docs/
├── test_check_slash_command_freshness.py  # NEW: bidirectional + missing/extra negative tests
├── test_published_pages.py        # MODIFY: per-glob empty→raises negative test; archive pre-exclusion pass
├── test_description_length_check_propagation.py  # NEW: empty-glob fixture through description_length_check entry point
└── test_docs_freshness_invariant.py  # NEW: workflow safety-structure assertions
```

**Structure Decision**: Single-project Python layout. Gates live under `scripts/docs/` (invoked by CI), tests under `tests/docs/`, mirroring the existing `check_cli_reference_freshness.py` / `test_check_cli_reference_freshness.py` precedent.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs. The three concerns are independent (no cross-dependencies) and can be sequenced in parallel lanes; each carries its own ATDD test.

### IC-01 — Slash-command reference gate + backfill

- **Purpose**: Make `docs/api/slash-commands.md` fail CI when its `## /spec-kitty.<name>` heading set diverges (either direction) from `CONSUMER_SKILLS`, and backfill the three missing sections.
- **Relevant requirements**: FR-001, FR-002; NFR-001/002/004; C-001, C-004; SC-001, SC-002.
- **Affected surfaces**: `scripts/docs/check_slash_command_freshness.py` (new), `docs/api/slash-commands.md`, `.github/workflows/docs-freshness.yml` (new step + PYTHONPATH hoist), `tests/docs/test_check_slash_command_freshness.py` (new).
- **Sequencing/depends-on**: none.
- **Risks**: the existing `_HEADING_RE` will NOT match the slash+dot heading form — a **new** extractor is required (reuse shape/test-harness only). Backfill prose must match existing per-section style and use `<mission>` (C-004). Wiring the CI step is where the tidy-first `PYTHONPATH` hoist lands (must not change behavior of existing steps).

### IC-02 — Per-include-glob publication non-vacuity

- **Purpose**: Make the published-page resolver fail loud when any declared docfx include glob resolves (pre-exclusion) to zero pages, closing the silent-under-collection band the aggregate floor left open.
- **Relevant requirements**: FR-003, FR-004; NFR-001/003; C-002; SC-003, SC-004.
- **Affected surfaces**: `scripts/docs/_published_pages.py` (per-glob guard between the collect loop and `_assert_non_vacuous`; extract `_vacuity_error()` builder — tidy-first, becomes 3rd shared message), `tests/docs/test_published_pages.py` (negative test), `tests/docs/test_description_length_check_propagation.py` (new, FR-004).
- **Sequencing/depends-on**: none.
- **Risks**: **granularity + exclusion landmine** (post-spec HIGH): guard must be per-*include-glob*, not per-content-entry, and evaluated **pre-exclusion** so the fully-excluded `archive` tree (0 post-exclusion) does not false-fail. `_collect_entry_pages` currently OR-collapses globs — the fix must track matches per compiled include pattern. Preserve the 500 floor (C-002).

### IC-03 — docs-freshness safety-structure test + notes

- **Purpose**: Encode the repo-readable safety structure that keeps the docs-freshness `paths:` gap harmless, and record the deploy-side analogue note.
- **Relevant requirements**: FR-005, FR-006, FR-007; NFR-001; C-003; SC-005.
- **Affected surfaces**: `tests/docs/test_docs_freshness_invariant.py` (new), `.github/workflows/docs-freshness.yml` (cross-ref invariant comment, reuse the "Required-check contract" idiom), `.github/workflows/docs-pages.yml` (FR-007 comment note).
- **Sequencing/depends-on**: none.
- **Risks**: must assert **repo-readable** properties (paths filter still excludes `tests/**`/`kitty-specs/**`; unfiltered `push:main` backstop present; invariant comment present) — NOT the live GitHub required-check setting (unobservable). Do not hardcode `required == {drift-detector}` (conflicts with `ui-e2e.yml`'s contract comment).
