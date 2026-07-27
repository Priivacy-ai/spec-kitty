# Feature Specification: Docs Site IA & Onboarding Overhaul

**Mission ID:** `01KY02JBGCYS2H0EFDS76WDRFR`
**Mission Slug:** `docs-ia-onboarding-overhaul-01KY02JB`
**Mission Type:** documentation
**Branch Contract:** current=`feat/docs-ia-onboarding-overhaul`, planning_base=`feat/docs-ia-onboarding-overhaul`, merge_target=`feat/docs-ia-onboarding-overhaul` (`branch_matches_target: true`)
**Created:** 2026-07-20
**Status:** Draft

---

## Purpose

**TLDR:** Restructure docs.spec-kitty.ai's information architecture to restore a clear discover-to-install-to-wow path, fully document core governance concepts, and activate the canonical glossary across docs.

**Context:** docs.spec-kitty.ai currently buries its best onboarding content and opens with governance jargon instead of explaining who Spec Kitty is for and what it is good for. This mission restructures the site's information architecture with strict end-user/contributor segregation, restores a single discoverable discover-to-first-mission path, and fully documents previously-thin concepts (Ops vs. Missions, mission types, Charter, and all doctrine artifact kinds). It also activates the published glossary by auto-linking canonical terms across docs with tooltips and click-through, backed by a doctrine-style check that flags non-canonical term usage.

---

## Documentation Scope

**Iteration Mode:** Gap-filling — auditing and reworking an existing, substantially-built site, not authoring from scratch.
**Target Audience:** Primary — prospective adopters evaluating Spec Kitty before install, and existing users needing authoritative core-concept documentation (Ops vs. Missions, mission types, Charter, doctrine). Secondary — contributors/maintainers, served by a strictly separated documentation zone rather than by this mission's new content.
**Selected Divio Types:** All four (tutorial, how-to, reference, explanation), applied as internal `type:` frontmatter classification for editorial completeness — never surfaced as customer-facing navigation vocabulary (see C-002).
**Generators:** None of the code-comment generators (JSDoc/Sphinx/rustdoc) apply — this mission documents the tool itself, not a client codebase. One new internal build tool is added: a glossary term-linking post-processor in `scripts/docs/` (see FR-011/FR-012).

A full page-by-page inventory and disposition (keep / merge / rewrite / remove) is produced as `gap-analysis.md` during the audit phase, per this mission type's artifact contract. Key findings from pre-specify research are summarized below and ground the Functional Requirements.

**Known gaps (pre-specify research):**

- No landing content states who Spec Kitty is for or what it's good for before governance jargon appears.
- The working tutorial (`docs/guides/getting-started.md` → `docs/guides/your-first-feature.md`) has zero inbound links from the homepage or top nav — effectively invisible to a first-time visitor.
- `docs/guides/` is a flat 72-file pile mixing end-user tutorials/how-tos with contributor/maintainer runbooks.
- The doctrine system (8 artifact kinds) has only 3 thin explanation files and no "create your own doctrine artifact" how-to.
- Charter-creation guidance is scattered across 4 pages (`docs/context/charter-overview.md`, `docs/guides/charter-governed-workflow.md`, `docs/guides/setup-governance.md`, `docs/guides/troubleshoot-charter.md`) with no single authoritative path.
- The published glossary (`kitty-specs/glossary.html`, generated from `.kittify/glossaries/spec_kitty_core.yaml`) has zero inbound links from doc prose and no stable per-term anchors to link to.

---

## User Scenarios & Testing

### User Story 1 - First-time discovery, install, and first mission (Priority: P1)

A prospective adopter with no prior Spec Kitty knowledge lands on docs.spec-kitty.ai, determines whether it fits their project, installs it, and completes a first mission end-to-end.

**Why this priority**: Without this path, no one adopts Spec Kitty regardless of how good any individual feature's documentation is — this is the funnel's only entry point.

**Independent Test**: A person with no prior context, starting from the homepage, can state who Spec Kitty is for, install it, and finish their first mission using only in-doc navigation, without hitting a dead link or landing on contributor-only content.

**Acceptance Scenarios**:

