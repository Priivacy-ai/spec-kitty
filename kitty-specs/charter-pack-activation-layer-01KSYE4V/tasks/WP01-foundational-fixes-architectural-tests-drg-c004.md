---
work_package_id: WP01
title: 'Foundational Fixes: Architectural Tests + DRG + C-004'
dependencies: []
requirement_refs:
- FR-020
- FR-021
- FR-022
- FR-023
- FR-025
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-pack-activation-layer-01KSYE4V
base_commit: 64f1c6c3cc8a9fbfd2e388f76546b4f980aac1f0
created_at: '2026-05-31T13:03:16.593739+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
shell_pid: "4108021"
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/test_layer_rules.py
- tests/architectural/test_template_governance_payload_contract.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/_baselines.yaml
- src/doctrine/missions/mission_step_repository.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the implementer profile:

```
/ad-hoc-profile-load python-pedro
```

You are implementing as **python-pedro** (Python implementer). Work precisely, fix
only what is described, run validation after each subtask, and do not touch files
outside the `owned_files` list above.

---

## Objective

Repair six independent defects that block the architectural test suite and violate
structural rules established by prior missions. None of these subtasks depend on
each other within WP01 — they can be executed in any order — but all six must be
complete before the architectural gate (`pytest tests/architectural/ -x`) is green.
This WP has no declared dependencies and runs in parallel with WP02.

---

## Context

The `pr/charter-doctrine-mission-type-configuration` branch introduces the charter
pack activation layer. Before that new behavior can be built and tested, the
architectural test suite must be clean. Currently the suite has several pre-existing
failures caused by:

- A namespace-package false positive in `test_legacy_subpackage_is_gone`
- Stale path constants (`command-templates/`) in template governance tests
- Two upcoming migration modules not yet in the dead-modules allowlist
- Tracked test fixture directories in `kitty-specs/`
- A wrong plural mapping in `drg.py` (`"mission_steps"` instead of
  `"mission_step_contracts"`)
- A C-004 layer violation: `src/doctrine/` importing from `charter` under
  `TYPE_CHECKING`

Each subtask below is a targeted, self-contained fix. Read the subtask fully before
touching any file. Run the validation command at the end of each subtask before
moving to the next.

---

## Branch Strategy

```
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch:  pr/charter-doctrine-mission-type-configuration
```

This WP has no sub-branches. All commits go directly onto
`pr/charter-doctrine-mission-type-configuration` in the lane worktree allocated by
`finalize-tasks`. Do not create additional git branches. Commit after completing
each subtask group (T001–T003 together, T004–T006 together, or each individually —
your call — as long as every commit leaves the suite in a passing state).

---

## Subtasks

---

### T001 — Fix `test_legacy_subpackage_is_gone` namespace-package false positive

**Requirement**: FR-021

**Purpose**: `find_spec("doctrine.mission_step_contracts")` may return non-`None`
for a namespace package even when no source files are present, causing the test to
fail with a false positive.

**Files**:
- `tests/architectural/test_layer_rules.py` (around lines 196–225)

**Steps**:

1. Open `tests/architectural/test_layer_rules.py` and locate the test
   `test_legacy_subpackage_is_gone` (or similar name referencing
   `doctrine.mission_step_contracts`).

2. Before editing, verify actual runtime behavior:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   python -c "import importlib.util; print(importlib.util.find_spec('doctrine.mission_step_contracts'))"
   ```
   - If the output is `None`: `find_spec` already returns `None`, the test passes as
     written. Skip to validation.
   - If the output is a `ModuleSpec(...)` (non-None): the namespace package is being
     found. You must remove the `find_spec` assertion from the test while keeping
     the source-file existence check.

3. If removal is needed: locate the block that calls `find_spec` (roughly lines
   196–208) and remove only the assertion that checks `find_spec` returns `None`.
   Do NOT remove the subsequent block (roughly lines 209–215) that checks for
   source `.py` files on disk — that check is the reliable gate and must remain.

4. The resulting test should rely solely on "no `.py` files exist under the
   namespace path" to confirm the legacy subpackage is gone.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/architectural/test_layer_rules.py -k "legacy_subpackage" -x -v
```
Expected: 1 test passes (PASSED, not skipped).

