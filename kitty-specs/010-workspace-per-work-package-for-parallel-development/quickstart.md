# Quickstart: Workspace-per-Work-Package (v0.11.0+)

**Feature**: 010-workspace-per-work-package-for-parallel-development

## What Changed in 0.11.0?

**OLD (0.10.x)**: One worktree per feature
```
/spec-kitty.specify → Creates .worktrees/010-feature/
All WPs work in same worktree
spec-kitty merge → Merges feature branch
```

**NEW (0.11.0)**: One worktree per work package
```
/spec-kitty.specify → Works in main, NO worktree
spec-kitty implement WP01 → Creates .worktrees/010-feature-WP01/
spec-kitty implement WP02 → Creates .worktrees/010-feature-WP02/
Each WP has isolated worktree
```

---

## New Workflow

### 1. Planning (in main repository)

```bash
# All planning happens in main, no worktrees created
cd /path/to/project

# Create specification
/spec-kitty.specify
→ Creates kitty-specs/011-my-feature/spec.md
→ Commits to main
→ NO WORKTREE

# Create plan
/spec-kitty.plan
→ Creates kitty-specs/011-my-feature/plan.md
→ Commits to main
→ NO WORKTREE

# Generate work packages
/spec-kitty.tasks
→ LLM creates kitty-specs/011-my-feature/tasks.md + WP01.md, WP02.md, WP03.md
→ NO WORKTREE

# Finalize tasks (parse dependencies, validate, commit)
spec-kitty agent feature finalize-tasks
→ Parses dependencies from tasks.md
→ Updates WP frontmatter with dependencies field
→ Validates graph (cycle detection)
→ Commits all to main
```

**Result**: Planning artifacts in main, visible to all future WP implementations.

### 2. Implementation (creates worktrees on-demand)

**Independent WPs (no dependencies):**
```bash
# Agent A implements WP01
spec-kitty implement WP01
→ Creates .worktrees/011-my-feature-WP01/
→ Branches from main

# Agent B implements WP03 (in parallel!)
spec-kitty implement WP03
→ Creates .worktrees/011-my-feature-WP03/
→ Branches from main
→ Agent A and B work simultaneously without conflicts
```

**Dependent WPs:**
```bash
# Agent C implements WP02 (depends on WP01)
# Must wait until WP01 workspace exists
spec-kitty implement WP02 --base WP01
→ Creates .worktrees/011-my-feature-WP02/
→ Branches from 011-my-feature-WP01 branch
→ Contains WP01's code changes
```

### 3. Merging (unchanged for now)

```bash
# When all WPs in done lane:
spec-kitty merge 011-my-feature
→ Validates all WP worktrees
→ Merges entire feature to main (all WPs together)
→ Optionally removes worktrees
```

---

## Work Package Dependencies

### How Dependencies Work

**Declared in WP frontmatter:**
```yaml
---
work_package_id: "WP02"
title: "Build API"
dependencies: ["WP01"]  # ← This WP needs WP01's code
---
```

**Generated during `/spec-kitty.tasks` and finalized by `finalize-tasks`:**
- LLM creates tasks.md with dependency descriptions
- `finalize-tasks` parses dependencies from tasks.md
- Writes `dependencies: []` field to each WP frontmatter
- Validates dependency graph (cycle detection, invalid references)
- Includes correct `spec-kitty implement` command in WP prompt

**Used during implementation:**
- `spec-kitty implement WP02 --base WP01` validates WP01 workspace exists
- Creates WP02 worktree branching from WP01's branch
- WP02 gets WP01's code changes automatically

### Common Patterns

**Pattern 1: Linear Chain**
```
WP01 → WP02 → WP03
```
```bash
spec-kitty implement WP01
spec-kitty implement WP02 --base WP01
spec-kitty implement WP03 --base WP02
```

