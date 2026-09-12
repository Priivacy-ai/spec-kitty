# Implementation Plan: Charter Preflight Missing-Charter Advisory Mode

**Branch**: `fix/charter-preflight-missing-charter-advisory` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/doctrine/missions/software-dev/command-templates/plan.md` for the execution workflow.

> **Pre-merge correction (2026-08-16):** Canonical layer state is the sole exemption authority. `_is_optional_missing_charter_stack()` qualifies before display-only warning selection. Stale/invalid residue blocks regardless of prose. Every next mode and implement emits stderr while JSON stdout stays clean; dashboard persists; canonical charter imports stay off cold startup. This supersedes contrary historical wording below.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

`spec-kitty next` and `spec-kitty implement WP##` hard-block (exit 1) when canonical charter state is safely uninitialized. A working runner exemption exists but the shared hook never opts in. This plan wires the flag into the shared hook, defines a canonical missing-stack predicate, uses `charter.md` only as a post-decision warning-copy selector, emits advisories on mutation consumers, and persists them on dashboard. Invalid YAML, stale synthesis, and other partial residue keep blocking regardless of prose presence.

## Technical Context

**Language/Version**: Python 3.11+ (existing `specify_cli` package; no new language/runtime surface)
**Primary Dependencies**: None new. Touches `specify_cli.charter_runtime.preflight` (`runner.py`, `hook.py`) and the existing dashboard command's warning-persistence branch; `typer` remains the existing CLI wrapper.
**Storage**: N/A — reads filesystem state under `.kittify/charter/` and `.kittify/doctrine/` only; no persistent data model changes.
**Testing**: pytest, extending runner, cold-import performance, actual next wrapper, implement hook, and dashboard command suites. Test-first-bug-fixing doctrine: write changed assertions red before production changes.
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows, per DIR-001) — no platform-specific logic introduced.
**Project Type**: single (existing `src/specify_cli/` CLI package; no frontend/backend split)
**Performance Goals**: Stay within the existing charter-preflight clean-tree budget (<100ms, NFR-001 in spec.md); legacy-bundle detection adds at most one extra `Path.exists()` check.
**Constraints**: No new blocking behavior may be introduced (C-001); the fix must live in the single shared hook consumed by both `next` and `implement`, not duplicated per-consumer (C-002) — this is the exact drift class that caused #3498.
**Scale/Scope**: Surgical behavior changes in `runner.py`, shared `hook.py`, `next_cmd.py`, and dashboard command/persistence; five existing test files extended. No new modules, flags, or schema keys.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority**: The fresh-project exemption already lives in one place (`runner.py`); this plan keeps the legacy-bundle exemption in the same module rather than introducing a second, competing implementation (C-002). PASS.
- **Architectural alignment**: No shared-package-boundary, workspace, or status-model surfaces are touched — this stays entirely inside `charter_runtime/preflight/`. PASS.
- **`change-apply-smallest-viable-diff` tactic / `DIRECTIVE_024` Locality of Change**: New logic is additive (`_is_legacy_charter_bundle()` alongside the existing `_is_optional_missing_charter_fresh_project()`), and the hook-level fix is a one-line flag flip at the existing call site plus one new branch. No unrelated refactors bundled in. PASS.
- **`DIRECTIVE_025` Boy Scout Rule**: Not invoked — this mission does not opportunistically touch unrelated code in the files it edits beyond the scoped fix.
- **ATDD-first**: `spec.md` already defines Given/When/Then acceptance scenarios per user story; `/spec-kitty.tasks` will derive WPs from those plus the Implementation Concern Map below.
- **Glossary & terminology adherence**: Uses this codebase's existing canonical terms (`charter_source`, `synced_bundle`, `synthesized_drg`, `fresh-project`, `legacy bundle`) as already defined in `freshness/computer.py` and this mission's spec Key Entities — no new/competing vocabulary introduced.
- **DIR-005/006/007** (tests, mypy --strict, docstrings): Addressed by IC-04 (test coverage) and standard authoring discipline on the two touched functions; both new predicates get docstrings matching the style of `_is_optional_missing_charter_fresh_project`.
- **DIR-009** (breaking changes in CHANGELOG): This is a user-visible CLI behavior fix (two previously-blocking states now pass advisory) — a CHANGELOG.md entry is required as part of implementation, tracked as a task.
- **DIR-012** (tracker-issue HiC assignment): This mission's input is tracker-backed (Priivacy-ai/spec-kitty#3498). The implementing agent must assign #3498 to the Human-in-Charge before/as part of starting implementation — tracked as a pre-implementation step, not a plan-time action.

