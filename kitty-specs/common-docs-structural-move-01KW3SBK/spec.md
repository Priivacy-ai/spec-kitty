# Common Docs Structural Move (Mission B)

**Mission**: `common-docs-structural-move-01KW3SBK` · **Type**: software-dev · **Parent**: epic #651 · **Closes**: #2165, #2054

> **Mission B of the Common Docs split** (post-spec squad, 2026-06-27). Mission B performs the actual consolidation **against the governed, self-testing foundation merged by Mission A** (`common-docs-consolidation-01KW3Q6M`). It is **gated on Mission A's reconciliation ADR being accepted and merged** (the dependency is a merge boundary, not intra-mission ordering). Mission B dogfoods A's directive/styleguide/tactics and **flips A's report-only rulers to blocking** against the cleaned tree.

## Overview

Mission A decided every mechanism and shipped the rulers report-only. Mission B executes the move with no remaining design questions: collapse the four roots (`architecture/`, `docs/`, `development/`, `engineering_notes/`) into one 13-section Common Docs `docs/` root, migrate all **140 ADRs** into `adr/<era>/` with YAML frontmatter, rewrite the **~2,190 doc-path references across ~571 files** (src/ first), apply the DocFX redirect mechanism A chose, rewrite the DocFX content manifest + TOCs, resolve the shadow trees correctly, backfill frontmatter, and switch the rulers to blocking.

**Squad-verified facts (the floor):** 140 unique ADRs (120 under `<era>/adr/` + **20 era-less in flat `architecture/adrs/`**); 0/140 use YAML frontmatter; ~571 files / ~2,190 occurrences reference doc paths, of which **only ~3 src/ reads are genuinely runtime-critical** (`charter/context_renderers/authority_paths.py`, `compat/__init__.py`, `cli/commands/doctor.py`); 568-row inventory, drift-free; DocFX on GitHub Pages (no native redirect); `docs/3x/` carries **live charter content** (not a pure shadow).

## User Scenarios & Testing

### The maintainer finds the current design from one root
After the move, a reader starts at `docs/index.md` and reaches the current design in `docs/architecture/` with no era detour and no parallel tree — resolving #2054's "current design not discoverable."

### Every old URL still resolves
A previously-published page was moved; its prior public URL resolves via a generated redirect stub (the mechanism A chose), validated against a captured baseline URL inventory.

### A re-introduced violation is now rejected
With A's rulers flipped to blocking, a second doc root / missing `index.md` / un-frontmattered ADR / re-introduced shadow tree fails CI.

### No ADR is lost — including the 20 era-less ones
All 140 ADRs (including the 20 that lived only in flat `architecture/adrs/`) are present post-move under `adr/<era>/` with YAML frontmatter and unchanged decision content.

## Requirements