1. **Given** a first-time visitor on the homepage, **When** they read the above-the-fold content, **Then** they can state in one sentence who Spec Kitty is for and what problem it solves, before encountering governance or architecture terminology.
2. **Given** a first-time visitor wants to get started, **When** they look for a next step from the homepage, **Then** they find one unambiguous "Get Started" entry point, not a flat card grid of equally-weighted sections.
3. **Given** a visitor following the Get Started path, **When** they complete it, **Then** they have installed Spec Kitty and successfully run their first mission.

---

### User Story 2 - Core concept literacy for existing users (Priority: P2)

A user who has completed their first mission needs authoritative documentation on Ops vs. Missions, the available mission types, and how to create a Charter — concepts that are foundational beyond the first mission but currently thin, scattered, or missing.

**Why this priority**: Users who can't distinguish an ad-hoc Op from a full Mission, or don't know how to stand up a Charter, misuse the tool or abandon it after the tutorial.

**Independent Test**: A user who has completed User Story 1 can find, from a single core-concepts starting point, an explanation of Ops vs. Missions, a comparison of mission types, and a working charter-creation how-to, without searching multiple scattered pages.

**Acceptance Scenarios**:

1. **Given** a user wants to know when to use a lightweight Op versus a full Mission, **When** they consult the core-concepts documentation, **Then** they get one page with a concrete decision rule.
2. **Given** a user wants to choose a mission type, **When** they read the mission-types page, **Then** all mission types present in the codebase (software-dev, research, documentation, plan) are listed with purpose and phases.
3. **Given** a user wants to create a Charter, **When** they follow the charter how-to, **Then** a single page walks them through the full interview-to-generation flow without redirecting them through the other three scattered pages to complete it.

---

### User Story 3 - Doctrine literacy and trustworthy glossary usage (Priority: P3)

Anyone authoring governance content needs to understand what each doctrine artifact kind is for and how to create one; anyone reading docs needs glossary terms to be reliably linked and used consistently.

**Why this priority**: Doctrine is governance-critical and almost entirely undocumented (3 thin files for 8 kinds); inconsistent glossary usage undermines the credibility of a tool whose entire premise is governed, terminology-consistent workflows.

**Independent Test**: A user unfamiliar with doctrine can, from one explanation page, learn what each of the 8 doctrine kinds is for and follow a how-to to create a new one; a reviewer can run the canonical-term check and see any non-canonical glossary-term usage flagged with page/line references.

**Acceptance Scenarios**:

1. **Given** a user wants to create a new tactic, **When** they read the doctrine how-to, **Then** they follow concrete, working steps (CLI commands, file locations, schema).
2. **Given** a documentation page mentions a glossary term, **When** the page renders, **Then** the first mention is a link with a tooltip showing the definition and a click-through to that term's own glossary entry.
3. **Given** a page uses a non-canonical spelling or casing of a glossary term, **When** the canonical-term check runs, **Then** the occurrence is flagged with page and line references.

---

### Edge Cases

- A glossary term's surface form appears inside a code block or as part of an unrelated proper noun — it must not be auto-linked in those contexts.
- Two glossary terms overlap as substrings (e.g., a multi-word term contains a shorter standalone term) — the linker must apply longest-match-first so the more specific term wins.
- A contributor-only page needs to reference an end-user-facing concept — an explicit, labeled cross-zone link is allowed; the reverse (end-user content silently depending on contributor-only content) is not.
- The abandoned `charter-end-user-docs-828` mission's gap-analysis findings conflict with this mission's own audit — this mission's audit is authoritative (see C-006).
- A reference-heavy page (API, ADR, Configuration, Operations, Migrations, Historical Archive) is found to be factually inaccurate during the audit — it is corrected in this mission (FR-010), not merely flagged for later.

---

## Domain Language

Canonical terms for this mission (avoid synonyms in spec, plan, tasks, and docs unless quoting archival material):

