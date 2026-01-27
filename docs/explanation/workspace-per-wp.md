# Workspace-per-Work-Package Explained

*This document explains the "why" behind the workspace-per-work-package model. For step-by-step instructions, see the [how-to guides](../how-to/use-dashboard.md). For an introduction, see the [tutorials](../tutorials/claude-code-workflow.md).*

## Overview

Spec Kitty 0.11.0 introduces the workspace-per-work-package model to enable parallel multi-agent development. Instead of creating one worktree per feature where all work packages share the same workspace, each work package now gets its own isolated worktree.

**Key Change**: One git worktree per work package (instead of one per feature)

For background on how git worktrees work, see [Git Worktrees Explained](git-worktrees.md).

## Benefits

- **Parallel development**: Multiple agents work on different WPs simultaneously without conflicts
- **Isolation**: Each WP has its own workspace with separate git branch
- **Scalability**: Features with 10+ WPs can have multiple agents working in parallel

## Workflow Comparison

### Old Model (0.10.x)

```bash
# Planning creates worktree immediately
/spec-kitty.specify "My Feature"
→ Creates .worktrees/010-my-feature/
→ All WPs work in same worktree
→ Sequential development (one agent at a time)

# Implementation happens in shared worktree
cd .worktrees/010-my-feature/
/spec-kitty.implement  # Agent implements all WPs here
```

**Limitations**:
- Only one agent can work at a time (shared workspace)
- All WPs on same branch (no isolation)
- Cannot parallelize work across WPs

### New Model (0.11.0+)

```bash
# Planning happens in main repository (NO worktree created)
/spec-kitty.specify "My Feature"
→ Creates kitty-specs/010-my-feature/spec.md in main
→ Commits to main
→ NO worktree created

/spec-kitty.plan
→ Creates plan.md in main
→ Commits to main

/spec-kitty.tasks
→ LLM creates tasks.md + tasks/WP01.md, tasks/WP02.md, ... in main

spec-kitty agent feature finalize-tasks
→ Parses dependencies from tasks.md
→ Generates dependency graph in WP frontmatter
→ Validates dependencies (cycle detection)
→ Commits all to main

# Implementation creates worktrees on-demand (one per WP)
spec-kitty implement WP01
→ Creates .worktrees/010-my-feature-WP01/
→ Branches from main
→ Agent A implements WP01

spec-kitty implement WP02 --base WP01
→ Creates .worktrees/010-my-feature-WP02/
→ Branches from WP01's branch
→ Agent B implements WP02 (in parallel!)

spec-kitty implement WP03
→ Creates .worktrees/010-my-feature-WP03/
→ Branches from main (independent WP)
→ Agent C implements WP03 (also in parallel!)
```

**Benefits**:
- Three agents working simultaneously on WP01, WP02, WP03
- Each WP isolated in its own worktree with dedicated branch
- Dependencies explicitly declared in frontmatter
- Planning artifacts live in main (visible to all agents)

## Workflow Step-by-Step

### Phase 1: Planning (in main repository)

All planning commands run in your main repository. No worktrees are created during planning.

**1. Specify the feature**
```bash
/spec-kitty.specify "Add user authentication system"
```
Creates:
- `kitty-specs/011-user-authentication-system/spec.md` (committed to main)

**2. Plan the implementation**
```bash
/spec-kitty.plan
```
Creates:
- `kitty-specs/011-user-authentication-system/plan.md` (committed to main)

**3. Generate work packages**
```bash
/spec-kitty.tasks
```
LLM creates tasks.md and WP files:
- `kitty-specs/011-user-authentication-system/tasks.md`
- `kitty-specs/011-user-authentication-system/tasks/WP01-database-schema.md`
- `kitty-specs/011-user-authentication-system/tasks/WP02-api-endpoints.md`
- `kitty-specs/011-user-authentication-system/tasks/WP03-frontend-components.md`

**4. Finalize and commit tasks**
```bash
spec-kitty agent feature finalize-tasks
```
- Parses dependencies from tasks.md
- Updates WP frontmatter with `dependencies: []` field
- Validates dependency graph (cycle detection)
- Commits everything to main

Each WP file then includes dependency information in frontmatter:
```yaml
---
work_package_id: "WP02"
title: "API Endpoints"
dependencies: ["WP01"]  # WP02 depends on WP01
lane: "planned"
---
```

### Phase 2: Implementation (in separate worktrees)

Now agents create worktrees on-demand for each WP they implement.

**1. Implement WP01 (foundation)**
```bash
spec-kitty implement WP01
```
Creates:
- `.worktrees/011-user-authentication-system-WP01/`
- Branch: `011-user-authentication-system-WP01` (from main)

Agent A works in this worktree, commits to the WP01 branch.

