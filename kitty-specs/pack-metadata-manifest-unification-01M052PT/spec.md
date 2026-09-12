# Mission Specification: Pack-Metadata Manifest Unification

**Mission Branch**: `feat/pack-metadata-manifest-unification`
**Created**: 2026-08-16
**Status**: Draft
**Input**: Unify pack metadata onto a single canonical manifest per ratified ADR `docs/adr/3.x/2026-08-16-1-pack-metadata-manifest-unification.md`. Keystone: #2467. Work packages: #3500 (core), #3501 (identity), #3502 (lineage), #3503 (split). Scope: the manifest-unification slice only — **not** #2467's compound-packs slice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One verifiable manifest for every pack (Priority: P1)

A pack author or the build/upgrade tooling produces a **single** manifest that enumerates exactly what a pack contains — every constituent artifact with a content hash — in the same schema for **every** pack type (built-in, org, fetched, charter). Today the same information lives in two incompatible formats (per-kind *counts* for org packs, *enumerated* artifacts for charter bundles) and the built-in reference pack that every other pack extends has no manifest at all.

**Why this priority**: This is the SSOT that everything else hangs on — identity, lineage, and verified distribution all key on a single canonical constituent record. Without it, the other stories have no schema to attach to.

**Independent Test**: Generate the manifest for each pack type and confirm each yields one `pack-manifest.yaml` in the unified schema whose `constituents[]` enumerates the pack's real artifacts; confirm the built-in pack — previously manifest-less — now has one enumerating its DRG nodes.

**Acceptance Scenarios**:

1. **Given** a built-in pack with per-kind `*.graph.yaml` nodes, **When** the manifest generator runs, **Then** a `pack-manifest.yaml` is produced enumerating every node as a `constituents[]` entry `{kind, id, path, content_hash}`.
2. **Given** an org pack that previously carried `artifact_counts`, **When** its manifest is regenerated, **Then** counts are no longer stored and any caller requesting counts receives them derived from `constituents[]` with identical values.
3. **Given** a charter bundle, **When** its manifest is produced, **Then** it uses the same schema plus an optional `charter:` profile block (`mission_id`, `bundle_content_hash`, `synthesizer_version`).

---

### User Story 2 - A pack carries stable identity and declared lineage (Priority: P2)

A pack has a **stable identity** (`pack_id`) and a **declared lineage** — its parent pack, and, for a charter pack, which doctrine pack it accompanies — instead of being keyed only by a config `name` with lineage scattered across per-activation records.

**Why this priority**: Identity and lineage make packs navigable and are the keys trust/verifiability hang on; they depend on the US1 schema but are independently valuable.

**Independent Test**: Give a pack a `parent_pack` edge and resolve its lineage order through the existing resolver; confirm a charter pack's `accompanies_doctrine_pack` points at its doctrine pack at the pack level (not only per-activation).

**Acceptance Scenarios**:

1. **Given** a pack without prior identity, **When** identity is minted, **Then** it carries a stable, immutable `pack_id`.
2. **Given** a pack declaring `parent_pack`, **When** lineage order is resolved, **Then** resolution is produced by the existing `org_extends.resolve_extends_order` (no new resolver), including its cycle detection.
3. **Given** a charter pack, **When** its `accompanies_doctrine_pack` is set, **Then** its binding to the doctrine pack is readable at the pack level.

---

### User Story 3 - Authored metadata is separate from generated constituents (Priority: P2)

Human-authored identity/lineage lives in files an author may edit (`pack.yaml` + `pack.md`); the enumerated constituents and hashes live in a **generated** manifest an author must never hand-edit — honoring the pack-layout contract.

**Why this priority**: Prevents the authored-vs-generated collision the pack-layout contract forbids; small but load-bearing for correctness of every regeneration.

**Independent Test**: Confirm authored fields (`pack_id`, `pack_version`, `parent_pack`, `accompanies_doctrine_pack`) resolve from `pack.yaml`, while `constituents[]`/hashes resolve from the generated `pack-manifest.yaml`, and regeneration never rewrites the authored files.

**Acceptance Scenarios**:

1. **Given** an authored `pack.yaml` and a generated `pack-manifest.yaml`, **When** the manifest is regenerated, **Then** `pack.yaml` and `pack.md` are left byte-unchanged.
2. **Given** a regeneration of an unchanged pack, **When** it runs twice, **Then** the generated manifest is byte-identical both times (deterministic).

### Edge Cases

- What happens when a `parent_pack` edge forms a cycle? → Surfaced by the existing `org_extends` cycle detection; no new detection logic.
- What happens when a pack has zero constituents? → A valid manifest with an empty `constituents[]` and a well-formed `manifest_hash`.
- What happens when a legacy pack still carries stored `artifact_counts`? → Treated as migration input only; the derived view supersedes it and stored counts are not re-emitted.
- What happens when `accompanies_doctrine_pack` names an unknown pack? → Fail-closed with a legible error (consistent with lineage-edge resolution), never a silent drop.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Single canonical pack-manifest schema (enumerated constituents) for all pack types | As tooling, I want one `pack-manifest.yaml` schema with `constituents:[{kind,id,path,content_hash}]` for built-in/org/fetched/charter packs so pack contents are described one way. | High | Open |
| FR-002 | Built-in pack manifest generator wired into build/upgrade | As tooling, I want the built-in pack's manifest generated from its per-kind `*.graph.yaml` nodes so the reference pack every pack extends has a manifest. | High | Open |
| FR-003 | Retire `artifact_counts` as stored state; expose derived counts | As a counts consumer, I want counts derived from `constituents[]` so `artifact_counts` need not be stored. | High | Open |
| FR-004 | Charter profile block on the unified schema | As the synthesizer, I want charter-only fields (`mission_id`, `bundle_content_hash`, `synthesizer_version`) in an optional `charter:` block so the charter bundle uses the same schema. | High | Open |
| FR-005 | Stable, immutable `pack_id` identity | As tooling, I want each pack to carry a stable `pack_id` (mirroring the `mission_id` ULID model) so packs are keyed by identity, not config `name`. | High | Open |
| FR-006 | Authored `parent_pack` + `accompanies_doctrine_pack` edges | As a pack author, I want to declare a parent pack and (for a charter pack) the doctrine pack it accompanies. | High | Open |
| FR-007 | Pack-level charter→doctrine binding | As a reader, I want a single pack-level `accompanies_doctrine_pack` pointer instead of relying on per-activation `doctrine_pack_id`. | Medium | Open |
| FR-008 | Two-file authored/generated split | As a pack author, I want authored identity/lineage in `pack.yaml`(+`pack.md`) and generated constituents/hashes in `pack-manifest.yaml`. | High | Open |
| FR-009 | Self-integrity + per-constituent hashing | As a verifier, I want a `manifest_hash` over the generated manifest and a `content_hash` per constituent so the manifest is tamper-evident. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Delegated lineage resolution | Lineage order is produced exclusively by `org_extends.resolve_extends_order`; **0** new resolver/traversal implementations added (verified by the no-parallel-resolver architectural test). | Correctness | High | Open |
| NFR-002 | Zero counts-consumer regressions | 100% of existing `artifact_counts` consumers return identical values via the derived view; **0** failing existing count-dependent tests. | Compatibility | High | Open |
| NFR-003 | Deterministic, idempotent generation | Regenerating a pack's manifest for an unchanged pack yields a byte-identical `constituents[]` and `manifest_hash` (re-run diff = **0 bytes**). | Reliability | High | Open |
| NFR-004 | No-author-edit generated file | The generated `pack-manifest.yaml` carries **0** hand-authored fields; regeneration leaves authored `pack.yaml`/`pack.md` byte-unchanged (verified by the pack-layout contract test). | Integrity | High | Open |
| NFR-005 | Zero charter-reader regressions | Absorbing `synthesis-manifest.yaml` into the `charter:` profile causes **0** regressions across its ~8 readers (freshness/preflight/lint/apply/provenance/versioning/charter_bundle + the two `m_3_2_0rc35_charter_*` migrations); `built_in_only` + `provenance_path` survive absorption. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Enumerated is canonical | `constituents[]` is the canonical inventory; `artifact_counts` must not remain stored state (derive only). | Technical | High | Open |
| C-002 | Lineage stores edges only | `parent_pack`/`accompanies_doctrine_pack` store edges only; resolution delegates to `org_extends` — no parallel resolver (enforced by the no-parallel-resolver arch ratchet; distinct from spec-local C-005). | Technical | High | Open |
| C-003 | Scope boundary | Manifest-unification slice only; #2467's compound-packs slice is out of scope for this mission. | Business | High | Open |
| C-004 | `pack_id` immutability | Once minted, a `pack_id` is immutable (mirrors `mission_id` immutability). | Technical | Medium | Open |
| C-005 | Authored/generated separation | Authored lineage/identity live only in `pack.yaml`; the generated manifest honors the pack-layout no-author-edit contract (`pack-layout.md:104`). | Technical | High | Open |

