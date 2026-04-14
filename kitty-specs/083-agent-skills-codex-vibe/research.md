# Phase 0 Research: Argument Delivery and Skills Autocomplete Across Coding Agents

**Feature**: 083-agent-skills-codex-vibe
**Date**: 2026-04-14
**Status**: Complete — all six P0 unknowns resolved

## Why this research exists

The mission was initially scoped as "add Mistral Vibe + modernize Codex onto the same Agent Skills renderer." During plan-phase interrogation the user flagged a concern that moving `/spec-kitty.*` commands from the command-file rendering pipeline into the Agent Skills layer could **silently change how user arguments reach the prompt body**. Today, every Spec Kitty command template relies on a literal `$ARGUMENTS` (or `{{args}}` for TOML) placeholder that is **substituted before the model ever sees the prompt** — so typing `/spec-kitty.specify "build an app"` results in the literal string `"build an app"` being pasted into the template body. The user asked whether skills preserve that semantic on every agent, and — separately — whether skills participate in TUI autocomplete the way commands do.

Both questions are load-bearing for the architecture. If skills **silently** changed argument delivery or autocomplete on even one agent, shipping a "unify everything into skills" renderer would ship a UX regression in the same release that announces Mistral support. This research resolves the question authoritatively per agent, with citations.

## Six unknowns entering this phase

| # | Unknown | Status |
|---|---------|--------|
| 1 | Exact Codex `SKILL.md` frontmatter field requirements | Resolved |
| 2 | Exact Vibe `SKILL.md` frontmatter field requirements | Resolved |
| 3 | Whether a single `SKILL.md` body can satisfy both agents | Resolved |
| 4 | How user input reaches the skill body on each agent | Resolved |
| 5 | Whether moving to skills affects TUI autocomplete | Resolved |
| 6 | Whether opencode's skills layer is a viable command UX target | Resolved |

## Spec Kitty's current command-rendering baseline

Captured here as the ground truth the research is measured against.

`src/specify_cli/core/config.py:45-59` (`AGENT_COMMAND_CONFIG`):

```python
AGENT_COMMAND_CONFIG = {
    "claude":     {"dir": ".claude/commands",  "ext": "md",         "arg_format": "$ARGUMENTS"},
    "gemini":     {"dir": ".gemini/commands",  "ext": "toml",       "arg_format": "{{args}}"},
    "copilot":    {"dir": ".github/prompts",   "ext": "prompt.md",  "arg_format": "$ARGUMENTS"},
    "cursor":     {"dir": ".cursor/commands",  "ext": "md",         "arg_format": "$ARGUMENTS"},
    "qwen":       {"dir": ".qwen/commands",    "ext": "toml",       "arg_format": "{{args}}"},
    "opencode":   {"dir": ".opencode/command", "ext": "md",         "arg_format": "$ARGUMENTS"},
    "windsurf":   {"dir": ".windsurf/workflows","ext": "md",        "arg_format": "$ARGUMENTS"},
    "codex":      {"dir": ".codex/prompts",    "ext": "md",         "arg_format": "$ARGUMENTS"},
    "kilocode":   {"dir": ".kilocode/workflows","ext": "md",        "arg_format": "$ARGUMENTS"},
    "auggie":     {"dir": ".augment/commands", "ext": "md",         "arg_format": "$ARGUMENTS"},
    "roo":        {"dir": ".roo/commands",     "ext": "md",         "arg_format": "$ARGUMENTS"},
    "q":          {"dir": ".amazonq/prompts",  "ext": "md",         "arg_format": "$ARGUMENTS"},
    "antigravity":{"dir": ".agent/workflows",  "ext": "md",         "arg_format": "$ARGUMENTS"},
}
```

And the pattern inside every canonical command template (representative example from `src/specify_cli/missions/software-dev/command-templates/specify.md:28-34`):

```markdown
## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
```

The `$ARGUMENTS` token is **textually replaced** by the CLI on behalf of each agent before the file is ever loaded by that agent's runtime. Gemini's TOML entry uses `{{args}}` instead, but the same mechanic applies. The substitution is Spec Kitty's responsibility — it happens inside our template rendering and shim generation paths (`src/specify_cli/template/asset_generator.py:136` and `src/specify_cli/shims/generator.py:55-63`).

