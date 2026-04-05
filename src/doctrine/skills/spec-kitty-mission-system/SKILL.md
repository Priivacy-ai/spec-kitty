---
name: spec-kitty-mission-system
description: >-
  Understand how Spec Kitty missions work: the 4 built-in mission types, how
  they define workflows via step contracts and action indices, how missions and
  work packages relate, how templates are resolved through the 5-tier chain,
  and how doctrine artifacts (procedures, tactics, directives) compose mission
  behavior.
  Triggers: "what missions are available", "how do missions work",
  "which mission should I use", "explain the mission system",
  "what is a mission", "change the mission", "mission templates",
  "step contracts", "action index", "mission procedures".
  Does NOT handle: runtime loop advancement (use runtime-next),
  setup or repair (use setup-doctor), governance (use charter-doctrine),
  or glossary curation (use glossary-context).
---

# spec-kitty-mission-system

Understand how missions structure work in Spec Kitty. A mission is a
domain-specific workflow blueprint that defines what phases you go through,
what templates agents see, what artifacts you produce, and how to validate
success.

---

## How Missions Work

### The Core Concept

A mission answers: "What process should we follow to achieve this goal?"

Different goals need different processes. Building a software component is
different from conducting research or writing documentation. Each mission
provides domain-appropriate:

- **Steps** — the ordered phases of work (specify → plan → implement → review)
- **Templates** — prompts that tell agents what to do at each step
- **Artifacts** — expected outputs (spec.md, plan.md, tasks.md)
- **Guards** — conditions that must be met before advancing (e.g., spec.md must exist before planning)
- **Validation** — checks that verify the output quality
- **Agent context** — personality and instructions for the AI agent

### The Hierarchy: Mission Type → Mission → Work Package → Workspace

```
Mission Type (e.g., software-dev)
  └── Mission (kitty-specs/042-auth-system/)
        ├── meta.json           ← links mission to mission type + target branch
        ├── spec.md             ← what we're building
        ├── plan.md             ← how we'll build it
        ├── tasks.md            ← WP breakdown
        └── tasks/
              ├── WP01.md       ← work package prompt
              ├── WP02.md
              └── WP03.md
                    └── Workspace (.worktrees/042-auth-system-lane-b/)
```

- **Mission Type** = the workflow blueprint (reusable across missions)
- **Mission** = a concrete thing you're building, linked to a mission type via `meta.json`
- **Work Package (WP)** = one parallelizable slice of work within a mission
- **Workspace** = an isolated git worktree owned by one execution lane

### meta.json (Mission → Mission Type Link)

Every mission has a `meta.json` that records which mission type it uses:

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

The `mission` field determines which templates, guards, and validation rules
apply. Default is `software-dev` if omitted.

---

## The 4 Built-In Mission Types

### software-dev (default)

Full software development lifecycle with work packages and code review.

**Steps:**
```
discovery → specify → plan → tasks_outline → tasks_packages → tasks_finalize → implement → review → accept
```

**Required artifacts:** `spec.md`, `plan.md`, `tasks.md`

**Guards:**
- `specify → plan`: `spec.md` must exist
- `plan → implement`: `plan.md` and `tasks.md` must exist
- `implement → review`: all WPs must be done
- `review → done`: review must be approved

**Agent context:** TDD practices, library-first architecture, tests before code.

**Use when:** Building components, fixing bugs, refactoring code — any work that
produces code changes.

### research

Systematic research with evidence-gated transitions.

**Steps (state machine):**
```
scoping → methodology → gathering → synthesis → output → done
                            ↑            │
                            └── gather_more (loop back)
```

**Required artifacts:** `spec.md`, `plan.md`, `tasks.md`, `findings.md`

**Guards:**
- `scoping → methodology`: scope document must exist
- `methodology → gathering`: methodology plan must exist
- `gathering → synthesis`: at least 3 sources documented
- `synthesis → output`: findings document must exist
- `output → done`: publication approved

**Special:** The `gathering → synthesis → gathering` loop allows iterative
evidence collection. Source tracking in `source-register.csv`, evidence in
`evidence-log.csv`.

**Use when:** Investigating technologies, conducting literature reviews,
evaluating options, any work requiring structured evidence gathering.

### plan

Goal-oriented planning with iterative refinement.

**Steps:**
```
specify → research → plan → review
```

**Use when:** Planning a project, designing architecture, creating roadmaps —
any work that produces planning artifacts but not code.

### documentation

Documentation creation following the Divio 4-type system.

**Workflow phases:**
```
discover → audit → design → generate → validate → publish
```

**Required artifacts:** `spec.md`, `plan.md`, `tasks.md`, `gap-analysis.md`

