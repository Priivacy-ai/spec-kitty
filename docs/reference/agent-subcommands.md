---
title: "Agent Subcommand Reference"
description: "Reference for spec-kitty agent subcommands. Learn how agent-only actions like config, status, decision, and retrospect behave in workflows."
---

# Agent Subcommand Reference

The `spec-kitty agent` commands are designed for AI agents and automation tooling. They generally emit JSON and update task metadata or mission artifacts directly.

Terminology note:
- `Mission Type` = reusable blueprint
- `Mission` = tracked item under `kitty-specs/<mission-slug>/`
- `Mission Run` = runtime/session instance
- The `agent feature` command group remains a legacy compatibility alias; tracked-mission selectors are documented canonically as `--mission`

## Getting Started
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Non-Interactive Init](../how-to/non-interactive-init.md)

<!-- BEGIN GENERATED -->
# Agent Subcommand Reference

## spec-kitty agent

_Commands for AI agents to execute spec-kitty mission actions programmatically_

```
 Usage: spec-kitty agent [OPTIONS] COMMAND [ARGS]...

 Commands for AI agents to execute spec-kitty mission actions programmatically

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ config      Manage project AI agent configuration (add, remove, list agents) │
│ mission     Mission lifecycle commands for AI agents                         │
│ tasks       Task workflow commands for AI agents                             │
│ context     Agent context management commands                                │
│ release     Release packaging commands for AI agents                         │
│ action      Mission action commands that display prompts and instructions    │
│             for agents                                                       │
│ status      Canonical status management commands                             │
│ tests       Test-related commands for AI agents                              │
│ decision    Decision Moment ledger for interview questions.                  │
│ retrospect  Retrospective synthesis commands                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent action

_Mission action commands that display prompts and instructions for agents_

```
 Usage: spec-kitty agent action [OPTIONS] COMMAND [ARGS]...

 Mission action commands that display prompts and instructions for agents

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ implement  Display work package prompt with implementation instructions.     │
│ review     Display work package prompt with review instructions.             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent action implement

```
 Usage: spec-kitty agent action implement [OPTIONS] [WP_ID]

 Display work package prompt with implementation instructions.

 This command outputs the full work package prompt content so agents can
 immediately see what to implement, without navigating the file system.

 Automatically moves WP from planned to in_progress (requires --agent to track
 who is working).

 Examples:
     spec-kitty agent action implement WP01 --agent claude
     spec-kitty agent action implement WP02 --agent claude
     spec-kitty agent action implement wp01 --agent codex
     spec-kitty agent action implement --agent gemini  # auto-detects first
 planned WP

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   wp_id      [WP_ID]  Work package ID (e.g., WP01, wp01, WP01-slug) -        │
│                       auto-detects first planned if omitted                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission                          TEXT  Mission slug                        │
│ --agent                            TEXT  Agent name (required for auto-move  │
│                                          to in_progress)                     │
│ --allow-sparse-checkout                  Proceed even if legacy              │
│                                          sparse-checkout state is detected.  │
│                                          Use of this override is logged.     │
│                                          Does not bypass the commit-time     │
│                                          data-loss backstop.                 │
│ --acknowledge-not-bulk-edit              Suppress the bulk-edit inference    │
│                                          warning when spec language          │
│                                          resembles a bulk edit but the       │
│                                          mission is not one.                 │
│ --help                                   Show this message and exit.         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent action review

```
 Usage: spec-kitty agent action review [OPTIONS] [WP_ID]

 Display work package prompt with review instructions.

 This command outputs the full work package prompt (including any review
 feedback from previous reviews) so agents can review the implementation.

 Automatically moves WP from for_review to in_review (requires --agent to track
 who is reviewing).

 Examples:
     spec-kitty agent action review WP01 --agent claude
     spec-kitty agent action review wp02 --agent codex
     spec-kitty agent action review --agent gemini  # auto-detects first
 for_review WP

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   wp_id      [WP_ID]  Work package ID (e.g., WP01) - auto-detects first      │
│                       for_review if omitted                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug                                          │
│ --agent          TEXT  Agent name (required for auto-move to in_progress)    │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent config

_Manage project AI agent configuration (add, remove, list agents)_

```
 Usage: spec-kitty agent config [OPTIONS] COMMAND [ARGS]...

 Manage project AI agent configuration (add, remove, list agents)

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list    List configured agents and their status.                             │
│ add     Add agents to the project.                                           │
│ remove  Remove agents from the project.                                      │
│ status  Show which agents are configured vs present on filesystem.           │
│ sync    Sync filesystem with config.yaml.                                    │
│ set     Set a project-level agent configuration value.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent config add

```
 Usage: spec-kitty agent config add [OPTIONS] AGENTS...

 Add agents to the project.

 Creates agent directories and updates config.yaml.

 Example:
     spec-kitty agent config add claude codex

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    agents      AGENTS...  Agent keys to add (e.g., claude codex)           │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent config list

```
 Usage: spec-kitty agent config list [OPTIONS]

 List configured agents and their status.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent config remove

```
 Usage: spec-kitty agent config remove [OPTIONS] AGENTS...

 Remove agents from the project.

 Deletes agent directories and updates config.yaml.

 Example:
     spec-kitty agent config remove codex gemini

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    agents      AGENTS...  Agent keys to remove [required]                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --keep-config          Keep in config.yaml but delete directory              │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent config set

```
 Usage: spec-kitty agent config set [OPTIONS] KEY VALUE

 Set a project-level agent configuration value.

 Currently supported keys:
     auto_commit  - Enable/disable automatic commits by agents (true/false)

 Examples:
     spec-kitty agent config set auto_commit false
     spec-kitty agent config set auto_commit true

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    key        TEXT  Configuration key (e.g., auto_commit) [required]       │
│ *    value      TEXT  Configuration value (e.g., true, false) [required]     │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent config status

```
 Usage: spec-kitty agent config status [OPTIONS]

 Show which agents are configured vs present on filesystem.

 Identifies:
 - Configured and present (✓)
 - Configured but missing (⚠)
 - Not configured but present (orphaned) (✗)

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent config sync