**Pattern 2: Fan-Out (Parallel)**
```
     WP01
    /  |  \
  WP02 WP03 WP04
```
```bash
spec-kitty implement WP01
# After WP01 done, run in parallel:
spec-kitty implement WP02 --base WP01 &
spec-kitty implement WP03 --base WP01 &
spec-kitty implement WP04 --base WP01 &
```

**Pattern 3: Diamond (Complex)**
```
    WP01
    /  \
  WP02  WP03
    \  /
    WP04
```
```bash
spec-kitty implement WP01
spec-kitty implement WP02 --base WP01 &  # Parallel
spec-kitty implement WP03 --base WP01 &  # Parallel
# After both done:
spec-kitty implement WP04 --base WP03
# Note: WP04 needs WP02 also - manual merge required
cd .worktrees/011-my-feature-WP04
git merge 011-my-feature-WP02
```

---

## Review Feedback Handling (Git Limitation)

### The Problem

**Scenario:**
1. Agent A creates WP01 workspace, implements, moves to `for_review`
2. Agent B creates WP02 workspace from WP01 (`--base WP01`), starts implementing
3. Reviewer requests changes to WP01
4. Agent A modifies WP01, commits
5. **⚠️ Agent B's WP02 workspace has OLD version of WP01**

### The Solution (Manual Rebase)

**Agent B must manually rebase:**
```bash
cd .worktrees/011-my-feature-WP02
git rebase 011-my-feature-WP01
# Resolve any conflicts
git add .
git rebase --continue
```

### Warnings You'll See

**When WP01 enters review (and WP02 depends on it):**
```
⚠️ Warning: WP02 depends on WP01
If changes are requested, WP02 will need manual rebase:
  cd .worktrees/011-my-feature-WP02 && git rebase 011-my-feature-WP01
```

**When resuming WP02 after WP01 changed:**
```
⚠️ Warning: Base WP01 has changed since WP02 was created
Consider rebasing to get latest changes:
  cd .worktrees/011-my-feature-WP02 && git rebase 011-my-feature-WP01
```

### Future: jj Will Solve This

When Spec Kitty adds jj support (future feature), jj will **automatically rebase** dependent workspaces when parent changes. No manual intervention required.

---

## Upgrading to 0.11.0

### Pre-Upgrade Checklist

**Before running `pip install --upgrade spec-kitty-cli`:**

1. **Check for in-progress features:**
   ```bash
   ls .worktrees/
   # Look for directories: ###-feature (without -WP## suffix)
   ```

2. **Complete or delete legacy features:**
   ```bash
   # Option A: Merge feature to main
   spec-kitty merge 009-jujutsu-vcs

   # Option B: Delete worktree (if abandoning feature)
   git worktree remove .worktrees/009-jujutsu-vcs
   git branch -D 009-jujutsu-vcs
   ```

3. **Verify clean state:**
   ```bash
   ls .worktrees/
   # Should be empty or only have ###-feature-WP## patterns
   ```

4. **Upgrade:**
   ```bash
   pip install --upgrade spec-kitty-cli
   spec-kitty --version  # Should show 0.11.0
   ```

### If Upgrade Blocked

**Error message:**
```
❌ Cannot upgrade to 0.11.0
Legacy worktrees detected:
  - 009-jujutsu-vcs-integration-and-abstraction

Action required:
  Complete: spec-kitty merge 009-jujutsu-vcs-integration-and-abstraction
  OR Delete: git worktree remove .worktrees/009-jujutsu-vcs-integration-and-abstraction
```

**Resolution:**
- Complete features: `spec-kitty merge <feature>`
- Abandon features: `git worktree remove .worktrees/<feature>` + `git branch -D <branch>`
- Retry upgrade

### Post-Upgrade

