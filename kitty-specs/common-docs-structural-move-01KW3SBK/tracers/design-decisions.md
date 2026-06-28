# Tracer: Design Decisions — Mission B (Common Docs Structural Move)

> Standing-orders tracer (experiment #2095). The non-obvious calls + their rationale.

## Seeded at implement-start (2026-06-27)

- **Topology: FLATTEN to `single_branch` (operator-approved).** This is a `bulk_edit`
  mission where WP03/WP08/WP09/WP10/WP12 legitimately co-edit `docs/` by occurrence-
  CATEGORY (the occurrence-map partition), which file-disjoint lane isolation cannot
  express. Lane collapse produced cyclic `depends_on_lanes`. Flat (WP-level status
  gating) is the structurally-correct topology AND it kills the #2160 coord/planning
  split-brain that bit Mission A's tracers 3×. Coord branch/worktree carried no unique
  content (only regenerable status-bootstrap chores), so teardown was lossless.

- **`kitty-specs/**` is `do_not_change`.** Historical mission artifacts are immutable
  snapshots (Terminology Canon); their doc-path references record the tree as it stood
  at each mission's close. Rewriting the 1621 in-tree refs (453 files) would mutate the
  historical record for zero benefit (kitty-specs/ isn't published; WP07 redirect stubs
  cover any external continuity). Strikes the blast radius 2920→1299 occ / 751→298 files.

- **The 71 `architecture/` back-compat symlinks are dereferenced + dropped, NOT converted.**
  47 in `adrs/` + 24 in `2.x/adr/` are symlinks to canonical era files — not byte-copies.
  Converting an in-era symlink would dangle (relative target breaks post-move) AND inflate
  the unique census past 117. WP06 converts realpath-unique real files only; the census-117
  + non-vacuous invariance (compared==117) prove nothing was skipped.

- **Ownership disjointing for acyclic lanes (occurrence-map-governed-leeway model).**
  Cross-cutting bulk-edit WPs declare ONLY a thin authoritative surface (their tool / a
  ledger / their sole target file) and do the broad edit as occurrence-map-governed
  leeway, category-disjoint (frontmatter-fields vs prose-refs vs serialized-keys). Applied
  to WP08 (bulk_ref_rewrite.py), WP12 (section ledger), WP10/WP04/WP15. Result: 15 one-WP
  acyclic lanes.

- **The occurrence map names the TRACKED source, not generated artifacts** (see
  tooling-friction): read #6 → `charter.md`, not the gitignored/generated `governance.yaml`.
