# Issue matrix — post-merge-write-authoring-finish-01KYRRM5

One row per issue referenced in spec.md. Terminal verdicts required before mission `done`.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3033 | Post-consolidation (E2) writes fail against a deleted Target Ref | in-mission | WP02 (red-first) + WP03 (phase-aware CONSOLIDATED resolution) + WP04 (fix-green); terminal `fixed` at mission `done` |
| #3073 | Composed writers stage before the routability probe (residue on refusal) | in-mission | WP04 (single-locus staging thunk) + WP05/WP06 (per-writer call-site + residue regressions); terminal at `done` |
| #2318 | Deterministic accept: negative invariants + diagnose + stale verdict + prompt | in-mission | WP05 (register/execute, --diagnose hardening, fresh verdict, prompt rewire); terminal at `done` |
| #1738 | Completeness gate misses same-repo URL refs; no source-file provenance | in-mission | WP06 (single-regex same-repo URL + source_file provenance); terminal at `done` |
| #3080 | Make `consolidate` canonical for the lane-consolidation sense | deferred-with-followup | FOUNDATION ONLY in-mission (WP01: ADR + glossary + drift-ratchet guard); the full command/code/docs rename remains #3080 — **DO NOT CLOSE** #3080 at mission done |
| #2160 | Epic: coord topology — unify artifact authority | deferred-with-followup | Parent epic — advanced by this mission, NOT closed here |
| #1676 | Epic: deterministic structured authoring | deferred-with-followup | Parent epic — advanced by this mission, NOT closed here |
| #3044 | Epic: review-artifact integrity | deferred-with-followup | Parent epic — advanced by this mission, NOT closed here |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

**Closure dispositions (operator-confirmed):** #3033/#3073/#2318/#1738 → closeable (terminal `fixed`) at merge. **#3080 → DO NOT CLOSE** (foundation only; full rename remains). Epics #2160/#1676/#3044 → NOT closed here.
