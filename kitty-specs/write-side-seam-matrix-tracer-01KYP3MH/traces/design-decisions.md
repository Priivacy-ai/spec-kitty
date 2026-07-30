# Tracer: design-decisions

Append design decisions taken *during* implement that the spec/plan did not already
fix (a schema shape, a partition call, the `%O` lineage decision in WP01's ADR).
One entry per decision: `YYYY-MM-DD · WP## · actor · <decision + rationale + alternatives>`.

Seeded at planning 2026-07-29. WP01's ADR `%O`-partition decision (E-B) should be
mirrored here when taken.

---

2026-07-29 · WP01/WP11 · claude+architect-alphonso · **Merge %O is topology-resolved, not WP01's lane base (E-B).**
Investigation (opus, on merged base) confirmed the seam resolves ISSUE_MATRIX/ACCEPTANCE_MATRIX placement
topology-dependently (resolution.py:1602-1607): PRIMARY in single-branch/lanes, COORD worktree in coord-topology.
Matrices are COORD-partitioned and serialize onto the single coord worktree (commit_router.py:248-306), never
diverging on lane branches. Therefore FR-008 durability draws %O from the seam-resolved surface's own lineage
(coord for this mission's topology), NOT WP01's PRIMARY lane base. WP01/FR-009 governs PRIMARY-partition (planning)
durability through lane consolidation only. Decision: soften WP11→WP01 (drop the hard dep); the driver contract now
states %O = seam-resolved matrix surface per topology. Alternatives rejected: (a) hardcode %O to primary lane base
(wrong — matrices are coord); (b) hardcode to coord (wrong for flat topology). Evidence: artifacts.py:172-183,
resolution.py:1211-1217, commit_router.py:248-306, merge.py:94-103, merge_driver.py:347-364.
