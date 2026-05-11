---
work_package_id: WP05
title: Create Repair Branches and PRs
dependencies:
- WP04
requirement_refs:
- FR-013
- FR-014
planning_base_branch: fix/teamspace-mission-state-closeout-guards
merge_target_branch: fix/teamspace-mission-state-closeout-guards
branch_strategy: Each target repo gets a repair/teamspace-mission-state-history branch targeting main. PRs are raised in each target repo. T017/T018/T019 are parallel-safe (different repos).
subtasks:
- T017
- T018
- T019
- T020
agent: claude
history:
- at: '2026-05-11T10:18:12Z'
  event: created
agent_profile: operator
authoritative_surface: kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/
execution_mode: planning_artifact
owned_files:
- kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/wp05-pr-links.md
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

For each repaired repo, create a `repair/teamspace-mission-state-history` branch, commit the repair artifacts (manifest + modified `kitty-specs/`), and raise a PR to `main`. Each PR body must satisfy Contract 5 from `contracts/cli-contracts.md`. T017, T018, T019 are parallel-safe.

---

## Context

**Prerequisites**: WP04 complete — all repos show zero blockers and passing dry-runs.

**PR body requirements** (Contract 5):
Each PR must include:
1. Baseline audit summary (from `<repo>.before.audit.json`)
2. Post-repair audit summary (from `<repo>.after.audit.json`)
3. Dry-run command and result (from `<repo>.dry-run.json`)
4. Manifest path under `.kittify/migrations/mission-state/`
5. Links to `spec-kitty#979` and `spec-kitty#920`

**Repos and their repair scope** (confirm from `wp02-audit-results.md`):
- `spec-kitty-saas` → PR to `main`
- `spec-kitty-events` → PR to `main`
- `spec-kitty-runtime` → PR to `main` (only if it was repaired in WP03)

**PR title format**: `repair: TeamSpace mission-state history (<repo>)`
**Branch name**: `repair/teamspace-mission-state-history`

---

## T017 — Create repair branch + PR in spec-kitty-saas [P]

**Purpose**: Commit repair artifacts and raise PR.

**Steps**:
```bash
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge
cd $WORKSPACE/spec-kitty-saas

# Create branch
git checkout -b repair/teamspace-mission-state-history

# Stage repair artifacts
git add .kittify/migrations/mission-state/
git add kitty-specs/

# Verify what's staged
git diff --cached --stat

# Commit
git commit -m "repair: TeamSpace mission-state history — deterministic repair manifest"

# Build PR body with audit summaries
BEFORE=$(python3 -c "import json; d=json.load(open('../spec-kitty-saas.before.audit.json')); print(f'total_missions={d[\"total_missions\"]}, missions_with_teamspace_blockers={d[\"missions_with_teamspace_blockers\"]}, teamspace_blockers={d[\"teamspace_blockers\"]}')")
AFTER=$(python3 -c "import json; d=json.load(open('../spec-kitty-saas.after.audit.json')); print(f'total_missions={d[\"total_missions\"]}, missions_with_teamspace_blockers={d[\"missions_with_teamspace_blockers\"]}, teamspace_blockers={d[\"teamspace_blockers\"]}')")
DRYRUN=$(python3 -c "import json; d=json.load(open('../spec-kitty-saas.dry-run.json')); print(f'envelopes_synthesized={d[\"envelopes_synthesized\"]}, envelope_validation_errors={d[\"envelope_validation_errors\"]}, side_logs_skipped={d.get(\"side_logs_skipped\",0)}')")
MANIFEST=$(ls -t .kittify/migrations/mission-state/*.json | head -1)

# Push and create PR
git push -u origin repair/teamspace-mission-state-history
gh pr create \
  --base main \
  --title "repair: TeamSpace mission-state history (spec-kitty-saas)" \
  --body "$(cat <<EOF
## TeamSpace Mission-State History Repair — spec-kitty-saas

Closes spec-kitty#979. Parent epic: spec-kitty#920.

### Baseline Audit (before repair)

\`\`\`
spec-kitty doctor mission-state --audit --json
$BEFORE
\`\`\`

### Post-Repair Audit (after repair)

\`\`\`
spec-kitty doctor mission-state --audit --json
$AFTER
\`\`\`

### Dry-Run Result

\`\`\`
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --teamspace-dry-run --json
$DRYRUN
\`\`\`

### Repair Manifest

\`${MANIFEST}\`

### Verification

- missions_with_teamspace_blockers: 0 ✓
- envelope_validation_errors: [] ✓
- Manifest includes: repo_head, checksums, row_transformations, quarantine_count, validation_results

### Links

- Tracking issue: [spec-kitty#979](https://github.com/Priivacy-ai/spec-kitty/issues/979)
- Parent epic: [spec-kitty#920](https://github.com/Priivacy-ai/spec-kitty/issues/920)
EOF
)"
```

**Record PR URL**: Save the output PR URL to `wp05-pr-links.md`.

---

## T018 — Create repair branch + PR in spec-kitty-events [P]

**Purpose**: Commit repair artifacts and raise PR in spec-kitty-events (same pattern as T017).

