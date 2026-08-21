# Implementation Plan: M7 — ExecutionMode / enum consolidation

**Branch**: `rc3-execution-mode-consolidation-01M0GGX1` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/rc3-execution-mode-consolidation-01M0GGX1/spec.md`

## Summary

Behavior-preserving code-hygiene mission. Three distinct classes are named
`ExecutionMode`; two collide on a `code_change` token meaning contradictory things.
Fix: **delete** the dead `mission_runtime.context.ExecutionMode` (governance-gate:
also drop its export, unpin the arch surface test, note the ADR), **rename** the live
`ownership.models.ExecutionMode` → `WorkProductKind` (member string values held
constant for frontmatter wire-compatibility), and add a **re-drift guard test** that
permits M6's future additive member. No behavior, lane, worktree, or status-payload
change. The external `spec_kitty_events.status.ExecutionMode` (#3) is out of reach and
becomes the sole surviving live `ExecutionMode`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: (none new) — `spec_kitty_events` (external, unchanged)
**Storage**: WP frontmatter `execution_mode:` string values — MUST stay wire-compatible
**Testing**: pytest; mypy --strict; ruff — targeted surfaces (see below)
**Target Platform**: Linux/macOS/Windows CLI
**Project Type**: single (Python CLI/library)
**Performance Goals**: N/A (no runtime path change)
**Constraints**: zero consumer-behavior diff; no new suppressions; static gates clean
**Scale/Scope**: 9 in-repo modules touch enum #1; 5 locations for enum #2 retirement; 1 new guard test

**Chosen class name**: `WorkProductKind`. Rationale: reads as "the kind of product a
WP yields", pairs naturally with existing member semantics (`code_change` /
`planning_artifact`), and is short. Verified free of collision via `git grep`
(no existing `WorkProductKind` symbol in `src/`). Alternative `WorkPackageOutputKind`
rejected as needlessly long for the same meaning.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** ✅ — this mission *establishes* single authority per
  axis (removes a dead duplicate; removes a class-name clash). Directly serves the charter.
- **Architectural alignment** ✅ — retirement respects the surface-pin + ADR governance
  gate (updated in the same change, not bypassed).
- **ATDD-first / red-first** ✅ — each WP leads with a failing-first test (guard test red
  before implementation; consumer suite green as the behavior-preservation contract).
- **Terminology canon** ✅ — no `feature*` introduced; `--mission` used throughout.
- **Behavior preservation** ✅ — member values held constant; consumer suite is the contract.
- **No version numbers in scope** ✅ (this is not an `__init__.py` public-API change; but
  see note under Complexity Tracking on CHANGELOG).

No violations → no Complexity Tracking rows required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/rc3-execution-mode-consolidation-01M0GGX1/
├── plan.md              # This file
├── research.md          # Phase 0 (enum audit, re-verified on HEAD)
├── data-model.md        # Phase 1 (the three types + consumer edges)
├── quickstart.md        # Phase 1 (how to verify the change)
├── contracts/
│   └── enum-consolidation.md   # Phase 1 (retire/rename/guard contract)
└── tasks/               # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root) — touched surfaces

```
src/specify_cli/ownership/
├── models.py            # RENAME class ExecutionMode → WorkProductKind (values unchanged)
├── __init__.py          # update import + __all__ entry
├── inference.py         # update import + infer_execution_mode return annotation + members
└── validation.py        # update import + member comparisons

src/specify_cli/core/worktree.py            # update import + members
src/specify_cli/lanes/compute.py            # update import + member
src/specify_cli/lanes/implement_support.py  # update import + member
src/specify_cli/workspace/context.py        # update import + coercion + member
src/specify_cli/cli/commands/agent/mission_parsing.py  # update import + member + docstring

src/mission_runtime/context.py     # DELETE class ExecutionMode (dead)
src/mission_runtime/__init__.py    # drop import (:32) + __all__ entry (:82)

tests/architectural/test_mission_runtime_surface.py   # unpin retired symbol
tests/architectural/test_execution_mode_no_redrift.py # NEW re-drift guard (permits M6)

docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md  # record retirement
docs/changelog/CHANGELOG.md  # [Unreleased] entry (root CHANGELOG.md is a symlink)
```

**Structure Decision**: single-project Python. All edits are in `src/` + `tests/` +
`docs/`; no new package or module boundary.

## Complexity Tracking

No Constitution violations. One note (not a violation): the rename does **not** touch
`src/specify_cli/__init__.py`, so the "version bump on `__init__.py` change" rule is not
triggered. A `docs/changelog/CHANGELOG.md` `[Unreleased]` entry is still added per the
deliverable requirement and Code Review Checklist (breaking-change documentation).

## Work Package Breakdown (Phase 2 preview)

Sequenced for red-first, behavior-preservation, and clean attribution. Three WPs, run
in dependency order on a single branch (topology `single_branch`):

- **WP01 — Guard test (red-first) + baseline capture.** Add
  `tests/architectural/test_execution_mode_no_redrift.py` asserting the footgun's
  absence (no `class ExecutionMode` under `src/`; no live `worktree`+`code_change`
  enum pairing; retired symbol absent from the mission_runtime surface). It is RED on
  the mission base (enum #2 still exists) and turns GREEN only after WP02+WP03. Written
  to **permit** M6's additive member (asserts absence-of-footgun, not an exact member
  set). Also record the green merge-base baseline for the targeted suites.
  → FR-006, AC-5.
- **WP02 — Retire dead enum #2 (governance-gate).** Delete
  `mission_runtime.context.ExecutionMode`, drop its `__init__` import + `__all__` entry,
  unpin `test_mission_runtime_surface.py`, and record the retirement in ADR-2026-06-07-1.
  → FR-001, AC-1.
- **WP03 — Rename live enum #1 + update consumers.** Rename class → `WorkProductKind`
  across the 9 modules; hold member names/values constant; update docstrings; add the
  `[Unreleased]` CHANGELOG entry. → FR-002/003/004/005, AC-2/3/4/6.

**Dependencies:** WP02 and WP03 both make WP01 go green; WP01 must land first (red-first).
WP02 and WP03 are independent in principle but touch disjoint files, so they can be
authored in sequence on one branch without conflict. Guard-green is verified after both.

## Parallel Work Analysis

Single-branch, single-implementer mission (small blast radius). No lane parallelism
required. Sequencing: WP01 (red guard) → WP02 (retire) → WP03 (rename) → guard green +
full targeted suite green.

### Targeted test surfaces (per-WP validation)

- `tests/architectural/test_mission_runtime_surface.py` (WP02)
- `tests/architectural/test_execution_mode_no_redrift.py` (WP01, new)
- `tests/specify_cli/ownership/` (WP03 — inference/validation/models)
- `tests/specify_cli/` worktree/workspace/lanes coverage touching `execution_mode`
- `tests/architectural/test_no_dead_symbols.py` / surface gates (retirement)
- `ruff check .` + `mypy --strict src/` (all WPs)