| Canonical term | Definition | Avoid |
|-----------------|------------|-------|
| **Mission** | The canonical product term for a full spec-to-merge workflow unit. | "Feature", "feature" |
| **Op** | A lightweight, governed ad-hoc invocation via `spec-kitty dispatch` that does not create a mission. | "quick task", unlabeled "one-off" |
| **Charter** | The binding project governance document at `.kittify/charter/charter.md`. | "config", "settings" |
| **Doctrine artifact** | A governed content unit of one of 8 kinds: directive, tactic, styleguide, toolguide, paradigm, procedure, agent_profile, mission_step_contract. `template` and `asset` are related but distinct, non-charter-activatable kinds — not among the 8 (corrected during WP06 implementation against live source/CLI; the original CLAUDE.md table this mission started from was stale). | "doc snippet", "policy file" |
| **Divio type** | One of {tutorial, how-to, reference, explanation}; internal editorial frontmatter classification only. | "doc kind" as a customer-facing nav label |
| **Glossary term** | An entry in `.kittify/glossaries/spec_kitty_core.yaml`, published at `kitty-specs/glossary.html`. | "keyword", "vocabulary word" |
| **End-user zone / Contributor zone** | The two strictly segregated top-level navigation areas this mission establishes. | "public docs" / "internal docs" (ambiguous) |

---

## Functional Requirements

> Status legend: **Planned** = required for mission acceptance. **Optional** = include if scope permits.

