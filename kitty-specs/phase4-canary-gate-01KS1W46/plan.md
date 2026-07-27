# Implementation Plan: Phase 4 Auth Identity-Boundary Canary Gate

**Branch**: `main` | **Date**: 2026-05-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/phase4-canary-gate-01KS1W46/spec.md`
**Mission**: phase4-canary-gate-01KS1W46 (01KS1W46ZAR9S9RJPQQJAMCV6P)

---

## Summary

This gate verifies that both Phase-4 blockers (#1141: `OfflineQueue.queue_event` silent replacement; #1182: `sync now` unknown-error misclassification) are closed with substantive, test-backed fixes. It then installs the post-rc15 CLI RC, runs the four-scenario auth identity-boundary canary to 4/4 consecutive passes, attaches evidence to `e2e#41` and closes it, runs the Teamspace MVP canary suite four times, and posts the evidence comment to `spec-kitty#1038`. The entire gate is delivered as a sequence of 8 work packages executed in the `spec-kitty-end-to-end-testing` and `spec-kitty` repos inside the prepared workspace.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty-cli and e2e testing stack); Bash (canary runner script)
**Primary Dependencies**: `spec-kitty-cli` (pipx-managed), `uv` (env management), `gh` CLI (GitHub issue/PR operations), `pytest` (canary test execution), `flyctl` (SaaS preflight), `curl` (health endpoints)
**Storage**: Filesystem — JSON evidence files at `spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/`, log files at `/tmp/teamspace-canary-run-*.log`
**Testing**: Targeted: `spec-kitty-end-to-end-testing/tests/identity_boundary/` (sync_identity_boundary_deployed_dev marker); `tests/identity_boundary_*_unit_test.py` for harness preflight; `test_go_live_pre_connector_saas_e2e.py`, `test_teamspace_pulse_deployed_dev_e2e.py`, `test_teamspace_sync_deployed_dev_e2e.py` for Teamspace MVP suite
**Target Platform**: macOS/Linux (trusted runner at `/Users/robert/.local/`)
**Project Type**: Operational gate (verification + evidence collection; minimal code changes)
**Performance Goals**: Each canary scenario completes within SaaS timeout bounds; `sync now` 5s final-sync timeout is a gate criterion, not a target to extend
**Constraints**: No SaaS DB mutation, no local queue surgery, no ingress cap change, no final 3.2.0 cut; historical 22 business-rule rows must not be modified; `SPEC_KITTY_ENABLE_SAAS_SYNC=1` required for all auth/SaaS CLI commands

## Branch Contract (confirmed twice per command rules)

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **branch_matches_target**: true

## Charter Check

*Checked against `.kittify/charter/charter.md`.*

| Criterion | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ required | ✅ | Existing CLI stack |
| pytest with 90%+ coverage for new code | ✅ | WP01/WP02 include test coverage audit; new RC cut only if blockers are confirmed via tests |
| mypy --strict | ✅ | Not applicable to operational gate WPs; any RC cut must already pass mypy |
| Integration tests for CLI commands | ✅ | Canary itself IS the integration test surface |
| PyPI distribution via release workflow | ✅ | RC16 (if needed) uses existing `release.yml` workflow per CLAUDE.md |

No violations. Gate passes.

## Project Structure

### Documentation (this feature)

```
kitty-specs/phase4-canary-gate-01KS1W46/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── e2e-41-evidence-comment-template.md
│   └── issue-1038-evidence-comment-template.md
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not created here)
```

### Execution Repos (workspace)

```
spec-kitty-end-to-end-testing/
├── scripts/run-sync-identity-boundary-canary.sh   # Canary runner
├── tests/identity_boundary/                       # Scenario pytest tests
├── tests/identity_boundary_*_unit_test.py         # Harness preflight tests
├── tests/test_go_live_pre_connector_saas_e2e.py   # Teamspace MVP suite
├── tests/test_teamspace_pulse_deployed_dev_e2e.py
├── tests/test_teamspace_sync_deployed_dev_e2e.py
└── artifacts/sync_identity_boundary/
    ├── rc15-attempt1/       # Preserved prior evidence (read-only)
    ├── <new-rc>-attempt1/   # New evidence per attempt (written by gate)
    ├── latest.json          # Symlink/copy of most recent single run
    └── runs/
        ├── run-1.json
        ├── run-2.json
        ├── run-3.json
        └── run-4.json

spec-kitty/
├── pyproject.toml           # Version bump if RC16 needed
├── CHANGELOG.md             # Entry if RC16 needed
└── .kittify/metadata.yaml   # Version metadata if RC16 needed
```

## Complexity Tracking

No charter violations.

---

## Phase 0: Research

### Research Tasks

1. **Understand fix-substance criteria for #1141**: What file(s) contain `OfflineQueue.queue_event` or the call site in the `fire_saas_fanout` → `emit_wp_status_changed` → `OfflineQueue.queue_event` chain? What does "a test that fails without the fix and passes with it" look like for this specific bug?

2. **Understand RC-cut workflow**: What are the exact files that need version bumps? What does `release.yml` require? Is there a `metadata.yaml` that also needs updating?

3. **Canary evidence format**: What is the exact JSON schema expected in `run-N.json`? What fields beyond `"outcome"` are present?

4. **Teamspace MVP canary failure interpretation matrix**: What does each failure mode look like and how do we triage (413, 503, materialization timeout)?

### Research Findings (consolidated into research.md)

