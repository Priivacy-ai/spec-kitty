# Missions Reference

Spec Kitty supports three mission types, each tailored to a different kind of work. Missions determine the workflow phases, artifacts, and templates used during feature development.

---

## Mission Overview

| Mission | Domain | Best For |
|---------|--------|----------|
| `software-dev` | Software development | Building features, APIs, UIs |
| `research` | Research and analysis | Investigations, competitive analysis, technical research |
| `documentation` | Documentation creation | User guides, API docs, tutorials |

---

## software-dev (Default)

The default mission for building software features.

### Domain
Software development: building new features, APIs, user interfaces, and system components.

### Phases
1. **research** — Understand requirements and constraints
2. **design** — Plan architecture and data models
3. **implement** — Build the solution
4. **test** — Verify correctness
5. **review** — Quality assurance

### Artifacts

| Artifact | Created By | Purpose |
|----------|------------|---------|
| `spec.md` | `/spec-kitty.specify` | User stories, requirements, acceptance criteria |
| `plan.md` | `/spec-kitty.plan` | Architecture, design decisions, file changes |
| `tasks.md` | `/spec-kitty.tasks` | Work package breakdown |
| `data-model.md` | `/spec-kitty.plan` | Database schema, entity relationships |
| `contracts/` | `/spec-kitty.plan` | API specifications (optional) |
| `tasks/*.md` | `/spec-kitty.tasks` | Individual WP prompt files |

### When to Use
- Adding new features to an application
- Building APIs or services
- Creating user interfaces
- System integrations
- Bug fixes that require planning

---

## research

Mission for research and analysis work.

### Domain
Research and analysis: investigating technologies, competitive analysis, feasibility studies, and technical deep-dives.

### Phases
1. **question** — Define research questions
2. **methodology** — Plan research approach
3. **gather** — Collect data and evidence
4. **analyze** — Analyze findings
5. **synthesize** — Draw conclusions
6. **publish** — Document results

### Artifacts

| Artifact | Created By | Purpose |
|----------|------------|---------|
| `spec.md` | `/spec-kitty.specify` | Research questions and scope |
| `plan.md` | `/spec-kitty.plan` | Research methodology |
| `research.md` | `/spec-kitty.research` | Research findings and evidence |
| `tasks.md` | `/spec-kitty.tasks` | Research task breakdown |
| `findings.md` | Implementation | Final synthesized findings |
| `sources/` | Implementation | Source materials and references |

### When to Use
- Technology evaluation
- Competitive analysis
- Feasibility studies
- Performance investigations
- Security audits
- Best practices research

---

## documentation

Mission for creating documentation.

### Domain
Documentation creation: user guides, API documentation, tutorials, and reference materials.

### Phases
1. **discover** — Understand documentation needs
2. **audit** — Assess existing documentation
3. **design** — Plan documentation structure
4. **generate** — Create content
5. **validate** — Review and test
6. **publish** — Deploy documentation

### Artifacts

| Artifact | Created By | Purpose |
|----------|------------|---------|
| `spec.md` | `/spec-kitty.specify` | Documentation scope and audience |
| `plan.md` | `/spec-kitty.plan` | Structure and approach |
| `research.md` | `/spec-kitty.research` | Audit of existing docs |
| `gap-analysis.md` | Planning | Coverage gaps identified |
| `tasks.md` | `/spec-kitty.tasks` | Documentation task breakdown |
| Divio templates | Implementation | Tutorial, how-to, reference, explanation files |

### Divio Documentation Types

The documentation mission uses the Divio 4-type system:

| Type | Orientation | Purpose |
|------|-------------|---------|
| **Tutorial** | Learning | Teach beginners step-by-step |
| **How-To** | Task | Solve specific problems |
| **Reference** | Information | Complete technical details |
| **Explanation** | Understanding | Explain concepts and "why" |

### When to Use
- Creating user documentation
- Writing API references
- Building tutorial content
- Documenting architecture
- Creating onboarding guides

---

## Selecting a Mission

Missions are selected **per-feature** during `/spec-kitty.specify`. The mission is stored in `meta.json`:

```json
{
  "mission": "documentation"
}
```

### During Feature Creation

When you run `/spec-kitty.specify`, you'll be asked to choose a mission:

```
? Which mission type for this feature?
  ○ software-dev — Building software features (default)
  ○ research — Research and analysis
  ○ documentation — Creating documentation
```

### Changing Mission

The mission cannot be changed after feature creation. If you need a different mission, create a new feature.

---

## Mission Configuration Files

Advanced users can customize missions via configuration files.

### Location
```
.kittify/missions/<mission-key>/mission.yaml
```

### Format

```yaml
key: software-dev
name: Software Development
domain: Building software features
description: >
  Standard mission for building new features, APIs, and user interfaces.
phases:
  - research
  - design
  - implement
  - test
  - review
artifacts:
  required:
    - spec.md
    - plan.md
    - tasks.md
  optional:
    - data-model.md
    - contracts/
templates:
  spec: spec-template.md
  plan: plan-template.md
  tasks: tasks-template.md
```

### Custom Missions

You can create custom missions by:

1. Creating a new directory: `.kittify/missions/my-mission/`
2. Adding a `mission.yaml` file
3. Optionally adding custom templates

Custom missions appear as options during `/spec-kitty.specify`.

---

## Mission Comparison

| Aspect | software-dev | research | documentation |
|--------|--------------|----------|---------------|
| Primary output | Working code | Research findings | Documentation |
| Typical WPs | 5-10 | 3-7 | 5-15 |
| Data model | Yes | No | No |
| API contracts | Optional | No | No |
| Gap analysis | No | No | Yes |
| Divio structure | No | No | Yes |

---

## See Also

- [Configuration](configuration.md) — Mission configuration details
- [Spec-Driven Development](../explanation/spec-driven-development.md) — The philosophy behind missions
- [Mission System](../explanation/mission-system.md) — Why missions exist

## Getting Started
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Non-Interactive Init](../how-to/non-interactive-init.md)

## Background
- [Mission System](../explanation/mission-system.md)
