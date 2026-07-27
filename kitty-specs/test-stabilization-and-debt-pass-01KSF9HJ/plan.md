# Implementation Plan — Test Stabilization & Architectural Debt Pass

**Branch**: `kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ` → merges into `main`
**Date**: 2026-05-25
**Mission slug**: `test-stabilization-and-debt-pass-01KSF9HJ`
**Mission ID**: `01KSF9HJBFKRBC617JVHKZXNE2`
**Spec**: [spec.md](./spec.md)
**Predecessor mission**: `charter-ux-and-org-pack-vocabulary-01KSAF14` (#122, merged 2026-05-24)
**Architect review source**: [`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`](../../docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md)
**Linked issues**: [#1298](https://github.com/Priivacy-ai/spec-kitty/issues/1298) (test failures), [#1163](https://github.com/Priivacy-ai/spec-kitty/issues/1163) (issue-matrix scaffolding)

## Summary

Intermediate remediation mission that closes the 242 remaining failures from #1298 and four architectural debt items (LD-1, LD-3, LD-5, MS-1) identified in the post-mission-122 audit. Four small follow-ups from the mission #122 engineering notes ride along (#1163 issue-matrix scaffold, F-04 retro mining, F-10 tracker_refs field, F-01 bulk-edit-gate docs).

The mission is **deliberately bounded**: ≤10 WPs (NFR-004), three slices, no architectural re-design — only repayment of known debts and stabilisation of known failures.

Technical approach:

1. **Triage first** (FR-001) — the very first WP authors `triage.md` so the test-fix WPs can be scoped precisely.
2. **Fix-and-defer** (FR-002..FR-005) — fix the largest cluster (`tests/sync/test_events.py` `ModuleNotFoundError`) and two surgical failures; file follow-up sub-issues for residual clusters.
3. **Architectural-debt slices** (FR-006, FR-007, FR-013, FR-014) — four focused refactors with behaviour-preservation contracts.
4. **Quality follow-ups** (FR-009..FR-012) — close 4 small loose ends from the engineering notes.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty toolchain).
**Primary Dependencies**: typer, ruamel.yaml, pydantic, rich; existing `doctrine.drg`, `charter.compiler`, `specify_cli.charter_*` packages; pytest + pytest-asyncio; gh CLI (for DIR-012 issue assignment).
**Storage**: Filesystem only — `kitty-specs/<slug>/`, `.kittify/`, `architecture/3.x/adr/`, `docs/reference/`.
**Testing**: pytest (unit + integration + architectural); `tests/sync/`, `tests/tasks/`, `tests/test_dashboard/`, `tests/doctrine/`, `tests/specify_cli/charter_*/`.
**Target Platform**: Linux/macOS/Windows 10+ (DIR-001 cross-platform).
**Project Type**: single (Python CLI tool with library packages); follows existing `src/` layout.
**Performance Goals**: Mission MUST NOT introduce any new perf regression beyond the existing 3.2.0 baselines (the `charter preflight <300 ms` NFR from #122 still applies, and the LD-3 chokepoint routing must not regress it).
**Constraints**: `mypy --strict` clean on touched files; `ruff check` clean on touched files; `pytest tests/ -q` failure count drops from 242 → ≤75 (NFR-001); existing public APIs preserved (NFR-002, C-007); shim re-exports for one deprecation window (C-008); HiC issue assignment per DIR-012 on WPs that begin a linked-issue (#1298, #1163).
**Scale/Scope**: 14 FRs / 4 NFRs / 8 constraints. Predecessor mission's 67 specify_cli subpackages stay 67 except for the WP07 split (charter.py → per-subcommand) and the WP08 grouping (charter_runtime/ umbrella). No mass-rename / bulk-edit gate involvement this time.

## Charter Check

`spec-kitty charter status` confirms the project charter is SYNCED. Action-scoped context for `plan` loaded via `spec-kitty charter context --action plan --json` (compact mode). Relevant gates applied:

| Charter rule | Compliance plan |
|---|---|
| **DIR-001** Cross-platform | All changes pure Python; no new shell-specific dependencies. |
| **DIR-005 / DIR-006 / DIR-007** Tests + mypy --strict + docstrings | Every new function and refactor lands with pytest coverage, mypy-strict annotations, docstrings for public symbols. Especially binding for FR-006 (one method replaces two) and FR-007 (~6 new modules). |
| **DIR-009** CHANGELOG | FR-014 (charter_runtime/ umbrella) requires a CHANGELOG entry per C-008 (deprecation window for old import paths). FR-007 (charter.py split) requires no CHANGELOG entry IF import paths via `cli/commands/charter` continue to resolve (re-export shim). |
| **DIR-012** HiC issue assignment | First WP for each linked issue (#1298 → WP01 / WP02 / WP03 / WP04; #1163 → WP09) assigns the GitHub issue to the HiC before implementation. |
| **DIR-013** Pre-existing failure reporting | NOT applicable — this entire mission IS the response to a DIR-013 issue (#1298). The mission's baseline failure count is the starting point, not pre-existing context. |
| **DIR-031** Bounded contexts | FR-013 / FR-014 are exactly bounded-context corrections. The plan MUST NOT introduce any inverse import (`doctrine` → `specify_cli` or `charter` → `specify_cli`). Architect Alphonso's review §1 verified zero inverse imports today; mission must preserve. |
| **DIR-032** Conceptual alignment | FR-007's per-subcommand split renames nothing user-visible. FR-014's umbrella rename of three package paths IS user-visible; the deprecation shim window (C-008) keeps the old paths working. |
| **ADR `2026-05-16-1-doctrine-layer-merge-semantics.md`** | FR-006 (LD-1 consolidation) MUST preserve the field-merge semantics this ADR ratified. Spec C-002 locks this. The consolidation makes the identical-by-design intent visible; it does NOT change semantics. |
| **ADR `2026-05-24-1-charter-freshness-ux-contract.md`** (mission #122's freshness contract) | FR-013 (LD-3 chokepoint routing) MUST preserve `compute_freshness()`'s public return shape (`CharterFreshness` dataclass with three sub-states). Spec C-007 locks this. |
| **ADR `2026-05-24-2-pack-augmentation-vocabulary.md`** (mission #122's pack vocabulary) | FR-008 (LD-2 augmentation-test parametrisation) MUST preserve the per-kind coverage that this ADR's authoring vocabulary depends on. |
| **Charter binding C-007 (`__all__` convention)** | FR-007 (charter.py split) MUST update the charter command's `__all__` exports as it splits. FR-014 (charter_runtime/) MUST update each new submodule's `__all__` AND the shim re-export `__all__` at the old paths. |
| **Charter binding C-011 (ATDD-First)** | Test fixes (FR-001..FR-005) are by definition tests-first. Refactors (FR-006, FR-007, FR-013, FR-014) MUST have their behaviour-preservation tests written/identified BEFORE the refactor commit. |

**Charter-Check verdict**: PASS. No directive violation requires justification; the Complexity Tracking table at the end is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/test-stabilization-and-debt-pass-01KSF9HJ/
├── spec.md                  # /spec-kitty.specify output (committed)
├── plan.md                  # this file
├── triage.md                # FR-001 output — first WP's deliverable
├── research/                # (may stay empty — no design unknowns)
├── tasks.md                 # /spec-kitty.tasks output (not yet)
├── tasks/                   # WP01..WPn (not yet)
└── meta.json                # mission identity
```

### Source code (repository root)

The mission touches these existing trees:

```
src/
├── doctrine/
│   └── base.py                       # FR-006 — overlay-layer consolidation (LD-1)
├── specify_cli/
│   ├── charter_lint/                 # FR-014 — moves to src/specify_cli/charter_runtime/lint/
│   ├── charter_freshness/            # FR-014 — moves to .../freshness/; FR-013 — chokepoint routing
│   │   └── computer.py               # FR-013 main change site
│   ├── charter_preflight/            # FR-014 — moves to .../preflight/
│   ├── charter/                      # FR-014 — moves to .../facade/
│   ├── charter_runtime/              # FR-014 NEW umbrella package
│   ├── cli/commands/
│   │   ├── charter.py                # FR-007 — split into per-subcommand package
│   │   └── charter/                  # FR-007 NEW package (per-subcommand handlers)
│   │       ├── __init__.py
│   │       ├── status.py
│   │       ├── sync.py
│   │       ├── synthesize.py
│   │       ├── lint.py
│   │       ├── preflight.py
│   │       ├── bundle.py
│   │       └── resynthesize.py
│   ├── tasks/                        # FR-011 — WPMetadata tracker_refs field
│   └── retrospect/                   # FR-010 — event-log mining
└── ...
docs/
├── reference/
│   └── bulk-edit-gate.md             # FR-012 NEW reference doc
└── ...
tests/
├── sync/test_events.py               # FR-002 — ModuleNotFoundError cluster fix
├── test_dashboard/test_scanner.py    # FR-003 — tolerance fix
├── tasks/test_move_task_git_validation_unit.py  # FR-004 — commit-message contract
└── doctrine/
    └── test_augmentation_fields.py   # FR-008 — parametrised consolidation
.kittify/templates/                   # FR-009 — issue-matrix.md template addition
```

**Structure decision**: no new top-level packages beyond `charter_runtime/` (FR-014). The per-subcommand split (FR-007) is a package, not new top-level. NFR-004 (≤10 WPs) is the operational cap.

## Phase 0 — Research findings

No new research artifacts are required. The architect's deep-dive review (`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`) supplies the design rationale for FR-006, FR-007, FR-013, FR-014. The mission spec already cites:

- The merge-semantics ADR for FR-006 (C-002).
- The freshness-contract ADR for FR-013 (C-007).
- The pack-vocabulary ADR for FR-008.

The only outstanding "research" task is the test-failure triage itself (FR-001 / WP01), which produces `triage.md` — the empirical input for the test-fix WPs.

## Phase 1 — Design outputs

This mission is debt-repayment, not new design. Phase 1 artifacts are minimal:

- **No new `data-model.md`** — no new doctrine entities. FR-011 (`tracker_refs` field on `WPMetadata`) is documented inline.
- **No new `contracts/` directory** — the refactors are behaviour-preserving. New behaviour (`tracker_refs` field, retro mining heuristics, issue-matrix scaffold) is documented in the relevant WP prompts.
- **No `quickstart.md`** — no new user-facing scenarios to walk through.
- **`triage.md`** — produced by WP01 (FR-001) before any other WP runs.

### Architect-resolved open questions from the spec

The spec carries two open questions for Planner Priti. Both are answered here so the tasks-phase doesn't re-derive them:

1. **FR-007 split granularity (one WP or two?)** — **ONE WP** (WP06). The seven subcommands are independent handler functions; the move is mechanical. A two-WP split (skeleton then handlers) adds ceremony without reducing risk. Planner may revisit IF the WP06 prompt grows past 7 subtasks.
2. **FR-012 doc location** — **`docs/reference/bulk-edit-gate.md`** (alongside existing `cli-commands.md`). Resolved in Wave Q above.

If planner Priti judges that LD-3 (FR-013) needs an explicit chokepoint-contract document at `contracts/charter-freshness-chokepoint.md`, they may add it during /spec-kitty.tasks. This plan does not require it.

## Implementation waves (dependency-ordered)

These waves map to dependency clusters in the work-package graph. WPs within a wave can be parallelised; waves themselves are sequential because of test-suite-state coupling.

### Wave T — Test triage + targeted fixes (FR-001..FR-005)

- **WP01 — Triage (FR-001)**: produces `triage.md`. MUST run first; gates Wave T's remaining WPs.
- **WP02 — `tests/sync/test_events.py` cluster (FR-002)**: fix the ~27 ModuleNotFoundError failures.
- **WP03 — Surgical fixes (FR-003, FR-004)**: dashboard scanner + move-task commit-message assertion.
- **WP04 — Triage closeout (FR-005)**: file follow-up sub-issues for residual clusters; verify NFR-001 ceiling (≤75 failures).

Lane-wise: WP02-04 can run in parallel after WP01 produces triage.md, because they touch disjoint test files.

### Wave A — Architectural debt repayment (FR-006, FR-007, FR-008, FR-013, FR-014)

- **WP05 — LD-1 consolidation (FR-006)**: rewrite `_apply_org_overrides`/`_apply_project_overrides` → `_apply_overlay_layer`. Behaviour-preservation tests: `tests/doctrine/test_doctrine_layered_resolution.py` + `tests/doctrine/test_doctrine_layer_collision_warnings.py` (existing); these MUST be green at HEAD before and after the refactor commit (C-002).
- **WP06 — MS-1 split (FR-007)**: split `cli/commands/charter.py` into per-subcommand package. Behaviour-preservation tests: `tests/specify_cli/cli/commands/test_charter_lint.py` + `tests/integration/test_charter_status_freshness.py` + `tests/integration/test_charter_lint_lints_all_layers.py` (existing); these are the green-anchor set.
- **WP07 — LD-3 chokepoint routing (FR-013)**: route `charter_freshness/computer.py` reads through `ensure_charter_bundle_fresh`. Preserves public API (C-007). Behaviour-preservation tests: `tests/specify_cli/charter_freshness/test_computer.py` + `tests/integration/test_charter_status_freshness.py`. **Architect-mandated additional test**: the data-model §6 conflict-resolution case (`built_in_only=true` AND `graph.yaml` present ⇒ `state="invalid"`) is currently asserted in `test_computer.py::test_invalid_state_when_built_in_only_and_graph_yaml_both_exist` (per mission #122 WP02 deliverables); WP07 MUST keep this assertion green after rerouting through the chokepoint.
- **WP08 — LD-5 charter_runtime umbrella (FR-014)**: group `charter_*` packages under `charter_runtime/`. Shim re-exports + CHANGELOG (C-008). Behaviour-preservation tests: the full `tests/specify_cli/charter_lint/`, `tests/specify_cli/charter_freshness/`, `tests/specify_cli/charter_preflight/` suites (~120 tests across the three) MUST be green AND a new architectural test `tests/architectural/test_charter_runtime_shim_paths.py` MUST assert that `from specify_cli.charter_lint import LintEngine` (the old path) still resolves to the new canonical class.
- **WP08b — LD-2 augmentation-test parametrisation (FR-008, stretch)**: collapse the 5 `tests/doctrine/test_{kind}_augmentation_fields.py` files into a single parametrised `tests/doctrine/test_augmentation_fields.py`. Spec NFR-004 marks this as droppable if WP count creeps past 10. Coverage-parity assertion: post-refactor test count ≥ 20 (matching the 4 cases × 5 kinds in the predecessor mission's WP05). **Architect note**: if WP10 below absorbs the 3 small Wave-Q items cleanly, this stretch WP can ride alongside as WP08b (parallel-safe — different files). If WP10 is already at the budget cap, drop this WP and re-file as a sub-mission per NFR-004.

Lane-wise: **WP05 is independent of WP06/WP07/WP08** (doctrine package, no overlap with `specify_cli/charter*`). **WP06 → WP07 → WP08 MUST be sequenced** because WP08's package move would conflict with WP06's per-subcommand split and WP07's chokepoint changes if run in parallel. WP08b (if included) is independent — `tests/doctrine/` is disjoint from the charter package surface.

### Wave Q — Small quality fixes (FR-009, FR-010, FR-011, FR-012)

- **WP09 — Issue-matrix scaffold (FR-009)**: `/spec-kitty.tasks` emits `issue-matrix.md` skeleton when spec references GH issues. Closes #1163.
- **WP10 — Composite small fixes (FR-010, FR-011, FR-012)**: retrospective generator mining + `tracker_refs` field on `WPMetadata` + bulk-edit-gate docs. Bundled in one WP because each is small (<100 LOC). **Doc-location decision** (spec open question 2): `FR-012` documentation lands at `docs/reference/bulk-edit-gate.md` (alongside other CLI reference docs and the existing `cli-commands.md`). Skill prose at `.kittify/doctrine/skills/spec-kitty-bulk-edit-classification/SKILL.md` is updated to link there.

Lane-wise: WP09 and WP10 can run in parallel — disjoint surfaces.

### Wave-A / Wave-Q parallelism (architect note)

**Wave Q does NOT depend on Wave A.** WP09 (`/spec-kitty.tasks` scaffold) touches `src/specify_cli/cli/commands/tasks_*.py` (no overlap with charter/doctrine). WP10's three sub-changes touch `src/specify_cli/retrospect/`, `src/specify_cli/tasks/metadata.py`, and `docs/reference/`. None of these collide with WP05-08 source files. The two waves are sequenced for narrative clarity in the spec, NOT for technical reasons. During `/spec-kitty.tasks` decomposition and `lanes.json` computation, Wave Q WPs should be placed in independent lanes from Wave A.

### Cross-cutting (every wave)

| Concern | Binding | Concrete placement |
|---|---|---|
| **HiC issue assignment** | DIR-012 | WP02/WP04 assign #1298 to HiC; WP09 assigns #1163 to HiC. |
| **CHANGELOG entry** | DIR-009, C-008 | WP08's commit MUST add a CHANGELOG entry naming `src/specify_cli/charter_runtime/` as the canonical path and noting the shim deprecation window. |
| **ATDD-First** | charter C-011 | WP05/06/07/08 MUST identify their behaviour-preservation tests (already-existing or net-new) BEFORE the production-code commit lands. |
| **`__all__` updates** | charter C-007 | Every `__init__.py` touched by FR-007 and FR-014 MUST have its `__all__` updated. |
| **No new bulk-edit gate involvement** | spec | Mission's `meta.json` does NOT set `change_mode: bulk_edit`. WP08's package rename is small enough (4 directories) to not require occurrence-classification. |

## Complexity Tracking

*No charter violations require justification.* The Complexity Tracking table is empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|

## Branch contract (final restatement)

- **Current branch**: `kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ`
- **Planning / base branch**: same (mission lane branch; matches `branch_matches_target=true` from setup-plan output)
- **Final merge target**: `main` (per `meta.json::target_branch`)
- Lane workspaces will be allocated by `finalize-tasks` from this mission branch as base.

## Next step

Run `/spec-kitty.tasks` to decompose this plan into work packages.

⚠️ DO NOT proceed to tasks generation inside this command. The user invokes `/spec-kitty.tasks` separately.
