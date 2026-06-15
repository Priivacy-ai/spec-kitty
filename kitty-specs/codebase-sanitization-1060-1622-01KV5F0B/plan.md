# Implementation Plan: Internal `--feature` & `status_service` sanitization

**Branch**: `mission/codebase-sanitization-1060-1622` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/codebase-sanitization-1060-1622-01KV5F0B/spec.md`

## Summary

A tightly-bounded #1797 sanitization slice with two workstreams. **Workstream 1
(#1060-A):** remove the hidden `--feature` Typer alias from the 10 internal/agent
command modules, retarget their `resolve_selector` calls to the mission-only
path, update in-scope tests, and tighten the terminology gate to forbid the
alias on that cluster — `resolve_selector` and `_legacy_aliases.py` stay for the
deferred user-facing commands. **Workstream 2 (#1622):** verify-only — research
(see [research.md](research.md) R1) proved the code work was already completed by
mission 01KTPKST WP09; this mission confirms the resolved import-graph state and
closes the ticket with the re-classification. Net effect: LOC-negative, no
runtime/status hot-path edits, rebase-safe.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer (CLI), pytest, ruff, mypy; internal:
`specify_cli.cli.selector_resolution`, `specify_cli.missions._legacy_aliases`
**Storage**: N/A (no data layer touched)
**Testing**: pytest — contract test `tests/contract/test_terminology_guards.py`
(gate flip, ATDD-first), per-command unit tests under
`tests/specify_cli/cli/commands/`, dead-symbol/architectural gates under
`tests/architectural/`
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows)
**Project Type**: single (Python CLI package)
**Performance Goals**: N/A (no hot-path / throughput change)
**Constraints**: Bounded conflict surface — **zero** diff hunks under
`src/specify_cli/status/`, `src/specify_cli/task_utils/`, or `legacy_detector.py`
(NFR-001); net LOC-negative in `src/` (NFR-002); ruff+mypy+full suite green,
dead-symbol baselines not regressed (NFR-003); rebase-safe vs parallel bug-fix
landings.
**Scale/Scope**: 10 in-scope command modules; 38 in-scope `--feature`
occurrences; 1 contract-test flip; ~a subset of ~30 `--feature` test files;
0 `status_service.py` edits (verify-only for #1622).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Terminology Canon** (`Mission`/`--mission` canonical; `feature` prohibited
  for active systems): this mission *advances* the canon by deleting alias
  surface. ✔
- **ATDD-First (C-011)**: gate flip lands as a failing test before removal. ✔
- **Bulk-Edit discipline (DIRECTIVE_035)**: `change_mode: bulk_edit` set;
  `occurrence_map.yaml` authored and validated (structural + admissibility both
  `valid=True`). ✔
- **`__all__` Convention (C-007)**: no `__all__` changes (workstream 2 is
  verify-only; the de-export already landed in 01KTPKST). ✔
- **No-test-deletion-to-reduce-code (C-001/high-risk discipline)**: in-scope
  tests are *updated* (alias→`--mission` / rejection assertions), not deleted to
  pass. ✔
- **PR-bound, no direct origin/main push (C-003)**: lands via PR. ✔
- No charter violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/codebase-sanitization-1060-1622-01KV5F0B/
├── plan.md              # This file
├── spec.md              # Mission spec
├── research.md          # Phase 0: #1614 archaeology + alias-shape + caller analysis
├── occurrence_map.yaml  # Bulk-edit classification (workstream 1)
├── checklists/requirements.md
├── decisions/           # DM-01KV5F16… (resolved: verify-only)
└── tasks/               # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/
│   ├── agent/{status,tasks,workflow,context,mission}.py   # WS1: remove --feature
│   ├── charter/lint.py                                    # WS1: remove --feature
│   ├── materialize.py                                     # WS1: remove --feature
│   ├── validate_encoding.py                               # WS1: remove --feature
│   ├── validate_tasks.py                                  # WS1: remove --feature
│   └── verify.py                                          # WS1: remove --feature
├── cli/selector_resolution.py                             # RETAINED (no edit)
├── missions/_legacy_aliases.py                            # RETAINED (no edit)
└── coordination/status_service.py                         # WS2: verify-only (no edit)

tests/
├── contract/test_terminology_guards.py                    # WS1: gate flip (ATDD-first)
├── specify_cli/cli/commands/…                             # WS1: in-scope alias tests → --mission
└── architectural/test_no_dead_symbols.py + _baselines.yaml # WS2: verify green (no edit)
```

**Structure Decision**: Single Python CLI package; all edits live under
`src/specify_cli/cli/commands/` + `tests/`. No new modules.

