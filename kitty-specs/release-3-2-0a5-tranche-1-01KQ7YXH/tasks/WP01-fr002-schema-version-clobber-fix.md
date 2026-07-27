---
work_package_id: WP01
title: FR-002 schema_version clobber fix + regression
dependencies: []
requirement_refs:
- FR-002
- NFR-006
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-release-3-2-0a5-tranche-1-01KQ7YXH
base_commit: b0ff84cf47e2fe659d1c6c71bab5a2d998e2d02c
created_at: '2026-04-27T19:14:52.199710+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "66749"
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/upgrade/
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- src/specify_cli/upgrade/runner.py
- tests/cross_cutting/versioning/test_upgrade_version_update.py
- tests/e2e/test_upgrade_post_state.py
role: implementer
tags:
- foundational
- regression
---

# WP01 — FR-002 schema_version clobber fix + regression

## ⚡ Do This First: Load Agent Profile

Before reading further or making any edits, invoke the `/ad-hoc-profile-load` skill with these arguments:

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

This loads your identity, governance scope, boundaries, and self-review checklist for code-change work. Do not skip — the profile carries the bug-fixing-checklist tactic that requires a reproduction test BEFORE you touch production code.

## Objective

Fix the upgrade runner so that, after `spec-kitty upgrade` reports `Upgrade complete!`, the project's `.kittify/metadata.yaml` actually contains the `spec_kitty.schema_version` field that the compat planner gate requires. Today, the success path silently leaves the project unable to run any `spec-kitty agent ...` command — exactly the trap that bit this mission's authoring agent during `/spec-kitty.specify` and forced a manual `schema_version: 3` stamp into `.kittify/metadata.yaml`.

After this WP merges, no manual stamp should ever again be necessary on a freshly-upgraded project.

## Context

**Live evidence** (already captured in [spec.md](../spec.md) "Live Evidence"):

- `~/.local/bin/spec-kitty` reported `3.2.0a3` in the fresh dev workspace; `pyproject.toml` and `.kittify/metadata.yaml` were both at `3.2.0a4`.
- Two consecutive runs of `spec-kitty upgrade --yes` printed `Upgrade complete! 3.2.0a4 -> 3.2.0a4` while leaving `.kittify/metadata.yaml` without `spec_kitty.schema_version`.
- `spec-kitty agent mission create ...` was then blocked by:
  > `This project needs Spec Kitty project migrations before this command can run. Run: spec-kitty upgrade`

