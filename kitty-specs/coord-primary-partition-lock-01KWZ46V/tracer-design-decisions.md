# Tracer: design decisions

Append design choices + rationale as they are made; assess at close. Full rationale trail: `research.md` (D1–D13).

- **[specify] Seeded late (2026-07-08).** Key binding decisions below (see research.md for evidence).
- **C-001 (centerpiece):** one topology-aware placement seam is the single access point for "where do I store/read artifact kind K?"; a PRIMARY answer is NOT license to bypass it. No parallel/shadow authority (Directive-044).
- **Partition (settled):** coord = lifecycle (status/notes/trace/issue-matrix/move-task); primary = stable planning (spec/plan/WP outlines); no-coord topology → all primary. Ratifies #2106/#2113; supersedes #1716's original "Locked Architecture Decision".
- **Extend, not build:** the SSOT (`artifact_home_for`/`MissionArtifactHome` + frozensets) and the ratchet (`test_no_write_side_rederivation.py`) already exist — formalize/extend them.
- **D11 fail-closed:** the `if …is None: CommitTarget(ref=<checkout>)` legacy fallbacks are resolved require-canonical (structured error), not silent runtime fallback. Legacy support via migration, not a shadow path.
- **RETROSPECTIVE (H-1):** seam delegates its RETROSPECTIVE leg to the existing `resolve_retrospective_home` (#2119) — no second authority.
- **Topology is 2×2** (`SINGLE_BRANCH`/`LANES`/`COORD`/`LANES_WITH_COORD`), routed by `routes_through_coordination`; read STORED meta.json topology, never the on-disk husk.
- **Open architecture question (from the operator's #2404 note, 2026-07-08):** whether `ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT` should flip from `_PLACEMENT_ARTIFACT_KINDS`→`_PRIMARY_ARTIFACT_KINDS` (the swappable-locus fix for #2404). Shelved as an architecture decision under #2160/#1716; may belong to this mission's family. NOT in current WP scope (WP08 only asserts the read-partition for #2404-lite).
