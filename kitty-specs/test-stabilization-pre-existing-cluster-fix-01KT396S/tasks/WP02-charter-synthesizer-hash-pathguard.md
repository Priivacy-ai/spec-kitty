---
work_package_id: WP02
title: Charter Synthesizer Hash Determinism + PathGuard
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Execution worktree is allocated per lane from lanes.json. Implement on the lane-B worktree branch. WP06 depends on this WP — complete and get WP02 approved before WP06 begins.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
owned_files:
- src/charter/synthesizer/**/*.py
- tests/charter/synthesizer/test_bundle_validate_extension.py
- tests/charter/synthesizer/test_path_guard.py
- tests/charter/synthesizer/test_manifest.py
- tests/charter/synthesizer/conftest.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Fix the charter synthesizer so that:
1. All write operations go through `PathGuard` (no direct `Path.write_text` / `Path.write_bytes` / `Path.mkdir` / `Path.replace` calls in synthesizer modules).
2. The manifest hash is deterministic: same artifact inputs always produce identical `manifest_hash` regardless of insertion order.

After this WP, `test_manifest`, `test_path_guard`, `test_chokepoint_coverage`, and `test_bundle_validate_cli` must pass.

**GitHub issue closed**: #1303
**Unblocks**: WP06 (charter integration suite)

---

## Context

The charter synthesizer was split from a 3328-line `charter.py` monolith (in WP06/WP08 of mission `test-stabilization-and-debt-pass-01KSF9HJ`) into a per-subcommand package under `src/charter/`. During this split, at least one module bypassed the `PathGuard` chokepoint (FR-016/R-10 requirement). Additionally, the manifest hash computation may not be applying the canonical `(kind, slug)` sort before hashing.

The `PathGuard` class lives at `src/charter/synthesizer/path_guard.py`. All synthesizer write operations must go through its `write_text`, `write_bytes`, `mkdir`, and `replace` methods.

The manifest hash determinism is required by FR-010: same artifact inputs → identical `manifest_hash`. The sort must be applied **before** hash computation, not after.

---

## Subtasks

### T006 — Grep for direct write primitives outside PathGuard

**Steps**:

1. Run the R-10 lint grep:
   ```bash
   grep -rn "\.write_text\|\.write_bytes\|\.mkdir\|\.replace(" \
     src/charter/synthesizer/ \
     --include="*.py" \
     | grep -v "path_guard.py" \
     | grep -v "^Binary"
   ```

2. For each hit, record:
   - File path and line number
   - Which primitive is used (`write_text`, `write_bytes`, `mkdir`, or `replace`)
   - What it is writing (staging file, provenance file, manifest, etc.)

3. Also check for `open(... "w")` or `open(... "wb")` patterns:
   ```bash
   grep -rn 'open(' src/charter/synthesizer/ --include="*.py" | grep -v "path_guard.py"
   ```

**Files**: `src/charter/synthesizer/*.py` (all modules except `path_guard.py`)

**Validation**: List of all direct write calls is complete before proceeding to T007.

---

### T007 — Route all direct writes through PathGuard

**Steps**:

For each hit found in T006:

