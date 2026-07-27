# Contract: event sync journal, target authority, and delivery

**Mission**: `event-sync-retention-delivery-01KVYWRG`
**Scope**: CLI-side event capture, migration, dispatch, receiver integration, and status surfaces for #2124/#2146.

This contract is the task-generation boundary. Work packages may split it, but they must not weaken these observable behaviors.

## 1. Target Authority

Runtime hosted/sync commands resolve one `ResolvedSyncTarget` before selecting a queue/journal, opening a network connection, or printing status.

Required fields:

| Field | Meaning |
|---|---|
| `configured_server_url` | URL read from `~/.spec-kitty/config.toml` `[sync].server_url`, if present |
| `env_server_url` | `SPEC_KITTY_SAAS_URL`, if set |
| `override_mode` | `none`, `setup_only`, or `process_override` |
| `resolved_server_url` | URL used by auth/readiness/WebSocket/tracker/sync network calls |
| `user_id` / `team_slug` | authenticated identity when known |
| `derived_queue_scope` | deterministic isolation key derived from resolved URL + identity |
| `queue_db_path` | scoped queue path derived from `derived_queue_scope` |
| `active_queue_scope_status` | `absent`, `matches`, or `stale_non_authoritative` |

Rules:

- `active_queue_scope` is never an input selector. It is absent, recomputed cache, or stale diagnostic state.
- If `SPEC_KITTY_SAAS_URL` disagrees with `config.toml`, hosted commands either use an explicit whole-process override everywhere or fail/warn before network calls.
- Queue scope, ledger target identity, auth/readiness, WebSocket, tracker, and batch posts use the same resolved URL.

Required tests:

- Env/config disagreement cannot derive queue scope for one target while posting to another.
- Stale `active_queue_scope` is reported and ignored as authority.
- `sync status --check --json` exposes target-authority fields.

## 2. Capture Before Drain Gates

For Teamspace-bound event families, local durability happens before drain eligibility checks.

Rules:

- `SPEC_KITTY_ENABLE_SAAS_SYNC=0`, missing auth, missing team, Private-Teamspace gate failure, daemon lock failure, and network failure do not mean "do not write".
- The event is written to `event_journal` or an approved git source before those gates decide whether delivery can proceed.
- A blocked drain records `drain_blocked_reason`/audit state that status can show and later delivery can clear.
- `OPT_OUT`/`TRASH` can discard only local-only or explicitly discardable families. Teamspace-bound discard must be refused or audit-recorded through a registered durable source.

Required tests:

- Disabled sync + event production leaves Teamspace-bound events locally durable.
- Missing auth/team leaves events locally durable with blocked-drain diagnostics.
- Opt-out of a Teamspace-bound family does not silently drop the fact.

## 3. Journal And Ledger

Rules:

- `event_journal` stores payload bytes by `event_id` and never deletes them during normal `sync now`.
- Successful delivery and duplicate delivery update `delivery_ledger`; they do not delete journal rows.
- Terminal-failed outcomes write a terminal-failed ledger state, are excluded from future automatic selection, stay inspectable, and require explicit operator action to retry.
- Coalescing may mutate only events that have no terminal delivery to any target. Once delivered anywhere, payload bytes are immutable.
- `sync gc`/`sync archive` are the only destructive payload operations and preserve delivery history/provenance.

Required tests:

- Sync to target A, switch to target B, and deliver the same retained events.
- Re-sync to target A skips already-successful rows.
- Coalescing against a delivered event leaves original bytes unchanged.
- Oversized/permanent failure progresses the drain and remains inspectable.

## 4. DeliveryReceiver

Every delivery target type implements one `DeliveryReceiver` contract consumed by the dispatcher.

Required interface semantics:

| Aspect | Teamspace | External receiver | Stub receiver |
|---|---|---|---|
| Endpoint | `{resolved_server_url}/api/v1/events/batch/` | operator URL | localhost/in-process URL |
| Auth | Bearer token | operator-supplied or none | none |
| Gates | SaaS enabled + Private Teamspace + auth | endpoint configured | none |
| Results | success, duplicate, pending, rejected, terminal-failed, transient | same mapping | same mapping |
| Retry | ledger attempt state | ledger attempt state | ledger attempt state |

Rules:

- The dispatcher depends on the contract, not target-specific conditionals.
- The stub is a real receiver implementation, not a test-only alternate dispatch path.
- Batch response semantics remain compatible with `contracts/batch-api-contract.md`; only local event-row behavior changes from delete-on-success to ledger-on-success.

Required tests:

- Fork/CI test runs against stub with no Teamspace credentials.
- Teamspace and stub receivers produce the same ledger state for equivalent result payloads.

## 5. Migration

Rules:

- Discover all scoped `queue-<digest>.db` files and legacy `queue.db`; do not migrate only the active scope.
- The digest is not reversible. Unknown source scope is represented as unknown provenance, never fabricated URL/team identity.
- Delivered-and-deleted historical events are unrecoverable; migration preserves only currently queued payloads.
- Migration is transactional per source DB and idempotent on re-run.
- Same `event_id` + identical canonical payload imports once and records all source DB provenance.
- Same `event_id` + divergent canonical payload writes a migration-conflict/audit row, leaves the source DB untouched, blocks cleanup, and exits non-zero/blocked until operator resolution.
- Migration never rewrites event IDs.

Required tests:

- Multiple scoped DBs migrate in one run.
- Unknown digest source migrates with unknown provenance.
- Identical duplicate event IDs dedupe with source provenance.
- Divergent duplicate event IDs create a conflict and preserve the source DB.

## 6. Status And Compatibility

`sync status` and `sync status --check --json` extend existing status output additively.

Required additive JSON sections:

- `target_authority`
- `event_journal`
- `delivery_targets`
- `delivery_ledger`
- `migration_conflicts`
- `terminal_failures`
- `body_upload_compatibility`

Compatibility rules:

- Existing queue/body-upload counts remain available for existing consumers.
- `body_upload_queue` and `body_upload_failure_log` remain owned by `sync/queue.py`.
- No status field may imply body-upload rows are event-journal rows.

Required tests:

- JSON includes all new sections while preserving old top-level fields.
- Status distinguishes retained event count, current-target delivered count, previous-target delivered count, terminal-failed count, and body-upload count.
- GC/archive suggestions trigger only when retained payloads are large and delivered to all known targets.
