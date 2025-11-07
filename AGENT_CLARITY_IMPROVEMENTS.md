# Spec-Kitty Agent Clarity Improvements

## Problem Solved
Agents were creating artifacts in the wrong location (`kitty-specs/001-feature/`) when the dashboard expected them in worktree locations (`.worktrees/001-feature/kitty-specs/001-feature/`). This was due to unclear instructions about working directory requirements.

## Changes Implemented

### 1. ✅ Standardized Location Checks in Command Templates

**Files Modified:**
- `.kittify/missions/software-dev/commands/plan.md`
- `.kittify/missions/software-dev/commands/tasks.md`

**Changes:**
Added explicit "CRITICAL: Location Requirement" section with:
- Bash script to verify worktree location
- Clear ✅/❌ indicators
- Step-by-step fix instructions
- "DO NOT PROCEED" warning for wrong location

### 2. ✅ Worktree-Aware Python CLI

**File Modified:** `src/specify_cli/__init__.py`

**Changes:**
- Added `resolve_worktree_aware_feature_dir()` function (line 855)
- Updated `research()` to use worktree-aware resolution (line 1994)
- Function intelligently detects and prefers worktree locations
- Provides console feedback about location choices

### 3. ✅ New verify-setup Command

**File Modified:** `src/specify_cli/__init__.py`

**Changes:**
- Added `verify_setup()` command (line 2678)
- Comprehensive diagnostic tool that checks:
  - Current working directory and branch
  - Worktree existence
  - Artifact location comparison (CLI vs Dashboard)
  - Existing artifacts
  - Provides specific recommendations

### 4. ✅ Improved Error Messages

**File Modified:** `scripts/bash/common.sh`

**Changes:**
- Enhanced `check_feature_branch()` function (line 75)
- Clear visual separators with emoji indicators
- Shows current location and required location
- Numbered fix steps with exact commands
- Lists available worktrees
- Points to verify-setup for debugging

## Usage Examples

### For AI Agents

When encountering spec-kitty commands, agents should:

1. **First verify location:**
```bash
if [[ $(pwd) == *"/.worktrees/"* ]]; then
    echo "✅ Ready to proceed"
else
    cd .worktrees/001-feature-name
fi
```

2. **Then run commands:**
```bash
spec-kitty research
```

### For Debugging

If artifacts don't appear in dashboard:
```bash
spec-kitty verify-setup --feature 001-feature-name
```

## Testing Verification

✅ Error messages show clear fix instructions:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ ERROR: Command run from wrong location!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current location: /Users/robert/Code/spec-kit
Current branch: main
Required: Feature branch (e.g., 001-feature-name)

🔧 TO FIX THIS ISSUE:
...
💡 TIP: Run 'spec-kitty verify-setup' to diagnose issues
```

## Impact

These changes ensure:
1. **Agents understand** they must work in worktrees
2. **Clear error messages** guide to the solution
3. **Artifacts are created** in the correct location
4. **Dashboard displays** all artifacts properly
5. **Debugging is easy** with verify-setup command

## Next Steps

The improvements are ready to use. When agents encounter spec-kitty commands, they will:
- Be explicitly told to work in worktrees
- Get clear error messages if in wrong location
- Have artifacts created in the correct location
- Be able to self-diagnose with verify-setup

This solves the artifact location mismatch issue permanently.