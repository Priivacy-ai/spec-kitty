# Mission Specification: Docs Quality Gate Hardening

**Mission Branch**: `docs/3253-docs-gaps`
**Created**: 2026-08-08
**Status**: Draft
**Input**: GitHub issue #3253 (docs SEO follow-ups from the #3248 landing squad), part of epic #2314; grounded by a pre-spec research squad (grounding / related-surfaces / tidy-first lenses).

## Overview

Issue #3253 catalogued three ways the documentation pipeline can pass **green while wrong**: the slash-command reference page can silently drift from the command registry, the published-page collector can silently under-count when a content subtree resolves empty, and a PR-time link/consistency gate can be skipped for deletions outside its path filter. This mission makes each failure **loud at the cheapest point** — PR time — instead of shipping green and being caught only by a post-merge backstop (or not at all).

The three surfaces were each verified against live code by the pre-spec squad; the canonical authority for the command set is `CONSUMER_SKILLS` in `src/specify_cli/shims/registry.py`, and the reference gate mirrors the existing `scripts/docs/check_cli_reference_freshness.py` pattern.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Slash-command reference cannot silently drift from the registry (Priority: P1)

A contributor adds or removes a consumer slash command in the command registry but forgets to update `docs/api/slash-commands.md`. Today the doc quietly falls out of sync (it currently documents 12 of the 15 registered consumer commands). This story makes CI catch that drift at PR time and backfills the three commands already missing.

**Why this priority**: User-facing correctness defect that is confirmed, self-contained, and the primary residual from #3248. A reference page that lies about the command surface misleads every consumer.

**Independent Test**: In a throwaway change, add a fake command to `CONSUMER_SKILLS` (or remove one from the doc) and run the new gate — it must fail, naming the drifted command; revert and it passes. Independently delivers a trustworthy reference page.

**Acceptance Scenarios**:

1. **Given** `docs/api/slash-commands.md` documents a set that equals `CONSUMER_SKILLS`, **When** the gate runs, **Then** it passes.
2. **Given** a consumer command exists in `CONSUMER_SKILLS` but has no section in the doc, **When** the gate runs, **Then** it fails and names the missing command(s).
3. **Given** the current tree (12 of 15 documented), **When** the three missing sections (`tasks-outline`, `tasks-packages`, `tasks-finalize`) are backfilled, **Then** the doc documents all 15 and the gate passes.

---

### User Story 2 - Published-page collection fails loud on a dropped subtree (Priority: P1)

A maintainer (or an incidental refactor) causes one declared content entry's `base` directory to resolve to zero pages. Today `_collect_entry_pages` returns an empty set silently, and the only non-vacuity check is against the *aggregate* floor of 500 — so as long as the surviving pages still exceed 500 (675 are published today), the loss hides in a ~175-page band and CI stays green.

**Why this priority**: This is the mission's core thesis and the exact silent-under-collection shape #3248 bounded but did not eliminate. A dropped documentation subtree that ships unnoticed is a real content-loss risk.

**Independent Test**: Point one declared content entry at a non-existent/empty base in a fixture and assert the resolver raises loud even though the aggregate stays ≥500. Independently delivers per-entry collection integrity.

**Acceptance Scenarios**:

1. **Given** every declared content entry resolves to ≥1 page, **When** the publication resolver runs, **Then** it succeeds and the count reflects the true live set.
2. **Given** one declared content entry resolves to zero pages while the aggregate union stays ≥500, **When** the resolver runs, **Then** it fails loud and names the empty entry.
3. **Given** the per-entry guard is in place, **When** `description_length_check.py` (which shares the resolver) runs, **Then** it inherits the same protection (proven by test).

---

### User Story 3 - The docs-freshness link-gate safety invariant is protected (Priority: P2)

A maintainer relies on `docs-freshness.yml` catching broken cross-tree links. Its `paths:` filter excludes `tests/**` and `kitty-specs/**`, so a PR deleting a linked target under those trees skips the gate at PR time; only the unfiltered `push: main` run catches it post-merge. This is **safe only** because docs-freshness is not a GitHub-required check (operator-confirmed non-required, 2026-08-08). This story records and protects that invariant so a future change cannot silently turn the residual gap into a PR-blocking hazard.

