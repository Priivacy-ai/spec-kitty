# Mission Specification: Per-Project Sync Consent Ledgers

**Mission Branch**: `feat/per-project-sync-consent`  
**Created**: 2026-08-09  
**Status**: Draft  
**Input**: Implement Priivacy-ai/spec-kitty#3262 as the CLI half of the consent-incident program: explicit per-project opt-in, physically separate project sync state, no default-on inheritance, and the global environment setting only as a deny-only kill switch. Consume the SaaS admission boundary tracked by Priivacy-ai/spec-kitty-saas#585. Historical disposition of the 1,322 already-ingested events remains a separate Human-in-Charge decision.

## Intent and scope

Hosted sync consent belongs to one immutable project identity, not to a login, service URL, checkout path, repository slug, remote URL, active target, or machine-wide switch. Each canonical `project_uuid` owns a physically isolated sync store containing its consent decision, event journal, delivery results and retries, body/offline queue, target binding, and migration/cutover metadata. No live operation for one project may open or mutate another project's store.

Local project-isolated capture is allowed without hosted consent so that offline durability is not coupled to commercial-service use. Hosted egress remains default-denied and requires all of: the global kill switch permits egress, the current project has an explicit local grant, its target is ready, and the SaaS admission generation is current. This deliberately supersedes the shared-store capture restriction recorded by predecessor mission #3030 while preserving #3030's consent-bearing batches, final transmit checks, SQL identity checks, and terminal refusal handling as defense in depth.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep every project's sync state physically isolated (Priority: P1)

As a developer working on multiple projects, I want each canonical project UUID to own a separate sync store, so that an operation for one project cannot observe, acknowledge, retry, migrate, purge, or deliver another project's data even if filtering is defective.

**Why this priority**: Shared journals and delivery ledgers created the structural blast radius behind the consent incident; query predicates alone are containment, not isolation.

**Independent Test**: Create projects A and B on one machine, including identical slugs with different UUIDs. Trap all store opens while capturing, draining, acknowledging, migrating, and opting out A. Only A's deterministic store paths are touched, and an unfiltered query of A's databases cannot return B.

**Acceptance Scenarios**:

1. **Given** projects A and B with events on one machine, **When** their sync contexts are resolved, **Then** journal, delivery, body/offline, consent, target, and migration state resolve to distinct UUID-owned stores.
2. **Given** an operation scoped to A, **When** it captures, selects, sends, acknowledges, retries, migrates, diagnoses, or purges, **Then** it performs zero opens, locks, reads, writes, or deletes against B's stores.
3. **Given** the same repository slug but different project UUIDs, **When** stores are resolved, **Then** the projects remain distinct and no slug collision can merge their state.
4. **Given** two legitimate worktrees that share the same canonical project UUID, **When** they capture locally on the same machine, **Then** they use the same project-owned store and the same consent decision with safe concurrency.

---

### User Story 2 - Opt in explicitly without implicit inheritance (Priority: P1)

As a project owner, I want one clear project-scoped opt-in action, so that neither another checkout nor global configuration can silently enable hosted sync.

**Why this priority**: Consent must be attributable, explicit, and absent by default.

**Independent Test**: Combine truthy environment settings, login, a configured URL, route metadata, a repo-slug default, a path record, and an old UUID cache without running the new opt-in. The project remains denied. Run opt-in once and exactly one versioned project decision is recorded, even while offline or while the kill switch is off.

**Acceptance Scenarios**:

1. **Given** a project with no new-format decision, **When** the user logs in, configures `https://app.spec-kitty.ai`, enables the global environment setting, or shares a remote with a consented project, **Then** the project remains denied.
2. **Given** the global kill switch is off or the network is unavailable, **When** the user explicitly opts in, **Then** the local project grant is recorded and remote admission is reported as pending rather than discarding the decision.
3. **Given** an explicitly consented project, **When** the global kill switch is disabled, **Then** no egress occurs but the project decision remains recorded.
4. **Given** a fresh clone or re-initialized project with the same remote and a new UUID, **When** it starts, **Then** it is denied and receives a separate store.
5. **Given** only a legacy granting record, **When** the new resolver evaluates consent, **Then** it requires explicit re-consent and never promotes that record automatically.

