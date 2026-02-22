---
description: Generate or update the project constitution from a structured interview.
---

# /spec-kitty.constitution - Interview + Compile Constitution

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Standard Workflow

Run the CLI constitution interview, then compile:

```bash
spec-kitty constitution interview --profile minimal
spec-kitty constitution generate --from-interview
```

For deterministic defaults:

```bash
spec-kitty constitution interview --defaults --profile minimal --json
spec-kitty constitution generate --from-interview --json
```

## Artifacts

- `.kittify/constitution/constitution.md`
- `.kittify/constitution/interview/answers.yaml`
- `.kittify/constitution/references.yaml`
- `.kittify/constitution/library/*.md`

## Context Bootstrap

Lifecycle commands should load context before execution:

```bash
spec-kitty constitution context --action specify --json
spec-kitty constitution context --action plan --json
spec-kitty constitution context --action implement --json
spec-kitty constitution context --action review --json
```
