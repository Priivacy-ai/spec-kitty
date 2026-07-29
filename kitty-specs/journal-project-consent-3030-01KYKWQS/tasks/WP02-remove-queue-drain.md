---
work_package_id: WP02
title: Remove the legacy queue-backed daemon drain
dependencies: []
requirement_refs:
- FR-012
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-journal-project-consent-3030-01KYKWQS
base_commit: b09ac6680ad89efcdaf0fbf029895cea7ca3394b
created_at: '2026-07-29T11:03:42.214983+00:00'
subtasks:
- T007
- T008
history: []
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/background.py
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/queue.py
tags: []
tracker_refs: []
---

# WP02 — Remove the legacy queue drain

Research decision 1 resolved to **remove**, not enforce.

## Why removal strands nothing

`_capture_to_journal` is called at `sync/emitter.py:2057`, **before** the identity check at
`:2081-2085` and before every gate. Its own comment: *"the journal write is unconditional; the gates
only set the recorded drain_blocked_reason, never whether the durable write happens."* So every event
reaching the legacy queue — including identity-less ones that skip `_route_event` — already has a
journal copy the dispatcher can deliver. This retires the `queue.py:1-12` objection, whose stated
precondition is satisfied per `cli/commands/sync.py:2360-2367`.

## Definition of done

- `migrate_queues_to_journal` run or required first; legacy queue asserted empty; **fails loudly**
  rather than discarding — pre-WP03 rows may predate journal capture.
- SC-005 asserts **no code path constructs the queue-backed drain**.
- `queue.remove_project_events` retired per C-004.
