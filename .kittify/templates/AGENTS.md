# Agent Rules for Spec Kitty Projects

**⚠️ CRITICAL**: All AI agents working in this project must follow these rules.

These rules apply to **all commands** (specify, plan, research, tasks, implement, review, merge, etc.).

---

## 1. Path Reference Rule

**When you mention directories or files, provide either the absolute path or a path relative to the project root.**

✅ **CORRECT**:
- `kitty-specs/001-feature/tasks/planned/WP01.md`
- `/Users/robert/Code/myproject/kitty-specs/001-feature/spec.md`
- `tasks/planned/WP01.md` (relative to feature directory)

❌ **WRONG**:
- "the tasks folder" (which one? where?)
- "WP01.md" (in which lane? which feature?)
- "the spec" (which feature's spec?)

**Why**: Clarity and precision prevent errors. Never refer to a folder by name alone.

---

## 2. UTF-8 Encoding Rule

**When writing ANY markdown, JSON, YAML, CSV, or code files, use ONLY UTF-8 compatible characters.**

### What to Avoid (Will Break the Dashboard)

❌ **Windows-1252 smart quotes**: “ ” ‘ ’ (from Word/Outlook/Office)  
❌ **Em/en dashes and special punctuation**: — –  
❌ **Copy-pasted arrows**: → (becomes illegal bytes)  
❌ **Multiplication sign**: × (0xD7 in Windows-1252)  
❌ **Copy/paste from Microsoft Office** without cleaning  

### What to Use Instead

✅ Standard ASCII quotes: `"`, `'`  
✅ Hyphen-minus: `-` instead of en/em dash  
✅ ASCII arrow: `->` instead of →  
✅ Lowercase `x` for multiplication  
✅ Plain punctuation  

### Safe Characters

✅ Emoji (proper UTF-8)  
✅ Accented characters typed directly: café, naïve, Zürich  
✅ Unicode math typed directly (√ ≈ ≠ ≤ ≥)  

### Copy/Paste Guidance

1. Paste into a plain-text buffer first (VS Code, TextEdit in plain mode)  
2. Replace smart quotes and dashes  
3. Verify no � replacement characters appear  
4. Run `python scripts/validate_encoding.py <path>` when in doubt

**Failure to follow this rule causes the dashboard to render blank pages.**

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

### Quick Reference

- 📁 **Paths**: Always specify exact locations.  
- 🔤 **Encoding**: UTF-8 only. Run the validator when unsure.  
- 🧠 **Context**: Read what you need; don’t forget what you already learned.  
- ✅ **Quality**: Follow secure, tested, documented practices.  
- 📝 **Git**: Commit cleanly with clear messages.
