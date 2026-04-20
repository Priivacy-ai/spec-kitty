# Tasks: Specify Brief Intake Mode

**Mission**: `specify-brief-intake-mode-01KPMXQB` (`01KPMXQBM67RJQTCWB31SC6PGM`)
**Branch**: `main` → `main`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Generated**: 2026-04-20

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-----------|----|---------|
| T001 | Create `src/specify_cli/mission_brief.py` — write/read/clear helpers for `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` | WP01 | | [D] |
| T002 | Create `src/specify_cli/cli/commands/intake.py` — `intake()` command with path/stdin/`--force`/`--show` | WP01 | | [D] |
| T003 | Register `intake` in `src/specify_cli/cli/commands/__init__.py` | WP01 | | [D] |
| T004 | Update `.gitignore` — add `.kittify/mission-brief.md` and `.kittify/brief-source.yaml` | WP01 | [D] |
| T005 | Write `tests/specify_cli/test_mission_brief.py` — unit tests for mission_brief module | WP01 | [D] |
| T006 | Write `tests/specify_cli/cli/commands/test_intake.py` — integration tests via `CliRunner` | WP01 | [D] |
| T007 | Edit `src/specify_cli/missions/software-dev/command-templates/specify.md` — insert Brief Context Detection section | WP02 | | [D] |
| T008 | Run `spec-kitty upgrade` to propagate the template change to all 13 agent directories | WP02 | | [D] |
| T009 | Verify propagation — spot-check section presence in `.claude/commands/spec-kitty.specify.md` | WP02 | | [D] |

---

## Work Package WP01 — `spec-kitty intake` CLI Command

**Goal**: Implement the `spec-kitty intake <path>` command end-to-end: business logic module, CLI command, registration, gitignore, and full test coverage.

**Priority**: High (enables the primary user workflow)
**Estimated prompt size**: ~380 lines
**Dependencies**: none
**Prompt**: [tasks/WP01-intake-cli-command.md](tasks/WP01-intake-cli-command.md)

**Included subtasks**:
- [x] T001 Create `src/specify_cli/mission_brief.py` — write/read/clear helpers (WP01)
- [x] T002 Create `src/specify_cli/cli/commands/intake.py` — intake() command (WP01)
- [x] T003 Register intake in `src/specify_cli/cli/commands/__init__.py` (WP01)
- [x] T004 Update `.gitignore` with two new entries (WP01)
- [x] T005 Write `tests/specify_cli/test_mission_brief.py` — unit tests (WP01)
- [x] T006 Write `tests/specify_cli/cli/commands/test_intake.py` — CLI integration tests (WP01)

**Parallel opportunities**: T004, T005, T006 are all independent of each other (different files, different concerns). T001 must precede T002 and T005. T002+T003 must precede T006.

**Acceptance**:
- `spec-kitty intake PLAN.md` writes `.kittify/mission-brief.md` and `.kittify/brief-source.yaml`
- `spec-kitty intake -` reads from stdin correctly
- `--force` overwrites; without it exits 1 on existing brief
- `--show` prints content + provenance; exits 1 if absent
- `.gitignore` contains both new entries
- `pytest tests/specify_cli/test_mission_brief.py tests/specify_cli/cli/commands/test_intake.py -v` passes
- `mypy --strict src/specify_cli/mission_brief.py src/specify_cli/cli/commands/intake.py` passes

---

## Work Package WP02 — Specify Template: Brief Context Detection

**Goal**: Insert the Brief Context Detection section into the specify source template and propagate it to all 13 agent directories via `spec-kitty upgrade`.

**Priority**: High (enables the brief-intake mode in /spec-kitty.specify)
**Estimated prompt size**: ~220 lines
**Dependencies**: none (independent of WP01)
**Prompt**: [tasks/WP02-specify-template-brief-context-detection.md](tasks/WP02-specify-template-brief-context-detection.md)

**Included subtasks**:
- [x] T007 Edit specify source template — insert Brief Context Detection section (WP02)
- [x] T008 Run `spec-kitty upgrade` to propagate to all 13 agent directories (WP02)
- [x] T009 Verify propagation in `.claude/commands/spec-kitty.specify.md` (WP02)

**Parallel opportunities**: T008 must follow T007. T009 must follow T008. Sequential.

**Acceptance**:
- New section appears in `src/specify_cli/missions/software-dev/command-templates/specify.md` after "Charter Context Bootstrap" and before "Discovery Gate"
- `spec-kitty upgrade` exits 0
- Section is present in `.claude/commands/spec-kitty.specify.md` (spot-check)

---

## Parallelization Summary

WP01 and WP02 are fully independent. They can run concurrently on separate lanes.

```
WP01 ─────────────────────────────────────────────── (CLI command)
WP02 ─────────────────────────────────────────────── (Template edit)
```

Both must complete before the feature can be end-to-end tested.
