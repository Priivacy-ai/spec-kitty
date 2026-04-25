# Mission Types Reference

Spec Kitty supports three built-in mission types, each tailored to a different kind of work. A mission type is the reusable workflow blueprint. A mission is the concrete tracked item under `kitty-specs/<mission-slug>/`.

Terminology note:
- `Mission Type` = reusable blueprint
- `Mission` = concrete tracked item
- `Feature` = software-dev compatibility alias for a mission
- Current legacy command names may still use `feature` wording even when they are acting on a mission

---

## Mission Type Overview

| Mission | Domain | Best For |
|---------|--------|----------|
| `software-dev` | Software development | Building features, APIs, UIs |
| `research` | Research and analysis | Investigations, competitive analysis, technical research |
| `documentation` | Documentation creation | User guides, API docs, tutorials |

---

## software-dev (Default Mission Type)

The default mission type for building software missions such as features.

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
- Adding a new software mission to an application
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

## Selecting a Mission Type

Mission types are selected when `/spec-kitty.specify` creates a new mission. The selected mission type is currently stored in `meta.json` under the historical key `mission`:

```json
{
  "mission": "documentation"
}
```

### During Mission Creation

When you run `/spec-kitty.specify`, you'll be asked to choose a mission type:

```
? Which mission type should this mission use?
  ○ software-dev — Building software features (default)
  ○ research — Research and analysis
  ○ documentation — Creating documentation
```

### Changing Mission

The mission type cannot be changed after mission creation. If you need a different mission type, create a new mission.

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

## Authoring Custom Missions

Custom missions are project-authored mission definitions that the Local Custom Mission Loader discovers, validates, and runs through the same composition path used by the built-in `software-dev` mission. This section is the canonical reference for the `mission.yaml` format. For an operator-narrative walkthrough, see [`kitty-specs/local-custom-mission-loader-01KQ2VNJ/quickstart.md`](../../kitty-specs/local-custom-mission-loader-01KQ2VNJ/quickstart.md).

### YAML shape

A custom mission lives at `.kittify/missions/<mission-key>/mission.yaml`. Top-level keys are `mission` (metadata block) and `steps[]` (ordered list of `PromptStep` entries). The optional `audit_steps[]` list mirrors the same shape and is reserved for end-of-mission audits.

Minimal valid example:

```yaml
mission:
  key: my-custom
  name: My Custom Mission
  version: 0.1.0
  description: Minimal custom mission for the loader reference.

steps:
  - id: do-the-thing
    title: Do the thing
    description: A composed step that delegates to a profile-bound agent.
    agent_profile: researcher-robbie

  - id: retrospective
    title: Mission retrospective marker
    description: Reserved structural marker; execution lands in a later tranche.
    depends_on: [do-the-thing]
```

### Step fields

Every entry in `steps[]` is a `PromptStep`. The table below covers every author-facing field; `id` and `title` are required on every step, and at least one of `agent_profile` / `contract_ref` / `requires_inputs` must be present so the step has a meaningful binding.

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `id` | yes | str | Unique within the mission; the final step's `id` MUST be `retrospective`. |
| `title` | yes | str | Short human label rendered in the Kanban / panels. |
| `description` | no | str | Free-form prose. Recommended for clarity. |
| `agent_profile` (alias `agent-profile`) | conditional | str | Profile key for composed steps. Required unless the step uses `contract_ref` or is a `requires_inputs` gate. Both snake-case and kebab-case YAML keys are accepted. |
| `contract_ref` | conditional | str | Reference to an existing `MissionStepContract` ID. Mutually exclusive with `agent_profile`. |
| `requires_inputs` | no | list[str] | Marks the step as a decision-required gate. The runtime pauses and the operator answers via `spec-kitty agent decision resolve …`. |
| `depends_on` | no | list[str] | Step IDs this step waits on. Used for dependency-aware ordering. |
| `raci` | no | object | Optional RACI override (`responsible`, `accountable`, `consulted`, `informed`). |
| `raci_override_reason` | no | str | Required string explanation when `raci` is set. |

### The retrospective marker

Every custom mission MUST declare a final `PromptStep` whose `id == "retrospective"`. The validator checks one rule: the last entry of `steps[]` (after dependency-aware sort) has `id == "retrospective"`. Missing or misnamed markers are rejected with the stable error code `MISSION_RETROSPECTIVE_MISSING`.