### Functional

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Consolidate `architecture/` + `docs/` + `development/` + `engineering_notes/` into a single 13-section Common Docs `docs/` root per Mission A's ADR structure. | Draft |
| FR-002 | Move the 120 era ADRs into `docs/adr/<era>/` **and migrate the 20 era-less ADRs** (flat `architecture/adrs/`) into `docs/adr/3.x/` (assigned by date, per A's plan), then close the flat shim. All **140** preserved. | Draft |
| FR-003 | Convert all 140 ADRs to YAML frontmatter — **two parsers** (markdown-table + bold-inline), a **content-invariance check** (body-minus-header byte-identical), and the `PROPOSED`/`superseded` status mapping using A's namespaced status key. | Draft |
| FR-004 | Unify the living architectural design into a single unversioned `docs/architecture/`. | Draft |
| FR-005 | Rewrite the ~2,190 doc-path references across ~571 files via the occurrence map (bulk-edit, 8 categories). **`src/` first** — the ~3 runtime-critical reads land with **resolution tests proving the new path resolves**, before any tree move; then doctrine / `kitty-specs/` / tests / docs. | Draft |
| FR-006 | Apply Mission A's chosen **DocFX redirect mechanism** (e.g. generated `<meta http-equiv=refresh>` stubs per old path into `_site`) at every move; a coverage check asserts every captured-baseline URL produces a resolving stub. | Draft |
| FR-007 | Rewrite `docs/docfx.json` content globs + every `toc.yml` to the 13-section structure so the DocFX build stays green. | Draft |
| FR-008 | Resolve the shadow trees correctly: `docs/1x` + `docs/2x` (true HTML snapshots) → delete + redirect; **`docs/3x` → distil + move + redirect** (live charter content: `charter-overview.md`, `governance-files.md`, `index.md` — wired into `toc.yml`/`llms.txt`/`index.md`, fix the 3 nav refs); `docs/architecture/` → **verify-before-delete** the 4 orphan files (promote the 2 un-promoted connector-auth ADRs or confirm a canonical home). | Draft |
| FR-009 | Apply the agreed source→target mapping (CHANGELOG→`changelog/`; Divio→`guides/`+`api/`+`architecture/`; **glossary+audiences→`context/` per A's read-path mapping**; user-journeys→`plans/`; investigations/traces→`plans/` with the distil-then-retire lifecycle). Move the glossary so the dashboard's `.kittify/glossaries/*.yaml` read-path stays intact and the doctrine-extraction source resolves (C-001 of A). | Draft |
| FR-010 | Backfill frontmatter into each page from the 568-row inventory, regenerate the lockfile (Mission A's generator), and pass the generate-and-compare freshness gate. | Draft |
| FR-011 | **Flip Mission A's rulers to blocking** against the cleaned tree — the anti-sprawl ratchet, the `related:` validator, and the lockfile freshness gate — paired with a **full-gate dry-run before merge**. | Draft |
| FR-012 | Fold **#2054** — resolve its drift (the `docs/architecture/` boundary violation, the `docs/development/` durable-vs-ephemeral mixing, the no-single-entry-point gap); add it to the issue-matrix and `Closes #2054` on the PR. | Draft |

### Non-Functional

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | History integrity: all **140** ADRs present post-move with era + frontmatter; **0 lost or content-altered** (content-invariance check passes for every ADR). | Draft |
| NFR-002 | URL continuity: 100% of the captured baseline public URLs resolve via a redirect stub. | Draft |
| NFR-003 | Generator parity: DocFX builds and publishes green; every published page retains `title`+`description` (length 50–180); no SEO regression (canonical/301 preserved). | Draft |
| NFR-004 | Link integrity: 0 broken internal doc links and 0 dangling `related:` edges (validator, now blocking, green). | Draft |
| NFR-005 | The ~3 runtime-critical `src/` rewrites have resolution tests proving the new path resolves; the full suite is green. | Draft |
| NFR-006 | The inventory lockfile regenerates deterministically; generated == committed in CI. | Draft |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Mission A's reconciliation ADR is **merged and accepted before Mission B begins**. **Merge-blocker.** | Draft |
| C-002 | No ADR **content** mutation — only location (`adr/<era>/`) and header format (YAML frontmatter). | Draft |
| C-003 | `src/` runtime-critical rewrites (~3) land + tested **first**, before any tree move. | Draft |
| C-004 | `docs/3x/` is **distilled + moved + redirected, never blind-deleted** (it holds live charter content); `docs/architecture/` orphans are verified before deletion. | Draft |
| C-005 | The ratchet flip (FR-011) pairs with a **full-gate dry-run before merge** (gate-unmask cannot self-validate). | Draft |
| C-006 | The glossary move preserves the dashboard `.kittify/glossaries/` read-path and the doctrine-extraction source per A's ADR. **Merge-blocker.** | Draft |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A reader reaches any document from a single `docs/` entry point — one root, zero parallel/shadow trees. |
| SC-002 | All 140 ADRs present with era + machine-readable frontmatter; none lost or altered. |
| SC-003 | 100% of captured baseline public URLs still resolve. |
| SC-004 | 0 broken internal links / `related:` edges; DocFX builds + publishes green. |
| SC-005 | The rulers are blocking; a re-introduced second root / missing `index.md` / un-frontmattered ADR is rejected by CI. |
| SC-006 | Metadata lives in exactly one place (frontmatter); the inventory is a generated lockfile (generate-and-compare green). |
| SC-007 | #2054's drift is resolved (current design discoverable from one place; no boundary-violating `docs/architecture/`). |

## Key Entities

- **Doc page** (frontmatter SSOT) · **ADR** (`adr/<era>/`, immutable content) · **Page-inventory lockfile** (generated) · **Redirect map** (old→new, baseline-anchored) · **Occurrence map** (the 8-category rewrite plan).

## Assumptions

- Mission A is merged: the directive/styleguide/tactics, the three rulers (report-only), the lockfile generator, and the ADR (with the redirect mechanism, glossary read-path, era-less plan, status namespace) all exist in `main`.
- The link-rewrite is a **bulk path-move**; `change_mode: bulk_edit` + the occurrence map are set at plan time.
- The move is a largely **serial spine** (occurrence-map → src/ → tree-move → {ADR-conversion ∥ refs+redirect+backfill} → ratchet-flip), not a parallel fan-out.

## Out of Scope

- Anything Mission A owns (the ADR, the doctrine artifacts, authoring the rulers).
- The Hygiene slice (ships separately).
- Migrating off DocFX; rewriting ADR content; #1652 SEO optimization (sequence after this mission).