---

### User Story 3 - Stop egress predictably on opt-out (Priority: P1)

As a project owner, I want opt-out to be an immediate local barrier with visible remote-revocation status, so that no local sender can race my decision and offline failure cannot be mistaken for server acknowledgement.

**Why this priority**: Revocable consent requires a precise concurrency boundary across interactive, daemon, WebSocket, body, history, and tracker-hosted senders.

**Independent Test**: Pause each sender after selection but before transport, run opt-out, then release it. After opt-out returns, none begins a network write or records success for that project; another consented project continues. If SaaS is unreachable, the CLI reports remote revocation pending and retries only the revocation control action, never event delivery.

**Acceptance Scenarios**:

1. **Given** a selected project batch, **When** opt-out increments the local consent generation before transport starts, **Then** the stale batch is refused locally and not acknowledged as delivered.
2. **Given** an active daemon outside every checkout, **When** project A opts out, **Then** the daemon stops opening or draining A while continuing consented project B.
3. **Given** SaaS is reachable, **When** opt-out requests remote revocation, **Then** the CLI records the acknowledged server generation and reports complete revocation.
4. **Given** SaaS is unreachable, **When** opt-out completes locally, **Then** local egress is stopped, remote revocation is visibly pending, and no claim of server-side completion is made.
5. **Given** the user later opts in again, **When** a new generation is admitted, **Then** stale batches and purged/terminal rows are not silently resurrected.

---

### User Story 4 - Migrate shared legacy state without granting consent (Priority: P1)

As an existing user, I want legacy shared state partitioned safely into project-owned stores, so that upgrading neither loses delivery history nor manufactures consent.

**Why this priority**: The current shared journal, delivery ledger, and offline/body queue contain mixed-project state and cannot remain on a live delivery path.

**Independent Test**: Seed a mixed shared store with A/B events, acknowledgements, retries, terminal refusals, malformed identities, and an injected interruption at each phase. The migration is previewable, crash-safe, repeatable, preserves exact identifiable row sets and status, leaves unknown rows in non-deliverable quarantine, and cuts live readers over exclusively to project stores.

**Acceptance Scenarios**:

1. **Given** identifiable legacy rows, **When** migration runs, **Then** each row and its delivery/body history move only to the store named by its canonical UUID with IDs and status preserved.
2. **Given** missing, malformed, conflicting, nil, or identity-less rows, **When** migration runs, **Then** they remain in a named local quarantine that no live sender can drain.
3. **Given** legacy refusals and grants, **When** consent records are migrated, **Then** refusals remain refusals while grants require a new explicit opt-in.
4. **Given** an interruption or rerun, **When** migration resumes, **Then** it neither duplicates nor redelivers rows and reports verifiable before/after identities, counts, and hashes.
5. **Given** cutover is complete, **When** any live capture or delivery path runs, **Then** it cannot open the shared legacy journal, ledger, or offline queue; those remain diagnostic/purge-only.
6. **Given** project A invokes opt-in, **When** migration is still needed, **Then** A's action cannot inspect, assign, delete, acknowledge, or migrate B's rows as a side effect.

---

### User Story 5 - Use one project context across every sender (Priority: P2)

As a maintainer, I want all hosted senders to carry one immutable project sync context, so that current working directory, daemon scope, active target, or independently paired stores cannot redirect data.

**Why this priority**: The application has multiple transports and background drains; closing only `sync now` would leave alternate routes around consent.

**Independent Test**: For each sender, set the working directory and active target to project B while the envelope/task belongs to A. The decision, store, target, admission, and transport all follow A's canonical context, or the operation fails before network I/O.

**Acceptance Scenarios**:

1. **Given** direct dispatch, emitter WebSocket, daemon publish, event relay, body drain, final sync, reconnect flush, history import, tracker-hosted, and generic SaaS paths, **When** they attempt egress, **Then** each requires a matching immutable project context and current consent generation.
2. **Given** a journal from A and delivery ledger or target from B, **When** a caller tries to construct a live delivery operation, **Then** it fails before selection or network I/O.
3. **Given** the global daemon runs outside a checkout, **When** it enumerates project stores, **Then** its discovery index is non-authoritative and it re-reads each project's own consent before every drain tick.
4. **Given** target configuration changes, **When** a project next drains, **Then** target readiness is evaluated separately from consent and historical rows are not automatically redrained.

