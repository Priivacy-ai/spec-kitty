---
description: Implement a research work package by conducting research and documenting findings.
---

## Research WP Implementation

**CRITICAL**: Research missions separate PLANNING ARTIFACTS from RESEARCH DELIVERABLES.

### Two Types of Artifacts (IMPORTANT)

| Type | Location | Edited Where | Purpose |
|------|----------|--------------|---------|
| **Sprint Planning** | `kitty-specs/{{feature_slug}}/research/` | Main repo | Evidence/sources for planning THIS sprint |
| **Research Deliverables** | `{{deliverables_path}}` | Worktree | Actual research outputs (your work product) |

### Where to Put Your Research

**Your research findings go in:** `{{deliverables_path}}`

This is configured in `meta.json` during planning. To find it:

```bash
# Check deliverables_path in meta.json
cat kitty-specs/{{feature_slug}}/meta.json | grep deliverables_path
```

Examples of valid deliverables paths:
- `docs/research/001-market-analysis/`
- `research-outputs/002-literature-review/`

**DO NOT** put research deliverables in:
- `kitty-specs/` (reserved for sprint planning)
- `research/` at project root (ambiguous, conflicts with kitty-specs/###/research/)

---

## Implementation Workflow

Run this command to get started:

```bash
spec-kitty agent workflow implement $ARGUMENTS --agent <your-name>
```

**CRITICAL**: You MUST provide `--agent <your-name>` to track who is implementing!

### Step 1: Navigate to Your Worktree

```bash
cd {{workspace_path}}
```

Your worktree is an isolated workspace for this WP. The deliverables path is accessible here.

### Step 2: Create Research Deliverables (In Worktree)

Create your research outputs in the deliverables path:

```bash
# Create the deliverables directory if it doesn't exist
mkdir -p {{deliverables_path}}

# Create your research files
# Examples:
# - {{deliverables_path}}/findings.md
# - {{deliverables_path}}/report.md
# - {{deliverables_path}}/data/analysis.csv
# - {{deliverables_path}}/recommendations.md
```

### Step 3: Commit Research Deliverables (In Worktree)

**BEFORE moving to for_review**, commit your research outputs:

```bash
cd {{workspace_path}}
git add {{deliverables_path}}/
git commit -m "research({{wp_id}}): <describe your research findings>"
```

Example commit messages:
- `research(WP01): Document core entities and relationships`
- `research(WP03): Add market analysis findings and recommendations`
- `research(WP05): Complete literature review synthesis`

### Step 4: Move to Review

**Only after committing**, move your WP to review:

```bash
spec-kitty agent tasks move-task {{wp_id}} --to for_review --note "Ready for review: <summary>"
```

---

## Sprint Planning Artifacts (Separate)

Planning artifacts in `kitty-specs/{{feature_slug}}/research/` are:
- `evidence-log.csv` - Evidence collected DURING PLANNING
- `source-register.csv` - Sources cited DURING PLANNING

**If you need to update these** (rare during implementation):
- They're in the main repo (sparse-excluded from worktrees)
- Edit them directly in the main repository
- Commit to main before moving status

**Most research WPs only produce deliverables, not planning updates.**

---

## Key Differences from Software-Dev

| Aspect | Software-Dev | Research |
|--------|--------------|----------|
| **Primary output** | Source code in worktree | Research docs in `deliverables_path` |
| **Commit location** | Worktree branch | Worktree branch (same!) |
| **Merges to main** | Yes, via spec-kitty merge | Yes, via spec-kitty merge |
| **Planning artifacts** | N/A | `kitty-specs/.../research/` (in main) |

### Why This Changed

Previously, research artifacts went in `kitty-specs/` which is sparse-excluded from worktrees. This meant:
- Research outputs never got merged to main
- WPs were marked "done" but work was stuck in worktrees

Now, research deliverables go in `{{deliverables_path}}` which:
- EXISTS in worktrees (not sparse-excluded)
- MERGES to main when WPs complete
- Works just like code in software-dev missions

---

## Common Mistakes to Avoid

### Mistake 1: Putting Deliverables in kitty-specs/

**Wrong**:
```bash
# Creating files in planning artifacts location
echo "# Findings" > kitty-specs/{{feature_slug}}/findings.md  # BAD!
```

**Right**:
```bash
# Creating files in deliverables path (in worktree)
echo "# Findings" > {{deliverables_path}}/findings.md  # GOOD!
```

### Mistake 2: Forgetting to Commit Before Review

**Wrong**:
```bash
# Edit deliverables
# Immediately run:
spec-kitty agent tasks move-task {{wp_id}} --to for_review  # BAD! Nothing committed!
```

**Right**:
```bash
# Edit deliverables
git add {{deliverables_path}}/
git commit -m "research({{wp_id}}): Document findings"
spec-kitty agent tasks move-task {{wp_id}} --to for_review  # GOOD!
```

### Mistake 3: Editing Planning Artifacts in Worktree

Planning artifacts (`evidence-log.csv`, `source-register.csv`) are NOT in worktrees.
If you need to update them, do so in the main repository.

---

## Parallelization

**Research WPs CAN run in parallel** (unlike old model):

Since deliverables go in `{{deliverables_path}}`, not `kitty-specs/`:
- Each WP writes to different files/subdirectories
- No merge conflicts with planning artifacts
- Works just like parallel software-dev WPs

**Exception**: If multiple WPs need to update the same deliverable file, coordinate to avoid conflicts.

---

## Completion Checklist

Before running `move-task --to for_review`:

- [ ] Research findings documented in `{{deliverables_path}}/`
- [ ] All deliverable files committed to worktree branch: `git add {{deliverables_path}}/ && git commit`
- [ ] Commit message follows format: `research({{wp_id}}): <description>`
- [ ] All subtasks marked as done: `spec-kitty agent tasks mark-status T### --status done`

---

**NOTE**: If `/spec-kitty.status` shows your WP in "doing" after you moved it to "for_review", don't panic - a reviewer may have moved it back (changes requested), or there's a sync delay. Focus on your WP.
