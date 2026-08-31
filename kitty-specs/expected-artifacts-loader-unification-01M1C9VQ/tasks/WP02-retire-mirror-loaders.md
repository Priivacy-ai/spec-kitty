---
work_package_id: WP02
title: Retire the Three Mirror Loaders
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- FR-006
planning_base_branch: fix/expected-artifacts-loader-unification
merge_target_branch: fix/expected-artifacts-loader-unification
branch_strategy: Planning artifacts for this mission were generated on fix/expected-artifacts-loader-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/expected-artifacts-loader-unification unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 2 - Consolidation
history:
- timestamp: '2026-08-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/runtime/resolver.py
create_intent:
- tests/runtime/next/test_presence_filenames.py
execution_mode: code_change
mission_id: 01M1C9VQZ28CFRW741WRADS6SZ
owned_files:
- src/specify_cli/runtime/resolver.py
- src/runtime/next/runtime_bridge_io.py
- src/charter/activation/mission_type_profiles.py
- tests/specify_cli/runtime/test_configured_artifact_name.py
- tests/runtime/next/test_presence_filenames.py
tags: []
tracker_refs: []
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Retire the three surviving mirror loaders by re-pointing each at the WP01
authority (`charter/activation/manifest_loader.load_manifest`), so exactly one
implementation of the org→built-in-precedence + `model_validate` logic remains
(FR-004, FR-005, FR-006). Each re-point preserves its caller's observable
behavior — this WP is **all characterization, green-stays-green**; nothing here
carries `@pytest.mark.regression`. The behavioral fail-loud change lives in WP03
(org tier); this WP only removes the duplicate load logic and threads the new
authority through.

## Context & Constraints

- **The three mirrors:**
  - `resolver._load_expected_artifact_manifest` (`src/specify_cli/runtime/resolver.py:557`) —
    an uncached duplicate.
  - `runtime_bridge_io._presence_filenames_for` (`src/runtime/next/runtime_bridge_io.py:841`) —
    an uncached mirror that projects to a `frozenset`.
  - `mission_type_profiles._resolve_expected_artifacts_slot`
    (`src/charter/activation/mission_type_profiles.py:1093`) — returns a RAW,
    unvalidated mapping today.
