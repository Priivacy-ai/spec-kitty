# Issue matrix — single-mission-surface-resolver-01KVGCE8

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2040 | Single mission-surface resolver — finish strangling the coord/primary read/write desync (driver) | fixed | whole mission delivered: all 8 WPs approved; sole resolver (WP06) + FR-002 gate (WP02) + guard (WP08) |
| #2010 | Read-path resolver unification not behavior-equivalent (residual being completed) | fixed | FR-002 deletion gate (WP02 approved) + FR-005 ambiguous-selector translation (WP05 approved) + collapse (WP06 approved) |
| #2007 | Parent epic — coord/primary read/write desync | deferred-with-followup | mission delivers the selection-resolver-unification slice (FR-001/FR-002/FR-007); the read/write-desync epic continues for other facets — #2007 remains the tracked home |
| #1716 | Coordination topology coherence / coord-empty fallback policy | fixed | FR-006 coord-empty two-path hard-fail + ADR 2026-06-19-1 → WP06 (T024/T025) approved |
| #15 | Typed read-path error flattened through next/mission_runtime (#2010 bug #15 family) | fixed | FR-005 `MissionSelectorAmbiguous`→`ActionContextError` at 2 boundary sites → WP05 approved (live red→green) |
| #1900 | Drain the topology-ratchet C-002 allowlist (status_transition.py = 5th selection site) | fixed | FR-007 predicate migration + allowlist drain (ratchet bites) → WP06 (T022/T023) approved; SC-005 proven |
| #1993 | Extraction-without-adoption shadow-path risk (C-002 forbids a new parallel resolver) | fixed | C-002 migrate-don't-wrap honored; collapse removed/migrated resolvers (WP06), guard locks zero-bypass (WP08/FR-004) approved |
| #1868 | Canonical seams "exist in name only" — bind authority to a seam + guard | fixed | FR-001 `resolve_status_surface_with_anchor` sole authority (WP06) + FR-004 load-bearing guard (WP08) approved |
| #1918 | `_mid8_from_primary_meta`/`resolve_declared_mid8` cascade — separate seam | deferred-with-followup | spec.md Out of Scope; tracked in its own issue #1918 (not closed by this mission) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
