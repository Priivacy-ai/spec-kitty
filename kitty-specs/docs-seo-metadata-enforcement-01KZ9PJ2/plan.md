# Implementation Plan: Docs SEO Metadata Audit and Enforcement

**Branch**: `feat/docs-seo-metadata-enforcement` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)
**Input**: Mission specification from `kitty-specs/docs-seo-metadata-enforcement-01KZ9PJ2/spec.md`
**Mission ID**: `01KZ9PJ2QG6BWH6MFMMZHVB72C`

---

## Summary

Every published documentation page must carry a unique, non-boilerplate description, and that must be enforced by a gate whose page set is **derived from the build's own content globs** rather than maintained beside them.

The current failure is not the one issue #1652 describes. The two pages it names were already fixed and have since moved. What is actually broken is that `tests/docs/test_docs_seo.py` hardcodes a glob list describing the *pre-move* directory layout; when `how-to/` → `guides/` and `reference/slash-commands` → `api/` moved, the build followed and the gate did not. The gate now covers **16 of 674** built pages and reports green regardless of the rest. Behind that blind spot, 147 architecture-decision pages ship with no description tag at all, sharing one boilerplate social description.

The technical approach has four separable parts: a resolver that makes the published-page set single-sourced from `docs/docfx.json`; a hardened source-level gate that consumes it; a render-path fix plus built-output verifier that proves what actually ships; and the content work (147 descriptions, navigation links).

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: DocFX 8.x (.NET tool, build-time only), PyYAML (already vendored via existing `scripts/docs/_inventory.py` frontmatter parsing), stdlib `json`/`re`/`pathlib`. No new runtime dependencies (C-004).
**Storage**: Filesystem only — Markdown frontmatter is the authoring surface; `docs/_site/` is the generated artifact. No database.
**Testing**: `pytest` under `tests/docs/`, markers `unit`/`fast` for source-level checks and `architectural` for gate boundary proofs, following the precedent already set by `tests/docs/test_description_length_gate.py`. Red-first: every gate change ships with a boundary test proving it can fail.
**Target Platform**: GitHub Actions Ubuntu runners (`blacksmith-4vcpu-ubuntu-2404`); source-level gates run without .NET, built-output verification runs only where DocFX is installed.
**Project Type**: single — a documentation build pipeline plus its test gates. No frontend/backend split.
**Performance Goals**: source-level gate ≤ 30 s over ~674 pages (NFR-007); documentation build wall-clock increase ≤ 10% (NFR-008). The existing structural lint holds a 5-second budget on the real tree, so per-page work must stay O(n) with a single read per file.
**Constraints**: complexity ceiling 15 (`C901`/`S3776`); repeated literals ≥3 occurrences hoisted to module constants (`S1192`); no `# noqa`/`# type: ignore` to reach green; every new branch/helper carries a focused test in the same change.
**Scale/Scope**: 674 built pages, of which 147 need authored descriptions; 3 scripts modified, 1 script added, 2 workflows touched, ~4 test modules touched or added.

