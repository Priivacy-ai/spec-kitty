# Mission Specification: Event sync — preserve local events & track per-target drains

**Mission Branch**: `mission/event-sync-retention-delivery`
**Created**: 2026-06-25
**Status**: Draft
**Input**: [spec-kitty#2124](https://github.com/Priivacy-ai/spec-kitty/issues/2124) — separate local event *retention* from *delivery* state so the CLI's sync queue stops destroying events on successful upload, and operators can re-drain the same events to transient SaaS targets. Folds in Stijn's `EventSyncConfig` operator framing and the separate-domain requirement (design synthesis: `architecture/3.x/research/2026-06-25-event-sync-retention-delivery-synthesis.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Replay the same events to a fresh target (Priority: P1)

An operator drains local event data to an Upsun PR preview environment, then destroys that environment and stands up a new one at a different URL. They re-run `sync now` against the new environment and the **same local events are delivered again** — without copying SQLite files by hand.

**Why this priority**: This is the reason the issue exists. Today a terminal success deletes the local row (`process_batch_results`, `src/specify_cli/sync/queue.py:1693`), so the second drain is impossible. Without this, transient preview environments are unusable for replay-heavy testing — which blocks exposing Teamspace to users.

**Independent Test**: Produce N events; `sync server <A>` + `sync now`; assert delivered to A and **still present locally**; `sync server <B>` + `sync now`; assert the same N events delivered to B. No manual DB copy.

**Acceptance Scenarios**:

1. **Given** N retained events all delivered to target A, **When** the operator switches to target B and runs `sync now`, **Then** all N events are delivered to B and remain locally retained.
2. **Given** an event already delivered to target A, **When** `sync now` runs again against A, **Then** the dispatcher skips it (terminal successful delivery recorded) and does not re-post.
3. **Given** a successful upload, **When** it completes, **Then** the local payload is **not deleted** — only a ledger row is written/updated.

---

### User Story 2 - Choose where events go (`EventSyncConfig`) (Priority: P2)

An operator (or repository config) selects how event sync behaves: send to Teamspace, send to their own receiver, retain locally only, or opt out entirely.

**Why this priority**: Robert's mechanism needs an operator-facing dial (Stijn's `EventSyncConfig`). It also unblocks people who don't want SaaS delivery at all. Modeled as two orthogonal axes — **retention** (journal on/off) × **delivery** (none / Teamspace / external-receiver) — with the named modes as presets.

**Independent Test**: For each mode, produce events and assert observable on-disk + network state matches the mode (e.g. `LOCAL_RETENTION` journals but never posts; `OPT_OUT` neither journals nor posts).

**Acceptance Scenarios**:

1. **Given** `TEAMSPACE` mode, **When** events are produced and `sync now` runs, **Then** events are journaled and delivered to the configured Teamspace target.
2. **Given** `LOCAL_RETENTION` mode, **When** events are produced, **Then** they are journaled and no delivery is attempted; a target can later be set and `sync now` drains them.
3. **Given** `EXTERNAL_RECEIVER` mode with a configured endpoint, **When** `sync now` runs, **Then** events are delivered to that endpoint via the same ledger machinery.
4. **Given** `OPT_OUT`/`TRASH` mode, **When** events are produced, **Then** nothing is journaled and nothing is sent.

---

### User Story 3 - Test against a stub receiver (no Teamspace key) (Priority: P3)

A contributor runs the suite (including in a fork CI) against a local stub receiver that accepts and records events, with no dependency on a real Teamspace or the `teamspace_key` in core.

**Why this priority**: Stijn's concrete pain — the `teamspace_key` dependency keeps breaking fork CI. With `EXTERNAL_RECEIVER` generalizing the target, the stub is just a localhost sink, so this falls out of US2 rather than being a special case.

**Independent Test**: Point `EXTERNAL_RECEIVER` at an in-process/localhost stub; run a sync; assert the stub received the expected events and the ledger recorded delivery — with no Teamspace credentials present.

**Acceptance Scenarios**:

1. **Given** a stub receiver and no Teamspace credentials, **When** `sync now` runs, **Then** events are delivered to the stub and the ledger records terminal success.

---

### User Story 4 - Inspect retention and clean up explicitly (Priority: P3)

An operator can see how much is retained and how much is delivered to the current vs previous targets, and can archive/GC payloads only by explicit command.

**Why this priority**: Append-only retention must stay honest and inspectable, and must not grow unbounded silently. Destructive cleanup must be explicit.

**Independent Test**: After mixed deliveries, assert `sync status` reports retained count and per-target delivery counts separately; assert `sync gc`/`sync archive` only removes/archives under explicit invocation and preserves ledger history.

**Acceptance Scenarios**:

1. **Given** 124 retained events delivered to a previous target but 0 to the current one, **When** `sync status` runs, **Then** it reports retained=124, current-target delivered=0, previous-target delivered=124, and the oldest retained timestamp.
2. **Given** retained payloads, **When** the operator runs `sync gc`/`sync archive`, **Then** payloads are archived/purged per policy while delivery-ledger history is preserved.
3. **Given** no explicit cleanup command, **When** any `sync now` completes, **Then** no source events are deleted.

### Edge Cases

