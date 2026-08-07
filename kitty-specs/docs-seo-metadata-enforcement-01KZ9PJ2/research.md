# Phase 0 Research: Docs SEO Metadata Audit and Enforcement

**Mission**: `docs-seo-metadata-enforcement-01KZ9PJ2`
**Date**: 2026-08-05

All findings below were established by direct inspection of this repository and of the live site at `https://docs.spec-kitty.ai`, not from general SEO practice. Where a claim could not be verified, it is marked as unverified.

---

## R-001 — The originating issue's premise is largely stale

**Decision**: Treat issue #1652's two named pages as already-satisfied, and re-aim the mission at the defects the audit actually found.

**Rationale**: Retrieved both pages live.
- `/api/slash-commands.html` returns 200 with `<title>Spec Kitty slash commands reference — CLI quick reference</title>` — verbatim the issue's own suggested direction — plus a full description and a correct canonical.
- `guides/install-spec-kitty.md` carries `title: Install Spec Kitty — macOS, Linux, and Windows Installation Guide`, satisfying the "install plus OS targets" criterion.

Both URLs cited in the issue (`docs/reference/slash-commands`, `how-to/install-spec-kitty.html`) appear in `scripts/docs/redirect_map.yaml` as **moved**:
```
how-to/install-spec-kitty.html: guides/install-spec-kitty.html
reference/slash-commands.html:  api/slash-commands.html
```
The reported "135 impressions, 0 clicks" therefore accrued to addresses that now serve `<meta http-equiv="refresh">` stubs. A stub has no content to click through to, which is a sufficient mechanical explanation for the zero-click pattern without invoking title quality at all.

**Alternatives considered**: Taking the issue at face value and rewriting the two titles. Rejected — it would have changed correct pages and left every real defect in place.

**Unverified**: The attribution of the click data to pre-move URLs is inference from the redirect map. Search Console access was not available, so this cannot be confirmed directly. Recorded as an assumption in `spec.md`.

---

## R-002 — The enforcement gate covers 2.4% of the site

**Decision**: Replace `test_docs_seo.py`'s hardcoded glob list with a resolver reading `docs/docfx.json`.

**Rationale**: Measured directly. `test_docs_seo.py::_published_markdown_files` globs:

| Pattern | Files matched today |
|---|---|
| `index.md` | 1 |
| `tutorials/*.md` | 0 |
| `how-to/*.md` | 0 |
| `how-to/harnesses/*.md` | 0 |
| `reference/*.md` | 1 |
| `explanation/*.md` | 0 |
| `recovery/*.md` | 0 |
| `3x/**/*.md` | 0 |
| `archive/**/*.md` | 14 |
| `migration/**/*.md` | 0 |
| **Total** | **16** |

Against 674 Markdown pages actually reachable through `docfx.json`'s `build.content` globs. Five of the ten patterns match nothing at all — they describe a directory layout that no longer exists.

The gate asserts title presence, description presence, and the 50–180 band. It has been asserting them against 16 files while reporting green for the tree.

**Root cause**: two independent authorities for "what is published" — `docs/docfx.json` (which the build follows) and this glob list (which the gate follows). A directory reorganisation moved one and not the other. This is precisely the "single canonical authority" failure the charter names.

**Alternatives considered**:
- *Manually re-sync the glob list.* Rejected — restores correctness for exactly as long as it takes someone to move another directory. It re-creates the bug.
- *Derive from the filesystem (`docs/**/*.md`).* Rejected — over-collects. It would sweep in `docs/plans/`, `docs/templates/`, and other trees whose publication status is `docfx.json`'s decision to make, not the test's.

---

## R-003 — 147 pages ship with no description tag

**Decision**: Hand-author a description for every ADR page (operator decision, specify phase).

**Rationale**: Measured across the pages `docfx.json` actually publishes:

| Category | Count |
|---|---|
| Built Markdown pages | 674 |
| Have both `title` and `description` | 527 |
| Have frontmatter but no `description` | 144 |
| Have no frontmatter at all | 3 |
| **Total lacking a description** | **147** |
| Lacking a `title` | 0 |

