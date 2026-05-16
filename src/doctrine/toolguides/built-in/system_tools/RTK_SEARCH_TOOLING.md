# RTK Interception and Search Tooling

RTK (Rust Token Killer) is a CLI proxy that reduces agent token consumption by
filtering noisy output from common shell commands. It is activated via a
Claude Code `PreToolUse` hook that transparently rewrites eligible commands.

This guide covers which commands RTK intercepts, which invocations break under
interception, and the correct search tooling patterns to use in worktree sessions.

---

## What RTK intercepts

When the hook is active, the following commands are transparently rewritten:

| Original command | Rewrites to |
|-----------------|-------------|
| `git status` | `rtk git status` |
| `git diff` | `rtk git diff` |
| `git log` | `rtk git log` |
| `grep …` | `rtk grep …` |
| `find …` | `rtk find …` |
| `ls …` | `rtk ls …` |

RTK wraps these and strips output noise. For common invocations this is
transparent. For advanced invocations it silently breaks them.

---

## Broken invocations — do not use

RTK's wrappers do not pass through all flags. These patterns **fail silently
or produce wrong output**:

| Broken pattern | Why it breaks |
|----------------|---------------|
| `grep --type py pattern` | RTK strips unrecognised flags |
| `grep -c pattern file` | count mode not forwarded |
| `grep -r pattern dir` | recursive mode may be stripped |
| `find . -name "*.py" -exec sed … \;` | `-exec` not supported by RTK find |
| `find . -not -name "*.pyc"` | compound predicates stripped |

---

## Correct patterns for worktree sessions

### Content search

Always use `rg` (ripgrep) directly. It bypasses RTK interception entirely.

```bash
# Find pattern in Python files
rg --type py "pattern" src/

# Find pattern, show line numbers
rg -n "constitution" src/doctrine/

# List files containing pattern
rg -l "from doctrine" src/

# Count matches per file
rg -c "import" src/specify_cli/

# Search with context lines
rg -C 3 "def emit_status" src/
```

### File discovery

Use `fd` directly, or the Glob tool. Both bypass RTK.

```bash
# Find all YAML files under doctrine
fd '\.yaml$' src/doctrine/

# Find files by name fragment
fd "constitution" src/

# Find Python files modified recently
fd '\.py$' src/ --changed-within 1d
```

Do not use `find` for file discovery inside worktrees. RTK intercepts it and
strips compound predicates (`-exec`, `-not`, `-newer`).

### Bulk file edits

Use `sed -i` with shell globs, or pipe `rg --files` into `xargs`:

```bash
# Replace a string in all Python files in a directory
sed -i 's/old_name/new_name/g' src/charter/*.py

# Replace across a subtree via rg + xargs
rg -l "old_name" src/ | xargs sed -i 's/old_name/new_name/g'
```

Do not use `find . -name "*.py" -exec sed … \;` — the `-exec` flag is not
forwarded by RTK's find wrapper.

### Escaping RTK for a single command

If you genuinely need raw tool output for a specific invocation:

```bash
rtk proxy find . -name "*.py" -exec wc -l {} \;
rtk proxy grep -c "pattern" file.txt
```

`rtk proxy` passes the command through without any filtering or rewriting.

---

## Summary

| Task | Use | Avoid |
|------|-----|-------|
| Content search | `rg pattern path` | `grep -r`, `grep --type` |
| File discovery | `fd` or Glob tool | `find . -name …` |
| Bulk edits | `sed -i` + shell glob or `rg -l \| xargs sed` | `find -exec sed` |
| Count matches | `rg -c pattern` | `grep -c` |
| Raw tool access | `rtk proxy <cmd>` | calling tool directly with advanced flags |
