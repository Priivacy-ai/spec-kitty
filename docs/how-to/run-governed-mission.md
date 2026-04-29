---
title: How to Run a Governed Mission
description: Run spec-kitty next with Charter context injection, read JSON output, handle composed steps and blocked decisions.
---

# How to Run a Governed Mission

This guide covers running a mission action under Charter governance using `spec-kitty next`.

For background on governed profile invocation, see [How Charter Works](../3x/charter-overview.md).

---

## Before you begin

Confirm your governance is ready before running a mission:

1. Charter bundle is current: `uv run spec-kitty charter status`
2. Bundle validates: `uv run spec-kitty charter bundle validate`
3. Doctrine is synthesized: check that `.kittify/doctrine/` is present and populated

If the bundle is stale, run the synthesis flow first. See
[How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md).

---

## 1. Run a governed mission action

The primary loop command is `spec-kitty next`. It inspects the mission's state machine, evaluates
guards, and returns the next deterministic action with its prompt file:

```bash
uv run spec-kitty next --agent claude --mission my-feature-slug --json
```

`--agent` identifies the agent profile to invoke. `--mission` is the mission slug (the
human-readable identifier, e.g., `my-feature-slug`).

When `--result` is omitted, `next` operates in **query mode**: it reads and returns the current
mission state without advancing it. This is safe to call repeatedly to check what step is next.

```bash
# Query mode — inspect without advancing
uv run spec-kitty next --mission my-feature-slug --json
```

Charter context is injected automatically. When the bundle is current and `.kittify/doctrine/`
is populated, each invoked agent profile receives the relevant DRG-derived governance context
for the current action. You do not need to pass governance flags manually.

---

## 2. Read the output

`spec-kitty next --json` emits a structured decision object. Key fields:

| Field | Type | Description |
|---|---|---|
| `action` | string | The action the agent should perform (e.g., `specify`, `plan`, `implement`) |
| `mission_state` | string | Current state machine state (`not_started`, `in_progress`, `for_review`, etc.) |
| `step` | object | Current step details including step ID and prompt file path |
| `preview_step` | object | Next step preview (on fresh-run query) |
| `governance_context_loaded` | boolean | Whether Charter context was successfully injected |

A fresh-run query returns `mission_state: "not_started"` and a `preview_step` showing the first
step. Do not depend on `unknown` as the fresh-run state — that is a legacy value.

---

## 3. Advance through composed steps

To advance the mission after completing a step, report the result:

```bash
# Report success and get the next step
uv run spec-kitty next --agent claude --mission my-feature-slug --result success --json

# Report failure (mission may loop or escalate)
uv run spec-kitty next --agent claude --mission my-feature-slug --result failed --json

# Report blocked (mission pauses pending a decision)
uv run spec-kitty next --agent claude --mission my-feature-slug --result blocked --json
```

A composed mission (e.g., `software-dev`) has multiple steps: `discover`, `specify`, `plan`,
`implement`, `review`, and so on. Each call to `next --result success` advances the state machine
to the next step. The runtime returns the action and prompt file for that step.

---

## 4. Prompt resolution

`spec-kitty next` resolves which prompt template to use for the current step from the mission's
`mission-runtime.yaml` configuration. The step's `prompt_template` field points to a file in the
packaged doctrine missions directory.

When prompt resolution succeeds, the output includes a `step.prompt_file` path. When it fails
(for example, the mission type is unrecognized or the step template is missing), `next` returns a
non-zero exit code with a structured error explaining the resolution failure.

If you encounter a resolution failure:
- Verify the mission type is valid: `uv run spec-kitty mission list`
- Check that the mission slug matches a real mission: `uv run spec-kitty mission current`

---

## 5. Handle blocked decisions

When a mission action encounters a question that requires a concrete answer before proceeding,
the mission opens a Decision Moment and blocks. `spec-kitty next` will return with
`mission_state: "blocked"` or `result: "blocked"`.

To resolve a blocked decision:

```bash
# View the decision (from the --json output, extract the decision_id)
uv run spec-kitty next --mission my-feature-slug --json

# Resolve the decision with a final answer
uv run spec-kitty agent decision resolve <decision-id> \
  --mission my-feature-slug \
  --final-answer "yes" \
  --json
```

After resolving, resume the mission:

```bash
uv run spec-kitty next --agent claude --mission my-feature-slug --result success --json
```

You can also answer a decision inline while reporting a result:

```bash
uv run spec-kitty next --agent claude --mission my-feature-slug \
  --answer "approve" \
  --decision-id "input:review" \
  --result success \
  --json
```

---

## See Also

- [How Charter Works](../3x/charter-overview.md)
- [Understanding Governed Profile Invocation](../explanation/governed-profile-invocation.md)
- [Charter CLI Reference](../reference/charter-commands.md)
- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md)
