---
work_package_id: WP03
title: Project-local artifact storage + provenance writer (plan alias WP3.6)
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- FR-014
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222
base_commit: 9d239e76b5e1eef0f31811a179a5de91ff0c8149
created_at: '2026-04-17T17:44:15.403040+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
shell_pid: "70043"
agent: "claude:opus-4.6:reviewer:reviewer"
history:
- at: '2026-04-17T16:43:25Z'
  actor: tasks
  event: generated
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
mission_id: 01KPE222CD1MMCYEGB3ZCY51VR
mission_slug: phase-3-charter-synthesizer-pipeline-01KPE222
owned_files:
- src/charter/synthesizer/provenance.py
- src/charter/synthesizer/staging.py
- src/charter/synthesizer/manifest.py
- src/charter/synthesizer/write_pipeline.py
- src/charter/bundle.py
- tests/charter/synthesizer/test_provenance.py
- tests/charter/synthesizer/test_staging_atomicity.py
- tests/charter/synthesizer/test_manifest.py
- tests/charter/synthesizer/test_bundle_validate_extension.py
tags: []
---

# WP03 · Project-local artifact storage + provenance writer

## Objective

Deliver the stage-and-promote filesystem pipeline (KD-2). Every synthesis run stages **all** writes under `.kittify/charter/.staging/<runid>/{doctrine,charter}/`; after WP04's validation gate passes, ordered `os.replace` demultiplexes into `.kittify/doctrine/` (content) and `.kittify/charter/` (bookkeeping); the **synthesis manifest** is written last as the authoritative commit marker. Also: `charter bundle validate` extension (FR-015) that bridges the two trees.

## Context

Read before writing code:
- [plan.md §KD-2](../plan.md) — atomicity model in detail.
- [data-model.md §E-4, §E-6, §E-9](../data-model.md) — provenance schema, manifest schema, run-lifecycle state diagram.
- [contracts/provenance.schema.yaml](../contracts/provenance.schema.yaml) — authoritative shape.
- [contracts/synthesis-manifest.schema.yaml](../contracts/synthesis-manifest.schema.yaml) — authoritative shape.
- [quickstart.md §1 "What just happened under the hood"](../quickstart.md) — the 8-step sequence is the test oracle for `test_staging_atomicity.py`.
- Existing bundle logic at `src/charter/bundle.py` — understand v1.0.0 contract before extending; keep backward-compat (C-012).

## Branch strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: allocated by finalize-tasks (Lane A)
- Branch name: `kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222-lane-a`

## Subtasks

### T015 — `provenance.py` [P]

**File**: `src/charter/synthesizer/provenance.py`

Pydantic v2 model `ProvenanceEntry` exactly matching `contracts/provenance.schema.yaml`. IO helpers:
- `dump_yaml(entry, path)` — serializes via `ruamel.yaml` using the same canonical formatting as artifact bodies; goes through `PathGuard.write_text`.
- `load_yaml(path) -> ProvenanceEntry` — round-trips; validates on load.

The `allOf` rule (at least one of `source_section` or `source_urns` non-empty) is enforced by Pydantic validator.

### T016 — `staging.py` [P]

**File**: `src/charter/synthesizer/staging.py`

Manage the staging directory lifecycle:
- `StagingDir.create(repo_root, run_id) -> StagingDir` — creates `.kittify/charter/.staging/<run_id>/doctrine/{directives,tactics,styleguides}/` and `.kittify/charter/.staging/<run_id>/charter/provenance/` via `PathGuard.mkdir`.
- `StagingDir.path_for_content(kind, filename) -> Path` — returns the staged location under the `doctrine/` subtree.
- `StagingDir.path_for_provenance(kind, slug) -> Path` — returns the staged location under the `charter/` subtree.
- `StagingDir.commit_to_failed(cause: str)` — renames `.staging/<run_id>/` → `.staging/<run_id>.failed/` and writes `cause.yaml` with `{reason, traceback, timestamp}`.
- `StagingDir.wipe()` — on successful promote, remove the staging dir.
- Context manager support: `with StagingDir.create(...) as stage:` — on unhandled exception, route to `commit_to_failed`; on success, caller must explicitly call `wipe` after promote (see T018).

