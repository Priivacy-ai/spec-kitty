---
work_package_id: WP04
title: Single-Run Identity-Boundary Canary
dependencies:
- WP02
- WP03
requirement_refs:
- C-003
- C-004
- C-008
- FR-007
- FR-009
- FR-010
- NFR-001
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
- T023
agent: claude
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/tasks/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/tasks/WP04-single-run-canary.md
- spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/*-attempt*/latest.json
- spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/*-attempt*/canary-single-run.log
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

Run the identity-boundary canary in `--single` mode using the post-rc15 RC installed in WP02. All four scenarios must pass. On any failure, re-open the appropriate GitHub issue and preserve evidence — do not retry until the fix is confirmed.

**Hard gate**: If any scenario fails, halt. Do not proceed to WP05.

---

## Context

Working directory: `/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing`

Scenario definitions:
- **Scenario 1**: Fresh authenticated mission — proves `sync now` works from clean state
- **Scenario 2**: Legacy queue row migration — proves old queue rows migrate cleanly
- **Scenario 3**: Daemon owner mismatch refusal — proves the boundary refuses foreign daemons
- **Scenario 4**: Review-rejection force-required contract — proves `in_review → planned` rollback rows reach the queue

Previously failing patterns (must NOT reappear):
- Scenarios 1+2: `sync.event_loop_unavailable` + `unknown: N` errors → signals #1182 regression
- Scenario 4: assertion `from='for_review' to='in_review'` → signals #1141 regression

Do NOT manually kill daemons, delete queue files, or mutate SaaS state to "make it green."

---

## Subtask T017: Export Required Environment Variables

**Purpose**: All env vars must be set before running any canary step.

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_E2E_TRUSTED_RUNNER=1
export SK_E2E_SPEC_KITTY_BIN=/Users/robert/.local/bin/spec-kitty
export SK_E2E_SPEC_KITTY_PYTHON=/Users/robert/.local/pipx/venvs/spec-kitty-cli/bin/python
export SK_E2E_SPEC_KITTY_REPO=/nonexistent

# Confirm vars are set
echo "CLI: $SK_E2E_SPEC_KITTY_BIN"
echo "Python: $SK_E2E_SPEC_KITTY_PYTHON"
"$SK_E2E_SPEC_KITTY_BIN" --version
```

---

## Subtask T018: uv sync

**Purpose**: Ensure the e2e test dependencies are current.

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing
uv sync
```

---

## Subtask T019: Kill Orphan Sync Daemons

**Purpose**: Eliminate any stale daemon processes that could interfere with the fresh-auth scenario.

```bash
pkill -9 -f run_sync_daemon 2>/dev/null || true
sleep 2
ps aux | grep run_sync_daemon | grep -v grep || echo "Clean — no orphan daemons"
```

---

## Subtask T020: Run Harness Unit Test Preflight

**Purpose**: Validate the test harness itself before running the live canary.

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing

uv run pytest \
  tests/identity_boundary_evidence_unit_test.py \
  tests/identity_boundary_preflight_unit_test.py \
  tests/identity_boundary_status_parser_unit_test.py \
  tests/test_harness_sync_and_ids.py \
  -q

# Also validate the canary script syntax
bash -n scripts/run-sync-identity-boundary-canary.sh
```

**Expected**: All preflight tests pass. Script syntax check exits 0.

**If preflight tests fail**: This is a harness issue, not a canary failure. Investigate the test files but do not modify them without root cause.

---

## Subtask T021: Run --single Canary

**Purpose**: Execute one full pass of all four scenarios against deployed-dev.

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing

./scripts/run-sync-identity-boundary-canary.sh --single 2>&1 | tee /tmp/canary-single-run.log
CANARY_EXIT=$?
echo "Canary exit code: $CANARY_EXIT"
```

The script writes evidence to `artifacts/sync_identity_boundary/latest.json` and `runs/run-1.json`.

---

## Subtask T022: Assert All 4 Scenarios in latest.json

**Purpose**: Inspect the result JSON — do not trust the exit code alone.

