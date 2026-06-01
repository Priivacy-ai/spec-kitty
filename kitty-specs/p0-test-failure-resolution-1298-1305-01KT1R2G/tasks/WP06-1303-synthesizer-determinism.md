---
work_package_id: WP06
title: '#1303: Charter Synthesizer Determinism Fix'
dependencies:
- WP05
requirement_refs:
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
agent: claude
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_lint/
execution_mode: code_change
owned_files:
- src/specify_cli/charter_lint/**
- src/specify_cli/path_guard.py
- tests/charter/synthesizer/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This configures your Python implementer persona. Proceed only after the profile is loaded.

---

## Objective

Make the charter synthesizer's manifest hash computation deterministic, route all file writes through `path_guard.py`, and ensure chokepoint coverage is complete so all 5 charter synthesizer tests pass.

---

## Context

Issue #1303 (cluster C99-d) reports 5 failures in `tests/charter/synthesizer/test_bundle_validate_extension.py`:
- `test_manifest` — manifest hash computed at test time differs from stored hash (non-determinism).
- `test_path_guard` — direct write primitives bypass `path_guard.py`.
- `test_chokepoint_coverage` — not all write paths are registered with the guard.
- `test_bundle_validate_extension` — bundle validation fails (likely downstream of hash drift).
- `test_bundle_validate_cli` — CLI invocation fails (likely downstream).

Root causes: (1) non-deterministic hash generation in the synthesizer (dict key ordering, set iteration, or embedded timestamps); (2) write calls that bypass the path_guard chokepoint.

**Prerequisite**: WP05 must be complete. All prior clusters must be green.

---

## Subtask T024 — Reproduce the #1303 Cluster

**Purpose**: Establish the exact failure output before touching any code.

**Steps**:
```bash
pytest tests/charter/synthesizer/ -q --tb=long -p no:cacheprovider 2>&1 | tee /tmp/wp06-before.txt
```

Record:
- Exact hash mismatch values (stored vs computed)
- Which write paths are flagged as bypassing `path_guard.py`
- Whether `test_chokepoint_coverage` shows a list of missing call sites

**Validation**:
- [ ] All failing tests reproduced with clear error output
- [ ] If zero failures: mark WP06 stale, stop

---

## Subtask T025 — Fix Manifest Hash Non-Determinism

**Purpose**: The synthesizer computes a hash over its output manifest, but the hash is different each run. This means the manifest data structure contains non-deterministic elements.

**Steps**:
1. Locate the synthesizer source and hash computation:
   ```bash
   find src/specify_cli/charter_lint/ -name "*.py" | xargs grep -l "hash\|manifest\|sha" 2>/dev/null
   find src/specify_cli/ -name "synthesizer*" -o -name "*synthesizer*" 2>/dev/null
   ```

2. Read the hash computation code. Look for:
   - `dict` traversal without sorted keys → non-deterministic ordering
   - `set` iteration → non-deterministic ordering
   - `datetime.now()` or `time.time()` embedded in the hash input → timestamp drift
   - UUID generation or random values

3. Fix each non-determinism source:
   - Replace `{k: v for ...}` with `{k: manifest[k] for k in sorted(manifest)}` where needed.
   - Replace `set` with `sorted(list(...))` when sets appear in hash input.
   - Remove timestamps from hash input (use content-only hash).
   - If the hash is computed over a JSON string, use `json.dumps(data, sort_keys=True)`.

4. Run the synthesizer locally to confirm the same input produces the same hash across two consecutive runs:
   ```python
   # Quick determinism check
   from specify_cli.charter_lint.synthesizer import compute_manifest_hash  # adjust import
   result1 = compute_manifest_hash(some_input)
   result2 = compute_manifest_hash(some_input)
   assert result1 == result2, f"{result1} != {result2}"
   ```

**Files modified**: Synthesizer source under `src/specify_cli/charter_lint/` (or equivalent path).

**Validation**:
- [ ] Same input produces same hash in repeated calls (manual check)
- [ ] `test_manifest` passes after fixture regeneration (see T028)

---

## Subtask T026 — Route Write Primitives Through path_guard.py

**Purpose**: `test_path_guard` fails because some write operations in the synthesizer bypass `path_guard.py`. The guard is the established chokepoint for all file writes in this subsystem.

**Steps**:
1. Read `src/specify_cli/path_guard.py` to understand the guard API:
   - How does code register a write path?
   - What function must be used for all writes?

2. Audit the synthesizer for direct write calls:
   ```bash
   grep -n "open.*['\"]w\|write_text\|write_bytes\|shutil\.copy\|shutil\.move" \
     src/specify_cli/charter_lint/ --include="*.py" -r
   ```

3. For each direct write found:
   - Replace with the path_guard-mediated equivalent.
   - Example: replace `path.write_text(content)` with `path_guard.safe_write(path, content)` (adjust to actual API).

4. Run `test_path_guard` to confirm it passes:
   ```bash
   pytest "tests/charter/synthesizer/test_bundle_validate_extension.py::test_path_guard" -v --tb=long
   ```

**Files modified**: Synthesizer source files that contain direct write calls.

**Validation**:
- [ ] `test_path_guard` passes
- [ ] No direct write calls remain in the synthesizer outside `path_guard.py`

---

## Subtask T027 — Fix Chokepoint Coverage Registration

**Purpose**: `test_chokepoint_coverage` asserts that every code path that writes files is explicitly registered in the chokepoint registry. After routing writes through path_guard in T026, the registry entries must match.

**Steps**:
1. Run `test_chokepoint_coverage` with verbose output:
   ```bash
   pytest "tests/charter/synthesizer/test_bundle_validate_extension.py::test_chokepoint_coverage" -v --tb=long
   ```
   The failure output should list which call sites are unregistered.

2. Read the test to understand the registration mechanism:
   - Is there a list/set of known write sites that the test enumerates?
   - Is registration done via a decorator, a `register()` call, or a manifest file?

3. Add the missing call sites to the registry using the established pattern.

4. Run `test_chokepoint_coverage` again to confirm it passes.

**Files modified**: Either the synthesizer source (adding `@register` decorators or similar) or the test file's expected-sites list.

**Validation**:
- [ ] `test_chokepoint_coverage` passes

---

## Subtask T028 — Regenerate Fixture Hashes

**Purpose**: After fixing hash determinism (T025), the stored fixture hashes in the test files are stale. They must be regenerated to match the now-deterministic output.

**Steps**:
1. Understand how fixture hashes are stored:
   ```bash
   grep -r "hash\|sha256\|expected_manifest" tests/charter/synthesizer/ --include="*.py"
   ```
   Look for hardcoded hash strings in the test file or a companion fixture file.

2. Run the synthesizer against the same input the test uses and capture the new hash:
   ```python
   # Conceptual — adjust to actual test setup
   from specify_cli.charter_lint.synthesizer import build_bundle
   result = build_bundle(test_input)
   print(result.manifest_hash)
   ```

3. Update the hardcoded hash(es) in the test/fixture file to the new deterministic value.

4. **Important**: Only do this AFTER T025 is complete and confirmed deterministic. Do not regenerate fixtures before fixing the root cause.

**Files modified**: `tests/charter/synthesizer/test_bundle_validate_extension.py` or a companion fixture file.

**Validation**:
- [ ] `test_manifest` passes with the updated hash
- [ ] Running the synthesizer twice still produces the same hash (determinism confirmed)

---

## Subtask T029 — Full #1303 Verification and Final Suite Check

**Purpose**: Confirm all 5 charter synthesizer tests pass and run the final cross-mission verification.

**Steps**:
1. Run the charter synthesizer cluster:
   ```bash
   pytest tests/charter/synthesizer/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/wp06-after.txt
   ```

2. Run the full suite to confirm net failure count ≤ refreshed baseline:
   ```bash
   PWHEADLESS=1 pytest tests/ -q --tb=no -p no:cacheprovider 2>&1 | tee /tmp/final-suite.txt
   tail -3 /tmp/final-suite.txt
   ```
   Compare to the count in `baseline-refresh.md` from WP01.

3. Commit all WP06 changes:
   ```bash
   git add -p
   git commit -m "fix(#1303): make synthesizer manifest hash deterministic and route writes through path_guard"
   ```

4. Write a brief summary comment in `baseline-refresh.md` noting the post-fix state (optional but helpful for the reviewer).

**Validation**:
- [ ] All 5 `tests/charter/synthesizer/` tests pass
- [ ] Full suite failure count ≤ count in `baseline-refresh.md`
- [ ] No regressions in sync/contract/next/doctrine tests
- [ ] Changes committed with issue-scoped message

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: Allocated by `lanes.json`.

Implementation command:
```bash
spec-kitty agent action implement WP06 --agent claude
```

---

## Definition of Done

- [ ] `test_manifest` passes
- [ ] `test_path_guard` passes
- [ ] `test_chokepoint_coverage` passes
- [ ] `test_bundle_validate_extension` passes
- [ ] `test_bundle_validate_cli` passes
- [ ] Full suite failure count ≤ WP01 baseline
- [ ] Synthesizer produces identical output on repeated runs (manually verified)
- [ ] Changes committed with issue-scoped message

---

## Risks

- **Hash mismatch from timestamp**: If a timestamp is deeply embedded in the manifest structure, removing it may change the semantics of the stored bundle. Verify with the charter context maintainers before removing timestamps.
- **Fixture regeneration order**: Do T025 and T026 completely before T028. Regenerating fixtures too early will just lock in the wrong (non-deterministic) hash.
- **path_guard API mismatch**: If path_guard.py has a different API than expected, read the file fully before routing writes through it.
- **Chokepoint test is brittle**: If `test_chokepoint_coverage` uses string matching on source code to enumerate call sites, adding the write in T026 may need a specific format (e.g., a specific comment or registration call) to be recognized.
