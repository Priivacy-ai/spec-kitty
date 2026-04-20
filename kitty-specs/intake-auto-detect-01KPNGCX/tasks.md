# Tasks: Intake Auto-Detect from Harness Plan Artifacts

**Mission**: intake-auto-detect-01KPNGCX  
**Branch**: `main` → `main`  
**Issue**: #703

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Research plan-mode behavior for all 13 harnesses (docs, GitHub source, empirical test) | WP01 | No |
| T002 | Produce `docs/reference/agent-plan-artifacts.md` with per-harness tables + source_agent mapping | WP01 | No |
| T003 | Create `src/specify_cli/intake_sources.py` with `HARNESS_PLAN_SOURCES` list | WP01 | No |
| T004 | Implement `scan_for_plans(cwd)` function in `intake_sources.py` | WP01 | No |
| T005 | Extend `write_mission_brief()` with optional `source_agent` kwarg; conditional YAML field | WP02 | No |
| T006 | Add `--auto` flag to `intake.py` with mutual exclusion guard | WP02 | No |
| T007 | Implement 0-match path: print no-match message, exit 1 | WP02 | [P] |
| T008 | Implement 1-match path: print BRIEF DETECTED, --force check, write brief, exit 0 | WP02 | [P] |
| T009 | Implement 2+-match path: numbered list, TTY prompt or non-TTY stderr + exit 1 | WP02 | [P] |
| T010 | Write `tests/specify_cli/test_intake_sources.py` (unit tests for scan_for_plans) | WP02 | [P] |
| T011 | Write `tests/specify_cli/cli/commands/test_intake.py` (CLI tests for --auto scenarios) | WP02 | [P] |

---

## Work Packages

---

### WP01 — Research Deliverable & Scan Module

**Priority**: P0 (gates WP02)  
**Estimated prompt size**: ~320 lines  
**Execution mode**: code_change  
**Depends on**: (none)

**Goal**: Produce the canonical harness reference document and the `intake_sources.py` module. WP02 cannot start until this is complete.

**Included subtasks**:
- [ ] T001 Research plan-mode behavior for all 13 harnesses (WP01)
- [ ] T002 Produce `docs/reference/agent-plan-artifacts.md` (WP01)
- [ ] T003 Create `src/specify_cli/intake_sources.py` with `HARNESS_PLAN_SOURCES` (WP01)
- [ ] T004 Implement `scan_for_plans(cwd)` in `intake_sources.py` (WP01)

**Implementation sketch**:
1. Research each of the 13 harnesses in priority order: official docs → GitHub source → empirical test → community reports
2. Write `docs/reference/agent-plan-artifacts.md` — per-harness table + source_agent mapping table
3. Create `intake_sources.py` with `HARNESS_PLAN_SOURCES` — verified entries active, lower-confidence as commented TODO blocks
4. Add `scan_for_plans(cwd: Path)` — iterates list, stats each candidate path, returns matches

**Parallel opportunities**: T001–T004 are sequential within WP01 (each builds on the previous).

**Risks**:
- Most harnesses may remain Inferred/Unknown after research → active list may be sparse or empty; this is acceptable and explicitly handled
- Empirical testing requires the harness to be installed; skip gracefully and document as "not empirically tested on this machine"

**Success criteria**:
- `agent-plan-artifacts.md` covers all 13 harnesses with explicit confidence level for each
- `scan_for_plans(Path("/tmp/empty"))` returns `[]` without exception
- `ruff check src/specify_cli/intake_sources.py` passes

**Prompt file**: `tasks/WP01-research-and-scan-module.md`

---

### WP02 — CLI Implementation & Tests

**Priority**: P1  
**Estimated prompt size**: ~480 lines  
**Execution mode**: code_change  
**Depends on**: WP01

**Goal**: Wire `--auto` into `spec-kitty intake`, extend `write_mission_brief()` with `source_agent`, and add full test coverage for all `--auto` scenarios.

**Included subtasks**:
- [ ] T005 Extend `write_mission_brief()` with optional `source_agent` kwarg (WP02)
- [ ] T006 Add `--auto` flag to `intake.py` with mutual exclusion guard (WP02)
- [ ] T007 Implement 0-match path in `--auto` (WP02)
- [ ] T008 Implement 1-match path in `--auto` (WP02)
- [ ] T009 Implement 2+-match path in `--auto` (WP02)
- [ ] T010 Write `tests/specify_cli/test_intake_sources.py` (WP02)
- [ ] T011 Write `tests/specify_cli/cli/commands/test_intake.py` (WP02)

**Implementation sketch**:
1. Extend `write_mission_brief()` signature — `source_agent` kwarg, conditional dict inclusion
2. Add `--auto: bool = typer.Option(False, "--auto")` to `intake()` function signature
3. Implement mutual exclusion guard at top of function body
4. Implement three result branches (0 / 1 / 2+ matches) using `scan_for_plans(Path.cwd())`
5. Write unit tests for scan logic (T010)
6. Write CLI tests covering all 9 acceptance scenarios (T011)

**Parallel opportunities**: T007/T008/T009 are logically parallel (different branches of the same function) but must all be in the same file — implement sequentially. T010 and T011 are independently testable.

**Risks**:
- TTY detection in `typer.testing.CliRunner`: CliRunner stdin is a StringIO, so `sys.stdin.isatty()` returns False — non-TTY path is the default in tests; mock `sys.stdin.isatty` → True for TTY tests
- `--force` interaction: check `brief_path.exists() and not force` before calling `write_mission_brief()`, same as the explicit-path branch

**Success criteria**:
- `pytest tests/specify_cli/test_intake_sources.py tests/specify_cli/cli/commands/test_intake.py -v` passes
- `ruff check src/specify_cli/mission_brief.py src/specify_cli/cli/commands/intake.py` passes
- `spec-kitty intake --help` shows `--auto` in output
- `brief-source.yaml` has no `source_agent` key for manual intake paths

**Prompt file**: `tasks/WP02-cli-implementation-and-tests.md`
