# Spec: Phase 4 Auth Identity-Boundary Canary Gate

**Mission**: phase4-canary-gate-01KS1W46
**Mission ID**: 01KS1W46ZAR9S9RJPQQJAMCV6P
**Status**: Draft
**Created**: 2026-05-20

---

## Overview

Two Phase-4 blockers stalled the Teamspace MVP auth-boundary launch gate after `spec-kitty-cli 3.2.0rc15` scored 1/4 on the identity-boundary canary:

- **#1141** (re-opened): Scenario 4 fails because a `for_review → in_review` rollback row silently overwrites the correct `in_review → planned` row in the offline queue when `OfflineQueue.queue_event` is called downstream of `fire_saas_fanout`. The rc15 landing was diagnostic-only; root cause was not fixed.
- **#1182** (new): Scenarios 1 and 2 reach `sync now` successfully (the #1142 fix held), but `sync now` misclassifies durably-queued events as `unknown` errors and exits non-zero when the in-process 5-second final-sync timeout fires.

This mission gates the release by verifying both blockers are closed with substantive fixes, installing the post-rc15 RC, proving all four identity-boundary scenarios pass 4/4 consecutive runs, and attaching the required evidence to close the Teamspace MVP release gate.

---

## User Scenarios & Testing

### Primary Scenario: Release Gating Agent Completes Phase 4

