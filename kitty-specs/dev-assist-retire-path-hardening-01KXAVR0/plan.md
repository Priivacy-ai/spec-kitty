# Implementation Plan: Dev-Assist Retirement + Path-Validation Hardening

**Branch**: `feat/dev-assist-retire-path-hardening` | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/dev-assist-retire-path-hardening-01KXAVR0/spec.md`

## Summary

Two coupled goals under epic #2071: (1) **harden `validate_deliverables_path`** so it rejects the malicious-path classes that are today accepted and masked by `xfail` (Phase-0 research R1: all 17 vectors are live), landing red→green in-mission; and (2) **retire / narrow / consolidate the development-assist test scaffolding** left by the god-module decompositions, with each removal's coverage proven subsumed by a named standing guard before deletion (research R2). Approach: ATDD red-first for the security surface; coverage-membership verification for every retirement; per-family compat-guard consolidation as the structural lever.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (+ pytest-xdist), ruff, mypy, typer, spec-kitty CLI (test-suite + `src/specify_cli`)
**Storage**: N/A (filesystem path validation; no datastore)
**Testing**: pytest; ATDD red-first for the security fix; architectural/family compat-surface guards as the coverage authority for retirements; `PWHEADLESS=1` for any UI-adjacent runs
**Target Platform**: Linux/macOS dev + CI (cross-platform path semantics matter for the validator)
**Project Type**: single project (`src/specify_cli` + `tests/`)
**Performance Goals**: N/A (correctness/security + test-suite maintainability mission; net test LOC must not grow)
**Constraints**: security fix lands verified live (C-001); no test deleted before its invariant is proven covered by a standing guard (C-002); retirements follow `development-assist-test-cleanup` + DIRECTIVE_041 (C-003); zero new masking/ratchet/wiring-only debt (NFR-003)
**Scale/Scope**: 1 product function hardened (`validate_deliverables_path`); ~4 test families triaged (runtime-bridge, doctor/mission/merge, tasks/merge seam clusters); ~16 fragmented compat batteries consolidation candidates

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after design.*

- **ATDD-first** — SATISFIED: FR-001/FR-002 are red-first (research R1 proves the vectors red today); the fix is complete only when red→green live (C-001, NFR-001).
- **Tests-as-scaffold / DIRECTIVE_041** — SATISFIED and central: retirements classify each test (keep/retire/narrow) and never weaken a valid guard; coverage-before-deletion (C-002) enforced by symbol-set membership (research R2).
- **Canonical sources** — SATISFIED: retirement governed by the canonical `development-assist-test-cleanup` procedure; consolidation mirrors the existing `test_bridge_compat_surface` / `test_mission_shim_reexports` shape (no improvised parallel guard).
- **DDD tiered rigour** — `validate_deliverables_path` is a security-relevant core surface → full rigour (exhaustive vector coverage + anti-vacuity); test retirements are glue-tier hygiene.
- **Terminology canon** — SATISFIED: no `feature`-for-Mission drift introduced; "retire/narrow/split", not blanket "delete".

No charter violations → Complexity Tracking is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/dev-assist-retire-path-hardening-01KXAVR0/
├── plan.md              # This file
├── research.md          # Phase 0 output (live-vs-stale, coverage method, consolidation shape)
├── spec.md              # Requirements (FR/NFR/C)
├── checklists/          # requirements.md quality checklist
└── tasks/               # /spec-kitty.tasks output (WP decomposition — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
└── mission.py                              # validate_deliverables_path (IC-01 security surface)

tests/
├── adversarial/test_path_validation.py     # IC-01 — unmask + strict ATDD
├── runtime/                                 # IC-02 — bridge dev-assist retire/narrow
│   ├── test_bridge_compat_surface.py        #   (standing family guard — the coverage authority)
│   ├── test_bridge_{cores,retrospective,composition,io}.py
│   └── test_bridge_parity.py
├── specify_cli/cli/commands/                # IC-03 — doctor/mission shim + golden
│   ├── test_doctor_shim_reexports.py / test_doctor_cli_surface_golden.py
│   └── agent/test_mission_shim_reexports.py / test_tasks_*_seam.py
├── merge/test_*_seam.py                     # IC-04 — merge family consolidation
└── (cross-cutting) source docstrings naming moved/deleted tests   # IC-05
```

**Structure Decision**: single-project layout; the only production surface is `src/specify_cli/mission.py` (IC-01). All other concerns are test-suite surfaces under `tests/`. No new modules/packages.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are architectural areas, NOT work packages. `/spec-kitty.tasks` translates these into executable WPs (one concern may become several WPs, or small concerns may merge).

### IC-01 — Deliverables-path security hardening

