---
work_package_id: WP08
title: Charter synthesizer determinism
dependencies: []
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pre-doctrine-test-stabilization-01KSMG8Y
base_commit: fcec446d1be3c2c67d5ce9f0bc36a40133fe6684
created_at: '2026-05-27T12:19:36.655895+00:00'
subtasks:
- T032
- T033
- T034
- T035

shell_pid: "40565"
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
history:
- date: '2026-05-27'
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/charter/synthesizer/**
- tests/charter/synthesizer/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Fix non-deterministic manifest hash computation in the charter synthesizer by sorting file lists before hashing. Enforce the `path_guard.py` chokepoint so direct write primitives cannot bypass it. Refresh stored manifest hashes in test fixtures.

**Closes**: GitHub issue #1303

---

## Context

The charter synthesizer produces manifest hashes that vary across runs because file traversal order is non-deterministic (OS-dependent). The fix is to sort all file lists before hashing to produce a consistent, deterministic order.

**Critical ownership constraint**:
- WP08 owns `src/charter/synthesizer/` exclusively
- WP05 owns `src/specify_cli/cli/commands/charter/synthesize.py` (the CLI adapter) — do NOT touch it here
- Do NOT touch `src/specify_cli/charter_lint/` or any `src/specify_cli/` charter paths

**Source path**: The charter synthesizer library is at `src/charter/synthesizer/` — note this is under `src/charter/`, NOT under `src/specify_cli/charter/`.

---

## Subtask T032 — Run tests to identify the hash computation path

**Purpose**: Before editing, identify which function(s) compute the manifest hash and confirm the traversal is non-deterministic.

**Steps**:

1. Run the synthesizer tests:
   ```bash
   pytest tests/charter/synthesizer/test_bundle_validate_extension.py -v --tb=long 2>&1 | head -80
   ```

2. Identify which of the five assertions fail and what the failure message says (e.g., "hash mismatch", "unexpected hash value", "hash changed between runs").

3. Explore the synthesizer source to find the manifest computation:
   ```bash
   find src/charter/synthesizer/ -name "*.py" | sort
   grep -rn "hash\|manifest\|digest\|sha" src/charter/synthesizer/ --include="*.py" | head -20
   ```

4. Identify the file traversal: which function calls `os.walk`, `Path.iterdir()`, `glob()`, or similar, and whether the results are sorted before being passed to the hash function.

5. Also identify the `path_guard.py` chokepoint:
   ```bash
   find src/charter/synthesizer/ -name "path_guard*" | head -5
   grep -rn "path_guard\|write\|open.*w" src/charter/synthesizer/ --include="*.py" | head -20
   ```

**Output**: You know which function to fix for determinism and where the path_guard chokepoint is (or needs to be).

**Validation**:
- [ ] You have identified the non-deterministic traversal location
- [ ] You have located `path_guard.py` (or know it needs to be created)

---

## Subtask T033 — Sort file lists before hashing

**Purpose**: Make the manifest hash deterministic by sorting file lists before feeding them into the hash function.

**Steps**:

1. Locate the traversal that feeds the hash (identified in T032).

2. Apply a sort before the hash computation. Example pattern:

   ```python
   # Before (non-deterministic):
   files = list(Path(bundle_dir).rglob("*"))
   for f in files:
       hasher.update(f.read_bytes())

   # After (deterministic):
   files = sorted(Path(bundle_dir).rglob("*"))
   for f in files:
       hasher.update(f.read_bytes())
   ```

   The sort key should be the relative path string to ensure cross-platform consistency:
   ```python
   files = sorted(Path(bundle_dir).rglob("*"), key=lambda p: str(p.relative_to(bundle_dir)))
   ```

3. Run the tests TWICE without `PYTEST_UPDATE_SNAPSHOTS` to confirm the hash is now identical across runs:
   ```bash
   pytest tests/charter/synthesizer/ -v --tb=short 2>&1 | tail -20
   pytest tests/charter/synthesizer/ -v --tb=short 2>&1 | tail -20
   ```

   Both runs should produce the same result.

**Files**: The manifest computation module in `src/charter/synthesizer/`

**Validation**:
- [ ] Hash is identical across two consecutive test runs
- [ ] Only sorting was added (no semantic change to what is hashed)

---

## Subtask T034 — Enforce path_guard.py chokepoint

**Purpose**: Direct write primitives (`open(f, "w")`, `Path.write_text()`, `Path.write_bytes()`) must not be called outside `path_guard.py`. This prevents accidental writes to files outside the bundle boundary.

**Steps**:

1. Read `path_guard.py` to understand its current interface:
   ```bash
   cat src/charter/synthesizer/path_guard.py
   ```
   (If it doesn't exist yet, it needs to be created as the single write-permitted entry point.)

2. Identify any direct write calls outside `path_guard.py`:
   ```bash
   grep -rn "\.write_text\|\.write_bytes\|open(.*['\"]w" src/charter/synthesizer/ --include="*.py" | grep -v "path_guard"
   ```

3. For each direct write call found:
   - Refactor to route through `path_guard.py`'s write method
   - The path_guard should validate that the target path is within the allowed directory before writing

4. If no direct writes exist outside `path_guard.py`: the chokepoint is already enforced. Document this in the commit message.

5. Verify the test assertion about the chokepoint passes:
   ```bash
   pytest tests/charter/synthesizer/test_bundle_validate_extension.py -v --tb=short -k "path_guard or chokepoint"
   ```

**Files**: `src/charter/synthesizer/path_guard.py` and any callers that bypass it

**Validation**:
- [ ] No direct write primitives exist outside `path_guard.py` in `src/charter/synthesizer/`
- [ ] Relevant `test_bundle_validate_extension` assertions pass

---

## Subtask T035 — Refresh stored manifest hashes in test fixtures

**Purpose**: After fixing the hash computation, the stored expected hashes in test fixtures are stale. Update them so the tests can assert against the new deterministic hashes.

**Steps**:

1. Run the tests to see which fixture hashes are now mismatched:
   ```bash
   pytest tests/charter/synthesizer/test_bundle_validate_extension.py -v --tb=short 2>&1 | head -60
   ```

2. If the tests have an update mode: use it:
   ```bash
   PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/charter/synthesizer/ -v 2>&1 | tail -20
   ```

3. If there is no update mode: manually update the expected hash values in the fixture files based on the actual hash values now produced by the deterministic computation.

4. Run the tests twice without the update flag to confirm they pass consistently:
   ```bash
   pytest tests/charter/synthesizer/test_bundle_validate_extension.py -v
   pytest tests/charter/synthesizer/test_bundle_validate_extension.py -v
   ```

**Files**: Test fixtures in `tests/charter/synthesizer/` (hash values, baseline files)

**Validation**:
- [ ] All five `test_bundle_validate_extension` assertions pass
- [ ] Tests pass consistently across two consecutive runs (determinism confirmed)

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

This WP can run in parallel with WP07 and WP09. WP05 must not touch `src/charter/synthesizer/`.

To start implementation:
```bash
spec-kitty agent action implement WP08 --agent claude
```

---

## Definition of Done

- [ ] All five `test_bundle_validate_extension` assertions pass
- [ ] Hash is identical across two consecutive runs of the test suite (determinism)
- [ ] No direct write primitives outside `path_guard.py` in `src/charter/synthesizer/`
- [ ] No changes made to `src/specify_cli/cli/commands/charter/synthesize.py` (WP05 scope)
- [ ] No changes made to any `src/specify_cli/` paths

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Sort key must be cross-platform (Windows path separators) | Medium | Use `str(p.relative_to(base))` with forward slashes |
| path_guard.py does not exist yet (needs creation) | Low | Check first; create if needed per the pattern for write chokepoints |
| Test fixture has hardcoded hash from a specific traversal order | High | T035 explicitly refreshes fixtures after sorting fix |

---

## Reviewer Guidance

1. Run the full synthesizer test suite TWICE and confirm identical results
2. `grep` for direct write calls in `src/charter/synthesizer/` — none should exist outside `path_guard.py`
3. No `src/specify_cli/` files were modified
4. Hash sort key uses string comparison (not OS path ordering)
</content>

## Activity Log

- 2026-05-27T12:19:37Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=40565 – Assigned agent via action command
- 2026-05-27T12:26:09Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=40565 – T032-T035 complete: charter synthesizer deterministic, all 5 bundle_validate_extension tests pass. Added 3 new determinism + path_guard chokepoint coverage tests (23 total). No src/specify_cli/ files modified.
