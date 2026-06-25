# Research Notes: Event sync — separating retention from delivery

**Status:** Draft synthesis — converging toward an ADR; prerequisites and open decisions below
**Owner:** Lynn Cole (design), with Robert Douglass (proposal) and Stijn (feedback)
**Last updated:** 2026-06-28
**Primary issue:** https://github.com/Priivacy-ai/spec-kitty/issues/2124
**Related issues:** https://github.com/Priivacy-ai/spec-kitty/issues/2146, https://github.com/Priivacy-ai/spec-kitty/issues/2144, https://github.com/Priivacy-ai/spec-kitty/issues/1800, https://github.com/Priivacy-ai/spec-kitty/issues/1666

---

## Issue topology and sequencing

This note is not a standalone build spec. It sits in the SaaS sync durability
cluster:

- **#2146 — sync target authority**: prerequisite. It decides which value owns
  runtime target selection (`config.toml`, `SPEC_KITTY_SAAS_URL`, or an explicit
  override) and proves queue scope, auth, and network calls cannot diverge.
- **#2124 — retained event journal + per-target ledger**: this note's primary
  design spike.
- **#2144 — Teamspace durability registry + git/SaaS replay**: sibling/follow-on.
  It proves every Teamspace-bound fact has an approved durable source and replay
  path.
- **#1800 / #1666**: parent sync/event-envelope hardening and execution-state
  domain-boundary redesign.

Recommended planning order: **#2146 -> #2124 -> #2144**. The #2124 mission must
not be planned in isolation from target authority or Teamspace durability
coverage.

## Why this exists

The CLI's local sync queue is a destructive outbound queue: on a terminal
success from a SaaS endpoint the local row is deleted (`process_batch_results`,
`src/specify_cli/sync/queue.py:1674-1720`). That is fine for one durable
production target. It is wrong for transient SaaS test environments (Upsun PR
envs), where the operator wants to drain the same local events to env A, destroy
it, and drain the same events again to env B.

Robert opened #2124 to fix this at the CLI level before Teamspace is exposed to
users. Stijn added the operator-config framing and a hard requirement on module
boundaries. This note folds both into one design.

## The core move (Robert): separate retention from delivery

Today, one concept does two jobs: the queue row is both *the event payload* and
*the delivery state*. Split them:

- **Event journal** — append-only local record of event payloads. Does not know
  whether an event was ever sent anywhere.
- **Delivery target registry** — target identity (canonical URL + user/team
  scope, plus optional server-advertised deployment metadata).
- **Delivery ledger** — per-event/per-target state: was event X sent to target
  Y, when, with what result?
- **Dispatcher** — selects journal events lacking terminal successful delivery
  for the active target, posts, updates the ledger. Never deletes source events.
- **Retention / GC** — explicit operator action only.

A successful upload becomes a *ledger update*, not event destruction.

## The operator surface (Stijn): `EventSyncConfig` is the same split, from the top

Stijn's `EventSyncConfig` (`LOCAL_RETENTION` / `EXTERNAL_RECEIVER` / `TEAMSPACE`
/ `OPT_OUT`/`TRASH`) is not a competing proposal — it is the operator-facing dial
for exactly the retention-vs-delivery separation above. Under the hood it resolves
to **two orthogonal axes**:

- **Retention** (the journal): on = keep payloads locally · off = discard
- **Delivery** (the target + ledger): none · Teamspace · external-receiver

The four named modes are the useful presets over those axes:

| Mode | Retention | Delivery |
|---|---|---|
| `TEAMSPACE` | journal on | → SaaS Teamspace target (default for connected users) |
| `EXTERNAL_RECEIVER` | journal on | → operator-configured endpoint (just another target type) |
| `LOCAL_RETENTION` | journal on | none — retain now, choose a target and drain later (the replay case) |
| `OPT_OUT` / `TRASH` | off | none |

Modeling it as two axes (not a flat enum) keeps Robert's separation honest and
leaves room for presets to grow without reshaping the core.

### Target-authority prerequisite (#2146)

`EventSyncConfig` must sit behind one target-authority rule, not become a fifth
source of truth. Before implementation, #2146 must settle this matrix:

| Surface | Current role | Required decision before #2124 implementation |
|---|---|---|
| `EventSyncConfig` | Desired operator policy dial for retention and delivery mode. | Selects policy only; does not independently choose a network target. |
| `SyncConfig.server_url` / `config.toml` | Current sync commands and queue-scope derivation read this path. | Either canonical runtime target, or explicitly overridden everywhere. |
| `SPEC_KITTY_SAAS_URL` | Current auth/readiness path treats this as SaaS base URL. | Internal/dev override only if it overrides auth, sync, tracker, queue scope, and diagnostics consistently. |
| `SPEC_KITTY_ENABLE_SAAS_SYNC` | Enables hosted sync behavior. | Affects drain eligibility only; Teamspace-bound capture must still land in SQLite or git. |
| Auth session + team scope | Supplies user/team identity for scoped queues and target identity. | Required input to target identity and ledger rows. |
| Queue scope | Current isolation key: `server|user|team`. | Remains an isolation/legacy migration input, not an independent target selector. |
| Network calls | Current call sites can follow different URL sources. | Must use the same resolved target as queue scope and diagnostics. |

Acceptance for #2146 must prove env/config disagreement cannot create a queue
scope for one target while network calls go to another.

### The testing stub falls out for free

Stijn wants a stub receiver so fork CI stops depending on a real Teamspace and
the `teamspace_key` in core that keeps breaking his runs. A stub is just an
`EXTERNAL_RECEIVER` pointed at a localhost sink that accepts and records events
for assertions. It is a configuration of the design, not a special case — and it
gets CI off the Teamspace dependency.

