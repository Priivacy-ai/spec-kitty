---
name: spec-kitty-charter-doctrine
description: >-
  Run charter interview, generation, context, and sync workflows for
  project governance in Spec Kitty 3.x. Access doctrine artifacts
  programmatically via DoctrineService. Resolve agent profiles. Load
  action-scoped governance context iteratively, not all at once.
  Triggers: "interview for charter", "generate charter",
  "sync charter", "use doctrine", "set up governance",
  "charter status", "extract governance config", "load doctrine",
  "agent profile", "DoctrineService", "action index".
  Does NOT handle: generic spec writing not tied to governance, direct runtime
  loop advancement, setup/repair diagnostics, or editorial glossary maintenance.
---

# spec-kitty-charter-doctrine

Manage the charter lifecycle: interview, generate, context-load, sync,
and status. Access doctrine artifacts programmatically via `DoctrineService`.
Resolve agent profiles for role-scoped behavior. Load governance context
iteratively at action boundaries rather than dumping everything upfront.

The charter is the single authoritative governance document for a Spec
Kitty project. All structured config (governance.yaml, directives.yaml,
references.yaml) is derived from it. The doctrine layer (`src/doctrine/`)
provides the reusable knowledge artifacts (directives, tactics, paradigms,
styleguides, toolguides, procedures, agent profiles, step contracts) that
the charter references.

---

## How the Charter System Works

The charter is a **governance-as-code** framework. A human-written markdown
document captures project policy, and the runtime extracts structured YAML from
it to constrain what agents see and do during workflow actions.

### The 3-Layer Model

1. **Charter** (`charter.md`) — Human-editable markdown. The single
   authoritative source. Created via interview or written by hand.

2. **Extracted config** — Machine-readable YAML derived deterministically by
   sync. Never edit these directly — they are overwritten on every sync.
   - `governance.yaml` — Testing, quality, performance, branching, doctrine selections
   - `directives.yaml` — Numbered project rules with severity and scope
   - `metadata.yaml` — Hash, timestamp, extraction mode

3. **Doctrine references** (`library/*.md`) — Detailed guidance documents for
   selected paradigms, directives, and tools. Copied from `src/doctrine/` during
   generation.

### Data Flow

```
Interview Answers (answers.yaml)
        ↓
  [generate command]  ← doctrine templates, mission config
        ↓
Charter (charter.md)  ← authoritative source
        ↓
  [auto-sync triggered]
        ↓
    ├→ governance.yaml      ← extracted structured config
    ├→ directives.yaml      ← extracted numbered rules
    ├→ metadata.yaml        ← hash, timestamp, extraction mode
    └→ library/*.md         ← copied doctrine reference docs
        ↓
  [context command]  at each workflow action
        ↓
    Text injected into agent prompt
```

### How Sync Extraction Works

The sync command parses `charter.md` by classifying section headings
against a keyword map:

| Heading keyword | Target schema |
|---|---|
| `testing`, `test`, `coverage` | `governance.testing` |
| `quality`, `lint` | `governance.quality` |
| `commit` | `governance.commits` |
| `performance` | `governance.performance` |
| `branch` | `governance.branch_strategy` |
| `paradigm`, `tool`, `template` | `governance.doctrine` |
| `directive`, `constraint`, `rule` | `directives.directives` |

For each matched section, the parser extracts structured data from:
1. **Markdown tables** — rows parsed as key-value dicts
2. **YAML code blocks** — parsed directly
3. **Numbered lists** — extracted as directive items
4. **Keyword patterns** — regex matching for quantitative values:
   - `90%+ coverage` → `testing.min_coverage: 90`
   - `TDD required` → `testing.tdd_required: true`
   - `< 2 seconds` → `performance.cli_timeout_seconds: 2.0`
   - `<project-type-checker>` → `testing.type_checking: "<project-type-checker>"`
   - `1 approval` → `quality.pr_approvals: 1`
   - `conventional commits` → `commits.convention: "conventional"`
   - `pre-commit hooks` → `quality.pre_commit_hooks: true`

