# The Mission System Explained

Spec Kitty's mission system lets you choose a workflow optimized for your type of work. This document explains why missions exist and how they shape your experience.

## Why Different Missions?

Not all projects are the same:

| Work Type | Primary Goal | Key Activities |
|-----------|--------------|----------------|
| **Software development** | Working code | Write tests, implement features, review code |
| **Research** | Validated findings | Collect evidence, analyze data, synthesize conclusions |
| **Documentation** | Clear docs | Audit gaps, create content, validate accessibility |

A workflow designed for software development doesn't fit research:

- "All tests pass" makes no sense for a literature review
- "Documented sources" isn't relevant for code implementation
- Phases like "gather data" don't apply to feature development

Missions solve this by providing domain-specific workflows, validation rules, and artifacts.

## How Missions Work

### Selected Per-Feature During /spec-kitty.specify

When you run `/spec-kitty.specify`, Spec Kitty prompts for the mission type:

```
? Select mission type:
  Software Dev Kitty - Build high-quality software with structured workflows
  Deep Research Kitty - Conduct systematic research with evidence synthesis
  Documentation Kitty - Create high-quality documentation following Divio principles
```

Your choice determines:

- Workflow phases
- Required artifacts
- Validation rules
- Agent context (personality/instructions)

### Stored in Feature's meta.json

The mission selection is stored per-feature:

```json
// kitty-specs/012-user-auth/meta.json
{
  "mission": "software-dev",
  "created": "2026-01-15T10:00:00Z"
}
```

Different features can use different missions:

- `kitty-specs/012-user-auth/` → Software Dev Kitty
- `kitty-specs/013-market-analysis/` → Deep Research Kitty
- `kitty-specs/014-user-docs/` → Documentation Kitty

### Affects Templates, Phases, and Artifacts

Each mission provides:

**Templates**: Slash command prompts optimized for the domain
**Phases**: Workflow stages appropriate for the work type
**Artifacts**: Files created during the workflow

## The Three Missions

### Software Dev Kitty

**Focus**: Building software features with test-driven development.

**Workflow phases**:

1. **research** - Research technologies and best practices
2. **design** - Define architecture and contracts
3. **implement** - Write code following TDD
4. **test** - Validate implementation
5. **review** - Code review and quality checks

**Key practices**:

- Tests before code (non-negotiable)
- Library-first architecture
- CLI interfaces for all features
- Real dependencies over mocks in testing

**Required artifacts**:

- `spec.md` - Feature specification
- `plan.md` - Technical design
- `tasks.md` - Work packages

**Validation checks**:

- Git is clean (no uncommitted changes)
- All tests pass
- Kanban board complete (all WPs done)
- No unresolved clarification markers

### Deep Research Kitty

**Focus**: Systematic research with evidence-based conclusions.

**Workflow phases**:

1. **question** - Define research question and scope
2. **methodology** - Design research methodology
3. **gather** - Collect data and sources
4. **analyze** - Analyze findings
5. **synthesize** - Synthesize results
6. **publish** - Prepare for publication

**Key practices**:

- Document ALL sources in source register (CSV)
- Extract findings to evidence log with confidence levels
- Distinguish raw evidence from interpretation
- Every claim must have a citation

**Required artifacts**:

- `spec.md` - Research question and scope
- `plan.md` - Methodology plan
- `tasks.md` - Research work packages
- `findings.md` - Synthesized findings

**Validation checks**:

- All sources documented
- Methodology clearly stated
- Findings synthesized
- No unresolved questions

### Documentation Kitty

**Focus**: Creating documentation following Write the Docs best practices.

**Workflow phases**:

1. **discover** - Identify documentation needs
2. **audit** - Analyze existing docs, identify gaps
3. **design** - Plan structure and Divio types
4. **generate** - Create from templates and generators
5. **validate** - Check quality and accessibility
6. **publish** - Deploy documentation

**Key practices**:

- Documentation as code (in version control)
- Divio 4-type system (tutorial, how-to, reference, explanation)
- Accessibility and bias-free language
- Iterative improvement (gap-filling mode)

**Required artifacts**:

- `spec.md` - Documentation needs
- `plan.md` - Structure and generator config
- `tasks.md` - Documentation work packages
- `gap-analysis.md` - Coverage matrix and gaps

**Validation checks**:

- All Divio types valid
- No conflicting generators
- Templates populated (no `[TODO]` markers)
- Gap analysis complete

## Mission Templates

Each mission customizes the slash commands with domain-appropriate prompts:

### /spec-kitty.specify

| Mission | Prompt Focus |
|---------|--------------|
| **Software Dev** | User scenarios and acceptance criteria |
| **Deep Research** | Research question, scope, expected outcomes |
| **Documentation** | Iteration mode, Divio types, target audience |

### /spec-kitty.plan

| Mission | Prompt Focus |
|---------|--------------|
| **Software Dev** | Technical architecture and implementation plan |
| **Deep Research** | Research methodology and data collection strategy |
| **Documentation** | Documentation structure and generator configuration |

### /spec-kitty.tasks

| Mission | Prompt Focus |
|---------|--------------|
| **Software Dev** | Work packages with TDD workflow |
| **Deep Research** | Literature review, data collection, analysis |
| **Documentation** | Template creation, generator setup, content authoring |

## Per-Feature vs. Global

### Before 0.8.0: Project-Wide Mission

Early versions set the mission at project level:

```
.kittify/
└── mission.yaml  # One mission for entire project
```

**Problem**: Real projects need different approaches for different features:

- Feature A is new software development
- Feature B is researching which library to use
- Feature C is writing user documentation

### After 0.8.0: Per-Feature Mission

Now missions are selected per-feature:

```
kitty-specs/
├── 010-auth-system/
│   └── meta.json  # mission: "software-dev"
├── 011-library-comparison/
│   └── meta.json  # mission: "research"
└── 012-user-docs/
    └── meta.json  # mission: "documentation"
```

**Benefits**:

- Choose the right workflow for each task
- Same project can have software, research, and documentation features
- No need to reconfigure between different types of work

## How Missions Affect Agent Behavior

The `agent_context` field in each mission provides instructions that shape agent behavior:

**Software Dev agent**:
> You are a software development agent following TDD practices. Tests before code (non-negotiable).

**Research agent**:
> You are a research agent conducting systematic literature reviews. Document ALL sources.

**Documentation agent**:
> You are a documentation agent following Write the Docs best practices and Divio system.

These instructions guide AI agents to behave appropriately for the domain.

## See Also

- [Spec-Driven Development](spec-driven-development.md) - The methodology missions implement
- [Divio Documentation](divio-documentation.md) - The documentation system used by Documentation Kitty
- [Kanban Workflow](kanban-workflow.md) - How work moves through lanes (applies to all missions)

---

*This document explains why missions exist and how they differ. For how to select and use missions, see the tutorials and how-to guides.*

## Try It

- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## How-To Guides

- [Install Spec Kitty](../how-to/install-spec-kitty.md)
- [Use the Dashboard](../how-to/use-dashboard.md)

## Reference

- [Missions](../reference/missions.md)
- [Slash Commands](../reference/slash-commands.md)
