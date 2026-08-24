# Work Packages: Exclude Canceled Work Packages from Lanes

**Mission**: `exclude-canceled-work-packages-from-lanes-01M0S6W4`  
**Planning branch**: `fix/exclude-canceled-work-packages-from-lanes`  
**Merge target**: `fix/exclude-canceled-work-packages-from-lanes`  
**Source**: GitHub issue #3432

## Delivery Strategy

This Mission uses one atomic work package. The acceptance test, pure eligibility policy, and `mission_finalize.py` integration form one green review boundary: splitting the RED test from production would strand an unapprovable red-only package, while splitting the finalizer integration would require overlapping ownership of the same orchestration and acceptance-test files.

The implementer must still use checkpointed commits. The first commit is the planning-base RED acceptance contract; production edits begin only after that failure is recorded.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Commit exact-command RED cancellation acceptance coverage | WP01 | No |
| T002 | Perform the distinct tidy-first campsite checkpoint | WP01 | No |
| T003 | Implement and unit-test the immutable eligibility projection | WP01 | No |
| T004 | Reuse one canonical lifecycle snapshot and reject stale edges before writes | WP01 | No |
| T005 | Filter every ownership and execution-lane consumer through the eligible set | WP01 | No |
| T006 | Support normal and validate-only all-canceled zero-work success | WP01 | No |
| T007 | Complete compatibility, integrity, determinism, Windows, and performance regressions | WP01 | No |
| T008 | Enforce coverage and focused quality gates and prepare review evidence | WP01 | No |

## Work Package WP01: Cancellation-Aware Finalization

**Priority**: P1  
**Dependencies**: None  
**Prompt**: `tasks/WP01-cancellation-aware-finalization.md`  
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010; NFR-001, NFR-002, NFR-003, NFR-004, NFR-005; C-001, C-002, C-003, C-004, C-005, C-006  
**Plan concerns**: IC-01, IC-02, IC-03, IC-04  
**Estimated prompt size**: approximately 376 lines (target: 200–500)

### Summary

Introduce one canonical cancellation-eligibility boundary in `finalize-tasks`. Read event-derived lifecycle state once, reject all eligible-to-canceled direct dependencies before any finalization write, exclude canceled work packages from ownership and execution-lane consumers, and represent an all-canceled Mission as a valid zero-execution-lane result. Preserve `done`, first-finalize, reopening, no-cancellation, and #3431 post-collapse-cycle behavior.

**Independent test**: Seed canonical lifecycle events for mixed, stale-dependency, all-canceled, done, reopened, and corrupt-status Missions. Invoke the exact `finalize-tasks` CLI in normal and validate-only modes. Verify eligibility, complete diagnostics, zero mutation on refusal, zero-lane success, history preservation, and unchanged surviving allocation semantics.

### Included Subtasks

- [x] T001 Commit exact-command RED cancellation acceptance coverage (WP01)
- [x] T002 Perform the distinct tidy-first campsite checkpoint (WP01)
- [x] T003 Implement and unit-test the immutable eligibility projection (WP01)
- [x] T004 Reuse one canonical lifecycle snapshot and reject stale edges before writes (WP01)
- [x] T005 Filter every ownership and execution-lane consumer through the eligible set (WP01)
- [x] T006 Support normal and validate-only all-canceled zero-work success (WP01)
- [x] T007 Complete compatibility, integrity, determinism, Windows, and performance regressions (WP01)
- [x] T008 Enforce coverage and focused quality gates and prepare review evidence (WP01)

### Implementation Sketch

1. Add and separately commit non-vacuous CLI acceptance tests that fail on the planning base for cancellation behavior, without production changes.
2. Before production behavior changes, perform and separately record the tidy-first campsite assessment/cleanup on the touched finalizer methods.
3. Add a small immutable/pure `finalization_eligibility.py` seam and direct unit tests, including a literal Windows-critical test marker.
4. In `mission_finalize.py`, validate raw dependency ID/reference integrity, take one coordination-aware canonical lifecycle snapshot before every writer, reuse it for eligibility and later provenance consumers, reject all stale cut edges, then validate DAG cycles on `eligible_dependencies`. Canceled-only or isolated canceled cycles do not block; eligible cycles still do.
5. Apply the same eligible-ID set to frontmatter, ownership manifests, bodies, dependencies, validate-only preview, committed lane computation, and reports.
6. Retain existing empty-input refusal when eligible work remains, but call the allocator's existing empty-safe path when all known work is canceled.
7. Exercise cancellation-only and no-cancellation compatibility, corrupt status refusal, deterministic ordering, canceled-only and isolated-canceled cycle success, eligible-cycle and stale-cut refusal, #3431 surviving-graph cycles, Windows collection, and the governed 100-WP benchmark protocol.
8. Close with a 90% changed-line coverage floor, focused tests, lint, strict typing, architecture/terminology gates, clean diff, and review-ready evidence.

### Parallel Opportunities

No intra-package file-edit parallelism is authorized. The new pure helper and tests could be drafted independently in theory, but the RED-first commit order and shared CLI acceptance fixtures make sequential implementation safer and easier to review. Read-only review may occur at the checkpoints after T001, T003, and T005.

### Risks

- A status helper that degrades read errors could violate fail-closed integrity.
- Filtering only manifests, but not frontmatter, could let `_resolve_wp_manifests_for_validation` reintroduce canceled work.
- A late stale-edge check could leave target-branch metadata, matrices, events, frontmatter, or commits behind.
- Unconditionally accepting empty maps could regress the existing malformed eligible-work refusal.
- Adding lifecycle logic to `compute_lanes` would violate the selected authority boundary.
- Timing coverage can become flaky if it uses sleeps rather than deterministic fixtures.

### Completion Gate

The WP is complete only when the exact command succeeds for mixed and all-canceled Missions, refuses every stale direct edge before mutation, retains all canceled history, preserves no-cancellation lane results and #3431 cycle findings, meets the governed 100-WP benchmark, is collected by Windows CI, reaches at least 90% changed-line coverage, and passes the focused quality gates without retries or blanket suppressions.
