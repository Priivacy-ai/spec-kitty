---
work_package_id: WP03
title: Run Deterministic Repair
dependencies:
- WP02
requirement_refs:
- C-001
- C-002
- C-003
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-002
planning_base_branch: fix/teamspace-mission-state-closeout-guards
merge_target_branch: fix/teamspace-mission-state-closeout-guards
branch_strategy: Planning artifacts for this mission were generated on fix/teamspace-mission-state-closeout-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/teamspace-mission-state-closeout-guards unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
agent: "claude:sonnet-4-6:operator:reviewer"
shell_pid: "75134"
history:
- at: '2026-05-11T10:18:12Z'
  event: created
agent_profile: operator
authoritative_surface: kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/
execution_mode: planning_artifact
owned_files:
- kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/wp03-repair-manifest-review.md
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

Run `spec-kitty doctor mission-state --fix` in each repo that had blockers in WP02. Review the generated manifest for each repo. Verify quarantine lists are explicit. Run repos **serially** (not in parallel) to avoid concurrent repair locks producing different manifests.

---

## Context

**Prerequisites**: WP02 complete. Consult `checklists/wp02-audit-results.md` to get the list of repos requiring repair. Only repair repos with `missions_with_teamspace_blockers > 0`.

**Env var required**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
```

**Repair contract** (from `contracts/cli-contracts.md` Contract 2):
- Must write a manifest to `.kittify/migrations/mission-state/`
- Must be deterministic and idempotent (same repo HEAD → same output)
- Must remove legacy fields: `feature_slug`, `feature_number`, `mission_key`, `legacy_aggregate_id`, `work_package_id`
- Must NOT rewrite existing valid canonical IDs
- Must NOT run if relevant git paths are dirty (unless `--allow-dirty`)

**Manifest required fields**:
- `repo_head`: git commit SHA at repair time
- `checksums`: map of affected file paths → SHA256
- `row_transformations`: count of rows modified
- `quarantine_count`: count of quarantined rows
- `quarantine_list`: list of quarantined row identifiers (if any)
- `validation_results`: summary of post-repair validation

**Serial execution**: Run T009, T010, T011 one at a time. Do not run two repair commands concurrently in different terminal tabs.

---

## T009 — Run --fix in spec-kitty-saas; review manifest

**Purpose**: Execute the deterministic repair in spec-kitty-saas and verify the manifest.

**Steps**:
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
cd /Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge/spec-kitty-saas

# Confirm clean state before repair
git status --short
# If not clean, stop and investigate

# Run repair
spec-kitty doctor mission-state --fix
```

**Verify manifest**:
```bash
# Find the manifest file
MANIFEST=$(ls -t .kittify/migrations/mission-state/*.json 2>/dev/null | head -1)
echo "Manifest: $MANIFEST"

# Validate required fields
python3 -c "
import json, sys
d = json.load(open('$MANIFEST'))
required = ['repo_head', 'checksums', 'row_transformations', 'quarantine_count', 'validation_results']
missing = [k for k in required if k not in d]
if missing:
    print(f'ERROR: Missing manifest fields: {missing}', file=sys.stderr)
    sys.exit(1)
print(f'OK: repo_head={d[\"repo_head\"][:8]}')
print(f'OK: row_transformations={d[\"row_transformations\"]}')
print(f'OK: quarantine_count={d[\"quarantine_count\"]}')
if d['quarantine_count'] > 0:
    print(f'WARNING: {d[\"quarantine_count\"]} rows quarantined: {d.get(\"quarantine_list\", [])}')
"
```

**Idempotency check** (optional but recommended):
```bash
# Run again; manifest checksums must be identical
spec-kitty doctor mission-state --fix
python3 -c "
import json
m1 = json.load(open('$MANIFEST'))
# Re-read after second run
import glob
latest = sorted(glob.glob('.kittify/migrations/mission-state/*.json'))[-1]
m2 = json.load(open(latest))
assert m1['checksums'] == m2['checksums'], 'Idempotency violation: checksums differ on second run'
print('OK: idempotent')
"
```

**Acceptance**: Manifest exists; all required fields present; `quarantine_list` is explicit (not silent); idempotency confirmed.

---

## T010 — Run --fix in spec-kitty-events; review manifest

**Purpose**: Execute the deterministic repair in spec-kitty-events and verify the manifest.

**Steps** (run after T009 completes):
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
cd /Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge/spec-kitty-events

# Confirm clean state
git status --short