No Charter Check violations requiring justification — Complexity Tracking table below is intentionally empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/charter_runtime/preflight/
├── runner.py       # ADD: _is_legacy_charter_bundle(), new warning constant,
│                   #      second advisory branch in run_charter_preflight()
├── hook.py         # CHANGE: run_preflight_or_abort() passes
│                   #      allow_missing_charter=True; run_preflight_for_dashboard()
│                   #      gains the legacy-bundle warning detail
├── result.py       # UNCHANGED (warnings: list[str] already supports this)
└── config.py       # UNCHANGED

tests/specify_cli/charter_preflight/
├── test_runner.py                          # ADD: canonical predicate + warning tests
└── test_performance.py                     # ADD: cold-import startup gate

tests/agent/cli/commands/
├── test_next_preflight.py                  # ADD: all next wrapper modes preserve advisory
└── test_implement_preflight.py             # ADD: legacy-bundle now advisory on `implement`

tests/test_dashboard/
└── test_dashboard_preflight.py             # ADD: dashboard banner shows legacy-bundle detail

CHANGELOG.md                                 # ADD: entry documenting the behavior fix
src/specify_cli/cli/commands/dashboard.py    # CHANGE: persist passed advisories
src/specify_cli/cli/commands/next_cmd.py     # CHANGE: preserve stderr in JSON/query routing
```

**Structure Decision**: Option 1 (single project) — this is an internal CLI/library fix inside the existing `src/specify_cli/` package. No new directories, no new modules; all changes land inside the existing `charter_runtime/preflight/` package and its four existing test locations.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map

*Include this section when the mission has multiple distinct architectural areas that inform how tasks are decomposed.*

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP. Do not label concerns
> with WP-style IDs or sequencing language.

### IC-01 — Canonical missing-stack predicate + legacy warning selector (runner.py)

- **Purpose**: Add `_is_optional_missing_charter_stack()` for canonical `missing/missing/(missing|built_in_only)` qualification, then use `_is_legacy_charter_bundle()` only to select a distinct warning after the outcome is fixed.
- **Relevant requirements**: FR-002, FR-003, FR-004, C-001, NFR-001
- **Affected surfaces**: `src/specify_cli/charter_runtime/preflight/runner.py`
- **Sequencing/depends-on**: none
- **Risks**: Any direct `charter.md`-keyed pass branch violates doctrine C-001/FR-016 and can mask stale residue. Tests compare identical canonical states with/without prose and inject stale/invalid residue while prose exists.

### IC-02 — Wire next/implement shared hook to advisory mode

- **Purpose**: Pass `allow_missing_charter=True` into `run_preflight_or_abort()` and emit returned advisories to stderr so both mutation consumers continue and inform the operator.
- **Relevant requirements**: FR-001, FR-005, C-002
- **Affected surfaces**: `src/specify_cli/charter_runtime/preflight/hook.py` (`run_preflight_or_abort`)
- **Sequencing/depends-on**: IC-01
- **Risks**: This is the single shared call site fix; a parallel/duplicated fix here instead of reusing IC-01's predicates would recreate the exact class of drift that caused #3498.

### IC-03 — Extend dashboard warning banner with legacy-bundle detail

- **Purpose**: Dashboard already never blocks server startup; make its warning banner also distinguish the legacy-bundle case using IC-01's predicate/message instead of a generic one (in scope per user confirmation — decision `01M05RT3Q6HZYY4BCV9YS8JZAC`).
- **Relevant requirements**: FR-003 (scope extended to dashboard)
- **Affected surfaces**: `src/specify_cli/cli/commands/dashboard.py` plus the shared dashboard hook result
- **Sequencing/depends-on**: IC-01
- **Risks**: A passed result previously cleared warning persistence; command-level tests prove advisory metadata reaches the banner channel.

### IC-04 — Regression test coverage across all three consumers

- **Purpose**: Prove both advisory shapes pass on `next`/`implement`/dashboard with the correct distinct warnings, and prove every other charter state (invalid, stale, partial-residue) still blocks exactly as before — written test-first per this repo's `test-first-bug-fixing` doctrine.
- **Relevant requirements**: NFR-002, C-003, SC-001–SC-004
- **Affected surfaces**: `tests/specify_cli/charter_preflight/test_runner.py`, `tests/agent/cli/commands/test_next_preflight.py`, `tests/agent/cli/commands/test_implement_preflight.py`, `tests/test_dashboard/test_dashboard_preflight.py`
- **Sequencing/depends-on**: none structurally (tests are written red before IC-01/02/03 turn them green), but content depends on IC-01's predicate names/warning text being decided first.
