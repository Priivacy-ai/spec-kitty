# Mission Specification: Journal Project Consent

**Mission Branch**: `feat/journal-project-consent-3030`
**Created**: 2026-07-28
**Revised**: 2026-07-28 (post-spec adversarial squad — root cause re-anchored, see "Correction")
**Status**: Draft
**Input**: `Priivacy-ai/spec-kitty#3030` (P0) — CLI counterpart of `Priivacy-ai/spec-kitty-saas#585`

## Problem

The sync drain **authorizes and delivers at different scopes**. One opted-in checkout ships the
whole producer-scoped event store — every unrelated local project on the machine — to the hosted
server. Confirmed live on 2026-07-27: 1,322 events belonging to 5 projects the operator never opted
into were delivered alongside 7,811 from the one intended project. Per-repo routing in that checkout
was correct throughout. Confidentiality breach reachable with no misconfiguration; the only
"mistake" available is working on more than one project on one machine.

### Correction to the original diagnosis

Issue #3030 and `saas#585` both pin the defect at `sync/batch.py:1064-1080`. **That is the wrong
drain for `sync now`.** Verified:

- `cli/commands/sync.py:2360-2367` — "the journal-based dispatcher is now the **SOLE** event drain
  (FR-001): the retired legacy `service.sync_now()` offline-queue drain deleted journal-owned events
  AND double-POSTed every event the dispatcher also delivers (the dual-drain defect)".
  `cli/commands/sync.py:1004-1005` repeats it: "This is the SOLE event-delivery path for `sync now`".
- `sync/queue.py:1-12` — "Event-queueing authority has been **retired** from this module: the durable
  event store is now the WP03 append-only journal… The `queue` table here is kept only as the
  *legacy batch-transport bridge*".
- `sync/migrate_journal.py:769-772` — "delivery reads from the journal, not the queues".

The real selection is `delivery/dispatcher.py:192-223` `_select_undelivered`, whose universe is
`journal.read_all()` (`dispatcher.py:214`) — every row of every project, with no project predicate —
reached from `cli/commands/sync.py:1001-1049` `_run_event_sync_dispatch`. The `selected` figure the
incident reported is `DispatchSummary.selected` (`dispatcher.py:87`, printed at
`cli/commands/sync.py:1047-1048`), not a `batch.py` counter.

A fix implemented at `batch.py:1064` would pass its unit tests and leak in production.

### Root cause, restated against the real path

1. **The delivery context has no consent gate at all.** The complete gate vocabulary is
   `GateKind = {SAAS_ENABLED, PRIVATE_TEAMSPACE, AUTH, ENDPOINT_CONFIGURED}`
   (`delivery/receivers.py:143-146`), built at `cli/commands/sync.py:681-686` from
   `is_saas_sync_enabled()`, `bool(target.team_slug)`, `bool(auth_token)`, `receiver.endpoint_url`.
   No consent field exists. `is_sync_enabled_for_checkout` has **zero callers** under `delivery/`.
   Authorization on the leaking path is per-producer/team (`event_journal/journal.py:60-75`) — which
   is exactly the scope of the whole machine's journal. The defect is larger than "scope mismatch":
   it is the total absence of a consent gate where delivery is decided.
2. **The consent registry that does exist is default-ALLOW.** `sync/routing.py:82-87`
   (`_build_checkout_sync_routing`) falls through to `effective_sync_enabled = True` when neither a
   checkout override nor a repo default is recorded. In the incident the five client repos were
   **never opted in**, so they have no record — under a literal "reuse the existing records" reading
   each evaluates to *consented*. Inverting only the `routing is None` branch
   (`routing.py:114-116`) does not close this.
3. **Consent is keyed by absolute filesystem path; events are keyed by project.**
   `sync/config.py:216,233` writes `checkout_overrides[str(repo_root.resolve())]`. `project_uuid`
   appears nowhere in `sync/config.py`. A `project_uuid` is bound to a checkout only inside that
   checkout's own working tree (`routing.py:64` reads `repo_root/.kittify/config.yaml`).
   `sync/project_identity.py` is a 29-line re-export shim holding no mapping. **There is no durable,
   machine-global `project_uuid → consent` index.** The predicate FR-003 needs has no data source.
