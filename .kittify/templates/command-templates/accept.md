---
description: Validate feature readiness and guide final acceptance steps.
scripts:
  sh: .kittify/scripts/bash/accept-feature.sh --json {ARGS}
  ps: .kittify/scripts/powershell/accept-feature.ps1 --json {ARGS}
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.


*Path: [templates/commands/accept.md](templates/commands/accept.md)*


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Discovery (auto-detect with smart defaults)

**Goal:** Minimize user interaction by auto-detecting information from the environment.

### Auto-Detection Strategy

1. **Feature slug**:
   - Run `git branch --show-current` to get current branch name
   - If branch matches pattern `\d{3}-[a-z0-9-]+` (e.g., `001-privacy-cli`), use it as feature slug
   - Only ask user if branch name doesn't match or if on `main`/`master`

2. **Acceptance mode**:
   - **Default to `local`** (most common workflow)
   - User can override by saying "use PR mode" or "checklist only"
   - Only ask if user explicitly requests clarification

3. **Validation commands**:
   - Search recent git log for test/build commands:
     ```bash
     git log --oneline -20 | grep -iE "(test|build|check|cargo|npm|pytest|make)"
     ```
   - Look for common patterns in project:
     - Rust: `cargo test`, `cargo build --release`, `cargo check`
     - Python: `pytest`, `python -m pytest`, `make test`
     - Node: `npm test`, `npm run build`, `yarn test`
     - Go: `go test ./...`, `go build`
   - Check for CI config files (`.github/workflows/`, `.gitlab-ci.yml`) and extract test commands
   - If found, report them and say "proceeding with these validation commands"
   - If none found, proceed without validation commands (user can add later)
   - **Never block on missing validation commands**

4. **Acceptance actor**:
   - Always defaults to `__AGENT__` (current agent name)
   - No need to ask or confirm

### Execution Flow

**Preferred flow (no user questions):**
```
1. Auto-detect feature slug from git branch
2. Use mode=local by default
3. Search for validation commands in git log/project
4. Proceed directly with acceptance
```

**Only ask the user if:**
- Feature slug cannot be auto-detected (e.g., on main branch)
- User explicitly provides conflicting information in $ARGUMENTS
- Auto-detection fails for technical reasons

**Present auto-detected values clearly:**
```
Running acceptance with auto-detected values:
- Feature: 001-privacy-compiler-cli (from git branch)
- Mode: local (default)
- Validation: cargo test --all, cargo build --release (from git log)
```

**Never use `WAITING_FOR_ACCEPTANCE_INPUT` unless:**
- Feature slug detection fails AND user didn't provide one
- User explicitly asks a question that needs an answer

If user provides explicit values in $ARGUMENTS, those override auto-detected values.

## Execution Plan

1. **Auto-detect parameters** (run these commands silently):
   ```bash
   # Detect feature slug
   git branch --show-current

   # Search for validation commands in recent commits
   git log --oneline -20 | grep -iE "(test|build|check|cargo|npm|pytest|make)"
   ```

2. **Determine final values** (using auto-detection + user overrides):
   - Feature slug: From git branch (or user override from $ARGUMENTS)
   - Mode: `local` (or user override: "pr"/"checklist")
   - Validation commands: From git log search (or user-specified)
   - Actor: `__AGENT__` (always)

3. **Present detected values to user** (brief confirmation):
   ```
   Running acceptance for feature 001-privacy-cli (mode: local)
   Validation: cargo test --all, cargo build --release
   ```

4. **Compile the acceptance options** into an argument list:
   - Always include `--actor "__AGENT__"`.
   - Append `--feature "<slug>"` (from detection or user input).
   - Append `--mode <mode>` (default: `local`).
   - Append `--test "<command>"` for each validation command found.

5. Run `{SCRIPT}` (the CLI wrapper) with the assembled arguments **and** `--json`.

6. Parse the JSON response. It contains:
   - `summary.ok` (boolean) and other readiness details.
   - `summary.outstanding` categories when issues remain.
   - `instructions` (merge steps) and `cleanup_instructions`.
   - `notes` (e.g., acceptance commit hash).

7. Present the outcome:
   - If `summary.ok` is `false`, list each outstanding category with bullet points and advise the user to resolve them before retrying acceptance.
   - If `summary.ok` is `true`, display:
     - Acceptance timestamp, actor, and (if present) acceptance commit hash.
     - Merge instructions and cleanup instructions as ordered steps.
     - Validation commands executed (if any).

8. When the mode is `checklist`, make it clear no commits or merge instructions were produced.

## Output Requirements

- Summaries must be in plain text (no tables). Use short bullet lists for instructions.
- Surface outstanding issues before any congratulations or success messages.
- If the JSON payload includes warnings, surface them under an explicit **Warnings** section.
- Never fabricate results; only report what the JSON contains.

## Error Handling

- If the command fails or returns invalid JSON, report the failure and request user guidance (do not retry automatically).
- When outstanding issues exist, do **not** attempt to force acceptance—return the checklist and prompt the user to fix the blockers.
