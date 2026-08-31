# Research: Common Docs Structural Move (Mission B)

**Phase 0 output** · Mission `common-docs-structural-move-01KW3SBK` · Branch
`docs/2165-mission-b-structural-move` · 2026-06-27

Mission A's reconciliation ADR (`architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md`,
**Accepted**) decided every *design* mechanism. Mission B has **no remaining design questions**. This
research therefore records the **execution-method decisions** — the "how do we apply A's mechanism
safely" choices — and their rationale, each grounded in the live foundation present on this branch.

---

## D-R1 — The #1815 structural-restructure occurrence-map approach

**Decision.** Drive every move through a **regenerated-from-live `occurrence_map.yaml`** built as a
set of **path-pair mappings** (old-path → new-path), classified into the 8 bulk-edit categories,
**paired with a verification gate** (every old path resolves to exactly one new path; every new path
is reachable; no occurrence is left unclassified). The map is regenerated from the live tree at plan
time — **not** anchored on the historical "~2,190 occurrences / ~571 files".

**Rationale.** The `change_mode: bulk_edit` occurrence map was built for **single-term renames** (one
identifier → one identifier across N files). A structural restructure is **N path-pairs**, each a
distinct old→new mapping with its own redirect and reference-rewrite consequences — that is exactly
**#1815**'s documented gap, and FR-005 *is* that gap made concrete. The path-pair representation is
the minimal extension that lets the existing 8-category classifier and bulk-edit gate operate over a
move: each path-pair is an occurrence cluster, classified once, applied everywhere it appears.

**Evidence / undersizing risk.** Live sweeps bracket **452 ↔ 7,614 occurrences and trend up**; the
historical ~571-file figure is a **likely-LOW estimate (active undersizing risk)**. A live `grep`
this session found **21 `src/` `.py` files** referencing `architecture/`/doc-roots (11 touching
`architecture/<era>/adr`) — the doctrine/`kitty-specs/`/tests/docs reference count is regenerated
into the map, never assumed. **A missed `src/` occurrence is a runtime break, not a dead link** — so
the verification gate fails closed on any unclassified `src/` path.

**Note for the issue-matrix.** B **field-tests and documents** this workaround as the #1815 fold:
the occurrence-map schema models single-term renames; the path-pair-mapping + verification-gate
pattern is the structural-restructure extension. (The `occurrence_map.yaml` file itself is authored
by a parallel task — this mission documents the contract it must satisfy.)

**Rejected.** Ad-hoc `sed` across the tree (no classification, no verification, no redirect linkage);
anchoring on the historical count (undersizes by up to ~13×).

---

## D-R2 — ADR two-parser conversion + content-invariance method

**Decision.** Convert all **117 unique** ADRs with **two parsers** — a **markdown-table** parser
(for the ~12 table-header ADRs) and a **bold-inline** parser (for the ~34 `**Status:** …` header
ADRs) — emitting **bare-`status` YAML frontmatter** with the MADR vocabulary
(`Proposed`/`Accepted`/`Deprecated`/`Superseded`) plus `title` + `date`
(`ADR_FRONTMATTER_REQUIRED_KEYS = ("title", "status", "date")`). Prove no decision content mutated
with a **content-invariance check**: extract the ADR **body minus its old header block**, and assert
it is **byte-identical** before and after conversion.

**Rationale.** Directive `042-common-docs.directive.yaml` carves the **ADR `status` exception** out
of the page `doc_status` namespace (verified: "Architecture Decision Records are the one sanctioned
exception — ADR frontmatter uses `status` for the MADR decision status"). The ratchet already encodes
the required keys. Two parsers are required because the live ADRs use two distinct header dialects
(table vs bold-inline) and **0 of 117 use YAML frontmatter** today (invisible to DocFX). The
body-minus-header byte-identity check is the only invariance proof that survives a header-format
change (a re-render comparison would false-green on whitespace/normalisation).

**Apparent tension, resolved.** A's ADR D2 *prohibits* a bare `status` frontmatter key (collision with
the WP-lane status model). The spec (squad-hardened, ground truth) and directive 042 **both** record
the **ADR exception**: pages use `doc_status`; ADRs use bare `status` for the MADR decision status.
B honors the spec — bare `status` for ADRs, `doc_status` for pages.

**Era handling.** 97 era ADRs keep their era; the **20 era-less** flat ADRs migrate to **`adr/3.x/`**
by **dated filename** (D6, deterministic sort); the **47 byte-identical flat mirrors are dropped**
losslessly as the flat `architecture/adrs/` shim closes — *after* the era-less migration, so no ADR
is orphaned mid-move (D6).

**Rejected.** A single universal parser (cannot handle both dialects); a re-render diff for invariance
(false-greens on normalisation); dropping the era axis (D3 rejected flat `adr/` — erases
era-of-decision reasoning across 117 ADRs).