**Divio types:** Tutorial (learning-oriented), How-To (task-oriented),
Reference (information-oriented), Explanation (understanding-oriented).

**Special:** Supports auto-generation via JSDoc, Sphinx, or rustdoc. Gap
analysis identifies missing documentation by classifying existing docs and
finding coverage gaps.

**Use when:** Creating docs for a project, filling documentation gaps,
documenting a specific component or API.

---

## Mission Type Definition Files

Each mission type lives in `src/doctrine/missions/{mission-key}/` with:

### mission-runtime.yaml (Runtime DAG)

Defines steps as a directed acyclic graph with dependencies:

```yaml
mission:
  key: software-dev
  name: Software Dev Kitty
  version: "2.1.0"

steps:
  - id: specify
    title: Specification
    depends_on: [discovery]
    prompt_template: specify.md
    description: Define user scenarios and acceptance criteria

  - id: plan
    depends_on: [specify]
    prompt_template: plan.md

  - id: implement
    depends_on: [tasks_finalize]
    prompt_template: implement.md
```

This is what `spec-kitty next` uses to determine step ordering.

### mission.yaml (Configuration + State Machine)

Contains both v0 configuration (artifacts, validation, agent context) and
v1 state machine definitions (states, transitions, guards):

**v0 fields (configuration):**
```yaml
name: "Software Dev Kitty"
domain: "software"
artifacts:
  required: [spec.md, plan.md, tasks.md]
  optional: [data-model.md, quickstart.md]
workflow:
  phases:
    - name: "research"
    - name: "implement"
    - name: "review"
agent_context: |
  You are a software development agent following TDD practices.
mcp_tools:
  required: [filesystem, git]
  recommended: [code-search, test-runner]
validation:
  checks: [git_clean, all_tests_pass, kanban_complete]
```

**v1 fields (state machine):**
```yaml
initial: discovery
states:
  - name: discovery
  - name: specify
  - name: plan
  - name: implement
  - name: review
  - name: done
transitions:
  - trigger: advance
    source: specify
    dest: plan
    conditions:
      - 'artifact_exists("spec.md")'
guards:
  has_spec:
    description: "Specification document must exist"
    check: 'artifact_exists("spec.md")'
```

### command-templates/ (Agent Prompts)

Markdown files shown to agents at each step:
- `specify.md` — Instructions for writing the specification
- `plan.md` — Instructions for creating the implementation plan
- `implement.md` — Instructions for implementing a work package
- `review.md` — Instructions for reviewing a work package
- `accept.md` — Instructions for final acceptance validation

### templates/ (Content Templates)

Scaffolding files for artifacts:
- `spec-template.md` — Starting structure for spec.md
- `plan-template.md` — Starting structure for plan.md
- `task-prompt-template.md` — Starting structure for WP prompt files
- `tasks-template.md` — Starting structure for tasks.md

---

## Doctrine Composition Layer

Missions are backed by structured doctrine artifacts that define action
behavior and link to reusable knowledge.

### MissionStepContract (Action Contracts)

Each public action (specify, plan, implement, review) has a step contract
that defines its internal structure:

```yaml
# implement.step-contract.yaml
id: implement
action: implement
mission: software-dev
schema_version: "1.0"
steps:
  - id: setup-workspace
    description: "Create or enter the WP workspace"
  - id: implement-code
    description: "Write code following governance constraints"
    delegates_to:
      kind: tactic
      candidates: [tdd-red-green-refactor, zombies-tdd]
  - id: validate
    description: "Run tests and lint checks"
```

The `delegates_to` field links a step to doctrine artifacts. This is how
mission behavior connects to the knowledge layer: the contract says *what*
to do, the referenced tactic/directive/procedure says *how*.

### Procedure (Reusable Workflow Primitives)

Procedures are multi-step doctrine artifacts with prerequisites and ordered
steps. They are the reusable building blocks that step contracts delegate to.
Each procedure describes a complete mini-workflow (e.g., a refactoring
sequence, a test-first bug fix, a situational assessment).

Procedures live in `src/doctrine/procedures/shipped/` (shipped) or
`.kittify/procedures/` (project-local). Access via `DoctrineService`:

```python
procedure = service.procedures.get("refactoring")
# procedure.steps → ordered list of actions
# procedure.prerequisites → what must be true before starting
```

```bash
spec-kitty doctrine list --kind procedure
```

### Agent Profiles (Role-Based WP Assignment)

Agent profiles define roles, specializations, and boundaries for work
package assignment. Each profile has 6 sections: context_sources, purpose,
specialization (languages, frameworks, boundaries), collaboration (handoffs,
outputs), mode_defaults, and initialization_declaration.

