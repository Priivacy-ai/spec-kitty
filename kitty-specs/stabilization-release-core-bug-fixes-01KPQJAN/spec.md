# Stabilization Release: Core Bug Fixes

**Mission ID**: 01KPQJAN4P2V4MTHRFGS7VW17M  
**Mission Slug**: stabilization-release-core-bug-fixes-01KPQJAN  
**Mission Type**: software-dev  
**Target Branch**: main  
**Validation Date**: April 21, 2026  
**Validation Repo**: Priivacy-ai/spec-kitty (fresh clone at `/tmp/spec-kitty-stabilization-20260421-101150`)

---

## Problem Statement

Four distinct bugs exist on the current `main` branch of spec-kitty, all reproduced against live code as of April 21, 2026. Left unaddressed, they cause merge operations to abort incorrectly, produce broken shim files for Gemini and Qwen agents, record an illegal lane state when reviewers claim work packages, and leave intake operations vulnerable to partial writes, unbounded memory use, and path escape. This mission fixes all four bug clusters in a single stabilization release with no scope beyond the validated defects.

Issues #574 and #716 are confirmed resolved on current `main` and are excluded from this mission.

---

## Goals

1. Fix all four live bug clusters in a single stabilization release.
2. Ship regression tests alongside each fix to prevent recurrence.
3. Preserve backward compatibility with existing event logs, shim deployments, and intake workflows.
4. Produce a clean, green test suite after each work package merges.

## Non-Goals

