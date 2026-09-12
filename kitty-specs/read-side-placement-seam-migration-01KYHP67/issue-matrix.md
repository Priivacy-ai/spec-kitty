# Issue matrix — read-side-placement-seam-migration-01KYHP67

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2922 | Read-side "whack-a-read" migration | fixed | WP02 classification ledger (`docs/development/read-side-seam-classification.md`) → WP03–WP07 migrated all 72 fail-loud sites onto `PlacementSeam.read_dir(kind)` (16 stay-lenient preserved per ledger) → WP08 structural gate `tests/architectural/test_no_read_side_bypass.py` (26 passed; allow-list == the 16 ledger stay-lenient sites, shrink-only + twin-guard) makes new bypasses unrepresentable. All 8 WPs approved. |
| #1878 | Parent of read-side placement port | fixed | Closed by the #2922 work packages WP02–WP08 (see row above); the read leg now routes through the kind-aware seam and is gate-enforced. |
| #2921 | Fix repair_lane_mismatch frontmatter corruption | fixed | 8863d7691 (WP01) |
| #2920 | Placement seam hardened (write+read port) | verified-already-fixed | https://github.com/Priivacy-ai/spec-kitty/pull/2920 (pre-mission; seam already landed) |
| #2966 | Write-target / read-leg consolidation | deferred-with-followup | Part-1 remainder (`_mission_id` PRIMARY-leg) fixed here — WP09 `aae140e8f` (FR-008); `_synthesize_claim_anchor` half already fixed by Mission E. Follow-up: #2966 parts 2/3/4 → Missions B & C |
| #2964 | Leftover terminology mismatch (feature* → mission*) | deferred-with-followup | Out of scope per C-004; Follow-up: #2964 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
