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
