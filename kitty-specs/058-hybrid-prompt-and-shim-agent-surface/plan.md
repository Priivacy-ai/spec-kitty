# Implementation Plan: Hybrid Prompt and Shim Agent Surface

**Branch**: `058-hybrid-prompt-and-shim-agent-surface` | **Date**: 2026-03-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/058-hybrid-prompt-and-shim-agent-surface/spec.md`

## Summary

Restore the source → runtime → project chain for agent command files. Prompt-driven commands (specify, plan, tasks, etc.) get full prompt templates restored in the canonical source at `src/specify_cli/missions/software-dev/command-templates/`. CLI-driven commands (implement, review, merge, etc.) keep thin shims. Init installs the right type for each. A migration updates existing consumer projects.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (strict)
**Storage**: Filesystem only
**Testing**: pytest with 90%+ coverage, mypy --strict
**Target Platform**: Linux, macOS, Windows 10+
**Project Type**: Single Python package (src/specify_cli/)

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | Pass | |
| typer/rich/ruamel.yaml | Pass | No new dependencies |
| pytest 90%+ | Pass | Required for new code |
| mypy --strict | Pass | Required for new interfaces |
| TEST_FIRST directive | Noted | Tests alongside implementation |

## Project Structure

### Source Code

```
src/specify_cli/
├── missions/
│   └── software-dev/
│       └── command-templates/          # RESTORE — prompt-driven command templates
│           ├── specify.md              # Full specify workflow (from .claude/commands/ with fixes)
│           ├── plan.md                 # Full plan workflow
│           ├── tasks.md               # Full tasks workflow (with ownership guidance)
│           ├── tasks-outline.md       # Tasks outline sub-workflow
│           ├── tasks-packages.md      # Tasks packages sub-workflow
│           ├── checklist.md           # Checklist generation
│           ├── analyze.md             # Cross-artifact analysis
│           ├── research.md            # Phase 0 research
│           └── constitution.md        # Constitution workflow
│
├── shims/
│   ├── registry.py                    # MODIFY — add PROMPT_DRIVEN / CLI_DRIVEN sets
│   ├── generator.py                   # MODIFY — only generate shims for CLI_DRIVEN
│   └── entrypoints.py                 # MODIFY — dispatch CLI_DRIVEN to handlers
│
├── template/
│   └── asset_generator.py             # REUSE — generate_agent_assets() for prompt-driven
│
├── cli/commands/
│   └── init.py                        # MODIFY — hybrid install: prompts + shims
│
├── runtime/
│   └── bootstrap.py                   # NO CHANGE — ensure_runtime() already deploys missions/
│
└── upgrade/
    └── migrations/
        └── m_2_1_3_restore_prompt_commands.py  # NEW — replace thin shims with full prompts