```
 Usage: spec-kitty agent config sync [OPTIONS]

 Sync filesystem with config.yaml.

 By default, removes orphaned directories (present but not configured).
 Use --create-missing to also create directories for configured agents.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --create-missing                          Create directories for configured  │
│                                           agents that are missing            │
│ --remove-orphaned    --keep-orphaned      Remove directories for agents not  │
│                                           in config                          │
│                                           [default: remove-orphaned]         │
│ --help                                    Show this message and exit.        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent context

_Agent context management commands_

```
 Usage: spec-kitty agent context [OPTIONS] COMMAND [ARGS]...

 Agent context management commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ resolve  Resolve canonical feature/work-package/action context for prompt    │
│          execution.                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent context resolve

```
 Usage: spec-kitty agent context resolve [OPTIONS]

 Resolve canonical feature/work-package/action context for prompt execution.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --action         TEXT  Action to resolve context for (tasks,              │
│                           tasks_outline, tasks_packages, tasks_finalize,     │
│                           implement, review, accept)                         │
│                           [required]                                         │
│    --mission        TEXT  Mission slug (e.g., '020-my-mission')              │
│    --wp-id          TEXT  Work package ID (e.g., WP01)                       │
│    --agent          TEXT  Agent name for exact command rendering             │
│    --json                 Output results as JSON                             │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent decision

_Decision Moment ledger for interview questions._

```
 Usage: spec-kitty agent decision [OPTIONS] COMMAND [ARGS]...

 Decision Moment ledger for interview questions.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ open     Open a new Decision Moment or return idempotently if one already    │
│          exists.                                                             │
│ resolve  Resolve a decision with a concrete final answer.                    │
│ defer    Defer a decision for later resolution.                              │
│ cancel   Cancel a decision (deemed no longer relevant).                      │
│ verify   Cross-check deferred decisions against inline sentinel markers.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent decision cancel

```
 Usage: spec-kitty agent decision cancel [OPTIONS] DECISION_ID

 Cancel a decision (deemed no longer relevant).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    decision_id      TEXT  ULID identifier of the decision to cancel        │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                     TEXT  Mission handle [required]             │
│ *  --rationale                   TEXT  Explanation of why it's being         │
│                                        canceled (required)                   │
│                                        [required]                            │
│    --resolved-by                 TEXT  Identity of canceling party           │
│    --actor                       TEXT  Identity of the acting agent          │
│                                        [default: cli]                        │
│    --dry-run                           Validate without writing              │
│    --json           --no-json          Output JSON (default true)            │
│                                        [default: json]                       │
│    --help                              Show this message and exit.           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent decision defer

```
 Usage: spec-kitty agent decision defer [OPTIONS] DECISION_ID

 Defer a decision for later resolution.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    decision_id      TEXT  ULID identifier of the decision to defer         │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                     TEXT  Mission handle [required]             │
│ *  --rationale                   TEXT  Explanation of why it's being         │
│                                        deferred (required)                   │
│                                        [required]                            │
│    --resolved-by                 TEXT  Identity of deferring party           │
│    --actor                       TEXT  Identity of the acting agent          │
│                                        [default: cli]                        │
│    --dry-run                           Validate without writing              │
│    --json           --no-json          Output JSON (default true)            │
│                                        [default: json]                       │
│    --help                              Show this message and exit.           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent decision open

```
 Usage: spec-kitty agent decision open [OPTIONS]

 Open a new Decision Moment or return idempotently if one already exists.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                   TEXT  Mission handle (slug, mission_id, or    │
│                                      mid8)                                   │
│                                      [required]                              │
│ *  --flow                      TEXT  Origin flow: charter | specify | plan   │
│                                      [required]                              │
│ *  --input-key                 TEXT  The input key this decision governs     │
│                                      [required]                              │
│ *  --question                  TEXT  Human-readable question text [required] │
│    --step-id                   TEXT  Interview step identifier               │
│    --slot-key                  TEXT  Slot key (use when step_id unavailable) │
│    --options                   TEXT  Candidate answers as a JSON array       │
│                                      string                                  │
│    --actor                     TEXT  Identity of the opening actor           │
│                                      [default: cli]                          │
│    --dry-run                         Validate without writing                │
│    --json         --no-json          Output JSON (default true)              │
│                                      [default: json]                         │
│    --help                            Show this message and exit.             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent decision resolve

```
 Usage: spec-kitty agent decision resolve [OPTIONS] DECISION_ID

 Resolve a decision with a concrete final answer.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    decision_id      TEXT  ULID identifier of the decision to resolve       │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                      TEXT  Mission handle [required]            │
│ *  --final-answer                 TEXT  The chosen answer (non-empty)        │
│                                         [required]                           │
│    --other-answer                       True if answer is a write-in         │
│    --rationale                    TEXT  Explanation of the choice            │
│    --resolved-by                  TEXT  Identity of resolver                 │
│    --actor                        TEXT  Identity of the acting agent         │
│                                         [default: cli]                       │
│    --dry-run                            Validate without writing             │
│    --json            --no-json          Output JSON (default true)           │
│                                         [default: json]                      │
│    --help                               Show this message and exit.          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent decision verify

