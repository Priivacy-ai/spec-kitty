# Implementation Plan: MVP Sync Boundary — CLI

**Branch**: `main` (planning + merge target)
**Date**: 2026-05-17
**Spec**: [spec.md](./spec.md)

## Summary

Fix four CLI-side breaks in the auth/queue/daemon/setup-plan identity boundary. Land four scope-bounded WPs (one per issue) plus shared status diagnostics. No SaaS or events repo changes (those are separate missions); all interaction with the canonical `WPStatusChanged` contract is consumption-only.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty CLI codebase; `requires-python = ">=3.11"` in pyproject.toml).
**Primary Dependencies**: typer, rich, ruamel.yaml, httpx, pyyaml, readchar (existing). New: none.
**Storage**: SQLite for `OfflineQueue`/`body_upload_queue` (existing); JSON for daemon owner record (new file, no DB schema).
**Testing**: `pytest` with tmp HOME isolation; `mypy --strict` on touched packages.
**Target Platform**: macOS + Linux developer workstations.
**Project Type**: Single Python package (`src/specify_cli/`).
**Performance Goals**: Queue migration must complete in < 1 s for typical legacy DBs (≤10k rows).
**Constraints**: No new top-level deps; no live `~/.spec-kitty` mutation in tests; no event-contract changes.
**Scale/Scope**: Tens of WPs per mission, hundreds of body uploads per mission, dozens of missions per project.

## Charter Check

Skipped — no `.kittify/charter/charter.md` present at this repo root describing extra gates. CLAUDE.md guidance on testing, status model patterns, and merge preflight is followed.

## Phase 0 outputs (research, embedded inline)

1. **Queue migration shape**: row-level merge by `event_id` for `queue` table; `(table, upload_id)` (or composite of the table's natural keys) for body upload tables. Use `INSERT OR IGNORE` semantics so duplicates are skipped atomically. Delete from legacy in a second pass per row to preserve crash-safety.
2. **Daemon owner record location**: `<sync_root>/daemon/owner.json` (next to existing `daemon.lock`). Atomic write via `os.replace()` after `tempfile.NamedTemporaryFile(delete=False)`. No new dependency.
3. **Foreground/daemon mismatch detection**: foreground reads `daemon/owner.json` (or queries daemon health endpoint per FR-006), compares fields, and refuses on D-3 mismatches. Detection logic lives in a new `src/specify_cli/sync/owner.py` module with pure functions.
4. **Status augmentation**: extend the existing `sync status` command (search `src/specify_cli/cli/commands/sync/`) with a coherence-check function. `--check` returns non-zero on incoherence and prints the specific failing field(s).
5. **Setup-plan re-route**: identify every body-upload call in the agent mission setup-plan code path and confirm they all go through `default_queue_db_path()`. Add a regression test that asserts no setup-plan code path calls `_legacy_queue_db_path()` directly.

## Phase 1 outputs (design)

- [data-model.md](./data-model.md) — DaemonOwnerRecord shape and migration row-key strategy.
- No new contracts/ directory (this mission consumes the existing events contract).
- No new quickstart (uses existing developer workflow).

## Project Structure

```
kitty-specs/mvp-sync-boundary-cli-01KRVCQS/
├── plan.md
├── spec.md
├── data-model.md
├── tasks.md
└── tasks/
    ├── WP01-row-level-queue-migration.md
    ├── WP02-daemon-owner-record.md
    ├── WP03-sync-status-doctor-truth.md
    └── WP04-setup-plan-sync-evidence.md

src/specify_cli/
├── sync/
│   ├── queue.py                 (CHANGED: rewrite _migrate_legacy_queue_to_scope)
│   ├── daemon.py                (CHANGED: write owner record on start, retire stale)
│   └── owner.py                 (NEW: DaemonOwnerRecord I/O + comparison helpers)
├── cli/commands/sync/           (CHANGED: status surfaces new boundary fields; --check returns non-zero on incoherence)
└── cli/commands/agent/          (CHANGED: setup-plan refuses unauth+SAAS sync; all body uploads route through default_queue_db_path)

tests/
├── sync/
│   ├── test_queue_row_level_migration.py     (NEW)
│   ├── test_daemon_owner_record.py            (NEW)
│   └── test_sync_status_boundary_check.py     (NEW)
└── runtime/
    └── test_setup_plan_sync_evidence.py       (NEW)
```

## Branch contract (restated)

- Current branch: `main`
- Planning / base branch: `main`
- Merge target: `main`
- `branch_matches_target`: true.

## Complexity Tracking

No charter violations.

## Next step

`/spec-kitty.tasks --mission mvp-sync-boundary-cli-01KRVCQS`