---

## D-R3 — Redirect-stub generation (A's meta-refresh mechanism) + baseline-URL capture

**Decision.** Implement A's **D4 mechanism**: a **post-build step in `scripts/docs/`** (new
`redirect_stub_generator.py`) reads a **checked-in redirect map** (old-path → new-path) and emits a
**`<meta http-equiv="refresh">` stub page at each old path** into the DocFX `_site` output. Capture a
**baseline-URL inventory** (the pre-move published URL set) as the **denominator**, and add a
**coverage check** asserting every baseline URL resolves directly or via a stub (NFR-002 = 100%).

**Rationale.** DocFX on GitHub Pages has **no native redirect/alias mechanism** (A's D4 Context); a
client-side `<meta refresh>` stub is the only redirect primitive on a static site. Generating it
**per old path from a reviewed map** makes the URL-preservation guarantee **testable**, and capturing
the baseline *before* the move makes the denominator **explicit** — without it, "100% resolve" is
unfalsifiable.

**Method.** (1) Capture baseline URLs from the current published site / `docfx.json` build **before**
any move. (2) As IC-05 rewrites references, append each old→new path-pair to the redirect map. (3) The
generator emits one stub per old path post-build. (4) The coverage check intersects the baseline set
with {direct-resolving ∪ stub-covered} and **fails CI on any uncovered baseline URL**.

**Rejected.** No redirect / accept URL churn (~1,589 link occurrences + live SEO regress — D4
rejected it); server-side redirects / DocFX native aliases (unavailable on static GitHub Pages).

---

## D-R4 — Frontmatter-backfill source-of-truth: 580-row inventory → per-page frontmatter → generated lockfile

**Decision.** Backfill each page's `doc_status` + per-page frontmatter **from the 580-row inventory**
(`docs/development/3-2-page-inventory.yaml` — the last authoritative snapshot), then **invert the
SSOT**: in-file frontmatter becomes the source, and the inventory is **regenerated FROM frontmatter**
as a **generated lockfile** via `scripts/docs/inventory_lockfile.py` (`run_generate_and_compare`).
The freshness gate then asserts **generated == committed** (drift = 0).

**Rationale.** A's **D1** chose Candidate A: in-file frontmatter is the per-page SSOT; the inventory
becomes a generated/asserted lockfile (generator-native — the live site already reads frontmatter,
not the sidecar). The 580-row inventory is the only authoritative metadata snapshot, so it **seeds**
the frontmatter; once seeded, frontmatter is authoritative and the lockfile is derived. D1's
**load-bearing caveat** is preserved: the rollup semantics (completeness, workstream ownership,
deterministic alphabetical diff) survive **as the generated lockfile artifact**, not deleted.

**The drift is the workload, not a clean floor.** The legacy `check_docs_freshness.py` is green
(exit 0), but `inventory_lockfile.py --strict` reports **252 removed / 296 changed / 0 added** against
the committed inventory. **That gap IS FR-010's backfill workload.** Critically, the **ordering**:
the drift closes to **0 only AFTER FR-001 (IC-03) lands all content under `docs/`** *and* frontmatter
is backfilled — regenerating the lockfile before the move reports false drift (paths not yet moved).

**Rejected.** Candidate B (sidecar stays SSOT, frontmatter generated from it — a permanent deviation
from the standard the operator fully adopted; the published site still wouldn't read the SSOT);
regenerating the lockfile before the move (false drift).

---

## D-R5 — The lockfile-gate-flip code change (FR-011)

**Decision.** Flip the lockfile freshness gate to **blocking** via a **code change**, not a flag.
In `scripts/docs/check_docs_freshness.py`: thread `strict=True` through
`_check_inventory_lockfile_drift` (it currently calls
`run_generate_and_compare(..., strict=False)` hardcoded), and **escalate
`INVENTORY-LOCKFILE-DRIFT` from `severity="warning"` to `severity="error"`** in `_lockfile_finding`
(currently hardcoded `"warning"`). The aggregate exit code already keys off
`any(f.severity == "error")`, so the escalation is what makes drift fail CI.

**Rationale.** The flip is **non-uniform**. The anti-sprawl ratchet
(`anti_sprawl_ratchet.py`) and the `related:` validator (`related_validator.py`) both have a
**wired-but-off `--strict`** flag (`if args.strict and report[...]: return 1`) — flipping them is a
CI-wiring toggle. But the lockfile gate **has no flag**: `_check_inventory_lockfile_drift` hardcodes
`strict=False` and every finding is emitted at `"warning"`, so the gate is structurally report-only
(it can never raise the aggregate exit). Making it blocking is therefore a **code change** to two
functions, not a toggle (verified live in the source this session).

**Gate-unmask discipline.** The flip is paired with a **full-gate dry-run on the whole tree before
merge** (C-005). A ruler that only bites on the mission diff is invisible until post-merge — memory
("gate-unmask cannot self-validate"): an un-masking only takes effect post-merge, so it can't catch
offenders in its own merge unless dry-run against the full tree first. **Order matters:** the gate
flips **after** the drift is closed to 0 (IC-03 + IC-05), or it red-fails the mission's own merge.

**LEAK retirement coupling (FR-014).** `version_leakage_check.py`'s `LEAK-FRONTMATTER-MISMATCH` is
retired **only once the lockfile gate is proven red live + blocking** — the lockfile drift gate
**subsumes** it (under D1 the leaked datum lives in one place, so the cross-check is structurally
unnecessary). A deferred this retirement to B explicitly.

**Rejected.** Adding a `--strict` flag to the lockfile gate (more surface than threading the existing
`strict` param; the gate is invoked from CI, not a human, so a code-level default is cleaner);
retiring LEAK before the lockfile gate is proven blocking (drops enforcement with no replacement).

---

## Foundation inventory (Mission A, present on this branch — consumed, not rebuilt)

| Artifact | Path | B's use |
|----------|------|---------|
| Reconciliation ADR (Accepted) | `architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md` | Design source of truth; amended (FR-013) + moved to `docs/adr/3.x/` (IC-03) |
| Directive | `src/doctrine/directives/built-in/042-common-docs.directive.yaml` | The 13-section + ADR-`status`-exception + lockfile rules B enforces |
| Styleguide | `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml` | Authoring conventions |
| Tactics (4) | `src/doctrine/tactics/built-in/common-docs-{scaffold,write,find,curation}.tactic.yaml` | Dogfooded; the 3 named in FR-013 |
| Anti-sprawl ratchet (ruler 3, report-only) | `scripts/docs/anti_sprawl_ratchet.py` | Flip via `--strict` (FR-011); `ADR_FRONTMATTER_REQUIRED_KEYS=("title","status","date")` |
| `related:` validator (report-only) | `scripts/docs/related_validator.py` | Flip via `--strict` (FR-011) |
| Lockfile drift gate (report-only) | `scripts/docs/check_docs_freshness.py` | Flip via **code change** (FR-011, D-R5) |
| Lockfile generator | `scripts/docs/inventory_lockfile.py` | `run_generate_and_compare(...)` → generate-and-compare (FR-010) |
| LEAK check | `scripts/docs/version_leakage_check.py` | `LEAK-FRONTMATTER-MISMATCH` retired (FR-014) |
| Runtime ADR read-path | `src/charter/context_renderers/authority_paths.py` | Rewritten first w/ resolution test (IC-02); already 3.x-default |
| Glossary read-path | `src/glossary/scope.py` (`load_seed_file`) + `src/specify_cli/dashboard/handlers/glossary.py` | Preserved (C-006, merge-blocker) |

**Open at task time (deliberately deferred to IC-01/IC-02 execution, not design):** the exact
runtime-critical `src/` read set (re-derived by a live resolve-grep over the 11 `architecture/<era>/adr`
files); the final occurrence count (regenerated into `occurrence_map.yaml` by the parallel task).

## Post-planning brownfield checks (2026-06-27)

Run after `/plan`, before `/tasks` (standing cadence). All four pass — the pre-planning + plan-review squads + the remediation already absorbed the substantive findings.

- **Split-brain:** PASS. Mission B's *purpose* is resolving the existing docs split-brain (`docs/{1x,2x,3x}` + `docs/architecture/` shadow-duplicating `architecture/*.x`); the occurrence map's `moves:` enumerate every shadow tree + the 4 orphans (FR-008). No NEW split-brain — the root `CHANGELOG.md` alias (`relocate-with-alias`) and the staying page-inventory are intentional, controlled dual-homes (tooling artifacts), not divergent copies.
- **Deprecation:** PASS. Three sequenced retirements, each gated on its prerequisite: `LEAK-FRONTMATTER-MISMATCH` retired (FR-014 / IC-07, only after the lockfile gate is proven blocking); the flat `architecture/adrs/` shim closed (IC-04, after the 20 era-less migrate to `adr/3.x/`); the 47 byte-identical flat mirrors dropped (IC-04, as duplicates).
- **Foldable issues:** PASS. No new candidates beyond the pre-planning scope — #1815 folded (closes on B's merge), #2053/#648 coordinate-only. Other open issues (#2173 / #614 infra-separation epics) are out of B's documentation domain.
- **LOC / god-module:** PASS. The net-new deliverables (`redirect_stub_generator.py`, the ADR converter with the 3-format parser, the frontmatter-backfill tooling) are scoped as separate IC-04/IC-05 work packages, not a monolith.
