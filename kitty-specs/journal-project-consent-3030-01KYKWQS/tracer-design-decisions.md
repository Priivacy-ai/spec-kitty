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
