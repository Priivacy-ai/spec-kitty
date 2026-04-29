---
title: How to Set Up Project Governance
description: Configure your project charter, generate structured governance config, and keep it in sync.
---

# How to Set Up Project Governance

Spec Kitty uses a charter to govern how agents behave during workflow actions. This guide walks you through creating a charter, generating structured config from it, and keeping everything in sync as your project evolves.

## Prerequisites

- Spec Kitty 3.x installed — verify with `uv run spec-kitty --version`
- A project initialized with `uv run spec-kitty init` inside a git working tree

## Understanding the 3-Layer Model

Governance is built on three layers. Only the first layer is human-edited; the other two are derived automatically.

### Layer 1: Charter (`charter.md`)

The single authoritative policy document. It lives at `.kittify/charter/charter.md` and is written in markdown. You create it through the interview process or write it by hand. This is the only governance file you should ever edit directly.

### Layer 2: Extracted Config (YAML files)

Machine-readable config derived deterministically from your charter. These files are overwritten every time you run sync or generate:

- `governance.yaml` -- Testing standards, quality gates, performance targets, branching rules, and doctrine selections
- `directives.yaml` -- Numbered project rules with severity levels and action scopes
- `metadata.yaml` -- Hash of the charter, timestamp of last sync

### Layer 3: Doctrine References and Project Doctrine

`references.yaml` records the shipped and local doctrine references selected by the charter.
`charter synthesize` can then promote project-local doctrine artifacts into `.kittify/doctrine/`.
Current `charter generate` does not copy doctrine pages into an authoritative `library/*.md`
tree; runtime context resolves doctrine through the reference manifest and doctrine service.

### How the Layers Connect

```
charter.md    (you edit this)
       |
   [sync / generate]
       |
       +-- governance.yaml     (auto-generated)
       +-- directives.yaml     (auto-generated)
       +-- metadata.yaml       (auto-generated)
       +-- references.yaml     (auto-generated)
       +-- synthesis state     (after synthesize)
```

When you run a governed workflow action through `spec-kitty next`, the runtime reads the
extracted config and doctrine references, then renders relevant governance context into the
prompt file returned to the agent.

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
  --available-tools "spec-kitty,git,python,pytest,ruff,mypy,uv" \
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

> **Note (3.2.0a6+):** `charter generate` auto-tracks the produced
> `charter.md` (it stages the file via `git add` and ensures the required
> `.gitignore` entries exist for the derived artifacts). You do **not**
> need to run `git add charter.md` before `spec-kitty charter bundle
> validate` — the bundle is accepted immediately. If `generate` is run
> outside a git working tree it fails fast with an actionable error
> naming `git init` as the remediation.

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

During governed workflow actions, the runtime automatically loads governance context into agent
prompts. You do not need to call this manually during normal use.

### How It Works

When `spec-kitty next` builds a prompt for a mission action, the runtime uses the same context
builder exposed for debugging as:

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

`governance.yaml`, `directives.yaml`, `metadata.yaml`, `references.yaml`, runtime state, and
synthesis outputs are owned by CLI commands. Manual changes can be overwritten or can make bundle
validation misleading. Edit `charter.md` instead, then run sync and synthesis as needed.

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
uv run spec-kitty specify "Build user authentication module"
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

## Charter Synthesis Flow (3.x)

After setting up and syncing your governance (steps 1–4 above), run the Charter synthesis flow
to promote doctrine artifacts for runtime context injection. This is a 3.x addition to the
governance setup workflow.

**`charter synthesize` vs `charter sync` distinction**:
- `charter sync` syncs `charter.md` to YAML config files (`governance.yaml`, `directives.yaml`,
  `metadata.yaml`). Run it after manually editing `charter.md`.
- `charter synthesize` validates and promotes agent-generated doctrine artifacts to
  `.kittify/doctrine/` via the DRG-backed synthesis pipeline. Run it to make doctrine available
  for governed mission context injection.
- They are different operations. You typically run `charter sync` first (after editing), then
  `charter synthesize` to complete the promotion.

```bash
# 1. Check for graph-native decay before synthesis
uv run spec-kitty charter lint

# 2. Synthesize (dry-run first)
uv run spec-kitty charter synthesize --dry-run
uv run spec-kitty charter synthesize

# 3. Validate the bundle
uv run spec-kitty charter bundle validate

# 4. Confirm status
uv run spec-kitty charter status
```

Once synthesis completes successfully, governed mission actions via `spec-kitty next` will
automatically receive the current Charter context.

---

## Command Reference

- [CLI Commands](../reference/cli-commands.md) -- Full CLI reference including charter subcommands

## See Also

- [How Charter Works](../3x/charter-overview.md) -- Charter mental model and synthesis flow
- [How to Synthesize and Maintain Doctrine](synthesize-doctrine.md) -- Full synthesis workflow
- [Create a Specification](create-specification.md) -- Start a feature with governance active
- [Switch Missions](switch-missions.md) -- How missions interact with governance
- [Non-Interactive Init](non-interactive-init.md) -- Automated project setup including charter
- [Doctrine Packs](../doctrine/README.md) -- Optional pack selections, including [SPDD and the REASONS Canvas](../doctrine/spdd-reasons.md)

## Background

- [Mission System](../explanation/mission-system.md) -- How missions use governance context