---

### T002 — Fix 8 broken `test_template_governance_payload_contract` tests

**Requirement**: FR-022

**Purpose**: The template governance tests reference a path segment
`"command-templates"` that no longer exists. The current doctrine layout stores
mission templates under
`src/doctrine/missions/mission-steps/{mission_type}/{step_id}/`. Update the path
constants so the 8 tests can find the templates they exercise.

**Files**:
- `tests/architectural/test_template_governance_payload_contract.py` (lines 39 and 48)

**Steps**:

1. Read `tests/architectural/test_template_governance_payload_contract.py`. Find the
   two path constants near lines 39 and 48. They will contain something like:
   ```python
   TEMPLATES_ROOT = Path("src") / "doctrine" / "command-templates"
   ```
   or a similar string with `"command-templates"`.

2. Determine the correct root. Run:
   ```bash
   find /home/stijn/Documents/_code/SDD/fork/spec-kitty/src/doctrine/missions/mission-steps \
       -name "prompt.md" | head -5
   ```
   This shows the actual template tree. The root you need is
   `src/doctrine/missions/mission-steps` (relative to the repo root).

3. Update the two path constants to point at the correct root. Example:
   ```python
   TEMPLATES_ROOT = Path("src") / "doctrine" / "missions" / "mission-steps"
   ```
   Verify by checking that at least one `.md` template file exists under that path:
   ```bash
   ls /home/stijn/Documents/_code/SDD/fork/spec-kitty/src/doctrine/missions/mission-steps/ | head
   ```

4. Do not change any test logic — only the path constants.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/architectural/test_template_governance_payload_contract.py -x -v
```
Expected: all 8 tests pass.

---

### T003 — Dead-modules allowlist + baseline bump for m_3_2_7 and m_3_2_8

**Requirement**: FR-023

**Purpose**: Two upcoming migration modules (`m_3_2_7_activate_builtin_mission_types`
and `m_3_2_8_default_charter_pack`) must be pre-registered in the dead-modules
test so they are not flagged as dead code once created. The baseline counter must
also reflect the new expected count.

**Files**:
- `tests/architectural/test_no_dead_modules.py`
- `tests/architectural/_baselines.yaml`

**Steps**:

1. Open `tests/architectural/test_no_dead_modules.py`. Find the list named
   `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS` (or similar — it is a list of migration
   module name strings).

2. Add both new entries **in alphabetical / version-ordered position** within the
   list:
   ```python
   "m_3_2_7_activate_builtin_mission_types",
   "m_3_2_8_default_charter_pack",
   ```
   Note: `m_3_2_8` does not exist yet (it is implemented in WP05). Pre-registering
   it here prevents WP05 from breaking this test.

3. Open `tests/architectural/_baselines.yaml`. Find the key:
   ```yaml
   category_1_auto_discovered_migrations: 71
   ```
   Bump it to `73` (two new entries). Add a `# justification:` inline comment
   following the style already used in the file for other bumped baselines. Look at
   nearby commented baselines for the exact format, then write:
   ```yaml
   category_1_auto_discovered_migrations: 73  # justification: +2 for m_3_2_7_activate_builtin_mission_types and m_3_2_8_default_charter_pack (charter-pack-activation-layer-01KSYE4V)
   ```

4. Save both files.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/architectural/test_no_dead_modules.py -x -v
```
Expected: all tests pass (the two new migration names are now known-good; the
counter matches).

---

### T004 — Remove tracked test fixture files from `kitty-specs/`

**Requirement**: FR-025

**Purpose**: Stale test fixture mission directories committed under `kitty-specs/`
pollute the repository and can confuse mission scanners.

**Files**: variable (determined by git)

**Steps**:

1. Identify tracked test fixture directories:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   git ls-files kitty-specs/ | grep "^kitty-specs/test-feature"
   ```

