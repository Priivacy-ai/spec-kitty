# Issue matrix — contract-ownership-boundary-01KWYRE5

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2441 | Shared contracts + their retirement are not a modeled, owned artifact | in-mission | The MVP delivers the modeled owned artifact — Contract Registry (schema+manifest+loader), `doctor contracts` validator, advisory static-arm sweep, and a parity proof (WP01 `f2c2c92` + WP02 `3f977c2` + WP03 `041d3f1`, all approved). Closes #2441's core gap; the higher-blast mechanism-adoption arms are Follow-up: #2441 |
| #2077 | CT7: mechanise the retired-literal absence sweep into one content-anchored driver | deferred-with-followup | Follow-up: #2077 — WP02's static-arm sweep IS the #2077 payload but **advisory** in v1; the enforcing sweep that fully discharges #2077 is deferred with the enforcing-driver mode (NFR-004) |
| #2438 | Dynamic review-time regression gate (`pre_review_gate`) | deferred-with-followup | Follow-up: #2438 — the dynamic arm (wiring `pre_review_gate` to read `consumers.test_shards`) is explicitly out of scope; #2438 tracks it |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.
