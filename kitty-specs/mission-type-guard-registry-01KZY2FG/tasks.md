# Work Packages: Mission Type Guard Registry

**Mission**: `mission-type-guard-registry-01KZY2FG`
**Mission ID**: `01KZY2FGYX2B90XXDD1DM3M95B`
**Branch**: `kitty/mission-mission-type-guard-registry-01KZY2FG` (planning base == merge target;
`branch-context --json` confirms `recommended_strategy: stay`, `primary_branch: main`)
**Source of truth**: [spec.md](./spec.md) · [plan.md](./plan.md) — no `research.md` /
`data-model.md` / `contracts/` / `quickstart.md` for this mission (plan.md's own Project
Structure section states why: the spec's verified-figures table and the plan's Seam & Module
Placement / Contracts sections already carry the design research and data-shape decisions
inline).
**Total subtasks**: 12 across 2 work packages

> This file is the WP manifest. Each WP has a prompt at `tasks/WP0N-slug.md`. Status lives in
> `status.events.jsonl`, not in frontmatter. Do **not** hand-edit lane state — use
> `spec-kitty agent tasks move-task`.

## Scope carried forward from plan.md (binding, not re-derived here)

This mission implements exactly what spec.md's C-003 and plan.md's Charter Check bound it to:
the `_GUARD_TABLES` registry (FR-001/FR-006), `plan`'s own guard table plus the one-line
`_PRESENCE_FILE_TAGS` fix (FR-002), the strict/tolerant split (FR-003–FR-005, C-001, C-002),
`spec-kitty doctor mission-type --json [--fail-on ...]` (FR-007–FR-009), and tests for all of
the above (FR-010, FR-011). **Out of scope, and no WP below touches any of it**: the
project-wide doctrine-override hatch (`_project_has_doctrine_overrides`,
`src/charter/activation/mission_type_profiles.py:1041`), the two divergent meta readers
(`mission_type_profiles.py:681` vs `mission.py:542`), the dashboard's silent
`"software-dev"` default (`dashboard/handlers/features.py:68`), the unverified wider ~22-site
census, any roster/validation check inside `validate_meta`/`write_meta` (C-004), and modeling
guards as DRG graph primitives. A follow-up tracking issue naming the four deferred sites is
close-out work for this mission, not a WP.

## No campsite-clean-first WP