```

### Documentation (this feature)

```
kitty-specs/058-hybrid-prompt-and-shim-agent-surface/
├── spec.md
├── plan.md              # This file
├── research.md
├── quickstart.md
└── tasks/
```

## The Source → Runtime → Project Chain (Restored)

### For Prompt-Driven Commands (9 commands)

```
src/specify_cli/missions/software-dev/command-templates/*.md   (CANONICAL SOURCE)
                    │
                    ▼  (ensure_runtime)
~/.kittify/missions/software-dev/command-templates/*.md         (GLOBAL RUNTIME)
                    │
                    ▼  (init / upgrade via generate_agent_assets)
.claude/commands/spec-kitty.specify.md                          (CONSUMER PROJECT)
.codex/prompts/spec-kitty.specify.md
.opencode/command/spec-kitty.specify.md
... (all 12 agents)
```

### For CLI-Driven Commands (7 commands)

```
src/specify_cli/shims/generator.py                             (CANONICAL SOURCE — code, not template)
                    │
                    ▼  (init / upgrade via generate_all_shims)
.claude/commands/spec-kitty.implement.md                        (CONSUMER PROJECT — thin shim)
.codex/prompts/spec-kitty.implement.md
... (all 12 agents)
```

## Command Classification

| Command | Type | Source | Install Method |
|---------|------|--------|---------------|
| specify | prompt-driven | `command-templates/specify.md` | `generate_agent_assets()` |
| plan | prompt-driven | `command-templates/plan.md` | `generate_agent_assets()` |
| tasks | prompt-driven | `command-templates/tasks.md` | `generate_agent_assets()` |
| tasks-outline | prompt-driven | `command-templates/tasks-outline.md` | `generate_agent_assets()` |
| tasks-packages | prompt-driven | `command-templates/tasks-packages.md` | `generate_agent_assets()` |
| checklist | prompt-driven | `command-templates/checklist.md` | `generate_agent_assets()` |
| analyze | prompt-driven | `command-templates/analyze.md` | `generate_agent_assets()` |
| research | prompt-driven | `command-templates/research.md` | `generate_agent_assets()` |
| constitution | prompt-driven | `command-templates/constitution.md` | `generate_agent_assets()` |
| implement | CLI-driven | `shims/generator.py` | `generate_all_shims()` |
| review | CLI-driven | `shims/generator.py` | `generate_all_shims()` |
| accept | CLI-driven | `shims/generator.py` | `generate_all_shims()` |
| merge | CLI-driven | `shims/generator.py` | `generate_all_shims()` |
| status | CLI-driven | `shims/generator.py` | `generate_all_shims()` |
| dashboard | CLI-driven | `shims/generator.py` | `generate_all_shims()` |
| tasks-finalize | CLI-driven | `shims/generator.py` | `generate_all_shims()` |

## Today's Fixes to Port

These fixes were applied to `.claude/commands/` (gitignored) and must be ported to the canonical source in `src/specify_cli/missions/software-dev/command-templates/`:

1. **"planning repository" → "project root checkout"** — all prompt files (24 occurrences across 7 files)
2. **Template path references** → "do NOT try to read template files from `.kittify/`" — specify, tasks, tasks-outline, tasks-packages, checklist
3. **Ownership metadata guidance** — tasks prompt (owned_files, authoritative_surface, execution_mode requirements + validate-only hint)
4. **`--feature` requirement note** — add to all prompts: "In repos with multiple features, always pass `--feature <slug>` to every spec-kitty command"
5. **Integration Verification section** — already in `task-prompt-template.md` (separate from command-templates, already canonical)

## Implementation Phases

### Phase 1: Restore Command Templates (prompt-driven)

Copy the 9 prompt-driven files from `.claude/commands/` to `src/specify_cli/missions/software-dev/command-templates/`, stripping:
- Any 057-specific feature slugs
- Dev-repo-specific paths
- Already applied: "project root checkout", template path fixes, ownership guidance

Verify `generate_agent_assets()` still works with the restored directory.

### Phase 2: Update Registry and Generator

Add `PROMPT_DRIVEN_COMMANDS` and `CLI_DRIVEN_COMMANDS` to `shims/registry.py`. Update `generate_all_shims()` to skip prompt-driven commands. Verify it only generates 7 shims, not 16.

### Phase 3: Update Init

Modify `init.py` to call `generate_agent_assets()` for prompt-driven commands (using the 4-tier resolution chain) and `generate_all_shims()` for CLI-driven commands only.

### Phase 4: Wire CLI-Driven Dispatch

Update `shim_dispatch()` to actually delegate CLI-driven commands to their handlers instead of just returning context.

### Phase 5: Migration

Write `m_2_1_3_restore_prompt_commands.py` that:
- Detects thin shims for prompt-driven commands
- Replaces them with full prompts from the global runtime
- Leaves CLI-driven shims untouched

### Phase 6: Test

- `spec-kitty init` in temp dir → verify hybrid install
- `spec-kitty upgrade` in spec-kitty-tracker → verify migration
- Full test suite

## Branch Contract (repeated per workflow)

- Current branch: `main`
- Planning/base: `main`
- Merge target: `main`

**Next step**: `/spec-kitty.tasks`