- **Target reset under a stable URL**: a preview env is wiped but keeps its URL. URL+scope identity would report "fully delivered" while the server has nothing. The system records server-advertised deployment identity and uses a *change* in it to detect the reset and offer a re-drain — without forking target identity on every redeploy (Upsun re-stamps `deployment_id` per push).
- **Coalescing after delivery**: a new event arrives that would coalesce into an event already delivered to some target. The system must not mutate a delivered event (that would make the ledger lie); it coalesces only among undelivered events and otherwise records a new event, marking the prior superseded.
- **Migration with no recoverable history**: events already delivered-and-deleted under the old destructive queue cannot be reconstructed; migration preserves only currently-queued payloads and says so.
- **Multiple pre-existing scoped queue DBs** (`server|user|team`) must consolidate into one producer-scoped journal without losing queued payloads.
- **Content rejection vs transient failure**: a per-event content rejection records a failure state without losing the payload; a batch-level transient failure (401/403/5xx/timeout) updates attempt metadata without poisoning per-event retry counts.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Non-destructive success | As an operator, I want a successful upload to update delivery state, not delete the event, so the payload survives for replay. | High | Open |
| FR-002 | Per-target delivery ledger | As an operator, I want per-event/per-target delivery state so the system knows whether event X reached target Y. | High | Open |
| FR-003 | Target-independent journal | As an operator, I want events retained independent of any target so I can deliver them to a target chosen later. | High | Open |
| FR-004 | Dispatcher selects undelivered-for-target | As an operator, I want `sync now` to send only events lacking terminal successful delivery for the active target. | High | Open |
| FR-005 | Re-drain to a new target | As an operator, I want to change `sync server <url>` and re-deliver the same retained events to the new target. | High | Open |
| FR-006 | `EventSyncConfig` modes | As an operator, I want to select TEAMSPACE / EXTERNAL_RECEIVER / LOCAL_RETENTION / OPT_OUT(TRASH). | Medium | Open |
| FR-007 | External receiver target | As an operator, I want to deliver to my own endpoint via the same ledger machinery. | Medium | Open |
| FR-008 | Stub receiver for tests | As a contributor, I want a local stub receiver so tests/fork-CI need no real Teamspace or `teamspace_key`. | Medium | Open |
| FR-009 | `sync status` retention/ delivery split | As an operator, I want retained count and per-target delivery counts reported separately. | Medium | Open |
| FR-010 | Explicit `sync gc`/`sync archive` | As an operator, I want destructive cleanup only by explicit command, preserving ledger history. | Medium | Open |
| FR-011 | Coalescing honesty | As an operator, I want coalescing to never mutate an already-delivered event. | High | Open |
| FR-012 | Target-reset detection | As an operator, I want a notice/offer to re-drain when a stable URL's deployment identity changes. | Low | Open |
| FR-013 | Migration of existing queues | As an operator, I want existing scoped queue DBs migrated into the journal without losing queued payloads. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Observable-state tests | Tests assert observable CLI output and on-disk/ledger state, not internal call order. | Quality | High | Open |
| NFR-002 | Coverage of delivery outcomes | Tests cover success, duplicate, pending, transient failure, rejection, and explicit GC/archive. | Quality | High | Open |
| NFR-003 | Idempotent re-delivery | Re-draining already-delivered event IDs to a target yields `duplicate` handling with no data corruption; event IDs are unchanged. | Reliability | High | Open |
| NFR-004 | Bounded growth visibility | `sync status` surfaces journal size; GC is suggested once the journal is large AND fully delivered to all known targets. | Reliability | Medium | Open |
| NFR-005 | Migration safety | Migration is atomic per DB and never loses currently-queued payloads. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Separate core domain | Modeled as a separate domain in core — `events/` (journal) + `delivery/` (target registry + ledger + dispatcher) + `EventSyncConfig` policy — not woven into the existing `queue.py`. (Stijn, hard requirement.) | Technical | High | Open |
| C-002 | Identity = URL + scope | Delivery target identity is canonical-URL + user/team scope (`UNIQUE(url_hash, team_slug, user_email)`); deployment metadata is recorded as provenance/reset-detection, never an identity key. | Technical | High | Open |
| C-003 | Single active target (MVP) | MVP delivers to one operator-selected active target; no automatic fan-out. The ledger's per-event/per-target shape must be able to grow into many-targets without a schema break. | Technical | High | Open |
| C-004 | SaaS health metadata is a cross-repo dependency | CLI ships with URL-only identity first; consuming `/api/v1/sync/health/` deployment metadata is sequenced after the SaaS exposes it (separate `spec-kitty-saas` follow-on). | Technical | Medium | Open |
| C-005 | No event-ID changes | This mission does not change event IDs and does not require SaaS to retain events forever or replicate cross-environment. | Technical | Medium | Open |

### Key Entities

- **Event Journal**: append-only local store of event payloads (`event_id`, type, payload, timestamps, coalesce key, archived marker). Producer-scoped (`user|team`/repo), **not** server-scoped. Does not know delivery state.
- **Delivery Target**: one endpoint identity — canonical URL + url_hash + user/team scope; optional recorded deployment metadata (`server_instance_id`, `deployment_id`, `environment_name`, `git_sha`).
- **Delivery Ledger**: per-event/per-target row — status, attempt count, timestamps, server drain state, last HTTP status/error/response. Answers "was X delivered to Y, when, with what result?"
- **EventSyncConfig**: operator/repository policy selecting retention (on/off) × delivery (none / Teamspace / external-receiver), exposed as the four named modes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given two distinct SaaS endpoints, the same local event data is delivered to endpoint A and then endpoint B with zero manual SQLite copying.
- **SC-002**: After a successful sync, 100% of local event payloads remain inspectable until an explicit archive/GC command runs.
- **SC-003**: `sync status` reports retained event count and current-target delivery count as distinct numbers.
- **SC-004**: Every terminal successful delivery records endpoint URL and user/team scope (and deployment identity when SaaS health exposes it).
- **SC-005**: The full suite — including fork CI — passes against a stub receiver with no Teamspace credentials present.
- **SC-006**: Migrating an existing scoped queue DB preserves 100% of currently-queued payloads and loses none.
