# Implementation Plan: Task Workflow Bug Fixes: Spec Path and Error Hint

**Branch**: `fix/task-workflow-bug-fixes` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/task-workflow-bug-fixes-01KV69BZ/spec.md`

## Summary

Two narrow call-site fixes to the task workflow CLI layer. Fix A swaps the topology-aware resolver for a topology-blind one when `map-requirements` reads `spec.md`, eliminating a "spec.md not found" failure that occurs whenever a coordination worktree exists. Fix B enhances the per-path zero-match error in `validate_glob_matches` to include a ready-to-paste YAML fragment for `create_intent`, and adds regression tests for both changes.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, pytest, mypy (strict)
**Storage**: N/A — no persistence layer changes
**Testing**: pytest with `--dist loadfile` parallel runs; 90%+ new-code branch coverage; mypy --strict must pass; ruff must pass
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: Single project
**Performance Goals**: spec.md path resolution remains pure-path (filesystem stat only, no subprocess or git calls) — NFR-002
**Constraints**: mypy --strict zero errors; ruff zero issues; no `# noqa` / `# type: ignore` without inline rationale; architectural test `test_no_raw_mission_spec_paths.py` must remain green; C-001 (use sanctioned resolver); C-002 (field name `create_intent` exactly); C-003 (fixes must be independently revertable)
**Scale/Scope**: 2 changed call sites across 2 modules; 2 new test functions

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | ✓ PASS | All changes in existing Python 3.11+ modules |
| mypy --strict | ✓ PASS | No new type annotations required; swapping one Path-returning function for another with identical signature |
| pytest 90%+ new code | ✓ PASS | Two new test functions added — one per fix — covering the new branches |
| ruff clean | ✓ PASS | No new complexity introduced |
| Terminology Canon (Mission not Feature) | ✓ PASS | No user-facing strings changed except the error hint (which already uses `create_intent`, not a legacy term) |
| `test_no_raw_mission_spec_paths.py` | ✓ PASS | IC-01 fix uses `primary_feature_dir_for_mission` from the sanctioned resolver module |
| Complexity ceiling ≤ 15 | ✓ PASS | Both change sites reduce or hold complexity — one line swapped, one string extended |

## Project Structure

### Documentation (this mission)

```
kitty-specs/task-workflow-bug-fixes-01KV69BZ/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not created here)
```

### Source Code (affected surfaces)

```
src/specify_cli/
├── cli/commands/agent/
│   └── tasks.py                  # IC-01: spec_md path swap (line ~3535-3541)
└── ownership/
    └── validation.py             # IC-02: validate_glob_matches error string (line ~379-382)

tests/specify_cli/
├── cli/commands/agent/
│   └── test_map_requirements_spec_path.py  # IC-01 regression test (new file, declared in create_intent)
└── ownership/
    └── test_validation.py  # IC-02 regression test (existing file, add method)
```

## Implementation Concern Map

### IC-01 — map-requirements spec.md topology fix

- **Purpose**: Ensure `map-requirements` reads `spec.md` from the primary checkout regardless of coordination worktree presence, eliminating the "spec.md not found" failure that blocks the post-setup-plan task workflow.
- **Relevant requirements**: FR-001, FR-002, FR-005, NFR-002, C-001
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/tasks.py` (lines ~3533–3544); import of `primary_feature_dir_for_mission` from `specify_cli.missions.feature_dir_resolver`
- **Sequencing/depends-on**: none — independent of IC-02
- **Risks**: `primary_feature_dir_for_mission` is topology-blind by design; confirm the import already exists in `tasks.py` or add it. Must verify the architectural test `test_no_raw_mission_spec_paths.py` passes with the new call site.

### IC-02 — validate_glob_matches create_intent YAML example

- **Purpose**: Enhance the per-path zero-match error message to include a ready-to-paste YAML fragment (`create_intent:\n  - <path>`), enabling agents and developers to self-recover without consulting documentation.
- **Relevant requirements**: FR-003, FR-004, NFR-003, C-002
- **Affected surfaces**: `src/specify_cli/ownership/validation.py` — `validate_glob_matches()` function, the `else` branch that appends to `result.errors` (lines ~370–383)
- **Sequencing/depends-on**: none — independent of IC-01
- **Risks**: The new multi-line string in the error message must not exceed NFR-003's 300-character ceiling. The `_nearest_match_suggestion` hint (when a close filename exists) must remain in the output alongside the new YAML fragment — they are appended independently.

### IC-03 — Regression tests

- **Purpose**: Lock in both fixes against future refactors with targeted, fast unit/integration tests.
- **Relevant requirements**: FR-004, FR-005, NFR-001
- **Affected surfaces**: Test files for `tasks.py` (IC-01) and `validation.py` (IC-02). Tests must be collected and pass in the parallel `pytest -n auto --dist loadfile` run.
- **Sequencing/depends-on**: IC-01 and IC-02 (tests validate the fixed behaviour)
- **Risks**: IC-01 test requires simulating a coord worktree on disk or mocking `CoordinationWorkspace.worktree_path`. Use the existing test fixture patterns to avoid real git operations.
