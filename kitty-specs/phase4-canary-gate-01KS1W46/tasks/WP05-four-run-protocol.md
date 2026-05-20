---
work_package_id: WP05
title: Four-Run Canary Protocol
dependencies:
- WP04
requirement_refs:
- C-003
- FR-008
- FR-009
- FR-010
- NFR-001
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "64426"
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/tasks/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/tasks/WP05-four-run-protocol.md
- spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/runs/run-*.json
- spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/latest.json
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer
```

Read the entire prompt before acting.

---

## Objective

Run the full four-run identity-boundary canary protocol. All four consecutive runs must produce `"outcome": "pass"`. No manual SaaS, queue, or daemon interventions between runs.

**Hard gate**: If any run fails, halt, re-open the appropriate issue, preserve evidence.

---

## Context

Working directory: `/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing`

The four-run protocol is sequential — runs cannot be parallelized. The harness manages run numbering and produces `artifacts/sync_identity_boundary/runs/run-{1..4}.json`.

**Intervention prohibition (NFR-001)**: Do NOT perform any of the following between runs:
- `pkill -f run_sync_daemon`
- `flyctl ssh console` (any write/delete operation)
- Direct SQLite queue file deletion or modification
- Curl mutations to SaaS endpoints
- Local `.kittify/` queue file deletions

If you find yourself wanting to clean up before a run to make it pass — that is a stop condition. Preserve evidence and halt.

---

## Subtask T024: Run Full Four-Run Canary Protocol

**Purpose**: Execute the official four-consecutive-run protocol.

Env vars must already be exported from WP04. If this is a fresh shell, re-export:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_E2E_TRUSTED_RUNNER=1
export SK_E2E_SPEC_KITTY_BIN=/Users/robert/.local/bin/spec-kitty
export SK_E2E_SPEC_KITTY_PYTHON=/Users/robert/.local/pipx/venvs/spec-kitty-cli/bin/python
export SK_E2E_SPEC_KITTY_REPO=/nonexistent
```

Run the protocol:
```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing

./scripts/run-sync-identity-boundary-canary.sh 2>&1 | tee /tmp/canary-four-run.log
FOUR_RUN_EXIT=$?
echo "Four-run exit code: $FOUR_RUN_EXIT"
```

The script runs 4 iterations sequentially. It writes:
- `artifacts/sync_identity_boundary/runs/run-1.json`
- `artifacts/sync_identity_boundary/runs/run-2.json`
- `artifacts/sync_identity_boundary/runs/run-3.json`
- `artifacts/sync_identity_boundary/runs/run-4.json`
- `artifacts/sync_identity_boundary/latest.json` (= run-4)

---

## Subtask T025: Assert "outcome":"pass" in All 4 Run Files

**Purpose**: Inspect each run's JSON — do not rely solely on the script exit code.

```bash
python3 - <<'EOF'
import json, sys, pathlib

runs_dir = pathlib.Path("artifacts/sync_identity_boundary/runs")
all_pass = True

for run_num in range(1, 5):
    path = runs_dir / f"run-{run_num}.json"
    if not path.exists():
        print(f"❌ run-{run_num}.json NOT FOUND at {path}")
        all_pass = False
        continue

    with open(path) as f:
        result = json.load(f)

    outcome = result.get('outcome', '?')
    icon = '✅' if outcome == 'pass' else '❌'
    print(f"{icon} Run {run_num}: outcome={outcome}")

    for s in result.get('scenarios', []):
        s_status = s.get('status', '?')
        s_icon = '  ✅' if s_status == 'pass' else '  ❌'
        print(f"{s_icon} Scenario {s['id']}: {s['name']} → {s_status}")
        if s_status != 'pass':
            print(f"     failure_mode: {s.get('failure_mode','?')}")
            all_pass = False

if all_pass:
    print("\n🎉 All 4 runs: PASS. Proceed to WP06.")
else:
    print("\n🛑 FAILURE detected. Execute T027.")
    sys.exit(1)
EOF
```

