# Issue matrix — harden-dead-symbol-gate-01KW0RJR

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2158 | Dead-symbol gate parser bug + caller-detection hardening (split from #2049) | fixed | This mission: `_extract_all_literal` fixed, 4 anchored detectors added, ~88 surfaced symbols demoted from `__all__` across ~26 modules (defs retained), 6 genuine-public allowlisted, `BANNED_FLAGS` enforced; ratchet flat (12/286, net downward). Merge commit 0fd2f7c92. |
| #2049 | Shrink architectural ratchet allowlists (parent burn-down) | deferred-with-followup | Out of scope; delivered separately by PR #2159. |
| #2159 | PR for #2049 | deferred-with-followup | Sibling PR, not this mission. |
| #2048 | Retire dead backcompat shim (category_4 9→8) | deferred-with-followup | Out of scope; delivered by PR #2152. |
| #2152 | PR for #2048 | deferred-with-followup | Sibling PR, not this mission. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
