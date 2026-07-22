# Issue matrix — charter-deadcode-noop-campsite-01KXW0NY

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

> ⚠ `finalize-tasks` re-scaffolds only MISSING rows (idempotent — verified it preserves filled
> verdicts). Safe to re-finalize.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2373 | build_charter_context regenerates tracked .kittify/doctrine as a render side-effect (dirty-tree) | verified-already-fixed | Render path fixed by #2773 (sync() retired; render writes only gitignored context-state.json); preflight→synthesize by #2732 (charter.yaml content-hash freshness) + #1912 (four `_substantively_equal` promote guards). Post-tasks squad confirmed NO reproducible residual churn at HEAD. This mission landed regression guards pinning both: WP03 (render G1/G3, approved) + WP04 (preflight G2/G3 + INV-2, approved). No behavioral change needed. |
| #1797 | Epic: 3.2.0 codebase sanitization — dead-code & LOC reduction | deferred-with-followup | Epic tracking root — stays open. **Follow-up: #1797** remains the parent epic. This mission is a child slice retiring `charter.generator` + `charter.extractor` (FR-001/003) and shrinking the dead-code baseline downward (FR-004). |
| #1914 | Umbrella: governed/gate operations must be no-op-stable | deferred-with-followup | Umbrella — stays open. **Follow-up: #1914** tracks the remaining no-op-stability instances. #2373 is its enumerated charter-layer instance, guarded/closed in-mission here (FR-005/006). |
| #2773 | consolidate-charter-bundle: authoritative charter.yaml | verified-already-fixed | Merged (`53030b051`). Provides the charter.yaml authority inversion + the render-path no-op fix this mission builds on and guards (WP03). Not modified here. |
| #2732 | synthesized_drg freshness by content-identity | verified-already-fixed | Merged (`4c5fb725c`). Bases `synthesized_drg` on the charter.yaml content-hash so a no-op is `fresh` → no synthesize. WP04 guards this behavior; not modified. |
| #1912 | promote no-op-stable writes (_substantively_equal) | verified-already-fixed | Merged. `write_pipeline.promote` guards all four written surfaces with `_substantively_equal`, so a no-op synthesize produces zero tracked diff. WP04 guards this; not modified. |
| #2467 | pack-split (charter pack ecosystem) | deferred-with-followup | Out of scope for this charter-layer sanitization slice. **Follow-up: #2467** stays open (larger doctrine-pack epic). |
| #2216 | doctrine governance tiers | deferred-with-followup | Out of scope. **Follow-up: #2216** stays open (governance-tier work, distinct grain). |
| #2539 | pack trust root | deferred-with-followup | Out of scope. **Follow-up: #2539** stays open (pack-trust epic). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

Note: the `#2373` `in-mission` row resolves to `verified-already-fixed` as WP03/WP04's guards are approved/merged; it must be terminal before mission `done`.