**Steps**:
```bash
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge
cd $WORKSPACE/spec-kitty-events

git checkout -b repair/teamspace-mission-state-history
git add .kittify/migrations/mission-state/
git add kitty-specs/
git diff --cached --stat
git commit -m "repair: TeamSpace mission-state history — deterministic repair manifest"

BEFORE=$(python3 -c "import json; d=json.load(open('../spec-kitty-events.before.audit.json')); print(f'missions_with_teamspace_blockers={d[\"missions_with_teamspace_blockers\"]}, teamspace_blockers={d[\"teamspace_blockers\"]}')")
AFTER=$(python3 -c "import json; d=json.load(open('../spec-kitty-events.after.audit.json')); print(f'missions_with_teamspace_blockers={d[\"missions_with_teamspace_blockers\"]}, teamspace_blockers={d[\"teamspace_blockers\"]}')")
DRYRUN=$(python3 -c "import json; d=json.load(open('../spec-kitty-events.dry-run.json')); print(f'envelope_validation_errors={d[\"envelope_validation_errors\"]}, envelopes_synthesized={d[\"envelopes_synthesized\"]}')")
MANIFEST=$(ls -t .kittify/migrations/mission-state/*.json | head -1)

git push -u origin repair/teamspace-mission-state-history
gh pr create \
  --base main \
  --title "repair: TeamSpace mission-state history (spec-kitty-events)" \
  --body "$(cat <<EOF
## TeamSpace Mission-State History Repair — spec-kitty-events

Closes spec-kitty#979. Parent epic: spec-kitty#920.

### Baseline Audit (before repair)
$BEFORE

### Post-Repair Audit (after repair)
$AFTER

### Dry-Run Result
$DRYRUN

### Repair Manifest
\`${MANIFEST}\`

### Links
- [spec-kitty#979](https://github.com/Priivacy-ai/spec-kitty/issues/979)
- [spec-kitty#920](https://github.com/Priivacy-ai/spec-kitty/issues/920)
EOF
)"
```

---

## T019 — Create repair branch + PR in spec-kitty-runtime [P] (conditional)

**Purpose**: Commit repair artifacts and raise PR in spec-kitty-runtime, **only if** it was repaired in WP03.

**Gate**: Check `wp03-repair-manifest-review.md` or directly:
```bash
python3 -c "
import json
d = json.load(open('/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge/spec-kitty-runtime.before.audit.json'))
if d['missions_with_teamspace_blockers'] == 0:
    print('SKIP: runtime not repaired — no PR needed')
    exit(0)
print('PROCEED: runtime was repaired — raise PR')
"
```

If SKIP: mark T019 as skipped; no PR for runtime. Record this in `wp05-pr-links.md`.

If PROCEED:
```bash
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge
cd $WORKSPACE/spec-kitty-runtime

git checkout -b repair/teamspace-mission-state-history
git add .kittify/migrations/mission-state/ kitty-specs/
git commit -m "repair: TeamSpace mission-state history — deterministic repair manifest"
git push -u origin repair/teamspace-mission-state-history
gh pr create --base main \
  --title "repair: TeamSpace mission-state history (spec-kitty-runtime)" \
  --body "Closes spec-kitty#979. Parent epic: spec-kitty#920. [add audit summaries]"
```

---

## T020 — Verify all PRs link to #979 and #920

**Purpose**: Confirm each raised PR body contains links to both `spec-kitty#979` and `spec-kitty#920`.

**Steps**:
```bash
# List PRs raised from repair branches
for REPO in spec-kitty-saas spec-kitty-events; do
  echo "=== $REPO ==="
  gh pr list --repo Priivacy-ai/$REPO --head repair/teamspace-mission-state-history --json number,title,url,body | \
    python3 -c "
import json, sys
prs = json.load(sys.stdin)
for pr in prs:
    body = pr['body']
    has_979 = '979' in body
    has_920 = '920' in body
    print(f'PR #{pr[\"number\"]}: #979={has_979}, #920={has_920}, URL={pr[\"url\"]}')
    if not (has_979 and has_920):
        print('  ERROR: missing required issue links')
"
done
```

**Record**: Write the PR URL table to `checklists/wp05-pr-links.md`:
```
| Repo | PR # | URL | Links #979 | Links #920 |
|------|------|-----|-----------|-----------|
| spec-kitty-saas | ... | ... | yes | yes |
| spec-kitty-events | ... | ... | yes | yes |
| spec-kitty-runtime | skipped | - | - | - |
```

---

## Branch Strategy

Each target repo gets a `repair/teamspace-mission-state-history` branch targeting `main` in that repo. The spec-kitty coordination repo (this repo) is not modified by this WP — only `checklists/wp05-pr-links.md` is updated here.

- Target repos: spec-kitty-saas (main), spec-kitty-events (main), spec-kitty-runtime (main, conditional)
- This WP's only artifact in spec-kitty: `checklists/wp05-pr-links.md`

---

## Definition of Done

- [ ] T017: PR raised in spec-kitty-saas with Contract 5 body; URL recorded
- [ ] T018: PR raised in spec-kitty-events with Contract 5 body; URL recorded
- [ ] T019: PR raised in spec-kitty-runtime (or explicitly skipped); result recorded
- [ ] T020: All PRs verified to link to #979 and #920
- [ ] `wp05-pr-links.md` written with PR URL table

---

## Risks

- **Missing baseline/after audit files**: T017/T018/T019 depend on audit JSON from WP02/WP04. If the files are missing, stop and regenerate them.
- **PR body missing required sections**: Contract 5 is a hard requirement. A reviewer will reject PRs missing any of the 5 required sections.
- **Branch already exists**: If a previous attempt left a `repair/teamspace-mission-state-history` branch, delete it and start fresh: `git branch -D repair/teamspace-mission-state-history`.
- **gh auth**: Ensure `gh auth status` shows an authenticated token with `repo` scope. If GITHUB_TOKEN has limited scopes, unset it: `unset GITHUB_TOKEN`.

---

## Reviewer Guidance

Verify `wp05-pr-links.md` contains:
1. A PR URL for each repaired repo (or explicit "skipped" for runtime if zero blockers)
2. Confirmation each PR body includes all 5 Contract 5 sections
3. Confirmation both #979 and #920 are linked in each PR
