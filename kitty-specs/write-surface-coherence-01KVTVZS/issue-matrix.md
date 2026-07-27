# Issue matrix — write-surface-coherence-01KVTVZS

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2099 | single-authority-topology-cleanup precedent (read-side bifurcation) | verified-already-fixed | spec.md:12,148 — this mission is the write-side twin; converges across WP01–WP06 |
| #1878 | `_try_advance_ref` ff-advance correctness post-bifurcation | fixed | spec.md:88 FR-005 — addressed by the coord-helper governance WP (status-only coord writes) |
| #2062 | planning read path must not fall back to coord husk | fixed | spec.md:88 FR-006 — addressed by the read-path-no-coord-fallback WP |
| #2100 | ~53-site inline meta-reader backlog | deferred-with-followup | spec.md:90,158 — ≈3 touched sites routed (FR-009); remaining backlog deferred to its own sweep. Follow-up: #2100 |
| #1891 | `agent action implement --json` slice | deferred-with-followup | spec.md:160 — separate deferred slice, not folded here. Follow-up: #1891 |
| #2085 | acceptance-matrix C-010 gate slice | deferred-with-followup | spec.md:160 — separate deferred slice, not folded here. Follow-up: #2085 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
