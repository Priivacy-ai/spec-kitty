# M2 tracer — approach

Append approach decisions as the mission runs.

- Two disjoint emit passes (#3605 procedure rationale via `_reference_edge_kwargs`;
  #3604 net-new governance-profile.yaml → `mission_type --scope--> gov`) that share
  only the single golden re-ledger.
- #3488 delivery is verify-and-close: no code gap on current main → doc-surfacing +
  net-new FR-008 anti-divergence test.
- Golden re-ledger is a dedicated final WP, run after M3 (#3617) lands + rebase.
