# Implementation Plan: Docs Structural Sanity & Concern Guard

**Branch**: `docs/common-docs-section-audit` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/docs-structural-sanity-01KY53KJ/spec.md`

## Summary

Bring the `docs/` tree to a structurally-sane baseline by redistributing the misfiled subset the Common-Docs section audit found (concentrated in `architecture/`, plus a `plans/notes/` split-brain shadow tree and an incomplete section index), and replace the retired anti-sprawl ratchet with a durable guard: **extend the existing DIRECTIVE_042 + `common-docs` styleguide** (the concern-bucket→canonical-section map, the point-in-time allowlist, and a machine-parseable config block) — NOT a new directive — plus a `scripts/docs/docs_structural_lint.py` structural lint that LOADS that styleguide config and is wired into the docs CI surface (`.github/workflows/docs-freshness.yml`). The same extension reconciles the 4 artifacts still citing the retired "WP05 anti-sprawl structure ratchet" to name the new lint. Every move carries its relative-link (in-repo + non-`docs/`), page-inventory, and frontmatter obligations (Common-Docs ADR `2026-06-27-1`); the moved paths were never published, so **no redirect stubs are generated** — running the shared `regenerate-map` would derive `{}` and wipe a landed mission's redirects. Nothing lands in `guides/` (FR-003 boundary). Change mode is `bulk_edit` — an `occurrence_map.yaml` classifies every cross-file referrer so no link is silently missed; the redirect/link tooling is driven against **this** mission's map via `--occurrence-map` overrides (it defaults to a foreign mission — FR-010/C-007).

## Technical Context

**Language/Version**: Python 3.11+ (docs lint + doctrine artifact loading; matches repo baseline)
**Primary Dependencies**: existing `scripts/docs/` tooling (`redirect_map.yaml` + `redirect_stub_generator.py`, `relative_link_fixer.py`, `check_docs_freshness.py`, page-inventory lockfile), the doctrine tree (`src/doctrine/`), DocFX docsite (`toc.yml`), `ruamel.yaml`/`pyyaml` for frontmatter/lint parsing
**Storage**: files — Markdown docs, YAML doctrine artifacts, `redirect_map.yaml`, `3-2-page-inventory.yaml`
**Testing**: `pytest tests/docs/` (new lint unit tests + regression fixture), terminology guard (`tests/architectural/test_no_legacy_terminology.py`), `check_docs_freshness --ci`
**Target Platform**: Linux / CI (docs build + gates)
**Project Type**: single
**Performance Goals**: docs structural lint completes in < 5 s locally (NFR-003)
**Constraints**: no content into `docs/guides/` (C-001); path-pinned artifacts regenerated in place, never moved (C-004); redistribution targets limited to `engineering-notes/`, `operations/`, doctrine tree, or in-zone (C-002); EXTEND existing doctrine, do not mint (C-005); redirect tooling driven off this mission's map, not the foreign default (C-007)
**Scale/Scope**: 9 firm file moves + 2 borderline (default STAYS unless verified point-in-time) + 3 shadow-tree fold-then-deletes + 1 new lint module + a config-block/reconcile edit across **4 existing doctrine artifacts** (no new directive) + un-pin of 2 tooling scripts; ~25–30 referrer files to repoint (measured: `audits/`→11, `adr-connector`→6, `feature-detection`→5, `closeout`→4, `883-brief`→2) plus ≥1 non-`docs/` referrer (`brownfield-onboarding.paradigm.yaml`)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Charter present (`.kittify/charter/charter.md`), context mode `bootstrap`.

| Principle | Verdict | Note |
|---|---|---|
| Canonical sources, never improvise | PASS | The standard is delivered by EXTENDING the existing DIRECTIVE_042 + `common-docs` styleguide (not a new directive, not an ad-hoc page); the lint reads the styleguide's machine-parseable config as SSOT (C-005, FR-006, FR-011). |
| Unification not parity | PASS | The new lint is a single authoritative structural guard replacing the *retired* anti-sprawl ratchet, and the 4 artifacts still naming that dead ratchet are reconciled to cite it — it does not resurrect the ratchet or chase a dead quirk. |
| ATDD-first / red-first | PASS | The lint ships with a regression fixture that reintroduces each of the 4 audit finding-classes (red) before the tree is proven green (NFR-003, SC-003). |
| Terminology adherence | PASS | Terminology guard is part of the aggregate gate sweep (NFR-004); prose moves scrub point-in-time residue. |
| Campsite cleaning | PASS | The mission *is* a campsite pass on the docs tree; the guard prevents re-accretion. |
| Tiered rigour (DDD) | PASS | The lint is enforcement tooling (glue-tier) with focused unit tests per check; moves are content ops with gate verification. |

No violations → Complexity Tracking omitted.

## Project Structure

### Documentation (this mission)

```
kitty-specs/docs-structural-sanity-01KY53KJ/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (docs-lint contract, doc-standard schema)
├── occurrence_map.yaml  # Bulk-edit classification (change_mode: bulk_edit)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code / docs (repository root)

