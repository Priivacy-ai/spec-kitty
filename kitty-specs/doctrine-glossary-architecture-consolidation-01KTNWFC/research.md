# Research / Open Decisions — Doctrine, Glossary & Architecture Consolidation

**Mission**: doctrine-glossary-architecture-consolidation-01KTNWFC
**Status**: open decisions being resolved conversationally (one at a time). Each `Decision:` line is filled as we agree; HiC-gating items must be resolved before `/spec-kitty.plan`.

---

## A. Architecture restructure (#1805) — design-gating

### R-01 — architecture/ vs docs/ boundary rule  ⛔ HiC-gating
**Context:** `architecture/` currently holds ADRs, C4 (under 2.x), `glossary/`, `audits/`, `calibration/`, `audience/`; `docs/` is Divio (tutorial/how-to/reference/explanation).
**Question:** What is the canonical split principle? Do C4 models stay in `architecture/`? Where `docs/explanation/` (the "why") overlaps architecture narrative, which wins?
**Decision (2026-06-09):** **`architecture/` = decisions & models** (ADRs, C4, audits, calibration — authoritative, deliberately changed). **`docs/` = consumption** (Divio); **`docs/explanation/` narrates + links to architecture, never duplicates** (single source of truth = architecture). **C4 stays in `architecture/`.** **Glossary is PROMOTED to a canonical top-level `glossary/` surface** (not under architecture) — and **all path + code references are updated accordingly** (charter authority paths, `src/glossary`, `.kittify/glossaries/`, `architecture/glossary/`, doctrine references). Implies hard moves + reference rewrites (see R-05).

### R-02 — versioned dirs (1.x / 2.x / 3.x)  ⛔ HiC-gating
**Question:** Is 3.x the only live tree? Archive/freeze 1.x–2.x (and target C4 refresh at 3.x only), or keep all versions first-class?
**Decision (2026-06-09):** **Living-architecture-at-top + versioned-history-beneath** model:
- **Top-level `architecture/` = the current + future architecture** (the synthesized "what is the architecture now and going forward").
- **`architecture/<version>/` = traceability record** — per-era `adr/ vision/ research/`, immutable.
- **Decay path:** when a piece of the living architecture is no longer current/future, **demote it into its version directory** (history accrues by version; nothing deleted). *(confirmed: a→yes)*
- **Current-era ADRs keep landing in `architecture/3.x/adr/`**; top-level living docs **reference** them (ADRs stay era-stamped; top-level synthesizes). *(confirmed: b→3.x with references)*
- **C4 carried forward** from 2.x to the top-level living model, then refreshed in place; 2.x keeps its snapshot as history.
- **New top-level directories** to keep it clean/discoverable: **`vision/`** (current+future vision), **`audience/`** (stakeholder views — already exists), **`diagrams/`** (living C4 + diagrams). **`architecture/README.md` updated** with the boundary rule + navigation.

### R-03 — vision/ home & semantics
**Question:** `vision/` under `docs/`? Relationship to ADRs (ratified) vs `design-spike` tickets? Need a "vision vs decision vs spike" rule.
**Decision (2026-06-09):** Vision is an **architecture concern, not a docs one** — **no `docs/vision/`**. Top-level **`architecture/vision/`** holds current+future vision; **`architecture/<version>/vision/`** holds the historical per-era vision (demoted on obsolescence). Rule: **vision = forward intent** (top-level, may change) · **ADR = ratified decision** (versioned, immutable) · **spike = exploration** (research/, versioned).

### R-04 — C4 maintenance model
**Question:** Are C4 drilldowns hand-authored prose/diagrams or generated (Structurizr/Mermaid/PlantUML)? Determines refresh scope + repeatability.
**Decision (2026-06-09):** Keep the existing convention — **hand-authored Markdown + Mermaid** (renders on GitHub, no build tooling). FR-006 refresh = carry the level-structured Markdown forward into top-level **`architecture/diagrams/`**, **keep the numbered C4 levels** (`01_context/ 02_containers/ 03_components/`), update Mermaid to the 3.x domain model; 2.x keeps its snapshot. **Generated-C4 tooling swap deferred → #1812** (`future`).