4. **Two live drains over two stores.** `sync now` uses the journal dispatcher, but the background
   daemon still drains the legacy queue: `sync/background.py:589-592` constructs
   `BackgroundSyncService(queue=OfflineQueue(), …)` and `background.py:455-461` reaches
   `batch_sync(queue=self.queue, …)`, plus `background.py:395` `_perform_full_sync` →
   `sync_all_queued_events`. Whichever store this mission does not cover keeps shipping.

## User Scenarios & Testing *(mandatory)*

### User Story 1a - Containment: the drain refuses rather than leaks (Priority: P1)

Before any schema work, the drain stops being silent. If a selected batch spans more than one
project, it refuses, names the projects, and exits non-zero without POSTing. If consent cannot be
determined, it denies.

**Why this priority**: This is hours of work with no migration, and it converts a silent
confidentiality breach into a loud refusal. It ships first and independently of everything below.

**Independent Test**: Seed a journal with events from six projects, run the drain against a
recording ingress, assert zero HTTP requests were made and the refusal names the projects.

**Acceptance Scenarios**:

1. **Given** a selected batch spanning more than one project, **When** pre-flight runs, **Then** the
   drain refuses before any POST, names the projects, and exits non-zero without mutating delivery
   state or bumping retry counts.
2. **Given** `resolve_checkout_sync_routing_readonly()` returns `None`, **When** the sync-enabled
   gate is consulted, **Then** it denies and no network request is made.
3. **Given** a project with **no** consent record at all, **When** consent is evaluated for
   delivery, **Then** the answer is deny — absence of a record is non-consent.
4. **Given** no consented events are selectable, **When** the drain runs, **Then** it short-circuits
   before building or POSTing a payload, reports "nothing to deliver", and exits zero with a message
   that names the real cause rather than the unrelated no-Private-Teamspace diagnostic.

---

### User Story 1b - Only consented projects are ever selected (Priority: P1)

Selection itself excludes non-consented projects, so the invariant holds without relying on a
refusal.

**Why this priority**: The durable fix. Depends on the enablers below, which is why US1a ships
first.

**Independent Test**: Seed a journal with events from six `project_uuid`s, consent exactly one,
drain against a recording ingress, and assert `delivered_project_uuids ⊆ consented_project_uuids`
and `None ∉ delivered_project_uuids`. Fixture must leave the five non-consenting projects with **no**
consent record, mirroring the incident.

**Acceptance Scenarios**:

1. **Given** a journal holding events from 6 projects with consent recorded for 1, **When** the drain
   runs, **Then** every delivered event belongs to the consented project and the other 5 projects'
   rows remain in the journal, undeleted.
2. **Given** an event whose project identity cannot be resolved, **When** selection runs, **Then**
   it is treated as non-consented and never selected, and it is **counted and reported** so the
   denial is observable rather than silent.
3. **Given** 2,000 non-consented events older than 10 consented events, **When** one drain runs,
   **Then** all 10 consented events are delivered — the predicate is applied before the row limit,
   not after it.
4. **Given** a checkout that is opted out, **When** the drain runs, **Then** rows are left untouched
   and no request is made.
5. **Given** the background daemon rather than `sync now`, **When** it drains, **Then** the same
   consent invariant holds on that path and store.

---

### User Story 2 - Per-project store state is visible before draining (Priority: P1)

`sync doctor` and `sync status` report what is actually in the store, per project, with consent
state.

**Why this priority**: `doctor` reported healthy throughout the incident. A fix the operator cannot
verify is not a fix.

**Independent Test**: Seed a multi-project journal; assert both commands report one row per project
with event count, oldest-event age and consent state, and that totals reconcile against the
journal's retained-event count.

**Acceptance Scenarios**:

1. **Given** a journal spanning 6 projects, **When** `sync doctor` runs, **Then** it reports a
   per-project breakdown with consent state and flags non-consented projects.
2. **Given** the same, **When** totals are summed, **Then** they reconcile against the journal's
   retained-event count (`_count_retained_events`, `cli/commands/sync.py:714-717`) — **not** against
   `OfflineQueue().get_queue_stats()` (`cli/commands/sync.py:3619-3627`), which is empty after
   `sync migrate` and is the source of the incident's false-green.