```
docs/
├── architecture/                  # FR-001/FR-004: point-in-time artifacts leave; index.md refreshed to full membership
│   ├── audits/                    #   → 7 dated forensic files move to plans/engineering-notes/
│   ├── 883-research-synthesis.md  #   → moves (self-declared point-in-time)
│   └── 883-mission-type-authority-brief.md  # → moves
├── plans/
│   ├── notes/                     # FR-003: 1.x shadow tree retired (3 drifted dups reconciled/deleted)
│   └── engineering-notes/         # destination for point-in-time artifacts (+ this mission's audit note)
├── migrations/                    # FR-005: closeout evidence relocates out
└── adr/3.x/2026-06-27-1-common-docs-reconciliation.md   # governing ADR

scripts/docs/
├── <new> docs_structural_lint.py  # FR-007: index-completeness (curated-complete) · point-in-time (plans/** + allowlist) · shadow-tree (non-nav) · frontmatter (in-scope)
├── redirect_map.yaml              # LEFT UNTOUCHED — moved paths never published; regenerate-map would wipe landed 01KW3SBK redirects (do NOT run it)
├── bulk_ref_rewrite.py            # FR-010: parametrize DEFAULT occurrence-map (keep symbol) / drive via --occurrence-map (prefix-anchored, incl. src//scripts/ refs)
├── inventory_lockfile.py          # FR-009: regenerate 3-2-page-inventory.yaml via --write (check_docs_freshness is read-only verify)
└── relative_link_fixer.py, check_docs_freshness.py  # existing, reused (relative_link_fixer walks docs/** ONLY, imports bulk_ref_rewrite DEFAULT)

src/doctrine/                      # FR-006: EXTEND 042-common-docs.directive.yaml + common-docs.styleguide.yaml (config block, FR-011);
                                   #         reconcile common-docs-curation + common-docs-scaffold tactics (dangling-ratchet refs)

tests/docs/
└── <new> test_docs_structural_lint.py  # regression fixture (4 finding-classes) + current-clean-tree pass + config-SSOT assertion (FR-011)
```

**Structure Decision**: Single project. Content moves within `docs/`; the guard lives in `scripts/docs/` (its natural home, where the retired ratchet lived) with tests in `tests/docs/`; the standard is an EXTENSION of the existing doctrine (DIRECTIVE_042 + `common-docs` styleguide) under `src/doctrine/`, not a new artifact. The redirect/link tooling in `scripts/docs/` is parametrized off its foreign-mission default and driven against this mission's `occurrence_map.yaml`.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Extend existing documentation doctrine + reconcile dangling-ratchet refs

