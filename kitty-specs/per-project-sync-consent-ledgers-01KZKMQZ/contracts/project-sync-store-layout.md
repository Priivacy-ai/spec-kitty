# Project Sync Store Layout Contract

## Authority

This mission-local contract defines the internal project storage boundary. It
does not replace `contracts/cli-saas-current-api.yaml` in the explicitly attested
SaaS candidate checkout.

## Canonical resolver

Input: canonical UUID value only.  
Output: `<runtime-root>/projects/<lowercase-hyphenated-uuid>/sync/sync.db` plus sibling `egress.lock` and non-sensitive migration reports.

Rules:

1. Parse as UUID once; reject missing/nil/malformed values.
2. Render only the canonical UUID, which is deterministic ASCII.
3. Resolve runtime root only through `get_runtime_root()` so `SPEC_KITTY_HOME` and platform semantics remain canonical.
4. Do not accept caller-provided store paths on live APIs.
5. A component opened through context A must assert its on-disk owner UUID is A before reading or mutating.
6. Consent, epochs, journal, delivery, outbox/body, target/admission, and cutover metadata share this one SQLite transaction boundary.
7. `ProjectSyncStore.unit_of_work()` exclusively owns live SQLite connections and outer transactions. Component repositories accept that unit; no live journal/ledger/queue/control adapter may call `sqlite3.connect()` or `commit()` itself. Nested work uses explicit savepoints.
8. `ProjectSyncStore.layout_generation()` is the only current-version writer authority. It returns a generation-bound write permit under the machine layout lock immediately before insert; stale permits retry/redirect exactly once and `project_only` permits can never name a legacy destination.

## Live component contract

| Component | Required capability | Cross-project behavior |
|---|---|---|
| journal | ProjectSyncContext/unit of work | Atomically assign monotonic capture sequence+epoch and reject mismatched UUID before insert. |
| delivery attempt/result | same unit of work | Persist attempt before I/O and result after reconciliation; reject IDs not owned by store. |
| outbox/body queue | same store capability | Assign epoch; reject task UUID mismatch before insert/drain. |
| consent/epoch control | sole store-owned writer | Only explicit opt-in/out or refusal migration may mutate; opt-in begins at current tail and opt-out seals. |
| target/admission control | store-owned writer | Exact server/account/Private-Teamspace/project tuple; cannot mutate local consent. |
| admission operation outbox | store-owned writer | Persist operation key/expected generation/audience before remote mutation; retry same identity. |
| history disclosure | explicit preview/confirm writer | Bind immutable cohort/hash/actor/generations; ordinary selection cannot mint. |
| daemon deny hint | discovery-only writer | May record only bounded deny/revoke; cannot represent or infer grant. |
| purge/status/doctor | explicit project context or explicit legacy diagnostic mode | Never fall back from project context to shared live state. |

## Egress eligibility

```text
eligible = kill_switch_allows
           and consent.state == granted
           and context.consent_generation == current_generation
           and row.epoch_id == current_eligible_epoch
           and target.ready
           and context.target_identity == current_target_identity
           and admission.state == admitted
           and context.admission_generation == current_admission_generation
```

Selection and final transport both enforce eligibility. Every Event, LocalCommit, body, and history/preflight item carries source UUID, current admission generation, and binding audience. Before network I/O, a durable attempt records native idempotency/correlation, generations, payload hash/reference, deadline, and recovery mode. The final check, transport start, and genuine result record occur under a bounded lease. Opt-out cancels unstarted attempts and, while holding that barrier, discovers every orphaned old-generation attempt left after process death. It reconciles with the original identity or freezes the attempt as `terminal_unknown` before returning. No later automatic recovery may promote that state to success or resend.

## Capture epoch contract

Local rows may be captured without consent. Capture sequence and epoch assignment are one transaction. Explicit opt-in records the current inclusive sequence tail; only later sequences in the new epoch are ordinary candidates. Opt-out seals without deleting. Target changes/re-opt-in do not select sealed rows. A history action must preview exact IDs/count/hash, then explicitly confirm under unchanged consent/target/admission audience; it is the only capability permitted to select the cohort.

## Daemon discovery contract

A fresh deny/revoke hint at `<runtime-root>/projects/.deny-hints/<uuid>.json` may skip `sync.db`. It is atomically published after the decision commit, removed after opt-in, expires by bounded TTL, and has no granted value. Missing, expired, malformed, generation-mismatched, pending, or possibly granted state opens authority. Benchmark evidence records every database/table open.

## Legacy rule

Legacy state is migration/diagnostic input only. Before migration implementation, ProjectSyncStore publishes the one layout-generation/write-permit API. Every current-version journal, delivery, event-outbox, body/offline, foreground, background, daemon, and CLI writer uses it immediately before insert, redirecting/retrying after cutover. Migration consumes this authority, quiesces recognized daemons, obtains a strictly read-only logical SQLite snapshot with explicit WAL/SHM treatment, copies/verifies, and atomically publishes project-only cutover. No live fallback delivers legacy state; only unrecognized old binaries can create late residue, which is diagnosed and non-deliverable.

## Candidate contract input

Core contract consumers take an explicit SaaS candidate checkout path, expected commit, and expected SHA-256 digest. They read `contracts/cli-saas-current-api.yaml` from that checkout and fail if the checkout commit or digest differs. Relative ambient sibling lookup, branch name, and version string are forbidden as proof inputs.