Profiles form a hierarchy via `specializes_from` — a language-specific
profile inherits from a general implementer profile, adding language-scoped
capabilities. The DDR-011 algorithm resolves which profile best matches a
given task context based on weighted signals (language, framework,
file-pattern, keyword, exact-id).

The `mission.yaml` `task_types` section maps WP actions to agent roles:

```yaml
task_types:
  implement:
    agent_role: implementer
  review:
    agent_role: reviewer
  plan:
    agent_role: planner
```

```bash
# Discover available profiles
spec-kitty agent profile list

# Inspect a profile's boundaries and initialization context
spec-kitty agent profile show <profile-id>

# Visualize the specialization hierarchy
spec-kitty agent profile hierarchy
```

### Action Indices (Doctrine Scoping)

Each mission action has an index that declares which doctrine artifacts are
relevant to that step:

```yaml
# src/doctrine/missions/software-dev/actions/implement/index.yaml
action: implement
directives: [TEST_FIRST]
tactics: [tdd-red-green-refactor, zombies-tdd, acceptance-test-first]
styleguides: [python-implementation]
toolguides: []
procedures: [implementation-handoff]
```

The charter context builder uses these indices to scope what gets
injected into the agent prompt at each step. This prevents agents from
seeing review-scoped doctrine during implementation and vice versa.

---

## 6 Guard Primitives

Guards block step transitions until conditions are met:

| Guard | Syntax | What it checks |
|---|---|---|
| `artifact_exists` | `artifact_exists("spec.md")` | File exists in mission dir |
| `gate_passed` | `gate_passed("review_approved")` | Event exists in mission event log |
| `all_wp_status` | `all_wp_status("done")` | Every WP is in the specified lane |
| `any_wp_status` | `any_wp_status("for_review")` | At least one WP is in the lane |
| `input_provided` | `input_provided("architecture")` | Input was provided to runtime |
| `event_count` | `event_count("source_documented", 3)` | Minimum event count in log |

Guards are composed as `conditions` lists on transitions. All conditions in the
list must pass for the transition to fire.

---

## Template Resolution (5-Tier Chain)

When a command template is needed, spec-kitty searches 5 locations in order:

| Tier | Path | Purpose |
|---|---|---|
| 1. Override | `.kittify/overrides/command-templates/` | Project customization |
| 2. Legacy | `.kittify/command-templates/` | Deprecated pre-migration |
| 3. Global Mission | `~/.kittify/missions/{mission}/command-templates/` | User global |
| 4. Global | `~/.kittify/command-templates/` | User global fallback |
| 5. Package | `src/doctrine/missions/{mission}/command-templates/` | Built-in default |

First match wins. Override a template by placing your version in
`.kittify/overrides/command-templates/`. The package default is always the
fallback.

Content templates (`templates/`) follow the same 5-tier resolution.

---

## Selecting a Mission Type

The mission type is set when you create a mission with `/spec-kitty.specify`.
It's recorded in `meta.json` and cannot be changed after creation.

**Commands:**

```bash
# List available mission types
spec-kitty list-missions

# Specify a mission with a specific mission type
spec-kitty specify --mission research "What are the best auth patterns?"

# Check which mission type a mission uses
cat kitty-specs/<mission-slug>/meta.json | jq .mission
```

**Decision guide:**

| If you're... | Use mission type |
|---|---|
| Building a component, fixing a bug, refactoring | `software-dev` |
| Investigating, evaluating options, literature review | `research` |
| Planning architecture, roadmaps, design docs | `plan` |
| Writing tutorials, API docs, how-to guides | `documentation` |

---

## The Two State Machines

Missions involve two orthogonal state machines:

**Mission-type state** — which phase of the workflow are we in?
```
discovery → specify → plan → tasks → implement → review → accept
```
Managed by `mission-runtime.yaml` DAG and `spec-kitty next`.

**WP status** — where is each work package in its lifecycle?
```
planned → claimed → in_progress → for_review → approved → done
                                                    ↕
                                                 blocked / canceled
```
Managed by the status model (append-only event log).

Together they determine what `spec-kitty next` returns: "we're in the implement
phase, WP01 is done, WP02 is in_progress, WP03 is planned — your next action
is implement WP03."

---

## Runtime Bootstrap

On every CLI invocation, `ensure_runtime()` runs:
1. Checks `~/.kittify/cache/version.lock` — if version matches, fast path (< 100ms)
2. If stale: copies mission files from installed package to `~/.kittify/missions/`
3. Uses file locking to prevent concurrent corruption

This ensures `~/.kittify/` always matches the installed spec-kitty version.

---

## References

- `references/mission-comparison-matrix.md` -- Side-by-side comparison of all 4 mission types
