# Issue matrix — dev-assist-retire-path-hardening-01KXAVR0

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

`in-mission` = being fixed by a WP in this mission (non-terminal; must reach a terminal verdict —
`fixed` / `verified-already-fixed` / `deferred-with-followup` — before mission `done`). Parent /
sibling-mission / deferral-target issues carry a documented follow-up.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2071 | Epic: Tests as scaffold, not friction | deferred-with-followup | Follow-up: #2071 — parent epic; this mission is one sibling under it, epic stays open. |
| #2073 | CT2: de-theater the security path-validation tests (8 xfail masks) | fixed | WP01 (approved; review a09189b5, LAND) — de-masked the 8 xfails + case-variant skip, strict red-first ATDD, hardened `validate_deliverables_path` (44 green/0 xfail; all vectors rejected). Runtime-wiring out of #2073's test-scope → deferred to #2539/#2536. |
| #2557 | Runtime-bridge dev-assist retire/split (post-slice cleanup) | fixed | WP02 (approved; review a106606a, LAND) — retired 3 family-guard duplicates + inert `test_nfr006_timing_seed`, NARROWed `test_bridge_io` to its 2 uncovered public symbols, KEPT the unique untracked-reexport test; family guard untouched + planted-regression verified; 604 green. (LOW docstring tidy in `test_bridge_cores.py` deferred to wrap-up.) |
| #2565 | Consolidate fragmented per-seam re-export identity batteries | fixed | WP04 (approved; merge 54-symbol `{symbol→residual}` guard + ×8 import guards folded) + WP05 (approved; tasks 129-symbol guard) + WP06 (approved; heavy-seam identity retirements). Doctor family already single-guarded (no work). Interception proofs KEPT as unique routing coverage per review (retirement residual → sibling #2075). All three reviews LAND. |
| #2076 | CT5: stale golden-count + fakeable-DoD / dead-assertion tail | deferred-with-followup | WP03 addresses the doctor golden-count duplicates + the mission `..._gap_closed` one-shot; the broader 182-wide `assert len==N` tail + other dead-assertion files remain → #2076 stays open. |
| #2077 | CT7: test-hygiene directive + positional-anchor ban gate | verified-already-fixed | Closed; the ban gate shipped. This mission does not touch it; the ban-gate HOLE it left is tracked separately as #2564 (sibling mission). |
| #2539 | Epic: Pack trust, verifiability & verified distribution | deferred-with-followup | Runtime-wiring of `validate_deliverables_path` (path-containment/trust surface) deferred to this epic's ship-code-as-assets design (Follow-up: #2539); mission delivers verified latent hardening only. |
| #2536 | Pack activation must warn when a pack ships executable code assets | deferred-with-followup | Follow-up: #2536 — specific home for the deferred validator runtime-wiring (trust surface). |
| #2564 | test-gate hole: positional line-anchors evade the #2077 ban | deferred-with-followup | Sibling mission (gate-hardening) under #2071 — out of scope here. |
| #2074 | CT3: meta/mission test factory + production-shaped ULIDs | deferred-with-followup | Sibling mission (fixtures/data realism) under #2071 — out of scope here. |
| #2075 | CT4: re-point mock-wiring 'assert HOW not WHAT' tests | deferred-with-followup | Sibling mission (wiring-only triage) under #2071 — out of scope here. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a WP in this mission; must reach a terminal verdict before mission `done`).