- **Purpose**: EXTEND the existing DIRECTIVE_042 + `common-docs` styleguide with the concern-bucket→canonical-section map, the point-in-time allowlist, and a machine-parseable config block (FR-011), so placement is doctrine-defined; and reconcile the 4 artifacts still citing the retired "WP05 anti-sprawl structure ratchet" to name `docs_structural_lint.py`. NO new `documentation-placement` directive. Satisfies #2302.
- **Relevant requirements**: FR-006, FR-011; C-005.
- **Affected surfaces** (exactly 4 dangling-ratchet files + the config block):
  - `src/doctrine/directives/built-in/042-common-docs.directive.yaml` — `validation_criteria` (currently notes the ratchet retired, wires no replacement → cite the lint).
  - `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml` — `tooling` map rows + `quality_test` (rewrite the 4 "WP05 anti-sprawl structure ratchet" rows to the lint) **and** add the FR-011 machine-parseable config block.
  - `src/doctrine/tactics/built-in/common-docs-curation.tactic.yaml` — steps/quality lines naming the ratchet (lines ~50/53/58).
  - `src/doctrine/tactics/built-in/common-docs-scaffold.tactic.yaml` — 13-section-ratchet references (lines ~50/52/55/60).
- **Sequencing/depends-on**: none for the doctrine extension; the lint's NAME lands back here (reverse edge **IC-02 → IC-01**: once `docs_structural_lint.py` exists, its module path is written into these 4 artifacts). Highest existing directive number is 046 — no new directive is minted.
- **Risks**: the styleguide config block must stay in lock-step with the lint (FR-011 test); must not duplicate the rule DIRECTIVE_042 already binds.

### IC-02 — Structural docs lint (config-driven; CI enablement deferred to IC-06)

- **Purpose**: Mechanically enforce the standard — the durable successor to the retired ratchet — with 4 checks **scoped so the current clean tree passes** (NFR-003): index completeness (curated-complete sections only, start `architecture/`); point-in-time placement (`plans/**` broadly + allowlist `adr/**`, `plans/research/**`, `plans/investigations/**`); shadow-tree (non-nav content basenames); frontmatter (in-scope pages, excluding section READMEs).
- **Relevant requirements**: FR-007, FR-011; NFR-003, NFR-005, NFR-006. (FR-008 CI-gate enablement lands in IC-06, post-moves — wiring the lint into CI while the 7 audits + 3 shadows are still in place would red every PR.)
- **Affected surfaces**: `scripts/docs/docs_structural_lint.py` (LOADS the styleguide config — FR-011, no hard-coded policy), `tests/docs/test_docs_structural_lint.py` (4-class red fixture + a **post-move-shaped** clean-tree fixture + live **cohort-clean** assertions for `adr/**`/`plans/{research,investigations}/**`/nav basenames/the 3 ADR READMEs + a **config-SSOT assertion**). Does NOT own `docs-freshness.yml` (IC-06 wires CI post-moves).
- **Sequencing/depends-on**: consumes IC-01's config block (can start against a stub, finalize after IC-01); reverse edge — its module path is written back into IC-01's 4 artifacts. Its OWN clean-tree proof uses a post-move fixture, so it does NOT depend on IC-03/IC-04.
- **Risks**: false positives on legitimately-dated/nav/README files → the scoping above + the allowlist are load-bearing; must not reintroduce the ratchet's over-strict absolute-count behaviour (NFR-005/NFR-006 are scoped, not absolute).

### IC-03 — Architecture point-in-time redistribution + index completeness

- **Purpose**: Move the 9 firm + 2 borderline point-in-time artifacts to `engineering-notes/` and refresh `architecture/index.md` to full membership.
- **Relevant requirements**: FR-001, FR-002, FR-004; SC-001, SC-005.
- **Affected surfaces**: `docs/architecture/{883-*.md, audits/*, assessments/*}`, `docs/architecture/index.md`, `docs/plans/engineering-notes/`, ~13+ referrers.
- **Sequencing/depends-on**: index refresh (FR-004) follows the moves; verified by IC-02's completeness check.
- **Risks**: referrers in end-user-reachable pages (repoint the in-repo link, never move to guides/); page-inventory regeneration.

### IC-04 — Shadow-tree retirement