Every one of the 147 is under `docs/adr/`. Confirmed on the live render: an ADR page returns `grep -c 'name="description"'` → **0**, and its `og:description` is the module-level fallback string `"Spec Kitty documentation for CLI workflows, governed missions, AI harnesses, and 3.2 upgrades."` — identical across all 147.

**Alternatives considered**:
- *Machine-derive from each ADR's Context section.* Offered to the operator and explicitly rejected in favour of hand-authored quality (specify decision `01KZ9PJS30X2ZTDZAQS51XRTT8`).
- *`noindex` the ADR tree.* Offered and rejected; ADRs already draw impressions and are legitimate developer search landings.

---

## R-004 — The ADR exemption rests on an expired rationale

**Decision**: Remove `docs/adr/` from `description_length_check.py`'s `_EXCLUDE_PREFIXES` **after** the backfill lands, and correct the comment rather than silently deleting it.

**Rationale**: The exclusion is justified in-source as:

> ADR bodies are byte-identical to their pre-move originals (C-002, enforced by `test_adr_content_invariance`) and carry only bare `status` frontmatter — by design they have no `description`.

But `tests/docs/test_adr_content_invariance.py`'s own docstring records:

> **Retired earlier (2026-06-29):** the byte-identity content-invariance proof (`TestContentInvariance` …) was a transitional gate for the move itself, self-invalidating once merged to main.

and separately, *"With byte-invariance retired upstream (`ccd278061`)…"*. The constraint the exclusion cites no longer exists. The exclusion has been outliving its reason.

**What still holds**: `test_every_adr_has_bare_madr_status_frontmatter` reads each census ADR's frontmatter and asserts `status` is in the canonical MADR set. Inspected the assertion directly — it checks only that key. It does **not** enumerate permitted keys and does **not** fail on additional ones.

**Therefore**: adding `description:` to ADR frontmatter is compatible with the surviving census gate. Verified by reading the assertion, not by assuming.

**Alternatives considered**: Retiring the ADR exemption across all frontmatter gates. Rejected by operator decision `01KZ9Q2DC9WX6GTJZ57GE0BZNM` on locality-of-change grounds — the structural-lint frontmatter contract exempts ADR bodies through a separate styleguide config, and pulling 147 files into that contract's full field requirements would cascade scope well past this mission.

---

## R-005 — Source-level checks cannot see the render; build-level checks cannot see the PR

**Decision**: Both layers (operator decision `01KZ9Q2CMWF5H7TEXDFRSJ6SWD`).

**Rationale**: The two CI surfaces have disjoint capabilities.

| | `docs-freshness.yml` | `docs-pages.yml` |
|---|---|---|
| Trigger | every `pull_request` + push to main | push to `main`/`2.x`, path-filtered |
| Has .NET/DocFX | No | Yes |
| Can build `_site` | No | Yes |
| Catches defects | before merge | after merge |

`seo_postprocess.py` reads a description via `extract_description()` and falls back to boilerplate for OG/Twitter/JSON-LD, but **never writes a `<meta name="description">` tag**. A source-level gate cannot observe this: frontmatter can be perfectly correct while the render still omits the tag. Only an assertion against built HTML catches it. Conversely, a build-only gate reports the defect after it has already merged.

**Alternatives considered**: Source-only (cheapest, leaves the render unguarded — this is the exact defect class under repair) and build-only (proves the render, but post-merge). Both rejected as leaving a real defect class uncovered.

---

## R-006 — Path-filtering `docs-freshness` is safe here

**Decision**: Add a `paths:` filter covering the gates' full input set.

**Rationale**: The workflow currently declares a bare `on: pull_request` with no path filter, so it runs on every PR.

The standard hazard — a **required** status check skipped by a path filter leaves PRs indefinitely pending — was checked against live branch protection:

```
$ gh api repos/Priivacy-ai/spec-kitty/branches/main/protection --jq '.required_status_checks.contexts'
["drift-detector"]
```

`docs-freshness` is not a required context. The filter is safe.

