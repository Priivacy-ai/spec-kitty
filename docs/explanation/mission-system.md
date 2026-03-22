# The Mission System Explained

Spec Kitty's mission system lets you choose a workflow optimized for your type of work. This document explains why missions exist, how they shape your experience, and how the pieces fit together.

## Why Different Missions?

Not all projects are the same:

| Work Type | Primary Goal | Key Activities |
|-----------|--------------|----------------|
| **Software development** | Working code | Write tests, implement features, review code |
| **Research** | Validated findings | Collect evidence, analyze data, synthesize conclusions |
| **Planning** | Actionable plan | Define architecture, map dependencies, write roadmaps |
| **Documentation** | Clear docs | Audit gaps, create content, validate accessibility |

A workflow designed for software development doesn't fit research:
- "All tests pass" makes no sense for a literature review
- "Documented sources" isn't relevant for code implementation
- Phases like "gather data" don't apply to feature development

Missions solve this by providing domain-specific workflows, validation rules, and artifacts.

## The Hierarchy: Mission, Feature, Work Package, Workspace

Understanding how the pieces nest together is key to understanding Spec Kitty.

```
Mission (reusable workflow blueprint, e.g. software-dev)
  |
  +-- Feature (concrete thing being built)
  |     kitty-specs/042-auth-system/
  |       meta.json        <-- links feature to mission + target branch
  |       spec.md          <-- what we're building
  |       plan.md          <-- how we'll build it
  |       tasks.md         <-- WP breakdown
  |       tasks/
  |         WP01.md        <-- work package prompt
  |         WP02.md
  |         WP03.md
  |           |
  |           +-- Workspace (.worktrees/042-auth-system-WP03/)
  |                 isolated git worktree for this WP
```

**Mission** -- A reusable workflow blueprint. It defines the steps, templates, artifacts, and guards. You never edit missions directly; you select one when starting a feature.

**Feature** -- A concrete thing you're building, stored in `kitty-specs/###-feature-name/`. Each feature is linked to exactly one mission via its `meta.json` file. Different features in the same project can use different missions.

**Work Package (WP)** -- One parallelizable slice of work within a feature. Each WP has its own markdown prompt file (`tasks/WP01.md`), its own status on the kanban board, and its own dependencies on other WPs.

**Workspace** -- An isolated git worktree where a single WP is implemented. Each workspace has its own branch, its own working directory, and its own agent. Multiple workspaces can run in parallel.

### meta.json: The Feature-to-Mission Link

Every feature directory contains a `meta.json` that records which mission it uses:

```json
{
  "feature_number": "042",
  "slug": "042-auth-system",
  "mission": "software-dev",
  "target_branch": "main",
  "created_at": "2026-03-22T10:00:00Z",
  "vcs": "git"
}
```

The `mission` field determines which templates, guards, and validation rules apply. If omitted, it defaults to `software-dev`.

Different features can use different missions simultaneously:
- `kitty-specs/042-auth-system/` -- software-dev
- `kitty-specs/043-market-analysis/` -- research
- `kitty-specs/044-api-docs/` -- documentation
- `kitty-specs/045-roadmap/` -- plan

## How Missions Work

### Selected Per-Feature During /spec-kitty.specify

When you run `/spec-kitty.specify`, Spec Kitty prompts for the mission type:

```
? Select mission type:
  Software Dev Kitty - Build high-quality software with structured workflows
  Deep Research Kitty - Conduct systematic research with evidence synthesis
  Plan Kitty - Goal-oriented planning with iterative refinement
  Documentation Kitty - Create high-quality documentation following Divio principles
```

Your choice determines:
- Workflow phases (the steps you go through)
- Required artifacts (the files you produce)
- Guards (conditions that must be met to advance)
- Agent context (personality and instructions for AI agents)

The mission is locked in at feature creation and cannot be changed afterwards.

### Two State Machines Working Together

Missions involve two orthogonal state machines that work in tandem:

**Mission state** -- which phase of the workflow are we in?
```
discovery --> specify --> plan --> tasks --> implement --> review --> accept
```
Managed by the mission's step DAG and `spec-kitty next`.

**WP status** -- where is each work package in its lifecycle?
```
planned --> claimed --> in_progress --> for_review --> approved --> done
```
Managed by the status model (append-only event log).

Together they determine what `spec-kitty next` returns: "We're in the implement phase, WP01 is done, WP02 is in_progress, WP03 is planned -- your next action is implement WP03."

