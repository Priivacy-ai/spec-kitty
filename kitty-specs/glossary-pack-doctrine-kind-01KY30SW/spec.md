# Mission Specification: Glossary Pack Doctrine Kind

**Mission Branch**: `glossary-pack-doctrine-kind-01KY30SW`
**Created**: 2026-07-21
**Status**: Draft
**Input**: Mission A (keystone) of the Glossary Doctrine Overhaul program — build `GLOSSARY_PACK` as a first-order, charter-activatable doctrine ArtifactKind and ship the canonical terms as a built-in pack.

> **Program context.** This is Mission **A** (the keystone) of the four-mission Glossary
> Doctrine Overhaul program (A → D → B → C). Grounding: ADR
> [`docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md`](../../docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md)
> and program plan
> [`docs/plans/glossary-doctrine-overhaul-program.md`](../../docs/plans/glossary-doctrine-overhaul-program.md).
> Tracks issue #1418. Mission A builds the kind and migrates the terms; it deliberately does
> **not** wire enforcement (Mission B) or retire the runtime glossary (Mission C).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canonical terminology ships as a first-order doctrine artefact (Priority: P1)

Spec Kitty's canonical terminology currently lives in a runtime seed file
(`.kittify/glossaries/spec_kitty_core.yaml`) consumed by a dynamic pipeline. A doctrine
maintainer needs that terminology promoted to a **first-order doctrine artefact** — a
distributable, activatable, DRG-addressable `GLOSSARY_PACK` — so it composes with the rest of
the doctrine system exactly like directives and agent profiles do.

**Why this priority**: This is the keystone. Every downstream mission (executable enforcement,
runtime retirement) builds against the new kind; nothing else can start until it exists and
loads.

**Independent Test**: Ship the built-in `spec-kitty-core` glossary pack, run
`spec-kitty doctor doctrine --json`, and confirm the pack appears as a loaded, healthy DRG node
carrying its migrated terms — with the runtime glossary untouched.

**Acceptance Scenarios**:

1. **Given** the built-in `spec-kitty-core` glossary pack is shipped, **When** the doctrine
   system loads, **Then** `spec-kitty doctor doctrine --json` reports it as a loaded, healthy
   `glossary_pack` node.
2. **Given** the pack is resolved, **When** its DRG URN is inspected, **Then** it is
   `glossary_pack:<id>` (underscore) and the hyphenated `glossary-pack:` form is rejected.
3. **Given** the 104 canonical terms in the seed, **When** they are migrated into the pack,
   **Then** every term's surface, definition, confidence, and status is preserved with zero loss.

---

### User Story 2 - The kind is charter-activatable and active by default (Priority: P1)

The charter activation system must treat `GLOSSARY_PACK` as a first-class, charter-activatable
kind — one that participates in activation, cascade, and deactivation generically — and the
built-in `spec-kitty-core` pack must be **active by default** so terminology governance ships
on out of the box (operator decision, 2026-07-21).

**Why this priority**: Without activation wiring the pack loads but never reaches charter
resolution; without default activation, consumer projects silently lose the terminology
governance they have today.

**Independent Test**: With no manual activation steps, confirm the built-in glossary pack
resolves in the compiled charter reference set, and that
`charter activate/deactivate glossary-pack spec-kitty-core --cascade all` operate through the
generic DRG edges (not per-kind special-casing).

**Acceptance Scenarios**:

1. **Given** a freshly synchronised charter, **When** activation resolves, **Then** the built-in
   `spec-kitty-core` glossary pack is active without any manual `charter activate` step.
2. **Given** the operator token `glossary-pack`, **When** it is normalised at an input boundary,
   **Then** it maps to the canonical kind `glossary_pack`.
3. **Given** the three mirrored kind-lists, **When** the drift-guard runs, **Then** all three
   include `GLOSSARY_PACK` and the guard passes (they moved in lockstep).

---

### User Story 3 - Pack schema carries the enforcement fields for Mission B (Priority: P2)

The pack's term schema must expose `aliases`, `banned_synonyms`, and `synonyms_to_avoid` fields
so the later enforcement mission (B) can consume them without a second schema change. In Mission
A these fields exist and round-trip, but are not required to be populated and are not consumed by
any gate.

**Why this priority**: Getting the schema shape right now avoids a breaking schema revision in
Mission B; it is schema-forward-compatibility, not behaviour.

