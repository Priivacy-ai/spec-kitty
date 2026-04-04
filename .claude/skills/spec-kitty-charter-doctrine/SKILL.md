---
name: spec-kitty-charter-doctrine
description: >-
  Run charter interview, generation, context, and sync workflows for
  project governance in Spec Kitty 2.x.
  Triggers: "interview for charter", "generate charter",
  "charter sync", "use doctrine", "set up governance",
  "charter status", "extract governance config".
  Does NOT handle: generic spec writing not tied to governance, direct runtime
  loop advancement, setup/repair diagnostics, or editorial glossary maintenance.
---

# spec-kitty-charter-doctrine

Manage the charter lifecycle: interview, generate, context-load, sync,
and status. The charter is the single authoritative governance document
for a Spec Kitty project. All structured config (governance.yaml,
directives.yaml, references.yaml) is derived from it.

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
   - `mypy --strict` → `testing.type_checking: "mypy --strict"`
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
  framework: pytest             # Test framework
  type_checking: "mypy --strict" # Type checker
quality:
  linting: ruff                 # Linter
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

### Available Doctrine Assets

**Paradigms** (from `src/doctrine/paradigms/`):
- `test-first` — Prefer acceptance-first and red-green-refactor loops

**Directives** (from `src/doctrine/directives/`):
- `TEST_FIRST` — Require test-first behavior across acceptance and implementation.
  References tactics: acceptance-test-first, tdd-red-green-refactor, zombies-tdd.

**Template sets** (from `src/doctrine/missions/`):
- `software-dev-default` — Core development workflow
- `plan-default` — Goal-oriented planning
- `documentation-default` — Documentation creation (Divio)
- `research-default` — Research and evidence gathering

**Styleguides** (from `src/doctrine/styleguides/`):
- `python-implementation` — Python coding principles
- `kitty-glossary-writing` — Glossary authoring style

**Default tool registry:** spec-kitty, git, python, pytest, ruff, mypy, poetry

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
  - "test-first"
selected_directives:
  - "TEST_FIRST"
available_tools:
  - "spec-kitty"
  - "git"
  - "python"
  - "pytest"
  - "ruff"
  - "mypy"
  - "poetry"
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

**Fast path (deterministic defaults):**

```bash
spec-kitty charter interview --mission software-dev --profile minimal --defaults --json
```

**Full interactive interview:**

```bash
spec-kitty charter interview --mission software-dev --profile comprehensive
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

Load governance context before each workflow action:

```bash
spec-kitty charter context --action specify --json
spec-kitty charter context --action plan --json
spec-kitty charter context --action implement --json
spec-kitty charter context --action review --json
```

The runtime calls context automatically during slash commands. Manual
invocation is useful for debugging what governance policy an action receives.

---

## Step 5: Sync After Manual Edits

```bash
spec-kitty charter sync --json
spec-kitty charter sync --force --json   # re-extract even if unchanged
```

Sync is idempotent — skips extraction when the charter hash is unchanged
unless `--force` is passed.

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

See `references/doctrine-artifact-structure.md` for the full anti-pattern table.

---

## References

- `references/charter-command-map.md` -- Full CLI command reference with all flags and output fields
- `references/doctrine-artifact-structure.md` -- File layout, authority classes, and data flow
