# Decision Moment `01M0P6C8C7Q6SPBT412V39RPN0`

- **Mission:** `retire-doctrine-term-01M0JMK9`
- **Origin flow:** `plan`
- **Slot key:** `plan.m5.serialized-historical-records`
- **Input key:** `serialized_historical_records_disposition`
- **Status:** `resolved`
- **Created:** `2026-08-23T02:14:45.895803+00:00`
- **Resolved:** `2026-08-23T05:54:04.352157+00:00`
- **Resolved by:** `operator`
- **Opened by:** `operator`
- **Other answer:** `false`

## Question

How does M5 treat tracked serialized runtime records keyed to immutable kitty-specs/ archive slugs or retired profile IDs (mission-state quarantine status.events.jsonl, kitty-ops/*.jsonl, .kittify/missions/**/retrospective.yaml)?

## Options

- Treat as immutable historical records: add them to the fixed exclusion set next to kitty-specs/ (amend DM-01M0NMS9WPH33EPFCJQRTQVNSA)
- Untrack/delete after verified backup (Git history retains them)
- Schema-aware rewrite with CR-08-style aliases for profile IDs; slug values keep the archive slug

## Final answer

Treat as immutable historical records: add them to the fixed exclusion set next to kitty-specs/ (amend DM-01M0NMS9WPH33EPFCJQRTQVNSA)

## Rationale

Operator decision 2026-08-23: the immutable historical-record set is kitty-specs/ plus .kittify/migrations/mission-state/quarantine/, kitty-ops/, and .kittify/missions/ — backups of, ledgers about, and terminus snapshots of missions, keyed to archive slugs or point-in-time profile keys. They are excluded from inventory and terminal audits by the same fixed, enumerated pathspec mechanism (not an allowlist); no wave edits, renames, or deletes a pre-existing path under them; runtime may keep appending new records. Consistent with the archive rule; no linkage or provenance loss; 83 content hits + 3 pathnames leave M5.

## Change log

- `2026-08-23T02:14:45.895803+00:00` — opened
- `2026-08-23T05:54:04.352157+00:00` — resolved (final_answer="Treat as immutable historical records: add them to the fixed exclusion set next to kitty-specs/ (amend DM-01M0NMS9WPH33EPFCJQRTQVNSA)")