# Run repair
spec-kitty doctor mission-state --fix
```

**Verify manifest**:
```bash
MANIFEST=$(ls -t .kittify/migrations/mission-state/*.json 2>/dev/null | head -1)
python3 -c "
import json, sys
d = json.load(open('$MANIFEST'))
required = ['repo_head', 'checksums', 'row_transformations', 'quarantine_count', 'validation_results']
missing = [k for k in required if k not in d]
if missing:
    print(f'ERROR: {missing}', file=sys.stderr)
    sys.exit(1)
print(f'OK: {d[\"row_transformations\"]} rows transformed, {d[\"quarantine_count\"]} quarantined')
"
```

---

## T011 — Run --fix in spec-kitty-runtime; review manifest (conditional)

**Purpose**: Execute repair in spec-kitty-runtime **only if** the WP02 T007 gate determined it has `missions_with_teamspace_blockers > 0`.

**Gate check**:
```bash
python3 -c "
import json
d = json.load(open('/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge/spec-kitty-runtime.before.audit.json'))
if d['missions_with_teamspace_blockers'] == 0:
    print('SKIP: spec-kitty-runtime has zero TeamSpace blockers — repair not needed')
    exit(0)
print(f'PROCEED: {d[\"missions_with_teamspace_blockers\"]} missions need repair')
"
```

If the gate says SKIP, mark T011 as skipped (document the zero-blocker result). If the gate says PROCEED:

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
cd /Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge/spec-kitty-runtime

git status --short  # must be clean
spec-kitty doctor mission-state --fix

MANIFEST=$(ls -t .kittify/migrations/mission-state/*.json 2>/dev/null | head -1)
python3 -c "
import json
d = json.load(open('$MANIFEST'))
print(f'Manifest: {d[\"row_transformations\"]} rows, {d[\"quarantine_count\"]} quarantined')
"
```

---

## T012 — Verify quarantine lists are explicit and reviewable

**Purpose**: For every repo that was repaired, ensure the quarantine_list is not empty when quarantine_count > 0 — rows must be explicitly listed, never silently dropped.

**Steps**:
```bash
python3 - <<'EOF'
import json, glob, os

WORKSPACE = "/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge"
repos = ["spec-kitty-saas", "spec-kitty-events", "spec-kitty-runtime"]

for repo in repos:
    manifests = sorted(glob.glob(f"{WORKSPACE}/{repo}/.kittify/migrations/mission-state/*.json"))
    if not manifests:
        print(f"{repo}: no manifest (skipped or not repaired)")
        continue
    d = json.load(open(manifests[-1]))
    qcount = d.get("quarantine_count", 0)
    qlist = d.get("quarantine_list", [])
    if qcount > 0 and not qlist:
        print(f"ERROR: {repo} quarantine_count={qcount} but quarantine_list is empty — silent drop!")
    elif qcount > 0:
        print(f"WARNING: {repo} has {qcount} quarantined rows: {qlist}")
        print(f"  → These rows must be reviewed before raising PRs")
    else:
        print(f"OK: {repo} quarantine_count=0")
EOF
```

**If any quarantine_list is non-empty**: Document each quarantined row identifier in `wp03-repair-manifest-review.md`. Quarantined rows must be explained and accepted before WP04 proceeds. The PR body (WP05) must call them out.

---

## Branch Strategy

Repair commands run in-place in each target repo (not in a worktree). After `--fix`, each target repo has modified `kitty-specs/` files and a new manifest in `.kittify/migrations/mission-state/`. These changes stay uncommitted until WP05 creates the repair branch and PR.

- Planning/base branch: `fix/teamspace-mission-state-closeout-guards` (spec-kitty repo)
- Merge target: `fix/teamspace-mission-state-closeout-guards`

---

## Definition of Done

- [ ] T009: spec-kitty-saas repaired; manifest validated; idempotency confirmed
- [ ] T010: spec-kitty-events repaired; manifest validated
- [ ] T011: spec-kitty-runtime gate evaluated; repaired if needed (or explicitly skipped)
- [ ] T012: quarantine lists verified; any quarantined rows documented and accepted
- [ ] `wp03-repair-manifest-review.md` written with manifest summaries for all repaired repos

---

## Risks

- **Concurrent repair locks**: Running two `--fix` commands simultaneously in two terminal tabs can produce non-deterministic manifests. Always run serially.
- **Dirty working tree**: `--fix` refuses to run if git paths are dirty (unless `--allow-dirty`). Do not pass `--allow-dirty` without understanding the dirty files.
- **Missing manifest fields**: If the manifest is missing required fields, the repair is incomplete. Do not proceed to WP04.
- **Non-empty quarantine list**: Quarantined rows need human review before raising PRs. They represent rows the repair could not automatically fix.

---

## Reviewer Guidance

Verify `wp03-repair-manifest-review.md` contains:
1. Manifest path and required-field check for each repaired repo
2. `row_transformations` and `quarantine_count` for each repo
3. Any quarantined row identifiers with explanation
4. Idempotency confirmation for at least one repo
5. Runtime T011 gate result (skipped or repaired)

## Activity Log

- 2026-05-11T10:28:51Z – claude:sonnet-4-6:operator:implementer – shell_pid=74843 – Started implementation via action command
- 2026-05-11T10:31:28Z – claude:sonnet-4-6:operator:implementer – shell_pid=74843 – Repair complete: all 3 repos repaired, 0 quarantined rows, manifests validated
- 2026-05-11T10:31:36Z – claude:sonnet-4-6:operator:reviewer – shell_pid=75134 – Started review via action command
- 2026-05-11T10:31:43Z – claude:sonnet-4-6:operator:reviewer – shell_pid=75134 – Review passed: all 3 manifests present, 0 quarantined rows, runtime repair confirmed, equivalent contract fields verified
