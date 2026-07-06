# Issue matrix — census-freshness-loc-insensitive-01KWVD6Y

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2386 | bulk-edit finalize fix — census-staleness fold instance cited in #2416 | fixed | LOC-tax removed at `live_derived_worklist`; a bulk_edit LOC shift no longer reds the gate (SC-001 reproduction verified GREEN) |
| #2414 | session-banner version-compare fix — census-staleness fold instance cited in #2416 | fixed | the session_presence LOC shift that forced fold 1d533e94c no longer reds the gate (membership/routing unchanged → GREEN) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