---

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`; action doctrine loaded via `spec-kitty charter context --action plan`.

| Governing rule | Application to this mission | Status |
|---|---|---|
| **Single canonical authority** | This is the mission's central design driver. The published-page set currently has *two* authorities (`docs/docfx.json` and a hardcoded list in `test_docs_seo.py`) which silently diverged. IC-01 collapses them to one. | ✅ Pass — the mission exists to restore this |
| **DIRECTIVE_001 — Architectural integrity** | Four concerns with distinct boundaries: page-set resolution, source gate, render/verify, content. The resolver is consumed by the others but knows nothing about them. | ✅ Pass |
| **DIRECTIVE_003 — Decision documentation** | 8 decision moments recorded (5 specify, 3 plan). The stale `_EXCLUDE_PREFIXES` rationale is corrected in place rather than silently deleted, so the next reader sees why it changed. | ✅ Pass |
| **DIRECTIVE_010 — Specification fidelity** | Every IC traces to FR/NFR IDs; the traceability table in `spec.md` covers issue criteria including the two the audit added. | ✅ Pass |
| **DIRECTIVE_024 — Locality of change** | Drove the D2 decision: retire the ADR description exemption **only**, not the whole ADR frontmatter exemption set. | ✅ Pass |
| **DIRECTIVE_037 — Living documentation sync** | Behaviour changes here *are* documentation changes. The `_EXCLUDE_PREFIXES` comment, the gate's module docstring, and `docs/development/` guidance must move with the code. | ⚠️ Requires explicit task — see IC-02, IC-03 |
| **ATDD-first** | Acceptance is expressed as gate behaviour: the boundary proofs (missing / out-of-band / duplicate → RED) are written before the gate is widened. | ✅ Pass |
| **Glossary & terminology adherence** | "Mission" not "feature" (C-006). Note `docs/` prose is in the terminology guard's scan roots even though `kitty-specs/` is not — authored ADR descriptions are in scope for that guard. | ⚠️ Requires explicit check — see IC-04 |
| **Tiered rigour** | Highest rigour on the gate logic (it is the thing that failed silently); routine rigour on content authoring. | ✅ Pass |

**No charter violations require justification.** The two ⚠️ rows are not violations; they are obligations that must become tasks rather than assumptions, and they are recorded as such in the concern map.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/docs-seo-metadata-enforcement-01KZ9PJ2/
├── plan.md              # This file
├── spec.md              # Committed, substantive (13 FR / 9 NFR / 8 C)
├── research.md           # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   ├── published-page-set-resolver.md
│   ├── source-metadata-gate.md
│   └── built-output-verifier.md
├── checklists/
│   └── requirements.md
└── decisions/            # 8 recorded decision moments
```

### Source Code (repository root)

```
docs/
├── docfx.json                     # AUTHORITY for the published-page set (read, not modified)
├── toc.yml                        # Untouched — 2-zone/<=6 shape preserved (D3)
├── index.md                       # MODIFIED — one-click links to install + slash commands
├── adr/                           # MODIFIED — 147 pages gain `description:` frontmatter
│   ├── 1.x/ 2.x/ 3.x/
│   └── */README.md                # 3 files currently carry no frontmatter at all
└── guides/, api/, ...             # Cross-links added where topically relevant

scripts/docs/
├── _published_pages.py            # NEW — resolves the published-page set from docfx.json
├── description_length_check.py    # MODIFIED — drop docs/adr/ exclusion; add uniqueness +
│                                  #   boilerplate detection + coverage assertion
├── seo_postprocess.py             # MODIFIED — emit <meta name="description">
└── seo_verify.py                  # NEW — built-output verifier over docs/_site

tests/docs/
├── test_published_pages.py        # NEW — resolver contract + drift-detection proof
├── test_description_length_gate.py# MODIFIED — extend boundary proofs to new failure modes
├── test_docs_seo.py               # MODIFIED — consume the resolver; delete hardcoded globs
└── test_seo_verify.py             # NEW — built-output verifier boundary proofs

.github/workflows/
├── docs-freshness.yml             # MODIFIED — add paths: filter (D1)
└── docs-pages.yml                 # MODIFIED — add built-output verification step
```

**Structure Decision**: Single-project layout, matching the repository's existing documentation-tooling convention. Scripts live in `scripts/docs/` beside their siblings (`seo_postprocess.py`, `redirect_stub_generator.py`, `glossary_linker.py`), and their tests live in `tests/docs/` mirroring the script name. The new `_published_pages.py` takes the leading-underscore convention already used by `scripts/docs/_inventory.py` and `_render.py` for shared internal helpers, signalling it is a library rather than an entry point.

The built-output verifier is a **separate script** (`seo_verify.py`) rather than a `--verify` flag on `seo_postprocess.py`, because the two have opposite responsibilities — one mutates the render, the other asserts against it — and folding an assertion mode into the mutator would let a future change satisfy its own check.

---

## Complexity Tracking

No Charter Check violations. Table omitted.

One deliberate complexity note that is **not** a violation: this mission adds a second enforcement layer (built-output verification) where one layer exists today. That is not redundancy — the layers catch structurally different defects. The source gate cannot observe that `seo_postprocess.py` fails to emit a tag; the built-output gate cannot run on a PR without .NET. Collapsing to either one alone leaves a real defect class unguarded, which is what D1 settled.

