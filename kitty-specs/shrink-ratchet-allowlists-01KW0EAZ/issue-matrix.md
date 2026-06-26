# Issue matrix — shrink-ratchet-allowlists-01KW0EAZ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2049 | Shrink architectural ratchet exception allowlists (burn-down) | fixed | This mission: category_a 11→9, category_b 286→276, legacy_contract 152→151, pure_shim/category_5 3→0; corrections posted (issuecomment-4805174448). Merge commit 00394fb. |
| #2048 | Retire dead backcompat shim specify_cli.mission_read_path (category_4 9→8) | deferred-with-followup | Out of scope (C-005); delivered separately by PR #2152. |
| #2152 | PR for #2048 (category_4 9→8 reversal) | deferred-with-followup | Sibling PR, not this mission; #2049 must not touch category_4 (C-005). |
| #2158 | Dead-symbol gate parser bug (_extract_all_literal) split from #2049 | deferred-with-followup | The FR-006 parser fix was split out here (its ~117-symbol blast radius would grow the ratchet); tracked in #2158. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