## Module boundary (Stijn's hard requirement)

Stijn requires this be modeled as a **separate sync-domain component**, to avoid
the spaghetti trap from 2.x. The current `queue.py` is 1,861 lines; an honest
append-only journal and safe coalescing are not achievable inside it. Proposed
boundary, mapping 1:1 to Robert's components:

- `sync/journal` (or `sync_event_journal`) — append-only payload store.
- `sync/delivery` — target registry + ledger + dispatcher.
- `EventSyncConfig` — the policy layer that selects retention × delivery target.

Do not name the new journal package simply `events/`. That collides with the
existing event-log integration surface (`src/specify_cli/events`), sync emission
helpers (`src/specify_cli/sync/events.py`), and the external `spec_kitty_events`
contract package.

## Code-level sharpening points (from the #2124 review)

1. **The migration depends on #2146's target-authority decision.** Today the
   queue DB is keyed `server|user|team` (`build_queue_scope`,
   `src/specify_cli/sync/queue.py:402`), so events produced against env A live
   only in A's DB. That is correct as a safety property for the destructive
   queue: it prevents accidental cross-target drain. The new journal can become
   target-independent only after target authority is settled and the delivery
   ledger carries the target dimension. Migration consolidates possibly-several
   per-server DBs into one journal and backfills ledger rows. Honest limit:
   events already delivered-and-deleted are gone; migration can only preserve
   *currently-queued* payloads.

2. **Coalescing vs append-only is the correctness trap.** Coalescing today
   *mutates* an existing row (`UPDATE event_type, data ...`,
   `src/specify_cli/sync/queue.py:1278`; key-based coalescing updates at
   `src/specify_cli/sync/queue.py:1507`). Once an event has a terminal delivery
   to any target, mutating it makes the ledger lie. Rule: coalesce only among
   events with no terminal delivery to any target; after first delivery the
   event is immutable and a new event is a new row (mark the old superseded).
   This protects the audit honesty the feature exists for.

3. **Target identity = URL + scope; deployment metadata is provenance, not
   identity.** `UNIQUE(url_hash, team_slug, user_email)` is right. Upsun stamps a
   new `deployment_id` per push, so deployment identity must not fork the target —
   record it, and use a *change* in it to detect "same URL, env reset underneath
   us" and offer a re-drain. Reset-detection, not identity-forking.

4. **`/api/v1/sync/health/` deployment metadata is a SaaS cross-repo
   dependency.** Sequence it: ship the CLI with URL-only identity first (already
   correct for destroy-and-recreate, since a new env is a new URL), then SaaS
   exposes the metadata, then the CLI consumes it. Don't let the health work
   block the CLI work.

5. **Append-only grows until `sync gc`.** Safe default, but surface journal size
   in `sync status` and suggest GC once the journal is large *and* fully
   delivered to all known targets. "Explicit only" must not mean "silent
   unbounded."

One easing fact: `pending` / `rejected` / `failed_transient` handling already
mostly matches the proposal (`src/specify_cli/sync/queue.py:1674-1689`);
`success` / `duplicate` / `failed_permanent` still delete rows
(`src/specify_cli/sync/queue.py:1717-1723`) and must become ledger writes. The
heavy lifting is the journal/ledger split + the migration, not the dispatch
loop.

## Falsifiable acceptance matrix

The mission/ADR that consumes this note should carry these checks forward:

| Area | Required evidence |
|---|---|
| Target authority (#2146) | Env/config disagreement cannot silently split queue scope from network target; status reports configured target, resolved target, env override, derived scope, and stale markers. |
| Endpoint replay | Given retained events and two distinct endpoints, sync to A then B delivers the same retained payloads without manual SQLite copying. |
| Post-success retention | After `success` or `duplicate`, payload rows remain inspectable until explicit archive/GC; ledger records terminal delivery. |
| Delivery state | `sync status` reports retained event count separately from current-target delivery count and previous-target history. |
| Coalescing | Coalescing cannot mutate payload bytes for any event with terminal delivery to any target. |
| Failure buckets | Tests cover success, duplicate, pending, transient failure, content rejection, and permanent failure without payload loss except explicit policy. |
| GC/archive | Cleanup is explicit, reports journal size, and preserves ledger/provenance after payload archive. |
| Teamspace durability (#2144) | Every Teamspace-bound fact has a registered durable source and replay/import path, or a documented local-only reason. |
| Stub receiver | `EXTERNAL_RECEIVER` localhost stub works in fork CI without Teamspace credentials. |

## Open decisions

**Single active delivery target, or journal-once-deliver-to-many fan-out?**
The original #2124 non-goals say operator-selected target sync is sufficient,
but Robert later stated a preference for "journal-once-deliver-to-many fan-out"
in the issue thread. There is no consensus yet.

Decision criteria before implementation:

- Does the operator need one command to deliver to several active targets, or is
  explicit target selection enough?
- How does fan-out report partial success, retries, and per-target drain state
  without hiding failures?
- Does fan-out create any auth/scope ambiguity once #2146 settles target
  authority?
- Can the single-target path be upgraded to fan-out without schema break?

Conservative build shape: per-event/per-target ledger rows either way. The
dispatcher behavior (single active target vs fan-out over configured targets)
must be decided by the ADR/spec, not inferred from this draft.

## Next step

First settle #2146's target authority. Then run the #2124 mission using this
note, #2146, and #2144 as inputs. The mission produces the spec, plan, and ADR
in `architecture/3.x/adr/`, including the acceptance matrix above and the final
single-target/fan-out decision.
