---
work_package_id: WP01
title: 'Containment: refuse loudly, fail closed'
dependencies: []
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-005
- FR-010
- FR-014
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:53:39.091131+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T009
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/
owned_files:
- src/specify_cli/delivery/dispatcher.py
- src/specify_cli/delivery/receivers.py
- src/specify_cli/sync/routing.py
---

# WP01 — Containment: refuse loudly, fail closed

Makes the leak **loud**, with no schema change. Honest limit: this does not make delivery correct on a
multi-project machine — WP06 does.

## Where the leak actually is

`delivery/dispatcher.py:192-223` `_select_undelivered` takes its universe from `journal.read_all()`
(`dispatcher.py:214`) — every row of every project. `sync/batch.py` is **not** the drain `sync now`
uses (`cli/commands/sync.py:2360-2367`, `sync/queue.py:1-12`, `sync/migrate_journal.py:769-772`).

## Do not mistake FR-003 for containment

`is_sync_enabled_for_checkout` has **zero callers under `delivery/`** — only `sync/emitter.py:1890,1921`,
`sync/batch.py:338`, `sync/body_upload.py:150`, `sync/runtime.py:77`. Fixing its fail-open default
hardens the emit path, the daemon drain and body uploads. Containment here comes from **T002**.

## T003 covers ZERO incident rows — say so out loud

In the incident `SPEC_KITTY_ENABLE_SAAS_SYNC=1` was exported and the five projects had **no** consent
record, so `checkout_enabled` resolved `True` via the default-allow at `routing.py:87`.
`classify_drain_blocked_reason` therefore returned `None` for every one of those 1,322 captures and
their column is NULL. T003 closes a real class; it closes **none of this breach**. Do not let a reviewer
read it as containment.

## T003 must not become a data-loss switch

`drain_blocked_reason` is write-once — nothing in `src/specify_cli` ever clears it — and its vocabulary
includes `missing_auth` and `missing_team` (`journal.py:338-352`), i.e. every capture before login or
team resolution. `emitter.py:2246-2248` states the intended contract: *"Drain-blocked events stay in the
durable outbox; the drain loop re-evaluates conditions on each tick."* Excluding all non-null values
would permanently strand honest users' pre-login backlog. Split the vocabulary: transient gate reasons
are re-evaluated at drain; only a terminal reason excludes. Ship a **negative test** — a
`missing_auth` row delivers once the gate clears.

## T009 — terminal reject lands in `receivers.py`, not the ledger

`DeliveryOutcome.TERMINAL_FAILED` is reachable from exactly one predicate today: `_is_oversized(...) and
len(events) == 1` (`delivery/receivers.py:411-414`). Everything the server refuses becomes `REJECTED` or
`TRANSIENT` — which is precisely why the operator saw `rejected 4141 / terminal_failed 0`.
`delivery/ledger.py:98-101` **already** maps `terminal_failed` and `failed_permanent`, and
`record_terminal_failed` already exists, so there is no ledger work. Restate SC-009 as a
**cross-invocation** assertion (a second `sync now` selects strictly fewer events) — within a single run
`_run_dispatch_batches` already advances past non-progressing events via its `exclude` set
(`cli/commands/sync.py:807-860`), so a single-run assertion is green on `origin/main`.

## Second leak class (T003)

`classify_drain_blocked_reason` (`event_journal/journal.py:338`) already stamps `drain_blocked_reason`
from `gate.checkout_enabled`, and `delivery/` never reads it — so events captured while a checkout was
opted out are marked blocked at `journal.py:345` and **shipped anyway**. Excluding non-null values from
the universe is migration-free.

## Definition of done

- T001's reproduction is **RED on `origin/main`** before T002 lands, with the five non-consenting
  projects carrying **no consent record at all** (a fixture that seeds explicit opt-outs does not
  reproduce the incident — the registry is default-allow at `routing.py:87`).
- Every fail-closed path asserts **no network request was made**.
- T006 stamps identity-less capture non-deliverable; it must not drop events (NFR-005).
- A `missing_auth`-stamped row **is** delivered after authentication (the T003 negative test).
- SC-009 asserts cross-invocation shrinkage, not single-run progress.
- T005's message replacement touches `batch.py:1484-1488`, owned by WP02 — coordinate, or move that
  line-item into WP02 rather than no-op'ing inside WP01's surface.