**First new feature:**
```bash
/spec-kitty.specify
# Notice: No worktree created!
# spec.md is in main: kitty-specs/012-feature/spec.md

git log
# See commit: "Add spec for feature 012-feature"

/spec-kitty.tasks
# LLM creates tasks.md and WP files in main

spec-kitty agent feature finalize-tasks
# Parses dependencies, validates, commits to main

spec-kitty implement WP01
# NOW worktree created: .worktrees/012-feature-WP01/
```

---

## Troubleshooting

### "Base workspace WP01 does not exist"

**Problem**: Trying to implement WP02 before WP01 workspace exists

**Solution**: Implement WP01 first, or if WP02 is actually independent, remove `--base` flag

### "Circular dependency detected"

**Problem**: tasks.md has circular dependencies (WP02 → WP03 → WP02)

**Solution**: Fix tasks.md to remove cycle, ensure dependencies form a DAG

### "Directory exists but is not a valid worktree"

**Problem**: `.worktrees/011-feature-WP01/` exists but isn't a git worktree

**Solution**: Remove manually: `rm -rf .worktrees/011-feature-WP01/`, then retry

### "Legacy worktrees detected" during upgrade

**Problem**: In-progress features from 0.10.x prevent 0.11.0 upgrade

**Solution**: Complete or delete features before upgrading (see Pre-Upgrade Checklist)

---

## Commands Reference

### New in 0.11.0

```bash
# Create WP workspace (no dependencies)
spec-kitty implement WP01

# Create WP workspace (with dependencies)
spec-kitty implement WP02 --base WP01

# List legacy features (before upgrade)
spec-kitty list-legacy-features  # NEW utility command
```

### Changed in 0.11.0

```bash
# Planning commands no longer create worktrees
/spec-kitty.specify   # Works in main
/spec-kitty.plan      # Works in main
/spec-kitty.tasks     # Works in main

# Merge handles workspace-per-WP
spec-kitty merge 011-feature  # Merges all WP branches
```

### Unchanged

```bash
spec-kitty init myproject --ai claude
spec-kitty --version
git worktree list  # View all worktrees
```

---

## Real Example: How This Feature Was Built

**This workspace-per-WP feature (010) was itself built using the NEW model as a dogfooding exercise.**

### Planning Phase (in main)

All planning happened in the main repository without creating worktrees:

```bash
# Step 1: Created specification in main
/spec-kitty.specify "Workspace-per-Work-Package for Parallel Development"
→ Created kitty-specs/010-workspace-per-work-package-for-parallel-development/spec.md
→ Committed to main
→ NO worktree created

# Step 2: Created plan in main
/spec-kitty.plan
→ Created plan.md, data-model.md, quickstart.md in main
→ Committed to main

# Step 3: Generated work packages in main
/spec-kitty.tasks
→ Created tasks/WP01.md through tasks/WP10.md in main
→ Generated dependencies in each WP frontmatter
→ Committed to main

# Check git log
git log --oneline
→ 3 commits visible in main with all planning artifacts
```

### Implementation Phase (worktrees created on-demand)

Work packages were implemented in isolated worktrees with dependency-aware branching:

```bash
# Wave 1: Foundation (WP01 - independent)
spec-kitty implement WP01
→ Created .worktrees/010-workspace-per-work-package-for-parallel-development-WP01/
→ Branched from main
→ Agent A implemented dependency graph module

# Wave 2: Parallel work (WP02, WP03, WP06 - some dependent, some independent)
spec-kitty implement WP02 --base WP01
→ Created WP02 workspace from WP01's branch (includes WP01 code)
→ Agent B implemented worktree utilities (needed dependency graph)

spec-kitty implement WP03 --base WP01
→ Created WP03 workspace from WP01's branch (includes WP01 code)
→ Agent C implemented CLI commands (needed dependency graph)
→ **Parallel with WP02!**

spec-kitty implement WP06
→ Created WP06 workspace from main (independent of WP01-WP05)
→ Agent D implemented merge command updates
→ **Parallel with WP02 and WP03!**

# Wave 3: More dependencies (WP04, WP05)
spec-kitty implement WP04 --base WP02
→ WP04 needed WP02's worktree utilities
→ Also needed WP03's CLI commands (manual merge required):
cd .worktrees/010-workspace-per-wp-WP04/
git merge 010-workspace-per-wp-WP03

spec-kitty implement WP05 --base WP01
→ Frontmatter parsing needed dependency graph

# Wave 4: Agent templates (WP07)
spec-kitty implement WP07 --base WP01
→ Template updates needed dependency syntax from WP01

# Wave 5: Testing (WP08, WP09 - parallel)
spec-kitty implement WP08 --base WP07
→ Migration tests needed template updates

spec-kitty implement WP09 --base WP04
→ Integration tests needed full workflow from WP04
→ **Parallel with WP08!**

# Wave 6: Documentation (WP10)
spec-kitty implement WP10 --base WP09
→ Documentation needed everything complete
```

