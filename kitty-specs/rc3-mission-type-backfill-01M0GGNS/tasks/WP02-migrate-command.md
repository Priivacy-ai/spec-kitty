---
work_package_id: WP02
title: migrate backfill-mission-type command
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
planning_base_branch: pr/rc3-mission-type-backfill
merge_target_branch: pr/rc3-mission-type-backfill
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-mission-type-backfill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-mission-type-backfill unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-mission-type-backfill-01M0GGNS-lane-a
base_commit: 6c1d61921c51722c63109f464799e73786e1a3f7
created_at: '2026-08-21T06:55:56.761330+00:00'
subtasks:
- T005
- T006
history: []
authoritative_surface: src/specify_cli/cli/commands/migrate_cmd.py
create_intent:
- tests/specify_cli/cli/commands/test_migrate_backfill_mission_type.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/migrate_cmd.py
- tests/specify_cli/cli/commands/test_migrate_backfill_mission_type.py
tags: []
tracker_refs: []
wp_code: WP02
---

# Work Package WP02 — `migrate backfill-mission-type` command

## Objective

Add a dedicated `@app.command(name="backfill-mission-type")` to
`src/specify_cli/cli/commands/migrate_cmd.py` wrapping WP01's `backfill_mission_type_repo`.
Mirror the `backfill-identity` option surface; diverge only where the spec requires.

## Subtasks

### T005 — Command
- Options: `--json`, `--dry-run`, `--mission SLUG` (same annotations/help style as `backfill_identity`).
- Resolve `repo_root` via `locate_project_root()`; None → `_error(...)` + exit 1 (existing helper).
- Call `backfill_mission_type_repo(repo_root, dry_run=dry_run, mission_slug=mission)`.
- Build the **stable** `--json` payload — identical keys for dry-run and live (FR-006/AC-7):
  `{dry_run, summary:{total, wrote, skip, needs_manual_resolution, error}, results:[{slug, action,
  mission_type, legacy_value, reason, dossier_warning}]}`.
- Human summary: counts + list `error` slugs+reasons; when `needs_manual_resolution>0` print an
  **actionable** diagnostic (which slugs; the fix is "a mission type whose governance profile
  resolves at some layer — built-in/org/project — or author/activate that type", NOT necessarily a
  typo) (FR-007, squad-2 BLOCKER-1).
- Exit contract (FR-007/AC-8): non-zero iff `error>0`; `--dry-run` always 0; clean live 0;
  `needs_manual_resolution>0` alone → 0.
- Catch WP01's structured unknown-slug error → print structured message + exit non-zero (FR-008/AC-9).
- Update the module docstring's subcommand list.

### T006 — Red-first CLI tests
`tests/specify_cli/cli/commands/test_migrate_backfill_mission_type.py`,
`pytestmark = [pytest.mark.unit, pytest.mark.fast]`, via `typer.testing.CliRunner`:
- `test_json_shape_identical_dry_run_and_live` (AC-7 — key-set equality of both payloads)
- `test_exit_codes_error_dryrun_clean` (AC-8)
- `test_unknown_mission_slug_structured_error` (AC-9 — `--mission nope` → exit≠0, structured msg)

## Definition of Done

- All WP02 tests green, each red-first; `ruff` + `mypy` clean; complexity ≤15.

## Terminal state

`done` when the above hold.

## Campsite folds (squad #3 Sonar census) — land WITH the WP02 commit

- **M1 (fold-now)** — hoist `_NO_PROJECT_ROOT = "Could not locate project root. No .kittify/ directory
  found in any parent directory."` next to the existing constants block (`migrate_cmd.py:56-71`) and fold
  the 5 existing call-sites (`:267,382,676,872,939`) plus WP02's new one onto it. Same-file, zero-behavior
  campsite sweep (S1192 — already over threshold; WP02 would add a 6th copy).
- **M2 (fold-now)** — WP02's new command MUST consume the existing hoisted `_DRY_RUN_FLAG`/`_MISSION_FLAG`/
  `_MISSION_METAVAR`/`_JSON_FLAG` (+ help) constants (`:60-66`) for its option strings, not re-spell
  `"--dry-run"`/`"--json"`/`"--mission"`/`metavar="SLUG"`. Add ONE new command-specific help constant if
  the generic help text doesn't fit. **FREEZE**: do NOT retrofit the existing identity/topology/provenance
  commands onto these constants (separate dedup mission). Match the existing per-command printer style
  (prefix/footer/errors block) — add exactly one command, don't rewrite the three printers.

## Added test coverage (squad #3 anti-laziness — M3/m3)

Add to T006 (red-first):
- `test_needs_manual_only_exits_zero_with_diagnostic` (**M3/FR-007**): a needs_manual-only run exits
  `0` AND prints the actionable diagnostic ("a valid mission type whose governance profile resolves …
  not necessarily a typo").
- **m3**: `test_exit_codes_error_dryrun_clean` must include an `error` mission under `--dry-run` and
  assert exit `0` (dry-run is always 0, even when error>0).
