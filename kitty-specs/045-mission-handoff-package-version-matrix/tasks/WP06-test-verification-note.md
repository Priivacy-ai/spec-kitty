---
work_package_id: WP06
title: Test Run + Verification Note
lane: "doing"
dependencies: [WP02, WP03, WP04, WP05]
base_branch: 2.x
base_commit: 21a6cf3bce5293de281d8f0b2a272ab505eae166
created_at: '2026-02-23T20:35:37.533857+00:00'
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 4 - Evidence Gate
assignee: ''
agent: ''
shell_pid: "31188"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-23T18:04:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Test Run + Verification Note

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status`. If `has_feedback`, read **Review Feedback** below first.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

Run the 4 setup-plan context test scenarios on `2.x` at source commit, confirm all pass, and commit `handoff/verification.md` as the evidence gate for this handoff. This WP is the final implementation step and BLOCKS the feature from acceptance if any test fails.

**Done when**:
- [ ] pytest ran successfully on branch `2.x`
- [ ] All 4 setup-plan context scenarios are PASS
- [ ] `handoff/verification.md` is committed with the 4-scenario table
- [ ] verification.md includes: branch name, commit SHA, run date, pass/fail counts, re-run command
- [ ] Verification note is self-contained — readable without any other file

**⚠️ BLOCKING RULE**: Do NOT write verification.md if any test fails. If a failure occurs, escalate as a bug against 2.x before completing this WP.

**Implementation command** (depends on all previous WPs):
```bash
spec-kitty implement WP06 --base WP05
# Also ensure WP02, WP03, WP04 are merged before running tests
```

---

## Context & Constraints

- **Output file**: `kitty-specs/045-mission-handoff-package-version-matrix/handoff/verification.md`
- **Branch**: `2.x` (MUST be on this branch when running tests)
- **Source commit**: `21ed0738f009ca35a2927528238a48778e41f1d4` — tests validate the fix from THIS commit
- **Test files**:
  - `tests/integration/test_planning_workflow.py` (class `TestSetupPlanCommand`)
  - `tests/specify_cli/test_cli/test_agent_feature.py`
- **C-lite constraint**: No new tests are written. Existing tests are run and their output is recorded.
- **Supporting docs**: `research.md` Decision 7 (test-to-scenario mapping), `quickstart.md` (re-run command)

---

## Subtasks & Detailed Guidance

### Subtask T019 – Run the 4 Setup-Plan Context Scenarios via Pytest

**Purpose**: Execute the existing test suite to produce the evidence that the plan-context-bootstrap-fix wave is validated.

**Pre-flight checks**:
1. Confirm you are on branch `2.x`:
   ```bash
   git rev-parse --abbrev-ref HEAD
   # Must output: 2.x
   ```
2. Confirm the source commit is reachable:
   ```bash
   git log --oneline | grep "21ed0738"
   # Must show: Merge WP05 from 041-enable-plan-mission-runtime-support
   ```
3. Confirm test files exist:
   ```bash
   pytest --collect-only -q tests/integration/test_planning_workflow.py 2>&1 | grep "setup_plan"
   # Must show at least 3 test names containing "setup_plan"
   ```

**Run tests and capture output**:
```bash
pytest \
  tests/integration/test_planning_workflow.py::TestSetupPlanCommand \
  tests/specify_cli/test_cli/test_agent_feature.py \
  -v --tb=short 2>&1 | tee /tmp/verification-run-$(date +%Y%m%d-%H%M%S).txt

