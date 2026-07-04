# Issue matrix — relocate-saas-sync-flag-to-core-01KWQ3RV

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2252 | Relocate is_saas_sync_enabled out of saas/rollout.py to remove last CORE↛INTEGRATION allowlist exemption | in-mission | WP01 GREEN commit 04a96715e relocates the reader to `core/saas_sync_config.py`, repoints `readiness/coordinator.py`, empties `ALLOWLIST`, and tightens the ratchet to `== 0`. Terminal closure pending WP02 (ADR + stability-contract recording). |
| #2172 | Enforce CORE↛INTEGRATION boundary in-place (#614) | verified-already-fixed | Boundary guard `tests/architectural/test_integration_boundary.py` is present and enforcing; PR #2172 MERGED. This mission builds on that guard and removes its sole exemption. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
