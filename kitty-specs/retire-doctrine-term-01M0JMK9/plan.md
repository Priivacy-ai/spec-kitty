# Implementation Plan: Retire the Doctrine Term

**Branch**: `feat/retire-doctrine-term` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/retire-doctrine-term-01M0JMK9/spec.md`

**Note**: Filled by `/spec-kitty.plan`. Execution workflow: `packs/built-in/missions/mission-steps/software-dev/plan/prompt.md`.

## Summary

This is a **research-and-planning mission**: it produces four program artifacts and executes no rename (C-001).

1. **ADR** in `docs/adr/3.x/` recording the retirement of "doctrine" from user-facing language in favor of "charter", with the three-way distinction (**charter bundle** / **active charter** / **inactive charter**), surviving kind vocabulary, scope boundary (non-public internals out; operator identifiers and supported public APIs in), and the 3.x-deprecate / 4.0-gone compatibility policy (FR-001..FR-005, FR-011 decisions). It amends the terminology portion of ADR `2026-07-15-1` (status → `Superseded` + pointer; body byte-for-byte untouched per C-003 carve-out) and reconciles with ADR `2026-07-18-1` (bundle authority).
2. **Occurrence inventory** (`inventory.md` + supporting `inventory-hits.tsv`) — pinned, mechanical content-and-path audits with one row per occurrence, each joined to a stable OC-## or X1/X2/X3 classification (FR-006, FR-007, NFR-001).
3. **Methodology analysis** (`methodology.md`) — surface ordering, stack invariants, reversible-prefix rollback rules, and a non-vacuous terminology guard based on exact classified occurrence fingerprints rather than file allowlisting (FR-008, C-004).
4. **Stacked mission plan** (`stacked-plan.md`) — the operator-approved shape (decision `01M0JWDEMKXQ5CMAE9PFEK8GF9`): **5 active missions + 1 deferred to 4.0**, each with slug, purpose, inputs/outputs, dependencies, ordinary OCs retired, and CRs introduced/removed; every OC-## has one M1–M5 primary owner (or explicit external deferral), while every CR has one M1–M4 introduction and M6 removal (FR-009, FR-010, NFR-003).

**Technical approach**: authority-first sequencing with an **atomic authority flip**. ADR acceptance in this planning mission fixes the future decision but explicitly leaves existing operational authority coherent through pre-I1. The glossary authorities, Charter Pack/Bundle distinction, charter-bundle human-owned sections, and two-track occurrence-fingerprint/compatibility guard land in **one mission / one PR** (M1). Before M1: transitional existing authority. After I1: replacement vocabulary effective and guard armed, with no split-authority product state.

**Stacked shape (operator-approved 2026-08-21):**

| # | Mission (proposed slug) | Retires |
|---|---|---|
| M1 | `charter-authority-flip` — rewrite all three glossary authorities atomically, rename `docs/context/doctrine.md` to `docs/context/charter.md` with every active referrer while retaining X2 refs as history, define Charter Pack/Bundle, update human-owned charter sections, refresh metadata, record pre-M1 preimage + M1 shrink, then arm guard | glossary-authority/referrer + charter-bundle classes; arms ratchet |
| M2 | `charter-cli-surface` — freeze exhaustive operator map + set-equal CLI projection; update commands, serialized/API values, supported public Python charter facades, exact `doctrine.api.__all__`, public distribution/wheel metadata, evidence-driven warning aliases, semantic config seams, and every mapped consumer regardless directory | CLI/config/serialized/API/public-API/distribution classes |
| M3 | `charter-packs-source` — Charter Pack strings/titles, built-in/org/project overlays, fixed `.kittify/doctrine/` → `.kittify/charter-packs/` checked migration, and canonical directive ID `018-charter-versioning-requirement` with alias | pack/overlay + directive-ID classes; excludes M2 map hits |
| M4 | `charter-skills-artifacts` — execute the ADR contract's complete skill/profile map, including both charter-lifecycle legacy IDs → `spk-charter-lifecycle`; source prompts, overrides, generated agent dirs via migration/upgrade; excludes route references already owned by M2 | non-route prompt/skill/profile/agent classes |
| M5 | `charter-docs-prose` — all remaining current human-facing prose regardless directory; ADR titles stay legacy; excludes glossary referrers owned by M1 and route references owned by M2 | active-human-prose classes |
| M6 *(deferred to 4.0)* | `charter-removal-audit` — strip aliases and migrated legacy paths/keys, delete all active/closed-no-channel CR product/control records, run the NFR-001 content-and-path audit | removes all CRs; verifies hard rule |

## Technical Context

**Language/Version**: Markdown/TSV deliverables; Python 3.11+ only via existing tooling and a NUL-safe audit one-liner; `git grep` for content and `git ls-tree -z` for pathnames; `python -m scripts.docs.freshen_adr_inventory` for ADR registration. No product rename occurs (C-001).
**Primary Dependencies**: None. No dependency is added, upgraded, or removed — the supply-chain planning section of the plan step prompt is therefore N/A (documented, not silent).
**Storage**: N/A — tracked files only; no databases or state stores touched.
**Testing**: Existing terminology guard, contract example round-trip, ratchet-baseline, docs freshness, and mission validation. The inventory schema's illustrative YAML carries an explicit round-trip skip marker and ratchet bump.
**Target Platform**: N/A — repository documentation and decision records.
**Project Type**: single — docs-only deliverables; no source-structure change.
**Performance Goals**: N/A (planning artifacts only).
**Constraints**: C-001..C-005 from the spec, plus charter constraints: PRs only / operator merges; ADR conventions (C-002); no version numbers in scope — the 3.x/4.0 references are the *content* of the compatibility decision (FR-005), not implementation pins.
**Scale/Scope**: 4 primary deliverables + supporting hit manifest and review evidence; 10 surface classes. Base evidence: 429 `src/`, 731 `tests/`, 430 total `docs/` (367 non-ADR/non-`docs/context` prose), 103 `packs/`, and 45 `.kittify/` files contain the term case-insensitively. The exact audit, not these orientation counts, governs.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — no new gaps.*

| Charter rule | Status | Note |
|---|---|---|
| Single canonical authority | PASS (by design) | The ADR is the one new vocabulary authority; it amends `2026-07-15-1` (terminology portion) and reconciles with `2026-07-18-1` (bundle authority). No second authority is introduced; the glossary rewrite (M1) derives from it. |
| Architectural alignment | PASS | No code changes; deliverables land in canonical homes (`docs/adr/3.x/`, mission directory). |
| DDD + tiered rigour | PASS | Occurrence class / stacked mission modeled as entities with invariants (`data-model.md`); rigour concentrated on the ADR content contract and the audit procedure, not on glue. |
| ATDD-first (adapted for docs) | PASS | Each FR maps to a verifiable acceptance procedure (`quickstart.md`). Red-first analog: the inventory WP runs the mechanical audit **before** classifying and records raw hits — evidence before conclusion. |
| Glossary & terminology adherence | PASS (with note) | This mission's own artifacts quote the retired term as *subject matter*; they live in `kitty-specs/` (guard-excluded) and become immutable X2 snapshots at merge, whether or not later archived (C-003). No new user-facing "doctrine" is introduced into `src/`, `tests/`, or scanned `docs/`. |
| Standing order #1 — adversarial squad cadence | PASS | Post-spec, post-plan, and post-tasks squad evidence exists; this PR reroll is recorded in `squad-findings-post-tasks-reroll.md`. |
| Standing order #5 — non-vacuous gates | PASS (by design) | Four ordinary mutations reject growth/substitution/staleness/new files. Six CR mutations reject wrong-wave/unregistered use, budget excess, fragment evasion, double-funded source coordinates, overlapping product fingerprints, and duplicate/moved/stale X3 controls; fail-closed M2 targets also block introduction before edits. |
| Standing order #6 — canonical sources | PASS | ADR template (`docs/architecture/adr-template.md`), freshen script, guard test — all used canonically; no improvised substitutes. |
| No version numbers in scope (Specify/Plan) | PASS (with note) | 3.x/4.0 appear only as the recorded compatibility decision (FR-005), per the operator's resolved decision moment `specify.compatibility.alias-policy`. |
| Branch-intent terminology | PASS | "repository root checkout" used; branch names stated explicitly (`feat/retire-doctrine-term`). |

## Project Structure

### Documentation (this mission)

```
kitty-specs/retire-doctrine-term-01M0JMK9/
├── plan.md              # This file (/spec-kitty.plan output)
├── research.md          # Phase 0 output — resolved unknowns (Decision/Rationale/Alternatives)
├── data-model.md        # Phase 1 output — occurrence class, surface taxonomy, stacked mission entities
├── contracts/           # Phase 1 output — artifact schemas this mission commits to
│   ├── README.md        # Index + consumers of each contract
│   ├── adr-content-contract.md    # What the ADR must state (FR-001..FR-005, FR-011 decisions)
│   ├── inventory-schema.md        # Format of inventory.md + inventory-hits.tsv and canonical audit
│   ├── operator-surface-map-schema.md # M2 authoritative map + frozen CLI projection contract
│   └── stacked-plan-schema.md     # Format of stacked-plan.md (per-mission fields + assignment table)
├── quickstart.md        # Phase 1 output — verification runbook (SC-001..SC-004 + guard green)
├── implementation-baseline.json # durable WP01-start diff anchor — created before first WP01 edit
├── inventory.md         # DELIVERABLE — created at implementation (IC-02)
├── inventory-hits.tsv   # supporting per-hit evidence — created with inventory.md
├── methodology.md       # DELIVERABLE — created at implementation (IC-03)
├── stacked-plan.md      # DELIVERABLE — created at implementation (IC-04)
└── squad-findings-post-tasks-reroll.md  # initial + reroll adversarial evidence
```

### Repository surfaces touched by the deliverables (no `src/` changes — C-001)

```
docs/adr/3.x/
├── <creation-date>-N-retire-doctrine-term-charter-is-the-canonical-vocabulary.md   # NEW ADR (IC-01; actual WP01 date; N = next free number for that date)
├── index.md                                                        # + table row via freshen script
└── 2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md  # status frontmatter ONLY → Superseded + pointer (C-003 carve-out)
docs/development/3-2-page-inventory.yaml                            # regenerated by freshen script (lockfile)
```

**Structure Decision**: planning-only, single stream. Deliverables live in the mission directory; the ADR lives in `docs/adr/3.x/`. No product source or agent-directory changes occur. A contract example skip marker and its ratchet metadata are allowed planning-CI compatibility edits under C-001.

## Complexity Tracking

No Charter Check violations — section not applicable.

## Implementation Concern Map

> Concerns are NOT work packages; `/spec-kitty.tasks` translates them into WPs.

### IC-01 — ADR authoring and registration

- **Purpose**: Record the terminology decision as the single canonical authority so no downstream mission re-litigates vocabulary.
- **Relevant requirements**: FR-001..FR-005, FR-011 (decisions the ADR must fix), NFR-002, C-002, C-003.
- **Affected surfaces**: `docs/adr/3.x/` (new ADR + index row), `docs/development/3-2-page-inventory.yaml` (lockfile via freshen script), `docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md` (status frontmatter only).
- **Sequencing/depends-on**: none — first concern; everything else cites the ADR.
- **Risks**: (a) ADR self-sufficiency: all six questions must be answerable. (b) Operator IDs, supported public APIs, exact `doctrine.api.__all__`, and distribution/wheel metadata are in scope; only non-public internals remain X1. M2 maps public exports/imports and packaging to charter facades/distribution, records publication evidence, and owns wheel-closure consumers while internal implementation may stay under `src/doctrine/`. (c) Exact canon line fixed. (d) Pack vs Bundle and `.kittify/charter-packs/` fixed. (e) Old ADR body untouched except metadata. (f) Active glossary refs move; X2 refs remain history.

### IC-02 — Occurrence inventory (mechanical audit)

- **Purpose**: Produce the evidence-based work list for the whole program, with stable class identifiers trackable from inventory → mission → completion.
- **Relevant requirements**: FR-006, FR-007, NFR-001, SC-002.
- **Affected surfaces**: `inventory.md` and `inventory-hits.tsv` (new artifacts; schema in `contracts/inventory-schema.md`).
- **Sequencing/depends-on**: IC-01 (classification rules cite the ADR's scope decisions, especially operator-typed identifiers).
- **Risks**: (a) The previous shell-expanded audit exceeds this repo's `ARG_MAX`, omits tracked pathname debt, and `-I` omits NUL-containing blobs; the contract pins safe `-a` content and NUL-safe pathname commands at the exact fetched `origin/main` tip, after an ancestor precondition rejects stale branch points. (b) Every content occurrence has path/line/column; every matched pathname has one row. Inventory summaries derive from that manifest. (c) Classification is per hit: X1 non-public internal identifiers, X2 immutable ADR/event/merged-mission history (archive optional), X3 intentional quoted/non-user-facing test or data. Supported public APIs, active glossary authorities, and compatibility aliases remain in scope. Active human-facing source-tree Markdown/READMEs are S3, not X merely because they live below `src/`; root docs are exclusively S9. (d) Canonical glossary data exists in `.kittify/glossaries/spec_kitty_core.yaml` and `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`; both move atomically under `tests/architectural/test_glossary_pack_parity.py`, coordinated with open issue #2727.

### IC-03 — Ordering and methodology analysis

- **Purpose**: State *in what order and why*, with the invariant that must hold at each stack level, so the program never breaks user-facing coherence mid-flight.
- **Relevant requirements**: FR-008, C-004, SC-003 (ordering half).
- **Affected surfaces**: `kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md` (new artifact).
- **Sequencing/depends-on**: IC-02 (ordering rationale cites inventory evidence).
- **Risks / required content**: (a) Guard seeds exact normalized fingerprints for every actual pre-M1 guard-root hit, including owner=M1. M1 records complete preimage → scoped same-PR source/baseline shrink → post-M1 guard; ordinary OC entries with one M1–M5 owner continue shrinking. WP02's semantic CR candidates carry observed evidence; M1 fail-closed reconciles actual-base drift and materializes disjoint source coordinates, frozen product maxima, fixed/M2-referenced targets, X3 control records, introduction waves, M6 removal, and tests in the fixed registry path. Every funded source OC owner equals introduction wave; mixed-owner rows split. Only that wave may replace ordinary hits with at-budget OC product compatibility and transition `reserved` to `active` (or M2 distribution-only `closed-no-channel`); M2 resolves referenced targets before edits without changing CR identity. Control records do not consume product budget; no source double-funds CRs. I6 has only justified X plus an empty CR inventory. Mutations cover ordinary growth/equal-count/stale/new-file and unregistered relocation/overlap/double-funding/budget/duplicate-control/fragment evasion. File/count allowlisting is forbidden. (b) Every out-of-root class has one named audit/parity/runtime verifier. (c) Atomic authority flip, I0–I6, per-wave manifest regeneration, and same-wave consumers prevent catfooding drift. (d) M6 proves content and pathname removal. (e) Rollback is prefix-safe: before dependents, revert the wave; afterward reverse the landed suffix or forward-fix. M6 may restore compatibility only while 3.x remains supported.

### IC-04 — Stacked mission plan

- **Purpose**: Express the retirement as executable spec-kitty missions with explicit dependencies, so execution proceeds mission by mission without re-deciding anything.
- **Relevant requirements**: FR-009, FR-010, NFR-003, SC-003/SC-004.
- **Affected surfaces**: `kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md` (new artifact; schema in `contracts/stacked-plan-schema.md`).
- **Sequencing/depends-on**: IC-03 (stack follows the methodology ordering).
- **Risks / required content**: (a) Shape is fixed: 5 active + 1 deferred. (b) M1 has zero local questions. M2's one bounded operator-surface-map question owns every affected command, serialized/API occurrence/consumer, supported public API, and distribution/wheel surface across categories and freezes authoritative `canonical-operator-surface-map.md` plus mechanically derived set-equal `canonical-cli-route-map.md`, so M3–M5 do not depend on it. Exact `doctrine.api.__all__`, packaging metadata, publication evidence, fixed known rows, and schema prevent a wildcard deferral. All other names and path semantics are fixed, including `.kittify/charter-packs/` and its dual-read/collision/migration contract. (c) Every M1–M6 wave is `change_mode: bulk_edit` with a scoped occurrence map. (d) Assignment lives only in `stacked-plan.md`: every OC-## has one M1–M5 owner or a complete external deferral; every CR has one declared M1–M4 introduction and M6 removal; each funded source OC owner equals introduction wave; mixed-owner rows split; disjoint source/product coordinates prevent double funding. (e) Skill/profile/directive canonical mappings and three distinct semantic config seams are already fixed.

### IC-05 — Verification and closeout

- **Purpose**: Prove the four success criteria with live evidence before merge.
- **Relevant requirements**: SC-001..SC-004, NFR-001..NFR-003.
- **Affected surfaces**: `kitty-specs/retire-doctrine-term-01M0JMK9/quickstart.md` (runbook) + review evidence in the PR.
- **Sequencing/depends-on**: IC-01..IC-04 (runs last).
- **Risks / required content**: One named independent reviewer (squad or operator) answers the spec's exact six questions; operator review is optional, not a second gate. Fetch target, reject unless `origin/main` is an ancestor, and re-run the identical audit at that exact target tip with manifest arithmetic; reject ownerless deferrals/TBDs; dry-run M1 with zero new decisions; validate guard and docs-contract CI. C-001 compares both the current target-tip planning base (`git rev-parse origin/main`) and the SHA WP01 durably records before editing in `implementation-baseline.json`, including committed and working-tree changes.

## Parallel Work Analysis

Single stream — no parallel work. The deliverables are sequentially dependent (ADR → inventory → methodology → stacked plan), and this mission is docs-only; there are no independent file sets to split across agents.
