---
name: spec-kitty.accept
description: Validate an approved mission before merge
user-invocable: true
---
## Startup Upgrade Check

Run this at most once per active agent session before the first Spec Kitty command workflow.
If you already ran `spec-kitty upgrade --agent-check --json` in this session, reuse that result and skip this block.
Do not run or announce an upgrade check again for later Spec Kitty commands in the same session.
Otherwise, before continuing, run:

```bash
spec-kitty upgrade --agent-check --json
```

If JSON `action` is `none`, continue.
If `action` is `auto_upgrade`, run `upgrade_command` before continuing. If it fails, tell the user and continue with the current Spec Kitty version.
If `action` is `guidance`, show `upgrade_note` briefly, then continue.
If `action` is `prompt`, ask the user with the host-native question UI when available:

`Spec Kitty {latest_version} is available. You are on {installed_version}. Upgrade now?`

Use these choices:

1. Upgrade now (recommended) - record `upgrade_now`, run `upgrade_command`, then continue.
2. Always keep me up to date - record `always`, run `upgrade_command`, then continue.
3. Not now - record `not_now`, then continue.
4. Never ask again - record `never_ask`, then continue.

Record the selected choice before continuing:

```bash
spec-kitty upgrade --agent-choice <upgrade_now|always|not_now|never_ask> --agent-latest <latest_version> --json
```

If no host-native question UI is available, present the same four choices in plain text and wait for the user.
In non-interactive hosts, choose `not_now` and continue.


# /spec-kitty.accept - Validate Mission Readiness

**Version**: 0.12.0+

## Purpose

Validate that every work package is complete and the mission is ready to merge.
This step runs the acceptance gate, surfaces any blocking diagnostics, and only
clears the path to merge once the gate passes.

---

## 📍 WORKING DIRECTORY: Run from the MAIN repository

**IMPORTANT**: Acceptance runs from the primary repository checkout root, NOT
from a work-package worktree.

```bash
# If you are inside a worktree, return to the main checkout first:
cd $(git rev-parse --show-toplevel)
```

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`. The resolver disambiguates by `mission_id` and returns a structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

The content of the user's message that invoked this skill (everything after the skill invocation token, e.g. after `/spec-kitty.<command>` or `$spec-kitty.<command>`) is the User Input referenced elsewhere in these instructions.

You **MUST** consider this user input before proceeding (if not empty).

## Steps

### 1. Run the Acceptance Gate

Run the acceptance command from the repository root:

```bash
spec-kitty accept --mission <handle>
```

This validates that all work packages are `approved` or `done`, checks the
readiness gates, and reports what (if anything) still blocks merge.

### 2. Inspect Acceptance Diagnostics

Read the command output carefully:

- If the gate **passes**, the output confirms the mission is ready to merge and
  prints the merge instructions.
- If the gate **fails**, the output lists each outstanding category (for
  example: WPs not yet approved, failing checks, or unresolved review
  feedback). Treat every outstanding item as a blocker.

### 3. Resolve Any Gate Failures

For each blocker reported:

- Route the affected work package back through implement/review as needed.
- Re-run the relevant tests or checks until they pass.
- Re-run `spec-kitty accept --mission <handle>` and confirm the gate is now
  clean. Do **not** force acceptance past an unresolved blocker.

### 4. Proceed to Merge

Only after the acceptance gate passes:

```bash
spec-kitty merge --mission <handle>
```

Follow the merge instructions printed by the acceptance command (and any
cleanup steps it lists).

## Output

After completing this step:

- The acceptance gate has passed for `<handle>`.
- All blocking diagnostics have been resolved (or none were present).
- Merge instructions have been surfaced to the operator.

**Next step**: `spec-kitty next --agent <name>` will advance to merge, or run
`spec-kitty merge --mission <handle>` directly.