- Issues #574 and #716 (already resolved on `main`).
- New features, UX redesigns, or user-facing behavior changes unrelated to the named defects.
- Architectural refactoring or introduction of new subsystems.
- Expanding the intake path hardening beyond the four specific issues (#723, #722, #720, #721) into a broader security program.
- Changes to documentation, deployment tooling, or release pipeline.

---

## Actors

| Actor | Role |
|-------|------|
| spec-kitty CLI user | Runs `spec-kitty merge` and observes incorrect post-merge abort |
| Agent runtime (Gemini) | Reads generated shim files; currently receives malformed Markdown instead of TOML |
| Agent runtime (Qwen) | Reads generated shim files; currently receives wrong argument placeholder |
| Agent runtime (reviewer) | Claims a WP for review; currently emits an illegal lane state |
| Operator / CI pipeline | Runs `spec-kitty intake`; currently has no protection against oversized input or path escape |
| Historical log reader | Reads event logs from before this fix; must continue to parse without error |

---

## User Scenarios and Testing

### S-01: Merge with untracked tooling files present

A user runs `spec-kitty merge` in a repository that has untracked directories such as `.claude/`, `.agents/`, `.kittify/`, or `.worktrees/`. The post-merge invariant runs, observes untracked files, and **completes successfully** — no abort, no false error about HEAD divergence.

**Failure precondition (before fix):** merge aborts with an incorrect sparse-checkout error message.  
**Pass condition (after fix):** merge completes; untracked entries are ignored by the invariant.

### S-02: Merge with genuinely dirty tracked files

A user runs `spec-kitty merge` in a repository where tracked files have uncommitted changes after the merge operation. The post-merge invariant detects the actual divergence and **aborts** with a precise error message that does not reference sparse-checkout. The message tells the user what is actually wrong.

**Pass condition:** abort fires; error message is accurate and actionable.

### S-03: Gemini shim generation produces valid TOML

An operator runs shim generation for a project configured to use Gemini. The `.gemini/commands/` directory is populated with `.toml` files that contain valid TOML syntax and use `{{args}}` as the argument placeholder.

**Failure precondition (before fix):** `.md` files with YAML frontmatter and `$ARGUMENTS` placeholder are generated.  
**Pass condition (after fix):** `.toml` files with correct TOML syntax and `{{args}}` are generated.

### S-04: Non-Gemini shim generation is unchanged

An operator regenerates shims for Claude, Codex, GitHub Copilot, and other supported agents after the Gemini fix is applied. All previously passing shim formats remain identical in structure, extension, and content.

**Pass condition:** no regression in non-Gemini/Qwen agent shim output.

### S-05: Review-claim emits correct lane transition

An agent runtime claims a WP that is in `for_review` state. The event log records a `for_review → in_review` transition. Subsequent approval and rejection operations originating from `in_review` complete successfully.

**Failure precondition (before fix):** event log records `for_review → in_progress` with `review_ref="action-review-claim"`.  
**Pass condition (after fix):** event log records `for_review → in_review`; approval and rejection from `in_review` work correctly.

### S-06: Historical event logs with legacy review-claim shape parse without error

An operator or agent reads an event log from a project that recorded review claims before this fix, where the log contains `in_progress` entries with `review_ref="action-review-claim"`. The read completes without errors and returns a coherent snapshot.

**Pass condition:** historical logs parse cleanly; no crash or silent data loss.

### S-07: Intake rejects an oversized brief before reading it

A user attempts to ingest a markdown file that exceeds the defined maximum size limit. Intake immediately rejects the operation with a clear error message identifying the size limit, without reading the full file into memory.

**Pass condition:** error is raised before full read; error message states the size limit.

### S-08: Intake rejects a file path that escapes the repo root

A project's plan source configuration or HARNESS_PLAN_SOURCES variable references a path that resolves outside the repository root (e.g., `../escape/plan.md`). Auto-scan does not return that file. No error is surfaced to the user from this silent exclusion.

**Pass condition:** out-of-bounds path is excluded; in-bounds paths are unaffected.

### S-09: Intake directory expansion does not follow symlinks out of the repo

A symlink inside a configured plan directory points to a file or directory outside the repository root. Auto-scan expansion does not include the linked target.

**Pass condition:** symlink target is excluded; regular in-repo files in the same directory are included.

### S-10: Brief write is atomic and recoverable from a crash

A process crash occurs between writing the brief file and writing its provenance sidecar. On the next invocation, the intake command does not report a blocking inconsistency — either both files are present or neither is, and re-ingest proceeds normally.

**Pass condition:** no half-written state blocks subsequent intake; both files exist together or neither does.

### S-11: Valid in-repo markdown intake is unaffected

A user runs `spec-kitty intake` on a valid, reasonably sized markdown file within the repository. The operation succeeds without change to existing behavior.

**Pass condition:** normal intake works as before.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The post-merge invariant must classify untracked files (porcelain status `??`) as non-divergent and must not abort the merge operation because of them. | Approved |
| FR-002 | The post-merge invariant must abort when tracked files carry uncommitted modifications after merge. | Approved |
| FR-003 | The post-merge abort message must accurately reflect the actual failure type and must not recommend `spec-kitty doctor sparse-checkout --fix` for failures unrelated to sparse checkout. | Approved |
| FR-004 | Untracked entries under tooling directories (`.claude/`, `.agents/`, `.kittify/`, `.worktrees/`, and equivalents) must not trigger the post-merge invariant. | Approved |
| FR-005 | Generated Gemini command shim files must be valid TOML and must use the `.toml` file extension. | Approved |
| FR-006 | Generated Qwen command shim files must use the correct format and file extension for the Qwen agent runtime. | Approved |
| FR-007 | Gemini and Qwen shim files must use `{{args}}` as the argument placeholder, not `$ARGUMENTS`. | Approved |
| FR-008 | Shim generation for all agents other than Gemini and Qwen must produce output identical to pre-fix behavior. | Approved |
| FR-009 | A review-claim transition must emit a `for_review → in_review` event in the event log. | Approved |
| FR-010 | Approval transitions initiated from the `in_review` lane must complete successfully after a review claim. | Approved |
| FR-011 | Rejection transitions initiated from the `in_review` lane must complete successfully after a review claim. | Approved |
| FR-012 | Event logs that recorded review claims as `in_progress` with `review_ref="action-review-claim"` (written before this fix) must be readable without errors and must produce a coherent state snapshot. | Approved |
| FR-013 | The mission brief file and its provenance sidecar must be written atomically such that a process crash mid-write does not leave a partially written state that blocks subsequent intake. | Approved |
| FR-014 | Intake must reject input files that exceed a defined maximum file size before reading the full file into memory, and must surface a clear error message stating the limit. | Approved |
| FR-015 | The plan auto-scan must exclude any candidate file whose resolved path falls outside the repository root. | Approved |
| FR-016 | Plan auto-scan directory expansion must not traverse symlinks that resolve to a path outside the allowed directory tree. | Approved |
| FR-017 | Valid in-repo markdown files within the size limit must be accepted by intake without any change to existing behavior. | Approved |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage for all new and modified code paths | ≥ 90% line coverage | Approved |
| NFR-002 | Type checking must pass in strict mode with zero new errors after changes are applied | 0 new mypy --strict errors | Approved |
| NFR-003 | The full existing test suite must pass after each work package is applied | 0 regressions | Approved |
| NFR-004 | Each bug fix must include at least one regression test that explicitly demonstrates the previously failing case now passing | 1 regression test per defect (minimum) | Approved |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Issues #574 and #716 are explicitly out of scope and must not be reopened or re-addressed by this mission. | Active |
| C-002 | All fixes must be applied in the existing modules; no new packages or subsystems may be introduced. | Active |
| C-003 | The maximum file size threshold for intake (FR-014) must be expressed as a named constant rather than an anonymous literal, enabling future configuration without source changes. | Active |
| C-004 | Backward compatibility with historical event logs containing the legacy review-claim shape (`in_progress` + `review_ref="action-review-claim"`) must be preserved in all read paths. | Active |
| C-005 | The intake hardening fixes (WP04) must not alter the behavior of intake for valid, in-bounds, reasonably sized files. | Active |

---

## Assumptions

1. The `??` status code is the only porcelain status prefix that represents untracked files. Other two-character codes with any letter in the index or worktree position represent tracked-file states and are correctly subject to the invariant.
2. The Qwen agent runtime uses the same `{{args}}` placeholder convention as Gemini. If Qwen uses a different convention, that difference will be surfaced during implementation and this spec will be updated.
3. A maximum brief file size of 5 MB is a reasonable default upper bound; this value will be expressed as a named constant and can be changed without a spec revision.
4. The `action-review-claim` review_ref value is the complete set of legacy marker shapes that need backward-compatible read support. No other legacy review-claim shapes exist.
5. The plan auto-scan containment check applies to HARNESS_PLAN_SOURCES, `.kittify/` sources, and any configured project plan directories. It does not need to apply to explicit file paths provided directly by the user on the command line.

---

## Key Technical Scope

The following existing modules are the change targets. No new modules will be introduced.

| Module | Bug Fix |
|--------|---------|
| `src/specify_cli/cli/commands/merge.py` | WP01: post-merge invariant porcelain parsing |
| `src/specify_cli/shims/generator.py` | WP02: Gemini/Qwen shim format and placeholder |
| `src/specify_cli/cli/commands/agent/workflow.py` | WP03: review-claim lane transition |
| `src/specify_cli/mission_brief.py` | WP04: atomic write for brief + sidecar |
| `src/specify_cli/cli/commands/intake.py` | WP04: file size cap |
| `src/specify_cli/intake_sources.py` | WP04: path containment and symlink exclusion |

---

## Work Package Summary

### WP01 — Merge Post-Merge Invariant Fix (Issue #675)

**User impact**: High. Users whose projects have untracked tooling directories (common in multi-agent setups) experience incorrect merge aborts that cannot be resolved without manual cleanup.

**Scope**: Fix the porcelain status parser in the post-merge invariant to treat `??` entries as non-divergent. Update the error message to reflect the actual failure cause. Add regression tests for both the untracked-file and tracked-dirty cases.

**Acceptance criteria**:
- FR-001, FR-002, FR-003, FR-004 pass.
- NFR-001, NFR-002, NFR-003, NFR-004 pass.
- Scenarios S-01 and S-02 pass.

### WP02 — Gemini/Qwen Shim Generation Fix (Issue #673)

**User impact**: High. Projects using Gemini receive malformed shim files, making the Gemini agent integration completely non-functional until regenerated after this fix.

**Scope**: Add agent-specific shim format routing for Gemini (TOML, `.toml` extension, `{{args}}`) and Qwen (correct format and placeholder). All other agents must produce identical output to pre-fix behavior. Add regression tests for file extension, content format, and placeholder syntax per agent type.

**Acceptance criteria**:
- FR-005, FR-006, FR-007, FR-008 pass.
- NFR-001, NFR-002, NFR-003, NFR-004 pass.
- Scenarios S-03 and S-04 pass.

### WP03 — Review Lane Semantics Fix (Issue #622)

**User impact**: Medium-High. Review-claim operations write an illegal state (`in_progress`) instead of `in_review`, potentially breaking downstream approval/rejection flows and violating the event log's transition invariants.

**Scope**: Update the review-claim code path to emit `for_review → in_review`. Remove any forced bypass of the transition guard that was required by the legacy incorrect shape. Add a compatibility read path for historical logs with the old shape. Add regression tests for new behavior and legacy compatibility.

**Acceptance criteria**:
- FR-009, FR-010, FR-011, FR-012 pass.
- NFR-001, NFR-002, NFR-003, NFR-004 pass.
- Scenarios S-05 and S-06 pass.

### WP04 — Intake Hardening Cluster (Issues #723, #722, #720, #721)

**User impact**: Medium. These are defensive hardening fixes — the risk is primarily to project integrity and predictability rather than immediate visible breakage for most users. However, the atomicity gap (#723) can leave projects in an unrecoverable state after a crash, which is high-severity when it occurs.

**Scope**: Four targeted fixes in three modules:
- Make brief + sidecar writes atomic using temp-file-then-rename semantics (#723).
- Add a named-constant file size cap to intake before the file read (#722).
- Enforce repo-root containment check on all resolved auto-scan paths (#720).
- Exclude symlinks during directory expansion in auto-scan (#721).

**Acceptance criteria**:
- FR-013, FR-014, FR-015, FR-016, FR-017 pass.
- C-003, C-005 pass.
- NFR-001, NFR-002, NFR-003, NFR-004 pass.
- Scenarios S-07, S-08, S-09, S-10, S-11 pass.

---

## Success Criteria

1. All four defect scenarios described in the user scenarios section pass end-to-end after the mission merges.
2. The full test suite is green with zero new failures.
3. All new code achieves 90% or greater test coverage.
4. No mypy --strict errors are introduced.
5. Agent setups using Gemini can successfully use generated shim files without manual correction.
6. Review-claim operations produce an event log that satisfies the canonical 9-lane state machine defined in the status model.
7. Projects with untracked tooling directories complete merge operations without false aborts.
8. Intake operations on valid, in-bounds files proceed without change.

---

## Risks and Compatibility Notes

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Legacy review-claim read path missed in some code branch | Medium | High | Audit all event-log read paths (reducer, doctor, dashboard) for `review_ref="action-review-claim"` shapes; add coverage for each. |
| Qwen placeholder convention differs from Gemini | Low | Medium | Verify Qwen runtime docs during implementation; update spec assumption if different. |
| Atomic write on Windows (no atomic rename) | Low | Low | Use Python's `pathlib.Path.replace()` which provides atomic semantics on POSIX and best-effort on Windows; document the behavior. |
| Post-merge invariant change inadvertently widens the non-abort condition | Low | High | Narrow the fix to `??` only; ensure any other unexpected porcelain code still triggers abort with a clear unknown-state message. |
| Shim format change breaks existing Gemini deployments that relied on old .md files | Low | Medium | Old `.md` files will remain unless explicitly regenerated; the fix is forward-only. Document that operators should run shim regeneration after upgrading. |
| Intake size cap set too low, breaking existing large brief workflows | Low | Medium | Set cap at 5 MB (assumption 3); express as named constant so operators can adjust without a code change. |

---

## Dependencies

- No external library additions required.
- Regression tests for WP01 depend on the existing `tests/merge/` test cluster.
- Regression tests for WP02 depend on the existing shim generation test infrastructure.
- Regression tests for WP03 depend on the existing `tests/specify_cli/status/` test cluster.
- Regression tests for WP04 depend on the existing `tests/specify_cli/` test infrastructure.
- Already-passing tests: `tests/merge/test_merge_done_recording.py` and `tests/upgrade/migrations/test_m_3_1_1_event_log_merge_driver.py` must remain green throughout.