---

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP.

### IC-01 — Single-sourced published-page set

- **Purpose**: Make "which pages are published" resolvable from exactly one authority, so a directory move can never again leave a gate guarding an empty tree.
- **Relevant requirements**: FR-002, FR-003, FR-013, NFR-005
- **Affected surfaces**: `scripts/docs/_published_pages.py` (new), `tests/docs/test_published_pages.py` (new); reads `docs/docfx.json`
- **Sequencing/depends-on**: none — this is the foundation the gates consume
- **Risks**: DocFX glob semantics are not Python `glob` semantics — `**.md` in DocFX matches recursively in a way `pathlib.Path.glob` does not replicate directly. The resolver must be validated against the *actual* built output count (674), not against an assumed translation. Getting this subtly wrong reproduces the exact silent-undercount bug being fixed, so the resolver needs a test asserting a realistic floor rather than only shape.
- **Design obligation (FR-013)**: exclusions (archive, generated mission-run pages, toc pages) must be an explicit enumerated list with a stated reason per entry, never an accidental glob gap.

### IC-02 — Source-level metadata gate hardening

- **Purpose**: Make a missing, boilerplate, or duplicated description fail at PR time, across the whole published tree rather than 2.4% of it.
- **Relevant requirements**: FR-002, FR-003, FR-006, FR-007, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006
- **Affected surfaces**: `scripts/docs/description_length_check.py`, `tests/docs/test_description_length_gate.py`, `tests/docs/test_docs_seo.py`
- **Sequencing/depends-on**: IC-01 (consumes the resolver). The **exclusion removal must not land before IC-04 completes**, or CI goes red for 147 files mid-mission.
- **Risks**: This is the highest-risk sequencing coupling in the mission. Two viable orderings — land descriptions first then flip the gate, or flip behind a shrinking allowlist. The first is simpler and preferred; it makes the gate flip a one-line change with an obvious green/red signal.
- **Living-documentation obligation (DIRECTIVE_037)**: the `_EXCLUDE_PREFIXES` comment currently cites byte-invariance "enforced by `test_adr_content_invariance`". That enforcement was **retired 2026-06-29** (`ccd278061`) per that module's own docstring. The comment must be corrected, not merely deleted, so the next reader learns the rationale expired rather than that it never existed.

### IC-03 — Render-path emission and built-output verification

- **Purpose**: Prove that what ships actually carries the metadata, closing the defect class where frontmatter is correct but the render drops it.
- **Relevant requirements**: FR-001, FR-005, FR-008, FR-010, FR-011, FR-012
- **Affected surfaces**: `scripts/docs/seo_postprocess.py`, `scripts/docs/seo_verify.py` (new), `tests/docs/test_seo_verify.py` (new), `.github/workflows/docs-pages.yml`
- **Sequencing/depends-on**: IC-01 for the indexable-page definition; independent of IC-02
- **Risks**: Step ordering inside `docs-pages.yml` is load-bearing and already subtle — `seo_postprocess.py` runs before `glossary_linker.py` and before `redirect_stub_generator.py` specifically so stubs never receive SEO or glossary injection. The verifier must run **after** stub generation (so it can confirm stubs are correctly excluded) but must not treat stubs as indexable. Inserting it in the wrong position produces either false failures on stubs or a blind spot.
- **Regression guard (FR-012)**: the existing redirect-coverage gate must stay green; the verifier must not alter stub markup.

### IC-04 — Architecture-decision page descriptions

- **Purpose**: Give each of the 147 ADR pages a unique, human-meaningful description so the tree stops sharing one boilerplate social description and starts describing itself.
- **Relevant requirements**: FR-004, NFR-002, NFR-003, NFR-004, C-008
- **Affected surfaces**: `docs/adr/1.x/**`, `docs/adr/2.x/**`, `docs/adr/3.x/**`, including the 3 README files that carry no frontmatter at all
- **Sequencing/depends-on**: none to start; **must complete before IC-02's exclusion removal goes strict**
- **Risks**: Highest-volume, lowest-coupling work in the mission and the natural parallelism candidate. Three specific hazards:
  - Descriptions must be hand-authored for meaning (C-008); a mechanical "ADR about X" template would satisfy the length band while defeating the purpose and would still trip the uniqueness check only by accident.
  - The 50–180 band is narrow; the uniqueness requirement means near-identical ADRs need genuinely distinguishing text.
  - `docs/` **is** in the terminology guard's scan roots (unlike `kitty-specs/`), so authored descriptions are subject to it — "Mission" not "feature", and the `primary`/`merge`/`routing` overloaded-term guidance applies.