1. Identify the `PathGuard` instance in scope (it should be passed as a parameter or available via the module's main entry point).

2. Replace the direct call with the corresponding PathGuard method:
   - `path.write_text(content)` → `guard.write_text(path, content)`
   - `path.write_bytes(data)` → `guard.write_bytes(path, data)`
   - `path.mkdir(...)` → `guard.mkdir(path)`
   - `src.replace(dst)` → `guard.replace(src, dst)`
   - `open(path, "w") as f: f.write(...)` → use `guard.write_text(path, content)`

3. If `PathGuard` is not yet in scope for a given module, add it as a parameter to the function/method and thread it through from the caller.

4. Do **not** expand the `extra_allowed_prefixes` of PathGuard to work around violations — the guard must enforce the existing allowed paths.

**Files**: Each file identified in T006.

**Validation**: Re-run the T006 grep — it must return zero hits.

---

### T008 — Verify sort-before-hash in the promote pipeline

**Steps**:

1. Locate the `promote()` function (or equivalent) in `src/charter/synthesizer/`. This is the function that:
   - Takes a list of `ManifestArtifactEntry` items
   - Computes `manifest_hash`
   - Calls `dump_manifest()`

   Search:
   ```bash
   grep -rn "manifest_hash\|promote\|dump_manifest" src/charter/synthesizer/ --include="*.py"
   ```

2. Find where `manifest_hash` is computed. It should be computed from a **sorted** list of artifact entries:
   ```python
   sorted_artifacts = sorted(artifacts, key=lambda a: (a.kind, a.slug))
   # then serialize sorted_artifacts to canonical YAML and hash the bytes
   ```

3. If the sort is missing or applied after serialization: add `sorted(artifacts, key=lambda a: (a.kind, a.slug))` before the serialization step.

4. Confirm that `_make_v2_manifest` in the test fixtures (`tests/charter/synthesizer/conftest.py` or `test_bundle_validate_extension.py`) uses the same sort. If the fixture sorts but the production code does not, the test will catch real divergence.

5. Also verify there are no timestamp fields, random values, or OS-dependent dict ordering in the hashed content. The hash must be a pure function of `(kind, slug, path, provenance_path, content_hash)` for each artifact.

**Files**:
- `src/charter/synthesizer/` (the promote/hash computation module)
- `tests/charter/synthesizer/conftest.py` (fixture alignment)

**Validation**: `test_manifest_hash_is_deterministic` and `test_manifest_hash_is_stable_regardless_of_artifact_insertion_order` pass.

---

### T009 — Regenerate stale test fixtures

**Steps**:

1. Run the target tests first to see what fails:
   ```bash
   pytest tests/charter/synthesizer/test_bundle_validate_extension.py \
          tests/charter/synthesizer/test_manifest.py -v 2>&1 | head -80
   ```

2. If any test fails with a hash mismatch between a stored fixture and a computed hash:
   - The fixture was generated before the sort was added (or before another schema change).
   - Delete the stale fixture file and regenerate it by running the test that creates it.
   - Or if fixtures are inline in the test, update the expected hash value.

3. Never regenerate a fixture just to make a wrong hash "match" — the fixture must represent a correctly-computed hash.

**Files**: Any `*.yaml` fixture files under `tests/charter/synthesizer/` that store expected manifest hashes.

**Validation**: No "hash mismatch between stored fixture and computed" errors in test output.

---

### T010 — Verify all target tests pass

**Steps**:

```bash
pytest tests/charter/synthesizer/test_bundle_validate_extension.py \
       tests/charter/synthesizer/test_path_guard.py \
       tests/charter/synthesizer/test_manifest.py \
       -v 2>&1
```

Expected: all four named tests (`test_manifest`, `test_path_guard`, `test_chokepoint_coverage`, `test_bundle_validate_cli`) pass, along with all other tests in those files.

Then run the broader synthesizer suite:
```bash
pytest tests/charter/synthesizer/ -q
```

Confirm zero new failures compared to the pre-WP02 baseline.

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Worktree allocated per Lane B from `lanes.json`. Run `spec-kitty agent action implement WP02 --agent claude` to enter the correct workspace.

WP06 must not begin until WP02 is in `approved` lane.

---

## Definition of Done

- [ ] Zero direct `Path.write_text` / `.write_bytes` / `.mkdir` / `.replace` calls in `src/charter/synthesizer/` (outside `path_guard.py`)
- [ ] `test_path_guard` passes (including `test_no_direct_writes_in_synthesizer`)
- [ ] `test_manifest_hash_is_deterministic` passes
- [ ] `test_manifest_hash_is_stable_regardless_of_artifact_insertion_order` passes
- [ ] `test_chokepoint_coverage` passes
- [ ] `test_bundle_validate_cli` passes
- [ ] `mypy --strict` passes on all modified modules
- [ ] No previously-passing synthesizer test regresses

## Risks

- **Scope of PathGuard**: PathGuard only allows writes to `.kittify/doctrine/` and `.kittify/charter/`. If a synthesizer module legitimately needs to write to a staging dir outside these paths, the module is architecturally incorrect and needs redesign — do not expand PathGuard's allowed paths to paper over this.
- **Timestamp fields**: If the manifest YAML includes `synthesized_at` or similar timestamps, they must be excluded from the hash computation. Check the `SynthesisManifest` model carefully.

## Reviewer Guidance

1. Confirm the R-10 grep returns zero hits on the diff.
2. Confirm the sort is applied before hash computation — not after.
3. Confirm no `extra_allowed_prefixes` were added to PathGuard.
4. Run `pytest tests/charter/synthesizer/ -q` independently and confirm green.
