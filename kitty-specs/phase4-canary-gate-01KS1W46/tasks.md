# Tasks: Phase 4 Auth Identity-Boundary Canary Gate

**Mission**: phase4-canary-gate-01KS1W46 | **Branch**: main → main
**Date**: 2026-05-20 | **Total WPs**: 8 | **Total Subtasks**: 43

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Query #1141 state via gh issue view | WP01 | — |
| T002 | Query #1182 state via gh issue view | WP01 | [P] |
| T003 | Gate: either OPEN → stop and report | WP01 | — |
| T004 | Inspect #1141 merge commit diff (queue.py, adapters.py) | WP01 | — |
| T005 | Verify #1141 fix has test coverage (fail-without, pass-with) | WP01 | — |
| T006 | Inspect #1182 merge commit diff (error-classification change) | WP01 | — |
| T007 | Determine latest prerelease RC tag from PyPI/GitHub | WP02 | — |
| T008 | Gate: if latest is still rc15 → stop and report | WP02 | — |
| T009 | Kill any orphan sync daemons (pkill) | WP02 | — |
| T010 | Install post-rc15 RC via pipx | WP02 | — |
| T011 | Verify installed CLI version output | WP02 | — |
| T012 | Verify sync.owner + sync.preflight boundary imports | WP02 | — |
| T013 | Check /health/ → 200 + events version | WP03 | [P] |
| T014 | Check /health/ready/ → 200 | WP03 | [P] |
| T015 | Check infra terminal_failed count via Fly SSH | WP03 | — |
| T016 | Confirm business_rule_rejected_count == 22 | WP03 | — |
| T017 | Export required env vars for canary | WP04 | — |
| T018 | uv sync in spec-kitty-end-to-end-testing | WP04 | — |
| T019 | Kill any orphan sync daemons before canary | WP04 | — |
| T020 | Run harness unit test preflight (3 preflight test files) | WP04 | — |
| T021 | Run --single canary | WP04 | — |
| T022 | Assert all 4 scenario statuses in latest.json | WP04 | — |
| T023 | On failure: re-open issue(s), preserve evidence, stop | WP04 | — |
| T024 | Run full four-run canary protocol | WP05 | — |
| T025 | Assert "outcome":"pass" in all 4 run-N.json files | WP05 | — |
| T026 | Confirm zero interventions between runs | WP05 | — |
| T027 | On failure: re-open issue(s), preserve evidence, stop | WP05 | — |
| T028 | Gather environment metadata (CLI, SaaS, events) | WP06 | [P] |
| T029 | Take post-run health snapshot | WP06 | [P] |
| T030 | Bundle evidence tarball | WP06 | — |
| T031 | Post evidence comment to e2e#41 (template) | WP06 | — |
| T032 | Close e2e#41 | WP06 | — |
| T033 | Verify #41 is closed | WP06 | — |
| T034 | Check #1038 for latest comment (Teamspace still required?) | WP07 | — |
| T035 | Teamspace MVP canary run 1 | WP07 | — |
| T036 | Teamspace MVP canary run 2 | WP07 | — |
| T037 | Teamspace MVP canary run 3 | WP07 | — |
| T038 | Teamspace MVP canary run 4 | WP07 | — |
| T039 | Preserve logs at /tmp/teamspace-canary-run-{1..4}.log | WP07 | — |
| T040 | Bundle Teamspace log tarball | WP08 | — |
| T041 | Gather final environment metadata | WP08 | — |
| T042 | Post evidence comment to spec-kitty#1038 (template) | WP08 | — |
| T043 | Verify #1038 remains OPEN | WP08 | — |

---

## WP01 — Blocker Verification

**Priority**: Critical (hard gate — all other WPs depend on this)
**Execution Mode**: planning_artifact
**Dependencies**: none
**Estimated prompt**: ~320 lines

**Goal**: Confirm both Phase-4 blocker issues are CLOSED and that #1141's fix is substantive (test-backed behavioral change, not diagnostic logging).

**Included subtasks**:
- [x] T001 Query #1141 state via gh issue view (WP01)
- [x] T002 Query #1182 state via gh issue view (WP01)
- [x] T003 Gate: either OPEN → stop and report (WP01)
- [ ] T004 Inspect #1141 merge commit diff (queue.py, adapters.py) (WP01)
- [ ] T005 Verify #1141 fix has test coverage (fail-without, pass-with) (WP01)
- [ ] T006 Inspect #1182 merge commit diff (error-classification change) (WP01)

