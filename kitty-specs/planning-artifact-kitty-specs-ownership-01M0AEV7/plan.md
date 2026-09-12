# Implementation Plan: Planning-artifact WPs Own kitty-specs Paths

**Branch**: `feat/3222-2643-kitty-specs-ownership` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/planning-artifact-kitty-specs-ownership-01M0AEV7/spec.md`

## Summary

Narrow the `finalize-tasks` "owned_files cannot include paths under `kitty-specs/`" ban so it
exempts `execution_mode: planning_artifact` work packages while staying fail-closed for
`code_change`. The ownership model already blesses `kitty-specs/` ownership for planning artifacts
(`ownership/validation.py` `_PLANNING_PREFIXES` + `validate_execution_mode_consistency`), and the
lane layer already routes such work packages to the repo-root planning lane; only the finalize ban
disagrees. The technical approach is a single execution-mode guard in the ban predicate
(`_invalid_mission_specs_owned_files`, `cli/commands/agent/mission_parsing.py`), with red-first
acceptance coverage and a preserved fail-closed floor. No other production surface changes —
verified end-to-end by the research squad (workspace resolution, lane guards, manifest build, and
lane computation all already accept the planning-artifact-owns-kitty-specs shape).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: None new. Touches existing internal surfaces only — `specify_cli.cli.commands.agent.mission_parsing`, `mission_finalize`, and (read-only, no change) `specify_cli.ownership.validation`, `specify_cli.lanes.compute`.
**Storage**: N/A — WP frontmatter (YAML) under `kitty-specs/<mission>/tasks/`; no datastore.
**Testing**: `pytest` (targeted, per the parallel-run rules in CLAUDE.md); `ruff` and `mypy --strict` on changed files. Red-first acceptance test drives the change.
**Target Platform**: Spec Kitty CLI (Linux/macOS developer environments).
**Project Type**: single (Python CLI package under `src/specify_cli/`).
**Performance Goals**: N/A — the guard runs once per WP at finalize time; the added check is an equality comparison per WP.
**Constraints**: Every changed/added function stays at cyclomatic complexity ≤ 15; no `# noqa` / `# type: ignore` / Sonar suppressions; preserve the dynamic-alias patch seam `_invalid_kitty_specs_owned_files`; the exemption keys strictly on `execution_mode == planning_artifact`; the `code_change` ban stays fail-closed.
**Scale/Scope**: One predicate guard + focused tests; ~1 file of production change plus test additions/updates.

