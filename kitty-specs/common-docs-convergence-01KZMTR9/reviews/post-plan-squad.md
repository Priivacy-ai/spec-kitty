---
title: Post-Plan Adversarial Squad — Common Docs Convergence
doc_status: active
updated: '2026-08-10'
---
# Post-Plan Adversarial Squad Review

Mission: `common-docs-convergence-01KZMTR9`. Point-cut: post-plan, pre-tasks.
Squad: 4 lenses (DAG/decomposition, tooling-feasibility, gate-coverage, occurrence-map/bulk-edit),
verified against the actual `scripts/docs/` code + CI workflows. Dispositions per
`contracts/adversarial-evidence-contract.md`: `changed` unless noted.

## CRITICAL / HIGH — folded into plan + occurrence_map
- **Cumulative redirect spine is unachievable as written** (tooling #1, occ C1). `derive_redirect_map`
  overwrites the whole map from ONE occurrence-map; `_relocate` applies a single move (no transitive
  closure). The occurrence_map had NONE of the prior closed mission's 29 moves → regen would drop ~52
  baseline URLs (NFR-010 fail). **Changed:** occurrence_map must encode collapsed `baseline→FINAL`
  moves incl. the prior mission's spine, + a test that `regenerate-map` reproduces all prior entries +
  new; OR a code change (`--merge`/fixed-point). Flagged as an open build decision (see plan).
- **Pre-merge DocFX job was advisory → doesn't block** (gate CRITICAL). **Changed:** register the PR
  build as a REQUIRED check; block-vs-advise steps made explicit (zero-error build blocks).
- **IC-11 modeled as a per-mover role a WP graph can't express** (DAG P1). **Changed:** IC-11 is a
  single TERMINAL reconcile WP that regenerates all shared manifests once after 04–07/09/10.
- **occurrence_map.yaml + common-docs.styleguide.yaml were unguarded multi-writer files** (DAG P0/P2).
  **Changed:** both added to C-011 single-threaded surfaces; movers emit per-WP ledger fragments IC-11
  merges; the mover↔IC-11 line drawn (movers run in-tree relative-link fixes on owned files ONLY; never
  touch redirect_map/toc/docfx/llms/plans).
- **IC-03 can't be green pre-move** (DAG P1). **Changed:** split IC-03a (build resolvers + grep +
  extended-lint code, advisory foundation) / IC-03b (flip structural invariants to blocking + final
  green, terminal after IC-11).
- **IC-05/IC-10 double-own docs/adr/** (DAG P1). **Changed:** IC-05 owns all `adr/<era>/` structure
  incl. era-index; IC-10 keeps only non-era dated-prefix + `doc_status` polish; #2227 split stated.
- **IC-10 is not a parallel leaf** (DAG P1, gate HIGH). **Changed:** IC-10 renames → occurrence-map;
  edges IC-10→IC-02, IC-10→IC-03, IC-10→IC-11 added.
- **NFR-008 presence/description + SC-007 placement lack a touched-set gate** (gate HIGH×3). **Changed:**
  add git-diff touched-set gates for audience-presence + description-band; placement check
  (internal-audience→development/, external→guides/) as a touched-scoped diff-aware check (NOT the
  whole-tree lint — tooling #3).
- **NFR-009 fidelity was reviewer-only** (gate HIGH). **Changed:** per-page fidelity ledger (claim→code
  backing) as a required review artifact; `check_cli_reference_freshness` runs on PR.
- **IC-06 too big + hidden config overlap** (DAG P1). **Changed:** split by tree (guides WP /
  development WP); the single `structural_lint_config` routing edit isolated into its own sub-WP.
- **IC-08 rewrite still open-ended** (DAG/gate). **Changed:** enumeration produced by /spec-kitty.tasks
  strictly from the IC-04..07 touched-set, numeric per-WP page ceiling; edge = "final path settled
  (post-IC-07)".
- **IC-07 persona kebab-rename would break IC-01's migrated audience refs** (DAG P2). **Changed:** fold
  persona kebab-rename into IC-01; migrate `audience:` values directly to final kebab paths.
- **Occurrence-map landmines** (occ C2–C6, M7–M10): `spec-kitty-mission-workflow.md` is a canonical
  authority doc (refs in lint_canonical_producers.py + canonical-producer-lint.yml + 2 tests) →
  destination architecture/authority NOT guides; `research/`→plans/research VIOLATES C-001 → integrations
  or RETIRE; `docs/output/` retire breaks documentation mission.yaml deliverables → repoint; README logo
  is an absolute HTML `<img>` the link-fixer won't touch → manual rewrite; `spec-driven.md` move breaks
  test_current_charter_paths.py → enumerate; `doctrine/` routes to `src/doctrine/` per config (not
  architecture|guides); `docs/archive/` unrepresented + holds 14 baseline redirect targets → decide;
  `code_symbols` must include the `MISSION_SLUG` constant. **Changed:** occurrence_map corrected.

## MEDIUM — deferred / flagged as open build items
- **Single-root as a blocking lint reverses #2851** (tooling #4). **deferred_with_rationale:** keep
  structural-invariant enforcement as the terminal IC-03b verification + curation, NOT a standing
  per-PR blocking lint, to respect the recorded retirement of the anti-sprawl ratchet. Reconcile with
  #2851 before adding any standing single-root gate.
- **Reverse reconciliation gate** (gate MEDIUM): git `--find-renames` ⊆ occurrence-map — added to IC-03a.
- **Inline body-link integrity** (gate MEDIUM): add `relative_link_fixer --check` to the blocking PR set.
- **#3147 whole-tree freshness reds** (gate MEDIUM): scope the freshness gate to changed paths / emit a
  baseline-diff classification — added as an IC-03a sub-item (was C-013 awareness-only).

## Simplifications / confirmations (no work needed)
- `--occurrence-map`, `coverage`, `check-map`, `regenerate-map` ALREADY exist — IC-02 is "repoint the
  closed-mission default + always pass the flag", not "add a flag."
- `build_cli_reference.py` + `check_cli_reference_freshness.py` exist — NFR-009 regen is backed.
- `assert_examined_floor` exists; `related_validator` extension viable (must handle scalar audience value).
- docfx already installed in CI (`docs-pages.yml`) — the PR build recipe is a copy.
- Constraint safety verified: C-002 (fixtures untouched), C-003 (authority paths not relocated),
  C-004 (theme preserved), C-005 (rollups untouched), all 8 bulk-edit categories classified.
