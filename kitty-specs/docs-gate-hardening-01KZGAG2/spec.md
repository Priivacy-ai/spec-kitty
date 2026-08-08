# Mission Specification: Docs Quality Gate Hardening

**Mission Branch**: `docs/3253-docs-gaps`
**Created**: 2026-08-08
**Status**: Draft
**Input**: GitHub issue #3253 (docs SEO follow-ups from the #3248 landing squad), part of epic #2314; grounded by a pre-spec research squad and revised after a post-spec adversarial squad (see Revision History).

## Revision History

- **2026-08-08 r2 (post-spec squad fold):** Re-seamed FR-003 from per-*content-entry* to **per-include-glob, pre-exclusion** non-vacuity — a confirmed critical finding (two independent lenses, executed evidence): `docfx.json` declares only 2 content entries, so a per-entry guard stays green when a real subtree glob like `guides/` is dropped. Reframed FR-005 from an unobservable "required-check tripwire" to an assertion on the workflow's in-repo **safety structure**. Pinned committed negative tests per gate (was "throwaway"). Added reverse-direction drift scenario; defined "documented"; tightened FR-004, C-006, NFR-004, SC-002/003/004; corrected FR-007.

## Overview

Issue #3253 catalogued three ways the documentation pipeline can pass **green while wrong**: the slash-command reference page can silently drift from the command registry, the published-page collector can silently under-count when a documentation subtree resolves empty, and a PR-time link/consistency gate can be skipped for deletions outside its path filter. This mission makes each failure **loud at the cheapest point** — PR time — instead of shipping green and being caught only by a post-merge backstop (or not at all).

