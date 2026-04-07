---
work_package_id: WP07
title: Status Test Suite CI Stage Split
dependencies: []
requirement_refs: [NFR-008]
planning_base_branch: feature/metadata-state-type-hardening
merge_target_branch: feature/metadata-state-type-hardening
branch_strategy: Planning artifacts for this feature were generated on feature/metadata-state-type-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/metadata-state-type-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
phase: Phase 4 - Infrastructure & Cross-Cutting
assignee: ''
agent: "codex"
shell_pid: "226958"
history:
- at: '2026-04-06T06:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: .github/workflows/ci-quality.yml
execution_mode: code_change
lane: planned
agent_profile: implementer
owned_files:
- .github/workflows/ci-quality.yml
task_type: implement
---

# Work Package Prompt: WP07 – Status Test Suite CI Stage Split

## IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- **Objective**: Add dedicated `fast-tests-status` and `integration-tests-status` CI jobs to `.github/workflows/ci-quality.yml`, running status-layer tests in parallel with existing core/doctrine test stages. Update existing jobs to exclude status test paths.
- **NFR-008**: Status-layer tests run in a dedicated CI stage parallel to core tests.
- **Acceptance**: New CI jobs appear in the workflow; `fast-tests-core` no longer executes status tests; total wall-clock time for fast stages does not increase.

## Context & Constraints

- **Plan**: `kitty-specs/065-wp-metadata-state-type-hardening/plan.md` (WP07 section)
- **Research**: `kitty-specs/065-wp-metadata-state-type-hardening/research.md` (Finding 4 — CI Stage Layout)

**Target CI graph** (from plan.md):
```
kernel-tests
├── fast-tests-doctrine     (unchanged)
├── fast-tests-status       (NEW: tests/status/ + tests/specify_cli/status/)
├── fast-tests-core         (modified: --ignore these paths)
│   ├── integration-tests-doctrine    (unchanged)
│   ├── integration-tests-status      (NEW: needs fast-tests-status + fast-tests-core)
│   └── integration-tests-core        (modified: same ignores)
```

**This WP is independent of all others** and can be implemented at any point during the mission.

**Doctrine**:
- **Self Observation Protocol** (NFR-009): Write observation log at session end.
- **Quality Gate** (DIRECTIVE_030): Tests + type checks must pass before `for_review`.

## Branch Strategy

- **Implementation command**: `spec-kitty implement WP07`
- **Planning base branch**: `feature/metadata-state-type-hardening`
- **Merge target branch**: `feature/metadata-state-type-hardening`

## Subtasks & Detailed Guidance

### Subtask T034 – Add fast-tests-status CI job

- **Purpose**: Create a new CI job that runs status-layer tests in parallel with existing fast test jobs.
- **Steps**:
  1. Open `.github/workflows/ci-quality.yml`:
     ```bash
     rg "fast-tests-core|fast-tests-doctrine" .github/workflows/ci-quality.yml
     ```
  2. Add a new `fast-tests-status` job that:
     - Depends on `kernel-tests` (same as `fast-tests-core`)
     - Runs only status test paths:
       ```yaml
       - name: Run fast status tests
         run: |
           pytest tests/status/ tests/specify_cli/status/ -x --timeout=60 -v
       ```
     - Uses the same Python version, caching, and checkout setup as `fast-tests-core`
  3. Ensure the job name is unique — no collision with existing matrix entries:
     ```bash
     rg "fast-tests" .github/workflows/ci-quality.yml
     ```
  4. Verify test discovery locally:
     ```bash
     pytest --collect-only tests/status/ tests/specify_cli/status/ 2>/dev/null | tail -5
     ```
     If either path doesn't exist yet (WP05 creates `tests/specify_cli/status/`), the job should gracefully handle empty paths or be committed after WP05.
- **Files**: `.github/workflows/ci-quality.yml`
- **Parallel?**: Yes — can be done alongside T035 (both are new job definitions in the same file).
- **Validation**:
  - [ ] `fast-tests-status` job defined in CI config
  - [ ] Depends on `kernel-tests`
  - [ ] Runs correct test paths

### Subtask T035 – Add integration-tests-status CI job

- **Purpose**: Create a new CI job for integration-level status tests.
- **Steps**:
  1. Add an `integration-tests-status` job that:
     - Depends on both `fast-tests-status` and `fast-tests-core` (integration tests run after fast tests pass)
     - Runs status integration tests (if separate from fast):
       ```yaml
       needs: [fast-tests-status, fast-tests-core]
       ```
     - Uses the same setup as `integration-tests-core`
  2. If there's no distinction between fast and integration status tests currently, the job can run the same test paths with different markers or simply be a placeholder that runs the full status suite:
     ```yaml
     - name: Run integration status tests
       run: |
         pytest tests/status/ tests/specify_cli/status/ -x --timeout=120 -v
     ```
  3. Check existing integration test patterns for guidance:
     ```bash
     rg "integration-tests" .github/workflows/ci-quality.yml | head -10
     ```
