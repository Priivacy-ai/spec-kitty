# Mission Specification: Fix sync strict-JSON ingress-skip auth

**Mission**: sync-strict-json-auth-01KWA6KN
**Mission type**: software-dev
**Status**: Draft
**Tracker**: [Priivacy-ai/spec-kitty#2254](https://github.com/Priivacy-ai/spec-kitty/issues/2254) · Related: #2034 (gate-selection blind spots)

## Purpose

A committed test on the primary branch is silently red. `tests/sync/test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress` is meant to prove that `spec-kitty agent mission create --json` keeps its stdout strict-JSON while the sync subsystem skips direct ingress and emits a structured diagnostic on stderr. Instead the command falls through to a `sync.server_auth_failure` at the `final_sync` phase ("Not authenticated: no valid access token"), so the intended ingress-skip diagnostic never fires and the assertion fails.

The failure is invisible in normal CI because the `integration-tests-sync` gate runs only when a change touches `sync/` paths (`needs.changes.outputs.sync == true`). Most pushes to the primary branch and most PRs leave the gate `SKIPPED`, so a genuinely broken committed test sits undetected — and any PR that legitimately edits a `sync/` path inherits a red gate through no fault of its own diff.

This mission restores a trustworthy signal: it finds why a pre-seeded, shared-only, encrypted `StoredSession` is no longer recognized as authenticated by the sync flow at `final_sync`, decides whether the **test's session-seeding** or the **sync auth/session resolution** is the side that drifted, and aligns them so the test exercises (and passes on) its intended contract.

## Scope

**In scope (core):** Root-cause the auth/session mismatch and make `test_mission_create_json_strict_when_sync_skips_ingress` pass by exercising the genuine direct-ingress-skip path — not by weakening the assertion into a no-op.

**Research-gated (decide during the research phase, then confirm before planning):** Whether to also broaden how path-filtered integration gates are triggered (a periodic/full run, or a wider trigger) so committed-and-failing tests can no longer hide behind a `SKIPPED` gate. This overlaps issue #2034.

[NEEDS CLARIFICATION: final scope of the CI-trigger blind-spot remediation (this mission vs. defer to #2034) is to be decided after the research phase confirms root cause and blast radius] <!-- decision_id: 01KWA6Q7SPH9ZN20CH6EW68QDM -->

**Out of scope:** Redesigning the sync authentication model, changing the SaaS auth protocol, or any sync behavior change beyond what is required to make the seeded shared-only session resolve correctly (or to correct the test's seeding).

## User Scenarios & Testing

### Primary scenario — CI / maintainer trusts the sync gate

1. **Actor:** A maintainer (and CI on their behalf) running the sync test suite.
2. **Trigger:** `pytest tests/sync/test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress` (directly, or via the `integration-tests-sync` gate when a PR touches `sync/`).
3. **Setup the test establishes:** a fresh isolated `HOME` seeded with a shared-only encrypted `StoredSession`; isolated `SPEC_KITTY_HOME`; `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; `SPEC_KITTY_SAAS_URL=http://localhost:1` (so the remote fails fast); a minimal git + `.kittify/` scaffold in CWD.
4. **Happy-path outcome:** `agent mission create ac-006-smoke --json` exits 0; stdout is a single valid JSON object with `result == "success"` and a `mission_slug`; the sync flow reaches the direct-ingress resolver and emits `direct ingress skipped` (or `direct_ingress_missing_private_team`) on **stderr**; no sync diagnostic prose (`Connection failed`, `direct ingress skipped`) leaks onto **stdout**.

### Exception / current-failure path (the bug)

- The seeded shared-only session is treated as unauthenticated at `final_sync`, producing `sync_diagnostic … diagnostic_code=sync.server_auth_failure … sync_phase=final_sync … Detail: Not authenticated: no valid access token`. The expected ingress-skip diagnostic is never emitted and the test fails. After this mission, this path must no longer occur for a validly seeded shared-only session.

### Rules / invariants that must always hold

- A correctly seeded shared-only encrypted `StoredSession` MUST be recognized by the sync auth/session resolution as authenticated through to the `final_sync` phase (i.e. it must not degrade to "no valid access token").
- The strict-JSON stdout contract for `agent mission create --json` MUST remain intact: stdout is exactly one JSON document; all sync diagnostics go to stderr.
- The fix MUST exercise the real ingress-skip code path; the assertion that the diagnostic fired MUST NOT be removed or weakened into a tautology.
- The test, once green, MUST stay deterministic under the project's parallel and serial run modes.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Root-cause the mismatch and produce a written determination of which side drifted: the test's shared-only `StoredSession` seeding, or the sync auth/session resolution path that reaches `final_sync`. | Draft |
| FR-002 | Align the two sides so a validly seeded shared-only encrypted session resolves as authenticated through `final_sync` and reaches the direct-ingress resolver, rather than failing with `sync.server_auth_failure`. | Draft |
| FR-003 | After the fix, `test_mission_create_json_strict_when_sync_skips_ingress` passes by emitting `direct ingress skipped` or `direct_ingress_missing_private_team` on stderr (the genuine ingress-skip path), with the diagnostic assertion preserved (not weakened). | Draft |
| FR-004 | Preserve all other assertions of the test: exit code 0, single valid JSON object on stdout with `result == "success"` and a `mission_slug`, and no sync diagnostic prose on stdout. | Draft |
| FR-005 | If the root cause is a regression in shared production sync code (e.g. `sync/_team.py`, `queue.py`, `client.py`, `batch.py`, or session/auth resolution), fix the production code; if it is test-seeding drift, fix the test seeding to match the current contract — whichever FR-001 determines is correct. | Draft |
| FR-006 | Add or adjust regression coverage so the corrected behavior is locked in and a future recurrence of this specific drift is caught by a test that actually runs. | Draft |
| FR-007 | Decide and document whether path-filtered integration gates (`integration-tests-sync` and peers) should gain a broader/periodic trigger so committed-and-failing tests cannot hide behind a `SKIPPED` gate; if adopted in this mission, implement it, otherwise record the decision and its rationale (deferring to #2034). | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The corrected test is deterministic — no flakiness across repeated runs. | 10/10 consecutive green runs locally (`-n0`), and green under the project's parallel mode. | Draft |
| NFR-002 | The fix does not regress the rest of the sync suite. | `tests/sync/` passes (serial real-port pass included) with zero new failures. | Draft |
| NFR-003 | Code changes meet repo quality bars with no new suppressions. | `ruff` and `mypy` clean on changed files; no new `# noqa` / `# type: ignore` / per-file ignores. | Draft |
| NFR-004 | Strict-JSON stdout contract is preserved byte-for-stream-shape. | stdout parses as exactly one JSON object; zero sync diagnostic lines on stdout. | Draft |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Changes land via a PR from `fix/sync-strict-json-auth` into the primary branch; no direct pushes to `origin/main`. | Active |
| C-002 | The diagnostic-fired assertion in the test must remain meaningful — no fix may be achieved by deleting or trivializing that assertion. | Active |
| C-003 | No change to the SaaS authentication protocol or the sync auth model beyond what is required to recognize a validly seeded shared-only session. | Active |
| C-004 | Any CI-trigger change (FR-007) must not materially inflate routine PR CI cost without an explicit, recorded trade-off decision. | Active |

## Success Criteria

- **SC-001:** The previously-red test passes on the primary branch via its genuine ingress-skip path (verified by re-running it on a pristine primary-branch checkout after the fix).
- **SC-002:** A maintainer can no longer be surprised by this class of failure — either the gate runs broadly enough to surface it, or a clear recorded decision defers that to #2034 with rationale.
- **SC-003:** The full `tests/sync/` suite is green with no new failures and no new lint/type suppressions.
- **SC-004:** A written root-cause determination (FR-001) exists in the mission artifacts, stating which side drifted and why the chosen alignment is correct.

## Key Entities

- **StoredSession** — the encrypted, persisted authentication session; here seeded as "shared-only" in an isolated `HOME`. Central to whether the sync flow considers the caller authenticated.
- **Direct ingress resolver** — the sync code path (`resolve_private_team_id_for_ingress` and callers) that decides whether direct ingress applies or is skipped, emitting the `direct ingress skipped` / `direct_ingress_missing_private_team` diagnostic.
- **final_sync phase** — the post-local-command sync phase where the failure currently surfaces as `sync.server_auth_failure`.
- **integration-tests-sync gate** — the path-filtered CI job (`.github/workflows/ci-quality.yml`) gated on `changes.outputs.sync == true` that hides the failure when no `sync/` path changes.

## Assumptions

- The failure is a genuine pre-existing break on the primary branch (the issue documents: byte-identical test and exercised code vs. the primary branch, and reproduction on a pristine checkout). Confirmed locally on `ccd278061`.
- Either the test seeding or the production auth/session resolution drifted; the research phase determines which. Both are treated as candidate fixes until then.
- The CI-trigger blind-spot is real but its remediation may legitimately belong to #2034; this mission will make an explicit decision rather than assume.

## Dependencies

- Reproduction harness: the test's own isolated-HOME / scaffold helpers in `tests/sync/test_strict_json_stdout.py`.
- Related issue #2034 for the gate-selection blind-spot direction.
