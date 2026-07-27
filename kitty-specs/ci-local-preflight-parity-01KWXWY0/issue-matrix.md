# Issue matrix — ci-local-preflight-parity-01KWXWY0

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2283 | Delivery-topology: CI-only shards invisible pre-PR | fixed | Phase 3 delivers local pre-PR parity (venv lock-parity `88602f99` + residual runner) + the (c) boundary decision; factor-a (#2034) + c-dynamic (#2438) already shipped; c-static homed in CT7 #2077 / #2441 |
| #2034 | Marker-gate divergence (factor a) | verified-already-fixed | The `unit-contract-residual` gate already landed (`6e5453e6d`); WP02 `81d028bf` pins it (always-on + quality-gate.needs member, fault-injection red-first) — no re-add |
| #2438 | Review-time regression gate (c-dynamic) | deferred-with-followup | Discharges factor (c-dynamic); delivered in our PR #2438, PENDING its merge — boundary decision records it conditionally. Follow-up: #2438 |
| #2077 | CT7 mechanise-the-sweep (c-static home) | deferred-with-followup | (c-static/c′) retired-contract assert-absence owned by CT7 #2077 (sharpened payload); durable contract-ownership boundary filed as #2441. Follow-up: #2077 / #2441 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
