## Summary

Mission `mvp-sync-boundary-cli-01KRVCQS` — bundles the four CLI-side fixes from the MVP launch blocker (planning#17):

- **#1090** Row-level legacy→scoped queue migration (removes whole-DB emptiness guard; adds `detect_legacy_rows_for_scope` helper).
- **#1088** Daemon owner record + ownership semantics (new `src/specify_cli/sync/owner.py` with `DaemonOwnerRecord` dataclass + atomic write + mismatch/orphan helpers; daemon writes record on start, exposes redacted via health endpoint).
- **#1087** `sync status` and `doctor` truthfulness (surfaces FR-008 fields; `--check` returns non-zero on D-3 mismatch / legacy backlog / orphan daemon; FR-013 stranded-mission tag; doctor orphan-daemons subcommand).
- **#1089** Setup-plan SaaS-evidence guarantee (refuses loudly when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and unauthenticated; FR-012 audit block).

## Mission artifacts

Planning + WP prompts are in `kitty-specs/mvp-sync-boundary-cli-01KRVCQS/` (committed earlier to `main`). This PR delivers the merged code on top of that.

## Work packages

- **WP01** Row-level migration: `src/specify_cli/sync/queue.py` + 6 new tests in `tests/sync/test_queue_row_level_migration.py`. Key implementation note: excludes synthetic `id` AUTOINCREMENT column from migration so INSERT OR IGNORE doesn't silently drop rows on PK collision.
- **WP02** Daemon owner record: new `src/specify_cli/sync/owner.py` (370 lines) + `src/specify_cli/sync/daemon.py` wiring + 26 tests in `tests/sync/test_daemon_owner_record.py`. Atomic write via `tempfile.mkstemp` + `os.replace`. C-002 guard test asserts orphan detection never calls `os.kill` on operator processes.
- **WP03** Status + doctor truthfulness: extended `src/specify_cli/cli/commands/sync.py` + `doctor.py` + 5 tests in `tests/sync/test_sync_status_boundary_check.py`. `--check` returns non-zero on D-3 mismatch / legacy backlog / orphan daemon.
- **WP04** Setup-plan refuse-loudly: `src/specify_cli/cli/commands/agent/mission.py` + 5 tests in `tests/runtime/test_setup_plan_sync_evidence.py` (includes AST regression: no `_legacy_queue_db_path` calls in setup-plan code path).

## Verification

- `uv run pytest tests/sync tests/status tests/runtime`: **2470 passed, 9 skipped, 1 pre-existing failure** (`test_doctor_healthy` — environment-dependent; host has live orphan daemons unrelated to this mission; reproduces on baseline commit).
- `uv run mypy --strict src/specify_cli/sync/`: clean.
- `uv run mypy --strict src/specify_cli/cli/commands/agent/`: 4 pre-existing errors carved out (same set on baseline; zero regressions introduced).
- All four WPs reviewed by `reviewer-renata` and approved one cycle each (no rejections).

## Post-merge mission review

`kitty-specs/mvp-sync-boundary-cli-01KRVCQS/MISSION-REVIEW.md` documents the post-merge audit: **PASS WITH NOTES**. One MEDIUM follow-up: `check_daemon_owner_match()` is not yet wired into per-sync-action gates (FR-007 currently only fires via `sync status --check`, not at action precondition). Tracked as a follow-up issue, not blocking this PR.

## Test plan
- [ ] CI green.
- [ ] Spot-check `_migrate_legacy_queue_to_scope` is row-level (no whole-DB emptiness guard).
- [ ] Spot-check daemon `owner.json` write is atomic (tempfile + os.replace).
- [ ] `sync status --check` returns non-zero on a faked D-3 mismatch.
- [ ] `setup-plan` exits non-zero with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and no auth.

Depends on:
- `spec-kitty-events#29` (`WPStatusChanged` backward-transition contract) — already merged.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
