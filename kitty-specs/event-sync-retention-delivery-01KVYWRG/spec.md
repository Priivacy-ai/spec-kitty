# Mission Specification: Event sync — preserve local events & track per-target drains

**Mission Branch**: `mission/event-sync-retention-delivery`
**Created**: 2026-06-25
**Status**: Draft
**Input**: [spec-kitty#2124](https://github.com/Priivacy-ai/spec-kitty/issues/2124) — separate local event *retention* from *delivery* state so the CLI's sync queue stops destroying events on successful upload, and operators can re-drain the same events to transient SaaS targets. Folds in Stijn's `EventSyncConfig` operator framing, the separate-domain requirement, and the design synthesis from [PR #2130](https://github.com/Priivacy-ai/spec-kitty/pull/2130).

**Linked issue review**: #2146 is in-scope as the target-authority prerequisite; #2144 supplies the capture-before-drain invariant this design must not violate; #1800/#1666/#1619 are parent architecture context; #2165 is acknowledged as docs-reorg context but does not move this mission's artifacts.

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

**Independent Test**: For each mode, produce events and assert observable on-disk + network state matches the mode (e.g. `LOCAL_RETENTION` journals but never posts; `OPT_OUT` neither journals nor posts for local-only/discardable families, and refuses or records audit evidence for Teamspace-bound families).

**Acceptance Scenarios**:

1. **Given** `TEAMSPACE` mode, **When** events are produced and `sync now` runs, **Then** events are journaled and delivered to the configured Teamspace target.
2. **Given** `LOCAL_RETENTION` mode, **When** events are produced, **Then** they are journaled and no delivery is attempted; a target can later be set and `sync now` drains them.
3. **Given** `EXTERNAL_RECEIVER` mode with a configured endpoint, **When** `sync now` runs, **Then** events are delivered to that endpoint via the same ledger machinery.
4. **Given** `OPT_OUT`/`TRASH` mode for an event family classified local-only or explicitly discardable, **When** events are produced, **Then** nothing is journaled and nothing is sent.
5. **Given** a Teamspace-bound event family, **When** a user/repo policy would silently discard it, **Then** the system either writes approved durable evidence (SQLite/git audit/replay source) or refuses the policy with an audit-visible reason.

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
- **Hash-only scoped DB paths**: existing scoped queues are stored as `queue-<digest>.db`, where the digest is a one-way hash of `server|user|team` — so the original URL/scope **cannot be recovered from the filename**. Migration must (a) discover all such DBs, (b) attach migrated events to a best-effort or explicitly-`unknown` delivery target rather than fabricating identity, (c) define duplicate-`event_id` collision rules when consolidating multiple DBs, and (d) handle an unrecognized digest without aborting. (The current migration only folds a legacy `queue.db` into the active scope — insufficient.)
- **Env/config target split-brain**: `config.toml`, `SPEC_KITTY_SAAS_URL`, auth/readiness, queue scope, WebSocket, tracker, and network calls must not resolve different runtime targets. One resolver owns the target; queue scope is a derived isolation key, not a selector.
- **Capture before drain gates**: Teamspace-bound facts must be written to SQLite or git even when SaaS sync is disabled, auth is missing, the Private Teamspace gate blocks, or the network target is unavailable. Those conditions block delivery only and are recorded as `drain_blocked_reason`/audit state.
- **Duplicate `event_id` collision during migration**: identical duplicate payloads import once with source provenance; divergent duplicate payloads are quarantined/audited and block cleanup of the source DB until operator resolution. The migration does not rewrite event IDs and does not fabricate a merged event.
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
| FR-013 | Migration of existing queues | As an operator, I want existing scoped queue DBs (hash-only `queue-<digest>.db` paths) discovered and migrated into the journal without losing queued payloads, with unknown-scope and duplicate-`event_id` handling defined. | High | Open |
| FR-014 | DeliveryReceiver contract | As a maintainer, I want each delivery target type to implement one explicit `DeliveryReceiver` contract (endpoint URL, auth/headers, per-event result mapping, retry semantics, and which gates apply) so Teamspace, external-receiver, and stub share one dispatch path. | High | Open |
| FR-015 | Terminal-failed handling | As an operator, I want permanently-failed events (e.g. oversized) recorded as a terminal-failed ledger state that is excluded from future drains and stays inspectable — the drain still progresses, but the payload is not deleted. | High | Open |
| FR-016 | Canonical sync target authority | As an operator, I want config/env/auth/network/status to use one resolved sync target so queue scope cannot point at one server while hosted calls go to another. | High | Open |
| FR-017 | Capture-first durability | As an operator, I want Teamspace-bound facts captured in SQLite or git before auth/team/sync/network gates are evaluated, so disabled or blocked sync cannot silently drop them. | High | Open |
| FR-018 | Migration collision quarantine | As an operator, I want divergent duplicate `event_id` rows quarantined/audited rather than overwritten, merged, or silently ignored. | High | Open |
| FR-019 | Machine-readable status contract | As an operator/tool, I want `sync status --check --json` to expose resolved target authority, stale markers, journal counts, delivery counts, terminal failures, migration conflicts, and body-upload compatibility state. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Observable-state tests | Tests assert observable CLI output and on-disk/ledger state, not internal call order. | Quality | High | Open |
| NFR-002 | Coverage of delivery outcomes | Tests cover success, duplicate, pending, transient failure, rejection, terminal-failed (oversized), explicit GC/archive, **delivered-event immutability** (a DB test: a coalesce attempt against an event with any terminal delivery does not mutate it), and **multi-DB migration** (multiple `queue-<digest>.db` sources, unknown-scope, duplicate `event_id`). | Quality | High | Open |
| NFR-003 | Idempotent re-delivery | Re-draining already-delivered event IDs to a target yields `duplicate` handling with no data corruption; event IDs are unchanged. | Reliability | High | Open |
| NFR-004 | Bounded growth visibility | `sync status` surfaces journal size; GC is suggested once the journal is large AND fully delivered to all known targets. | Reliability | Medium | Open |
| NFR-005 | Migration safety | Migration is atomic per DB and never loses currently-queued payloads. | Reliability | High | Open |
| NFR-006 | Contract extensions stay additive | Existing batch/status contracts remain backward-compatible for body-upload and legacy sync surfaces; event payload semantics are extended by this mission rather than silently redefining unrelated queues. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Separate core domain | Modeled as a separate domain in core — `event_journal/` (journal) + `delivery/` (target registry + ledger + dispatcher) + `EventSyncConfig` policy — not woven into the existing `queue.py`. Do not use bare `events/`: `src/specify_cli/events/` already owns event-log integration and decision-log surfaces. (Stijn, hard requirement.) | Technical | High | Open |
| C-002 | Identity = URL + scope | Delivery target identity is canonical-URL + user/team scope (`UNIQUE(url_hash, team_slug, user_email)`); deployment metadata is recorded as provenance/reset-detection, never an identity key. | Technical | High | Open |
| C-003 | Single active target (decided) | MVP delivers to one operator-selected active target; no automatic fan-out. **Decided 2026-06-25 (stability over volume):** the fan-out lean raised in review was declined on #2131 — "deliver to the chosen target" avoids partial-failure/ordering semantics for no MVP gain, and matches the original non-goal ("operator-selected target sync is sufficient"). The ledger's per-event/per-target shape must still be able to grow into many-targets later without a schema break. | Technical | High | Decided |
| C-004 | SaaS health metadata is a cross-repo dependency | CLI ships with URL-only identity first; consuming `/api/v1/sync/health/` deployment metadata is sequenced after the SaaS exposes it (separate `spec-kitty-saas` follow-on). FR-012 reset-detection is advisory/follow-on, not an MVP blocker for `/spec-kitty.tasks`. | Technical | Medium | Open |
| C-005 | No event-ID changes | This mission does not change event IDs and does not require SaaS to retain events forever or replicate cross-environment. | Technical | Medium | Open |
| C-006 | Body-upload tables untouched | `queue.py` also owns `body_upload_queue` / `body_upload_failure_log` (setup-plan / dossier sync) — these are NOT event queueing. The new `event_journal`/`delivery` domains take over event delivery only; the body-upload tables and their flow stay in place. No "retire `queue.py`" step may break non-event uploads. | Technical | High | Open |
| C-007 | Target authority before journal migration | #2146 is a prerequisite within this mission: `config.toml`, env overrides, auth/readiness, WebSocket, tracker, queue scope, diagnostics, and delivery calls must share one resolved target model before event migration/drain logic ships. | Technical | High | Open |
| C-008 | No silent Teamspace-bound discard | Feature flags, missing auth/team, and opt-out policy can block drain eligibility, but cannot silently discard Teamspace-bound facts unless a durability registry/audit classification proves they are local-only or explicitly discarded. | Technical | High | Open |

### Key Entities

- **Sync Target Resolver**: the target-authority surface that resolves configured target, env override policy, auth/user/team scope, derived queue scope, network base URL, and diagnostics. Queue scope is derived from this resolver and is never an independent selector.
- **Event Journal**: append-only local store of event payloads (`event_id`, type, payload, timestamps, coalesce key, archived marker). Repo/install/session-local and producer-scoped where identity is known, **not** server-scoped and not requiring user/team at capture time. Does not know delivery state.
- **Delivery Target**: one endpoint identity — canonical URL + url_hash + user/team scope; optional recorded deployment metadata (`server_instance_id`, `deployment_id`, `environment_name`, `git_sha`).
- **Delivery Ledger**: per-event/per-target row — status, attempt count, timestamps, server drain state, last HTTP status/error/response. Answers "was X delivered to Y, when, with what result?"
- **EventSyncConfig**: operator/repository policy selecting retention (on/off) × delivery (none / Teamspace / external-receiver), exposed as the four named modes.
- **DeliveryReceiver**: the contract a delivery target type implements — endpoint URL, auth/headers, per-event result mapping (→ success/duplicate/pending/rejected/terminal-failed/transient), retry semantics, and which gates apply (Teamspace: SaaS+Private-Teamspace+Bearer; external: operator-supplied; stub: none). One dispatch path drives all three.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given two distinct SaaS endpoints, the same local event data is delivered to endpoint A and then endpoint B with zero manual SQLite copying.
- **SC-002**: After a successful sync, 100% of local event payloads remain inspectable until an explicit archive/GC command runs.
- **SC-003**: `sync status` reports retained event count and current-target delivery count as distinct numbers.
- **SC-004**: Every terminal successful delivery records endpoint URL and user/team scope (and deployment identity when SaaS health exposes it).
- **SC-005**: The full suite — including fork CI — passes against a stub receiver with no Teamspace credentials present.
- **SC-006**: Migrating from **one or more** existing `queue-<digest>.db` scoped DBs preserves 100% of currently-queued payloads, resolves duplicate `event_id`s deterministically, attaches events to a best-effort-or-`unknown` target without fabricating identity, and loses none.
- **SC-007**: Every delivery target type drives the same dispatch path via one `DeliveryReceiver` contract; a permanently-failed event is recorded terminal-failed, excluded from future drains, and never deleted.
- **SC-008**: With `SPEC_KITTY_SAAS_URL` set to a different URL than `config.toml`, hosted commands either use one explicit whole-process override everywhere or fail/warn before any network call; they never derive queue scope for one target and call another.
- **SC-009**: With SaaS sync disabled, missing auth/team, or Private-Teamspace gate failure, Teamspace-bound events are still captured locally with a drain-blocked/audit reason and are deliverable after the blocker clears.
- **SC-010**: `sync status --check --json` includes additive target-authority, journal, delivery, terminal-failure, migration-conflict, and body-upload compatibility fields defined by this mission's contract.
- **SC-011**: Divergent duplicate `event_id` rows across migrated DBs produce a migration conflict record and leave source DB cleanup blocked; identical duplicates dedupe with source provenance.
