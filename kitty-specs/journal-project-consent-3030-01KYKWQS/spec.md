# Mission Specification: Journal Project Consent

**Mission Branch**: `feat/journal-project-consent-3030`
**Created**: 2026-07-28
**Status**: Draft
**Input**: `Priivacy-ai/spec-kitty#3030` (P0) — CLI counterpart of `Priivacy-ai/spec-kitty-saas#585`

## Problem

The sync drain **authorizes per-checkout but delivers per-journal**. One opted-in checkout ships
the entire machine-global event journal — every unrelated local project — to the hosted server.
Confirmed live on 2026-07-27: 1,322 events belonging to 5 projects the operator never opted into
were delivered alongside 7,811 from the one intended project. Per-repo routing in that checkout was
correct throughout. This is a confidentiality breach reachable with no misconfiguration; the only
"mistake" available is working on more than one project on one machine.

Verified root cause, three facts:

1. **Selection precedes authorization, and authorization never reads the selection.**
   `src/specify_cli/sync/batch.py:1064-1080` selects via
   `_select_events_for_advertised_limits(queue, ...)` — no project predicate, observed
   `selected 13384` — then gates on `_is_checkout_sync_enabled_for_batch()`, a single boolean about
   the checkout the process happens to be in. `project_slug` does not appear in `batch.py` at all.
2. **The gate fails open.** `src/specify_cli/sync/routing.py:114-116` returns `True` when
   `resolve_checkout_sync_routing_readonly()` yields `None`. Unresolvable routing is treated as
   consent.
3. **Project identity is not a queryable property of a stored event.** The `queue` table is
   `(id, event_id, event_type, data TEXT, timestamp, retry_count, coalesce_key)`
   (`src/specify_cli/sync/queue.py:651-663`). Project identity exists only inside the `data` JSON
   blob, reachable only by decoding every row — which is exactly what
   `queue.remove_project_events()` (`queue.py:1702-1723`) already does. The journal is
   producer-scoped, not project-scoped: `resolve_journal_path()`
   (`src/specify_cli/event_journal/journal.py:78-90`) keys the DB by
   `user_id`/`team_slug` only (`journal-<token>.db`).

Fact 3 is why this cannot be fixed by adding a `WHERE` clause: the column the predicate needs does
not exist. An enabler is required before the security property is expressible.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A drain delivers only consented projects (Priority: P1)

A consultant works on five clients' repositories plus one internal repository on the same laptop.
They opt the internal repository into SaaS sync and run `spec-kitty sync now`. Only the internal
repository's events leave the machine. The five clients' events stay in the journal, untouched and
undelivered, no matter how the drain is invoked or from which directory.

**Why this priority**: This is the confidentiality breach. Everything else in this mission is
visibility or cleanup around it. Delivered data cannot be recalled, so this is the only requirement
whose absence keeps the P0 open.

**Independent Test**: Seed a journal with events from six distinct `project_uuid`s, consent exactly
one, drain against a recording fake ingress, and assert the outbound payload contains events from
exactly one project and that the delivered count equals the consented project's event count. This
is a direct regression reproduction of the 2026-07-27 incident and fails on today's `main`.

**Acceptance Scenarios**:

1. **Given** a journal holding events from 6 projects and consent recorded for 1, **When**
   `sync now` runs, **Then** every event in every outbound batch belongs to the consented project,
   and the 5 non-consented projects' rows remain in the journal with `retry_count` unchanged.
2. **Given** an event whose project identity cannot be resolved from envelope or payload, **When**
   selection runs, **Then** the event is treated as **not consented** and is never selected —
   unresolvable identity denies, it does not permit.
3. **Given** `resolve_checkout_sync_routing_readonly()` returns `None`, **When** the sync-enabled
   gate is consulted, **Then** it returns deny and the drain makes no network request.
4. **Given** a selected batch that — through any path, including a future regression — spans more
   than one project, **When** the pre-flight runs, **Then** the drain refuses before any POST,
   names the projects involved, and exits non-zero without bumping `retry_count`.
5. **Given** a checkout that is opted out, **When** `sync now` runs, **Then** behaviour is
   unchanged from today: rows are left untouched with a transient `sync_disabled` outcome.

---

### User Story 2 - The operator can see per-project queue state before draining (Priority: P1)

Before opening the valve, the operator runs `spec-kitty sync doctor` and sees which projects are
sitting in the queue, how many events each holds, how old the oldest is, and whether each is
consented. Cross-project contamination is visible *before* anyone drains, not discoverable
afterwards by hand-querying SQLite.

**Why this priority**: In the incident, `sync doctor` reported `Server: Connected` and a healthy
queue depth throughout. The contamination was found only by querying `journal-stijn.db` payloads
directly and grouping by `project_slug`. A fix the operator cannot verify is not a fix — and this
surface is what makes US1 auditable in the field.