3. **Given** a consented project whose checkout path no longer resolves, **When** the report runs,
   **Then** it appears as a distinct "consented but unresolvable" row rather than silently denied.
4. **Given** `sync migrate` consolidating rows, **When** it runs, **Then** it reports the per-project
   composition of what it moved.

---

### User Story 3 - The operator can purge non-consenting data locally (Priority: P2)

**Why this priority**: There is no remediation path today; `sync gc` only purges payloads delivered
to *all* targets, so it cannot clear retained rejected rows. Independent of the enablers, so it can
be pulled forward.

**Independent Test**: Seed delivered, rejected and undelivered rows across projects; dry-run and
assert nothing changed; execute and assert exact removal.

**Acceptance Scenarios**:

1. **Given** a multi-project store, **When** `sync purge --project <slug-or-uuid>` runs without
   confirmation, **Then** it reports per-state counts and changes nothing.
2. **Given** the same, **When** run with confirmation, **Then** only that project's rows are removed
   across **both** the journal and the delivery ledger, including rejected rows `sync gc` cannot
   reach.
3. **Given** a slug matching nothing, **When** purge runs, **Then** it reports zero matches and
   exits zero.
4. **Given** `sync purge --all` with confirmation, **When** it runs, **Then** the store is emptied
   and the total is reported.

---

### User Story 4 - Machine-global arming is documented (Priority: P3)

**Acceptance Scenarios**:

1. **Given** the sync docs, **When** an operator reads the env-var reference, **Then** the
   machine-global scope of `SPEC_KITTY_ENABLE_SAAS_SYNC` and `SPEC_KITTY_SAAS_URL` is stated
   explicitly, with a docs-anchor check that fails in CI if the section is removed.

---

### Edge Cases

- **Consented checkout moved, renamed or deleted.** Consent is path-keyed
  (`sync/config.py:216`), and resolving a `project_uuid` requires reading a file inside that path
  (`routing.py:64`). A `git mv`, reclone or laptop migration makes the lookup miss, FR-004 denies,
  and the operator's **own** history strands with no diagnostic. Covered by FR-013 (uuid-keyed
  consent) and US2 scenario 3.
- **Identity-less events.** `sync/emitter.py:2081-2085` deliberately enqueues events with no
  `project_uuid`. Identity resolves from three sites (`namespace.project_uuid`, top-level, payload —
  `sync/queue.py:1714-1720`). Any recorder or predicate must use the same three-site chain, and the
  nil sentinel `00000000-0000-0000-0000-000000000000` (`emitter.py:2150`) counts as unresolvable,
  not as a groupable value.
- **Two checkouts of one repository with opposite overrides.** `project_uuid` lives in
  `.kittify/config.yaml`, which can be committed, so two checkouts can share a uuid and hold
  contradictory `checkout_overrides`. Resolution rule is mandated by FR-013.
- **Same repository re-`git init`ed.** New `project_uuid`, genuinely a new project, starts
  non-consented.
- **Consent revoked between selection and POST.** Evaluated at selection; an in-flight batch is not
  retroactively filtered. Revocation takes effect from the next selection.
- **Journal per producer, not per team.** `resolve_journal_path` keys on `user_id`/`team_slug`;
  switching teams selects a different DB. The predicate must not assume one journal means one team.
- **Backfill interrupted.** Idempotent and resumable; a partial backfill must never leave a row
  *appearing* consented.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Consent gate in the delivery context | US1a | As a maintainer, I want the delivery context to carry a consent gate — a new `GateKind` plus a consent port injected into the dispatcher, mirroring the existing `ReceiverGate`/`GateContext` pattern (`delivery/receivers.py:165-203`) — so delivery is authorized at the scope it delivers. | High | Open |
