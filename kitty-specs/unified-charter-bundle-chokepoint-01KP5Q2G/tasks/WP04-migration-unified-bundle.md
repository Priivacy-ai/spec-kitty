---
work_package_id: WP04
title: Migration m_3_2_3_unified_bundle.py
dependencies:
- WP03
requirement_refs:
- FR-007
- FR-008
- FR-013
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
agent: "codex:gpt-5:python-reviewer:reviewer"
shell_pid: "26285"
history:
- at: '2026-04-14T11:16:00Z'
  actor: claude
  event: created
authoritative_surface: src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py
- src/specify_cli/upgrade/migrations/__init__.py
- tests/upgrade/test_unified_bundle_migration.py
- tests/upgrade/fixtures/unified_bundle/**
- CHANGELOG.md
- kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP04.yaml
tags: []
---

# WP04 — Migration `m_3_2_3_unified_bundle.py`

**Tracks**: [Priivacy-ai/spec-kitty#479](https://github.com/Priivacy-ai/spec-kitty/issues/479)
**Depends on**: WP03 (chokepoint and bundle contract must be live)
**Merges to**: `main`

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution mode**: lane-based worktree allocated by `finalize-tasks`. Run `spec-kitty agent action implement WP04 --agent <name> --mission unified-charter-bundle-chokepoint-01KP5Q2G`.

---

## Objective

Land the registry-discoverable migration `m_3_2_3_unified_bundle.py` that advances a populated 3.x project to post-Phase-2 state: validates the bundle against `CharterBundleManifest` v1.0.0, invokes the chokepoint to regenerate missing derivatives, and emits a structured JSON report. **Scope is intentionally narrow.** The migration does NOT scan worktrees, NOT remove symlinks, NOT reconcile `.gitignore` — all three were artifacts of the pre-design-review scope bugs that P1 #1 and P1 #2 corrected.

Ship the FR-013 fixture matrix test, the `CHANGELOG.md` entry, and the final mission-level occurrence index.

## Context

- EPIC: [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
- Phase 2 tracking: [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)
- WP tracking issue: [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479)
- Design-review corrections: migration filename is `m_3_2_3_unified_bundle.py` (C-008); v1.0.0 manifest scope only (C-012); no worktree scanning (C-011 adjacent).

## Authoritative files (read before starting)

- [spec.md](../spec.md) — FR-007, FR-008, FR-013, FR-015; C-001, C-002, C-007, C-008, C-011, C-012
- [plan.md](../plan.md) — WP2.4 section + D-12 (gitignore policy — no-op on first apply)
- [data-model.md](../data-model.md) — `MigrationReport` entity
- [contracts/migration-report.schema.json](../contracts/migration-report.schema.json) — JSON Schema for the report
- [quickstart.md](../quickstart.md) — WP04 smoke-check recipe, common pitfalls

Reference migrations to study before writing:
- `src/specify_cli/upgrade/migrations/m_3_2_0_update_planning_templates.py` — most recent 3.2.x migration pattern
- `src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py` — Phase 1 charter-touching migration
- `src/specify_cli/upgrade/migrations/__init__.py` — registry auto-discovery pattern

---

## Subtask details

### T025 — Create `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py`

**Purpose**: The migration module itself. Small, focused, idempotent.

**Steps**:

1. Create `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` (new, ~160 lines).

   Pattern matches `m_3_2_0_update_planning_templates.py:50-60`. Structure:

   ```python
   """Migration m_3_2_3_unified_bundle: advance project to unified bundle (v1.0.0).

   Phase 2 migration. On apply:
       (a) Detect whether .kittify/charter/charter.md exists at the canonical root.
       (b) If yes, validate the bundle against CharterBundleManifest v1.0.0.
       (c) Invoke ensure_charter_bundle_fresh() to regenerate any missing derivatives.
       (d) Emit a structured JSON report per contracts/migration-report.schema.json.

   Explicitly OUT OF SCOPE:
       - Scanning or modifying worktrees (C-011).
       - Removing symlinks.
       - Reconciling .gitignore (v1.0.0 manifest already matches current .gitignore).
   """
   from __future__ import annotations

   import time
   from pathlib import Path
   from typing import Any

   from ._base import Migration  # Adjust import per actual registry pattern.


   MIGRATION_ID = "m_3_2_3_unified_bundle"
   TARGET_VERSION = "3.2.3"


   class UnifiedBundleMigration(Migration):
       migration_id = MIGRATION_ID
       target_version = TARGET_VERSION

       def apply(self, project_path: Path, dry_run: bool = False) -> dict[str, Any]:
           start_ns = time.monotonic_ns()
           errors: list[str] = []
           applied = False
           chokepoint_refreshed = False

           # Lazy imports to avoid cost at registry-discovery time.
           from charter.bundle import CANONICAL_MANIFEST
           from charter.resolution import resolve_canonical_repo_root
           from charter.sync import ensure_charter_bundle_fresh

           canonical_root = resolve_canonical_repo_root(project_path)
           charter_md = canonical_root / ".kittify" / "charter" / "charter.md"
           charter_present = charter_md.exists()

           bundle_validation: dict[str, Any] = {
               "passed": True,
               "missing_tracked": [],
               "missing_derived": [],
               "unexpected": [],
           }

           if charter_present:
               # Validate BEFORE refresh to get the pre-refresh snapshot.
               missing_tracked = [str(p) for p in CANONICAL_MANIFEST.tracked_files
                                  if not (canonical_root / p).exists()]
               missing_derived = [str(p) for p in CANONICAL_MANIFEST.derived_files
                                  if not (canonical_root / p).exists()]
               if missing_derived and not dry_run:
                   sync_result = ensure_charter_bundle_fresh(canonical_root)
                   if sync_result and sync_result.synced:
                       chokepoint_refreshed = True
                       applied = True
                       # Re-check after refresh.
                       missing_derived = [str(p) for p in CANONICAL_MANIFEST.derived_files
                                          if not (canonical_root / p).exists()]

               # Enumerate unexpected (out-of-v1.0.0-scope) files.
               charter_dir = canonical_root / ".kittify" / "charter"
               declared = {str(p) for p in CANONICAL_MANIFEST.tracked_files + CANONICAL_MANIFEST.derived_files}
               unexpected = []
               if charter_dir.exists():
                   for p in charter_dir.rglob("*"):
                       rel = str(p.relative_to(canonical_root))
                       if p.is_file() and rel not in declared:
                           unexpected.append(rel)

               bundle_validation = {
                   "passed": not missing_tracked and not missing_derived,
                   "missing_tracked": missing_tracked,
                   "missing_derived": missing_derived,
                   "unexpected": sorted(unexpected),
               }

           duration_ms = int((time.monotonic_ns() - start_ns) / 1_000_000)

           return {
               "migration_id": MIGRATION_ID,
               "target_version": TARGET_VERSION,
               "applied": applied,
               "charter_present": charter_present,
               "bundle_validation": bundle_validation,
               "chokepoint_refreshed": chokepoint_refreshed,
               "errors": errors,
               "duration_ms": duration_ms,
           }
   ```

2. The exact `Migration` base-class signature depends on the existing registry pattern. Consult `m_3_2_0_update_planning_templates.py` and `_base.py` (if present). Match conventions.

3. **Idempotency**: on re-apply, `bundle_validation.missing_derived` is empty → no `ensure_charter_bundle_fresh` call → `applied=False`, `chokepoint_refreshed=False`, `errors=[]`. This is the no-op path.

4. **Do NOT touch**: worktrees, any symlink, any `.gitignore`, `.kittify/memory`, `.kittify/AGENTS.md`.

**Files**:
- `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` (new, ~160 lines)

**Validation**:
- [ ] `mypy --strict src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` passes.
- [ ] `python -c "from specify_cli.upgrade.migrations.m_3_2_3_unified_bundle import UnifiedBundleMigration; print(UnifiedBundleMigration.target_version)"` prints `3.2.3`.

---

### T026 — Write `tests/upgrade/test_unified_bundle_migration.py`

**Purpose**: Exercise the full FR-013 fixture matrix. Prove idempotency and the JSON report shape.

**Steps**:

1. Create `tests/upgrade/test_unified_bundle_migration.py` (new, ~250 lines). Fixtures (one per FR-013 row):

   - **Fixture (a)** `pre_phase_2_with_full_derivatives`: tmp repo with `charter.md` tracked and all three derivatives present, hashes matching.
   - **Fixture (b)** `pre_phase_2_no_derivatives`: tmp repo with `charter.md` tracked, no derivatives on disk.
   - **Fixture (c)** `phase_2_shaped_already_applied`: tmp repo with the post-Phase-2 state. Migration must be a no-op.
   - **Fixture (d)** `stale_metadata_hash`: tmp repo where `metadata.yaml` hash does NOT match `charter.md`. Chokepoint must refresh during the migration.
   - **Fixture (e)** `no_charter`: tmp repo with no `.kittify/charter/charter.md`. Migration must report `charter_present: false, applied: false`.

2. Test cases:
   - `test_fixture_a_passes_bundle_validation_no_chokepoint_refresh()` — `applied: False` (derivatives already present), `chokepoint_refreshed: False`.
   - `test_fixture_b_chokepoint_refreshes_derivatives()` — `applied: True`, `chokepoint_refreshed: True`, `bundle_validation.missing_derived: []` post-refresh.
   - `test_fixture_c_second_apply_is_no_op()` — run migration twice on the same fixture; second run has `applied: False`, `chokepoint_refreshed: False`, `errors: []`.
   - `test_fixture_d_stale_metadata_triggers_refresh()` — `chokepoint_refreshed: True`.
   - `test_fixture_e_no_charter_is_clean_no_op()` — `charter_present: False`, `applied: False`, `bundle_validation.passed: True`.
   - `test_report_matches_schema()` — validate JSON output against `contracts/migration-report.schema.json` using `jsonschema`.
   - `test_migration_does_not_touch_worktree()` — set up a fixture with a pre-existing `.worktrees/foo/` containing a file; run migration; assert the worktree is untouched.
   - `test_migration_does_not_touch_gitignore()` — record `.gitignore` mtime + content before; run migration; assert unchanged.
   - `test_migration_does_not_touch_memory_symlinks()` — fixture with `.kittify/memory` / `.kittify/AGENTS.md` files (simulated); migration leaves them alone.
   - `test_duration_ms_under_2000()` — assert `duration_ms <= 2000` on fixture (a) or (b).

**Files**:
- `tests/upgrade/test_unified_bundle_migration.py` (new, ~250 lines)
- `tests/upgrade/fixtures/unified_bundle/` (new — may be fixture-helper code or committed sample files)

**Validation**:
- [ ] `pytest tests/upgrade/test_unified_bundle_migration.py` green (10 tests).

---

### T027 — Register migration in `__init__.py` (if required)

**Purpose**: Ensure the registry discovers the new migration.

**Steps**:

1. Check the pattern in `src/specify_cli/upgrade/migrations/__init__.py`. If registrations are explicit (e.g., an `__all__` list or a `REGISTRY = [...]`):
   - Add `m_3_2_3_unified_bundle` to the list.
   - Preserve ordering (registry is version-sorted typically).

2. If auto-discovery is the pattern (glob over `m_*.py`): no edit needed; the new file is picked up automatically. Just run the registry auto-discovery and verify the migration ID appears.

**Files**:
- `src/specify_cli/upgrade/migrations/__init__.py` (modified only if explicit registration is required)

**Validation**:
- [ ] `python -c "from specify_cli.upgrade.migrations import MigrationRegistry; r = MigrationRegistry.auto_discover(); ids = [m.migration_id for m in r.migrations]; assert 'm_3_2_3_unified_bundle' in ids"` succeeds.

---

### T028 — `CHANGELOG.md` entry + post `#464` tracking comment

**Purpose**: Document the release-visible behavior change per spec §Success Criterion 11 and close the filename loop on issue #464.

**Steps**:

1. Add a new entry to `CHANGELOG.md` at the top of the unreleased section (format per existing repo convention):

   ```markdown
   ### Added
   - Unified charter bundle manifest v1.0.0 at `src/charter/bundle.py` declaring the three `sync()`-produced derivatives as the authoritative bundle contract.
   - Canonical-root resolver at `src/charter/resolution.py`; readers running inside a git worktree now transparently see the main-checkout charter bundle.
   - `spec-kitty charter bundle validate [--json]` CLI for operator and CI bundle-health checks.
   - Migration `m_3_2_3_unified_bundle` advances 3.x projects to the unified bundle layout (idempotent; no worktree scanning, no symlink removal, no .gitignore reconciliation).

   ### Changed
   - `SyncResult` extended with `canonical_root: Path`; `files_written` continues to be relative to that root. Existing readers rewired in lockstep; no back-compat shim.
   - `ensure_charter_bundle_fresh()` is now the sole chokepoint for readers of `governance.yaml`, `directives.yaml`, and `metadata.yaml`. Direct reads of those files are forbidden (verified by AST-walk test).

   ### Unchanged (explicitly)
   - `.kittify/memory/` and `.kittify/AGENTS.md` symlinks in worktrees — these are project-memory and agent-instructions sharing, documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179`. They are NOT part of the charter bundle and are out of scope for this tranche.
   - Files under `.kittify/charter/` that are not v1.0.0 manifest files (`references.yaml`, `context-state.json`, `interview/answers.yaml`, `library/*.md`) are unchanged; they are produced by other pipelines.
   ```

2. Post a tracking comment on [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) summarizing:
   - Migration filename is `m_3_2_3_unified_bundle.py` (C-008 — slots 3.2.0/3.2.1/3.2.2 were already taken).
   - Manifest v1.0.0 scope narrowed to `sync()`-produced files only (C-012).
   - Worktree memory/AGENTS symlink removal was not the actual fix; canonical-root resolution is (C-011, superseding #339's original proposal).

**Files**:
- `CHANGELOG.md` (modified — new entry block)

**Validation**:
- [ ] `CHANGELOG.md` entry visible in `git diff`.
- [ ] Comment posted on #464 (manual step; reviewer confirms).

---

### T029 — Author `occurrences/WP04.yaml` + finalize `index.yaml`

**Purpose**: Close out the mission-level occurrence classification.

**Steps**:

1. Create `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP04.yaml`:

   ```yaml
   wp_id: WP04
   mission_slug: unified-charter-bundle-chokepoint-01KP5Q2G
   requires_merged: [WP01, WP02, WP03]
   categories:
     filesystem_path_literal:
       description: "Migration module path + test fixtures."
       include: ["src/specify_cli/upgrade/migrations/**", "tests/upgrade/**"]
       exclude: []
       occurrences:
         - path: src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py
           pattern: "m_3_2_3_unified_bundle"
           action: leave
           rationale: New migration identifier.
     symbol_name:
       description: "New migration class symbol."
       include: ["src/specify_cli/upgrade/migrations/**", "tests/upgrade/**"]
       exclude: []
       occurrences:
         - path: src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py
           pattern: "UnifiedBundleMigration"
           action: leave
     test_identifier:
       description: "Migration test module."
       include: ["tests/upgrade/**"]
       exclude: []
       occurrences:
         - path: tests/upgrade/test_unified_bundle_migration.py
           pattern: "test_.*"
           action: leave
   carve_outs: []
   must_be_zero_after:
     - "worktrees_scanned"  # In v1.0.0 migration report schema — this field must NOT exist.
     - "symlinks_removed"
     - "copies_removed"
     - "git_exclude_entries_removed"
     - "gitignore_reconciled"
   verification_notes: |
     WP04 pins the narrow migration scope. The "must_be_zero_after" entries
     verify that the migration's JSON report does not include the dropped
     fields from the pre-design-review schema.
   ```

2. Finalize `occurrences/index.yaml`:
   - Add WP04 to `wps`.
   - Ensure the mission-level `must_be_zero_after` set matches NFR-005 exactly:
     ```yaml
     must_be_zero_after:
       - "direct_read_of_governance_yaml_bypassing_chokepoint"
       - "direct_read_of_directives_yaml_bypassing_chokepoint"
       - "direct_read_of_metadata_yaml_bypassing_chokepoint"
       - "fr004_reader_missing_ensure_charter_bundle_fresh_call"
       - "chokepoint_not_calling_resolve_canonical_repo_root"
     ```
   - Confirm all carve-outs are present and correctly justified.

**Files**:
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP04.yaml` (new)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml` (finalized)

**Validation**:
- [ ] `python scripts/verify_occurrences.py kitty-specs/.../occurrences/WP04.yaml` exits 0.
- [ ] `python scripts/verify_occurrences.py kitty-specs/.../occurrences/index.yaml` exits 0 (mission-level verification).

---

## Definition of Done

- [ ] T025–T029 all complete.
- [ ] `pytest tests/upgrade/test_unified_bundle_migration.py` green (10 tests).
- [ ] `mypy --strict` green across all modified files.
- [ ] Registry auto-discovers `m_3_2_3_unified_bundle`.
- [ ] `spec-kitty upgrade --json` on FR-013 reference fixture completes in ≤2 s and emits a report matching `contracts/migration-report.schema.json`.
- [ ] CHANGELOG entry committed.
- [ ] Tracking comment posted on #464 (manual; reviewer verifies).
- [ ] Verifier green against `WP04.yaml` and the finalized `index.yaml`.
- [ ] All prior WP gates still hold.
- [ ] `grep -rn "worktrees_scanned\|symlinks_removed\|gitignore_reconciled" src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` returns zero rows (scope narrowing verification).

## Risks

- **Scope creep**. The implementer may be tempted to add worktree scanning, symlink removal, or `.gitignore` reconciliation. All three are explicitly dropped in the design-review corrections. If the PR adds any of those behaviors, reject it and reference C-011 / C-012.
- **Idempotency bug**. Fixture (c) must pass with `applied: False` on second apply. Any stateful side effect — writes to a registry file, a marker file, etc. — risks breaking idempotency.
- **Mistaken import ordering**. The migration imports `charter.bundle`, `charter.resolution`, `charter.sync` — all lazy (inside `apply()`) to avoid cost at registry-discovery time. Inlining imports at module-top can slow boot and potentially create cycles.
- **Fixture realism**. The FR-013 fixtures must look like real pre-Phase-2 / post-Phase-2 project layouts. An overly synthetic fixture may pass the tests while a real project fails the upgrade.

## Reviewer guidance

- Read the migration module top-to-bottom; confirm no filesystem writes outside `.kittify/charter/` (no worktree scanning, no `.gitignore` edits, no symlink operations).
- Verify the JSON report from fixture (a) matches `contracts/migration-report.schema.json` using `jsonschema.validate()` — call this out in code review.
- Run `pytest tests/upgrade/test_unified_bundle_migration.py::test_fixture_c_second_apply_is_no_op` specifically and verify it passes twice in a row.
- Confirm the CHANGELOG entry includes the "Unchanged (explicitly)" block — this is the visible documentation of the C-011 carve-out for operators reading release notes.
- Verify the `#464` tracking comment is posted with the three bullets (filename, scope, worktree-framing correction).

## Activity Log

- 2026-04-14T15:05:05Z – claude:sonnet:implementer:implementer – shell_pid=17894 – Started implementation via action command
- 2026-04-14T15:15:43Z – claude:sonnet:implementer:implementer – shell_pid=17894 – WP04 migration complete: m_3_2_3_unified_bundle.py registered (auto-discovery), FR-013 fixture matrix green (12/12), CHANGELOG updated, occurrence artifact authored + mission index finalized. Scope respected: no worktree scanning, no symlink removal, no gitignore reconciliation. Verifier green for WP04.yaml and index.yaml. NFR-006 duration_ms=22ms.
- 2026-04-14T15:16:38Z – codex:gpt-5:python-reviewer:reviewer – shell_pid=26285 – Started review via action command
- 2026-04-14T15:21:48Z – codex:gpt-5:python-reviewer:reviewer – shell_pid=26285 – Moved to planned
