# Tasks: Pack-Metadata Manifest Unification

**Mission**: `pack-metadata-manifest-unification-01M052PT` | **Branch**: `feat/pack-metadata-manifest-unification`
**Plan**: [plan.md](./plan.md) · **Data model**: [data-model.md](./data-model.md) · **ADR**: `docs/adr/3.x/2026-08-16-1`

Four work packages mapping 1:1 to the IC concerns and the filed GitHub WPs. Subtask rows are event-sourced references (record via `spec-kitty agent tasks mark-status`, not checkboxes).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Unified `PackManifest` schema model + reader + widened `Constituent.kind` | WP01 | |
| T002 | Charter profile absorption: full SynthesisManifest field-set + `provenance_path` on Constituent | WP01 | |
| T003 | Pin the charter-manifest reader surface green (no charter-reader regressions) | WP01 | |
| T004 | Built-in manifest generator (emits ONLY `pack-manifest.yaml`; reserves `pack.yaml` path) | WP01 | |
| T005 | Deterministic generation (exclude `generated_at/by` from hash+diff; `(kind,id)` sort; LF `content_hash`) | WP01 | |
| T006 | Retire stored per-kind `artifact_counts`; per-kind derived view + transitional precedence | WP01 | |
| T007 | Pin real pack-counts readers green | WP01 | |
| T008 | `PackDescriptor` model: `pack_id` + `parent_pack` + `accompanies_doctrine_pack` fields | WP02 | |
| T009 | Mint + idempotent-backfill built-in `pack_id`; DRG `org_pack_config` key; no silent fallback | WP02 | |
| T010 | Confirm DRG shared-package-boundary arch tests tolerate the change | WP02 | |
| T011 | `pack_id → resolvable-key` adapter feeding `org_extends.resolve_extends_order` (no 2nd walker) | WP03 | |
| T012 | Fail-closed on unresolvable `parent_pack` / unknown `accompanies_doctrine_pack` | WP03 | [P] |
| T013 | No-parallel-resolver arch ratchet (AST import/call scan) | WP03 | [P] |
| T014 | Authored `pack.yaml`/`pack.md` for the built-in pack (identity + lineage + human doc) | WP04 | |
| T015 | Relocate `pack_version` to authored; stop generator emitting it; switch consumers | WP04 | |
| T016 | No-author-edit contract test (regen leaves `pack.yaml`/`pack.md` byte-unchanged) | WP04 | [P] |

## WP01 — Pack-core: unified schema, charter absorption, built-in writer, counts *(GitHub #3500)*

- **Goal**: land the single canonical `pack-manifest` schema, absorb the charter manifest as a profile without dropping its contract, generate the built-in pack's manifest, and retire stored per-kind `artifact_counts` for a derived view. This is the MVP vertical slice (SC-001/SC-002).
- **Priority**: P1 · **Independent test**: generate each pack type's manifest and confirm one unified `pack-manifest.yaml` with enumerated `constituents[]`; built-in manifest enumerates its DRG nodes; re-run is byte-identical; charter readers stay green; counts derive per-kind.
- **Subtasks**: T001, T002, T003, T004, T005, T006, T007
- **Dependencies**: none
- **Prompt**: [tasks/WP01-pack-core-schema-writer-counts.md](./tasks/WP01-pack-core-schema-writer-counts.md) (~230 lines)

## WP02 — Pack identity: stable `pack_id` *(GitHub #3501)*

- **Goal**: mint a stable, immutable ULID `pack_id` as the sole runtime identity (DRG `org_pack_config`), with `parent_pack`/`accompanies_doctrine_pack` edge fields on the descriptor; built-in first (Q2).
- **Priority**: P2 · **Independent test**: built-in pack carries a stable `pack_id`; backfill idempotent; resolver disambiguates with no silent fallback; DRG arch tests green.
- **Subtasks**: T008, T009, T010
- **Dependencies**: WP01
- **Prompt**: [tasks/WP02-pack-identity.md](./tasks/WP02-pack-identity.md) (~150 lines)

## WP03 — Pack lineage: delegated resolution *(GitHub #3502)*

- **Goal**: resolve `parent_pack` order via a data-only id→key adapter into `org_extends` (no second walker); fail-closed on unresolvable edges; pin the no-parallel-resolver ratchet.
- **Priority**: P2 · **Independent test**: a `parent_pack` edge resolves through `org_extends` with 0 new resolvers; an unresolvable edge fails closed; the arch ratchet fails on an injected second walker.
- **Subtasks**: T011, T012, T013
- **Dependencies**: WP01, WP02 · **Parallel with WP04 after WP02.**
- **Prompt**: [tasks/WP03-pack-lineage.md](./tasks/WP03-pack-lineage.md) (~160 lines)

## WP04 — Authored/generated split *(GitHub #3503)*

- **Goal**: author `pack.yaml`/`pack.md`; relocate `pack_version` off the generated file to the authored descriptor (switch consumers); pin the no-author-edit contract.
- **Priority**: P2 · **Independent test**: authored fields resolve from `pack.yaml`; regen leaves `pack.yaml`/`pack.md` byte-unchanged; `pack_version` consumers read the authored descriptor.
- **Subtasks**: T014, T015, T016
- **Dependencies**: WP01, WP02 · **Parallel with WP03 after WP02.**
- **Prompt**: [tasks/WP04-authored-generated-split.md](./tasks/WP04-authored-generated-split.md) (~160 lines)

## Dependency graph & lanes

```
WP01 (core) ── WP02 (identity) ─┬─ WP03 (lineage)   [parallel]
                                └─ WP04 (split)      [parallel]
```
MVP = **WP01**. After WP02 approves, WP03 and WP04 run in parallel. Do **not** rebase the planning branch after `finalize-tasks` (coord-divergence footgun).
