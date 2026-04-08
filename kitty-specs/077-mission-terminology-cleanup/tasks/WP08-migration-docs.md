---
work_package_id: WP08
title: Migration Policy Documentation
dependencies:
- WP01
requirement_refs:
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Lane workspace per execution lane (resolved by spec-kitty implement WP08)
subtasks:
- T033
- T034
- T035
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: docs/migration/
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- docs/migration/feature-flag-deprecation.md
- docs/migration/mission-type-flag-deprecation.md
priority: P1
tags: []
---

# WP08 — Migration Policy Documentation

## Objective

Create the two migration doc files referenced from the deprecation warnings emitted by `selector_resolution.py`. These docs are the link target in the warning messages and must explain the deprecation rationale, removal criteria, suppression env vars, and provide migration commands for legacy scripts.

This is FR-013 and supports NFR-002, NFR-003 from the spec.

## Context

The deprecation warning emitted by `selector_resolution.py` (defined in WP02) looks like:
```
Warning: --feature is deprecated; use --mission. See: docs/migration/feature-flag-deprecation.md
```

The path `docs/migration/feature-flag-deprecation.md` is what this WP creates. Without this file, the warning links to a 404 and users have no migration guidance.

There are **two warnings**, one per direction:
1. `--feature` → `--mission` (tracked-mission selection)
2. `--mission` → `--mission-type` (blueprint/template selection)

