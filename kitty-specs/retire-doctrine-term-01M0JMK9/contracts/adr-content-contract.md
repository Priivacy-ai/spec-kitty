# Contract: ADR Content (IC-01)

**Governs**: the new ADR `docs/adr/3.x/2026-08-21-N-retire-doctrine-term-charter-is-the-canonical-vocabulary.md` (N = next free number at creation; latest existing is `2026-08-20-1`).
**Requirements**: FR-001..FR-005, FR-011 (decisions), NFR-002, C-002, C-003.
**Verification**: SC-001 self-sufficiency pass — a reviewer with no other context states all items below from the ADR alone.

## Mandatory content (checklist)

The ADR **must** state, each self-contained:

1. **The decision**: "doctrine" is retired from all user-facing and operator-facing language; "charter" is the canonical term. (FR-001)
2. **The three-way distinction** — precise definitions, each distinguishable without outside context (FR-002) — including disambiguation of "charter" the term from `src/charter/` the pre-existing code package (spec edge case: the term names the governance layer, not that package; user-facing strings inside it are in scope via surface S7, its identifiers are not):
   - **Charter bundle** — the per-project file set under `.kittify/charter/` (`charter.yaml` authoritative structured source per ADR `2026-07-18-1`, `charter.md` curated companion, plus graph/interview files).
   - **Active charter** — the bundle's currently-activated state (what loads at session start).
   - **Inactive charter** — a bundle/state not currently activated.
3. **Surviving kind vocabulary**: the artifact-kind terms (directive, tactic, styleguide, toolguide, procedure, paradigm, agent profile, glossary pack, mission step contract) are **not** retired — only the umbrella term "doctrine" is. (FR-003)
4. **Scope boundary** — in scope: user/operator-facing language (CLI commands + help/errors/output, docs prose, glossary, prompts/skills/agent artifacts, charter bundle, packs source strings). Out of scope: internal code identifiers (`src/doctrine/` package, module names, import paths — C-005) and legacy-marked historical artifacts (C-003). **Operator-typed identifiers** — explicit classification, split by kind (spec edge case: the inventory must not leave this to downstream missions): **skill names** (`spk-doctrine-*`) are *in scope with aliases* — resolved decision moment `specify.compatibility.alias-policy` (`decisions/DM-01M0JN29JGRA2GVEJJ89JZH3R2.md`) covers skill names as executable user-facing surfaces (3.x hidden aliases + deprecation warnings; removed by 4.0), and the operator-approved stack shape assigns M4 = skills/agent artifacts with legacy alias skills. **Profile IDs** (e.g. `doctrine-daphne`) and **directive IDs** (e.g. `018-doctrine-versioning-requirement`) are *out of scope as a named exception* (stable DRG node identifiers, analogous to `mission_id`; surrounding prose is renamed). M3/M4 scope follows this classification. (FR-004)
5. **Compatibility policy** — 3.x: old names become hidden aliases with deprecation warnings; by 4.0: zero user-visible "doctrine" (hard rule). (FR-005)
6. **Relationship to prior ADRs** (US1-AS2): explicitly supersedes the *terminology portion* of `2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md` (its resolution mechanics remain intact; its frontmatter status becomes `Superseded` with a pointer to this ADR, body untouched per C-003); reconciles with `2026-07-18-1` (bundle authority — the charter bundle is the consume-side surface this ADR's vocabulary names).
7. **FR-011 glossary decisions** (so M1 executes rather than re-decides):
   - Add a canonical **Charter Bundle** term entry to the glossary.
   - Disambiguate it from **Doctrine Pack** (offer side: versioned distributable catalogue — `packs/built-in/`, org packs) and from the other code senses of "bundle" (action-doctrine bundle, prompt bundles, tool-surface bundles).
   - Fix the "Doctrine Pack" definition's use of "bundle" as a generic word.
   - Define the replacement for the **"Doctrine Domain"** sense (the DDD bounded-context glossary entry, `Location: src/doctrine/`) — plan position: the domain sense retires with the term; the entry is rewritten to name the governance-artefact layer without a "domain" re-brand.
8. **Charter-bundle Terminology Canon line** — the exact wording M1 adds to `.kittify/charter/` (via `charter.yaml` + regeneration) instructing all sessions: use "charter", not "doctrine". M1 executes this line verbatim.
9. **Guard-arming intent** — the terminology guard will be armed to forbid "doctrine" in user-facing surfaces (scan roots `src/tests/docs`) with a file-level frozen baseline, shrink-only ratchet, and self-mutation test; the methodology artifact carries the full design. (C-004)

## Registration mechanics (C-002)

- Author from `docs/architecture/adr-template.md`.
- Register with `python -m scripts.docs.freshen_adr_inventory` (updates era index row + page-inventory lockfile in one command).
- Old ADR edit is **status frontmatter only** (`Proposed` → `Superseded` + pointer line); body byte-for-byte untouched.

## Anti-goals (what the ADR must NOT do)

- Must not rename any surface itself (C-001 — this mission is planning-only).
- Must not assign version numbers to implementation scope (the 3.x/4.0 references are the compatibility decision's content, not pins).
- Must not mark any ADR other than `2026-07-15-1` as superseded (titles of the other 9 doctrine-titled ADRs are immutable legacy snapshots).