Doctrine selections (paradigms, directives, tools, template_set) are merged
from YAML blocks and tables that contain keys like `selected_paradigms`,
`available_tools`, or `template_set`.

### governance.yaml Schema

```yaml
testing:
  min_coverage: 90              # Minimum test coverage %
  tdd_required: false           # TDD mandatory
  framework: <project-runner>   # Test framework / runner
  type_checking: "<project-type-checker>" # Type checker
quality:
  linting: "<project-linter>"   # Linter
  pr_approvals: 1               # Required approvals before merge
  pre_commit_hooks: false       # Pre-commit hooks required
commits:
  convention: conventional      # Commit convention (or null)
performance:
  cli_timeout_seconds: 2.0      # Max CLI command duration
  dashboard_max_wps: 100        # Max work packages dashboard displays
branch_strategy:
  main_branch: main             # Primary branch
  dev_branch: null              # Development branch (optional)
  rules: []                     # Branch naming/protection rules
doctrine:
  selected_paradigms: []        # Active paradigm IDs
  selected_directives: []       # Active directive IDs
  available_tools: []           # Active tool IDs
  template_set: null            # Mission template set
enforcement: {}                 # Enforcement policy by domain
```

### directives.yaml Schema

```yaml
directives:
  - id: DIR-001                 # Auto-generated or custom ID
    title: "Short title"        # First 50 chars
    description: "Full text"    # Full description
    severity: warn              # error (blocks), warn (displayed), info (logged)
    applies_to: [implement, review]  # Actions where directive fires
```

### Hash-Based Staleness Detection

Sync uses SHA-256 to detect changes. The hash of `charter.md` content
(whitespace-normalized) is stored in `metadata.yaml`. On sync:
- If hashes match and `--force` not set → skip (idempotent)
- If hashes differ → re-extract
- If no `metadata.yaml` exists → always stale

### How Context Gets Injected Into Workflow Actions

When you run `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.implement`,
or `/spec-kitty.review`, the runtime automatically calls
`spec-kitty charter context --action <action>`. The returned text is
injected into the agent prompt.

**Three context modes:**

| Mode | When | Content |
|---|---|---|
| `bootstrap` | First load for an action | Full policy summary (up to 8 bullets) + reference doc list (up to 10) |
| `compact` | Subsequent loads | Resolved paradigms, directives, tools, template_set only |
| `missing` | No charter exists | Instructions to create one |

First-load state is tracked in `.kittify/charter/context-state.json`.
Each action (specify, plan, implement, review) has an independent first-load
timestamp.

### Doctrine Artifact Kinds

Doctrine organizes knowledge into 8 artifact kinds. Each kind has a
dedicated repository in `DoctrineService`, follows two-source loading
(shipped defaults + project overrides), and is accessible programmatically
or via CLI.

**Directives** — Numbered project rules that constrain agent behavior.
Each directive has a severity (`error`, `warn`, `info`), an `applies_to`
scope listing which actions it fires on, and may reference tactics.
Directives are the *what you must do* layer.

```python
directive = service.directives.get("DIRECTIVE_034")
# directive.title → "Test-First Development"
# directive.severity → "warn"
# directive.applies_to → ["implement", "review"]
```

```bash
spec-kitty doctrine list --kind directive
```

**Tactics** — Reusable implementation approaches that describe *how* to do
something. Tactics cover testing (TDD, ZOMBIES, acceptance-test-first),
domain modeling (bounded context, aggregate boundaries), refactoring
(strangler fig, extract class), review (intent-and-risk-first), and
planning (problem decomposition, eisenhower). The shipped set includes a
refactoring sub-catalog.

```python
tactic = service.tactics.get("tdd-red-green-refactor")
# tactic.title, tactic.description, tactic.steps
```

**Paradigms** — High-level development philosophies that group related
tactics and directives. A paradigm (e.g., `domain-driven-design`) declares
which tactics it recommends. Paradigms are selected during the charter
interview and scope which tactics appear in governance context.

```python
paradigm = service.paradigms.get("domain-driven-design")
# paradigm.tactics → ["bounded-context-identification", ...]
```

