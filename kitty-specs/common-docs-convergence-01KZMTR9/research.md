# Research — Common Docs Convergence

Phase 0 decisions. Grounded by the post-spec adversarial squad (5 lenses) — see
`reviews/post-spec-squad.md`. Format: Decision / Rationale / Alternatives.

## D1 — Audience metadata: formalize what exists (not copy built-in)
- **Decision**: Treat the existing `docs/context/audience/` catalog as the docs persona SSOT. Make `audience:` a resolvable repo-relative `.md` path into it; canonize the field in `042-common-docs` + `common-docs` styleguide + `047`; migrate the 13 free-text values; add a non-vacuous resolver test.
- **Rationale**: The catalog (10 project personas) and the field already exist but are disconnected; the catalog is richer and more specific than the 5 generic built-in pack personas. Copying built-in personas over it would fork a canonical SSOT (DIRECTIVE_044 violation) and collide with #3024.
- **Alternatives**: copy built-in personas (rejected — SSOT fork); test-only without migrating values (rejected — leaves field/catalog disconnected, does not realize the ask).

## D2 — How-to home: audience-based routing
- **Decision**: Contributor/maintainer how-tos → `development/`; user-facing how-tos → `guides/`. Update `structural_lint_config.concern_bucket_to_section`/`guides_boundary` to this audience-aware routing with recorded rationale.
- **Rationale**: The loaded config routes `how_to → development/` and forbids `guides/` as a how-to target, but `guides/` currently holds ~21 how-tos. An audience split reconciles config with reality, ties into the audience catalog (internal/external), and is intuitive for readers.
- **Alternatives**: strict config (all how-tos → development/, biggest churn, moves user how-tos out of the intuitively-named section); type-only defer (punts the IA decision).

## D3 — Redirect/move tooling model (corrected)
- **Decision**: Author this mission's own `occurrence_map.yaml` as a **cumulative** move spine; drive `redirect_stub_generator.py`/`relative_link_fixer.py` with `--occurrence-map <this mission>`; regenerate `redirect_map.yaml` (DERIVED, never hand-edit); treat `redirect_baseline_urls.json` as immutable; preserve the prior closed mission's 149 entries so coverage does not regress; reconcile cross-mission single-writer ownership (#2358).
- **Rationale**: The tooling is real but hardcodes a different, closed mission's slug/occurrence-map; the map is derived and the baseline is the coverage denominator. The original spec's "edit map + baseline per move" was wrong and would break coverage.
- **Alternatives**: improvised redirect stubs (rejected — DIRECTIVE_044); per-move map edits (rejected — corrupts derived artifact + denominator).

## D4 — Verification gates: pre-merge, non-vacuous
- **Decision**: Add a pre-merge DocFX build + redirect-coverage + seo_verify job on `pull_request`; extend the structural-lint asset to check mission invariants (single-root, sanctioned-sections-only, one-index-per-dir, Divio-type presence); add occurrence-map⊆redirect-map + stale-`docs/**`-path grep gate; add a charter authority-path resolution test; make the audience + related resolvers non-vacuous.
- **Rationale**: The authoritative DocFX/SEO/redirect gates run only on push to main/2.x, so NFR-001/FR-017 were unverifiable pre-merge; the current structural-lint is green at 0/699 and measures none of this mission's goals (vacuous NFR-003); resolvers with a 0-examined pass silently rot (the exact class #3273 closes).
- **Alternatives**: rely on deploy-time gates (rejected — post-merge discovery); drop NFR-003 (rejected — lose the durable mechanical gate).

## D5 — Rewrites: bounded, fact-safe, split from moves
- **Decision**: FR-014 rewrites operate on an **enumerated per-WP page list** with a scanability checklist (lead summary, H2/H3 structure, tables/lists over long prose), are prose-only and diff-reviewed, and are **separate reviewable WPs** from the mechanical moves. Behavior-documenting pages are regenerated from source (`build_cli_reference.py`), not hand-rewritten. NFR-009: no rewrite alters a factual claim unverified against current code.
- **Rationale**: "rewrite every touched page for scanability" is unbounded and unmeasurable, and mixing editorial with mechanical review hides fact drift (publication-authority: code is source of truth).
- **Alternatives**: fold rewrites into movers (rejected — conflates reviews, unbounded); defer all rewrites (rejected — operator chose to include them).

## D6 — Concurrency: single-threaded shared surfaces
- **Decision**: Shared manifests (`redirect_map.yaml`, `toc.yml`, `docfx.json`, `llms.txt`, per-section toc, inventory lockfiles) and `docs/plans/**` link-fixes are edited by exactly one nav/redirect-reconcile owner (IC-11); mover WPs record move intent in the occurrence-map and never touch shared manifests concurrently.
- **Rationale**: A worktree-per-WP model would otherwise produce guaranteed merge collisions on the same YAML keys across every mover.
- **Alternatives**: parallel movers each regenerating manifests (rejected — collisions); no worktree isolation (rejected — mission uses lanes).

## Supply-chain security (DIRECTIVE_051 / supply-chain-install-safety)
- **Decision / posture**: **No new runtime dependencies are added.** All tooling (`docfx`, `ruamel.yaml`, `pytest`, `scripts/docs/*`) is already present. The new pre-merge DocFX job invokes the already-pinned `docfx` toolchain via existing CI patterns; no new registry package, no new lifecycle scripts.
- **Conclusion**: registry authenticity / freshness / lifecycle-script / Node-LTS checks are **N/A for a no-new-dependency change** — recorded here so the absence is deliberate, not an omission (advisory, non-blocking per the plan step contract).

## Adversarial evidence (mandatory for plan/research)
- The **post-spec** adversarial squad ran (5 lenses); every contested finding's disposition is recorded in `reviews/post-spec-squad.md` and folded into the revised spec — dispositions: `changed` (spec corrections FR-001/019/021, C-010, NFR-003/009/010), `accepted` (structural findings → IC map), `deferred_with_rationale` (#3265 remainder, `docs-freshness` required-check hazard, `_published_pages` re-walk). No contested finding was silently dropped.
- A **post-plan** adversarial squad runs next; its dispositions will be recorded in `reviews/post-plan-squad.md` per `contracts/adversarial-evidence-contract.md`.
