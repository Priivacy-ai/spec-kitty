---
work_package_id: WP02
title: Charter Bundle Validation Repair
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: fix/cli-bug-sweep-tool-surface-self-registration
merge_target_branch: fix/cli-bug-sweep-tool-surface-self-registration
branch_strategy: Planning artifacts for this mission were generated on fix/cli-bug-sweep-tool-surface-self-registration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cli-bug-sweep-tool-surface-self-registration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-bug-sweep-tool-surface-self-registration-01KV5AWE
base_commit: 145670caf7e7bedcb30ef3ea108690f8b8aacfc4
created_at: '2026-06-15T11:24:31.093929+00:00'
subtasks:
- T004
- T005
- T006
- T007
- T008
agent: claude
shell_pid: '16428'
history:
- date: '2026-06-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/specify_cli/charter/test_bundle_validate_fresh_seed.py
execution_mode: code_change
owned_files:
- .kittify/charter/provenance/**
- src/charter/synthesizer/artifact_naming.py
- src/charter/synthesizer/write_pipeline.py
- src/charter/bundle.py
- tests/specify_cli/charter/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Fix `spec-kitty charter bundle validate` so it exits 0 on a fresh checkout of the spec-kitty repository with no project-level synthesis artifacts. There are three interlocking defects to address.

## Branch Strategy

- **Implementation branch**: allocated by `spec-kitty agent action implement WP02 --agent claude`
- **Planning/base branch**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Final merge target**: `fix/cli-bug-sweep-tool-surface-self-registration`

## Context

### The three defects (confirmed by Debugger Debbie investigation)

**Defect 1 — Stale sidecars (T004)**: Seven `adapter_id: fixture` placeholder files are tracked in `.kittify/charter/provenance/`. They were committed in commit `0b6e2d7d9` without corresponding generated artifacts. The validator finds them, looks for their artifacts, finds nothing, and fails.

**Defect 2 — Plural/singular mismatch (T005, T006)**: `doctrine_kind_subdir()` in `src/charter/synthesizer/artifact_naming.py` maps kinds to plural directories (`directives/`, `tactics/`, `styleguides/`). The `.gitignore` must whitelist only singular directories (`directive/`, `tactic/`, `styleguide/`). Synthesized artifacts are structurally ungittrackable when produced under plural directories. The validator's `_find_artifact()` does `doctrine_root.rglob("*.directive.yaml")` which hits nothing because no plural-dir artifacts exist.

**Defect 3 — Validator early-exit gap (T007)**: `validate_synthesis_state()` early-exits only when artifact_files, provenance_files, AND manifest are ALL absent. The seeded `synthesis-manifest.yaml` (`built_in_only: true`, `artifacts: []`) prevents the early-exit even though no synthesis has occurred.

### The correct fix sequence
1. **T004 first**: Remove the stale sidecars so the provenance directory is empty.
2. **T005 + T006 together**: Fix `doctrine_kind_subdir()` and all its callers so future synthesis writes to the correct (singular, gittrackable) directories.
3. **T007 + T008**: Add the `built_in_only` early-exit as a defensive belt-and-suspenders check.

Do NOT change `.gitignore` to whitelist plural dirs — that would allow gitignored synthesizer output into the tracked tree.

---

## Subtask T004 — Remove Stale Provenance Sidecars

**Purpose**: Remove the 7 `adapter_id: fixture` placeholder sidecar files that have no corresponding generated artifacts.

**Steps**:

1. Confirm the 7 files exist:
   ```
   .kittify/charter/provenance/directive-mission-type-scope-directive.yaml
   .kittify/charter/provenance/directive-neutrality-posture-directive.yaml
   .kittify/charter/provenance/directive-risk-appetite-directive.yaml
   .kittify/charter/provenance/styleguide-python-style-guide.yaml
   .kittify/charter/provenance/styleguide-testing-style-guide.yaml
   .kittify/charter/provenance/tactic-how-we-apply-directive-003.yaml
   .kittify/charter/provenance/tactic-testing-philosophy-tactic.yaml
   ```

2. Remove all 7 with `git rm`:
   ```bash
   git rm .kittify/charter/provenance/directive-mission-type-scope-directive.yaml
   git rm .kittify/charter/provenance/directive-neutrality-posture-directive.yaml
   git rm .kittify/charter/provenance/directive-risk-appetite-directive.yaml
   git rm .kittify/charter/provenance/styleguide-python-style-guide.yaml
   git rm .kittify/charter/provenance/styleguide-testing-style-guide.yaml
   git rm .kittify/charter/provenance/tactic-how-we-apply-directive-003.yaml
   git rm .kittify/charter/provenance/tactic-testing-philosophy-tactic.yaml
   ```

3. These are `adapter_id: fixture` bootstrap placeholders. No information is lost by removing them.

**Validation**:
- `ls .kittify/charter/provenance/` returns empty (or only non-fixture files if any were added later).
- `git status` shows 7 deleted files staged.

---

## Subtask T005 — Fix `doctrine_kind_subdir()` to Use Singular Names

**Purpose**: Make the synthesizer write generated artifacts to the correct singular directories that the `.gitignore` policy whitelists.

**Steps**:

1. Read `src/charter/synthesizer/artifact_naming.py` — find `doctrine_kind_subdir()`.

2. Change the return values from plural to singular:
   - `"directives"` → `"directive"`
   - `"tactics"` → `"tactic"`
   - `"styleguides"` → `"styleguide"` (the singular gitignore-whitelisted name)

3. Run `mypy src/charter/synthesizer/artifact_naming.py --strict` — must pass with zero errors.

**Validation**:
- `ruff check src/charter/synthesizer/artifact_naming.py` passes.
- The function returns singular dir names for all supported kinds.

---

## Subtask T006 — Audit Callers in `write_pipeline.py`

**Purpose**: Ensure no hardcoded plural-dir strings in `write_pipeline.py` survive the fix to T005. Missing a caller leaves a dangling plural path that could write artifacts to the wrong directory.

**Steps**:

1. Read `src/charter/synthesizer/write_pipeline.py` in full. Look for:
   - Calls to `doctrine_kind_subdir()` — these will now receive the correct singular name from T005.
   - Any hardcoded string literals with `"directives"`, `"tactics"`, or `"styleguides"` (plural). Lines ~174, ~206, ~584 were flagged in the investigation.

2. For each hardcoded plural string found: replace with the singular equivalent OR refactor to call `doctrine_kind_subdir()` so the mapping is in one place.

3. Read all other files in `src/charter/synthesizer/` for hardcoded plural paths. Fix any found.

4. Do NOT change callers in `src/charter/bundle.py` that call `doctrine_root.rglob(...)` — those search recursively so singular vs. plural subdirs do not affect them (they find by extension, not by parent dir name). Confirm this before leaving bundle.py alone.

**Validation**:
- `grep -rn "directives\|tactics\|styleguides" src/charter/synthesizer/` returns no hardcoded plural-dir strings (only legitimate use of the words in comments or docstrings is acceptable).
- `mypy src/charter/synthesizer/ --strict` passes.
- `ruff check src/charter/synthesizer/` passes.

---

## Subtask T007 — Add `built_in_only` Early-Exit to `validate_synthesis_state()`

**Purpose**: Make the fresh-seed state (`built_in_only: true`, `artifacts: []`) bypass sidecar checking in the validator.

**Steps**:

1. Read `src/charter/bundle.py` — locate `validate_synthesis_state()`. Understand the existing early-exit at the top (the C-012 backward-compatibility gate).

2. After the manifest is loaded (or after `manifest_path.exists()` check), add:
   ```python
   if manifest_path.exists():
       manifest = _load_manifest(manifest_path)  # use whatever the real load function is
       if getattr(manifest, 'built_in_only', False) and not manifest.artifacts:
           # Fresh-seed project: no user synthesis has occurred.
           # Sidecar files (if any) are stale fixtures; do not validate against them.
           result.synthesis_state_present = True
           return result
   ```
   Adapt to the actual manifest loading pattern in this file. Do not introduce a new manifest load if the manifest is already loaded earlier in the function — add the check at the right point in the existing flow.

3. The condition must be BOTH `built_in_only: true` AND `artifacts == []`. Do not suppress validation for repos where `built_in_only` is true but `artifacts` is non-empty (that would be an inconsistent state worth catching).

**Validation**:
- `mypy src/charter/bundle.py --strict` passes with zero errors.
- `ruff check src/charter/bundle.py` passes.

---

## Subtask T008 — Add `built_in_only` Fresh-Seed Test

**Purpose**: Assert that `validate_synthesis_state()` returns no errors when the manifest declares `built_in_only: true` with an empty artifact list, regardless of whether sidecar files are present.

**Steps**:

1. Read the existing tests in `tests/specify_cli/charter/` (or `tests/charter/`) to understand the test patterns for `validate_synthesis_state()`.

2. Add a test that:
   - Creates a temp directory with:
     - `.kittify/charter/synthesis-manifest.yaml` containing `built_in_only: true` and `artifacts: []`
     - No sidecar files in `.kittify/charter/provenance/`
     - No doctrine artifact files
   - Calls `validate_synthesis_state(repo_root)` (or however it is invoked in existing tests)
   - Asserts the result has zero errors and `synthesis_state_present` is (truthy or the appropriate value per the function's contract).

3. Add a second test showing that if sidecars ARE present with `built_in_only: true` + `artifacts: []`, the early-exit still applies and no errors are raised. This is required, not optional — it directly reproduces the pre-fix state (stale sidecars + built_in_only manifest) and confirms the fix is robust.

**Validation**:
- `pytest tests/specify_cli/charter/ -v -k "built_in_only or fresh_seed"` → new test passes.
- `mypy tests/specify_cli/charter/ --strict` passes.

---

## Integration Check

After all five subtasks:

```bash
# Must exit 0 with no synthesis_state errors
spec-kitty charter bundle validate --json

# Full charter test suite must pass
PWHEADLESS=1 pytest tests/specify_cli/charter/ -v

# No regressions
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q
```

## Definition of Done

- [ ] 7 stale sidecar files removed from `.kittify/charter/provenance/`.
- [ ] `doctrine_kind_subdir()` returns singular names.
- [ ] No hardcoded plural-dir strings remain in `src/charter/synthesizer/`.
- [ ] `validate_synthesis_state()` returns success on fresh-seed state.
- [ ] New test for fresh-seed scenario passes.
- [ ] `spec-kitty charter bundle validate --json` exits 0 on a fresh checkout.
- [ ] `mypy src/charter/ --strict` and `ruff check src/charter/` pass.

## Risks for Reviewer

- If any sidecar files in `.kittify/charter/provenance/` were NOT in the original 7 (e.g., added by another mission), do not git rm them blindly — only the 7 listed in spec.md.
- The `built_in_only` early-exit must check `not manifest.artifacts` (or `manifest.artifacts == []`), not just `built_in_only`. A manifest with `built_in_only: true` but non-empty `artifacts` is an edge case that warrants full validation.
- Confirm the field name in the manifest dataclass is `built_in_only` before using `getattr` — read the dataclass definition first.
