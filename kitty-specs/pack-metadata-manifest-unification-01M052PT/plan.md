# Implementation Plan: Pack-Metadata Manifest Unification

**Branch**: `feat/pack-metadata-manifest-unification` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/pack-metadata-manifest-unification-01M052PT/spec.md`

> **Revised 2026-08-16 after the post-plan adversarial squad** (paula-patterns / reviewer-renata / planner-priti). Folds: lineage key-space/authority decision (PP-M1), full charter field-set + `provenance_path` home (PP-M2), the synthesis-manifest reader surface (PP-M3), the `pack_version` writer-leak (PP-M4), determinism vs. timestamped hash (RR-MF1), the per-kind-vs-dossier counts reconciliation (RR-MF2 / PT-S3), the DRG path correction (RR-MF3 / PT-S2), the C-002/NFR-001-vs-C-005 naming split (RR-MF4), and the WP `blocked_by` correction + IC-06 precondition (PT-M1/M2).

## Summary

Unify pack metadata onto **one** canonical manifest schema for every pack type (built-in, org, fetched, charter), replacing the two divergent formats that ship today — per-kind `artifact_counts` for org packs (`src/specify_cli/doctrine/snapshot.py:157-212`) and enumerated `artifacts[]` for charter bundles (`src/charter/activation/synthesizer/manifest.py`). The enumerated shape is promoted to the canonical `constituents[]`; identity/lineage become authored data in a `pack.yaml`/`pack.md` pair, distinct from the generated `pack-manifest.yaml`; lineage resolution reuses the existing `org_extends` resolver via an identity-keyed edge map. Ratified by ADR `docs/adr/3.x/2026-08-16-1-pack-metadata-manifest-unification.md`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: internal — `specify_cli.doctrine` (snapshot/pack_assembler), **`doctrine.drg`** (org_pack_config), `charter.activation.synthesizer.manifest`, `charter.activation.org_extends`; `ruamel.yaml`; ULID minting reused from the mission-identity model.
**Storage**: YAML — authored `pack.yaml`/`pack.md` + generated `pack-manifest.yaml` at each pack root; `packs/built-in/` for the reference pack.
**Testing**: `pytest` — unit under `tests/doctrine/`; the no-parallel-resolver ratchet under `tests/architectural/`; the no-author-edit rule under `tests/architectural/` (no `tests/contracts/` dir exists).
**Target Platform**: Linux/macOS/Windows CLI (DIR-001). **`content_hash` normalizes line endings (LF)** so hashes are cross-platform-stable (trust substrate, #2539).
**Project Type**: single (CLI/library).
**Performance Goals**: build/upgrade-time generation; determinism > speed.
**Constraints**: deterministic/idempotent generation (0-byte re-run diff, provenance-timestamp excluded from the hashed/diffed content); 0 new lineage resolvers; 0 pack-counts-consumer regressions; generated file never hand-authored; **no second lineage authority**.
**Scale/Scope**: 1 built-in pack (~14 kinds), N org/fetched packs, 1 charter bundle profile; the ~7-heuristic secondary tail is out of scope (deferred to #2721).

## Charter Check

- **DIR-001 cross-platform** — POSIX-normalized paths; **LF-normalized `content_hash`**.
- **DIR-010/011 identifier safety** — `pack_id` is ULID; constituent `kind`/`id` are canonical URNs.
- **Single-canonical-authority** — the mission removes a two-manifest violation; the **no-parallel-resolver** half is enforced by the arch ratchet (tracked as **C-002 / NFR-001** — *not* the spec's local C-005, which is authored/generated separation).
- **DIR-018 doctrine versioning** — `schema_version` gates future shape changes.
- **Base dependency (hard):** the ratifying ADR `2026-08-16-1` and the `pack-layout.md` contract resolve only once PR #3480 (and the org-layer mission) are on base. **Implementation MUST NOT start until the ADR + pack-layout contract are on the mission's base** — otherwise the C-002/authored-generated contracts are unverifiable.

## Project Structure

### Documentation (this mission)
```
kitty-specs/pack-metadata-manifest-unification-01M052PT/
  spec.md · plan.md · data-model.md · research/ · tasks/
