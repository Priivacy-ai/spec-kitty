# Implementation Plan: Remove hidden --feature alias from user-facing CLI commands

**Branch**: `feat/feature-alias-removal` | **Date**: 2026-06-26 | **Spec**: `kitty-specs/feature-alias-removal-01KW0N87/spec.md`
**Input**: Feature specification from `kitty-specs/feature-alias-removal-01KW0N87/spec.md`
**Mission ID**: `01KW0N879YNT6HYB6DX1JE6STX`

---

## Summary

Hard-remove the hidden `--feature` Typer option from the 8 remaining user-facing CLI commands
(`implement`, `merge`, `next`, `research`, `context`, `accept`, `lifecycle plan`, `lifecycle tasks`,
`mission_type current`). Replace every `resolve_selector(alias_value=feature, alias_flag="--feature", ...)`
call with a two-line inline whitespace-normalization guard that raises `typer.BadParameter` (exit code 2)
on empty/None input. Rename `feature`/`feature_slug` internal parameter names to `mission`/`mission_slug`
within each in-scope file. Extend the terminology guard to cover the 8 new files. Add 8 no-selector
regression tests. Update docs and CHANGELOG.

The `resolve_selector` function is retained (C-005). Stored JSON field keys (`feature_slug` in
`meta.json`, event JSONL) are immutable (C-003).

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer, Click, Rich (all existing; no new dependencies)
**Storage**: N/A — no schema changes; stored artifact field names are immutable
**Testing**: pytest with typer.testing.CliRunner; ruff + mypy for static checks; `PWHEADLESS=1 pytest ... -n auto --dist loadfile`
**Target Platform**: Linux CLI (same as the rest of the codebase)
**Project Type**: Single Python package (`src/specify_cli`)
**Performance Goals**: N/A — this is a CLI surface change, not a hot path
**Constraints**: No function modified may exceed cyclomatic complexity 15 (NFR-003); no test deletions (NFR-001); out-of-scope files untouched (NFR-004)
**Scale/Scope**: 8 source files; 3 test files updated; 1 new test file; ~6 doc files

---

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No charter file found at `.kittify/charter/charter.md` in this clone. Charter check skipped.

Terminology Canon compliance verified:
- All new code uses `mission`, `mission_slug`, `--mission` as canonical terms.
- `feature`, `feature_slug`, `--feature` appear only in comments documenting their removal.
- `resolve_selector` is retained (not deleted), satisfying C-005.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/feature-alias-removal-01KW0N87/
├── plan.md                             # This file
├── research.md                         # Phase 0 output — full caller-audit evidence
├── data-model.md                       # Phase 1 output — selector-resolution contract
├── quickstart.md                       # Phase 1 output — per-WP edit guide
├── contracts/
│   └── no-selector-error-contract.md  # Exit code 2 + message shape contract
└── tasks.md                            # Phase 2 output (not yet created)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/
├── implement.py         ← WP01: remove --feature, refactor detect_feature_context
├── merge.py             ← WP01: remove --feature, rename resolved_feature
├── next_cmd.py          ← WP02: remove --feature, inline guard in _resolve_mission_slug
├── research.py          ← WP02: remove --feature, inline guard
├── context.py           ← WP02: remove --feature, inline guard
├── accept.py            ← WP02: remove --feature, rename feature_slug params
├── lifecycle.py         ← WP03: remove --feature (plan/tasks); positional rename (specify)
└── mission_type.py      ← WP03: remove --feature, inline guard

tests/
├── contract/
│   ├── test_terminology_guards.py      ← WP04: extend INSCOPE_FEATURE_FREE_FILES
│   ├── test_feature_alias_scope.py     ← WP04: flip merge assertions, extend INSCOPE
│   └── test_no_selector_guard.py       ← WP05: NEW — 8 no-selector regression tests
└── specify_cli/cli/
    └── test_no_visible_feature_alias.py ← WP04: add test_zero_feature_flags_exist_cli_wide

docs/
├── status-model.md                     ← WP06: update "deferred" language
├── reference/environment-variables.md  ← WP06: mark SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION inert
├── reference/orchestrator-api.md       ← WP06: remove --feature from opts list
└── engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md ← WP06: update implement opts