The canonical authority for the command set is `CONSUMER_SKILLS` in `src/specify_cli/shims/registry.py` (import-time-asserted equal to `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS` and to `command_installer.CANONICAL_COMMANDS`). The published-page collector is `scripts/docs/_published_pages.py`, whose page set is defined by the globs inside the two `build.content[]` entries of `docs/docfx.json` (excluded trees such as `archive/**` are stripped by `DEFAULT_EXCLUSIONS`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Slash-command reference cannot silently drift from the registry (Priority: P1)

A contributor adds or removes a consumer slash command in the command registry but forgets to update `docs/api/slash-commands.md`. Today the doc quietly falls out of sync (it documents 12 of the 15 registered consumer commands). This story makes CI catch drift **in both directions** at PR time and backfills the three commands already missing.

**Why this priority**: User-facing correctness defect, confirmed, self-contained, and the primary residual from #3248.

**Independent Test**: A **committed** negative test that (a) constructs a documented-set with an extra/missing command and asserts the gate exits non-zero naming the offender, and (b) asserts the current tree passes once backfilled. Not a manual throwaway edit.

**Acceptance Scenarios**:

1. **Given** the set of `## /spec-kitty.<name>` headings in the doc equals `CONSUMER_SKILLS`, **When** the gate runs, **Then** it passes.
2. **Given** a command exists in `CONSUMER_SKILLS` but has no `## /spec-kitty.<name>` heading in the doc, **When** the gate runs, **Then** it fails naming the missing command(s).
3. **Given** the doc has a `## /spec-kitty.<name>` heading for a command **absent** from `CONSUMER_SKILLS` (a retired command), **When** the gate runs, **Then** it fails naming the extra command (symmetric-difference, mirroring the sibling CLI-reference checker's REF-EXTRA guard).
4. **Given** the current tree (12 of 15), **When** the three missing sections (`tasks-outline`, `tasks-packages`, `tasks-finalize`) are backfilled, **Then** the doc's heading set equals `CONSUMER_SKILLS` and the gate passes.

---

### User Story 2 - Published-page collection fails loud on a dropped documentation subtree (Priority: P1)

A maintainer (or an incidental refactor) deletes or empties a declared documentation subtree — e.g. `docs/guides/` (76 pages today) — that is one **include glob** inside docfx's single root content entry. Today `_collect_entry_pages` OR-collapses all of an entry's globs, and the only non-vacuity check is against the *aggregate* floor of 500. Because the surviving pages (599 after dropping `guides/`) stay above 500 and the entry as a whole is still non-empty, the loss hides in the ~175-page band and CI stays green.

**Why this priority**: The mission's core thesis and the exact silent-under-collection shape #3248 bounded but did not eliminate. The post-spec squad proved a per-*content-entry* guard does NOT catch this — the guard must be **per-include-glob**.

**Independent Test**: A **committed** negative test using the existing `_write_config`/`synthetic_docs` harness in `tests/docs/test_published_pages.py`: declare two markdown globs (one populated ≥500, one empty), assert the resolver raises loud naming the empty glob — while confirming an equivalent per-entry check would stay green.

**Acceptance Scenarios**:

1. **Given** every declared include glob resolves (pre-exclusion) to ≥1 markdown page, **When** the resolver runs, **Then** it succeeds and the count reflects the true live set (675 today).
2. **Given** one declared include glob resolves to zero pages while the aggregate union stays ≥500 (e.g. `guides/**.md` emptied → 599), **When** the resolver runs, **Then** it fails loud naming the empty glob.
3. **Given** a fully-excluded tree (`archive/**`, stripped by `DEFAULT_EXCLUSIONS`) whose raw glob still matches ≥1 file pre-exclusion, **When** the resolver runs, **Then** it does **not** false-fail (the per-glob check is evaluated pre-exclusion).
4. **Given** the per-glob guard lives in the shared resolver, **When** `description_length_check.py` runs, **Then** it inherits the guard (proven by FR-004's test through that entry point).

---

### User Story 3 - The docs-freshness link-gate safety structure is protected (Priority: P2)

A maintainer relies on `docs-freshness.yml` catching broken cross-tree links. Its `paths:` filter excludes `tests/**` and `kitty-specs/**`, so a PR deleting a linked target under those trees skips the gate at PR time; only the unfiltered `push: main` run catches it post-merge. This is **safe only** because docs-freshness is not a GitHub-required check (**operator-confirmed this session, 2026-08-08**). Because the required-check setting lives solely in the GitHub control plane and produces no repo diff, a test cannot observe it flipping; instead this story pins the **in-repo structural properties that make the filter safe**, so a repo-side change that erodes them is caught and reviewed.

**Why this priority**: The gap is real but currently harmless; the value is preventing a latent future hazard, not fixing a live break. Cheaper and lower-risk than widening the filter (which risks #3147-style over-firing).

**Independent Test**: A committed test asserting, against the workflow file (repo-readable): (a) the `paths:` filter is present and still excludes `tests/**` and `kitty-specs/**`; (b) the unfiltered `push: main` backstop is present; (c) the documented safety-invariant comment is present. The test explicitly does **not** claim to observe live branch protection.

**Acceptance Scenarios**:

1. **Given** the workflow retains its paths filter, unfiltered `push:main` backstop, and invariant comment, **When** the structure test runs, **Then** it passes.
2. **Given** a repo-side change removes the `push:main` backstop or the documented invariant, **When** the structure test runs, **Then** it fails pointing at the missing safety property.
3. **Given** a maintainer reads the workflow, **When** they inspect the `paths:` filter, **Then** the residual-gap + non-required-safety invariant is documented in-file, reusing the existing "Required-check contract" comment idiom (as in `ui-e2e.yml`).

---

### Edge Cases

- **Operator-only commands**: the gate anchors on `CONSUMER_SKILLS` only; operator/dev skills are neither required nor forbidden in the consumer reference.
- **Excluded trees** (`archive/**`): the per-glob non-vacuity check is evaluated **pre-exclusion**, so a legitimately fully-excluded tree whose raw glob still matches files does not false-fail; an entry that is empty *pre-exclusion* is the real failure.
- **Heading form**: "documented" means a top-level `## /spec-kitty.<name>` heading. The existing `check_cli_reference_freshness._HEADING_RE` matches the space form `spec-kitty foo` and will **not** match the slash+dot form — a new heading extractor is required; only the *shape* and test harness are reused.
- **Single-page churn**: the aggregate floor deliberately tolerates ±1-page drift (675 vs the issue's 674); the per-glob guard targets whole-subtree loss, not single-page drift.
- **Required-check list is API-unreadable** with a non-admin token: the FR-005 test asserts repo-readable structural properties, never a live privileged API call.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Bidirectional registry-derived slash-command gate | As a maintainer, I want CI to fail when the set of `## /spec-kitty.<name>` headings differs (either direction) from `CONSUMER_SKILLS`, so the reference cannot drift. | High | Open |
| FR-002 | Backfill missing command sections | As a consumer, I want `tasks-outline`, `tasks-packages`, and `tasks-finalize` documented in the existing per-section prose style (using `<mission>` placeholders), so all 15 consumer commands are covered. | High | Open |
| FR-003 | Per-include-glob non-vacuity (pre-exclusion) | As a maintainer, I want the publication resolver to fail loud when any declared docfx include glob resolves (pre-exclusion) to zero pages, so a dropped subtree cannot hide under the aggregate floor. | High | Open |
| FR-004 | Propagation coverage through the sharing consumer | As a maintainer, I want a committed test that drives the empty-glob fixture through `description_length_check.py`'s own entry point and asserts it fails loud, so the shared-resolver consumer provably inherits the guard's failure path. | Medium | Open |
| FR-005 | docs-freshness safety-structure test | As a maintainer, I want a test asserting the workflow retains its `paths:` filter (still excluding `tests/**`/`kitty-specs/**`), its unfiltered `push:main` backstop, and its documented invariant, so a repo-side erosion of the safety structure is caught. | Medium | Open |
| FR-006 | Consolidate/relocate the docs-freshness invariant note | As a maintainer, I want the existing in-file invariant comment cross-referenced to FR-005's test (reusing the "Required-check contract" idiom), so prose and test co-evolve — not a re-addition of already-present content. | Medium | Open |
| FR-007 | Note docs-pages seo_verify PR-time gap | As a maintainer, I want it documented that `docs-pages.yml`'s `seo_verify` runs push-only (`main`/`2.x`) with no `pull_request` trigger — a deploy-side analogue of the item-3 gap — recorded as an intentionally verification-free note. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Committed negative test per gate | Each new/changed gate MUST ship a **committed, permanent** negative test that constructs a mutated input and asserts the gate raises / exits non-zero — not a throwaway manual check. A gate with only a green-on-current-tree test is a defect. | Reliability | High | Open |
| NFR-002 | Canonical-pattern maintainability | New gate code reuses the *shape* and test-harness idiom of `check_cli_reference_freshness.py` (parse → diff-against-authority → emit → non-zero exit); every new/changed function stays ≤15 cyclomatic complexity; repeated (≥3) non-trivial literals are hoisted. (Note: the heading regex is NOT reusable — see Edge Cases.) | Maintainability | High | Open |
| NFR-003 | Same-change test coverage | Every new branch/helper introduced by this mission has a focused test in the same change (new-code coverage ≥ project gate). | Testability | High | Open |
| NFR-004 | In-process gate, no heavy dependencies | The slash-command gate is a pure in-process set-diff — it imports `CONSUMER_SKILLS` and parses one Markdown file, with no subprocess, network, or application/runtime import beyond the registry — so its CI cost is inspection-verifiable rather than a timing claim. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Single canonical registry | The slash-command gate MUST import and anchor on `CONSUMER_SKILLS` (`src/specify_cli/shims/registry.py`) as the sole authority; do not fork or re-parse a second command set. | Technical | High | Open |
| C-002 | Preserve floor; guard pre-exclusion | `MINIMUM_EXPECTED_PAGES = 500` MUST be preserved as a floor; the per-glob non-vacuity check is additive and evaluated **before** `_apply_exclusions`, so excluded-by-design trees (`archive/**`) do not false-fail. Do not replace the floor with an exact-count census. | Technical | High | Open |
| C-003 | docs-freshness stays non-required | The `paths:`-filter approach is safe only while docs-freshness is a non-required check (**operator-confirmed this session, 2026-08-08**; note this is an operator assertion, not an API read — the token cannot read live branch protection). Making it required requires revisiting the filter; this mission encodes the safety structure rather than widening the filter. | Technical | High | Open |
| C-004 | Terminology canon | New doc prose MUST use `<mission>` (never `<feature>`) placeholders. | Technical | Medium | Open |
| C-005 | Scope boundary | OUT of scope, tracked separately: `related_validator.py` missing non-vacuity floor (#3264); the two no-backstop CI workflows (#3265); the whole-file `<feature>`→`<mission>` sweep; a `relative_link_fixer.py` `Resolver` refactor. Also OUT: re-structuring `docfx.json` into per-subtree content entries (the per-glob guard makes that unnecessary). | Process | High | Open |
| C-006 | ATDD / red-first (per artifact) | Each change lands test-first with a demonstrable RED. FR-002's backfill test goes genuinely RED on the base branch (doc is 12/15 today). For new-gate FRs (001/003/005) where test and gate are introduced together, the PR MUST carry captured evidence of the negative test failing before the gate exists (e.g. a test-only first commit or a recorded failing run), since importing not-yet-existing gate code errors rather than cleanly failing. | Process | High | Open |

### Key Entities

- **Command registry (`CONSUMER_SKILLS`)**: canonical frozenset of consumer slash commands (15 today); the sole authority the reference gate diffs against.
- **Slash-command reference (`docs/api/slash-commands.md`)**: hand-authored page (no generator, no parser today) that must mirror the registry via `## /spec-kitty.<name>` headings; documents 12 today.
- **Published page set**: the union of pages resolved from docfx include globs after exclusions (675 today); guarded by an aggregate floor of 500.
- **DocFX content entry / include glob**: `docs/docfx.json` declares **2** content entries; the meaningful documentation subtrees (`guides/`, `adr/`, `api/`, …) are **include globs inside the root entry**, not separate entries — hence the guard must be per-glob, not per-entry.
- **docs-freshness workflow**: a CI gate with a `paths:` filter (PR) + unfiltered `push: main` backstop; non-required, which is the safety structure this mission protects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A PR that adds or removes a consumer command without updating the reference doc fails CI at PR time (previously shipped green).
- **SC-002**: `docs/api/slash-commands.md` heading set equals `CONSUMER_SKILLS` exactly (symmetric-difference empty — no missing and no retired-command sections).
- **SC-003**: A PR that empties any declared include glob fails the publication gate loud naming the glob, even when the aggregate union stays ≥ 500 (verified by the `guides/**.md`-emptied → 599 fixture).
- **SC-004**: A fixture with two declared globs — one ≥500 pages, one **zero** pages — fails the per-glob guard while an equivalent per-content-entry check would pass, demonstrating the seam is at the right granularity.
- **SC-005**: A repo-side change that removes the `docs-freshness.yml` `push:main` backstop, widens the paths filter to include the excluded trees, or deletes the documented invariant, fails the FR-005 structure test. (The test does not and cannot observe a live GitHub branch-protection change.)
- **SC-006**: 100% of the mission's new gates ship a committed negative test that fails on its regression fixture (non-vacuous).

## Assumptions

- `CONSUMER_SKILLS` is and remains the canonical consumer-command set; its import-time equality with `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS` (`registry.py:87`) is an executing invariant, not a deferred check.
- Each docfx `files` markdown glob is treated as an independent subtree contract that must resolve to ≥1 page pre-exclusion; `docs/docfx.json` is not slated to be re-structured into per-subtree entries during this mission (if it were, the guard granularity would need revisiting — see C-005).
- docs-freshness remains a non-required check (operator-confirmed this session); FR-005 encodes the repo-readable safety structure as the tripwire, not the live setting.
- Backfilled prose for the three `tasks-*` sections matches the existing per-command section style, validated against the `professional-communications` / `plain-language` doctrine active in the charter.
- The live published-page count (675) is used in tests rather than the stale 674 from the issue text.