```
 Usage: spec-kitty agent decision verify [OPTIONS]

 Cross-check deferred decisions against inline sentinel markers.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                                TEXT  Mission handle [required]  │
│    --fail-on-stale    --no-fail-on-stale          Exit non-zero when         │
│                                                   findings are present       │
│                                                   (default true)             │
│                                                   [default: fail-on-stale]   │
│    --json             --no-json                   Output JSON (default true) │
│                                                   [default: json]            │
│    --help                                         Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission

_Mission lifecycle commands for AI agents_

```
 Usage: spec-kitty agent mission [OPTIONS] COMMAND [ARGS]...

 Mission lifecycle commands for AI agents

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ branch-context       Return deterministic branch contract for planning-stage │
│                      prompts.                                                │
│ create               Create new mission directory structure in the project   │
│                      root checkout.                                          │
│ check-prerequisites  Validate mission structure and prerequisites.           │
│ record-analysis      Persist `/spec-kitty.analyze` output as                 │
│                      `analysis-report.md`.                                   │
│ setup-plan           Scaffold implementation plan template in the project    │
│                      root checkout.                                          │
│ accept               Perform mission acceptance workflow.                    │
│ merge                Merge mission branch into target branch.                │
│ finalize-tasks       Parse dependencies from tasks.md and update WP          │
│                      frontmatter, then commit to target branch.              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission accept

```
 Usage: spec-kitty agent mission accept [OPTIONS]

 Perform mission acceptance workflow.

 This command:
 1. Validates all tasks are in 'done' lane
 2. Runs acceptance checks from checklist files
 3. Creates acceptance report
 4. Marks mission as ready for merge

 Wrapper for top-level accept command with agent-specific defaults.

 Examples:
     # Run acceptance workflow
     spec-kitty agent mission accept --mission 077-my-mission

     # With JSON output for agents
     spec-kitty agent mission accept --mission 077-my-mission --json

     # Lenient mode (skip strict validation)
     spec-kitty agent mission accept --mission 077-my-mission --lenient --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission          TEXT  Mission slug (required in multi-mission repos)      │
│ --mode             TEXT  Acceptance mode: auto, pr, local, checklist         │
│                          [default: auto]                                     │
│ --json                   Output results as JSON for agent parsing            │
│ --lenient                Skip strict metadata validation                     │
│ --no-commit              Skip auto-commit (report only)                      │
│ --diagnose               Diagnose acceptance blockers without mutation       │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission branch-context

```
 Usage: spec-kitty agent mission branch-context [OPTIONS]

 Return deterministic branch contract for planning-stage prompts.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                       Output JSON format                              │
│ --target-branch        TEXT  Planned landing branch (defaults to current     │
│                              branch)                                         │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission check-prerequisites

```
 Usage: spec-kitty agent mission check-prerequisites [OPTIONS]

 Validate mission structure and prerequisites.

 This command is designed for AI agents to call programmatically.

 Examples:
     spec-kitty agent mission check-prerequisites --json
     spec-kitty agent mission check-prerequisites --mission 020-my-feature
 --paths-only --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission              TEXT  Mission slug (e.g., '020-my-mission')           │
│ --json                       Output JSON format                              │
│ --paths-only                 Only output path variables                      │
│ --include-tasks              Include tasks.md in validation                  │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission create

```
 Usage: spec-kitty agent mission create [OPTIONS] MISSION_SLUG

 Create new mission directory structure in the project root checkout.

 This command is designed for AI agents to call programmatically.
 Creates mission directory in kitty-specs/ and commits to the current branch.

 Examples:
     spec-kitty agent mission create "new-dashboard" --json

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_slug      TEXT  Mission slug (e.g., 'user-auth') [required]     │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission-type                               TEXT  Mission type (e.g.,       │
│                                                    'documentation',          │
│                                                    'software-dev')           │
│ --json                                             Output JSON format        │
│ --target-branch                              TEXT  Target branch (defaults   │
│                                                    to current branch)        │
│ --friendly-name                              TEXT  Human-friendly mission    │
│                                                    title                     │
│ --purpose-tldr                               TEXT  One-line stakeholder TLDR │
│                                                    for the mission           │
│ --purpose-context                            TEXT  Short stakeholder-facing  │
│                                                    paragraph for the mission │
│ --pr-bound                  --no-pr-bound          Mark mission as PR-bound  │
│                                                    (gate fires on            │
│                                                    merge_target_branch)      │
│                                                    [default: no-pr-bound]    │
│ --branch-strategy                            TEXT  Branch-strategy gate      │
│                                                    control (e.g.,            │
│                                                    'already-confirmed' to    │
│                                                    bypass the prompt)        │
│ --force-recreate-coordi…                           Delete and recreate the   │
│                                                    per-mission coordination  │
│                                                    branch if it already      │
│                                                    exists and has diverged   │
│                                                    from the target. Operator │
│                                                    escape hatch; never used  │
│                                                    by automation.            │
│ --help                                             Show this message and     │
│                                                    exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission finalize-tasks