- **Purpose**: make `validate_deliverables_path` reject every malicious-path class it currently accepts, and replace the test file's `xfail`/`skip` masks with strict red-first assertions. **Scope: hardens the function only; runtime wiring is deferred to the ship-code-as-assets doctrine (#2539/#2536) — the validator has no production callers today.**
- **Relevant requirements**: FR-001, FR-002; NFR-001; C-001.
- **Affected surfaces**: `src/specify_cli/mission.py::validate_deliverables_path`; `tests/adversarial/test_path_validation.py` (17 live vectors + 5 tests, of which only 1 is a genuine malicious vector); over-rejection tripwire (run, not owned): `tests/research/test_research_deliverables_unit.py`.
- **Sequencing/depends-on**: none (independent; highest priority).
- **Risks**: symlink resolution needs a real base (the symlink test resolves against CWD, not `tmp_path` — needs chdir/base); Windows-`C:\` is not caught by POSIX `is_absolute` (needs explicit backslash/drive rule); the case-variant class is `skip`-guarded so must be de-skipped and asserted unconditionally; absolute-check must run on RAW input (resolve makes everything absolute) and containment via `relative_to` not `startswith` (cf. canonical `core/paths.py`). Anti-vacuity: a reintroduced accepted path must re-red the suite.

### IC-02 — Runtime-bridge dev-assist retirement

- **Purpose**: retire the family-guard-duplicate shape tests + inert timing seed, narrow the partially-covered `io` test, keep the unique untracked-reexport test.
- **Relevant requirements**: FR-003; NFR-002; C-002/C-003.
- **Affected surfaces**: `tests/runtime/test_bridge_{cores,retrospective,composition,io,parity}.py`; authority = `test_bridge_compat_surface.py`.
- **Sequencing/depends-on**: none (coverage already verified in research R2).
- **Risks**: must re-point the `test_seam_defines_every_relocated_symbol` docstrings that reference removed assertions; narrow (not delete) `io:104`.

### IC-03 — Sibling-mission dev-assist retirement

- **Purpose**: retire/narrow doctor/mission golden-count duplicates, one-shot "gap closed" pins, and presence-overlaps where a named standing guard subsumes the invariant.
- **Relevant requirements**: FR-004; NFR-002; C-002/C-003.
- **Affected surfaces**: `tests/specify_cli/cli/commands/test_doctor_shim_reexports.py` + `test_doctor_cli_surface_golden.py`; `agent/test_mission_shim_reexports.py`; `test_commit_router_planning_residue.py`.
- **Sequencing/depends-on**: none (per-candidate coverage verification, same method as IC-02).
- **Risks**: verify golden set-equality actually subsumes each retired count before deletion.

### IC-04 — Compat-surface battery consolidation

- **Purpose**: consolidate the fragmented per-seam re-export identity batteries — **merge and tasks families only** — into one per-family compat-surface guard; retire tautological literal pins, the ×8 byte-identical one-way-import guards, and the `assert_called` interception proofs; keep behavioural orchestration/ports tests. (The **doctor** family is already single-guarded — `test_doctor_shim_reexports.py::test_contracted_symbol_resolves_from_doctor` — so it is NOT in scope for consolidation; WP03 keeps it.)
- **Relevant requirements**: FR-005; NFR-002; C-002/C-003.
- **Affected surfaces**: `tests/merge/test_*_seam.py` (WP04), `tests/specify_cli/cli/commands/agent/test_tasks_*_seam.py` (WP05a/WP05b).
- **Sequencing/depends-on**: benefits from the consolidated-guard pattern (already merged authorities: `test_bridge_compat_surface.py`, `test_mission_shim_reexports.py`) — concern-level, not a hard WP order. Within the tasks family, WP05b depends on WP05a's guard (coverage-before-deletion).
- **Risks**: consolidation needs a `{symbol→residual-module}` MAP not a flat union (merge `preflight` → two residuals; each symbol confirmed identity-reexport not native-redefine); consolidated key-set MUST be a strict superset of the retired batteries' union; reconcile the wave1 `*_orchestration.py` ↔ wave2 `*_seam.py` overlap before asserting coverage. Keep each consolidated guard **self-contained** (no cross-family shared helper — codebase convention).

### IC-05 — Coverage-preservation harness & docstring re-pointing (cross-cutting)

- **Purpose**: the standing method that makes every retirement safe — symbol-set membership proof per candidate, planted-regression anti-vacuity checks, and re-pointing any source docstring that names a moved/deleted test.
- **Relevant requirements**: FR-006; NFR-002, NFR-003, NFR-004; SC-004.
- **Affected surfaces**: cross-cutting across IC-02/03/04; module docstrings in `src/runtime/next/runtime_bridge*` and the seam test files.
- **Sequencing/depends-on**: applies throughout; its checks gate each retirement.
- **Risks**: skipping the planted-regression check would let a vacuous consolidation pass; must run the full pre-existing runtime/arch/doctor/merge suites green after each concern.