| FR-002 | Absence of a consent record denies | US1a | As a consultant, I want an unrecorded project treated as non-consented **for capture and for delivery**, overriding the default-allow fall-through at `sync/routing.py:87`, so never-opted-in projects neither reach the journal nor ship. Pinned by `tests/sync/test_sync_consent_default_deny.py::test_unconfigured_checkout_does_not_consent_to_sync`. | High | Open |
| FR-003 | Routing gate fails closed | US1a | As a maintainer, I want `is_sync_enabled_for_checkout()` to deny when routing is unresolvable (`routing.py:114-116`) so inability to determine consent is never read as consent. Defence in depth for the daemon path, which is its only caller set. | High | Open |
| FR-004 | Cross-project drain refusal | US1a | As an operator, I want the drain to refuse, name the projects and exit non-zero if a selected batch spans more than one project, so a regression in FR-007 cannot silently leak. | High | Open |
| FR-005 | Empty-selection short-circuit | US1a | As an operator, I want the drain to short-circuit before building or POSTing when nothing is selectable, and to report the real cause, instead of POSTing `{"events": []}` and printing the unrelated no-Private-Teamspace message (`sync/batch.py:1484-1488`). | High | Open |
| FR-006 | Project identity on stored events | US1b | As a maintainer, I want additive indexed `project_uuid`/`project_slug` columns on the journal event row (`event_journal/models.py:31-58` `ORDERED_COLUMNS`) as a derived projection of the envelope, so consent is evaluable without decoding every payload. | High | Open |
| FR-007 | Selection filters by consent | US1b | As a consultant, I want the project predicate applied inside the journal read, so non-consented events are never part of the selected universe. | High | Open |
| FR-008 | Project-filtered journal read seam | US1b | As a maintainer, I want a project-filtered journal read API (e.g. `read_all(project_uuids=…)`) consumed by `_select_undelivered` (`delivery/dispatcher.py:214`), because the current `read_all()` materializes every row of every project and an indexed predicate is otherwise impossible. | High | Open |
| FR-009 | Backfill existing rows | US1b | As an operator, I want existing rows' identity decoded into the new columns idempotently, using the three-site resolution chain, so the predicate covers the 42-day history. | High | Open |
| FR-010 | Mandatory identity at write time | US1b | As a maintainer, I want project identity required when an event is journaled going forward, closing the identity-less class by construction rather than denying it forever downstream. | High | Open |
| FR-011 | Unresolved-identity events are observable | US1b | As an operator, I want events denied for unresolvable identity counted and surfaced in the per-project report, so fail-closed denial is visible rather than silent data loss. | High | Open |
| FR-012 | Both drains enforce the invariant | US1b | As a maintainer, I want the consent invariant enforced on the background-daemon queue drain (`sync/background.py:455-461`) as well as the journal dispatcher, or the queue-backed drain removed, so the uncovered store cannot keep shipping. | High | Open |
| FR-013 | Durable per-project consent index | US1b | As a consultant, I want consent recorded against `project_uuid` (written by `enable_checkout_sync`/`disable_checkout_sync`, `routing.py:130-182`, which already hold both `repo_root` and the resolved uuid), backfilled from today's path-keyed records, with a stated conflict rule — **deny if any checkout of the project is opted out** — and a way to grant or revoke consent by slug/uuid without standing in the checkout. | High | Open |
| FR-014 | Terminal reject classification | US1b | As a maintainer, I want a stable server reject reason mapped to `failed_permanent` and counted in terminal-failure totals, because `failed_permanent` is produced at exactly one site today (`sync/batch.py:414-418`, oversized events) and every server rejection becomes `rejected` → `retry_count + 1` with no deletion and no retry ceiling. Folds #3005; required by `saas#585` FR-004. | High | Open |
| FR-015 | Per-project store reporting | US2 | As an operator, I want `sync doctor`, `sync status` and `sync migrate` to report per-project event count, oldest-event age and consent state, reconciled against the journal's retained count. Folds #3004, without which the report renders from the wrong store. | High | Open |
| FR-016 | Purge by project | US3 | As an operator, I want `sync purge --project <slug-or-uuid>`, dry-run by default, removing that project's rows from both the journal and the delivery ledger via `delivery/retention.py` (`_purge_journal_rows`, `retention.py:51,189`). | Medium | Open |
| FR-017 | Purge all | US3 | As an operator, I want `sync purge --all` behind explicit confirmation. | Medium | Open |
| FR-018 | Document machine-global env vars | US4 | As an operator, I want the machine-global scope of both env vars documented, with a CI-checkable anchor. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No unconsented egress | For every drain in the suite, `delivered_project_uuids ⊆ consented_project_uuids` **and** `None ∉ delivered_project_uuids`. Stated as a subset invariant, not a cardinality check: identity-less events collapse to `{None}` and would satisfy `cardinality == 1` while leaking. The recorder must resolve identity via the same three-site chain as `queue.remove_project_events` (`queue.py:1714-1720`). | Security | High | Open |
| NFR-002 | Predicate precedes the row limit | A drain delivers consented events regardless of how many non-consented rows precede them in FIFO order. Filtering after `LIMIT` starves the drain permanently (`_should_stop_sync_loop` breaks on an empty selection); the predicate must be inside the filtered read. | Reliability | High | Open |
| NFR-003 | Predicate cost does not scale with store size | With 100k rows across 20 projects, selecting one project's batch performs no full-table payload decode — indexed column lookup only, via FR-008's filtered read. | Performance | High | Open |
| NFR-004 | Backfill is idempotent and lossless | Two runs yield identical column values and identical row counts; no row deleted or mutated outside **the new identity columns**. | Reliability | High | Open |
| | | *Wording narrowed 2026-07-30: was "the two new columns". `repo_slug` was added later (WP06, operator decision) and is one of the columns this mission introduced, so the invariant always held — only the count was stale. Narrowing the **write** instead was rejected: it would blank the repo name for all pre-mission history, which is the incident's own population, with no safety gain since `repo_slug` cannot widen consent.* | | | |
| NFR-005 | Consent gates capture, not only delivery | **Amended 2026-07-29 (operator decision).** Previously: "capture continues unconditionally; no event dropped at write time." That yielded to `#3031` Defect 3 — a non-consenting project's events must **never reach the journal**. Capture-first durability now applies only to *consenting* projects. `event_journal/journal.py` documents the journal write as deliberately unconditional for Teamspace-bound families, so this is a **deliberate reversal of a documented invariant**, not an oversight; the journal's own contract must be updated with it. Beware the fake-green: a bare `if skip_journal: return event` guard leaves capture unconditional at the real caller. | Security | High | Open |
| NFR-006 | Purge is exact | After purging project X, a differential row count over all other projects, in journal and ledger, is zero. | Correctness | High | Open |
| NFR-007 | Fake ingress must exercise the real window | **Retargeted 2026-07-30.** `max_events_per_batch` / `_should_probe_advertised_limits` live only in `sync/batch.py`, whose queue drain WP02 retired — a fake advertising batch limits would exercise an unreachable path. The journal drain's real window is the local constant `_EVENT_SYNC_DISPATCH_BATCH_LIMIT` in `_run_dispatch_batches` (`cli/commands/sync.py:807-820`), halved on HTTP 413 and regrown. The recording ingress must exercise **that** window, since it is what decides whether non-consented rows can fill the selection window. Note WP02 un-exported `batch.py`'s drain entry points but did not delete the module, so it still exists and must not be used as the target. | Security | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Additive schema only | New columns nullable and additive; no rename, retype or drop. An older CLI reading the same DB keeps working. | Technical | High | Open |
| C-002 | Migration never deletes | The backfill must not delete or quarantine any row, including rows whose identity stays unresolvable. Deletion is the operator's explicit act via FR-016/FR-017. | Technical | High | Open |
| C-003 | Journal carries no target/receiver identity | Restated post-review: the journal is **target**-agnostic, not delivery-agnostic — it already stores a delivery-eligibility verdict via `classify_drain_blocked_reason` and the `drain_blocked_reason` column (`journal.py:338`, `models.py:26`). So "the journal must not know about consent" is not load-bearing; what must stay out is *target/receiver* identity (`models.py:2-9`: no target/server/queue-scope field). The new columns are a data projection; the consent *decision* stays in delivery. Decide explicitly whether project consent extends the existing eligibility vocabulary or is a third one — never ship two representations of one invariant. **Decided 2026-07-29: a SEPARATE representation, and the two never overlap.** `drain_blocked_reason` is a *machine-global gate snapshot* taken at capture time (saas/auth/team), re-evaluated at each drain tick and therefore transient; project consent is a *per-project* decision that is stable across ticks. Collapsing them would mean either stranding every pre-login capture or making consent transient. So: consent is represented by the stored `project_uuid` column plus the `consent.py` resolver, and `drain_blocked_reason` keeps its existing vocabulary untouched. Post-backfill the stored column is the **sole** authority for selection (T018); the in-memory identity chain is used only by FR-004's refusal check and the backfill. The one invariant is "delivered ⊆ consented", represented once, in selection. | Technical | High | Open |
| C-004 | Purge routes through retention, not the legacy queue | Use `delivery/retention.py`. `queue.remove_project_events()` (`queue.py:1702-1723`) targets the retired store and full-decodes every row; treat it as superseded and remove it. | Technical | High | Open |
| C-005 | Journal-per-repository-root is a non-goal | Re-scoping the journal per repo root would strand existing multi-week history and is not required for the *egress* property, which FR-006+FR-007 secure within the shared store. Recorded and declined. | Technical | Medium | Open |
| C-006 | Collection remains open for *consenting* projects only | **Restated 2026-07-29** — the original text said "NFR-005 forecloses" write-path gating and concluded the mission secures egress, not collection. NFR-005's amendment reversed that premise: write-path gating is now **required and shipped** (T006 — a non-consenting project's events never reach the journal). The either/or is therefore resolved in favour of gating the write path, and C-005 still declines per-root journal scoping. What remains open is narrower than before: a *consenting* project's payloads still accumulate in one machine-global store shared with other consenting projects, and rows captured **before** T006 landed are still on disk for every project (the incident's own 1,322 among them) until FR-016's purge removes them. So this mission now secures egress **and** future collection for non-consenting projects, while historical collection stays an operator purge action. Whether that is sufficient for a P0 is the operator's call. | Technical | High | Open |
| C-007 | Server-side half is out of scope | Rejecting events whose project is not bound to the authenticated teamspace is `spec-kitty-saas#585`. **Exception:** FR-014 is a genuine directed dependency from that mission into this one and is in scope here. | Technical | High | Open |

