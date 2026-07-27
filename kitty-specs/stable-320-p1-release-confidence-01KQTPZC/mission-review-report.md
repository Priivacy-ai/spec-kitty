# Mission Review Report: stable-320-p1-release-confidence-01KQTPZC

**Reviewer**: Codex
**Date**: 2026-05-05
**Mission**: `stable-320-p1-release-confidence-01KQTPZC` - Stable 3.2.0 P1 Release Confidence
**Baseline commit**: `14375247`
**HEAD at review**: `6490f9c9`
**WPs reviewed**: WP01, WP02, WP03, WP04

---

## Gate Results

### Gate 1 - Contract tests

- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run --extra test python -m pytest tests/contract/ -v`
- Exit code: 0
- Result: PASS
- Notes: 237 passed, 1 skipped. Initial review exposed board-summary `mission_number` string output and orchestrator-api non-JSON stdout when sync warnings were emitted; both were fixed in commit `8ffb7bf3` and the full gate passed afterward. The post-push CI agent integration shard then exposed a request-object sync-control regression in `emit_status_transition`; commit `9d95db33` fixed that path, and the local CI shard reproduction passed.

### Gate 2 - Architectural tests

- Command: `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run --extra test python -m pytest tests/architectural/ -v`
- Exit code: 0
- Result: PASS
- Notes: 96 passed, 1 skipped.

### Gate 3 - Cross-Repo E2E

- Command: `SPEC_KITTY_REPO=/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty SPEC_KITTY_ENABLE_SAAS_SYNC=1 UV_CACHE_DIR=/private/tmp/spec-kitty-e2e-uv-cache uv run --python 3.11 python -m pytest scenarios/ -v`
- Exit code: 1
- Result: EXCEPTION
- Exception: `mission-exception.md`
- Notes: 4 passed, 1 xfailed, 1 failed. The failed scenario was `scenarios/contract_drift_caught.py::test_contract_drift_caught`; it failed while stdlib `venv.create(..., with_pip=True)` attempted to run `ensurepip` in a nested temporary venv and could not load the uv-managed Python dylib. This happened before the scenario reached Spec Kitty product behavior. The SaaS scenario was XFAIL because the dev endpoint was unreachable from this workstation.

### Gate 4 - Issue Matrix

- File: `kitty-specs/stable-320-p1-release-confidence-01KQTPZC/issue-matrix.md`
- Rows: 23
- Empty / `unknown` verdicts: 0
- `deferred-with-followup` rows missing a follow-up handle: 0
- Result: PASS

## FR Coverage Matrix

| FR ID | Description | WP Owner | Test / Evidence | Test Adequacy | Finding |
| --- | --- | --- | --- | --- | --- |
| FR-001 | Consistent task-board progress output | WP01 | `tests/specify_cli/status/test_progress.py`; `tests/specify_cli/agent_utils/test_status.py`; `tests/specify_cli/cli/commands/agent/test_tasks_status_progress.py` | ADEQUATE | - |
| FR-002 | Done-only numerator must not pair with readiness percentage unless labeled | WP01 | Human output and JSON regression tests; `release-evidence.md#966-task-board-progress-semantics` | ADEQUATE | - |
| FR-003 | Approved-only, done-only, mixed, empty coverage | WP01 | Focused status/progress tests, 292 passed in WP01 review | ADEQUATE | - |
| FR-004 | Touched machine-readable output remains parseable and explicit | WP01 | JSON status regression tests; contract gate after mission-review fix | ADEQUATE | - |
| FR-005 | Verify current gates for installed-vs-lock drift | WP02 | `scripts/release/check_shared_package_drift.py --check-installed`; contract gate | ADEQUATE | - |
| FR-006 | Produce closure evidence if gates sufficient | WP02/WP04 | `release-evidence.md#848-dependency-drift-gate`; `issue-closure-notes.md#848` | ADEQUATE | - |
| FR-007 | Add/harden focused drift guard if needed | WP02 | `tests/release/test_check_shared_package_drift.py`; release workflows invoke `--check-installed` | ADEQUATE | - |
| FR-008 | Include `spec-kitty-events` in drift verification | WP02 | Release evidence records installed and lockfile `spec-kitty-events` 4.1.0 | ADEQUATE | - |
| FR-009 | Drift failure names package/version/remediation | WP02 | Guard remediation says `uv sync --extra test --extra lint` | ADEQUATE | - |
| FR-010 | Fresh local-only lifecycle smoke | WP03 | `smoke-evidence.md#local-only-lifecycle` | ADEQUATE | - |
| FR-011 | Fresh SaaS-enabled lifecycle smoke with env var | WP03 | `smoke-evidence.md#saas-enabled-lifecycle` | ADEQUATE WITH NOTE | Sync drain proof unavailable; limitation documented. |
| FR-012 | Smoke covers setup/specify/plan/tasks/implement-review/merge/PR-ready evidence | WP03 | `smoke-evidence.md` command tables | ADEQUATE | - |
| FR-013 | Smoke failures have issue/fix/blocker/decision | WP03/WP04 | `smoke-evidence.md#failure-and-limitation-handling`; `deferrals.md#smoke-limitation` | ADEQUATE | - |
| FR-014 | #971 included/deferred explicitly | WP04 | `release-evidence.md#971-strict-mypy-decision`; `deferrals.md#explicit-deferrals` | ADEQUATE | - |
| FR-015 | Final evidence includes ruff status | WP04 | `release-evidence.md#final-gate` | ADEQUATE | - |

