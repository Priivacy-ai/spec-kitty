---
work_package_id: WP07
title: Targeted Coverage and CI Gate Split
dependencies: [WP01, WP02, WP03, WP04, WP05, WP06]
requirement_refs:
- FR-006
- NFR-002
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
assignee: "claude"
agent: "opencode"
role: "reviewer"
shell_pid: "254171"
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-implementer
authoritative_surface: .github/workflows/
execution_mode: code_change
lane: planned
owned_files:
- .github/workflows/ci-quality.yml
- tests/test_dashboard/test_missions_handler.py
- tests/init/test_mission_detection_coverage.py
task_type: implement
---

# Work Package Prompt: WP07 -- Targeted Coverage and CI Gate Split

## Objectives & Success Criteria

- Critical-path diff-coverage >= 90% (status, mission detection, dashboard API, scanner, merge, next)
- CI workflow split into enforced critical gate + advisory full report
- Non-critical paths have no minimum (no obtuse tests for migrations/scaffolding)

## Context & Constraints

- **Philosophy**: Coverage effort must be proportional to risk. A flat 80% gate incentivizes meaningless tests.
- **Critical paths**: `status/`, `core/mission_detection.py`, `dashboard/handlers/`, `dashboard/scanner.py`, `merge/`, `next/`
- **Non-critical**: `tasks_cli.py`, `tracker/origin.py`, `verify_enhanced.py`, all migration files
- **CI file**: `.github/workflows/ci-quality.yml` (line 761: current `--fail-under=80`)
- **Spec**: `kitty-specs/062-fix-doctrine-migration-test-failures/spec.md` (NFR-002)

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP07 --base WP06`

## Subtasks & Detailed Guidance

### Subtask T023 -- Measure diff-coverage after WP01-06

- **Purpose**: Understand the coverage baseline after all test fixes land.
- **Steps**:
  1. Run the full test suite with coverage:
     ```bash
     pytest --cov=src/specify_cli --cov-report=xml:coverage.xml
     ```
  2. Run diff-cover against the base:
     ```bash
     diff-cover coverage.xml --compare-branch=origin/develop
     ```
  3. Note the overall percentage and per-file breakdown
  4. Identify critical-path files that are below 90%
- **Output**: List of critical-path files needing tests, with specific missing line numbers

### Subtask T024 -- Write tests for dashboard handlers critical paths

- **Purpose**: The `dashboard/handlers/missions.py` file is at 7.5% coverage on changed lines -- the lowest critical-path file.
- **File**: Create or extend `tests/test_dashboard/test_missions_handler.py`
- **Focus on**:
  - `handle_missions_list()` -- test with mocked `scan_all_missions()` returning various states (empty, multiple missions, active mission)
  - `handle_kanban()` -- test with valid and invalid mission IDs
  - Use the `_DummyAPIHandler` pattern from `test_api_constitution.py`
- **Do NOT test**: Non-critical paths like error formatting, display helpers
- **Parallel?**: Yes -- independent from T025

### Subtask T025 -- Write tests for mission_detection.py uncovered lines

- **Purpose**: `core/mission_detection.py` is at 85% -- close to 90% but has gaps on lines 98, 146, 253, 263-264, 268, 276-277, etc.
- **File**: Create or extend tests in `tests/init/` or `tests/specify_cli/`
- **Steps**:
  1. Read the uncovered lines from the diff-cover output (T023)
  2. Write tests that exercise only the uncovered critical logic
  3. Skip edge cases in non-critical error handling branches
- **Parallel?**: Yes -- independent from T024

### Subtask T026 -- Split CI diff-cover into enforced critical + advisory full

- **Purpose**: Replace the flat `--fail-under=80` with risk-proportional gating.
- **File**: `.github/workflows/ci-quality.yml`
- **Current** (line 746-761):
  ```yaml
  - name: "[ENFORCED] Enforce diff coverage policy (80% on changed lines)"
    run: |
      ...
      diff-cover "${coverage_reports[@]}" \
        --compare-branch=origin/${{ github.base_ref }} \
        --fail-under=80
  ```
- **Replace with TWO steps**:
  ```yaml
  - name: "[ENFORCED] Critical-path diff coverage (90% on core modules)"
    run: |
      git fetch origin "${{ github.base_ref }}" --depth=1

      coverage_reports=()
      [ -f out/reports/fast/coverage/coverage.xml ] && coverage_reports+=(out/reports/fast/coverage/coverage.xml)
      [ -f out/reports/integration/coverage/coverage-integration.xml ] && coverage_reports+=(out/reports/integration/coverage/coverage-integration.xml)

      if [ ${#coverage_reports[@]} -eq 0 ]; then
        echo "::error::No coverage reports found for diff coverage."
        exit 1
      fi

      diff-cover "${coverage_reports[@]}" \
        --compare-branch=origin/${{ github.base_ref }} \
        --fail-under=90 \
        --include src/specify_cli/status/* \
        --include src/specify_cli/core/mission_detection.py \
        --include src/specify_cli/dashboard/handlers/* \
        --include src/specify_cli/dashboard/scanner.py \
        --include src/specify_cli/merge/* \
        --include src/specify_cli/next/*

  - name: "[ADVISORY] Full diff coverage report (informational)"
    if: always()
    run: |
      coverage_reports=()
      [ -f out/reports/fast/coverage/coverage.xml ] && coverage_reports+=(out/reports/fast/coverage/coverage.xml)
      [ -f out/reports/integration/coverage/coverage-integration.xml ] && coverage_reports+=(out/reports/integration/coverage/coverage-integration.xml)

      if [ ${#coverage_reports[@]} -gt 0 ]; then
        diff-cover "${coverage_reports[@]}" \
          --compare-branch=origin/${{ github.base_ref }} || true
      fi
  ```
- **Key details**:
  - Enforced step uses `--fail-under=90` with `--include` for critical paths only
  - Advisory step uses `|| true` so it never blocks the build
  - Advisory step has `if: always()` so it runs even if the enforced step fails

### Subtask T027 -- Verify CI workflow config validity

- **Purpose**: Ensure the YAML is syntactically valid and the `diff-cover --include` flag works.
- **Steps**:
  1. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-quality.yml'))"`
  2. Test `diff-cover --include` locally:
     ```bash
     diff-cover coverage.xml \
       --compare-branch=origin/develop \
       --fail-under=90 \
       --include 'src/specify_cli/status/*'
     ```
  3. If `--include` doesn't support globs, fall back to explicit file lists
  4. Verify the workflow file passes GitHub Actions syntax validation (push and check)

## Risks & Mitigations

- `diff-cover --include` may not support glob patterns → test locally first; use explicit file list as fallback
- Advisory step should not block the build → `|| true` ensures this
- Critical-path list may need updating as the codebase evolves → document the list in a comment in the workflow file

## Review Guidance

- Verify the critical-path file list is comprehensive (status, detection, dashboard, merge, next)
- Verify tests target genuinely critical logic, not just easy-to-cover boilerplate
- Check that the advisory step actually runs (test with a deliberate failure)

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
- 2026-04-03T16:51:43Z – claude:opus-4-6:python-implementer:implementer – Moved to in_progress
- 2026-04-03T18:49:50Z – claude:opus-4-6:python-implementer:implementer – Implementation complete: CI split + critical-path tests + worktree detection fix
- 2026-04-03T18:58:00Z – opencode:unknown:generic:unknown – shell_pid=254171 – Started review via workflow command
- 2026-04-03T19:00:58Z – opencode – shell_pid=254171 – Review passed: CI split into enforced 90% critical-path gate + advisory full report. Dashboard handler tests, worktree detection fix, and identity parser test all target genuine critical logic. YAML valid. Critical-path list comprehensive (adds kernel/doctrine/constitution beyond spec minimum). Non-blocking: owned_files list was too narrow for actual scope; T025 coverage achieved via existing test modifications rather than new file.
