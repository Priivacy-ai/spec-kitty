---
work_package_id: WP06
title: Closeout
dependencies:
- WP05
requirement_refs:
- FR-015
- FR-016
planning_base_branch: fix/teamspace-mission-state-closeout-guards
merge_target_branch: fix/teamspace-mission-state-closeout-guards
branch_strategy: Planning artifacts for this mission were generated on fix/teamspace-mission-state-closeout-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/teamspace-mission-state-closeout-guards unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
agent: "claude:sonnet-4-6:operator:reviewer"
shell_pid: "76283"
history:
- at: '2026-05-11T10:18:12Z'
  event: created
agent_profile: operator
authoritative_surface: kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/
execution_mode: planning_artifact
owned_files:
- kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/wp06-closeout-evidence.md
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

After all repair PRs from WP05 are merged, re-audit from fresh clean checkouts. Confirm zero TeamSpace blockers across all repos. Post an evidence table comment on #979 and close it. Re-assess #920 parent epic and update its child issue checklist.

---

## Context

**Hard prerequisite**: WP06 cannot start until all repair PRs from WP05 are merged. Verify PR status before proceeding:
```bash
for REPO in spec-kitty-saas spec-kitty-events; do
  STATE=$(gh pr list --repo Priivacy-ai/$REPO --head repair/teamspace-mission-state-history --json state --jq '.[0].state')
  echo "$REPO: $STATE"
done
# Both must show MERGED
```

**env var required**: `export SPEC_KITTY_ENABLE_SAAS_SYNC=1`

---

## T021 — Re-audit from fresh clean checkouts of all repos

**Purpose**: Validate that the merged repair is intact from a clean state — proving the repair is durable, not just pre-commit.

**Steps**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge

for REPO in spec-kitty-saas spec-kitty-events spec-kitty-runtime; do
  echo "=== $REPO ==="
  cd $WORKSPACE/$REPO
  git fetch origin
  git checkout main
  git pull --ff-only origin main
  git status --short  # must be clean
  spec-kitty doctor mission-state --audit --json > ../spec-kitty-post-merge.${REPO}.audit.json
  echo "=== $REPO post-merge ===" && cat ../spec-kitty-post-merge.${REPO}.audit.json | python3 -m json.tool
done
```

**Acceptance**: All repos pull cleanly on main (ff-only succeeds); audit JSON files written with all required keys.

---

## T022 — Confirm zero TeamSpace blockers across all repos

**Purpose**: Assert the hard gate: zero blockers in every repo after the repair PRs are merged.

**Steps**:
```bash
python3 - <<'EOF'
import json, os, sys

WORKSPACE = "/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge"
repos = ["spec-kitty-saas", "spec-kitty-events", "spec-kitty-runtime"]

print("| Repo | Total Missions | Missions w/ Blockers | Total Blockers | Result |")
print("|------|---------------|---------------------|----------------|--------|")

all_zero = True
for repo in repos:
    path = os.path.join(WORKSPACE, f"spec-kitty-post-merge.{repo}.audit.json")
    if not os.path.exists(path):
        print(f"| {repo} | MISSING | - | - | FAIL |")
        all_zero = False
        continue
    d = json.load(open(path))
    blockers = d["missions_with_teamspace_blockers"]
    total = d["teamspace_blockers"]
    result = "PASS" if blockers == 0 else "FAIL"
    if blockers != 0:
        all_zero = False
    print(f"| {repo} | {d['total_missions']} | {blockers} | {total} | {result} |")

print()
if all_zero:
    print("FINAL GATE: PASSED — zero TeamSpace blockers across all repos")
    sys.exit(0)
else:
    print("FINAL GATE: FAILED — blockers remain; WP06 cannot complete")
    sys.exit(1)
EOF
```

If the gate fails for any repo, stop. The corresponding repo's repair PR may have merged incorrectly or been reverted. Do not close #979 until this gate passes.

---

## T023 — Comment on #979 with evidence table and close it

**Purpose**: Post the final evidence table (before/after, per-repo, with PR links) as a comment on #979, then close the issue.

**Build evidence table**:
```bash
python3 - <<'EOF'
import json, os

WORKSPACE = "/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge"
repos = ["spec-kitty-saas", "spec-kitty-events", "spec-kitty-runtime"]

rows = []
for repo in repos:
    before_path = os.path.join(WORKSPACE, f"{repo}.before.audit.json")
    after_path = os.path.join(WORKSPACE, f"spec-kitty-post-merge.{repo}.audit.json")
    if not os.path.exists(before_path) or not os.path.exists(after_path):
        rows.append(f"| {repo} | missing | missing | - |")
        continue
    b = json.load(open(before_path))
    a = json.load(open(after_path))
    rows.append(f"| {repo} | {b['missions_with_teamspace_blockers']} | {a['missions_with_teamspace_blockers']} | {'PASS' if a['missions_with_teamspace_blockers'] == 0 else 'FAIL'} |")

print("| Repo | Before (missions w/ blockers) | After (missions w/ blockers) | Gate |")
print("|------|------------------------------|------------------------------|------|")
for r in rows:
    print(r)
