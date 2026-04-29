---
title: "Understanding Charter: Synthesis, DRG, and Governed Context"
description: How charter synthesize works, what the DRG is, how governed context flows to agents, and known limitations.
---

# Understanding Charter: Synthesis, DRG, and Governed Context

This document explains the Charter synthesis model and the DRG-backed context system. For a
practical walkthrough, see [How Charter Works](../3x/charter-overview.md). For step-by-step
how-to instructions, see [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md).

---

## What the charter bundle is

The **charter bundle** is the machine-readable synthesis of your `charter.md` governance document.
It is not a simple copy of the prose — it is a structured set of YAML artifacts that the runtime
can traverse, merge, and inject as context for specific workflow actions.

The bundle lives in `.kittify/charter/` and consists of:

- `governance.yaml` — resolved directives in structured form
- `directives.yaml` — extracted directive list with severity and action scope
- `metadata.yaml` — bundle metadata: charter hash, last-sync timestamp, provenance

Why is the bundle needed rather than raw prose? Because the runtime context injection requires a
structured artifact. When `spec-kitty next` prepares a prompt for the `implement` action, it
needs to select the directives that apply specifically to `implement` (not to `specify` or
`review`). A flat prose document cannot serve that purpose efficiently. The bundle provides the
structure for action-scoped context injection.

---

## How synthesis works

The synthesis pipeline has four logical phases:

1. **Parse**: `charter synthesize` reads `charter.md` and the interview answers. It also reads any
   agent-generated YAML from `.kittify/charter/generated/` (artifacts the LLM harness has written).

2. **DRG edge computation**: The synthesizer constructs the Directive Relationship Graph (DRG) by
   resolving relationships between directives, tactics, and glossary terms. Edges encode
   relationships such as "directive A implies directive B" or "tactic C specializes directive D."

3. **Directive resolution**: With the DRG computed, the synthesizer determines which artifacts
   need to be generated or updated. Artifacts whose provenance points to unchanged inputs are
   left intact (this is what makes `charter resynthesize --topic <selector>` work — only affected
   artifacts are regenerated).

4. **Emit bundle**: The synthesizer writes the resolved artifacts to `.kittify/doctrine/` (project-
   local doctrine) and updates the bundle files in `.kittify/charter/`. The `--dry-run` flag stops
   after validation, before the emit step.

The authoritative file throughout is always `charter.md`. The synthesizer reads it; it does not
write to it. Doctrine artifacts are outputs, not inputs.

---

## DRG edge computation

The **Directive Relationship Graph (DRG)** is a directed graph with three node types:
**directives**, **tactics**, and **glossary terms**. Edges encode relationships:

- *implies*: directive A's presence logically requires directive B to be active
- *overrides*: directive A supersedes directive B for the same concern area
- *specializes*: tactic C is a specific application of directive D
- *scopes-to*: glossary term E is most relevant for action F

When the runtime prepares context for a specific mission action (e.g., `implement`), it traverses
the DRG from the action's entry node and collects the relevant subgraph. The traversal follows
only the edges that are in-scope for that action, ensuring that agents for the `implement` action
receive implementation-relevant directives and tactics, not specification-phase concerns.

The DRG is not stored as a standalone file that you can inspect directly. It is computed by the
synthesizer and manifests as the structured content of the bundle artifacts.

---

## Bootstrap vs compact context

The DRG traversal for a given action can produce large payloads for complex governance structures.
Two modes handle this:

**Bootstrap mode**: On the first load for an action (or after a fresh synthesis), the full
relevant DRG subgraph is injected into the governed profile invocation. The agent sees all
applicable directives, tactics, and glossary terms for its current action, plus the full doctrine
library references.

**Compact-context mode**: When the DRG context payload exceeds the size threshold for inclusion,
the runtime falls back to compact-context mode. In this mode, the agent receives only the resolved
paradigm list, directive list, and tool list — without the full doctrine library text. This is a
known limitation (see issue #787 in the project issue tracker; check that issue for current
resolution status). Do not assume full-context behavior unconditionally on large governance layers.

First-load state is tracked per action in `.kittify/charter/context-state.json`. Each action
(specify, plan, implement, review) has an independent first-load timestamp.

---

## Why the authoritative vs generated distinction matters

Charter governance is built on a strict read/write boundary:

- **Authoritative files**: `charter.md` — human-edited, the source of truth
- **Generated files**: everything else in `.kittify/charter/` and `.kittify/doctrine/` — written
  by the synthesizer, never by hand

If you edit a generated file (for example, add a directive to `governance.yaml` directly), the
edit will be silently lost on the next `charter synthesize` run. The synthesizer rewrites generated
files from the authoritative source. There is no merge step.

`charter status` detects drift between `charter.md` and the bundle hash. `charter lint` detects
decay within the DRG (orphaned artifacts, contradictions, staleness). Both tools exist precisely
because the authoritative/generated boundary creates a risk of divergence if synthesis is not run
after charter edits.

---

## Known limitations

1. **Compact-context mode (issue #787)**: Large governance layers may trigger compact-context
   fallback, causing agents to receive summarized rather than full doctrine context. The workaround
   is to reduce governance scope or break the project into smaller governance domains.

2. **Fresh-project synthesis**: On a project where `.kittify/charter/generated/` is missing or
   empty (no agent-generated artifacts), `charter synthesize` produces only the minimal artifact
   set (directory marker and PROVENANCE.md). The runtime falls back to shipped doctrine until a
   full synthesis run with agent-generated content completes.

3. **Synthesis requires `charter.md`**: `charter synthesize` will exit non-zero if `charter.md`
   does not exist. Run `charter interview` and `charter generate` first.

---

## See Also

- [How Charter Works](../3x/charter-overview.md)
- [Governance Files Reference](../3x/governance-files.md)
- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md)
- [Troubleshooting Charter Failures](../how-to/troubleshoot-charter.md)
