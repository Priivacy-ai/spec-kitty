# Implementation Plan: Common Docs Convergence

**Branch**: `docs/common-docs-cleanup` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/common-docs-convergence-01KZMTR9/spec.md`
**Revisions**: post-spec squad (spec) → this plan → post-plan squad ([reviews/post-plan-squad.md](./reviews/post-plan-squad.md), folded below).

## Summary

Converge Spec Kitty's ~700-file docs corpus onto the repository's sanctioned Common Docs section set, driven by a bulk-edit move spine and the canonical `scripts/docs/` tooling, with audience metadata formalized first to ground rewrites. Two foundations (audience formalization; the occurrence-map/redirect spine + resolver/lint code) land before any file moves; every shared manifest is written by exactly one terminal reconcile WP; content rewrites are bounded, fact-guarded, and split from mechanical moves; and new pre-merge gates make acceptance verifiable on PR.

## Technical Context

**Language/Version**: Python 3.11+ (gates/tests/tooling); Markdown + YAML (docs content); DocFX (published site)
**Primary Dependencies**: Existing only — `docfx`, `ruamel.yaml`, `pytest`, and `scripts/docs/*` (`redirect_stub_generator.py`, `relative_link_fixer.py`, `related_validator.py`, `inventory_lockfile.py`, `_guards.py`, `build_cli_reference.py`, `check_cli_reference_freshness.py`). **No new runtime dependencies.**
**Storage**: N/A (filesystem; docs + committed manifests)
**Testing**: `pytest` (`tests/docs/`, `tests/architectural/`) + new gates: non-vacuous audience resolver, touched-set presence/description/placement gates, occurrence-map⊆redirect-map + reverse rename-reconciliation grep gate, charter authority-path resolution test; new pre-merge DocFX build job (GitHub Actions `pull_request`, registered required).
**Target Platform**: repo docs tree + published DocFX site (docs.spec-kitty.ai) + CI (GitHub Actions)
**Project Type**: single (repo tooling + docs content)
**Performance Goals**: structural-lint < 5s over corpus; PR gate set within docs-freshness budget (note: full docfx build adds minutes)
**Constraints**: DocFX build zero-error on PR (required check); 0 dangling `related:`/`audience:` refs; all mission gates non-vacuous & touched-scoped where presence-based; shared surfaces single-threaded; no new deps; charter authority paths preserved or updated in-commit
**Scale/Scope**: ~700 pages; ~151 redirect entries (cumulative spine incl. prior closed mission's 29 moves); 5 root dirs + ~8 loose root files; `development/`(22)+`guides/`(59) subdivision; 13 free-text `audience:` values to migrate; 3 dead authority paths

## Charter Check

Charter present + activated. Aligned: DIRECTIVE_042 (governing), 044 canonical-sources (FR-021 canonical tooling), 035 bulk-edit (own occurrence_map), publication-authority (NFR-009), 047 audience (US1), 037/delete-stale (FR-024/FR-006), no-legacy-terminology (NFR-004), 025/024 (bounded WP scope, C-011). No violations; Complexity Tracking not required.

## Project Structure

```
docs/{13 canonical sections} + development/            # sanctioned CONTENT sections
docs/{assets, templates/spec-kitty}                    # sanctioned NON-content
docs/context/audience/{internal,external}/             # persona catalog (SSOT)
scripts/docs/                                          # canonical tooling (extended, not replaced) + NEW audience resolver
packs/built-in/{styleguides/common-docs.styleguide.yaml, directives/042|047, assets/docs_structural_lint.py}
tests/docs/                                            # resolvers, touched-set gates, authority-path, rename-reconcile
.github/workflows/                                     # docs-freshness.yml (+audience --strict); NEW required pre-merge docfx build
```
**Structure Decision**: single-project repo; docs under `docs/`, gate/tooling under `scripts/docs/`+`packs/built-in/`, tests under `tests/docs/`, CI under `.github/workflows/`. No new top-level trees.

## Implementation Concern Map

> Concerns, not WPs. Dependency edges are load-bearing (encode the post-plan squad's corrected DAG).
> **Shared-surface rule (C-011):** the ONLY writer of `redirect_map.yaml`, `redirect_baseline_urls.json`
> (read-only), `docs/toc.yml`, `docs/docfx.json`, `docs/llms.txt`, per-section `toc.yml`, the inventory
> lockfiles, `docs/plans/**` link-targets, `common-docs.styleguide.yaml`, and the merged
> `occurrence_map.yaml` is IC-11. Movers (IC-04..07,09,10) run in-tree `relative_link_fixer` on files
> **they own** and emit a per-WP occurrence-map ledger fragment; they never touch the shared manifests.

### IC-01 — Audience formalization *(foundation; gates rewrites)*
Use existing `docs/context/audience/` catalog (SSOT); canonize `audience:` in 042/047 + styleguide (with `tooling:` row); **kebab-rename the snake_case persona files here** and migrate the 13 free-text values directly to the FINAL kebab paths; pre-author any new personas needed by movers (no mover writes the catalog — a C-003 authority path). FR-001..004, C-012. **depends-on:** none. **Precedes** IC-06, IC-08.

### IC-02 — Move spine & redirect tooling *(foundation; gates all moves)*
Author this mission's `occurrence_map.yaml` as a **collapsed cumulative spine** — every entry maps a baseline path to its FINAL destination, and the prior closed mission's 29 moves are carried so `regenerate-map` reproduces all prior baseline URLs + the new ones (the tool has no additive-merge and `_relocate` is single-move). Repoint the closed-mission **default** (`MISSION_SLUG`/`DEFAULT_OCCURRENCE_MAP`) and always pass `--occurrence-map <this mission>` (the flag/subcommands already exist). FR-021, C-007, C-010, NFR-010. **depends-on:** none. **Precedes** IC-03..07, 09, 10, 11.
- **Open build decision (OB-1):** collapsed-data spine vs a code change to union multiple mission maps / iterate `_relocate` to a fixed point. Default: collapsed-data spine + a regen-reproduces-all test (avoids editing shared closed-mission tooling).

### IC-03a — Gate scaffolding *(advisory foundation, before movers)*
Build (not yet blocking): non-vacuous audience resolver (scalar-or-list; `assert_examined_floor`); touched-set gates (git-diff denominator) for audience-presence + description-band + audience-placement (internal→development/, external→guides/); occurrence-map⊆redirect-map cross-check + **reverse** `git --find-renames ⊆ occurrence-map` reconciliation; `relative_link_fixer --check` in the PR set; extended structural-lint check-fns + config fields (one-index-per-dir, sanctioned-section membership) — each as check-fn+config-field+focused test, section lists in the styleguide block; scope the docs-freshness gate to changed paths / baseline-diff classification (#3147). FR-017/018/023, NFR-002/005, gate-coverage findings. **depends-on:** IC-01, IC-02.

### IC-03b — Gates blocking + pre-merge build *(terminal verification)*
Flip the structural invariants to blocking and register the **required** pre-merge DocFX build job (zero-error build blocks; `redirect coverage` + `seo_verify` on built `_site`; block-vs-advise steps explicit). Final green verification after IC-11. NFR-001/003, SC-006. **depends-on:** IC-11.
- **Open build decision (OB-2):** a standing single-root/sanctioned-section **blocking** lint reverses #2851 (anti-sprawl ratchet deliberately retired). Default: enforce structural invariants as IC-03b terminal verification + curation, NOT a standing per-PR blocking lint, unless #2851 is re-sanctioned.

### IC-04 — Single-root consolidation
Retire/rehome docs outside `docs/` to the sanctioned set. FR-005/006, NFR-006, SC-002. **depends-on:** IC-02, IC-03a. Feeds IC-11. Precedes IC-06 (examples rehome). Landmines resolved in occurrence_map (README `<img>` manual rewrite; `spec-driven.md` test; `spec-kitty-mission-workflow.md` → architecture/authority; `docs/output/` deliverables repoint; research→integrations/RETIRE not plans).

### IC-05 — Section canon, architecture collapse & ADR-era structure
Dissolve non-canonical/umbrella sections; collapse `architecture/` version shadow to one living design (closes #2215; repoint `src/doctrine/templates/diagrams/README.md` anchors FIRST); **own all `adr/<era>/` structure incl. era-index README→index** (the #2227 split stated here). FR-007/008, NFR-007, SC-003. **depends-on:** IC-02, IC-03a. Feeds IC-09, IC-11. `docs/api/` consolidation (fold `reference/`→`api/` incl. index) owned here; IC-04 only drops `batch-api-contract.md` in.

### IC-06 — How-to audience routing, Divio typing & subdivision *(split by tree)*
Two mover WPs — **guides** and **development** — each does route+type+subdivide as one pass (avoids double-move). A separate small sub-WP makes the single `structural_lint_config.concern_bucket_to_section`/`guides_boundary` routing edit both consume. FR-009/010/011, SC-007/009. **depends-on:** IC-01, IC-02, IC-04. Feeds IC-11.

### IC-07 — Naming & index normalization
One `index.md` per in-scope dir; kebab-case (persona files already handled in IC-01). FR-012/013, SC-004. **depends-on:** IC-04, IC-05, IC-06. Feeds IC-11.

### IC-08 — Bounded, fact-safe rewrites
Prose-only scanability rewrites; **enumeration produced by /spec-kitty.tasks strictly from the IC-04..07 touched-set, numeric per-WP page ceiling** (no page outside a completed move is eligible); per-page fidelity ledger (claim→code/test backing) as a required review artifact (NFR-009); behavior-doc pages regenerated via `build_cli_reference.py`. FR-014. **depends-on:** IC-01 + **the page's FINAL path settled (post-IC-07)**. Separate reviewable WPs from movers.

### IC-09 — Governance paths & rollups
Repair all 3 dead authority paths; regenerate rollups in place (sequence vs ~10 owning missions); reconcile stale `plans/notes/` terminology exemption. FR-019/020, NFR-004, C-003/005. **depends-on:** IC-04 (glossary path), IC-05 (architecture paths). Feeds IC-11.

### IC-10 — ADR dated-prefix + `doc_status` polish & migrations curation
Non-era ADR dated-prefix + redundant-`doc_status` fixes (#2887); migrations delete-stale (FR-024). Era-index work belongs to IC-05. **depends-on:** IC-02 (renames → occurrence-map), IC-03a. Feeds IC-11. *(Can start in parallel with IC-01/02 but is NOT a leaf — its renames need the spine + gates.)*

### IC-11 — Terminal nav/redirect reconcile WP *(single writer of all shared surfaces)*
Runs once after IC-04..07/09/10: merges the per-WP occurrence-map fragments into the collapsed spine, regenerates the derived `redirect_map.yaml` + all nav manifests + inventory lockfiles, applies `docs/plans/**` inbound link-target fixes, and verifies coverage. FR-016/020, C-009/011, NFR-010, SC-005/010. **depends-on:** all movers.

**DAG**: `IC-01, IC-02, IC-10(start)` ∥ → `IC-03a`(needs 01+02) → `IC-04` → `IC-05`, `IC-06`(needs 01+04) → `IC-07` → `IC-08`(per page, post-07) ; `IC-09`(needs 04+05) → **`IC-11`(terminal, all movers incl. 10)** → `IC-03b`(terminal blocking + build). No fully-parallel leaf; IC-01/IC-02/IC-10 are the parallel *start* set.

## Gate Coverage Matrix (NFR/SC → verifying gate)

| Criterion | Gate | Where |
|-----------|------|-------|
| NFR-001/SC-006 | required pre-merge DocFX build (zero-error blocks) | IC-03b |
| NFR-002/SC-005 | non-vacuous `related`+`audience` resolvers `--strict` + `relative_link_fixer --check` | IC-03a |
| NFR-003/006/007/SC-003/004 | extended structural-lint (terminal blocking; see OB-2) | IC-03a/b |
| NFR-005 | occurrence-map⊆redirect-map + reverse rename-reconcile grep gate | IC-03a |
| NFR-008 presence/description | touched-set (git-diff denominator) gates | IC-03a |
| SC-007 placement | touched-scoped audience-placement check | IC-03a |
| NFR-009 | per-page fidelity ledger (required artifact) + `check_cli_reference_freshness` on PR | IC-08/IC-03a |
| NFR-010/SC-010 | `coverage` + `check-map` on the collapsed cumulative spine | IC-02/IC-11 |
| NFR-004 | terminology guard + `plans/notes/` exemption reconcile | IC-09 |
| #3147 | freshness gate scoped to changed paths / baseline-diff classifier | IC-03a |

## Open Build Items (carry into tasks)
- **OB-1** cumulative redirect spine: collapsed-data (default) vs code-merge — resolve in IC-02 with a regen-reproduces-all-151 test.
- **OB-2** single-root blocking lint vs #2851: default keep as terminal verification + curation; re-sanction #2851 to make it a standing gate.
- Occurrence-map destinations fully resolved (no `NAV_ZONE`/`OR`/`RETIRE_OR_` placeholders) before `implement` — see `occurrence_map.yaml`.
