# WP10 Independent Review — Cycle 1

- **Reviewer:** reviewer-renata (independent; did not implement)
- **Date:** 2026-08-13
- **Governed Op:** invocation `01KZX6F78PHP8TSPMZ2GSFHWK0` (profile reviewer-renata, action audit)
- **Scope:** WP10 "WAL-aware layout migration, quarantine, and atomic cutover" as landed in
  commit `94dff4366d881eddcccdf4f1b97e2fd81863d2ac` on `pr/per-project-sync-consent-progress`:
  `src/specify_cli/sync/project_store_migration.py` (1749 lines),
  `src/specify_cli/sync/daemon_protocol.py`, migration/cutover/history commands in
  `src/specify_cli/cli/commands/sync.py`, plus the owned test suites.
- **Verdict:** **APPROVED** (moved WP10 `for_review → approved`; `--force` was required and used
  only because assignee metadata records the implementing agent `claude`, not the reviewer).

## Gate commands and results

| Gate | Command | Result |
|---|---|---|
| Owned suites | `uv run python -m pytest tests/sync/test_project_store_migration.py tests/sync/test_daemon_cutover_protocol.py tests/sync/test_migration_writer_barrier.py tests/sync/test_queue_row_level_migration.py tests/sync/test_body_queue_migration.py tests/cli/commands/test_sync_project_store_commands.py tests/cli/commands/test_sync_migrate_backfills_h4.py -q --tb=short --timeout=300 -n auto --dist loadfile` | **71 passed** in 11.32s (matches expectation) |
| Lint | `uv run ruff check` on the three owned src files | All checks passed |
| Types | `uv run mypy --strict` on the three owned src files | Success: no issues found in 3 source files |

## Findings by subtask

### T044 — WAL-aware inventory and verification: PASS
`_snapshot_source` copies main/WAL/SHM bytes into a `0700` staging directory with each
destination pre-created `0600` (`_create_private_empty_file`, `O_EXCL`), requires byte-identical
pre/post source fingerprints (`SourceChangedError` otherwise), opens **only the private copy**
(`PRAGMA query_only`, `busy_timeout = 0`), and materializes committed WAL state via the SQLite
backup API into a disposable snapshot. The source is never passed to a connection or
schema-mutating constructor. Inventory uses `PRAGMA table_xinfo` and fails closed on
generated/hidden columns; required-column mismatches fail closed with evidence.
`MigrationManifest` records exact row identities, per-row `logical_sha256`, physical sidecar
fingerprints, and a source digest computed from the **logical** snapshot (schema, tables,
columns, row count, logical sha) — explicitly not inode bytes, so a WAL checkpoint is not a
false "source changed".

### T045 — Copy partition and quarantine: PASS
`CanonicalProjectUUID.parse` canonicalizes once; column/payload identity conflicts quarantine as
`conflicting_project_uuid`. Divergent-duplicate poisoning runs on the raw census **before**
schema/relation filtering, so one malformed divergent copy poisons every same-identity copy;
result rows are reconciled to their exact source-owned attempt (fixed-point pass) so no result
outlives a quarantined attempt. Quarantine uses a closed `QuarantineReason` vocabulary, is
persisted to named `quarantine.json`/manifest artifacts only, and no sender API consumes it.
Migrated rows land in sealed epochs (`state='sealed'`, `legacy_migration:<id>` reason); attempt
epochs are re-created sealed with their original `epoch_id`/`consent_generation` and collide
fail-closed. Consent copy inserts only `migrated_refusal` rows for refusals; old grants create
no grant row (proven by `copy_preserves_project_partition_state_and_never_promotes_grant`), and
the retired `sync migrate --backfill-consent-index` path refuses before any consent access.

### T046 — Atomic cutover through existing authority: PASS
`_cutover` uses WP02's `LayoutGenerationAuthority` exclusively: `begin_cutover` advances to a
migration-owned `CUTOVER_PENDING` generation; `publish_project_only` runs the winning
re-snapshot + copy + exact verification **inside the machine layout lock** and refuses
publication unless `verify_exact()` returns exactly `True`. No WP04 writer was modified; writers
go through `execute_write`, which revalidates the permit under the same lock and redirects a
stale writer exactly once. Both orderings are pinned:
`test_writer_commit_before_quiesce_is_captured_once` (snapshot captures the winning commit once),
`test_writer_redirects_once_when_cutover_wins` and
`test_writer_waiting_post_verify_redirects_once_after_publication` (a live thread blocked on the
lock during publication redirects once into the project store, source untouched), and
`test_commit_immediately_before_cutover_is_in_winning_snapshot`.