**Parallel opportunities**: T001 and T002 can run concurrently.

**Risks**:
- #1141 was previously "fixed" with only diagnostic logging — the gate must reject that pattern.
- GitHub token scope issues: unset GITHUB_TOKEN and use keyring if needed (see CLAUDE.md).

**Prompt file**: [WP01-blocker-verification.md](tasks/WP01-blocker-verification.md)

---

## WP02 — RC Install and Boundary Verification

**Priority**: Critical (hard gate)
**Execution Mode**: planning_artifact
**Dependencies**: WP01
**Estimated prompt**: ~350 lines

**Goal**: Install the post-rc15 CLI RC, confirm it contains both #1141 and #1182 fixes, and verify that auth boundary imports are clean.

**Included subtasks**:
- [x] T007 Determine latest prerelease RC tag from PyPI/GitHub (WP02)
- [x] T008 Gate: if latest is still rc15 → stop and report (WP02)
- [ ] T009 Kill any orphan sync daemons (pkill) (WP02)
- [ ] T010 Install post-rc15 RC via pipx (WP02)
- [ ] T011 Verify installed CLI version output (WP02)
- [ ] T012 Verify sync.owner + sync.preflight boundary imports (WP02)

**Parallel opportunities**: WP03 (SaaS Preflight) is independent and can run concurrently with WP02.

**Risks**:
- No post-rc15 RC may exist yet — WP02 stops and reports rather than cutting autonomously.
- pipx symlink path mismatch (same as rc13 regression) — verify both `spec-kitty --version` and the Python import.

**Prompt file**: [WP02-rc-install.md](tasks/WP02-rc-install.md)

---

## WP03 — SaaS Preflight

**Priority**: High (read-only; gates WP04)
**Execution Mode**: planning_artifact
**Dependencies**: none (independent)
**Estimated prompt**: ~260 lines

**Goal**: Confirm the deployed SaaS environment is healthy before running any canary. Read-only checks only.

**Included subtasks**:
- [ ] T013 Check /health/ → 200 + events version (WP03)
- [ ] T014 Check /health/ready/ → 200 (WP03)
- [ ] T015 Check infra terminal_failed count via Fly SSH (WP03)
- [ ] T016 Confirm business_rule_rejected_count == 22 (WP03)

**Parallel opportunities**: T013 and T014 can run concurrently.

**Risks**:
- SaaS may be redeploying — wait and retry once if 503.
- Fly SSH console may require flyctl authentication.

**Prompt file**: [WP03-saas-preflight.md](tasks/WP03-saas-preflight.md)

---

## WP04 — Single-Run Identity-Boundary Canary

**Priority**: Critical (hard gate)
**Execution Mode**: planning_artifact
**Dependencies**: WP02, WP03
**Estimated prompt**: ~420 lines

**Goal**: Run the identity-boundary canary in `--single` mode. All four scenarios must pass. On any failure, re-open the appropriate issue and preserve evidence.

**Included subtasks**:
- [ ] T017 Export required env vars for canary (WP04)
- [ ] T018 uv sync in spec-kitty-end-to-end-testing (WP04)
- [ ] T019 Kill any orphan sync daemons before canary (WP04)
- [ ] T020 Run harness unit test preflight (3 preflight test files) (WP04)
- [ ] T021 Run --single canary (WP04)
- [ ] T022 Assert all 4 scenario statuses in latest.json (WP04)
- [ ] T023 On failure: re-open issue(s), preserve evidence, stop (WP04)

**Risks**:
- Scenario 4 regression: if `from='for_review' to='in_review'` reappears, re-open #1141.
- Scenarios 1+2 regression: if `unknown: N` + `sync.event_loop_unavailable` reappears, re-open #1182.
- Do NOT burn a canary cycle if fix substance was questionable (WP01 gate catches this first).

**Prompt file**: [WP04-single-run-canary.md](tasks/WP04-single-run-canary.md)

---

## WP05 — Four-Run Canary Protocol

**Priority**: Critical
**Execution Mode**: planning_artifact
**Dependencies**: WP04
**Estimated prompt**: ~280 lines

**Goal**: Run the full four-run canary protocol. All four JSON result documents must contain `"outcome": "pass"`. No interventions between runs.

