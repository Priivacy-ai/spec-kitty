# Coordination Topology Stabilization

**Mission**: coordination-topology-stabilization-01KTZVQ2
**Mission ID**: 01KTZVQ2KB742M37VB5V2380CN
**Type**: software-dev
**Status**: Specifying
**Issues**: #1164, #1878 (umbrella), #1883, #1884, #1885, #1886, #1887, #1888

---

## Summary

The spec-kitty 3.x coordination branch topology splits write paths (status transitions, planning commits) onto a per-mission coordination branch while read paths, gates, and tooling remain anchored to the primary checkout. The split has produced eight confirmed defects that collectively prevent operators from completing a mission lifecycle without manual workarounds. This mission fixes all eight and introduces structural guards so the same class cannot silently recur.

---

## Problem Statement

Operators running missions under the coordination topology experience:

1. An accept gate that cannot converge — it fails on artifacts its own prior run wrote, and retrying never helps.
2. A setup-plan gate that rejects specs that have been correctly committed to the coordination branch.
3. A `spec-kitty next` query that returns a silent success (exit 0, empty output) when the mission cannot be found, hiding errors that require investigation.
4. Planning artifacts for coordination worktrees committed to `origin/main`'s index, polluting the shared repository with 26 leaked paths.
5. Work-package ownership validation warnings that are generated but structurally unreachable by any downstream prompt or operator.
6. A terminus retrospective that never triggers when missions complete via the standard merge path, and that finds no learnings even on missions with 28 documented failures.
7. A stale-assertion analyzer that flags intentional error-message assertions as false positives, eroding trust in the release-readiness report.

Together, these defects make the coordination topology operationally unusable for production missions and systematically hide quality signals that exist to protect the codebase.

---

## Primary Actor & Trigger

**Primary actor**: A spec-kitty operator running missions under the coordination topology (spec-kitty 3.x, `--coordination` flag active or `lanes.json` present).

**Trigger**: The operator invokes standard lifecycle commands (`spec-kitty accept`, `spec-kitty next`, `spec-kitty merge`, `spec-kitty agent mission finalize-tasks`) in a mission where the coordination branch holds planning artifacts.

**Desired outcome**: Every lifecycle command completes reliably, all warnings and errors are visible, no leaked artifacts appear in the shared repository, and the retrospective fires automatically at mission close.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The accept gate must not count its own previously-written artifacts (acceptance matrix, status views, coordination residue) as operator-introduced working-tree dirt. A run that fails the gate must not leave artifacts that prevent the next run from succeeding, making retries convergent. | Proposed |
| FR-002 | Running `spec-kitty accept --no-commit` must leave the working tree byte-for-byte identical to its state before the command was invoked — no file writes of any kind. | Proposed |
| FR-003 | The setup-plan entry gate must recognize a spec that has been committed to the mission's coordination branch as a valid committed spec, not require it to be present at primary HEAD. | Proposed |
| FR-004 | When `spec-kitty next` cannot resolve the requested mission handle, it must exit with a non-zero status code and emit a structured, named error (in both human-readable and `--json` modes) that identifies the unresolvable handle and provides a remediation hint. | Proposed |
| FR-005 | No files under `.worktrees/` may appear in the git index of the shared repository. Any merge or squash operation that would introduce such paths must be rejected by a fail-closed guard before the index is modified. | Proposed |
| FR-006 | Ownership validation warnings produced during `spec-kitty agent mission finalize-tasks` must be emitted to the operator (stderr for JSON mode, visible in human-readable output). A literal path in `owned_files` that matches no existing files must be treated as a hard error unless the work package explicitly declares the path as a planned new file. | Proposed |
| FR-007 | The terminus retrospective must be triggered for every mission that completes via any supported completion path — including the standard `spec-kitty merge` path — not only missions that exit through the `spec-kitty next` terminal-decision branch. If the retrospective cannot run, a `RetrospectiveSkipped` or `CaptureFailed` event must be recorded in the mission's event log so that absence is observable. | Proposed |
| FR-008 | The retrospective generator must ingest mission-local artifact files (workflow-failures-log.md, analysis-report.md, mission-review-report.md, review-feedback files) as sources for findings, in addition to the lane-event log it currently mines. | Proposed |
| FR-009 | The stale-assertion analyzer must not emit findings for assertions that test the content of error messages, diagnostic output, or captured streams — i.e., assertions where the removed literal is contained inside a message-capture expression. Such assertions must be either suppressed or emitted as a distinct informational grade that is clearly distinguished from a stale-assertion finding. | Proposed |
| FR-010 | Running a mission from specify through merge under the coordination topology must require zero manual `git merge --ff-only` invocations from the operator. The toolchain must advance the primary branch reference automatically after each coordination-branch write. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All existing passing tests must continue to pass after each workstream is merged. | 0 regressions | Proposed |
| NFR-002 | New and modified code must pass ruff lint and mypy strict with zero issues. | 0 errors, 0 warnings | Proposed |
| NFR-003 | Test coverage for net-new logic must be at or above 90% line coverage. | ≥ 90% | Proposed |
| NFR-004 | Each confirmed bug (FR-001 through FR-010) must have at least one regression test that would have caught it. | 1 regression test per FR | Proposed |
| NFR-005 | Fixes must not degrade the lifecycle of missions running without the coordination topology (flat topology). | 0 flat-topology regressions | Proposed |
| NFR-006 | The `spec-kitty doctor` command must report clean after all fixes are applied, including the `.worktrees/` index check. | `doctor` exits 0 with no errors | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | No new gate or cleanliness check may be introduced that anchors exclusively to the primary checkout HEAD or working tree, without also consulting the coordination branch via the shared read primitive introduced in WS1. | Proposed |
| C-002 | All changes must reach `origin/main` through pull requests. Direct pushes to `origin/main` are prohibited. | Proposed |
| C-003 | The `spec-kitty merge` command must not be run with `--push`; the caller creates a PR branch after local merge. | Proposed |
| C-004 | Before starting workstreams WS1 and WS5, the team must confirm with PR #1895 authors that the work does not duplicate in-flight fixes for #1884 FR-001 and #1885 hardening. | Proposed |
| C-005 | The `.worktrees/` index cleanup (WS2 cleanup PR) must land after the writer fix and the architectural ratchet test, never before both are in place. | Proposed |
| C-006 | Literal path entries in `owned_files` that match zero files and are not annotated as planned-new-file must produce an error, not a warning, beginning with this mission's merge. This is a tightening of existing behavior and must not be gated on a feature flag. | Proposed |