### T047 — Recognized-daemon protocol and residue diagnosis: PASS
`DaemonCutoverProtocol` verifies exact loopback URL shape before any I/O, checks
`protocol_version`/`package_version` against the current binary, uses the authenticated shutdown
endpoint, and fails closed on identity drift during the quiesce wait
(`reachable_identity_drift_after_shutdown_request_fails_closed`).
`discover_daemon_cutover_protocol` raises on daemon state that exists but is not a recognized
healthy current binary. Phases `inventoried → quiesced → copied → verified → cutover → restarted
→ complete/failed` are durable and monotonic; `migrate()` resumes idempotently from the
persisted manifest, and PROJECT_ONLY layout forbids a new legacy copy unless the manifest is a
verified resumable one for this migration. Post-cutover legacy writes surface only through
`diagnose_residue` as `post_cutover_residue` records — never copied, never delivered
(`test_post_cutover_old_binary_write_is_residue_not_live_delivery`,
`test_new_migration_identity_cannot_rematerialize_post_cutover_residue`).

### T048 — Commands and hard-kill convergence: PASS
`project-store-preview/-migrate/-status [--diagnose-residue]/-quarantine` and
`project-store-history` are wired; status/quarantine are manifest-only (no source or store
open). The retired shared `sync migrate` refuses with guidance before runtime/consent access.
Hard-kill convergence is proven with **real subprocess kills** (`os._exit(73)`) after each of
the six durable phases, each rerun converging to exactly one copied row
(`test_hard_kill_after_each_phase_resumes_to_one_exact_copy`); raw-staging residue from a kill
is private and cleaned on resume. The history-disclosure flow previews the exact sealed cohort
(row ids, epoch ids, hash), requires explicit `--confirm-by` + `--idempotency-key` (mutually
exclusive with `--apply`), consumes a persisted capability under the current target/admission
context, and hands the exact cohort to WP07's `run_import_upload` with that capability; preview
never confirms and migration never manufactures consent
(`history_preview_never_confirms_or_manufactures_legacy_grant`,
`history_confirmation_then_apply_uses_exact_wp07_capability_transport`).

## Adversarial checks performed
- Searched for fail-open paths: `_cutover` returning early on `PROJECT_ONLY` is guarded upstream
  in `migrate()` by the owned-manifest resumability check — not fail-open.
- Verification failure evidence is hash-only (`_safe_failure`, `_safe_evidence`); no raw row
  values persist in manifests or failure records.
- Quarantine/residue records have no consumer in any delivery/sender path (census tests pin the
  exact three snapshot connections, one loopback sink, eight staged-copy INSERT sites).
- Cross-project isolation: partitions copy into per-project stores only;
  `rerun_is_idempotent_and_cross_project_stores_are_disjoint` passes.

## Non-blocking observations
1. `test_hard_kill_after_each_phase_resumes_to_one_exact_copy` sets
   `os.environ["SPEC_KITTY_HOME"]` directly (no monkeypatch restore); `--dist loadfile` and the
   per-worker HOME isolation contain it today, but it is a latent cross-test leak within the
   file's worker.
2. `DaemonCutoverProtocol.restart()` without an injected restart seam returns a synthetic
   acknowledgement with `daemon_protocol=0`. Unreachable via `discover_daemon_cutover_protocol`
   (which always injects the seam), but a direct construction could record a hollow "restarted"
   phase.
3. Non-UTF8 legacy payload bytes are wrapped as `{"legacy_bytes": ...}` JSON during copy; the
   inventory identity hash still covers the original bytes and copy/verify use the same
   transform, so exactness holds, but the destination payload is a re-encoding, not the raw
   bytes.

None of these weakens a Definition-of-Done invariant; all six DoD bullets are satisfied.