| ID | Description | Acceptance | Status |
|----|-------------|------------|--------|
| **FR-001** | The homepage's above-the-fold content must state who Spec Kitty is for and what problem it solves before any governance or implementation terminology appears. | `docs/index.md`'s first screen contains a plain-language value statement and target-audience framing; no governance/architecture term precedes it. | Planned |
| **FR-002** | A single, unambiguous "Get Started" entry point must be reachable from the homepage and lead a visitor through install → first mission → visible result, with no orphaned steps. | Homepage links to one Get Started page; it (or its immediate children) links onward through install and the first-mission tutorial with zero dead ends; existing `getting-started.md`/`your-first-feature.md` content is reused and updated, not duplicated. | Planned |
| **FR-003** | Site navigation must strictly segregate end-user documentation from contributor/maintainer documentation into two distinct top-level zones. | Every page under `docs/` is classified end-user or contributor; `toc.yml` reflects two clearly separated zones; no contributor-only page (e.g. PR-review or testing-flakiness runbooks) is reachable from within end-user navigation. | Planned |
| **FR-004** | One explanation page must describe Ops (lightweight ad-hoc dispatch) vs. Missions (full spec-to-merge lifecycle), including when to use each. | Page exists in the end-user zone, is linked from a core-concepts index, and states a concrete decision rule distinguishing the two. | Planned |
| **FR-005** | One page must enumerate and compare all mission types present in the codebase (software-dev, research, documentation, plan) to help a user choose one. | Page lists each mission type's purpose and phases and is linked from the core-concepts area. | Planned |
| **FR-006** | Charter-creation guidance must be consolidated into one authoritative how-to covering the full interview-to-generation flow. | A single how-to page carries the complete flow; the four currently scattered charter pages are reworked to link into it rather than duplicating its steps. | Planned |
| **FR-007** | One explanation page must enumerate every doctrine artifact kind (directive, tactic, styleguide, toolguide, paradigm, procedure, agent_profile, mission_step_contract) and state what each is for. | Page covers all 8 kinds, each with a purpose statement and an example use case. | Planned |
| **FR-008** | One how-to page must walk through creating a new doctrine artifact end to end. | How-to gives concrete, followable steps (CLI commands, file locations, schema) sufficient to author and activate a new doctrine artifact. | Planned |
| **FR-009** | Existing documentation must be re-audited, reclassified, and consolidated; redundant, stale, or superseded pages must be merged or removed rather than left alongside new content. | `docs-audit.md` (this mission's own disposition table — distinct from the pre-existing auto-generated `gap-analysis.md` coverage matrix, see research.md item 10) records a disposition (keep/merge/rewrite/remove) for every existing page; the count of merged/removed pages is reported. | Planned |
| **FR-010** | Reference-heavy sections (API, ADRs, Configuration, Operations, Migrations, Historical Archive) must be audited for factual accuracy and navigational placement; confirmed inaccuracies must be corrected and nav placement improved where it reduces overall complexity. | Audit findings are recorded; every confirmed inaccuracy is fixed within this mission; any nav placement change is reflected in `toc.yml`. | Planned |
| **FR-011** | The first mention of each glossary term on a documentation page must render as a link to that term's glossary entry, with a hover tooltip showing its definition. | For a sample spanning all restructured zones, every first occurrence of a glossary surface term is a working link carrying a title/tooltip attribute with the definition text. | Planned |
| **FR-012** | Each glossary entry must be individually addressable via a stable per-term anchor, not only linkable to the glossary page as a whole. | `glossary_page()`'s output includes a stable, unique anchor id per term; a direct link to that anchor resolves to the correct entry. | Planned |
| **FR-013** | A repeatable check must flag any documentation page using a glossary term in a non-canonical spelling or casing. | Running the check against the docs tree produces a report of flagged occurrences (zero or more) with page and line references. | Planned |
| **FR-014** | All authored and reviewed documentation content must comply with the project's Terminology Canon (e.g., "Mission" not "Feature" for the domain object). | A terminology scan of all mission-touched pages finds zero forbidden-term occurrences; `your-first-feature.md` is retitled and reworded accordingly. | Planned |
| **FR-015** | Top-level navigation must use hierarchical grouping (nested parent/child sections, e.g. submenus) so related pages are organized under expandable parent items rather than exposed as flat top-level entries. | `toc.yml` and any child TOCs express nested parent/child structure for both zones; no page that isn't a genuine top-level landing concept appears as a flat top-level entry — it is nested under a grouping parent instead. | Planned |

---

## Non-Functional Requirements

| ID | Description | Measurable Threshold | Status |
|----|-------------|-----------------------|--------|
| **NFR-001** | A new visitor must reach the start of the Get Started tutorial quickly from the homepage. | 2 clicks or fewer from `docs.spec-kitty.ai` home to the first tutorial step. | Planned |
| **NFR-002** | A new user must be able to complete install and a first mission in a bounded time. | 30 minutes or less end to end, following only the Get Started path (matches the existing tutorial's stated scope). | Planned |
| **NFR-003** | Top-level (unexpanded) navigation must be measurably narrower than today, achieved through the hierarchical grouping required by FR-015, not merely a flatter list. | 6 or fewer unexpanded top-level entries per zone are visible before any submenu is expanded, down from today's 16 top-level `docs/toc.yml` entries site-wide (verified count; 15 flat plus one already-nested "Historical Archive"). | Planned |
| **NFR-004** | Glossary auto-linking must not degrade to link spam. | The same glossary term is never auto-linked more than once on a single page (first mention only). | Planned |
| **NFR-005** | Every page this mission moved, renamed, or newly authored must carry a valid Divio classification. | 100% of pages this mission touched or created carry a valid `type:` frontmatter value (tutorial/how-to/reference/explanation). Pre-existing `docs/guides/` pages this mission did not otherwise touch are out of scope for this criterion (a full-tree frontmatter audit is separate, larger scope than an IA/onboarding mission — corrected post-mission-review from an earlier "100% of all `docs/guides/`" wording that the delivered scope never actually committed to). | Planned |
| **NFR-006** | No page may become undiscoverable after restructuring. | Every page retained after restructuring is reachable from top-level navigation within 3 clicks; zero pages are reachable only by direct URL. | Planned |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| **C-001** | Deployment/build tooling (DocFX pipeline invocation, GitHub Pages workflow triggers, custom domain/CNAME) is out of scope; only content, structure, and DocFX TOC/file-list configuration change. | Active |
| **C-002** | Divio types are used as internal editorial/frontmatter classification only; they are never exposed as customer-facing navigation vocabulary or forced into a literal 4-way top-level nav split. | Active |
| **C-003** | Full alias/banned-synonym glossary governance (a schema change to `.kittify/glossaries/spec_kitty_core.yaml` plus population) is out of scope for this mission; a GitHub issue is filed to track it as follow-up. | Active |
| **C-004** | All new/modified pages satisfy the existing CI-enforced doc-quality gates inherited from the `common-docs-consolidation` mission's doctrine (frontmatter description length 50-180 chars, anti-sprawl ratchet, relative-link validator). | Active |
| **C-005** | Strict end-user/contributor segregation (FR-003) is binding: no end-user-facing page links into contributor-only content without an explicit, clearly labeled cross-zone signal. | Active |
| **C-006** | This mission's own audit is authoritative over the abandoned `charter-end-user-docs-828` mission's gap-analysis; the latter may be consulted as input but is not treated as ground truth. | Active |

---

## Assumptions

1. **Build pipeline stability.** The existing DocFX build and GitHub Pages deployment continue working unmodified; this mission changes content, nav configuration, and adds one new build step (the glossary term-linking post-processor) that plugs into the existing `scripts/docs/` pipeline alongside `seo_postprocess.py`.
2. **Prior gap-analysis is input, not ground truth.** The abandoned `charter-end-user-docs-828` mission's `gap-analysis.md`/`research.md` may be reused as a starting input for the doctrine/charter gap findings, superseded by this mission's own audit where they conflict (C-006).
3. **"Wow" is defined operationally.** The "wow" moment is completing a first real mission (specify → plan → tasks → implement) end-to-end, consistent with the existing `getting-started.md`/`your-first-feature.md` tutorial's scope.
4. **Reference sections need touch-ups, not rewrites.** Pre-specify research found API, ADR, Configuration, Operations, Migrations, and Historical Archive sections structurally sound; this mission audits and corrects specific issues (FR-010) rather than rewriting them wholesale.
5. **Volume reduction is a success signal.** Consolidating and cutting redundant or stale documentation counts toward mission success, not only adding new pages — reflected in NFR-003 and Success Criteria below.

---

## Success Criteria

1. A first-time visitor can state who Spec Kitty is for and what it does within 15 seconds of landing on the homepage.
2. A new user goes from the homepage to a completed first mission in 30 minutes or less, using only in-doc navigation.
3. Zero pages are reachable only by direct URL; every retained page is reachable from top-level navigation within 3 clicks.
4. Unexpanded top-level navigation entries drop from today's 16 to 6 or fewer per zone, with deeper content organized into expandable submenus and end-user/contributor content clearly separated.
5. All 8 doctrine artifact kinds have a findable explanation, and creating a new one is covered by a single how-to.
6. Every glossary term's first appearance in reviewed docs is clickable, shows a tooltip definition, and deep-links to its own glossary entry.
7. A terminology/glossary-canonical-form check runs clean (zero flags) across all mission-touched docs at completion.
8. The number of distinct pages in the restructured end-user guide area decreases from the current 72-file baseline through consolidation, without loss of essential content.

---

## Key Entities

- **DocsPage** — a markdown file under `docs/`. Attributes: path, navigation zone (end-user/contributor), Divio type, target audience.
- **NavigationZone** — one of {end-user, contributor}; the two strictly segregated top-level areas established by FR-003.
- **NavigationGroup** — a nested `toc.yml` parent entry that collapses related pages under one expandable top-level item, per FR-015; a `DocsPage` belongs to exactly one `NavigationGroup` within its `NavigationZone`.
- **DoctrineArtifactKind** — one of {directive, tactic, styleguide, toolguide, paradigm, procedure, agent_profile, mission_step_contract}.
- **GlossaryTerm** — an entry in `.kittify/glossaries/spec_kitty_core.yaml` with a stable per-term anchor on the published glossary page (FR-012).
- **GlossaryLink** — an auto-generated, first-mention link from a doc page to a `GlossaryTerm`'s anchor, carrying a tooltip with the term's definition (FR-011).
- **Get Started Path** — the single onboarding sequence from homepage through install to first completed mission (FR-002).

---

## Out of Scope

- Deployment/build infrastructure changes (DocFX pipeline internals, GitHub Pages workflow, custom domain).
- Full alias/banned-synonym glossary governance — tracked as a follow-up GitHub issue (C-003).
- Non-English localization or translation.
- Analytics or telemetry on documentation usage.
- Video or screencast content.
- Wholesale rewriting of reference-heavy sections (only accuracy/nav touch-ups per FR-010).
