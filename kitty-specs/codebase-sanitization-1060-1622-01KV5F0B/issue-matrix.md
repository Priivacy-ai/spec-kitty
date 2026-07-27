# Issue matrix — codebase-sanitization-1060-1622-01KV5F0B

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1797 | Epic: 3.2.0 codebase sanitization — dead-code & LOC reduction | deferred-with-followup | Parent epic; this mission is one slice (#1060-A + #1622). Epic stays open. |
| #1060 | Legacy cleanup: remove hidden --feature aliases from the CLI surface | deferred-with-followup | Partial fix: internal/agent cluster `--feature` removed (WP01–WP03) + dead `_legacy_aliases.hidden_feature_option` deleted (WP05). User-facing top-level commands (`implement`/`merge`/`next`/`research`/`context`/`accept`/`lifecycle`/`mission_type`) remain open. Follow-up: #1059 (sunset policy gating the user-facing slice); #1060 stays open. |
| #1622 | Upstream dead symbols: coordination.status_service (5) | verified-already-fixed | Resolved by 01KTPKST WP09 (`be932d19a`): 2 deleted, 3 de-exported-because-live. WP04 locks with a regression test + closes the ticket. See research.md R1. |
| #1059 | Compatibility inventory and sunset policy (--feature) | deferred-with-followup | Out of scope — referenced as the dependency gating the deferred user-facing `--feature` slice. Not modified by this mission. Follow-up: #1059 (tracks the user-facing `--feature` sunset; gates #1060). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
