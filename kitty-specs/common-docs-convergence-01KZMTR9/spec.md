# Mission Specification: Common Docs Convergence

**Mission Branch**: `docs/common-docs-cleanup`
**Created**: 2026-08-10 · **Revised**: 2026-08-10 (post-spec adversarial squad + grounding)
**Status**: Draft
**Input**: Documentation structural cleanup / Common Docs convergence. Formalize the audience metadata first, then rehome, restructure, normalize, and rewrite the docs corpus onto the repository's sanctioned Common Docs section set. Folds #3273, #2215, #2887 (and partially #2227); coordinates #3024, #2358, #3147. Excludes the `docs/plans/` backlog (follow-on mission).

## Context

Spec Kitty's documentation is ~700 Markdown files across flat mega-directories plus stray doc directories at the repository root. Per-page frontmatter is already clean (the structural-lint gate is green), but the corpus fails on **structure, location, and lifecycle**, none of which the current lint catches. The activated Common Docs doctrine (DIRECTIVE_042, `common-docs` styleguide + its `structural_lint_config`, `common-docs-*` tactics) and the audience doctrine (`047-audience-oriented-writing`, `writing-audience-catalog`) define the target.

**Grounding facts established during post-spec review (do not re-derive):**
- The audience catalog **already exists** at `docs/context/audience/` (singular) — a mature project persona set (`internal/`: maintainer, lead-developer, system-architect, ai-collaboration-agent, cli-runtime, project-codebase; `external/`: architect-evaluator, tech-lead-evaluator, product-manager-evaluator, project-owner). This is the docs SSOT for personas and is richer than the 5 generic built-in pack personas (which remain the separate consumer-project baseline).
- The `audience:` frontmatter field **already exists** on 13 pages but as **free-text labels** ("end-users", "packagers", …) that do **not** resolve to the catalog; the field is **not canonized** in the common-docs doctrine and has **no resolution test**.
- The `structural_lint_config` (loaded by the lint asset) routes concern buckets to homes: `how_to → development/`, `reference_policy → development/`, `ops_runbook → operations/`, `point_in_time → plans/engineering-notes/`, `generated_nav → pinned`, `doctrine_artifact → src/doctrine/`, and pins `guides_boundary` (guides/ is not a how-to relocation target). It also enumerates `frontmatter_required_fields: [doc_status, updated]`, a redirect-stub description prefix (`"Redirect stub:"`), and shadow-tree nav exemptions. Convergence targets the config's **actual sanctioned section set**, not the nominal 13 alone.
- The canonical docs-move tooling (`scripts/docs/`) is real but **single-writer**: `redirect_stub_generator.py` hardcodes a *different, closed* mission's slug + occurrence-map; `redirect_map.yaml` is a **DERIVED, do-not-hand-edit** artifact; `redirect_baseline_urls.json` is an **immutable** coverage denominator; `redirect derivation regenerates the whole map from `baseline + one moves list`.
- The authoritative DocFX build / SEO / redirect-coverage gates run **only on push to main/2.x**, not on PRs. The PR gate set (`docs-freshness.yml`) is source-level only.

**Operator decisions folded in:** (D1) how-to content is homed by **audience** — contributor/maintainer how-tos → `development/`, user-facing how-tos → `guides/` — and the config's concern mapping is updated to be audience-aware. (D2) the audience work **formalizes what exists** rather than copying built-in personas.

The `docs/plans/` distil-and-retire triage remains **out of scope** (follow-on mission). All cleanup missions run in sequence on `docs/common-docs-cleanup`; a single upstream PR opens only after the sequence completes.

## Definitions (normative)