### Key Entities

- **Journal event row**: the durable record in `event_journal`. Gains additive, indexed
  `project_uuid`/`project_slug` as a derived projection; identity remains authoritative in the
  envelope.
- **Project consent record**: uuid-keyed consent (FR-013), backfilled from today's path-keyed
  `checkout_overrides`. Absence means deny.
- **Consent port**: the delivery-context abstraction the dispatcher consults. Pure data, no globals,
  mirroring `ReceiverGate`.
- **Selected universe**: the output of the project-filtered journal read. Post-mission invariant:
  every member belongs to a consented project.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Incident reproduction — 6 projects, 1 consented, the other 5 carrying **no consent
  record at all** — delivers events from exactly the consented project. Fails on `origin/main` at
  mission start.
- **SC-002**: Liveness — 2,000 non-consented events older than 10 consented events; one drain
  delivers all 10.
- **SC-003**: Each fail-closed path denies with no network request, each with its own test:
  unresolvable routing (FR-003), absent consent record (FR-002), unresolvable event identity
  (FR-011), multi-project batch (FR-004), empty selection (FR-005).
- **SC-004**: `sync doctor` on a contaminated store names every project present with count, oldest
  age and consent state, reconciled against the journal's retained count. Zero hand-written SQLite
  queries needed to answer "whose data is in here?".