---

### User Story 6 - Interoperate with SaaS admission and terminal refusal (Priority: P2)

As a user of hosted sync, I want the CLI to establish and use the SaaS project's admission generation and understand stable refusal, so that local consent cannot be confused with server authorization.

**Why this priority**: Core recurrence prevention must compose with the independent SaaS pre-write boundary.

**Independent Test**: Run a real CLI-built mixed-project batch against the SaaS contract. Only locally consented, remotely admitted A is sent and persisted; unadmitted B is refused as `project_not_admitted` and parked terminally without retry.

**Acceptance Scenarios**:

1. **Given** a recorded local opt-in and valid target, **When** admission is requested, **Then** the client stores the returned opaque server generation without treating the event channel as admission.
2. **Given** admission is pending or refused, **When** delivery runs, **Then** no event egress occurs and diagnostics name the required operator action.
3. **Given** SaaS returns `project_not_admitted`, **When** the delivery result is recorded, **Then** the event is parked terminally and not retried as transient.
4. **Given** tracker-specific Channel 2 permission is granted, **When** hosted-service consent is absent, **Then** tracker permission cannot grant or substitute for project sync consent.

### Edge Cases

- Same slug with different UUIDs, renamed repositories, symlinked/case-variant paths, and remote URL aliases never affect store or consent identity.
- Braced, dashless, uppercase, nil, missing, or malformed UUIDs are canonicalized once or rejected; they cannot create colliding stores.
- Storage tokens are deterministic ASCII on Linux, macOS, and Windows even when display names contain accented Latin or other non-ASCII characters.
- Corrupt, locked, partially migrated, or schema-incompatible stores fail closed and preserve source evidence.
- Concurrent worktrees sharing a UUID serialize migrations and consent-generation updates without losing locally captured events.
- An event may be captured locally before opt-in, but it cannot be selected or transmitted until current local consent, target readiness, kill-switch permission, and server admission all agree.
- Disabling the kill switch never deletes the local grant or queue; enabling it never grants a project.
- Changing active target never makes another project's store eligible and never triggers implicit historical redelivery.
- Re-opt-in behavior preserves terminal refusals, purges, and explicit user choices; it does not manufacture a retry backlog.
- Unknown legacy rows remain local and non-deliverable until a separate explicit Human-in-Charge disposition.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Canonical project identity | All sync storage, consent, routing, and delivery authority shall be keyed by one canonical immutable `project_uuid`. | High | Open |
| FR-002 | ProjectSyncStore boundary | Each project shall own physically separate consent, journal, delivery, body/offline, target, and migration state; no live project operation may open another project's store. | High | Open |
| FR-003 | One consent authority | One versioned project-owned decision shall be the only local grant authority; path, slug, remote, login, URL, environment, target, store presence, and machine indexes shall never grant. | High | Open |
| FR-004 | Explicit offline-capable opt-in | The named opt-in action shall record an attributable project grant even when offline or while the global kill switch is disabled, then report remote admission as active, pending, or refused. | High | Open |
| FR-005 | Deny-only kill switch | `SPEC_KITTY_ENABLE_SAAS_SYNC` shall only suppress egress; no value shall create, copy, revive, or delete a project grant. | High | Open |
| FR-006 | Capture/egress separation | Project-isolated local capture may occur without hosted consent, while selection and every final transport require current project consent and matching project context. | High | Open |
| FR-007 | Separate target binding | Project target configuration shall be stored and evaluated separately from consent and shall never grant consent or select another project's data. | High | Open |
| FR-008 | Local opt-out barrier | Opt-out shall change the project generation so that, after the command returns, no new HTTP, WebSocket, body, history, tracker-hosted, daemon, relay, reconnect, or final-sync write can begin for that project. | High | Open |
| FR-009 | Remote revocation truth | Opt-out shall attempt or queue SaaS revocation and distinguish acknowledged server revocation from locally complete but remotely pending state. | High | Open |
| FR-010 | Sender-context integrity | Every live sender shall consume one immutable project context whose UUID, store, consent generation, target, and server admission agree; mismatches fail before network I/O. | High | Open |
| FR-011 | Daemon isolation | Background discovery may enumerate project stores but shall re-read project-owned consent per tick and never use current working directory or a machine index as granting authority. | High | Open |
| FR-012 | Legacy partition migration | A previewable, idempotent, crash-safe migration shall partition identifiable shared journal, delivery, and offline/body state by canonical UUID while preserving event identities and delivery status. | High | Open |
| FR-013 | Legacy quarantine | Missing, malformed, conflicting, and identity-less legacy rows shall remain in a named non-deliverable local quarantine with diagnostics and no synthetic project assignment. | High | Open |
| FR-014 | No legacy grant promotion | New-format refusals may be derived from legacy refusals, but every legacy grant lacking current explicit provenance shall require re-consent. | High | Open |
| FR-015 | Exclusive live cutover | After migration, live capture and delivery shall read only project stores; shared stores shall be diagnostic/purge-only with no dual-read delivery fallback. | High | Open |
| FR-016 | Stable SaaS refusal | The CLI shall consume the canonical SaaS `project_not_admitted` terminal refusal and park affected events without transient retry. | High | Open |
| FR-017 | Structural diagnostics | Diagnostics shall report store identity, local decision, kill-switch state, target readiness, server-admission state, pending revocation, migration/quarantine state, and the blocking reason without secrets or payloads. | Medium | Open |
| FR-018 | Predecessor preservation | Consent-bearing batches, final transmit rechecks, project SQL identity predicates, purge, and terminal-refusal controls from #3030 shall remain as independent defense in depth. | High | Open |
| FR-019 | Cross-repository proof | The final acceptance gate shall run a real six-project CLI↔SaaS scenario with one admitted project and prove exact sent identities plus absence of foreign markers and hosted rows. | High | Open |
| FR-020 | Incident evidence separation | Core #3262 closure evidence shall not claim SaaS #585 is closed; historical disposition remains a separate Human-in-Charge gate. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Physical isolation proof | Store-open instrumentation shall observe zero cross-project file opens, locks, reads, writes, acknowledgements, schema operations, or deletes across the required A/B matrix. | Privacy | High | Open |
| NFR-002 | Migration fidelity | For identifiable legacy data, before/after event-ID sets, delivery states, attempts, and content hashes shall match exactly; rerunning after every injected phase failure shall add zero duplicates and zero redeliveries. | Reliability | High | Open |
| NFR-003 | Revocation race proof | At least one barrier-controlled test per live sender class shall prove zero network writes beginning after opt-out returns, while an unreleased positive control delivers successfully. | Concurrency | High | Open |
| NFR-004 | Mutation strength | Mutants that restore a shared store, grant from environment or repo defaults, remove the final consent check, or cross-pair project context shall each make named acceptance tests fail. | Test integrity | High | Open |
| NFR-005 | Cross-platform identity | Project store resolution shall produce deterministic ASCII-safe paths and pass the identity matrix on Linux, macOS, and Windows, including accented and non-ASCII display names. | Portability | High | Open |
| NFR-006 | Performance | With 100 discovered project stores, a daemon eligibility scan shall complete within 500 ms p95 without opening stores for projects known locally to be denied or revoked. | Performance | Medium | Open |
| NFR-007 | Credential and payload safety | Diagnostics, migration reports, logs, fixtures, and errors shall expose zero access tokens and zero raw event bodies outside their owning project store. | Security | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Supersede shared-store non-goal | This mission explicitly supersedes predecessor #3030 C-005/C-006 where they preserve shared live stores or forbid project-owned local capture; the reason and replacement boundary must be recorded in an ADR/Decision Moment. | Architecture | High | Open |
| C-002 | Preserve #3030 safety | Default denial, consent-bearing selection, final transmit checks, identity filtering, terminal parking, and purge behavior remain mandatory defense in depth. | Compatibility | High | Open |
| C-003 | No implicit consent | Repo slug, checkout path, remote URL, login, configured host, target readiness, daemon startup, or environment variables shall never create consent. | Privacy | High | Open |
| C-004 | Canonical hosted contract | Admission and refusal behavior shall consume `../spec-kitty-saas/contracts/cli-saas-current-api.yaml`; core shall not define an incompatible parallel contract. | Architecture | High | Open |
| C-005 | Tracker Channel 2 separate | Core #3108/PR #3135 remains separate; its tracker permission may narrow egress but can never grant hosted-service consent. | Scope | High | Open |
| C-006 | Historical events excluded | This mission shall not inspect, delete, move, reassign, or decide the disposition of the 1,322 historical SaaS events. | Operational | High | Open |
| C-007 | No production mutation | Implementation, testing, review, and retrospective shall use local/test environments and shall not alter production configuration, data, consent, or admission state. | Safety | High | Open |
| C-008 | No silent compatibility fallback | Old shared stores and legacy consent records may support diagnosis, explicit migration, or purge only; they shall never silently re-enter live delivery. | Architecture | High | Open |

