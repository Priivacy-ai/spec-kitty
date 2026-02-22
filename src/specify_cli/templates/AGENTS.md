# Agent Rules for Spec Kitty Projects

**⚠️ CRITICAL**: All AI agents working in this project must follow these rules.

These rules apply to **all commands** (specify, plan, research, tasks, implement, review, merge, etc.).

---

## 1. Path Reference Rule

**When you mention directories or files, provide either the absolute path or a path relative to the project root.**

✅ **CORRECT**:
- `kitty-specs/001-feature/tasks/WP01.md`
- `/Users/robert/Code/myproject/kitty-specs/001-feature/spec.md`
- `tasks/WP01.md` (relative to feature directory)

❌ **WRONG**:
- "the tasks folder" (which one? where?)
- "WP01.md" (in which lane? which feature?)
- "the spec" (which feature's spec?)

**Why**: Clarity and precision prevent errors. Never refer to a folder by name alone.

---

## 2. UTF-8 Encoding Rule

**When writing ANY markdown, JSON, YAML, CSV, or code files, use ONLY UTF-8 compatible characters.**

### What to Avoid (Will Break the Dashboard)

❌ **Windows-1252 smart quotes**: " " ' ' (from Word/Outlook/Office)
❌ **Em/en dashes and special punctuation**: — –
❌ **Copy-pasted arrows**: → (becomes illegal bytes)
❌ **Multiplication sign**: × (0xD7 in Windows-1252)
❌ **Plus-minus sign**: ± (0xB1 in Windows-1252)
❌ **Degree symbol**: ° (0xB0 in Windows-1252)
❌ **Copy/paste from Microsoft Office** without cleaning

**Real examples that crashed the dashboard:**
- "User's favorite feature" → "User's favorite feature" (smart quote)
- "Price: $100 ± $10" → "Price: $100 +/- $10"
- "Temperature: 72°F" → "Temperature: 72 degrees F"
- "3 × 4 matrix" → "3 x 4 matrix"

### What to Use Instead

✅ Standard ASCII quotes: `"`, `'`
✅ Hyphen-minus: `-` instead of en/em dash
✅ ASCII arrow: `->` instead of →
✅ Lowercase `x` for multiplication
✅ `+/-` for plus-minus
✅ ` degrees` for temperature
✅ Plain punctuation

### Safe Characters

✅ Emoji (proper UTF-8)  
✅ Accented characters typed directly: café, naïve, Zürich  
✅ Unicode math typed directly (√ ≈ ≠ ≤ ≥)  

### Copy/Paste Guidance

1. Paste into a plain-text buffer first (VS Code, TextEdit in plain mode)
2. Replace smart quotes and dashes
3. Verify no � replacement characters appear
4. Run `spec-kitty validate-encoding --feature <feature-id>` to check
5. Run `spec-kitty validate-encoding --feature <feature-id> --fix` to auto-repair

**Failure to follow this rule causes the dashboard to render blank pages.**

### Auto-Fix Available

If you accidentally introduce problematic characters:
```bash
# Check for encoding issues
spec-kitty validate-encoding --feature 001-my-feature

# Automatically fix all issues (creates .bak backups)
spec-kitty validate-encoding --feature 001-my-feature --fix

# Check all features at once
spec-kitty validate-encoding --all --fix
```

---

## 3. Context Management Rule

**Build the context you need, then maintain it intelligently.**

- Session start (0 tokens): You have zero context. Read plan.md, tasks.md, relevant artifacts.  
- Mid-session (you already read them): Use your judgment—don’t re-read everything unless necessary.  
- Never skip relevant information; do skip redundant re-reads to save tokens.  
- Rely on the steps in the command you are executing.

---

## 4. Work Quality Rule

**Produce secure, tested, documented work.**

- Follow the plan and constitution requirements.  
- Prefer existing patterns over invention.  
- Treat security warnings as fatal—fix or escalate.  
- Run all required tests before claiming work is complete.  
- Be transparent: state what you did, what you didn’t, and why.

---

## 5. Git Discipline Rule

**Keep commits clean and auditable.**

- Commit only meaningful units of work.
- Write descriptive commit messages (imperative mood).
- Do not rewrite history of shared branches.
- Keep feature branches up to date with main via merge or rebase as appropriate.
- Never commit secrets, tokens, or credentials.

---

## 6. Git Best Practices for Agent Directories

**NEVER commit agent directories to git.**

### Why Agent Directories Must Not Be Committed

Agent directories like `.claude/`, `.codex/`, `.gemini/` contain:
- Authentication tokens and API keys
- User-specific credentials (auth.json)
- Session data and conversation history
- Temporary files and caches

### What Should Be Committed

✅ **DO commit:**
- `.kittify/templates/` - Command templates (source)
- `.kittify/missions/` - Mission definitions
- `.kittify/constitution/constitution.md` - Project constitution
- `.gitignore` - With all agent directories excluded

❌ **DO NOT commit:**
- `.claude/`, `.codex/`, `.gemini/`, etc. - Agent runtime directories
- `.kittify/templates/command-templates/` - These are templates, not final commands
- Any `auth.json`, `credentials.json`, or similar files

### Automatic Protection

Spec Kitty automatically:
1. Adds all agent directories to `.gitignore` during `spec-kitty init`
2. Creates `.claudeignore` to optimize AI scanning

### Manual Verification

```bash
# Verify .gitignore protection
cat .gitignore | grep -E '\.(claude|codex|gemini|cursor)/'

# Check for accidentally staged agent files
git status | grep -E '\.(claude|codex|gemini|cursor)/'

# If you find staged agent files, unstage them:
git reset HEAD .claude/
```

### Worktree Constitution Sharing

In worktrees, `.kittify/memory/` is a symlink to the main repo's memory,
ensuring all feature branches share the same constitution.

```bash
# In a worktree, this should show a symlink:
ls -la .kittify/memory
# lrwxr-xr-x ... .kittify/memory -> ../../../.kittify/memory
```

This is intentional and correct - it ensures a single source of truth for project principles.

---

### Quick Reference

- 📁 **Paths**: Always specify exact locations.  
- 🔤 **Encoding**: UTF-8 only. Run the validator when unsure.  
- 🧠 **Context**: Read what you need; don’t forget what you already learned.  
- ✅ **Quality**: Follow secure, tested, documented practices.  
- 📝 **Git**: Commit cleanly with clear messages.
