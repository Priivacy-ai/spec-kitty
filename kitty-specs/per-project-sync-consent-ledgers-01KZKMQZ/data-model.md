# Data Model: Per-Project Sync Consent Ledgers

## ProjectSyncStore

One directory aggregate for one canonical project UUID:

```text
<runtime-root>/projects/<canonical-uuid>/sync/
├── sync.db
├── egress.lock
└── migration/
    └── reports/
```

`sync.db` is the single transactionally coherent database for consent, capture epochs/sequences, journal, delivery attempts/results, body/offline tasks, target/admission operations, history disclosure actions, and migration/cutover state. The UUID is parsed once and rendered in lowercase hyphenated ASCII; display names, slugs, paths, remotes, users, and teams do not affect the path.

The database stores an immutable owner UUID and schema/layout version. Every open verifies the owner before reading or mutating. `ProjectSyncStore.unit_of_work()` owns the SQLite connection and outer transaction; journal, epoch, ledger, outbox, admission-operation, attempt, and migration repositories receive that unit of work and never call `sqlite3.connect()` or commit on live paths. Nested operations reuse the outer unit and use savepoints only when explicitly requested. `egress.lock` is the cross-process transport/result barrier. The sibling machine layout authority described below decides whether a current-version writer may use a legacy source or must redirect; no component privately infers layout. Reports contain only counts, IDs, hashes, phases, and reason codes—never credentials or raw bodies.

## LayoutGenerationAuthority

One machine-local authority, reached only through the ProjectSyncStore API, coordinates all current-version writers with legacy cutover.

| Field | Rules |
|---|---|
| `generation` | Monotonic machine layout generation. |
| `mode` | `legacy`, `cutover_pending`, or `project_only`. |
| `migration_id` | Nullable owner of an active cutover. |
| `updated_at` | UTC audit timestamp. |

The authority is read and advanced under one machine layout lock. Every current-version journal, delivery, event-outbox, body/offline, foreground, background, daemon, and CLI writer obtains a `LayoutWritePermit` immediately before insert. A permit binds generation, destination kind, and canonical project UUID. If cutover changes the generation before insert, the writer discards the permit and retries through the authority; it never writes both layouts. `project_only` permits cannot name a legacy destination. Migration may advance the authority only after its staged stores verify exactly. Unrecognized old binaries do not possess this API; their late legacy rows are diagnosed residue and never enter live delivery.

## ProjectConsentDecision

| Field | Rules |
|---|---|
| `project_uuid` | Equals the database owner UUID. |
| `state` | `granted` or `refused`; absence denies. |
| `generation` | Monotonic positive integer advanced only by explicit project actions or refusal migration. |
| `action` | `explicit_opt_in`, `explicit_opt_out`, or `migrated_refusal`; never migrated grant. |
| `actor` | Stable local provenance identifier, never a credential. |
| `decided_at` | UTC timestamp. |
| `schema_version` | Explicit decision schema. |

State transitions:

```text
absent --explicit opt-in--> granted(g=1)
absent --migrated refusal--> refused(g=1)
granted(g=n) --explicit opt-out--> refused(g=n+1)
refused(g=n) --explicit opt-in--> granted(g=n+1)
same idempotent action --> unchanged generation
legacy grant --> absent/refused-to-egress until explicit opt-in
```

Only the explicit project-store opt-in/out writer may create a current grant. Retired checkout/default/index paths fail non-zero and do not write this table.

## ConsentEpoch

| Field | Rules |
|---|---|
| `epoch_id` | Monotonic store-local identity. |
| `project_uuid` | Equals the store owner. |
| `opened_at_tail` | Inclusive monotonic capture sequence observed atomically when the epoch opens. |
| `state` | `capture_only`, `eligible`, or `sealed`. |
| `consent_generation` | Nullable for capture-only periods; otherwise the generation that opened eligibility. |
| `sealed_at_tail` / `sealed_at` | Fixed when opt-out or supersession closes the epoch. |
| `reason` | `initial_capture`, `opt_in`, `opt_out`, `target_change`, or explicit migration reason. |

Every event/body/offline row receives a monotonic `capture_sequence` in the same transaction as epoch lookup and references exactly one epoch. Explicit opt-in records the current inclusive tail; ordinary eligibility begins at `capture_sequence > opened_at_tail` in the new epoch. Both transaction orderings are deterministic. Ordinary delivery selects only rows in the current eligible epoch. A separate previewed history action records an explicit cohort; it never relabels or automatically drains the source epoch.

