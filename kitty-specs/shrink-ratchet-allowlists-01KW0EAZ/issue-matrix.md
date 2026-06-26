# Issue matrix — shrink-ratchet-allowlists-01KW0EAZ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2049 | Shrink architectural ratchet exception allowlists (burn-down) | fixed | WP01 commit 79761317b — category_a 11→9, category_b 286→276, legacy_contract 152→151, pure_shim 3→0, category_5 3→0; gates green |
| #2048 | category_4 9→8 mission_read_path reversal | deferred-with-followup | Out of scope per spec.md §Out-of-scope / C-005; delivered by sister PR #2152 |
| #2152 | PR delivering the #2048 category_4 reversal | deferred-with-followup | Out of scope here (C-005: this mission must not touch category_4); tracked in PR #2152 |
| #2158 | _extract_all_literal dead-symbol-gate parser fix | deferred-with-followup | Parser fix split out per spec.md scope note (would grow, not shrink, the ratchet); tracked in #2158 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