---

## Subtask T026: Confirm Zero Interventions Between Runs

**Purpose**: Self-attestation that the protocol was clean.

After the four-run protocol completes, confirm in your implementation output:

```
Intervention attestation:
- No pkill commands run between runs: ✓
- No flyctl ssh console write operations: ✓
- No local queue file modifications: ✓
- No SaaS endpoint curl mutations: ✓
- No .kittify/ queue file deletions: ✓
```

If any intervention was performed — even if the runs still passed — note it explicitly. The evidence comment in WP06 requires an explicit "no mutation" statement; any intervention invalidates the gate.

---

## Subtask T027: On Failure — Re-open Issue(s) and Preserve Evidence

**Purpose**: Only if T025 found failures.

```bash
RC_TAG=$(spec-kitty --version 2>&1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+' | head -1)
# Find next attempt number (don't overwrite prior attempts)
ATTEMPT_N=1
while [ -d "artifacts/sync_identity_boundary/${RC_TAG}-attempt${ATTEMPT_N}" ]; do
  ATTEMPT_N=$((ATTEMPT_N + 1))
done
ATTEMPT_DIR="artifacts/sync_identity_boundary/${RC_TAG}-attempt${ATTEMPT_N}"

mkdir -p "$ATTEMPT_DIR/runs"
cp artifacts/sync_identity_boundary/runs/run-*.json "$ATTEMPT_DIR/runs/" 2>/dev/null || true
cp artifacts/sync_identity_boundary/latest.json "$ATTEMPT_DIR/latest.json" 2>/dev/null || true
cp /tmp/canary-four-run.log "$ATTEMPT_DIR/canary-four-run.log" 2>/dev/null || true
echo "Evidence preserved at: $ATTEMPT_DIR"
```

Re-open issues based on failure mode:
- Scenario 4 `from='for_review' to='in_review'`: re-open `#1141`
- Scenarios 1/2 `unknown: N` + `sync.event_loop_unavailable`: re-open `#1182`

```bash
unset GITHUB_TOKEN
# Re-open whichever issue(s) match the failure mode
gh issue reopen <ISSUE_NUMBER> --repo Priivacy-ai/spec-kitty \
  --comment "Reopened: four-run protocol failed on ${RC_TAG} attempt ${ATTEMPT_N}.
Evidence: artifacts/sync_identity_boundary/${RC_TAG}-attempt${ATTEMPT_N}/"
```

Then halt:
```
GATE BLOCKED: Four-run protocol failed.
Evidence preserved at: ${ATTEMPT_DIR}
Do not proceed to WP06.
```

---

## Definition of Done

- [ ] T024: Full four-run protocol completed (exit code recorded)
- [ ] T025: All 4 × `"outcome": "pass"` confirmed in run-{1..4}.json
- [ ] T026: Zero interventions attested
- [ ] T027: (only if failure) Evidence preserved, issues re-opened, gate blocked

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Any run fails | T027: preserve evidence, re-open issue, halt |
| Temptation to clean up between runs | Never — this is a stop condition |
| run-N.json files missing | T025 catches missing files |
| Script produces pass exit code but JSON shows fail | T025: always verify JSON directly |

---

## Reviewer Guidance

- Verify all 4 run-N.json files exist and contain `"outcome": "pass"`
- Confirm the intervention attestation in T026 is explicit and honest
- If any failure: confirm evidence preserved before issue re-open

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
Run `spec-kitty agent action implement WP05 --agent claude` to start this WP.
(Requires WP04 to pass completely first.)

## Activity Log

- 2026-05-20T05:26:09Z – claude:sonnet-4-6:implementer:implementer – shell_pid=64426 – Started implementation via action command
- 2026-05-20T05:27:48Z – claude:sonnet-4-6:implementer:implementer – shell_pid=64426 – Deferred: all subtasks pending WP04 canary pass. Result document: wpwp05-*-result.md.
