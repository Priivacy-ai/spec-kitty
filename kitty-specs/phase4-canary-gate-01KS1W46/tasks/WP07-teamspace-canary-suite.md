---
work_package_id: WP07
title: Teamspace MVP Canary Suite
dependencies:
- WP06
requirement_refs:
- C-002
- C-004
- FR-009
- FR-013
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "65704"
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/tasks/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/tasks/WP07-teamspace-canary-suite.md
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

Run the Teamspace MVP canary suite four consecutive times, preserving logs for each run. The suite proves the full Teamspace lifecycle works against deployed-dev after the auth-boundary fixes.

**No SaaS mutation between runs.** The same intervention prohibition from WP05 applies here.

---

## Context

Working directory: `/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing`

Test files:
- `tests/test_go_live_pre_connector_saas_e2e.py` — primary assertion: `test_authenticated_cli_lifecycle_sync_materializes_in_teamspace_before_connector_testing`
- `tests/test_teamspace_pulse_deployed_dev_e2e.py` — pulse/heartbeat checks
- `tests/test_teamspace_sync_deployed_dev_e2e.py` — full sync lifecycle

Marker: `-m "deployed_dev"`

**Failure triage** (no SaaS mutation as fix):

| Failure | Root Cause | Investigation (do NOT fix by)  |
|---------|-----------|-------------------------------|
| `mission did not materialize within 60s` | Polling helper not connected; drain stalled | Check e2e#40 helper is in use; do NOT extend timeout |
| HTTP 413 on sync | CLI payload too large | Inspect payload; do NOT raise ingress cap |
| `/health/ready/` 503 | Readiness contamination | Check infra terminal_failed; do NOT delete rows |
| DrainMaterializationRejected (business_rule) | planning#16 regression or expected | Verify `last_failure_class`; if business_rule and readiness OK, acceptable |

---

## Subtask T034: Check #1038 for Latest Comment

**Purpose**: Confirm the Teamspace canary is still required.

```bash
unset GITHUB_TOKEN
gh issue view 1038 --repo Priivacy-ai/spec-kitty \
  --json comments \
  --jq '.comments | last | {author: .author.login, body: .body[:300], createdAt}'
```

If the latest comment or the issue body explicitly says the Teamspace canary suite is **no longer required** for this gate, skip T035–T039 and proceed directly to WP08.

Otherwise: proceed with the four-run suite.

---

## Subtask T035: Teamspace MVP Canary Run 1

**Purpose**: First of four consecutive runs.

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing
uv sync

echo "=== Teamspace MVP canary run 1/4 ==="
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
uv run pytest -v \
  tests/test_go_live_pre_connector_saas_e2e.py \
  tests/test_teamspace_pulse_deployed_dev_e2e.py \
  tests/test_teamspace_sync_deployed_dev_e2e.py \
  -m "deployed_dev" \
  2>&1 | tee /tmp/teamspace-canary-run-1.log
RUN1_EXIT=${PIPESTATUS[0]}
echo "Run 1 exit: $RUN1_EXIT"
```

**If `--junitxml` is accepted by local pytest config**, add:
```bash
--junitxml="/tmp/teamspace-canary-run-1.xml"
```

**If run 1 fails**: Triage the failure using the table above. Root-cause before retry. If the fix requires SaaS mutation → halt per stop condition.

---

## Subtask T036: Teamspace MVP Canary Run 2

**Purpose**: Second of four consecutive runs.

```bash
echo "=== Teamspace MVP canary run 2/4 ==="
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
uv run pytest -v \
  tests/test_go_live_pre_connector_saas_e2e.py \
  tests/test_teamspace_pulse_deployed_dev_e2e.py \
  tests/test_teamspace_sync_deployed_dev_e2e.py \
  -m "deployed_dev" \
  2>&1 | tee /tmp/teamspace-canary-run-2.log
