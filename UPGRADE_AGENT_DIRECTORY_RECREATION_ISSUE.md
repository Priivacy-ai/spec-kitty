# Issue: Upgrade Recreates Deleted Agent Directories

## Problem

When running `spec-kitty upgrade` from 0.11.0 → 0.11.3, deleted agent directories (`.codex/`, `.gemini/`, etc.) are recreated even though the user intentionally removed them.

## Root Cause

### The Exact Mechanism

**Location:** Two migrations that ran during your upgrade:
1. `src/specify_cli/upgrade/migrations/m_0_11_1_improved_workflow_templates.py:137-141`
2. `src/specify_cli/upgrade/migrations/m_0_11_2_improved_workflow_templates.py:137-141`

**Code that recreates directories:**

```python
# m_0_11_1_improved_workflow_templates.py (lines 134-141)
for agent_root, subdir in self.AGENT_DIRS:
    agent_dir = project_path / agent_root / subdir

    # Create agent directory if it doesn't exist (for new agents)
    if not agent_dir.exists():
        if not dry_run:
            agent_dir.mkdir(parents=True, exist_ok=True)  # ← RECREATES DIRECTORY
            changes.append(f"Created {agent_root}/{subdir} directory")
```

**AGENT_DIRS list** (lines 32-45):
```python
AGENT_DIRS = [
    (".claude", "commands"),
    (".github", "prompts"),
    (".gemini", "commands"),      # ← Recreated even if you deleted it
    (".cursor", "commands"),
    (".qwen", "commands"),
    (".opencode", "command"),
    (".windsurf", "workflows"),
    (".codex", "prompts"),         # ← Recreated even if you deleted it
    (".kilocode", "workflows"),
    (".augment", "commands"),
    (".roo", "commands"),
    (".amazonq", "prompts"),
]
```

### Why This Happens

The migration's intent was to:
1. Update existing agent slash command templates
2. Create directories for "new agents" added in later versions

**However**, the migration **cannot distinguish** between:
- "Agent directory never existed" (should create)
- "User intentionally deleted agent directory" (should NOT create)

**Result:** It treats all missing directories as "new agents" and recreates them.

### Which Migrations Do This

| Migration | Behavior | Lines |
|-----------|----------|-------|
| `m_0_11_1_improved_workflow_templates.py` | **Recreates** deleted agent dirs | 137-141 |
| `m_0_11_2_improved_workflow_templates.py` | **Recreates** deleted agent dirs | 137-141 |
| `m_0_11_3_workflow_agent_flag.py` | **Skips** if dir doesn't exist ✅ | Uses `continue` |

**Note:** m_0_11_3 has the correct behavior (skips missing dirs), but m_0_11_1 and m_0_11_2 already ran and recreated them.

---

## Step-by-Step What Happened

### Your Upgrade Sequence

1. **Before upgrade:** You had deleted `.codex/`, `.gemini/`, and other unwanted agent directories
2. **Upgrade starts:** `spec-kitty upgrade` runs from 0.11.0 → 0.11.3
3. **Migration m_0_11_1 runs:**
   - Loops through ALL 12 agent directories
   - Finds `.codex/` doesn't exist
   - Assumes it's a "new agent" added in 0.11.1
   - **Creates `.codex/prompts/` directory** ← Problem!
   - Writes updated templates to it
4. **Migration m_0_11_2 runs:**
   - Same behavior
   - Recreates any directories that were still missing
5. **Migration m_0_11_3 runs:**
   - This one has `continue` if directory doesn't exist
   - Doesn't recreate, but damage already done by m_0_11_1 and m_0_11_2

---

## Design Flaw

### Assumption

The migration assumes:
```
if agent_dir doesn't exist:
    → Must be a new agent added in this version
    → Should create directory
```

### Reality

```
if agent_dir doesn't exist:
    → Could be a new agent (should create)
    → OR user intentionally deleted it (should NOT create)
```

**The migration has no way to distinguish these cases.**

---

## Why This Design Exists

### Legitimate Use Case

When spec-kitty adds support for a **new AI agent** (e.g., Amazon Q was added later), the migration needs to create the directory for users upgrading from older versions.

