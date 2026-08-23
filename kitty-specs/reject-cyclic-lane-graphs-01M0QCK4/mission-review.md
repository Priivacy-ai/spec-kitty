# Mission Review Report: reject-cyclic-lane-graphs-01M0QCK4

**Reviewer**: Codex, with an independent Reviewer Renata trace
**Date**: 2026-08-23
**Mission**: `reject-cyclic-lane-graphs-01M0QCK4` — Reject Cyclic Lane Graphs
**Baseline commit**: `d060cff9a5c9f8cf369c8786e5bf9b4f89931d0a`
**Mission squash**: `886f33e828c910d86450ef069bcf4b6c4bc7c09f`
**Adversarial remediation**: `9231457027d4aec0ce43e39f1bb9aa9839a53228`
**HEAD at review**: `9231457027d4aec0ce43e39f1bb9aa9839a53228`
**WPs reviewed**: WP01–WP03

The post-merge `meta.json` records the mission squash as `baseline_merge_commit`.
For a meaningful implementation diff, this review uses the parent of the first
mission commit, `d060cff9a`, as the pre-mission baseline.

## Gate Results

### Gate 1 — Contract tests

- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/contract/ -q`
- Exit code: 0
- Result: PASS
- Notes: 297 passed, 5 skipped in 42.42 seconds.

### Gate 2 — Architectural tests

- Command: `uv run pytest tests/architectural/ -q`
- Exit code: 0
- Result: PASS
- Notes: 1,679 passed, 5 skipped, 2 expected xfails in 14m41s. The sole warning reports that the project-store census shrank; it is not a mission regression.

### Gate 3 — Cross-repo E2E

- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest scenarios/ -q` with an isolated `SPEC_KITTY_HOME`, local checkout first on `PATH`, and `SPEC_KITTY_SYNC_DISABLE=1`
- Exit code: 0
- Result: PASS WITH ENVIRONMENT NOTE
- Notes: 5 passed and 1 expected xfail in 4m13s. The complete local floor executes on companion E2E fix [#586](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/pull/586), filed from issue [#585](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/585). The live SaaS case remains an expected xfail because no dev endpoint is configured; it does not fail the pytest gate.

### Gate 4 — Issue Matrix

- File: `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/issue-matrix.json`
- Rows: 1
- Empty or unknown verdicts: 0
- Deferred rows missing follow-up: 0
- Result: PASS
- Notes: #3431 is `fixed`, with reachable merged/remediation evidence and complete FR/NFR/SC/repository scope.

## FR Coverage Matrix

| FR ID | Brief contract | WP | Production seam | Test adequacy | Finding |
|---|---|---|---|---|---|
| FR-001 | Validate the final post-collapse graph | WP01 | `compute.py::_find_lane_dependency_cycle` called unconditionally by `compute_lanes` | ADEQUATE | — |
| FR-002 | Fail every cyclic final graph | WP01 | `LaneDependencyCycleError` at the acceptance seam | ADEQUATE | — |
| FR-003 | Never persist a rejected graph | WP02 | computation precedes SHA capture and `write_lanes_json` | ADEQUATE | — |
| FR-004 | Preserve prior valid manifest bytes | WP02 | writer is unreachable on rejection | ADEQUATE | — |
| FR-005 | Report closed path and lane membership | WP01/WP02 | immutable typed error facts plus shared renderer | ADEQUATE | — |
| FR-006 | Stable JSON envelope and nonzero exit | WP02 | `_emit_finalize_error_with_revert_note` | ADEQUATE | — |
| FR-007 | Preserve valid DAG behavior | WP02/WP03 | unchanged manifest construction after the new gate | ADEQUATE | — |
| FR-008 | Validate-only parity and no mutation | WP02 | same `compute_lanes` authority, guarded `wps.yaml` regeneration | ADEQUATE | — |
| FR-009 | Canonical deterministic cycle | WP01/WP03 | sorted iterative DFS and direction-preserving rotation | ADEQUATE | — |
| FR-010 | Terminate safely | WP01/WP03 | iterative traversal; defensive depth guard retained | ADEQUATE | — |

NFR-001 is proven by absent-file, valid-prior-manifest byte identity, and
full-repository validate-only inventories. NFR-002 is proven by competing-cycle
permutations and canonical subprocesses under hash seeds 1, 7, and 97. NFR-003
is proven by the governed 100-lane/500-edge benchmark: 5 warm-ups, 20 measured
rounds, and observed mean 62.60 microseconds with p95 below 100 milliseconds.

## Drift Findings

No open spec-to-code drift remains.

The independent mission review initially found generated placeholder evidence
in `acceptance-matrix.json` and incomplete issue metadata in
`issue-matrix.json`. Both are repaired: the acceptance matrix now contains
requirement-specific FR/NFR/SC evidence plus a recorded no-write invariant, and
the issue row contains the exact GitHub title, complete scope mapping, and
reachable evidence.

## Resolved Adversarial Findings

1. **Validate-only `wps.yaml` mutation (HIGH)** — `mission_finalize.py` used to regenerate `tasks.md` before the validate-only branch. Commit `923145702` guards that write and adds a modern `wps.yaml` full-inventory regression.
2. **Three-lane CLI proof gap (HIGH)** — both human and JSON modes now assert an exact three-lane closed path and all lane memberships.
3. **Invalid prior-manifest fixture (MEDIUM)** — the byte-preservation test now serializes and preserves a genuine `LanesManifest`.
4. **Schema drift gap (MEDIUM)** — a real rendered payload is now validated with `Draft202012Validator` against the checked-in contract.
5. **Inventory scope gap (MEDIUM)** — validate-only mutation checks now inventory the whole temporary repository, not only the mission directory.
6. **Mutating-mode classification gap (LOW)** — `LANE_DEPENDENCY_CYCLE` is asserted unconditionally in both modes.
7. **Performance-test CI orphan (architectural gate)** — the benchmark now also carries `fast`, giving it a push-to-main collection home while the global performance chokepoint still skips normal execution.

## Risk Findings

No open boundary-condition, error-path, dead-code, or cross-WP integration risk
was confirmed. The authoritative graph check is singularly located inside
`compute_lanes`, after code and planning-lane edges are complete and before
depth computation, planning-SHA capture, or persistence.

## Silent Failure Candidates

None in mission-owned production changes. The new detector returns `None` only
for an acyclic graph; every detected cycle raises the typed governed failure.

## Security Notes

The mission adds no network, credential, subprocess, shell, path-resolution, or
authentication behavior. Diagnostics serialize internal lane IDs and WP IDs;
they do not incorporate dynamic shell execution or new filesystem targets.

## Final Verdict

**PASS WITH NOTES**

All FRs, NFRs, success criteria, constraints, and non-goals trace to live
production code and non-fakeable tests. Contract, architectural, focused,
typing, lint, schema, deterministic subprocess, and performance gates pass.
The only operational note is sequencing: companion E2E PR #586 must merge so
the default E2E branch retains the hard-gate repair used by this review.

### Open items (non-blocking)

- Merge Priivacy-ai/spec-kitty-end-to-end-testing#586 before or with this mission PR.
- Configure a dev SaaS endpoint to execute the live-sync scenario instead of its expected environmental xfail.

## Retrospective Reminder

The runtime-authored retrospective exists at
`kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/retrospective.yaml`. The
canonical follow-through is `spec-kitty retrospect summary`, then
`spec-kitty agent retrospect synthesize --mission reject-cyclic-lane-graphs-01M0QCK4`
to inspect proposals; `--apply` is intentionally a separate mutating action.