The staging root (`.kittify/charter/.staging/`) is deliberately under the bookkeeping tree so doctrine consumers never traverse it.

### T017 — `manifest.py` [P]

**File**: `src/charter/synthesizer/manifest.py`

Pydantic v2 models `SynthesisManifest` + `ManifestArtifactEntry` matching `contracts/synthesis-manifest.schema.yaml`. IO:
- `dump_yaml(manifest, path)` — writes to `.kittify/charter/synthesis-manifest.yaml` via `PathGuard.write_text`.
- `load_yaml(path) -> SynthesisManifest`.
- `verify(manifest, repo_root) -> None` — for every entry, checks that the file at `path` exists and its blake3-256 hash equals `content_hash`; raises `ManifestIntegrityError` on mismatch.

This module implements the **authority rule** from KD-2: live tree is authoritative IFF manifest is present AND all `content_hash` checks pass.

### T018 — `write_pipeline.py`

**File**: `src/charter/synthesizer/write_pipeline.py`

Public entry: `promote(request, staging_dir, results, validation_callback) -> SynthesisManifest`.

Flow:
1. Write every `(body, provenance)` tuple into the staged subtrees (content → `staging/doctrine/...`, provenance → `staging/charter/provenance/...`).
2. Call `validation_callback(staging_dir)` — WP04 wires its validation gate here; a raised exception aborts and routes to `staging_dir.commit_to_failed(...)`.
3. On validation pass, execute ordered `os.replace` calls (via `PathGuard.replace`) into the final trees:
   - Content files → `.kittify/doctrine/<kind-dir>/<filename>`.
   - Provenance files → `.kittify/charter/provenance/<kind>-<slug>.yaml`.
   - Project DRG graph (if present under `staging/doctrine/graph.yaml`) → `.kittify/doctrine/graph.yaml`.
4. **Manifest last**: build `SynthesisManifest` from the committed state, write to `.kittify/charter/synthesis-manifest.yaml` via `PathGuard.write_text`.
5. `staging_dir.wipe()`.
6. Return the manifest.

On any exception between step 3 and step 4, **do not** delete staging — let the `commit_to_failed` path preserve it for diagnosis. Step 4's manifest-last property means a partial-promote before step 4 leaves the live tree authored but without a manifest → readers correctly treat it as partial-and-rerunable.

