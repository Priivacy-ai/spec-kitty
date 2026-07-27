# Issue matrix — content-address-ratchet-allowlists-01KX8M4D

Parent epic: #2071 (test-QA friction, audit-fed). Surfaced by the CaaCS analysis during the coord-authority trio degod (PR #2545). Hardened by four adversarial squads.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2547 | Propagate content-addressed allowlist key (composite_key) | in-mission | WS1 (WP02 descriptor resolver + WP03/WP04 migrations) delivers the content-descriptor re-keying; terminalizes at mission done. |
| #2072 | CT1 — canonical file:line ratchet re-keying (the #1 friction engine) | in-mission | Folded as WS1's canonical delivery (#2547 was its residual). Now also covers `_RAW_JOIN_SITES` (WP04). Operator to confirm fold on close. |
| #2546 | Replace/harden the whole-codebase dead-code scanners | deferred-with-followup | Follow-up: #2546 — WS2 relocation-hardening CARVED to a follow-up mission (operator-confirmed after the hardening squad found the relocation promise undeliverable for ~60 re-export/facade entries). WP06 spike (approved) delivered the feasibility proof + design; #2546 carries the squad research (shape census, dangling-ratchet, fail-closed, bite battery). |
| #2548 | Audit the ratio=1.00 architectural test cluster | in-mission | WS3 (WP01): 10 KEEP validated (no change) + 2 test_layer_rules conversions + test_template_governance hardening; wp05 line-347 handled in WS1 (WP03). |
| #2077 | CT7 — test-hygiene directive + recurrence-prevention guard | in-mission | FR-004 standing meta-guard (WP05) IS the recurrence-prevention guard; coordinate closure on merge. |
| #2293 | category_b grandfathered dead-symbol carry-over burn-down | deferred-with-followup | Not folded — not line-anchored. WP06's FR-008 auto-derivation checked against #2293's burn-down so they don't fight. |
| #2071 | Epic: test-QA friction (parent) | deferred-with-followup | Follow-up: parent epic #2071 stays open; audit-fed children #2546/#2547/#2548 tracked in this matrix. |
| #2545 | Coord-authority trio degod (PR, MERGED 2026-07-11) | verified-already-fixed | Merged; enables the IC-WS1-TRIO rebase-then-fold fast-follow (C-002). Not modified by this mission. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (must reach a terminal verdict before mission `done`).
