---
work_package_id: WP01
title: Relocate & Unify the Loader Authority
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-013
- FR-014
- NFR-001
- NFR-002
planning_base_branch: fix/expected-artifacts-loader-unification
merge_target_branch: fix/expected-artifacts-loader-unification
branch_strategy: Planning artifacts for this mission were generated on fix/expected-artifacts-loader-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/expected-artifacts-loader-unification unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-expected-artifacts-loader-unification-01M1C9VQ
base_commit: cdc1a87de874f3eb887063cab2c903f4cdc536e6
created_at: '2026-08-31T17:39:09.029842+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
history:
- timestamp: '2026-08-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/activation/manifest_loader.py
create_intent:
- src/charter/activation/manifest_loader.py
execution_mode: code_change
mission_id: 01M1C9VQZ28CFRW741WRADS6SZ
owned_files:
- src/charter/activation/manifest_loader.py
- src/specify_cli/dossier/manifest.py
- src/charter/offering/missions/expected_artifact_manifest.py
- tests/dossier/test_manifest.py
tags: []
tracker_refs: []
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Collapse the four drifted reimplementations of the `expected-artifacts.yaml`
org→built-in-precedence + `model_validate` + `ValidationError`-wrap logic into
**one cached authority**, relocated into `charter` so both runtime callers and
charter-tier callers can reach it without violating C-001 (charter must not
import `specify_cli`). This WP is the SEQUENTIAL foundation — every other WP
consumes the seam it establishes (FR-001, FR-002, FR-003, FR-013, FR-014). It
must land green with byte-compatible behavior (NFR-001) and identical cache
semantics (NFR-002) before any re-point (WP02/WP03) runs.

## Context & Constraints

- The current authority is `ManifestRegistry.load_manifest`
  (`src/specify_cli/dossier/manifest.py:193`). It is the canonical org-first /
  built-in-fallback / `model_validate` / wrap-`ValidationError`→`ManifestSchemaError`
  implementation — transcribe its exact logic (`:193-341`), do NOT re-derive it.
- **Sibling-error model (load-bearing).** `MalformedManifestError`
  (`src/charter/offering/missions/repository.py:38`) is the fail-loud channel for
  **present-but-unparseable** manifests (YAML-syntax, non-mapping, unreadable) on
  BOTH tiers. `ManifestSchemaError` is the sibling for **schema / `extra="forbid"`**
  violations. They are distinct siblings; NEVER canonicalize malformation onto
  `ManifestSchemaError` (its `__str__` says "schema-invalid" and its docstring
  excludes parse faults). Both are distinct from `None` = "not found".
- **C-001**: the relocated loader AND `ManifestSchemaError` must live where
  charter-tier consumers reach them WITHOUT charter importing `specify_cli`.
  Activation may import offering (proven at `mission_type_profiles.py:975,1120,1130`);
  offering must NOT import activation. Hence the loader lives in
  `charter/activation/` and `ManifestSchemaError` is **defined in the new
  `manifest_loader.py`** (activation). `MalformedManifestError` STAYS in
  `charter/offering/missions/repository.py` — it is raised by
  `get_expected_artifacts` (offering), which cannot import activation. The two
  sibling errors therefore live in different modules by necessity; the shim
  re-exports both from the old specify_cli path. **WP01 does NOT edit
  `repository.py`** (that module is owned by WP03/FR-012).