Per plan.md's Campsite-Clean Scope section: the touched lines
(`runtime_bridge_cores.py:348-567`, `runtime_bridge.py:775-804` (re-verified
post-#3346-rebase, shifted +105 lines from 670-699, same code),
`runtime_bridge_composition.py:427-486`) were checked first-hand for pre-existing Sonar
findings, complexity violations, or stale in-code citations, and none were found. **This
mission has no distinct campsite-clean-first commit** — Standing Order #2's determination
requirement is satisfied by stating this explicitly, not by silently skipping it. WP01's first
commit is its FR-010 ATDD red-first test, not a tidy-up commit.

## Baseline of record (captured in plan.md, cited not re-run)

`7deadff0a4f3dfd2744b5e1e35680c0d70f4565e` — **784 passed, 0 failed**:
`tests/runtime/test_bridge_cores.py` + `test_bridge_composition.py` (71 passed) and
`tests/next/` + `tests/specify_cli/next/` + `tests/integration/test_custom_mission_runtime_walk.py`
(713 passed). Verified first-hand this session: `git log --oneline
7deadff0a4f3dfd2744b5e1e35680c0d70f4565e..HEAD -- src/runtime/next/
src/specify_cli/cli/commands/doctor.py src/specify_cli/cli/commands/_identity_audit.py
tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` returns empty — **no drift**
in any file this mission touches since the baseline was captured, so every line-number citation
below (re-verified against the current checkout, not carried over from plan.md unchecked) is
still accurate. #3284 (23 known-red main-suite failures) is a separate, pre-existing, unrelated
tracking issue — not to be conflated with this baseline or fixed by either WP below.

Each WP's own targeted test surface and pytest invocation are stated in its own prompt file
(charter Testing Requirements / C-005) — neither WP runs the full ~17,000-test suite.

## Dependency table

| WP | Title | Requirements | Depends on | Subtasks |
|----|-------|--------------|------------|----------|
| WP01 | Guard-table registry, strict/tolerant split, and `plan`'s guard table | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-010, FR-011, NFR-001, NFR-002, NFR-003, C-001, C-002 | — | T001–T007 |
| WP02 | `spec-kitty doctor mission-type` command | FR-007, FR-008, FR-009, NFR-004 | — | T008–T012 |

WP02 has **no functional dependency** on WP01 (plan.md's IC-05 note: "independent of IC-01-04
... sequenced after them in the PR narrative since it is the 'diagnosability' half of the
mission, not the 'fix' half"). Both are marked concurrently claimable below.

## Write-scope disjointness (concurrent-claim check)

| WP | Owned files |
|----|-------------|
| WP01 | `src/runtime/next/runtime_bridge_cores.py`, `src/runtime/next/runtime_bridge_composition.py`, `src/runtime/next/runtime_bridge.py`, `src/runtime/next/runtime_bridge_io.py`, `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_composition.py`, `tests/runtime/test_bridge_io.py` |
| WP02 | `src/specify_cli/cli/commands/doctor.py`, `src/specify_cli/cli/commands/_mission_type_audit.py` (new), `tests/specify_cli/cli/commands/test_doctor_mission_type.py` (new), `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` |

Zero file overlap between WP01 and WP02 — confirmed disjoint, both may be claimed and
implemented in parallel lanes. This is the full production+test file manifest for the mission
(6 production files + 5 test files — `tests/runtime/test_bridge_io.py` added per the
TASKS-VERIFY-002 fix below, alongside WP01's other owned test files); no file outside this list
is touched by either WP. The orchestrator has independently confirmed zero collisions against the
18 other currently-open PRs' file sets against this same manifest.

## Chokepoints (shared CI gates — not optional to skip, per plan.md's Gate Set)

Neither of these serializes WP01 against WP02 at the *implementation* level (disjoint write
scopes, no shared file), but both WPs land in **one PR** (see PR Shape below), so both gates
below run against the PR's *aggregate* diff and a regression from either WP can fail the whole
PR:

1. **Golden CLI-surface contract test**
   (`tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`,
   `test_registered_command_names_match_frozen_subcommands`, currently pinning **19**
   subcommands by frozenset equality). WP02 registers a 20th (`mission-type`) — the golden
   test's `FROZEN_SUBCOMMANDS` / `EXPECTED_OPTIONS` / `EXPECTED_HELP` **must** be updated in the
   same commit that registers the new command (WP02/T011), or CI fails deterministically on
   this frozen-contract check. This is WP02-internal but load-bearing: plan.md's Contracts
   section calls it "the one place in this mission where 'what looks like a docs-only test
   file' is actually load-bearing production-contract enforcement."
2. **PR diff-coverage critical-path gate** (`.github/workflows/ci-quality.yml`, `--fail-under=90
   --include 'src/runtime/next/*'`, fed by `integration-tests-next`'s `--cov=src/runtime/next`
   report). Every WP01 production file lives under `src/runtime/next/`, inside this gate's
   scope. WP01's ATDD commits (T001/T002) and the implementation commit (T003–T006) are
   expected to satisfy the 90% floor on new/changed lines, but this must be verified locally
   with `uv run diff-cover` against the base branch before push (plan.md Gate Set,
   PLAN-VERIFY-001's fix), not assumed.

Both gates run on every push of this mission's single PR (not only at merge time) — see
plan.md's Gate Set table for the full always-on-vs-path-gated breakdown.

## Requirement coverage (for `map-requirements`)

| WP | Requirements |
|----|--------------|
| WP01 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-010, FR-011, NFR-001, NFR-002, NFR-003, C-001, C-002 |
| WP02 | FR-007, FR-008, FR-009, NFR-004 |

C-003, C-004, C-005 are mission-scope/process constraints (bounded scope, no `validate_meta`
roster check, targeted test surface) satisfied by this tasks.md's own structure and each WP's
test-strategy section, not by a specific code change inside either WP — they are not mapped to
a WP via `map-requirements` for that reason (consistent with how constraints of that shape are
generally not code-mapped elsewhere in this repo's missions).

## PR Shape — carried forward from plan.md, re-verified against this WP slicing

**One PR for the whole mission**, per plan.md's own decision. Re-verified here against the
actual 2-WP slice, not just repeated: the full touched-file set is 6 production files + 5 test
files (see Write-scope disjointness above), the behavior change is one conceptual unit (close
one silent-fallback defect class across two call paths, plus one diagnostic command reading the
same underlying facts), and splitting into 2 WPs did not surface any migration-chain touch,
contract move, or cross-repo coordination trigger that plan.md's own split-it checklist would
flag. Both WPs are small enough to review in one sitting individually. Sizing the combined diff
precisely rather than folding it into one undifferentiated figure (TASKS-DECOMP-001/002 fix):
WP01's Commit 3 (T003-T006) is **two different sizes in two different places** — T004-T006 are
genuinely small, ~10 lines total across 3 files (`runtime_bridge_io.py`,
`runtime_bridge_composition.py`, `runtime_bridge.py`), each a one-call-site change; T003 alone,
in `runtime_bridge_cores.py`, adds a new `_GUARD_TABLES` dict, a new
`UnregisteredMissionFamilyError` exception class (carrying a mandated cross-reference docstring —
this codebase's own analogous exception, `charter.activation.mission_type_profiles.UnknownMissionTypeError`,
runs 13 lines, a concrete size anchor), a new `evaluate_guards_strict` function, the new ~5-way
`_evaluate_plan_guards` function, and a rewritten `evaluate_guards` — five new/changed symbols in
one file, realistically 40-60 new/changed lines, not "~10 lines." WP02's `_mission_type_audit.py`
is sized per WP02's own Context & Constraints guidance rather than as an independent target: it
combines the domain-classifier and CLI-glue roles of two precedent modules
(`src/specify_cli/status/identity_audit.py`, 361 lines; `src/specify_cli/cli/commands/_identity_audit.py`,
346 lines — 707 lines combined, `wc -l` verified), and WP02's own prompt explicitly instructs the
implementer not to treat either single precedent's line count as a target — so the new sibling
module should be expected to land at the two precedents' **combined LOC order of magnitude,
roughly 600-700 lines**, not the smaller "~300-line" figure this section previously stated.
With both figures corrected (WP01: ~10 lines in 3 files, plus ~40-60 lines / 5 symbols in one
file; WP02: one new CLI command + one new ~600-700-line sibling module), the combined diff is
still small enough to review in one sitting as a whole — a review budget of one sitting for a
handful of new symbols in one existing runtime file, three tiny call-site edits, and one new
sibling module of that scale is realistic for this codebase's typical review cadence. **This
tasks author's conclusion: one PR remains correct.** If a reviewer disagrees after seeing the
actual diff size once WP02's `_mission_type_audit.py` is drafted (plan.md's own PR Shape section
already flags this exact risk — "if the golden-contract update turns out to ripple into other
doctor-surface tests not identified here" — as a stop-and-rescope signal), that is a decision for
the orchestrator/operator to make, not something this tasks.md pre-decides.

## Work Package Sections

### WP01 — Guard-table registry, strict/tolerant split, and `plan`'s guard table

- **Prompt**: `tasks/WP01-guard-table-registry-and-plan-guards.md`
- **Depends on**: —
- **Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-010, FR-011,
  NFR-001, NFR-002, NFR-003, C-001, C-002
- **Goal**: Replace `evaluate_guards`'s if/if/fall-through with an explicit `_GUARD_TABLES`
  registry; split the shared `evaluate_guards` call into a strict lookup
  (`evaluate_guards_strict`, raises `UnregisteredMissionFamilyError`) that `_check_cli_guards`
  calls directly and a tolerant, WARNING-logging wrapper that `_check_composed_action_guard`
  calls directly; author `_evaluate_plan_guards` and register it under `"plan"`; fix the
  `_PRESENCE_FILE_TAGS` gap for `research.md`. This is IC-01 through IC-04 from plan.md's
  Implementation Concern Map, landed as one coherent, single-concern change (plan.md's own
  determination: these four concerns must land together, not be further split by an
  artificial tidy-up pre-commit).
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`): T001–T007

### WP02 — `spec-kitty doctor mission-type` command

- **Prompt**: `tasks/WP02-doctor-mission-type-command.md`
- **Depends on**: —
- **Requirement refs**: FR-007, FR-008, FR-009, NFR-004
- **Goal**: Ship `spec-kitty doctor mission-type --json [--fail-on <states>]`, modeled directly
  on `doctor identity`, classifying every mission under `kitty-specs/` into the FR-008
  6-state taxonomy. This is IC-05 + IC-06 from plan.md's Implementation Concern Map.
- **Included subtasks** (tracked via `spec-kitty agent tasks mark-status`): T008–T012

---

## Subtask Index

| ID | Description | WP | RED/impl | Parallel? |
|----|--------------|----|----------|-----------|
| T001 | RED: FR-010 ATDD pin — `plan`/`review` target-shape assertion (`[]`), genuinely RED against base; plus the FR-002/User-Story-2-AC3 `plan`/`research` tightening pin, the `plan`/`specify` branch pin (User Story 2 AC2) plus `plan`/`plan` and fail-closed-else branch pins (hardening beyond spec.md's literal Acceptance Scenarios), and a disk-backed `gather_artifact_presence` pin for the `research.md` presence tag | WP01 | RED | No |
| T002 | RED: FR-011 ATDD pin — unregistered-family fall-through, 3 assertions (`evaluate_guards_strict` raises; `_check_cli_guards` propagates via injection seam; `_check_composed_action_guard` returns `[]` + WARNING log) | WP01 | RED | No |
| T003 | Add `_GUARD_TABLES`, `UnregisteredMissionFamilyError`, `evaluate_guards_strict`, tolerant `evaluate_guards` wrapper, `_evaluate_plan_guards` in `runtime_bridge_cores.py` | WP01 | impl | No |
| T004 | Add `"research.md"` to `_PRESENCE_FILE_TAGS` in `runtime_bridge_io.py`; update module docstring "three"→"four" | WP01 | impl | Yes (with T005/T006) |
| T005 | `_check_composed_action_guard` in `runtime_bridge_composition.py`: call `evaluate_guards_strict` directly, catch, WARNING-log, return `[]` | WP01 | impl | Yes (with T004/T006) |
| T006 | `_check_cli_guards` in `runtime_bridge.py`: call `evaluate_guards_strict` directly, no catch | WP01 | impl | Yes (with T004/T005) |
| T007 | Verify T001/T002 GREEN; zero new reds vs. 784-baseline; local `diff-cover` check against `src/runtime/next/*` | WP01 | impl | No |
| T008 | RED: FR-008/SC-005/SC-006 ATDD pin — `test_doctor_mission_type.py`, fixture tree with one mission per taxonomy state + FR-008 boundary case + `--fail-on` behavior + an automated NFR-004 timing regression test (synthetic 200-mission fixture, `elapsed < 2.0`) | WP02 | RED | No |
| T009 | Implement `_mission_type_audit.py` — `MissionTypeState`, `classify_mission_type`, `audit_mission_types`, `summarize_mission_types`, `run_mission_type_audit` | WP02 | impl | No |
| T010 | Implement `doctor.py` `mission-type` thin `@app.command` shell | WP02 | impl | Yes (with T011) |
| T011 | Update golden contract test: `FROZEN_SUBCOMMANDS`, `EXPECTED_OPTIONS["mission-type"]`, `EXPECTED_HELP["mission-type"]`, 19→20 count comment | WP02 | impl | Yes (with T010) |
| T012 | Verify T008 GREEN, including the automated NFR-004 timing test; manual timing spot-check as a belt-and-suspenders confirmation; targeted test surface green | WP02 | impl | No |

---

> Replace-placeholder note: this file was hand-authored per the mission's tasks-phase brief
> (no `/spec-kitty.tasks` LLM step available in this dispatch — the canonical tasks-template.md
> structure is followed directly). `spec-kitty agent tasks map-requirements` and
> `spec-kitty agent mission finalize-tasks` are the canonical tools that validate and finalize
> this file's dependency declarations and write `lanes.json` — run after the WP prompt files
> exist.
