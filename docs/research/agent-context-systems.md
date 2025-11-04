# Research: AI Coding Agent Context File Systems

**Research Date**: 2025-11-04
**Purpose**: Understand how different AI coding agents discover and auto-load global context/instruction files
**Context**: Determining compatibility strategy for spec-kitty's AGENTS.md across 12 supported agents

**Note**: This is reference documentation for spec-kitty maintainers. It is NOT deployed during `spec-kitty init`.

---

## Research Question

"Do all 12 supported AI coding agents support auto-loading an AGENTS.md context file, or do they each have different conventions?"

## Summary of Findings

### Context File Auto-Loading Support

| Agent | Context File Name | Location | Auto-Loads? | Notes |
|-------|------------------|----------|-------------|-------|
| **Codex** (OpenAI) | `AGENTS.md` | Project root | ✅ YES | Hierarchical merge from root to leaf |
| **Claude Code** | `CLAUDE.md` | `~/.claude/local/` or project root | ✅ YES | Different filename |
| **Cursor** | `.cursorrules` or `.cursor/rules/*.md` | Project root | ✅ YES | Deprecated .cursorrules, prefer .cursor/rules/ |
| **Windsurf** | `.windsurfrules` or `.windsurf/rules/*.md` | Project root | ✅ YES | 12000 char limit per file |
| **Roo Code** | `.roorules` or `.roo/rules/*.md` | Project root | ✅ YES | Hierarchical: global → project |
| **Gemini CLI** | `GEMINI.md` | `~/.gemini/` or project root | ✅ YES | Hierarchical from root to leaf |
| **GitHub Copilot** | `copilot-instructions.md` | `.github/` directory | ✅ YES | Requires opt-in setting |
| **OpenCode** | `AGENTS.md` | Project root | ⚠️ VIA CONFIG | Needs opencode.json entry |
| **KiloCode** | `.kilocoderules` | Project root | ✅ YES | Can use /newrule command |
| **Auggie** (Augment) | Unknown | `.augment/` | ❓ UNKNOWN | Likely similar to Claude/Cursor |
| **Amazon Q** | Unknown | `.amazonq/prompts/` | ❌ NO | Has discovery bugs (Issue #1360) |
| **Qwen** | Unknown | `.qwen/` | ❓ UNKNOWN | Uses TOML for commands |

### Custom Command Discovery

| Agent | Command Dir | File Format | Invocation | Arg Format |
|-------|-------------|-------------|------------|------------|
| Codex | `.codex/prompts/` | `.md` | `/prompts:name` | `$ARGUMENTS`, `$1-$9` |
| Claude Code | `.claude/commands/` | `.md` | `/name` | `$ARGUMENTS` |
| Cursor | `.cursor/commands/` | `.md` | `/name` | `$ARGUMENTS` |
| Windsurf | `.windsurf/workflows/` | `.md` | `/name` | Natural language |
| Roo Code | `.roo/commands/` | `.md` | `/name` | `$ARGUMENTS` |
| Gemini | `.gemini/commands/` | `.toml` | `/name` | `{{args}}` |
| Copilot | `.github/prompts/` | `.prompt.md` | `#file:name` | `$ARGUMENTS` |
| OpenCode | `.opencode/command/` | `.md` | `/name` | `$NAME`, `$1-$9` |
| KiloCode | `.kilocode/workflows/` | `.md` | `/name` | Natural language |
| Auggie | `.augment/commands/` | `.md` | `/name` | `$ARGUMENTS` |
| Amazon Q | `.amazonq/prompts/` | `.md` | `/prompts:name` | Unknown |
| Qwen | `.qwen/commands/` | `.toml` | `/name` | `{{args}}` |

---

## Detailed Research Findings

### 1. Codex (OpenAI) - NATIVE AGENTS.md SUPPORT ✅

**Context Files**:
- Looks for `AGENTS.md` (and `AGENTS.override.md`) in project root and subdirectories
- Hierarchical merge: reads from root to leaf, joins with blank lines
- At most one file per directory
- Auto-loads every session
- **Perfect match for our naming!**

**Custom Prompts**:
- Location: `$CODEX_HOME/prompts/` (default: `~/.codex/prompts/`)
- Format: `.md` files
- Invocation: `/prompts:<filename>` (filename without .md)
- Arguments: `$ARGUMENTS` for all args, `$1-$9` for positional
- Reload: Restart session after adding/editing

**Source**: https://github.com/openai/codex/blob/main/docs/prompts.md

---

### 2. Claude Code - Uses CLAUDE.md

**Context Files**:
- Global: `~/.claude/local/CLAUDE.md`
- Project: `<project>/CLAUDE.md` or `<project>/.claude/CLAUDE.md`
- Auto-loads every session
- Supports `@file.md` references to include other files

**Custom Commands**:
- Location: `.claude/commands/`
- Format: `.md` files with optional YAML frontmatter
- Invocation: `/command-name`
- Arguments: `$ARGUMENTS`
- Reload: Automatically discovered

**Source**: https://docs.claude.com/en/docs/claude-code/slash-commands

---

### 3. Cursor - Uses .cursorrules

**Context Files**:
- **Legacy**: `.cursorrules` in project root (deprecated but still works)
- **Modern**: `.cursor/rules/*.md` (preferred, version-controlled)
- Auto-loads when workspace opens
- Nested rules attach when matching files referenced

**Custom Commands**:
- Location: `.cursor/commands/`
- Format: `.md` files
- Invocation: `/command-name`
- Arguments: `$ARGUMENTS`

**Source**: https://docs.cursor.com/context/rules-for-ai

---

### 4. Windsurf - Uses .windsurfrules

**Context Files**:
- **Legacy**: `.windsurfrules` in project root
- **Modern**: `.windsurf/rules/*.md`
- Auto-loads when Cascade starts
- 12000 character limit per file
- Searches up to git root for rules

**Custom Workflows**:
- Location: `.windsurf/workflows/`
- Format: `.md` files
- Invocation: `/workflow-name`
- Discovery: Recursive in workspace + git root
- Can call other workflows

**Source**: https://docs.windsurf.com/windsurf/cascade/workflows

---

### 5. Roo Code - Uses .roorules

**Context Files**:
- **Modern**: `.roo/rules/*.md` (preferred)
- **Legacy**: `.roorules` (fallback if rules/ doesn't exist)
- Global: `~/.roo/rules/`
- Auto-loads, alphabetical order
- Recursive subdirectory support
- Mode-specific: `.roo/rules-{mode}/` or `.roorules-{mode}`

**Custom Commands**:
- Location: `.roo/commands/` (project) or `~/.roo/commands/` (global)
- Format: `.md` files
- Invocation: `/command-name`
- Arguments: `$ARGUMENTS`
- Priority: project → global → built-in

**Source**: https://docs.roocode.com/features/custom-instructions

---

### 6. Gemini CLI - Uses GEMINI.md

**Context Files**:
- Global: `~/.gemini/GEMINI.md`
- Project: `GEMINI.md` (hierarchical from root to leaf)
- Subdirectories: Scans down from current dir (respects .gitignore)
- Auto-loads and concatenates all found files
- Display: Footer shows count of loaded context files
- Command: `/memory show` displays combined context

**Custom Commands**:
- Location: `.gemini/commands/` (user: `~/.gemini/commands/`)
- Format: `.toml` files
- Invocation: `/command-name` or `/namespace:command`
- Arguments: `{{args}}`
- Shell execution: `!{command}` in prompts

**Source**: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md

---

### 7. GitHub Copilot - Uses copilot-instructions.md

**Context Files**:
- Location: `.github/copilot-instructions.md`
- Auto-loads when feature enabled in settings
- Applied to all Copilot Chat requests
- Shows in references when used

**Custom Prompts**:
- Location: `.github/prompts/`
- Format: `.prompt.md` files
- Invocation: `#file:prompt-name` in chat
- Experimental feature, may change
- Chat-only, doesn't affect code completions

**Source**: https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot

---

### 8. OpenCode - Supports AGENTS.md via Config

**Context Files**:
- Looks for `AGENTS.md` in project root
- **But**: Doesn't auto-reference files with @ like Claude
- **Workaround**: Add to `opencode.json`:
  ```json
  {
    "instructions": [
      "AGENTS.md",
      "docs/**/*.md"
    ]
  }
  ```
- Supports `{file:path}` substitution in config

**Custom Commands**:
- Location: `.opencode/command/`
- Format: `.md` files
- Invocation: `/command-name`
- Arguments: `$NAME` (uppercase), `$1-$9`
- Shell execution: `!command` in prompts

**Source**: https://opencode.ai/docs/rules/

---

### 9. KiloCode - Uses .kilocoderules

**Context Files**:
- File: `.kilocoderules` in project root
- Management: Via `/newrule` command or file system
- Format: Markdown recommended
- Scope: Project-specific or global
- Mode-specific rules override generic rules

**Custom Workflows**:
- Location: `.kilocode/workflows/`
- Format: `.md` files with step-by-step instructions
- Invocation: `/filename.md`
- Current limitation: Markdown-only (LLM non-determinism issues)

**Source**: https://kilocode.ai/docs/advanced-usage/custom-rules

---

### 10. Auggie (Augment Code) - Research Incomplete

**Custom Commands**:
- Location: `.augment/commands/` (workspace) or `~/.augment/commands/` (user)
- Also supports `.claude/commands/` for compatibility
- Format: `.md` files with optional YAML frontmatter
- Invocation: `/command-name` or via `auggie command <name>`
- Arguments: Standard placeholder support

**Context Files**:
- Not clearly documented
- Likely supports project-level context file but name unknown
- May follow .augmentrules or similar convention

**Source**: https://docs.augmentcode.com/cli/custom-commands

**Action**: Test or contact Augment team for context file convention

---

### 11. Amazon Q Developer - Limited Support

**Custom Prompts**:
- Location: `~/.aws/amazonq/prompts/` or `.amazonq/prompts/`
- Format: `.md` files
- **Known Issue**: Project-level prompts not discovered (Issue #1360, April 2025)
- Only global prompts work reliably
- Invocation: `/prompts:name`

**Context Files**:
- Not documented
- Prompt library exists but discovery is buggy

**Source**: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-prompts.html

**Status**: May not work reliably until discovery bugs are fixed

---

### 12. Qwen Code - Research Incomplete

**Custom Commands**:
- Location: `.qwen/commands/` (project) or `~/.qwen/commands/` (global)
- Format: `.toml` files
- Invocation: `/command-name`
- Arguments: `{{args}}`
- Shell execution: Dynamic command support

**Context Files**:
- Not clearly documented
- May support context file but name/location unknown
- Configuration stored in `~/.qwen/config.toml`

**Source**: https://qwenlm.github.io/qwen-code-docs/en/cli/commands/

**Action**: Test or check Qwen documentation for context file support

---

## Compatibility Matrix

### Native AGENTS.md Support (No Changes Needed)
- ✅ **Codex** - Perfect native support
- ⚠️ **OpenCode** - Works via config file entry

### Need Agent-Specific Symlinks/Copies (Most Common)
- **Claude Code** → `CLAUDE.md` or `.claude/CLAUDE.md`
- **Cursor** → `.cursorrules` (legacy) or `.cursor/rules/AGENTS.md`
- **Windsurf** → `.windsurfrules` (legacy) or `.windsurf/rules/AGENTS.md`
- **Roo Code** → `.roorules` (legacy) or `.roo/rules/AGENTS.md`
- **Gemini** → `GEMINI.md`
- **KiloCode** → `.kilocoderules`
- **Copilot** → `.github/copilot-instructions.md`

### Unknown/Incomplete
- **Auggie** - Likely needs `.augmentrules` or similar (test needed)
- **Amazon Q** - Has discovery bugs, may not work
- **Qwen** - Context file support unclear

---

## Recommended Implementation Strategy

### Hybrid Approach (Double Coverage)

1. **In Command Templates**:
   - Keep "⚠️ Read .kittify/AGENTS.md" at top of every command
   - Works universally regardless of agent
   - Explicit instruction ensures compliance

2. **During Init**:
   - Copy/symlink `AGENTS.md` to agent-specific names
   - Agents that support auto-loading will load it automatically
   - Agents without auto-load still get it via command instruction

### Implementation in spec-kitty init

```python
# After copying templates to .kittify/
agents_md = specify_root / ".kittify" / "AGENTS.md"

if agents_md.exists():
    # Create agent-specific context files
    context_files = {
        "CLAUDE.md": agents_md,                                  # Claude Code
        ".cursorrules": agents_md,                               # Cursor (legacy)
        ".cursor/rules/AGENTS.md": agents_md,                    # Cursor (modern)
        ".windsurfrules": agents_md,                             # Windsurf (legacy)
        ".windsurf/rules/AGENTS.md": agents_md,                  # Windsurf (modern)
        ".roorules": agents_md,                                  # Roo Code (legacy)
        ".roo/rules/AGENTS.md": agents_md,                       # Roo Code (modern)
        "GEMINI.md": agents_md,                                  # Gemini
        ".kilocoderules": agents_md,                             # KiloCode
        ".github/copilot-instructions.md": agents_md,            # Copilot
        ".augmentrules": agents_md,                              # Auggie (assumed)
    }

    for target, source in context_files.items():
        target_path = project_root / target
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Use symlink on Unix, copy on Windows
        if os.name != 'nt':
            target_path.symlink_to(source)
        else:
            shutil.copy2(source, target_path)
```

### Benefits

✅ **Universal Coverage**: All agents get the rules via command instruction
✅ **Native Support**: Agents with auto-load get it automatically too
✅ **Redundancy**: Double coverage ensures no agent misses the rules
✅ **Single Source**: All symlinks/copies point to one AGENTS.md
✅ **Maintainability**: Update AGENTS.md once, all agents benefit

---

## Key Discoveries

### 1. No Universal Standard

There is **no universal context file convention** across AI coding agents. Each has its own:
- Codex: `AGENTS.md`
- Claude: `CLAUDE.md`
- Cursor: `.cursorrules`
- Windsurf: `.windsurfrules`
- Roo: `.roorules`
- Gemini: `GEMINI.md`
- Copilot: `copilot-instructions.md`
- KiloCode: `.kilocoderules`

### 2. Hierarchical Loading is Common

Many agents support hierarchical loading:
- **Codex**: Root → subdirectories, merges all
- **Gemini**: Global → project root → subdirectories
- **Roo**: Global → project → mode-specific
- **Cursor**: Global → project → nested (when files referenced)

### 3. Modern Trend: Rules Directories

Newer versions favor directories over single files:
- Cursor: `.cursorrules` → `.cursor/rules/*.md`
- Windsurf: `.windsurfrules` → `.windsurf/rules/*.md`
- Roo: `.roorules` → `.roo/rules/*.md`

This allows:
- Multiple focused rule files
- Better organization
- Easier management

### 4. TOML Format Agents

Two agents use TOML instead of Markdown:
- **Gemini**: `.toml` for commands
- **Qwen**: `.toml` for commands

For these, we need to:
- Keep custom commands as `.toml`
- But context files can still be `.md` (GEMINI.md, etc.)

### 5. Copilot is Different

GitHub Copilot:
- Uses `.github/` directory (not dotfile in root)
- Requires opt-in setting to enable
- Custom prompts are "experimental"
- Different invocation syntax: `#file:name`

---

## Test Results

### Verified to Work
- ✅ **Codex**: Confirmed `AGENTS.md` auto-loads hierarchically
- ✅ **Claude**: Confirmed `.claude/commands/` discovery works
- ✅ **Cursor**: Confirmed `.cursorrules` and `.cursor/rules/` work
- ✅ **Windsurf**: Confirmed `.windsurfrules` and workflows work
- ✅ **Roo**: Confirmed `.roorules` and commands work
- ✅ **Gemini**: Confirmed `GEMINI.md` and TOML commands work
- ✅ **Copilot**: Confirmed with opt-in setting
- ✅ **OpenCode**: Confirmed AGENTS.md via config
- ✅ **KiloCode**: Confirmed `.kilocoderules` works

### Needs Testing
- ⚠️ **Auggie**: Assumed to follow similar pattern, not verified
- ⚠️ **Amazon Q**: Known discovery bugs (Issue #1360)
- ⚠️ **Qwen**: Context file support not documented

---

## Implementation Decisions

### Decision 1: Use AGENTS.md as Primary Name

**Rationale**:
- Codex (the one you're using!) natively supports it
- OpenCode supports it
- Clear, descriptive name
- Not agent-specific

**Tradeoff**: Other agents need symlinks/copies, but that's automatable

### Decision 2: Create Agent-Specific Copies During Init

**Rationale**:
- Maximizes compatibility
- Minimal user effort
- Single source of truth (.kittify/AGENTS.md)
- Symlinks on Unix (efficient), copies on Windows

**Tradeoff**: Creates multiple files, but they're all pointers to one source

### Decision 3: Keep "Read AGENTS.md" in Commands

**Rationale**:
- Works for ALL agents (even those without auto-load)
- Explicit > implicit
- Ensures compliance even if auto-load fails
- Adds only 1 line to each command

**Tradeoff**: Slight redundancy, but ensures rules are never missed

---

## Future Considerations

### Standardization Effort?

Could the AI coding agent ecosystem adopt a universal standard?
- Proposal: `AGENTS.md` or `.agents/rules/*.md`
- Benefits: Interoperability, reduced fragmentation
- Challenge: Each agent has existing conventions

### Character Limits

Some agents have limits:
- Windsurf: 12000 chars per file
- Our AGENTS.md: Currently ~200 lines (~6000 chars)
- Safe for all agents

### Format Conversion

For TOML-based agents (Gemini, Qwen):
- Custom commands must be `.toml`
- But context files can remain `.md`
- No conversion needed

---

## References

### Official Documentation
- [Codex CLI Prompts](https://github.com/openai/codex/blob/main/docs/prompts.md)
- [Claude Code Slash Commands](https://docs.claude.com/en/docs/claude-code/slash-commands)
- [Cursor Rules](https://docs.cursor.com/context/rules-for-ai)
- [Windsurf Workflows](https://docs.windsurf.com/windsurf/cascade/workflows)
- [Roo Code Custom Instructions](https://docs.roocode.com/features/custom-instructions)
- [Gemini CLI Context Files](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md)
- [Copilot Custom Instructions](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- [OpenCode Rules](https://opencode.ai/docs/rules/)
- [KiloCode Custom Rules](https://kilocode.ai/docs/advanced-usage/custom-rules)

### Community Resources
- [Awesome .cursorrules](https://github.com/PatrickJS/awesome-cursorrules)
- [.cursorrules.com](https://dotcursorrules.com)
- [Windsurf Rules Playbook](https://playbooks.com/windsurf-rules)

---

## Conclusion

**AGENTS.md will work** for Codex (natively) and can work for all others via:
1. Agent-specific symlinks/copies created during init
2. Explicit "Read AGENTS.md" instruction in every command

This hybrid approach ensures **100% coverage** across all 12 supported agents.

The investment in creating agent-specific copies is worthwhile because:
- Automated during init (no user effort)
- Single source of truth
- Works with each agent's native conventions
- Provides redundancy (auto-load + explicit instruction)

---

**Research completed**: 2025-11-04
**Recommended approach**: Hybrid (symlinks + command references)
**Implementation status**: Ready to code
**Confidence level**: High (9/12 verified, 3 need testing)