2. If entries are found: remove them from git tracking and disk:
   ```bash
   git rm -r kitty-specs/test-feature-*
   ```
   Verify the removal:
   ```bash
   git ls-files kitty-specs/ | grep "test-feature"
   ```
   Expected: no output.

3. If no entries are found: add a comment in this WP's implementation notes (a
   commit message or inline code comment is fine) stating:
   `# T004: no tracked test-feature-* entries found in kitty-specs/; subtask is a no-op`
   Do not create any files to record this — a commit message note is sufficient.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
git ls-files kitty-specs/ | grep "test-feature"
```
Expected: zero lines of output (either because none existed, or because they were
removed).

---

### T005 — Fix `_SINGULAR_TO_PLURAL["mission_step_contract"]` in `drg.py`

**Requirement**: FR-028

**⚠️ RELOCATED**: This fix has been moved to **WP08 T034** (steps 4–5), which owns
`src/charter/drg.py`. WP01 does not own `drg.py` — ownership is held by WP08 to
avoid cross-WP conflicts.

**This subtask is a no-op for WP01.** Proceed to T006.

If you are reviewing WP01 and notice this subtask, verify that WP08 T034 contains
the `_SINGULAR_TO_PLURAL` fix (search for `FR-028` in WP08's body). Do not edit
`src/charter/drg.py` from WP01's lane.

---

### T006 — Fix C-004: replace TYPE_CHECKING charter import with `_PackContextLike` protocol

**Requirement**: FR-020

**Purpose**: `src/doctrine/missions/mission_step_repository.py` imports
`PackContext` from `charter.pack_context` under `TYPE_CHECKING`. This violates
architectural rule C-004: `doctrine` must not import from `charter`. The fix is to
replace the concrete import with a narrow structural `Protocol` defined inline in
the doctrine module.

**Files**:
- `src/doctrine/missions/mission_step_repository.py` (lines ~38–43 and method signatures throughout)

**Steps**:

1. Open `src/doctrine/missions/mission_step_repository.py`. Find the `TYPE_CHECKING`
   block (around lines 38–43):
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from charter.pack_context import PackContext
   ```

2. Before removing it, grep all `PackContext` and `pack_context.` usages in the file
   to confirm exactly which attributes of `PackContext` are accessed:
   ```bash
   grep -n "pack_context\." \
       /home/stijn/Documents/_code/SDD/fork/spec-kitty/src/doctrine/missions/mission_step_repository.py
   ```
   Confirm only `.pack_roots` and `.repo_root` are accessed (research.md §4 states
   these are the only two fields — lines 256, 289, 312, 325, 347). If you find any
   other attribute accesses, note them and add them to the Protocol.

3. Add the Protocol **before** the class definition in the file (after the standard
   library imports, not inside any class):
   ```python
   from typing import Protocol

   class _PackContextLike(Protocol):
       pack_roots: tuple[Path, ...]
       repo_root: Path
   ```
   `Path` must already be imported (it is used throughout the file); if not,
   add `from pathlib import Path`.

4. Remove the `TYPE_CHECKING` import block entirely:
   ```python
   # DELETE these lines:
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from charter.pack_context import PackContext
   ```
   If `TYPE_CHECKING` is used elsewhere in the file for other purposes, remove only
   the `charter` import line inside the block, not the block itself.

5. Replace every type annotation that currently reads `PackContext` or
   `"PackContext"` (quoted forward reference) in method signatures with
   `_PackContextLike | None`. Use search-and-replace carefully — only in type
   annotations, not in string literals or comments.

6. Run mypy on the file to verify type-check passes:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   python -m mypy src/doctrine/missions/mission_step_repository.py --strict 2>&1 | head -40
   ```
   Address any errors. Common issue: if `Protocol` was already imported via another
   path, you may get a duplicate import warning — consolidate.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/architectural/test_layer_rules.py -k "c004 or C004 or doctrine" -x -v
python -m mypy src/doctrine/missions/mission_step_repository.py --strict 2>&1 | tail -5
grep -rn "from charter" src/doctrine/ | grep -v "\.pyc"
```
Expected:
- Architectural tests pass.
- mypy reports no errors on the file.
- `grep` returns no lines (no `from charter` imports remain in `src/doctrine/`).