**Example:**
- User has 0.10.0 (only has `.claude/`, `.cursor/`)
- Upgrade to 0.11.1 (adds support for `.amazonq/`)
- Migration creates `.amazonq/prompts/` automatically

This is actually helpful behavior **for new agents**, but problematic for **intentionally deleted agents**.

### Conflicting Requirements

1. **Create directories for new agents** (helpful for users upgrading)
2. **Don't recreate intentionally deleted directories** (respect user choices)

The current implementation chooses requirement #1, which breaks requirement #2.

---

## Possible Solutions

### Option 1: Track User Preferences

Add `.kittify/config.yaml` setting:
```yaml
agents:
  enabled:
    - claude
    - cursor
  disabled:
    - codex      # User explicitly disabled
    - gemini     # User explicitly disabled
```

Migrations check this list before creating directories.

**Pros:**
- Respects user choices
- Explicit configuration
- Allows new agents to be created while preserving deletions

**Cons:**
- Requires manual configuration
- Users must explicitly disable agents
- More complex migration logic

### Option 2: Skip Missing Directories (Simple)

Change migrations to use `continue` like m_0_11_3:
```python
if not agent_dir.exists():
    continue  # Skip if directory doesn't exist
```

**Pros:**
- Simple, clear behavior
- Respects deletions

**Cons:**
- Users upgrading don't get new agent support automatically
- Must manually create directories for new agents

### Option 3: Prompt User During Upgrade

Ask user if they want agent directories created:
```
Found missing agent directories:
  - .codex
  - .gemini
  - .amazonq

Create them? [y/N]:
```

**Pros:**
- User has full control
- Clear what's happening

**Cons:**
- Interactive (breaks automation)
- Annoying for users who upgrade frequently

### Option 4: Detect Intentional Deletion

Check if agent was ever present:
```python
# If agent directory never existed in git history, create it (new agent)
# If agent directory existed before and was deleted, don't recreate (user choice)
```

**Pros:**
- Automatic and intelligent
- Respects user choices
- Creates new agents automatically

**Cons:**
- Complex logic
- Requires git history inspection
- May not work in all scenarios

---

## Current Workaround

### For Your Specific Case

After upgrade, delete unwanted directories again:
```bash
rm -rf .codex .gemini .qwen .opencode .windsurf .kilocode .augment .roo .amazonq
```

### To Prevent This on Future Upgrades

**Option A:** Don't run upgrades (stay on current version)

**Option B:** Use `--dry-run` first, then selectively apply:
```bash
spec-kitty upgrade --dry-run  # Preview what will happen
# If it shows "Created .codex directory", skip upgrade or patch migration
```

**Option C:** Patch the migrations before upgrading:
Edit `m_0_11_1_improved_workflow_templates.py` and `m_0_11_2_improved_workflow_templates.py`:
```python
# Change line 138-141 to:
if not agent_dir.exists():
    continue  # Skip missing directories instead of creating them
```

---

## Recommendation for Spec Kitty

**Short-term fix:** Update existing migrations to use `continue` instead of `mkdir`

**Long-term solution:** Implement Option 1 (track user preferences in config.yaml)

**Example fix:**

```python
# In m_0_11_1_improved_workflow_templates.py, change:
if not agent_dir.exists():
    if not dry_run:
        agent_dir.mkdir(parents=True, exist_ok=True)
        changes.append(f"Created {agent_root}/{subdir} directory")

# To:
if not agent_dir.exists():
    continue  # Skip missing directories - respect user deletions
```

This would prevent future migrations from recreating deleted directories.

---

## Summary

**Exact mechanism:**
1. Migrations `m_0_11_1` and `m_0_11_2` loop through hardcoded `AGENT_DIRS` list
2. For each agent directory, check if it exists
3. If it doesn't exist → **assume it's a new agent** → `mkdir(parents=True)`
4. This recreates directories you intentionally deleted

**Why it exists:**
- Legitimate need to create directories for newly supported agents
- No way to distinguish "new agent" from "intentionally deleted"

**Solution:**
- Change migrations to skip missing directories (`continue`)
- OR track enabled/disabled agents in config.yaml
- OR prompt user during upgrade
