# Implementation Plan: Common Docs Structural Move (Mission B)

**Branch**: `docs/2165-mission-b-structural-move` | **Date**: 2026-06-27 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/kitty-specs/common-docs-structural-move-01KW3SBK/spec.md`

**Note**: Mission B is the **execution mission** of the Common Docs split. Mission A
(`common-docs-consolidation-01KW3Q6M`) decided every mechanism in its reconciliation ADR
(`architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md`, **Accepted**) and shipped the
foundation — the directive (`042-common-docs.directive.yaml`), the styleguide, the four tactics,
the three **report-only** rulers (`scripts/docs/anti_sprawl_ratchet.py`,
`scripts/docs/related_validator.py`, the lockfile drift gate in
`scripts/docs/check_docs_freshness.py`), and the lockfile generator
(`scripts/docs/inventory_lockfile.py`). Mission B executes the move against that governed
foundation with **zero remaining design questions**, and **flips the rulers to blocking**.

## Summary

Fold the repository's **two top-level documentation roots** — `architecture/` and `docs/` — into a
single 13-section Common Docs `docs/` root, re-sectioning the existing `docs/development/` and
`docs/engineering_notes/` subdirectories into that structure. Convert the **117 unique ADRs** into
`docs/adr/<era>/` with YAML frontmatter (bare `status` MADR key), drop the 47 byte-identical flat
mirrors, migrate the 20 era-less ADRs to `adr/3.x/`. Rewrite all live doc-path references via a
freshly-regenerated occurrence map (`src/` runtime-critical reads **first**, with resolution tests,
**before any tree move**), emit DocFX `<meta refresh>` redirect stubs per move against a captured
baseline-URL inventory, rewrite `docfx.json` globs + every `toc.yml`, distil-then-move-and-redirect
the `docs/3x` live-charter shadow tree, backfill per-page `doc_status` frontmatter from the 580-row
inventory and regenerate the lockfile, then **flip the three rulers to blocking** (two via `--strict`,
the lockfile gate via a code change) paired with a full-gate dry-run before merge. The technical
shape is a **serial spine**, not a parallel fan-out: occurrence-map → `src/` reads (+ the 2 non-`src/`
land-first reads) → **redirect-baseline-URL capture (PRE-move — you cannot snapshot old URLs after
the move)** → tree-move → {ADR-conversion ∥ refs+redirect+backfill} → ruler-flip → ADR-note
amendment + LEAK retirement.

## Technical Context

**Language/Version**: Python 3.11+ (rulers and generators live in `scripts/docs/`; runtime reads in
`src/`). No new language surface.
**Primary Dependencies**: **Existing deps only** — `ruamel.yaml` (frontmatter/inventory parsing,
already vendored for the inventory lockfile), the stdlib (`argparse`, `pathlib`, `urllib`), DocFX
(unchanged, invoked by `.github/workflows/docs-pages.yml`). **No new dependency is introduced.**
**Storage**: Files only — Markdown docs, ADR `.md`, `docs/development/3-2-page-inventory.yaml`
(generated lockfile), `.kittify/glossaries/<scope>.yaml` (seed read-path, preserved), a new
checked-in **redirect map** (old-path → new-path) and a **captured baseline-URL inventory**.
**Testing**: `pytest`. Resolution tests for the runtime-critical `src/` path rewrites (prove the new
path resolves before the tree moves); content-invariance tests for the ADR conversion; redirect
coverage tests against the baseline denominator; a generate-and-compare freshness test for the
lockfile; ruler-blocking regression tests (re-introduced violation must be rejected). Run the
CI-only architectural/integration shards locally before PR (`tests/architectural/`).
**Target Platform**: Linux dev + GitHub Actions CI; published site is DocFX on GitHub Pages
(`https://docs.spec-kitty.ai/`).
**Project Type**: Single repository, documentation-and-tooling restructure (a **bulk_edit**
structural move — `change_mode: bulk_edit`, set in `meta.json`).
**Performance Goals**: N/A (one-time migration). The only runtime-perf-adjacent constraint is that
the lockfile **regenerates deterministically** (generated == committed) so the CI freshness gate is
stable.
**Constraints**: `change_mode: bulk_edit` — every move is classified in `occurrence_map.yaml`
(8 categories) and reviewed by the bulk-edit gate. **No ADR decision-record content mutation**
(C-002): only location and header format change; a content-invariance check (body-minus-header
byte-identical) proves it for all 117 ADRs. The glossary `.kittify/glossaries/<scope>.yaml` seed
read-path and the doctrine-extraction source are **merge-blockers** (C-006). The reconciliation ADR
being Accepted+merged is a **merge-boundary precondition** (C-001).
**Scale/Scope (live-derived at plan time, not anchored on stale numbers)**: **two doc roots**
collapsing into one; **192 ADR files → 117 unique** converted (97 era + 20 era-less migrated to
`adr/3.x/`; 47 byte-identical flat mirrors dropped; 68 files in flat `architecture/adrs/`);
**~21 `src/` `.py` files** reference `architecture/`/doc-roots today (live `grep`), of which
**11 touch `architecture/<era>/adr`** and **~3 are runtime-critical** (re-derived below) — these
land first; the doctrine/`kitty-specs/`/tests/docs reference count is **regenerated from the live
tree into `occurrence_map.yaml`** (the historical "~2,190/~571" is a **likely-LOW estimate — active
undersizing risk**, live sweeps bracket 452↔7,614 and trend up); **580-row** page inventory; live
lockfile `--strict` drift **252 removed / 296 changed / 0 added** against the committed inventory —
that gap **is FR-010's backfill workload**, closing to 0 only after the tree move + backfill.