```

### Source Code (repository root) — corrected package boundaries
```
src/specify_cli/doctrine/
  snapshot.py            # write_pack_manifest: retire per-kind artifact_counts (:176/:195) → derived view; KEEP pack_version (:172) as fetched/org provenance (built-in reads authored); write constituents
  pack_manifest.py       # NEW: unified schema model + reader + derive-per-kind-counts view
  builtin_manifest.py    # NEW: generator emitting pack-manifest.yaml from packs/built-in/*.graph.yaml
  pack_descriptor.py     # NEW: authored pack.yaml model (pack_id, pack_version, lineage edges)
  pack_assembler.py       # reads artifact_counts (:388) + pack_version (:390) → derived view / authored descriptor
src/doctrine/drg/
  org_pack_config.py      # CORRECT home of OrgPackConfig (name at :166; extends lineage); add pack_id key. DRG boundary — confirm arch-boundary tests tolerate it.
src/charter/
  synthesizer/manifest.py # becomes the charter profile instance; compute_manifest_hash (:205) / finalize_manifest (:224) reused
  org_extends.py          # unchanged authority; parent_pack resolution feeds an identity-keyed edge map here
packs/built-in/
  pack.yaml               # NEW authored descriptor
  pack-manifest.yaml      # NEW generated manifest
tests/
  doctrine/test_pack_manifest_schema.py, test_builtin_manifest.py, test_counts_derivation.py, test_charter_profile_absorption.py
  architectural/test_pack_lineage_no_parallel_resolver.py   # C-002/NFR-001 ratchet (AST import/callgraph scan for a new traversal — see IC-05)
  architectural/test_pack_manifest_no_author_edit.py        # NFR-004 (pack-layout no-author-edit)