- **De-risking fact established during planning**: the page-inventory lockfile emits `path`, `tag`, `divio_type`, `owning_workstream`, `current_target`, `notes` — **not** `description`. This backfill therefore does **not** trigger `INVENTORY-LOCKFILE-DRIFT`, which has been a recurring failure in recent history.
- **Compatibility fact established during planning**: the ADR census gate asserts only that `status` is a canonical MADR value; it does **not** forbid additional frontmatter keys. Adding `description:` is compatible with it.

### IC-05 — Internal link equity for high-intent pages

- **Purpose**: Put the install guide and slash-command reference one click from where readers actually land, without disturbing the navigation shape a prior mission deliberately chose.
- **Relevant requirements**: FR-009, NFR-009
- **Affected surfaces**: `docs/index.md`, topically relevant pages under `docs/guides/` and `docs/api/`
- **Sequencing/depends-on**: none
- **Risks**: `docs/toc.yml` documents a "exactly 2 zones, ≤6 unexpanded top-level entries" shape from a prior mission, and zone 1 sits at exactly 6. Per D3 this shape is **not** to be altered; one-click depth is achieved through `docs/index.md` body links and guide cross-links instead. Worth recording that this constraint is a comment, not an automated gate — a future contributor could breach it without CI noticing.
- **Secondary risk**: new relative links are subject to the existing relative-body-link gate and the `related:` edge validator; added cross-links must satisfy both.

### IC-06 — CI trigger scoping

- **Purpose**: Stop `docs-freshness` from running on pull requests that touch no documentation surface.
- **Relevant requirements**: supports NFR-007 (keeps the gate cheap enough to stay blocking); operationalises D1
- **Affected surfaces**: `.github/workflows/docs-freshness.yml`
- **Sequencing/depends-on**: none
- **Risks**: The classic failure mode — a *required* status check that gets skipped by a path filter leaves PRs pending forever — does not apply: branch protection on `main` requires only `drift-detector`. This was verified, not assumed. If the required-check set ever changes, this filter becomes a hazard.
- **Correctness obligation**: the filter must cover every input the gates *read*, not just `docs/**`. At minimum `docs/**`, `scripts/docs/**`, `packs/built-in/assets/docs_structural_lint.py`, `packs/built-in/styleguides/common-docs.styleguide.yaml`, and the workflow file itself. A filter narrower than the gates' true input set silently stops guarding real changes — the same class of bug this mission exists to fix.

---

## Decisions Recorded

| ID | Question | Resolution |
|---|---|---|
| `01KZ9Q2CMWF5H7TEXDFRSJ6SWD` | Enforcement gate layer | Both layers + `paths:` filter on `docs-freshness.yml` |
| `01KZ9Q2DC9WX6GTJZ57GE0BZNM` | ADR exemption retirement scope | Narrow — description only (DIRECTIVE_024) |
| `01KZ9Q2E397AB1WJYZMAP0A0VB` | One-click navigation approach | Home body + guide cross-links; `toc.yml` shape preserved |

Specify-phase decisions (`01KZ9PJQ…`, `01KZ9PJS…`, `01KZ9PJT…`, `01KZ9PJV…`, `01KZ9PJX…`) are recorded in `decisions/`.

---

## Known Environment Limitation

The planning session had **no working Python environment** — neither `uv` nor `pytest` was available on any interpreter present. Consequently the current green baseline of `docs-freshness` gates was **not** empirically confirmed; it is inferred from `main` being the merge base of a passing CI history.

**First implementer action** must be to establish that baseline (`uv sync`, then run the four `docs-freshness` gates unchanged) before making any edit, so that pre-existing red is attributed correctly per the repository's baseline-red policy rather than folded into this mission's diff.