**Confirmed root cause** (from [research.md R2](../research.md#r2--schema-version-clobber-root-cause-fr-002--705)):

In `src/specify_cli/upgrade/runner.py` lines 156–164, the success path runs:

```python
metadata.version = target_version
metadata.last_upgraded_at = datetime.now()
if REQUIRED_SCHEMA_VERSION is not None:
    self._stamp_schema_version(self.kittify_dir, REQUIRED_SCHEMA_VERSION)  # line 163
metadata.save(self.kittify_dir)                                            # line 164
```

The `_stamp_schema_version` helper (lines 375–418) writes `spec_kitty.schema_version` into the YAML via raw read-modify-atomic-write. The very next line, `metadata.save(...)`, then reconstructs the YAML payload from a hardcoded three-key dict (`spec_kitty`, `environment`, `migrations`) inside `src/specify_cli/upgrade/metadata.py:147–169` — and **does not preserve unknown keys**. So the freshly-stamped `schema_version` is wiped out one line later.

After the fix, an immediately-following `spec-kitty agent mission branch-context --json` MUST exit 0 with no `PROJECT_MIGRATION_NEEDED` block. That is the operator-visible promise.

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- `branch_matches_target` was `true` at planning time.
- Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`).
- This WP has no dependencies, so its lane is rebased directly onto `release/3.2.0a5-tranche-1`.

## Subtasks

### T001 — Swap call order so `metadata.save()` precedes `_stamp_schema_version()`

**Purpose**: Apply the smallest-blast-radius fix identified in research.md R2.

**Files**:
- `src/specify_cli/upgrade/runner.py` (~2-line change inside the upgrade success block)

**Steps**:

1. Open `src/specify_cli/upgrade/runner.py` and locate the success path inside `UpgradeRunner.upgrade()` around lines 156–164. The current ordering is:

   ```python
   if not dry_run and result.success:
       metadata.version = target_version
       metadata.last_upgraded_at = datetime.now()
       if REQUIRED_SCHEMA_VERSION is not None:
           self._stamp_schema_version(self.kittify_dir, REQUIRED_SCHEMA_VERSION)
       metadata.save(self.kittify_dir)
   ```

2. Swap the last two statements so `metadata.save()` runs first:

   ```python
   if not dry_run and result.success:
       metadata.version = target_version
       metadata.last_upgraded_at = datetime.now()
       metadata.save(self.kittify_dir)
       if REQUIRED_SCHEMA_VERSION is not None:
           self._stamp_schema_version(self.kittify_dir, REQUIRED_SCHEMA_VERSION)
   ```

3. Add a one-line code comment immediately above the `_stamp_schema_version` call explaining WHY it must run after `save()`:

   ```python
   # MUST run after metadata.save(): ProjectMetadata.save() reconstructs the YAML
   # from a fixed dict and does not preserve unknown keys, so stamping schema_version
   # before save() would silently clobber it. See FR-002 / #705.
   ```

   (This comment is non-obvious WHY information per the global "comments" rule and survives reviewer scrutiny.)

**Validation**:
- [ ] `runner.py` imports unchanged.
- [ ] No other call sites of `_stamp_schema_version` exist (`grep -n _stamp_schema_version src/`).
- [ ] Diff is exactly the two-line swap + the comment.

**Edge Cases / Risks**:
- The existing `_stamp_schema_version` already reads the file fresh, mutates the in-memory dict, and atomic-writes it back — so it remains correct when called after `save()`.
- A future refactor that teaches `ProjectMetadata` to round-trip unknown keys would let us remove the swap. Not in scope here; the comment documents the constraint.

### T002 — Extend `test_upgrade_version_update.py` with a schema_version persistence assertion

**Purpose**: Lock the post-save invariant so any future regression to the same family of bug is caught at unit-test time.

**Files**:
- `tests/cross_cutting/versioning/test_upgrade_version_update.py` (extend; do NOT replace existing tests)

**Steps**:

1. Read the existing file. Identify the fixture that sets up a `UpgradeRunner` against a tmp project. Reuse it.

2. Add a new test function:

   ```python
   def test_upgrade_persists_schema_version(tmp_path: Path) -> None:
       # Arrange: set up a project with .kittify/ but without schema_version
       kittify_dir = tmp_path / ".kittify"
       kittify_dir.mkdir()
       _write_pre_schema_metadata_yaml(kittify_dir, version="3.2.0a4")

       # Act: run the upgrade
       runner = UpgradeRunner(kittify_dir=kittify_dir, target_version="3.2.0a5")
       result = runner.upgrade(dry_run=False, include_worktrees=False)

       # Assert
       assert result.success is True
       data = yaml.safe_load((kittify_dir / "metadata.yaml").read_text())
       assert data["spec_kitty"]["schema_version"] == REQUIRED_SCHEMA_VERSION
   ```

3. Where `_write_pre_schema_metadata_yaml` already exists in the file, reuse it; otherwise add a helper that writes a metadata.yaml with `spec_kitty.version`, `initialized_at`, and `last_upgraded_at` but **no** `schema_version`.

**Validation**:
- [ ] New test passes against the fixed runner (after T001).
- [ ] New test FAILS against `main` without T001 (manually verify by stashing T001 once).
- [ ] `pytest tests/cross_cutting/versioning/test_upgrade_version_update.py -q` exits 0.

**Edge Cases / Risks**:
- Do not assert on the exact `last_upgraded_at` timestamp; assert it is updated relative to a `before` capture if you need the temporal check.

### T003 — New e2e smoke covering upgrade → branch-context

**Purpose**: Catch the gate-blocking failure mode end-to-end through the actual CLI, not just the runner.

**Files**:
- `tests/e2e/test_upgrade_post_state.py` (new)

**Steps**:

1. Create the new test file with this shape (adapt to existing e2e helpers in `tests/e2e/`):

   ```python
   from __future__ import annotations

   import json
   import subprocess
   from pathlib import Path

   import pytest


   def test_upgrade_then_branch_context_does_not_gate(tmp_path: Path) -> None:
       # Arrange: spec-kitty init in a tmp project
       project = tmp_path / "demo"
       subprocess.run(
           ["spec-kitty", "init", "demo", "--no-confirm"],
           cwd=tmp_path, check=True, capture_output=True, text=True,
       )

       # Act 1: spec-kitty upgrade --yes
       upgrade_result = subprocess.run(
           ["spec-kitty", "upgrade", "--yes"],
           cwd=project, check=True, capture_output=True, text=True,
       )
       assert "Upgrade complete!" in upgrade_result.stdout

       # Assert intermediate: schema_version landed in metadata.yaml
       import yaml
       metadata = yaml.safe_load((project / ".kittify" / "metadata.yaml").read_text())
       assert metadata["spec_kitty"]["schema_version"], (
           "schema_version was not stamped — FR-002 regression"
       )

       # Act 2: spec-kitty agent mission branch-context --json (the gate consumer)
       bc_result = subprocess.run(
           ["spec-kitty", "agent", "mission", "branch-context", "--json"],
           cwd=project, check=False, capture_output=True, text=True,
       )

       # Assert: command exits 0 and JSON result is success (no gate trip)
       assert bc_result.returncode == 0, (
           f"branch-context gated unexpectedly. stderr={bc_result.stderr!r}"
       )
       payload = json.loads(bc_result.stdout)
       assert payload["result"] == "success"
   ```

2. Mark the test with whatever pytest marker the existing `tests/e2e/` suite uses for "needs the spec-kitty CLI on PATH" (commonly `@pytest.mark.e2e` or a `cli` marker).

3. If `tests/e2e/conftest.py` provides a fixture for an isolated env (PATH manipulation, HOME isolation), reuse it.

**Validation**:
- [ ] `PWHEADLESS=1 uv run --extra test pytest tests/e2e/test_upgrade_post_state.py -q` passes after T001.
- [ ] Same test FAILS without T001 (verify locally by stashing T001 once).

**Edge Cases / Risks**:
- The test uses subprocess against the installed CLI. If the dev env uses an editable install, run `uv sync --reinstall` first or invoke via `uv run spec-kitty …`.

### T004 — Run `mypy --strict` and `ruff check` on changed surfaces

**Purpose**: No regressions in the type or lint surface for the touched files.

**Files**:
- (none — verification only)

**Steps**:

1. Run `uv run --extra lint mypy --strict src/specify_cli/upgrade/runner.py`. Expect zero errors. Address any drift introduced by the swap (none expected).
2. Run `uv run --extra lint ruff check src/specify_cli/upgrade/runner.py tests/cross_cutting/versioning/test_upgrade_version_update.py tests/e2e/test_upgrade_post_state.py`. Expect zero errors.
3. Capture the command outputs in the PR description for reviewer convenience.

**Validation**:
- [ ] Both commands exit 0.

## Test Strategy

- **Unit** (T002): exercises `UpgradeRunner.upgrade()` against a fixture metadata file. Asserts the post-save YAML retains `schema_version`.
- **E2E** (T003): drives the actual CLI through `subprocess` against a fresh tmp project. Asserts the gate consumer (`agent mission branch-context --json`) succeeds immediately after upgrade.

Both tests fail without T001's fix; both pass after.

## Definition of Done

- [ ] T001–T004 complete.
- [ ] `pytest tests/cross_cutting/versioning/test_upgrade_version_update.py tests/e2e/test_upgrade_post_state.py -q` exits 0.
- [ ] `mypy --strict` on `src/specify_cli/upgrade/runner.py` exits 0.
- [ ] `ruff check` on the three changed files exits 0.
- [ ] PR description includes:
  - One-line CHANGELOG entry text for **WP02** to consolidate under `[3.2.0a5] · Fixed`. Suggested: `Fix `spec-kitty upgrade` silently leaving projects in PROJECT_MIGRATION_NEEDED state by stamping schema_version after metadata save (#705).`
  - Link to this WP file.

## Risks

- **R1**: A future refactor of `ProjectMetadata.save()` that DOES preserve unknown keys would make the swap unnecessary, but the swap is also harmless in that future. Document the constraint with the in-code comment so the next reader understands the temporal coupling.
- **R2**: The e2e test in T003 depends on `spec-kitty` being on PATH inside the test environment. If CI uses a different invocation pattern, adapt to `uv run spec-kitty …` or to whichever CLI invocation the existing `tests/e2e/` suite uses.

## Reviewer Guidance

- Diff in `runner.py` should be exactly: 2 statements moved, 3-line comment added. Anything else is suspect.
- Verify the in-code comment names the constraint (`ProjectMetadata.save() does not preserve unknown keys`) and references FR-002 / #705.
- Verify T002 asserts on `REQUIRED_SCHEMA_VERSION` (the constant), not on the literal `3` — so the test follows future schema bumps.
- Verify T003 asserts `branch-context` exits 0 AND payload is `result == "success"` — not just one or the other.
- Cross-check that no other code path calls `_stamp_schema_version` between `save()` and the next file read.

## Implementation command

```bash
spec-kitty agent action implement WP01 --agent claude
```

## Activity Log

- 2026-04-27T19:23:23Z – claude – shell_pid=63270 – Ready for review: schema_version clobber fix + unit + e2e regressions; mypy --strict + ruff clean
- 2026-04-27T19:25:35Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=66749 – Started review via action command
- 2026-04-27T19:28:49Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=66749 – Review passed: code fix correctly stamps schema_version AFTER metadata.save() in both call sites; # Why: comments name ProjectMetadata.save unknown-key behavior and reference FR-002/#705; unit regression test_upgrade_persists_schema_version PASSED; e2e test_upgrade_then_branch_context_does_not_gate PASSED end-to-end; mypy --strict on runner.py clean. Deviation 1 (second clobber path in early-return at runner.py:112-129) ACCEPTED -- same FR-002 root cause and the live-evidence reproduction path. Deviation 2 (pre-existing C901 on _upgrade_worktrees not silenced) ACCEPTED per locality of change; warning exists on base branch unmodified by WP01. Deviation 3 (chore commit 04df3393 stamping schema_version=3 in worktree .kittify/metadata.yaml) ACCEPTED as environmental, isolated, droppable at merge, covered by occurrence_map exception.
