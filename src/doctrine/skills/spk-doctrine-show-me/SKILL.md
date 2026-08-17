---
name: spk-doctrine-show-me
description: "Explain Spec Kitty work with compact, checkable visuals. Use for specs, plans, architecture, control flow, diffs, status boards, or whenever prose obscures structure."
---

# spk-doctrine-show-me

Make the current point visible. Skip the preamble, keep prose brief, and pick
the smallest representation that answers the question. Do not add a diagram
when a sentence or short list is clearer.

## Choose the Shape

- Logic or an algorithm: compact pseudocode.
- Runtime behavior: call tree or sequence diagram.
- UI composition: component tree with only relevant state and boundaries.
- Ownership or refactor scope: shallow file tree with one responsibility per entry.
- Existing-to-proposed change: `diff` over the matching tree, flow, or pseudocode.
- Domain lifecycle: state diagram.
- Data or concept relationships: entity-relationship or class diagram.
- Architecture: C4 Context first, then Container or Component only when useful.
- Dense visual UI/layout comparison: one focused HTML artifact when the host can
  open it; keep durable project documentation diagram-as-code.

Place each visual beside the text it supports. Include only the calls, files,
states, relationships, and boundaries needed for the current decision. Label
relationships and preserve source paths or identifiers that make the visual
checkable against code and artifacts.

## Use Spec Kitty's Diagram Sources

Prefer Mermaid for inline Markdown. Use PlantUML for richer layout control,
standalone sources, mature C4 support, or the workshop/stickies DSL. Read only
the guide needed for the selected notation:

- `packs/built-in/toolguides/MERMAID_DIAGRAMMING.md`
- `packs/built-in/toolguides/PLANTUML_DIAGRAMMING.md`
- `src/doctrine/templates/diagrams/` for project-owned themes and examples

For architecture, apply `USE_C4_MODEL_TECHNIQUES`; zoom progressively and stop
when the question is answered. Before sharing an architecture diagram, apply
the `architecture-diagram-review-checklist` tactic: title, audience, legend
when needed, typed/described elements, and labelled unidirectional relationships.

In specification, visualize actor flows, concepts, rules, and lifecycle states;
do not smuggle implementation choices into product requirements. In planning,
visualize architecture, data/control flow, boundaries, migrations, and risky
interactions. Prose requirements and contracts remain authoritative.

## Render `/spec-kitty.status` in a TUI

Use the command's Rich human output in a capable terminal. For a custom TUI,
consume structured data instead of scraping ANSI output:

```bash
spec-kitty agent tasks status --json --mission <handle>
```

Render the canonical flow in this order:

```text
Planned → Doing → For Review → Approved → Done
```

Fold `claimed`, `in_progress`, and `in_review` into **Doing**; mark claimed and
in-review entries rather than inventing extra columns. Surface blocked,
canceled, stale, stalled-review, and stale-verdict items in a warning section.
On narrow screens, stack the same five groups vertically instead of squeezing a
wide table.

Show **Done progress** (`done_count / total_wps`) separately from **Weighted readiness**
(`progress_percentage`). Never label weighted readiness as completed
work. End with the exact next action from status output, normally
`spec-kitty next --agent <name> --mission <handle>`.

## Origin and Attribution

Adapted from HumanLayer's MIT-licensed `show-me` skill by Dexter Horthy:
<https://github.com/humanlayer/skills/tree/main/plugins/show-me/skills/show-me>.
The source article also credits Dillon Mulroy for the call-tree shape and Matt
Pocock for HTML-explainer inspiration. Preserve the notice and provenance in
`references/humanlayer-origin-and-license.md` when redistributing this skill.
