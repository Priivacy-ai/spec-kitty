# Data Model: Pack-Metadata Manifest Unification

Entities and fields for the unified pack-metadata design (ADR 2026-08-16-1), revised after the post-plan squad. Two files per pack: an **authored** descriptor and a **generated** manifest.

## PackDescriptor  *(authored — `pack.yaml`; never machine-rewritten)*

| Field | Type | Notes |
|---|---|---|
| `pack_id` | ULID (26 chars) | Stable, **immutable**, **sole runtime identity** (mirrors `mission_id`). |
| `pack_version` | semver string | Author-managed **for the built-in pack** (authored here). **Scoped, not wholesale** (post-tasks paula-MF-3): fetched/org packs keep `pack_version` as generated provenance on `snapshot.py`'s output (it is a required key of `_has_recognisable_pack_manifest`). Consumers (`_doctrine_collect.py:81` `_resolve_pack_version`, `pack_assembler.py:390`) read **authored-when-present, else generated**. |
| `parent_pack` | ULID \| null | Edge only → parent `pack_id`. |
| `accompanies_doctrine_pack` | ULID \| null | Charter-pack → doctrine-pack pack-level binding (was per-activation `doctrine_pack_id`). |
| `name` | string | Human handle only. **No longer the identity key**; resolver disambiguates with no silent fallback. |

Lineage authority (two-key period): the live `extends:` (name-keyed) map remains the single resolution authority; `parent_pack` (id-keyed) is populated and resolved via a data-only `pack_id→resolvable-key` adapter feeding `org_extends.resolve_extends_order`. An unresolvable `parent_pack` (pre-backfill) **fails closed**, never a silent no-op. Retiring `extends:` in favor of `parent_pack` is deferred until `pack_id` backfill is universal.

## PackManifest  *(generated — `pack-manifest.yaml`; never hand-authored, NFR-004)*

| Field | Type | In hash / byte-diff? | Notes |
|---|---|---|---|
| `schema_version` | string | **yes** | Version-gates shape changes (DIR-018). |
| `generated_by` / `generated_at` | string | **NO** | Provenance only. **Excluded from `manifest_hash` and the byte-diff assertion** so re-runs are byte-identical (NFR-003). |
| `source_url` / `source_type` / `fetched_at` | string | yes (when present) | Genuine *generated* provenance for fetched packs; stays on the generated file. |
| `manifest_hash` | sha256 | (self) | Computed via `finalize_manifest`→`compute_manifest_hash` (`manifest.py:224/:205`) over the hashed set **minus** `generated_at/by`. Single hasher — no second implementation. |
| `constituents` | list[Constituent] | yes | Canonical enumerated inventory, sorted by `(kind, id)`. |
| `charter` | CharterProfile \| absent | yes | Optional; charter packs only. |

Derived (not stored): per-kind `artifact_counts` `{kind: int}` — computed by counting `constituents` per kind (Q1 compat view; transitional precedence = derive-when-present else stored fallback). NOT the dossier `{total,required,required_present}` counts, which are a separate domain (out of scope).

## Constituent  *(element of `PackManifest.constituents`)*

| Field | Type | Notes |
|---|---|---|
| `kind` | ArtifactKind (~14) | Widened from the charter manifest's 3-kind literal so built-in kinds pass the shared model. |
| `id` | string (URN or bare id) | Canonical artifact id within its kind. |
| `path` | string (POSIX) | Repo-relative path to the artifact source. |
| `content_hash` | sha256 | Over **LF-normalized** artifact bytes (cross-platform stable, DIR-001; trust substrate #2539). |
| `provenance_path` | string \| null | **Required for charter constituents** (relocated from `ManifestArtifactEntry.provenance_path`); null for non-charter packs. |

## CharterProfile  *(optional block on a charter pack's manifest — FULL field-set)*

Carries the **entire** `SynthesisManifest` charter-only contract so no working field is dropped (PP-M2):

| Field | Type | Notes |
|---|---|---|
| `mission_id` | ULID | Synthesizing mission. |
| `bundle_content_hash` | sha256 | Existing bundle hash. |
| `synthesizer_version` | string | Existing provenance. |
| `run_id` | string | Matches the staging dir. |
| `adapter_id` / `adapter_version` | string | Synthesizer adapter provenance. |
| `created_at` | string | Existing charter timestamp (provenance; treat like `generated_at` w.r.t. hashing). |
| `built_in_only` | bool | **Load-bearing** across `charter_runtime` freshness/preflight/lint — authoritative; must survive absorption. |

## Relationships

```
PackDescriptor(pack_id) ──parent_pack──▶ PackDescriptor(pack_id)      [resolved via id→key adapter → org_extends]
PackDescriptor(charter) ──accompanies_doctrine_pack──▶ PackDescriptor(doctrine pack)   [fail-closed on unknown]
PackDescriptor 1───1 PackManifest        (same pack root; authored vs generated)
PackManifest 1───N Constituent
PackManifest 0/1─── CharterProfile       (charter packs only)
```

## Migration inputs (read-only, not re-emitted)

- Legacy org `pack-manifest.yaml` `artifact_counts` (`snapshot.py:176/195`) → superseded by the per-kind derived view.
- Legacy `synthesis-manifest.yaml` (`manifest.py`) → becomes the charter pack's `pack-manifest.yaml` instance (full field-set on the `charter:` profile; readers pinned green).
- Packs keyed by config `name` (`src/doctrine/drg/org_pack_config.py:166`) → gain a `pack_id` (built-in first; Q2).
- `pack_version` previously on the generated file → relocated to the authored descriptor.
