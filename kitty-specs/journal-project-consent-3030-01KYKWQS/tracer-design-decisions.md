# Tracer: design decisions — journal-project-consent-3030

Charter standing order 3. Decisions whose rationale would otherwise live only in
commit messages.

## The root cause was mis-pinned, and the correction shaped everything

#3030 and `saas#585` both pinned the defect at `sync/batch.py:1064-1080`. That is
not the drain `sync now` uses. The real path is
`delivery/dispatcher.py:_select_undelivered` over `journal.read_all()`. A fix at
`batch.py:1064` would have passed its unit tests and leaked in production.

## Consent is a separate representation from `drain_blocked_reason` (C-003)

`drain_blocked_reason` is a machine-global gate snapshot taken at capture and
re-evaluated each tick; consent is a stable per-project decision. Collapsing them
would either strand every pre-login capture or make consent transient. Consent is
represented by the stored `project_uuid` plus `consent.py`'s resolver; the one
invariant (`delivered ⊆ consented`) is expressed once, in selection.

## T003's split is policy vs readiness, not null vs non-null

Excluding every non-null `drain_blocked_reason` would strand every capture taken
before login. Terminal = the operator's policy did not permit shipping
(`saas_disabled`). Transient = they consented but the machine was not ready
(`missing_auth`, `missing_team`, `private_teamspace_gate`, `daemon_lock`,
`network_unavailable`). An unrecognised token is terminal: a stranded event is
purgeable, an unconsented delivery is not.

## NFR-005 was reversed deliberately (T006)

Capture-first durability was unconditional for Teamspace-bound facts. That
invariant is what made the journal a machine-global pool of every local project's
payloads. It now applies to consenting projects only, and
`capture_teamspace_bound`'s contract was updated to say so. The gate lives at
`EventEmitter._capture_to_journal`, the single production entry point — gating
inside `capture_teamspace_bound` via its unused `skip_journal` parameter would
have greened a test while every real capture stayed unconditional.

## FR-013 × FR-019: both stores, project-local wins (operator, 2026-07-29)

FR-019 supersedes FR-013 on authority, not existence. The uuid-keyed index must
exist because the dispatcher resolves consent for events carrying only a uuid and
must answer when the checkout has moved or been deleted. The index is a cache: a
readable checkout that disagrees wins, and the index is corrected.

## `repo_slug` became a third identity column (operator, 2026-07-30)

Consent is stored repo-slug-keyed (`[sync.repo_defaults."owner/repo"]`) and the
acceptance pins deliberately record it that way, but rows carried only
`project_uuid`. Rather than weaken the pins, the row now carries `repo_slug` and
the resolver gained a `REPO_DEFAULT` level between the uuid index (project-specific)
and the env var (machine-wide arming).

## The filtered read takes no LIMIT, on purpose

`ledger.select_undelivered` fetches the full terminal-id set and slices an
already-filtered universe. Pushing a LIMIT into the journal SQL would let delivered
rows fill the window and be stripped afterwards — an empty selection with consented
rows behind it, which is NFR-002's starvation. The ledger is a separate SQLite
file, so no join can rescue it.

## C-004 moved to WP08 for a schema reason

Retiring `queue.remove_project_events` needs `disable_checkout_sync` to purge the
journal instead, and the journal had no `project_uuid` to purge by until WP04.

## The egress point owns its own refusal (M1-1, 2026-07-30)

`drain_blocked_reason` was derived from the **current working directory's** checkout
routing, so one project's grant published another project's envelope over the
WebSocket. Two facts settled the shape of the fix, and only one of them was the
reported bug.

The reported half is the leak. The unreported half is that the same read was
**simultaneously dead**: with no readable checkout, `resolve_checkout_sync_routing`
returns `None`, so every event of every project was stamped `sync_disabled` — the
WebSocket publish was broken for *consenting* projects too, which is the daemon's
normal case. This is why the fix could not be a gate at `_route_event` alone:
`test_an_index_grant_publishes_from_outside_any_checkout` would have stayed red
forever. `_classify_drain_blocked_reason` had to stop being cwd-derived.