```
 Usage: spec-kitty agent mission finalize-tasks [OPTIONS]

 Parse dependencies from tasks.md and update WP frontmatter, then commit to
 target branch.

 This command is designed to be called after LLM generates WP files via
 /spec-kitty.tasks.
 It post-processes the generated files to add dependency information and
 commits everything.

 Use --validate-only to check for issues (missing requirement mappings,
 ownership overlaps,
 dependency cycles) without making any changes or committing.

 Bootstrap Mutation Surface (FR-003 / SC-002)
 =============================================
 The following 8 frontmatter fields may be written or overwritten by this
 command. When ``--validate-only`` is active, ALL writes are skipped — the
 ``frontmatter_changed and not validate_only`` guard ensures zero bytes of
 mutation on disk.

 +--------------------------+------------------------------+-------------------
 ----------+
 | Field                    | Source                       | Condition
 |
 +--------------------------+------------------------------+-------------------
 ----------+
 | dependencies             | Parsed from tasks.md         | Written if absent
 or differs|
 | planning_base_branch     | _resolve_planning_branch()   | Written if differs
 |
 | merge_target_branch      | Same as target_branch        | Written if differs
 |
 | branch_strategy          | Computed long-form string    | Written if differs
 |
 | requirement_refs         | WP frontmatter / tasks.md    | Written if absent
 or differs|
 | execution_mode           | infer_ownership()            | Written only if
 absent      |
 | owned_files              | infer_ownership()            | Written only if
 absent      |
 | authoritative_surface    | infer_ownership()            | Written only if
 absent      |
 +--------------------------+------------------------------+-------------------
 ----------+

 In validate-only mode, the bootstrap loop still infers all 8 fields in
 memory so that downstream validation (ownership overlap checks, lane
 preview) operates against the post-bootstrap state — not the stale
 on-disk frontmatter.  The in-memory snapshots are stored in
 ``_inmemory_frontmatter`` / ``_inmemory_bodies`` and consumed by the
 manifest-building loop that follows.

 See also: ``tasks.py:finalize-tasks()`` which writes ``dependencies`` via
 ``build_document() + write_text()`` — guarded the same way (T002).
 Examples:
     spec-kitty agent mission finalize-tasks --mission 020-my-feature --json
     spec-kitty agent mission finalize-tasks --mission 020-my-feature
 --validate-only --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission              TEXT  Mission slug (e.g., '020-my-mission')           │
│ --json                       Output JSON format                              │
│ --validate-only              Run all validations without committing. Reports │
│                              issues that would block finalization.           │
│ --target-branch        TEXT  Override the canonical merge target branch read │
│                              from meta.json. Use this for legacy missions    │
│                              created before WP07 persisted target_branch in  │
│                              meta.json (FR-012 escape hatch).                │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission merge

```
 Usage: spec-kitty agent mission merge [OPTIONS]

 Merge mission branch into target branch.

 This command:
 1. Validates the mission is accepted
 2. Merges the mission branch into target (usually 'main')
 3. Cleans up worktree
 4. Deletes the mission branch

 Auto-retry logic:
 If current branch doesn't match feature pattern and auto-retry is enabled,
 it retries only when --mission is provided so worktree selection is
 deterministic.

 Delegates to existing tasks_cli.py merge implementation.

 Examples:
     # Merge into main branch
     spec-kitty agent mission merge --mission 077-my-mission

     # Merge into specific branch with push
     spec-kitty agent mission merge --mission 077-my-mission --target develop
 --push

     # Dry-run mode
     spec-kitty agent mission merge --mission 077-my-mission --dry-run

     # Keep worktree and branch after merge
     spec-kitty agent mission merge --mission 077-my-mission --keep-worktree
 --keep-branch

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission                             TEXT  Mission slug (required in        │
│                                             multi-mission repos)             │
│ --target                              TEXT  Target branch to merge into      │
│                                             (required in multi-feature       │
│                                             repos)                           │
│ --strategy                            TEXT  Merge strategy: merge, squash,   │
│                                             rebase                           │
│                                             [default: merge]                 │
│ --push                                      Push to origin after merging     │
│ --dry-run                                   Show actions without executing   │
│ --keep-branch                               Keep mission branch after merge  │
│                                             (default: delete)                │
│ --keep-worktree                             Keep worktree after merge        │
│                                             (default: remove)                │
│ --auto-retry       --no-auto-retry          Auto-navigate to a deterministic │
│                                             mission worktree if in the wrong │
│                                             location                         │
│                                             [default: no-auto-retry]         │
│ --help                                      Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission record-analysis

```
 Usage: spec-kitty agent mission record-analysis [OPTIONS]

 Persist `/spec-kitty.analyze` output as `analysis-report.md`.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission           TEXT  Mission slug (e.g., '020-my-mission')              │
│ --input-file        TEXT  Markdown report path, or '-' to read report from   │
│                           stdin                                              │
│                           [default: -]                                       │
│ --agent             TEXT  Agent name that produced the analysis report       │
│ --json                    Output JSON format                                 │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent mission setup-plan

```
 Usage: spec-kitty agent mission setup-plan [OPTIONS]

 Scaffold implementation plan template in the project root checkout.

 This command is designed for AI agents to call programmatically.
 Creates plan.md and commits to target branch.

 Examples:
     spec-kitty agent mission setup-plan --json
     spec-kitty agent mission setup-plan --mission 020-my-feature --json

 ------------------------------------------------------------------
 WP04 / FR-011 + FR-012 audit (2026-05-17)
 ------------------------------------------------------------------
 This command's full call graph was audited to confirm every body
 upload / queue write goes through ``default_queue_db_path()`` and
 that no setup-plan path opens the legacy home-scoped queue database
 directly. The audit covered:

   * ``trigger_feature_dossier_sync_if_enabled()`` (this function
     constructs ``OfflineBodyUploadQueue()`` which delegates to
     ``default_queue_db_path()`` — FR-012 lock).
   * ``OfflineBodyUploadQueue.__init__`` (``sync.body_queue``) —
     falls back to ``default_queue_db_path()`` when ``db_path`` is
     ``None``.
   * ``emit_artifact_phase()`` / ``SPECIFY_COMPLETED`` /
     ``PLAN_STARTED`` / ``PLAN_COMPLETED`` — writes to local
     lifecycle JSONL only, no queue DB.
   * ``safe_commit()`` — local git only, no queue DB.

 No direct ``_legacy_queue_db_path()`` call sites exist in the
 setup-plan call graph as of 2026-05-17. The FR-011 refuse-loudly
 guard immediately below this comment is the load-bearing gate that
 ensures we never silently fall back to the legacy queue when SaaS
 sync is enabled but the foreground is unauthenticated.

 ------------------------------------------------------------------
 WP04 (mission ``mvp-cli-sync-boundary-completion-01KRX11M``)
 boundary preflight integration — 2026-05-18
 ------------------------------------------------------------------
 Immediately after the FR-011 hosted-auth refusal above (and only
 when ``SPEC_KITTY_ENABLE_SAAS_SYNC=1``, matching the existing FR-011
 gate), setup-plan invokes
 :func:`specify_cli.sync.preflight.run_preflight` with
 ``require_auth=True`` to enforce FR-002 / FR-009. The boundary
 preflight refuses (``typer.Exit(2)``) on:

   * any of the six canonical daemon-owner / foreground mismatch
     fields (D-3 canon);
   * any orphan daemon owner record on disk;
   * any legacy queue rows belonging to the active scope; or
   * missing hosted auth when SaaS sync is required.

 The preflight is read-only — no DB writes, no SaaS round-trip — so
 placing it AFTER the FR-011 auth guard and BEFORE any
 ``emit_artifact_phase`` / ``trigger_feature_dossier_sync`` /
 ``emit_wp_created`` call ensures every SaaS-producing code path
 downstream of this function has passed the gate. The same gate is
 applied in ``sync now`` (WP03); the two surfaces share
 :func:`specify_cli.sync.preflight.build_boundary_failure_set` as
 their single source of truth.

 Cross-reference: WP04 of mission
 ``mvp-sync-boundary-cli-01KRVCQS``; regression tests in
 ``tests/runtime/test_setup_plan_sync_evidence.py``.
 ------------------------------------------------------------------

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug (e.g., '020-my-mission')                 │
│ --json                 Output JSON format                                    │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent profile list

