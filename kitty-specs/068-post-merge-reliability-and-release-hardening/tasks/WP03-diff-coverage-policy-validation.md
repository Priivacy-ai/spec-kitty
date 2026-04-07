---
work_package_id: WP03
title: Diff-Coverage Policy Validation And Closure
dependencies: []
requirement_refs:
- FR-010
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-068-post-merge-reliability-and-release-hardening
base_commit: e361b104cbecf8fb24bf8c9f504d0f0868c14492
created_at: '2026-04-07T09:17:31.278877+00:00'
subtasks:
- T015
- T016
- T017
- T018
shell_pid: "61930"
agent: "claude:sonnet:reviewer:reviewer"
history:
- at: '2026-04-07T08:46:34Z'
  actor: claude
  action: created
authoritative_surface: kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md
execution_mode: code_change
mission_number: '068'
mission_slug: 068-post-merge-reliability-and-release-hardening
owned_files:
- kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md
- .github/workflows/ci-quality.yml
- docs/explanation/diff-coverage-policy.md
- tests/release/test_diff_coverage_policy.py
priority: P1
status: planned
---

# WP03 — Diff-Coverage Policy Validation And Closure

## Objective

Resolve issue [Priivacy-ai/spec-kitty#455](https://github.com/Priivacy-ai/spec-kitty/issues/455) by validating current `ci-quality.yml` behavior against the policy intent and then taking the correct fork: either close the issue with evidence (FR-011) or modify the workflow so only critical-path coverage hard-fails (FR-012). This is a **verification-first** WP — no workflow edits before the validation report exists.

## Context

Mission 067 partially addressed #455. Current main's `.github/workflows/ci-quality.yml` already enforces critical-path diff coverage and emits a separate advisory full-diff report. The question WP03 must answer is: does this enforce/advisory split actually match the policy intent of #455, or are large PRs still hitting misleading hard failures?

The expected outcome (per the spec's Assumptions section) is the **FR-011 path** — current main already satisfies the intent and the fix is to close the issue with evidence and tighten messages. But WP03 MUST NOT skip the validation step. Walking the current workflow on a real large PR sample is mandatory before any code change OR before closing the issue.

**Key spec references**:
- FR-010: written validation report BEFORE any policy code is changed
- FR-011: close-with-evidence path if current main satisfies intent
- FR-012: tighten-workflow path if there's residual mismatch
- C-005: closing comment must link to merge commit AND verification evidence
- NFR-006 carve-out: WP03 may legitimately change the threshold; NFR-006 is re-evaluated after WP03 lands rather than blocking it

**Key planning references**:
- `contracts/diff_coverage_policy.md` for the validation report schema and the test surface (including the content gate)
- `data-model.md` for `DiffCoverageValidationReport` shape
- `research.md` "Current-Main Analysis" for `.github/workflows/ci-quality.yml` context

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP03` and resolved from `lanes.json`.

To start work:
```bash
spec-kitty implement WP03
```

## Subtasks

### T015 — Author the WP03 validation report

**Purpose**: Walk the current `.github/workflows/ci-quality.yml` against the policy intent of #455. Capture findings. Decide.

**Files**:
- New: `kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md`

**Steps**:
1. Read `.github/workflows/ci-quality.yml` end-to-end. Identify:
   - Which job runs critical-path diff coverage
   - Which job runs full-diff coverage
   - What threshold each enforces
   - Which step has `continue-on-error: true` (advisory) vs hard-fail
   - The critical-path file list source (config path or pattern)
2. Identify a representative large PR. Options:
   - Use the most recent merged large PR (PR #452 from mission 067 is a good candidate; it's the squash-merge that motivated this whole mission)
   - Or build a synthetic large diff via `git diff --stat HEAD~10 HEAD`
3. Walk the PR through the policy mentally (or run `coverage.py` locally if you want hard data) and record:
   - Critical-path coverage % observed
   - Full-diff coverage % observed
   - Whether the build passes correctly under the current policy
   - Any cases where the build hard-failed on a surface that the policy never intended to gate
4. Write the report at `kitty-specs/068-post-merge-reliability-and-release-hardening/wp03-validation-report.md` with the structure from `contracts/diff_coverage_policy.md`:
   - Validated at commit (use the current HEAD)
   - Workflow path (absolute)
   - Sample PR description
   - Critical-path threshold (enforced)
   - Full-diff threshold (advisory)
   - Findings (checkbox list of policy mismatches OR explicit "no mismatches found" entries)
   - Decision: `close_with_evidence` OR `tighten_workflow` (exactly one)
   - Rationale (≥ 50 characters)
5. **Content gate**: if your decision is `close_with_evidence`, every finding must carry an explicit "satisfied by" rationale (e.g., "satisfied by line 35 of ci-quality.yml which marks full-diff as continue-on-error").

**Validation**: the report file exists, has all required sections, and exactly one decision is recorded. The content gate test (T018) will assert this.

### T016 — FR-011 path: close #455 + tighten CI step names (only if `decision == close_with_evidence`)

**Purpose**: Close the issue with evidence and improve CI output messages so future contributors immediately understand which surface is enforced and which is advisory.

**Files**:
- Possibly modified: `.github/workflows/ci-quality.yml` (renaming step `name:` fields only; no logic changes)
- Possibly created: `docs/explanation/diff-coverage-policy.md`

**Steps** (only if T015's decision is `close_with_evidence`):
1. Update CI step `name:` fields in `ci-quality.yml` to be self-documenting:
   - Old: `name: Diff coverage check`
   - New: `name: diff-coverage (critical-path, enforced)`
   - Old: `name: Full diff coverage report`
   - New: `name: diff-coverage (full-diff, advisory)`
   - **No logic changes**, only renames
2. Optionally create `docs/explanation/diff-coverage-policy.md` documenting:
   - What the critical-path file set is
   - Why critical-path is enforced and full-diff is advisory
   - How to interpret CI output
   - How to add files to the critical-path set
3. Close issue #455 with a comment containing:
   - Link to the validation report
   - Quote of the relevant `ci-quality.yml` line ranges
   - Link to PR/commit landing this WP
   - Statement: "Validated on current main: critical-path enforce + advisory full-diff already satisfies #455's policy intent. No workflow logic changes required. CI step names tightened in <commit>."

**Validation**: `git diff main -- .github/workflows/ci-quality.yml` shows ONLY `name:` field changes (no `if:`, no `run:`, no threshold changes). #455 is closed with the documented comment.

**SKIP this subtask if T015's decision is `tighten_workflow` instead.**

### T017 — FR-012 path: modify `ci-quality.yml` + add large-PR test (only if `decision == tighten_workflow`)

**Purpose**: If validation found a real mismatch, fix it. Modify the workflow so only the intended critical-path surface produces hard failures and full-diff coverage stays advisory.

**Files**:
- Modified: `.github/workflows/ci-quality.yml`

**Steps** (only if T015's decision is `tighten_workflow`):
1. Identify the specific mismatch from the validation report
2. Modify `ci-quality.yml` to fix it. Common shapes:
   - Add `continue-on-error: true` to a step that should be advisory but is hard-failing
   - Narrow the critical-path file pattern (in the diff-cover config or the workflow `paths:` filter)
   - Move a step between jobs to change its hard-fail semantics
3. Add an integration test (or a curated synthetic diff test) demonstrating that a large PR meeting critical-path coverage but missing full-diff coverage now passes
4. Close issue #455 with a comment containing:
   - Link to the validation report
   - Diff of the workflow change
   - Link to the new test
   - Statement: "Validated on current main: residual mismatch in <specific issue>. Fixed in <commit>."

**Validation**: `act` (or a real CI run) shows the synthetic large PR passes. The workflow diff is minimal and targeted.

**SKIP this subtask if T015's decision is `close_with_evidence` instead.**

### T018 — Test suite covering the report content gate, decision recording, and conditional FR-011/FR-012 paths

**Purpose**: Lock the validation report contract and the conditional paths.

**Files**:
- New: `tests/release/test_diff_coverage_policy.py`

**Tests** (per `contracts/diff_coverage_policy.md` test surface table):
- `test_validation_report_authored` — file exists, has all required sections (validated at, workflow path, sample PR, thresholds, findings, decision, rationale)
- `test_decision_is_recorded` — exactly one of `close_with_evidence` or `tighten_workflow` is checked
- `test_validation_report_close_path_populated` — **the content gate**:
  - When decision is `close_with_evidence`, rationale length ≥ 50 chars
  - AND either findings list is empty OR each finding carries a "satisfied by" rationale
  - This prevents shipping a vacuous report
- `test_close_with_evidence_does_not_modify_workflow` — when decision is `close_with_evidence`, `git diff main -- .github/workflows/ci-quality.yml` is empty OR contains only `name:` field changes
- `test_tighten_workflow_passes_large_pr_sample` — only if FR-012 fired; runs the synthetic large PR through the modified workflow and asserts it passes

**Validation**: `pytest tests/release/test_diff_coverage_policy.py -v` exits zero. The content gate fires if anyone tries to ship a vacuous report.

## Test Strategy

Tests are required by the spec (FR-010 mandates the report; FR-011/FR-012 mandate the conditional behavior). The most important test is the **content gate** (`test_validation_report_close_path_populated`) — it prevents WP03 from shipping a vacuous "I authored a file" report.

## Definition of Done

- [ ] `wp03-validation-report.md` exists with all required sections and a recorded decision
- [ ] Rationale is ≥ 50 characters
- [ ] If decision is `close_with_evidence`: every finding has a "satisfied by" rationale, CI step names are tightened, #455 is closed with evidence
- [ ] If decision is `tighten_workflow`: workflow modified, large-PR test added, #455 is closed with workflow diff
- [ ] All tests in `test_diff_coverage_policy.py` pass
- [ ] `git diff main -- .github/workflows/ci-quality.yml` is consistent with the chosen path (empty/name-only on close path, targeted change on tighten path)

## Risks

- **Skipping validation**: jumping straight to "make full-diff advisory" without the validation step is forbidden by FR-010. The validation report MUST exist before any workflow edit.
- **Vacuous report**: a one-paragraph "looks fine to me" report would pass the file-exists test but fail the content gate. The 50-char rationale + "satisfied by" requirement is the safety net.
- **Wrong fork**: if you author a `close_with_evidence` report and then also modify the workflow logic, the test `test_close_with_evidence_does_not_modify_workflow` will fail. Pick one fork and stick with it.
- **NFR-006 interaction**: NFR-006 is pinned to commit `7307389a` for exactly this reason — WP03 may legitimately change the threshold without breaking NFR-006. The carve-out is documented in NFR-006's body in `spec.md`.

## Reviewer Guidance

- Open the validation report and read the rationale — does it actually justify the decision, or is it boilerplate?
- If the decision is `close_with_evidence`, verify the workflow diff contains ONLY `name:` field changes
- If the decision is `tighten_workflow`, verify the change is targeted (not a wholesale rewrite)
- Verify #455 is closed with a comment linking to evidence, not silently closed

## Next steps after merge

WP03 is verification-first and low-risk. Once it lands, #455 is permanently off the workflow-stabilization track.

## Activity Log

- 2026-04-07T09:23:28Z – unknown – shell_pid=42198 – Claimed by claude orchestrator
- 2026-04-07T09:29:21Z – unknown – shell_pid=42198 – Ready for review: diff-coverage policy validated and documented
- 2026-04-07T09:29:56Z – claude:sonnet:reviewer:reviewer – shell_pid=59664 – Started review via action command
- 2026-04-07T09:31:42Z – claude:sonnet:reviewer:reviewer – shell_pid=59664 – Moved to planned
- 2026-04-07T09:33:46Z – claude:sonnet:reviewer:reviewer – shell_pid=59664 – Fixed: issue #455 closed with evidence comment
- 2026-04-07T09:34:12Z – claude:sonnet:reviewer:reviewer – shell_pid=61930 – Started review via action command
