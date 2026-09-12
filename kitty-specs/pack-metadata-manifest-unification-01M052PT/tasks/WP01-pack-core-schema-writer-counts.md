---
work_package_id: WP01
title: 'Pack-core: unified schema, charter absorption, built-in writer, counts'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-009
planning_base_branch: feat/pack-metadata-manifest-unification
merge_target_branch: feat/pack-metadata-manifest-unification
branch_strategy: Planning artifacts for this mission were generated on feat/pack-metadata-manifest-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pack-metadata-manifest-unification unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- at: '2026-08-16'
  note: Authored at /spec-kitty.tasks; folds post-plan squad findings.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/
create_intent:
- src/specify_cli/doctrine/pack_manifest.py
- src/specify_cli/doctrine/builtin_manifest.py
- packs/built-in/pack-manifest.yaml
- tests/doctrine/test_pack_manifest_schema.py
- tests/doctrine/test_builtin_manifest.py
- tests/doctrine/test_counts_derivation.py
- tests/doctrine/test_charter_profile_absorption.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/pack_manifest.py
- src/specify_cli/doctrine/builtin_manifest.py
- src/specify_cli/doctrine/snapshot.py
- src/charter/synthesizer/manifest.py
- packs/built-in/pack-manifest.yaml
- tests/doctrine/test_pack_manifest_schema.py
- tests/doctrine/test_builtin_manifest.py
- tests/doctrine/test_counts_derivation.py
- tests/doctrine/test_charter_profile_absorption.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). Apply its identity, boundaries, and Python 3.11+ / TDD discipline throughout.

## Objective

Land the **single canonical `pack-manifest` schema** and its first producers: the unified model + reader, the charter-manifest absorbed as a profile (no dropped fields), the built-in pack's generated manifest, and the retirement of stored per-kind `artifact_counts` for a derived view. This is the mission MVP (SC-001/SC-002).

**Gate:** do not start until ADR `docs/adr/3.x/2026-08-16-1` and the `pack-layout.md` contract are on this base.

## Context

- Design: [plan.md](../plan.md) IC-01/IC-02/IC-03 + [data-model.md](../data-model.md). Two divergent manifests today: org per-kind counts (`snapshot.py:157-212`) and charter enumerated `artifacts[]` (`charter/synthesizer/manifest.py`).
- Reuse the single hasher: `finalize_manifest` → `compute_manifest_hash` (`manifest.py:224/:205`). Do **not** add a second hasher.

## Subtasks

### T001 — Unified `PackManifest` schema + reader + widened `Constituent.kind`
Create `src/specify_cli/doctrine/pack_manifest.py`: the `PackManifest` model (`schema_version`, `generated_by/at`, `source_*`, `manifest_hash`, `constituents[]`, optional `charter:` profile) and `Constituent` (`kind: ArtifactKind`, `id`, `path`, `content_hash`, optional `provenance_path`). **Widen `kind`** from the charter manifest's 3-kind literal to the shared `ArtifactKind` (~14). Provide a reader and a `counts_by_kind(constituents) -> dict[str,int]` derived view. Test: `test_pack_manifest_schema.py`.

### T002 — Charter profile absorption (full field-set)
Make `charter/synthesizer/manifest.py` emit the unified schema as the charter instance. `CharterProfile` carries the **entire** SynthesisManifest charter-only field-set: `mission_id`, `bundle_content_hash`, `synthesizer_version`, `run_id`, `adapter_id`, `adapter_version`, `created_at`, `schema_version`, **`built_in_only`** (load-bearing). Give per-constituent **`provenance_path`** a home on `Constituent` (required for charter constituents). Drop nothing. Test: `test_charter_profile_absorption.py`.

### T003 — Pin the charter-manifest reader surface green
Enumerate + pin every charter-manifest reader so absorption causes 0 regressions: `doctrine_synthesizer/{apply,provenance,__init__}.py`, `charter_runtime/freshness/computer.py`, `charter_runtime/preflight/runner.py`, `charter_runtime/lint/findings.py`, `cli/commands/charter_bundle.py`, `doctrine/versioning.py`, and the two `m_3_2_0rc35_charter_*` migrations. Add regression coverage in `test_charter_profile_absorption.py`. (These readers are *read-only* here — do not edit them; if any needs a change, record a one-line out-of-map rationale.)

### T004 — Built-in manifest generator, wired + integration-tested
Create `src/specify_cli/doctrine/builtin_manifest.py`: generate `packs/built-in/pack-manifest.yaml` from the per-kind `packs/built-in/*.graph.yaml` `nodes:`. **Emit ONLY `pack-manifest.yaml`; never write `pack.yaml`** (authored path reserved for WP04) and **never emit `pack_version`** (built-in reads it from the authored `pack.yaml`; see WP04). **Name the wiring call site** (which build/upgrade function invokes the generator) and add an **integration assertion** that the wiring *fires* — run the upgrade/build path on a fixture and assert `pack-manifest.yaml` materializes (renata M1: enumeration alone does not prove the generator is ever invoked). Test: `test_builtin_manifest.py` — (a) 100% of DRG nodes enumerated (SC-002); (b) the build/upgrade path materializes the manifest.

### T005 — Deterministic + tamper-evident generation
Constituents sorted by `(kind, id)`; `content_hash` over **LF-normalized** artifact bytes (cross-platform, DIR-001); **exclude `generated_at`/`generated_by` from both the `manifest_hash` and the byte-diff assertion**. Named tests in `test_builtin_manifest.py`: (a) **determinism/NFR-003** — generate twice for an unchanged pack → byte-identical file + identical `manifest_hash`; (b) **tamper-evidence/FR-009** — mutate one constituent's bytes → its `content_hash` and the `manifest_hash` both change (proves the hash *detects* tampering, not just that it is stable).

### T006 — Retire stored per-kind `artifact_counts`; derived view
In `snapshot.py` (`write_pack_manifest`, counts at `:176/:195`), stop persisting the per-kind `artifact_counts` block; expose it via `counts_by_kind(constituents)`. **Transitional precedence:** derive-from-constituents when present, else fall back to stored counts (migration input) so a not-yet-generated pack does not read 0. The derived view preserves the existing `dict[str,int]` interface so consumers need no change.

### T007 — Pin real pack-counts readers green
The genuine **pack** per-kind counts consumers are `pack_assembler.py:388-396` and `charter/_profile_health_render.py:111`. Add `test_counts_derivation.py` proving the derived view returns identical per-kind values for each. **Do NOT pin `_doctrine_collect.py:421` (`_count_pack_artifacts`)** — it counts YAML files on disk directly and never reads the stored `artifact_counts` block, so a "derived == stored" assertion there would pass trivially (paula SF-1). **Explicitly out of scope:** the `dossier` `{total,required,required_present}` counts (`dossier/api.py:237`, dashboard JS) — a different domain fed by `snapshot.total_artifacts`. No frontend work.

## Definition of Done
- One unified schema; charter manifest is a profile instance with its full field-set; built-in pack has a generated manifest enumerating its nodes; re-run is byte-identical; per-kind counts derive; all named readers green; `ruff`/`mypy` clean; new branches covered by focused tests.

## Reviewer guidance
Verify: no second hasher; `generated_at/by` excluded from hash+diff; `built_in_only` + `provenance_path` survive absorption; generator writes only `pack-manifest.yaml`; the dossier counts are untouched.