```bash
python3 - <<'EOF'
import json, sys
with open("artifacts/sync_identity_boundary/latest.json") as f:
    result = json.load(f)

print(f"Overall outcome: {result['outcome']}")
print(f"CLI version: {result.get('cli_version','?')}")
for s in result.get('scenarios', []):
    status = s.get('status','?')
    icon = '✅' if status == 'pass' else '❌'
    print(f"  {icon} Scenario {s['id']}: {s['name']} → {status}")
    if status == 'fail':
        print(f"     failure_mode: {s.get('failure_mode','?')}")
        print(f"     details: {s.get('details','?')[:200]}")

if result['outcome'] != 'pass':
    sys.exit(1)
EOF
```

**If outcome is "pass"**: All four scenarios green. Proceed to WP05.

---

## Subtask T023: On Failure — Re-open Issue(s) and Preserve Evidence

**Purpose**: Fail safely and cleanly. Only execute this subtask if T022 found failures.

**Preserve evidence first** (auto-increments attempt number — never overwrites prior attempts):
```bash
RC_TAG=$(spec-kitty --version 2>&1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+' | head -1)
# Auto-increment: find first unused attempt slot
ATTEMPT_N=1
while [ -d "artifacts/sync_identity_boundary/${RC_TAG}-attempt${ATTEMPT_N}" ]; do
  ATTEMPT_N=$((ATTEMPT_N + 1))
done
ATTEMPT_DIR="artifacts/sync_identity_boundary/${RC_TAG}-attempt${ATTEMPT_N}"
mkdir -p "$ATTEMPT_DIR"
cp artifacts/sync_identity_boundary/latest.json "$ATTEMPT_DIR/latest.json" 2>/dev/null || true
cp /tmp/canary-single-run.log "$ATTEMPT_DIR/canary-single-run.log" 2>/dev/null || true
echo "Evidence preserved at: $ATTEMPT_DIR"
```

**Triage scenario failures**:

For scenario 4 failure (`from='for_review' to='in_review'`):
```bash
unset GITHUB_TOKEN
gh issue reopen 1141 --repo Priivacy-ai/spec-kitty \
  --comment "Reopened: ${RC_TAG} canary single run attempt ${ATTEMPT_N} — scenario 4 still failing.
Assertion: from='in_review' to='planned'
Got: from='for_review' to='in_review'
Evidence: artifacts/sync_identity_boundary/${RC_TAG}-attempt${ATTEMPT_N}/latest.json"
```

For scenarios 1/2 failure (`sync.event_loop_unavailable` + `unknown: N`):
```bash
unset GITHUB_TOKEN
gh issue reopen 1182 --repo Priivacy-ai/spec-kitty \
  --comment "Reopened: ${RC_TAG} canary single run attempt ${ATTEMPT_N} — scenarios 1/2 still failing.
sync.event_loop_unavailable + unknown error classification persists.
Evidence: artifacts/sync_identity_boundary/${RC_TAG}-attempt${ATTEMPT_N}/latest.json"
```

After re-opening issue(s):
```
GATE BLOCKED: Single-run canary failed on ${RC_TAG} (attempt ${ATTEMPT_N}).
Issues re-opened: [list]
Evidence: artifacts/sync_identity_boundary/${RC_TAG}-attempt1/latest.json
Do not proceed to WP05. Wait for new fixes and a fresh RC.
```

---

## Definition of Done

- [ ] T017: All env vars exported and CLI version confirmed
- [ ] T018: `uv sync` completed without errors
- [ ] T019: No orphan daemons running
- [ ] T020: All preflight tests pass; script syntax clean
- [ ] T021: `--single` canary completed (exit code recorded)
- [ ] T022: `latest.json` shows `"outcome": "pass"` for all 4 scenarios
- [ ] T023: (only if failure) Evidence preserved, issues re-opened, gate blocked

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Scenario 4 regression (#1141 not fully fixed) | T023: re-open #1141, preserve evidence |
| Scenarios 1/2 regression (#1182 not fully fixed) | T023: re-open #1182, preserve evidence |
| Daemon orphan from prior run | T019: explicit pkill before canary |
| Harness test failures (not canary failures) | T020: distinguish harness vs canary issues |

---

## Reviewer Guidance

- Confirm T021 ran with `--single` flag (not the full four-run protocol)
- Verify `latest.json` was read after the run, not from a cached prior result
- If any scenario failed: confirm the issue was re-opened and evidence was preserved before halting

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
Run `spec-kitty agent action implement WP04 --agent claude` to start this WP.
(Requires WP02 and WP03 to be complete first.)
