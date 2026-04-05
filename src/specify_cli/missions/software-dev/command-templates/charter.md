# /spec-kitty.charter - Interview + Compile Charter

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

**In repos with multiple features, always pass `--feature <slug>` to every spec-kitty command.**

## Command Contract

This command delegates charter work to the CLI charter workflow. Do not hand-author long governance content in chat unless the user explicitly asks for manual drafting.

### Output location

- Charter markdown: `.kittify/constitution/constitution.md`
- Interview answers: `.kittify/constitution/interview/answers.yaml`
- Reference manifest: `.kittify/constitution/references.yaml`
- Local reference docs: `.kittify/constitution/library/*.md`

## Execution Paths

### Path A: Deterministic minimal setup (fast)

Use when user wants speed, defaults, or bootstrap:

```bash
spec-kitty charter interview --defaults --profile minimal --json
spec-kitty charter generate --from-interview --json
```

### Path B: Interactive interview (full)

Use when the user wants project-specific policy capture:

```bash
spec-kitty charter interview --profile comprehensive
spec-kitty charter generate --from-interview
```

## Editing Rules

- To revise policy inputs, rerun `charter interview` (or edit `answers.yaml`) and regenerate.
- Use `--force` with generate if the charter already exists and must be replaced.
- Keep charter concise; full detail belongs in reference docs listed in `references.yaml`.

## Validation + Status

After generation, verify status:

```bash
spec-kitty charter status --json
```

## Context Bootstrap Requirement

After charter generation, first-run lifecycle actions should load context explicitly:

```bash
spec-kitty charter context --action specify --json
spec-kitty charter context --action plan --json
spec-kitty charter context --action implement --json
spec-kitty charter context --action review --json
```

Use JSON `text` as governance context. If `mode=bootstrap`, follow referenced docs as needed.