```

Charter-manifest reader surface that IC-01 must keep green (PP-M3): `doctrine_synthesizer/{apply,provenance,__init__}.py`, `charter_runtime/freshness/computer.py`, `charter_runtime/preflight/runner.py`, `charter_runtime/lint/findings.py`, `cli/commands/charter_bundle.py`, `doctrine/versioning.py`, migrations `m_3_2_0rc35_charter_bundle_v2.py` / `m_3_2_0rc35_charter_manifest_defaults_repair.py`.

## Complexity Tracking

| Concern | Why it exists | Why simpler is insufficient |
|---|---|---|
| Two files (authored `pack.yaml` vs generated `pack-manifest.yaml`) | Pack-layout forbids authoring the generated file (`pack-layout.md:104`) | A fenced-block single file needs the generator to preserve authored regions — fragile. |
| `charter:` profile carrying the **full** SynthesisManifest field-set | The charter manifest carries load-bearing fields (`built_in_only`, `run_id`, `adapter_*`, `provenance_path`) read across freshness/preflight/lint | A 3-field profile drops a working contract; a forked charter schema re-creates the split the mission removes. |
| Identity-keyed edge-map adapter for `org_extends` | `org_extends` is generic over `str` keys but is fed **name→name** today | Building a `pack_id`-keyed map is data-only; a second resolver would violate C-002. |

## Implementation Concern Map

### IC-01 — Unified schema + enumerated constituents + charter profile absorption  *(WP-core → #3500; FR-001, FR-004, FR-009; C-001)*
- **Purpose**: define the single `pack-manifest` schema and reader; absorb `synthesis-manifest.yaml` as the charter profile **without dropping its contract**.
- **Charter field-set (PP-M2):** `CharterProfile` carries the **full** SynthesisManifest field-set — `mission_id`, `bundle_content_hash`, `synthesizer_version`, `run_id`, `adapter_id`, `adapter_version`, `created_at`, `schema_version`, **`built_in_only`** (load-bearing). Per-constituent **`provenance_path`** gets a home on `Constituent` (optional; required for charter constituents). Nothing is dropped.
- **Reader surface (PP-M3):** every charter-manifest reader listed above stays green — add an NFR mirroring NFR-002 for the charter side (0 charter-reader regressions), pinned by `test_charter_profile_absorption.py`.
- **Hashing (RR-SF2):** reuse `compute_manifest_hash` (`manifest.py:205`) via `finalize_manifest` (`:224`) — the single write-time finalizer — not a second hasher; the cited `:107` is the field declaration.
- **Determinism (RR-MF1):** the hash and the byte-diff assertion cover `constituents` + `schema_version` + authored-independent fields **only**; `generated_at`/`generated_by` are **excluded from both** (or content-derived) so a re-run is byte-identical.
- **Sequencing/depends-on**: none (foundation).

### IC-02 — Built-in pack manifest generator  *(WP-core → #3500; FR-002; SC-002; NFR-003)*
- **Purpose**: emit `pack-manifest.yaml` for `packs/built-in/` from the per-kind `*.graph.yaml` `nodes:`, wired into build/upgrade.
- **Determinism**: constituents sorted by `(kind, id)`; `content_hash` over **LF-normalized** artifact bytes (cross-platform, DIR-001); provenance timestamp excluded from the hashed/diffed set (per IC-01).
- **Sequencing/depends-on**: IC-01. **Writer boundary (PT-M2):** emits **only** `pack-manifest.yaml`; the authored `pack.yaml` path is reserved and never written here (this precondition is a WP-core acceptance criterion, pulled forward from IC-06).

### IC-03 — Retire stored pack `artifact_counts`; per-kind derived view  *(WP-core → #3500, own acceptance boundary; FR-003; NFR-002; Q1)*
- **Purpose**: stop persisting the **per-kind** pack `artifact_counts` (`snapshot.py:176/195`, shape `{kind: count}`); expose counts derived by counting `constituents[]` per kind.
- **Scope reconciliation (RR-MF2 / PT-S3):** the pack manifest's `artifact_counts` is **per-kind** and IS derivable from `constituents[]`. The `dossier` counts `{total, required, required_present, …}` (`dossier/api.py:237`, read by the dashboard JS) are a **different domain** fed by `snapshot.total_artifacts` — **explicitly out of scope**; no frontend/Playwright work.
- **Real pack-counts readers to pin green (NFR-002):** `pack_assembler.py:388-396`, `charter/_profile_health_render.py:111`, `_doctrine_collect.py:427`. Enumerate + test each.
- **Transitional precedence (PP-S1):** derive-from-`constituents` when present; else fall back to stored counts (migration input) — so a pack whose generator has not yet run does not read 0.
- **Sequencing/depends-on**: IC-01. Distinct acceptance boundary (own commit + reader-pin) within WP-core so the P1 manifest (IC-01/IC-02) can land independently of this compat work.

### IC-04 — Stable `pack_id` identity  *(WP-identity → #3501; FR-005; C-004)*
- **Purpose**: mint a stable, immutable ULID `pack_id` (mirroring the mission-identity model); make it the **sole runtime identity**, `name` a human handle.
- **Path (RR-MF3 / PT-S2):** the surface is **`src/doctrine/drg/org_pack_config.py`** (`OrgPackConfig.name` at `:166`) — the DRG layer, governed by the shared-package-boundary arch tests; confirm they tolerate the change.
- **Two-key discipline (PP-S2):** adopt the Mission-Identity contract — `pack_id` sole identity, `name` handle, resolver disambiguates with **no silent fallback**. State the interim contract for not-yet-backfilled packs.
- **Sequencing/depends-on**: IC-01. **Q2:** built-in first; org/fetched backfill as coverage extends.

### IC-05 — Lineage edges + delegated resolution, authority resolved  *(WP-lineage → #3502; FR-006, FR-007; NFR-001; C-002)*
- **Lineage-authority decision (PP-M1):** `org_extends.resolve_extends_order` is generic over `str` keys but is fed a **name→name** map from the live `extends:` field today (`org_charter.py:517,525`; `extends` = base pack **name**). Decision for this mission:
  - **`extends:` (name-keyed) remains the single live lineage authority.** `parent_pack` is populated on the descriptor but resolution feeds `org_extends` an edge map built from **the pack's resolvable identity** — via a data-only adapter that maps `pack_id → resolvable key`; **no second walker**.
  - For a pack whose `pack_id` is not yet backfilled (Q2), an unresolvable `parent_pack` edge **fails closed** (surfaces an error, like `org_extends`' `ExtendsBaseNotFoundError`) — it is **never a silent no-op / inert field**.
  - Full migration to `parent_pack` as the **sole** edge source (retiring `extends:`) is **deferred until `pack_id` backfill is universal** — out of scope here, recorded so the two-key period is intentional, not accidental.
- **`accompanies_doctrine_pack` (FR-007):** the pack-level charter→doctrine binding (replaces reliance on per-activation `doctrine_pack_id`, `activations.py:241`); fail-closed on unknown target.
- **Ratchet (RR-SF1):** `test_pack_lineage_no_parallel_resolver.py` detects a new traversal by an **AST import/call scan** asserting lineage resolution routes only through `org_extends.resolve_extends_order` (falsifiable, not vacuous).
- **Sequencing/depends-on**: IC-04.

### IC-06 — Authored/generated split, writer boundary closed  *(WP-split → #3503; FR-008; NFR-004; C-005)*
- **Purpose**: authored `pack.yaml`(+`pack.md`) holds identity/lineage; generated `pack-manifest.yaml` holds constituents/hashes; regeneration never touches authored files.
- **`pack_version` — scoped, NOT wholesale (PP-M4 + post-tasks paula-MF-3):** `pack_version` is genuine fetch-time provenance for fetched/org packs (`snapshot.py:172`, `pack_assembler.py:357`) and a **required** key of `_has_recognisable_pack_manifest` (`pack_assembler.py:377`) — stripping it wholesale breaks pack recognition. So only the **built-in** pack's `pack_version` becomes authored (`pack.yaml`); its generator (`builtin_manifest.py`) never emits it. Fetched/org packs **keep** generated `pack_version`. Consumers use **derive-else-fallback** (authored when present, else generated). The real resolver is `_doctrine_collect.py:81` (`_resolve_pack_version`, call site `:423`) — `doctor.py:1098` is a re-export shell. Genuine generated provenance (`source_url`/`source_type`/`fetched_at`) stays on the generated file.
- **Kind vocabulary (PP-S4):** the charter instance's `kind` literal (`Literal["directive","tactic","styleguide"]`) widens to the shared `ArtifactKind` (~14) so the built-in pack's kinds pass the shared model.
- **Sequencing/depends-on**: IC-01 (schema), IC-04 (descriptor fields). The **naming/placement precondition** already landed in WP-core (IC-02); this WP adds the authored **content** + the no-author-edit **contract test**.

### Concern → WP mapping & dependency graph
```
IC-01 (schema+charter absorption) ─┬─ IC-02 (built-in writer; reserves pack.yaml path)
                                   └─ IC-03 (per-kind counts derive; own acceptance boundary)
