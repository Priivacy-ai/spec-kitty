---
title: Context
description: "Context section landing page: the unified home for Spec Kitty's canonical glossary contexts and the stakeholder/audience persona catalog (Mission B, FR-009)."
doc_status: active
updated: '2026-06-27'
---
# Context

Domain context for Spec Kitty: the canonical glossary contexts, the
stakeholder/audience persona catalog, and the current Charter-era overview.

<!--
  #2053 LANDING ZONE (coordinate only — do NOT build the charter-landing page here).
  Under FR-008 / C-004 the live `docs/context` charter content was distilled + moved
  into this `docs/context/` section (never blind-deleted), and the old `3x/*`
  URLs redirect here via WP07 stubs:
    docs/context/charter-overview.md -> docs/context/charter-overview.md  (3x/charter-overview.html -> context/charter-overview.html)
    docs/context/governance-files.md -> docs/context/governance-files.md  (3x/governance-files.html -> context/governance-files.html)
    docs/context/index.md            -> folded into this page (below)      (3x/index.html            -> context/index.html)
  #2053 should later surface a dedicated top-level charter landing page sourced
  from these context pages. That implementation is OUT OF SCOPE for Mission B.
-->

This section is the unified home (Mission B, FR-009) for:

- **Glossary contexts** (`*.md`) — canonical terminology per bounded context,
  relocated from `docs/context/`. These remain the doctrine-extraction
  source consumed by `scripts/generate_contextive_glossaries.py` (C-006); the
  dashboard glossary seed files under `.kittify/glossaries/` are unchanged.
- **`audience/`** — architecture audience personas (internal/external),
  relocated from `docs/context/audience/`.
- **Charter-era overview** — the current Spec Kitty 3.2 Charter governance
  model, distilled here from the retired `docs/context` shadow tree (FR-008). See
  [How Charter Works](charter-overview.md) and the
  [Governance Files Reference](governance-files.md).

---

## Spec Kitty 3.2 Charter-era overview

You are looking at the current Spec Kitty 3.2 documentation surface for new
projects and upgrades.

### Answer summary

- Current target version: Spec Kitty 3.2.
- Current runtime model: Charter-era missions with governed context injection.
- Current governance source: `.kittify/charter/charter.md`.
- Current mission loop: `spec-kitty next --agent <name> --mission <slug>`.
- Upgrade path: [Migration to Spec Kitty 3.2](../migration/index.md).

### What is Charter?

Charter is the governance layer introduced in Spec Kitty 3.x. A single
human-edited file (`charter.md`) drives a synthesis pipeline that produces
structured context for governed mission actions and standalone profile
invocations. The flow is:

```
charter.md  ->  charter synthesize  ->  validated Charter state  ->  governed prompt/context
```

When you run `spec-kitty next --agent <name> --mission <slug>`, the runtime
automatically injects the relevant Charter context into the prompt file it
returns for the next mission action. For standalone work,
`spec-kitty dispatch "<request>"` uses the same governed-context model and
records an Op trail.

For the full mental model, see [How Charter Works](charter-overview.md).

### Documentation by type

#### Tutorials — learning-oriented

- [Governed Charter Workflow End-to-End](../guides/charter-governed-workflow.md) — Start from a fresh repo, set up governance, synthesize doctrine, and run a governed mission action
- [Getting Started with Spec Kitty](../guides/getting-started.md) — First project from scratch
- [Multi-Agent Workflow](../guides/multi-agent-workflow.md) — Run a mission across multiple harnesses

#### How-to guides — task-oriented

- [How to Set Up Project Governance](../guides/setup-governance.md) — Charter interview, generate, and sync
- [How to Synthesize and Maintain Doctrine](../guides/synthesize-doctrine.md) — `charter synthesize`, `charter resynthesize`, bundle validation
- [How to Run a Governed Mission](../guides/run-governed-mission.md) — `spec-kitty next --agent` with Charter context injection
- [How to Manage the Glossary](../guides/manage-glossary.md) — Living glossary, Charter integration, retrospective proposals
- [How to Use the Retrospective Learning Loop](../guides/use-retrospective-learning.md) — `retrospect summary`, `agent retrospect synthesize`
- [Troubleshooting Charter Failures](../guides/troubleshoot-charter.md) — Stale bundle, missing doctrine, compact-context, retro gate failures

#### Reference — authoritative specifications

- [Charter CLI Reference](../api/charter-commands.md) — All `charter` subcommands with flags
- [CLI Commands](../api/cli-commands.md) — Full spec-kitty CLI reference including Charter-era additions
- [Profile Invocation Reference](../api/profile-invocation.md) — standalone dispatch and invocation trail
- [Retrospective Schema Reference](../api/retrospective-schema.md) — `retrospective.yaml` schema, proposal kinds, exit codes
- [Governance Files Reference](governance-files.md) — Every file in `.kittify/charter/`

#### Explanation — conceptual background

- [How Charter Works](charter-overview.md) — Mental model: doctrine → DRG → governed context
- [Understanding Charter: Synthesis, DRG, and Governed Context](../architecture/charter-synthesis-drg.md) — Deep dive into synthesis and the Directive Relationship Graph
- [Understanding Governed Profile Invocation](../architecture/governed-profile-invocation.md) — The `(profile, action, governance-context)` triple
- [Understanding the Retrospective Learning Loop](../architecture/retrospective-learning-loop.md) — Why retrospectives exist and how the gate model works

### Migration

Upgrading from an earlier version? See
[Migrating from 2.x / Early 3.x](../migration/from-charter-2x.md) — what changed,
migration steps, and known failure modes.

### What is archived

Documentation for Spec Kitty 1.x and 2.x is preserved through the
[migration hub](../migration/index.md) for historical context. The 2.x
governance model did not include the DRG-backed synthesis pipeline or the
retrospective learning loop. If you are running a current project, use the 3.2
documentation above.
