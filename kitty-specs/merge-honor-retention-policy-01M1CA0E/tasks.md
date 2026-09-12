# Tasks: Merge Honors Mission Retention Policy (#3131)

**Mission**: `merge-honor-retention-policy-01M1CA0E`
**Planning base / merge target**: `fix/3131-merge-retention`

Subtask completion is event-sourced — record with
`spec-kitty agent tasks mark-status Txxx --status done`. The rows below are
reference rows, not checkboxes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `retain_branches`/`retain_worktrees` to `MissionMetaOptional` | WP01 | |
| T002 | Add `read_retention_from_meta` (raw, uncoerced) over `load_meta_fail_closed` | WP01 | |
| T003 | Add pure `resolve_merge_retention` + `RetentionDecision` (precedence, provenance, coupled coord) | WP01 | |
| T004 | Resolver unit tests: 6 precedence cases + malformed value + corrupt meta | WP01 | |
| T005 | Red-first `@pytest.mark.regression` repro: coord retaining mission survives default merge (RED on main) | WP02 | |
| T006 | Tri-state cleanup flags (`Optional[bool]`, default `None`); thread unchanged to the resolver site | WP02 | |
| T007 | Resolve once in unlocked `_run_lane_based_merge` (primary partition); emit retention warning + override notice | WP02 | |
| T008 | `_MergeRunState.teardown_coordination`; pass resolved bools into locked driver; couple coord marker-flatten + coord-worktree teardown | WP02 | |
| T009 | `merge --abort` coordination teardown honors retention (skip + warn) | WP02 | |
| T010 | Audit `orchestrator_api` merge entry (C-007): route through resolver or document out-of-scope | WP02 | |
| T011 | Executor + abort unit tests: coupled coord gate, malformed value, override notice, abort-survives, scratch-still-cleaned | WP02 | |
| T012 | Forecast: reuse `resolve_merge_retention` against primary meta; emit resolved values + `retention` conflict note | WP03 | [P] |
| T013 | Update `test_forecast_seam.py` golden key set + a resolved-retention forecast assertion | WP03 | [P] |
| T014 | `create_mission_core` keyword-only `retain_branches`/`retain_worktrees`; conditional mint (field-absent when false) | WP04 | [P] |
| T015 | `mission create` CLI `--retain-branches`/`--retain-worktrees` typer options | WP04 | [P] |
| T016 | Create-time mint tests: flags → meta fields; no flags → fields absent; meta round-trip | WP04 | [P] |
| T017 | Correct stale `CLAUDE.md` "Merge & Preflight Patterns" doc (C-005) + add retain⇔keep mapping (C-004) | WP05 | |
| T018 | Merge docs + CLI help text: retention policy, fail-closed, retain⇔keep mapping, scratch-worktree note (C-006) | WP05 | |
| T019 | Specify-interview prompt: create-time retention opt-in note (template source) | WP05 | |
| T020 | CHANGELOG.md entry (#3131) | WP05 | |

## Work Packages

### WP01 — Retention meta field + pure resolver (foundation)

- **Goal**: The single machine-readable authority + the pure resolver every
  consumer shares. Establishes the `RetentionDecision` contract.
- **Priority**: P1 (shared dependency of WP02/WP03/WP04).
- **Independent test**: resolver unit tests cover all 6 precedence cases +
  malformed + corrupt without touching git.
- **Subtasks**: T001, T002, T003, T004
- **Dependencies**: none
- **Prompt**: `tasks/WP01-retention-meta-and-resolver.md` (~350 lines)

### WP02 — Merge enforcement: honor, couple coord, abort, red-first (core)

- **Goal**: Make `spec-kitty merge` honor the resolved decision fail-closed;
  couple coordination teardown; abort honors retention; the issue-pinned
  red-first regression.
- **Priority**: P1 (the data-loss fix itself).
- **Independent test**: the red-first regression is RED on main and GREEN after
  this WP through the real `_run_lane_based_merge` entry point.
- **Subtasks**: T005 (red-first, committed FIRST), T006, T007, T008, T009, T010, T011
- **Dependencies**: WP01
- **Prompt**: `tasks/WP02-merge-enforcement-and-red-first.md` (~600 lines)

### WP03 — Dry-run forecast reuses the resolver

- **Goal**: `merge --dry-run` reports the RESOLVED cleanup decision + a
  retention-conflict note instead of echoing raw flags.
- **Priority**: P2.
- **Independent test**: forecast payload for a retaining mission shows
  `delete_branch: false` + `retention` provenance.
- **Subtasks**: T012, T013
- **Dependencies**: WP01
- **Prompt**: `tasks/WP03-forecast-resolver-reuse.md` (~250 lines)

### WP04 — Create-time retention opt-in

- **Goal**: `mission create --retain-branches/--retain-worktrees` mint the
  fields into `meta.json`; field-absent when not requested.
- **Priority**: P2.
- **Independent test**: create with flags → fields present; without → absent.
- **Subtasks**: T014, T015, T016
- **Dependencies**: WP01
- **Prompt**: `tasks/WP04-create-time-retention-optin.md` (~300 lines)

### WP05 — Docs, CLAUDE.md correction, CHANGELOG

- **Goal**: Correct the stale preflight doc, document the retain⇔keep mapping
  and fail-closed policy, add the specify opt-in note, CHANGELOG.
- **Priority**: P2 (convergence).
- **Independent test**: terminology/docs-freshness gates pass; CLAUDE.md no
  longer references the non-existent `PreflightResult` merge surface.
- **Subtasks**: T017, T018, T019, T020
- **Dependencies**: WP02, WP03, WP04
- **Prompt**: `tasks/WP05-docs-and-changelog.md` (~250 lines)

## MVP scope

WP01 + WP02 deliver the data-loss fix (authority + honored enforcement + red-first
proof). WP03/WP04/WP05 complete the lifecycle (preview, authoring, docs).

## Parallelization

After WP01 lands, WP02 / WP03 / WP04 touch disjoint files and can run in parallel.
WP05 converges last.