- **Files**: `.github/workflows/ci-quality.yml`
- **Parallel?**: Yes — can be defined alongside T034.
- **Validation**:
  - [ ] `integration-tests-status` job defined
  - [ ] Correct `needs:` dependencies
  - [ ] Runs correct test paths

### Subtask T036 – Update existing CI jobs to --ignore status paths

- **Purpose**: Ensure `fast-tests-core` and `integration-tests-core` no longer run status tests (they're handled by the new dedicated jobs).
- **Steps**:
  1. In the `fast-tests-core` job, add `--ignore` flags:
     ```yaml
     - name: Run fast core tests
       run: |
         pytest tests/ -x --timeout=60 \
           --ignore=tests/status/ \
           --ignore=tests/specify_cli/status/
     ```
  2. Similarly update `integration-tests-core`.
  3. Verify locally that the ignore paths are correct:
     ```bash
     pytest --collect-only tests/ --ignore=tests/status/ --ignore=tests/specify_cli/status/ 2>/dev/null | grep "status" | head -5
     ```
     Should return no status test files.
  4. Also verify that status tests ARE collected without the ignore:
     ```bash
     pytest --collect-only tests/status/ tests/specify_cli/status/ 2>/dev/null | head -5
     ```
- **Files**: `.github/workflows/ci-quality.yml`
- **Validation**:
  - [ ] `fast-tests-core` has `--ignore` for status paths
  - [ ] `integration-tests-core` has `--ignore` for status paths
  - [ ] Status tests still collected by the new dedicated jobs

### Subtask T037 – Validate CI jobs run correctly

- **Purpose**: Push the branch and verify the new CI jobs appear and run correctly.
- **Steps**:
  1. Run a local dry-run to verify test collection:
     ```bash
     # Status tests only
     pytest --collect-only tests/status/ tests/specify_cli/status/ 2>/dev/null

     # Core tests without status
     pytest --collect-only tests/ --ignore=tests/status/ --ignore=tests/specify_cli/status/ 2>/dev/null | wc -l
     ```
  2. Verify no test is "lost" — the sum of status + core (ignored) tests should equal the total:
     ```bash
     # Total tests
     pytest --collect-only tests/ 2>/dev/null | tail -1
     # Core without status
     pytest --collect-only tests/ --ignore=tests/status/ --ignore=tests/specify_cli/status/ 2>/dev/null | tail -1
     # Status only
     pytest --collect-only tests/status/ tests/specify_cli/status/ 2>/dev/null | tail -1
     ```
  3. If the numbers add up, the CI config is correct. Note any discrepancies in the Activity Log.
  4. After pushing, check the GitHub Actions UI to verify:
     - `fast-tests-status` appears as a new job
     - `integration-tests-status` appears as a new job
     - `fast-tests-core` does NOT run status tests (check job logs)
     - All jobs pass
- **Files**: No file changes — validation only.
- **Validation**:
  - [ ] Local test collection verified (no tests lost)
  - [ ] CI jobs visible in GitHub Actions (after push)
  - [ ] All CI jobs pass

## Definition of Done

- [ ] `fast-tests-status` CI job added (T034)
- [ ] `integration-tests-status` CI job added (T035)
- [ ] `fast-tests-core` and `integration-tests-core` ignore status paths (T036)
- [ ] No tests lost — sum of dedicated + ignored equals total (T037)
- [ ] CI pipeline runs successfully
- [ ] Total wall-clock time for fast stages does not increase

## Risks & Mitigations

- **Risk**: CI job names may collide with existing matrix entries. **Mitigation**: Verify unique names with `rg` before committing.
- **Risk**: `--ignore` paths may not match exactly if test directory structure changes. **Mitigation**: Test locally with `--collect-only` before pushing.
- **Risk**: Some status tests may have implicit dependencies on core fixtures. **Mitigation**: Run status tests in isolation locally first; fix any fixture imports.

## Review Guidance

- Verify new CI jobs have correct `needs:` dependencies (parallel with doctrine, not serial)
- Check that `--ignore` paths match the actual test directory structure
- Confirm no tests are "lost" — verify sum of status + core tests equals total
- Check that existing CI jobs (doctrine, core) are NOT modified beyond adding `--ignore` flags

## Activity Log

- 2026-04-06T06:15:00Z – system – Prompt created.
- 2026-04-06T07:01:51Z – opencode – shell_pid=152804 – Started implementation via action command
- 2026-04-06T07:21:01Z – opencode – shell_pid=152804 – T034-T037 complete. CI split validated: 477 status + 7155 core = 7632 total (zero tests lost). Status tests pass in isolation (<1s). Ready for review.
- 2026-04-06T08:24:52Z – codex – shell_pid=226958 – Started review via action command
- 2026-04-06T08:25:42Z – codex – shell_pid=226958 – Review passed: CI status stage split validated; status/core collection partitions are consistent
