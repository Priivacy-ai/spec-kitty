# Research: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 0 output** · **Updated**: 2026-08-22

All cross-wave decisions are resolved. The only retained local design question is M2's frozen canonical operator-surface map for still-unfixed command routes and inventory-discovered serialized/API tokens; it is bounded to M2 and cannot change stack order or another wave's inputs.

## R1 — ADR registration

**Decision**: Author from `docs/architecture/adr-template.md` under `docs/adr/3.x/`, use the next free dated sequence at creation, and run `python -m scripts.docs.freshen_adr_inventory` so the era index and `docs/development/3-2-page-inventory.yaml` update together.

**Evidence/rationale**: The index uses `Date | Title`; status is ADR frontmatter. The freshen script owns both registration surfaces.

**Rejected**: hand-edited index/lockfile or a new index status column.

## R2 — Exact occurrence fingerprints, not file allowlisting

**Decision**: M1 arms `tests/architectural/test_no_legacy_terminology.py` from a two-track baseline of **all** classified pre-M1 guard-root occurrences. Ordinary primary-use OC-## owned exactly once by M1–M5 plus X1/X2/X3 records carry path, normalized-line/path hash, match ordinal, kind, classification, and owner wave. M1 materializes the complete pre-edit baseline, then removes its authority source/baseline entries in the same PR; the preimage, scoped M1 delta, and post-M1 baseline are evidence. Later ordinary OC entries shrink in M2–M5; I6 permits only justified X. Separately, WP02 plans semantic CR candidates from disjoint observed hit coordinates. M1 reruns at its actual base, reconciles drift fail-closed, and materializes each reservation in `tests/architectural/legacy_terminology_compatibility_registry.yaml` with disjoint source coordinates, frozen product maximum, fixed target or fail-closed M2 owner/OC reference, introduction wave, M6 removal, disposition, exact X3 control fingerprint, and named tests. CR identity excludes the mutable resolved target; registry control literals never consume product budget. Every funded source hit's OC owner equals its introduction wave, with mixed-owner OCs/CRs split. Only that M1–M4 wave may remove ordinary hits, set `reserved` to `active` (or M2 distribution-only `closed-no-channel`), and introduce/relocate at most that budget of OC product compatibility fingerprints; M2 freezes referenced target before edits without changing CR identity. M6 removes all CR control/product fingerprints and runtime/file/key exposure. Tests prove four ordinary failures plus six CR failures: unregistered/wrong-wave use, product-budget excess, fragment evasion, double-funded source coordinates, overlapping product fingerprints, and duplicate/moved/stale controls; a separate fail-closed check blocks M2-owned introduction before target/disposition resolution.

**Evidence/rationale**: The current guard scans `src/tests/docs` and has path-fragment exclusions, not an active-surface exemption model. A file allowlist would hide growth in mixed files; `src/charter/context_renderers/bootstrap_text.py` alone mixes an emitted heading with many internal occurrences. Fingerprints make equal-count substitution and stale allowances observable; the registry prevents retained 3.x keys/paths/aliases from escaping the same proof during relocation.

**Rejected**: directory/file allowlists, count-only budgets, and line-number-only exemptions.

## R3 — Charter bundle ownership

**Decision**: M1 direct-edits the human-authored governance/directive/activation/override sections of `.kittify/charter/charter.yaml`. `charter.md` is a human-curated companion and is directly curated if its classified text needs change. `charter generate` refreshes only catalog/metadata. Graph, interview answers, and generated/runtime sections go through their owning workflows. `charter sync` is never treated as a writer.

**Evidence/rationale**: `src/charter/sync.py:145-157` writes nothing. `docs/context/governance-files.md:17-24,30-52,93-101` states `charter.md` is human-curated and never generated; generation refreshes catalog/metadata. Base orientation: `charter.yaml` 53 matching lines, `charter.md` 13, `graph.yml` 2, interview answers 9.