# Check exit code:
echo "Exit code: $?"
```

**Expected passing tests (minimum)**:
- `test_setup_plan_ambiguous_context_returns_candidates` (scenario a)
- `test_setup_plan_explicit_feature_reports_spec_path` (scenario b)
- `test_setup_plan_missing_spec_reports_absolute_path` (scenario c)
- At least one test in `test_agent_feature.py` covering invalid slug / validation error (scenario d)

**Files**: `/tmp/verification-run-*.txt` (temporary capture; not committed)

**Notes**:
- Run from repo root, not from inside a subdirectory.
- If the venv is not activated: `source .venv/bin/activate` or `poetry run pytest ...`
- `tee` captures both stdout and file simultaneously so you see results in real time.

---

### Subtask T020 – Confirm All 4 Scenarios Pass

**Purpose**: Gate on actual test results. This subtask MUST block WP06 completion if any test fails.

**Steps**:
1. Review the test output from T019.
2. Locate the final summary line (e.g., `7 passed, 0 failed`).
3. Identify which tests map to which scenario:

   | Scenario | Test Name | Expected Result |
   |---------|-----------|----------------|
   | (a) Multiple features → ambiguity error | `test_setup_plan_ambiguous_context_returns_candidates` | PASS |
   | (b) Explicit `--feature` → success | `test_setup_plan_explicit_feature_reports_spec_path` | PASS |
   | (c) Missing spec.md → hard error | `test_setup_plan_missing_spec_reports_absolute_path` | PASS |
   | (d) Invalid slug → validation error | test in `test_agent_feature.py` matching `invalid` or `slug` | PASS |

4. **If all 4 pass**: proceed to T021.
5. **If any fail**: STOP. Do not write verification.md. Document the failure in the Activity Log and leave the WP in `doing`. The failure represents a regression in the plan-context-bootstrap-fix wave and must be investigated before this WP can complete.

**Finding scenario (d)**: If you don't immediately see an invalid-slug test in the output:
```bash
pytest tests/specify_cli/test_cli/test_agent_feature.py \
  -v --collect-only 2>&1 | grep -i "invalid\|slug\|validation"
```

**Files**: No output files from this step; only a pass/fail decision.

---

### Subtask T021 – Write `verification.md` with Scenario Table

**Purpose**: Commit the evidence that the 4 test scenarios pass. This is the only proof downstream teams need that the plan-context-bootstrap-fix wave is validated.

**Steps**:
1. Gather the metadata to embed:
   ```bash
   BRANCH=$(git rev-parse --abbrev-ref HEAD)
   COMMIT=$(git rev-parse HEAD)
   RUN_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
   echo "Branch: $BRANCH | Commit: $COMMIT | Date: $RUN_DATE"
   ```
2. Write `handoff/verification.md` with this structure (fill in actual pass counts, commit, date from your run):

```markdown
# Verification Note: Setup-Plan Context Tests

**Branch**: 2.x
**Source commit (bootstrap-fix wave)**: 21ed0738f009ca35a2927528238a48778e41f1d4
**HEAD commit (at verification run)**: <actual HEAD SHA from step 1>
**Run date**: <ISO 8601 UTC from step 1>
**Overall result**: ✅ PASS

---

## Test Coverage: 4 Setup-Plan Context Scenarios

All 4 required scenarios from the plan-context-bootstrap-fix acceptance criteria are confirmed green.

| # | Scenario | Test | File | Result |
|---|---------|------|------|--------|
| (a) | Fresh session + multiple features → deterministic ambiguity error | `test_setup_plan_ambiguous_context_returns_candidates` | `tests/integration/test_planning_workflow.py` | ✅ PASS |
| (b) | Fresh session + explicit `--feature` → successful plan setup | `test_setup_plan_explicit_feature_reports_spec_path` | `tests/integration/test_planning_workflow.py` | ✅ PASS |
| (c) | Explicit feature + missing spec.md → hard error with remediation | `test_setup_plan_missing_spec_reports_absolute_path` | `tests/integration/test_planning_workflow.py` | ✅ PASS |
| (d) | Invalid feature slug → validation error | `<test_name_from_actual_run>` | `tests/specify_cli/test_cli/test_agent_feature.py` | ✅ PASS |

---

## Summary

| Metric | Value |
|--------|-------|
| Scenarios required | 4 |
| Scenarios passing | 4 |
| Scenarios failing | 0 |
| Total tests in run | <count from your output> |
| Total failures | 0 |

