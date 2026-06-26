# Research Notes: Event sync — separating retention from delivery

**Status:** Draft synthesis — converging toward an ADR; one open decision below
**Owner:** Lynn Cole (design), with Robert Douglass (proposal) and Stijn (feedback)
**Last updated:** 2026-06-25
**Related issue:** https://github.com/Priivacy-ai/spec-kitty/issues/2124

---

## Why this exists

The CLI's local sync queue is a destructive outbound queue: on a terminal
success from a SaaS endpoint the local row is deleted (`process_batch_results`,
`src/specify_cli/sync/queue.py:1693`). That is fine for one durable production
target. It is wrong for transient SaaS test environments (Upsun PR envs), where
the operator wants to drain the same local events to env A, destroy it, and
drain the same events again to env B.

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

### The testing stub falls out for free

Stijn wants a stub receiver so fork CI stops depending on a real Teamspace and
the `teamspace_key` in core that keeps breaking his runs. A stub is just an
`EXTERNAL_RECEIVER` pointed at a localhost sink that accepts and records events
for assertions. It is a configuration of the design, not a special case — and it
gets CI off the Teamspace dependency.

## Module boundary (Stijn's hard requirement)

Stijn requires this be modeled as a **separate domain in core**, to avoid the
spaghetti trap from 2.x. The current `queue.py` is 1,861 lines; an honest
append-only journal and safe coalescing are not achievable inside it. Proposed
boundary, mapping 1:1 to Robert's components:

- `events/` — the journal (append-only payload store).
- `delivery/` — target registry + ledger + dispatcher.
- `EventSyncConfig` — the policy layer that selects retention × delivery target.

## Code-level sharpening points (from the #2124 review)

1. **The migration *is* the scope collapse.** The queue DB is keyed
   `server|user|team` (`build_queue_scope`, `queue.py:391`), so events produced
   against env A live only in A's DB. The journal must become
   **target-independent** — scoped to producer (`user|team` / repo-local) — with
   the server URL moving out to the target registry. Migration consolidates
   possibly-several per-server DBs into one journal and backfills ledger rows.
   Honest limit: events already delivered-and-deleted are gone; migration can
   only preserve *currently-queued* payloads.

2. **Coalescing vs append-only is the correctness trap.** Coalescing today
   *mutates* the existing row (`UPDATE event_type, data …`, `queue.py:1267`).
   Once an event has a terminal delivery to any target, mutating it makes the
   ledger lie. Rule: coalesce only among events with no terminal delivery to any
   target; after first delivery the event is immutable and a new event is a new
   row (mark the old superseded). This protects the audit honesty the feature
   exists for.

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
matches the proposal (`queue.py:1666-1678`); only `success` / `duplicate` /
`failed_permanent` need to stop deleting and become ledger writes. The heavy
lifting is the journal/ledger split + the migration, not the dispatch logic.

## Open decision

**Single active delivery target, or journal-once-deliver-to-many fan-out?**
Robert's non-goals lean single (operator-selected target is sufficient; no
automatic fan-out). Recommendation: build single-active-target, but shape the
ledger (per-event/per-target rows) so it can grow into many without a schema
break. This is the one fork to settle at the table before the mission runs.

## Next step

Once the thread agrees, run this as a spec-kitty mission. This note becomes the
design input; the mission produces the spec, plan, and the ADR in
`architecture/3.x/adr/`.
