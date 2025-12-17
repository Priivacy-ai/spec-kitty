# Agent Rules for Spec Kitty Projects

**⚠️ CRITICAL**: All AI agents working in this project must follow these rules.

These rules apply to **all commands** (specify, plan, research, tasks, implement, review, merge, etc.).

---

## 1. Path Reference Rule

**When you mention directories or files, provide either the absolute path or a path relative to the project root.**

✅ **CORRECT** (v0.9.0+):
- `kitty-specs/001-feature/tasks/WP01.md`
- `/Users/robert/Code/myproject/kitty-specs/001-feature/spec.md`
- `tasks/WP01.md` (relative to feature directory)

❌ **WRONG**:
- "the tasks folder" (which one? where?)
- "WP01.md" (where? which feature?)
- "the spec" (which feature's spec?)
- `tasks/planned/WP01.md` (v0.8.x format - no longer used)
- `tasks/phase-1/WP01.md` (NO subdirectories!)

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

## 5. Task Lane Management Rule (v0.9.0+)

**v0.9.0+ FLAT STRUCTURE**: All WP files are stored directly in `tasks/` (no subdirectories).

The lane is determined **solely by the `lane:` frontmatter field**, not directory location.

**Directory structure:**
```
tasks/
├── WP01-setup.md       (lane: "planned" in frontmatter)
├── WP02-backend.md     (lane: "doing" in frontmatter)
├── WP03-frontend.md    (lane: "for_review" in frontmatter)
└── WP04-testing.md     (lane: "done" in frontmatter)
```

⚠️  **CRITICAL: NO SUBDIRECTORIES IN tasks/**

**NEVER** create subdirectories for organization:
- ❌ `tasks/phase-1/WP01.md` - WRONG
- ❌ `tasks/backend/WP02.md` - WRONG
- ❌ `tasks/planned/WP03.md` - WRONG (old v0.8.x format)
- ✅ `tasks/WP01.md` - CORRECT

Use frontmatter fields for organization:
- `phase: "Phase 1"` - NOT directories
- `component: "Backend"` - NOT directories

**To change lanes, use the update command:**
```bash
python3 .kittify/scripts/tasks/tasks_cli.py update <FEATURE> <WPID> <lane> --note "Your note"

# Examples:
python3 .kittify/scripts/tasks/tasks_cli.py update 011-my-feature WP04 doing --note "Starting implementation"
python3 .kittify/scripts/tasks/tasks_cli.py update 011-my-feature WP04 for_review --note "Ready for review"
```

The update command handles:
1. Updating the `lane:` field in frontmatter (file stays in `tasks/`)
2. Updating the `lane:` field in YAML frontmatter
3. Recording `agent` and `shell_pid` metadata
4. Appending an entry to the Activity Log
5. Staging the changes for commit

---

## 6. Git Discipline Rule

**Keep commits clean and auditable.**

- Commit only meaningful units of work.  
- Write descriptive commit messages (imperative mood).  
- Do not rewrite history of shared branches.  
- Keep feature branches up to date with main via merge or rebase as appropriate.  
- Never commit secrets, tokens, or credentials.

---

### Quick Reference

- **Paths**: Always specify exact locations.
- **Encoding**: UTF-8 only. Run the validator when unsure.
- **Context**: Read what you need; don't forget what you already learned.
- **Quality**: Follow secure, tested, documented practices.
- **Tasks**: FLAT structure only - NO subdirectories in `tasks/`. Use `tasks_cli.py update` to change lanes.
- **Git**: Commit cleanly with clear messages.