```
 Usage: spec-kitty agent profile list [OPTIONS]

 List agent profiles (activated-only by default; --all for the full catalog).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                    Output JSON array.                                 │
│ --all                     Show every profile across all source layers        │
│                           (annotated by source layer and activated|available │
│                           state). Supersedes the activated-only default and  │
│                           --show-available.                                  │
│ --show-available          Also show available-but-not-activated profiles     │
│                           (annotated by state).                              │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent profile show

```
 Usage: spec-kitty agent profile show [OPTIONS] PROFILE_ID

 Show the full resolved definition of an agent profile (FR-013/014/015).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profile_id      TEXT  Profile ID to show. [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output JSON object.                                          │
│ --all           Bypass the activation gate for inspection (show              │
│                 non-activated profiles).                                     │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent release

_Release packaging commands for AI agents_

```
 Usage: spec-kitty agent release [OPTIONS] COMMAND [ARGS]...

 Release packaging commands for AI agents

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ prep  Prepare release artifacts (changelog draft, version bump, structured   │
│       inputs).                                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent release prep

```
 Usage: spec-kitty agent release prep [OPTIONS]

 Prepare release artifacts (changelog draft, version bump, structured inputs).

 Reads kitty-specs/ artifacts and local git tags. No network calls.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --channel        [alpha|beta|stable]  Release channel: alpha | beta |     │
│                                          stable                              │
│                                          [required]                          │
│    --repo           PATH                 Repository root (default: current   │
│                                          directory)                          │
│                                          [default: .]                        │
│    --json                                Emit JSON instead of human-readable │
│                                          text                                │
│    --help                                Show this message and exit.         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent retrospect

_Retrospective synthesis commands_

```
 Usage: spec-kitty agent retrospect [OPTIONS] COMMAND [ARGS]...

 Retrospective synthesis commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ synthesize  Apply staged proposals from a mission's retrospective record.    │
│ summary     Cross-mission retrospective summary.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent retrospect summary

_Cross-mission retrospective summary._

```
 Usage: spec-kitty agent retrospect summary [OPTIONS]

 Cross-mission retrospective summary.

 Back-compat alias: equivalent to `spec-kitty retrospect summary`.

 Distinguishes four record states: has_findings / ran_no_findings / missing /
 failed.

 No mutation is performed.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --project                  PATH                     Project root (default:   │
│                                                     cwd)                     │
│ --json                                              Emit JSON to stdout      │
│ --json-out                 PATH                     Also write JSON to this  │
│                                                     file                     │
│ --limit                    INTEGER RANGE            Top-N for ranked         │
│                            [1<=x<=100]              sections                 │
│                                                     [default: 20]            │
│ --since                    TEXT                     ISO-8601 date filter     │
│ --include-malformed                                 Include malformed record │
│                                                     detail                   │
│ --filter                   TEXT                     Filter by record state   │
│                                                     (has_findings|ran_no_fi… │
│ --help                                              Show this message and    │
│                                                     exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent retrospect synthesize

_Apply staged proposals from a mission's retrospective record._

```
 Usage: spec-kitty agent retrospect synthesize [OPTIONS]

 Apply staged proposals from a mission's retrospective record.

 --dry-run is the default; pass --apply to mutate project state.
 flag_not_helpful is the only auto-applied kind (Q2-A).
 Conflict detection is fail-closed: any conflict blocks the whole batch.

 When no retrospective.yaml exists, the command errors with
 RETROSPECTIVE_RECORD_MISSING (exit 1) and points to 'spec-kitty retrospect
 create'.
 Pass --fabricate-empty to use the legacy auto-fabrication path instead.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                TEXT  Mission handle (mission_id / mid8 /        │
│                                   mission_slug)                              │
│                                   [required]                                 │
│    --apply                        Execute application after checks pass      │
│                                   (default is dry-run)                       │
│    --proposal-id            TEXT  Restrict batch to specific proposal ids    │
│                                   (repeatable)                               │
│    --json-out               PATH  Write JSON envelope to PATH in addition to │
│                                   other output                               │
│    --json                         Emit JSON to stdout (suppresses Rich       │
│                                   rendering)                                 │
│    --actor-id               TEXT  Override provenance actor id (default:     │
│                                   inferred from environment)                 │
│    --fabricate-empty              Legacy: auto-fabricate an empty record     │
│                                   when none exists (synthesize_fabricate     │
│                                   provenance)                                │
│    --help                         Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status

_Canonical status management commands_

```
 Usage: spec-kitty agent status [OPTIONS] COMMAND [ARGS]...

 Canonical status management commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ emit         Emit a status transition event for a work package.              │
│ materialize  Rebuild status.json from the canonical event log.               │
│ doctor       Run health checks for status hygiene and global runtime.        │
│ lifecycle    Show the canonical lifecycle state for one mission.             │
│ migrate      [REMOVED] Frontmatter-to-event-log bootstrap migration has been │
│              removed.                                                        │
│ validate     Validate canonical status model integrity.                      │
│ reconcile    [REMOVED] Cross-repo reconciliation has been removed.           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status doctor

```
 Usage: spec-kitty agent status doctor [OPTIONS]

 Run health checks for status hygiene and global runtime.

 Detects global runtime issues (missing runtime directory, version mismatch,
 corrupted missions) and project-level issues (stale claims, orphan
 workspaces, drift).
 Exit code 0 = healthy, 1 = issues found.

 Examples:
     spec-kitty agent status doctor
     spec-kitty agent status doctor --mission 034-my-feature
     spec-kitty agent status doctor --stale-claimed-days 3 --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission                       TEXT     Mission slug                        │
│ --stale-claimed-days            INTEGER  Threshold for stale claims (days)   │
│                                          [default: 7]                        │
│ --stale-in-progress-days        INTEGER  Threshold for stale in-progress     │
│                                          (days)                              │
│                                          [default: 14]                       │
│ --json                                   Machine-readable JSON output        │
│ --help                                   Show this message and exit.         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status emit

```
 Usage: spec-kitty agent status emit [OPTIONS] WP_ID

 Emit a status transition event for a work package.

 Records a lane transition in the canonical event log, validates the
 transition against the state machine, materializes a snapshot, and
 updates legacy compatibility views.

 Examples:
     spec-kitty agent status emit WP01 --to claimed --actor claude
     spec-kitty agent status emit WP01 --to done --actor claude --evidence-json
 '{"review": {"reviewer": "alice", "verdict": "approved", "reference":
 "PR#1"}}'
     spec-kitty agent status emit WP01 --to in_progress --actor claude --force
 --reason "resuming after crash"

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    wp_id      TEXT  Work package ID (e.g., WP01) [required]                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --to                                 TEXT  Target lane (e.g., claimed,    │
│                                               in_progress, for_review,       │
│                                               approved, done)                │
│                                               [required]                     │
│ *  --actor                              TEXT  Who is making this transition  │
│                                               [required]                     │
│    --mission                            TEXT  Mission slug (required in      │
│                                               multi-mission repos)           │
│    --force                                    Force transition bypassing     │
│                                               guards                         │
│    --reason                             TEXT  Reason for forced transition   │
│    --evidence-json                      TEXT  JSON string with done evidence │
│    --review-ref                         TEXT  Review feedback reference      │
│    --workspace-context                  TEXT  Workspace context identifier   │
│                                               for claimed->in_progress       │
│    --subtasks-complete                        Whether required subtasks are  │
│                                               complete for                   │
│                                               in_progress->for_review        │
│    --implementation-evidence-pr…              Whether implementation         │
│                                               evidence exists for            │
│                                               in_progress->for_review        │
│    --execution-mode                     TEXT  Execution mode (worktree or    │
│                                               direct_repo)                   │
│                                               [default: worktree]            │
│    --json                                     Machine-readable JSON output   │
│    --help                                     Show this message and exit.    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status lifecycle