- **Out of scope (do NOT touch):** the `blocking_artifact_names` None-vs-`frozenset()`
  tri-state (#3729, C-002) and the guard-table short-circuit (`cores.py:721-723`,
  #3386/#3397/#3407, C-003). This WP only relocates the load+cache concern.
- **Tag hygiene (D8/C-004):** every test in this WP is green-stays-green
  **characterization** — none may carry `@pytest.mark.regression` (a green
  `@regression` test is a landing defect).

## Subtasks & Detailed Guidance

### T001 — Create `charter/activation/manifest_loader.py` (the cached authority)

**Purpose.** Establish the single cached `load_manifest(mission_type, repo_root=None)`
FUNCTION that owns org→built-in precedence, `model_validate`, and the
`ValidationError`→`ManifestSchemaError` wrap, carrying its own module-level
`_cache`. Define `ManifestSchemaError` here-adjacent (moved into charter).

**Steps.**
1. Create the new module. Transcribe the precedence + validate logic from
   `ManifestRegistry.load_manifest` (`specify_cli/dossier/manifest.py:193-341`) —
   copy the exact resolution order, do not improvise.
2. DEFINE `ManifestSchemaError` in the NEW `manifest_loader.py` itself (activation
   layer), moved out of `specify_cli/dossier/manifest.py:104`. Do NOT put it in
   `repository.py` and do NOT edit `repository.py` in this WP — that module is
   owned by WP03 (FR-012). `MalformedManifestError` STAYS in `repository.py`
   (offering) and is imported into the loader; the two siblings live in different
   modules by necessity (offering cannot import activation).
3. Imports the loader needs: `MalformedManifestError`, `MissionTemplateRepository`
   from `charter.offering.missions.repository`; `resolve_org_expected_artifacts`
   from `charter.activation.org_expected_artifacts`; `resolve_existing_org_roots`
   from `charter.offering.drg.org_pack_config`; the model from
   `charter.offering.missions.expected_artifact_manifest`.
4. Give the module a private `_cache: dict[tuple[str, tuple[str, ...]], ExpectedArtifactManifest | None]`
   keyed `(mission_type, org_roots)` (data-model §Loader authority contract).
   Preserve cross-repo-root non-shadowing and declaration order (NFR-002).
5. **Remove the legacy org-branch `except Exception → None` swallow** — do NOT
   swallow schema or malformed errors. On a `ValidationError`, wrap into
   `ManifestSchemaError`; let `MalformedManifestError` propagate.
6. Errors are NOT cached — cache only successful loads and genuine `None`.

**Files.** `src/charter/activation/manifest_loader.py` (new — defines both the
loader and `ManifestSchemaError`). `repository.py` is NOT edited here.

**Validation.** `mypy` strict + `ruff` clean on the new module; each function
≤15 complexity (NFR-003). No import of `specify_cli` anywhere in charter.

### T002 — Convert `ManifestRegistry.load_manifest` to a thin delegate + shim re-export

**Purpose.** Keep `ManifestRegistry` in `specify_cli` (it is a stateful class
with sibling completeness methods, instantiated 4×) but make its `load_manifest`
a thin delegate to the charter authority, and re-export the moved names so no
importer breaks (FR-002/FR-003).

**Steps.**
1. Rewrite `ManifestRegistry.load_manifest` (`:193`) to call
   `charter.activation.manifest_loader.load_manifest(...)`. KEEP the sibling
   methods `get_required_artifacts` (`:346`), `get_blocking_artifacts` (`:367`),
   `validate_manifest` (`:393`), `clear_cache` (`:433`) — they do NOT move.
2. Add module-level shim re-exports so all four names resolve from the OLD path:
   `from charter.activation.manifest_loader import load_manifest, ManifestSchemaError`
   and `from charter.offering.missions.repository import MalformedManifestError`.
3. Guarantee **object identity**: `specify_cli.dossier.manifest.ManifestSchemaError
   is charter.offering.missions.repository.ManifestSchemaError` (same object, not a
   copy), so `except ManifestSchemaError` at the 8+ old-path catch sites
   (`sync/namespace.py:102`, `sync/dossier_pipeline.py:363`, 6 tests) still catches
   errors raised by the charter authority. Same for `MalformedManifestError`.

**Files.** `src/specify_cli/dossier/manifest.py`.

**Validation.** See `contracts/shim-reexport-surface.md`. All four names import
from the old path; identity assertions hold; delegate returns the SAME object the
authority returns for identical inputs.

### T003 — Delete `ExpectedArtifactManifest.from_yaml_file` and migrate its tests

**Purpose.** Remove the orphan direct-read loader (FR-013) — it constructs via
`cls(**data)` (`expected_artifact_manifest.py:152`), which a `model_validate`-only
gate cannot police, so it must be deleted, not "routed".

**Steps.**
1. Delete `from_yaml_file` (`src/charter/offering/missions/expected_artifact_manifest.py:130-152`).
   Confirm there are no production callers first (`grep -rn from_yaml_file src/`).
2. Migrate its 3 tests (`tests/dossier/test_manifest.py:458/472/486`) to use the
   canonical `load_manifest` or explicit direct construction where the intent was
   to test the model itself.

**Files.** `src/charter/offering/missions/expected_artifact_manifest.py`;
`tests/dossier/test_manifest.py`.

**Validation.** `grep -rn from_yaml_file src/ tests/` returns nothing; the 3
migrated tests pass.

### T004 — [P] Reconcile the stale `load_manifest` docstring + sibling comments (FR-014)

**Purpose.** Campsite-clean: the current docstrings/comments still call #3412 an
open BUILT-IN gap. Correct them to the shipped semantics.

**Steps.**
1. Update the moved `load_manifest` docstring to describe the shipped fail-loud
   semantics (malformed → `MalformedManifestError`, schema → `ManifestSchemaError`,
   absent → `None`).
2. Sweep sibling comments in the touched modules for the same stale framing and
   fix them. This is prose-only — no behavior change.

**Files.** `src/charter/activation/manifest_loader.py` (docstring);
`src/specify_cli/dossier/manifest.py` (sibling comments).

**Validation.** No comment in the touched modules describes #3412 as open.

### T005 — Shim re-export contract tests + cache characterization (NFR-002)

**Purpose.** Lock the shim surface (object identity for all 4 names) and prove the
relocated cache behaves identically via the delegate.

**Steps.**
1. Add import-level + identity contract tests per `contracts/shim-reexport-surface.md`
   (all four names resolve from `specify_cli.dossier.manifest`; identity holds).
2. Port / re-run `TestManifestRegistryOrgTier` cache-key, cross-root
   non-shadowing, and declaration-order tests through the delegate (NFR-002).
3. Tag ALL of these as **characterization**, NOT `@pytest.mark.regression`.

**Files.** `tests/dossier/test_manifest.py`.

**Validation.** New identity tests + ported cache tests green; zero
`@pytest.mark.regression` markers added in this WP.

## Branch Strategy

Planning artifacts for this mission were generated on
`fix/expected-artifacts-loader-unification`. During `/spec-kitty.implement` this
WP's execution workspace (worktree) is allocated per-lane from `lanes.json` by
`resolve_workspace_for_wp`; do not reconstruct the path. Completed changes merge
back into `fix/expected-artifacts-loader-unification` unless the human explicitly
redirects the landing branch. The final PR targets upstream as a DRAFT — the
operator merges.

## Definition of Done

- `charter/activation/manifest_loader.py` exists with `load_manifest` + `_cache`
  + `ManifestSchemaError` (defined there); `MalformedManifestError` stays in
  `repository.py` (not edited in this WP).
- `ManifestRegistry.load_manifest` is a thin delegate; completeness methods stay.
- Shim re-exports resolve all four names from the old path with object identity.
- `from_yaml_file` deleted; its 3 tests migrated and green.
- Stale #3412 docstrings/comments corrected.
- Charter never imports `specify_cli`; `ruff` + `mypy` zero-new; ≤15 complexity.
- All new/ported tests are characterization (no `@regression`), and green.

## Risks

- **Identity drift.** Re-exporting a *copy* instead of the same object silently
  breaks `except ManifestSchemaError` at old catch sites. Assert identity, not
  equality.
- **Accidental error caching.** Caching a raised error would poison later loads;
  cache only successes / genuine `None`.
- **Import cycle.** A stray `specify_cli` import in charter trips the boundary
  arch-gate — keep the loader's imports offering/activation-only.
- **Over-move.** Moving `ManifestRegistry` wholesale would drag specify_cli-owned
  completeness logic into charter (D3) — only the load+cache concern relocates.

## Reviewer Guidance

- Confirm the loader logic is a faithful transcription of `manifest.py:193-341`,
  not a re-derivation — diff the resolution order and the cache key.
- Verify the org-branch `except Exception → None` swallow is GONE and nothing
  swallows `MalformedManifestError` / `ManifestSchemaError`.
- Check object-identity assertions exist for all four shim names.
- Verify no `@pytest.mark.regression` was added (D8) and no `specify_cli` import
  appears in any charter module.
