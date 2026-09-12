# Research: Charter Authority Flip (M1) — brownfield seam synthesis

Consolidated from a pre-plan brownfield research squad (3 profile-loaded scouts, opus). All findings cited `file:line`.

## Seam 1 — Glossary quartet parity (slice 4)

- **Four authorities**: `.kittify/glossaries/spec_kitty_core.yaml` (18 hits), `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml` (24 hits; regen script gone → hand-edit + byte-parity), `docs/context/doctrine.md`→`charter.md` (Markdown tables), Charter Bundle referrers.
- **Term ID = `surface` string**; schema `extra="forbid"` + lowercase-trim (`src/glossary/seed_schema.py:20,34,73`) → Canon disambiguation goes in Markdown.
- **Parity test**: extend `tests/architectural/test_glossary_pack_parity.py` (seed-driven every-key join, anti-vacuity) to auth 3; do NOT delete it.
- **Canon shape**: copy `### PRIMARY partition` table at `docs/context/orchestration.md:538-546`.
- Link-closure gate: `tests/doctrine/test_glossary_link_integrity.py` (double-hyphen anchors literal).
- **Polysemy**: keep `src/doctrine/` paths + `drg`/`doctrine reference graph`/`doctrine pack` domain terms; only governing-term sense retires.

## Seam 2 — CR-01 key + migration (slice 6)

- **Load seam**: `load_governance_config` `src/charter/sync.py:262-263` — dict-level warn-and-map before `model_validate` (silent alias fails SC-002).
- **Field**: `GovernanceConfig.doctrine`→`.charter` `src/charter/schemas.py:209` (keep value class `DoctrineSelectionConfig`).
- **3 readers**: `resolver.py:845`, `org_pack_discovery.py:201`, `_status_collectors.py:175`.
- **Warn precedent**: `src/charter/_catalog_miss.py:327-365`; legacy-key structural precedent `compiler.py:648-680`; warn-once via `lru_cache`, not filter.
- **Migration script new**: `scripts/migrate_charter_interview_answers.py`; writer to harden `src/charter/interview.py:400-404`; answers `.kittify/charter/interview/answers.yaml` (`_common.py:101`). Token-literal-free (numeric bytes); scope to governing-term bytes (slug `doctrine-catfooding-2196` is a proper noun — do not touch); prefer targeted substitution over ruamel round-trip; preimage restore.
- **charter generate**: `compiler.py:515-516` section-update (safe), never `:725` (clobbers governance).
- **Compat registry**: spec-artifact + guard-test, no runtime object; CR-01 budget 3 + control; `data-model.md:82-101`, `methodology.md:145-159`.

## Seam 3 — Referrers + transition guard (slice 5/6)

- **43 referrers** (72 raw − 4 roots): **18** `docs/api/agent_profiles/*.md` `related:` = authored remainders (hand-edit; `derive_related` at `frontmatter_backfill.py:244` won't re-emit); **2** `docs/development/3-2-*.yaml` lockfiles = generated (regen `scripts/docs/inventory_lockfile.py:213`; `INVENTORY-LOCKFILE-DRIFT` gate); ~23 source hand-edit. Close with `scripts/docs/related_validator.py`.
- **Guard**: reuse `tests/architectural/test_bare_prose_corpus_ratchet.py` (per-path signature, shrink-or-equal, **self-mutation teeth**). Precedent mission `doctrine-controlled-transition-gates` is a red herring (runtime lane gate).
- **Baseline store UNTRACKED, never under `kitty-specs/`** (`methodology.md:273` is stale; `:144`/`spec.md:61` authoritative). Baseline = M1 own opening four-root fingerprint (`d8a09ef1…`, not stale single-root `3631531b…`). M6 owns `scripts/audit_retired_term_zero.py` — do NOT pre-create.
- **Cross-ownership**: 43 referrers disjoint from 302 rows; re-point path token only.