**Independent Test**: Author a pack term with `aliases` / `banned_synonyms` / `synonyms_to_avoid`
populated, load it, and confirm the values round-trip through the repository model unchanged.

**Acceptance Scenarios**:

1. **Given** a pack term declaring `aliases` and `banned_synonyms`, **When** the pack is loaded,
   **Then** the loaded model exposes those fields unchanged.
2. **Given** a pack term omitting the enforcement fields, **When** the pack is loaded, **Then**
   the term loads successfully with empty/defaulted enforcement fields (fields are optional in A).

### Edge Cases

- **Malformed pack file** (invalid YAML, missing required term fields) → the pack is reported
  **unhealthy** by `doctor doctrine`; a pack with an invalid member is never reported healthy.
- **Hyphenated URN** `glossary-pack:<id>` → rejected by the DRG URN regex / `prefix == kind.value`
  assertion; only the underscore form is valid on the wire.
- **Silent-invisibility trap** — a pack that loads from disk but whose node is not emitted by the
  extractor (or ships without a `*.graph.yaml` fragment) → the "resolves as a loaded node" guard
  **fails**, so the defect cannot ship green.
- **Duplicate term surface** within a single pack → validation error at load.
- **Kind misclassification** — if `GLOSSARY_PACK` were placed in the `{template, asset}`
  non-augmentation-eligible set, charter activation would silently exclude it → guarded by an
  explicit membership assertion.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | GLOSSARY_PACK is a first-order ArtifactKind | As a doctrine maintainer, I want `GLOSSARY_PACK` added to `ArtifactKind` (member, plural, glob) so the glossary is a first-order artefact. | High | Open |
| FR-002 | Charter-activatable classification | As the charter system, I want `GLOSSARY_PACK` in the 8-kind charter-activatable universe (not the `{template, asset}` exclusion set) so it can be activated. | High | Open |
| FR-003 | DRG node + URN | As the DRG, I want a `NodeKind.GLOSSARY_PACK` addressable as `glossary_pack:<id>` (underscore) so packs are graph-addressable. | High | Open |
| FR-004 | Glossary-pack repository | As the doctrine service, I want a `src/doctrine/glossary_packs/` repository that loads `*.glossary-pack.yaml` files (via `BaseDoctrineRepository`) exposed as `DoctrineService.glossary_packs` (plural == dir == accessor). | High | Open |
| FR-005 | Pack + term schema | As a pack author, I want a pack aggregate whose terms carry surface, definition, `confidence` (a **float**), status, `see_also`, `introduced_in_mission`, `synonyms_to_avoid` (every seed field, for zero-loss migration) **plus** optional `aliases`, `banned_synonyms` (Mission B). | High | Open |
| FR-006 | Built-in spec-kitty-core pack + term migration | As a maintainer, I want a built-in `spec-kitty-core` pack carrying the 104 canonical terms migrated from `spec_kitty_core.yaml` with zero loss. | High | Open |
| FR-007 | Default activation | As a consumer project, I want the built-in `spec-kitty-core` glossary pack charter-activated by default (per-pack via `activated_glossary_packs`). | High | Open |
| FR-008 | Mirrored kind-lists updated in lockstep | As the pack/activation system, I want `GLOSSARY_PACK` added to all three mirrored kind-lists so the drift-guard passes. | High | Open |
| FR-009 | Activation, cascade, deactivation wiring | As the charter system, I want glossary-pack activation/cascade/deactivation handled through generic DRG edges + `charter/drg.py` maps. | High | Open |
| FR-010 | Operator-token normalisation | As an input boundary, I want `from_operator_token("glossary-pack")` to normalise to `glossary_pack`. | Medium | Open |
| FR-011 | Extractor emission + graph fragment | As the DRG loader, I want the extractor to emit glossary-pack nodes and a **generated** `*.graph.yaml` fragment shipped at the doctrine **package root** (where `load_built_in_graph` globs non-recursively) so the built-in pack resolves as a loaded node. | High | Open |
| FR-012 | Doctor reporting | As a maintainer, I want `spec-kitty doctor doctrine --json` to report glossary-pack counts and health (invalid packs not reported healthy). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | URN spelling correctness | A regression test asserts the underscore URN `glossary_pack:` is accepted and the hyphenated `glossary-pack:` is rejected by the DRG regex + `prefix == kind.value` assertion. | Correctness | High | Open |
| NFR-002 | Migration fidelity (standing parity) | A **standing** parity test (live until Mission C deletes the seed) asserts the pack has all 104 terms and every term matches the seed across the **full key-set** — `surface`, `definition`, `confidence` (a **float**), `status`, `see_also`, `introduced_in_mission`, `synonyms_to_avoid` — so no field is silently dropped. Not a one-shot migration snapshot. | Data integrity | High | Open |
| NFR-003 | Non-vacuous resolution guard | A "resolves as a loaded node" test proves the built-in pack reaches charter resolution (loading + extractor emission + graph fragment) and fails if any link is broken (fakeable-failure guard). | Reliability | High | Open |
| NFR-004 | Quality gates | New code passes `ruff` + `mypy --strict` with zero warnings, cyclomatic complexity ≤ 15, and ≥ 90% coverage for new branches/helpers. | Maintainability | High | Open |
| NFR-005 | Doctor performance | `spec-kitty doctor doctrine --json` completes in < 2 s on this repository with the built-in pack loaded. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Copy `directive` wiring, not `asset` | `GLOSSARY_PACK` follows the `directive` kind's activatable wiring; it MUST NOT be added to `_NON_AUGMENTATION_ELIGIBLE_KINDS` (`{template, asset}`). | Technical | High | Open |
| C-002 | No seeding into the runtime glossary | The #1418-proposed `pack_seed_loader.py` ACL is dropped. Mission A introduces **no** new coupling from the pack into `src/glossary/`. | Technical | High | Open |
| C-003 | Do not retire the runtime or repoint the casing gate | `src/glossary/`, the seed `spec_kitty_core.yaml`, and `test_glossary_canonical_terms.py` remain unchanged and authoritative in A (retirement = Mission C, gate repoint = Mission B). | Technical | High | Open |
| C-004 | No enforcement wiring in A | `aliases`/`banned_synonyms`/`synonyms_to_avoid` are present and round-trip but are not populated-as-required and not consumed by any gate; enforcement is Mission B. | Scope | High | Open |
| C-005 | Lockstep kind-lists | The three mirrored kind-lists (`pack_context._BUILTIN_ARTIFACT_KINDS`, `activations._ALLOWED_KINDS`, `org_pack_loader._ORG_DRG_CANONICAL_KINDS`) MUST be updated together; the drift-guard is authoritative. | Technical | High | Open |
| C-006 | Charter discipline | ATDD red-first per WP; canonical doctrine template/loader chain (no improvised paths); terminology canon; `__all__` convention for any touched `src/charter/` or `src/kernel/` module. | Process | High | Open |

