# Contract: ADR Content (IC-01)

**Governs**: the new ADR `docs/adr/3.x/<creation-date>-N-retire-doctrine-term-charter-is-the-canonical-vocabulary.md` (`creation-date` = actual WP01 execution date; N = next free number for that date, discovered immediately before creation).
**Requirements**: FR-001..FR-005, FR-011 (decisions), NFR-002, C-002, C-003.
**Verification**: SC-001 self-sufficiency pass — a reviewer with no other context states all items below from the ADR alone.

## Mandatory content (checklist)

The ADR **must** state, each self-contained:

1. **The decision and effectiveness boundary**: "doctrine" is retired — meaning deprecated and no longer the chosen future vocabulary — from user/operator-facing language; "charter" is the canonical replacement. ADR acceptance records the decision but does not pretend product authorities changed in the planning PR. Before M1/I1, existing glossary/runtime authority remains operational and coherent. M1/I1 atomically makes the new glossary/charter authorities effective. Existing inventoried primary-use debt may remain only until its M1–M5 owner wave; registered 3.x compatibility surfaces may remain/relocate under C-004 until M6. No unregistered new primary use is allowed after ADR acceptance. (FR-001)
2. **The three-way distinction** — precise definitions, each distinguishable without outside context (FR-002) — including disambiguation of "charter" the term from `src/charter/` the pre-existing code package (spec edge case: the term names the governance layer, not that package; user-facing strings and supported public APIs inside it are in scope via S7, while only non-public identifiers are X1):
   - **Charter bundle** — the per-project file set under `.kittify/charter/` (`charter.yaml` authoritative structured source per ADR `2026-07-18-1`, `charter.md` curated companion, plus graph/interview files).
   - **Active charter** — a governance artefact activated/wired in for the project.
   - **Inactive charter** — a governance artefact available in a Charter Pack but not activated for the project.
3. **Surviving kind vocabulary**: directive, tactic, styleguide, toolguide, procedure, paradigm, agent profile, glossary pack, and mission step contract remain canonical labels in their existing roles. The ADR must not claim all kinds are activatable. (FR-003)
4. **Scope boundary** — in scope: every user/operator-facing occurrence/path, including CLI; human prose; glossary/prompt/skill/profile/directive/charter/pack/config/workflow/generated surfaces; serialized/API values; supported public Python names/imports; exact `doctrine.api.__all__`; and installable distribution/project/wheel metadata. Public means `__all__`, package re-export, public API/operator docs/skills, supported external contract, or package metadata consumed by installers/builds. Out of scope: non-public internal identifiers and the internal `src/doctrine/` implementation tree/module paths (C-005), immutable history, and intentional non-user-facing quoted test/data. Supported access migrates to a canonical charter facade even when implementation stays in `src/doctrine/`; old public imports warn in 3.x and leave supported exports/docs in M6. Distribution-name compatibility follows publication evidence under the M2 map contract. (FR-004)

   | 3.x ID(s) | Canonical ID |
   |-----------|--------------|
   | `spk-doctrine-charter`, `spec-kitty-charter-doctrine` | `spk-charter-lifecycle` |
   | `spk-doctrine-glossary` | `spk-charter-glossary` |
   | `spk-doctrine-spdd-reasons` | `spk-charter-spdd-reasons` |
   | `spk-doctrine-profile-load` | `spk-charter-profile-load` |
   | `spk-doctrine-semantic-compression` | `spk-charter-semantic-compression` |
   | `spk-doctrine-bulk-edit` | `spk-charter-bulk-edit` |
   | `spk-doctrine-show-me` | `spk-charter-show-me` |
   | `doctrine-daphne` | `charter-daphne` |
   | `018-doctrine-versioning-requirement` | `018-charter-versioning-requirement` |

   Serialized/operator mappings are also fixed by semantic seam, never by one blanket key rename:

   | 3.x surface | Canonical surface | Owner |
   |-------------|-------------------|-------|
   | `.kittify/charter/charter.yaml` `governance.doctrine` selection block | `governance.charter` | M1; 3.x reader alias, M6 removal |
   | glossary authority pathname `docs/context/doctrine.md` | `docs/context/charter.md` | M1 plus every active referrer; 3.x redirect/loader alias, M6 removal; X2 refs remain historical text |
   | `.kittify/config.yaml` top-level `doctrine.org.packs` | `charter_packs.org.packs` | M2; 3.x reader alias, M6 removal |
   | tracker `doctrine` ownership block, `--doctrine-mode`, and emitted/API `doctrine_mode` | `ownership`, `--ownership-mode`, and `ownership_mode` | M2; hidden warning/read aliases, M6 removal |
   | retrospective/apply target URN `doctrine:<kind>:<id>` | `charter:<kind>:<id>` (`<kind>`/`<id>` preserved) | M2 producer/reader/renderer/event consumers; 3.x active-read alias, M6 removal |
   | exported/documented public Python names/imports containing the legacy term | collision-free canonical charter-facade names in the frozen M2 map | M2 re-exports/docs/consumers/parity tests; 3.x warning aliases; M6 supported-export removal |
   | `spec-kitty-doctrine` project/distribution/wheel metadata plus exact `doctrine.api.__all__` | collision-free charter distribution/facade names in the frozen M2 map | M2 publication evidence, build/install/export consumers and wheel-closure tests; compatibility only if evidence requires it; M6 legacy metadata/export removal |
   | offer-side project overlay root `.kittify/doctrine/` | `.kittify/charter-packs/` | M3 checked upgrade + 3.x old-root reader warning; M6 removal |

   Tracker `field_owners` keeps its name under the canonical `ownership` block. M2 owns exhaustive `canonical-operator-surface-map.md`, its mechanically derived set-equal `canonical-cli-route-map.md` projection, local CLI/config/output/schema/event/API tests, and every mapped consumer regardless directory; known rows are fixed by the map contract. Any out-of-repo SaaS/event consumer must have an owner role, linked tracking reference/process, and compatibility milestone before M2 closes. `.kittify/charter-packs/` never aliases the distinct Charter Bundle at `.kittify/charter/`: M3 writes only the canonical root; 3.x reads either root; disjoint entries merge with canonical-root precedence; identical duplicates deduplicate; differing duplicate relative paths/URNs hard-fail; upgrade uses atomic rename or recoverable checked merge. M3 owns all readers, writers, staging, migrations, and consumers in the same PR.
