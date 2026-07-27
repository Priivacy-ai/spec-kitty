# Contract — `tasks.step-contract.yaml` schema

**Mission**: `software-dev-composition-rewrite-01KQ26CY`
**Artifact**: `src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml`
**Schema source of truth**: `doctrine.mission_step_contracts.models.MissionStepContract`

## YAML shape (binding)

```yaml
schema_version: "1.0"      # exact string required by repository loader
id: tasks                   # uniquely names this contract within the shipped set
action: tasks               # routes via repo.get_by_action(mission, action)
mission: software-dev       # mission key (exact match)

steps:                      # ordered; executor walks each in sequence
  - id: <step-id>           # unique within this contract; namespaces with contract_id externally
    description: <text>     # human-readable; reproduced in invocation request_text
    command: <string|null>  # optional declared command; executor declares only, never runs
    inputs:                 # optional; CLI-style flag/source pairs
      - flag: --profile
        source: wp.agent_profile
        optional: true
    delegates_to:           # optional; selects DRG artifacts via action context
      kind: <directive|tactic|paradigm|styleguide|toolguide|procedure|agent_profile>
      candidates: [<id-or-name>, ...]
    guidance: <text>        # optional; appended to invocation request_text
```

## Required steps for this contract

| Step ID | Required | Has command | Has delegations | Notes |
|---|---|---|---|---|
| `bootstrap` | yes | yes (charter context) | no | Mirrors specify/plan/implement/review contracts. |
| `outline` | yes | no | yes (tactics: problem-decomposition, requirements-validation-workflow) | Produces `kitty-specs/<mission>/tasks.md`. |
| `packages` | yes | no | yes (directives: 010, 024) | Produces `kitty-specs/<mission>/tasks/WP##.md` files. |
| `finalize` | yes | yes (`spec-kitty agent mission finalize-tasks`) | yes (directive: 024) | Validates dependencies; finalizes WP frontmatter. |

## Validation rules (enforced by executor + tests)

1. `MissionStepContractRepository.get_by_action("software-dev", "tasks")` must return the loaded contract.
2. Every `delegates_to.candidates` value must, after action-context resolution, appear in the `ResolvedContext.artifact_urns` set produced by `resolve_context(graph, "action:software-dev/tasks", depth=2)`. Any unresolved candidate goes into `unresolved_candidates` on the step result and is logged but does not fail the run.
3. The `bootstrap` step's `command` is **declared only**. The host owns execution. (Same convention as the four shipped contracts.)
4. The `finalize` step's declared command is `spec-kitty agent mission finalize-tasks`; this is the canonical existing CLI surface for finalize semantics.
5. No step may write lane state directly. Any lane-state side-effect must invoke `emit_status_transition`. (Cross-cutting; not a YAML rule but a runtime invariant.)

## Negative tests

- Loading the contract with `mission: other-mission` MUST fail repository validation.
- Loading with a `delegates_to.kind` outside the supported set MUST fail repository validation.
- Loading with a duplicate step `id` within the contract MUST fail repository validation.
