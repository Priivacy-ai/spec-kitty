# Data Model: Model Selection per Task

**Feature**: 042-model-selection-per-task

## Entities

### GlobalConfig

Stored at: `~/.spec-kitty/config.yaml`

```yaml
# Full structure (all sections optional)
models:
  specify: claude-opus-4-6         # /spec-kitty.specify command
  plan: claude-opus-4-6            # /spec-kitty.plan command
  tasks: claude-sonnet-4-6         # /spec-kitty.tasks command
  implement: claude-sonnet-4-6     # /spec-kitty.implement command
  review: claude-sonnet-4-6        # /spec-kitty.review command
  accept: claude-sonnet-4-6        # /spec-kitty.accept command
  merge: claude-haiku-4-5          # /spec-kitty.merge command
  clarify: claude-sonnet-4-6       # /spec-kitty.clarify command
  status: claude-haiku-4-5         # /spec-kitty.status command
  checklist: claude-haiku-4-5      # /spec-kitty.checklist command
  analyze: claude-sonnet-4-6       # /spec-kitty.analyze command
  research: claude-opus-4-6        # /spec-kitty.research command
```

**Rules**:
- File is optional — absence means no model injection
- The `models:` key is optional — other top-level keys may exist in future
- Model strings are opaque — not validated by spec-kitty
- Unknown command keys produce a warning, not an error

### AgentCommandFile

Location: `<project>/<agent_dir>/<subdir>/spec-kitty.<cmd>.md`

Example frontmatter after injection:

```yaml
---
description: Create or update the feature specification from a natural language feature description.
model: claude-opus-4-6
---
```

**Rules**:
- `model:` is added when command is in the global config mapping
- `model:` is removed when command is absent from the mapping (cleanup)
- All other frontmatter fields are preserved unchanged
- Files without frontmatter get a new frontmatter block created

## State Transitions

```
Command file (no model:)
    + command in config
    → Command file (model: <value>)

Command file (model: old-value)
    + command in config (new-value)
    → Command file (model: new-value)

Command file (model: <value>)
    + command NOT in config
    → Command file (no model:)

Command file (no model:)
    + command NOT in config
    → Command file (no model:)   [no change]
```