### Key Entities

- **Pack descriptor (`pack.yaml`, authored)**: `pack_id`, `pack_version`, `parent_pack`, `accompanies_doctrine_pack`, human metadata.
- **Pack manifest (`pack-manifest.yaml`, generated)**: `schema_version`, `generated_by`/`generated_at`, `manifest_hash`, `constituents[]`, optional `charter:` profile block.
- **Constituent entry**: `{kind, id, path, content_hash}` — one enumerated artifact of the pack.
- **Lineage edge**: `parent_pack` (pack→parent pack) and `accompanies_doctrine_pack` (charter pack→doctrine pack), resolved by `org_extends`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 4 pack types (built-in, org, fetched, charter) produce exactly one manifest in the unified schema; 0 packs remain on a counts-only format.
- **SC-002**: The built-in pack — previously manifest-less — has a generated manifest enumerating 100% of its DRG nodes as constituents.
- **SC-003**: A pack's parent and accompanied doctrine pack are resolvable from its manifest via the existing resolver, with 0 new resolver code paths.
- **SC-004**: Regenerating any unchanged pack's manifest is byte-stable (0-diff) across repeated runs.
- **SC-005**: 100% of existing counts consumers keep working (0 regressions) through the derived-count view.

### Delivery status (this slice)

- **SC-001**: emission is **built-in-pack-only** this slice — the unified schema is defined
  for all 4 pack types, but org/fetched/charter manifest *writers* are deferred to a future
  integration WP.
- **SC-002**: "100% of its DRG nodes" covers artifact **constituents that ship content**;
  graph-only / non-artifact kinds are intentionally excluded (no file, no `content_hash` to
  enumerate).
- **FR-007**: pack-level `accompanies_doctrine_pack` binding is **capability-only** this
  slice — a fail-closed resolver exists, but per-activation `doctrine_pack_id` remains the
  authoritative source until the integration WP wires the resolver to production callers.

## Assumptions

- **Q1 (counts-migration depth):** this mission ships the **derive-and-expose compat view** for `artifact_counts` (counts computed from `constituents[]`); full migration of every stored-counts *reader* to read constituents directly is a fast-follow. Operator may elect full in-mission reader migration at plan time.
- **Q2 (`pack_id` backfill breadth):** `pack_id` is minted for the **built-in pack first**; org/fetched pack backfill lands as identity coverage extends (WP-identity). Operator may elect full backfill at plan time.
- **ADR/doc dependency:** the ratifying ADR `2026-08-16-1` and the disposition doc currently live on PR 3480 (not yet on the mission's base); this spec references them by path and they land when that PR merges.
- **Trust adjacency:** the constituent + content-hash manifest is the substrate for the pack-trust/verified-distribution epic 2539; signing/verification is out of scope here but the schema is designed to carry it.

## Issue Traceability

This mission is the implementation vehicle for the **pack-manifest bullet of keystone #2467** (design bullet 1: "Design a pack-manifest schema at the pack-root tier"). It delivers, and its issue-matrix tracks:

- **#2467** — parent keystone; this mission delivers its pack-manifest bullet (the compound-packs bullet remains a separate slice, out of scope here per C-003).
- **#3500** — WP-core (unify schema + built-in manifest writer).
- **#3501** — WP-identity (`pack_id`).
- **#3502** — WP-lineage (`parent_pack` + `accompanies_doctrine_pack`).
- **#3503** — WP-split (authored vs generated files).

Context only (not delivered here): epic 2539 (trust/verified distribution — the schema carries its substrate), PR 3480 (the ratifying ADR + disposition docs).
