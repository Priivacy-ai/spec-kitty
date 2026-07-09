# Tracer — Tooling Friction

Mission `doctrine-template-asset-kinds-01KX2YQ7` · #2495 (P0) + #2469. Seeded with known friction.

## Watch-list carried in
- **F1 — Add-a-member exhaustiveness.** A new ArtifactKind/NodeKind member silently misses switch/iteration/mapping
  sites (KeyError, dropped node, or a comprehension that skips it). Cover the enumerated surfaces (tracer-design D5)
  and add a new-member guard test (C-005) so the NEXT kind can't regress it.
- **F2 — Doctrine changes trip CI-only shards.** terminology guard + docs-freshness + the pack-validator arch tests
  run in CI's integration-tests-core-misc; run them LOCALLY before push (resolver-mission lesson: full arch suite
  before hand-off, not just targeted).
- **F3 — .contextive / glossary regeneration.** If a new doctrine term is added, the glossary source (docs/context/*)
  is the edit point; regenerate .contextive via scripts/generate_contextive_glossaries.py, don't hand-edit the yaml
  (resolver-mission lesson).
- **F4 — Forward-compat trap (NFR-003).** The assets/<pack>/ convention must not assume the current single built-in
  tree — #2467 pack-split will re-layout. Design the path resolution pack-relative, not built-in-absolute.
- **F5 — Doctrine artifacts are shipped** (installed into consumer projects via upgrade/migrations). A new kind's
  directory + any generated agent/skill surface must flow through the migration + release scripts if user-visible.

## Friction encountered during implement
_(append dated entries here)_