### What We Learned (Lessons from Dogfooding)

1. **Parallelization benefits**: 3-4 agents worked simultaneously on Waves 2 and 5, reducing time-to-completion
2. **Dependency tracking works**: WP frontmatter clearly showed which WPs needed which base
3. **Git limitation is real**: Manual merges for multi-parent dependencies (WP04) are annoying but manageable
4. **Review warnings helpful**: Warnings during review prevented downstream rebase confusion
5. **Planning in main is cleaner**: All agents saw planning artifacts without cd'ing to worktrees

### Timeline Comparison

**If built with legacy model (0.10.x)**:
- Sequential: ~10 time units (one WP per unit)
- All agents wait for shared worktree access

**Built with workspace-per-WP (0.11.0)**:
- ~6 time units (thanks to parallel waves)
- 40% faster due to parallelization

### Dependency Graph for This Feature

```
WP01 (Dependency Graph)
  ├── WP02 (Worktree Utilities)
  │   └── WP04 (Implement Command)
  │       └── WP09 (Integration Tests)
  │           └── WP10 (Documentation) ← You are here!
  ├── WP03 (CLI Commands)
  │   └── WP04 (Implement Command) [merged manually]
  ├── WP05 (Frontmatter Parsing)
  └── WP07 (Agent Templates)
      └── WP08 (Migration Tests)

WP06 (Merge Command) [independent]
```

**Parallel waves**:
- Wave 1: WP01
- Wave 2: WP02, WP03, WP06 (3 agents)
- Wave 3: WP04, WP05 (2 agents, WP05 could have been parallel but wasn't)
- Wave 4: WP07
- Wave 5: WP08, WP09 (2 agents)
- Wave 6: WP10

---

## FAQ

**Q: Can I still work on features the old way?**
A: No. Version 0.11.0 removes legacy worktree support. All new features use workspace-per-WP.

**Q: What happens to my 0.10.x features in progress?**
A: Merge or delete them before upgrading to 0.11.0. The upgrade will block if legacy worktrees exist.

**Q: Can I have 3 agents work on the same WP simultaneously?**
A: No. One workspace per WP means one agent per WP. But 3 agents can work on different WPs (WP01, WP02, WP03) simultaneously.

**Q: Do I need to manually track which WP depends on what?**
A: No. `/spec-kitty.tasks` generates the dependency information and writes it to WP frontmatter. The WP prompt files tell you the correct command to run.

**Q: What if WP04 depends on both WP02 and WP03?**
A: Use `--base WP03` (or WP02), then manually merge the other dependency in the worktree with `git merge <branch>`. Full multi-parent support requires additional design (future enhancement).

**Q: When do I get automatic rebase for dependencies?**
A: In the future jj integration feature. Git requires manual rebase, but 0.11.0 provides warnings to guide you.

**Q: Can I merge WP01 to main before WP02 is done?**
A: Not in 0.11.0. Current merge behavior is "merge entire feature" (all WPs together). Incremental WP-by-WP merging is deferred to future version.
