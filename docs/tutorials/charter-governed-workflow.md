---
title: "Tutorial: Governed Charter Workflow End-to-End"
description: Learn to set up governance, synthesize doctrine, and run a governed mission action from scratch.
---

# Tutorial: Governed Charter Workflow End-to-End

> **Background**: If you're new to Charter, read [How Charter Works](../3x/charter-overview.md) first.

## What you'll build

By the end of this tutorial, you will have a project with Charter governance fully configured,
doctrine synthesized into a valid bundle, and at least one governed mission action run. You will
understand the complete operator flow: from a blank git repository to agents receiving consistent,
policy-backed context on every action.

## Prerequisites

- Spec Kitty 3.x installed — verify with `uv run spec-kitty --version`
- A git repository (new or existing). Charter requires a git working tree.
- A Spec Kitty project scaffold. For a fresh repository, run `uv run spec-kitty init --ai claude --non-interactive` before the Charter interview.
- Optional: a Spec Kitty account if you want SaaS sync enabled. Steps that require SaaS sync are
  labeled with a note.

---

## Step 1: Initialize Spec Kitty and governance

The first step creates the Spec Kitty project scaffold, captures your project's policy decisions,
and generates the charter bundle.

### 1a. Initialize the project scaffold

If this is a fresh git repository, initialize Spec Kitty first:

```bash
uv run spec-kitty init --ai claude --non-interactive
```

`init` creates `.kittify/config.yaml`, agent command templates, and ignore files. It is
idempotent, so rerunning it in an already-initialized project exits cleanly. Use the agent key
that matches your workflow; this tutorial uses `claude` because the later `next` examples use
`--agent claude`.

### 1b. Run the interview

The interview collects your project's policy decisions and saves them as structured answers. Use
the minimal profile to start; upgrade to comprehensive later if needed.

```bash
# Interactive mode — follow the prompts
uv run spec-kitty charter interview --profile minimal

# Non-interactive mode — use deterministic defaults (useful for CI or bootstrapping)
uv run spec-kitty charter interview --profile minimal --defaults --json
```

The interview asks about your project intent, language and framework choices, testing policy,
quality gates, review requirements, performance targets, and deployment constraints. Answers are
saved to `.kittify/charter/interview/answers.yaml`.

This step is interactive when you omit `--defaults`. Follow the prompts to describe your project.

### 1c. Generate the charter bundle

Generate `charter.md` and all derived governance files from your interview answers:

```bash
uv run spec-kitty charter generate --from-interview --json
```

This renders `charter.md` and `references.yaml` from your answers and doctrine templates, runs
`charter sync` to derive YAML config, then automatically stages the tracked `charter.md` via
`git add`. After this step, `.kittify/charter/` contains the core governance bundle.

> **Note**: `charter generate` requires a git working tree. If you run it outside a git repo it
> will exit non-zero with an error message directing you to run `git init` first.

---

## Step 2: Validate the bundle

Before promoting doctrine, verify the bundle is clean.

### 2a. Check for graph-native decay

```bash
uv run spec-kitty charter lint
```

`charter lint` detects orphaned directives (referenced in the DRG but without a backing tactic),
contradictions between directives, and staleness (directives whose provenance points to a deleted
or superseded shipped directive). A clean lint means the bundle graph is internally consistent.

### 2b. Validate the bundle schema

```bash
uv run spec-kitty charter bundle validate
```

This validates the charter bundle against the CharterBundleManifest v1.0.0 schema. It checks that
all required files are present, correctly structured, and consistent. A clean validate means you
have a valid bundle that the runtime can use.

### 2c. Check sync status

```bash
uv run spec-kitty charter status
```

Status reports whether your bundle matches the current `charter.md`. If the status shows the
bundle is current after lint and validate pass, you are ready to synthesize.

---

## Step 3: Synthesize doctrine

Synthesis promotes agent-generated project-local doctrine artifacts into `.kittify/doctrine/`,
making them available for runtime context injection.

### 3a. Dry-run first

Preview what synthesis would do without making any changes:

```bash
uv run spec-kitty charter synthesize --dry-run
```

The dry-run stages and validates artifacts but does not promote them. Review the output to confirm
the synthesis plan matches your expectations.

### 3b. Apply synthesis

When the dry-run looks correct, apply:

```bash
uv run spec-kitty charter synthesize
```

On a fresh project where `.kittify/charter/generated/` is missing or empty (i.e., the LLM harness
has not yet written agent artifacts), synthesize creates the minimal artifact set: a `.kittify/doctrine/`
directory marker and a `PROVENANCE.md` record. The runtime falls back to shipped doctrine for all
artifact lookups until a full synthesis run with agent-generated content completes.

### 3c. Confirm status

```bash
uv run spec-kitty charter status
```

After a successful synthesis, status should show no drift. You are ready to run a governed mission.

---

## Step 4: Run a governed mission action

With governance set up and doctrine synthesized, you can run a governed mission action. Charter
context is now injected automatically.

First, create a mission to work on (if you don't have one already):

```bash
uv run spec-kitty specify my-first-feature
```

The command returns a `mission_slug` such as `my-first-feature-01KQEE5E`. Use that full slug
for `spec-kitty next`; the short feature name alone is not enough once Spec Kitty has appended
the mission identity suffix.

Then drive the mission using `spec-kitty next`. The `--agent` flag identifies the agent name used
for the issued action; `--mission` identifies the mission by its full slug:

```bash
uv run spec-kitty next --agent claude --mission my-first-feature-01KQEE5E --json
```

In query mode (when `--result` is omitted), `next` reads and prints the current mission state
without advancing it. This is useful to see what step is next before acting.

To advance the mission after completing a step, pass `--result`:

```bash
uv run spec-kitty next --agent claude --mission my-first-feature-01KQEE5E --result success --json
```

The runtime resolves the next step from the mission's state machine, builds the governed prompt
(including Charter context resolved from the bundle and doctrine layers), and returns the action
and `prompt_file` for the agent to execute. `next` itself does not spawn the agent.

> **What governed means**: each prompt the agent receives includes the relevant DRG-derived
> governance context for the current action (specify, plan, implement, review, etc.). The agent
> does not invent governance — it reads what the charter says.

---

## Step 5: View the retrospective summary

When a mission completes, the retrospective learning loop captures findings, proposals, and
governance gaps. View the cross-mission summary with:

```bash
uv run spec-kitty retrospect summary
```

> **Note**: `retrospect summary` reads `.kittify/missions/*/retrospective.yaml` and
> `kitty-specs/*/status.events.jsonl`. It requires at least one completed mission with a
> retrospective record. On a brand-new project with no completed missions, it will report zero
> missions in its summary — this is expected.

The summary shows counts (completed, skipped, failed, in-flight), top "not helpful" targets,
top missing glossary terms, and proposal acceptance statistics.

To see the output in machine-readable form:

```bash
uv run spec-kitty retrospect summary --json
```

---

## What's next

You've completed the full Charter governance loop. Here is where to go from here:

- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md) — partial resynthesis, provenance, recovery from stale bundles
- [How to Run a Governed Mission](../how-to/run-governed-mission.md) — composed steps, prompt resolution, blocked decisions
- [How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md) — preview and apply synthesis proposals
- [Understanding Charter: Synthesis, DRG, and the Bundle](../3x/charter-overview.md) — deeper conceptual background

---

## See also

- [How to Set Up Project Governance](../how-to/setup-governance.md)
- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md)
- [How to Run a Governed Mission](../how-to/run-governed-mission.md)
- [How Charter Works: Synthesis, DRG, and the Bundle](../3x/charter-overview.md)