EOF
```

**Post comment and close**:
```bash
# Build the comment body
EVIDENCE_TABLE=$(python3 - <<'EOF'
import json, os

WORKSPACE = "/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge"
repos = ["spec-kitty-saas", "spec-kitty-events", "spec-kitty-runtime"]
rows = []
for repo in repos:
    before_path = os.path.join(WORKSPACE, f"{repo}.before.audit.json")
    after_path = os.path.join(WORKSPACE, f"spec-kitty-post-merge.{repo}.audit.json")
    b = json.load(open(before_path)) if os.path.exists(before_path) else {}
    a = json.load(open(after_path)) if os.path.exists(after_path) else {}
    before_val = b.get('missions_with_teamspace_blockers', 'missing')
    after_val = a.get('missions_with_teamspace_blockers', 'missing')
    gate = 'PASS' if after_val == 0 else 'FAIL'
    rows.append(f"| {repo} | {before_val} | {after_val} | {gate} |")
print("| Repo | Before | After | Gate |")
print("|------|--------|-------|------|")
for r in rows: print(r)
EOF
)

unset GITHUB_TOKEN && gh issue comment 979 --repo Priivacy-ai/spec-kitty --body "$(cat <<EOF
## TeamSpace Mission-State Repair: Complete

Repair PRs merged in all target repos. Final post-merge audit confirms zero TeamSpace blockers.

### Evidence Table

${EVIDENCE_TABLE}

### Repair PRs

See \`checklists/wp05-pr-links.md\` in mission \`teamspace-mission-state-repair-coordination-01KRB8AC\` for PR URLs.

### Dry-Run Results

All repos passed \`spec-kitty doctor mission-state --teamspace-dry-run --json\` with:
- \`envelope_validation_errors == []\`  
- \`side_logs_skipped >= 0\` (runtime side logs correctly classified)

### Command Sequence

\`\`\`bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
spec-kitty doctor mission-state --audit --json    # → zero blockers
spec-kitty doctor mission-state --teamspace-dry-run --json  # → zero errors
\`\`\`

Closing this issue. Parent epic spec-kitty#920 updated in T024.
EOF
)"

# Close the issue
unset GITHUB_TOKEN && gh issue close 979 --repo Priivacy-ai/spec-kitty --reason completed
```

---

## T024 — Re-assess #920; update child issue checklist

**Purpose**: Review #920 (parent epic) and update its child issue checklist now that the repair is complete. Do not close #920 — per `start-here.md`, #920 closes only after all three cross-repo missions (spec-kitty repair, runtime closeout, SaaS closeout) are done.

**Steps**:

1. Read current #920 state:
```bash
unset GITHUB_TOKEN && gh issue view 920 --repo Priivacy-ai/spec-kitty --json body,state,title
```

2. Identify the checklist item referencing #979 (or the spec-kitty repair mission) and update it:
```bash
# Post a progress comment on #920
unset GITHUB_TOKEN && gh issue comment 920 --repo Priivacy-ai/spec-kitty --body "$(cat <<EOF
## Update: TeamSpace Mission-State Repair Complete (spec-kitty, spec-kitty-saas, spec-kitty-events)

Issue #979 has been resolved and closed. The following repos now have zero TeamSpace blockers:

- spec-kitty-saas: 0 missions_with_teamspace_blockers ✓
- spec-kitty-events: 0 missions_with_teamspace_blockers ✓
- spec-kitty-runtime: 0 missions_with_teamspace_blockers ✓ (was already clean; side-log classifier PR #19 confirmed active)

**#920 remains open** pending:
- Mission 2: spec-kitty-runtime side-log classification closeout (issue #17)
- Mission 3: spec-kitty-saas historical import readiness (#143-146)

Once all three missions complete, #920 can be closed.
EOF
)"
```

3. Write a summary of the #920 status to `wp06-closeout-evidence.md`.

---

## Branch Strategy

This WP produces only planning evidence (`checklists/wp06-closeout-evidence.md`) committed to `fix/teamspace-mission-state-closeout-guards`. All operational commands run in the target repos against their merged `main` branches.

- Planning/base branch: `fix/teamspace-mission-state-closeout-guards`
- Merge target: `fix/teamspace-mission-state-closeout-guards`

---

## Definition of Done

- [ ] T021: Fresh post-merge audit JSON files written for all repos
- [ ] T022: Zero-blocker gate passed for all repos; FINAL GATE: PASSED logged
- [ ] T023: Comment with evidence table posted on #979; #979 closed
- [ ] T024: Progress comment posted on #920; #920 status updated (but not closed)
- [ ] `wp06-closeout-evidence.md` written with final evidence table and issue status

---

## Risks

- **WP06 started before PRs are merged**: The re-audit will reflect pre-merge state and may show false zeros if the working tree changes haven't been committed. Always verify PR state first.
- **#979 already closed**: If a previous run closed #979, skip the close step but still post the evidence comment.
- **#920 closed prematurely**: Per `start-here.md`, #920 must not close until all three cross-repo missions complete. Only post a progress update; do not attempt to close #920.
- **gh auth**: Use `unset GITHUB_TOKEN` before `gh issue` commands if organization auth fails.

---

## Reviewer Guidance

Verify `wp06-closeout-evidence.md` contains:
1. Post-merge blocker table (all repos, PASS/FAIL per repo)
2. URL of the #979 closing comment
3. Confirmation that #979 is closed
4. Confirmation that #920 received a progress comment but was not closed
5. Explicit statement that Missions 2 and 3 remain pending

## Activity Log

- 2026-05-11T10:42:02Z – claude:sonnet-4-6:operator:implementer – shell_pid=75994 – Started implementation via action command
- 2026-05-11T10:45:22Z – claude:sonnet-4-6:operator:implementer – shell_pid=75994 – Ready for review: zero-blocker gate PASSED all repos, #979 closed, #920 updated, wp06-closeout-evidence.md written
- 2026-05-11T10:45:27Z – claude:sonnet-4-6:operator:reviewer – shell_pid=76283 – Started review via action command
