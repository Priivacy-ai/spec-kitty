# Context Switching Guide for Agents

**Version**: 1.0
**Last Updated**: 2025-11-13
**Audience**: LLM agents, automation systems
**Status**: Phase 2A Documentation

## Quick Start

When using spec-kitty scripts, always follow this pattern:

```bash
# 1. Create feature (returns JSON with paths)
$ feature_json=$(/spec-kitty.create-feature "Your feature" --json)
worktree_path=$(echo $feature_json | jq -r '.WORKTREE_PATH')

# 2. Switch to worktree
$ cd "$worktree_path"

# 3. All scripts now work in correct context
$ /spec-kitty.plan
$ /spec-kitty.tasks
$ /spec-kitty.accept
$ /spec-kitty.merge
```

## The Problem: Context Sensitivity

Spec-kitty scripts are **context-sensitive**. They need to know:

- ✅ Which feature you're working on
- ✅ Where the feature's specifications are
- ✅ What branch you're on

When context is wrong:

```bash
# Wrong context
$ pwd
/Users/robert/projects/myapp

$ /spec-kitty.accept
❌ ERROR: Feature directory not found
Expected: .../kitty-specs/NNN-feature

# Right context
$ cd .worktrees/001-my-feature
$ /spec-kitty.accept
✓ Feature validated successfully
```

## How Scripts Determine Context

### Context Detection Order

When you run a script, it checks (in order):

1. **What branch am I on?** - Check `git branch`
   - If `001-something` → Use this feature
   - If `main` → Try to auto-detect

2. **If on main, auto-detect** - Look for recent worktrees
   - Find `.worktrees/` directory
   - Pick most recently modified worktree
   - Switch to it automatically

3. **If no worktree found** - Error
   - Script can't determine which feature
   - Returns specific error with remediation

### Example: Context Detection in Action

```bash
# Scenario 1: You're in a worktree
$ cd .worktrees/001-payment/
$ git branch
* 001-payment   ← On a feature branch

$ /spec-kitty.plan
[spec-kitty] ✓ Detected feature: 001-payment
[spec-kitty] ✓ Context: .worktrees/001-payment/kitty-specs/001-payment/
[spec-kitty] ✓ Implementation plan created
```

```bash
# Scenario 2: You're on main, with recent worktree
$ cd project-root
$ git branch
* main          ← On main branch

$ /spec-kitty.merge
[spec-kitty] Auto-switching to feature worktree: .worktrees/001-payment
[spec-kitty] ✓ Detected feature: 001-payment
[spec-kitty] ✓ Merged into main
```

```bash
# Scenario 3: You're on main, no worktree
$ cd project-root
$ git branch
* main

$ /spec-kitty.plan
❌ ERROR: Unable to determine current feature

// Try one of:
1. cd .worktrees/NNN-feature
2. Create a new feature with /spec-kitty.create-feature
3. Or manually set SPEC_KITTY_AUTORETRY=1
```

## Context for Agents: Best Practices

### Rule 1: Always Use JSON Output from create-feature

```python
import json
import subprocess

# Create feature and parse JSON
result = subprocess.run(
    ['/spec-kitty.create-feature', 'My feature', '--json'],
    capture_output=True,
    text=True,
    check=True
)

feature_data = json.loads(result.stdout)
worktree_path = feature_data['WORKTREE_PATH']
feature_dir = feature_data['FEATURE_DIR']
branch_name = feature_data['BRANCH_NAME']

# Use these paths for all subsequent commands
print(f"Created feature at: {worktree_path}")
print(f"Specs directory: {feature_dir}")
```

### Rule 2: Always CD to Worktree Before Subsequent Scripts

```python
import os
import subprocess

# After creating feature, always cd to worktree
os.chdir(worktree_path)

# Now any script runs in correct context
subprocess.run(['/spec-kitty.plan'], check=True)
subprocess.run(['/spec-kitty.tasks'], check=True)
```

### Rule 3: Always Use Absolute Paths

```python
# ❌ DON'T: Use relative paths
os.chdir('.worktrees/001-feature')  # Breaks if pwd changes

# ✅ DO: Use absolute paths
os.chdir('/Users/robert/projects/myapp/.worktrees/001-feature')
```