---
```

**Files**:
- `handoff/verification.md` (new, partial — re-run command section added in T022)

**Notes**:
- The "(a)" through "(d)" labels must map to the same scenario labels used in the spec (FR-013) for traceability.
- Use actual test names from your run for scenario (d) — do not guess.
- `HEAD commit` may differ from `source commit` (045 WPs add commits on top of the source anchor).

---

### Subtask T022 – Add Re-Run Command + Completeness Self-Check

**Purpose**: Ensure the verification note is fully self-contained — a downstream reviewer can reproduce the test run from nothing but this file.

**Steps**:
1. Append the re-run section to `handoff/verification.md`:

```markdown
---

## Re-Run Command

To reproduce this verification run from a clean checkout of spec-kitty on branch `2.x`:

```bash
git checkout 2.x
git pull origin 2.x  # Ensure latest
source .venv/bin/activate  # Or: poetry shell

pytest \
  tests/integration/test_planning_workflow.py::TestSetupPlanCommand \
  tests/specify_cli/test_cli/test_agent_feature.py \
  -v --tb=short
```

Expected: all 4 scenario tests pass; exit code 0.

---

## Notes

- Tests were run on branch `2.x` which contains the plan-context-bootstrap-fix (feature 041, source commit `21ed0738f009ca35a2927528238a48778e41f1d4`).
- The `TestSetupPlanCommand` class covers the core setup-plan behaviours introduced by the bootstrap-fix wave.
- No new tests were written for this verification; all tests existed prior to 045 implementation.
```

2. Run completeness self-check:
   ```bash
   python3 - <<'EOF'
   from pathlib import Path

   doc = Path("kitty-specs/045-mission-handoff-package-version-matrix/handoff/verification.md").read_text(encoding="utf-8")
   checks = {
       "has 4 scenario rows": all(f"({c})" in doc for c in "abcd"),
       "has PASS for all 4": doc.count("✅ PASS") >= 4,
       "has branch field": "**Branch**:" in doc,
       "has source commit": "21ed0738f009ca35a2927528238a48778e41f1d4" in doc,
       "has re-run command": "pytest" in doc and "TestSetupPlanCommand" in doc,
       "has run date": "Run date" in doc,
   }
   failures = [k for k, v in checks.items() if not v]
   if failures:
       print("COMPLETENESS FAIL:")
       for f in failures:
           print(f"  - {f}")
       import sys; sys.exit(1)
   else:
       print("verification.md: completeness PASS — all checks green")
   EOF
   ```
3. Fix any failures.

**Files**: Final append to `handoff/verification.md` (file complete)

---

## Risks & Mitigations

- **Test failure on 2.x**: The bootstrap-fix wave is supposed to be validated. If a test fails, this is a REGRESSION — escalate immediately. Do not skip or mark the test as expected-failure.
- **`TestSetupPlanCommand` class not found**: If the class name changed, use `pytest --collect-only -q tests/integration/test_planning_workflow.py` to find the current class name and update the re-run command accordingly.
- **Venv not activated**: `python3 -c "import specify_cli"` will fail if the venv is not active. Always activate before running.
- **HEAD commit differs from source commit**: This is expected and correct. The verification note records both: the source anchor (21ed...) and the HEAD at verification time (which includes 045 WP commits).

---

## Review Guidance

Reviewers verify:
1. verification.md exists in `handoff/`
2. All 4 scenario rows show ✅ PASS (no ❌ or blank)
3. `source commit` in the note == `21ed0738f009ca35a2927528238a48778e41f1d4`
4. Re-run command is copy-pasteable (no placeholders, no broken indentation)
5. Completeness self-check (T022 script) exits 0 when run against the committed file
6. No test failure was swept under the rug — if any test was skipped or xfailed, flag for discussion

---

## Activity Log

- 2026-02-23T18:04:02Z – system – lane=planned – Prompt created.
