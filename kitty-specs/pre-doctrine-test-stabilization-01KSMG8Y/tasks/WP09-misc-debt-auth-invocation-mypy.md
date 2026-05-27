---
work_package_id: WP09
title: Misc debt — auth / invocation / mypy / mission switching
dependencies: []
requirement_refs:
- FR-011
- FR-014
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pre-doctrine-test-stabilization-01KSMG8Y
base_commit: fcec446d1be3c2c67d5ce9f0bc36a40133fe6684
created_at: '2026-05-27T12:19:43.288952+00:00'
subtasks:
- T036
- T037
- T038
- T039
- T040
- T041
- T050

shell_pid: "42001"
agent: "claude:claude-opus-4-7:debugger-debbie:investigator"
history:
- date: '2026-05-27'
  event: created
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- src/specify_cli/auth/**
- src/specify_cli/cli/commands/invocations_cmd.py
- src/specify_cli/mission_step_contracts/executor.py
- tests/auth/**
- tests/specify_cli/invocation/**
- tests/cross_cutting/test_mypy_strict_mission_step_contracts.py
- tests/missions/test_mission_switching_integration.py
role: investigator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load debugger-debbie
```

---

## Objective

Fix five in-scope miscellaneous debt items from #1310 and file two GitHub issues for the re-deferred items. The five fixes are independent — address them in any order. The two re-defer issues MUST be filed before this WP is closed (C-008).

**Closes**: GitHub issue #1310 (partially; two items re-deferred with new issues)

---

## Context

These are miscellaneous failures that don't fit neatly into other waves. Each requires test-driven investigation. Two items (`spec-kitty.checklist` skill package and schema-version wording) are explicitly re-deferred because they require dedicated mission work.

**Self-referential trap for T039**: The Pydantic validator test (`test_all_kitty_specs_wp_files_validate`) uses a glob that includes ALL `kitty-specs/` WP files — including this mission's own WP files. By the time WP09 runs (after WP01–WP08 are merged), this mission's WP files will exist on disk. Run the validator test FIRST to see the current failure list before attempting any fixes.

---

## Subtask T036 — Fix auth integration exit-code

**Purpose**: `test_refresh_through_transport` returns exit code 2 instead of the expected value.

**Steps**:

1. Run the test to understand the failure:
   ```bash
   pytest tests/auth/ -v --tb=long -k "refresh_through_transport" 2>&1 | head -60
   ```

2. Read the test to identify:
   - What exit code is expected
   - What command/path produces exit code 2

3. Trace the exit-code propagation in `src/specify_cli/auth/`:
   ```bash
   grep -rn "exit\|Exit\|return.*2\|sys.exit" src/specify_cli/auth/ --include="*.py" | head -20
   ```

4. Fix the exit-code propagation (do not change the expected exit code in the test — fix the production code).

5. Run the test to confirm:
   ```bash
   pytest tests/auth/ -v --tb=short -k "refresh_through_transport"
   ```

**Files**: `src/specify_cli/auth/` (exit-code propagation path)

**Validation**:
- [ ] `tests.auth.integration.test_refresh_through_transport` passes
- [ ] The exit code matches the test's expectation

---

## Subtask T037 — Prevent logged_out_on_connected_teamspace noise from JSON output

**Purpose**: The string `logged_out_on_connected_teamspace` is leaking into JSON CLI output. When `--json` flag is used, only valid JSON should appear on stdout.

**Steps**:

1. Run the failing invocation tests:
   ```bash
   pytest tests/specify_cli/invocation/ -v --tb=long -k "do or profiles or record" 2>&1 | head -80
   ```
   Exact test IDs: `tests.specify_cli.invocation.cli.test_do`, `test_profiles`, `test_record`.

2. Identify where `logged_out_on_connected_teamspace` is printed:
   ```bash
   grep -rn "logged_out_on_connected_teamspace\|logged.out" src/specify_cli/ --include="*.py" | head -10
   ```

3. The print or echo call must be guarded so it only appears when NOT in JSON mode. Add a check like:
   ```python
   if not json_output:
       console.print("logged_out_on_connected_teamspace")
   ```
   Or route it through the existing JSON-aware output mechanism.

4. Run the tests to confirm:
   ```bash
   pytest tests/specify_cli/invocation/ -v --tb=short -k "do or profiles or record"
   ```

**Files**: `src/specify_cli/cli/commands/invocations_cmd.py` or related

**Validation**:
- [ ] `test_do`, `test_profiles`, `test_record` all pass
- [ ] JSON output contains no non-JSON noise

---

## Subtask T038 — Fix mypy --strict failures in executor.py

**Purpose**: `executor.py` must pass `mypy --strict`. The cross-cutting test validates this.

**Steps**:

1. Run the mypy test to get current errors:
   ```bash
   pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -v --tb=long 2>&1 | head -60
   ```

2. Run mypy directly to get the full error list with line numbers:
   ```bash
   mypy --strict src/specify_cli/mission_step_contracts/executor.py 2>&1
   ```

3. Fix each mypy error:
   - Missing return type annotations: add `-> ReturnType`
   - Missing parameter type annotations: add `: TypeHint`
   - Implicit `Any`: add explicit types or `cast()`
   - `[no-untyped-def]`: add type annotations
   - `[no-untyped-call]`: annotate the called function or add overloads

4. Run mypy again until clean:
   ```bash
   mypy --strict src/specify_cli/mission_step_contracts/executor.py 2>&1 | grep -c "error:"
   ```
   Should output `0`.

5. Run the test to confirm:
   ```bash
   pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py::test_mission_step_contracts_executor_is_mypy_strict_clean -v
   ```

**Files**: `src/specify_cli/mission_step_contracts/executor.py`

**Validation**:
- [ ] `test_mission_step_contracts_executor_is_mypy_strict_clean` passes
- [ ] `mypy --strict executor.py` exits with 0 errors

---

## Subtask T039 — Fix or exclude legacy kitty-specs WP files failing Pydantic validation

**Purpose**: `test_all_kitty_specs_wp_files_validate` uses a glob to check all WP files in `kitty-specs/`. Some legacy WP files (from pre-3.0 missions) fail Pydantic validation.

**SELF-REFERENTIAL TRAP**: By the time WP09 runs, this mission's own WP files will exist at `kitty-specs/pre-doctrine-test-stabilization-01KSMG8Y/tasks/WP*.md`. Run the validator test FIRST to see the current failure list before fixing anything.

**Steps**:

1. Run the validator test to see the full current failure list:
   ```bash
   pytest tests/specify_cli/status/test_wp_metadata.py::test_all_kitty_specs_wp_files_validate -v --tb=long 2>&1 | head -80
   ```

2. Categorize the failing files:
   - This mission's own WP files (WP01–WP11) — if they fail, fix the frontmatter
   - Legacy pre-3.0 WP files — fix if trivial, or add to the validator's exclude list with rationale

3. For this mission's WP files: ensure the frontmatter matches the validator's schema (all required fields present and correctly typed).

4. For legacy WP files that cannot be trivially fixed: add them to the validator's exclude list in the test or the validator config. Document WHY each excluded file is excluded.

5. For exactly 6 failing WP files (per spec): fix or exclude each one.

6. Run the test until it passes:
   ```bash
   pytest tests/specify_cli/status/test_wp_metadata.py::test_all_kitty_specs_wp_files_validate -v
   ```

**Files**: Legacy WP files in `kitty-specs/` and/or validator test/config

**Validation**:
- [ ] `test_all_kitty_specs_wp_files_validate` passes
- [ ] This mission's own WP files (WP01–WP11) all have valid frontmatter
- [ ] Excluded files have documented rationale

---

## Subtask T040 — Fix mission-switching blocking condition

**Purpose**: Two test parametrizations in `test_mission_switching_integration` are blocked by an unknown condition.

**Steps**:

1. Run the tests:
   ```bash
   pytest tests/missions/test_mission_switching_integration.py -v --tb=long 2>&1 | head -80
   ```

2. Identify the blocking condition from the test output — is it:
   - A git state issue?
   - A metadata lock?
   - A missing field in `meta.json`?
   - An unsatisfied pre-condition?

3. Trace the mission-switching code to the blocking point:
   ```bash
   grep -rn "switch\|mission_switch\|select_mission" src/specify_cli/ --include="*.py" | head -15
   ```

4. Fix the blocking condition.

5. Run the tests:
   ```bash
   pytest tests/missions/test_mission_switching_integration.py -v
   ```

**Files**: Mission-switching implementation (as identified by tests)

**Validation**:
- [ ] Both `test_mission_switching_integration` parametrizations pass

---

## Subtask T041 — File GitHub issues for re-deferred items (C-008 mandatory)

**Purpose**: Two items from #1310 cannot be fixed within this mission's scope. Per C-008, each must have a filed follow-on GitHub issue BEFORE WP09 is closed.

**Re-deferred items**:

1. **`spec-kitty.checklist` skill package missing**: The skill package requires dedicated template work outside this mission's scope (new skill packaging infrastructure). File a new GitHub issue with:
   - Title: "Restore spec-kitty.checklist skill package"
   - Body: reference to #1310, explanation of why it is deferred, scope estimate
   - Labels: `needs-triage` or similar

2. **Schema-version wording drift**: Minor UX wording inconsistency in schema version descriptions. File a new GitHub issue with:
   - Title: "Fix schema-version wording drift in CLI output"
   - Body: reference to #1310, brief description of what the drift is
   - Labels: `good-first-issue` or similar (it is a minor fix)

**Steps**:

```bash
# Unset GITHUB_TOKEN to use keyring auth with broader scopes
unset GITHUB_TOKEN

gh issue create --title "Restore spec-kitty.checklist skill package" \
  --body "Deferred from #1310 (mission 01KSMG8Y). The checklist skill package requires dedicated template work outside the pre-doctrine-stabilization scope. This item was explicitly re-deferred per C-008 of the mission spec." \
  --label "needs-triage"

gh issue create --title "Fix schema-version wording drift in CLI output" \
  --body "Deferred from #1310 (mission 01KSMG8Y). Minor UX wording inconsistency in schema version descriptions. Suitable as a good-first-issue. Explicitly re-deferred per C-008 of the mission spec." \
  --label "good-first-issue"
```

Record the new issue numbers in the WP09 commit message.

**Validation**:
- [ ] Two new GitHub issues filed
- [ ] Issue numbers recorded in commit message
- [ ] Issues reference #1310 and the mission slug

---

## Subtask T050 — Delete stray test-feature-* missions and enforce teardown hygiene (FR-014)

**Purpose**: Ten stray `test-feature-*` mission directories exist in `kitty-specs/` from test runs that did not clean up after themselves. FR-014 requires (a) immediate deletion of all existing stray directories, (b) fixture-level teardown in every test that creates a mission directory, and (c) a `.gitignore` safety net.

**Steps**:

1. Delete all existing stray directories:
   ```bash
   git rm -r kitty-specs/test-feature-01KRR081 \
              kitty-specs/test-feature-01KRZEQE \
              kitty-specs/test-feature-01KSETQZ \
              kitty-specs/test-feature-01KSFS15 \
              kitty-specs/test-feature-01KSFSQ7 \
              kitty-specs/test-feature-01KSFTAC \
              kitty-specs/test-feature-01KSFXEV \
              kitty-specs/test-feature-01KSFXTT \
              kitty-specs/test-feature-01KSHPPB \
              kitty-specs/test-feature-01KSHQ1R
   ```
   Confirm: `find kitty-specs/ -maxdepth 1 -name "test-feature-*" | wc -l` → must print `0`.

2. Add a `.gitignore` rule so future test-created missions cannot be accidentally staged:
   ```bash
   echo "kitty-specs/test-feature-*/" >> .gitignore
   ```
   Verify: `grep "test-feature" .gitignore` shows the rule.

3. Find all tests that create mission directories during execution:
   ```bash
   grep -rn "mission create\|mission_create\|MissionCreate\|kitty-specs.*test" tests/ \
     --include="*.py" -l
   ```
   For each identified file, locate the creation call and ensure a `yield`-based fixture cleans up:
   ```python
   @pytest.fixture
   def tmp_mission(tmp_path, monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SPECS_DIR", str(tmp_path))
       yield tmp_path
       # cleanup happens automatically via tmp_path isolation
   ```
   Preferred: redirect `SPEC_KITTY_SPECS_DIR` (or equivalent env var) to `tmp_path` so missions are created outside `kitty-specs/`. If the code does not support redirection, add explicit `shutil.rmtree` teardown in a `yield` fixture.

4. Run `test_all_kitty_specs_wp_files_validate` and `test_mission_switching_integration` to confirm no regression from the directory removals.

5. Confirm `kitty-specs/` has no `test-feature-*` directories:
   ```bash
   find kitty-specs/ -maxdepth 1 -name "test-feature-*"
   ```
   Must return empty.

**Files**: `.gitignore`, `tests/` (fixture changes in whichever test files create mission dirs)

**Validation**:
- [ ] `find kitty-specs/ -maxdepth 1 -name "test-feature-*"` returns empty
- [ ] `.gitignore` contains `kitty-specs/test-feature-*/`
- [ ] Every test that creates a mission directory has unconditional teardown (pass AND fail)
- [ ] `test_all_kitty_specs_wp_files_validate` still passes after deletions

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

This WP can run in parallel with WP07 and WP08.

To start implementation:
```bash
spec-kitty agent action implement WP09 --agent claude
```

---

## Definition of Done

- [ ] `tests.auth.integration.test_refresh_through_transport` passes
- [ ] `tests.specify_cli.invocation.cli.test_do`, `test_profiles`, `test_record` pass
- [ ] `tests.cross_cutting.test_mypy_strict_mission_step_contracts::test_mission_step_contracts_executor_is_mypy_strict_clean` passes
- [ ] `tests.specify_cli.status.test_wp_metadata::test_all_kitty_specs_wp_files_validate` passes
- [ ] `tests.missions.test_mission_switching_integration` (both parametrizations) pass
- [ ] Two new GitHub issues filed for re-deferred items before WP09 is closed (C-008)

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| This mission's WP files fail the Pydantic validator | Medium | Run validator test FIRST; fix own WP files if needed |
| mypy --strict requires changes to imported modules | Low | Use `cast()` or `# type: ignore` as last resort; prefer annotations |
| GitHub CLI auth fails with GITHUB_TOKEN | Medium | `unset GITHUB_TOKEN` and use keyring auth |
| Mission-switching block is a git-state issue | Medium | Run in a clean checkout; check for stale locks |

---

## Reviewer Guidance

1. T041: confirm two GitHub issues exist and reference #1310
2. T039: confirm this mission's own WP files pass validation
3. T038: confirm `mypy --strict executor.py` exits with 0 errors
4. All five in-scope test clusters pass; two items have filed follow-on issues
</content>

## Activity Log

- 2026-05-27T12:19:44Z – claude:claude-opus-4-7:debugger-debbie:investigator – shell_pid=42001 – Assigned agent via action command
- 2026-05-27T12:39:23Z – claude:claude-opus-4-7:debugger-debbie:investigator – shell_pid=42001 – T036-T041+T050 complete: all 5 in-scope tests pass (57/57), 2 re-defer issues filed (#1317 #1318). NOTE: kitty-specs/ changes (T039 legacy frontmatter fix + T050 stray dir removal) need to land on planning branch separately
