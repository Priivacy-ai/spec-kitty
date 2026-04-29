---
title: Troubleshooting Charter Failures
description: Diagnose and fix stale bundle, missing doctrine, compact-context, retrospective gate, and synthesizer rejection failures.
---

# Troubleshooting Charter Failures

This guide covers the most common Charter failure modes and how to fix them.

For background, see [How Charter Works](../3x/charter-overview.md).

---

## 1. Stale bundle

**Symptoms**:
- `uv run spec-kitty charter status` reports drift between `charter.md` and the bundle
- `spec-kitty next` injects outdated governance context into agent prompts
- Agent behavior does not reflect recent changes you made to `charter.md`

**What is happening**: `charter.md` was edited after the last synthesis run, so the derived
bundle files no longer match the authoritative source.

**Fix**:

```bash
# 1. Re-sync charter.md to YAML config files
uv run spec-kitty charter sync

# 2. Check for graph-native decay
uv run spec-kitty charter lint

# 3. Re-run synthesis
uv run spec-kitty charter synthesize

# 4. Re-validate the bundle
uv run spec-kitty charter bundle validate

# 5. Confirm no drift
uv run spec-kitty charter status
```

---

## 2. Missing doctrine

**Symptoms**:
- `uv run spec-kitty charter status` reports no bundle, an empty bundle, or missing `.kittify/doctrine/`
- `spec-kitty next` fails or warns that no governance context is available
- Agent prompts receive no Charter context

**What is happening**: The synthesis step has not been run, or the `.kittify/doctrine/` directory
is missing or empty.

**Fix**:

```bash
# 1. Run the full synthesis flow
uv run spec-kitty charter synthesize

# 2. Validate
uv run spec-kitty charter bundle validate

# 3. Confirm
uv run spec-kitty charter status
```

If `charter synthesize` fails because `charter.md` does not exist:

```bash
# Run the interview and generate a charter.md first
uv run spec-kitty charter interview --profile minimal --defaults
uv run spec-kitty charter generate --from-interview

# Then synthesize
uv run spec-kitty charter synthesize
uv run spec-kitty charter bundle validate
```

---

## 3. Compact-context limitation

**Symptoms**:
- Governed mission actions receive incomplete Charter context
- Large project governance appears to be truncated in agent prompts
- Agents reference only a subset of your directives

**What is happening**: When the DRG context payload for an action is too large to include in full,
the runtime falls back to **compact-context mode** — a summarized view that includes resolved
paradigms, directives, and tool list but omits full doctrine library text.

This is a known limitation (see issue #787 in the project issue tracker; check that issue for
current resolution status).

**Workarounds**:
- Reduce the scope of `charter.md` by removing directives that are not relevant to the current
  project phase or that overlap significantly with other directives.
- Break a very large project governance layer into smaller, focused governance domains, each with
  its own charter.
- Use `charter resynthesize --topic <selector>` to regenerate only the high-priority directives
  and ensure they are correctly represented in the DRG.

---

## 4. Retrospective gate failure

**Symptoms**:
- `spec-kitty next` blocks at mission terminus with a retrospective gate error
- Mission cannot transition to `done`
- You see a message like "Charter does not authorize operator-skip in autonomous mode"

**What is happening**: The retrospective learning loop gate is blocking mission completion. In
autonomous mode, the retrospective is mandatory and cannot be skipped. In HiC mode, the gate
offered a retrospective and requires either running it or explicitly skipping it.

**Fix for HiC mode**:

```bash
# 1. View pending retrospective (summary)
uv run spec-kitty retrospect summary

# 2. Preview proposals for the blocked mission
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug

# 3. Apply proposals (or skip in HiC mode by responding 'n' with a reason at the terminus prompt)
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug --apply
```

**Fix for autonomous mode**: The retrospective cannot be skipped. If the facilitator failed:

```bash
# Check the retrospective record
# .kittify/missions/<mission_id>/retrospective.yaml

# View the summary for diagnostics
uv run spec-kitty retrospect summary

# Check for facilitator errors in the event log
# kitty-specs/<slug>/status.events.jsonl (filter by event_name prefix "retrospective.")
```

If the facilitator itself errored (exit code 2 with "Retrospective facilitator failed"), check
the retrospective YAML for schema errors and the status events file for the error event. Once
the underlying data issue is fixed, re-run `spec-kitty next` to retry the gate.

---

## 5. Synthesizer rejection

**Symptoms**:
- `uv run spec-kitty agent retrospect synthesize --mission <slug> --apply` exits with non-zero code
- Proposals are not applied
- The output shows "Conflict detection is fail-closed: no proposals applied"

**What is happening**: Two or more proposals conflict with each other (e.g., both try to add the
same glossary term with different definitions). The synthesizer fails closed and applies nothing.

**Fix**:

```bash
# 1. Run dry-run to see the conflict details
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug

# 2. Read the conflict report — it names the conflicting proposals and the conflicting field

# 3. Manually resolve the conflict by editing charter.md to pre-apply the correct version
$EDITOR .kittify/charter/charter.md

# 4. Re-run synthesis to propagate the manual edit
uv run spec-kitty charter sync
uv run spec-kitty charter synthesize
uv run spec-kitty charter bundle validate

# 5. Re-run retrospect synthesize — conflicting proposals should now be resolved
uv run spec-kitty agent retrospect synthesize --mission my-feature-slug --apply
```

---

## Diagnostic Quick Reference

| Question | Command |
|---|---|
| Is the bundle current? | `uv run spec-kitty charter status` |
| Are there graph decay issues? | `uv run spec-kitty charter lint` |
| Is the bundle schema valid? | `uv run spec-kitty charter bundle validate` |
| What retrospectives are pending? | `uv run spec-kitty retrospect summary` |
| What proposals exist for a mission? | `uv run spec-kitty agent retrospect synthesize --mission <slug>` |

---

## See Also

- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md)
- [How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md)
- [Retrospective Schema Reference](../reference/retrospective-schema.md)
- [How Charter Works](../3x/charter-overview.md)