RUN2_EXIT=${PIPESTATUS[0]}
echo "Run 2 exit: $RUN2_EXIT"
```

Halt if RUN2_EXIT != 0 and follow same triage.

---

## Subtask T037: Teamspace MVP Canary Run 3

```bash
echo "=== Teamspace MVP canary run 3/4 ==="
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
uv run pytest -v \
  tests/test_go_live_pre_connector_saas_e2e.py \
  tests/test_teamspace_pulse_deployed_dev_e2e.py \
  tests/test_teamspace_sync_deployed_dev_e2e.py \
  -m "deployed_dev" \
  2>&1 | tee /tmp/teamspace-canary-run-3.log
RUN3_EXIT=${PIPESTATUS[0]}
echo "Run 3 exit: $RUN3_EXIT"
```

---

## Subtask T038: Teamspace MVP Canary Run 4

```bash
echo "=== Teamspace MVP canary run 4/4 ==="
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
uv run pytest -v \
  tests/test_go_live_pre_connector_saas_e2e.py \
  tests/test_teamspace_pulse_deployed_dev_e2e.py \
  tests/test_teamspace_sync_deployed_dev_e2e.py \
  -m "deployed_dev" \
  2>&1 | tee /tmp/teamspace-canary-run-4.log
RUN4_EXIT=${PIPESTATUS[0]}
echo "Run 4 exit: $RUN4_EXIT"
```

---

## Subtask T039: Verify and Preserve Logs

**Purpose**: Confirm all runs passed and logs are present.

```bash
echo "=== Run results ==="
for i in 1 2 3 4; do
  LOG="/tmp/teamspace-canary-run-${i}.log"
  if [ -f "$LOG" ]; then
    # Extract pytest exit line
    RESULT=$(tail -5 "$LOG" | grep -E "passed|failed|error" | head -1)
    echo "Run ${i}: $RESULT"
  else
    echo "Run ${i}: LOG NOT FOUND at $LOG"
  fi
done

ls -lh /tmp/teamspace-canary-run-*.log
```

If any run failed, root-cause before accepting the WP. The WP is not done until all 4 runs pass.

---

## Definition of Done

- [ ] T034: #1038 checked — Teamspace suite still required (or skipped with operator confirmation)
- [ ] T035: Run 1 passed; log at `/tmp/teamspace-canary-run-1.log`
- [ ] T036: Run 2 passed; log at `/tmp/teamspace-canary-run-2.log`
- [ ] T037: Run 3 passed; log at `/tmp/teamspace-canary-run-3.log`
- [ ] T038: Run 4 passed; log at `/tmp/teamspace-canary-run-4.log`
- [ ] T039: All logs exist and show passing results

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Materialization timeout | Check e2e#40 polling helper; do not extend timeout |
| HTTP 413 | Investigate CLI payload; do NOT raise ingress cap |
| `/health/ready/` 503 | Check infra terminal_failed; do NOT delete rows |
| pytest --junitxml rejected | Drop it; use .log files as evidence |
| Run fails and needs SaaS cleanup to fix | STOP: this is an explicit stop condition |

---

## Reviewer Guidance

- All 4 run logs must exist at the expected `/tmp/` paths
- Logs must show pytest passing (exit 0); failures must be root-caused and resolved
- Confirm no SaaS mutation occurred between or during runs

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
Run `spec-kitty agent action implement WP07 --agent claude` to start this WP.
(Requires WP06 to be complete — e2e#41 must already be closed.)

## Activity Log

- 2026-05-20T05:26:14Z – claude:sonnet-4-6:implementer:implementer – shell_pid=64426 – Started implementation via action command
- 2026-05-20T05:27:50Z – claude:sonnet-4-6:implementer:implementer – shell_pid=64426 – Deferred: all subtasks pending WP04 canary pass. Result document: wpwp07-*-result.md.
- 2026-05-20T05:28:02Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=65704 – Started review via action command
- 2026-05-20T05:28:22Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=65704 – Review passed: deferral correctly documented with gate condition. No out-of-scope actions. Constraints respected (C-006, C-007). Re-execute when WP04 single-run canary passes.