```
 Usage: spec-kitty agent status lifecycle [OPTIONS]

 Show the canonical lifecycle state for one mission.

 This is the product-facing state layer above raw WP lanes. It answers
 whether a mission is active, recently completed, stale, abandoned, or
 now just recoverable/archive history.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug                                          │
│ --json                 Machine-readable JSON output                          │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status materialize

```
 Usage: spec-kitty agent status materialize [OPTIONS]

 Rebuild status.json from the canonical event log.

 Reads all events from status.events.jsonl, applies the deterministic
 reducer to produce a snapshot, writes status.json, and updates legacy
 compatibility views.

 Examples:
     spec-kitty agent status materialize
     spec-kitty agent status materialize --mission 034-my-feature
     spec-kitty agent status materialize --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug (required in multi-mission repos)        │
│ --json                 Machine-readable JSON output                          │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status migrate

```
 Usage: spec-kitty agent status migrate [OPTIONS]

 [REMOVED] Frontmatter-to-event-log bootstrap migration has been removed.

 The canonical status model uses the event log as sole authority.
 One-shot bootstrap migration from frontmatter is handled by the
 upgrade migration system (``spec-kitty upgrade``), not this command.

 Examples:
     spec-kitty upgrade  # applies all pending migrations

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission  -f      TEXT  Single mission slug to migrate                      │
│ --all                    Migrate all features in kitty-specs/                │
│ --dry-run                Preview migration without writing events            │
│ --json                   Output results as JSON                              │
│ --actor            TEXT  Actor name for bootstrap events                     │
│                          [default: migration]                                │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status reconcile

```
 Usage: spec-kitty agent status reconcile [OPTIONS]

 [REMOVED] Cross-repo reconciliation has been removed.

 The canonical status model uses the event log as sole authority.
 Cross-repo drift detection via frontmatter scanning is no longer
 supported. Use ``spec-kitty agent status validate`` to check
 event log integrity.

 Examples:
     spec-kitty agent status validate --mission 034-feature-name

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission      -f             TEXT  Mission slug (required in multi-mission  │
│                                     repos)                                   │
│ --dry-run          --apply          Preview vs persist reconciliation events │
│                                     [default: dry-run]                       │
│ --target-repo  -t             PATH  Target repo path(s) to scan              │
│ --json                              Machine-readable JSON output             │
│ --help                              Show this message and exit.              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent status validate

