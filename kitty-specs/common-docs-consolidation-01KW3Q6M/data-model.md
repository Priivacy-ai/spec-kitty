# Phase 1 Data Model — Mission A

Mission A introduces doctrine artifacts and tooling outputs (no domain runtime entities, no DB).

## Doctrine artifacts (`src/doctrine/`)

- **Common Docs directive** (`directive/<id>-common-docs.directive.yaml`) — canonical doctrine-artifact format. Binds documentation to: the 13-section structure, in-file-frontmatter SSOT, and the delete-stale curation policy. **Invariant:** its id is referenced by the anti-sprawl ratchet (bound, not advisory — C-003).
- **Common Docs styleguide** (`styleguide/<id>-common-docs.styleguide.yaml`) — codifies the conventions (structure, frontmatter schema incl. `doc_status` + the SEO 50–180 `description` constraint, naming, `adr/<era>/`, the `related:` resolvable-path form, curation). **Invariant:** every codified rule maps to a live check (frontmatter→IC-04; `related:`→IC-03; structure→IC-05).
- **Common Docs tactic(s)** (`tactic/<id>-*.tactic.yaml`) — how-we-apply (place a doc; author an ADR with era + frontmatter incl. PROPOSED/superseded mapping; run the rulers). **Invariant:** DRG-wired with the declared relation types.
- **DRG** (`graph.yaml`) — gains the 3 nodes + relations; regenerated + `--check`-gated.

## Page-inventory lockfile (`docs/development/3-2-page-inventory.yaml`)

- **Generated** from frontmatter (no longer hand-maintained). Schema per row: `path`, `tag`, `divio_type`, `owning_workstream`, `current_target`, `notes` (+ `doc_status` if surfaced). **`citation_refs` is DROPPED** (D1). Rollup invariants preserved: completeness (every `.md` present), ownership, deterministic alphabetical diff.
- **State**: in Mission A the generator + the inverted freshness check exist and run **report-only**; the inventory is not yet authoritative (the backfill is Mission B).

## Ruler outputs

- **`related_validator`** → `{ checked_count: int (>0), dangling_edges: [{from, to}] }`; report-only exit 0.
- **`inventory_lockfile`** → a generated lockfile; the freshness check compares `generated == committed`.
- **`anti_sprawl_ratchet`** → `{ violations: [{condition, path}], baseline_count: int, directive_ref: <id>, floor: [13 section names] }`; report-only exit 0.

## Reconciliation ADR

- The decision record carrying D1–D7 (the 7 FR-001 decisions). Authored in `architecture/3.x/adr/`; **accepted + merged** is the C-001 boundary.
