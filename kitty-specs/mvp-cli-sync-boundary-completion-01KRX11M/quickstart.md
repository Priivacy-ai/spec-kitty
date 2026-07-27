# Quickstart: MVP CLI Sync Boundary Completion

**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`
**Branch**: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (PR #1107)

This quickstart is for the operator finishing PR #1107. It captures the exact commands to verify the mission's deliverables and to compose evidence comments for the four sub-issues at close time.

## Prerequisites

- Repository checkout at the operator's spec-kitty path. On POSIX hosts this is usually under `/Users/...` or `/home/...`; on Windows 10+ it is typically under `C:\Users\...`.
- Current branch is `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`.
- `uv` and Python 3.11+ are installed and `uv sync` has been run on the branch HEAD.
- For any hosted-auth or sync command, `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set:
  - POSIX: `export SPEC_KITTY_ENABLE_SAAS_SYNC=1`
  - Windows `cmd.exe`: `set SPEC_KITTY_ENABLE_SAAS_SYNC=1`
  - Windows PowerShell: `$env:SPEC_KITTY_ENABLE_SAAS_SYNC = "1"`

All commands below are shown in POSIX form. On Windows, substitute the env-var syntax above and use `\` paths if you copy snippets into a native shell (paths inside spec-kitty are `pathlib.Path` and handle separators automatically).

## 1. Targeted unit + integration tests

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-082805-q0Lu7J/spec-kitty
uv run pytest \
  tests/sync/test_queue_row_level_migration.py \
  tests/sync/test_daemon_owner_record.py \
  tests/sync/test_sync_status_boundary_check.py \
  tests/sync/test_sync_boundary_preflight.py \
  tests/runtime/test_setup_plan_sync_evidence.py \
  -q
```

Expected: all pass.

## 2. Broader regression suites

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-082805-q0Lu7J/spec-kitty
uv run pytest tests/sync tests/status tests/runtime -q
```

Expected: all pass; no new failures or warnings vs. branch baseline.

## 3. Strict type check

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-082805-q0Lu7J/spec-kitty
uv run mypy --strict src/specify_cli/sync/
```

Expected: exit 0 with no errors.

## 4. Live coherence check (requires hosted auth)

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check
```

Expected on a coherent host: exit 0; identity-boundary block prints all documented fields with no mismatches and zero orphans.

Expected on a split-brain host: exit 2; mismatch list names the failing canonical field(s) and points to the appropriate remediation command.

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check --json | jq .
```

Expected: a single JSON object matching `contracts/sync-status-output.md`.

## 5. Sub-issue evidence templates

Use these templates for the close comments on each sub-issue. Run the command, capture the output, and paste it under the template header.

### Issue #1090 — Row-level legacy → scoped queue migration

```
$ uv run pytest tests/sync/test_queue_row_level_migration.py -q
```

Required cases passing:
- empty scoped DB migration (`tests/sync/test_queue_row_level_migration.py:190`)
- non-empty scoped DB merge (`:231`)
- legacy row detection (`:320`)
- new: body-upload row migration with non-empty scoped DB
- new: re-run idempotence (`INSERT OR IGNORE`)

### Issue #1088 — Daemon owner coherence

```
$ uv run pytest tests/sync/test_daemon_owner_record.py tests/sync/test_sync_boundary_preflight.py -q
```

Required cases passing:
- health endpoint redacts owner (`tests/sync/test_daemon_owner_record.py:167`)
- owner-match green path (`:264`)
- orphan detection without `os.kill` (`:336`)
- new: preflight refuses on each of six canonical mismatch fields
- new: preflight refuses on orphan record

### Issue #1087 — Truthful `sync status --check` / `sync doctor`

```
$ SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check
$ uv run pytest tests/sync/test_sync_status_boundary_check.py -q
```

Required cases passing:
- coherent status exits 0 (`tests/sync/test_sync_status_boundary_check.py:193`)
- orphan daemon record makes `--check` fail (`:269`)
- new: every canonical mismatch field independently fails `--check`
- new: legacy rows in scope fail `--check`

### Issue #1089 — `setup-plan` SaaS evidence / refuse-loudly guarantee

```
$ uv run pytest tests/runtime/test_setup_plan_sync_evidence.py -q
```

Required cases passing:
- authenticated `setup-plan` writes scoped queue (`tests/runtime/test_setup_plan_sync_evidence.py:116`)
- unauthenticated `setup-plan` refuses (`:296`)
- no `_legacy_queue_db_path()` in `setup-plan` path (`:369`)
- new: `setup-plan` invokes boundary preflight after auth preflight

## 6. Pre-merge checklist for PR #1107

Before requesting merge:

- [ ] All commands above exit 0 (where applicable).
- [ ] `spec-kitty agent decision verify --mission mvp-cli-sync-boundary-completion-01KRX11M` is clean.
- [ ] PR #1107 description has had the "post-merge follow-up" line for daemon-owner gating removed (or rephrased to "shipped in this PR").
- [ ] Each of #1090, #1088, #1087, #1089 has a draft close comment composed from §5 above, ready for the operator to post once the PR merges.

## Operator FAQ

**Q. Daemon refuses with `daemon_package_version` mismatch right after I upgrade locally.**
A. Restart the daemon at the new version: `spec-kitty doctor restart-daemon`. The refusal is correct: foreground at `vN+1` against a daemon at `vN` is a split-brain shape.

**Q. The legacy queue contains rows for a different scope.**
A. They are not counted against the current scope; `legacy_rows_for_scope` filters by `(server_url, team_or_user)`. Use `sync status --check --json` to see both subtotals.

**Q. I have an orphan record but no obvious cleanup command.**
A. Run `spec-kitty doctor orphan-daemons`. It uses `list_orphan_records()` and never calls `os.kill`.

**Q. Can I bypass the preflight in CI?**
A. No. The preflight is the MVP boundary; bypassing it defeats the mission. CI should run on a coherent host (matching daemon and foreground versions, or no daemon at all).