- **SC-005**: The background-daemon drain satisfies NFR-001 on its own store, or the queue-backed
  drain is gone and a test asserts no code path constructs it.
- **SC-006**: `sync purge --project X` removes 100% of X's rows across journal and ledger and 0% of
  any other project's.
- **SC-007**: Backfill run twice over a 10k-row multi-project journal yields byte-identical column
  values and an unchanged row count.
- **SC-008**: A live two-project drain against **`spec-kitty-dev`** (never production, per
  `docs/production-safety-guardrails.md`) delivers only the consented project, verified server-side
  by grouping delivered events by `project_slug`. Evidence artefact: the captured query output. If
  `saas#585` FR-009's report command has shipped, use it; otherwise a read-only Django-shell
  aggregation is the sanctioned fallback.
- **SC-009**: A server rejection carrying the stable refusal reason is classified `failed_permanent`,
  counted in terminal-failure totals, and the drain makes forward progress past it (closes #3005 and
  unblocks `saas#585` FR-004).

## Absorbed: spec-kitty#3031's red pins (operator decision, 2026-07-29)

`origin/main` carries two deliberately-red P0 reproductions under the honest-red-P0 policy
(ADR 2026-07-17-1). **This mission absorbs them and they are its acceptance gate.** They are marked
`regression`, so the blocking `regression tests` CI job selects them; the marker comes off as each
goes green.