IC-01 + IC-04 (pack_id) ── IC-05 (lineage)      IC-04 ── IC-06 (two-file split)
```
- **WP-core #3500** = IC-01 + IC-02 + IC-03 (IC-03 a distinct acceptance boundary/commit).
- **WP-identity #3501** = IC-04.  **WP-lineage #3502** = IC-05.  **WP-split #3503** = IC-06.
- **`blocked_by` (corrected, PT-M1):** #3501←#3500; **#3502←#3500,#3501**; **#3503←#3500,#3501**. After #3501 approves, **#3502 and #3503 run in parallel** (PT-S4).

## Risks & Mitigations

- **Two lineage authorities (`extends:` name vs `parent_pack` id).** Mitigated by IC-05's decision: `extends:` stays live authority; `parent_pack` fail-closed until backfill; sole-source migration deferred — no silent inert field.
- **Charter absorption drops a working field.** Mitigated by IC-01's full field-set + the charter-reader pin-green NFR.
- **`pack_version`/counts two-authority window.** Mitigated by IC-06 (generator stops emitting authored fields) + IC-03 transitional precedence.
- **Determinism break from provenance timestamp.** Mitigated by excluding `generated_at/by` from the hashed/diffed content + `(kind,id)` sort + LF-normalized `content_hash`.
- **A second lineage walker.** Mitigated by the AST-scan arch ratchet (IC-05).
- **ADR/contract not on base.** Implementation gated on the ADR + `pack-layout.md` being on base (Charter Check). Do **not** rebase the planning branch after finalize-tasks to acquire them (coord-divergence footgun); the ADR resolves on merge.