### Key Entities

- **Project sync store**: The complete local hosted-sync boundary for one canonical UUID, holding consent, target, journal, delivery, body/offline, and migration state.
- **Project sync context**: An immutable operation-scoped binding of project UUID, store identity, local consent generation, target binding, and SaaS admission generation.
- **Project consent decision**: A versioned, attributable local grant or refusal written only by an explicit project action.
- **Target binding**: The hosted destination for a project; necessary for delivery but never a consent source.
- **SaaS admission**: The independent server authorization for `(team, project_uuid)`, represented locally by an opaque current generation and state.
- **Legacy quarantine**: A non-deliverable store for rows that cannot be attributed safely during migration.
- **Discovery index**: Optional non-authoritative metadata used to find project stores; it can never grant consent or supply the decision itself.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For two projects on one machine, every capture, delivery, acknowledgement, migration, diagnostic, purge, and opt-out test observes zero access to the other project's sync stores.
- **SC-002**: Every combination of login, host configuration, target, repo/path legacy records, old UUID cache, daemon state, and global environment setting leaves an unconsented project denied; only the explicit new opt-in creates a grant.
- **SC-003**: Mixed-store migration preserves 100% of attributable event identities and delivery states, quarantines 100% of unknown identities, and remains idempotent after injected interruption at every phase.
- **SC-004**: After opt-out returns, barrier-controlled coverage across all live sender classes observes zero new network writes or success acknowledgements for that project while another project continues.
- **SC-005**: The global flag suppresses 100% of hosted egress when disabled and grants zero projects when enabled.
- **SC-006**: A six-project cross-repository test sends and persists only the one locally consented and remotely admitted project, with exact request-body identity evidence and no foreign marker leakage.
- **SC-007**: Each required shared-store, implicit-grant, missing-final-gate, and cross-context mutant causes a named test to fail.
- **SC-008**: Core #3262 has implementation, contract, test, and review evidence, while SaaS #585 remains explicitly gated on the Human-in-Charge's historical-event disposition.

