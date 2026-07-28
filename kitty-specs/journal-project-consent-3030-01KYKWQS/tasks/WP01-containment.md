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