**Why this priority**: The gap is real but currently harmless; the value is preventing a latent future hazard, not fixing a live break. Cheaper and lower-risk than widening the filter (which risks #3147-style over-firing).

**Independent Test**: A regression test that fails if `docs-freshness` is declared a required status check (or, equivalently, asserts the required-check set is `{drift-detector}`), plus in-workflow documentation of the invariant. Independently delivers a tripwire on the safety assumption.

**Acceptance Scenarios**:

1. **Given** docs-freshness is not a required check, **When** the invariant test runs, **Then** it passes.
2. **Given** a change makes docs-freshness a required check without addressing the `paths:` gap, **When** the invariant test runs, **Then** it fails, pointing at the constraint.
3. **Given** a maintainer reads the workflow, **When** they inspect the `paths:` filter, **Then** the residual-gap + required-check invariant is documented in-file.

---

### Edge Cases

- A command exists in the registry but is **operator-only** (not in `CONSUMER_SKILLS`): the gate anchors on `CONSUMER_SKILLS` only, so operator skills are neither required nor forbidden in the consumer reference.
- A content entry is **intentionally empty**: an intentionally empty subtree must not be a *declared* content entry — the guard treats "declared but resolves to zero" as a failure; the fix is to stop declaring it, not to weaken the guard.
- The live published-page count naturally fluctuates by a page or two (675 today vs 674 in the issue): the aggregate floor deliberately tolerates that churn; the per-entry guard targets whole-subtree loss, not single-page drift.
- The required-status-check list is not readable via API with a non-admin token: the invariant test must assert against a source it can read (repo CI config / a recorded expectation), not a live privileged API call.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Registry-derived slash-command gate | As a maintainer, I want CI to fail when the documented command set differs from `CONSUMER_SKILLS`, so the reference page cannot silently drift. | High | Open |
| FR-002 | Backfill missing command sections | As a consumer, I want `tasks-outline`, `tasks-packages`, and `tasks-finalize` documented in the same style as existing sections, so all 15 consumer commands are covered. | High | Open |
| FR-003 | Per-content-entry non-vacuity assertion | As a maintainer, I want the publication resolver to fail loud when any declared content entry resolves to zero pages, so a dropped subtree cannot hide under the aggregate floor. | High | Open |
| FR-004 | Propagation coverage for shared resolver | As a maintainer, I want a test proving the per-entry guard also protects `description_length_check.py`, so the shared resolver's consumers inherit the fix. | Medium | Open |
| FR-005 | docs-freshness required-check invariant test | As a maintainer, I want a regression test that fails if docs-freshness becomes a required check without addressing the `paths:` gap, so the safety assumption is a tripwire not a comment. | Medium | Open |
| FR-006 | Document the docs-freshness paths invariant | As a maintainer reading the workflow, I want the residual-gap + non-required invariant documented in-file, so the constraint is discoverable. | Medium | Open |
| FR-007 | Note docs-pages seo_verify PR-time gap | As a maintainer, I want it documented that `docs-pages.yml`'s `seo_verify` runs push:main-only (a deploy-side analogue of the item-3 gap), so the known limitation is recorded. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Non-vacuous gates | Each new/changed gate MUST fail on a constructed regression fixture (self-mutation), not merely pass on the current tree; a vacuous gate is a defect. | Reliability | High | Open |
| NFR-002 | Canonical-pattern maintainability | New gate code follows the existing `check_cli_reference_freshness.py` shape; every new/changed function stays at ≤15 cyclomatic complexity and repeated (≥3) non-trivial literals are hoisted to constants. | Maintainability | High | Open |
| NFR-003 | Same-change test coverage | Every new branch/helper introduced by this mission has a focused test in the same change (new-code coverage ≥ project gate). | Testability | High | Open |
| NFR-004 | Negligible CI cost | The new slash-command gate adds < 2s to the docs CI job locally, consistent with sibling doc gates. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Single canonical registry | The slash-command gate MUST anchor on `CONSUMER_SKILLS` (`src/specify_cli/shims/registry.py`) as the sole authority; do not introduce or fork a second command registry. | Technical | High | Open |
| C-002 | Preserve the page floor | `MINIMUM_EXPECTED_PAGES = 500` MUST be preserved as a floor; the per-entry check is additive — do not replace the floor with an exact-count census. | Technical | High | Open |
| C-003 | docs-freshness stays non-required | The `paths:`-filter approach is safe ONLY while docs-freshness is a non-required check (operator-confirmed 2026-08-08). Making it required requires revisiting the filter; this mission encodes the invariant rather than widening the filter. | Technical | High | Open |
| C-004 | Terminology canon | New doc prose MUST use `<mission>` (never `<feature>`) placeholders, per the Terminology Canon. | Technical | Medium | Open |
| C-005 | Scope boundary | `related_validator.py` missing non-vacuity floor (#3264) and the two no-backstop CI workflows `orchestrator-boundary.yml` / `doctrine-charter-tests.yml` (#3265) are OUT of scope, tracked as separate follow-ups. Whole-file `<feature>`→`<mission>` sweep and a `relative_link_fixer.py` `Resolver` refactor are also OUT (they grow the file set). | Process | High | Open |
| C-006 | ATDD / red-first | Each gate lands with a failing-first test that is RED on the planning base branch and GREEN at the WP's final commit. | Process | High | Open |

### Key Entities

- **Command registry (`CONSUMER_SKILLS`)**: The canonical frozenset of consumer-facing slash commands (15 today). The single source of truth the reference gate diffs against.
- **Slash-command reference (`docs/api/slash-commands.md`)**: The human-facing page that must mirror the registry; currently documents 12.
- **Published page set**: The union of pages resolved from all declared content entries (675 today); guarded by an aggregate floor of 500.
- **Content entry**: A declared `(base, includes)` source of documentation pages; a declared entry resolving to zero pages is the failure this mission makes loud.
- **docs-freshness workflow**: A CI gate with a `paths:` filter (PR) + unfiltered `push: main` backstop; non-required, which is the invariant this mission protects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A PR that adds or removes a consumer command without updating the reference doc fails CI at PR time (previously shipped green).
- **SC-002**: `docs/api/slash-commands.md` documents 100% (15/15) of `CONSUMER_SKILLS`, with zero drift.
- **SC-003**: A PR that makes any declared content entry resolve to zero pages fails the publication gate loud, even when the aggregate union stays ≥ 500.
- **SC-004**: The published-page assertion reflects the true live set with no silent under-collection band for a dropped subtree (verified by a fixture in the 500–674 band).
- **SC-005**: A change that turns docs-freshness into a required check without closing the `paths:` gap fails the invariant test.
- **SC-006**: 100% of the mission's new gates are non-vacuous — each fails on its own regression fixture.

## Assumptions

- The command registry `CONSUMER_SKILLS` is and remains the canonical consumer-command set; `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS` is confirmed (during plan) to reconcile with it.
- Backfilled prose for the three `tasks-*` sections is authored to match the existing per-command section style (validated against the `professional-communications` / `plain-language` doctrine now active in the charter).
- docs-freshness remains non-required (operator-confirmed 2026-08-08); the invariant test encodes this as the tripwire.
- The live published-page count (675) is used in tests rather than the stale 674 from the issue text.
