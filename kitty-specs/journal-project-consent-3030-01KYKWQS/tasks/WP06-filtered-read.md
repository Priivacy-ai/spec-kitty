---
work_package_id: WP06
title: Filtered journal read and per-project selection
dependencies:
- WP04
- WP05
requirement_refs:
- FR-007
- FR-008
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:54:16.365774+00:00'
subtasks:
- T003
- T017
- T018
- T019
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/delivery/
create_intent:
- src/specify_cli/delivery/selection.py
owned_files:
- src/specify_cli/delivery/dispatcher.py
- src/specify_cli/delivery/selection.py
---

# WP06 — Filtered read and per-project selection

The **only** per-project seam. FR-001 lives in WP01 because `GateContext` is four run-scoped booleans
with no project dimension (`delivery/receivers.py:135-165`), so a `GateKind` can never mean
"project X consented".

## Pinned design

- The filtered read is an **identity projection** — `event_id`, `created_at`, `project_uuid`, **no
  payload BLOB** — used to build the universe. Payloads hydrate via `read_by_id` over the
  ledger-selected batch only.
- **No `LIMIT` is pushed into the filtered SQL.** `ledger.select_undelivered` fetches the full
  terminal-id set and slices the already-filtered universe, so the predicate composes — but a `LIMIT`
  in the filtered read reintroduces the exact starvation NFR-002 bans: terminal rows would fill the SQL
  window and then be stripped, yielding an empty selection while consented undelivered rows sit behind
  them. The ledger is a **separate SQLite file** (`cli/commands/sync.py:535`), so no join can fix it.
- Post-backfill the **stored column is the sole authority for selection**. The in-memory chain is used
  only by WP01's FR-004 refusal check and by WP04's backfill. NULL-identity rows are permanently
  unselectable and counted (FR-011), not lazily re-resolved.

## NFR-001 is a subset invariant, not a count

`delivered_project_uuids ⊆ consented_project_uuids` **and** `None ∉ delivered_project_uuids`. A
cardinality check is fakeable: identity-less events collapse to `{None}`, so N leaked projects would
satisfy `cardinality == 1` while breaching.

## NFR-007 — the fake must exercise the real window

`_should_probe_advertised_limits` (`sync/batch.py:177-183`) returns False for localhost, `127.0.0.1`,
`::1` and `*.example`, so a naive fake never applies `max_events_per_batch` — the variable that decides
whether non-consented rows fill the selection window.

## Definition of done

- SC-001 reproduction passes; SC-002 liveness (2,000 non-consented older than 10 consented → all 10
  delivered in one drain) passes and was **written red-first at this seam**.