This is the baseline the research is checking against: **does every agent's skills layer preserve this literal-substitution semantic, or do we lose it when we move to skills?**

## Per-agent findings

### Claude Code

**Source of truth**: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills); [Anthropic Claude Code issue #19355](https://github.com/anthropics/claude-code/issues/19355).

**Key quotes (from the cited sources, via web search summaries)**:

> "Claude Code used to have 'commands' (`.claude/commands/*.md`) and 'skills' (`.claude/skills/*/SKILL.md`) as distinct concepts, and these have since been merged — files in either location create the same `/slash-command` interface."

> "Arguments are available via the `$ARGUMENTS` placeholder, which always expands to the full argument string as typed. Skills support indexed arguments using shell-style quoting, so wrap multi-word values in quotes to pass them as a single argument."

But: Anthropic's own open issue [#19355](https://github.com/anthropics/claude-code/issues/19355), fetched directly, explicitly states:

> "Since the `SlashCommand` tool and `Agent Skills` have been merged into a single `Skill` tool (as of v2.1.3), there is significant ambiguity regarding argument parsing for `SKILL.md` files."

> "It is unclear if model-invoked Skills (which are now handled by the same underlying tool as Slash Commands) support the same `$1`, `$2` positional substitutions that Slash Commands do."

**Interpretation**:
- **`$ARGUMENTS` in skills on Claude**: works. The placeholder is substituted and skills and commands are unified at the tool layer.
- **Positional `$1`, `$2` in skills on Claude**: ambiguous per Anthropic's own open issue. Not reliable for Spec Kitty to depend on.
- **Autocomplete**: Both `.claude/commands/*.md` and `.claude/skills/*/SKILL.md` surface as `/slash-command` entries in Claude Code's TUI.

**Spec Kitty implication**: Claude is a command-layer agent today with a fully working `$ARGUMENTS` pipeline. We keep it on command-file rendering. No change required by this mission.

### OpenAI Codex

**Sources of truth**: [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills); [developers.openai.com/codex/cli/slash-commands](https://developers.openai.com/codex/cli/slash-commands); [developers.openai.com/codex/custom-prompts](https://developers.openai.com/codex/custom-prompts); [blog.fsck.com/2025/12/19/codex-skills](https://blog.fsck.com/2025/12/19/codex-skills/); [github.com/openai/codex/blob/main/docs/skills.md](https://github.com/openai/codex/blob/main/docs/skills.md); [simonw.substack.com/p/openai-are-quietly-adopting-skills](https://simonw.substack.com/p/openai-are-quietly-adopting-skills).

**Key quotes (from the cited sources, via web search summaries)**:

> "At its simplest, a skill is a directory that contains a SKILL.md file that must start with YAML frontmatter containing required metadata: `name` and `description`. Skills are stored in `~/.codex/skills/**/SKILL.md`, and only files named exactly SKILL.md are recognized."

> "You can invoke a skill explicitly by typing `$skill-name` (for example, `$skill-installer`), or let Codex select a skill automatically based on your prompt."

> "For passing arguments through the CLI API, when using the turn/start method, you can include the input text with the skill name (e.g., `$skill-creator Add a new skill for triaging flaky CI`) and optionally include a skill input item with the skill name and path to avoid latency."

And critically, OpenAI's custom-prompts page:

> "Custom prompts are deprecated — use skills for reusable instructions that Codex can invoke explicitly or implicitly."

**Interpretation**:
- **`SKILL.md` frontmatter for Codex**: `name` and `description` required; other fields optional.
- **`$ARGUMENTS`-style substitution on Codex**: **not documented**. The documented mechanism is that the user types `$skill-name <free-form text>` and the free-form text becomes **turn content** — it is visible to the model as part of the invocation message, not spliced into the `SKILL.md` body by the runtime.
- **Autocomplete**: `/skills` surface and `$skill-name` mention both participate in Codex's slash-command autocomplete.
- **`.codex/prompts/` path**: deprecated; moving off it is official guidance.

**Spec Kitty implication**: This is the whole reason the mission expanded. Codex is **no longer a command-layer agent** — its command layer is officially deprecated. And its skills layer does **not** do `$ARGUMENTS` substitution. If we move Codex's Spec Kitty commands to skills naively, the `$ARGUMENTS` token in every template body would be delivered to the model as a literal `$ARGUMENTS` string. The skill body must instead **instruct the model to treat the invocation turn's free-form text as the user input**.

### Mistral Vibe

**Sources of truth (official)**: [docs.mistral.ai/mistral-vibe/agents-skills](https://docs.mistral.ai/mistral-vibe/agents-skills); [docs.mistral.ai/mistral-vibe/introduction](https://docs.mistral.ai/mistral-vibe/introduction); [docs.mistral.ai/mistral-vibe/introduction/configuration](https://docs.mistral.ai/mistral-vibe/introduction/configuration); [github.com/mistralai/mistral-vibe](https://github.com/mistralai/mistral-vibe); [help.mistral.ai/en/articles/496007-get-started-with-mistral-vibe](https://help.mistral.ai/en/articles/496007-get-started-with-mistral-vibe).

**Sources of truth (community)**: [deepwiki.com/mistralai/mistral-vibe/3.8-skills-and-subagents](https://deepwiki.com/mistralai/mistral-vibe/3.8-skills-and-subagents); [deepwiki.com/mistralai/mistral-vibe/2.3-quick-start-guide](https://deepwiki.com/mistralai/mistral-vibe/2.3-quick-start-guide); [datacamp.com/blog/mistral-vibe-2-0](https://www.datacamp.com/blog/mistral-vibe-2-0).

**Key quotes (from the cited sources, via web search summaries)**:

> "Skills are defined in directories with a SKILL.md file containing metadata in YAML frontmatter. Skill discovery paths include: Global: `~/.vibe/skills/`, Local project: `.vibe/skills/`, and Custom: Configure in `config.toml`."

> "Skills are structured with YAML frontmatter containing fields like `name`, `description`, `license`, `compatibility`, `user-invocable` (boolean), and `allowed-tools` (list of accessible tools)."

> "Custom slash commands appear in the autocompletion menu alongside built-in commands."

> "When invoked, the skill's Markdown content is loaded and injected into the conversation, potentially with variable substitution or parameterization." — (from DeepWiki's community doc; notably hedged with *potentially*)

And from a direct WebFetch of the official `docs.mistral.ai/mistral-vibe/agents-skills` page:

> "Based on the provided documentation, there is **no information about how Mistral Vibe skills receive user arguments when invoked as slash commands**. The page documents skill structure, discovery, and management, but does not explain: Argument passing mechanisms, Placeholder substitution systems like `$ARGUMENTS`, How text following a slash command is delivered to skills."

**Interpretation**:
- **`SKILL.md` frontmatter for Vibe**: `name` and `description` required; `license`, `compatibility`, `user-invocable`, `allowed-tools` optional.
- **`$ARGUMENTS`-style substitution on Vibe**: **officially undocumented.** DeepWiki's community page hedges with "potentially with variable substitution or parameterization," and Mistral's own docs are silent. We cannot stake Spec Kitty's argument delivery on a mechanism the vendor has not committed to.
- **Autocomplete**: custom slash commands from skills **do** appear in Vibe's autocomplete menu per official docs.

**Spec Kitty implication**: Vibe lands in the same bucket as Codex for this mission. The skill body must be written so it still works even if Vibe does **no** substitution — in which case the model reads the literal `SKILL.md` body as context and treats the user's invocation text as the turn content. If Vibe later turns out to substitute `$ARGUMENTS`, that is additive and harmless to our chosen design. The decision is driven by the worst-case semantic, not the best-case.

### Google Gemini CLI

**Sources of truth**: [github.com/google-gemini/gemini-cli/blob/main/docs/cli/custom-commands.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/custom-commands.md); [geminicli.com/docs/cli/custom-commands](https://geminicli.com/docs/cli/custom-commands/); [cloud.google.com/blog/topics/developers-practitioners/gemini-cli-custom-slash-commands](https://cloud.google.com/blog/topics/developers-practitioners/gemini-cli-custom-slash-commands).

**Key quotes (from the cited sources, via web search summaries)**:

> "The foundation of custom slash commands is rooted in `.toml` files. Your command definition files must be written in the TOML format and use the `.toml` file extension."

> "If your prompt contains the special placeholder `{{args}}`, the CLI will replace that placeholder with the text the user typed after the command name."

> "User commands (global) are located in `~/.gemini/commands/`. Project commands (local) are located in `<your-project-root>/.gemini/commands/`."

**Interpretation**:
- **Command layer for Gemini**: fully working, with `{{args}}` substitution — our existing pipeline is correct and matches Gemini's contract exactly.
- **Skills layer for Gemini**: not documented as a primary command surface at the time of this research. Gemini's user-facing mechanism for reusable prompts is custom commands, not skills.

**Spec Kitty implication**: No change. Gemini keeps its TOML `{{args}}` pipeline.

### opencode

**Sources of truth**: [opencode.ai/docs/commands](https://opencode.ai/docs/commands/); [opencode.ai/docs/skills](https://opencode.ai/docs/skills/); [opencode.ai/docs/config](https://opencode.ai/docs/config/); [github.com/code-yeongyu/oh-my-openagent/issues/640](https://github.com/code-yeongyu/oh-my-openagent/issues/640) (cited as evidence of the known argument-delivery bug when skills are invoked as slash commands).

**Key quotes (from the cited sources, via web search summaries)**:

> "Custom commands let you specify a prompt you want to run when that command is executed in the TUI. Create markdown files in the `commands/` directory to define custom commands. Templates support placeholders (`$ARGUMENTS`, `$1`, `$2`...), shell interpolation (`!cmd`), and file inclusion (`@filename`)."

> "Agent skills let OpenCode discover reusable instructions from your repo or home directory. Skills are loaded on-demand via the native skill tool — agents see available skills and can load the full content when needed."

> "For project-local paths, OpenCode walks up from your current working directory until it reaches the git worktree. It loads any matching `skills/*/SKILL.md` in `.opencode/` and any matching `.claude/skills/*/SKILL.md` or `.agents/skills/*/SKILL.md` along the way."

And the open upstream bug:

> "Issue #640: Skills invoked as slash commands without arguments ignore skill instructions." (title of the cited issue in `oh-my-openagent`)

**Interpretation**:
- **Command layer for opencode**: fully working, with `$ARGUMENTS`, positional, shell interpolation, and file inclusion.
- **Skills layer for opencode**: **loaded on-demand by the agent via the skill tool**. Skills are not primarily a user-invoked slash-command surface in opencode; they are model-discovered reusable instructions. There is an open upstream bug suggesting argument delivery via skills-as-slash-commands is itself unreliable on opencode.

**Spec Kitty implication**: This is the decisive finding for scoping. If we moved opencode's Spec Kitty commands to skills, we would **lose the autocomplete UX** (skills aren't user-invoked slash entries in opencode's TUI) **and potentially break argument delivery** (per the upstream bug). opencode stays on the existing `.opencode/command/` pipeline.

### Cursor

**Sources of truth**: [cursor.com/docs/cli/reference/slash-commands](https://cursor.com/docs/cli/reference/slash-commands); [cursor.com/changelog/1-6](https://cursor.com/changelog/1-6); [forum.cursor.com/t/custom-slash-commands-improvements/132611](https://forum.cursor.com/t/custom-slash-commands-improvements/132611).

**Key quotes (from the cited sources, via web search summaries)**:

> "Cursor Commands are reusable AI prompts saved as Markdown files in `.cursor/commands/`, and they act like AI-driven shortcuts..."

> "Claude Code has custom slash commands that support arguments and bash script execution, but this appears to be a feature that Cursor is still working on implementing. While Cursor's custom slash commands feature is useful for shortcuts, there's still room for improvement."

> "You can now create new rules and edit existing ones directly from the CLI with the `/rules` command, and Cursor shipped new slash commands that change how you manage models, rules, plugins, MCP servers, and your entire plan workflow."

**Interpretation**:
- **Command layer for Cursor**: exists via `.cursor/commands/*.md`. Argument support in those commands appears limited or actively-in-development per community forum threads.
- **Skills layer for Cursor**: not surfaced in current Cursor docs as a primary command mechanism.

**Spec Kitty implication**: No change for this mission. Cursor stays on command-file rendering. If Cursor's argument story improves or its skills layer matures, we can revisit in a follow-up.

### Other eleven agents (Copilot, Qwen, Windsurf, Kilocode, Auggie, Roo, Amazon Q, Antigravity)

Each of these has a working command-file rendering path in Spec Kitty today with a documented `$ARGUMENTS` (or `{{args}}`) substitution. None of them is the subject of this mission. Keeping them on their existing command-file pipeline is the zero-risk default, and NFR-005 locks this in with a regression test.

## Per-agent summary matrix

| Agent | Command layer | Args in commands | Skills layer | Args in skills | Autocomplete (cmds) | Autocomplete (skills) | Spec Kitty action |
|-------|--------------|------------------|--------------|----------------|---------------------|------------------------|-------------------|
| Claude Code | `.claude/commands/` | `$ARGUMENTS` + `$1`, `$2` | `.claude/skills/` (merged with commands as of v2.1.3) | `$ARGUMENTS` yes; positional ambiguous per Anthropic issue #19355 | Yes | Yes | Keep commands |
| Codex | `.codex/prompts/` (**deprecated**) | `$ARGUMENTS` (legacy) | `.agents/skills/` + `~/.codex/skills/` | No documented substitution; invocation text flows as turn content | (deprecated) | Yes (`$skill-name`, `/skills`) | **Move to skills** |
| Vibe | none | n/a | `.agents/skills/`, `.vibe/skills/`, `~/.vibe/skills/` | Mistral docs silent; DeepWiki hedged | n/a | Yes | **New: skills** |
| Gemini | `.gemini/commands/` (TOML) | `{{args}}` | Not a primary surface | n/a | Yes | n/a | Keep commands |
| opencode | `.opencode/command/` | `$ARGUMENTS`, `$1/$2`, `!cmd`, `@file` | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/` — model-loaded via skill tool | Open upstream bug when invoked as slash commands | Yes | No (model-discovered) | Keep commands |
| Cursor | `.cursor/commands/` | Limited; argument support still requested | Not a primary surface | n/a | Yes | n/a | Keep commands |
| Copilot | `.github/prompts/` | `$ARGUMENTS` | — | — | Yes | — | Keep commands |
| Qwen | `.qwen/commands/` (TOML) | `{{args}}` | — | — | Yes | — | Keep commands |
| Windsurf | `.windsurf/workflows/` | `$ARGUMENTS` | — | — | Yes | — | Keep commands |
| Kilocode | `.kilocode/workflows/` | `$ARGUMENTS` | — | — | Yes | — | Keep commands |
| Auggie | `.augment/commands/` | `$ARGUMENTS` | — | — | Yes | — | Keep commands |
| Roo | `.roo/commands/` | `$ARGUMENTS` | — | — | Yes | — | Keep commands |
| Amazon Q | `.amazonq/prompts/` | `$ARGUMENTS` | — | — | Yes | — | Keep commands |
| Antigravity | `.agent/workflows/` | `$ARGUMENTS` | — | — | Yes | — | Keep commands |

## Decisions (pulled up to `plan.md`; justified here)

1. **Scope the new Agent Skills renderer to Codex + Vibe only.** Every other agent has a working command-file pipeline with deterministic `$ARGUMENTS` / `{{args}}` substitution today. Moving them to skills would either lose that substitution or lose autocomplete UX, or both (opencode is the worst case). Containment is a correctness property, not a scope-reduction convenience.
2. **Rewrite the `## User Input` block during skills rendering.** The renderer replaces the template's `## User Input\n\n$ARGUMENTS` block with an explicit instruction telling the model to read the invocation turn's free-form text as the User Input. This is the only mechanism that works on Codex today and is safe against Vibe's undocumented substitution semantics. If Vibe also substitutes `$ARGUMENTS` in the future, that is additive and harmless.
3. **Guard against stray `$ARGUMENTS` tokens outside the User-Input block.** The renderer raises `SkillRenderError` on any such token. This prevents future template edits from silently regressing Codex/Vibe output.
4. **Central JSON ownership manifest at `.kittify/command-skills-manifest.json`.** One source of truth for Spec-Kitty-owned files under `.agents/skills/`. Uses SHA-256 content hashes for drift detection. Matches our existing `.kittify/` pattern.
5. **Reference-counted `agents` array per manifest entry.** Shared-root coexistence requires that a skill package installed on behalf of both Codex and Vibe is removed only when **both** agents are deconfigured. Removing Codex alone must not delete a package Vibe still needs.
6. **Zero-touch Codex migration.** The upgrade migration hash-compares existing `.codex/prompts/spec-kitty.*.md` files against the previous Spec Kitty renderer's known output, deletes unedited matches, preserves user-edited variants, and installs the new skill packages — all in one `spec-kitty upgrade` invocation. No manual steps.

## Open questions that are NOT clarifications (implementation-phase tunables)

These are intentionally deferred to implementation; they do not block planning:

- Exact wording of the User-Input block replacement sentence — locked by snapshot test during implementation.
- Whether to add a `doctor` subcommand or extend an existing one to surface manifest drift — minor UX decision.
- Whether `~/.agents/skills/` global installation is worth exposing in a follow-up — explicitly out of scope for this release per spec §Out of Scope.

## Citations

### Mistral Vibe
- [Mistral Docs — Agents & Skills](https://docs.mistral.ai/mistral-vibe/agents-skills) *(official; silent on argument substitution)*
- [Mistral Docs — CLI Introduction](https://docs.mistral.ai/mistral-vibe/introduction)
- [Mistral Docs — Configuration](https://docs.mistral.ai/mistral-vibe/introduction/configuration)
- [Mistral Docs — Quickstart](https://docs.mistral.ai/mistral-vibe/introduction/quickstart)
- [Mistral Help Center — Get started with Mistral Vibe](https://help.mistral.ai/en/articles/496007-get-started-with-mistral-vibe)
- [mistralai/mistral-vibe — GitHub README](https://github.com/mistralai/mistral-vibe)
- [mistral-vibe on PyPI](https://pypi.org/project/mistral-vibe/)
- [DeepWiki — Skills & Subagents (community reference)](https://deepwiki.com/mistralai/mistral-vibe/3.8-skills-and-subagents)
- [DeepWiki — Quick Start Guide (community reference)](https://deepwiki.com/mistralai/mistral-vibe/2.3-quick-start-guide)
- [DeepWiki — Core Concepts (community reference)](https://deepwiki.com/mistralai/mistral-vibe/3-core-concepts)
- [DeepWiki — CLI Commands Reference (community reference)](https://deepwiki.com/mistralai/mistral-vibe/9.3-cli-commands-reference)
- [DataCamp blog — Mistral Vibe 2.0: The Terminal-Based AI Coding Agent](https://www.datacamp.com/blog/mistral-vibe-2-0)

### OpenAI Codex
- [OpenAI Developers — Agent Skills (Codex)](https://developers.openai.com/codex/skills)
- [OpenAI Developers — Custom Prompts (deprecated)](https://developers.openai.com/codex/custom-prompts)
- [OpenAI Developers — Slash commands in Codex CLI](https://developers.openai.com/codex/cli/slash-commands)
- [OpenAI Developers — Features (Codex CLI)](https://developers.openai.com/codex/cli/features)
- [OpenAI Developers — Command line options (Codex CLI)](https://developers.openai.com/codex/cli/reference)
- [OpenAI Developers — Changelog (Codex)](https://developers.openai.com/codex/changelog)
- [OpenAI Developers — Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [openai/codex — docs/skills.md](https://github.com/openai/codex/blob/main/docs/skills.md)
- [openai/codex — Issue #5291: Support for SKILL.md files](https://github.com/openai/codex/issues/5291)
- [openai/skills — Skills Catalog for Codex](https://github.com/openai/skills)
- [Skills in OpenAI Codex (blog.fsck.com, December 2025)](https://blog.fsck.com/2025/12/19/codex-skills/)
- [Simon Willison — OpenAI are quietly adopting skills](https://simonw.substack.com/p/openai-are-quietly-adopting-skills)
- [feiskyer/codex-settings — community settings and skills](https://github.com/feiskyer/codex-settings)

### Claude Code
- [Claude Code Docs — Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [anthropics/claude-code — Issue #19355: Clarify support for positional arguments in Agent Skills](https://github.com/anthropics/claude-code/issues/19355) *(explicitly documents Anthropic's open ambiguity on positional args in skills)*
- [alexop.dev — Claude Code Customization Guide](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/)
- [eesel AI — Your complete guide to slash commands Claude Code](https://www.eesel.ai/blog/slash-commands-claude-code)
- [egghead — Claude Skills Compared to Slash Commands](https://egghead.io/claude-skills-compared-to-slash-commands~lhdor)
- [Steve Kinney — Claude Code Commands](https://stevekinney.com/courses/ai-development/claude-code-commands)
- [batsov — Essential Claude Code Skills and Commands](https://batsov.com/articles/2026/03/11/essential-claude-code-skills-and-commands/)
- [luongnv89/claude-howto — 01-slash-commands](https://github.com/luongnv89/claude-howto/blob/main/01-slash-commands/README.md)

### Google Gemini CLI
- [Gemini CLI Docs — Custom commands](https://geminicli.com/docs/cli/custom-commands/)
- [Google Cloud Blog — Gemini CLI: Custom slash commands](https://cloud.google.com/blog/topics/developers-practitioners/gemini-cli-custom-slash-commands)
- [google-gemini/gemini-cli — docs/cli/custom-commands.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/custom-commands.md)
- [Mintlify mirror — Custom Commands](https://www.mintlify.com/google-gemini/gemini-cli/advanced/custom-commands)

### opencode
- [OpenCode — Commands](https://opencode.ai/docs/commands/)
- [OpenCode — Agent Skills](https://opencode.ai/docs/skills/)
- [OpenCode — Config](https://opencode.ai/docs/config/)
- [OpenCode — Custom Tools](https://opencode.ai/docs/custom-tools/)
- [OpenCode — Rules](https://opencode.ai/docs/rules/)
- [OpenCode — Tools](https://opencode.ai/docs/tools/)
- [code-yeongyu/oh-my-openagent — Issue #640: Skills invoked as slash commands without arguments ignore skill instructions](https://github.com/code-yeongyu/oh-my-openagent/issues/640) *(evidence of the skills-as-slash-commands argument-delivery gap)*

### Cursor
- [Cursor Docs — Slash commands](https://cursor.com/docs/cli/reference/slash-commands)
- [Cursor Changelog 1.6 — Slash commands, summarization, improved Agent](https://cursor.com/changelog/1-6)
- [Cursor Community Forum — Custom slash commands improvements](https://forum.cursor.com/t/custom-slash-commands-improvements/132611)
- [hamzafer/cursor-commands — Cursor Custom Slash Commands](https://github.com/hamzafer/cursor-commands)

## Research process notes

- All web searches above were performed on 2026-04-14 as part of planning for feature 083. Search queries and authoritative URLs are recorded in the plan's conversation thread for the mission.
- Where official vendor docs were silent on a question (notably Vibe's argument-substitution semantics), this research errs on the side of the pessimistic interpretation: the feature is not guaranteed and cannot be depended on by Spec Kitty.
- Community references (DeepWiki, blog posts) are cited as signal, not authority. The decisions above are load-bearing on the vendor-authoritative sources; community sources are cross-checks.
- The twelve agents that are **not** being migrated in this mission each had their argument-delivery mechanism inspected via the in-repo `AGENT_COMMAND_CONFIG` table and cross-checked against each vendor's docs for the primary command format. Spec Kitty's current behavior matches each vendor's contract.
