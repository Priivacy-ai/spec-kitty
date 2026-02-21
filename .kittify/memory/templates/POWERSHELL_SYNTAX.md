# PowerShell Syntax Guide for AI Agents

**⚠️ READ THIS if you are working in a PowerShell environment**

This guide helps AI agents use correct PowerShell syntax when working with spec-kitty workflows.

---

## Quick Reference: Bash vs PowerShell

| Task | ❌ Bash (WRONG) | ✅ PowerShell (CORRECT) |
|------|-----------------|-------------------------|
| **Command chaining** | `cmd1 && cmd2` | `cmd1; cmd2` |
| **Parameter flags** | `--json --paths-only` | `-Json -PathsOnly` |
| **Script path** | `./scripts/bash/script.sh` | `..\scripts\powershell\Script.ps1` |
| **Environment variable** | `$VAR_NAME` | `$env:VAR_NAME` |
| **Current directory** | `pwd` | `Get-Location` (or `pwd` alias) |
| **List files** | `ls -la` | `Get-ChildItem` (or `ls` alias) |
| **File exists check** | `[ -f file.txt ]` | `Test-Path file.txt` |
| **Directory separator** | `/path/to/file` | `\path\to\file` |
| **Home directory** | `~/projects` | `$HOME\projects` |

---

## Location Verification (PowerShell)

**Check your current location:**
```powershell
Get-Location
git branch --show-current
```

**Expected for feature worktrees:**
- Location: `C:\Users\...\project\.worktrees\001-feature-name`
- Branch: `001-feature-name` (NOT `main`)

---

## Running Spec-Kitty Commands (PowerShell)

### Using the spec-kitty CLI

Spec-kitty uses a Python CLI that works across all platforms:

**Common commands:**
- `spec-kitty agent feature create-feature <slug>` - Create a new feature
- `spec-kitty verify-setup` - Check environment and paths
- `spec-kitty agent workflow implement <WPID> --agent <name>` - Start implementing a work package
- `spec-kitty agent workflow review <WPID> --agent <name>` - Start reviewing a work package
- `spec-kitty agent tasks move-task <WPID> --to for_review` - Complete implementation (move to review)
- `spec-kitty merge` - Merge completed feature

### Parameter Naming Convention

PowerShell uses **PascalCase** with leading dash:
- `-Json` (not `--json`)
- `-FeatureName` (not `--feature-name`)
- `-IncludeTasks` (not `--include-tasks`)
- `-RequireTasks` (not `--require-tasks`)

### Examples

**Create feature:**
```powershell
.\.kittify\scripts\powershell\Create-NewFeature.ps1 `
  -FeatureName "User Authentication" `
  -FeatureDescription "Add login and registration"
```

**Check prerequisites:**
```powershell
.\.kittify\scripts\powershell\check-prerequisites.ps1 -Json -IncludeTasks
```

**Move task to review (after implementation):**
```powershell
# Using the CLI (recommended):
spec-kitty agent tasks move-task WP01 --to for_review --note "Ready for review"

# Or using PowerShell script:
.\.kittify\scripts\powershell\Move-TaskToLane.ps1 `
  -Feature "001-auth" `
  -TaskId "WP01" `
  -Lane "for_review" `
  -ShellPid $PID `
  -Agent "claude"
```

---

## Common Mistakes to Avoid

### ❌ Don't Use Bash Operators

```powershell
# WRONG:
cd worktrees && pwd

# CORRECT:
cd worktrees; Get-Location
```

### ❌ Don't Use Bash-Style Parameters

```powershell
# WRONG:
.\check-prerequisites.ps1 --json --require-tasks

# CORRECT:
.\check-prerequisites.ps1 -Json -RequireTasks
```

### Path Separators in PowerShell

PowerShell on Windows uses backslashes for native paths:

```powershell
# WRONG (Unix-style paths on Windows):
cd ./.kittify/memory

# CORRECT (Windows-style paths):
cd .\.kittify\memory
```

Note: Git commands work with forward slashes, but native PowerShell file operations expect backslashes. The spec-kitty CLI handles this automatically.

---

## Environment Variables

**Setting variables:**
```powershell
$env:SPEC_KITTY_TEMPLATE_ROOT = "C:\path\to\spec-kitty"
```

**Reading variables:**
```powershell
echo $env:SPEC_KITTY_TEMPLATE_ROOT
```

**Checking if set:**
```powershell
if ($env:SPEC_KITTY_TEMPLATE_ROOT) {
    Write-Host "Variable is set"
}
```

---

## File Operations

**Check if file exists:**
```powershell
if (Test-Path "spec.md") {
    Write-Host "Spec exists"
}
```

**Read file:**
```powershell
$content = Get-Content "spec.md" -Raw
```

**Create directory:**
```powershell
New-Item -ItemType Directory -Path "tasks\planned" -Force
```

---

## Workflow Tips

1. **Always use full parameter names** in scripts (not abbreviations)
2. **Use semicolons** to chain commands, not `&&` or `||`
3. **Backslashes** for local paths, forward slashes OK for git operations
4. **$PID** contains current PowerShell process ID (use for --shell-pid)
5. **Tab completion** works for parameter names in PowerShell

---

## When to Use What

**Use PowerShell scripts when:**
- User specified `--script ps` during init
- You're in a Windows PowerShell terminal
- Templates reference `.ps1` files in frontmatter

**Use Bash scripts when:**
- User specified `--script sh` during init
- You're in bash/zsh/fish terminal
- Templates reference `.sh` files in frontmatter

**Using spec-kitty commands:**
All spec-kitty commands work the same way on PowerShell and Bash:
```powershell
spec-kitty agent workflow implement WP01 --agent claude  # Auto-moves to doing
spec-kitty agent tasks move-task WP01 --to for_review    # Completion step
spec-kitty verify-setup
spec-kitty dashboard
```

The CLI is cross-platform and handles path differences automatically.

---

## Debugging PowerShell Issues

**Common errors and solutions:**

1. **"Parameter cannot be found that matches parameter name"**
   - You used bash-style parameters (`--json`)
   - Fix: Use PowerShell style (`-Json`)

2. **"The term '&&' is not recognized"**
   - You used bash command chaining
   - Fix: Use semicolon (`;`) instead

3. **"Cannot find path"**
   - You used forward slashes in PowerShell path
   - Fix: Use backslashes (`\`) for local paths

4. **"Unable to import mission module"**
   - Python can't find specify_cli package
   - Check: `pip show spec-kitty-cli`
   - Fix: Reinstall or check virtual environment

---

**For full spec-kitty documentation, see the main templates and README.**