Wire `orchestrator.synthesize` (from WP01, populated by WP02's `synthesize_pipeline`) to call `write_pipeline.promote` after WP02's in-memory assembly. The lazy-import seam at `orchestrator.synthesize` now resolves.

### T019 — Extend `src/charter/bundle.py` for FR-015

**File**: `src/charter/bundle.py` (edit; preserve v1.0.0 contract)

Extend `bundle validate` to cross-check:
- Every file matching `*.directive.yaml` / `*.tactic.yaml` / `*.styleguide.yaml` under `.kittify/doctrine/` has a corresponding provenance sidecar at `.kittify/charter/provenance/<kind>-<slug>.yaml`.
- Every provenance sidecar references an existing artifact.
- The synthesis manifest at `.kittify/charter/synthesis-manifest.yaml` (if present) verifies against disk via `manifest.verify`.
- Stale `.kittify/charter/.staging/<runid>.failed/` dirs produce a **warning** (not error) — R-7 accumulation signal.

Additive only. No `schema_version` bump. Legacy bundles (no synthesis state) pass exactly as before (regression test in T020).

### T020 — Tests

**Files**:
- `tests/charter/synthesizer/test_provenance.py` — Pydantic round-trip; `allOf` validator rejects entry with neither `source_section` nor non-empty `source_urns`; byte-reproducibility of `dump_yaml` under fixed inputs (NFR-006).
- `tests/charter/synthesizer/test_staging_atomicity.py` — injected failures at each lifecycle stage:
  - schema failure during T012 → no files in live tree; staging preserved at `.failed/`.
  - validation callback raises (WP04 scenarios) → no files in live tree; staging preserved.
  - promote fails at `os.replace` → staging preserved, live tree partial but no manifest → reader treats as partial-and-rerunable.
  - simulated SIGKILL before manifest write → same partial-state semantics.
  - Fail-closed timing < 5s (NFR-004).
- `tests/charter/synthesizer/test_manifest.py` — manifest-last: absence of manifest means "partial"; `verify` catches hash mismatch via `ManifestIntegrityError`; run_id matches staging dir.
- `tests/charter/synthesizer/test_bundle_validate_extension.py` — four fixtures:
  1. Valid post-synthesis bundle → pass.
  2. Artifact without provenance → structured error.
  3. Provenance without artifact → structured error.
  4. Schema-invalid artifact → structured error.
  Plus a **regression fixture** with no synthesis state at all → passes exactly as v1.0.0 did (C-012).

## Definition of Done

- All 6 subtasks complete.
- `pytest tests/charter/synthesizer/test_{provenance,staging_atomicity,manifest,bundle_validate_extension}.py` green.
- `mypy --strict` clean on WP03 files.
- Coverage ≥ 90% (NFR-001); staging failure paths specifically tested.
- Every write in WP03 routes through `PathGuard` — the WP01 lint-style grep test remains green.
- Bundle validate remains backwards-compatible with v1.0.0 (regression fixture passes).

## Risks & premortem

- **R-7 · Staging-dir accumulation** — Mitigation: `.failed/` preservation is intentional; `bundle validate` warns on stale failed-staging dirs.
- **R-3 · Bundle manifest drift** — Mitigation: additive-only; `schema_version` stays `1`; legacy-bundle regression fixture is the contract lock.
- **Promote-during-crash partial state** — Mitigation: manifest-last semantics + `ManifestIntegrityError` on reader side make partial state observable and recoverable.
- **Canonical YAML mismatch** — Mitigation: use the same `canonical_yaml` helper WP02 uses to compute `artifact_content_hash`; add a test that writes → reads → rehashes → equals the provenance `artifact_content_hash`.

## Reviewer guidance

1. `write_pipeline.promote` — step 4 (manifest-last) must be the sole mutation after the content `os.replace` calls; any reordering breaks the authority rule.
2. `staging.StagingDir` — does the context manager reliably route unhandled exceptions to `.failed/`?
3. `manifest.verify` — is hash comparison constant-time-irrelevant here? (No — content-hash check is integrity, not secrecy; plain `==` is fine.)
4. `bundle.py` diff — any change that would make a legacy v1.0.0 bundle fail validation is a regression; verify the regression fixture explicitly.
5. Timing tests — are NFR-004 thresholds CI-tolerant (use `pytest-timeout` with slack; don't sleep)?

## Next command

```bash
spec-kitty agent action implement WP03 --agent <your-agent>
```

## Activity Log

- 2026-04-17T17:44:16Z – claude:sonnet-4.6:implementer:implementer – shell_pid=65645 – Assigned agent via action command
- 2026-04-17T18:01:26Z – claude:sonnet-4.6:implementer:implementer – shell_pid=65645 – WP03 ready: staging+promote atomicity, manifest, provenance sidecars, bundle validate extension. 48 tests pass, ruff clean.
- 2026-04-17T18:01:47Z – claude:opus-4.6:reviewer:reviewer – shell_pid=70043 – Started review via action command
- 2026-04-17T18:07:17Z – claude:opus-4.6:reviewer:reviewer – shell_pid=70043 – Moved to planned
