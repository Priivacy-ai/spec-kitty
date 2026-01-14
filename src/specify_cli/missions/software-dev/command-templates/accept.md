---
description: Validate feature readiness and guide final acceptance steps.
---

# /spec-kitty.accept - Validate Feature Readiness

**Version**: 0.11.0+
**Purpose**: Validate all work packages are complete and feature is ready to merge.

## 📍 WORKING DIRECTORY: Run from MAIN repository

**IMPORTANT**: Accept runs from the main repository root, NOT from a WP worktree.

```bash
# If you're in a worktree, return to main first:
cd $(git rev-parse --show-toplevel)

# Then run accept:
spec-kitty accept
```

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Discovery (mandatory)

Before running the acceptance workflow, gather the following:

1. **Feature slug** (e.g., `005-awesome-thing`). If omitted, detect automatically.
2. **Acceptance mode**:
   - `pr` when the feature will merge via hosted pull request.
   - `local` when the feature will merge locally without a PR.
   - `checklist` to run the readiness checklist without committing or producing merge instructions.
3. **Validation commands executed** (tests/builds). Collect each command verbatim; omit if none.
4. **Acceptance actor** (optional, defaults to the current agent name).

Ask one focused question per item and confirm the summary before continuing. End the discovery turn with `WAITING_FOR_ACCEPTANCE_INPUT` until all answers are provided.

## Execution Plan

1. Compile the acceptance options into an argument list:
   - Always include `--actor "__AGENT__"`.
   - Append `--feature "<slug>"` when the user supplied a slug.
   - Append `--mode <mode>` (`pr`, `local`, or `checklist`).
   - Append `--test "<command>"` for each validation command provided.
2. Run `{SCRIPT}` (the CLI wrapper) with the assembled arguments **and** `--json`.
3. Parse the JSON response. It contains:
   - `summary.ok` (boolean) and other readiness details.
   - `summary.outstanding` categories when issues remain.
   - `instructions` (merge steps) and `cleanup_instructions`.
   - `notes` (e.g., acceptance commit hash).
4. Present the outcome:
   - If `summary.ok` is `false`, list each outstanding category with bullet points and advise the user to resolve them before retrying acceptance.
   - If `summary.ok` is `true`, display:
     - Acceptance timestamp, actor, and (if present) acceptance commit hash.
     - Merge instructions and cleanup instructions as ordered steps.
     - Validation commands executed (if any).
5. When the mode is `checklist`, make it clear no commits or merge instructions were produced.

## Output Requirements

- Summaries must be in plain text (no tables). Use short bullet lists for instructions.
- Surface outstanding issues before any congratulations or success messages.
- If the JSON payload includes warnings, surface them under an explicit **Warnings** section.
- Never fabricate results; only report what the JSON contains.

## Error Handling

- If the command fails or returns invalid JSON, report the failure and request user guidance (do not retry automatically).
- When outstanding issues exist, do **not** attempt to force acceptance—return the checklist and prompt the user to fix the blockers.