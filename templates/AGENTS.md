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

❌ **Windows-1252 smart quotes**: " " ' ' (from Word/Outlook/Office)
❌ **Em dashes and special punctuation**: — –
❌ **Copy-pasted content** from Microsoft Office (contains hidden encoding)
❌ **Arrows from copy-paste**: → (byte 0x86 0x92 in Windows-1252)
❌ **Multiplication signs**: × (byte 0xd7 in Windows-1252)

### What to Use Instead

✅ **Standard ASCII quotes**: " and '
✅ **Standard dashes**: - (hyphen)
✅ **ASCII arrows**: -> (not →)
✅ **Lowercase x**: Use `x` instead of `×` for multiplication
✅ **Plain punctuation**: Keep it simple

### Special Characters That ARE Safe

✅ **Emoji** (these are proper UTF-8): 📊 🔬 📜 ✅ ❌
✅ **Accented characters** (if typed correctly): café naïve Zürich
✅ **Unicode math symbols** (if you type them directly, not copy-paste): ≈ ≠ ≤ ≥

### When Copy-Pasting from External Sources

If you're copying research citations, API docs, or academic content:

1. **Paste into a plain text editor first**
2. **Replace smart quotes** with standard quotes
3. **Replace em dashes** with hyphens
4. **Verify no � symbols** appear
5. **Then write to the file**

### Why This Matters

Files with encoding errors:
- Won't display in the dashboard (empty pages)
- Break API endpoints (return 0 bytes)
- Cause silent failures
- Waste hours of debugging time

**Prevention**: Use standard ASCII punctuation. When in doubt, keep it simple.

**Validation**: After writing files with copy-pasted content, run:
```bash
python scripts/validate_encoding.py --fix kitty-specs/<feature>/
```

**Reference**: See [.kittify/templates/common/utf8-file-writing-guidelines.md](.kittify/templates/common/utf8-file-writing-guidelines.md) for comprehensive guidance.

---

## 3. Context Management

**You are smart. Manage your own context.**

- Read what you need to understand your task
- Don't re-read files you already have in context
- Don't skip relevant information (never be lazy)
- Use your judgment about what's important

**Available documentation** (read as needed):
- `spec.md` - What the feature should do
- `plan.md` - How to build it (tech stack, architecture, file structure)
- `tasks.md` - All tasks and their dependencies
- `data-model.md` - Entities and relationships
- `contracts/` - API specifications and test requirements
- `research.md` - Technical decisions and evidence
- `quickstart.md` - Integration scenarios
- Task prompts in `tasks/*/WP*.md` - Specific work assignments

**Don't read everything** - read what's relevant to your current task.

**Don't skip critical stuff** - if the task references a contract, read that contract.

---

## 4. Work Quality Expectations

### Security
- Never introduce command injection, XSS, SQL injection, or OWASP Top 10 vulnerabilities
- Validate all inputs
- Use parameterized queries
- Escape user-provided content
- If you notice you wrote insecure code, fix it immediately

### Code Quality
- Follow patterns from plan.md
- Maintain consistency with existing codebase
- Add comments for complex logic
- Write tests when task requires them
- If tests fail, fix them - don't move tasks to for_review with failing tests

### Honesty
- If you're stuck or blocked, say so clearly
- Don't skip parts of tasks - ask for clarification
- Don't write placeholder code or TODOs unless explicitly asked
- If you don't understand something, ask before proceeding

---

## 5. Git Commit Discipline

**Every meaningful change gets committed.**

Use clear, descriptive commit messages:
```bash
git commit -m "Add user authentication endpoints"
git commit -m "Complete WP03: GeoNames parser implementation"
git commit -m "Fix encoding error in research.md"
```

**Don't**:
- Batch unrelated changes into one commit
- Use vague messages like "updates" or "fixes"
- Leave work uncommitted

---

## Summary

These five rules apply to ALL spec-kitty workflows:

1. **Path References** - Always use absolute or repo-relative paths
2. **UTF-8 Encoding** - Standard ASCII punctuation, no Office copy-paste
3. **Context Management** - Read what you need, use your judgment
4. **Work Quality** - Secure, tested, honest, complete
5. **Git Discipline** - Commit often with clear messages

Follow these and the spec-kitty workflow will be smooth and productive.

---

**This file is copied to `.kittify/AGENTS.md` during `spec-kitty init` and should be read by all agents before starting work.**
