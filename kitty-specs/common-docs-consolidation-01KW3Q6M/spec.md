# Common Docs Doctrine & Reconciliation (Mission A)

**Mission**: `common-docs-consolidation-01KW3Q6M` · **Type**: software-dev · **Parent**: epic #651 · **Addresses**: #2165 (foundation)

> **This is Mission A of a 3-ship split** (post-spec squad, 2026-06-27). Mission A establishes the *governed foundation*: the reconciliation ADR (the binding decisions), the built-in Common Docs doctrine (directive + styleguide + tactics), and the *enforcement tooling* ("the rulers") in **report-only** mode. **Mission B** (the structural move — single-root, `adr/<era>/`, the link rewrites, the redirect application, flipping the ratchet to blocking) follows and **dogfoods** this foundation across a merge boundary. The **Hygiene slice** ships separately/now. The split is required, not cosmetic: C-002 (ADR accepted before the move), C-004 (gate + full-gate dry-run), and the gate-unmask-cannot-self-validate rule are only honestly satisfiable across merge boundaries.

## Overview

The Common Docs consolidation needs its *rules and its rulers to exist in merged doctrine before the structural move consumes them.* Mission A delivers exactly that and nothing that mutates the doc tree:

1. a **reconciliation ADR** that decides every open mechanism the move depends on (so Mission B has no undecided design),
2. the **built-in Common Docs doctrine** (a binding directive, a styleguide, tactics) wired into the DRG, so the conventions ship to every consumer project, and
3. the three **enforcement rulers** — the `related:` path validator, the frontmatter→inventory lockfile generator, and the anti-sprawl ratchet — authored with self-tests and run **report-only** against today's (messy) tree so we *measure* the violation baseline without blocking.

Research ground truth: `docs/engineering_notes/651-docs-consolidation/`. Corrected facts from the post-spec squad: `architecture/` = 218 files; **~117 unique ADRs** (191 files; **20 era-less in flat `architecture/adrs/`** is the exact figure); **0** use YAML frontmatter; the page-inventory `docs/development/3-2-page-inventory.yaml` = **568 rows** with `citation_refs` 6/568 (dead — to be dropped); inventory↔tree drift is **zero**; the live site is **DocFX on GitHub Pages** (`docs/docfx.json` → `docs.spec-kitty.ai`) with **no native redirect** primitive.

## User Scenarios & Testing

### A future doc lands under governed conventions
A contributor or agent adds a doc/ADR and follows the built-in Common Docs **styleguide** (via its **directive** and **tactics**); the conventions are governed doctrine shipped to every consumer project, not tribal knowledge — and the rulers from this mission are what Mission B will switch on to enforce them.

### The rulers prove themselves before they police anything
Each ruler (validator, lockfile generator, ratchet) ships with a **self-test**: a known-bad fixture asserts the gate goes RED and a known-good passes. Run report-only, the ratchet emits the *current* violation count (the baseline Mission B must drive to zero) without failing CI.

### The reconciliation ADR closes every open mechanism
Before Mission B starts, the ADR has decided: frontmatter-as-SSOT (Candidate A), the namespaced status key, the DocFX redirect mechanism, the glossary read-path mapping, the era-less-ADR migration plan, the 13-section target, and the curation policy — so the move is execution, not design.

## Requirements

