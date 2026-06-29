# Issue matrix — shrink-ratchet-allowlists-01KW0EAZ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2049 | Shrink architectural ratchet exception allowlists (burn-down) | fixed | Delivered scope after refresh onto current origin/main (PR #2159): legacy_contract 152→151 (FR-003), pure_shim/category_5 3→0 + 9 dead adapter symbols removed (FR-004), MismatchType demoted not grandfathered; informational accuracy sync category_a 12→10, category_b 286→264 (FR-005). FR-001/FR-002/FR-006 OVERTAKEN by main's harden-dead-symbol-gate. |
| #2048 | Retire dead backcompat shim specify_cli.mission_read_path (category_4) | deferred-with-followup | Out of scope (C-005); delivered separately by PR #2152. category_4_backcompat_shims stays at main's value 8 — not touched here. |
| #2152 | PR for #2048 (category_4 reversal) | deferred-with-followup | Sibling PR, not this mission; #2049 must not touch category_4 (C-005). |
| #2158 | Dead-symbol gate parser bug (_extract_all_literal) split from #2049 | verified-already-fixed | The FR-006 parser fix LANDED on main as part of harden-dead-symbol-gate; nothing owed by this PR. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