---

## User Scenarios & Testing

### Scenario 1: Accept converges on second run (FR-001)
An operator runs `spec-kitty accept` on a mission where a previous run failed the accept gate and left behind an acceptance-matrix.json. The new run succeeds or fails based on the mission's actual lane state — not on the presence of the prior run's artifacts. Running the command twice in the same state produces the same result.

### Scenario 2: --no-commit is truly read-only (FR-002)
An operator runs `spec-kitty accept --no-commit` to preview readiness without affecting the branch. After the command completes, `git status --porcelain` reports the same output as before the command was invoked.

### Scenario 3: Setup-plan passes when spec is on coordination branch (FR-003)
An operator commits the spec to the coordination branch as part of the normal workflow. Running `spec-kitty agent mission setup-plan` reports `phase_complete=true` and the mission proceeds to the plan phase. The gate does not require the spec to be present at primary HEAD.

### Scenario 4: Mission-not-found is a visible, actionable error (FR-004)
An operator types a mission handle that does not exist. `spec-kitty next --mission nonexistent-handle` exits with a non-zero status code and prints a structured error naming the handle and suggesting `spec-kitty mission list` as a recovery step. When `--json` is passed, the error appears in the `error` field, not as an `unknown` state document.

### Scenario 5: .worktrees/ paths do not enter the index (FR-005)
An operator runs a coordination-topology mission through implement and merge. `git ls-files .worktrees/` reports nothing. The 26 paths currently tracked on `origin/main` are removed by the cleanup PR.

### Scenario 6: Ownership phantom warning is visible (FR-006)
An operator finalizes tasks where a work package lists a path that does not exist. The finalize-tasks command prints a visible warning to stderr and the human-readable report. In JSON mode, the warning appears in the stderr stream, not only in a `ownership_warnings` field of the response body.

### Scenario 7: Retrospective fires after merge (FR-007)
An operator completes a mission via `spec-kitty merge`. After the merge command exits, `kitty-specs/<slug>/retrospective.yaml` exists, OR `status.events.jsonl` contains a `RetrospectiveSkipped` event with a reason. There is no path through merge that leaves both absent.

### Scenario 8: Retrospective finds content on a mission with documented failures (FR-008)
A mission with a `workflow-failures-log.md` containing 10+ numbered entries is merged. The generated retrospective includes at least one finding that references the failures log — it does not return `ran_no_findings`.