1. Release gating agent verifies both blocker issues (#1141, #1182) are closed on `Priivacy-ai/spec-kitty` and that #1141's fix is backed by a test that fails without the fix and passes with it.
2. Agent determines the latest prerelease RC tag; if it is still rc15, it either cuts rc16 from the fix SHA or stops and reports.
3. Agent installs the post-rc15 RC via `pipx` and confirms `specify_cli.sync.owner` and `specify_cli.sync.preflight` import cleanly.
4. Agent re-runs the read-only SaaS preflight and confirms `/health/` and `/health/ready/` return 200, events version is 5.1.0+, `terminal_failed` infra count is 0, and the historical 22 `business_rule` rows are untouched.
5. Agent runs the identity-boundary canary in `--single` mode. All four scenarios pass.
6. Agent runs the four-run protocol. All four consecutive runs pass with `"outcome": "pass"`.
7. Agent bundles evidence, posts a comment to `Priivacy-ai/spec-kitty-end-to-end-testing#41` with the required template fields, and closes #41.
8. Agent runs the Teamspace MVP canary suite four consecutive times and preserves logs.
9. Agent posts the evidence comment to `Priivacy-ai/spec-kitty#1038`. Does not close #1038.

### Exception: Blocker Still Open

- Either issue is still OPEN → agent stops and reports which one(s) remain. No further steps.

### Exception: #1141 Fix Is Diagnostic-Only

- Agent inspects the merge commit diff for `OfflineQueue.queue_event` (or adjacent call site). If the change is logging-only without a test that fails without the fix → agent stops and reports before installing the RC.

### Exception: Single-Run Canary Fails

- If scenario 4 still fails with `from='for_review' to='in_review'`: agent re-opens `#1141`, preserves evidence under `artifacts/sync_identity_boundary/<rc-tag>-attempt1/`, and stops.
- If scenarios 1 or 2 still fail with `unknown: N` + `sync.event_loop_unavailable`: agent re-opens `#1182` the same way.
- Evidence is never overwritten; each attempt gets a unique subdirectory.

### Exception: SaaS Preflight Fails

- `/health/ready/` is not 200, or infra `terminal_failed` count is nonzero → agent stops and reports. Does not proceed to canary.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | The gate checks that both `Priivacy-ai/spec-kitty#1141` and `Priivacy-ai/spec-kitty#1182` are in `closed` state before proceeding to any subsequent step. | Required |
| FR-002 | Before installing a new RC, the gate inspects the merge commit diff for `OfflineQueue.queue_event` (or the call site identified in the #1141 bisect path) and confirms at least one test was added or modified that would fail without the fix and pass with it. A pure-logging change without such a test must be rejected. | Required |
| FR-003 | The gate installs the latest post-rc15 prerelease RC from PyPI via `pipx`. If the latest published RC is still v3.2.0rc15, the gate either cuts a new RC from the fix SHA (following the Phase-2 release workflow in start-here.md) or stops and reports. | Required |
| FR-004 | After installation, the gate confirms `specify_cli.sync.owner` and `specify_cli.sync.preflight` import cleanly from the installed CLI environment. | Required |
| FR-005 | The gate re-runs the SaaS preflight: `/health/` returns 200 and reports `spec_kitty_events: 5.1.0` or newer; `/health/ready/` returns 200; infra `terminal_failed` count is 0. | Required |
| FR-006 | The gate confirms the historical 22 `business_rule_rejected` rows remain in `terminal_failed` state and have not been modified. | Required |
| FR-007 | The gate runs the identity-boundary canary in `--single` mode. All four scenarios (1–4) must pass. Failure in any scenario triggers the appropriate issue re-open and evidence preservation workflow. | Required |
| FR-008 | After the single run passes, the gate runs the full four-run canary protocol. All four JSON result documents must contain `"outcome": "pass"`. | Required |
| FR-009 | No manual SaaS queue mutation, Fly DB edits, daemon record surgery, local queue deletion, event replay, or ingress-cap override is performed at any point during the gate. | Required |
| FR-010 | The gate preserves canary evidence from each attempt in a unique subdirectory under `spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/<rc-tag>-attempt<N>/`. Prior attempt evidence (e.g., rc15-attempt1) is not overwritten. | Required |
| FR-011 | After the four-run protocol passes, the gate posts a comment to `Priivacy-ai/spec-kitty-end-to-end-testing#41` containing: CLI version/tag/SHA, SaaS Fly image/SHA, `/health/ready/` snapshot, drain counts, four-run result summary, evidence path, and an explicit statement that no manual mutation occurred. | Required |
| FR-012 | After posting the evidence comment, the gate closes `Priivacy-ai/spec-kitty-end-to-end-testing#41`. | Required |
| FR-013 | The gate runs the Teamspace MVP canary suite (`test_go_live_pre_connector_saas_e2e.py`, `test_teamspace_pulse_deployed_dev_e2e.py`, `test_teamspace_sync_deployed_dev_e2e.py` with `-m deployed_dev`) four consecutive times. Logs are preserved for each run. | Required |
| FR-014 | The gate posts the release-tracker evidence comment to `Priivacy-ai/spec-kitty#1038` using the template in start-here.md Phase 7, including: CLI version/tag/SHA, events version/tag/SHA, SaaS image/SHA, health snapshot, drain counts, identity-boundary canary result (4/4), Teamspace canary result (4/4), evidence paths, and the no-mutation statement. | Required |
| FR-015 | The gate does NOT close `Priivacy-ai/spec-kitty#1038`. | Required |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All four-run canary JSON documents must show `"outcome": "pass"` with zero manual interventions between runs. Interventions are defined as: pkill of sync daemon, curl mutations to SaaS endpoints, Fly DB console edits, or local `.kittify/` queue file deletions. | Zero interventions, 4/4 pass | Required |
| NFR-002 | The SaaS `/health/ready/` endpoint must return 200 with `terminal_failed_infra_count=0` at each preflight check. | 200, count=0 | Required |
| NFR-003 | Evidence files for each canary attempt must be immutable after the attempt completes — no post-hoc modification. | Zero post-hoc edits | Required |
| NFR-004 | The installed CLI must be traceable to a commit at or after `cc5e1ca983adff4a45489ce7afe11ad3a3a26e30` (the #1115 merge SHA). | SHA ≥ cc5e1ca9 on main | Required |
| NFR-005 | The Teamspace MVP canary suite must complete all four iterations without a retry that would require SaaS state cleanup. Each failed run must be root-caused before retrying. | Four clean consecutive runs | Required |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Do not cut the final `3.2.0` release. Only prerelease RCs (rc16, rc17, …) are permitted. | Required |
| C-002 | Do not rebase, reset, or modify the historical 22 `business_rule_rejected` rows in the deployed SaaS database. | Required |
| C-003 | Do not replay or delete events from the local offline queue to make the canary pass. | Required |
| C-004 | Do not raise the SaaS ingress size cap to suppress 413 errors. | Required |
| C-005 | Do not use a CLI build from a SHA before `cc5e1ca983adff4a45489ce7afe11ad3a3a26e30`. | Required |
| C-006 | PR #42 and PR #44 are already merged to `spec-kitty-end-to-end-testing` main. The "merge PR #42" sub-step in start-here.md Phase 5 is a no-op. | Required |
| C-007 | `Priivacy-ai/spec-kitty#1038` must not be closed by this gate. The release decision belongs to the operator. (Enforcement alias of FR-015; retained as a constraint to surface this rule at implementation boundaries.) | Required |
| C-008 | Work must stay inside the prepared workspace at `/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS`. Do not use older local checkouts. | Required |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| Identity-Boundary Canary | The four-scenario e2e test suite in `spec-kitty-end-to-end-testing` that proves the auth sync boundary holds against deployed-dev. Managed by `scripts/run-sync-identity-boundary-canary.sh`. |
| Blocker Issue #1141 | `OfflineQueue.queue_event` silent replacement bug; scenario 4 gate. Must be closed with test-backed fix before canary run. |
| Blocker Issue #1182 | `sync now` misclassifies durably-queued events as `unknown` errors on 5s final-sync timeout; scenarios 1+2 gate. |
| Release Candidate RC | A prerelease build of `spec-kitty-cli` from a SHA at/after #1115. The post-rc15 RC must contain fixes for both #1141 and #1182. |
| Canary Run Result | A JSON document at `artifacts/sync_identity_boundary/runs/run-N.json` with top-level key `"outcome"`. All four must contain `"outcome": "pass"`. |
| e2e#41 | `Priivacy-ai/spec-kitty-end-to-end-testing#41` — the MVP blocker canary issue. Closes only when 4/4 evidence is attached. |
| spec-kitty#1038 | The Teamspace MVP release tracker. Receives evidence comment but must not be closed by this gate. |
| Teamspace MVP Canary Suite | Three deployed-dev pytest files: `test_go_live_pre_connector_saas_e2e.py`, `test_teamspace_pulse_deployed_dev_e2e.py`, `test_teamspace_sync_deployed_dev_e2e.py`. |

---

## Assumptions

1. Both #1141 and #1182 will be closed by a separate fix-agent track before this gate runs. This mission does not implement those fixes — it verifies them.
2. The GitHub CLI (`gh`) is authenticated and has sufficient scopes to read issues, post comments, and close issues on `Priivacy-ai/spec-kitty-end-to-end-testing` and `Priivacy-ai/spec-kitty`. Per CLAUDE.md: unset `GITHUB_TOKEN` if scope errors arise and use keyring token.
3. The Fly.io `spec-kitty-dev` app and the deployed SaaS image will remain stable (no redeployment) during the gate run.
4. `pipx` and Python 3.11+ are available on the trusted runner at the expected paths.
5. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` must be set for any CLI command that touches hosted auth/SaaS. This is a machine-level rule from start-here.md.

---

## Success Criteria

1. Both blocker issues (#1141 and #1182) are confirmed closed with substantive test-backed fixes before any canary run.
2. A post-rc15 CLI RC is installed from a commit at/after the #1115 SHA, and boundary imports verify clean.
3. All four identity-boundary scenarios pass in a single run.
4. All four consecutive four-run protocol runs produce `"outcome": "pass"` with zero manual interventions.
5. Evidence is attached to `Priivacy-ai/spec-kitty-end-to-end-testing#41` and the issue is closed.
6. The Teamspace MVP canary suite passes four consecutive times with logs preserved.
7. Evidence comment is posted to `Priivacy-ai/spec-kitty#1038` and the issue remains open.
8. The historical 22 `business_rule_rejected` SaaS rows are untouched throughout.
