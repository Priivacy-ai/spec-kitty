# Implementation Plan: Tidy the charter/doctrine cutover surface

**Branch**: `spec/tidy-charter-cutover-surface` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/tidy-charter-cutover-surface-01M18R5B/spec.md`

## Summary

Four independent charter/doctrine-surface fixes, bundled as a tidy-first enabler before the remaining `retire-doctrine-term` waves. Each maps to one lane on `lanes` topology and touches a near-disjoint file set, so the four can be implemented in parallel with one shared coordination point (the arch-test completeness baselines). Two lanes (#3810, #3819) are bugfixes and land red-first; one (#3808) is a behavior-preserving refactor proven by before/after verdict parity; one (#3818) is a new guardrail gate.

## Implementation Concerns (IC)

- **IC-01** — Guardrail gate for stale moved-module path literals (Lane A · #3818).
- **IC-02** — Activation allowlist correctness for squad lenses (Lane B · #3810).
- **IC-03** — Consistency-gate dedup: one shared DRG load + fail-closed wrapper (Lane C · #3808).
- **IC-04** — Charter-sync doubled-path write fix + safe gitignore (Lane D · #3819).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing repo (typer, ruamel.yaml, pytest); no new deps
**Storage**: filesystem (`.kittify/**` synthesis output, `src/charter/packs/*.yaml`)
**Testing**: pytest (`tests/architectural/`, `tests/charter/`), ruff, mypy
**Target Platform**: Linux/CI
**Project Type**: single project
**Performance Goals**: new arch gate stays within the `tests/architectural/` shard budget (no new >5s outlier, NFR-002)
**Constraints**: ruff+mypy clean, no new suppressions (NFR-003); behavior-preserving on #3808 (NFR-001); PR-bound onto `upstream/main` (C-004)
**Scale/Scope**: ~4 focused changes; no cross-cutting rewrite

## Constitution / Charter Check

*GATE: must pass before and after design.*

- **Terminology Canon** — the mission touches charter/doctrine prose (issue refs, docstrings). Run `tests/architectural/test_no_legacy_terminology.py` on any prose/config touch. PASS-by-construction (no `feature`/`ceremony` introductions).
- **Canonical sources** — #3810 edits the *shipped* allowlist source (`src/charter/packs/default.yaml`), not a generated copy; #3818 gate lives in `tests/architectural/` beside the C-004 gate. PASS.
- **Red-first / test-remediation** — #3810 and #3819 land a failing test first (C-001). PASS by plan.
- **Architectural gate discipline** — #3818 adds a gate and joins the completeness baselines (C-002). PASS by plan.
- **No suppression** — NFR-003. PASS by plan.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/tidy-charter-cutover-surface-01M18R5B/
├── spec.md              # committed
├── plan.md              # this file
├── tasks.md             # /spec-kitty.tasks output
└── tasks/               # per-WP files + lanes.json
```

### Source Code (files each lane owns — near-disjoint by design)

```
Lane A · #3818 (guardrail):
  tests/architectural/test_no_stale_charter_path_literals.py   (new gate)
  tests/_arch_shard_map.py                                     (shared baseline — join)
  tests/architectural/marker_baseline.txt                      (shared baseline — join)
  tests/architectural/<golden-count baseline>                  (shared baseline — join)

Lane B · #3810 (reliability):
  src/charter/packs/default.yaml                               (activated_agent_profiles)
  .kittify/config.yaml / project charter allowlist             (if project-local)
  tests/charter/ or tests/doctrine/ test for activation resolve

Lane C · #3808 (simplify):
  src/charter/activation/consistency_check.py                  (shared load + wrapper)
  tests/charter/test_consistency_check.py                      (per-gate pass/fail arms)

Lane D · #3819 (declutter):
  src/charter/activation/synthesizer/manifest.py | bundle.py   (path-join fix)
  .gitignore                                                   (safe ignore of generated output)
  tests/charter/ test reproducing the doubled path (red-first)
```

**Structure Decision**: single-project layout; each lane edits its own module/test files. The only shared files are the arch-test completeness baselines, owned by Lane A but touched by any other lane that adds a new test file.

## Parallel Work Analysis

### Dependency Graph

```
No hard ordering — all four lanes are independent surfaces.
Preferred start order (value-first): A (guardrail) ∥ B (reliability)  →  C ∥ D
A and B are P1; C and D are P2. All four can run concurrently on lanes topology.
```

### Work Distribution

- **Sequential work**: none required. (Lane A defines the completeness-baseline pattern; other lanes that add a test file follow it.)
- **Parallel streams**: A, B, C, D — each owns a disjoint module set.
- **Agent assignments**: one implementer per lane (sonnet), one reviewer per WP (opus), profile-loaded through the charter.

### Coordination Points

- **Shared completeness baselines (the one real hazard)**: `tests/_arch_shard_map.py`, `tests/architectural/marker_baseline.txt`, and the golden-count baseline are edited by **every lane that adds a new test file** (A certainly; B/C/D if they add new test files). This is the known "shared-allowlist union-merge" footgun — resolve at lane-merge time by **union-merging** the baseline additions, never taking one side. Prefer adding tests to *existing* test files where possible (C extends `test_consistency_check.py`) to minimize baseline churn.
- **Integration check**: after all lanes merge, run `tests/architectural/` in full + `tests/charter/` + `ruff`/`mypy`/terminology + `check_docs_freshness --ci`, and confirm a clean `git status` after a charter sync (SC-004).
- **Merge/PR**: consolidate the four lanes, open one PR onto `upstream/main`, autoclose `#3818 #3819 #3808 #3810`.