### Scenario 9: Stale-assertion analyzer does not flag message-content assertions (FR-009)
A literal string is removed from production code but remains tested via `assert "removed-literal" in str(exc.value)`. The stale-assertion analyzer does not emit a stale-assertion finding for this literal. If it emits anything, it is at informational grade and is labeled as a message-content check, not a stale assertion.

### Scenario 10: Zero manual ff-merges through a full mission lifecycle (FR-010)
An operator runs a mission from specify through merge. At no point does the toolchain halt and require the operator to manually run `git merge --ff-only`. All primary branch reference advances happen automatically.

---

## Success Criteria

1. The accept gate produces consistent results across successive runs on the same mission state: two runs in the same lane configuration produce the same pass/fail outcome.
2. `spec-kitty accept --no-commit` produces zero working-tree changes as measured by `git status --porcelain` before and after the command.
3. Zero files under `.worktrees/` appear in `git ls-files` on `origin/main` after the cleanup PR lands.
4. `spec-kitty next` with an invalid mission handle exits non-zero in 100% of invocations and emits a named error code in both human and JSON output modes.
5. The terminus retrospective is present or a skip event is recorded for 100% of missions merged via `spec-kitty merge` after this mission lands.
6. A mission with a non-empty `workflow-failures-log.md` produces a non-empty retrospective (not `ran_no_findings`).
7. Stale-assertion false-positive rate on message-content assertions drops to zero for the mission-131 fixture set.
8. The `spec-kitty doctor` command exits cleanly (0 errors, 0 warnings) on a repository where this mission's changes are applied.
9. The full fast test suite passes with zero new failures after each workstream is merged.

---

## Assumptions

1. PR #1895 (`stijn-dejongh/spec-kitty` fork, mission `name-vs-authority-remediation-01KTYGTE`) has not yet been merged to `origin/main`; its fixes for #1884 FR-001 and #1885 are in-flight. Coordination will happen before WS1 and WS5 are dispatched.
2. The coordination branch topology (`lanes.json`, `kitty/mission-…-lane-*` branch naming) is the authoritative model for the write path; flat topology (no coordination branch) must continue to work unchanged.
3. The 26 leaked `.worktrees/` paths on `origin/main` originate from the squash commit of PR #1825 (`do-dispatch-open-op-lifecycle-01KTSJ2H-coord`) and have been confirmed via `git ls-tree origin/main .worktrees/`.
4. `workflow-failures-log.md` is the canonical mission artifact for session-level friction. Its numbered entries are the primary new ingestor target for the retrospective generator.
5. The `--no-commit` behavioral contract for `spec-kitty accept` is already documented in its help text (accept.py:224); this mission enforces the contract that the code has always claimed.

---

## Out of Scope

- New CLI commands not required to fix the eight defects above.
- Changes to the coordination branch topology architecture itself (branch naming, placement resolver logic beyond the read-primitive addition).
- Fixes for issues other than #1164, #1878, #1883–#1888.
- The `_globs_overlap` general false-negative defect (tracked as a follow-up in the working plan, Section 6).
- mid8 canonicalization enforcement at a shared selector boundary (tracked as a follow-up).

---

## Domain Language

| Canonical Term | Definition | Synonyms to Avoid |
|----------------|------------|-------------------|
| Coordination branch | The per-mission branch (`kitty/mission-<slug>-<mid8>`) that receives write-path commits | coord branch |
| Primary checkout | The main working tree checked out to `main` | primary, main checkout |
| Accept gate | The cleanliness and lane-state checks run by `spec-kitty accept` | acceptance gate, gate |
| Terminus retrospective | The retrospective capture triggered at mission completion | end-of-mission retro, final retro |
| Coordination topology | The operating mode where write paths target the coordination branch | coord topology, split topology |
| Flat topology | The operating mode without a coordination branch (single-branch writes to main) | non-coord, single-branch |
| Working plan | The file `WORKING-PLAN-coordination-stabilization-2026-06-12.md` | Debbie plan, issue plan |

---

## Dependencies

- Issue #1878 (umbrella): this mission closes the coordination read-surface and ff-merge treadmill portions.
- Issue #1771 (done): retrospective path canon — already landed, provides the correct record path.
- Issue #1814: accept-gate coordination-residue exclusion pattern — WS3 reuses this pattern.
- PR #1895 (in-flight): must be coordinated with WS1 and WS5 before dispatch.
- Issue #1149: acceptance-matrix verdict-recording CLI — companion to WS3, can ship separately.