`tests/sync/test_sync_consent_default_deny.py` — five pins:

1. `test_unconfigured_checkout_does_not_consent_to_sync` — **contradicted this spec's earlier
   position.** An unconfigured checkout must resolve `effective_sync_enabled is False`. An earlier
   implementation attempt flipped this, measured 39 regressions across `tests/sync`, and reverted on
   capture-first grounds. The operator has now ruled: those 39 tests encode the defect, not a
   requirement — they are updated as part of the fix.
2. `test_unresolvable_routing_does_not_consent_to_sync` — satisfied by FR-003 (shipped, `de274f3f`).
3. `test_project_config_refusal_is_honoured` — **new to this mission.**
4. `test_project_config_refusal_outranks_env_override` — **new.** Project-local refusal beats the
   machine-global env var.
5. `test_machine_global_opt_in_does_not_leak_to_sibling_projects` — **new.** The sibling-leak case.

`tests/sync/test_sync_consent_capture_gap_3031.py` — Defect 3, ungated capture. See NFR-005 as amended.

### New requirement inherited from #3031

**FR-019 — consent lives in the project, not the machine.** Today the consent record sits in
machine-global `~/.spec-kitty/config.toml` keyed by `repo_slug`: invisible in the repo it governs,
unreviewable, not version-controlled, and keyed on a **mutable git remote**. Consent must be
expressible in the project's own `.kittify/config.yaml` and must outrank the machine-global record and
the env var (pins 3 and 4). This partially supersedes FR-013's uuid-keyed index — reconcile the two
before implementing either.

### FR-013 × FR-019 reconciliation (operator decision, 2026-07-29)

**Both, with project-local winning.** FR-019 supersedes FR-013 on *authority*, not on *existence*:

1. **`.kittify/config.yaml` in the project** — authoritative whenever the checkout is readable. A
   project-local **refusal outranks a project-local grant** (the many-to-one case: two checkouts of one
   `project_uuid` with opposite settings resolve to deny, per FR-013's stated conflict rule).
2. **Machine-global uuid-keyed index** — the drain's lookup, and it must exist. The dispatcher resolves
   consent for events carrying only a `project_uuid`, and it must still answer when the checkout has
   moved, been renamed or deleted. A project-local-only design cannot: reading
   `.kittify/config.yaml` requires the path (`routing.py:64`), so a relocated checkout would strand the
   operator's own history — the "consented checkout moved" edge case and US2 scenario 3's
   "consented but unresolvable" row.
3. **Env var** — never a grant on its own. `SPEC_KITTY_ENABLE_SAAS_SYNC` is machine-global arming, not
   per-project consent; pin 5 (`test_machine_global_opt_in_does_not_leak_to_sibling_projects`) is
   exactly this.
4. **Absence at every level → deny** (FR-002).

Consequences for WP05: two writers, **one** resolver. The precedence chain is encoded once in
`sync/consent.py` and never re-derived per call site — the same single-definition rule T011 applies to
identity resolution, for the same reason (a second copy is how the reporting surface and the drain come
to disagree). The machine-global index is a **cache with a stated staleness rule**, not a second source
of truth: when a checkout is readable and its file disagrees with the index, the file wins and the index
is corrected. FR-015's report must render which level answered, or an operator cannot tell a
project-local grant from a stale cached one.

## Folded dependencies

Both were characterised as "incidental" on #3030 and `saas#585`. Neither is:

- **#3004** — `sync doctor`/`sync status` derive queue truth independently of `target_authority`,
  giving false-green `Queue size 0` after `sync migrate`. FR-015 bolts a per-project breakdown onto
  exactly those commands; rendering it from the wrong store would reproduce the incident's
  fake-green. Prerequisite for US2.
- **#3005** — permanently-rejected events reported as `Terminal failures 0`. FR-014 closes it, and
  `saas#585` FR-004 cannot work without it.

`#2995` / PR `#2998` are closed and merged as of 2026-07-27; no longer dependencies.
