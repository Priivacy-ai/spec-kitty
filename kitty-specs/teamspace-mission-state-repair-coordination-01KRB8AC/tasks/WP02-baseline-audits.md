---
work_package_id: WP02
title: Baseline Audits
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- NFR-001
planning_base_branch: fix/teamspace-mission-state-closeout-guards
merge_target_branch: fix/teamspace-mission-state-closeout-guards
branch_strategy: Planning artifacts for this mission were generated on fix/teamspace-mission-state-closeout-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/teamspace-mission-state-closeout-guards unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
agent: "claude:sonnet-4-6:operator:reviewer"
shell_pid: "74756"
history:
- at: '2026-05-11T10:18:12Z'
  event: created
agent_profile: operator
authoritative_surface: kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/
execution_mode: planning_artifact
owned_files:
- kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/wp02-audit-results.md
role: Operator / SRE
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load operator
```

---

## Objective

Run `spec-kitty doctor mission-state --audit --json` in each selected repo from a clean `main` pull. Save JSON reports as `../<repo>.before.audit.json` (i.e., in the workspace root). Record blocker counts by code. T005, T006, T007 are parallel-safe (different repos).

---

## Context

**Prerequisites**: WP01 complete (gate cleared, freeze active, repos on clean main).

**Env var required**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
```
Missing this flag produces incomplete output — TeamSpace validation will be skipped.

**Repos** (T005–T007 run in parallel):
- `spec-kitty-saas/` → `../spec-kitty-saas.before.audit.json`
- `spec-kitty-events/` → `../spec-kitty-events.before.audit.json`
- `spec-kitty-runtime/` → `../spec-kitty-runtime.before.audit.json`

Note: `spec-kitty` itself does not get audited as a repair target in this WP — it is the coordination repo. The three target repos are spec-kitty-saas, spec-kitty-events, and spec-kitty-runtime (conditional).

**Audit JSON schema** (must be present in output):
```json
{
  "total_missions": <int>,
  "missions_with_teamspace_blockers": <int>,
  "teamspace_blockers": <int>,
  "blocker_counts_by_code": {"<code>": <int>},
  "unexpected_errors": [<string>]
}
```

---

## T005 — Pull main + baseline audit in spec-kitty-saas [P]

**Purpose**: Pull latest main and run the baseline audit; capture the pre-repair blocker state.

**Steps**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge

cd $WORKSPACE/spec-kitty-saas
git checkout main
git pull --ff-only origin main
spec-kitty doctor mission-state --audit --json > ../spec-kitty-saas.before.audit.json
echo "=== spec-kitty-saas BEFORE ===" && cat ../spec-kitty-saas.before.audit.json | python3 -m json.tool
```

**Validation**:
```bash
python3 -c "
import json
d = json.load(open('../spec-kitty-saas.before.audit.json'))
required = ['total_missions', 'missions_with_teamspace_blockers', 'teamspace_blockers', 'blocker_counts_by_code']
missing = [k for k in required if k not in d]
assert not missing, f'Missing keys: {missing}'
print(f'OK: {d[\"missions_with_teamspace_blockers\"]} missions with blockers, {d[\"teamspace_blockers\"]} total blockers')
print(f'Blocker codes: {d[\"blocker_counts_by_code\"]}')
"
```

**Acceptance**: JSON file exists with all required keys; `unexpected_errors` is empty or explainable.

---

## T006 — Pull main + baseline audit in spec-kitty-events [P]

**Purpose**: Pull latest main and run the baseline audit in spec-kitty-events.

**Steps**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge

cd $WORKSPACE/spec-kitty-events
git checkout main
git pull --ff-only origin main
spec-kitty doctor mission-state --audit --json > ../spec-kitty-events.before.audit.json
echo "=== spec-kitty-events BEFORE ===" && cat ../spec-kitty-events.before.audit.json | python3 -m json.tool
```

**Validation**:
```bash
python3 -c "
import json
d = json.load(open('../spec-kitty-events.before.audit.json'))
required = ['total_missions', 'missions_with_teamspace_blockers', 'teamspace_blockers', 'blocker_counts_by_code']
missing = [k for k in required if k not in d]
assert not missing, f'Missing keys: {missing}'
print(f'OK: {d[\"missions_with_teamspace_blockers\"]} missions with blockers, {d[\"teamspace_blockers\"]} total blockers')
"
```

---

## T007 — Pull main + baseline audit in spec-kitty-runtime [P]

**Purpose**: Pull latest main and audit spec-kitty-runtime. This determines whether runtime is included in WP03 repair.

**Steps**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge

cd $WORKSPACE/spec-kitty-runtime
git checkout main
git pull --ff-only origin main
spec-kitty doctor mission-state --audit --json > ../spec-kitty-runtime.before.audit.json
echo "=== spec-kitty-runtime BEFORE ===" && cat ../spec-kitty-runtime.before.audit.json | python3 -m json.tool
```

**Runtime inclusion gate** (from WP01 T004 decision):
```bash
python3 -c "
import json
d = json.load(open('../spec-kitty-runtime.before.audit.json'))
if d['missions_with_teamspace_blockers'] > 0:
    print(f'INCLUDE RUNTIME IN REPAIR: {d[\"missions_with_teamspace_blockers\"]} missions with blockers')
else:
    print('SKIP RUNTIME REPAIR: zero TeamSpace blockers — runtime is clean')
"
```

---

## T008 — Analyze audit results; record blocker counts by code

**Purpose**: Read all three (or four) audit JSON files and produce a summary blocker table. Record the per-code counts. This summary feeds into WP03 repair planning and WP05 PR bodies.

**Steps**:
```bash
python3 - <<'EOF'
import json, os

WORKSPACE = "/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge"
repos = ["spec-kitty-saas", "spec-kitty-events", "spec-kitty-runtime"]

print("| Repo | Total Missions | Missions w/ Blockers | Total Blockers | Blocker Codes |")
print("|------|---------------|---------------------|----------------|---------------|")

repair_repos = []
for repo in repos:
    path = os.path.join(WORKSPACE, f"{repo}.before.audit.json")
    if not os.path.exists(path):
        print(f"| {repo} | MISSING | - | - | - |")
        continue
    d = json.load(open(path))
    codes = ", ".join(f"{k}:{v}" for k, v in d.get("blocker_counts_by_code", {}).items())
    print(f"| {repo} | {d['total_missions']} | {d['missions_with_teamspace_blockers']} | {d['teamspace_blockers']} | {codes or 'none'} |")
    if d["missions_with_teamspace_blockers"] > 0:
        repair_repos.append(repo)

print()
print(f"Repos requiring repair: {repair_repos}")
EOF
```

**Record results**: Write the output table to `checklists/wp02-audit-results.md`. Include:
- The full blocker table
- Which repos require repair (for WP03)
- Whether spec-kitty-runtime needs repair (gate from T004/T007)
- Any `unexpected_errors` from any audit

**Non-repairable errors gate**: If any repo has `unexpected_errors` that are not empty and not explainable, do not proceed to WP03 for that repo without investigation.

---

## Branch Strategy

This WP runs operational commands and writes audit JSON files to the workspace root (outside the spec-kitty repo). The only file committed to `fix/teamspace-mission-state-closeout-guards` is `checklists/wp02-audit-results.md`.

- Planning/base branch: `fix/teamspace-mission-state-closeout-guards`
- Merge target: `fix/teamspace-mission-state-closeout-guards`

---

## Definition of Done

- [ ] T005: `spec-kitty-saas.before.audit.json` written with all required keys
- [ ] T006: `spec-kitty-events.before.audit.json` written with all required keys
- [ ] T007: `spec-kitty-runtime.before.audit.json` written; runtime inclusion gate evaluated
- [ ] T008: Blocker table written to `wp02-audit-results.md`; repair repo list confirmed
- [ ] No `unexpected_errors` blocking repair (or all errors documented and explained)

---

## Risks

- **Missing SPEC_KITTY_ENABLE_SAAS_SYNC=1**: Audit skips TeamSpace checks; output is incomplete. Always export this var before running.
- **`--ff-only` pull fails**: Means the local branch has diverged from origin. Investigate before proceeding; do not force-push.
- **Non-repairable errors**: If audit returns unexpected_errors for any repo, stop and document before proceeding.
- **audit JSON missing required keys**: The `spec-kitty doctor mission-state --audit --json` contract guarantees these keys; if they're absent, the CLI version is wrong.

---

## Reviewer Guidance

Verify `wp02-audit-results.md` contains:
1. A populated blocker table with per-code counts for all three repos
2. The runtime inclusion gate result (include or skip)
3. No unexplained unexpected_errors
4. The list of repos that will receive WP03 repair

## Activity Log

- 2026-05-11T10:26:32Z – claude:sonnet-4-6:operator:implementer – shell_pid=74550 – Started implementation via action command
- 2026-05-11T10:28:23Z – claude:sonnet-4-6:operator:implementer – shell_pid=74550 – Baseline audits complete: all 3 repos confirmed need repair; runtime gate triggered (4 missions with blockers)
- 2026-05-11T10:28:30Z – claude:sonnet-4-6:operator:reviewer – shell_pid=74756 – Started review via action command
