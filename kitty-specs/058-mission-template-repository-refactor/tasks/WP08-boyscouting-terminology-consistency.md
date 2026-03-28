---
work_package_id: WP08
title: "Boyscouting: Terminology Consistency (agent feature \u2192 agent mission)"
lane: planned
dependencies: [WP07]
requirement_refs:
- Constitution terminology canon
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
- T037
- T038
- T043
- T048
phase: Boyscouting
assignee: ''
agent: ''
agent_profile: implementer
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-27T05:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt added manually during /spec-kitty.analyze review
---

# Work Package Prompt: WP08 -- Boyscouting: Terminology Consistency

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. `spec-kitty agent mission --help` shows clean "Mission" terminology in all subcommand names and descriptions
2. `spec-kitty agent feature` still works as a hidden backward-compat alias (no breaking change)
3. `create-feature` subcommand renamed to `create-mission` with hidden `create-feature` alias
4. All documentation references updated from `agent feature` to `agent mission`
5. Doctrine command templates emit `spec-kitty agent mission` (not `agent feature`)

6. `--mission <slug>` works as the primary flag; `--feature <slug>` works as deprecated alias
7. `spec-kitty agent workflow implement --mission <slug>` is the documented pattern

**Success gate**: `spec-kitty agent mission --help` output is free of "feature" terminology. Hidden alias `agent feature` still works. `--mission` flag works as primary, `--feature` as alias. All tests pass.

## Context & Constraints

- **Constitution**: Lines 302-308 mandate "Mission" as the only canonical term; "Feature/Features" are prohibited in user-facing language
- **Current state**: `agent mission` is already the canonical registration in `__init__.py` line 16; `agent feature` is a backward-compat alias on line 17
- **Scope guard**: Only touch strings/docs where "feature" means "mission" (the domain object). Do NOT touch:
  - Internal Python variable/function names (e.g., `create_feature()` function can keep its name)
  - The filename `feature.py` (internal, not user-facing)
- **Scope expansion (2026-03-28)**: The `--feature` → `--mission` flag rename is pulled INTO this WP from 057 scope. The `spec-kitty agent workflow implement --feature <slug>` pattern is the most visible user-facing instance.

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP08 --base WP07`

## Subtasks & Detailed Guidance

### Subtask T031 -- Rename `create-feature` subcommand to `create-mission`

- **Purpose**: The `create-feature` subcommand name violates the terminology canon.
- **Steps**:
  1. **Read** `src/specify_cli/cli/commands/agent/feature.py`, find the `@app.command(name="create-feature")` decorator
  2. **Change** the command name to `"create-mission"`
  3. **Add a hidden alias** for backward compat. Approach: add a thin wrapper command:
     ```python
     @app.command(name="create-feature", hidden=True, deprecated=True)
     def create_feature_alias(...):
         """Deprecated: use create-mission instead."""
         return create_feature(...)  # delegate to the real function
     ```
     Or use typer's built-in `deprecated` parameter if available.
  4. **Run tests**: `pytest tests/agent/test_agent_feature.py -v`
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`

### Subtask T032 -- Update feature.py user-facing strings