**Correctness constraint**: the filter must cover every input the gates *read*, not merely `docs/**`. The structural lint loads policy from `packs/built-in/styleguides/common-docs.styleguide.yaml` and executes `packs/built-in/assets/docs_structural_lint.py`; the description and related gates live in `scripts/docs/`. A filter narrower than the true input set would silently stop guarding real changes — the same failure shape as R-002, reintroduced in a new place.

**Also noted**: because these gates are whole-tree scans rather than diff-scoped, a red `main` propagates to the next docs-touching PR. Consistent with existing repository behaviour; not changed here.

---

## R-007 — Navigation shape is a documented intent, not an enforced one

**Decision**: Achieve one-click depth through `docs/index.md` body links and guide cross-links; leave `docs/toc.yml` untouched (operator decision `01KZ9Q2E397AB1WJYZMAP0A0VB`).

**Rationale**: `docs/toc.yml` opens with a comment recording a prior mission's design:

> Exactly 2 top-level zone entries. Each zone has <=6 unexpanded top-level (immediate-child) entries … (FR-003, FR-015, NFR-003, C-005)

Zone 1 ("Using Spec Kitty") currently holds exactly 6 immediate children — at the documented cap. Adding either high-intent page as a top-level entry would breach it.

Searched `tests/` and `scripts/` for any automated enforcement of the zone count or the ≤6 cap and found none. The constraint is **advisory prose**, not a gate. It is therefore breakable without CI noticing — which is a reason to respect it deliberately rather than a licence to ignore it.

Neither page is currently referenced from `docs/toc.yml`; `docs/index.md` links `guides/getting-started.md` but neither the install guide nor the slash-command reference directly.

**Alternatives considered**: Nesting under existing toc parents (satisfies navigation visibility but is two clicks, contradicting NFR-009) and amending the ≤6 cap (overturns a prior mission's recorded decision). Both rejected by the operator.

---

## R-008 — The backfill will not trip the inventory lockfile

**Decision**: No lockfile regeneration task is required for the description backfill.

**Rationale**: `INVENTORY-LOCKFILE-DRIFT` has been a recurring CI failure (visible in recent commit history), so this was checked rather than assumed. `scripts/docs/inventory_lockfile.py` emits exactly `path`, `tag`, `divio_type`, `owning_workstream`, `current_target`, `notes`. `description` is not among them. Adding a `description` key to frontmatter therefore produces no lockfile delta.

**Caveat**: the 3 ADR README files currently have **no frontmatter at all**. Adding frontmatter to them introduces keys the lockfile *does* read (`tag`, `divio_type`, `owning_workstream`). If those keys are added, the lockfile will drift and must be regenerated. Adding only `title`/`description` avoids it. This is a live trap for the implementer and is called out in `quickstart.md`.

---

## R-009 — Step ordering in the pages workflow is load-bearing

**Decision**: Insert built-output verification **after** redirect-stub generation and its coverage check.

**Rationale**: `docs-pages.yml` runs, in order: `docfx build` → `seo_postprocess.py` → `glossary_linker.py` → `redirect_stub_generator.py generate` → `redirect_stub_generator.py coverage`. The ordering is deliberate and documented in the workflow's own comments: SEO and glossary injection run before stub generation *specifically so stubs never receive them*.

The verifier must therefore run last, so it observes the final artifact, including stubs, and can assert that stubs are correctly classified non-indexable (FR-012). Placing it earlier would let stub-related regressions pass unobserved.

`seo_postprocess.py::should_index` already excludes `toc.html`, `assets/`, anything containing `http-equiv="refresh"`, and anything already marked `noindex` — this is the existing, working definition of "indexable" and the verifier should reuse it rather than invent a second one (single canonical authority).

---

## Open items carried into design

| Item | Handling |
|---|---|
| DocFX glob semantics differ from Python `pathlib` glob semantics | The resolver must be validated against real output counts, not assumed translation. Contract specifies a non-vacuous floor assertion. See `contracts/published-page-set-resolver.md`. |
| Current green baseline unconfirmed (no Python environment in the planning session) | First implementer action; recorded in `plan.md` and `quickstart.md`. |
| Authored ADR descriptions are subject to the terminology guard (`docs/` is in its scan roots) | Task obligation in IC-04. |