---

## Definition of Done

- [ ] `pytest tests/architectural/ -x` exits 0 (all architectural tests pass)
- [ ] `pytest tests/charter/test_activation_filtered_drg.py -x` passes (after MSC
      plural fix)
- [ ] `grep -rn "from charter" src/doctrine/ | grep -v "\.pyc"` returns no output
- [ ] `_SINGULAR_TO_PLURAL["mission_step_contract"]` fix: handled by WP08 T034 (drg.py not owned by WP01)
- [ ] The `_PackContextLike` Protocol is defined inline in
      `mission_step_repository.py` with at least `pack_roots` and `repo_root`
- [ ] `TYPE_CHECKING` import of `PackContext` from `charter` is removed from
      `src/doctrine/`
- [ ] Tracked test fixture files are removed (or confirmed never existed)
- [ ] `category_1_auto_discovered_migrations` baseline is `73` in `_baselines.yaml`
- [ ] Both `m_3_2_7_activate_builtin_mission_types` and
      `m_3_2_8_default_charter_pack` appear in the dead-modules allowlist
- [ ] `ruff check src/ tests/` passes (no new lint errors introduced)
- [ ] `python -m mypy src/doctrine/missions/mission_step_repository.py --strict`
      passes

---

## Risks

- **T001 namespace-package behavior is Python-version-sensitive.** The probe command
  (`python -c "... find_spec(...)"`) must be run before deciding whether to edit the
  test. Do not edit blindly.
- **T002 wrong root path guess.** Always confirm the path exists with `ls` before
  updating the constant. If the directory structure differs from what is described
  here, find the actual root with `find ... -name "prompt.md"` and use that.
- **T003 baseline off-by-one.** Count the existing entries in
  `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS` before and after adding the two new
  entries to make sure the baseline delta is exactly +2.
- **T005 reverse-map side effects.** Adding `"mission_step_contracts"` to the
  reverse map is additive and safe. Do not remove the old `"mission_steps"` entry —
  existing serialized data may still reference it.
- **T006 Protocol attribute omission.** If the grep in step 2 reveals attributes
  beyond `pack_roots` and `repo_root`, add them to `_PackContextLike`. An incomplete
  Protocol will cause mypy strict errors.

---

## Reviewer Guidance

Reviewers must verify:

1. **T001**: The architectural test passes under the actual Python version used in
   CI. Check that the source-file existence check (not just `find_spec`) is still
   present.

2. **T002**: `pytest tests/architectural/test_template_governance_payload_contract.py`
   reports exactly 8 tests, all PASSED.

3. **T003**: `_baselines.yaml` shows `category_1_auto_discovered_migrations: 73`
   with a `# justification:` comment. Both migration module names are present in the
   allowlist in `test_no_dead_modules.py`.

4. **T004**: `git ls-files kitty-specs/ | grep test-feature` returns no output.

5. **T005**: Relocated to WP08 T034. Verify `"mission_step_contract": "mission_step_contracts"` appears in WP08's diff of `src/charter/drg.py`, not WP01's diff.

6. **T006**: `grep -rn "from charter" src/doctrine/` returns no lines.
   `_PackContextLike` is defined in `mission_step_repository.py`. mypy strict passes
   on that file. The C-004 architectural layer test passes.

## Activity Log

- 2026-05-31T13:03:17Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=4062575 – Assigned agent via action command
- 2026-05-31T13:32:02Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=4062575 – Ready for review: architectural tests green, C-004 violation fixed, dead-modules baselines updated. T004 note: test fixture deletions (kitty-specs/test-feature-*) included on lane branch intentionally per WP spec - these are stale test artifacts, not planning artifacts.
- 2026-05-31T13:32:39Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=4108021 – Started review via action command
