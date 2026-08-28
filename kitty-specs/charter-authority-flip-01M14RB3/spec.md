# Mission Specification: Charter Authority Flip (retire-doctrine-term M1)

**Mission Branch**: `feat/charter-authority-flip`
**Created**: 2026-08-28
**Status**: Draft
**Input**: Wave M1 of the `retire-doctrine-term-01M0JMK9` (#3664) program. Make the accepted ADR `2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md` effective in the Charter and glossary **authority graph only**: record the override/canon through the owning writers, cut over the `governance.doctrine` selection key to `governance.charter` with a warning-compat reader (CR-01), migrate charter interview answers, and arm a shrink-only transition guard. Product/code/path/historical removals are downstream waves (M2–M6) and are out of scope here.

This mission also binds the #3732 product-vocabulary decision: the old activation-side "charter pack" concept is named **Pack Default Charter** (a default that ships inside a Charter Pack) — explicitly **not** "Active Charter", which ADR `2026-08-22-2` §76 binds to *an individual activated governance artefact* ("never bundle state"). "doctrine pack" collapses into **Charter Pack** (already the ADR §74 offer-side definition).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Charter and glossary authority speak "charter" (Priority: P1)

A maintainer or agent reading the canonical governance authority (the glossary triad + the Charter Bundle) finds **charter** as the governing term, with a Terminology-Canon entry disambiguating charter's overloaded senses. No live *governing* use of "doctrine" survives in the M1-owned authority surfaces.

**Why this priority**: The ADR is inert until the authority graph it governs actually carries the canon. Every downstream wave (M2–M6) derives its map from this authority; a wrong or absent canon here propagates.

**Independent Test**: Diff the three glossary authorities and the Charter Bundle; assert the Terminology-Canon `charter` entry exists with ≥5 senses + "do-NOT-use" guards + the `Pack Default Charter` row, and that three-authority parity (term set + definitions + aliases keyed by term ID + link closure) holds.

**Acceptance Scenarios**:

1. **Given** the pre-M1 authority graph, **When** M1 curates the three glossary authorities and Charter Bundle, **Then** term set + definitions + aliases (keyed by term ID) and link closure are identical across all three authorities, and divergence in any one rolls back all three.
2. **Given** the retired `doctrine` term, **When** a reader consults the Terminology-Canon, **Then** a `charter` entry lists Charter Bundle / Charter Pack / the `src/charter/` package / the `spec-kitty charter` CLI group / Active-Inactive Charter artefact **and** `Pack Default Charter`, each with a "do-NOT-use-when" guard.
3. **Given** `docs/context/doctrine.md`, **When** M1 runs, **Then** it is renamed to `docs/context/charter.md` and all 43 referrers are re-pointed with link closure intact (no dangling links).

---

### User Story 2 - Selection-key cutover with a warning-compat reader (Priority: P1)

The governance selection key becomes `governance.charter`. A 3.x reader still accepts the legacy `governance.doctrine` key but emits a deprecation warning and maps it forward, so existing projects do not fail closed.

**Why this priority**: The key is load-bearing for charter resolution; a hard cutover with no compat reader would brick every project still on the old key.

**Independent Test**: Load a config carrying the legacy key → assert a warning is emitted and the value maps to `governance.charter`; load a config carrying the canonical key → assert no warning and canonical read.

**Acceptance Scenarios**:

1. **Given** a `charter.yaml` with `governance.doctrine`, **When** the 3.x reader loads it, **Then** it warns once and resolves the value as `governance.charter` (CR-01, compatibility budget ≤ 3 products + control record).
2. **Given** a `charter.yaml` with `governance.charter`, **When** the reader loads it, **Then** it resolves canonically with no warning.

---

### User Story 3 - Charter interview answers migrate without loss (Priority: P2)

Existing `interview/answers.yaml` files migrate to the new key vocabulary. Every answer, every unknown key, selected assets, and the template set are preserved; only the frozen target bytes change; a failed migration restores the pre-image.

**Why this priority**: Silent loss of a user's charter answers is a data-integrity violation; migration must be total and reversible.

**Independent Test**: Run the migration over a fixture with unknown keys + selected assets; assert all answers/unknown keys/assets/template-set survive, only frozen bytes changed, and an injected failure restores the pre-image byte-for-byte.

**Acceptance Scenarios**:

1. **Given** an `answers.yaml` with unknown keys and all answers populated, **When** migration runs, **Then** every unknown key and answer is preserved and only the frozen target bytes differ.
2. **Given** a mid-migration failure, **When** it aborts, **Then** the pre-image is restored from backup.
3. **Given** an extended answers set, **When** the hardened serializer round-trips it, **Then** deletion / default-reset / empty `selected_tactics` mutations are rejected.

---

### User Story 4 - Shrink-only transition guard armed (Priority: P2)

A transition guard prevents the authority graph from regressing — the retired governing term cannot be re-introduced without an explicit, auditable widening. Its baseline store is untracked (never inside an archive root), so M6's later deletion never shows as a `D` under `kitty-specs/`.

**Why this priority**: Without a guard, a later edit silently re-introduces "doctrine" as a governing term and the extinction invariant rots.

**Independent Test**: `test_transition_guard_shrink_only` — a shrink (fewer governing-term occurrences) passes; a widen fails.

**Acceptance Scenarios**:

1. **Given** the armed guard, **When** a change reduces or holds the governing-term footprint, **Then** it passes.
2. **Given** the armed guard, **When** a change widens the governing-term footprint, **Then** it fails.

### Edge Cases

- A referrer of `docs/context/doctrine.md` lives in generated `docs/api/**` — it must be re-pointed via its generator, not hand-edited, or the next generation reverts it.
- A glossary alias exists in one authority but not the others — parity must fail rather than silently converge.
- The legacy `governance.doctrine` key and the canonical `governance.charter` key are both present — the reader must prefer canonical and warn on the legacy.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Three-authority glossary parity | As a maintainer, I want the glossary triad + Charter Bundle to carry charter as the governing term under one parity transaction (term set + defs + aliases by term ID + link closure) so authority never diverges. | High | Open |
| FR-002 | Rename `doctrine.md` + re-point 43 referrers | As a reader, I want `docs/context/doctrine.md` renamed to `charter.md` with every referrer re-pointed (generated `docs/api/**` via generators) so no link dangles. | High | Open |
| FR-003 | `charter` Terminology-Canon entry | As an agent, I want a canon entry listing ≥5 charter senses + `Pack Default Charter`, each with a "do-NOT-use" guard, so the retired term's ambiguity is disambiguated. | High | Open |
| FR-004 | `governance.doctrine` → `governance.charter` cutover (CR-01) | As an existing project, I want the legacy key still read with a deprecation warning and mapped forward (budget ≤3) so I do not fail closed. | High | Open |
| FR-005 | Charter interview answers migration | As a user, I want my `answers.yaml` migrated with zero answer/unknown-key loss, only frozen bytes changed, and pre-image restore on failure. | Medium | Open |
| FR-006 | Arm shrink-only transition guard | As a maintainer, I want a guard (untracked baseline store) that rejects re-widening the retired governing term. | Medium | Open |
| FR-007 | Closing audit: no M1-owned governing `doctrine` | As the program, I want zero M1-owned governing-term occurrence at close except CR-01 products (≤3) + control, with later-wave rows carried forward and listed. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero operator questions | M1 raises 0 local design questions (§3.1 dry-run confirmed zero). | Process | High | Open |
| NFR-002 | Archive gate byte-identical | The four fixed exclusion roots (`kitty-specs/`, mission-state quarantine, `kitty-ops/`, `.kittify/missions/`) are byte-identical pre/post M1 (`test_archive_root_byte_identical`). | Integrity | High | Open |
| NFR-003 | Clean static analysis | All new/changed code passes `ruff` + `mypy` with zero issues; `tests/architectural/test_no_legacy_terminology.py` green. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | `bulk_edit` change mode | `occurrence_map.yaml` classifies all 302 M1 occurrences (OC-01 221 / OC-02 80 / OC-40 1) across the canonical 8 categories; content and path both fixed. | Technical | High | Open |
| C-002 | Operator override recorded | The Charter's user-customization / historical-evidence protections are overridden for this program per ADR `2026-08-22-2`; M1 records the override through the owning writers. | Governance | High | Open |
| C-003 | `Pack Default Charter` naming | The pack-shipped default is named `Pack Default Charter`, never `Active Charter` (ADR §76 binds that to an individual activated artefact). Per #3732 resolution. | Terminology | High | Open |
| C-004 | Wave scope boundary | M1 touches the Charter + glossary authority only. `src/doctrine/**` code + paths, historical artifacts, and CLI/tracker surfaces are M2–M6. | Scope | High | Open |

### Key Entities

- **Charter Bundle**: the per-project materialised governance file set under `.kittify/charter/` (ADR §73).
- **Charter Pack**: the offer-side versioned distributable catalogue (ADR §74) — the term "doctrine pack" collapses into this.
- **Active / Inactive Charter artefact**: an individual governance artefact's activation state (ADR §76–77) — "never bundle state".
- **Pack Default Charter** *(new, M1)*: the default charter that ships inside a Charter Pack (formerly the informal "charter pack"). One new Terminology-Canon row.
- **Glossary authority triad** (parity is over these THREE glossary authorities; the Charter Bundle `governance.*` key is re-pointed by CR-01, not a parity participant — post-tasks squad H2): `.kittify/glossaries/spec_kitty_core.yaml`, `packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml`, and the Charter Bundle glossary referrers — kept in parity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Three-authority glossary parity holds — term set + definitions + aliases (by term ID) + link closure identical across all three authorities; divergence rolls back all three. (`test_glossary_authority_parity`, `test_charter_owner_map_executed`)
- **SC-002**: `governance.charter` reads canonically with no warning; the legacy `governance.doctrine` key warns once and maps forward. (`test_governance_doctrine_key_warns_and_maps`, `test_governance_charter_key_canonical`)
- **SC-003**: Interview-answers migration preserves all answers, unknown keys, selected assets, and template set; changes only frozen target bytes; restores the pre-image on failure; the serializer round-trips extended answers and rejects deletion/default-reset/empty-`selected_tactics` mutations. (`test_answers_migration_preserves_unknown_keys_and_all_answers`, `test_answers_migration_preserves_selected_assets_and_template_set`, `test_answers_migration_changes_only_frozen_target_bytes`, `test_answers_migration_failure_restores_preimage`, `test_interview_serializer_round_trips_extended_answers`)
- **SC-004**: The shrink-only transition guard is armed with an untracked baseline store and rejects widening; the four archive roots are byte-identical. (`test_transition_guard_shrink_only`, `test_archive_root_byte_identical`)
