# Issue matrix — journal-project-consent-3030-01KYKWQS

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3030 | Cross-project event leak: non-consenting projects delivered to a hosted instance | in-mission | WP01 `41bbf8c1e1`, `6b980f3132`; WP02 `387afabd16`, `0994518348`, `08c94a87b4` |
| #3005 | Permanently-rejected events reported as `Terminal failures 0` | fixed | `41bbf8c1e1` (WP01/T009, FR-014) |
| #3004 | `sync doctor`/`sync status` derive queue truth from the retired store | in-mission | WP07/T021 (FR-015) — not started |
| #3031 | Consent must gate capture, not only delivery (absorbed; its red pins are this mission's acceptance gate) | in-mission | 4 pins red by design; NFR-005 amended in `26c857b657` |

Verdict notes (2026-07-29):

- **#3030 is `in-mission`, not `fixed`.** WP01 (containment/fail-closed), WP02 (drain removal) and
  WP09 (docs) are complete, but the leak itself is closed by WP06's filtered journal read, which
  depends on WP04's `project_uuid` column. The four absorbed #3031 pins
  (`test_dispatch_project_consent_3030`, `test_dispatch_honours_drain_blocked_3031` ×2,
  `test_sync_consent_capture_gap_3031`) are still **red by design** and gate WP04–WP11. This must
  reach a terminal verdict before the mission is `done`.
- **#3005 is `fixed`.** `DeliveryOutcome.TERMINAL_FAILED` was reachable from exactly one predicate
  (`_is_oversized(...) and len(events) == 1`), which is why the operator saw
  `rejected 4141 / terminal_failed 0`. It is now reachable from three
  (`delivery/receivers.py:312,383,457`).
- **#3004 is `in-mission`.** FR-015's per-project reporting lands in WP07/T021, reconciled against the
  journal's retained count rather than `OfflineQueue().get_queue_stats()` — the false-green that made
  `doctor` read healthy during the incident.
- **#3031 is `in-mission` by operator decision.** It was absorbed rather than worked separately, so it
  cannot be `fixed` until its four pins go green. NFR-005 was amended for it — capture now yields to
  "never reach the journal" for non-consenting projects, a deliberate reversal of the documented
  `event_journal/journal.py` unconditional-write invariant, whose contract must be updated to match.

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