**2. Implement WP02 (depends on WP01)**
```bash
spec-kitty implement WP02 --base WP01
```
Creates:
- `.worktrees/011-user-authentication-system-WP02/`
- Branch: `011-user-authentication-system-WP02` (from WP01's branch)
- Workspace includes WP01's code changes

Agent B works here in parallel with Agent A (different worktrees).

**3. Implement WP03 (independent)**
```bash
spec-kitty implement WP03
```
Creates:
- `.worktrees/011-user-authentication-system-WP03/`
- Branch: `011-user-authentication-system-WP03` (from main)

Agent C works here in parallel with A and B.

### Phase 3: Review and Merge

**1. Review completed WPs**
```bash
/spec-kitty.review WP01
```
Moves WP01 from `doing` → `for_review` lane. If WP02 depends on WP01, displays warning:
```
⚠️ WP02 depends on WP01
If review feedback requires changes, WP02 will need rebase
```

**2. Merge completed WPs**
```bash
# Run from any WP worktree for the feature
cd .worktrees/011-user-authentication-system-WP01/
spec-kitty merge
```
Merges all completed WP branches to main, removes worktrees.

## Dependency Syntax

### Declaring Dependencies

Dependencies are declared in each WP's frontmatter using YAML list syntax:

```yaml
---
work_package_id: "WP02"
title: "Build API"
dependencies: ["WP01"]  # This WP depends on WP01
---
```

### Multiple Dependencies

```yaml
dependencies: ["WP01", "WP03"]  # Depends on both WP01 and WP03
```

**Git limitation**: Git can only branch from ONE base commit. If a WP has multiple dependencies, use `--base` for the primary dependency and manually merge the others.

```bash
spec-kitty implement WP04 --base WP02  # Branches from WP02
cd .worktrees/011-feature-WP04/
git merge 011-feature-WP03  # Manually merge WP03
```

### No Dependencies

```yaml
dependencies: []  # Independent WP, branches from main
```

### How Dependencies Work

**At implementation time**:
- `spec-kitty implement WP02 --base WP01` creates workspace branching from WP01's branch
- WP02 workspace contains all of WP01's code changes
- WP02 builds on WP01's foundation

**During review cycles**:
- If WP01 changes after WP02 starts, WP02 needs manual rebase
- Review warnings alert you to downstream impacts

### Validation Rules

Dependencies are validated during `spec-kitty agent feature finalize-tasks`:

- ✅ Dependencies must reference valid WP IDs (WP01, WP02, etc.)
- ✅ Cannot depend on self (WP01 depending on WP01 is invalid)
- ✅ No circular dependencies (WP01 → WP02 → WP01)
- ✅ All referenced WPs must exist in the feature

**Invalid dependency examples**:
```yaml
dependencies: ["WP1"]    # Invalid: must be WP##
dependencies: ["WP99"]   # Invalid: WP99 doesn't exist
dependencies: ["WP02"]   # Invalid in WP02.md (self-dependency)
```

## Common Dependency Patterns

### Pattern 1: Linear Chain

Sequential work where each WP builds on the previous one.

```
WP01 → WP02 → WP03 → WP04
```

**Example**: Authentication feature
- WP01: Database schema
- WP02: API endpoints (depends on WP01)
- WP03: Frontend components (depends on WP02)
- WP04: Tests (depends on WP03)

**Implementation**:
```bash
spec-kitty implement WP01
spec-kitty implement WP02 --base WP01
spec-kitty implement WP03 --base WP02
spec-kitty implement WP04 --base WP03
```

**Parallelization**: Limited (each WP must wait for previous one to complete)

### Pattern 2: Fan-Out (Parallel Work)

One foundation WP with multiple independent WPs building on it.

```
        WP01
       /  |  \
    WP02 WP03 WP04
```

**Example**: E-commerce platform
- WP01: Core database models
- WP02: Product catalog API (depends on WP01)
- WP03: Shopping cart API (depends on WP01)
- WP04: User management API (depends on WP01)

**Implementation**:
```bash
spec-kitty implement WP01

# After WP01 completes, run in parallel:
spec-kitty implement WP02 --base WP01  # Agent A
spec-kitty implement WP03 --base WP01  # Agent B
spec-kitty implement WP04 --base WP01  # Agent C
```

**Parallelization**: Excellent (3 agents work simultaneously after WP01 completes)

### Pattern 3: Diamond (Multiple Dependencies)

Converging dependencies where one WP depends on multiple upstream WPs.

```
        WP01
       /    \
    WP02    WP03
       \    /
        WP04
```

**Example**: Integration layer
- WP01: Database schema
- WP02: Read API (depends on WP01)
- WP03: Write API (depends on WP01)
- WP04: Integration layer (depends on WP02 and WP03)

**Implementation**:
```bash
spec-kitty implement WP01

# Parallel:
spec-kitty implement WP02 --base WP01
spec-kitty implement WP03 --base WP01

# After both WP02 and WP03 complete:
spec-kitty implement WP04 --base WP03
cd .worktrees/###-feature-WP04/
git merge ###-feature-WP02  # Manually merge second dependency
```

**Frontmatter**:
```yaml
# WP04.md
dependencies: ["WP02", "WP03"]
```

**Note**: Git requires manual merge of second dependency. Branch from one dependency, then manually merge the other.

### Pattern 4: Independent Modules

Multiple WPs with no dependencies (fully parallel).

```
WP01   WP02   WP03   WP04
```

**Example**: Documentation updates
- WP01: Update README
- WP02: Add architecture docs
- WP03: Write API reference
- WP04: Create quickstart guide

**Implementation**:
```bash
# All run in parallel from main:
spec-kitty implement WP01  # Agent A
spec-kitty implement WP02  # Agent B
spec-kitty implement WP03  # Agent C
spec-kitty implement WP04  # Agent D
```

**Parallelization**: Maximum (4 agents work simultaneously)

## Example Scenario: Building a Feature

Let's walk through a real example using this workspace-per-WP model.

### Scenario: Add OAuth Integration

**Goal**: Add OAuth login to an existing application.

**Planning Phase**:

1. Create specification:
```bash
/spec-kitty.specify "OAuth Integration for User Login"
```

2. Create plan:
```bash
/spec-kitty.plan
```

3. Generate work packages:
```bash
/spec-kitty.tasks
```

Generated WPs with dependencies:
- **WP01**: Database migration (add oauth_tokens table)
  - `dependencies: []`
- **WP02**: OAuth provider configuration
  - `dependencies: []` (independent of WP01)
- **WP03**: Backend OAuth flow
  - `dependencies: ["WP01", "WP02"]` (needs both database and config)
- **WP04**: Frontend login button
  - `dependencies: ["WP03"]` (needs backend flow first)
- **WP05**: Tests
  - `dependencies: ["WP04"]` (needs everything)

**Implementation Phase**:

```bash
# Wave 1: Foundation (parallel)
spec-kitty implement WP01  # Agent A: Database
spec-kitty implement WP02  # Agent B: Config
# Both agents work in parallel

# Wave 2: Backend (waits for Wave 1)
# After WP01 and WP02 complete:
spec-kitty implement WP03 --base WP02
cd .worktrees/012-oauth-integration-WP03/
git merge 012-oauth-integration-WP01  # Merge second dependency
# Agent C implements backend flow

# Wave 3: Frontend (waits for Wave 2)
spec-kitty implement WP04 --base WP03
# Agent D implements UI

# Wave 4: Tests (waits for Wave 3)
spec-kitty implement WP05 --base WP04
# Agent E writes tests
```

**Timeline**:
- Traditional (sequential): ~5 time units (one WP per unit)
- Workspace-per-WP: ~3 time units (Wave 1 parallel, then Wave 2, 3, 4)

## Troubleshooting

### Error: "Legacy worktrees detected"

**Symptom**: During upgrade to 0.11.0:
```
❌ Cannot upgrade to 0.11.0
Legacy worktrees detected:
  - 008-unified-python-cli
  - 009-improved-documentation
```

**Cause**: You have in-progress features using the old worktree model.

**Solution**:
1. Complete or delete each legacy feature:
   ```bash
   # Option A: Complete the feature
   spec-kitty merge 008-unified-python-cli

   # Option B: Delete the feature
   git worktree remove .worktrees/008-unified-python-cli
   git branch -D 008-unified-python-cli
   ```

2. Verify clean state:
   ```bash
   ls .worktrees/
   # Should be empty or only show ###-feature-WP## patterns
   ```

3. Retry upgrade:
   ```bash
   pip install --upgrade spec-kitty-cli
   ```

### Error: "Base workspace does not exist"

**Symptom**: When implementing dependent WP:
```
❌ Base workspace WP01 does not exist
Implement WP01 first or remove --base flag
```

**Cause**: You're trying to implement WP02 with `--base WP01`, but WP01's worktree hasn't been created yet.

**Solution**:
1. Implement the dependency first:
   ```bash
   spec-kitty implement WP01
   ```

2. Then implement dependent WP:
   ```bash
   spec-kitty implement WP02 --base WP01
   ```

### Error: "Circular dependency detected"

**Symptom**: During `/spec-kitty.tasks` generation:
```
❌ Circular dependency detected:
WP01 → WP02 → WP03 → WP01
```

**Cause**: Your dependency declarations create a cycle (WP01 depends on WP03, which depends on WP02, which depends on WP01).

**Solution**:
1. Review your WP dependencies in tasks.md
2. Identify the circular reference
3. Remove or restructure dependencies to break the cycle
4. Re-run `/spec-kitty.tasks`

**Valid restructuring**:
```
Before (invalid):
WP01 → WP02 → WP03 → WP01  ❌

After (valid):
WP01 → WP02 → WP03  ✅
```

### Warning: "Dependent WPs need rebase"

**Symptom**: During review:
```
⚠️ WP02, WP03 depend on WP01
If review feedback requires changes, they'll need rebase
```

**Cause**: WP02 and WP03 are built on WP01's branch. If WP01 changes during review, downstream WPs need updating.

**Solution**:
1. If WP01 has no changes after review:
   - No action needed, continue as normal

2. If WP01 has changes after review:
   ```bash
   # Update WP02 to include WP01 changes
   cd .worktrees/###-feature-WP02/
   git rebase ###-feature-WP01

   # Update WP03 to include WP01 changes
   cd .worktrees/###-feature-WP03/
   git rebase ###-feature-WP01
   ```

### Issue: Multiple dependencies, git limitation

**Symptom**: WP has multiple dependencies, but `--base` only accepts one.

**Cause**: Git branches from a single commit. If WP04 depends on WP02 and WP03, you must choose one as base.

**Solution**:
```bash
# Use primary dependency as base
spec-kitty implement WP04 --base WP03

# Manually merge secondary dependency
cd .worktrees/###-feature-WP04/
git merge ###-feature-WP02
```

### Problem: Empty Branches (Missing Implementation Work)

**Symptom**: Merge-base has no work from dependencies, or dependent WP sees missing files.

**Signs**:
- `git log 017-feature-WP01` shows only planning commits, no implementation
- WP09 workspace missing files from WP01-WP08
- Warning during `spec-kitty implement`: "Dependency branch 'X' has no commits beyond main"

**Cause**: Implementation files were never committed to worktree branch.

**How it happens**:
- Agent creates files in worktree but forgets to commit
- Agent stages files (`git add`) but never commits them
- Agent completes WP without running git commit

**Solution**:
1. Check for uncommitted changes in dependency worktree:
   ```bash
   cd .worktrees/017-feature-WP01/
   git status
   ```

2. If files are untracked (`??`) or staged (`A`) but not committed:
   ```bash
   git add docs/  # or relevant path
   git commit -m "docs(WP01): Add documentation"
   ```

3. Re-create merge-base (if already created with empty branches):
   ```bash
   # Delete existing workspace with bad merge-base
   spec-kitty workspace delete WP09

   # Re-implement with updated dependencies
   spec-kitty implement WP09 --base WP01,WP02,WP03,...
   ```

**Prevention**:
- Always commit work BEFORE moving WP to "for_review"
- The `move-task` command now validates git status for both "for_review" and "done"
- If validation fails, commit your work and retry
- Review git commit instructions in your mission's implement template

**Why this matters**:
- Git branches are the mechanism for dependency sharing
- Uncommitted changes exist only in the filesystem, not git history
- Dependent WPs receive dependencies through git merge-bases
- Empty branches = lost work that needs manual recovery

## Migration from Legacy Model

See [Upgrading to 0.11.0](../how-to/upgrade-to-0-11-0.md) for detailed migration guide.

**Quick checklist**:
- [ ] Complete or delete all in-progress features (legacy worktrees)
- [ ] Verify `.worktrees/` is empty or only contains `###-feature-WP##` patterns
- [ ] Upgrade to 0.11.0: `pip install --upgrade spec-kitty-cli`
- [ ] Test with dummy feature to verify new workflow

## See Also

### Related Explanations
- [Git Worktrees Explained](git-worktrees.md) - Background on the underlying technology
- [Spec-Driven Development](spec-driven-development.md) - The methodology that enables this workflow
- [Kanban Workflow](kanban-workflow.md) - How work moves through lanes
- [AI Agent Architecture](ai-agent-architecture.md) - How multiple agents collaborate
- [Mission System](mission-system.md) - How missions shape artifacts

### Migration and Reference
- [Upgrading to 0.11.0](../how-to/upgrade-to-0-11-0.md) - Migration guide

## Try It
- [Your First Feature](../tutorials/your-first-feature.md)
- [Multi-Agent Workflow](../tutorials/multi-agent-workflow.md)

## How-To Guides
- [Implement a Work Package](../how-to/implement-work-package.md)
- [Handle Dependencies](../how-to/handle-dependencies.md)
- [Sync Workspaces](../how-to/sync-workspaces.md)
- [Parallel Development](../how-to/parallel-development.md)
- [Upgrade to 0.11.0](../how-to/upgrade-to-0-11-0.md)

## Reference
- [CLI Commands](../reference/cli-commands.md)
- [File Structure](../reference/file-structure.md)
