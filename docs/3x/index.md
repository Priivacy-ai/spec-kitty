---
title: Spec Kitty 3.x — Charter Era
description: Landing page for current Spec Kitty 3.x Charter-era documentation.
---

# Spec Kitty 3.x — Charter Era

You are looking at Spec Kitty 3.x Charter-era documentation. This is the current product.

## What is Charter?

Charter is the governance layer introduced in Spec Kitty 3.x. A single human-edited file
(`charter.md`) drives a synthesis pipeline that produces structured context for every agent
mission action. The flow is:

```
charter.md  →  charter synthesize  →  charter bundle  →  governed agent invocation
```

When you run `spec-kitty next --agent <name> --mission <slug>`, the runtime automatically injects
the relevant Charter context into the agent prompt. Governance is enforced without manual
intervention on every mission action.

For the full mental model, see [How Charter Works](charter-overview.md).

---

## Documentation by Type

### Tutorials — Learning-Oriented

Step-by-step walkthroughs for new users.

- [Governed Charter Workflow End-to-End](../tutorials/charter-governed-workflow.md) — Start from a fresh repo, set up governance, synthesize doctrine, and run a governed mission action
- [Getting Started with Spec Kitty](../tutorials/getting-started.md) — First project from scratch
- [Your First Feature](../tutorials/your-first-feature.md) — Implement a feature with the full workflow

### How-To Guides — Task-Oriented

Focused guides for specific operator tasks.

- [How to Set Up Project Governance](../how-to/setup-governance.md) — Charter interview, generate, and sync
- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md) — `charter synthesize`, `charter resynthesize`, bundle validation
- [How to Run a Governed Mission](../how-to/run-governed-mission.md) — `spec-kitty next --agent` with Charter context injection
- [How to Manage the Glossary](../how-to/manage-glossary.md) — Living glossary, Charter integration, retrospective proposals
- [How to Use the Retrospective Learning Loop](../how-to/use-retrospective-learning.md) — `retrospect summary`, `agent retrospect synthesize`
- [Troubleshooting Charter Failures](../how-to/troubleshoot-charter.md) — Stale bundle, missing doctrine, compact-context, retro gate failures

### Reference — Authoritative Specifications

Precise CLI and schema references.

- [Charter CLI Reference](../reference/charter-commands.md) — All `charter` subcommands with flags
- [CLI Commands](../reference/cli-commands.md) — Full spec-kitty CLI reference including Charter-era additions
- [Profile Invocation Reference](../reference/profile-invocation.md) — `ask`, `advise`, `do`, invocation trail
- [Retrospective Schema Reference](../reference/retrospective-schema.md) — `retrospective.yaml` schema, proposal kinds, exit codes
- [Governance Files Reference](governance-files.md) — Every file in `.kittify/charter/`

### Explanation — Conceptual Background

Understanding-oriented pages that explain why things work the way they do.

- [How Charter Works](charter-overview.md) — Mental model: doctrine → DRG → governed context
- [Understanding Charter: Synthesis, DRG, and Governed Context](../explanation/charter-synthesis-drg.md) — Deep dive into synthesis and the Directive Relationship Graph
- [Understanding Governed Profile Invocation](../explanation/governed-profile-invocation.md) — The `(profile, action, governance-context)` triple
- [Understanding the Retrospective Learning Loop](../explanation/retrospective-learning-loop.md) — Why retrospectives exist and how the gate model works

---

## Migration

Upgrading from an earlier version? See:

- [Migrating from 2.x / Early 3.x](../migration/from-charter-2x.md) — What changed, migration steps, and known failure modes

---

## What Is Archived

Documentation for Spec Kitty 2.x is preserved in [`docs/2x/`](../2x/index.md) for reference. The
2.x governance model did not include the DRG-backed synthesis pipeline or the retrospective
learning loop. If you are running a current project, use the 3.x documentation above.

---

## See Also

- [How Charter Works](charter-overview.md) — deeper mental model
- [Governance Files Reference](governance-files.md) — file reference
