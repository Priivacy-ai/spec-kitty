# Implementation Plan: Charter Authority Flip (retire-doctrine-term M1)

**Branch**: `feat/charter-authority-flip` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)
**Input**: Wave M1 of `retire-doctrine-term-01M0JMK9` (#3664/#3732). Authority: ADR `2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md`; program methodology `kitty-specs/retire-doctrine-term-01M0JMK9/{methodology,stacked-plan,inventory}.md`.

Planning informed by a pre-plan brownfield research squad (3 profile-loaded scouts: glossary-parity seam, CR-01/migration seam, referrers/transition-guard seam). Their corrections to the spec are folded below.

## Summary

Make the accepted ADR effective in the **Charter + glossary authority graph only**. Four coordinated changes, one parity transaction + a shrink-only guard:

1. Flip the glossary **authority quartet** (core seed YAML, built-in pack YAML, the `docs/context/doctrine.md`→`charter.md` context glossary, and Charter Bundle referrers) from the retired *governing-term* sense of "doctrine" to "charter", under one parity gate that rolls back all authorities on divergence.
2. Author the `charter` **Terminology-Canon** entry (≥5 senses + "do-NOT" guards + the new **Pack Default Charter** row) in the canonical `### PRIMARY partition`-style table form.
3. Cut over the `governance.doctrine` selection key to `governance.charter` with a 3.x **warn-once compat reader** (CR-01, budget ≤3 + control) and migrate `interview/answers.yaml`.
4. Arm a **shrink-only transition guard** (untracked baseline) so the retired governing term cannot be re-introduced.

Product/code/path/historical removal is downstream (M2–M6) and out of scope. `change_mode: bulk_edit`.

## Technical Context

**Language/Version**: Python 3.11+ | **Primary Dependencies**: pydantic, ruamel.yaml, typer, pytest | **Storage**: YAML authority files + JSONL status | **Testing**: pytest (`tests/architectural/`, `tests/glossary/`, `tests/charter/`) | **Project Type**: single (CLI/runtime) | **Constraints**: `ruff`+`mypy` zero-issue; terminology guard green; four archive roots byte-identical (NFR-002); 0 operator questions (NFR-001).

## Charter Check (override recorded)

The Charter ordinarily protects user customization and historical/current-tree evidence. Per ADR `2026-08-22-2` the operator has **explicitly overridden** those protections for this terminology-extinction program. M1 records the override through the owning writers (C-002). Preserved invariants: single canonical authority, ATDD-first evidence, exact ownership (with rationale-backed link-closure leeway, see Cross-Ownership below), smallest coherent diffs, archive immutability.

## Corrections to the spec from the brownfield squad (binding)

- **C-COR-1 — Four authorities, not three.** The glossary triad is core-seed YAML + built-in-pack YAML + the **Markdown context glossary** `docs/context/doctrine.md`→`charter.md`; the Charter Bundle referrers are the fourth surface re-pointed in the same transaction. (spec.md said "3 glossary authorities + Charter Bundle" loosely.)
- **C-COR-2 — `doctrine` is polysemous; NOT a blanket replace.** Only the *authority/governing-term* sense retires. `src/doctrine/…` path literals and the domain concepts `drg` / `doctrine reference graph` / `doctrine artifact` / `doctrine pack` **stay** (they are M2/other-wave concerns or permanent vocabulary). Every hit is classified in `occurrence_map.yaml`.
- **C-COR-3 — The 18 `docs/api/agent_profiles/*.md` referrers are AUTHORED REMAINDERS, hand-edited, not regenerated.** `derive_related()` (`scripts/docs/frontmatter_backfill.py:244`) derives `related:` only from in-body links; there is no in-body doctrine.md link and no source-YAML origin, so re-running the generator would **drop** them. FR-002's "re-point via generator" applies instead to the **two `docs/development/3-2-*.yaml` lockfiles** (regen via `scripts/docs/inventory_lockfile.py`).
- **C-COR-4 — Baseline store is UNTRACKED and never under `kitty-specs/`.** `methodology.md:273` ("in M1's mission dir") is stale drafting; the authoritative rule (`methodology.md:144`, `spec.md:61`) is never-in-archive, so M6's later deletion doesn't break `test_archive_root_byte_identical`.
- **C-COR-5 — CR-01 remap must be dict-level, not a pydantic alias.** A `Field(alias=…)` remaps silently and fails SC-002's warn-once.

## Phase 0 — Occurrence classification (bulk_edit gate)

Author `occurrence_map.yaml` classifying the **302 M1-owned occurrence rows** (OC-01 221 / OC-02 80 / OC-40 1, `inventory.md`) across the canonical 8 categories, each as `rename` (governing-term) vs `keep` (domain concept / path literal) vs `path` (OC-40 rename). Re-derive the M1 slice at the current base (four-root exclusion, per the re-inventory; drift from pinned base is +219 total). The 43 path referrers are a **disjoint** edit set (see Cross-Ownership) and are listed as owned *surfaces*, not occurrence rows.

## Phase 1 — Design: three implementation slices (glossary-first)

### Slice 4 (P1) — Glossary quartet parity + charter Terminology-Canon

**Owned files:** `.kittify/glossaries/spec_kitty_core.yaml` (auth 1), `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml` (auth 2 — regen script gone, **hand-edit + keep byte-parity with seed**), `docs/context/doctrine.md`→`docs/context/charter.md` (auth 3), Charter Bundle referrers (auth 4).
**Term ID = the `surface` string** (no separate id field). Schema is `extra="forbid"` (`src/glossary/seed_schema.py:20,73`) + lowercase-trim `surface` validator (`:34`) → the Canon disambiguation lives in the **Markdown** (auth 3), never as new YAML keys.
**Canon entry:** copy the `### PRIMARY partition` two-column table at `docs/context/orchestration.md:538-546` (rows `**Definition**`, `**Canonical term**`, `**Do NOT use when**`). Add `### charter` with senses: Charter Bundle / Charter Pack / `src/charter/` package / `spec-kitty charter` CLI group / Active-Inactive Charter artefact / **Pack Default Charter** — each with a "do-NOT-use-when" redirect.
**Tests:** create `tests/architectural/test_glossary_authority_parity.py` reusing the seed-driven join in existing `test_glossary_pack_parity.py` (do NOT delete it — standing 1↔2 gate) and extending to auth 3; create `test_charter_owner_map_executed`. Safety net during edits: `test_glossary_pack_parity.py::test_every_seed_term_every_present_key_round_trips_identically` + `tests/doctrine/test_glossary_link_integrity.py` (anchor closure; double-hyphen anchors are literal).

### Slice 5 (P2) — `doctrine.md`→`charter.md` rename + 43 referrers

**Re-point order (whack-a-field-safe):** (1) `git mv docs/context/doctrine.md docs/context/charter.md`; (2) hand-edit the **18** `docs/api/agent_profiles/*.md` `related:` frontmatter paths (authored remainders — C-COR-3); (3) hand-edit the ~23 source referrers (`docs/context/{orchestration,governance,configuration-project-structure}.md`, `docs/architecture/doctrine-kinds.md`, `docs/development/how-to/create-a-doctrine-artifact.md`, 2 ADRs, `docs/plans/**`, `docs/reports/test-sanitation/**`, `src/doctrine/**/README.md`, `tests/architectural/test_no_dead_doctrine_paths.py`, `tests/glossary/test_canonical_promotion.py`) — **path token only**, not the term content later waves own; (4) regenerate the **2** `docs/development/3-2-*.yaml` lockfiles via `scripts/docs/inventory_lockfile.py` (never hand-edit — `INVENTORY-LOCKFILE-DRIFT` gate); (5) prove closure with `scripts/docs/related_validator.py` (zero dangling `related:`).

### Slice 6 (P1-code) — CR-01 key cutover + migration + guard

**Warn-compat reader:** in `load_governance_config` (`src/charter/activation/sync.py:262-263`), before `GovernanceConfig.model_validate`, detect legacy `doctrine` key in the raw `governance_data` dict, warn once (copy `emit_catalog_miss_warning` shape at `src/charter/activation/_catalog_miss.py:327`; gate with `@functools.lru_cache`/module flag — filter alone is unsafe under `filterwarnings=error`), prefer canonical when both present, rename → `charter`, then validate.
**Schema:** rename field `GovernanceConfig.doctrine`→`.charter` (`src/charter/activation/schemas.py:209`); keep value class `DoctrineSelectionConfig` (M2). **No** populate-by-name alias.
**Three readers:** `resolver.py:845`, `org_pack_discovery.py:201`, `_status_collectors.py:175` → `.charter`.
**Migration script (new):** `scripts/migrate_charter_interview_answers.py` — token-literal-free (frozen before/after strings from `bytes([...]).decode()`, unit-asserted); scope replacement to selection-key/governing-term bytes **only** (a global replace corrupts the comment slug `doctrine-catfooding-2196`, a proper noun); prefer targeted text substitution over ruamel load→dump (R5: renormalization); back up pre-image, restore byte-for-byte on failure. Answers path `.kittify/charter/interview/answers.yaml` (`_common.py:101`); harden the writer at `src/charter/activation/interview.py:400-404` into a **validating serializer** that fails closed if any answer/selection is dropped/reset.
**charter generate:** ensure only the section-update path `compiler.py:515-516` runs (INV-9 preserves other sections); never `compiler.py:725` (whole-doc save clobbers governance).
**Guard (armed LAST):** `test_transition_guard_shrink_only` — reuse the per-path-signature shrink-or-equal + **self-mutation teeth** shape of `tests/architectural/test_bare_prose_corpus_ratchet.py`; baseline = M1's own opening four-root fingerprint (`d8a09ef1…` procedure, not the stale single-root `3631531b…`); store **untracked**, never under `kitty-specs/`. Do NOT create `scripts/audit_retired_term_zero.py` (M6 owns it).

## The 12 ATDD tests (red-first)

| Test | Slice | Asserts |
|---|---|---|
| `test_glossary_authority_parity` | 4 | 4-authority term-set + defs + aliases-by-surface + link closure; divergence → all roll back |
| `test_charter_owner_map_executed` | 4 | every Charter artifact owner action ran or verified no-op; regenerated hashes match |
| `test_governance_doctrine_key_warns_and_maps` | 6 | legacy key warns once + maps to `governance.charter` |
| `test_governance_charter_key_canonical` | 6 | canonical key reads with no warning |
| `test_answers_migration_preserves_unknown_keys_and_all_answers` | 6 | all answers + unknown keys survive |
| `test_answers_migration_preserves_selected_assets_and_template_set` | 6 | `selected_assets` + `template_set` survive |
| `test_answers_migration_changes_only_frozen_target_bytes` | 6 | only governing-term bytes differ (slug `doctrine-catfooding-2196` untouched) |
| `test_answers_migration_failure_restores_preimage` | 6 | injected failure restores byte-identical pre-image |
| `test_interview_serializer_round_trips_extended_answers` | 6 | round-trips; deletion/default-reset/empty-`selected_tactics` rejected |
| `test_transition_guard_shrink_only` | 6 | shrink/equal passes, widen fails; non-vacuous (self-mutation teeth) |
| `test_archive_root_byte_identical` | all | four exclusion roots byte-identical pre/post M1 |
| `test_no_legacy_terminology` (extend) | 4/6 | governing `doctrine` absent from M1-owned surfaces (fix stale `src/doctrine/glossary_packs/built-in/` exemption path at `test_no_legacy_terminology.py:61,428`) |

## Cross-Ownership footprint (rationale-backed leeway)

The 43 path referrers are a **disjoint edit set** from the 302 occurrence rows; their *content* classes belong to later waves (18 OC-11/M4, 2 OC-26/M5, 4 OC-31/M5, 4 OC-30/M5, 6 OC-16/M2, 2 OC-23-24/M2). M1 re-points **only the path token** for link closure at its own tip — owned as *surfaces* (`stacked-plan.md:101,390`), not double-funding later waves' occurrence rows.

## Risk register (from squad landmines)

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | Polysemous `doctrine` blanket-replaced → corrupts `src/doctrine/` paths + DRG vocab | occurrence_map classifies every hit; keep domain/path senses |
| R2 | Silent pydantic alias fails warn-once (SC-002) | dict-level remap in `sync.py:262-263` |
| R3 | `compiler.py:725` whole-doc save clobbers migrated governance | pin `:515-516` section-update; assert governance partition byte-stable |
| R4 | Global byte-replace corrupts comment slug `doctrine-catfooding-2196` | scope to governing-term bytes; `test_answers_migration_changes_only_frozen_target_bytes` |
| R5 | ruamel load→dump renormalizes unchanged bytes | targeted substitution or prove byte-stable first |
| R6 | 18 profile `related:` edges dropped by re-running generator | hand-edit (authored remainders), regen only the 2 lockfiles |
| R7 | Baseline store tracked/under archive → breaks `test_archive_root_byte_identical` at M6 | untracked, never under `kitty-specs/` (C-COR-4) |
| R8 | Vacuous shrink-only guard passes trivially | self-mutation teeth assertion (bare-prose-ratchet shape) |
| R9 | Auth-2 pack hand-edit drifts from seed (regen script gone) | run `test_glossary_pack_parity` after every pack edit |
| R10 | Stale single-root baseline `3631531b…` → "stale baseline" mutation fires | derive guard baseline from four-root procedure |

## Progress

- [x] Phase 0 inputs (re-inventory + squad findings)
- [ ] Phase 0 `occurrence_map.yaml`
- [ ] Phase 1 tasks + 12 red-first ATDD tests
- [ ] Slice 4 / 5 / 6 implementation
- [ ] Consolidation, review squad, docs/changelog, draft PR
