---
work_package_id: WP04
title: ASSET sidecar validator + safety contract
dependencies: [WP01]
requirement_refs:
- FR-005
- FR-006
- FR-009
- FR-010
- NFR-005
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 3 - Loose-contract validator
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1769942"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/pack_validator.py
create_intent:
- src/doctrine/assets/built-in/README.md
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/doctrine/pack_validator.py
- src/doctrine/drg/org_pack_config.py
- src/doctrine/assets/**
- tests/specify_cli/doctrine/test_pack_validator.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – ASSET sidecar validator + safety contract

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for the frontmatter profile before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Validate the ASSET sidecar `*.asset.yaml` manifest and enforce the loose-contract safety rules — **without**
growing the already-large validator inline.

Done when:
- An `AssetManifest` Pydantic model (id/mime/path + optional title) is registered in `_artifact_schema_registry`
  with glob `*.asset.yaml`. The blob is never scanned (there is **no** "skip the blob schema" branch to write).
- A **separate** `_validate_asset_manifests(pack_dir, ...)` pass runs alongside `_validate_drg` (NOT inline in
  the branchy `_scan_artifact_directory` per-file loop).
- Path-containment reuses `org_pack_config.effective_root` / `OrgPackSubdirEscapeError`; an absolute/`..`-escape
  `path` → `asset_path_escape`.
- mime validation: `type/subtype` shape AND consistent with the path extension (`mimetypes.guess_type`) →
  `asset_mime_invalid` on mismatch.
- The `assets/built-in/` convention is documented on disk; red-first tests cover manifest + containment + mime.

## Context & Constraints

- Plan IC-03 + IC-04. Research **D-02, D-06, D-07, D-08 (revised), D-12**. Spec **FR-005/006/009/010**,
  **NFR-005**. Contract **AT-1, AT-2, AT-4, AT-5, AT-8**.
- Ground truth: `pack_validator.py:145` `_artifact_schema_registry`, `:206` `_scan_artifact_directory`,
  `:223/:289` per-pack `seen_ids` (per-pack-per-type — global uniqueness is WP03's merge scan, NOT here),
  `:367-371` the `_validate_drg` invocation seam (model your new pass on it). `pack_validator.py` is **1082 LOC**
  — extract helpers (`_validate_asset_manifest`, `_check_asset_path_containment`, `_check_asset_mime`); keep each
  ≤15 complexity (NFR-002).
- Containment reuse: `org_pack_config.py:210-249` `effective_root` (resolve-then-`relative_to`, `strict=False`,
  pack-root-aware) + `OrgPackSubdirEscapeError`. If a tiny public wrapper is needed to reuse it, add it in
  `org_pack_config.py` (you own that file) — do **not** hand-roll a 6th containment implementation.
- `_OrgDRGNode` is NOT yours and stays unchanged (asset metadata is sidecar-only).
- Depends on **WP01** (ASSET kind).

## Branch Strategy
- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (worktree per lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T014 – `AssetManifest` model + registry entry
- **Steps**: define `AssetManifest` (required `id: str`, `mime: str`, `path: str`; optional `title: str`).
  Register `(glob="*.asset.yaml", model=AssetManifest)` in `_artifact_schema_registry`. The scan loop then
  validates the manifest just like the 9 kinds' yaml — no special blob-skip branch.
- **Files**: `src/specify_cli/doctrine/pack_validator.py`.

### T015 – Separate `_validate_asset_manifests` pass
- **Steps**: add a pass invoked once per pack (mirroring the `if drg_dir.is_dir(): _validate_drg(...)` seam at
  `:367-371`), NOT inside `_scan_artifact_directory`. It iterates the pack's `assets/<pack>/` manifests and runs
  containment + mime checks.
- **Files**: `src/specify_cli/doctrine/pack_validator.py`.

### T016 – Path-containment (reused helper)
- **Steps**: resolve `manifest.path` under the owning `assets/<pack>/` root via `effective_root`; absolute or
  `..`-escape → raise/emit `asset_path_escape`. Reuse `OrgPackSubdirEscapeError`; translate to the structured
  validator error.
- **Files**: `src/specify_cli/doctrine/pack_validator.py`, `src/doctrine/drg/org_pack_config.py` (only if a
  public wrapper is required).

### T017 – mime validation
- **Steps**: assert `mime` matches `type/subtype` (a `/`-split with non-empty halves) AND
  `mimetypes.guess_type(path)` is consistent with it; mismatch → `asset_mime_invalid`.
- **Files**: `src/specify_cli/doctrine/pack_validator.py`.

### T018 – `assets/built-in/` convention + red-first tests
- **Steps**: create `src/doctrine/assets/built-in/README.md` documenting the sidecar convention (so the tree
  exists and is discoverable). Write red-first tests: valid manifest passes; missing/blank id → error;
  `path: ../../../etc/passwd` → `asset_path_escape`; `mime: notamimetype` and `mime: image/png` with a `.txt`
  path → `asset_mime_invalid`.
- **Files**: `tests/specify_cli/doctrine/test_pack_validator.py`, `src/doctrine/assets/built-in/README.md`.

## Test Strategy
`PWHEADLESS=1 pytest tests/specify_cli/doctrine/test_pack_validator.py -q`. Author the fail-loud tests RED
before the enforcement (ATDD-first). Realistic fixture data (a real png-shaped manifest), not toy placeholders.

## Risks & Mitigations
- **Complexity ceiling**: `pack_validator.py` is 1082 LOC — extract small helpers; do not inline the new pass.
- **Duplicating containment**: reuse `effective_root`; a 6th copy is a review reject.
- **Confusing per-pack vs global uniqueness**: this WP does NOT enforce global id-uniqueness — that is WP03's
  merge scan. Here only manifest well-formedness + containment + mime.

## Review Guidance
- Confirm the manifest is the validated surface (blob never scanned), the containment helper is reused (not
  re-implemented), the new pass is separate from `_scan_artifact_directory`, and each new helper is ≤15 complexity
  with a focused test.

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T11:02:31Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Assigned agent via action command
- 2026-07-09T11:17:39Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Ready: AssetManifest model + registry entry (T014), separate _validate_asset_manifests pass mirroring _validate_drg seam (T015), path containment reusing new resolve_relative_path_within_root/OrgPackSubdirEscapeError shared primitive (T016, also folded into OrgPackConfig.effective_root), mime type/subtype + guess_type consistency check (T017), assets/built-in/README.md + red-first tests (T018). 27/27 tests green: PWHEADLESS=1 uv run pytest tests/specify_cli/doctrine/test_pack_validator.py -q. ruff check exit 0, mypy exit 0 on all touched files. No global id-uniqueness enforced (WP03's scope).
- 2026-07-09T11:18:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=1769942 – Started review via action command
- 2026-07-09T11:24:10Z – user – shell_pid=1769942 – Review passed: AssetManifest (id/mime/path req, title opt) registered with glob *.asset.yaml, blob never scanned (no blob-skip branch); containment+mime in SEPARATE _validate_asset_manifests pass mirroring the _validate_drg seam (helpers small, <=15); containment REUSES shared resolve_relative_path_within_root primitive (effective_root refactored to also delegate — net consolidation, NOT a 6th hand-rolled copy, D-12 satisfied); mime type/subtype + mimetypes.guess_type consistency -> asset_mime_invalid; NO global id-uniqueness here (correctly WP03 scope); distinct structured errors asset_path_escape/asset_mime_invalid asserted by category; realistic red-first tests 27/27 green; ruff+mypy clean on all touched source; org_pack subdir tests (50) still green after primitive extraction.