**Styleguides** — Language- or domain-specific writing and coding style
rules. Applied when the charter's `languages_frameworks` answer
matches the styleguide's target language.

```python
styleguide = service.styleguides.get("python-conventions")
```

**Toolguides** — Operational guidance for specific tools. Teaches agents
how to use git, the project's test runner, diagramming tools, etc. within the project's
governance constraints.

```python
toolguide = service.toolguides.get("efficient-local-tooling")
```

**Procedures** — Multi-step workflow primitives with prerequisites and
ordered steps. Procedures are the reusable building blocks that step
contracts delegate to. They describe a complete mini-workflow (e.g.,
"refactoring", "test-first-bug-fixing", "situational-assessment").

```python
procedure = service.procedures.get("refactoring")
# procedure.steps → ordered list of actions
# procedure.prerequisites → what must be true before starting
```

**Agent Profiles** — Role definitions with 6 sections: context_sources,
purpose, specialization, collaboration, mode_defaults, and
initialization_declaration. Profiles form a hierarchy (`specializes_from`)
and support weighted matching against task context (DDR-011 algorithm).

```python
profile = service.agent_profiles.get("implementer")
# profile.purpose.mandate → what this agent is responsible for
# profile.specialization.boundaries → what it should not do

# Or resolve the best match for a task:
best = service.agent_profiles.find_best_match(task_context)
```

```bash
spec-kitty agent profile list
spec-kitty agent profile show implementer
```

**Step Contracts** — Structured action definitions that link public actions
(specify, plan, implement, review) to doctrine artifacts via `DelegatesTo`.
Each contract defines ordered steps; each step may delegate to a tactic,
directive, or procedure by kind and candidate list.

```python
contract = service.mission_step_contracts.get("implement")
for step in contract.steps:
    if step.delegates_to:
        # Load the referenced doctrine artifact
        artifact = getattr(service, step.delegates_to.kind + "s").get(
            step.delegates_to.candidates[0]
        )
```

### Discovering Available Artifacts

```bash
# List all artifacts of a kind
spec-kitty doctrine list --kind directive
spec-kitty doctrine list --kind tactic
spec-kitty doctrine list --kind paradigm

# Show detail for one artifact
spec-kitty doctrine show DIRECTIVE_034

# List agent profiles
spec-kitty agent profile list
```

Shipped artifacts live in `src/doctrine/<kind>/shipped/`. Project-local
overrides live in `.kittify/<kind>/`. Two-source loading merges both,
with project artifacts taking precedence on field-level merge.

**Template sets** (from `src/doctrine/missions/`):
- `software-dev-default` — Core development workflow
- `plan-default` — Goal-oriented planning
- `documentation-default` — Documentation creation (Divio)
- `research-default` — Research and evidence gathering

**Default tool registry:** spec-kitty, git

### Interview Profiles

**Minimal** (8 questions — fast bootstrap):

| Question | Governance use |
|---|---|
| `project_intent` | Policy summary, preamble |
| `languages_frameworks` | Styleguide selection (e.g., Python) |
| `testing_requirements` | `testing.framework`, `testing.min_coverage` |
| `quality_gates` | Quality Gates section |
| `review_policy` | `quality.pr_approvals`, Branch Strategy |
| `performance_targets` | `performance.cli_timeout_seconds` |
| `deployment_constraints` | `branch_strategy.rules` |

**Comprehensive** (11 questions — adds 4 more):

| Question | Governance use |
|---|---|
| `documentation_policy` | Added to Project Directives |
| `risk_boundaries` | Added to Project Directives |
| `amendment_process` | Amendment Process section |
| `exception_policy` | Exception Policy section |

### answers.yaml Schema

```yaml
schema_version: "1.0.0"
mission: "software-dev"
profile: "minimal"
answers:
  project_intent: "..."
  languages_frameworks: "..."
  testing_requirements: "..."
  quality_gates: "..."
  review_policy: "..."
  performance_targets: "..."
  deployment_constraints: "..."
  # comprehensive only:
  documentation_policy: "..."
  risk_boundaries: "..."
  amendment_process: "..."
  exception_policy: "..."
selected_paradigms:
  - "<project-paradigm>"
selected_directives:
  - "<project-directive>"
available_tools:
  - "spec-kitty"
  - "git"
  - "<project-tool>"
```