```
 Usage: spec-kitty agent status validate [OPTIONS]

 Validate canonical status model integrity.

 Runs all validation checks: event schema, transition legality,
 done-evidence completeness, materialization drift, and derived-view drift.

 Exit code 0 for pass (no errors), exit code 1 for fail (any errors).
 Warnings do not cause failure.

 Examples:
     spec-kitty agent status validate
     spec-kitty agent status validate --mission 034-my-feature
     spec-kitty agent status validate --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug (required in multi-mission repos)        │
│ --json                 Machine-readable JSON output                          │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks

_Task workflow commands for AI agents_

```
 Usage: spec-kitty agent tasks [OPTIONS] COMMAND [ARGS]...

 Task workflow commands for AI agents

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ move-task          Move task between lanes (planned → doing → for_review →   │
│                    approved → done).                                         │
│ mark-status        Update task checkbox status in tasks.md for one or more   │
│                    tasks.                                                    │
│ list-tasks         List tasks with optional lane filtering.                  │
│ add-history        Append history entry to task activity log.                │
│ finalize-tasks     Parse tasks.md and inject dependencies into WP            │
│                    frontmatter.                                              │
│ map-requirements   Register requirement-to-WP mappings with immediate        │
│                    validation.                                               │
│ validate-workflow  Validate task metadata structure and workflow             │
│                    consistency.                                              │
│ status             Display kanban status board for all work packages in a    │
│                    feature.                                                  │
│ list-dependents    Find all WPs that depend on a given WP (downstream        │
│                    dependents).                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks add-history

```
 Usage: spec-kitty agent tasks add-history [OPTIONS] TASK_ID

 Append history entry to task activity log.

 Examples:
 spec-kitty agent tasks add-history WP01 --note "Completed implementation"
 --json

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    task_id      TEXT  Task ID (e.g., WP01) [required]                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --note             TEXT  History note [required]                          │
│    --mission          TEXT  Mission slug                                     │
│    --agent            TEXT  Agent name                                       │
│    --shell-pid        TEXT  Shell PID                                        │
│    --json                   Output JSON format                               │
│    --help                   Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks finalize-tasks

```
 Usage: spec-kitty agent tasks finalize-tasks [OPTIONS]

 Parse tasks.md and inject dependencies into WP frontmatter.

 Scans tasks.md for "Depends on: WP##" patterns or phase groupings,
 builds dependency graph, validates for cycles, and writes dependencies
 field to each WP file's frontmatter.

 Examples:
     spec-kitty agent tasks finalize-tasks --mission 001-my-feature --json
     spec-kitty agent tasks finalize-tasks --mission 021-my-feature --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission              TEXT  Mission slug                                    │
│ --json                       Output JSON format                              │
│ --validate-only              Validate without writing changes                │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks list-dependents

```
 Usage: spec-kitty agent tasks list-dependents [OPTIONS] WP_ID

 Find all WPs that depend on a given WP (downstream dependents).

 This answers "who depends on me?" - useful when reviewing a WP to understand
 the impact of requested changes on downstream work packages.

 Also shows what the WP itself depends on (upstream dependencies).

 Examples:
     spec-kitty agent tasks list-dependents WP13
     spec-kitty agent tasks list-dependents WP01 --mission 001-my-feature
 --json

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    wp_id      TEXT  Work package ID (e.g., WP01) [required]                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug                                          │
│ --json                 Output JSON format                                    │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks list-tasks

```
 Usage: spec-kitty agent tasks list-tasks [OPTIONS]

 List tasks with optional lane filtering.

 Examples:
 spec-kitty agent tasks list-tasks --json
 spec-kitty agent tasks list-tasks --lane doing --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --lane           TEXT  Filter by lane                                        │
│ --mission        TEXT  Mission slug                                          │
│ --json                 Output JSON format                                    │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks map-requirements

```
 Usage: spec-kitty agent tasks map-requirements [OPTIONS]

 Register requirement-to-WP mappings with immediate validation.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --wp                                 TEXT  WP ID (e.g., WP04)                │
│ --refs                               TEXT  Comma-separated requirement refs  │
│                                            (e.g., FR-001,FR-002)             │
│ --batch                              TEXT  JSON batch mapping (e.g.,         │
│                                            '{"WP01":["FR-001"],"WP02":["FR-… │
│ --replace                                  Replace existing refs instead of  │
│                                            merging (default: merge/union)    │
│ --tracker-ref                        TEXT  External tracker reference (e.g., │
│                                            '#1298' or 'JIRA-123').           │
│                                            Repeatable; requires --wp.        │
│                                            Persists to the WP frontmatter as │
│                                            tracker_refs.                     │
│ --mission                            TEXT  Mission slug                      │
│ --json                                     Output JSON format                │
│ --auto-commit    --no-auto-commit          Automatically commit WP file      │
│                                            changes (default: from project    │
│                                            config)                           │
│ --help                                     Show this message and exit.       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks mark-status

```
 Usage: spec-kitty agent tasks mark-status [OPTIONS] TASK_IDS...

 Update task checkbox status in tasks.md for one or more tasks.

 Accepts MULTIPLE task IDs separated by spaces. All tasks are updated
 in a single operation with one commit.

 Examples:
     # Single task:
     spec-kitty agent tasks mark-status T001 --status done

     # Multiple tasks (space-separated):
     spec-kitty agent tasks mark-status T001 T002 T003 --status done

     # Many tasks at once:
     spec-kitty agent tasks mark-status T040 T041 T042 T043 T044 T045 --status
 done --mission 001-my-feature

     # With JSON output:
     spec-kitty agent tasks mark-status T001 T002 --status done --json

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    task_ids      TASK_IDS...  Task ID(s) - space-separated (e.g., T001     │
│                                 T002 T003)                                   │
│                                 [required]                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --status                             TEXT  Status: done/pending           │
│                                               [required]                     │
│    --mission                            TEXT  Mission slug                   │
│    --auto-commit    --no-auto-commit          Automatically commit tasks.md  │
│                                               changes to target branch       │
│                                               (default: from project config) │
│    --json                                     Output JSON format             │
│    --help                                     Show this message and exit.    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks move-task