## The Four Built-In Missions

### software-dev (default)

Full software development lifecycle with work packages and code review.

**Step sequence:**
```
discovery --> specify --> plan --> tasks_outline --> tasks_packages --> tasks_finalize --> implement --> review --> accept
```

**Required artifacts:** `spec.md`, `plan.md`, `tasks.md`

**Guards:**

| Transition | What must be true |
|---|---|
| specify --> plan | `spec.md` must exist |
| plan --> implement | `plan.md` and `tasks.md` must exist |
| implement --> review | All WPs must be in "done" lane |
| review --> done | Review must be approved |

**Agent context:** TDD practices, library-first architecture, tests before code.

**Use when:** Building features, fixing bugs, refactoring code -- any work that produces code changes.

### research

Systematic research with evidence-gated transitions.

**Step sequence (state machine with loop):**
```
scoping --> methodology --> gathering <--> synthesis --> output --> done
```
The `gathering <--> synthesis` loop allows iterative evidence collection. You can go back to gathering more data after an initial synthesis pass.

**Required artifacts:** `spec.md`, `plan.md`, `tasks.md`, `findings.md`

**Guards:**

| Transition | What must be true |
|---|---|
| scoping --> methodology | Scope document (`spec.md`) must exist |
| methodology --> gathering | Methodology plan (`plan.md`) must exist |
| gathering --> synthesis | At least 3 sources documented |
| synthesis --> output | Findings document must exist |
| output --> done | Publication approved |

**Special:** Source tracking in `source-register.csv`, evidence in `evidence-log.csv`.

**Agent context:** Research integrity, methodological rigor, evidence documentation.

**Use when:** Investigating technologies, evaluating options, conducting literature reviews, competitive analysis -- any work requiring structured evidence gathering.

### plan

Goal-oriented planning with iterative refinement.

**Step sequence:**
```
specify --> research --> plan --> review
```

This is the lightest mission -- four steps, no guards, no work packages. It produces planning artifacts (architecture documents, roadmaps, design proposals) without any implementation.

**Required artifacts:** `spec.md`, `plan.md`

**Guards:** None -- transitions are manual.

**Use when:** Planning architecture, creating roadmaps, designing systems before implementation begins, writing design proposals.

### documentation

Documentation creation following the Divio 4-type system (tutorials, how-to guides, reference, explanations).

**Step sequence:**
```
discover --> audit --> design --> generate --> validate --> publish
```

**Required artifacts:** `spec.md`, `plan.md`, `tasks.md`, `gap-analysis.md`

**Special features:**
- Gap analysis identifies missing documentation by classifying existing docs against the Divio grid
- Supports auto-generation via JSDoc, Sphinx, or rustdoc for API reference docs
- Three iteration modes: initial (from scratch), gap-filling (audit and fill), feature-specific (single component)

**Guards:** No guards on step transitions. Validation checks run during acceptance: all Divio types valid, no conflicting generators, templates populated (no `[TODO]` markers), gap analysis complete.

**Agent context:** Write the Docs best practices, Divio 4-type system, accessibility and bias-free language.

**Use when:** Writing tutorials, API docs, how-to guides, filling documentation gaps, documenting a specific feature.

## Mission Comparison

| | software-dev | research | plan | documentation |
|---|---|---|---|---|
| **Domain** | Software | Research | Planning | Documentation |
| **Steps** | 9 (DAG) | 6 (state machine) | 4 (linear) | 6 (phases) |
| **Has WP iteration** | Yes | Yes | No | Yes |
| **Has loops** | No | Yes (gather more) | No | No |
| **Default mission** | Yes | No | No | No |

### Required artifacts by mission

| Artifact | software-dev | research | plan | documentation |
|---|:---:|:---:|:---:|:---:|
| `spec.md` | Required | Required | Required | Required |
| `plan.md` | Required | Required | Required | Required |
| `tasks.md` | Required | Required | -- | Required |
| `findings.md` | -- | Required | -- | -- |
| `gap-analysis.md` | -- | -- | -- | Required |

## Which Mission Should I Use?

