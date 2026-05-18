## Resolution: PR #1107

This issue is fixed by PR #1107 (mission `mvp-cli-sync-boundary-completion-01KRX11M`).

### What changed (this issue's scope)

- A reusable `SyncBoundaryPreflight` helper (`run_preflight`) now composes the four boundary checks — `check_daemon_owner_match()`, `is_orphan()` / `list_orphan_records()`, foreground-vs-daemon field comparison, and `detect_legacy_rows_for_scope()` — into a single callable preflight (FR-001).
- The preflight names every mismatched field by its canonical identifier (`daemon_package_version`, `daemon_executable_path`, `daemon_source_path`, `daemon_server_url`, `daemon_team_or_user`, `daemon_queue_db_path`, plus `orphan_daemon_record` and `legacy_queue_rows`) so the operator can fix the right side of the drift without consulting docs (FR-003, NFR-004).
- Orphan-daemon detection never calls `os.kill` on operator processes. It relies on `psutil` liveness checks in `list_orphan_records()`. The architectural test `test_orphan_detection_without_os_kill` asserts this invariant on every CI run.
- The preflight is read-only and local-scope. WP01 fix commits ensure the preflight does not trigger migration (`5516e5d8`) and does not perform any SaaS round-trip during scope resolution (`bcda08ef`); it only inspects on-disk daemon owner records and queue scope.

### Verification

```
$ uv run --with pytest python -m pytest \
    tests/sync/test_daemon_owner_record.py \
    tests/sync/test_sync_boundary_preflight.py -q
............................                                              [54%]
........................                                                  [100%]
52 passed in 1.27s
```

Full transcripts: `kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/evidence/test-transcripts/targeted.txt` (the targeted run combines these two test modules with three others).

Live verification on this machine — `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty sync status --check` — printed the six canonical daemon fields under "Daemon owner record" (Status / PID / Port / Package version / Executable path / Source path / Server URL / Team/User / Queue DB path) and reported `Orphan records 0` plus `Mismatched fields none` against the active daemon. Transcript: `evidence/test-transcripts/sync-status-check-coherent.txt`. Singleton check independently surfaced 27 stale `run_sync_daemon` processes from other workspaces, demonstrating the `#1071` orphan-process scan path is wired into the same render.

### Code references

- `src/specify_cli/sync/preflight.py:439` — `collect_foreground_identity()` reads the foreground process identity used for comparison.
- `src/specify_cli/sync/preflight.py:542` — `_build_mismatches()` produces canonical field-name list for every mismatch shape.
- `src/specify_cli/sync/preflight.py:590` — `_count_legacy_rows_for_scope()` counts the legacy rows attributable to the current scope.
- `src/specify_cli/sync/preflight.py:708` — `build_boundary_failure_set()` is the canonical builder consumed by both `sync status --check` and `run_preflight`. Single source of truth.
- `src/specify_cli/sync/preflight.py:763` — `run_preflight()` — the reusable helper. Callers: `sync now` (`cli/commands/sync.py:1204`) and `setup-plan` (`cli/commands/agent/mission.py:1017`).

### Implementing commits

- `cab90672` — feat(WP01): Sync boundary preflight module
- `5516e5d8` — fix(WP01): preflight is read-only; do not trigger migration during identity collection
- `bcda08ef` — fix(WP01): preflight uses local-only scope resolution; no SaaS round-trip
- `4a3b3b27` — feat(WP03): single-source boundary failure builder; sync-now preflight; full status fields + --json

Closing per the mission's Definition of Done.
