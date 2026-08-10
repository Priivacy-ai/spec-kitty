---
title: Post-Spec Adversarial Squad — Common Docs Convergence
doc_status: active
updated: '2026-08-10'
---
# Post-Spec Adversarial Squad Review

Mission: `common-docs-convergence-01KZMTR9`. Point-cut: post-spec, pre-plan.
Squad: 5 profile-loaded lenses (Common-Docs curator, canonical-source/SSOT, architect/scope,
premortem/reviewer, upstream ticket sweep). All findings below were adjudicated and folded into
the revised `spec.md` (revision 2026-08-10) unless marked deferred.

## Grounding discoveries (reshaped the mission)
1. `docs/context/audience/` (singular) **already exists** — mature project persona catalog
   (internal: maintainer, lead-developer, system-architect, ai-collaboration-agent, cli-runtime,
   project-codebase; external: architect-evaluator, tech-lead-evaluator, product-manager-evaluator,
   project-owner). Richer than the 5 generic built-in pack personas.
2. `audience:` frontmatter **already used on 13 pages** — but as FREE-TEXT labels ("end-users",
   "packagers", …), NOT resolvable links to the catalog. No resolution test; not canonized in doctrine.
3. `structural_lint_config` routes `how_to → development/`, `reference_policy → development/`, and
   pins `guides_boundary` (guides/ not a how-to relocation target) — conflicting with the original
   guides-as-how-to-home framing.
4. `development/` and `assets/`/`templates/spec-kitty/` are sanctioned beyond the nominal 13 — the
   "only 13, 14th = red-line" framing was wrong; converge to the config's actual sanctioned set.
5. Canonical move tooling is SINGLE-WRITER: `redirect_stub_generator.py` hardcodes a closed
   mission's slug/occurrence-map; `redirect_map.yaml` is DERIVED do-not-hand-edit;
   `redirect_baseline_urls.json` is the immutable coverage denominator.
6. The DocFX build / SEO / redirect-coverage gates run only on push to main/2.x — NOT on PRs.

## Operator decisions
- **D1 (how-to home):** audience-based split — contributor how-tos → `development/`, user-facing →
  `guides/`; update `concern_bucket_to_section`/`guides_boundary` accordingly.
- **D2 (audience):** formalize what exists — resolvable links into `docs/context/audience/`, migrate
  the 13 free-text values, canonize the field, add a non-vacuous resolution test. Pack personas stay
  the separate consumer baseline; coordinate #3024.

## Findings by lens (folded)
**Curator / Common-Docs:** section-canon contradiction (dev/assets) → Definitions' sanctioned set
(C-006/NFR-007); how_to→development config conflict → FR-009 audience routing; audience not
canonized → FR-002; redirect stubs need "Redirect stub:" prefix → FR-022; open allowlist / undefined
"in-scope" → Definitions; missing 50–180 description band → NFR-008; audience must NOT enter
frontmatter_required_fields → C-012; migrations delete-stale → FR-024; FR-012 vs #2227 → FR-015.

**Canonical-source / SSOT:** tooling model wrong (derived map / immutable baseline / cross-mission
ownership / cumulative spine) → FR-021, C-010, NFR-010; blind-copy personas forks SSOT → FR-001;
FR-016 repaired only 1 of 3 dead authority paths → FR-019; `--strict`/check-map/coverage not invoked
→ FR-017/NFR-002; rollups owned across ~10 lanes → C-005.

**Architect / scope:** shared-manifest contention → C-011 single-threading; rewrite dimension
unbounded/unmeasurable → FR-014 enumerated+checklist; guides double-move (FR-008 vs FR-018) → merged
into one guides WP; plans-boundary bleed → C-001+C-011; rollup cross-mission collision → C-005;
NFR-003 vacuous → FR-023 extended lint; gameable allowlist / undefined in-scope → Definitions;
explicit DAG + serial-movers concurrency → C-009.

**Premortem / reviewer:** authoritative gates deploy-only → FR-017 pre-merge DocFX build job;
rewrite fact-drift unguarded → NFR-009 + FR-014 (regenerate behavior docs from source); bulk-rename
hits no-test paths (`gap_analysis.py`) → FR-018 grep gate + pin; audience validator vacuity → FR-003
non-vacuity floor; authority-path resolution untested → FR-019; redirect baseline desync → NFR-010.

**Upstream ticket sweep:** FOLD/CLOSES #3273, #2215 (arch era-README collapse → FR-008), #2887 (ADR
date-sequence → FR-015), partially #2227; COORDINATE #3024 (audience tree), #2358 (moves-ledger home
→ FR-021), #3147 (whole-tree freshness reds → PR-body caveat), #2302 (codify docs doctrine — keep
aligned); RELATE #2314 (parent epic), #3227, #2440, #3286.

## Deferred (recorded, not active scope)
- #3265 SEO-PR-gate: partially addressed by FR-017; remainder tracked separately.
- `docs-freshness` required-check hazard: awareness-only (documented in-code).
- `_published_pages._count_raw_matches` re-walk: opportunistic campsite fold only.
- `docs/plans/` triage (WP-F): follow-on mission.

Full working synthesis (with file:line evidence): see the mission plan's research inputs.
