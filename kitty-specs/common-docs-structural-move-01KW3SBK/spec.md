# Common Docs Structural Move (Mission B)

**Mission**: `common-docs-structural-move-01KW3SBK` · **Type**: software-dev · **Parent**: epic #651 · **Closes**: #2165, #2054, #2192 · **Folds**: #1815

> **Mission B of the Common Docs split** (post-spec + 3-lens pre-planning squad, 2026-06-27). Mission B performs the actual consolidation **against the governed, self-testing foundation merged by Mission A** (`common-docs-consolidation-01KW3Q6M`). It is **gated on Mission A's reconciliation ADR being accepted and merged** (the dependency is a merge boundary, not intra-mission ordering). Mission B dogfoods A's directive/styleguide/tactics and **flips A's report-only rulers to blocking** against the cleaned tree.

## Overview

Mission A decided every mechanism and shipped the rulers report-only. Mission B executes the move with no remaining design questions. The collapse is materially smaller than first framed: there are **two top-level documentation roots** today — `architecture/` and `docs/` — because `development/` and `engineering_notes/` have lived as `docs/` **subdirectories** (`docs/development/`, `docs/engineering_notes/`) since January. So the structural job is to **fold `architecture/` into `docs/` and re-section the existing `docs/development/` + `docs/engineering_notes/`** into the 13-section Common Docs structure, **convert the 117 unique ADRs** into `adr/<era>/` with YAML frontmatter, rewrite the live doc-path references (`src/` first — count regenerated at plan time), apply the DocFX redirect mechanism A chose, rewrite the DocFX content manifest + TOCs, resolve the shadow trees correctly, backfill frontmatter, and switch the rulers to blocking.

**Squad-verified facts (the floor):**