**Runtime read surface (re-derived live, C-003 / NFR-005):** `authority_paths.py` lives at
**`src/charter/context_renderers/authority_paths.py`** and already reflects the #2160/#2115
ADR-default flip (`architecture/3.x/adr/` default, back-compat for `architecture/2.x/adr/`). The
**4 runtime-critical reads** (the occurrence-map regen refined the spec's "~3" — it MISSED the
glossary read) are the `src/` paths that *resolve a real file at runtime* (not documentation
prose): (1) `authority_paths.py` → `architecture/3.x/adr/` (the ADR-default read, already flipped
via #2160/#2115); (2) `authority_paths.py` → **`glossary/contexts/`** — becomes critical when the
glossary moves to `docs/context/` (FR-009 / C-006, a merge-blocker); (3) `compat/doctor.py:69` →
`architecture/2.x/shim-registry.yaml`; (4) `compat/registry.py:51` → the same shim-registry read
(paired with the remediation string at `cli/commands/doctor.py:509`) — shim-registry's declared
destination is **`docs/migrations/shim-registry.yaml`** (see IC-02). The other ~17 `src/` ADR-path
hits are module-docstring prose (`user_facing_strings`), not runtime reads.

**Plus 2 NON-`src/` land-first reads** (out-of-relocate-scope surfaces that nonetheless *resolve* a
moving path at runtime, so they land first with the same dual-read/resolution-test discipline): (5)
**`scripts/generate_contextive_glossaries.py`** (`GLOSSARY_CONTEXTS_DIR = … / "glossary" / "contexts"`,
~line 30 — the C-006 doctrine-extraction source); (6) **`.kittify/charter/governance.yaml`**
`authority_paths` block (`glossary/contexts/`, `architecture/3.x/adr/`, `architecture/adrs/`). These
files are NOT moved — only their target literals are re-pointed in place. **All 6** land-first reads
get a resolution test proving the **new** path resolves **before** the tree move (C-003).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Canonical-sources discipline (CLAUDE.md):** PASS — this plan consumes Mission A's governed
  doctrine (directive 042, the four tactics, the three rulers, the reconciliation ADR) and the
  doctrine `plan.md` scaffold; it does not improvise structure or copy an older mission.
- **Terminology canon:** PASS — Mission nomenclature; no `feature*` aliases introduced; no `ceremony`.
  Note: the move touches doctrine/prose, so `pytest tests/architectural/test_no_legacy_terminology.py`
  is a pre-push gate (CI-only).
- **No-direct-push / PR workflow:** PASS — Mission B lands via PR (`Closes #2165/#2054/#2192`,
  `Folds #1815`); the orchestrator commits, this planning step does not.
- **Bulk-edit gate (DIRECTIVE / `change_mode: bulk_edit`):** PASS — `occurrence_map.yaml` is the
  classification authority (IC-01). **This planning task does NOT author `occurrence_map.yaml`** — a
  parallel task owns it; IC-01 documents the contract it must satisfy.
- **Gate-unmask discipline (memory — "gate-unmask cannot self-validate"):** TRACKED — the ruler flip
  (IC-06) is paired with a **full-gate dry-run before merge** (C-005); a mission-diff-scoped
  assertion is never shipped to main as the only proof.

No Charter Check violations require Complexity Tracking entries.

## Project Structure

### Documentation (this mission)

```
kitty-specs/common-docs-structural-move-01KW3SBK/
├── plan.md              # This file
├── research.md          # Phase 0 — mechanism decisions + rationale
├── data-model.md        # Phase 1 — entities + invariants
├── quickstart.md        # Phase 1 — validation scenarios
├── contracts/           # Phase 1 — ruler/redirect/invariance interface contracts
│   ├── rulers-blocking.md
│   ├── redirect-stub.md
│   └── content-invariance.md
└── tasks.md             # Phase 2 — /spec-kitty.tasks output (NOT created here)
```

### Source Code (repository root — the surfaces this mission moves/edits)

```
docs/                              # the single surviving documentation root (13 sections)
├── index.md                       # single entry point (SC-001)
├── context/                       # glossary human narrative + audiences (FR-009)
├── architecture/                  # unified, unversioned living design (FR-004)
├── adr/<era>/                     # 1.x | 2.x | 3.x — 117 unique ADRs, frontmattered (FR-002/003)
├── plans/                         # user-journeys + investigations/traces (distil-then-retire)
├── api/  configuration/  integrations/  security/  guides/  operations/  migrations/  changelog/
├── docfx.json                     # content globs rewritten to 13 sections (FR-007)
└── **/toc.yml                     # every TOC rewritten (FR-007)

architecture/                      # FOLDED INTO docs/ then removed (FR-001); flat adrs/ shim closes (FR-002)
.kittify/glossaries/<scope>.yaml   # seed read-path PRESERVED/regenerated (C-006, merge-blocker)

scripts/docs/                      # the rulers + generators (Mission A foundation; B flips + extends)
├── anti_sprawl_ratchet.py         # ruler 3 — flip via --strict (FR-011)
├── related_validator.py           # related: validator — flip via --strict (FR-011)
├── check_docs_freshness.py        # lockfile drift gate — CODE CHANGE to flip (FR-011)
├── inventory_lockfile.py          # generate-and-compare lockfile (FR-010, consumed not rewritten)
├── version_leakage_check.py       # LEAK-FRONTMATTER-MISMATCH — retired (FR-014)
└── redirect_stub_generator.py     # NEW — emits <meta refresh> stubs from the redirect map (FR-006)

src/charter/context_renderers/authority_paths.py   # runtime-critical ADR read-path (IC-02, FIRST)
src/glossary/scope.py                              # load_seed_file — glossary read-path (C-006)
src/specify_cli/dashboard/handlers/glossary.py     # GlossaryHandler — glossary read consumer (C-006)
tests/                              # resolution / invariance / redirect-coverage / ruler-blocking tests
```

**Structure Decision**: Single-repository bulk-edit structural move. The deliverable surface is the
existing `docs/` tree (re-sectioned to the 13 Common Docs sections), the `scripts/docs/` rulers
(flipped to blocking + one new redirect generator), and a small set of `src/` runtime read-paths
(rewritten first, with resolution tests). No new top-level packages; `architecture/` is removed once
its content lands under `docs/`.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation Concern Map — the SERIAL SPINE

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs. The spec is explicit that this mission
> is a **largely serial spine**, not a parallel fan-out: the ordering between ICs is load-bearing
> (a tree move before the runtime reads are rewritten is a runtime break). The only sanctioned
> parallelism is **inside the move window**: IC-04 (ADR conversion) ∥ IC-05 (refs+redirect+backfill)
> may interleave once IC-03 lands, because they touch disjoint surfaces.

> **IC-split sizing for `/tasks`** (these ICs are NOT 1:1 WPs — several fan out):
> - **IC-02 → 1–2 WPs** (the 6 land-first reads + resolution tests; optionally split src/ vs non-src/).
> - **IC-02b → 1 WP** (pre-move baseline-URL capture + committed manifest).
> - **IC-03 → 2 WPs** (the tree move proper; the `docs/development` per-file durable-vs-ephemeral split).
> - **IC-04 → 1–2 WPs** (3-parser conversion of 117; content-invariance test).
> - **IC-05 → 4–5 WPs**: redirect-gen + docs-pages.yml wiring / bulk ref-rewrite / `docfx.json`+TOC /
>   shadow-tree resolution / **`doc_status`+`description`+`related` backfill-authoring** (the authoring
>   sub-slice is itself a candidate WP, possibly two — it is real per-page work, not a footnote).
> - **IC-06 → 1–2 WPs** (the 3 code/CI changes + ruler-blocking regression tests + the C-005 dry-run).

### IC-01 — Occurrence-map regeneration + the bulk-edit plan

- **Purpose**: Regenerate the bulk-edit classification from the **live** tree — path-pair mappings
  (old-path → new-path), all moves sorted into the 8 occurrence categories — so every later rewrite
  is driven by a reviewed map, not ad-hoc `sed`. Field-tests and documents **#1815**'s gap: the
  `bulk_edit` occurrence map models single-term renames, **not multi-path structural restructures**;
  FR-005 *is* that gap, so IC-01 captures the path-pair-mapping workaround + a verification gate.
- **Relevant requirements**: FR-005, FR-009; Assumptions (#1815 fold), `change_mode: bulk_edit`.
- **Affected surfaces**: `occurrence_map.yaml` (**owned by a parallel task — IC-01 documents the
  contract, does not author the file**); the live `docs/` + `architecture/` + `src/` + doctrine +
  `kitty-specs/` + tests reference set.
- **Sequencing/depends-on**: none (spine head). Everything downstream consumes its map.
- **Risks**: **Blast-radius undersizing** — the historical ~571-file estimate is likely LOW; live
  sweeps bracket 452↔7,614 and **trend up**. Regenerate from the live tree; do not anchor on the
  historical number. A missed `src/` occurrence is a runtime break, not a dead link.

### IC-02 — runtime-critical reads FIRST (before any tree move)

- **Purpose**: Re-point the **6 land-first reads** (4 in `src/` + 2 non-`src/`) to the new doc paths
  **with resolution tests proving the new path resolves**, **before** any file moves (C-003,
  NFR-005), then rewrite the remaining **~39 (non-runtime) `src/` refs**. A read that dereferences a
  not-yet-moved path, or a not-yet-rewritten read after the move, is a runtime break.
- **DUAL-READ / back-compat staging (explicit)**: each land-first read is staged as **read
  old ∪ new** → test both resolve → move the tree (IC-03) → drop the old branch. This is the same
  pattern `authority_paths.py` already uses for `architecture/2.x/adr/` (3.x default + 2.x back-compat).
  The shim-registry readers (`compat/doctor.py:69`, `compat/registry.py:51`) need it explicitly:
  read `architecture/2.x/shim-registry.yaml` **∪** the new home, test, then move, then drop old.
- **Shim-registry DESTINATION DECLARED**: `architecture/2.x/shim-registry.yaml` →
  **`docs/migrations/shim-registry.yaml`** (stable section of the 13; pairs with
  `06_migration_and_shim_rules.md`). Re-point all 3 readers + the remediation string
  (`cli/commands/doctor.py:509`) in lock-step, dual-read.
- **Relevant requirements**: FR-005, NFR-005; C-003.
- **Affected surfaces**: `src/charter/context_renderers/authority_paths.py` (ADR + `glossary/contexts/`
  literals); `src/specify_cli/compat/doctor.py` + `compat/registry.py` + `cli/commands/doctor.py:509`
  (shim-registry → `docs/migrations/`); the 2 **non-`src/` land-first reads** —
  `scripts/generate_contextive_glossaries.py` (`glossary/contexts/` → `docs/context/`) and
  `.kittify/charter/governance.yaml` `authority_paths` (in-place targeted edits, NOT moves); the
  other ~39 `src/` reference sites; `tests/` resolution tests.
- **Sequencing/depends-on**: IC-01 (consumes the occurrence map). **Must complete before IC-03.**
- **Risks**: Mis-identifying the runtime-critical set (re-derive live, don't trust the stale
  "~3 reads" snapshot — it MISSED the glossary script + governance config); back-compat symlink
  interactions at `architecture/2.x/adr/`; dropping the old dual-read branch *before* IC-03 lands.

### IC-02b — Redirect baseline-URL capture (PRE-move — gates IC-03)

- **Purpose**: Capture the published-URL set of the **pre-move** site so the redirect-coverage check
  (NFR-002) has a falsifiable denominator. **This MUST run before the tree moves** — once the move
  lands you can no longer observe the old URLs. (It was previously mis-placed inside IC-05, which runs
  *after* IC-03; that ordering makes 100% coverage unfalsifiable.)
- **Steps**: (1) install DocFX (.NET — CI-only today, so install it in this step); (2) build the
  **pre-move** `docs/` + `architecture/` tree (`docfx docfx.json`); (3) snapshot the emitted `_site`
  URL set into a checked-in **baseline-URL manifest**; (4) **commit** that baseline manifest **before
  IC-03**. IC-05's coverage check asserts every baseline URL resolves directly or via a stub.
- **Relevant requirements**: FR-006, NFR-002.
- **Affected surfaces**: a new checked-in baseline-URL manifest; DocFX build (read-only over the
  pre-move tree).
- **Sequencing/depends-on**: after IC-02 (so runtime reads are safe), **before IC-03** (the move).
  Its committed manifest is consumed by IC-05's redirect-coverage check.
- **Risks**: Skipping the pre-move build → the baseline is reconstructed from the post-move tree →
  coverage is measured against the wrong denominator and silently reports 100% (unfalsifiable).

### IC-03 — The tree move (two-root collapse)

- **Purpose**: Fold `architecture/` into `docs/` and **re-section the existing `docs/development/` +
  `docs/engineering_notes/`** into the 13-section structure (FR-001 — a two-root collapse, not four).
  Move the glossary human narrative into `docs/context/` **while preserving the
  `.kittify/glossaries/<scope>.yaml` seed read-path and the doctrine-extraction source** (C-006,
  merge-blocker). Apply the agreed source→target mapping (FR-009: CHANGELOG→`changelog/`;
  Divio→`guides/`+`api/`+`architecture/`; glossary+audiences→`context/`; user-journeys→`plans/`;
  investigations/traces→`plans/` distil-then-retire).
- **Relevant requirements**: FR-001, FR-004, FR-009; C-006.
- **`docs/development` → `docs/operations` is a PER-FILE durable-vs-ephemeral classification, not one
  mechanical pair (FR-012 / #2054)**: each page is classified — **durable** dev/ops references →
  `docs/operations/` (or `guides/`/`configuration/` per A's ADR); **ephemeral** tracking/sprint docs →
  `docs/plans/` (distil-then-retire). `/tasks` must enumerate the classification, not move the dir
  wholesale. **EXCEPTION (operator directive): the page-inventory `docs/development/3-2-page-inventory.yaml`
  STAYS PUT** — it is a tooling artifact; the 4 lockfile constants
  (`inventory_lockfile.py`/`check_docs_freshness.py`/`version_leakage_check.py`/`_inventory.py`) are
  UNCHANGED. The re-section moves the doc PAGES, not the inventory file (resolves the freshness-gate
  self-block).
- **Affected surfaces**: `architecture/` (removed), `docs/development/` (per-file split; inventory
  file excluded), `docs/engineering_notes/`, `glossary/contexts/*.md` → `docs/context/`,
  `.kittify/glossaries/` (seed read-path preserved), `CHANGELOG.md` (**relocate-with-alias** — root
  copy persists for release tooling), Divio dirs (`docs/explanation`, `docs/how-to`, `docs/reference`,
  `docs/tutorials`), the 2.x design artifacts + shim-registry (→ `docs/architecture` / `docs/migrations`).
- **Sequencing/depends-on**: IC-02 (runtime reads rewritten + tested first) **and IC-02b** (baseline
  captured). Gates IC-04, IC-05.
- **Risks**: Breaking the glossary seed read-path (merge-blocker — verify the dashboard
  `GlossaryHandler` + `load_seed_file()` still resolve); mis-classifying durable vs ephemeral in
  `docs/development/` (the #2054 drift — FR-012); accidentally moving the inventory file (would
  re-open the freshness-gate self-block).

### IC-04 — ADR conversion (117 unique → `adr/<era>/`, frontmattered)

- **Purpose**: Convert all **117 unique** ADRs to YAML frontmatter with **THREE parsers** and a
  **bare `status`** MADR key (`Proposed`/`Accepted`/`Deprecated`/`Superseded` — carved out of the
  page `doc_status` namespace, per directive 042). Move the 97 era ADRs into `docs/adr/<era>/`,
  migrate the **20 era-less** flat ADRs into `docs/adr/3.x/` (by dated filename, **deterministically
  pinned in the occurrence map's `era_less_pinned` block, D6**), **drop the 47 byte-identical flat
  mirrors** as the flat shim closes. A **content-invariance check** (body-minus-header byte-identical)
  proves no decision content mutated (C-002, NFR-001).
- **PARSER CENSUS CORRECTED (live)**: the header formats are **70 bold-inline / 46 table /
  1 dash-bullet** = **117** (the spec's "~12 table / ~34 bold" was wrong and missed the dash-bullet
  format entirely). **A 3rd parser branch is REQUIRED** for the dash-bullet format
  (`- Status: …` / `- Date: …`, e.g.
  `architecture/2.x/adr/2026-04-15-2-explicit-empty-charter-selections-remain-empty.md`) — without it
  that ADR converts **status-less**, the ratchet (`title`/`status`/`date` required) blocks, and the
  conversion is stuck. **Size IC-04 for 117 ADRs across 3 parsers, not 46.**
- **Relevant requirements**: FR-002, FR-003; C-002, NFR-001.
- **Affected surfaces**: `architecture/<era>/adr/`, flat `architecture/adrs/` (68 files: 47 mirrors
  dropped, 20 era-less migrated, 1 README), `docs/adr/<era>/`; a conversion script + invariance test.
- **Sequencing/depends-on**: IC-03 (the move lands the era trees under `docs/`). **May run in
  parallel with IC-05** (disjoint surfaces) — the **`era_less_pinned` destination filenames decouple
  the two**: IC-05's ADR-reference rewrites + ADR redirect-stubs consume the pinned final paths
  without waiting for IC-04 to finish converting (resolves the IC-04→IC-05 ADR coupling).
- **Risks**: A parser missing a header variant → a malformed-frontmatter ADR (the **dash-bullet
  branch** is the one the spec missed); a content-invariance false-green (the check must compare
  body-minus-header bytes, not re-render). The era-less→3.x date assignment is now **deterministic
  via `era_less_pinned`** (was a risk; pinned).

### IC-05 — References + redirects + frontmatter backfill

- **Purpose**: Rewrite **all** remaining doc-path references (doctrine / `kitty-specs/` / tests /
  docs) via the occurrence map (FR-005); emit a **`<meta refresh>` redirect stub per move** from the
  checked-in redirect map, with a **coverage check** asserting every captured-baseline URL (from
  IC-02b's committed manifest) resolves (FR-006, NFR-002); **wire the stub generator into
  `.github/workflows/docs-pages.yml`** — call `redirect_stub_generator.py` **between the
  "Build documentation" (`docfx docfx.json`) step and the "Upload artifact" step** so stubs land in
  `_site` before publish; rewrite `docfx.json` content globs + **every** `toc.yml` to the 13 sections
  (FR-007); **resolve the shadow trees** — `docs/1x`+`docs/2x` (true HTML snapshots) delete+redirect,
  **`docs/3x` distil+move+redirect** (live charter content — never blind-delete, C-004), verify the
  4 `docs/architecture/` orphans before deletion (2 are connector-auth ADRs — promote or confirm a
  home) (FR-008); **backfill per-page `doc_status`/`description`/`related` frontmatter** (see the
  authoring sub-slice below), then **regenerate the lockfile** so the live `--strict` drift (252
  removed / 296 changed) closes to **0 — but only AFTER IC-03 lands all content under `docs/`**
  (FR-010 ordering).
- **FR-010 BACKFILL IS DERIVATION + AUTHORING, not a mechanical drift-close** (the inventory has **0**
  `doc_status`, **0** `description`, **0** `related` — there is nothing to "sync"; it must be
  authored). Its own WP(s):
  - **(a) `tag → doc_status` mapping** — derive each page's `doc_status` from its live `tag`
    (internal 419 / current 133 / archival 14 / migration 14) into the
    `{draft|active|deprecated|superseded}` MADR-adjacent vocabulary. Define the mapping table
    explicitly (e.g. `current→active`, `internal→active|draft` by signal, `archival→deprecated`,
    `migration→active`); it is a one-time derivation, not a guess-per-page.
  - **(b) `description` authoring (~580 pages, 50–180 chars, NFR-003)** — human/assisted authoring of
    a one-line description per page. **A length gate does NOT exist today** (`scripts/docs/` only has
    `seo_postprocess.py`, which *emits* but does not *validate* length) — **add the 50–180 length
    gate** as part of this slice.
  - **(c) `related` edges** — source the cross-page `related:` edges (NFR-004 = 0 dangling, enforced
    by R2). Where derivable from existing in-body links, derive; otherwise author.
  This is a **real authoring workload measured in pages, not a footnote** — sized as its own WP(s) and
  carried in the Risks table.
- **Relevant requirements**: FR-005, FR-006, FR-007, FR-008, FR-010; NFR-002, NFR-003, NFR-004,
  NFR-006; C-004.
- **Affected surfaces**: doctrine/`kitty-specs/`/tests/docs reference sites; `docs/docfx.json`,
  `**/toc.yml`, `llms.txt`, `docs/index.md`; `docs/{1x,2x,3x}`, `docs/architecture/` orphans;
  `docs/development/3-2-page-inventory.yaml` (regenerated lockfile — the file **stays at this path**);
  the redirect map + IC-02b's baseline URL manifest; `scripts/docs/redirect_stub_generator.py` (new);
  `.github/workflows/docs-pages.yml` (stub-injection step); a **new 50–180 `description` length gate**
  in `scripts/docs/`.
- **Sequencing/depends-on**: IC-03 (move) **and IC-02b** (committed baseline manifest, the
  coverage denominator). FR-010 drift→0 is gated on IC-03 **and** the backfill-authoring sub-slice.
  **May run in parallel with IC-04** — the **`era_less_pinned`** filenames let the ADR-reference
  rewrites + ADR redirect-stubs proceed against final paths without waiting on IC-04.
- **Risks**: **Redirect coverage vs baseline-URL denominator** — a move with no stub is a dead URL
  (NFR-002); capture the baseline *before* the move. `docs/3x` blind-delete would lose live charter
  content (C-004). FR-010 drift closes to 0 **only after** the move + backfill — wrong ordering
  reports false drift.

### IC-06 — Flip the rulers to blocking

- **Purpose**: Ratchet + `related:` validator flip via their **wired `--strict`** flag; the
  **lockfile drift gate flips via a CODE change** — `check_docs_freshness._check_inventory_lockfile_drift`
  currently hardcodes `strict=False` and `_lockfile_finding` hardcodes `severity="warning"`; thread
  `strict=True` through and **escalate `INVENTORY-LOCKFILE-DRIFT` to `error`** (FR-011). Pair with a
  **full-gate dry-run before merge** (C-005 — a ruler that only bites post-merge cannot catch its own
  offenders).
- **THE LOCKFILE FLIP NEEDS A THIRD CODE CHANGE**: `check_docs_freshness.run_orchestrator` runs the
  lockfile-drift check **only behind the `if inventory_lockfile_check:` opt-in guard (line ~433)**, and
  **CI (`.github/workflows/docs-freshness.yml:24`) invokes the script WITHOUT `--inventory-lockfile`**.
  So the severity escalation is **dead code in CI** unless the check is made **default-on** (remove the
  opt-in guard, or pass `--inventory-lockfile` in CI). Without this, R3 silently never fires.
- **CI WIRING (no CI job invokes the ratchet or `related:` validator today — confirmed)**: add the
  invocations to **`.github/workflows/docs-freshness.yml`** — a step running
  `anti_sprawl_ratchet.py --strict` and `related_validator.py --strict`, alongside the
  `check_docs_freshness.py` step (which gains `--inventory-lockfile` / default-on). Name the target
  workflow + step in `/tasks`.
- **Relevant requirements**: FR-011; C-005, NFR-006, SC-005.
- **Affected surfaces**: CI wiring (**`.github/workflows/docs-freshness.yml`** — `--strict` on the two
  scripts + lockfile default-on), `scripts/docs/check_docs_freshness.py`
  (`_check_inventory_lockfile_drift` + `_lockfile_finding` + the `run_orchestrator` opt-in guard),
  ruler-blocking regression tests.
- **Sequencing/depends-on**: IC-03, IC-04, IC-05 — the tree must be clean and the lockfile drift
  closed to 0 **before** the gates flip, or the flip red-fails the mission's own merge.
- **Risks**: **Gate-unmask cannot self-validate** (memory) — a mission-diff-scoped assertion shipped
  to main is invisible until post-merge; the C-005 full-gate dry-run on the whole tree is mandatory.
  Flipping before drift = 0 self-blocks the merge.

### IC-07 — ADR-note amendment + LEAK retirement

- **Purpose**: **Amend** the reconciliation ADR's "install as peer skills" Neutral note → record that
  the skills shipped as **3 doctrine tactics** (`common-docs-scaffold` / `common-docs-write` /
  `common-docs-find`) (FR-013 — a sanctioned self-amendment of the ADR's own prose, NOT barred by
  C-002 which protects *moved* decision-records). **Retire `LEAK-FRONTMATTER-MISMATCH`**
  (`version_leakage_check.py`) **once the lockfile gate (IC-06) is proven red live + blocking**
  (FR-014 — the lockfile drift gate subsumes it; A deferred this retirement to B).
- **Relevant requirements**: FR-013, FR-014.
- **Affected surfaces**: `architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md` (Neutral
  note — note: this file itself moves under IC-03 to `docs/adr/3.x/`), `scripts/docs/version_leakage_check.py`.
- **Sequencing/depends-on**: IC-06 (LEAK retirement is gated on the lockfile gate being proven
  blocking). Spine tail.
- **Risks**: Retiring LEAK before the lockfile gate is proven blocking would drop frontmatter-drift
  enforcement with no replacement. The ADR self-amendment must not trip the content-invariance check
  (it is a sanctioned exception — scope the invariance check to *moved* ADRs, not this one).

## Risks (mission-level, must be carried into tasks)

| Risk | Source | Mitigation |
|------|--------|-----------|
| **Move-ordering dependency** — FR-010 drift→0 is gated on IC-03 (move) **and** IC-05 (backfill); flipping IC-06 before drift=0 self-blocks the merge | FR-010, FR-011 | Strict spine ordering; close drift before the gate flips; C-005 full-gate dry-run |
| **#1815 occurrence-map structural-restructure gap** — the map models single-term renames, not multi-path moves | Assumptions, FR-005 | IC-01 path-pair-mapping workaround + verification gate; document for the issue-matrix |
| **Redirect coverage vs baseline-URL denominator** — a move with no stub = dead URL | FR-006, NFR-002 | **IC-02b** captures + commits the baseline URL set *before* the move; coverage check fails CI if any baseline URL lacks a resolving stub |
| **FR-010 backfill is an AUTHORING workload, not a drift-close** — inventory has 0 `doc_status`/`description`/`related`; ~580 descriptions (50–180 chars) must be authored, `tag→doc_status` derived, `related` edges sourced, and a length gate built (none exists) | FR-010, NFR-003, NFR-004 | Scope as its own WP(s) under IC-05; define the `tag→doc_status` table; add the 50–180 length gate; derive `related` from in-body links where possible |
| **Parser census undersized** — live = 70 bold / 46 table / **1 dash-bullet** = 117; spec said "~12 table/~34 bold" and missed the dash-bullet format → that ADR converts status-less, ratchet blocks | FR-003, IC-04 | **3rd parser branch** for `- Status:`/`- Date:`; size IC-04 for 117 across 3 parsers |
| **R3 lockfile flip is dead in CI** — `run_orchestrator` gates the check behind `if inventory_lockfile_check:` and CI invokes the script without `--inventory-lockfile` | FR-011, IC-06 | THIRD code change: make the lockfile check default-on (remove the guard) or pass the flag in `docs-freshness.yml` |
| **Content-invariance on 117 ADR conversions** — a parser bug or false-green invariance check mutates/loses decision content | FR-003, C-002, NFR-001 | Two parsers + body-minus-header byte-identity check per ADR; the 47 mirrors are *byte-identical* (drop is lossless) |
| **Gate-unmask discipline on the flip** — a diff-scoped assertion is invisible until post-merge | FR-011, C-005 | Full-gate dry-run on the whole tree before merge (memory: gate-unmask cannot self-validate) |
| **Blast-radius undersizing** — historical ~571 files is likely LOW; live sweeps trend up (452↔7,614) | FR-005, NFR | Regenerate the occurrence map from the live tree; never anchor on the historical number |
| **Glossary seed read-path break** (merge-blocker) | C-006 | Move only the human markdown; preserve/regenerate `.kittify/glossaries/<scope>.yaml`; verify `GlossaryHandler` + `load_seed_file()` |
| **`docs/3x` blind-delete** (merge-blocker) — holds live charter content | C-004, FR-008 | Distil + move + redirect; fix the 3 nav refs (`toc.yml`/`llms.txt`/`index.md`); record landing zone for #2053 |
| **Merge-boundary precondition** — Mission A's reconciliation ADR must be Accepted+merged first | C-001 | Confirmed: ADR is **Accepted** on this branch; verify it is on the integration branch before any move |

## Coordinate (do NOT implement here)

- **#2053** — record where the `docs/3x` charter files land post-distillation (IC-05/FR-008 must
  document the landing zone; do not build the charter-landing implementation).
- **#648** — IC-05's `docfx.json`/TOC rewrite (FR-007) **defines the structure** site-generation must
  follow; coordinate the contract, do not build the site-gen.