- **Purpose**: Module docstring and help text still say "Feature" where they mean "Mission."
- **Steps**:
  1. **Read** `src/specify_cli/cli/commands/agent/feature.py`
  2. **Update** line 1 docstring: `"""Feature lifecycle commands for AI agents."""` -> `"""Mission lifecycle commands for AI agents."""`
  3. **Search** the file for `rich.print` / `console.print` / help text strings containing "feature" in the domain-object sense
  4. **Replace** with "mission" where appropriate (e.g., "Created feature branch" -> "Created mission branch")
  5. **Do NOT touch**: Internal function names, variable names, or comments about the Python code structure
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`

### Subtask T033 -- Mark `agent feature` alias as hidden

- **Purpose**: `agent feature` should work but not appear in `--help`.
- **Steps**:
  1. **Read** `src/specify_cli/cli/commands/agent/__init__.py`
  2. **Change** line 17 from:
     ```python
     app.add_typer(feature.app, name="feature")  # backward-compat alias
     ```
     to:
     ```python
     app.add_typer(feature.app, name="feature", hidden=True)  # backward-compat alias
     ```
  3. **Also check** the `check_prerequisites_alias` command (line ~26) -- ensure its docstring says "Deprecated" and it's already `hidden=True`
  4. **Run tests**: `pytest tests/agent/ -v`
- **Files**: `src/specify_cli/cli/commands/agent/__init__.py`

### Subtask T034 -- Update docs/reference/agent-subcommands.md

- **Purpose**: Primary reference doc for CLI subcommands.
- **Steps**:
  1. **Read** `docs/reference/agent-subcommands.md`
  2. **Rename** the "spec-kitty agent feature" section heading to "spec-kitty agent mission"
  3. **Replace** all `spec-kitty agent feature` invocations with `spec-kitty agent mission`
  4. **Add a note**: "`spec-kitty agent feature` remains available as a hidden alias for backward compatibility."
  5. **Update** `create-feature` references to `create-mission`
- **Files**: `docs/reference/agent-subcommands.md`
- **Parallel?**: Yes

### Subtask T035 -- Update docs/reference/slash-commands.md

- **Purpose**: Slash command docs reference `agent feature` in examples.
- **Steps**:
  1. **Read** `docs/reference/slash-commands.md`
  2. **Replace** `spec-kitty agent feature` with `spec-kitty agent mission` at lines ~24, 47, 75, 145
  3. **Update** any `create-feature` references to `create-mission`
- **Files**: `docs/reference/slash-commands.md`
- **Parallel?**: Yes

### Subtask T036 -- Update README.md CLI examples

- **Purpose**: README is the first thing users see.
- **Steps**:
  1. **Read** `README.md` around lines 866-902
  2. **Replace** `spec-kitty agent feature` with `spec-kitty agent mission` in all examples
  3. **Update** `create-feature` references to `create-mission`
- **Files**: `README.md`
- **Parallel?**: Yes

### Subtask T037 -- Update CLAUDE.md reference

- **Purpose**: CLAUDE.md is loaded into every Claude Code conversation.
- **Steps**:
  1. **Read** `CLAUDE.md` around line 317
  2. **Replace** `spec-kitty agent feature finalize-tasks` with `spec-kitty agent mission finalize-tasks`
  3. **Search** for any other `agent feature` references in CLAUDE.md
- **Files**: `CLAUDE.md`
- **Parallel?**: Yes

### Subtask T038 -- Update doctrine command templates

- **Purpose**: Command templates generate prompts that agents execute. They must emit `agent mission`.
- **Steps**:
  1. **Search** all files under `src/doctrine/missions/*/templates/` for `agent feature`
  2. **Replace** with `agent mission`
  3. **Also check** `src/doctrine/missions/*/command-templates/` for any remaining `agent feature` references
  4. **Verify** the `specify.md` template already uses `agent mission` (it should per the research)
- **Files**: `src/doctrine/missions/*/templates/task-prompt-template.md` (and others if found)
- **Parallel?**: Yes

### Subtask T043 -- Update glossary with "Feature Branch" distinction

- **Purpose**: The constitution prohibits "Feature" as a domain term but "Feature Branch" is a standard VCS concept that should remain acceptable.
- **Steps**:
  1. Add a glossary entry for **Feature Branch**: "A short-lived VCS branch based on the active target branch, intended to be merged into the target branch once work is complete and validated. This is a standard VCS concept, not a Spec Kitty domain term."
  2. Clarify in the glossary that **Mission Specification** replaces **Feature Specification** in spec-kitty artifacts
  3. Use `/spec-kitty.glossary-context` or the doctrine glossary curation tactic to add the entries properly
- **Files**: Glossary artifacts (via doctrine system)
- **Parallel?**: Yes

### Subtask T048 -- Rename `--feature` flag to `--mission` across CLI surface

- **Purpose**: The `--feature <slug>` flag is the most visible user-facing instance of the prohibited "feature" terminology. Rename it to `--mission` with `--feature` kept as a deprecated alias. Pulled from 057 scope into this WP (2026-03-28).
- **Steps**:
  1. **Identify all `--feature` flag declarations** in `src/specify_cli/cli/commands/`:
     - `agent/feature.py` (primary: `spec-kitty agent workflow implement --feature <slug>`)
     - `agent/tasks.py` (`spec-kitty agent tasks ... --feature <slug>`)
     - Any other CLI modules that accept `--feature`
  2. **For each flag**: Add `--mission` as the primary option name, keep `--feature` as a deprecated alias:
     ```python
     # Before:
     feature: str = typer.Option(None, "--feature", help="Feature slug")
     # After:
     feature: str = typer.Option(None, "--mission", "--feature", help="Mission slug")
     ```
     Or use typer's Annotated style if the codebase prefers it.
  3. **Update help text**: Change "Feature slug" to "Mission slug" in all help strings for this flag.
  4. **Test that `--mission` works as primary**:
     ```bash
     spec-kitty agent workflow implement --mission 058-mission-template-repository-refactor --agent test
     spec-kitty agent tasks status --mission 058-mission-template-repository-refactor
     ```
  5. **Test that `--feature` still works as deprecated alias**:
     ```bash
     spec-kitty agent workflow implement --feature 058-mission-template-repository-refactor --agent test
     ```
  6. **Update existing tests** that use `--feature` flag to also cover `--mission`.
- **Files**: `src/specify_cli/cli/commands/agent/feature.py`, `src/specify_cli/cli/commands/agent/tasks.py`, and any other CLI modules with `--feature` flags
- **Parallel?**: Yes, independent of T031-T043

## Test Strategy

```bash
# Run agent tests
pytest tests/agent/ -v

# Verify hidden alias works
spec-kitty agent feature --help  # should still work
spec-kitty agent mission --help  # should show clean Mission terminology

# Verify create-mission works
spec-kitty agent mission create-mission --help
spec-kitty agent mission create-feature --help  # hidden alias, should still work
```

## Risks & Mitigations

1. **CI scripts hard-coding `agent feature`**: Hidden alias prevents breakage. No action needed.
2. **Overlap with feature 057 WP02**: This WP scopes to subcommand names and docs only. The `--feature` flag deprecation is 057's responsibility.
3. **Test assertions on command names**: Tests may assert on `"create-feature"` in help output. Update these assertions.

## Review Guidance

- Verify `spec-kitty agent mission --help` output is clean (no "feature" in domain-object sense)
- Verify `spec-kitty agent feature` hidden alias still works
- Verify `create-mission` subcommand works, `create-feature` alias works
- Verify no stale "agent feature" references remain in docs or templates
- Verify scope guard: `--feature` flag NOT touched, Python filenames NOT renamed

## Activity Log

- 2026-03-27T05:00:00Z -- system -- lane=planned -- Prompt added during /spec-kitty.analyze review.
