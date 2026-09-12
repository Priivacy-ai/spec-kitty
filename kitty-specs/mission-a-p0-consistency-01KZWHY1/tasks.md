# Tasks — Mission A — P0 Read/Write Consistency

**Mission**: `mission-a-p0-consistency-01KZWHY1` | **Branch**: `fix/mission-a-p0-consistency`
**Planning base**: `fix/mission-a-p0-consistency` | **Merge target**: `fix/mission-a-p0-consistency`

Four independent, module-local P0 fixes — **one WP per issue** (C-001 non-goal:
no shared helper). WP01–WP03 are independent (parallel-capable); **WP04 (#3311)
is sequenced LAST** (highest blast radius) via a dependency on the other three.
Every WP carries its product fix, non-fakeable green-wash guard tests, and the
NFR-005 regression-exit (relocate/replace the repro, drop the marker, canonical
marks + guard docstring).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Read-back merged record; build counts/JSON/event from it | WP01 | |
| T002 | On-disk emit-spy guard test | WP01 | [P] |
| T003 | Relocate #3320 repro → `tests/cli/commands/`; canonicalize | WP01 | |
| T004 | ruff/mypy + targeted retrospect suite | WP01 | |
| T005 | `overall_verdict` exempts only empty placeholder (`description==MARKER`) | WP02 | |
| T006 | Guard tests: partial-authoring, all-scaffold, real-`AC-001`-no-marker | WP02 | [P] |
| T007 | Relocate #3231 repro → `tests/acceptance/`; canonicalize | WP02 | |
| T008 | Touched-consumer check (incl. `acceptance_verdict.py`) + ruff/mypy | WP02 | |
| T009 | `ProjectMetadata` round-trips `schema_version` (load+save); drop mask entry | WP03 | |
| T010 | Verify runner success-path stamp + dry_run-writes-nothing; keep 2nd writer consistent | WP03 | |
| T011 | Round-trip unit test (load→save preserves `schema_version`) | WP03 | [P] |
| T012 | REPLACE #3334 repro: real `MigrationRunner.upgrade()`, STALE fixture, 4 post-conds | WP03 | |
| T013 | ruff/mypy + targeted upgrade suite | WP03 | |
| T014 | Execution-begun signal via resolved coord-aware surface | WP04 | |
| T015 | Gate `_compute_and_write_lanes`: preserve `planning_commit_sha` or refuse | WP04 | |
| T016 | Guard tests: non-`None`-tip preservation; observable regeneration (benign) | WP04 | [P] |
| T017 | Relocate #3311 repro → `tests/specify_cli/cli/commands/agent/`; canonicalize | WP04 | |
| T018 | ruff/mypy + targeted finalize suite (serial if daemon) | WP04 | |

## Work Packages

### WP01 — #3320 retrospect `--update` reports/emits the persisted record *(P1, land first)*

- **Goal**: report counts/`findings_status` and emit `RetrospectiveCaptured` from
  the merged on-disk record, not the pre-merge generated one.
- **Independent test**: seed `has_findings`+1 gap; `create --update` with a
  `ran_no_findings` generator; assert JSON **and** an emit-spy match on-disk.
- **Subtasks**: T001, T002, T003, T004.
- **Dependencies**: none.
- **Prompt**: `tasks/WP01-retrospect-update-persisted.md` (~280 lines).

### WP02 — #3231 acceptance verdict scaffold discriminator *(P1)*

- **Goal**: `overall_verdict` exempts only the contentless empty placeholder
  (`description==SCAFFOLD_TODO_MARKER`); seeded-pending FR rows + all-scaffold
  stay `pending`.
- **Independent test**: verdict over partial-authoring / all-scaffold / empty-only
  / real-`AC-001`-no-marker row sets.
- **Subtasks**: T005, T006, T007, T008.
- **Dependencies**: none.
- **Prompt**: `tasks/WP02-acceptance-verdict-scaffold.md` (~300 lines).

### WP03 — #3334 failed upgrade recoverability (`save()` root fix) *(P2)*

- **Goal**: `ProjectMetadata` round-trips `schema_version` so no `save()` caller
  strips it; a failed upgrade stays recoverable; genuine pre-3.x stays blocked.
- **Independent test**: real `MigrationRunner.upgrade()` with a stub failing
  migration; STALE fixture; assert stamp==pre_schema, gate no `SystemExit`,
  dry_run byte-identical, genuine-pre-3.x still `SystemExit(4)`.
- **Subtasks**: T009, T010, T011, T012, T013.
- **Dependencies**: none.
- **Prompt**: `tasks/WP03-upgrade-schema-roundtrip.md` (~360 lines).

### WP04 — #3311 re-finalize preserves provenance *(P3, LAST — highest blast radius)*

- **Goal**: gate finalize recompute on "execution begun" (resolved coord-aware
  status surface); preserve `planning_commit_sha` or refuse; pre-execution
  re-finalize still regenerates.
- **Independent test**: execution-begun re-finalize preserves a non-`None` SHA;
  pre-execution re-finalize observably regenerates.
- **Subtasks**: T014, T015, T016, T017, T018.
- **Dependencies**: WP01, WP02, WP03 (sequences #3311 last).
- **Prompt**: `tasks/WP04-finalize-provenance-guard.md` (~340 lines).

## Sequencing

WP01 ∥ WP02 ∥ WP03 (independent lanes) → WP04. MVP slice: WP01 (lowest risk).
Regression-exit (NFR-005/SC-006) is each WP's DoD; at completion
`pytest tests/ -m regression` shows none of the four green.