**Rejected**: regenerate-overwrite of `charter.md`, blanket direct edits to generated sections, and sync-as-writer.

## R4 — Operator command/serialization mapping is bounded local design

**Decision**: M2 produces authoritative `canonical-operator-surface-map.md` and set-equal frozen CLI projection before editing. It enumerates the 8-command group/`doctor` route plus every otherwise-unfixed M2-scope serialized/API token, supported public Python API name/import, one aggregate `doctrine.api` facade row carrying exact `__all__` membership evidence, separate OC-backed rows only for legacy-bearing members, and public distribution/project/wheel metadata joined from inventory, and owns every mapped consumer regardless directory. Public API is defined by `__all__`, package re-export, public docs/skills, external contract, or installable package metadata; non-public implementation remains X1. M2 adds canonical charter facades/distribution, records publication evidence, applies 3.x compatibility only where required, and proves M6 supported-export/docs/metadata removal. ADR-fixed M1/M3/M4 seams retain owners; M3–M5 exclude M2 hits.

**Evidence/rationale**: Existing command groups and serialized/API forms have different semantics, so a mechanical global substitution would be speculative. The local question cannot leak cross-wave because occurrence assignment follows operator-surface treatment rather than directory: M2 updates all mapped consumers and freezes one exhaustive map in the same PR; later waves neither decide nor update those hits.

**Rejected**: hard break, silent aliases, or an unreviewed one-to-one map in this mission.

## R5 — Complete surface topology

**Decision**: Use S1–S10 from `data-model.md`. In addition to the original docs/CLI/pack categories, inventory must cover `.kittify/config.yaml` serialized keys, `.kittify/overrides/`, `.kittify/glossaries/`, built-in glossary packs, `.kittify/doctrine/` project paths, workflow filenames, all operator-typed IDs, and active human-facing Markdown/READMEs under source directories. Human prose is classified by audience, not by a `docs/` pathname.

**Evidence/rationale**: Live occurrences exist on all these surfaces; content-only scans cannot find pathname debt. Current orientation counts are 429 `src/`, 731 `tests/`, 430 total `docs/` (367 prose after ADR/context exclusions), 103 `packs/`, and 45 `.kittify/` files.

**Rejected**: defaulting unlisted locations out of scope. Discovery yields an unclassified failure until a rule is explicit.

## R6 — Canonical vocabulary and operator IDs

**Decision**:

- **Charter Pack** = versioned distributable governance catalogue, offer side; replaces “Doctrine Pack”.
- **Charter Bundle** = per-project materialized file set under `.kittify/charter/`, consume side.
- **Active Charter** = governance artefact activated/wired in for the project.
- **Inactive Charter** = artefact available in a Charter Pack but not activated.
- Canonical operator IDs use the complete ADR-contract map. In particular, `spk-doctrine-charter` and its pre-existing legacy alias `spec-kitty-charter-doctrine` both route to `spk-charter-lifecycle`; the other six `spk-doctrine-*` skills map to explicitly named `spk-charter-*` IDs; profile/directive replacements are `charter-daphne` and `018-charter-versioning-requirement`. Every old ID warns through 3.x and is removed by M6.

Existing kind labels survive in their existing roles; the ADR must not imply every profile/glossary/step-contract kind is activatable. “Doctrine Domain” retires; its glossary sense becomes the governance-artefact layer without a new domain brand.

**Rejected**: preserving “Doctrine Pack”, treating bundle activation as the active/inactive distinction, or classifying operator IDs as internal.

## R7 — Glossary authority parity and #2727

**Decision**: M1 changes all three current glossary authorities atomically: rename `docs/context/doctrine.md` to canonical `docs/context/charter.md`, update every active referrer in docs/source/tests in the same PR, and update both YAML glossary authorities. Immutable ADR/archive inline/path references remain byte-identical X2 historical text with no current-HEAD link-resolution promise. A named audit proves zero active old referrer/dangling active link. A registered 3.x old-path redirect/loader alias warns and is removed by M6. M1 respects glossary parity and coordinates with #2727 without allowing split authority.

