<!--
Operator: apply this body to PR #1107 with:

    gh pr edit 1107 --repo Priivacy-ai/spec-kitty --body-file kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/pr-1107-body-update.md

This file is the canonical replacement for the current PR description. It removes
the stale "post-merge follow-up" line about `check_daemon_owner_match()` not being
wired into per-action gates — that follow-up is now shipped in this PR via the
WP01–WP04 boundary-preflight chain.
-->

## Summary

Mission `mvp-sync-boundary-cli-01KRVCQS` + closure mission `mvp-cli-sync-boundary-completion-01KRX11M` — together they deliver the four CLI-side fixes from the MVP launch blocker (planning#17) and close the daemon-owner-coherence gap:

- **#1090** Row-level legacy→scoped queue migration covering `body_upload_queue` rows with `INSERT OR IGNORE` idempotence and durable destination-first commit order.
- **#1088** Daemon owner record + ownership semantics. New `src/specify_cli/sync/owner.py` (`DaemonOwnerRecord` dataclass + atomic write + mismatch/orphan helpers). Daemon writes the record on start and exposes a redacted view via the health endpoint.
- **#1087** `sync status` and `doctor` truthfulness. `--check` exits non-zero on every documented split-brain shape including auth-absent; new `--json` mode emits a machine-consumable object matching `contracts/sync-status-output.md`.
- **#1089** Setup-plan SaaS-evidence guarantee. `setup-plan` refuses loudly when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and no authenticated identity is available, and now routes through the reusable boundary preflight after auth preflight so no SaaS-producing path can write to a wrong-scope queue.

## Boundary preflight (shipped in this PR)

The closure mission (`mvp-cli-sync-boundary-completion-01KRX11M`) closes the gap that the original mission's review identified as a "medium follow-up": `check_daemon_owner_match()` is now wired into every SaaS-producing CLI path. Specifically:

- **WP01** — Reusable `SyncBoundaryPreflight` helper composing `check_daemon_owner_match()`, `is_orphan()` / `list_orphan_records()`, foreground-vs-daemon field comparison, and `detect_legacy_rows_for_scope()`. Read-only and local-scope by construction (no SaaS round-trip in the gate). Module: `src/specify_cli/sync/preflight.py`.
- **WP02** — Row-level migration covers `body_upload_queue` with `INSERT OR IGNORE` keyed on schema-correct composite tuples, is idempotent on re-run, and commits to the destination DB before deleting from the legacy source so a power-cut mid-migration cannot lose rows.
- **WP03** — `sync status --check` and `sync now` route through a single shared failure-set builder (`build_boundary_failure_set` in `src/specify_cli/sync/preflight.py`). Full FR-005 printed-field coverage (active + legacy queue counts, all daemon canonical fields, mismatch list, orphan count). `--check --json` emits a machine-consumable JSON object. Auth-required exits with code 2 (the previous gap where auth-absent silently exited 0 is fixed).
- **WP04** — `setup-plan` invokes `run_preflight(...)` after the existing auth preflight and before any enqueue / SaaS event emission / body upload. FR-008 ordering is preserved; FR-009 (no silent legacy-queue writes) is now structurally gated.

## Mission artifacts

- Original planning: `kitty-specs/mvp-sync-boundary-cli-01KRVCQS/`
- Closure planning: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/`
- Operator runbook: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/quickstart.md`
- Sub-issue close comments (paste at close time): `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/close-{1090,1088,1087,1089}.md`

## Work packages (closure mission)

- **WP01** Sync boundary preflight module: new `src/specify_cli/sync/preflight.py` (805 lines) + 24 tests in `tests/sync/test_sync_boundary_preflight.py`. Two follow-up fixes: preflight is read-only (does not trigger migration during identity collection) and local-scope (no SaaS round-trip).
- **WP02** Row-level migration extension: `src/specify_cli/sync/queue.py` body-upload-queue coverage + 11 tests in `tests/sync/test_queue_row_level_migration.py`. Includes the destination-first commit-order fix.
- **WP03** Status/check single-source: `src/specify_cli/cli/commands/sync.py` extended to use `build_boundary_failure_set`; adds `--json`; 19 tests in `tests/sync/test_sync_status_boundary_check.py`. Auth-required exit code fix plus render compression to ≤ 25 visible lines per NFR-004.
- **WP04** Setup-plan preflight integration: `src/specify_cli/cli/commands/agent/mission.py:1015-1017` wires `run_preflight` into `setup-plan`; 10 tests in `tests/runtime/test_setup_plan_sync_evidence.py`, including the AST-level regression that asserts no `_legacy_queue_db_path()` call exists in the `setup-plan` code path.
- **WP05** Mission closure (this artifact set): verification transcripts, sub-issue close-comment drafts, this PR body update, Definition-of-Done checklist.

## Verification

- Targeted suites (mission-touched test modules): **92 passed**.
  - `uv run pytest tests/sync/test_queue_row_level_migration.py tests/sync/test_daemon_owner_record.py tests/sync/test_sync_status_boundary_check.py tests/sync/test_sync_boundary_preflight.py tests/runtime/test_setup_plan_sync_evidence.py -q`
  - Transcript: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/targeted.txt`
- Broad suites (`tests/sync tests/status tests/runtime`): **2454 passed, 8 skipped**, plus 24 pre-existing failures and 3 collection errors that reproduce on the pre-mission base commit and have **no overlap with files touched by this mission**. Detailed inventory in the transcript footer.
  - Transcript: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/broad.txt`
- `uv run mypy --strict src/specify_cli/sync/`: 11 errors, all pre-existing baseline drift (missing third-party stubs for `toml` / `requests` / `psutil`, and `Any`-return drift in modules outside this mission's diff — `namespace.py`, `_team.py`, `config.py`, `events.py`). No new errors introduced by WP01–WP04.
  - Transcript: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/mypy-strict.txt`
- Live `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty sync status --check`: exits 2 on this machine with auth absent and 4151 legacy rows present, printing the full FR-005 block. `--check --json` returns a single JSON object with `exit_code=2` and the matching field set.
  - Transcripts: `evidence/test-transcripts/sync-status-check-coherent.txt`, `evidence/test-transcripts/sync-status-check-json.txt`

## Test plan

- [ ] CI green on the PR branch (`kitty/pr/mvp-sync-boundary-cli-01KRVCQS`).
- [ ] Spot-check `_migrate_table_row_level()` in `src/specify_cli/sync/queue.py` is row-level (no whole-DB emptiness guard) and includes `body_upload_queue` in `_QUEUE_TABLES_FOR_MIGRATION`.
- [ ] Spot-check daemon `owner.json` write is atomic (tempfile + `os.replace`).
- [ ] `sync status --check` returns non-zero on a faked D-3 mismatch AND when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set without auth.
- [ ] `setup-plan` exits non-zero with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and no auth (FR-008) AND no `_legacy_queue_db_path()` call exists in the `setup-plan` code path (FR-009, AST regression test).
- [ ] `sync now` refuses on any boundary failure that `sync status --check` reports (single failure-set builder, no divergence by construction).

Depends on:
- `spec-kitty-events#29` (`WPStatusChanged` backward-transition contract) — already merged.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