### Rule 4: Validate Context Before Each Script

```bash
#!/bin/bash

# Validate we're in correct context
current_branch=$(git rev-parse --abbr-ref HEAD)
if [[ ! "$current_branch" =~ ^[0-9]{3}- ]]; then
    echo "ERROR: Not in a feature branch ($current_branch)"
    exit 1
fi

# Now safe to run scripts
/spec-kitty.plan
/spec-kitty.tasks
```

## Worktree Path Extraction

### From create-feature Output

```bash
# Get JSON output
output=$(/spec-kitty.create-feature "My feature" --json)

# Extract worktree path using jq
worktree=$(echo "$output" | jq -r '.WORKTREE_PATH')

# Or manually parse
worktree=$(echo "$output" | grep -o '"WORKTREE_PATH":"[^"]*"' | cut -d'"' -f4)
```

### From Directory Inspection

```bash
# If you know the branch name, find its worktree
branch_name="001-my-feature"
worktree_path="$(git rev-parse --show-toplevel)/.worktrees/$branch_name"

# Verify it exists
if [[ -d "$worktree_path" ]]; then
    cd "$worktree_path"
else
    echo "Worktree not found: $worktree_path"
    exit 1
fi
```

### Current Worktree Detection

```bash
# Get the current worktree path
current_worktree=$(git rev-parse --show-toplevel)

# Check if we're in a worktree or main
if [[ "$current_worktree" == *"/.git/worktrees/"* ]]; then
    echo "In a worktree"
else
    echo "In main worktree or regular repo"
fi
```

## Common Context Scenarios

### Scenario 1: Sequential Feature Development

Agent develops features one after another:

```python
import os
import json
import subprocess

features = [
    "Add user authentication",
    "Add rate limiting",
    "Add metrics collection"
]

for description in features:
    # 1. Create feature
    result = subprocess.run(
        ['/spec-kitty.create-feature', description, '--json'],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(result.stdout)

    # 2. Switch to worktree
    os.chdir(data['WORKTREE_PATH'])

    # 3. Plan and implement
    subprocess.run(['/spec-kitty.plan'], check=True)
    subprocess.run(['/spec-kitty.tasks'], check=True)
    # ... implement tasks ...

    # 4. Accept and merge
    subprocess.run(['/spec-kitty.accept'], check=True)
    subprocess.run(['/spec-kitty.merge'], check=True)

    # 5. Return to main for next feature
    os.chdir('..')  # Go up to main
```

### Scenario 2: Running Script from Different Directory

Agent might run script from unexpected location:

```bash
# You're here
$ pwd
/Users/robert/projects/myapp

# You run a script expecting it to work
$ /spec-kitty.accept

# What happens:
# 1. Script checks: git branch
#    → On "main" branch, not in a feature
# 2. Script checks: auto-detect worktrees
#    → Finds .worktrees/001-feature/ (most recent)
# 3. Script auto-switches context
#    → Enters .worktrees/001-feature/ directory
# 4. Script runs in correct context
#    → Success!

[spec-kitty] Auto-switching to feature worktree: .worktrees/001-feature
[spec-kitty] ✓ Feature validation complete
```

### Scenario 3: Parallel Features (Multiple Agents)

Multiple agents work on different features:

```python
# Agent 1: Working on authentication
agent1_worktree = "/path/to/project/.worktrees/001-auth"
os.chdir(agent1_worktree)
subprocess.run(['/spec-kitty.plan'], check=True)

# Agent 2: Working on payments (in parallel)
agent2_worktree = "/path/to/project/.worktrees/002-payments"
os.chdir(agent2_worktree)
subprocess.run(['/spec-kitty.plan'], check=True)

# Agent 1: Back to auth feature
os.chdir(agent1_worktree)
subprocess.run(['/spec-kitty.tasks'], check=True)
```

### Scenario 4: Handling Context Loss

Agent loses track of which feature it's working on:

```bash
# Agent is confused about context
$ pwd
/Users/robert/projects/myapp/src

# Query what context the scripts think you're in
$ /spec-kitty.check-prerequisites --json

# If this fails:
# 1. Find available worktrees
$ ls -la .worktrees/

# 2. Check which one is most recent
$ ls -lt .worktrees/

# 3. Explicitly switch to it
$ cd .worktrees/001-your-feature

# 4. Verify by checking git branch
$ git branch

# 5. Now safe to run scripts
$ /spec-kitty.plan
```

## Environment Variables for Context

### Disabling Auto-Detection

```bash
# Prevent auto-switching (for testing)
export SPEC_KITTY_AUTORETRY=skip
/spec-kitty.merge  # Won't auto-switch

# Re-enable
unset SPEC_KITTY_AUTORETRY
```

### Setting Feature Manually

```bash
# Manually set feature (if needed)
export SPECIFY_FEATURE=001-my-feature
/spec-kitty.plan  # Uses this feature

# Also works with feature name
export SPECIFY_FEATURE_NAME="My Feature"
```

## Debugging Context Issues

### Test 1: Confirm Current Branch

```bash
$ git branch
* 001-payment   ← Feature branch (good context)
  main

# If you're on main, scripts will auto-detect
# If you're on a feature, context is explicit
```

### Test 2: Check Worktree List

```bash
$ git worktree list
/Users/robert/projects/myapp (branch refs/heads/main)
.worktrees/001-auth (branch refs/heads/001-auth)
.worktrees/002-payments (branch refs/heads/002-payments)

# Shows all worktrees and their branches
```

### Test 3: Verify Prerequisites

```bash
# Check if prerequisites are satisfied
$ /spec-kitty.check-prerequisites

# With JSON (for agents)
$ /spec-kitty.check-prerequisites --json
{
  "FEATURE_DIR": "...",
  "AVAILABLE_DOCS": [...]
}
```

### Test 4: Validate Feature Directory

```bash
# Check if feature directory structure exists
$ ls -la kitty-specs/001-my-feature/
spec.md
plan.md
tasks.md

# If missing, you're not in the right context
# Solution: cd .worktrees/001-my-feature
```

## Error Messages & Remediation

### Error: "Feature directory not found"

```
❌ ERROR: Feature directory not found: .../kitty-specs/NNN-feature
  Have you run '/spec-kitty.specify' yet?
```

**Cause**: Not in a feature directory
**Fix**:
```bash
cd .worktrees/NNN-feature
```

### Error: "Unable to determine current feature"

```
❌ ERROR: Unable to determine current feature
  Expected: On a feature branch (NNN-*) or in a worktree
```

**Cause**: Not on a feature branch AND no worktree available
**Fix**:
```bash
# Either create a feature
/spec-kitty.create-feature "My feature"

# Or navigate to existing worktree
cd .worktrees/NNN-existing-feature
```

### Error: "tasks.md not found"

```
❌ ERROR: tasks.md not found
  Have you run '/spec-kitty.tasks' yet?
```

**Cause**: Tasks file doesn't exist in this feature
**Fix**:
```bash
/spec-kitty.tasks  # Create the tasks file
```

## Best Practice Checklist

For agents integrating spec-kitty:

- [ ] Always parse JSON output from `/spec-kitty.create-feature`
- [ ] Store `WORKTREE_PATH` from the JSON response
- [ ] Use `os.chdir(WORKTREE_PATH)` before subsequent scripts
- [ ] Always use absolute paths (avoid relative paths)
- [ ] Validate context with `check-prerequisites` before critical operations
- [ ] Handle auto-switching gracefully (don't assume pwd stays same)
- [ ] Log your context for debugging: `git branch`, `pwd`, `ls .worktrees/`
- [ ] Test with `--help` flag to verify scripts understand your context
- [ ] Use `--json` flag for machine-readable output
- [ ] Use `--quiet` flag to suppress logs in automation

## Integration Examples

### Python Agent

```python
#!/usr/bin/env python3
import os
import json
import subprocess
from pathlib import Path

class SpecKittyAgent:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.current_feature = None
        self.worktree_path = None

    def create_feature(self, description):
        """Create a new feature and set context"""
        os.chdir(self.project_root)

        result = subprocess.run(
            ['/spec-kitty.create-feature', description, '--json'],
            capture_output=True,
            text=True,
            check=True
        )

        data = json.loads(result.stdout)
        self.current_feature = data['BRANCH_NAME']
        self.worktree_path = data['WORKTREE_PATH']

        # Switch context
        os.chdir(self.worktree_path)

        return data

    def run_in_context(self, command):
        """Run command in current feature context"""
        if not self.worktree_path:
            raise RuntimeError("No feature context set")

        if os.getcwd() != self.worktree_path:
            os.chdir(self.worktree_path)

        return subprocess.run(command, shell=True, check=True)

# Usage
agent = SpecKittyAgent('/Users/robert/projects/myapp')
feature = agent.create_feature('Add authentication')
print(f"Created: {feature['BRANCH_NAME']}")

agent.run_in_context('/spec-kitty.plan')
agent.run_in_context('/spec-kitty.tasks')
```

### Shell Agent

```bash
#!/bin/bash
set -e

PROJECT_ROOT="/Users/robert/projects/myapp"
cd "$PROJECT_ROOT"

# Create feature
feature_json=$(/spec-kitty.create-feature "My feature" --json)
worktree_path=$(echo "$feature_json" | jq -r '.WORKTREE_PATH')
feature_name=$(echo "$feature_json" | jq -r '.BRANCH_NAME')

echo "Created feature: $feature_name"
echo "Worktree: $worktree_path"

# Switch context
cd "$worktree_path"

# Verify context
if ! git branch | grep -q "^* $feature_name"; then
    echo "ERROR: Context not set correctly"
    exit 1
fi

# Run scripts in correct context
/spec-kitty.plan
/spec-kitty.tasks
/spec-kitty.accept
/spec-kitty.merge

# Done
cd "$PROJECT_ROOT"
echo "Feature complete: $feature_name"
```

## Context Testing Checklist

Before deploying agent code:

```bash
# Test 1: Create feature and verify JSON
$ /spec-kitty.create-feature "Test feature" --json | jq .

# Test 2: Navigate to worktree
$ cd .worktrees/001-test-feature
$ pwd  # Verify you're there

# Test 3: Run script and verify context
$ /spec-kitty.check-prerequisites --json

# Test 4: Verify auto-detection from main
$ cd ../..  # Back to main
$ /spec-kitty.merge  # Should auto-detect and work

# Test 5: Cleanup
$ git worktree remove .worktrees/001-test-feature
$ rm -rf kitty-specs/001-test-feature/
```

## FAQ

### Q: Should I always use --json flag?

**A:** Yes, for agents. JSON provides structured output that's machine-parseable. Use `--quiet` to suppress logs if needed.

### Q: What if auto-detection picks the wrong worktree?

**A:** Always explicitly `cd .worktrees/NNN-feature` instead of relying on auto-detection in agents.

### Q: How do I know if I'm in the right context?

**A:** Check:
```bash
git branch           # Should show 001-NNN-* branch
pwd                  # Should show .worktrees/NNN-*/
ls kitty-specs/      # Should exist and contain NNN-*
```

### Q: Can I run scripts in parallel from different contexts?

**A:** Yes, but each process must have its own `pwd`. Use subshells or separate processes.

### Q: What if the worktree path contains spaces?

**A:** Always quote paths:
```bash
cd "$worktree_path"  # Quotes handle spaces
```

### Q: How do I switch between features?

**A:** Explicitly:
```bash
cd .worktrees/001-feature-a
/spec-kitty.plan

cd ../002-feature-b  # Switch
/spec-kitty.plan
```

## Summary

Context switching requires:

1. **Create feature** → Parse JSON for paths
2. **CD to worktree** → Use `WORKTREE_PATH` from JSON
3. **Verify context** → Check git branch, pwd, file structure
4. **Run scripts** → All scripts now work correctly
5. **Switch features** → Explicit CD between worktrees
6. **Clean up** → Remove worktree after merge

The key insight: **Scripts are context-sensitive, but context is predictable and machine-detectable**.

---

**See Also**: [WORKTREE_MODEL.md](WORKTREE_MODEL.md) for detailed worktree documentation
