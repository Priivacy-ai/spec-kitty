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

## Running Spec-Kitty Scripts (PowerShell)

### Script Location

PowerShell scripts are in: `.kittify\scripts\powershell\`

**Common scripts:**
- `Create-NewFeature.ps1` - Create a new feature
- `check-prerequisites.ps1` - Check environment and paths
- `Move-TaskToLane.ps1` - Move task between lanes
- `Set-TaskStatus.ps1` - Update task status
- `Merge-Feature.ps1` - Merge completed feature

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

**Move task:**
```powershell
.\.kittify\scripts\powershell\Move-TaskToLane.ps1 `
  -Feature "001-auth" `
  -TaskId "WP01" `
  -Lane "doing" `
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

### ❌ Don't Mix Script Types

```powershell
# WRONG (trying to run bash script in PowerShell):
.\.kittify\scripts\bash\create-new-feature.sh

# CORRECT (use PowerShell script):
.\.kittify\scripts\powershell\Create-NewFeature.ps1
```

### ❌ Don't Use Forward Slashes in Paths

```powershell
# WRONG:
cd ./.kittify/scripts/powershell

# CORRECT:
cd .\.kittify\scripts\powershell
```

Note: Git commands work with forward slashes, but PowerShell scripts expect backslashes.

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

**Check which scripts the user chose:**
Look at the template frontmatter:
```yaml
scripts:
  sh: ".kittify/scripts/bash/script-name.sh"
  ps: ".kittify/scripts/powershell/Script-Name.ps1"
```

If you see `{SCRIPT}` in the template, it will be replaced with the appropriate script path based on the user's choice.

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