## ProjectTargetAdmission

| Field | Rules |
|---|---|
| `target_identity` | Canonical normalized server identity. |
| `account_identity` | Stable authenticated account reference, never a token. |
| `private_teamspace_id` | Canonical auth-derived Private Teamspace identity. |
| `project_uuid` | Equals the store owner. |
| `configuration_generation` | Advances on target/account/team change. |
| `admission_state` | `pending`, `admitted`, `refused`, or `revocation_pending`. |
| `admission_generation` | Opaque server generation valid only for this exact tuple. |
| `last_error_category` | Payload-free diagnostic category. |

Changing any tuple member invalidates admission eligibility without mutating `ProjectConsentDecision` or selecting old epochs.

## ProjectAdmissionOperation

Durable client control-operation outbox written before remote admit/revoke/readmit:

| Field | Rules |
|---|---|
| `operation_key` | Stable random idempotency key reused after uncertainty. |
| `action` | `admit` or `revoke`. |
| `expected_generation` | Server generation asserted by the operation. |
| `target_identity` / `account_identity` / `private_teamspace_id` / `project_uuid` | Exact immutable audience tuple. |
| `state` | `pending`, `in_flight`, `succeeded`, `conflict`, or `unknown`. |
| `result_state` / `result_generation` / `binding_audience` | Original immutable server result. |
| `attempts` / timestamps | Bounded operational evidence. |

The operation record commits before network I/O. A crash or timeout retries the identical key and expected generation. A new readmission creates a new key only after the prior outcome is reconciled.

## HistoryDisclosureAction

Immutable capability created only by the explicit preview/confirm command:

| Field | Rules |
|---|---|
| `action_id` / `idempotency_key` | Stable identities. |
| `source_epoch_ids` | Sealed epochs eligible for preview only. |
| `row_ids` / `preview_count` / `preview_hash` | Exact immutable cohort. |
| `confirmed_by` / `confirmed_at` | Explicit attributable confirmation. |
| `consent_generation` / `target_generation` / `admission_generation` / `binding_audience` | Current authority snapshot. |
| `state` | `previewed`, `confirmed`, `sending`, `complete`, `terminal_refused`, or `canceled`. |
| `result_ids` | Exact terminal results for the cohort. |

Ordinary selection has no API that can create or consume this capability. Confirmation fails if the preview hash/cohort or any authority generation changed.

## JournalEntry, DeliveryAttempt, DeliveryResult, and OutboxTask

- Each row carries the owning `project_uuid`, `epoch_id`, and stable local ID.
- Before network I/O, `DeliveryAttempt` records the transport-native idempotency identity, target/binding/consent/admission generations, payload hash/reference, state, bounded deadline, and reconciliation policy in the store transaction.
- Results record the attempt ID, target binding generation, server admission generation, timestamps, and terminal refusal category.
- Event, LocalCommit, body, and history/preflight adapters serialize the same source UUID and per-write admission generation.
- A result for a transport started before opt-out is recorded under its original consent/admission generations while the transport/result lease is held. Process death releases the OS lock but leaves a durable `in_flight`/`unknown` attempt. Opt-out holding the barrier must discover those orphaned old-generation states and either reconcile them with Event ID, admission operation key, body content hash, LocalCommit git hash, or history action/event identity, or transition them irrevocably to `terminal_unknown` before acknowledgement. A later worker cannot promote `terminal_unknown` to success or silently resend; only an explicit operator workflow may append a separately attributed disposition.
- `project_not_admitted` is terminal for the correlated row; it never retries as transient.

## ProjectSyncContext

Immutable operation-scoped capability containing:

- canonical project UUID and verified `sync.db` owner;
- consent decision, generation, and current epoch;
- exact target/account/Private-Teamspace binding generation;
- SaaS admission state/generation;
- global deny-only kill-switch result;
- transport/result lease identity when egress begins.

It can answer eligibility but cannot mutate consent. Store/component constructors accept this context or a capability derived from it and reject independent cross-project pairing before selection or network I/O.

## DaemonDenyHint

| Field | Rules |
|---|---|
| `project_uuid` | Discovery key only. |
| `decision` | Only `deny` or `revoked`; no granted value exists. |
| `authority_generation` | Generation observed from the project store. |
| `expires_at` | Staleness boundary. |
| `reason` | Payload-free diagnostic category. |

