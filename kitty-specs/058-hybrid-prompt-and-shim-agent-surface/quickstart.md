# Quickstart: Hybrid Prompt and Shim Agent Surface

**Feature**: 058-hybrid-prompt-and-shim-agent-surface
**Date**: 2026-03-30

## What Changed

| Before (057) | After (058) |
|---------------|-------------|
| All commands → thin 3-line shims | Prompt-driven commands → full prompts |
| `spec-kitty agent shim specify` fails (no handler) | `spec-kitty.specify` works (full prompt with workflow) |
| Planning workflows broken in consumer projects | Planning workflows work after init/upgrade |
| Source templates deleted | Source templates restored in `missions/software-dev/command-templates/` |

## Command Types

**Prompt-driven** (full prompt installed): specify, plan, tasks, tasks-outline, tasks-packages, checklist, analyze, research, constitution

**CLI-driven** (thin shim installed): implement, review, accept, merge, status, dashboard, tasks-finalize

## For New Projects

```bash
spec-kitty init
# → .claude/commands/spec-kitty.specify.md = full prompt (397 lines)
# → .claude/commands/spec-kitty.implement.md = thin shim (3 lines)
```

## For Existing Projects

```bash
spec-kitty upgrade
# → Replaces thin shims for prompt-driven commands with full prompts
# → Keeps thin shims for CLI-driven commands
```

## Source Chain

```
src/specify_cli/missions/software-dev/command-templates/specify.md    (canonical source)
    → ~/.kittify/missions/software-dev/command-templates/specify.md   (global runtime)
    → .claude/commands/spec-kitty.specify.md                          (consumer project)
```