### R-05 — link/reference migration = bulk-edit?  ⛔ HiC-gating
**Context:** Moving files across architecture/↔docs/ breaks internal links and the charter's "Project authority paths" (`architecture/2.x/adr/`, `architecture/adrs/`, `glossary/contexts/`).
**Question:** Redirect stubs left behind, or hard moves + fix-all-references? Likely flips mission to `change_mode: bulk_edit`.
**Decision (2026-06-09):** **Hard moves + reference updates, no stubs** (from R-01). **Bulk-edit applied selectively, not mission-wide:** the path/reference-rewrite WPs (glossary promotion, C4/dir moves, charter authority-path + `src/glossary`/`.kittify/glossaries` + `GlossaryScope` loader + doctrine/doc cross-link rewrites) carry **`change_mode: bulk_edit` discipline via their ICs**, formulated at the **plan** step (each gets an `occurrence_map.yaml` of old→new paths). Additive WPs (new doctrine artefacts, Ops ADR, charter `extends:` code, DRG fixes) are normal mode. → **Plan-step action:** mark the rewrite WPs' ICs as bulk-edit; produce occurrence maps for them.

## B. Cross-cutting sequencing

### R-06 — restructure-first dependency
**Question:** Sequence the architecture/docs restructure (FR-005) before authoring the Ops ADR (FR-007) + doctrine artefacts (#1811) so we don't re-path mid-mission — or parallel with a frozen target layout decided up front?
**Decision (2026-06-09):** **Phased dependency:** (1) freeze target layout [done via R-01…R-04] → (2) execute moves + reference rewrites [bulk-edit WPs] → (3) author new content (Ops ADR, doctrine artefacts, glossary refresh) into the settled layout → **(4) code WPs (#1397 charter `extends:`, #1755 DRG) run in parallel from the start** (independent of doc paths). Hard dep: moves (2) before authoring (3); code lanes independent.

### R-07 — lane ownership by profile
**Question:** Should architect-alphonso own the restructure/C4/ADR lanes while implementer profiles take code lanes (#1397, #1755)? Affects lane decomposition.
**Decision (2026-06-09):** **Capture the need for profile diversity, but DO NOT pre-assign — let `finalize-tasks`/runtime routing decide.** Recommended ownership shape (guidance, not assignment): architect → arch-docs lanes (restructure, C4, Ops ADR, boundary README); implementer → code lanes (#1397, #1755); doctrine/curator → doctrine artefacts + glossary refresh. **Plan-step action:** add explicit **"revision / sign-off / deep-review" ICs** to the relevant WPs, naming the *recommended reviewer profile*:
- Architect sign-off on the restructure, C4, Ops ADR, and any doctrine that encodes architecture conventions (styleguide/toolguide).
- Reviewer profile (e.g. reviewer-renata) for standard WP review.
- Doctrine/charter sign-off on the doctrine artefacts + charter `extends:`.
These are *review ICs*, not assignment locks.

## C. Quick confirmations (defaults proposed)

### R-08 — glossary runtime-scope (FR-011)
**Decision (2026-06-09):** **Defer** runtime-scope promotion (reassess under #1418) — BUT **glossary content updates & improvements happen NOW** (FR-010 stands: refresh/expand content this mission; only the `GlossaryScope` registration is deferred).

### R-09 — DRG (#1755)
**Decision (2026-06-09):** Close gaps in the **existing generator** (regeneration command + symmetric profile-edge detection) — NOT a rebuild. **PLUS (expanded scope): sanitize and re-curate the built-in DRG and agent profiles** — fold in the new doctrine additions (the artefacts this mission authors), re-curate stale/duplicate edges and profiles, so the DRG reflects the consolidated doctrine.

### R-10 — charter `extends:` (#1397)
**Decision (2026-06-09):** **Additive merge**, base-org precedence + cycle detection, integrated with the existing `charter.activation_engine`/cascade. **No parallel mechanism.**

---

## D. Guiding principle (cross-cutting) — capture as C-005

**Consolidate; eliminate parallel mechanisms.** The mission's through-line is to do away with the "parallel mechanisms" accreted over past releases — they cause the split-brain failures seen across recent releases (cf. the GitHub issue-tracker sanitization that preceded this mission). New work **replaces/reconciles** existing surfaces rather than forking a second one. Applies to: glossary (one canonical surface, R-01), charter extends (R-10), DRG/profiles (R-09 re-curation), architecture docs (single source of truth, R-01/R-02).

## E. #391 as doctrine usage-test (operator aside)

**Observation:** #391 ("Tech/Functional Debt Remediation") is a *dumping ground*, not a coherent functional epic — its children should be split/reparented and #391 closed as **superseded/deprecated**.
**Decision (2026-06-09):** Do this **in-mission, as a usage test of the new doctrine artefacts** (dogfood the procedure/tactic/styleguide on a real messy epic) rather than pre-mission. Validates SC-1 against a live case. → New **FR-012** + success criterion.

---

_Resolution log: R-01…R-10 resolved + C-005 principle + #391 usage-test (FR-012) — 2026-06-09. Intake complete; ready for /spec-kitty.plan._