---

## Step 1: Check Current State

```bash
spec-kitty charter status --json
```

Reports `synced` or `stale`, current and stored hashes, library doc count,
and per-file sizes. If `stale`, run sync before relying on governance config.

---

## Step 2: Run the Charter Interview

For agent-mediated governance setup, the preferred interview surface is the chat
itself, not the CLI questionnaire.

Recommended flow:

1. Inspect the repo quickly.
2. Ask the user a short targeted governance interview in chat.
3. Synthesize `.kittify/charter/interview/answers.yaml` directly.
4. Run `spec-kitty charter generate --from-interview --json`.

Use the CLI interview only as a fallback when the user explicitly wants the CLI
prompt loop or wants deterministic defaults.

**CLI defaults path (fallback only):**

```bash
spec-kitty charter interview --mission-type software-dev --profile minimal --defaults --json
```

**CLI comprehensive path (fallback only):**

```bash
spec-kitty charter interview --mission-type software-dev --profile comprehensive
```

Key flags: `--profile minimal|comprehensive`, `--defaults`, `--json`,
`--selected-paradigms`, `--selected-directives`, `--available-tools`.
See `references/charter-command-map.md` for all flags.

**Output:** `.kittify/charter/interview/answers.yaml`

---

## Step 3: Generate the Charter

```bash
spec-kitty charter generate --from-interview --json
```

Key flags: `--mission`, `--template-set`, `--force`, `--from-interview`, `--json`.

Generation triggers an automatic sync, so governance.yaml and directives.yaml
are written immediately.

**Output:** `.kittify/charter/charter.md` plus extracted YAML files
and `library/*.md` reference documents.

---

## Step 4: Load Context for Workflow Actions

Do not preload all action contexts after generation.

The runtime calls context automatically during slash commands. Manual
invocation is useful only for debugging one immediate action, and should avoid
consuming first-load state:

```bash
spec-kitty charter context --action specify --json --no-mark-loaded
```

Load context iteratively at the action boundary, not as part of charter setup.

---

## Step 5: Sync After Manual Edits

```bash
spec-kitty charter sync --json
spec-kitty charter sync --force --json   # re-extract even if unchanged
```

Sync is idempotent — skips extraction when the charter hash is unchanged
unless `--force` is passed.

---

## Programmatic Doctrine Access (DoctrineService)

`DoctrineService` is the single entry point for programmatic access to all
doctrine artifacts. It lazily instantiates repositories on first access.

```python
from doctrine.service import DoctrineService

service = DoctrineService(shipped_root, project_root)
```

### Available Repositories

| Property | Returns | Artifacts |
|---|---|---|
| `service.agent_profiles` | `AgentProfileRepository` | Agent role profiles with DDR-011 matching |
| `service.directives` | `DirectiveRepository` | Numbered project rules (TEST_FIRST, etc.) |
| `service.tactics` | `TacticRepository` | Reusable implementation approaches (TDD, ZOMBIES, etc.) |
| `service.styleguides` | `StyleguideRepository` | Language/domain writing style guides |
| `service.toolguides` | `ToolguideRepository` | Tool-specific operational guidance |
| `service.paradigms` | `ParadigmRepository` | High-level development paradigms |
| `service.procedures` | `ProcedureRepository` | Multi-step reusable workflow primitives |
| `service.mission_step_contracts` | `MissionStepContractRepository` | Structured action contracts with delegation |

### Common Repository Operations

All repositories share a consistent pattern:

```python
# List all artifacts of a kind
all_tactics = service.tactics.list_all()

# Get a specific artifact by ID
tactic = service.tactics.get("tdd-red-green-refactor")

# Save a project-local artifact (procedures, step contracts)
service.procedures.save(my_procedure)
```

### Agent Profile Resolution

