# Tasks: Charter Authority Flip (retire-doctrine-term M1)

**Mission**: `charter-authority-flip-01M14RB3` | **Branch**: `feat/charter-authority-flip` | **change_mode**: `bulk_edit`
**Occurrence map**: [occurrence_map.yaml](./occurrence_map.yaml) (302 rows OC-01/02/40; polysemy keeps + B2 reconcile)

Single-stream mission; ATDD red-first; transition guard armed **last**. Glossary-first. Post-tasks squad findings folded (B1–B4, H1–H4, M1–M3, atomicity BLOCKER).

## Work Packages

| WP | Title | Slice | Depends on | Profile | Requirements |
|----|-------|-------|------------|---------|--------------|
| WP01 | Glossary parity + charter Canon + authority-3 rename + intra-context links | 4 | — | python-pedro | FR-001, FR-003 |
| WP02 | External referrer re-point (40) | 5 | WP01 | python-pedro | FR-002 |
| WP03 | CR-01 key cutover + answers migration + serializer | 6a | — | python-pedro | FR-004, FR-005 |
| WP04 | Shrink-only guard (armed last) + archive gate + closing audit | 6b | WP01, WP02, WP03 | reviewer-renata | FR-006, FR-007 |

**Authority count (H2, pinned):** parity is over the **three glossary authorities** (seed YAML, pack YAML, `docs/context/charter.md`). The **Charter Bundle** (`governance.*` key) is re-pointed by WP03/CR-01, not a glossary-parity participant.

## WP01 — Glossary parity + charter Canon + authority-3 rename + intra-context links

- **T001** [RED] `tests/architectural/test_glossary_authority_parity.py` — reuse the seed-driven join from `test_glossary_pack_parity.py`, extend to authority-3 (`docs/context/charter.md` tables). Assert: 3-authority term-set + definition + alias-by-`surface` + link closure; **(H1 anti-vacuity)** the governing `doctrine` surface is **ABSENT** and `charter` **present**; **(B2)** EXACTLY ONE `charter` surface exists. Fails now (charter.md absent, `doctrine` surface present).
- **T002** [RED] `tests/architectural/test_charter_owner_map_executed.py` — assert the M1 owner actions M1 ACTUALLY performs (glossary triad flip, Canon entry, key cutover) ran/verified-no-op with matching hashes. **(H4)** `context-state.json`/`synthesis-manifest.yaml`/`graph.yml` are **verify-no-op-or-defer**: assert unchanged (no M1 owner action), not "resynthesised".
- **T003** `git mv docs/context/doctrine.md docs/context/charter.md`; **(atomicity BLOCKER)** in the SAME step re-point the 3 intra-`docs/context/*.md` inline links path-token-only (`./doctrine.md#…`→`./charter.md#…`) in `orchestration.md:119,131,143`, `governance.md:95,107`, `configuration-project-structure.md:99`. **Preserve the `#doctrine-catalog` / `#procedure` heading anchors and the link TEXT** ("Doctrine Catalog"/"Procedure" = kept domain vocab) or the anchor check reds.
- **T004** Add the `### charter` Terminology-Canon entry in `docs/context/charter.md` (copy `docs/context/orchestration.md:538-546` table shape): ≥5 senses + **Pack Default Charter** row + "do-NOT" guards.
- **T005** Flip governing-term prose in `.kittify/glossaries/spec_kitty_core.yaml` + pack (hand-edit pack, keep seed↔pack byte-parity; run `test_glossary_pack_parity` after each edit). Keep domain surfaces `drg`/`doctrine reference graph`/`doctrine artifact`/`doctrine pack`.
- **T005a** **(B2 reconcile)** Retire `surface: doctrine` (seed:154/pack:165); fold its "body of governance artifacts" meaning into the single canonical `charter` term (seed:90/pack:100) and drop the "and doctrine" self-reference in charter's definition. Result: exactly one `charter` surface.
- **T006** [GREEN] T001/T002 pass; parity + link closure + `test_glossary_link_integrity` hold.

