# Sender and Migration Acceptance Matrix

## Live sender census

Every row must be bound to a ProjectSyncContext and durable DeliveryAttempt, covered by a denial test, admitted positive control, both revoke orderings, kill-before-send/during-response/before-result, per-write UUID/generation/audience capture, and architecture census.

| Sender class | Representative surface | Required identity source |
|---|---|---|
| direct dispatcher | `delivery/dispatcher.py` | selected event/store context |
| emitter WebSocket | `sync/emitter.py` | envelope project UUID/context |
| daemon publish | `sync/daemon.py`, `sync/runtime.py` | enumerated project store control state |
| event relay | runtime event emitter/client | frame/envelope context |
| body drain | `sync/body_queue.py`, `sync/body_transport.py` | task project/store context |
| final/exit sync | CLI/final sync orchestration | explicit project context |
| reconnect/local commit | `sync/local_commit.py` | stored frame project UUID/context |
| history import | `sync/history_import/` | import project context |
| tracker-hosted | tracker/SaaS adapter | hosted consent plus separate Channel 2 |
| generic SaaS client | `sync/client.py`/SaaS client | explicit project context |

No row may substitute current working directory, active target, login, global environment, or discovery index. Local consent is project-wide, but server admission is valid only for the exact normalized server, authenticated account/canonical Private Teamspace, project UUID, and generation in the context.

### Revocation orderings

1. **Paused before transport start**: opt-out acquires the barrier, advances/seals, cancels the work, and no request/result occurs.
2. **Transport already started**: the sender holds its result lease; opt-out waits; the genuine result is written under the old generation; opt-out then seals/returns; no later network write or success record occurs.

### Crash orderings

For each transport family, kill the sender after the durable attempt but before send, during response uncertainty, and after remote acceptance but before local result commit. Recovery uses the same Event ID, admission operation key, content hash, git hash, or history action/event identity and records duplicate/success truthfully. Add the compound ordering `kill during response -> immediate opt-out -> late recovery`: opt-out must reconcile or irrevocably freeze the orphan as `terminal_unknown` before acknowledgement, and the late recovery must be unable to record success or resend. A non-reconcilable transport never silently retries.

## Migration data classes

| Source class | Destination | Consent effect |
|---|---|---|
| valid canonical UUID event | owning `sync.db` journal table and capture epoch | none; pre-consent rows remain sealed |
| matching delivery outcome | owning `sync.db` delivery table | none; preserve status/attempts/target/generation |
| matching body/offline task | owning `sync.db` outbox table and capture epoch | none |
| legacy explicit refusal | owning project control state | may write `migrated_refusal` |
| legacy grant/path/repo default/old UUID cache | report only | never grant; explicit re-consent required |
| missing/malformed/nil/blank UUID | legacy quarantine | none; permanently non-deliverable |
| conflicting identity or ledger ghost | legacy quarantine/error report | none; fail closed |

## Fault injection phases

Run migration in a subprocess and hard-kill before/after daemon/current-writer quiesce, read-only logical snapshot, each table copy, verification, staged publication, cutover marker, redirect, and restart. Verify exact committed IDs/statuses/attempts/targets/timestamps/hashes and explicit main/WAL/SHM treatment; do not instantiate schema-migrating source constructors. For every current-version journal, delivery, event-outbox, body/offline, foreground, background, daemon, and CLI writer, pause before its layout permit/insert and exercise both orderings: the write is included in the legacy snapshot or redirected once to the project store, never both. An unrecognized old-binary post-cutover write is non-deliverable residue. No rerun duplicates or redelivers.

## Six-project acceptance

- A: current locally eligible epoch and exact-target remote admission — only project allowed to appear in conforming CLI request bytes or persist.
- B: locally refused.
- C: no decision.
- D: opted out during paused transport.
- E: identity-less legacy rows in quarantine.
- F: valid UUID admitted to a different target/account/team; bypass client attempts the wrong binding.

The core-owned real CLI scenario captures exact HTTP/WebSocket bytes and proves B–F are absent, then records stale-generation terminal parking. The separately owned SaaS evidence submits B–F through bypass/legacy adapters and proves correlated refusal with zero durable/readable/broadcast effects. Event ID sets and a unique foreign marker make negative evidence non-vacuous; selection counts alone are insufficient. A shared checksum manifest binds the exact core/SaaS/tombstone commits and canonical contract digest while preserving these non-overlapping proof owners.
