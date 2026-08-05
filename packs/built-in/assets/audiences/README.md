---
packaged: true
audiences: [software_engineer, automation_agent, agentic-framework-core-team, line_manager, nontech_educator]
note: >-
  Starter library of writing-audience personas. See
  tactics/communication/writing-audience-catalog.tactic.yaml for
  selection guidance.
---

# Writing-Audience Personas (Built-in Starter Library)

Purpose: a small, ready-to-use set of persona definitions that guide the tone, depth, and
structure of written communications — reports, wiki pages, release notes, executive summaries,
and other prose artifacts. Each persona describes **who is reading a piece of prose** and how to
calibrate it for them.

**This is not the architecture stakeholder-persona pattern.** `templates/architecture/
stakeholder-persona-template.md` and `tactics/communication/stakeholder-alignment.tactic.yaml`
describe a different concept: identifying who has a *stake in a design or architecture decision*
and surfacing inter-group conflict before that decision is made. The personas in this library are
about calibrating the tone and detail of a piece of writing for its intended reader, not about
decision stakeholders. The two patterns are deliberately not wired together.

What belongs: finished persona markdown files with goals, context, and needs, following the
`Persona: [Role Title]` shape. These are ready-to-use resources, not fill-in-the-blank templates.

What doesn't:

- Project-specific or one-off reader notes that won't be reused — keep those local to the task.
- Blank or partially-filled persona scaffolds.
- A stakeholder-of-a-decision pattern — that belongs with `stakeholder-alignment`, not here.

See `tactics/communication/writing-audience-catalog.tactic.yaml` for how to select one
of these personas before drafting.

## Library contents

| File | Persona |
|---|---|
| `software_engineer.md` | Software Engineer / Platform Engineer |
| `automation_agent.md` | Automation Agent (AI/LLM-based reader) |
| `agentic-framework-core-team.md` | Agentic Framework Core Team |
| `line_manager.md` | Manager / Non-Technical Leader |
| `nontech_educator.md` | Non-Technical Teacher / Educator |

Each persona file has a sidecar `<filename>.asset.yaml` manifest, per the ASSET artifact kind's
sidecar convention (see `assets/README.md`).

This library is intentionally small. Projects with a broader or more specific set of readers
(e.g. named customer segments, regulator profiles, internal audiences) should supply their own
persona library as an org-pack extension — additional personas placed under an
`assets/audiences/` directory in that pack are automatically added to the pool a writer can
select from, alongside these built-in defaults.