5. **Compatibility policy** — “retired” means non-canonical/deprecated, not instantly absent. Before I1, the unchanged current authority is transitional. From I1 through M5, ordinary inventoried debt can only shrink in its assigned wave, while registered 3.x legacy identifiers/routes/keys/paths/redirects remain compatibility surfaces with deprecation warnings where executable. Unregistered new primary use is forbidden. By 4.0/M6: zero user-visible "doctrine" except justified X history/internal/test evidence (hard rule). (FR-005)
6. **Relationship to prior ADRs** (US1-AS2): explicitly supersedes the *terminology portion* of `2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md` (its resolution mechanics remain intact; its frontmatter status becomes `Superseded` with a pointer to this ADR, body untouched per C-003); reconciles with `2026-07-18-1` (bundle authority — the charter bundle is the consume-side surface this ADR's vocabulary names).
7. **FR-011 glossary decisions** (so M1 executes rather than re-decides):
   - Rename `docs/context/doctrine.md` to `docs/context/charter.md` and update all active referrers in M1. Every merged ADR body/title — including this new Accepted ADR after merge — and merged-mission inline/path reference remains byte-identical X2 historical text, whether or not archived, and carries no current-HEAD link-resolution promise; status/pointer metadata is the narrow ADR carve-out. A named audit proves zero active old referrer or dangling active link. Retain the registered 3.x compatibility redirect/loader alias only until M6.
   - Replace **Doctrine Pack** with canonical **Charter Pack**: the offer-side versioned distributable catalogue (`packs/built-in/`, org packs, project overlays).
   - Add canonical **Charter Bundle**: the per-project materialized file set under `.kittify/charter/`.
   - Disambiguate pack from bundle and from unrelated code senses of “bundle”.
   - Define the replacement for the **"Doctrine Domain"** sense (the DDD bounded-context glossary entry, `Location: src/doctrine/`) — plan position: the domain sense retires with the term; the entry is rewritten to name the governance-artefact layer without a "domain" re-brand.
8. **Charter-bundle Terminology Canon line** — M1 adds this exact legacy-free text to the human-authored governance/directives section of `.kittify/charter/charter.yaml`:

   > Terminology Canon: Use “charter” for the governance artefact layer: “charter pack” for a distributable catalogue, “charter bundle” for the project-local file set, “active charter” for an activated artefact, and “inactive charter” for an available but unactivated artefact.

   `charter.md` remains human-curated and is edited directly only if its in-scope text requires it. `charter generate` refreshes catalog/metadata; `charter sync` is not a writer.
9. **Guard-arming intent** — M1 fingerprints every classified pre-M1 guard-root occurrence, including owner=M1. It materializes the complete pre-edit baseline, then records its scoped source/baseline shrink in the same PR before the final post-M1 guard lands; each OC has one M1–M5 primary-use owner. WP02 supplies semantic CR candidates from disjoint observed coordinates. At the actual pre-M1 base, M1 reruns the audit, records fail-closed drift reconciliation, and materializes `tests/architectural/legacy_terminology_compatibility_registry.yaml`: each non-owning CR reservation has full legacy literal/path, semantic seam, disjoint source hit coordinates/OCs, fixed product maximum, introduction wave, M6 removal, disposition, fixed canonical target or fail-closed M2 owner/OC reference, exact X3 control fingerprint, and named tests. CR identity excludes the mutable resolved target. Control records do not consume product budget. Every funded source hit's OC primary owner equals the CR introduction wave; mixed-owner OCs/CRs are split. That wave removes ordinary fingerprints, sets `reserved` to `active` (or M2 distribution-only `closed-no-channel`), and may create at most the reserved count of exact OC product compatibility fingerprints. M2 freezes its target/map row before editing without changing stable CR identity. An unpublished distribution becomes `closed-no-channel` with no alias. No hit is reclassified or double-owned; no source hit funds two CRs. The guard enforces in-root entries and the pinned registry audit plus named verifier enforces other roots. Product compatibility cannot use fragments to evade audit. M6 empties all CR control/product records and runtime/file/key compatibility; only X may remain at I6. Mutation tests cover ordinary and compatibility-evasion failures, including double funding/control duplication. (C-004)

## Registration mechanics (C-002)

- Author from `docs/architecture/adr-template.md`.
- Set the new ADR status to `Accepted`; record the actual creation date and deciders/reviewers. Its decision is accepted on merge while mandatory item 1 makes product-vocabulary effectiveness conditional on M1/I1.
- Register with `python -m scripts.docs.freshen_adr_inventory` (updates era index row + page-inventory lockfile in one command).
- Old ADR edit is **status frontmatter only** (`Proposed` → `Superseded` + pointer line); body byte-for-byte untouched.

## Anti-goals (what the ADR must NOT do)

- Must not rename any surface itself (C-001 — this mission is planning-only).
- Must not assign version numbers to implementation scope (the 3.x/4.0 references are the compatibility decision's content, not pins).
- Must not mark any ADR other than `2026-07-15-1` as superseded (the other 10 doctrine-titled ADRs are immutable legacy snapshots).