**Evidence/rationale**: The previously cited `src/doctrine/glossary_packs/built-in/` path does not exist. The actual YAML files have 15 and 23 matching lines and are held in parity.

**Rejected**: docs-only glossary flip, treating active glossary data as X3, or waiting on #2727 while authorities disagree.

## R8 — Pinned, non-fakeable audit

**Decision**: Immediately before WP01's first edit, `git fetch origin main` and the target-ancestor
check must pass; WP01 atomically stores that exact `target_tip` with `implementation_base`. WP02–WP05
load the same frozen tip as `base_commit`; a stale branch-point merge base or mid-mission refetch/repoint
is forbidden. Incorporating a different target invalidates evidence and requires a fresh target-based
branch, replay of planning commits only, and restart at WP01.
It uses `git grep -aino --column` for every occurrence, forcing NUL-containing tracked blobs to text,
plus `git ls-tree -r -z --name-only` with a NUL-safe filter for matched pathnames.
`inventory-hits.tsv` records one row per hit and drives every summary/count. Unit: one content
coordinate plus one pathname row per matching tracked path.

**Evidence/rationale**: The former shell-expanded command exceeds this repository's argument limit and omits pathname debt. `-I` also hid NUL-containing migration/quarantine JSON/JSONL (177 occurrences at the reviewed base), so the canonical audit uses `-a`. A branch point can omit target changes (the reroll found `origin/main` 119 commits ahead), so current target ancestry is a precondition. Exact pinned output governs; orientation counts are never contractual.

**Rejected**: file totals with three examples, line-based counts, pathname omission, and shell-expanded file lists.

## R9 — Per-hit classification

**Decision**: X1 is non-public internal identifiers only; supported public APIs are OC. X2 is every merged ADR body/title (including this new Accepted terminology ADR after merge), immutable event journals, and merged mission snapshots whether or not archived; merge is the threshold, so active/unmerged mission docs are never X2. ADR status/pointer metadata remains the narrow mutable carve-out. X3 is intentional non-user-facing quoted test/matcher/data. Glossary authorities, compatibility aliases/warnings, serialized keys, and operator IDs remain in-scope while they exist.

**Rationale**: File-level classification fails on mixed code/output files and allows evidence to be invented from totals. Per-hit manifest membership makes exhaustiveness reviewable.

## R10 — Authority-first stack and catfooding

**Decision**: M1 atomically flips glossary authorities and their direct referrers, charter instruction surfaces, and guard. M2 moves executable/config/workflow surfaces; M3 packs/overlays/directive ID; M4 skills/profiles/prompts/agents; M5 all remaining active human prose regardless directory; M6 compatibility removal and final audit. M1→I1, M2→I2, M3→I3, M4→I4, M5→I5, M6→I6.

Each wave regenerates per-hit evidence and updates same-wave consumers. New planning snapshots classify X2 at merge; later archival does not change classification. Generated old output must not be copied into a new user-facing surface.

**Rejected**: guard-first wave (creates a forbidden-before-canonical gap) and separate authority updates that break glossary parity.

## R11 — Bulk-edit and rollback contracts

**Decision**: This mission remains planning-only and is not a product bulk edit. Every downstream M1–M6 mission is `change_mode: bulk_edit` with a scoped occurrence map, including M6 alias/path/key removal. Before dependents land, a wave may be reverted alone. Afterward, reverse the landed suffix or forward-fix. M6 may restore aliases only while 3.x remains supported; after 4.0, rollback is release-level.

**Rejected**: classifying only M2–M5 as bulk, or allowing an arbitrary middle-wave revert after dependents rely on it.

## R12 — Prior ADR amendment

