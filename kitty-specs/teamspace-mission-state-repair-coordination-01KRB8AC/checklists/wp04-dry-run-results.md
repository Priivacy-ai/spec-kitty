# WP04: Post-Repair Dry-Run Validation Results

## Audit Gate Results (Contract 3)

| Repo | missions_with_teamspace_blockers | teamspace_blockers | missions_with_errors | Gate |
|------|----------------------------------|-------------------|---------------------|------|
| spec-kitty-saas | 0 | 0 | 0 | PASS |
| spec-kitty-events | 0 | 0 | 0 | PASS |
| spec-kitty-runtime | 0 | 0 | 0 | PASS |

**Contract 3 gate: PASSED** — zero TeamSpace blockers across all repos.

Note: spec-kitty-saas initially showed 3 SNAPSHOT_DRIFT errors post-repair (status.json key ordering
mismatch introduced by upgrade migration). Fixed by regenerating status.json in canonical reducer key order
for missions 003, 016, 017. After fix: 0 errors.

## Dry-Run Results (Contract 4)

| Repo | valid | envelope_count | errors | side_logs | Side Log Disposition |
|------|-------|----------------|--------|-----------|---------------------|
| spec-kitty-saas | false | 1853 | 41 PAYLOAD_INVALID | 4 skipped | skipped_local_side_log |
| spec-kitty-events | false | 337 | 5 PAYLOAD_INVALID | 1 skipped | skipped_local_side_log |
| spec-kitty-runtime | true | 79 | 0 | 0 | n/a |

## Pre-Existing PAYLOAD_INVALID Errors

The 41 (saas) and 5 (events) `PAYLOAD_INVALID` dry-run errors are **pre-existing data quality issues
unrelated to the LEGACY_KEY repair**. They occur because certain status transitions to `approved`/`done`
lanes are missing required `evidence` fields per spec-kitty-events==5.0.0 schema. These require a
separate evidence-backfill operation, not the `--fix` repair command (which only targets LEGACY_KEY shapes).

Affected missions (saas): 001-saas-dashboard-views, 002-event-driven-materialization,
004-github-connector-webhook-ingestion, 009-cli-authentication-and-event-sync-integration,
010-mission-collaboration-session-service-soft-coordination, 014-glossary-semantic-integrity-dashboard

Affected missions (events): 005-event-contract-conformance-suite

**These errors are NOT caused by our repair and were present before the repair sequence.**

## T016: Side Logs Skipped vs Transitions (Contract 4)

All side logs are correctly classified as `skipped_local_side_log` / `out_of_scope_for_launch_import`.
None appear as status transitions in the `row_mappings` or `envelope_count`.

| Repo | Side Logs | Disposition | PR #19 Active? |
|------|-----------|-------------|----------------|
| spec-kitty-saas | 4 files | skipped_local_side_log | yes |
| spec-kitty-events | 1 file | skipped_local_side_log | yes |
| spec-kitty-runtime | 0 files | n/a | yes (0 side logs, 79 row_mappings) |

spec-kitty-runtime: PR #19 (`feat: classify runtime logs for TeamSpace migration`) is confirmed active.
Zero side logs in dry-run output — runtime events are fully synthesizable without any side-log skips.

## Schema Note

The actual dry-run JSON schema (schema_version: 3.0.0) uses:
- `errors` (not `envelope_validation_errors`)
- `side_logs` (array, not `side_logs_skipped` scalar)
- `envelope_count` (not `envelopes_synthesized`)
- `valid` (boolean, overall pass/fail)

The contract field names are logical aliases for equivalent data.

## FINAL GATE

- **Contract 3 (audit): PASSED** — zero TeamSpace blockers in all repos ✓
- **Contract 4 (dry-run): PARTIAL** — runtime passes clean; saas/events have pre-existing PAYLOAD_INVALID errors (separate issue, not in repair scope)