Execution semantics for the marker step are deferred to the retrospective-execution tranche (#506–#511); v1 only enforces the structural rule. See [research §R-001](../../kitty-specs/local-custom-mission-loader-01KQ2VNJ/research.md) for the rationale.

### Profile binding

A composed step needs a profile so the runtime knows which agent persona to dispatch through `StepContractExecutionContext`. There are two binding surfaces:

- `agent_profile`: per-step inline declaration. The loader's contract synthesizer auto-generates a single-step `MissionStepContract` for the step. This is the ergonomic default for most authors.
- `contract_ref`: reference to a pre-existing `MissionStepContract` ID in the on-disk repository. Use this when multiple missions share the same contract or when a contract's execution rules need to be authored separately. If the referenced contract does not resolve, the loader rejects with `MISSION_CONTRACT_REF_UNRESOLVED`.

Declaring both `agent_profile` and `contract_ref` on the same step is rejected with `MISSION_STEP_AMBIGUOUS_BINDING`. Declaring neither (and having no `requires_inputs`) is rejected with `MISSION_STEP_NO_PROFILE_BINDING`. See [research §R-003](../../kitty-specs/local-custom-mission-loader-01KQ2VNJ/research.md) for the full rationale.

YAML examples:

```yaml
# Inline profile binding — most common.
- id: gather-data
  title: Gather data
  agent_profile: researcher-robbie

# Reuse an existing contract.
- id: gather-data
  title: Gather data
  contract_ref: shared-research-contract-v1
```

### Reserved keys

The following `mission.key` values are reserved for built-in missions and cannot be used by custom mission definitions:

- `software-dev`
- `research`
- `documentation`
- `plan`

Any non-builtin discovery tier that produces a definition with one of these keys is rejected at load time with the stable error code `MISSION_KEY_RESERVED`. Built-in dispatch logic is hard-coded to these keys, so silent shadowing would be a footgun. To customize behavior of a built-in workflow, rename your mission to a non-reserved key. See [research §R-002](../../kitty-specs/local-custom-mission-loader-01KQ2VNJ/research.md) for the rationale.

### Discovery precedence

The loader queries seven tiers in priority order; the highest-precedence tier wins. Lower-precedence definitions of the same key emit a `MISSION_KEY_SHADOWED` warning (except built-in shadow, which is the `MISSION_KEY_RESERVED` error above).

1. **Explicit path** — `--mission-path <path>` (env-forwarded; not exposed by `mission run` directly in v1).
2. **Environment variable** — `SPEC_KITTY_MISSION_PATHS=/path/one:/path/two`.
3. **Project override** — `.kittify/overrides/missions/<key>/mission.yaml`.
4. **Project legacy** — `.kittify/missions/<key>/mission.yaml`.
5. **User global** — `~/.kittify/missions/<key>/mission.yaml`.
6. **Project config (mission packs)** — `.kittify/config.yaml mission_packs: [...]` referencing `mission-pack.yaml` manifests.
7. **Built-in** — `software-dev`, `research`, `documentation`, `plan`.

### Validation error codes

The loader emits a closed enumeration of error and warning codes. Wire spellings are stable: removal or rename is a breaking change requiring a deprecation cycle. Additions are non-breaking. Tooling MAY rely on string equality on `error_code` / warning `code` and MUST NOT fail on unknown `details` keys.

<!-- This table mirrors kitty-specs/local-custom-mission-loader-01KQ2VNJ/contracts/validation-errors.md.
     Mission-review verifies parity. -->

Errors (exit code 2):

| Code | When | Required `details` keys |
| --- | --- | --- |
| `MISSION_YAML_MALFORMED` | Discovery scanned a file but failed to parse it as YAML, OR `MissionTemplate.model_validate` raised `ValidationError`. | `file`, `parse_error` |
| `MISSION_REQUIRED_FIELD_MISSING` | Top-level `mission.key`, `mission.name`, `mission.version`, or `steps[]` missing. (A specific subset of `MISSION_YAML_MALFORMED` surfaced separately for operator clarity.) | `file`, `mission_key` (best-effort), `field` |
| `MISSION_KEY_UNKNOWN` | The user invoked `spec-kitty mission run <key>` but no discovery tier produced a definition with that key. | `mission_key`, `tiers_searched` (list[str]) |
| `MISSION_KEY_AMBIGUOUS` | Two or more tiers produced the same key AND the resolver could not pick a single selected entry (extreme edge case; default precedence picks one). Reserved for future use. | `mission_key`, `paths` (list[str]) |
| `MISSION_KEY_RESERVED` | A non-builtin tier produced a definition whose `mission.key` is in `RESERVED_BUILTIN_KEYS`. | `mission_key`, `file`, `tier`, `reserved_keys` |
| `MISSION_RETROSPECTIVE_MISSING` | Validator R-001: the last step's `id` is not `"retrospective"`. | `file`, `mission_key`, `actual_last_step_id`, `expected: "retrospective"` |
| `MISSION_STEP_NO_PROFILE_BINDING` | Validator FR-008: a step with empty `requires_inputs` declares neither `agent_profile` nor `contract_ref`. | `file`, `mission_key`, `step_id` |
| `MISSION_STEP_AMBIGUOUS_BINDING` | Validator: a step declares both `agent_profile` AND `contract_ref`. | `file`, `mission_key`, `step_id` |
| `MISSION_CONTRACT_REF_UNRESOLVED` | A step's `contract_ref` does not resolve in the on-disk `MissionStepContractRepository`. | `file`, `mission_key`, `step_id`, `contract_ref` |

Warnings (exit code unaffected; included in envelope):

| Code | When | Required `details` keys |
| --- | --- | --- |
| `MISSION_KEY_SHADOWED` | A definition was discovered in multiple tiers; the higher-precedence tier wins. Emitted for non-built-in keys (built-in shadow is an error per `MISSION_KEY_RESERVED`). | `mission_key`, `selected_path`, `selected_tier`, `shadowed_paths` |
| `MISSION_PACK_LOAD_FAILED` | A mission-pack manifest pointed at a `mission.yaml` that failed to load. | `pack_root`, `failed_path`, `parse_error` |

Detail key conventions:

- All paths are absolute strings.
- `mission_key` is the value of `template.mission.key` once known; `null` when unknown.
- `tier` ∈ `{"explicit", "env", "project_override", "project_legacy", "user_global", "project_config", "builtin"}`.
- `step_id` is the `PromptStep.id` value.

### Example: ERP integration mission

The reference fixture used by the loader's test suite lives at [`tests/fixtures/missions/erp-integration/mission.yaml`](../../tests/fixtures/missions/erp-integration/mission.yaml). The fixture is the **authoritative** copy of this example: any drift between the fixture and the operator narrative in [quickstart.md](../../kitty-specs/local-custom-mission-loader-01KQ2VNJ/quickstart.md) is resolved in favor of the fixture, since the fixture is what the test suite executes against.

Inline copy of the fixture:

```yaml
mission:
  key: erp-integration
  name: ERP Integration
  version: 0.1.0
  description: Lookup an ERP record, ask the operator a question, and emit a JS adapter.

steps:
  - id: query-erp
    title: Query the ERP system
    description: Pull the active record set from the ERP integration endpoint.
    agent_profile: researcher-robbie

  - id: lookup-provider
    title: Look up the matching provider
    agent_profile: researcher-robbie
    depends_on: [query-erp]

  - id: ask-user
    title: Confirm the export shape
    description: Ask the operator which export shape to emit.
    requires_inputs: [export_shape]
    depends_on: [lookup-provider]

  - id: create-js
    title: Generate the JS adapter
    agent_profile: implementer-ivan
    depends_on: [ask-user]

  - id: refactor-function
    title: Refactor the legacy function
    agent_profile: implementer-ivan
    depends_on: [create-js]

  - id: write-report
    title: Summarize the run
    agent_profile: researcher-robbie
    depends_on: [refactor-function]

  - id: retrospective
    title: Mission retrospective marker
    description: Reserved structural marker; execution lands in #506-#511.
    depends_on: [write-report]
```

CLI invocations:

**1. Default panel output (success)**

```bash
$ spec-kitty mission run erp-integration --mission erp-q3-rollout
```

A `rich.panel.Panel` titled "Mission Run Started" is rendered. The body shows the success message, `feature_dir`, and `run_dir`. Exit code 0.

**2. JSON envelope (success)**

```bash
$ spec-kitty mission run erp-integration --mission erp-q3-rollout --json
{
  "result": "success",
  "mission_key": "erp-integration",
  "mission_slug": "erp-q3-rollout-01KQ…",
  "mission_id": "01KQ…",
  "feature_dir": "/abs/path/kitty-specs/erp-q3-rollout-01KQ…",
  "run_dir": "/abs/path/.kittify/runtime/runs/<run-id>",
  "warnings": []
}
```

Exit code 0. `warnings` is a list of `{code, message, details}` objects.

**3. JSON envelope (error)**

```bash
$ spec-kitty mission run no-such-key --mission x --json
{
  "result": "error",
  "error_code": "MISSION_KEY_UNKNOWN",
  "message": "No mission definition with key 'no-such-key' was found in any discovery tier.",
  "details": {
    "mission_key": "no-such-key",
    "tiers_searched": ["explicit", "env", "project_override", "project_legacy", "user_global", "project_config", "builtin"]
  },
  "warnings": []
}
```

Exit code 2. Validation errors do NOT start a run; the `kitty-specs/<slug>/` directory is not created.

For the operator-narrative walkthrough (decision resolution, advancement, recovery from validation failures), see [`kitty-specs/local-custom-mission-loader-01KQ2VNJ/quickstart.md`](../../kitty-specs/local-custom-mission-loader-01KQ2VNJ/quickstart.md).

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