**Decision**: The new ADR supersedes only the terminology portion of `2026-07-15-1`; its resolution mechanics survive. Change old frontmatter status/pointer only; keep body byte-identical. The other 10 matching-title ADRs remain immutable history.

**Evidence/rationale**: Eleven 3.x ADR titles contain the retired term: one amended and ten retained.

## R13 — Project overlay root cutover

**Decision**: M3 moves the offer-side project overlay root from `.kittify/doctrine/` to `.kittify/charter-packs/`; `.kittify/charter/` remains the distinct consume-side Charter Bundle. Canonical writers and synthesis staging publish only to `.kittify/charter-packs/`. During 3.x, readers accept either root with a deprecation warning for the old root. When both exist, disjoint relative paths merge with canonical-root precedence; byte-identical duplicates deduplicate; a differing duplicate relative path/URN is a hard collision with remediation, never a silent winner. The upgrade migration renames atomically when the destination is absent and otherwise performs that checked merge with recoverable backup. M3 owns every reader, writer, staging path, config/doc/test consumer, and migration in the same PR; rollback restores the pre-wave root/read order before dependents. M6 deletes old-root reading, migration, registry entry, and pathname.

**Rejected**: moving offer-side overlays into `.kittify/charter/`, dual-writing both roots, silent collision precedence, or leaving destination semantics to M3.

## R14 — Serialized seams are not one rename

**Decision**: M1 maps charter selection `governance.doctrine` to `governance.charter`. M2 maps org-pack config `doctrine.org.packs` to `charter_packs.org.packs`, and independently maps tracker ownership `tracker.doctrine`, `--doctrine-mode`, and `doctrine_mode` to `tracker.ownership`, `--ownership-mode`, and `ownership_mode`; `field_owners` survives. Each legacy seam has a registered 3.x reader/flag alias and named local migration/API/output tests; M6 removes it. Any SaaS consumer is an explicit owner/tracking/milestone deferral before M2 closes.

**Rejected**: a blanket `doctrine` → `charter_packs` serialized-key substitution.

## R15 — Durable implementation diff anchor

**Decision**: Before any WP01 edit, WP01 fetches/ancestry-checks `origin/main` and atomically records
`target_ref`, its exact 40-character `target_tip`, exact `implementation_base`, both capture commands,
`captured_at`, `captured_by`, and `wp_id` (`WP01`) in mission artifact
`implementation-baseline.json`. WP01 owns and commits it; WP02–WP05 never repoint it. WP05 validates
target→implementation→HEAD ancestry and the complete committed plus working-tree implementation delta.
A transient shell variable is orientation only; a post-capture target incorporation requires the
fresh-branch/planning-replay/WP01-restart procedure.

**Rejected**: relying on shell-session state or reconstructing the anchor from commit-message conventions.

## R16 — Serialized/API topology

**Decision**: `contracts/operator-surface-map-schema.md` is the exhaustive M2 contract. Fixed known mappings include target URN, target-kind enums, proposal category, policy/hash keys, tool enum, and emitted JSON alias. Mandatory public-API rows cover exported/documented `DoctrineCatalog`, `DoctrineSelectionConfig`, `DoctrineService`, loaders/factories/re-exports, an aggregate `doctrine.api` facade row with exact membership evidence, each legacy-bearing public member, `spec-kitty-doctrine` project/distribution/wheel metadata, wheel-closure consumers, and every additional inventory hit; M2 chooses collision-free charter-facade/distribution names and records publication evidence in its sole bounded question. Legacy-free `__all__` members are evidence rather than invented hit rows. Internal attributes may remain X1 while public aliases change. M2 owns producers/readers/events/renderers/contracts/builds and external coordination. Immutable X2 records stay byte-identical; applicable readers translate old values only at display boundaries.

**Rejected**: assigning serialized hits by source directory, treating persisted strings as internal symbols, mutating immutable journals, or leaving mappings for M3–M5.