**Independent Test**: Seed a multi-project journal, run `sync doctor` and `sync status`, and assert
both report one row per project with event count, oldest-event age, and consent state; assert
non-consented projects are visibly marked as such.

**Acceptance Scenarios**:

1. **Given** a journal spanning 6 projects, **When** `sync doctor` runs, **Then** output includes a
   per-project breakdown of queue depth and oldest-event age, and flags projects that are not
   consented.
2. **Given** the same journal, **When** `sync status` runs, **Then** it reports the same per-project
   breakdown, and the totals reconcile exactly with the existing aggregate queue depth.
3. **Given** a journal whose events all belong to consented projects, **When** `sync doctor` runs,
   **Then** no contamination warning is emitted.

---

### User Story 3 - The operator can purge non-consenting data from the journal (Priority: P2)

Having discovered other clients' events in the local journal, the operator removes them with a
supported command instead of deleting SQLite files by hand.

**Why this priority**: Today there is no remediation path at all. `sync gc` only purges payloads
delivered to *all* targets, so it cannot clear the retained rejected rows the incident left behind.
Ranked below US1/US2 because it cleans up damage rather than preventing it.

**Independent Test**: Seed a journal with delivered, rejected and undelivered rows across multiple
projects; run purge for one project in dry-run and assert nothing changed but counts were reported;
run with confirmation and assert exactly that project's rows are gone in all three states and other
projects are untouched.

**Acceptance Scenarios**:

1. **Given** a multi-project journal, **When** `sync purge --project <slug-or-uuid>` runs without
   confirmation, **Then** it reports the exact number of rows it would remove, per state, and
   changes nothing.
2. **Given** the same, **When** it runs with explicit confirmation, **Then** only that project's
   rows are removed — including rejected rows `sync gc` cannot reach — and other projects' counts
   are unchanged.
3. **Given** a project slug that matches nothing, **When** purge runs, **Then** it reports zero
   matches and exits zero without error.
4. **Given** `sync purge --all`, **When** it runs with explicit confirmation, **Then** the journal
   is emptied and the command reports the total removed.

---

### User Story 4 - Machine-global arming is documented (Priority: P3)

An operator reading the sync docs learns that `SPEC_KITTY_ENABLE_SAAS_SYNC` and
`SPEC_KITTY_SAAS_URL` are process/shell-global with no project-scoped form, so a single `export`
arms every project that shell subsequently touches.

**Why this priority**: Documentation cannot prevent the breach — US1 does that — but the absent
warning is what led the operator to arm the shell in the first place, on our own advice.

**Independent Test**: The sync documentation states the machine-global scope of both variables and
their interaction with per-checkout consent.

**Acceptance Scenarios**:

1. **Given** the sync docs, **When** an operator reads the env-var reference, **Then** the
   machine-global scope of both variables is stated explicitly, alongside the per-project consent
   model that now governs delivery.

---

### Edge Cases

- **Event predates project-identity capture.** Rows enqueued before the enabler column exists carry
  identity only inside `data`. The backfill must decode them; any row whose identity is still
  unresolvable afterwards is non-consented and therefore never delivered (US1 scenario 2). It is
  retained, not deleted — see C-002.
- **Same repository re-`git init`ed.** A new `project_uuid` is a genuinely new project and starts
  non-consented. This matches the known limitation already documented on `saas#584`.
- **Consent revoked between selection and POST.** The predicate is evaluated at selection; a batch
  already in flight is not retroactively filtered. Revocation takes effect from the next selection.
  Explicitly acceptable; must be stated in the plan, not silently assumed.
- **Journal shared across two teamspaces for one producer.** `resolve_journal_path` keys on
  `user_id`/`team_slug`, so switching teams selects a different DB. Per-project consent is evaluated
  within whichever journal is active; the cross-project predicate must not assume one journal means
  one team.
- **Empty queue / no consented projects at all.** Drain must report "nothing to deliver" and exit
  zero, not refuse as if contaminated.
- **Backfill interrupted mid-run.** Must be idempotent and resumable; a partial backfill must never
  leave a row *appearing* consented.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Project identity is a first-class stored column | As a maintainer, I want `project_uuid` and `project_slug` persisted as additive indexed columns on the queue/journal rows so consent can be evaluated without decoding every payload. | High | Open |