- **Purpose**: Reconcile the 3 `plans/notes/` drifted duplicates against their canonical twins (`architecture/`, `adr/3.x/`), preserve unique content, delete the shadows, repoint referrers, fix the `notes/` README.
- **Relevant requirements**: FR-003; NFR-005; SC-004.
- **Affected surfaces**: `docs/plans/notes/{feature-detection,gap-analysis-connector-installation-model,adr-connector-auth-binding-separation}.md` + README; canonical twins; ~12 referrers.
- **Sequencing/depends-on**: none; verified by IC-02's shadow-tree check.
- **Risks**: divergence (not pure duplication) — must merge unique content into the canonical copy before deleting, not blind-delete.

### IC-05 — Migrations closeout relocation

- **Purpose**: Move the dated mission-closeout evidence out of the operator-runbook zone to `engineering-notes/`, scrubbing point-in-time residue.
- **Relevant requirements**: FR-005; SC-001.
- **Affected surfaces**: `docs/migrations/teamspace-mission-state-920-closeout.md` → `engineering-notes/`; 4 referrers.
- **Sequencing/depends-on**: none.
- **Risks**: minimal; standard move + in-repo link repoint (no redirect stub — the closeout is not a published/baseline URL).

### IC-06 — IA-mechanics, tooling un-pin & aggregate gate sweep

- **Purpose**: Cross-cutting: parametrize the shared `bulk_ref_rewrite` tooling off its foreign-mission default and drive it against this mission's map; repoint in-repo relative links + a **non-`docs/` referrer sweep** (`relative_link_fixer` walks `docs/**` only); regenerate the page-inventory (`inventory_lockfile.py --write`); wire the lint into CI post-moves (`docs-freshness.yml`); and the aggregate gate verification (link integrity, freshness, terminology, tests/docs, lint clean). **The redirect map is left UNTOUCHED**, and `toc.yml` is verify-only.
- **Relevant requirements**: FR-009, FR-010, FR-008 (CI enablement); NFR-001, NFR-002, NFR-004; C-007.
- **Affected surfaces**:
  - **Do NOT run `redirect_stub_generator regenerate-map`.** The moved/removed paths are never-published (absent from `redirect_baseline_urls.json`), so derivation yields `{}` and OVERWRITES `redirect_map.yaml`, wiping the landed `01KW3SBK` mission's 149 published-URL redirects. `redirect_map.yaml` stays untouched (proven via `git status`). Upstream gap filed: redirect derivation is not cumulative across missions.
  - `scripts/docs/bulk_ref_rewrite.py` — parametrize `DEFAULT_OCCURRENCE_MAP` (foreign `01KW3SBK`) to resolve dynamically while **keeping the symbol defined** (`relative_link_fixer.py` imports it; `docs-freshness.yml` + 2 `tests/docs/` depend on it); always drive with `--occurrence-map <this mission's map>` (C-007). Prefix-anchored complement for `src/`+`scripts/` referrers of moved paths.
  - **Non-`docs/` referrer sweep (R6)**: `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml` references a moved audit (`relative_link_fixer` will NOT catch it); handled via `bulk_ref_rewrite --occurrence-map`. Recorded as a `manual_review` referrer in `occurrence_map.yaml`.
  - `docs/development/3-2-page-inventory.yaml` (regenerated via `inventory_lockfile.py --write`), `.github/workflows/docs-freshness.yml` (lint CI wiring). `docs/**/toc.yml` left untouched (verify-only grep — no toc references a moved path, no generator exists).
- **Sequencing/depends-on**: follows IC-03/IC-04/IC-05 (needs the final move set) + IC-02 (lint); the lint runs (and is CI-enabled) as part of the sweep.
- **Risks**: the shared tooling silently consuming the foreign `01KW3SBK` default if `--occurrence-map` is omitted (C-007); an implementer running the destructive `regenerate-map` (T023 guards against it). NFR-002 is reframed to "no baseline-URL 404 regression (moved paths never published) + in-repo relative links resolve" — not a 1:1 redirect count.