- **ADR census (live):** **117 unique ADRs** — **97 unique under `<era>/adr/`** plus **20 era-less** in flat `architecture/adrs/`. These are spread over **188 ADR files** (the extra **47 are byte-identical flat mirrors** of era ADRs duplicated under `architecture/adrs/`) + 4 README = 192 total. **0 of the 117 use YAML frontmatter.**
  - **DECISION:** convert the **117 unique** ADRs. The **47 byte-identical flat `architecture/adrs/` mirrors are dropped** as the flat shim closes (no information loss — they are exact duplicates). The **20 era-less** ADRs migrate to **`adr/3.x/`** (assigned by date, per A's plan).
- **References:** the prior "~2,190 occurrences / ~571 files" blast radius is **not reproducible** — live sweeps bracket **452 ↔ 7,614 and trend up**. **Regenerate the occurrence map from the live tree at plan time**; treat **~571 as a likely-LOW estimate (active undersizing risk).**
- **Runtime read surface:** `authority_paths.py` lives at **`src/charter/context_renderers/authority_paths.py`** (not `src/specify_cli/charter/...`) and **already reflects the #2160/#2115 ADR-default flip** (`architecture/2.x/adr/` → `architecture/3.x/adr/` with back-compat). The old "~3 runtime-critical reads" snapshot is **stale** — **re-derive the runtime read surface at plan time** (live: ~11 `src/` files touch `architecture/<era>/adr`; ~33 touch doc roots).
- **Inventory:** **580-row** page inventory (`docs/development/3-2-page-inventory.yaml`).
- **"Drift-free" floor is FALSE — split it:** the legacy `check_docs_freshness.py` is **green (exit 0)**, but A's new lockfile generator (`inventory_lockfile.py --strict`) reports **drift against the committed inventory: 252 removed / 296 changed (0 added)**. That gap **IS FR-010's backfill workload**, not a clean pre-existing state.
- DocFX on GitHub Pages (no native redirect); `docs/3x/` carries **live charter content** (not a pure shadow).

## User Scenarios & Testing

### The maintainer finds the current design from one root
After the move, a reader starts at `docs/index.md` and reaches the current design in `docs/architecture/` with no era detour and no parallel tree — resolving #2054's "current design not discoverable."

### Every old URL still resolves
A previously-published page was moved; its prior public URL resolves via a generated redirect stub (the mechanism A chose), validated against a captured baseline URL inventory.

### A re-introduced violation is now rejected
With A's rulers flipped to blocking, a second doc root / missing `index.md` / un-frontmattered ADR / re-introduced shadow tree fails CI.

### No ADR is lost — including the 20 era-less ones
All **117 unique** ADRs (including the 20 that lived only in flat `architecture/adrs/`) are present post-move under `adr/<era>/` with YAML frontmatter and unchanged decision content; the 47 byte-identical flat mirrors are dropped with the shim.

## Requirements

### Functional

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Fold `architecture/` into the single 13-section Common Docs `docs/` root and **re-section the existing `docs/development/` + `docs/engineering_notes/`** (already `docs/` subdirs since January, not parallel roots) into that structure per Mission A's ADR. This is a two-root collapse (`architecture/` + `docs/`), not four. | Draft |
| FR-002 | Move the **97 unique era ADRs** into `docs/adr/<era>/` **and migrate the 20 era-less ADRs** (flat `architecture/adrs/`) into `docs/adr/3.x/` (assigned by date, per A's plan); **drop the 47 byte-identical flat mirrors** as the flat shim closes. All **117 unique** ADRs preserved. | Draft |
| FR-003 | Convert all **117 unique** ADRs to YAML frontmatter — **two parsers** (markdown-table + bold-inline), a **content-invariance check** (body-minus-header byte-identical), and a **bare `status`** key carrying MADR decision-status vocabulary (`Proposed`/`Accepted`/`Deprecated`/`Superseded`). A carved ADR decision-status **out** of the doc-lifecycle `doc_status` key: ADR frontmatter uses bare `status` (verified: directive `042-common-docs.directive.yaml`; ratchet `anti_sprawl_ratchet.py` `ADR_FRONTMATTER_REQUIRED_KEYS = ("title", "status", "date")`). `doc_status` is reserved for doc **pages** (FR-010). | Draft |
| FR-004 | Unify the living architectural design into a single unversioned `docs/architecture/`. | Draft |
| FR-005 | Rewrite **all** doc-path references via the occurrence map (bulk-edit, 8 categories) — **count regenerated from the live tree at plan time** (the historical ~2,190/~571 is a likely-LOW estimate, do not anchor on it). The regenerated repo-wide census is 2920 occ / 751 files, but **`kitty-specs/` (1621 occ / 453 files) is `do_not_change` — immutable historical mission snapshots** (Terminology Canon; URL continuity covered by WP07 redirect stubs), so the **rewrite target is 1299 occ / 298 files**. Rewrite the runtime-critical `src/` refs FIRST (the live census re-derived 6 runtime reads: 4 in `src/`, plus `scripts/generate_contextive_glossaries.py` and `.kittify/charter/governance.yaml`) with **resolution tests proving the new path resolves** before any tree move; then the remaining `src/` refs, then doctrine / tests / docs. (The runtime read surface is re-derived at plan time — see census.) | Draft |
| FR-006 | Apply Mission A's chosen **DocFX redirect mechanism** (e.g. generated `<meta http-equiv=refresh>` stubs per old path into `_site`) at every move; a coverage check asserts every captured-baseline URL produces a resolving stub. | Draft |
| FR-007 | Rewrite `docs/docfx.json` content globs + every `toc.yml` to the 13-section structure so the DocFX build stays green. | Draft |
| FR-008 | Resolve the shadow trees correctly: `docs/1x` + `docs/2x` (true HTML snapshots) → delete + redirect; **`docs/3x` → distil + move + redirect** (live charter content: `charter-overview.md`, `governance-files.md`, `index.md` — wired into `toc.yml`/`llms.txt`/`index.md`, fix the 3 nav refs); `docs/architecture/` → **verify-before-delete** the **4 orphan files** (`adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md`, `feature-detection.md`, `gap-analysis-connector-installation-model.md`), **of which 2 are the connector-auth ADRs** (`adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md`) — promote them or confirm a canonical home. | Draft |
| FR-009 | Apply the agreed source→target mapping (CHANGELOG→`changelog/`; Divio→`guides/`+`api/`+`architecture/`; **glossary+audiences→`context/` per A's read-path mapping**; user-journeys→`plans/`; investigations/traces→`plans/` with the distil-then-retire lifecycle). Move the glossary so the dashboard's `.kittify/glossaries/*.yaml` read-path stays intact and the doctrine-extraction source resolves (C-001 of A). | Draft |
| FR-010 | Backfill `doc_status` + per-page frontmatter, then regenerate the lockfile and pass the generate-and-compare freshness gate. Concretely: **(a)** backfill populates each page's frontmatter from the **580-row inventory** (the last authoritative snapshot); **(b)** the lockfile is then generated **FROM that frontmatter** (SSOT inversion — frontmatter becomes the source, the lockfile the derived rollup); **(c) ORDERING:** the live `--strict` drift (252 removed / 296 changed) closes to **0 only AFTER FR-001 lands all content under `docs/`** and frontmatter is backfilled. `doc_status` is the page-lifecycle key here (distinct from FR-003's bare ADR `status`). | Draft |
| FR-011 | **Flip Mission A's rulers to blocking** against the cleaned tree — the flip is **non-uniform**: the anti-sprawl ratchet and the `related:` validator flip via their wired `--strict` flag; the **lockfile freshness gate has NO flag** — `check_docs_freshness.py` **hardcodes `strict=False` and severity `"warning"` on `INVENTORY-LOCKFILE-DRIFT`**, so flipping it is a **code change** (thread `strict=True` through `_check_inventory_lockfile_drift` and **escalate `INVENTORY-LOCKFILE-DRIFT` to `error`**), not a toggle. Paired with a **full-gate dry-run before merge**. | Draft |
| FR-012 | Fold **#2054** — resolve its drift (the `docs/architecture/` boundary violation, the `docs/development/` durable-vs-ephemeral mixing, the no-single-entry-point gap); add it to the issue-matrix and `Closes #2054` on the PR. | Draft |
| FR-013 | **Amend the reconciliation ADR's Neutral note.** Mission A's Accepted reconciliation ADR records an "install as peer skills" Neutral consequence; amend that prose to record that the skills shipped as **3 doctrine tactics** (`common-docs-scaffold` / `common-docs-write` / `common-docs-find`), superseding the wording. This is a **sanctioned amendment of the reconciliation ADR's own prose** — C-002's no-content-mutation applies to ADR *decision-records being moved*, not to this self-amendment. | Draft |
| FR-014 | **Retire `LEAK-FRONTMATTER-MISMATCH`.** Retire `version_leakage_check.py`'s `LEAK-FRONTMATTER-MISMATCH` enforcement **once the lockfile gate (FR-011) is proven red live + blocking** (A explicitly deferred this retirement to B — the lockfile drift gate subsumes it). | Draft |

### Non-Functional

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | History integrity: all **117 unique** ADRs present post-move with era + frontmatter; **0 lost or content-altered** (content-invariance check passes for every ADR); the 47 byte-identical mirrors are dropped, not lost. | Draft |
| NFR-002 | URL continuity: 100% of the captured baseline public URLs resolve via a redirect stub. | Draft |
| NFR-003 | Generator parity: DocFX builds and publishes green; every published page retains `title`+`description` (length 50–180); no SEO regression (canonical/301 preserved). | Draft |
| NFR-004 | Link integrity: 0 broken internal doc links and 0 dangling `related:` edges (validator, now blocking, green). | Draft |
| NFR-005 | The runtime-critical reads (the 6 re-derived at plan time: 4 in `src/` + `scripts/generate_contextive_glossaries.py` + `.kittify/charter/governance.yaml`) have resolution tests proving the new path resolves; the full suite is green. | Draft |
| NFR-006 | The inventory lockfile regenerates deterministically; generated == committed in CI (drift closed from the live 252-removed / 296-changed baseline to 0). | Draft |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Mission A's reconciliation ADR is **merged and accepted before Mission B begins**. **Merge-blocker.** | Draft |
| C-002 | No ADR **decision-record content** mutation — only location (`adr/<era>/`) and header format (YAML frontmatter). (Does not bar FR-013's sanctioned self-amendment of the reconciliation ADR's own Neutral prose.) | Draft |
| C-003 | `src/` runtime-critical rewrites (~3, re-derived at plan time) land + tested **first**, before any tree move. | Draft |
| C-004 | `docs/3x/` is **distilled + moved + redirected, never blind-deleted** (it holds live charter content); `docs/architecture/` orphans are verified before deletion. | Draft |
| C-005 | The ratchet flip (FR-011) pairs with a **full-gate dry-run before merge** (gate-unmask cannot self-validate). | Draft |
| C-006 | The glossary move preserves the dashboard `.kittify/glossaries/` read-path and the doctrine-extraction source per A's ADR. **Merge-blocker.** | Draft |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A reader reaches any document from a single `docs/` entry point — one root, zero parallel/shadow trees. |
| SC-002 | All **117 unique** ADRs present with era + machine-readable frontmatter (bare `status`); none lost or altered; the 47 byte-identical flat mirrors dropped with the shim. |
| SC-003 | 100% of captured baseline public URLs still resolve. |
| SC-004 | 0 broken internal links / `related:` edges; DocFX builds + publishes green. |
| SC-005 | The rulers are blocking; a re-introduced second root / missing `index.md` / un-frontmattered ADR is rejected by CI (lockfile drift gate now `error`, not `warning`). |
| SC-006 | Metadata lives in exactly one place (frontmatter); the inventory is a generated lockfile (generate-and-compare green, drift = 0). |
| SC-007 | #2054's drift is resolved (current design discoverable from one place; no boundary-violating `docs/architecture/`). |

## Key Entities

- **Doc page** (frontmatter SSOT, `doc_status` lifecycle key) · **ADR** (`adr/<era>/`, immutable content, bare `status` MADR key) · **Page-inventory lockfile** (generated FROM frontmatter) · **Redirect map** (old→new, baseline-anchored) · **Occurrence map** (the 8-category rewrite plan, regenerated from the live tree at plan time).

## Assumptions

- Mission A is merged: the directive/styleguide/tactics, the three rulers (report-only), the lockfile generator, and the ADR (with the redirect mechanism, glossary read-path, era-less plan, ADR `status` namespace) all exist in `main`.
- The link-rewrite is a **bulk path-move**; `change_mode: bulk_edit` + the occurrence map are set at plan time, **regenerated from the live tree** (the historical numbers undersize).
- The move is a largely **serial spine** (occurrence-map → src/ → tree-move → {ADR-conversion ∥ refs+redirect+backfill} → ratchet-flip), not a parallel fan-out.
- **#1815 is folded** (the `bulk_edit` occurrence-map only models single-term renames, not multi-path structural restructures — B's FR-005 *is* that gap). B field-tests and documents the workaround; note it for the issue-matrix.
- **Coordinate (do NOT implement here):** **#2053** — document where the `docs/3x` charter files land post-distillation (FR-008 distillation must record the landing zone for #2053). **#648** — B's `docfx.json`/TOC rewrite (FR-007) defines the structure that site-generation must follow; coordinate the contract, do not build the site-gen.

## Out of Scope

- Anything Mission A owns (the ADR, the doctrine artifacts, authoring the rulers).
- The Hygiene slice (ships separately).
- Migrating off DocFX; rewriting ADR **decision** content; #1652 SEO optimization (sequence after this mission).
- Building the site-generation for #648 and the charter-landing implementation for #2053 (coordinate only).