CHANGELOG.md                            ← WP06: unreleased entry
```

**Structure Decision**: Single project layout. All changes are in `src/specify_cli/cli/commands/`
and the adjacent test directory. No new source modules are introduced.

---

## Implementation Concern Map

### IC-01 — Flag removal + guard in implement.py and merge.py

- **Purpose**: Remove `--feature` from the two deepest commands (implement has `detect_feature_context`; merge has multi-function alias threading) and standardize their no-selector exits to code 2.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-006
- **Affected surfaces**: `src/specify_cli/cli/commands/implement.py`, `merge.py`
- **Sequencing/depends-on**: none
- **Risks**: `detect_feature_context` is called from two call sites and is `__all__`-exported; verify no external callers before changing its signature. `merge.py`'s `resolved_feature` rename is mechanical but spans ~10 occurrences across multiple helpers; a missed rename causes a NameError. `_run_real_merge` receives `resolved_feature` as a keyword argument — the rename must be consistent at both the definition and call site.

### IC-02 — Flag removal + guard in next_cmd.py, research.py, context.py, accept.py

- **Purpose**: Remove `--feature` from four simpler commands; each has a single `resolve_selector` call (or `or feature` pattern) to replace with the inline guard.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-006
- **Affected surfaces**: `src/specify_cli/cli/commands/next_cmd.py`, `research.py`, `context.py`, `accept.py`
- **Sequencing/depends-on**: none (independent of IC-01)
- **Risks**: `accept.py`'s `feature_slug` param renames touch two non-Typer helper functions; must confirm no callers pass `feature_slug=` as a keyword argument from outside the file. The `resolve_selector` import in `next_cmd.py` can be removed after the guard replacement; verify no other call in the file remains.

### IC-03 — Flag removal + positional rename in lifecycle.py and mission_type.py

- **Purpose**: Remove `--feature` from `plan()` and `tasks()` in lifecycle; rename the positional `feature`→`mission` in `specify()` per orchestrator ruling; remove `--feature` from `mission_type current`.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-006; orchestrator ruling
- **Affected surfaces**: `src/specify_cli/cli/commands/lifecycle.py`, `mission_type.py`
- **Sequencing/depends-on**: none (independent of IC-01, IC-02)
- **Risks**: `lifecycle.py` still calls `resolve_selector` in `specify()` with `alias_flag="--mission"` — this call must NOT be touched. The `resolve_selector` import in `lifecycle.py` must be kept because of that surviving call. The positional rename in `specify()` is a Python-level rename only; the CLI invocation is unchanged because Typer derives the metavar from the param name.

### IC-04 — Terminology guard extension and existing test updates

- **Purpose**: Extend `INSCOPE_FEATURE_FREE_FILES` with the 8 new files so any future reintroduction of `"--feature"` in those files fails CI. Update `test_feature_alias_scope.py` to reflect merge being in scope. Add zero-feature-flags assertion to `test_no_visible_feature_alias.py`.
- **Relevant requirements**: FR-007, FR-009
- **Affected surfaces**: `tests/contract/test_terminology_guards.py`, `tests/contract/test_feature_alias_scope.py`, `tests/specify_cli/cli/test_no_visible_feature_alias.py`
- **Sequencing/depends-on**: IC-01, IC-02, IC-03 (the guard must pass only after all 8 files are clean)
- **Risks**: `test_feature_alias_scope.py` tests currently assert that merge accepts `--feature`; those assertions must flip direction (from "merge accepts" to "merge rejects"), not be deleted. A mechanical find-and-replace risk: the `_INSCOPE_FILES` tuple in that file must be kept in sync with `INSCOPE_FEATURE_FREE_FILES` in `test_terminology_guards.py`.

### IC-05 — No-selector regression tests (FR-008)

- **Purpose**: Lock the no-selector guard behavior with 8 focused tests (one per command) to prevent the PR #1985 `TypeError` regression class from recurring.
- **Relevant requirements**: FR-008
- **Affected surfaces**: `tests/contract/test_no_selector_guard.py` (new file)
- **Sequencing/depends-on**: IC-01 through IC-03
- **Risks**: `spec-kitty implement` requires `wp_id` as a positional argument; the test must invoke it as `runner.invoke(app, ["implement", "WP01"])` (no `--mission`). `spec-kitty lifecycle plan` and `spec-kitty lifecycle tasks` are sub-commands of `lifecycle`; invoke as `["lifecycle", "plan"]` (no `--mission`). `spec-kitty mission-type current` with no `--mission` and no auto-detect (run from `tmp_path`).

### IC-06 — Docs and CHANGELOG (FR-010)

- **Purpose**: Remove stale references to `--feature` being available on user-facing commands from live docs and the CHANGELOG unreleased section.
- **Relevant requirements**: FR-010
- **Affected surfaces**: `docs/status-model.md`, `docs/reference/environment-variables.md`, `docs/reference/orchestrator-api.md`, `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md`, `CHANGELOG.md`
- **Sequencing/depends-on**: IC-01 through IC-03
- **Risks**: `docs/migration/feature-flag-deprecation.md` is explicitly excluded from the terminology scan — do not accidentally update it to claim `--feature` is fully gone from all commands (the migration doc's job is to name the deprecated form). Only update the _live usage_ docs (non-migration). The terminology guard test `test_no_feature_flag_in_live_first_party_docs` in `test_terminology_guards.py` will catch any remaining live-doc references.

---

## ORCHESTRATOR RULING

**Encoded**: IC-03 above and in `quickstart.md` WP03.

The `lifecycle.specify` sub-command's POSITIONAL argument `feature` is renamed to `mission`.
CLI invocation is unchanged: `spec-kitty lifecycle specify my-mission-name` continues to work
without modification. Only the Python parameter name, docstring references, and the help metavar
(`FEATURE` → `MISSION`) change. This is an internal rename satisfying the terminology canon.

---

## Branch Contract

**Current branch at plan start**: `feat/feature-alias-removal`
**Target branch**: `feat/feature-alias-removal`
**Merge target**: local `main` (via `spec-kitty merge`, then PR branch to origin/main)

All WPs execute on lane branches off `feat/feature-alias-removal` and merge back to it.
Per the no-direct-push policy, changes reach `origin/main` via a PR branch only.

---

## Complexity Tracking

No charter violations. All inline guards are two-to-three lines; no function approaches the complexity ceiling of 15.

| Note | Detail |
|------|--------|
| `implement()` is already `noqa: C901` | The function's existing complexity is unchanged by this mission; we remove a parameter, not add branching |
| Inline guards are 2-3 lines | `_normalize_selector` equivalence pattern; no nested conditionals |
