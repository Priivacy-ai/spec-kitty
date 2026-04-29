---
title: How Charter Works
description: The Charter mental model — synthesis, DRG, governed context, and profile invocation.
---

# How Charter Works

Charter is the governance layer that turns your project's policy document (`charter.md`) into
structured context that every agent mission action automatically receives. This page explains the
mental model. For a step-by-step walkthrough, see the
[Governed Charter Workflow Tutorial](../tutorials/charter-governed-workflow.md).

> **Key invariant**: `.kittify/charter/charter.md` is the human policy source of truth. Do not
> hand-edit derived files such as `governance.yaml`, `directives.yaml`, `metadata.yaml`,
> `references.yaml`, `context-state.json`, synthesis manifests, or provenance sidecars. Agent
> synthesis input under `.kittify/charter/generated/` is produced by the harness, not by routine
> operator edits.

---

## What Charter Does

Charter solves a specific problem: agent prompts need consistent, project-accurate policy context,
but that context must come from a single authoritative source that you as an operator control.

The mechanism:

1. You write (or generate via interview) a `charter.md` file that captures your project's policy
   decisions — testing standards, quality gates, branching rules, directive selections.
2. The synthesis pipeline reads that file and produces a structured **charter bundle** of YAML
   artifacts in `.kittify/charter/`.
3. When `spec-kitty next` invokes an agent profile for a mission action, the runtime injects
   the relevant charter context into the prompt automatically. The agent does not invent governance;
   it reads and complies with what the charter says.

---

## Synthesis Flow

The full Charter setup flow uses these commands in sequence:

```bash
# Step 1 — Capture policy decisions interactively (or use --defaults for CI)
uv run spec-kitty charter interview

# Step 2 — Generate charter.md and initial bundle from interview answers
uv run spec-kitty charter generate --from-interview

# Step 3 — Check for graph-native decay (orphaned directives, contradictions, etc.)
uv run spec-kitty charter lint

# Step 4 — Validate + promote agent-generated doctrine artifacts to .kittify/doctrine/
uv run spec-kitty charter synthesize

# Step 5 — Validate the charter bundle against the CharterBundleManifest v1.0.0 schema
uv run spec-kitty charter bundle validate

# Check sync status at any time
uv run spec-kitty charter status
```

**`charter context`** is a separate runtime/debug command for rendering action-specific
governance context for a specific workflow action. It is not part of the synthesis pipeline:

```bash
# Render what governance context an agent would receive for the 'implement' action
uv run spec-kitty charter context --action implement --json
```

After editing `charter.md` by hand, re-sync the YAML config files with:

```bash
uv run spec-kitty charter sync
```

For partial regeneration of a specific directive or tactic without touching unrelated artifacts:

```bash
uv run spec-kitty charter resynthesize --topic directive:PROJECT_001
```

---

## The DRG-Backed Context Model

The charter bundle is not a flat file — it is backed by a **Directive Relationship Graph (DRG)**.
The DRG is a directed graph whose nodes are directives, tactics, and glossary terms, and whose
edges use typed relations such as `scope`, `requires`, `suggests`, `vocabulary`, `instantiates`,
`replaces`, and `delegates_to`.

When `spec-kitty next` prepares a prompt for a mission action (for example, `implement`), the
runtime traverses the DRG from the entry point for that action and collects the relevant subgraph.
This is **governed profile invocation**: the agent receives a `(profile, action, governance-context)`
triple, where the governance context is the DRG-derived subgraph rendered as structured text.

The agent cannot see or modify the DRG directly. It receives the rendered context and acts in
accordance with the directives it finds there.

---

## Bootstrap vs Compact Context

The DRG traversal for a given action can produce large context payloads for complex projects.

- **Bootstrap mode**: the first time an action loads context (or when the charter is freshly
  synthesized), the runtime injects the full relevant DRG subgraph. The agent sees all applicable
  directives and tactics.
- **Compact-context mode**: when the DRG context payload is too large to include in full, the
  runtime falls back to a summarized view — resolved paradigms, directives, and tool list only,
  without the full library text. This is a known limitation (see issue #787 in the project tracker;
  check that issue for current resolution status).

Do not assume full-context behavior unconditionally. Large governance layers may trigger
compact-context mode, causing agents to receive less detail.

---

## Key Governance Files

| File | Written by | Purpose |
|---|---|---|
| `.kittify/charter/charter.md` | **Human** | Policy source of truth — the only file you edit |
| `.kittify/charter/governance.yaml` | Auto-generated (`charter sync`) | Testing, quality, performance, branch, and doctrine-selection config |
| `.kittify/charter/directives.yaml` | Auto-generated (`charter sync`) | Extracted directive list |
| `.kittify/charter/metadata.yaml` | Auto-generated (`charter sync`) | Charter hash, extraction timestamp, and parser metadata |
| `.kittify/charter/references.yaml` | Auto-generated (`charter generate`) | Reference manifest for shipped and local doctrine content |
| `.kittify/charter/generated/` | Agent harness | Candidate doctrine YAML consumed by `charter synthesize` |
| `.kittify/charter/synthesis-manifest.yaml` | Auto-generated (`charter synthesize`) | Manifest for promoted project-local doctrine artifacts |
| `.kittify/charter/provenance/*.yaml` | Auto-generated (`charter synthesize`) | Provenance sidecars for synthesized doctrine artifacts |
| `.kittify/doctrine/` | Auto-generated (synthesize) | Project-local doctrine promoted by synthesizer |

See [Governance Files Reference](governance-files.md) for the full table.

---

## See Also

- [Governance Files Reference](governance-files.md) — authoritative file table
- [How to Set Up Project Governance](../how-to/setup-governance.md) — initial setup walkthrough
- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md) — day-to-day synthesis
- [Understanding Charter: Synthesis, DRG, and Governed Context](../explanation/charter-synthesis-drg.md) — deeper explanation