## Drift Findings

No unresolved drift findings remain after commit `8ffb7bf3`.

Resolved during mission review:

- `src/specify_cli/status/views.py`: `board-summary.json` now emits numeric
  `mission_number` when the snapshot value is a numeric string, satisfying the
  canonical machine-facing contract.
- `src/specify_cli/orchestrator_api/commands.py` and
  `src/specify_cli/status/work_package_lifecycle.py`: orchestrator-api
  transitions disable sync daemon/dossier side effects so stdout remains a
  single JSON envelope when `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- `src/specify_cli/status/emit.py`: request-object transition calls now accept
  the same sync daemon/dossier controls without being misclassified as mixed
  legacy arguments; this fixed the `integration-tests-agent` CI shard.
- `tests/e2e/test_charter_epic_golden_path.py`: the charter golden-path E2E
  assertion now compares lifecycle records against the `/next --advance`
  envelope that actually writes the lifecycle entry, not the read-only query
  preview. This fixed the post-push `e2e-cross-cutting` CI failure in commit
  `6490f9c9`.
- `issue-matrix.md` was added so Gate 4 has explicit issue verdicts.

Post-fix CI on `6490f9c9`:

- `CI Quality`: PASS, including `e2e-cross-cutting` in 5m47s.
- `ci-windows`: PASS.
- `Protect Main Branch`: expected failure for direct push to `main`; not a
  code-health signal per repository policy.

## Risk Findings

No blocking risk findings remain.

Non-blocking risk: WP03 and Gate 3 both show this workstation cannot currently
prove hosted sync drain. The lifecycle commands completed and queued events,
but server delivery remains unproven here. This is documented in
`smoke-evidence.md`, `deferrals.md`, and `mission-exception.md`.

## Silent Failure Candidates

No new silent failure candidates were introduced by the mission-review fixes.
The new orchestrator path changes reduce a silent JSON-contract failure by
preventing sync side-effect warnings from contaminating machine stdout.

## Security Notes

| Finding | Location | Risk class | Recommendation |
| --- | --- | --- | --- |
| None blocking | N/A | N/A | No new subprocess, credential, or network call surface was introduced by the mission-review fixes. |

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

The merged mission now satisfies the spec contract for #966, #848, the local
and SaaS-enabled smoke evidence, #971 deferral, and release evidence. Contract
and architectural gates pass after the mission-review fixes. Cross-repo E2E has
a documented Gate 3 operator exception for a nested-venv Python dylib failure
outside Spec Kitty product behavior. The remaining hosted-sync limitation is
documented and non-blocking for this release-confidence mission.

### Open items (non-blocking)

- Retry cross-repo E2E on a trusted runner with a Python installation whose
  nested `venv.create(..., with_pip=True)` path works.
- Retry hosted SaaS sync drain when `https://spec-kitty-dev.fly.dev` and the
  local sync daemon are reachable without auth-refresh contention.