- **Sanctioned content section set**: the 13 canonical Common Docs sections (`index, context, architecture, adr, plans, api, configuration, integrations, security, guides, operations, migrations, changelog`) **plus** `development/` (the config's home for `how_to`/`reference_policy`). No other content section may exist.
- **Sanctioned non-content directories** (exempt from the section rule): `assets/` and `templates/spec-kitty/` (the DocFX theme). This is a closed set.
- **Sanctioned root allowlist** (the only documentation-bearing files permitted outside `docs/`): `README.md`, `LICENSE`, `CHANGELOG.md` (symlink), `CONTRIBUTING.md` (symlink), `CLAUDE.md`, `AGENTS.md`, `CODE_OF_CONDUCT.md`, `SECURITY-POSITION.md`, `CONTRIBUTORS.md`, `RELEASE_CHECKLIST.md`, `.all-contributorsrc`, `ascii-art.txt`. This is a **closed** set; NFR-006 asserts against it and any addition requires PR justification.
- **In-scope page**: any content page under `docs/` **except** `docs/plans/**` and the sanctioned non-content directories.
- **Touched page**: any page whose path or body changes in this mission's diff.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Audience metadata is formalized, linked, and tested (Priority: P1)

A writer (human or Comms Cleo) opening a page sees an `audience:` frontmatter value that **resolves to a persona in the existing `docs/context/audience/` catalog**, and a test fails if any `audience:` reference dangles.

**Why this priority**: This grounds every downstream rewrite in a named reader and closes the gap between the existing (but disconnected) field and catalog. It must land first.

**Independent Test**: Canonize `audience:` in the doctrine, migrate the 13 free-text values to catalog references, run the new non-vacuous resolution test — it passes only when every `audience:` reference resolves and fails on a dangling one or on zero examined.

**Acceptance Scenarios**:
1. **Given** the existing `docs/context/audience/` catalog, **When** WP-0 completes, **Then** `audience:` is canonized in `042-common-docs`/`common-docs` styleguide (semantics, resolvable-`.md`-path rule, a `tooling:` row naming the resolver) and in the `047-audience-oriented-writing` surface — without adding `audience:` to `structural_lint_config.frontmatter_required_fields`.
2. **Given** the 13 pre-existing free-text `audience:` values, **When** WP-0 completes, **Then** each is migrated to a resolvable path into `docs/context/audience/` (or the page's audience is a newly-authored catalog persona).
3. **Given** the resolution test, **When** it runs on PR (`--strict`), **Then** it fails on any dangling `audience:` and fails on zero examined (non-vacuity floor via `assert_examined_floor`).

---

### User Story 2 - All documentation lives under one root (Priority: P1)

A contributor finds documentation under the single `docs/` root, never scattered at the repository root.

**Why this priority**: The single-root violation is the most disorienting structural defect and is invisible to the docs-rooted lint; much of the root clutter has zero inbound links (low risk).

**Independent Test**: Enumerate documentation-bearing files outside `docs/`; the story is met when only the closed sanctioned root allowlist remains, every rehomed page resolves, and moves are recorded in this mission's occurrence-map.

**Acceptance Scenarios**:
1. **Given** root `research/`, `examples/`, `glossary/` and loose root doc files, **When** the mission completes, **Then** each is retired (stale, zero-inbound) or rehomed to the correct sanctioned section (research survivors → `docs/context/` or `docs/integrations/`, **never** `docs/plans/**` per C-001), with a prefixed redirect stub where an inbound link requires one.
2. **Given** `media/` → `docs/assets/`, **When** the README renders on GitHub/PyPI, **Then** the logo still displays (the absolute raw URL updated in the same change).
3. **Given** `contracts/`, **When** the mission completes, **Then** `batch-api-contract.md` → `docs/api/` while `contracts/fixtures/*.json` (test data read by `tests/contract/test_handoff_fixtures.py`) is left untouched.

---

### User Story 3 - Only sanctioned sections exist (Priority: P2)

A reader sees only the sanctioned content sections — non-canonical umbrella, empty-placeholder, and shadow-tree directories are gone (closes #2215).

**Why this priority**: Non-canonical/umbrella sections and the `architecture/` version shadow fragment discoverability; higher risk than US2 (link-heavy, nav-registered).

**Independent Test**: Enumerate top-level `docs/` directories; met when only the sanctioned content section set + sanctioned non-content dirs remain and no content basename is duplicated across section subtrees.

**Acceptance Scenarios**:
1. **Given** `reference/` duplicating `api/`, and non-canonical `doctrine/`, `core-concepts/`, `updates/`, `output/`, `release-goals/`, `archive/`, **When** the mission completes, **Then** each is folded into a sanctioned section or retired, and DocFX nav updated in lockstep.
2. **Given** `architecture/README-1.x/2.x/3.x.md` (the #2215 era stubs), **When** the mission completes, **Then** version history is distilled into `adr/<era>/`, `architecture/` presents one living design, and the shipped `src/doctrine/templates/diagrams/README.md` anchors are repointed **before** deletion.
3. **Given** the section-count invariant, **When** the extended structural-lint runs, **Then** any directory outside the sanctioned set fails the gate.

---

### User Story 4 - How-to content is homed by audience (Priority: P2)

A reader finds contributor/maintainer how-tos under `development/` and user-facing how-tos under `guides/`, every how-to/tutorial declares its Divio type, and the config reflects this routing.

**Why this priority**: Resolves the config↔reality conflict (config routes how_to→development/, guides/ holds ~21 how-tos) via the operator's audience-based split, and clarifies the two most-used reader surfaces.

**Independent Test**: Every `guides/**` and `development/**` how-to declares `type:`; user-facing how-tos live under `guides/`, contributor how-tos under `development/`; `concern_bucket_to_section` and `guides_boundary` reflect the audience-based routing; one index per grouping.

**Acceptance Scenarios**:
1. **Given** ~21 how-tos in `guides/` and ~15 in `development/`, **When** the mission completes, **Then** each is placed by its audience (external→guides/, internal→development/) with the move recorded in the occurrence-map and links repointed.
2. **Given** the loaded `structural_lint_config`, **When** the mission completes, **Then** `concern_bucket_to_section`/`guides_boundary` are updated to the audience-based routing in `common-docs.styleguide.yaml` with recorded rationale (no silent divergence).
3. **Given** guide/development pages lacking a Divio `type:`, **When** the mission completes, **Then** every in-scope page declares exactly one Divio type, and tutorials are separated from how-tos.

---

### User Story 5 - Pages are named, indexed, subdivided, and rewritten for scanability (Priority: P2)

A reader lands on any section/subdirectory and finds a single `index.md`, consistent kebab-case names, oversized flat sections broken into concern subdirectories (folds #3273), and page bodies written to be scanned — grounded in the page's declared audience, **without changing the facts**.

**Why this priority**: Naming inconsistency, flat oversized sections (`development/` 22 files/0 subdirs; `guides/` 59/1), and dense prose reduce scanability. Rewrites realize the quality goal — but must be bounded and fact-safe.

**Independent Test**: Every in-scope directory has one `index.md`; in-scope names are kebab-case; `development/` and `guides/` are subdivided by concern; each **enumerated** rewrite page passes a scanability checklist and carries a resolvable `audience:`; no rewrite alters an unverified factual claim.

**Acceptance Scenarios**:
1. **Given** `README.md`-as-landing or index-less directories, **When** the mission completes, **Then** each in-scope directory presents a single `index.md`.
2. **Given** non-kebab names in scope (incl. the snake_case persona files being formalized), **When** the mission completes, **Then** they are kebab-cased with every reference updated in the same change.
3. **Given** the flat `development/` and `guides/` sections, **When** the mission completes, **Then** they are subdivided into concern subdirectories with all inbound links (incl. `CLAUDE.md`/`AGENTS.md` refs and the `CONTRIBUTING.md` symlink target), `related:` refs, and redirect-map entries updated in the same change.
4. **Given** a page on an **enumerated per-WP rewrite list**, **When** it is finalized, **Then** its body is a prose-only, diff-reviewed rewrite that passes the scanability checklist (lead summary, H2/H3 structure, tables/lists over long prose) grounded in its `audience:`, and any behavior-documenting page is regenerated from source rather than hand-rewritten.

---

### User Story 6 - ADR corpus polished (Priority: P3)

A reader of the ADR corpus sees consistent era filing, dated filenames, correct MADR `status`, and working freshening commands (closes #2887).

**Why this priority**: The ADR corpus is largely compliant; low-value polish, sequenced last, mostly independent.

**Acceptance Scenarios**:
1. **Given** the #2887 date-sequence violations and 2 non-dated 3.x ADRs with redundant `doc_status`, **When** the mission completes, **Then** they carry dated prefixes and only the MADR `status` key.
2. **Given** ADR era `README.md` files (deferred to #2227 in the lint config), **When** the mission completes, **Then** the era-index normalization is reconciled with #2227 (either done here with the config exclusion updated, or explicitly left to #2227) — no silent double-ownership.

### Edge Cases

- A file that looks like docs but is read by code/tests/CI (`contracts/fixtures/*.json`, the generated rollups, charter authority-path targets) — preserved or repointed in the same change, never blindly moved.
- An inbound `related:` link living in out-of-scope `docs/plans/**` but pointing at a moved page — the target is fixed even though the plans page is otherwise untouched (single-threaded per C-011).
- A redirect stub shares its twin's basename — it MUST carry `description: "Redirect stub: …"` or it trips `shadow_tree_basename` (NFR-003).
- A page whose audience is not yet in the catalog — a new persona is authored in `docs/context/audience/` (template) rather than reintroducing a free-text value.
- The DocFX theme (`templates/spec-kitty/`) resembles docs but is site machinery — never treated as content.
- A moved `development/**` page may be referenced by `CLAUDE.md`/`AGENTS.md` or be the `CONTRIBUTING.md` symlink target — updated in the same change.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Use existing audience catalog | As a writer, I want the existing `docs/context/audience/` catalog treated as the docs persona SSOT (not forked or overwritten by the generic built-in personas), extended with new personas only where a page needs one. | High | Open |
| FR-002 | Canonize `audience:` field | As a writer, I want `audience:` canonized in `042-common-docs`/`common-docs` styleguide + the `047` surface as a resolvable repo-relative `.md` path into `docs/context/audience/`, with a `tooling:` row naming its check. | High | Open |
| FR-003 | Non-vacuous audience resolver | As a maintainer, I want a docs-consistency test (run `--strict` on PR) that fails on any dangling `audience:` and on zero examined (`assert_examined_floor`). | High | Open |
| FR-004 | Migrate free-text audience values | As a reader, I want the 13 pre-existing free-text `audience:` values migrated to resolvable catalog references. | High | Open |
| FR-005 | Single documentation root | As a contributor, I want no documentation files outside `docs/` except the closed sanctioned root allowlist. | High | Open |
| FR-006 | Rehome/retire root clutter | As a contributor, I want root `research/`, `examples/`, `contracts/*.md`, `glossary/`, `media/`, and loose root doc files retired or rehomed to a sanctioned section (research survivors NOT into `plans/`). | High | Open |
| FR-007 | Sanctioned sections only | As a reader, I want only the sanctioned content section set (13 + `development/`) plus the closed non-content dirs; all non-canonical/umbrella/placeholder sections folded or retired. | Medium | Open |
| FR-008 | Collapse architecture version shadow | As a reader, I want one unversioned living `architecture/` with version history in `adr/<era>/` (closes #2215), and the shipped `src/doctrine` diagram anchors repointed before deletion. | Medium | Open |
| FR-009 | Audience-based how-to routing | As a reader, I want contributor how-tos in `development/` and user-facing how-tos in `guides/`, with `concern_bucket_to_section`/`guides_boundary` updated to this audience-based routing (rationale recorded). | Medium | Open |
| FR-010 | Divio-typed guides/development | As a reader, I want every in-scope `guides/`+`development/` page to declare one Divio type, tutorials separated from how-tos, one index per grouping. | Medium | Open |
| FR-011 | Subdivide flat sections | As a reader, I want `development/` (22) and `guides/` (59) subdivided into concern subdirectories (folds #3273), each with an `index.md`. | Medium | Open |
| FR-012 | One landing page per directory | As a reader, I want each in-scope directory to present a single `index.md` (no README/index ambiguity). | Medium | Open |
| FR-013 | Kebab-case naming | As a contributor, I want in-scope file/dir names lowercase kebab-case (one concern per file), references updated in the same change. | Medium | Open |
| FR-014 | Bounded, fact-safe rewrites | As a reader, I want pages on an enumerated per-WP list rewritten prose-only for scanability grounded in `audience:`, diff-reviewed, without altering facts; behavior-documenting pages regenerated from source (`build_cli_reference.py`), not hand-rewritten. | Medium | Open |
| FR-015 | ADR polish | As a reader, I want the #2887 date-sequence + non-dated/redundant-`doc_status` ADRs fixed, and era-index normalization reconciled with #2227. | Low | Open |
| FR-016 | Cross-reference integrity | As a reader, I want every `related:` and `audience:` reference to resolve after restructuring, targets updated in the same change as each move. | High | Open |
| FR-017 | Navigation lockstep + pre-merge build | As a site visitor, I want DocFX nav (`toc.yml`, `docfx.json`, `llms.txt`, per-section toc) updated in lockstep, verified by a **new pre-merge DocFX build + redirect-coverage + seo_verify job** on `pull_request` (folds a slice of #3265). | High | Open |
| FR-018 | Code/test/CI reference updates | As a maintainer, I want every code/test/CI/`CLAUDE.md` reference to a moved doc path updated in the same change, enforced by a gate that greps for surviving `from`-paths in the occurrence-map (incl. pinning `gap_analysis.py`'s subdir-name assumptions). | High | Open |
| FR-019 | Governance path integrity | As a governance owner, I want ALL dead charter authority paths repaired — `glossary/contexts/`, `architecture/3.x/adr/`, `architecture/adrs/` — and `docs/context/`+`docs/adr/3.x/` preserved or updated in the same change. | High | Open |
| FR-020 | Regenerate rollups in place | As a maintainer, I want the page-inventory + retrieval-index rollups regenerated via `inventory_lockfile.py` in place (not relocated), sequenced against the live missions that own them. | Medium | Open |
| FR-021 | Canonical move tooling via own spine | As a maintainer, I want every move driven by **this mission's own `occurrence_map.yaml`** passed as `--occurrence-map` to `redirect_stub_generator.py`/`relative_link_fixer.py`; `redirect_map.yaml` regenerated (never hand-edited) as a **cumulative** spine preserving the prior mission's entries; `redirect_baseline_urls.json` treated as immutable; cross-mission single-writer ownership reconciled (#2358). | High | Open |
| FR-022 | Prefixed redirect stubs | As a maintainer, I want every generated redirect stub to carry the `description: "Redirect stub: …"` prefix so `shadow_tree_basename` recognizes it. | Medium | Open |
| FR-023 | Extend structural-lint to mission invariants | As a maintainer, I want the structural-lint asset + `structural_lint_config` extended to check this mission's invariants (single-root, sanctioned-sections-only, one-index-per-dir, Divio-type presence) so NFR-003's gate is non-vacuous. | Medium | Open |
| FR-024 | Curate migrations delete-stale | As a reader, I want `migrations/` completed one-off runbooks reclassified (`deprecated`/`superseded`) or distilled, per the delete-stale rule. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Pre-merge site build | The new PR DocFX build job completes with zero errors/warnings and redirect-coverage + seo_verify pass on the PR's built `_site`. | Reliability | High | Open |
| NFR-002 | Zero dangling references | 100% of `related:` and `audience:` references resolve; both resolvers are non-vacuous (fail on 0 examined). | Correctness | High | Open |
| NFR-003 | Extended lint green | The **extended** structural-lint reports 0 violations with `checked` = in-tree page count. | Correctness | High | Open |
| NFR-004 | Terminology guard green | 0 forbidden-term regressions; the stale `plans/notes/` exemption reconciled before any plans link-fix. | Correctness | High | Open |
| NFR-005 | No surviving stale paths | 0 un-updated `docs/**` path literals remain in `src/`, `tests/`, `.github/`, `scripts/`, `CLAUDE.md`/`AGENTS.md` for any move in the occurrence-map; touched tests pass. | Reliability | High | Open |
| NFR-006 | Single-root measurable | 0 documentation files outside `docs/` except the closed sanctioned root allowlist. | Maintainability | High | Open |
| NFR-007 | Sanctioned sections only | `docs/` top level contains only the sanctioned content section set + closed non-content dirs; 0 others. | Maintainability | Medium | Open |
| NFR-008 | Frontmatter completeness | 100% of touched pages carry required frontmatter incl. a resolvable `audience:` and a `description` of 50–180 chars. | Correctness | Medium | Open |
| NFR-009 | Rewrite factual fidelity | 0 FR-014 rewrites alter a factual claim not re-verified against current code/tests (reviewer cites the backing). | Correctness | High | Open |
| NFR-010 | Redirect coverage preserved | The regenerated `redirect_map.yaml` covers every prior baseline URL AND every move in this mission's occurrence-map (moves ⊆ map); coverage check passes. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Plans backlog out of scope | No distil/retire/restructure of `docs/plans/**`; only mechanical link-target fixes required by moves elsewhere; research survivors are NOT placed under `plans/`. | Scope | High | Open |
| C-002 | Test data is not docs | `contracts/fixtures/*.json` MUST NOT move into `docs/`. | Technical | High | Open |
| C-003 | Authority paths protected | `docs/context/` and `docs/adr/3.x/` are charter authority paths; not relocated unless charter+governance config updated in the same change. | Governance | High | Open |
| C-004 | Preserve DocFX theme | `docs/templates/spec-kitty/` is site machinery, preserved. | Technical | High | Open |
| C-005 | Rollups regenerate in place | The rollups are `owned_files` across ~10 live-mission lanes.json; regenerate in place, never relocate or reassign; sequence against those missions. | Technical | Medium | Open |
| C-006 | Sanctioned section canon | Converge to the Definitions' sanctioned section set; a section outside it, a second root, or a shadow tree is a red-line. | Governance | High | Open |
| C-007 | Bulk-edit discipline | This mission authors its OWN `occurrence_map.yaml` (cumulative move spine) per DIRECTIVE_035 occurrence-classification. | Process | High | Open |
| C-008 | No version numbers | No release/version numbers assigned; the release boundary belongs to the product owner. | Business | Medium | Open |
| C-009 | Sequenced, single PR, serial movers | Cleanup missions run in sequence on `docs/common-docs-cleanup`; one upstream PR after the sequence. Within a mission, mover WPs are serial or single-threaded on shared surfaces (C-011), with one integration point. | Process | High | Open |
| C-010 | Derived map, immutable baseline | `redirect_map.yaml` is DERIVED (regenerate, never hand-edit); `redirect_baseline_urls.json` is immutable (never edited per move); moves are recorded only in the occurrence-map. | Technical | High | Open |
| C-011 | Shared surfaces single-threaded | Shared manifests (redirect_map, baseline, toc.yml, docfx.json, llms.txt, inventory lockfiles) and `docs/plans/**` link-fixes are edited by exactly one nav/redirect-reconcile owner at a time. | Process | High | Open |
| C-012 | Audience field scope | `audience:` is required only on touched pages and MUST NOT be added to `structural_lint_config.frontmatter_required_fields`. | Technical | High | Open |
| C-013 | Coordinate external tickets | Coordinate `docs/context/audience/` ownership + singular/plural with #3024; establish the moves-ledger home per #2358; note #3147 whole-tree freshness reds in the PR body. | Process | Medium | Open |

### Key Entities

- **Documentation page** — Markdown under `docs/` with Common Docs frontmatter (`title`, `doc_status`, `updated`, `description` 50–180, `type`, `related`, resolvable `audience`).
- **Audience persona** — an existing page under `docs/context/audience/` (internal/external); the resolution target of `audience:`.
- **Occurrence map** — this mission's `occurrence_map.yaml`, the single move-spine driving the redirect/link tooling.
- **Sanctioned section set** / **sanctioned non-content dirs** / **sanctioned root allowlist** — the closed enumerations in Definitions that the acceptance gates assert against.
- **Redirect artifacts** — derived `redirect_map.yaml` + immutable `redirect_baseline_urls.json`.

## Success Criteria *(mandatory)*

- **SC-001**: `audience:` is canonized in doctrine, every touched page's `audience:` resolves into `docs/context/audience/`, the 13 free-text values are migrated, and the resolver is non-vacuous.
- **SC-002**: 0 documentation files outside `docs/` except the closed sanctioned root allowlist.
- **SC-003**: `docs/` contains only the sanctioned section set + closed non-content dirs; 0 non-canonical/shadow sections (closes #2215).
- **SC-004**: Every in-scope directory presents exactly one `index.md`.
- **SC-005**: 0 broken internal links after restructuring (`related:`+`audience:` resolve; non-vacuous).
- **SC-006**: The pre-merge DocFX build + redirect-coverage + seo_verify job passes; all PR docs gates green.
- **SC-007**: How-tos are homed by audience (contributor→development/, user→guides/), every in-scope guides/development page declares one Divio type, and the config's concern routing matches.
- **SC-008**: `docs/plans/` content unchanged except link-target fixes (scope boundary respected).
- **SC-009**: `development/` and `guides/` subdivided by concern with 0 broken links/refs/redirect entries (closes #3273's residual).
- **SC-010**: The regenerated redirect map preserves all prior baseline coverage and covers this mission's moves (0 coverage regressions).

## Assumptions

- `docs/context/audience/` (singular) is the docs persona SSOT; the 5 generic built-in pack personas are the separate consumer-project baseline and are NOT copied over it. #3024 ownership is coordinated, not pre-empted.
- The Common Docs + audience doctrine is already activated in the charter (verified); charter edits are limited to same-change authority-path repair and the audience-field canonization.
- #3273's two code findings already landed in this branch; folding closes it. Its 3 residual NOTES stay out-of-active-scope: SEO-PR-gate is partially addressed by FR-017 (else #3265); the `docs-freshness` required-check hazard is awareness-only; the `_published_pages` re-walk is an opportunistic campsite fold.
- This mission likely CLOSES #3273, #2215, #2887 and partially resolves #2227; it COORDINATES #3024, #2358, #3147.
- The follow-on `docs/plans/` triage and any full-corpus `audience:` backfill beyond touched pages are separate missions.
