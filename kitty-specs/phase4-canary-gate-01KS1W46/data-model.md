# Data Model: Phase 4 Auth Identity-Boundary Canary Gate

**Mission**: phase4-canary-gate-01KS1W46
**Date**: 2026-05-20

---

## Entities

### CanaryRunResult

Top-level artifact produced by `scripts/run-sync-identity-boundary-canary.sh` for each run.

| Field | Type | Description |
|-------|------|-------------|
| `outcome` | `"pass" \| "fail"` | Gate field — `"pass"` iff all scenarios pass |
| `run_id` | ULID string | Unique run identifier |
| `run_number` | int (1–4) | Position in the four-run protocol |
| `cli_version` | string | Installed `spec-kitty-cli` version (e.g., `3.2.0rc16`) |
| `events_package_version` | string | Installed `spec-kitty-events` version (e.g., `5.1.0`) |
| `timestamp` | ISO 8601 | Run start time |
| `scenarios` | list[ScenarioResult] | One entry per identity-boundary scenario |

**Invariants**:
- `outcome = "pass"` iff every `scenario.status == "pass"`
- `run_number` is unique within the four-run protocol; values 1–4 are required
- Evidence files for a completed run are immutable

### ScenarioResult

Sub-entity embedded in `CanaryRunResult.scenarios`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | int (1–4) | Scenario number |
| `name` | string | Human-readable scenario name |
| `status` | `"pass" \| "fail"` | Individual scenario outcome |
| `failure_mode` | string \| null | Diagnostic code when failing (e.g., `sync.event_loop_unavailable`) |
| `details` | string \| null | Free-text diagnostic detail |

**Scenario definitions**:

| id | Name | Tests |
|----|------|-------|
| 1 | Fresh Authenticated Mission | `sync now` after fresh auth; no prior queue state |
| 2 | Legacy Queue Row Migration | `sync now` with pre-existing queue rows from a different identity |
| 3 | Daemon Owner Mismatch Refusal | `sync status --check` with injected owner mismatch |
| 4 | Review Rejection Force-Required Contract | `move-task --to planned` rollback after review rejection; verifies `force=True` + `reason` queued |

### EvidenceBundle

Filesystem artifact produced by the gate after the four-run protocol passes.

| Path | Description |
|------|-------------|
| `artifacts/sync_identity_boundary/<rc-tag>-attempt<N>/latest.json` | Copy of the most recent single run (or run-4 for four-run) |
| `artifacts/sync_identity_boundary/<rc-tag>-attempt<N>/runs/run-{1..4}.json` | Individual run results |
| `/tmp/teamspace-canary-run-{1..4}.log` | Teamspace MVP canary stdout/stderr |
| `/tmp/teamspace-canary-run-{1..4}.xml` | Teamspace MVP pytest JUnit XML (if pytest accepts `--junitxml`) |

**Invariant**: Prior attempt directories (`rc15-attempt1/`) are read-only. Each attempt uses a new subdirectory.

---

## State Transitions

### Gate Execution State

```
IDLE
  └─ [both blockers CLOSED + fixes substantive] ──► BLOCKERS_VERIFIED
  └─ [either blocker OPEN or fix diagnostic-only] ──► STOPPED(report)

BLOCKERS_VERIFIED
  └─ [latest RC > rc15] ──────────────────────────► RC_INSTALLED
  └─ [latest RC == rc15] ─────────────────────────► STOPPED(report: need rc16)

RC_INSTALLED
  └─ [imports ok + preflight ok] ─────────────────► PREFLIGHT_CLEAN
  └─ [preflight fails] ────────────────────────────► STOPPED(report: SaaS degraded)

PREFLIGHT_CLEAN
  └─ [single run 4/4 pass] ───────────────────────► SINGLE_RUN_PASSED
  └─ [any scenario fails] ─────────────────────────► STOPPED(re-open issue, preserve evidence)

SINGLE_RUN_PASSED
  └─ [four-run 4×4/4 pass] ───────────────────────► FOUR_RUN_PASSED
  └─ [any run/scenario fails] ─────────────────────► STOPPED(re-open issue, preserve evidence)

FOUR_RUN_PASSED
  └─ [evidence comment posted, #41 closed] ───────► E2E_GATE_CLOSED

E2E_GATE_CLOSED
  └─ [Teamspace canary ×4 pass] ──────────────────► TEAMSPACE_PASSED
  └─ [any Teamspace run fails] ────────────────────► STOPPED(root-cause required)

TEAMSPACE_PASSED
  └─ [#1038 comment posted] ──────────────────────► GATE_COMPLETE (#1038 remains OPEN)
```

---

## Key Invariants

1. **No mutation between runs**: The SaaS database, local offline queue, and daemon record must not be modified between any two consecutive canary runs. The gate verifies this by relying solely on the canary harness's built-in state management.
2. **Immutable evidence**: Once a run result JSON is written, it must not be modified post-hoc.
3. **Historical rows untouched**: The 22 `terminal_failed / business_rule` rows in the deployed SaaS DB must have the same count and content at gate completion as at gate start.
4. **CLI traceability**: The installed CLI must be traceable to a commit at or after `cc5e1ca983adff4a45489ce7afe11ad3a3a26e30`.
