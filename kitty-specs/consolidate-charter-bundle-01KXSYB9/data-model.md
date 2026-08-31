# Data Model: Consolidate the Compiled Charter Bundle

The authoritative structured shape of `charter.yaml`, the manifest v2, and the **three landmines + write-discipline that must be resolved before any WP cuts code**.

## Entity: `charter.yaml` (the project charter)

Git-**tracked**, authorable, pack-shaped. Top-level keys (⚠ activation keys are **FLAT at root**, matching `default.yaml` — NOT nested under an `activation:` section — so `pack_context._read_activated_*` and the pack overlay read them unchanged; see paula BLOCKER-1):

| Key(s) | Provenance | Source model / shape |
|--------|-----------|----------------------|
| `schema_version` | authored constant | `"2.0.0"` (charter.yaml content schema — distinct from the manifest `SCHEMA_VERSION` and from `metadata.bundle_schema_version`) |
| `governance` | **AUTHORED** | verbatim `GovernanceConfig` body (`src/charter/schemas.py:124`): `testing/quality/commits/performance/branch_strategy/doctrine{selected_*,available_tools,template_set,authority_paths,governance_references}/activations[]/enforcement{}` |
| `directives` | **AUTHORED** | `DirectivesConfig` (`schemas.py:166`): `[{id,title,description,severity,references[]}]` |
| `catalog` | **DERIVED** (committed projection) | `references.yaml` body: `mission, template_set, languages[], references[]{id,kind,title,summary,source_path,local_path}` — kept honest by catalog↔activation parity (`consistency_check.py`) + freshness |
| `activated_kinds`, `mission_type_activations`, `activated_directives`, `activated_tactics`, `activated_styleguides`, `activated_toolguides`, `activated_paradigms`, `activated_procedures`, `activated_agent_profiles`, `activated_mission_step_contracts` | **AUTHORED** | **FLAT root keys**, identical shape/vocabulary to `src/charter/packs/default.yaml:5-38`; read by `pack_context._read_activated_*` / `_read_list_key` (`pack_context.py:239-256`) and written by `activation_engine.commit_plan` (`activation_engine.py:359`) — both operate on flat root keys today. `default.yaml` supplies the **absent-key fallback/seed** (via `merge_defaults` / `load_default_pack_activation_ids`), NOT a live per-artifact tiered activation merge (see INV-8). |
| `overrides` | **AUTHORED** | project-level doctrine overrides (schema designed to be forward-compatible with the tracked local-override mechanism; the mechanism itself is out of scope / C-008) |
| `metadata` | provenance | `{generated_at, bundle_schema_version: 2}` — KEEP `bundle_schema_version` (`versioning.py:176` reads it). **RETIRE** `charter_hash`, `extraction_mode`, `sections_parsed` (Landmine 2) |

**Model**: a new `CharterYaml` pydantic model in `src/charter/schemas.py` that nests the existing `GovernanceConfig` / `DirectivesConfig` under the `governance`/`directives` keys, with the activation lists as flat root fields (validation inherited, not re-authored).

**Filename constant**: introduce ONE shared `charter.yaml` filename constant consumed by `bundle.py`, `sync.py`, `compiler.py`, `consistency_check.py`, and the migration. Today the four bundle filenames are duplicated across two constant sets (`bundle.py:36-51` Path-form + `sync.py:43-44` str-form) — unify, do not re-scatter (S1192 pre-emption).