```
 Usage: spec-kitty agent tasks move-task [OPTIONS] TASK_ID

 Move task between lanes (planned → doing → for_review → approved → done).

 Examples:
 spec-kitty agent tasks move-task WP01 --to doing --assignee claude --json
 spec-kitty agent tasks move-task WP02 --to for_review --agent claude
 --shell-pid $$
 spec-kitty agent tasks move-task WP03 --to approved --note "Review passed"
 spec-kitty agent tasks move-task WP03 --to done --done-override-reason "Branch
 deleted after hotfix merge"
 spec-kitty agent tasks move-task WP03 --to planned --review-feedback-file
 feedback.md

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    task_id      TEXT  Task ID (e.g., WP01) [required]                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --to                                         TEXT  Target lane            │
│                                                       (planned/doing/for_re… │
│                                                       [required]             │
│    --mission                                    TEXT  Mission slug           │
│    --agent                                      TEXT  Agent name             │
│    --assignee                                   TEXT  Assignee name (sets    │
│                                                       assignee when moving   │
│                                                       to doing)              │
│    --shell-pid                                  TEXT  Shell PID              │
│    --note                                       TEXT  History note           │
│    --review-feedback-fi…                        PATH  Path to review         │
│                                                       feedback file          │
│                                                       (required for --to     │
│                                                       planned, including     │
│                                                       with --force)          │
│    --approval-ref                               TEXT  Approval reference for │
│                                                       approval/done          │
│                                                       transitions (e.g.,     │
│                                                       PR#42)                 │
│    --reviewer                                   TEXT  Reviewer name          │
│                                                       (auto-detected from    │
│                                                       git if omitted)        │
│    --self-review-fallba…                              Record that approval   │
│                                                       is a self-review       │
│                                                       fallback after the     │
│                                                       intended reviewer      │
│                                                       failed.                │
│    --intended-reviewer                          TEXT  Reviewer that should   │
│                                                       have reviewed this WP  │
│                                                       before fallback.       │
│    --reviewer-failure-r…                        TEXT  Reason the intended    │
│                                                       reviewer failed.       │
│    --done-override-reas…                        TEXT  Required when --to     │
│                                                       done and merge         │
│                                                       ancestry cannot be     │
│                                                       verified; recorded in  │
│                                                       history/event reason   │
│    --force                                            Force move even with   │
│                                                       unchecked subtasks     │
│                                                       (does not bypass       │
│                                                       planned rollback       │
│                                                       feedback requirement)  │
│    --tracker-ref                                TEXT  External tracker       │
│                                                       reference (e.g.,       │
│                                                       '#1298' or             │
│                                                       'JIRA-123').           │
│                                                       Repeatable; appended   │
│                                                       to the WP frontmatter  │
│                                                       tracker_refs.          │
│    --skip-review-artifa…                              Override a rejected    │
│                                                       latest review artifact │
│                                                       when                   │
│                                                       arbiter-approving;     │
│                                                       requires --note and    │
│                                                       records override       │
│                                                       evidence.              │
│    --auto-commit            --no-auto-commit          Automatically commit   │
│                                                       WP file changes to     │
│                                                       target branch          │
│                                                       (default: from project │
│                                                       config)                │
│    --json                                             Output JSON format     │
│    --help                                             Show this message and  │
│                                                       exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks status

```
 Usage: spec-kitty agent tasks status [OPTIONS]

 Display kanban status board for all work packages in a feature.

 Shows a beautiful overview of work package statuses, progress metrics,
 and next steps based on dependencies.

 WPs in "doing" with no commits for --stale-threshold minutes are flagged
 as potentially stale (agent may have stopped).

 Example:
     spec-kitty agent tasks status
     spec-kitty agent tasks status --mission 012-documentation-mission
     spec-kitty agent tasks status --json
     spec-kitty agent tasks status --stale-threshold 15

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission                TEXT     Mission slug                               │
│ --json                            Output as JSON                             │
│ --stale-threshold        INTEGER  Minutes of inactivity before a WP is       │
│                                   considered stale                           │
│                                   [default: 10]                              │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tasks validate-workflow

```
 Usage: spec-kitty agent tasks validate-workflow [OPTIONS] TASK_ID

 Validate task metadata structure and workflow consistency.

 Examples:
 spec-kitty agent tasks validate-workflow WP01 --json

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    task_id      TEXT  Task ID (e.g., WP01) [required]                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug                                          │
│ --json                 Output JSON format                                    │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tests

_Test-related commands for AI agents_

```
 Usage: spec-kitty agent tests [OPTIONS] COMMAND [ARGS]...

 Test-related commands for AI agents

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ stale-check  Detect test assertions likely invalidated by source changes     │
│              between two refs.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty agent tests stale-check

```
 Usage: spec-kitty agent tests stale-check [OPTIONS]

 Detect test assertions likely invalidated by source changes between two refs.

 Compares BASE..HEAD and reports assertions in the test suite that reference
 symbols (functions, classes, string literals) that were renamed or removed in
 the source diff.  Uses AST analysis only — no regex on test text, no test
 execution.

 Confidence levels:
   high   — identifier referenced directly inside Assert or assert* call
   medium — identifier appears anywhere in an assertion node
   low    — string literal matches a Constant in an assertion-bearing position

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --base        TEXT  Base git ref for the diff [required]                  │
│    --head        TEXT  Head git ref for the diff [default: HEAD]             │
│    --repo        PATH  Repository root (default: current directory)          │
│                        [default: .]                                          │
│    --json              Emit JSON instead of human-readable text              │
│    --help              Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```
<!-- END GENERATED -->