## Complexity Tracking

*No charter violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Terminology gate flip (ATDD-first)

- **Purpose**: Make alias-absence on the in-scope cluster machine-enforced before
  any removal, so the change is test-driven and regression-proof.
- **Relevant requirements**: FR-004, SC-002.
- **Affected surfaces**: `tests/contract/test_terminology_guards.py` (add an
  in-scope-cluster rule: fail on any `--feature` Typer option, hidden or visible,
  in the 10 listed files; keep the global hidden-only rule for out-of-scope).
- **Sequencing/depends-on**: none (lands first, red).
- **Risks**: must scope the new rule to the exact in-scope file list so it does
  not fail on the retained out-of-scope commands.

### IC-02 — Remove the alias from the agent-namespace commands

- **Purpose**: Delete `--feature` + `feature`/`explicit_feature` plumbing from
  `agent status/tasks/workflow/context/mission`, retargeting `resolve_selector`
  calls to the mission-only path.
- **Relevant requirements**: FR-001, FR-002, SC-001; occurrence_map cs-001..005,
  cli-001..005.
- **Affected surfaces**: the 5 `agent/*.py` modules. Largest is `agent/tasks.py`
  (12 hits) — candidate for its own WP.
- **Sequencing/depends-on**: IC-01 (gate exists first).
- **Risks**: `agent/workflow.py` also imports
  `merge_append_preserving_coordination_event_log_bytes` — that import is
  unrelated and MUST stay; touch only the alias.

### IC-03 — Remove the alias from the validate/materialize/charter-lint/verify commands

- **Purpose**: Same removal for `charter lint`, `materialize`,
  `validate_encoding`, `validate_tasks`, `verify`.
- **Relevant requirements**: FR-001, FR-002; occurrence_map cs-006..010,
  cli-006..010.
- **Affected surfaces**: the 5 non-agent in-scope modules.
- **Sequencing/depends-on**: IC-01.
- **Risks**: low; uniform 1–2 hits each.

### IC-04 — Update in-scope tests + prove out-of-scope unchanged

- **Purpose**: Update tests that invoke in-scope commands with `--feature` to use
  `--mission` (and add de-alias rejection assertions); prove out-of-scope
  commands still accept the alias (FR-005, SC-005).
- **Relevant requirements**: FR-002, FR-005, SC-001, SC-005; occurrence_map
  tf-001..002.
- **Affected surfaces**: in-scope subset of `tests/`; a focused regression test
  asserting an out-of-scope command (e.g. `merge`) still resolves `--feature`.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: must enumerate the in-scope test subset precisely (out-of-scope
  callers stay) — `git grep -- --feature tests/` at WP start.

### IC-05 — #1622 verify-and-close (no code)

- **Purpose**: Confirm the already-resolved state and close the ticket.
- **Relevant requirements**: FR-006, FR-007.
- **Affected surfaces**: none in `src/`. Evidence-only: grep proof that
  `append_event_log_batch`/`read_wp_lane_actor` are absent and the 3 enums/error
  are de-exported live internals; dead-symbol gate green; then close #1622 with
  the re-classification note.
- **Sequencing/depends-on**: none (independent of WS1).
- **Risks**: none — explicitly forbidden from editing `status_service.py`
  (re-deleting breaks the build, per 01KTPKST closeout).

## Phase 0 — Research

Complete. See [research.md](research.md): R1 resolves the #1622 wire-or-retire
decision (already-done; verify-only); R2 documents the alias declaration shape +
in-scope footprint; R3 shows first-party caller impact is nil; R4 specifies the
gate flip; R5 scopes the test footprint.

## Phase 1 — Design & Contracts

- **Data model**: none — no entities, storage, or schema. (data-model.md omitted
  intentionally; this is a code-surface removal + verify.)
- **Contracts**: the externally-observable contract is the CLI surface itself —
  encoded as the terminology gate (FR-004) + the de-alias behavior tests
  (FR-001/FR-002) + the out-of-scope-preservation test (FR-005). No HTTP/API
  contracts apply.
- **Bulk-edit artifact**: `occurrence_map.yaml` authored, 8 categories each with
  an explicit action, validated (`validate_occurrence_map` + `check_admissibility`
  both `valid=True`).

## Post-Planning Brownfield Checks (standing)

Run before `/spec-kitty.tasks`: foldable-issue search across #1797 children,
split-brain/LOC scan, deprecation check. Initial finding already recorded:
**#1622 folds to verify-only** (the deeper #1614 archaeology showed the code work
was already complete) — scope adjusted accordingly. Record any further outcomes
here.