### Key Entities

- **Glossary Pack**: the aggregate root — a built-in/org/project-provenanced collection of terms,
  identified by a pack id, distributed as a `*.glossary-pack.yaml` file, addressable as a DRG
  node `glossary_pack:<id>`.
- **Glossary Term**: an entity within a pack. Carries **every** seed field so migration is truly
  zero-loss: `surface`, `definition`, `confidence` (**float**), `status`, `see_also`,
  `introduced_in_mission`, `synonyms_to_avoid`, plus the (Mission-B) enforcement fields `aliases`
  and `banned_synonyms`.
- **ArtifactKind.GLOSSARY_PACK**: the new first-order, charter-activatable kind.
- **DRG glossary-pack node**: `NodeKind.GLOSSARY_PACK`, URN `glossary_pack:<id>`, reachable
  through the charter activation ledger (`activated_glossary_packs`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `spec-kitty doctor doctrine --json` lists the built-in `spec-kitty-core` glossary
  pack as a **loaded, healthy** node — and reports an unhealthy status when a member pack is
  invalid.
- **SC-002**: **100%** of the 104 canonical terms are present in the built-in pack with
  definitions preserved (zero loss versus the seed).
- **SC-003**: The built-in glossary pack is **active by default** — it appears in the compiled
  charter reference set with **no** manual activation step.
- **SC-004**: **Zero regressions** — all pre-existing glossary, doctrine, and architectural tests
  (including the runtime-glossary suite and `test_glossary_canonical_terms.py`) remain green,
  proving the runtime and the casing gate are untouched.
- **SC-005**: The kind-list drift-guard and the URN-spelling regression both pass, and the
  non-vacuous "resolves as a loaded node" guard fails when its emission/graph-fragment link is
  broken.
