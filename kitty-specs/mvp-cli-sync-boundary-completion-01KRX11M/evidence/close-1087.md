## Resolution: PR #1107

This issue is fixed by PR #1107 (mission `mvp-cli-sync-boundary-completion-01KRX11M`).

### What changed (this issue's scope)

- `sync status --check` now exits non-zero (exit code 2) in **every** documented split-brain shape (FR-004): daemon vs foreground version drift, executable drift, source-path drift, server-URL drift, team/user drift, queue-DB-path drift, orphan daemon owner record, AND when hosted SaaS sync is enabled but no authenticated identity is available (auth-required). The auth-required case is the fix in `c9c9bfdf` — previously it silently exited 0.
- `--check` and `sync now` route through a single shared failure-set builder (`build_boundary_failure_set` in `src/specify_cli/sync/preflight.py:708`). Whatever `--check` reports, `sync now` refuses on. No divergence is possible by construction.
- Every invocation prints the full FR-005 field block: active queue DB path + event/body counts, legacy queue DB path + event/body counts + rows in scope, all six daemon canonical fields (PID, port, package_version, executable_path, source_path, server_url, team_or_user, queue_db_path), mismatched-fields list (possibly empty), and orphan-record count. Render compressed to ≤ 25 visible lines per NFR-004.
- New `--json` flag emits a single machine-consumable JSON object on stdout with the same field set. Shape matches `contracts/sync-status-output.md`. Useful for canary / CI assertion paths.

### Verification

```
$ uv run --with pytest python -m pytest tests/sync/test_sync_status_boundary_check.py -q
...................                                                       [100%]
19 passed in 0.55s
```

Live invocation on this machine (worktree branch HEAD = `5a698312`):

```
$ SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check
# ... full identity-boundary block printed ...
Identity boundary check FAILED:
  ! legacy queue DB /Users/robert/.spec-kitty/queue.db has 4151 row(s) pending migration (queue=2869, body_upload_queue=1282)
  ! Hosted SaaS sync is enabled but no authenticated identity is available — run `spec-kitty auth login`.

EXIT=2
```

`--check --json` mode on the same host:

```
$ SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check --json
{"ok": false, "exit_code": 2, "auth_required": true, "auth_present": false,
 "foreground": {"package_version": "3.2.0rc11", "executable_path": "...", "source_path": "...",
                "server_url": null, "team_or_user": null, "queue_db_path": "/Users/robert/.spec-kitty/queue.db",
                "pid": 19509},
 "daemon_owner_record": {"status": "absent", "pid": null, "port": null, "package_version": null,
                         "executable_path": null, "source_path": null, "server_url": null,
                         "team_or_user": null, "queue_db_path": null},
 "active_queue": {"path": "/Users/robert/.spec-kitty/queue.db", "event_count": 2869, "body_upload_count": 1282},
 "legacy_queue": {"path": "/Users/robert/.spec-kitty/queue.db", "event_count": 2869, "body_upload_count": 1282, "rows_in_scope": 4151},
 "mismatches": [], "orphan_records": []}
EXIT=2
```

This proves all FR-005 fields are present in the JSON output and that `exit_code` matches the process exit (2). Full transcripts:

- `evidence/test-transcripts/sync-status-check-coherent.txt`
- `evidence/test-transcripts/sync-status-check-json.txt`
- `evidence/test-transcripts/targeted.txt`

### Code references

- `src/specify_cli/cli/commands/sync.py:1307` — `_render_boundary_check_failures()` builds operator-readable failure lines from the shared failure set.
- `src/specify_cli/cli/commands/sync.py:1481` — body-upload count emission for the active and legacy queue blocks.
- `src/specify_cli/cli/commands/sync.py:1569` — `--check` option declaration on `sync status`.
- `src/specify_cli/cli/commands/sync.py:1580-1582` — `--json` option declaration; emit a single JSON object on stdout when combined with `--check`.
- `src/specify_cli/sync/preflight.py:282` — `BoundaryFailureSet.to_dict()` is the JSON serializer.
- `src/specify_cli/sync/preflight.py:708` — `build_boundary_failure_set()` is the single source of truth used by `--check` and `run_preflight`.

### Implementing commits

- `4a3b3b27` — feat(WP03): single-source boundary failure builder; sync-now preflight; full status fields + --json
- `c9c9bfdf` — fix(WP03): auth-required exit code on sync status --check; compress render to <=25 lines

Closing per the mission's Definition of Done.