Agent profiles support weighted context-based matching. When the runtime
needs to assign an agent to a task, it resolves the best profile:

```python
from doctrine.agent_profiles.profile import TaskContext

context = TaskContext(
    languages=["python"],
    frameworks=["<project-test-runner>", "typer"],
    file_patterns=["src/**/*.py"],
    domain_keywords=["cli", "testing"],
)

profile = service.agent_profiles.find_best_match(context)
# profile.purpose.mandate → what this agent is responsible for
# profile.specialization.boundaries → what it should not do
# profile.initialization_declaration → startup context text
```

Profiles support hierarchy (`specializes_from` field). Language-specific
profiles can specialize from `implementer`, inheriting base capabilities and
adding stack-specific ones.

### Action-Scoped Doctrine via Action Indices

Each mission action (specify, plan, implement, review) has an action index
that lists which doctrine artifacts are relevant to that step:

```python
from doctrine.missions.action_index import load_action_index

index = load_action_index(missions_root, "software-dev", "implement")
# index.directives → ["TEST_FIRST"]
# index.tactics → ["tdd-red-green-refactor", "zombies-tdd"]
# index.procedures → ["implementation-handoff"]
```

The charter context builder uses these indices internally. When you call
`spec-kitty charter context --action implement`, only the doctrine
artifacts listed in the implement action index are included.

### MissionStepContract: Structured Action Contracts

Step contracts define the structure of each public action and link to
doctrine artifacts via `DelegatesTo`:

```python
contract = service.mission_step_contracts.get("implement")
for step in contract.steps:
    if step.delegates_to:
        # step.delegates_to.kind → ArtifactKind (e.g., "tactic")
        # step.delegates_to.candidates → ["tdd-red-green-refactor", ...]
        pass
```

This is the bridge between the mission execution surface and the doctrine
knowledge layer. Step contracts say *what* to do; doctrine artifacts say
*how*.

---

## Iterative Context Loading Pattern

Agents should load doctrine context **iteratively**, not all at once. The
architecture supports this through depth-controlled context and per-artifact
retrieval.

### The Pattern

1. **At session init**: Resolve agent profile. Load `initialization_declaration`.
2. **At each step boundary**: Call `charter context --action <action>`.
   First call gets bootstrap (depth-2), subsequent calls get compact (depth-1).
3. **Mid-step, when guidance needed**: Pull specific tactic or directive by ID
   through `DoctrineService`.
4. **Never**: Load the full doctrine catalog into prompt context.

### Why This Matters

Each doctrine artifact consumes tokens. Loading all directives, tactics,
paradigms, and styleguides at session start wastes context on artifacts that
are irrelevant to the current action. Action indices exist specifically to
scope which artifacts matter for each step.

---

## When Doctrine Constrains Runtime

Doctrine constrains runtime behavior when the charter has been generated
and the agent is executing a workflow action (specify, plan, implement, review).
The specific constraints come from the project's own charter — load them
with `spec-kitty charter context --action <action> --json` rather than
assuming fixed policy values.

Doctrine does NOT constrain when:

- The user works outside a mission.
- No charter has been generated.
- The action is not a workflow action (specify, plan, implement, review).

---

## Governance Anti-Patterns

1. **Editing derived files** — `governance.yaml`, `directives.yaml`, and
   `library/*.md` are overwritten by sync/generate. Edit `charter.md`.
2. **Skipping the interview** — produces generic defaults; the charter
   is most valuable with project-specific decisions.
3. **Stale charter** — an outdated charter silently injects wrong
   policy. Run `status` to check, `sync` to fix.
4. **Legacy path assumptions** — canonical path is
   `.kittify/charter/charter.md`, not `.kittify/memory/`.
5. **Upfront context dump** — loading all doctrine at session start wastes
   tokens and dilutes relevance. Use action-scoped loading and pull specific
   artifacts on demand.

See `references/doctrine-artifact-structure.md` for the full anti-pattern table.

---

## References

- `references/charter-command-map.md` -- Full CLI command reference with all flags and output fields
- `references/doctrine-artifact-structure.md` -- File layout, authority classes, and data flow