The decision therefore lands in **two** places deliberately, which is a considered
exception to C-003 and not an oversight: `_classify_drain_blocked_reason` resolves
through the one consent chain with an explicit `project_uuid`, **and** `_route_event`
re-checks consent independently immediately before publish. The reasoning is M1-1's
own lesson — the finding *was* the failure of resting a confidentiality boundary on a
field whose docstring calls it a diagnostic. Both sites must reach the same resolver;
two sites that could disagree about consent would be the C-003 violation this avoids.

Structural rather than test-enforced: `emitter.py` no longer imports
`routing.is_sync_enabled_for_checkout` at all, so the cwd-derived substitution cannot
creep back by someone re-reaching for the convenient helper.

## `queue_event` is deliberately not gated, and what would flip that

Three grounds, in descending durability. (1) It is **not egress** — every
`drain_queue`/`process_batch_results` call site was enumerated and verified, not
assumed, and `tests/sync/test_no_queue_drain_constructed_3030.py` pins that no code
path constructs the drain. Assuming "nothing reads this" is the exact mistake M1-1
corrected, so this ground was re-derived rather than inherited. (2) Gating it would
be **data loss, not confidentiality**: the local outbox is documented unconditional
(#1072), and refusing the write converts "not opted in to hosted sync" into "local
event history discarded". (3) The residual at-rest pooling is C-006's recorded open
collection surface, remediated by FR-016's purge rather than by refusing to write.

**Precondition, not a follow-up ticket:** if a queue-backed sender is ever restored,
this write becomes egress and must be gated *before* the sender lands. Recorded here
because the WP02 removal is what makes ground (1) true, and a future WP re-opening
`batch.py` for FR-014 will not otherwise know that.

## Two cwd-derived reads survive, both inert, both with the same trigger

`batch.py` retains a second one alongside `queue_event`'s at-rest pooling:
`_is_checkout_sync_enabled_for_batch` (`:335`) reads consent from the current working
directory. Reachability was traced rather than inferred from the anchor test's name —
`batch_sync` (`:990`) is its only caller, `sync_all_queued_events` (`:1374`) is
`batch_sync`'s only caller, and neither has a production reference outside `batch.py`.

Both residues share one trigger: **FR-014 re-opening `batch.py` to restore a
queue-backed sender.** That single change would simultaneously make `queue_event` an
egress write and make this read a live cross-project consent decision. Neither is
filed as an issue, because an issue in a tracker is not read by the person editing
`batch.py`; both are recorded at the code and in the WP that would be re-opened.

The general rule this mission keeps re-deriving: **cwd is not the bug.** A
human-invoked command whose subject is "this checkout" is right to read cwd —
`cli/commands/sync.py:1107,1204` are correct as written. The bug is cwd answering a
question about a *specific event's* project, which is why the fix everywhere was to
thread the event's own `project_uuid` rather than to purge `Path.cwd()` from the
codebase.

## Derive projections from `ORDERED_COLUMNS` — but judge per site (H6 class closure)

H6 was one symptom of a class: four hand-maintained column projections that a new
column silently falsifies. Closed in `6c48815fbd` by deriving them from
`ORDERED_COLUMNS` / `IDENTITY_COLUMNS`, proven by mutation rather than by argument.

**Mutation A** (a hypothetical 12th non-identity column `tenant_id`, created in the DDL
and written by `SET_IDENTITY_SQL`) made `test_backfill_preserves_all_non_identity_columns`
**pass pre-fix while the backfill damaged that column** — the class was open exactly as
the reviewer claimed. Post-fix it fails and names the column.
**Mutation B** (drop `repo_slug` from the ALTER loop) produced, pre-fix, a single failure
in an *unrelated* test via `read_all()` raising `no such column`, while all four C-001
pins passed. Post-fix, four failures including the pins.

**One site was deliberately not derived.** `_read_raw` exists to prove the migration did
not disturb values that existed *before* it ran, so it must keep asking about the
historical eight columns as the schema grows — deriving it would make it select the
columns the migration just added and compare them against themselves, which is the
tautology class. Resolved by naming the literal `_PRE_MIGRATION_COLUMNS` and asserting it
**equals** `ORDERED_COLUMNS - IDENTITY_COLUMNS`, so drift fails loudly without losing the
freeze. Blanket-deriving is the wrong lesson; the rule is *derive where the projection
should track the schema, freeze where it should track history, and assert the relationship
between them either way.*

Two guards were added on the derivations themselves, because **a derived projection fails
by going silent rather than by returning a wrong answer**: `PRESERVED_COLUMNS` must be
non-empty and disjoint from `IDENTITY_COLUMNS`, and every column must be classified as
either written-by-the-backfill or preserved. Same reasoning as the shrink-only ratchet — a
computed guard that quietly computes to nothing asserts nothing.

## An unpinned MINOR, recorded rather than asserted

A differing payload `repo_slug` overwriting a stored one on a `project_uuid IS NULL` row
is **permitted**: it is NFR-004's letter, and `repo_slug` is never an authorization key
(FR-019), so there is no confidentiality consequence. It is deliberately **not pinned**,
and the reason is the more important half — the behaviour was reasoned about but never
observed, and a pin asserting what an author believes rather than what they measured is
this mission's recurring failure mode. If the pin is wanted it needs a red-first cycle
commissioned as work, not a comment claiming knowledge nobody has.

## `--all` cannot compose from the per-project purges, and the reason is measured

FR-017's `purge_all_events` (`d2ad9c8b5f`) is deliberately **its own read of both tables**
rather than a loop over `distinct_project_uuids()` plus `purge_identity_less_events`. The
strongest available union was run against a store seeded with every population, and three
survived:

```
surviving journal : ['E-blank', 'E-whitespace']
surviving ledger  : ['E-ghost']
```

1. **`project_uuid = ''`** — `distinct_project_uuids()` *returns* it (it is not NULL), but
   `read_identity_projection` filters falsy uuids and `purge_project_events` blanks a falsy
   selector to select-nothing, while `iter_rows_missing_identity` is `IS NULL`-only.
   Measured: `purge('')` → `purged=0`.
2. **`project_uuid = '   '`** — the worse one, and nobody predicted it. The projection *can*
   return it (`projection(['   ']) → ['E-whitespace']`), but the purge strips its selector to
   `''` and selects nothing. **Visible in the census, unreachable by any purge.**
3. **A ledger row whose `event_id` has no journal row** — the union only ever collects ids
   *from the journal*. Not hypothetical: `gc_payloads` in this same module deletes journal
   rows while preserving ledger history **by design** (FR-010), so **every machine that has
   run `sync gc` is in this state.**

C-003 is respected because only *selection* differs — deletion still goes through the one
shared `_purge` core, so there is no second DELETE path. The non-composability is **pinned**,
so if a later change makes the union total, that test fails and the decision is revisited
rather than silently outliving its reason.

## NFR-006's differential was vacuous for one population

`_journal_census` read its identity-less bucket from `count_missing_identity()` (`IS NULL`)
while attributing every other row through a projection that **drops falsy uuids**. A
`''`-uuid row was therefore counted in **neither** bucket: measured, `census sum = 5` against
`count() = 6`.

This matters far beyond a wrong total. **Every NFR-006 differential subtracts this census**,
so a population absent from both buckets has a differential of zero *by construction* — a
purge could move those rows and still report, truthfully by its own arithmetic, "0% of any
other project's rows affected". The mission's own success metric was blind to the exact
population most likely to be malformed.

Fixed by deriving the bucket as `count() - attributed`. For the ordinary case the derived
number equals `count_missing_identity()` exactly, so no existing report changes — the fix
adds a population rather than restating one.

## Two stores, deliberately not one transaction

A failure injected between the two deletes leaves the **ledger** delete committed and the
journal untouched. That is the recoverable direction — the ordering `_purge` already
documents — and a re-run converges. Recorded as a **pinned observation** rather than a
comment, because "this falls the safe way" is a claim that should fail loudly if the
ordering is ever reversed.

## One deliberate omission, recorded as a decision

`purge_identity_less_events` still cannot remove a `''`-uuid row; only `--all` can. Widening
it would mean widening `iter_rows_missing_identity`, whose `IS NULL` restriction is exactly
what makes the backfill **idempotent** (NFR-004/SC-007). It therefore needs its own selector
rather than a widened one, and belongs to whoever owns FR-011. The census fix above turns
those rows from *invisible* into *observable-but-only-removable-by-`--all`*, which is
strictly better and does not pretend to be complete.