- **Tri-state is off-limits (C-002, #3729).** The `blocking_artifact_names`
  None-vs-`frozenset()` tri-state and the guard-table short-circuit
  (`cores.py:721-723`, C-003) must NOT change. In T007 keep ONLY the projection;
  absent ⇒ `frozenset()`, never `None`. In T008 keep absent ⇒ `None`.
- **Malformation semantics.** Because these delegate to the authority, a malformed
  manifest will now *propagate* from the authority. That propagation is correct
  and desired, but the org-tier raise itself is implemented in WP03 — here you
  just ensure the delegate does not re-swallow it (no `except` that catches
  `MalformedManifestError`/`ManifestSchemaError`).
- **Depends on WP01** — the authority + shim must exist first.

## Subtasks & Detailed Guidance

### T006 — [P] Retire the resolver mirror (FR-004)

**Purpose.** Replace `resolver._load_expected_artifact_manifest`'s duplicate
load+validate body with a delegate to the authority, keeping its public callers'
behavior identical.

**Steps.**
1. Rewrite `_load_expected_artifact_manifest` (`resolver.py:557`) to call
   `charter.activation.manifest_loader.load_manifest(mission_type, repo_root=...)`.
2. Delete the now-dead local `model_validate` / precedence code it duplicated.
3. Do NOT add any `except` that swallows malformed/schema errors — let them
   propagate exactly as the authority raises them.
4. Preserve the signature and return type the resolver's callers expect
   (`ExpectedArtifactManifest | None`).

**Files.** `src/specify_cli/runtime/resolver.py`.

**Validation.** `test_configured_artifact_name` passes unchanged (NFR-001).
`grep -n model_validate src/specify_cli/runtime/resolver.py` returns nothing.

### T007 — [P] Retire the runtime-bridge mirror, keep only the projection (FR-005)

**Purpose.** Have `_presence_filenames_for` obtain its manifest from the authority
and keep ONLY the `project_artifact_name_set` → `frozenset` projection step. Do
NOT touch the None-vs-`frozenset` tri-state.

**Steps.**
1. Rewrite `_presence_filenames_for` (`runtime_bridge_io.py:841`) to call the
   authority for the manifest, then apply its existing
   `project_artifact_name_set` → `frozenset()` projection.
2. **Absent manifest ⇒ `frozenset()`** (NOT `None`). Keep this exactly as today —
   the empty frozenset is the projection's absence output, unrelated to the
   `blocking_artifact_names` tri-state.
3. **Malformed manifest ⇒ propagate BEFORE the projection.** Because the authority
   raises `MalformedManifestError` before returning, the projection is never
   reached — do not wrap it in a swallowing `try`.
4. Delete the duplicated load body.
5. Remove the now-dead `ManifestSchemaError` / `ValidationError` imports in
   `runtime_bridge_io.py` after re-pointing — the mirror no longer validates or
   wraps, so those imports go unused (ruff F401, NFR-003 zero-new lint debt).

**Files.** `src/runtime/next/runtime_bridge_io.py`.

**Validation.** Bridge-parity suite passes unchanged; a new
`tests/runtime/next/test_presence_filenames.py` characterizes absent ⇒
`frozenset()` and (once WP03 lands) malformed ⇒ propagate. Tag characterization.

### T008 — [P] Re-point the charter-tier slot at a VALIDATED manifest (FR-006)

**Purpose.** Have `_resolve_expected_artifacts_slot` obtain a **validated**
manifest from the authority (it previously returned a raw mapping) — gaining
schema validation — while keeping its guard-table short-circuit input unchanged.

**Steps.**
1. Rewrite `_resolve_expected_artifacts_slot` (`mission_type_profiles.py:1093`) to
   call the authority instead of reading a raw mapping.
2. **Absent ⇒ `None`** (guard-table short-circuit input unchanged, C-003).
3. **Malformed ⇒ raise BEFORE any guard-table / None-vs-present decision** — the
   authority raises before returning, so the slot never makes a None decision on a
   malformed file. Do not add a swallowing `except`.
4. This is the caller that most needed the fix — it previously bypassed schema
   validation entirely.

**Files.** `src/charter/activation/mission_type_profiles.py`.

**Validation.** Existing slot characterization tests pass; the slot now surfaces
`ManifestSchemaError` for a schema-invalid file (add a focused characterization
test). C-001 preserved (this is a charter module calling a charter authority).

### T009 — Update parity / characterization tests

**Purpose.** Prove NFR-001 byte-compatibility across all three re-points.

**Steps.**
1. Run and, where signatures shifted, update the bridge-parity,
   `test_configured_artifact_name`, and slot characterization suites.
2. Ensure every assertion is green-stays-green; add no `@pytest.mark.regression`.
3. Add focused characterization for: resolver delegate parity, bridge absent ⇒
   `frozenset()`, slot absent ⇒ `None` and slot schema-invalid ⇒ `ManifestSchemaError`.

**Files.** `tests/specify_cli/runtime/test_configured_artifact_name.py`,
`tests/runtime/next/test_presence_filenames.py`.

**Validation.** All three suites green; the three mirror `model_validate`/load
bodies are gone (`grep` proof feeds WP05/T021).

## Branch Strategy

Planning artifacts were generated on `fix/expected-artifacts-loader-unification`.
During `/spec-kitty.implement` this WP's execution workspace (worktree) is
allocated per-lane from `lanes.json` by `resolve_workspace_for_wp` — do not
reconstruct the path. Completed changes merge back into
`fix/expected-artifacts-loader-unification` unless the human redirects. WP02 is a
parallel stream after WP01 (peer of WP03); coordinate on the shared authority
signature. Final PR targets upstream as a DRAFT — the operator merges.

## Definition of Done

- All three mirrors delegate to `charter.activation.manifest_loader.load_manifest`;
  no `model_validate` or duplicate precedence code remains in the three modules.
- T007 keeps ONLY the projection (absent ⇒ `frozenset()`), tri-state untouched.
- T008 gains validation (absent ⇒ `None`), guard-table short-circuit untouched.
- No delegate swallows `MalformedManifestError` / `ManifestSchemaError`.
- Parity/characterization suites green; zero `@regression` added.
- `ruff` + `mypy` zero-new; ≤15 complexity per touched function.

## Risks

- **Re-swallowing.** An over-defensive `except` on any delegate re-buries the
  malformed signal and silently re-opens #3412 at that caller. Do not add one.
- **Tri-state contamination.** Confusing the projection's absent-⇒-`frozenset()`
  with the `blocking_artifact_names` tri-state (#3729). They are different layers.
- **Signature skew.** WP01's authority signature is `load_manifest(mission_type,
  repo_root=None)`; a caller passing a different shape gets subtle drift — match it.
- **Ordering vs WP03.** The malformed-propagation characterization only goes
  green once WP03 makes the org reader raise; sequence the test expectations.

## Reviewer Guidance

- Grep the three modules for `model_validate` and for local YAML/precedence code —
  there must be none left.
- Confirm no delegate adds an `except` catching the sibling errors.
- Verify T007 still returns `frozenset()` (not `None`) for absent, and T008 still
  returns `None` for absent — the tri-state and short-circuit inputs are unchanged.
- Confirm all tests are characterization (no `@regression`).
