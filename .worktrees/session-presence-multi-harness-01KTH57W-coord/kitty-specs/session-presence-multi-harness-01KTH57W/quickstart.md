# Quickstart: Verifying Session Presence

## After Phase 1 Ships

### 1. Verify init writes orientation (new project)

```bash
# In a test project initialized with Claude Code:
spec-kitty init --ai claude

# Check CLAUDE.md section:
grep -A 10 "spec-kitty:orientation" .claude/CLAUDE.md

# Check settings.json hook:
python3 -c "
import json; d = json.load(open('.claude/settings.json'))
hooks = d.get('hooks', {}).get('SessionStart', [])
entries = [e for h in hooks for e in h.get('hooks', []) if e.get('command') == 'spec-kitty session-start']
print('Hook present:', bool(entries))
"
```

### 2. Verify session-start output (healthy project)

```bash
# From inside a spec-kitty project:
spec-kitty session-start
# Expected output starts with:
# <!-- spec-kitty:orientation -->
# **Spec Kitty vX.Y.Z** — project: <slug> (healthy)
# ...
# <!-- /spec-kitty:orientation -->
echo "Exit code: $?"  # must be 0
```

### 3. Verify session-start outside a project

```bash
cd /tmp
spec-kitty session-start
# Expected: no output
echo "Exit code: $?"  # must be 0
```

### 4. Verify idempotency

```bash
spec-kitty init --ai claude  # run a second time
# CLAUDE.md and settings.json must be byte-for-byte identical to after first run
# (or section content updated if version changed, but no duplicates)
diff <(cat .claude/CLAUDE.md) <(cat .claude/CLAUDE.md)  # trivially passes; check section count:
grep -c "spec-kitty:orientation" .claude/CLAUDE.md  # must be 1
```

### 5. Verify upgrade migration

```bash
# Simulate an existing project without session presence:
# (Remove the section and hook manually, then run upgrade)
spec-kitty upgrade
grep "spec-kitty:orientation" .claude/CLAUDE.md  # must appear
```

---

## After Phase 2 Ships

### 6. Verify multi-harness init

```bash
spec-kitty init --ai claude,cursor,copilot,codex

# Claude Code:
grep "spec-kitty:orientation" .claude/CLAUDE.md

# Cursor:
grep "spec-kitty:orientation" .cursor/rules/spec-kitty.mdc

# Copilot:
grep "spec-kitty:orientation" .github/copilot-instructions.md

# Codex (AGENTS.md):
grep "spec-kitty:orientation" AGENTS.md
```

### 7. Verify NullWriter harness is silent

```bash
spec-kitty init --ai q
# No output, no error, no new files related to session presence for Amazon Q
echo "Exit code: $?"  # must be 0
```

---

## Running the Test Suite

```bash
# All session_presence tests:
.venv/bin/pytest tests/specify_cli/session_presence/ -v

# session-start CLI tests:
.venv/bin/pytest tests/specify_cli/cli/commands/test_session_start.py -v

# Migration tests:
.venv/bin/pytest tests/specify_cli/upgrade/migrations/test_m_session_presence_claude_code.py -v
.venv/bin/pytest tests/specify_cli/upgrade/migrations/test_m_session_presence_all_harnesses.py -v
```
