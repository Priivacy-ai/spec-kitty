# Phase 0 Research — Mission A (Common Docs Doctrine & Reconciliation)

The substantive design was settled by the pre-spec research (`docs/engineering_notes/651-docs-consolidation/`) and the 5-lens post-spec squad. This consolidates the decisions the reconciliation ADR (IC-01) formalizes and the technical approach for the rulers (IC-03/04/05).

## D1 — Metadata SSOT = Candidate A (in-file frontmatter; inventory→lockfile)

- **Decision**: in-file frontmatter is the SSOT; the page-inventory is regenerated as a validated lockfile; `citation_refs` is dropped (6/568 populated — dead).
- **Rationale**: generator-native (the live DocFX site reads frontmatter, not the sidecar); standard-aligned (Common Docs mandates in-file); retires `LEAK-FRONTMATTER-MISMATCH` by construction.
- **Alternatives**: Candidate B (sidecar stays SSOT, frontmatter generated) — rejected: perpetuates the split-brain the consolidation exists to kill.

## D2 — DocFX redirect mechanism = generated meta-refresh stubs

- **Decision**: per old path, emit an HTML `<meta http-equiv="refresh">` stub page into the DocFX `_site` (a post-build step in `scripts/docs/`), keyed off a checked-in redirect map; a coverage check asserts every map entry produces a resolving stub.
- **Rationale**: DocFX and GitHub Pages have **no native alias/redirect** and no server-side rules (debbie); a client-side meta-refresh stub is the only mechanism that resolves on static Pages.
- **Alternatives**: `_redirects` (Netlify-only), server rewrite rules (no server), DocFX `uid`/`xref` (cross-link, not URL redirect) — all rejected.
- **Scope note**: Mission A *decides + records* this in the ADR + captures a baseline URL inventory approach; Mission B *applies* it.

## D3 — Glossary read-path

- **Decision**: the move of the human glossary markdown to `context/` MUST preserve (or regenerate) the dashboard's seed read-path; the doctrine-extraction source is the seed file.
- **Rationale**: the dashboard's `GlossaryHandler` reads `.kittify/glossaries/<scope>.yaml` **seed files** via `load_seed_file()`, **not** the human `glossary/contexts/*.md` (debbie code-truth). C-001 is only satisfiable if both representations are mapped — the ADR records which artifact moves and how the seed/extraction paths stay intact.

## D4 — Era-less-ADR migration

- **Decision**: the **20** ADRs that live only in flat `architecture/adrs/` (no era home) are 3.x by date → migrate to `adr/3.x/` (executed in Mission B; the plan + assignment recorded in the ADR).
- **Rationale**: closing the flat shim without migrating strands 20 real ADRs (violates NFR-004/SC-005). Total ADR count is **140**, not 99.

## D5 — `doc_status` namespace

- **Decision**: the frontmatter status key is `doc_status` (not bare `status`).
- **Rationale**: terminology-canon — bare `status` collides with the WP-lane status model (renata + daphne).

## D6 — Rulers ship report-only

- **Decision**: `related_validator`, `inventory_lockfile`, `anti_sprawl_ratchet` are authored as standalone scripts that **emit** violations and exit 0 (report-only), each with a self-test. Mission B flips them to exit-non-zero (blocking) against the cleaned tree.
- **Rationale**: gate-unmask-cannot-self-validate — a ratchet first enforced against the uncleaned tree cannot honestly police it; report-only lets us *measure* the baseline (NFR-003).

## D7 — DRG wiring

- **Decision**: wire the directive/styleguide/tactic nodes into `src/doctrine/graph.yaml` via `spec-kitty doctrine regenerate-graph`, freshness-gated with `--check`.
- **Rationale**: the canonical command exists (debbie). **Footgun (#1755):** the DRG generator had asymmetric-profile-edge / no-regen-command history — read it before wiring.
