# Mission Specification: Docs SEO Metadata Audit and Enforcement

**Mission**: `docs-seo-metadata-enforcement-01KZ9PJ2`
**Mission ID**: `01KZ9PJ2QG6BWH6MFMMZHVB72C`
**Mission type**: software-dev
**Created**: 2026-08-05
**Target branch**: `feat/docs-seo-metadata-enforcement`
**Source**: [issue #1652 — SEO audit needed for GitHub Pages docs site](https://github.com/Priivacy-ai/spec-kitty/issues/1652)

---

## Purpose

Make every published documentation page carry unique, search-intent-matched metadata, and enforce that with a gate whose coverage is derived from the build itself, so it cannot silently go vacuous when pages move.

Developers searching for how to install Spec Kitty or look up a slash command currently land on results that either do not describe the page or resolve to a redirect stub. The docs site earns impressions but almost no clicks.

---

## Context: what the originating issue assumed vs. what is true

Issue #1652 was filed from a pre-launch website action list. Two of its acceptance criteria were **already satisfied in production** before this mission began, and its Search Console figures refer to URLs that have since moved. Recording this is required by DIRECTIVE_003 so a future contributor does not "re-fix" already-correct pages.

| Issue claim | Verified state (checked against the live site, 2026-08-05) |
|---|---|
| `docs/reference/slash-commands` needs a CLI-reference title | Already correct. Live `<title>` is verbatim the issue's suggested direction. The page **moved** to `/api/slash-commands.html`; the cited address is now a redirect stub. |
| `install-spec-kitty.html` needs install-intent title with OS targets | Already correct: *"Install Spec Kitty — macOS, Linux, and Windows Installation Guide"*. The page **moved** from `how-to/` to `guides/`. |
| Canonical addresses may be missing | Already emitted on every indexed page by the existing SEO post-processing step. |
| Social sharing metadata may be missing | Already emitted (Open Graph, Twitter card, structured data). |

The measured zero-click behaviour is therefore substantially explained by impressions accruing to **pre-move addresses that now serve redirect stubs**, not by the two named pages lacking titles.

The genuine, still-unresolved defects are different from the ones the issue names:

1. **The enforcement gate is near-vacuous.** The docs SEO test derives its page set from a hardcoded glob list describing the *pre-move* directory layout. Those directories are now empty. The gate covers **16 of 674** built pages (2.4%) and reports green regardless of the other 658.
2. **147 architecture-decision pages ship with no description at all.** A live page in that tree emits **zero** description tags, and its social description is a single boilerplate string duplicated across all 147.
3. **The post-processing step never authors a description.** It only *reads* an existing one and falls back to boilerplate for social/structured metadata. When the source page has no description, the published page ships with none.
4. **The two highest-intent pages are absent from top-level navigation.** Neither the install guide nor the slash-command reference appears in the site's root navigation tree; both sit behind intermediate index pages.

**Root cause shared by (1) and the drift risk generally:** the gate's page set is maintained *separately* from the build's content definition. When directories were reorganised, the build followed and the gate did not. A gate that cannot go red is not a gate.

---

## User Scenarios & Testing

### Primary scenario — a developer evaluating Spec Kitty

1. A developer searches for how to install Spec Kitty.
2. A documentation page ranks in the results.
3. The result shows a title naming the task and the supported operating systems, and a description summarising what the page will help them do.
4. They click through and arrive at the live install page directly — not at a redirect hop.
5. From that page, navigation makes the next relevant page (slash-command reference, getting started) reachable without hunting.

**Success**: the developer can tell from the search result alone whether the page answers their question, and reaches it in one click.

### Secondary scenario — a maintainer adding a documentation page

1. A maintainer adds a new page under any published documentation directory.
2. They omit the description, or write one outside the accepted length band.
3. The docs quality gate **fails**, naming the offending file and the reason.
4. They add a compliant description; the gate passes.

**Success**: no page can reach the published site without unique, length-valid metadata.

### Tertiary scenario — a maintainer reorganising directories

1. A maintainer moves a documentation directory (as happened with `how-to/` → `guides/`).
2. The build's content definition is updated.
3. The gate's coverage **automatically follows**, because it is derived from that same definition.
4. If coverage would drop below the built page set, the gate fails rather than passing quietly.

**Success**: a directory move cannot silently reduce enforcement coverage.

### Edge cases

- **Redirect stubs** must remain excluded from indexing and from the sitemap; backfilling metadata must not accidentally promote a stub into a real indexable page.
- **Generated pages** (mission-run pages, table-of-contents pages) must not be forced through the human-authored-description requirement where no author exists; their exclusion must be explicit and enumerable, never an accidental glob miss.
- **Archive trees** (1.x, 2.x historical snapshots) are immutable legacy snapshots; they must not be rewritten for search, and their treatment must be a stated decision rather than an oversight.
- **Duplicate descriptions** across two legitimately similar pages must fail the gate, since duplicate descriptions are the specific defect being eliminated.
- A description that is present but is the **boilerplate fallback string** must be treated as missing, not as satisfied.

---

## Domain Language

| Canonical term | Meaning in this mission | Avoid |
|---|---|---|
| **Built site** | The rendered HTML output directory produced by the documentation build, before upload. Verification targets this, not source files. | "the docs", "the repo" |
| **Content globs** | The build configuration's declaration of which source pages become published pages. The single authority for gate coverage. | "the file list" |
| **Indexable page** | A built page that is neither a redirect stub, a table-of-contents page, nor an asset — i.e. a page search engines should index. | "page" (unqualified) |
| **Redirect stub** | A generated placeholder at a moved page's old address that forwards to its new address. Never indexable. | "redirect", "alias" |
| **Description band** | The existing accepted length range for a description, 50–180 characters inclusive. | "meta length" |
| **Mission** | The canonical product term for this unit of work. | "feature" (prohibited per Terminology Canon) |

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Produce an evidence-based audit of the **built site** enumerating, for every built page, its title, description, canonical address, social metadata, and indexable/stub classification. The audit is the factual basis for closing issue #1652 and must be reproducible by re-running a documented command. | Proposed |
| FR-002 | Derive the docs SEO gate's page set from the **same content globs the build uses**, so the gate and the build cannot disagree about which pages are published. The glob list must exist in exactly one place. | Proposed |
| FR-003 | The gate must be **non-vacuous by construction**: it must fail when its resolved page set is materially smaller than the set of indexable pages the build produces, rather than passing on an empty or shrunken set. | Proposed |
| FR-004 | Every page currently lacking a description — the 147 architecture-decision pages, including the three index pages with no frontmatter at all — must receive a **unique, hand-authored, human-meaningful description** within the description band. | Proposed |
| FR-005 | The SEO post-processing step must **emit a description tag** on every indexable page. A page that reaches the built site with no description tag is a defect. | Proposed |
| FR-006 | Treat the generic boilerplate fallback string as **equivalent to a missing description** for gate purposes, so fallback text cannot mask an unwritten description. | Proposed |
| FR-007 | Enforce **description uniqueness** across all indexable pages; two indexable pages sharing a description fails the gate, naming both files. | Proposed |
| FR-008 | Verify on the built output that every indexable page carries a **canonical address** pointing at its own preferred address, and that social/structured metadata is present and matches the page's own title and description. | Proposed |
| FR-009 | Make the **highest-intent pages reachable from top-level navigation**: at minimum the install guide and the slash-command reference must be reachable from the documentation home in **one click**, and linked from topically relevant guide pages. | Proposed |
| FR-010 | Provide a **documented verification procedure** an operator can run against the deployed site (retrieving a page and inspecting its markup) to confirm each acceptance criterion without reading source. | Proposed |
| FR-011 | Record, in the audit output, that the two addresses named in issue #1652 are **pre-move addresses now served as redirect stubs**, and re-verify the corresponding live pages at their current addresses. | Proposed |
| FR-012 | Preserve existing correct behaviour: redirect stubs remain non-indexable and excluded from the sitemap; the sitemap continues to list exactly the indexable pages. | Proposed |
| FR-013 | State an **explicit, recorded decision** for how archive trees and generated pages are treated by the gate, so their exclusion is deliberate and enumerable rather than an accidental glob miss. | Proposed |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|---|---|---|---|
| NFR-001 | Title coverage on the built site | 100% of indexable pages have a non-empty title distinct from the site-wide default | Proposed |
| NFR-002 | Description coverage on the built site | 100% of indexable pages have a description tag whose content is not the boilerplate fallback | Proposed |
| NFR-003 | Description length compliance | 100% of indexable page descriptions fall within 50–180 characters inclusive | Proposed |
| NFR-004 | Description uniqueness | 0 duplicate descriptions among indexable pages | Proposed |
| NFR-005 | Gate coverage | The gate's resolved page set covers ≥ 99% of indexable built pages; any shortfall is an enumerated, justified exclusion, not a silent gap | Proposed |
| NFR-006 | Gate demonstrability | The gate has a boundary self-test proving it goes **red** on a missing description, an out-of-band length, and a duplicate — following the existing precedent that a gate which cannot fail is fake | Proposed |
| NFR-007 | Gate runtime | The docs SEO gate completes in ≤ 30 seconds on the full page set, so it stays in the fast test tier | Proposed |
| NFR-008 | Build time impact | Documentation build wall-clock increases by ≤ 10% relative to the pre-mission baseline | Proposed |
| NFR-009 | Navigation depth for high-intent pages | Install guide and slash-command reference reachable in ≤ 1 click from the documentation home | Proposed |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | No changes to the marketing website repository. This mission's boundary is the documentation source, build configuration, post-processing, and test gates in this repository. | Active |
| C-002 | Do not alter the existing redirect map or reverse any prior page moves. Moved addresses stay moved; only metadata and enforcement change. | Active |
| C-003 | Keep the existing 50–180 character description band. Do not invent a new threshold. | Active |
| C-004 | No new external service dependencies and no change of documentation generator. Work within the existing generator plus post-processing arrangement. | Active |
| C-005 | Archive trees are immutable legacy snapshots and must not be rewritten for search. | Active |
| C-006 | Terminology Canon applies: **Mission**, not "feature", in all authored prose and metadata. | Active |
| C-007 | New and modified code passes lint and type checking with zero issues and zero warnings; suppressions are not an acceptable route to green. | Active |
| C-008 | Descriptions are hand-authored for meaning, not machine-generated from headings. Auto-derivation was explicitly considered and rejected during discovery. | Active |

---

## Success Criteria

| ID | Criterion |
|---|---|
| SC-001 | Every page a search engine can index describes itself: 100% carry a unique, meaningful title and description. |
| SC-002 | A developer searching for installation or command-reference information sees a result that names the task and the platforms, and reaches the page in a single click with no redirect hop. |
| SC-003 | Zero pages on the published site share a description with another page. |
| SC-004 | A maintainer who omits a description is told so before their change is published, with the file named. |
| SC-005 | Reorganising documentation directories cannot reduce enforcement coverage without failing the gate. |
| SC-006 | Every acceptance criterion in issue #1652 is demonstrable by retrieving the live page and inspecting its markup, with the evidence recorded rather than asserted. |
| SC-007 | The two pages named in the issue are confirmed correct at their current addresses, and the stale-address explanation for their reported zero-click behaviour is on record. |

---

## Key Entities

| Entity | Description |
|---|---|
| **Documentation page** | A source page with frontmatter carrying, at minimum, a title and a description. |
| **Built page** | The rendered output of a documentation page, classified as indexable, redirect stub, table-of-contents, or asset. |
| **Content glob set** | The build's declaration of which source pages are published. The single authority for gate coverage (FR-002). |
| **Audit record** | The reproducible evidence output enumerating per-page metadata state (FR-001). |
| **Coverage assertion** | The gate's self-check that its page set matches the built indexable set (FR-003). |

---

## Assumptions

- The zero-click figures quoted in issue #1652 are attributed to pre-move addresses; re-verification uses current canonical addresses. This is inference from the redirect map, not from Search Console access, which this mission does not have.
- Search Console is not available to this mission, so no requirement depends on retrieving live search analytics. Ranking and click-through improvements are consequences, not testable acceptance criteria — hence SC-002 is phrased on page quality and click depth, which are verifiable.
- Authoring 147 descriptions is substantial deliberate effort. The operator explicitly chose hand-authored quality over machine derivation, and chose to keep it in this mission rather than split it to a follow-up.
- Architecture-decision pages are worth indexing because developers evaluating the project legitimately search for them and they already draw impressions.
- The existing description length band and the existing redirect/stub behaviour are correct and stay as they are.

---

## Out of Scope

- The marketing website repository and any of its pages.
- Reversing or amending prior page moves, or editing the redirect map.
- Changing the documentation generator or the hosting arrangement.
- Rewriting archive (1.x, 2.x) content for search.
- Paid search, backlink acquisition, or any off-site optimisation.
- Acceptance criteria that depend on live search-analytics access.

---

## Dependencies

- The existing documentation build and its SEO post-processing step.
- The existing description length check and its 50–180 band.
- The existing redirect-stub generation and coverage gates, which must continue to pass unchanged.
- The page-inventory lockfile, which tracks per-page frontmatter and may require regeneration once descriptions are backfilled.

---

## Traceability to issue #1652

| Issue acceptance criterion | Addressed by |
|---|---|
| Important pages have unique descriptive titles | FR-001, NFR-001 |
| Important pages have useful descriptions for developer search intent | FR-004, FR-005, FR-006, NFR-002, NFR-003 |
| Slash-command reference has CLI-reference title/description | FR-011 (verify already correct; record moved address) |
| Install page has install-intent title/description with OS targets | FR-011 (verify already correct; record moved address) |
| Canonical addresses point to the preferred address | FR-008 |
| Important pages reachable through clear internal links/navigation | FR-009, NFR-009 |
| Generated output verifiable by retrieving the page and inspecting markup | FR-010, SC-006 |
| *(not in the issue — discovered during audit)* Enforcement gate covers 2.4% of the site | FR-002, FR-003, NFR-005, NFR-006 |
| *(not in the issue — discovered during audit)* 147 pages ship with no description | FR-004, FR-005 |