**Decision 1: Fix-substance verification approach for #1141**
- Rationale: The start-here.md bisect path is `fire_saas_fanout → emit_wp_status_changed → OfflineQueue.queue_event`. The fix must change behavior (not just add logging). Verification: inspect the merge commit diff; if the diff only touches `logger.*` calls without modifying the `queue_event` invocation logic or its callers, reject as diagnostic-only.
- Files to check: `spec-kitty/src/specify_cli/sync/queue.py` (OfflineQueue), `spec-kitty/src/specify_cli/status/adapters.py` (fanout), `spec-kitty/tests/sync/test_sync_*.py` (new/modified test).

**Decision 2: RC-cut procedure (if needed)**
- Per CLAUDE.md: `git tag -a v3.2.0rc16 -m "Release v3.2.0rc16 - Fix #1141 + #1182"` then `git push origin v3.2.0rc16`. Release is triggered by tag push via `release.yml`. Monitor via `gh run list --workflow=release.yml`.
- Files to bump: `pyproject.toml` (`version = "3.2.0rc16"`), `CHANGELOG.md` (add entry), `.kittify/metadata.yaml` (if version field present).

**Decision 3: Evidence file schema**
- From `spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/rc15-attempt1/`: run-N.json structure includes `outcome` (pass/fail), `run_number`, `scenarios` (list of scenario results), `cli_version`, `timestamp`. The gate checks only `"outcome": "pass"` at top level.

**Decision 4: No RC16 cut authority**
- CLAUDE.md states "NEVER create releases without explicit user instruction." The gate checks if a post-rc15 RC exists; if not, it STOPS and reports rather than cutting autonomously. WP02 reflects this stop condition.

---

## Phase 1: Design & Contracts

### WP Execution Sequence

```
WP01 [serial, hard gate]
  └── Verify #1141 + #1182 CLOSED; audit fix substance
WP02 [depends WP01, hard gate]
  └── Determine latest RC; if still rc15 → STOP; install + verify imports
WP03 [independent, can parallel with WP02]
  └── SaaS preflight: /health/, /health/ready/, drain counts
WP04 [depends WP02 + WP03, hard gate]
  └── Single-run canary (--single); all 4 scenarios must pass
WP05 [depends WP04]
  └── Four-run canary protocol; all 4 × "outcome":"pass"
WP06 [depends WP05]
  └── Bundle evidence; comment on e2e#41; close e2e#41
WP07 [depends WP06]
  └── Teamspace MVP canary suite ×4; preserve logs
WP08 [depends WP07]
  └── Evidence comment on spec-kitty#1038; do NOT close
```

### Contracts

#### Contract: e2e#41 Evidence Comment Template
*(→ `contracts/e2e-41-evidence-comment-template.md`)*

Required fields:
- CLI: `spec-kitty-cli==<version>`, tag `<tag>`, commit `<sha>`
- SaaS: Fly image `<image>`, git SHA `<sha>`
- `/health/ready/` status: 200, events `<version>`
- Drain counts: `terminal_failed_count=0`, `business_rule_rejected_count=22`
- Four-run result: 4/4 pass
- Evidence path: `artifacts/sync_identity_boundary/runs/run-{1..4}.json`
- Explicit statement: "No manual SaaS queue mutation, Fly DB edits, daemon record surgery, local queue deletion, or ingress-cap override was used."

#### Contract: #1038 Evidence Comment Template
*(→ `contracts/issue-1038-evidence-comment-template.md`)*

```markdown
## Canary evidence - post planning#16 auth boundary hardening

- CLI: spec-kitty-cli==<version>, tag <tag>, commit <sha>.
- Events: spec-kitty-events==5.1.0 or newer, tag <tag>, commit <sha>.
- SaaS: Fly image <image>, git SHA <sha>, `/health/` 200, `/health/ready/` 200.
- Drain counts: terminal_failed_infra=<N>, terminal_failed_business_rule=22.
- Identity-boundary canary: 4/4 pass, evidence attached on e2e#41.
- Teamspace MVP canary suite: 4/4 pass.
- Evidence bundle: <path or uploaded link>.

No manual SaaS queue mutation, event replay, DB cleanup, or ingress-cap override was used.
```

### Data Model: Canary Run Result

*(→ `data-model.md`)*

```
CanaryRunResult {
  outcome: "pass" | "fail"
  run_number: int
  timestamp: ISO8601
  cli_version: str
  scenarios: [
    {
      id: int (1-4)
      name: str
      status: "pass" | "fail"
      failure_mode: str | null
      evidence_files: [str]
    }
  ]
}
```

Invariants:
- `outcome = "pass"` iff ALL scenarios have `status = "pass"`
- Evidence files for each attempt are immutable post-run
- `run_number` is 1-indexed; the four-run protocol requires run_number ∈ {1, 2, 3, 4}

### Stop Conditions (Design Constraints)

Each WP has a stop-and-report condition. The gate must NEVER proceed past a stop condition:

| WP | Stop Condition | Action |
|----|---------------|--------|
| WP01 | Either issue still OPEN | Report which issues remain; halt |
| WP01 | #1141 diff is logging-only | Report fix is diagnostic-only; halt |
| WP02 | Latest RC is still rc15 | Report; offer to cut rc16 per operator instruction |
| WP03 | `/health/ready/` ≠ 200 | Report SaaS degradation; halt |
| WP04 | Any scenario fails | Re-open issue(s); preserve evidence; halt |
| WP05 | Any run ≠ "pass" | Re-open issue(s); preserve evidence; halt |
| WP07 | Any Teamspace run fails | Root-cause before retrying; halt on stop conditions |

## Branch Contract (second statement — final report)

- **Current branch at plan start**: `main`
- **Intended planning/base branch**: `main`
- **Final merge target for completed changes**: `main`
- **branch_matches_target**: true

**Next step**: Run `/spec-kitty.tasks` to generate the 8 work packages.