Each gets its own doc file.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP08` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T033 — Create `docs/migration/feature-flag-deprecation.md` [P]

**Purpose**: Write the migration doc for the `--feature` → `--mission` direction.

**Steps**:
1. Create the directory if it does not exist:
   ```bash
   mkdir -p docs/migration
   ```
   (Only if `docs/migration/` does not yet exist. Do not create it if it already exists.)

2. Create `docs/migration/feature-flag-deprecation.md` with this structure:

   ```markdown
   # Migration: `--feature` → `--mission`

   **Status**: Deprecated as of mission `077-mission-terminology-cleanup`.
   **Removal**: Gated on named conditions (see "Removal Criteria" below). No date.

   ## Why This Change

   The `--feature` CLI flag has been replaced by `--mission` as the canonical
   selector for tracked missions. The change brings the operator-facing CLI in
   line with the canonical terminology model defined in the [Mission Type / Mission /
   Mission Run ADR](../../architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md):

   - **Mission Type** = reusable workflow blueprint (`software-dev`, `research`, `documentation`)
   - **Mission** = concrete tracked item under `kitty-specs/<mission-slug>/`
   - **Mission Run** = runtime/session execution instance only

   `--feature` is retained as a **hidden deprecated alias** during the migration window
   so that legacy scripts continue to work. New scripts and documentation must use
   `--mission`.

   ## What Changed

   | Before | After |
   |---|---|
   | `spec-kitty mission current --feature 077-foo` | `spec-kitty mission current --mission 077-foo` |
   | `spec-kitty next --feature 077-foo` | `spec-kitty next --mission 077-foo` |
   | `spec-kitty agent tasks status --feature 077-foo` | `spec-kitty agent tasks status --mission 077-foo` |

   The `--feature` flag still works but emits a deprecation warning to stderr on
   every invocation.

   ## Behavioral Changes

   1. **Deterministic conflict detection**: Passing both `--mission` and `--feature`
      with different values now fails fast with a conflict error. Previously, the
      second value silently won (this was a verified bug fixed by mission 077).

   2. **Same-value compat**: Passing both flags with the same value works but emits
      the deprecation warning.

   3. **Hidden from help**: `--feature` no longer appears in `--help` output. New
      users will only see `--mission`.

   ## How to Migrate Your Scripts

   Replace `--feature` with `--mission` in any script that calls `spec-kitty`.

   ```bash
   # Old
   spec-kitty mission current --feature 077-mission-terminology-cleanup

   # New
   spec-kitty mission current --mission 077-mission-terminology-cleanup
   ```

   For automated migration of many scripts:

   ```bash
   find . -name "*.sh" -o -name "*.bash" | xargs sed -i 's/--feature /--mission /g'
   ```

   (Verify the diff before committing — `sed` may match strings inside other tool
   invocations that legitimately use `--feature`.)

   ## Suppressing the Warning During Cutover

   For CI consumers that cannot tolerate stderr noise during the migration window,
   set the environment variable:

   ```bash
   export SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1
   ```

   This suppresses the warning **only**. The flag itself still works, and the
   conflict detection still fires on dual-flag mismatches.

   The env var is a transitional escape hatch. Use it to unblock CI cutover, then
   remove it after migrating your scripts.

   ## Removal Criteria

   The `--feature` alias will be removed only when **all** of the following are true:

   1. All first-party doctrine skills, agent-facing docs, examples, tutorials, and
      reference docs use `--mission`.
   2. All first-party machine-facing surfaces have completed Scope B (issue #543).
   3. A documented telemetry or audit window has elapsed during which legacy
      `--feature` usage in first-party CI fixtures is zero.

   The decision to actually remove `--feature` is a separate change that must
   reference these conditions. There is **no calendar date** for removal — the
   conditions are the gate.

   ## References

   - Mission spec: [kitty-specs/077-mission-terminology-cleanup/spec.md](../../kitty-specs/077-mission-terminology-cleanup/spec.md)
   - ADR: [Mission Type / Mission / Mission Run Terminology Boundary](../../architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md)
   - Initiative: [Mission Nomenclature Reconciliation](../../architecture/2.x/initiatives/2026-04-mission-nomenclature-reconciliation/README.md)
   - Tracking issue: [#241](https://github.com/Priivacy-ai/spec-kitty/issues/241)
   ```

3. Verify the doc renders correctly (no broken Markdown):
   ```bash
   ls -la docs/migration/feature-flag-deprecation.md
   wc -l docs/migration/feature-flag-deprecation.md
   ```

### T034 — Create `docs/migration/mission-type-flag-deprecation.md` [P]

**Purpose**: Write the migration doc for the `--mission` → `--mission-type` direction.

**Steps**:
1. Create `docs/migration/mission-type-flag-deprecation.md` with the same shape as T033 but for the inverse direction:

   ```markdown
   # Migration: `--mission` → `--mission-type` (Blueprint/Template Selection)

   **Status**: Deprecated as of mission `077-mission-terminology-cleanup`.
   **Removal**: Gated on named conditions. No date.

   ## Why This Change

   On a small number of CLI commands, the `--mission` flag was used to mean
   "mission *type*" (i.e., the reusable blueprint: `software-dev`, `research`,
   `documentation`). This collided with the canonical use of `--mission` as the
   tracked-mission slug selector on every other command.

   To eliminate the ambiguity, those commands now use `--mission-type` as the
   canonical literal flag for blueprint selection. `--mission` is retained as a
   **hidden deprecated alias** on those specific commands during the migration
   window.

   This change applies only to the three "inverse drift" sites verified at HEAD
   `35d43a25`:

   - `spec-kitty agent mission create`
   - `spec-kitty charter interview`
   - `spec-kitty lifecycle specify`

   On every other command, `--mission` continues to mean "tracked mission slug" (its
   canonical meaning).

   ## What Changed

   | Before | After |
   |---|---|
   | `spec-kitty agent mission create new-thing --mission software-dev` | `spec-kitty agent mission create new-thing --mission-type software-dev` |
   | `spec-kitty charter interview --mission research` | `spec-kitty charter interview --mission-type research` |
   | `spec-kitty lifecycle specify my-feature --mission documentation` | `spec-kitty lifecycle specify my-feature --mission-type documentation` |

   The `--mission` flag still works on these specific commands but emits a
   deprecation warning to stderr on every invocation.

   ## Behavioral Changes

   1. **Deterministic conflict detection**: Passing both `--mission-type` and
      `--mission` with different values fails fast with a conflict error.

   2. **`charter interview` default preserved**: `charter interview` still defaults
      to `software-dev` when no flag is passed. The default behavior is unchanged.

   3. **Hidden from help**: `--mission` no longer appears in the `--help` output
      of these three commands. It only appears on commands where `--mission` is
      the canonical tracked-mission selector.

   ## Suppressing the Warning During Cutover

   ```bash
   export SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION=1
   ```

   This is a separate env var from the `--feature` deprecation suppression. The two
   are intentionally independent because they may have different removal timelines.

   ## Removal Criteria

   Same gate structure as the `--feature` migration: removal is conditional on (1)
   all first-party docs and skills using `--mission-type` for blueprint selection,
   (2) Scope B (issue #543) acceptance, (3) zero usage in first-party CI fixtures.
   No calendar date.

   ## References

   - Mission spec: [kitty-specs/077-mission-terminology-cleanup/spec.md](../../kitty-specs/077-mission-terminology-cleanup/spec.md)
   - ADR: [Mission Type / Mission / Mission Run Terminology Boundary](../../architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md)
   - Initiative: [Mission Nomenclature Reconciliation](../../architecture/2.x/initiatives/2026-04-mission-nomenclature-reconciliation/README.md)
   - Tracking issue: [#241](https://github.com/Priivacy-ai/spec-kitty/issues/241)
   ```

2. Verify the doc renders:
   ```bash
   wc -l docs/migration/mission-type-flag-deprecation.md
   ```

### T035 — Verify deprecation warning paths in `selector_resolution.py` match the new doc paths

**Purpose**: Ensure the `_doc_path_for` mapping in `selector_resolution.py` (defined in WP02) points to the doc files that this WP just created.

**Steps**:
1. Read `src/specify_cli/cli/selector_resolution.py` and find the `_MIGRATION_DOCS` dict (defined in WP02 T006):
   ```python
   _MIGRATION_DOCS = {
       "--feature": "docs/migration/feature-flag-deprecation.md",
       "--mission": "docs/migration/mission-type-flag-deprecation.md",
   }
   ```

2. Verify the paths match the files created in T033 and T034:
   - `docs/migration/feature-flag-deprecation.md` ✓ (created in T033)
   - `docs/migration/mission-type-flag-deprecation.md` ✓ (created in T034)

3. If WP02 used different paths, **update the docs**, not the code (because WP02 is already merged and its tests pin the warning text format). Or, if the code paths are obviously wrong, file a bug and coordinate with WP02 to fix.

4. Run the manual smoke test from `quickstart.md`:
   ```bash
   uv run spec-kitty mission current --feature 077-mission-terminology-cleanup 2>&1 >/dev/null | head -5
   ```
   Expected output:
   ```
   Warning: --feature is deprecated; use --mission. See: docs/migration/feature-flag-deprecation.md
   ```
   Verify the path in the warning matches the file you just created.

5. Add a contract test (or integrate with the WP09 grep guards) that asserts both files exist:
   ```python
   def test_migration_docs_referenced_by_warnings_exist():
       """The deprecation warnings link to migration docs that must exist."""
       repo_root = Path(__file__).resolve().parents[2]
       assert (repo_root / "docs/migration/feature-flag-deprecation.md").exists()
       assert (repo_root / "docs/migration/mission-type-flag-deprecation.md").exists()
   ```
   Add this to `tests/contract/test_terminology_guards.py` (which WP09 will create) OR to a new tiny `tests/contract/test_migration_docs.py`.

## Files Touched

| File | Action | Notes |
|---|---|---|
| `docs/migration/feature-flag-deprecation.md` | CREATE | New doc |
| `docs/migration/mission-type-flag-deprecation.md` | CREATE | New doc |
| (optional) `tests/contract/test_migration_docs.py` | CREATE | If WP09 hasn't created `test_terminology_guards.py` yet |

**Out of bounds**:
- `src/specify_cli/cli/selector_resolution.py` is owned by WP02 and is read-only here. T035 only verifies the paths match.

## Definition of Done

- [ ] `docs/migration/feature-flag-deprecation.md` exists with all 7 sections (Why, What, Behavior, How to Migrate, Suppression, Removal Criteria, References)
- [ ] `docs/migration/mission-type-flag-deprecation.md` exists with the same 7 sections
- [ ] Both docs link back to spec.md, ADR, initiative, and issue #241
- [ ] Both docs explain the named removal conditions (no calendar date)
- [ ] Both docs document the correct env var name
- [ ] T035 manual smoke test produces the expected warning text with the correct doc path
- [ ] Internal links in both docs are not broken
- [ ] No file under `src/specify_cli/`, `kitty-specs/**` (other than this mission), or `architecture/**` is modified

## Risks and Reviewer Guidance

**Risks**:
- If WP02 used different doc paths than T033/T034 create, the warning links are dangling. T035 catches this; coordinate with WP02 to fix.
- The `mkdir -p docs/migration` step is only safe if `docs/migration/` does not yet exist. If it exists, do not run mkdir.
- The cross-references to `architecture/2.x/adr/...` and `architecture/2.x/initiatives/...` use relative paths. Verify they resolve from the doc location (`docs/migration/`).

**Reviewer checklist**:
- [ ] Both doc files exist and are well-formed Markdown
- [ ] All cross-references resolve to real files in the repo
- [ ] Doc content matches the §11.1 policy (asymmetric: main CLI has window, orchestrator-api stays strict)
- [ ] No calendar dates for removal — only named conditions
- [ ] Env var names match WP02 constants exactly

## Implementation Command

```bash
spec-kitty implement WP08
```

This WP depends on WP01. After WP01 is merged, WP08 can run in parallel with WP02, WP06, WP07. T035 must run after WP02 is merged (because it verifies WP02's mapping).

## References

- Spec FR-013, NFR-002, NFR-003
- Spec §11 — Migration and Deprecation Policy (asymmetric)
- Spec §15 Q1 — named conditions, not date
- `contracts/deprecation_warning.md` §"Migration Documentation"
- WP02 T006 — `_MIGRATION_DOCS` dict (path constants)
