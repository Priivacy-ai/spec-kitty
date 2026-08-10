# Mission Specification: Per-project sync consent ledgers

**Mission Branch**: `per-project-sync-consent-ledgers-01KZNNZS`  
**Created**: 2026-08-10  
**Status**: Draft  
**Input**: Core issue Priivacy-ai/spec-kitty#3262 and SaaS incident Priivacy-ai/spec-kitty-saas#585 require explicit per-project hosted-sync opt-in, separate per-project ledgers, no default-on egress, safe migration from machine-global state, daemon/background enforcement, and evidence strong enough to close the 1,322-event contamination incident only after remediation disposition.

## Context

SaaS #585 proved that one opted-in checkout could drain events for unrelated local projects from a shared machine journal. Core #3262 records the product decision that hosted sync consent is a structural confidentiality boundary: consent must be explicit per project, not inferred from login, environment, shell, or a machine-global routing switch.

Prior #3030/#3167 work added consent primitives and retired one dead batch-drain path, but #3262 remains open because the product still needs a single decomposed implementation plan covering:

- per-project journal/ledger storage,
- migration out of shared machine state,
- explicit opt-in and opt-out,
- daemon/background delivery behavior,
- a global kill switch that can only deny egress,
- old-client/bypassed-gate defense,
- proof that two projects on one machine cannot select, transmit, or acknowledge each other’s events.

## User Scenarios & Testing

### User Story 1 - Non-consenting project cannot egress (Priority: P1)

As a consultant with multiple client repositories on one machine, I want enabling hosted sync in one project to leave every other project local-only unless I explicitly opt that project in.

**Why this priority**: This is the confidentiality boundary and the direct closure blocker for SaaS #585.

**Independent Test**: Create two local projects on the same machine with distinct project identities. Explicitly opt in only project A. Emit events in both projects, then run interactive sync and daemon/background delivery. The selected, transmitted, acknowledged, and retained remote-visible set contains project A only; project B remains unselected and unacknowledged.

**Acceptance Scenarios**:

1. **Given** project A is explicitly opted in and project B is not, **When** sync selection runs from project A, **Then** only project A’s ledger rows are selected.
2. **Given** project A is explicitly opted in and project B is not, **When** the background daemon drains available work, **Then** it cannot select or acknowledge project B events.
3. **Given** a legacy or patched caller bypasses an interactive command gate, **When** it attempts to send a project B event under project A consent, **Then** the delivery seam refuses before transmit and records no acknowledgement for project B.

---

### User Story 2 - Explicit per-project opt-in/out is understandable and reversible (Priority: P1)

As a user, I want a clear per-project command/state surface that shows whether this checkout is allowed to send hosted sync data, and I want opt-out to stop future delivery for that project.

**Why this priority**: Consent must be user-actioned and inspectable; an env var or login state is too broad to be the consent authority.

**Independent Test**: In a fresh checkout, verify hosted sync is denied by default even when the user is authenticated and the global rollout env var is enabled. Run explicit opt-in for that checkout and verify only that checkout becomes eligible. Run opt-out and verify new sends stop while local capture remains safe.

**Acceptance Scenarios**:

1. **Given** a fresh checkout with auth configured, **When** no per-project opt-in exists, **Then** hosted sync reports “not opted in” and sends nothing.
2. **Given** an opted-in checkout, **When** the user opts out, **Then** subsequent interactive and daemon delivery for that checkout is denied.
3. **Given** `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, **When** no project consent exists, **Then** the env var only opens the hidden/internal command surface and never grants project egress authority.

---

### User Story 3 - Existing shared journals migrate safely (Priority: P1)

As an existing internal user, I want historical shared machine journal state migrated so no unrelated project becomes silently admitted and no legitimate local history is lost.

**Why this priority**: A migration that blesses contaminated historical rows recreates the incident under a new data model.

**Independent Test**: Build a pre-migration machine-global journal with rows for multiple projects, including unknown or legacy identity rows. Run migration. Each project lands in a physically separate ledger with explicit consent state. Ambiguous or missing identity rows are retained locally but not eligible for hosted egress until resolved.

**Acceptance Scenarios**:

1. **Given** one pre-migration journal containing rows for projects A and B, **When** migration runs, **Then** project A and project B receive separate ledger stores.
2. **Given** a pre-migration row without a trustworthy project identity, **When** migration runs, **Then** it is quarantined/local-only and cannot be selected for hosted sync.
3. **Given** historical rows for a project without an explicit post-migration opt-in, **When** sync runs, **Then** those rows remain unsent until the project is explicitly opted in.

---

### User Story 4 - Operator evidence closes the incident deliberately (Priority: P2)

As an operator responsible for SaaS #585, I want closure evidence and remediation disposition before declaring the historical contamination resolved.

**Why this priority**: Shipping structural prevention is necessary but not sufficient; #585 also needs a decision on the already-delivered 1,322 events.

**Independent Test**: Produce a closure dossier that links the core shipping PR(s), tests, hosted/ingestion evidence, and an approved disposition for the 1,322-event contamination.

**Acceptance Scenarios**:

1. **Given** core prevention has shipped, **When** #585 closure is attempted, **Then** it remains open unless a remediation disposition for the 1,322 historical events is recorded.
2. **Given** a production or staging evidence run, **When** it validates two-project isolation, **Then** #585 can link that evidence as closure proof.

## Edge Cases

- A user is authenticated and `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set, but the current checkout has no consent record.
- Two repositories share a machine, shell, user account, SaaS account, or daemon process.
- A daemon started from one checkout discovers queued work for another checkout.
- A project is opted out while rows are queued or leases are in progress.
- Old pre-#3262 ledgers contain missing, conflicting, or stale `project_uuid` / `project_slug` identity.
- A legacy caller attempts to construct/send a batch directly after bypassing CLI consent checks.
- A global kill switch is disabled, then re-enabled, without changing any project consent records.
- A project is moved/renamed after opt-in.
- The local ledger is unreadable or partially migrated.

## Requirements

### Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Default denied | Hosted sync egress MUST be denied for every project until an explicit per-project opt-in record exists. | High | Open |
| FR-002 | Per-project consent authority | Consent MUST be keyed to a stable project identity and checkout/repo root, not to login, machine, shell, environment, or SaaS account alone. | High | Open |
| FR-003 | Per-project ledger isolation | Event journal, offline queue, sync state, leases, and acknowledgement state MUST be physically or logically isolated per project so one project cannot select another project’s rows. | High | Open |
| FR-004 | Selection predicate | Every hosted-sync selector MUST filter by the project consent authority before transmission. | High | Open |
| FR-005 | Acknowledgement predicate | A sender MUST NOT acknowledge, mark delivered, or purge rows for a project whose consent authority did not authorize that exact project. | High | Open |
| FR-006 | Explicit opt-in | Provide a user-facing command/API that records explicit opt-in for the current project and displays what project will be allowed to egress. | High | Open |
| FR-007 | Explicit opt-out | Provide a user-facing command/API that revokes hosted-sync eligibility for the current project and stops future interactive and background delivery. | High | Open |
| FR-008 | Kill switch is deny-only | `SPEC_KITTY_ENABLE_SAAS_SYNC` MAY remain as a global rollout/kill switch, but it MUST NOT grant egress consent; it may only hide/disable or deny hosted sync. | High | Open |
| FR-009 | Daemon enforcement | Background daemon startup, discovery, selection, transmission, retry, and acknowledgement MUST enforce the same per-project consent predicates as interactive sync. | High | Open |
| FR-010 | Safe legacy migration | Migration from shared machine-global state MUST split or map rows into per-project stores without silently admitting historical projects. | High | Open |
| FR-011 | Ambiguous legacy rows fail closed | Rows without trustworthy project identity MUST remain local-only or require explicit resolution before hosted egress. | High | Open |
| FR-012 | Old-client/bypass defense | Low-level delivery seams MUST refuse non-consenting project rows even if an old client or internal caller bypasses high-level command gates. | High | Open |
| FR-013 | Two-project proof | Tests MUST prove two projects on one machine cannot select, transmit, acknowledge, or purge each other’s events. | High | Open |
| FR-014 | Status/doctor visibility | `sync status` / `sync doctor` MUST expose per-project queue/consent state so cross-project backlog is visible before drain. | Medium | Open |
| FR-015 | Closure dossier | The mission MUST produce an operator-facing closure note for #3262/#585 including prevention evidence and the separate historical-remediation disposition requirement. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Fail-closed confidentiality | 100% of hosted egress paths covered by this mission must deny by default without explicit per-project consent. | Security | High | Open |
| NFR-002 | Multi-project isolation | The regression suite must include at least one real two-project-on-one-machine scenario covering selection, transmit, acknowledgement, and old-client/bypass attempts. | Security | High | Open |
| NFR-003 | Migration durability | Migration must be idempotent: rerunning it cannot duplicate, widen consent, or change previously classified local-only rows. | Reliability | High | Open |
| NFR-004 | No source loss | Migration must preserve all local rows, including refused/ambiguous rows, unless a user explicitly runs a purge/remediation command. | Reliability | High | Open |
| NFR-005 | Bounded status overhead | Per-project queue/consent reporting must complete within the existing sync status/doctor performance envelope for representative local journals. | Performance | Medium | Open |
| NFR-006 | Auditability | Opt-in, opt-out, migration classification, denied selection, and denied acknowledgement outcomes must leave local audit evidence suitable for #585 closure review. | Auditability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No default-on | No command, environment variable, config default, migration, daemon, or auth state may cause a project to egress without explicit per-project opt-in. | Product | High | Open |
| C-002 | No env-as-consent | `SPEC_KITTY_ENABLE_SAAS_SYNC` is not the consent authority and must not be repurposed as one. | Product | High | Open |
| C-003 | Existing stealth gate remains | Internal hosted surfaces that still require `SPEC_KITTY_ENABLE_SAAS_SYNC=1` may keep that rollout gate, but only as a coarse allow-surface/kill switch layered above project consent. | Technical | High | Open |
| C-004 | Historical incident not auto-closed | This mission may prevent new contamination but must not declare SaaS #585 closed until an approved disposition exists for the historical 1,322 delivered events. | Operational | High | Open |
| C-005 | Core before onboarding | Consent closure remains ahead of onboarding #751 → #729 → #727. This mission should not start onboarding work. | Planning | Medium | Open |
| C-006 | PR #3135 separate | Refresh/repair core PR #3135 separately; this mission must not merge that PR’s failing-check state into the consent redesign branch. | Planning | Medium | Open |

### Key Entities

- **Project Consent Record**: Durable local record that a specific project/checkout identity has explicitly opted in or out of hosted sync.
- **Project Ledger**: Per-project journal/offline queue/sync-state store containing only events for one project identity.
- **Global Kill Switch**: Coarse machine/process-level control that can disable hosted sync surfaces or deny all sends but never grants project consent.
- **Migration Classification**: Per-row/project result created while moving from the shared machine-global ledger to per-project ledgers.
- **Delivery Authorization Decision**: The exact per-event/per-project result used by selectors, senders, and acknowledgers before observable hosted egress.

## Success Criteria

- **SC-001**: A fresh checkout with auth and `SPEC_KITTY_ENABLE_SAAS_SYNC=1` sends zero hosted events until explicit per-project opt-in.
- **SC-002**: In a two-project local fixture, opting in project A sends and acknowledges only project A; project B remains unselected, untransmitted, unacknowledged, and unpurged.
- **SC-003**: Background daemon delivery produces the same project isolation result as interactive sync in the two-project fixture.
- **SC-004**: A legacy/bypassed delivery path attempting to send project B under project A consent is refused before transmit and records no acknowledgement.
- **SC-005**: Migration from a mixed shared journal creates per-project ledger state and leaves ambiguous/missing-identity rows local-only.
- **SC-006**: Opt-out stops future delivery for the project without deleting local history.
- **SC-007**: `sync status` or `sync doctor` exposes per-project queue and consent state before drain.
- **SC-008**: The mission’s closure artifact links core implementation PR evidence, relevant tests, SaaS #585 linkage, and states that the 1,322 historical delivered events require a separate approved remediation disposition before #585 can close.