Hints live outside payload stores at `<runtime-root>/projects/.deny-hints/<canonical-uuid>.json`, one atomically replaced file per UUID. The schema contains only the fields above, a layout version, and integrity checksum. The store unit-of-work publishes a deny/revoke hint only after its decision transaction commits; opt-in removes it after commit. A crash may leave a bounded-TTL stale denial, which affects liveness only and is surfaced by diagnostics. Missing, expired, malformed, generation-mismatched, pending, or possibly granted state requires an authoritative `sync.db` read. Directory enumeration is discovery only and cannot create a store or consent.

## MigrationManifest

| Field | Purpose |
|---|---|
| `migration_id` | Idempotency identity. |
| `protocol_version` | Daemon quiesce/restart and layout version. |
| `source_paths` | Exact legacy stores inventoried. |
| `source_fingerprints` | Logical committed snapshot including WAL content: exact IDs, statuses, attempts, targets, timestamps, counts, schema, and content hashes. |
| `partitions` | Canonical UUID to exact staged row IDs. |
| `quarantine` | Exact unsafe row IDs and reason codes. |
| `phase` | `inventoried`, `quiesced`, `copied`, `verified`, `cutover`, `restarted`, `complete`, or `failed`. |
| `cutover_version` | Project-store-only live layout marker. |
| `started_at` / `completed_at` | Audit chronology. |

Migration opens legacy SQLite sources strictly read-only/immutable or snapshots them through the SQLite backup API after WAL checkpoint semantics are recorded; it never runs constructors/schema migrations against a source. The logical committed snapshot, including main/WAL/SHM treatment, is the preservation authority rather than byte-for-byte inode identity. Staged databases are published only after exact verification. Every current-version legacy writer acquires the machine layout lock, checks layout generation before insert, and retries/redirects to the project store if cutover won. A recognized daemon acknowledges quiesce and restarts on the new layout. An unrecognized old binary may write only residue after cutover; it is diagnosed and never delivered.

## AcceptanceEvidenceManifest

A schema-versioned, immutable manifest emitted by the coordinated acceptance runner. It records exact core, SaaS, and tombstone commits; the selected SaaS checkout/ref; canonical contract SHA-256 digest; client-byte, terminal-parking, server-refusal, mutation, benchmark, and optional hosted-canary artifact references; a SHA-256 checksum and byte count for every referenced artifact; producing command/run identity; created timestamp; and retention location/expiry. Core-originated artifacts and SaaS-originated artifacts have distinct owners. The manifest contains no credentials, raw event bodies, or historical incident data.

## LegacyQuarantine

Non-deliverable copy/reference for rows with missing, malformed, nil, blank, conflicting, or unsafe identity. It has no target, consent, history-action, or sender API. Diagnostics and explicit purge inspect counts/IDs, not bodies by default.

## Invariants

1. One `sync.db` contains exactly one canonical UUID and all transactionally coupled sync state.
2. Store presence, discovery, hint, target, login, URL, environment, repo/path record, and legacy grant never yield `granted`.
3. Local capture always has an epoch; ordinary egress never crosses the current eligible epoch boundary.
4. Every send validates the immutable context inside the project transport/result lease.
5. Opt-out cancels pre-start work, waits for already-started result recording, seals the epoch, and permits no post-return network write or success record.
6. Target/account/Private-Teamspace changes invalidate server admission but not local consent and never redrain history.
7. After cutover, no live writer or reader opens shared legacy stores; late old writes are non-deliverable residue.
8. Migration never invents UUID identity or consent, never mutates sources, and converges after a hard kill at every durable phase.
9. Only `ProjectSyncStore.unit_of_work()` opens live `sync.db`; component-local commits/connections are forbidden by architecture tests.
10. Admission control operations and transport attempts survive process death with their original idempotency/audience identity.
11. Ordinary selection cannot send sealed epochs; only a confirmed immutable HistoryDisclosureAction can do so.
12. Every current-version writer receives its destination from LayoutGenerationAuthority immediately before insert and writes exactly one layout generation.
13. Opt-out does not acknowledge while an orphaned old-generation attempt remains promotable to success.
14. Coordinated acceptance evidence is bound to exact candidate commits and one canonical contract digest by a checksum manifest with explicit retention.
