---
work_package_id: WP03
title: SaaS Preflight
dependencies: []
requirement_refs:
- C-002
- FR-005
- FR-006
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
agent: claude
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/tasks/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/tasks/WP03-saas-preflight.md
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

Verify the live SaaS environment is healthy before any canary run. All checks are read-only. If any check fails, stop and report — do not attempt to fix the SaaS state.

**This WP can run concurrently with WP02.** Both must complete before WP04 starts.

---

## Context

- SaaS app: `spec-kitty-dev` on Fly.io
- Expected Fly image: `spec-kitty-dev:15c7e4589106797540594a531d036517d77b4907` (or newer if redeployed)
- Expected events version: `spec_kitty_events: 5.1.0` or newer
- Historical rows: 22 `terminal_failed` rows with `last_failure_class="business_rule"` — these must NOT be modified

**Stop conditions** (do not proceed to WP04 if any hold):
- `/health/` is not 200
- `/health/ready/` is not 200
- Infra `terminal_failed` count is > 0
- `business_rule_rejected_count` is not 22

---

## Subtask T013: Check /health/ Endpoint

**Purpose**: Confirm the SaaS app is live and running the correct events package version.

```bash
curl -sS --max-time 5 https://spec-kitty-dev.fly.dev/health/ | python3 -m json.tool
```

**Expected**:
- HTTP 200
- JSON contains `"spec_kitty_events": "5.1.0"` (or higher)

**If 503 or timeout**: Wait 15 seconds and retry once. If still failing, stop:
```
GATE BLOCKED: /health/ returned non-200. SaaS may be redeploying.
Do not proceed to canary. Investigate Fly app status.
```

---

## Subtask T014: Check /health/ready/ Endpoint

**Purpose**: Confirm the readiness probe is satisfied (infra terminal_failed count is below threshold).

```bash
curl -sS --max-time 5 https://spec-kitty-dev.fly.dev/health/ready/ | python3 -m json.tool
```

**Expected**: HTTP 200.

**If non-200**:
```
GATE BLOCKED: /health/ready/ returned non-200.
Readiness probe failing — possible infra terminal_failed contamination.
Do not proceed to canary. Check drain queue state.
```

T013 and T014 can run concurrently.

---

## Subtask T015: Check Infra Terminal_Failed Count

**Purpose**: Confirm that infra-classified `terminal_failed` rows are zero.

```bash
flyctl ssh console -a spec-kitty-dev -C "sh -lc 'cd /code && /code/.venv/bin/python manage.py shell <<PYEOF
from apps.sync.models import BatchIntakeItem
total_tf = BatchIntakeItem.objects.filter(state=\"terminal_failed\").count()
infra_tf = BatchIntakeItem.objects.filter(state=\"terminal_failed\", last_failure_class=\"infra\").count()
br_tf = BatchIntakeItem.objects.filter(state=\"terminal_failed\", last_failure_class=\"business_rule\").count()
print(f\"terminal_failed_total={total_tf}\")
print(f\"terminal_failed_infra={infra_tf}\")
print(f\"terminal_failed_business_rule={br_tf}\")
PYEOF'"
```

**Expected**:
- `terminal_failed_infra=0`
- `terminal_failed_business_rule=22`

**If infra count > 0**:
```
GATE BLOCKED: terminal_failed_infra={count} > 0.
This indicates an infrastructure failure, not a business-rule rejection.
Readiness is contaminated. Do not proceed to canary.
```

**Never delete or modify any BatchIntakeItem rows** (Constraint C-002).

---

## Subtask T016: Confirm Business_Rule Count

**Purpose**: The 22 historical rows are the baseline and must be unchanged.

From T015 output, confirm `terminal_failed_business_rule=22`.

If the count has changed (higher or lower), stop:
```
UNEXPECTED: business_rule_rejected_count={count}, expected 22.
This may indicate SaaS DB mutation or a new business-rule rejection.
Investigate before proceeding.
```

Record the full snapshot:
```
terminal_failed_total=22
terminal_failed_infra=0
terminal_failed_business_rule=22
/health/: 200 (spec_kitty_events: <version>)
/health/ready/: 200
```

---

## Definition of Done

- [ ] T013: `/health/` returns 200 with `spec_kitty_events: 5.1.0+`
- [ ] T014: `/health/ready/` returns 200
- [ ] T015: `terminal_failed_infra=0`
- [ ] T016: `terminal_failed_business_rule=22`
- [ ] Health snapshot recorded (for use in WP06 evidence comment)

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Fly SSH console requires auth | `flyctl auth status`; re-authenticate if needed |
| SaaS redeploying during check | Wait 30s and retry /health/ once |
| Infra terminal_failed > 0 | Stop; do not fix by deleting rows |

---

## Reviewer Guidance

- Confirm all four checks passed before approving
- The health snapshot must be captured verbatim for use in WP06 evidence comment

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
Run `spec-kitty agent action implement WP03 --agent claude` to start this WP.
(Can run concurrently with WP02.)