**Supply-chain security**: Not applicable — this plan adds, upgrades, and removes **no** dependencies in any ecosystem. No `research.md` supply-chain decision or lifecycle-script review is required.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** (`DIRECTIVE_044`): PASS — the fix *aligns* `finalize-tasks` to the existing ownership authority (`validate_execution_mode_consistency` / `_PLANNING_PREFIXES`) rather than adding a second rule. It removes a divergent, later over-reach; it does not introduce a competing surface.
- **Architectural alignment / gate discipline** (`DIRECTIVE_001`, `DIRECTIVE_043`): PASS — the `kitty-specs/` ban remains a non-vacuous fail-closed gate for `code_change`; only the `planning_artifact` case (which cannot reach a lane branch) is exempted.
- **ATDD-first** (`acceptance-test-first`): PASS — driven by a red-first finalize acceptance test (reuse #2643's YAML) plus a fail-closed floor.
- **Tiered rigour / tests-with-branches**: PASS — the single new branch (the exemption) is covered by a direct predicate unit test and an end-to-end finalize acceptance test in the same change.
- **Terminology canon**: PASS — "Mission" / "work package" vocabulary; no `feature*` aliases introduced.
- **Campsite discipline** (`DIRECTIVE_025`): the touched surfaces (`mission_parsing.py`, `mission_finalize.py`) are scanned for domain-matched debt at implementation; no god-surface refactor is anticipated (the change is a single guard).

No violations → no Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/planning-artifact-kitty-specs-ownership-01M0AEV7/
├── plan.md              # This file
├── research.md          # Phase 0 — decision consolidation (squad findings)
├── data-model.md        # Phase 1 — WP ownership entities + verdict table
├── quickstart.md        # Phase 1 — how to reproduce/verify
├── contracts/
│   └── finalize-ownership-contract.md   # Phase 1 — finalize-tasks kitty-specs ownership decision contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/agent/
├── mission_parsing.py      # CHANGE: _invalid_mission_specs_owned_files gains a planning_artifact exemption
└── mission_finalize.py     # CONFIRM: _validate_owned_files_not_in_mission_specs call-site reads post-bootstrap execution_mode

src/specify_cli/ownership/validation.py   # READ-ONLY: the authoritative model the fix aligns to (no change)
src/specify_cli/lanes/compute.py          # READ-ONLY: planning-lane routing already accepts the shape (no change)

tests/
├── specify_cli/cli/commands/agent/test_mission_parsing.py         # UPDATE: predicate unit tests gain execution_mode context
├── specify_cli/cli/commands/agent/test_mission_finalize_phases.py # UPDATE: direct-call unit tests supply execution_mode
├── tasks/test_finalize_tasks_owned_files_validation.py            # KEEP GREEN (code_change fail-closed floor) + ADD positive planning_artifact case
└── (new/extended) finalize acceptance test reusing #2643's YAML
```

**Structure Decision**: Single Python package (`src/specify_cli/`). The change is localized to the
`agent` command family; the ownership and lanes packages are consulted read-only to confirm the
downstream already accepts the shape.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

> **Post-plan squad refinements folded in** — see [squad-findings-post-plan.md](./squad-findings-post-plan.md). The exemption gains a **confinement** condition (R-1); the acceptance test must clear two downstream hard-gates (D-1); durability is filename-scoped (D-2); three extra negative/inference cases are added (A-1, A-2, D-3).

### IC-01 — Narrow the finalize kitty-specs ban to code_change (confined to planning ownership)

- **Purpose**: Make the `finalize-tasks` `kitty-specs/` owned-files ban execution-mode-aware so a `planning_artifact` work package may own `kitty-specs/` deliverables, while `code_change` stays fail-closed.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission_parsing.py` (`_invalid_mission_specs_owned_files`); `src/specify_cli/cli/commands/agent/mission_finalize.py` (`_validate_owned_files_not_in_mission_specs` call-site confirmation). Dynamic alias `_invalid_kitty_specs_owned_files` preserved.
- **Exemption condition (refined, R-1)**: skip a WP only when `execution_mode == planning_artifact` **AND** every `owned_files` entry is under `_PLANNING_PREFIXES` (import the canonical constant from `specify_cli.ownership.validation` — single authority, do not re-derive). This confinement means a `planning_artifact` WP that also owns `src/`/`tests/` is **not** exempted (closes the mislabel-owns-code hole). Compare against `ExecutionMode.PLANNING_ARTIFACT.value` / normalized (R-3), not incidental `StrEnum` equality.
- **Sequencing/depends-on**: none.
- **Risks**: preserve the monkeypatch/alias seam; the unset-mode path stays fail-closed (inference decides, and any code signal → `code_change`). Confirm the predicate reads the post-bootstrap `execution_mode` (the ban at `mission_finalize.py:2069` runs after `_apply_ownership_inference`). Keep the added condition at complexity ≤ 15 (extract a small helper if needed).

### IC-02 — Acceptance, fail-closed floor, and regression coverage

- **Purpose**: Prove the positive case *end-to-end*, lock every guardrail the exemption newly exposes, and bind the regression guards to concrete seams (not fragile integration tests).
- **Relevant requirements**: FR-006, NFR-001, C-003.
- **Affected surfaces**: `tests/specify_cli/cli/commands/agent/test_mission_parsing.py`, `test_mission_finalize_phases.py`, `tests/tasks/test_finalize_tasks_owned_files_validation.py`, plus an end-to-end finalize acceptance test reusing #2643's reproduction shape.
- **Test set (each red-first where it exercises IC-01)**:
  1. **Positive acceptance (D-1)** — `planning_artifact` owning only `kitty-specs/<slug>/…` finalizes cleanly and lands in the planning lane. MUST clear the two downstream hard-gates: build it **inference-driven** (empty `owned_files` + planning-only body → inferred kitty-specs ownership + `authoritative_surface`, glob matches existing `spec.md`/`plan.md`) **or** set a kitty-specs `authoritative_surface` + `create_intent`. Assert finalize passes `_validate_ownership_manifests` (mission_finalize.py:2085) **and** `wp_id in compute_lanes(...).planning_artifact_wps` (D-5).
  2. **Fail-closed floor (FR-003)** — existing `code_change` + kitty-specs ban tests stay green (fixtures already pin `code_change`).
  3. **Confinement (R-1)** — `planning_artifact` owning `kitty-specs/…` **and** `src/…` is still rejected.
  4. **Overlap floor (A-1)** — two `planning_artifact` WPs with overlapping `kitty-specs/` scopes and no dep edge are still rejected by `validate_no_overlap`.
  5. **Inferred-planning ACCEPT (A-2)** — unset mode + kitty-specs-only body infers `planning_artifact` and is accepted (pins the inference→ban ordering).
  6. **Inferred-code REJECT (D-3)** — unset mode + a `src/`/`.py` code signal in the body infers `code_change`; assert the resolved `execution_mode == code_change`, then assert `INVALID_WP_OWNED_FILES_KITTY_SPECS`.
  7. **Predicate unit tests (blast radius)** — update `test_mission_parsing.py` / `test_mission_finalize_phases.py` direct-call tests to supply `execution_mode`; assert the alias/shim identity is preserved.
- **Regression guards bound to seams (D-4, D-2)**:
  - `authoritative_surface` — exercise `infer_authoritative_surface` (`ownership/inference.py:154`) → `validate_authoritative_surface`; assert a kitty-specs owned file yields a compatible surface.
  - **Durability is filename-scoped** — exercise `_is_coordination_owned_artifact` / `kind_for_mission_file` (`lanes/auto_rebase.py:236`): assert a `kitty-specs/<slug>/disposition-matrix.md` deliverable is durable (`kind is None`) **and** a NEGATIVE assertion that `analysis-report.md` / `tasks/WP*.md` is a managed kind (documented carve-out — C-003 holds only for non-managed filenames).
- **Sequencing/depends-on**: exercises IC-01 (cases 1, 3, 5 are red before IC-01 lands).

### Follow-up (out of this mission, A-4)

File a tech-debt ticket for the duplicated topology rule between `policy/commit_guard.py:88` (runtime) and the finalize kitty-specs ban (plan-time) — a shared `can_lane_commit(path, mode)` predicate would host it once. Not a blocker; predicate-local is the correct minimal fix here.