## Entity: `.kittify/config.yaml` (after relocation)
Retains **non-doctrine** config (`agents:`, tooling) **plus a one-line pointer to the active charter**:
```yaml
charter: .kittify/charter/charter.yaml   # single-line indirection — the resolver reads this to locate charter.yaml
```
The `activated_*` keys are removed (relocated to `charter.yaml`'s flat root activation keys). The `charter:` pointer is the ONLY charter-related key remaining in `config.yaml`. Note (paula MINOR-1): `org_packs` (pack roots) also stay in `config.yaml` — `PackContext.from_config` becomes a **two-file read** (config for the `charter:` pointer + `org_packs`; charter.yaml for activation). `_load_config`'s absent→`{}` permissive branch must distinguish "config present with pointer, charter.yaml missing" (raise, INV-5) from "no project config at all" (default-pack fallback).

**Indirection rationale (operator, 2026-07-18)**: keeping a single `charter:` pointer in `config.yaml` (rather than a fixed path) means:
- the resolver finds `charter.yaml` deterministically via config;
- a charter **swap** (experimentation, local redirect, cross-project / shared charter) is a one-line change in `config.yaml`, not a rewrite of the big charter file;
- multi-user repositories avoid merge conflicts — the churny activation/governance edits live in `charter.yaml` (or a per-user/redirected charter), while `config.yaml` stays stable except for the deliberate one-line swap.

The pointer MAY resolve to a non-default path (a sibling charter, a shared/cross-project charter). Resolution is fail-loud: a `charter:` pointing at a missing/unreadable file raises (C-003), never falls back to a legacy file.

## Entity: `charter.md` (curated companion)
Git-tracked, hand-authored rationale prose. **Never** a resolving input; **never** written by a generate/compile path. Consumed only for display (bootstrap policy summary, critical-section bodies, section anchors).

## Entity: `CharterBundleManifest` v2 (`src/charter/bundle.py`)
| Field | v1 | v2 |
|-------|----|----|
| `SCHEMA_VERSION` | `"1.0.0"` | `"2.0.0"` (single bump) |
| `tracked_files` | `[charter.md]` | `[charter.md, charter.yaml]` |
| `derived_files` / `derivation_sources` | the triad, sourced from charter.md | **`[]` / `{}`** — nothing in the charter *bundle* is generated-and-gitignored anymore (charter.yaml is tracked/authored) |
| `content_hash_files` (**NEW distinct field**) | — (was the separate `BUNDLE_CONTENT_HASH_FILES` tuple) | `[charter.yaml]` — the content-hash input set, a field distinct from `derived_files` so `_validate`'s tracked∩derived=∅ rule holds untouched |
| `BUNDLE_CONTENT_HASH_FILES` | 4 files (gov/dir/references/meta) | `("charter.yaml",)` (feeds `content_hash_files`) |
| `gitignore_required_entries` | the triad | (removed; charter.yaml tracked) |

---

## ⚠ LANDMINE 1 — Manifest tracked-vs-derived + git-class (RESOLVED)

**Problem**: `CharterBundleManifest._validate` (`bundle.py:83-89`) forbids a path being both `tracked` and `derived`, and every `derivation_sources` value must be a `tracked` file. After inversion `charter.yaml` is authoritative/authorable → must be git-**tracked**, but the triad it replaces is `GitClass.IGNORED` (`state/contract.py:442-462`), and nothing "derives" `charter.yaml` from a tracked source anymore.

**Resolution** (renata M2 / alphonso MAJOR-1): `charter.yaml` ∈ `tracked_files`. Do **NOT** put `charter.yaml` in `derived_files` — the "content-hash input set" is a **distinct field** (`content_hash_files = [charter.yaml]`, sourced from the existing separate `BUNDLE_CONTENT_HASH_FILES` constant, which was always distinct from `derived_files` — that distinction is literally the 4-vs-3 mismatch). `derived_files` / `derivation_sources` become `[]` / `{}` (nothing generated-and-gitignored remains in the charter bundle). This keeps `CharterBundleManifest._validate`'s `tracked ∩ derived = ∅` invariant **intact and untouched** (charter.yaml is only in `tracked`). `state/contract.py` marks `charter.yaml` git-tracked and retires the four ignored entries. The `catalog`, though derived from activation + DRG, lives **inside** the one `charter.yaml` (not a separate file) and is kept honest by catalog↔activation parity (`consistency_check.py`) + freshness. Governance/directives/activation are authored.

**Why it's expensive-to-reverse**: getting the schema/git-class wrong forces a second `SCHEMA_VERSION` bump + migration on the same brand-new file — the churn #2519 exists to end. IC-02 owns the `_validate`/manifest change; do NOT relax the disjointness rule.

## ⚠ LANDMINE 2 — `charter_hash` self-reference (RESOLVED)

**Problem**: `_compute_charter_source` (`computer.py:270`) + `hasher.py:45,58` + `sync.py:342/387` compute freshness by comparing the `charter.md` SHA to `metadata.yaml::charter_hash`. Post-inversion `charter.md` is a never-resolving companion → that staleness is meaningless, and a hash of `charter.yaml` cannot live *inside* `charter.yaml` (chicken-egg).

**Resolution**: Retire the `charter.md`-hash staleness mechanism (`_compute_charter_source`), or re-home the content hash externally (the synthesis manifest already holds `bundle_content_hash`). Do **not** carry a self-referential `charter_hash` field into `charter.yaml.metadata`. The freshness signal is the `charter.yaml` content hash (`content_hash_files` single point), preserving the #2732 recipe (per-file BOM-strip/CRLF, write-side stamps, fresh-seed early-exit, `built_in_only` normalization).

**Extension (alphonso MINOR-3) — spurious authoring-staleness**: post-inversion the authored surface and the hash-input surface are the **same file**, so a human authoring-only edit (e.g. tweaking `governance`, which does not change the derived `catalog`) trips freshness-stale even though nothing *derived* drifted. The meaningful post-inversion question is intra-file `catalog`↔`activation` consistency (the **parity** check), not a whole-file hash. IC-06 MUST decide + test one of: (a) ground the freshness signal on catalog↔activation parity rather than a whole-file content hash; or (b) explicitly document that authored edits are *expected* to read stale until the next synth refreshes the baseline (and confirm that is acceptable to the gates that consume freshness).

## ⚠ LANDMINE 3 — charter.yaml recompile is the #2772 clobber reborn (NEW — alphonso MAJOR-2)

**Problem**: the only writer, `write_compiled_charter` (`compiler.py:393-421`), is a **full-file overwrite** (`charter_path.write_text(...)` — the exact #2772 clobber IC-03 guards for `charter.md`). Post-extractor-retirement, `governance`/`directives`/`activation` are AUTHORED and can no longer be re-scraped from prose. If a subsequent `charter generate`/compile reconstructs the whole file from `CompiledCharter` state, it **silently destroys hand-authored governance/activation edits** — the #2772 destruction, one level down, on a *tracked* file.

**Resolution**: charter.yaml writes are **partial / merge writes** — the compile pipeline refreshes ONLY the DERIVED `catalog` + `metadata` sections and preserves the AUTHORED `governance`/`directives`/`activation`/`overrides` **byte-for-byte** via a ruamel round-trip. The compiler treats `activation` as **read-only input** (this also dissolves the catalog←activation "circularity": it is an intra-file DAG, activation is never round-tripped through a derive step). Pin a regression test: authored governance/activation survives `charter generate --force` (mirrors the #2772 charter.md guard). IC-03 owns this; the write goes through the shared helper (INV-9).

## ⚠ Write-discipline — three writers, one tracked file (alphonso MAJOR-3)

Three independent writers now mutate `charter.yaml`: `activation_engine.commit_plan` (activation), `pack_manager.merge_defaults` (absent-key seed), and `compiler.write_compiled_charter` (catalog/metadata). Not a race (all sequential CLI ops; `merge_defaults` only fills *absent* keys). But each must preserve the others' sections. Route all three through a **single shared `load → mutate-owned-section → round-trip-save` helper owned by the IC-02 keystone**, so section-preservation is structural, not conventional (INV-9). (Note: `.kittify/config.yaml` is *already* git-tracked — the new hazard is co-locating churny activation with derived catalog + authored governance in one file, not "tracked vs untracked".)

## Invariants (must hold)
- **INV-1**: exactly one authored source per dimension — `charter.yaml` for structured doctrine/activation, `charter.md` for prose rationale. No third.
- **INV-2**: `.kittify/config.yaml` carries no `activated_*` after migration — only non-doctrine config + the single `charter:` pointer. The resolver locates `charter.yaml` via that pointer (a swap is a one-line change).
- **INV-3**: no governance/resolving DECISION reads `charter.md` prose (display-only).
- **INV-4**: the activation-parity + DRG-filter behavior is byte-preserved (behavior-preserving relocation).
- **INV-5**: fail-loud on an un-migrated project (four present, no charter.yaml) — no legacy-file fallback branch.
- **INV-6**: touch only `.kittify/charter/metadata.yaml`; never `.kittify/metadata.yaml` (project identity).
- **INV-7**: `src/charter/` imports no `specify_cli` (layer boundary).
- **INV-8 (activation set bound — the REAL invariant)**: a resolved `charter.yaml` activation set is a **subset** of all offered doctrine (`⊆ default ∪ org ∪ project ∪ local` packs); `filter_graph_by_activation` gates the offered universe down to the activated set. This mission relocates a **single flat activation surface** (config.yaml → charter.yaml) and preserves this bound (SC-008).
- **INV-8b (tier accumulation — FORWARD-INTENT, not built here)**: the `org_active ⊆ team/project_active ⊆ repo_active` superset/accumulation is the *target* charter-tier model (see the operator's Flashpoint journey in `contracts/active-doctrine-resolution.md`). ⚠ It is **NOT** implemented by the current `pack_roots` mechanism — `pack_roots` / `merge_three_layers` overlay artifact *definitions* (the offered universe), not activation tiers; activation today is a single flat set from one file (paula MAJOR-4). The accumulation overlay is **future work fenced OUT by C-008**; the diagram documents it as intent. Do not write a test asserting tier-accumulation against current code.
- **INV-9 (single write helper)**: all charter.yaml writers (`commit_plan`, `merge_defaults`, `compiler`) go through one shared `load→mutate-owned-section→round-trip-save` helper (owned by IC-02) that preserves non-owned sections byte-for-byte. Round-trip tests: writing activation preserves governance/catalog and vice versa (Landmine 3 / MAJOR-3).