## Dependencies and assumptions

- Every participating repository has a canonical immutable `project_uuid`; two worktrees with that same UUID represent one logical project and share one machine-local project store.
- The companion SaaS mission `project-sync-admission-boundary-01KZKMQ7` publishes the authoritative admission and `project_not_admitted` contract before core compatibility work is finalized.
- Predecessor #3030 remains the defense-in-depth baseline except where this mission explicitly supersedes its shared-store and capture-coupling decisions.
- The global environment setting remains available for emergency deny-only control, but users can record project consent while it is disabled.
- Cross-repository acceptance may add or update the end-to-end-testing repository if the existing harness cannot prove the six-project matrix.
- Historical #585 remediation is unavailable to automation until the Human-in-Charge records a disposition; it does not block core recurrence prevention but does block closing the SaaS incident.

## Out of Scope

- Deleting, moving, inspecting, or approving retention of the 1,322 historical SaaS events.
- Using repository slug, checkout path, remote URL, or current working directory as a security identity.
- Automatically granting a fresh clone or new UUID because another checkout is consented.
- General tracker connector redesign or completion of core #3108/PR #3135.
- Restoring retired shared-queue senders or shared-store delivery compatibility.
- Automatically redraining historical rows when a target changes or a project opts in again.
- Production deployment or production data/configuration mutation.