**Included subtasks**:
- [ ] T024 Run full four-run canary protocol (WP05)
- [ ] T025 Assert "outcome":"pass" in all 4 run-N.json files (WP05)
- [ ] T026 Confirm zero interventions between runs (WP05)
- [ ] T027 On failure: re-open issue(s), preserve evidence, stop (WP05)

**Risks**:
- Flaky SaaS state: if a run fails, preserve evidence and stop — do not retry by cleaning up.
- The four-run protocol is sequential; runs cannot be parallelized.

**Prompt file**: [WP05-four-run-protocol.md](tasks/WP05-four-run-protocol.md)

---

## WP06 — Evidence Collection and Close e2e#41

**Priority**: High
**Execution Mode**: planning_artifact
**Dependencies**: WP05
**Estimated prompt**: ~340 lines

**Goal**: Bundle evidence, post the required comment to `e2e#41`, and close the issue.

**Included subtasks**:
- [ ] T028 Gather environment metadata (CLI, SaaS, events) (WP06)
- [ ] T029 Take post-run health snapshot (WP06)
- [ ] T030 Bundle evidence tarball (WP06)
- [ ] T031 Post evidence comment to e2e#41 (template) (WP06)
- [ ] T032 Close e2e#41 (WP06)
- [ ] T033 Verify #41 is closed (WP06)

**Parallel opportunities**: T028 and T029 can run concurrently.

**Risks**:
- PR #42 is already merged — do not attempt to merge it again (no-op sub-step).
- GitHub token scope: unset GITHUB_TOKEN if posting/closing fails (see CLAUDE.md).

**Prompt file**: [WP06-evidence-and-close-41.md](tasks/WP06-evidence-and-close-41.md)

---

## WP07 — Teamspace MVP Canary Suite

**Priority**: High
**Execution Mode**: planning_artifact
**Dependencies**: WP06
**Estimated prompt**: ~360 lines

**Goal**: Run the Teamspace MVP canary suite four consecutive times without SaaS mutation. Preserve logs.

**Included subtasks**:
- [ ] T034 Check #1038 for latest comment (Teamspace still required?) (WP07)
- [ ] T035 Teamspace MVP canary run 1 (WP07)
- [ ] T036 Teamspace MVP canary run 2 (WP07)
- [ ] T037 Teamspace MVP canary run 3 (WP07)
- [ ] T038 Teamspace MVP canary run 4 (WP07)
- [ ] T039 Preserve logs at /tmp/teamspace-canary-run-{1..4}.log (WP07)

**Risks**:
- 413 on sync: investigate payload size — do NOT raise ingress cap.
- Materialization timeout: verify e2e#40 polling helper is in use.
- `/health/ready/` 503: investigate infra terminal_failed — do NOT fix by deleting rows.
- If #1038's latest comment says Teamspace canary is no longer required: skip to WP08.

**Prompt file**: [WP07-teamspace-canary-suite.md](tasks/WP07-teamspace-canary-suite.md)

---

## WP08 — Release Tracker Evidence Comment

**Priority**: High
**Execution Mode**: planning_artifact
**Dependencies**: WP07
**Estimated prompt**: ~270 lines

**Goal**: Post the release tracker evidence comment to `spec-kitty#1038`. Do NOT close the issue.

**Included subtasks**:
- [ ] T040 Bundle Teamspace log tarball (WP08)
- [ ] T041 Gather final environment metadata (WP08)
- [ ] T042 Post evidence comment to spec-kitty#1038 (template) (WP08)
- [ ] T043 Verify #1038 remains OPEN (WP08)

**Risks**:
- Accidentally closing #1038 — the gate explicitly prohibits this.
- Token scope: unset GITHUB_TOKEN if posting fails.

**Prompt file**: [WP08-release-tracker-evidence.md](tasks/WP08-release-tracker-evidence.md)

---

## Execution Order Summary

```
WP01 (gate) ──► WP02 (gate) ──► WP04 (gate) ──► WP05 ──► WP06 ──► WP07 ──► WP08
                     ↑
              WP03 (runs independently, must complete before WP04)
```

**WP03 can run in parallel with WP02.**
All other WPs are sequential due to hard gate dependencies.

## MVP Scope

WP01 through WP05 are the MVP: blocker verification → RC install → preflight → single run → four-run. WP06–WP08 are required for the gate to close but don't produce new canary evidence.
