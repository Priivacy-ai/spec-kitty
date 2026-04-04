---
title: How to Set Up Project Governance
description: Configure your project charter, generate structured governance config, and keep it in sync.
---

# How to Set Up Project Governance

Spec Kitty uses a charter to govern how agents behave during workflow actions. This guide walks you through creating a charter, generating structured config from it, and keeping everything in sync as your project evolves.

## Prerequisites

- Spec Kitty 2.x installed
- A project initialized with `spec-kitty init`

## Understanding the 3-Layer Model

Governance is built on three layers. Only the first layer is human-edited; the other two are derived automatically.

### Layer 1: Charter (`charter.md`)

The single authoritative policy document. It lives at `.kittify/charter/charter.md` and is written in markdown. You create it through the interview process or write it by hand. This is the only governance file you should ever edit directly.

### Layer 2: Extracted Config (YAML files)

Machine-readable config derived deterministically from your charter. These files are overwritten every time you run sync or generate:

- `governance.yaml` -- Testing standards, quality gates, performance targets, branching rules, and doctrine selections
- `directives.yaml` -- Numbered project rules with severity levels and action scopes
- `metadata.yaml` -- Hash of the charter, timestamp of last sync

### Layer 3: Doctrine References (`library/*.md`)

Detailed guidance documents for the paradigms, directives, and tools you selected. These are copied from the packaged doctrine library during generation.

### How the Layers Connect

```
charter.md    (you edit this)
       |
   [sync / generate]
       |
       +-- governance.yaml     (auto-generated)
       +-- directives.yaml     (auto-generated)
       +-- metadata.yaml       (auto-generated)
       +-- library/*.md        (auto-generated)
```

When you run a workflow action (`/spec-kitty.specify`, `/spec-kitty.implement`, etc.), the runtime reads the extracted config and injects relevant governance context into the agent prompt.

---

## Step 1: Run the Interview

The interview captures your project's policy decisions and saves them as structured answers.

### Quick Path (Non-Interactive)

Use `--defaults` to accept deterministic defaults without prompts. Good for bootstrapping or CI:

```bash
spec-kitty charter interview \
  --profile minimal \
  --defaults \
  --json
```

### Full Interactive Path

For a thorough setup, use the comprehensive profile which asks 11 questions:

```bash
spec-kitty charter interview \
  --profile comprehensive
```

### What the Interview Asks

**Minimal profile (8 questions):**

| Question | What it controls |
|----------|-----------------|
| Project intent | Policy summary in the charter preamble |
| Languages and frameworks | Styleguide selection (e.g., Python) |
| Testing requirements | Test framework, minimum coverage |
| Quality gates | Linting, type checking, pre-commit hooks |
| Review policy | Required PR approvals, branch strategy |
| Performance targets | CLI timeout thresholds |
| Deployment constraints | Branch naming and protection rules |

**Comprehensive profile adds 4 more:**

| Question | What it controls |
|----------|-----------------|
| Documentation policy | Added as a project directive |
| Risk boundaries | Added as a project directive |
| Amendment process | How the charter itself can be changed |
| Exception policy | How to handle one-off policy exceptions |

### Override Selections

You can override doctrine selections on the command line:

```bash
spec-kitty charter interview \
  --profile minimal \
  --defaults \
  --selected-paradigms "test-first" \
  --selected-directives "TEST_FIRST" \
  --available-tools "spec-kitty,git,python,pytest,ruff,mypy,poetry" \
  --json
```

The interview saves its answers to `.kittify/charter/interview/answers.yaml`.

---

## Step 2: Generate the Charter

Generate the charter markdown and all derived files from your interview answers:

```bash
spec-kitty charter generate --from-interview --json
```

This does two things in sequence:

1. Renders `charter.md` from your answers and doctrine templates
2. Automatically runs sync to extract structured YAML

After generation, your `.kittify/charter/` directory contains the full governance bundle.

### Overwrite an Existing Charter

If you already have a charter and want to regenerate from scratch:

```bash
spec-kitty charter generate --from-interview --force --json
```

### Choose a Template Set

Override the doctrine template set if your project needs a different workflow shape:

```bash
spec-kitty charter generate \
  --from-interview \
  --template-set plan-default \
  --json
```

Available template sets: `software-dev-default`, `plan-default`, `documentation-default`, `research-default`.

---

## Step 3: Check Status

After generation (or at any time), check whether your governance config is current:

```bash
spec-kitty charter status --json
```

This reports:

- **synced** -- The extracted config matches the current charter
- **stale** -- The charter has been edited since the last sync

When status shows "stale", agents may be working with outdated policy. Run sync to fix it.

---

## Step 4: Sync After Manual Edits

When you edit `charter.md` by hand, sync the changes to extracted config:

```bash
spec-kitty charter sync --json
```

Sync is idempotent. If the charter hash has not changed since the last sync, extraction is skipped. To force re-extraction regardless:

```bash
spec-kitty charter sync --force --json
```

---

## Step 5: Understand Context Loading

During workflow actions, the runtime automatically loads governance context into agent prompts. You do not need to call this manually during normal use.

### How It Works

When you run `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.implement`, or `/spec-kitty.review`, the runtime calls:

```bash
spec-kitty charter context --action <action> --json
```

This returns governance text tailored to the current action.

### Context Modes

| Mode | When it fires | What the agent sees |
|------|--------------|---------------------|
| Bootstrap | First time an action loads context | Full policy summary (up to 8 bullets) plus a list of reference docs |
| Compact | Subsequent loads for the same action | Resolved paradigms, directives, tools, and template set only |
| Missing | No charter exists | Instructions telling the agent to create one |

First-load state is tracked per action in `.kittify/charter/context-state.json`. Each action (specify, plan, implement, review) has an independent first-load timestamp.

### Manual Invocation for Debugging

If you want to see exactly what governance context an action receives:

```bash
spec-kitty charter context --action implement --json
```

This is useful when diagnosing unexpected agent behavior during a workflow step.

---

## Anti-Patterns to Avoid

### Editing Derived Files Directly

`governance.yaml`, `directives.yaml`, and `library/*.md` are overwritten on every sync or generate. Any manual changes to these files will be lost. Always edit `charter.md` instead, then run sync.

### Skipping the Interview

Running generate without an interview produces generic defaults. The charter is most valuable when it contains your project's actual policy decisions -- testing thresholds, review requirements, branching rules. Take the time to answer the questions.

### Working with a Stale Charter

If you edit `charter.md` but forget to sync, agents will work with outdated policy from the previous extraction. Run `spec-kitty charter status --json` to check, and `spec-kitty charter sync --json` to fix.

---

## Complete Workflow Example

Set up governance for a new project from scratch:

```bash
# 1. Run the interview
spec-kitty charter interview \
  --profile comprehensive

# 2. Generate charter and extracted config
spec-kitty charter generate --from-interview --json

# 3. Verify everything is in sync
spec-kitty charter status --json

# 4. Start working -- governance context loads automatically
/spec-kitty.specify "Build user authentication module"
```

Later, after updating your charter:

```bash
# Edit the charter
$EDITOR .kittify/charter/charter.md

# Sync changes
spec-kitty charter sync --json

# Verify
spec-kitty charter status --json
```

---

## Command Reference

- [CLI Commands](../reference/cli-commands.md) -- Full CLI reference including charter subcommands

## See Also

- [Create a Specification](create-specification.md) -- Start a feature with governance active
- [Switch Missions](switch-missions.md) -- How missions interact with governance
- [Non-Interactive Init](non-interactive-init.md) -- Automated project setup including charter

## Background

- [Mission System](../explanation/mission-system.md) -- How missions use governance context