| If you're... | Use mission | Why |
|---|---|---|
| Building a new feature with code changes | `software-dev` | Full lifecycle with TDD, work packages, code review |
| Fixing a bug or refactoring existing code | `software-dev` | Same lifecycle, just smaller scope |
| Investigating or evaluating technology options | `research` | Evidence-gated transitions ensure rigor |
| Conducting a literature review or competitive analysis | `research` | Source tracking and iterative gathering loops |
| Planning a project roadmap or architecture | `plan` | Lightweight, produces plans without code |
| Designing a system without implementing it yet | `plan` | Four steps, no work packages needed |
| Writing tutorials, API docs, or how-to guides | `documentation` | Divio system ensures comprehensive coverage |
| Filling gaps in existing documentation | `documentation` | Gap analysis mode finds what's missing |

**Commands:**

```bash
# List available missions
spec-kitty list-missions

# Start a feature with a specific mission
spec-kitty specify --mission research "What are the best auth patterns?"

# Check which mission a feature uses
cat kitty-specs/<feature-slug>/meta.json
```

## Template Resolution: Customizing Mission Prompts

Each mission provides command templates (the prompts agents see at each step) and content templates (scaffolding for artifacts like spec.md). You can override any template without modifying the package itself.

When a template is needed, Spec Kitty searches three locations in order:

| Priority | Location | Purpose |
|---|---|---|
| 1. Project override | `.kittify/overrides/command-templates/` | Per-project customization |
| 2. Global mission | `~/.kittify/missions/{mission}/command-templates/` | User-wide defaults |
| 3. Package default | (built into spec-kitty) | Ships with the tool |

First match wins. The package default is always the fallback.

**To customize a prompt for your project**, drop a file into `.kittify/overrides/command-templates/`:

```bash
# Copy the default template
cp ~/.kittify/missions/software-dev/command-templates/implement.md \
   .kittify/overrides/command-templates/implement.md

# Edit to taste
vim .kittify/overrides/command-templates/implement.md
```

Your override will be used instead of the package default for that step. Content templates (`templates/`) follow the same resolution chain.

## Guards: What Blocks Step Transitions

Guards are conditions that must be satisfied before a mission can advance to its next step. They prevent you from skipping ahead -- you can't plan without a specification, and you can't review without all work packages completed.

### Common guards you'll encounter

| Guard | What it checks | Example |
|---|---|---|
| Artifact exists | A required file is present | Can't start planning until `spec.md` exists |
| All WPs done | Every work package reached "done" lane | Can't start review until all WPs are complete |
| Gate passed | A named event was recorded | Can't finish until review is approved |
| Source count | Minimum number of evidence sources | Can't synthesize until at least 3 sources documented (research) |

When a guard blocks you, `spec-kitty next` tells you what's missing:

```
Blocked: artifact_exists("spec.md") not satisfied.
Action: Run /spec-kitty.specify to create the specification document.
```

Guards vary by mission. The software-dev mission has guards on most transitions. The plan mission has none -- you advance manually. The research mission uses source-count guards to ensure evidence quality. The documentation mission checks quality during acceptance rather than between steps.

## Mission Templates Per Slash Command

Each mission customizes the slash commands with domain-appropriate prompts:

### /spec-kitty.specify

| Mission | Prompt Focus |
|---------|--------------|
| **Software Dev** | User scenarios and acceptance criteria |
| **Research** | Research question, scope, expected outcomes |
| **Plan** | Goals, constraints, success criteria |
| **Documentation** | Iteration mode, Divio types, target audience |

### /spec-kitty.plan

| Mission | Prompt Focus |
|---------|--------------|
| **Software Dev** | Technical architecture and implementation plan |
| **Research** | Research methodology and data collection strategy |
| **Plan** | Architecture, roadmap, or design structure |
| **Documentation** | Documentation structure and generator configuration |

### /spec-kitty.implement

| Mission | Prompt Focus |
|---------|--------------|
| **Software Dev** | Work packages with TDD workflow |
| **Research** | Data collection, analysis, synthesis tasks |
| **Plan** | (no implementation phase) |
| **Documentation** | Template creation, generator setup, content authoring |

## Per-Feature vs. Global

### Before 0.8.0: Project-Wide Mission

Early versions set the mission at project level:
```
.kittify/
  mission.yaml  # One mission for entire project
```

**Problem**: Real projects need different approaches for different features:
- Feature A is new software development
- Feature B is researching which library to use
- Feature C is writing user documentation

### After 0.8.0: Per-Feature Mission

Now missions are selected per-feature:
```
kitty-specs/
  010-auth-system/
    meta.json  # mission: "software-dev"
  011-library-comparison/
    meta.json  # mission: "research"
  012-user-docs/
    meta.json  # mission: "documentation"
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