### Functional

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Land a single **reconciliation ADR** (accepted) that decides, with rationale: (a) **frontmatter-as-SSOT / Candidate A** (the page-inventory becomes a generated lockfile; `citation_refs` is dropped); (b) the **namespaced status key** (e.g. `doc_status`) to avoid the WP-lane `status` collision; (c) the **DocFX redirect mechanism** (DocFX/GitHub Pages has no native redirect → a concrete approach, e.g. generated `<meta http-equiv=refresh>` stub pages per old path emitted into `_site`); (d) the **glossary read-path mapping** (which artifact moves to `context/`, that the dashboard's `.kittify/glossaries/*.yaml` seed read-path stays intact or is regenerated, and the glossary-as-doctrine extraction source post-move); (e) the **era-less-ADR migration plan** (the 20 flat-only ADRs → `adr/3.x/` by date); (f) the **13-section target structure** with `adr/<era>/`; (g) the **delete-stale curation policy** and the **distil-then-retire** lifecycle for investigations. | Draft |
| FR-002 | Add a built-in Common Docs **directive** that binds documentation to the structure + frontmatter-SSOT + curation policy. It must be **referenced by the anti-sprawl ratchet** (FR-007) — i.e. bound, not advisory (a self-test asserts the reference exists). | Draft |
| FR-003 | Add a built-in Common Docs **styleguide** codifying the conventions (13-section structure, frontmatter schema incl. the namespaced status key + the SEO description-length 50–180 constraint, naming, `adr/<era>/`, the `related:` resolvable-path form, the curation policy). **Every codified rule maps to a live check** (frontmatter→FR-006 generator; `related:`→FR-005 validator; structure→FR-007 ratchet) — a rule with no check is a defect. | Draft |
| FR-004 | Add built-in Common Docs **tactic(s)** for applying the conventions (placing a doc, authoring an ADR with era + frontmatter incl. the `PROPOSED`/`superseded` status mapping, running the rulers). Wire the artifacts into the DRG via `spec-kitty doctrine regenerate-graph` and gate freshness with `--check`. | Draft |
| FR-005 | Build the **`related:` path validator** (resolvable repo-relative paths; dangling edge = fail) as a standalone tool. **Self-test:** a deliberately-dangling fixture asserts FAIL + a good fixture passes; the validator **reports the reference count it checked** (assert > 0). Run report-only over the live tree to produce a baseline. | Draft |
| FR-006 | Build the **frontmatter→inventory lockfile generator** + invert `check_docs_freshness` to *generate-and-compare* (committed lockfile == fresh generation, else CI fails). Drop `citation_refs`; preserve the inventory's rollup invariants (completeness, ownership, deterministic diff) as generated output. **Self-test (the linchpin):** mutate one frontmatter field → regenerate → assert the lockfile **changes** and the gate goes RED; and a hand-edit of the lockfile alone (frontmatter untouched) is **rejected**. Retire `LEAK-FRONTMATTER-MISMATCH` only once the new gate is proven red live. | Draft |
| FR-007 | Build the **anti-sprawl ratchet** in **report-only** mode (it emits violations, does not fail CI — Mission B flips it to blocking). It checks: a second doc root, any `docs/*/` missing `index.md`, an ADR missing the frontmatter schema, a re-introduced `docs/<version>x` shadow tree. **Self-test:** four injection fixtures (one per condition) each assert detection; the ratchet carries a **concrete content-anchored floor** (the enumerated 13 sections / "exactly one root"), and its violation message **references the FR-002 directive id** (proving the binding). | Draft |
| FR-008 | Resolve the **Common Docs Agent Skills** question: either ship `common-docs-scaffold`/`-write`/`-find` into the `.agents/skills/` layer (manifest `.kittify/command-skills-manifest.json` + renderer) **or** explicitly declare them out of scope and remove the dangling `common-docs-write` reference from the consolidation docs. (No requirement may reference a skill that isn't installed.) | Draft |

### Non-Functional

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | Every ruler ships a self-test that is **red on the seeded violation and green on the good fixture** (FR-005/006/007). A ruler without a passing red-fixture test is incomplete. | Draft |
| NFR-002 | The DRG freshness gate (`regenerate-graph --check`) is **green** with the new directive/styleguide/tactic nodes + their declared relations present. | Draft |
| NFR-003 | The report-only rulers run over the live tree in under the project's fast-tier budget and emit a **baseline violation count** (the number Mission B must drive to zero) as durable output. | Draft |
| NFR-004 | The lockfile generator is **deterministic** (two runs on the same tree produce byte-identical output). | Draft |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | The reconciliation ADR (FR-001) is **accepted and merged before Mission B begins** — the dependency is a merge boundary, not intra-mission ordering. **Merge-blocker.** | Draft |
| C-002 | The rulers ship **report-only** in this mission; flipping any of them to blocking is **out of scope** (Mission B does it against the cleaned tree, paired with a full-gate dry-run). | Draft |
| C-003 | The directive (FR-002) must be **bound** to the ratchet (FR-007) by reference; an orphan directive doc fails acceptance. | Draft |
| C-004 | The status frontmatter key is **namespaced** (not bare `status`) to avoid the WP-lane collision. | Draft |
| C-005 | The doctrine artifacts use the **canonical doctrine artifact format** and update the generated `graph.yaml` via the named command (`spec-kitty doctrine regenerate-graph`), freshness-gated. Account for the known `documentation_policy` directive-plumbing bug (#2153). | Draft |
| C-006 | Mission A **does not mutate the doc tree** (no file moves, no ADR conversion, no link rewrites) — it only adds doctrine + tooling + the ADR. The move is Mission B. | Draft |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | The reconciliation ADR is accepted and decides all seven items in FR-001 — Mission B opens with zero undecided design. |
| SC-002 | The Common Docs conventions exist as built-in doctrine: the directive is **referenced by the ratchet** (bound), every styleguide rule maps to a live check, and the tactics are DRG-wired and freshness-valid. |
| SC-003 | Each ruler's self-test demonstrably goes **RED** on its seeded violation (validator dangling edge; lockfile frontmatter-tamper; ratchet's four conditions) and green on the good fixture. |
| SC-004 | The report-only rulers produce a recorded **baseline violation count** for the live tree (the deltas Mission B must close). |
| SC-005 | No doc-tree file is moved, deleted, or content-changed by this mission (C-006). |
| SC-006 | The lockfile generator is **deterministic** (NFR-004): two runs on the same tree produce byte-identical output. |

## Key Entities

- **Reconciliation ADR** — the binding decision record gating Mission B (FR-001).
- **Common Docs doctrine set** — directive + styleguide + tactic(s), DRG-wired.
- **The rulers** — `related:` validator, frontmatter→inventory lockfile generator, anti-sprawl ratchet (report-only), each with a self-test.

## Assumptions

- Numbers are the squad-verified live values (140 ADRs incl. 20 era-less; 568 inventory rows; ~571 referencing files / ~2,190 occurrences). Mission B sizes against these.
- The 20 era-less ADRs in flat `architecture/adrs/` are real ADRs with no era home; their migration is **decided** here (FR-001e) and **executed** in Mission B.
- Coordinate (do not fold): #1652 (SEO audit — sequence after Mission B), #1755 (DRG regen footgun — required reading for FR-004), #2153 (doc-policy directive bug — affects FR-002 plumbing).

## Out of Scope (→ Mission B / Hygiene)

- **Mission B (the structural move):** single-root consolidation, `adr/<era>/` move + 140-ADR YAML conversion + the 20 era-less migration, living-design unification, the ~2,190 reference rewrites (src/ first — only ~3 are genuinely runtime-critical: `charter/context_renderers/authority_paths.py`, `compat/__init__.py`, `cli/commands/doctor.py`), the redirect-stub application, the `docfx.json` + `toc.yml` rewrite, `docs/3x` distil+move+redirect (NOT blind-delete — it holds live charter content), `docs/architecture/` verify-before-delete, the glossary move, frontmatter backfill, and **flipping the ratchet to blocking**. Folds **#2054**.
- **Hygiene slice (ships now, standalone):** the ~15 missing `index.md`, the `CLAUDE.md:531` + `AGENTS.md:531` twin dead links, `CONTRIBUTING.md:7,:119`, the 7-ADR README backfill, retire `NAVIGATION_GUIDE.md` + `ARCHITECTURE_DOCS_GUIDE.md`, the `llms.txt` rubric, the enumerated docs-body dead links. (The `architecture/adrs/` shim is **not** hygiene — it homes the 20 era-less ADRs; its closure is Mission B.)
