# Understanding Spec Kitty Missions

**Divio type**: Tutorial

Spec Kitty supports three mission types that tailor the workflow and artifacts to your goal.

**Time**: ~45 minutes
**Prerequisites**: Completed [Getting Started](getting-started.md)

## What Is a Mission?

A mission selects the default templates, prompts, and outputs for your feature. You choose it during `spec-kitty init` or when running `/spec-kitty.specify`.

## The Three Missions

### Software Dev Kitty

Best for building software features and products.

Example use cases:

- New API endpoint
- UI feature development
- Performance improvements

### Deep Research Kitty

Best for structured research deliverables.

Example use cases:

- Competitive analysis
- Architecture decision research
- Technology evaluation

### Documentation Kitty

Best for creating or updating documentation sets.

Example use cases:

- End-user docs refresh
- API reference overhaul
- Internal playbooks

## Try It: Create a Research Feature

Create a project with the research mission:

```bash
spec-kitty init my-research-project --mission research --ai claude
cd my-research-project
```

Run a research workflow.

In your agent:

```text
/spec-kitty.research Compare three task queue options for a Python service.
```

Expected results (abridged):

- `kitty-specs/###-task-queue-research/` directory
- Research artifacts defined by the mission templates

## How Missions Affect Your Workflow

- **Templates**: Each mission uses its own spec/plan/templates.
- **Artifacts**: Research missions create research notes; documentation missions generate Divio-oriented sections.
- **Validation**: Review criteria differ based on mission expectations.

## Troubleshooting

- **"Unknown mission"**: Use `spec-kitty mission` to list available missions.
- **Missing `/spec-kitty.research`**: Re-run `spec-kitty init --mission research` or refresh agent context with `spec-kitty agent context update-context`.

## What's Next?

Explore the full workflow in [Your First Feature](your-first-feature.md) or dive deeper into specific missions.

### Related How-To Guides

- [Switch Missions](../how-to/switch-missions.md) - Change mission types
- [Create a Specification](../how-to/create-specification.md) - Start with any mission
- [Install and Upgrade](../how-to/install-and-upgrade.md) - Initial setup options

### Reference Documentation

- [Missions](../reference/missions.md) - All mission types reference
- [CLI Commands](../reference/cli-commands.md) - Full command reference
- [Configuration](../reference/configuration.md) - Project settings

### Learn More

- [Mission System](../explanation/mission-system.md) - How missions work internally
- [Documentation Mission](../explanation/documentation-mission.md) - Divio-based docs workflow
- [Spec-Driven Development](../explanation/spec-driven-development.md) - The underlying philosophy