| FR-002 | Backfill existing rows | As an operator, I want existing rows' project identity decoded from `data` into the new columns idempotently so the predicate covers 42-day-old history, not just new events. | High | Open |
| FR-003 | Selection filters by consent | As a consultant, I want event selection to exclude every event whose project is not consented so a drain cannot deliver another client's data. | High | Open |
| FR-004 | Unresolvable identity denies | As a consultant, I want an event with unresolvable project identity treated as non-consented so unknown provenance never ships. | High | Open |
| FR-005 | Routing gate fails closed | As a maintainer, I want `is_sync_enabled_for_checkout()` to deny when routing is unresolvable so an inability to determine consent is never read as consent. | High | Open |
| FR-006 | Cross-project drain refusal | As an operator, I want the drain to refuse, name the projects, and exit non-zero if a selected batch ever spans more than one project so a regression in FR-003 cannot silently leak. | High | Open |
| FR-007 | Per-project queue reporting | As an operator, I want `sync doctor` and `sync status` to report queue depth, oldest-event age and consent state per project so contamination is visible before draining. | High | Open |
| FR-008 | Purge by project | As an operator, I want `sync purge --project <slug-or-uuid>` with dry-run default and explicit confirmation to remove one project's rows in every state, including rejected rows `sync gc` cannot reach. | Medium | Open |
| FR-009 | Purge all | As an operator, I want `sync purge --all` behind explicit confirmation so I can empty a contaminated journal outright. | Medium | Open |
| FR-010 | Consent registry read | As a maintainer, I want the per-project consent predicate to derive from the existing `sync opt-in`/`sync opt-out` checkout-routing records so this mission adds no second, competing consent policy. | High | Open |
| FR-011 | Document machine-global env vars | As an operator, I want the sync docs to state that `SPEC_KITTY_ENABLE_SAAS_SYNC` and `SPEC_KITTY_SAAS_URL` are machine-global so I do not arm every project by exporting once. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No unconsented egress | Across the full test suite, zero events belonging to a non-consented project appear in any outbound payload. Proven by a recording fake ingress asserting on delivered `project_uuid` set cardinality == 1, not by mocking the predicate. | Security | High | Open |
| NFR-002 | Predicate cost does not scale with journal size | Selection must not decode all journal payloads per drain. With 100k rows across 20 projects, selecting one project's batch performs no full-table JSON decode (indexed column lookup only). | Performance | High | Open |
| NFR-003 | Backfill is idempotent and lossless | Running the backfill twice yields identical column values and identical row counts; no row is deleted or mutated outside the two new columns. | Reliability | High | Open |
| NFR-004 | Capture-first durability preserved | Event capture continues unconditionally at emit time; no event is dropped at write time by this mission. Delivery, not capture, is what consent gates. | Reliability | High | Open |
| NFR-005 | Purge is exact | Purge removes rows for the named project only; a differential row count over all other projects before/after is zero. | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Additive schema only | New columns must be nullable and additive. No existing column is renamed, retyped or dropped; an older CLI reading the same DB must still function. | Technical | High | Open |
| C-002 | Migration never deletes | The backfill must not delete or quarantine any row, including rows whose identity stays unresolvable. Deletion is the operator's explicit act via FR-008/FR-009. | Technical | High | Open |
| C-003 | Reuse existing primitives | Build on `queue.remove_project_events()` and the existing `sync opt-in`/`opt-out` routing records rather than introducing parallel purge or consent implementations; remove any path they supersede. | Technical | High | Open |
| C-004 | Server-side half is out of scope | Rejecting events whose project is not bound to the authenticated teamspace is `spec-kitty-saas#585` and must not be implemented here. This mission must not depend on that landing to be correct on its own. | Technical | High | Open |
| C-005 | Journal remains producer-scoped | Re-scoping the journal per repository root is a larger architectural change and is a **documented non-goal** of this mission: it would strand existing multi-week history and is not required for the confidentiality property, which FR-001+FR-003 secure within the shared store. Record the option and its rationale; do not build it. | Technical | Medium | Open |

### Key Entities

- **Stored sync event**: an enqueued event row. Gains additive `project_uuid` and `project_slug`
  columns; identity remains authoritative inside `data` and the columns are a derived, indexed
  projection of it.
- **Project consent record**: the existing per-checkout routing decision from
  `sync opt-in`/`opt-out`, read as a per-project predicate. Not a new store.
- **Selected batch**: the set of events chosen for one POST. Post-mission invariant: every member
  belongs to one consented project.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The incident reproduction — a journal of 6 projects with 1 consented — delivers events
  from exactly 1 project. The same test fails on `origin/main` at mission start, demonstrating it
  reproduces the real defect rather than asserting current behaviour.
- **SC-002**: `sync doctor` on a contaminated journal names every project present, with per-project
  event count and oldest-event age, and marks the non-consented ones. Zero SQLite hand-queries
  required to answer "whose data is in here?".
- **SC-003**: Every one of the four fail-closed paths denies: unresolvable routing (FR-005),
  unresolvable event identity (FR-004), non-consented project (FR-003), multi-project batch
  (FR-006). Each has a dedicated test asserting no network request was made.
- **SC-004**: `sync purge --project X` removes 100% of project X's rows across delivered, rejected
  and undelivered states, and 0% of any other project's rows.
- **SC-005**: Backfill run twice over a 10k-row multi-project journal produces byte-identical column
  values and an unchanged row count.
- **SC-006**: A live end-to-end drain from a two-project machine against a real hosted instance
  delivers only the consented project, verified by querying delivered events server-side and
  grouping by `project_slug` — the same query that exposed the incident.
