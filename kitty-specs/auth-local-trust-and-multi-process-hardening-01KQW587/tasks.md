# Tasks: Auth Local Trust And Multi-Process Hardening

**Input**: `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/plan.md`
**Branch contract**: Planning/base branch `main`; final merge target `main`; `branch_matches_target=true`
**Generated**: 2026-05-05T13:41:33Z

## Subtask Index

| ID | Description | Work Package | Parallel |
|---|---|---|---|
| T001 | Inventory hosted-sync and tracker-bound diagnostic entry points | WP01 | [P] | [D] |
| T002 | Define classification mapping for unauthenticated, Private Teamspace, transport, and server failures | WP01 | [D] |
| T003 | Fix direct-ingress missing Private Teamspace classification for #889 | WP01 |  | [D] |
| T004 | Add logged-out Teamspace/tracker guidance for #829 | WP01 |  | [D] |
| T005 | Add diagnostic regression tests and verify focused sync/tracker slices | WP01 |  | [D] |
| T006 | Reproduce the hosted-URL-set refresh-lock isolation boundary without live network dependency | WP02 | [D] |
| T007 | Make machine refresh-lock fixtures hermetic for post-refresh membership rehydrate | WP02 |  | [D] |
| T008 | Add a no-hosted-/me regression guard for #977 | WP02 |  | [D] |
| T009 | Preserve targeted production membership rehydrate coverage | WP02 |  | [D] |
| T010 | Run hosted-URL-set and hosted-URL-unset concurrency verification | WP02 |  | [D] |
| T011 | Extract or isolate the auth/storage BLE001 audit helper | WP03 | [D] |
| T012 | Define the scoped auth/storage suppression rule and reason-quality checks | WP03 |  | [D] |
| T013 | Add guardrail tests for justified, missing, and generic BLE001 reasons | WP03 |  | [D] |
| T014 | Wire actionable file/line failure output into the review/check surface | WP03 |  | [D] |
| T015 | Measure baseline repeated durable-session operations for many short-lived processes | WP04 | [D] |
| T016 | Design and implement a bounded local session handoff/cache helper | WP04 |  | [D] |
| T017 | Integrate hot-path fallback with encrypted file-only durable storage | WP04 |  | [D] |
| T018 | Preserve cross-process refresh coordination and benign replay handling | WP04 |  | [D] |
| T019 | Add hot-path, stale-handoff, secure-storage, and packaging regression coverage | WP04 |  | [D] |
| T020 | Run the focused auth/sync/tracker/review/packaging evidence suite | WP05 |  | [D] |
| T021 | Record hosted smoke commands with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` where applicable | WP05 |  | [D] |
| T022 | Compile acceptance evidence for #829, #907, #889, #977, and CLI-side #77 | WP05 |  | [D] |
| T023 | Record pre-existing failure issue links if any verification command fails from baseline | WP05 |  | [D] |

## Work Packages

### WP01 Diagnostic Classification And Logged-Out Guidance

**Prompt**: `tasks/WP01-diagnostic-classification-and-logged-out-guidance.md`
**Priority**: P1
**Dependencies**: none
**Estimated prompt size**: ~330 lines
**Goal**: Make hosted-sync and tracker-bound command paths distinguish logged-out, missing Private Teamspace, retryable transport, and true server failures.
**Independent test**: Simulate logged-out Teamspace/tracker-bound workflows and missing Private Teamspace direct ingress; assert no generic `server_error` in those cases.

- [x] T001 Inventory hosted-sync and tracker-bound diagnostic entry points (WP01)
- [x] T002 Define classification mapping for unauthenticated, Private Teamspace, transport, and server failures (WP01)
- [x] T003 Fix direct-ingress missing Private Teamspace classification for #889 (WP01)
- [x] T004 Add logged-out Teamspace/tracker guidance for #829 (WP01)
- [x] T005 Add diagnostic regression tests and verify focused sync/tracker slices (WP01)

**Implementation notes**:
- Start from `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/diagnostic-classification.md`.
- Keep classification changes in CLI-owned surfaces unless investigation proves tracker package ownership.
- Preserve existing direct-ingress category language where possible.

**Parallel opportunities**: Can run in parallel with WP02 and WP03.

**Risks**:
- Avoid changing SaaS route contracts.
- Avoid leaking auth internals or token material in diagnostics.

### WP02 Refresh-Lock Hermeticity

**Prompt**: `tasks/WP02-refresh-lock-hermeticity.md`
**Priority**: P1
**Dependencies**: none
**Estimated prompt size**: ~300 lines
**Goal**: Fix #977 by making refresh-lock concurrency tests hermetic when hosted SaaS URL environment variables are present.
**Independent test**: Run the focused refresh-lock test with `SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev` and verify zero hosted `/api/v1/me` calls.

- [x] T006 Reproduce the hosted-URL-set refresh-lock isolation boundary without live network dependency (WP02)
- [x] T007 Make machine refresh-lock fixtures hermetic for post-refresh membership rehydrate (WP02)
- [x] T008 Add a no-hosted-/me regression guard for #977 (WP02)
- [x] T009 Preserve targeted production membership rehydrate coverage (WP02)
- [x] T010 Run hosted-URL-set and hosted-URL-unset concurrency verification (WP02)

**Implementation notes**:
- Use `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/refresh-lock-hermeticity.md`.
- Treat the issue as test isolation first; do not weaken production post-refresh membership behavior.

**Parallel opportunities**: Can run in parallel with WP01 and WP03. WP04 should wait for this boundary.

**Risks**:
- A broad env clear can hide the actual fixture bug; prefer a no-network assertion.

### WP03 Auth/Storage BLE001 Guardrail

**Prompt**: `tasks/WP03-auth-storage-ble001-guardrail.md`
**Priority**: P2
**Dependencies**: none
**Estimated prompt size**: ~300 lines
**Goal**: Make unjustified broad exception suppressions in auth/storage paths fail with actionable file/line feedback.
**Independent test**: Guard fixtures cover justified, missing, and generic BLE001 reasons.

- [x] T011 Extract or isolate the auth/storage BLE001 audit helper (WP03)
- [x] T012 Define the scoped auth/storage suppression rule and reason-quality checks (WP03)
- [x] T013 Add guardrail tests for justified, missing, and generic BLE001 reasons (WP03)
- [x] T014 Wire actionable file/line failure output into the review/check surface (WP03)

**Implementation notes**:
- Use `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/ble001-guardrail.md`.
- Reuse existing review command direction rather than adding a parallel lint framework.

**Parallel opportunities**: Can run in parallel with WP01 and WP02.

**Risks**:
- Do not make the guard so broad that unrelated non-auth suppressions become blockers for this mission.
- WP03 owns scoped auth command and auth transport/revoke cleanup; WP04 owns cleanup for auth hot-path files it edits after the guard exists.

### WP04 Local Session Hot Path And Cross-Process Coordination

**Prompt**: `tasks/WP04-local-session-hot-path-and-cross-process-coordination.md`
**Priority**: P2
**Dependencies**: WP02, WP03
**Estimated prompt size**: ~420 lines
**Goal**: Add bounded local session hot-path behavior for many short-lived processes while preserving encrypted file-only storage as the root of trust.
**Independent test**: Many-process local session coverage demonstrates reduced repeated work, safe stale-handoff fallback, and no forbidden credential-manager dependencies.

- [x] T015 Measure baseline repeated durable-session operations for many short-lived processes (WP04)
- [x] T016 Design and implement a bounded local session handoff/cache helper (WP04)
- [x] T017 Integrate hot-path fallback with encrypted file-only durable storage (WP04)
- [x] T018 Preserve cross-process refresh coordination and benign replay handling (WP04)
- [x] T019 Add hot-path, stale-handoff, secure-storage, and packaging regression coverage (WP04)

**Implementation notes**:
- Use `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/session-hot-path.md`.
- Treat any cache/handoff as derived and invalidatable. Durable encrypted file storage remains authoritative.

**Parallel opportunities**: Starts after WP02 and WP03. It can proceed independently of WP01 once auth-concurrency test isolation and the BLE001 guardrail are clear.

**Risks**:
- Do not store raw token material in user-visible or plaintext diagnostic surfaces.
- Do not introduce Keychain/keyring/Secret Service dependencies.

### WP05 Integrated Evidence And Smoke

**Prompt**: `tasks/WP05-integrated-evidence-and-smoke.md`
**Priority**: P1
**Dependencies**: WP01, WP02, WP03, WP04
**Estimated prompt size**: ~280 lines
**Goal**: Run and record the final evidence suite for all acceptance checks and hosted smoke policy.
**Independent test**: Evidence artifact includes focused command output summaries and issue links for any pre-existing baseline failures.

- [x] T020 Run the focused auth/sync/tracker/review/packaging evidence suite (WP05)
- [x] T021 Record hosted smoke commands with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` where applicable (WP05)
- [x] T022 Compile acceptance evidence for #829, #907, #889, #977, and CLI-side #77 (WP05)
- [x] T023 Record pre-existing failure issue links if any verification command fails from baseline (WP05)

**Implementation notes**:
- Use `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/quickstart.md`.
- This WP should mostly create mission evidence artifacts and should not change production code unless a narrow integration gap is discovered and explicitly justified.

**Parallel opportunities**: None; this is the final integration package.

**Risks**:
- Hosted smoke commands on this computer must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- If verification finds pre-existing failures, open/report an issue before treating them as accepted baseline.

## Dependency Graph

```
WP01
WP02 ┐
     ├──> WP04 ┐
WP03 ┘         ├──> WP05
WP01 ──────────┘
```

## MVP Recommendation

The MVP is WP01 + WP02. Together they close the highest-risk user-facing diagnostics and the known #977 test-isolation failure. WP03 and WP04 harden maintainability and local-process performance, and WP05 records integrated acceptance evidence.