## WP02 — External referrer re-point (40)

- **T007** [RED] Assert (a) zero dangling `context/doctrine.md` referrers (`related_validator`), and **(paula HIGH)** (b) each referrer diff is EXACTLY the `context/doctrine.md`→`context/charter.md` path token, touching no other `doctrine`-bearing line (positive diff-shape / no-double-funding check).
- **T008** Hand-edit the 18 `docs/api/agent_profiles/*.md` `related:` frontmatter path tokens (authored remainders — NOT via generator).
- **T009** Hand-edit the remaining source referrer path tokens (2 ADRs, `docs/architecture/doctrine-kinds.md`, `docs/development/how-to/create-a-doctrine-artifact.md`, `docs/plans/**`, 6 `src/doctrine/**/README.md`, 2 tests) — path token only; **exclude the frozen `docs/reports/test-sanitation/**/raw/*.json` census snapshots (M2)**.
- **T010** Regenerate BOTH lockfiles `docs/development/3-2-page-inventory.yaml` + `docs/development/3-2-docs-retrieval-index.yaml` via `scripts/docs/inventory_lockfile.py` (never hand-edit; `INVENTORY-LOCKFILE-DRIFT` gate).
- **T011** [GREEN] `related_validator` + link integrity + docs freshness green; diff-shape check passes.

## WP03 — CR-01 cutover + migration

- **T012** [RED] `tests/charter/test_governance_key_compat.py` — `test_governance_doctrine_key_warns_and_maps` + `test_governance_charter_key_canonical`.
- **T013** [RED] `tests/charter/test_answers_migration.py` — the 5 migration/serializer tests.
- **T014** Dict-level warn-and-map in `load_governance_config` (`sync.py:262-263`) — warn once (`_catalog_miss` shape + `lru_cache` gate), prefer canonical, map legacy→charter, then validate.
- **T015** Rename field `GovernanceConfig.doctrine`→`.charter` (`schemas.py:209`, keep value class); move ALL THREE readers `resolver.py:845`, `org_pack_discovery.py:201`, **`src/specify_cli/cli/commands/charter/_status_collectors.py:175`** (B4 — cross-package); flip `.kittify/charter/charter.yaml:19` key.
- **T016** New `scripts/migrate_charter_interview_answers.py` (numeric-byte frozen strings; scope to selection-key bytes only — leave slug `doctrine-catfooding-2196`; preimage restore) + harden `interview.py:400-404` to a validating serializer; verify only `compiler.py:515-516` generate path runs.
- **T017** [GREEN] T012/T013 pass; ruff+mypy clean.

## WP04 — Guard (armed last) + archive gate + closing audit

- **T018** [RED] `tests/architectural/test_transition_guard_shrink_only.py` — reuse `test_bare_prose_corpus_ratchet.py` shape (per-path signature, shrink-or-equal, **self-mutation teeth**); baseline = M1 opening four-root fingerprint; store **untracked, never under `kitty-specs/`**.
- **T019** [RED] **(B3)** Author `tests/architectural/test_archive_root_byte_identical.py` — the four fixed exclusion roots byte-identical pre/post M1 (NFR-002). No pre-existing owner.
- **T020** Fix the stale `src/doctrine/glossary_packs/built-in/` exemption path in `tests/architectural/test_no_legacy_terminology.py:61,428`; do NOT arm the global `doctrine` forbidden-term (later wave).
- **T021** [GREEN] T018/T019 + `test_no_legacy_terminology` green; closing audit shows no M1-owned governing `doctrine` except CR-01 products (≤3) + control.

## Merge gate

Every Charter artifact owner action ran/verified no-op with matching hashes; 3-authority glossary parity holds (divergence rolls back all; exactly one `charter` surface); CR-01 ≤3 products + control; guard armed; four archive roots byte-identical; `ruff`+`mypy`+terminology guard green; 0 operator questions.
