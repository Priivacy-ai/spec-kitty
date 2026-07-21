# Quickstart: Verifying the Docs IA & Onboarding Overhaul

This is the verification walkthrough a reviewer runs to confirm the mission's primary user
stories (spec.md) are actually satisfied, not just that individual pages were written.

## 1. First-time discovery, install, and first mission (User Story 1 / NFR-001 / NFR-002)

1. Open `docs/index.md` locally (or the built site). Confirm the first screen states who Spec
   Kitty is for and what it does, in plain language, before any governance/architecture term
   appears.
2. From the homepage, click through to the Get Started entry point. Confirm it takes 2 clicks
   or fewer to reach the first tutorial step (NFR-001).
3. Follow the path through install → `getting-started.md` → `your-first-mission.md`. Confirm no
   dead links and no detour through contributor-only content.
4. Time the full walkthrough — target 30 minutes or less (NFR-002).

## 2. Core concept literacy (User Story 2)

1. From the homepage or a core-concepts index, find the Ops-vs-Missions explanation page.
   Confirm it states a concrete decision rule (not just definitions).
2. Find the mission-types page. Confirm it lists exactly the 4 mission types present in
   `src/specify_cli/missions/` (software-dev, research, documentation, plan).
3. Find the charter how-to. Confirm it is a single page covering the full interview-to-generation
   flow, and that the four previously-scattered charter pages now link into it rather than
   duplicating its content.

## 3. Doctrine literacy and glossary trust (User Story 3)

1. Open `docs/doctrine/doctrine-kinds.md`. Confirm all 8 kinds (directive, tactic, styleguide,
   toolguide, paradigm, template, agent_profile, mission_step_contract) are present, each with a
   purpose statement and example.
2. Follow `docs/doctrine/create-a-doctrine-artifact.md` step by step against a scratch doctrine
   artifact. Confirm every step works as written.
3. On any page containing a glossary term, inspect the rendered HTML: the first occurrence is a
   link with a `title` attribute (tooltip) and resolves to
   `kitty-specs/glossary.html#term-{anchor_id}`; the second occurrence of the same term on the
   same page is plain text (NFR-004).
4. Run `pytest tests/architectural/test_glossary_canonical_terms.py -v` — expect a clean pass
   across all mission-touched pages.

## 4. Navigation breadth (FR-015 / NFR-003)

1. Open the built site's top navigation. Count unexpanded top-level entries per zone — expect
   6 or fewer per zone (down from today's verified 16).
2. Confirm exactly two top-level zones exist (end-user / contributor) and that expanding a
   contributor-zone group never surfaces an end-user page and vice versa (C-005).

## 5. No orphans, no broken redirects (NFR-006)

1. Run the existing anti-sprawl/link-validator doctrine tooling (inherited from
   `common-docs-consolidation`) over the full `docs/` tree.
2. Cross-check every path in `redirect_baseline_urls.json` still resolves — directly or via a
   generated refresh stub — after this mission's moves.

## 6. Terminology canon (FR-014)

1. Run `pytest tests/architectural/test_no_legacy_terminology.py -v` — expect a clean pass.
2. Confirm `your-first-feature.md` no longer exists under that name; its replacement
   (`your-first-mission.md`) and all inbound references use "Mission," not "Feature."
