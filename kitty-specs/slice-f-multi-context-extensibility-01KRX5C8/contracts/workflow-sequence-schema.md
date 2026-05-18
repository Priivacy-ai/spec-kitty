# Contract — Workflow Sequence Schema

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Closes: FR-012, FR-013, FR-014, FR-015 | Companions: [contract-round-trip-frontmatter.md](contract-round-trip-frontmatter.md)
> Data model: [../data-model.md §5](../data-model.md#5-workflowsequence-fr-012), [../data-model.md §6](../data-model.md#6-actionstep-fr-012)

Workflow sequence is the **first-class artifact** representing a mission's action sequence (`specify → plan → tasks → implement → review → merge` today). Slice F promotes it from a hardcoded constant to a doctrine-side YAML.

---

## Input Contract

### Operator-facing surface — workflow YAML

A workflow lives at `src/doctrine/workflows/<workflow_id>.workflow.yaml`. The default (byte-stable with today) is shipped at `src/doctrine/workflows/software-dev-default.workflow.yaml`.

#### Example: default workflow (byte-stable, C-008)

```yaml
# pydantic_model: specify_cli.next._internal_runtime.workflow_schema.WorkflowSequence
# expect: valid
workflow_id: software-dev-default
description: |
  The default Spec Kitty action sequence: specify -> plan -> tasks ->
  implement -> review -> merge. Byte-stable with the pre-Slice-F
  hardcoded behaviour (Mission C C-008).
version: 1
initial: specify
actions:
  - action_name: specify
    next: [plan]
    description: "Author the mission specification."
  - action_name: plan
    next: [tasks]
    description: "Author the implementation plan."
  - action_name: tasks
    next: [implement]
    description: "Decompose the plan into work packages."
  - action_name: implement
    next: [review]
    description: "Execute the next ready work package."
  - action_name: review
    next: [merge]
    description: "Review the implemented work package."
  - action_name: merge
    next: []
    description: "Merge approved work packages."
    terminal: true
```

#### Example: team workflow with an extra `design-review` step (fixture for AC-4)

```yaml
# pydantic_model: specify_cli.next._internal_runtime.workflow_schema.WorkflowSequence
# expect: valid
workflow_id: our-team-design-first
description: "Team workflow with mandatory design-review between plan and tasks."
version: 1
initial: specify
actions:
  - action_name: specify
    next: [plan]
    description: "Author the mission specification."
  - action_name: plan
    next: [design-review]
    description: "Author the implementation plan."
  - action_name: design-review
    next: [tasks]
    description: "Design lead reviews the plan before task decomposition."
  - action_name: tasks
    next: [implement]
    description: "Decompose into work packages."
  - action_name: implement
    next: [review]
    description: "Execute the next ready work package."
  - action_name: review
    next: [merge]
    description: "Review the implemented work package."
  - action_name: merge
    next: []
    description: "Merge."
    terminal: true
```

#### Invalid example: dangling `next` reference

```yaml
# pydantic_model: specify_cli.next._internal_runtime.workflow_schema.WorkflowSequence
# expect: invalid
workflow_id: bogus
description: "Has a dangling next reference."
version: 1
initial: specify
actions:
  - action_name: specify
    next: [does-not-exist]   # ← FR-012 invariant violated
    description: "Bogus."
```

### Operator-facing surface — `meta.json.workflow_id`

A mission's `meta.json` carries an optional `workflow_id` field (FR-013):

```json
{
  "mission_id": "01KRX5C8MQRGG7WJW1YK53DTF5",
  "mission_slug": "...",
  "workflow_id": "our-team-design-first"
}
```

Absent or `null` ⇒ resolves to `software-dev-default` (NEW-2: permanent default).

---

## Output Contract

### Registry API

```python
from specify_cli.next._internal_runtime.workflow_registry import get_workflow

workflow = get_workflow("software-dev-default")
# workflow.actions[0].action_name == "specify"
# workflow.actions[0].next == ["plan"]
```

### Resolution at `spec-kitty next` time

1. Read `kitty-specs/<mission>/meta.json` and extract `workflow_id` (default `None`).
2. If `workflow_id is None`, resolve to `software-dev-default`.
3. Look up the workflow via `get_workflow(workflow_id)`.
4. Determine the current action from the mission's lane state (existing logic, unchanged).
5. Compute the next action from the workflow's action graph (the `next` list of the current action's `ActionStep`; first element for linear interpretation).
6. Return the next action via the existing `NextDecision` / prompt-builder pipeline.

### Byte-stability guarantee (C-008, FR-014)

For every `(current_action, next_action)` transition the pre-Slice-F hardcoded sequence produced, the `software-dev-default` workflow MUST produce the same transition. Pinned by `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py`:

```python
HARDCODED_TRANSITIONS = [
    ("specify", "plan"),
    ("plan", "tasks"),
    ("tasks", "implement"),
    ("implement", "review"),
    ("review", "merge"),
]

def test_default_workflow_byte_stable():
    workflow = get_workflow("software-dev-default")
    transitions = [(a.action_name, a.next[0]) for a in workflow.actions if a.next]
    assert transitions == HARDCODED_TRANSITIONS
```

---

## Failure modes

| Trigger | Exception | Operator message |
|---|---|---|
| `meta.json.workflow_id` references an unknown id | `UnknownWorkflowError` | "Unknown workflow id `<id>`. Available workflows: `<list-from-src/doctrine/workflows/>`." (FR-015 — **no silent fallback**) |
| Workflow YAML has a dangling `next` reference | `pydantic.ValidationError` at load time | Per pydantic; names the offending action and the dangling reference |
| Workflow YAML has a cyclic action graph | `WorkflowCycleError` | "Workflow `<id>` action graph contains a cycle: `<cycle>`. Action graphs MUST be acyclic." |
| `software-dev-default.workflow.yaml` is missing from `src/doctrine/workflows/` | `WorkflowRegistryError` | "Default workflow `software-dev-default` is missing from `src/doctrine/workflows/`. This is a Spec Kitty installation defect; reinstall the package." (regression-catching only; shipped files are expected present) |
| Workflow YAML declares `terminal: true` AND a non-empty `next` | `pydantic.ValidationError` | Per FR-012 invariant; names the action |
| `version` is not `1` | `WorkflowVersionUnsupportedError` | "Workflow `<id>` declares schema version `<n>`; this Spec Kitty release supports version `1` only." (forward-compat hook for future schema extensions, RR-9) |

---

## Backward compatibility guarantee

- **Pre-Slice-F missions** (every mission with `meta.json` lacking `workflow_id`) continue to work unchanged — they implicitly resolve to `software-dev-default` (NEW-2 binding).
- **No silent semantic drift** between the hardcoded path and the default-via-YAML path (C-008 byte-stability).
- The Mission B test surfaces in `tests/specify_cli/next/test_wp_prompt_governance_contract.py` pass unchanged (NFR-001).
- No retroactive migration is run on historical missions (C-002 forward-only).

---

## ATDD anchors

- `tests/specify_cli/next/test_workflow_registry.py` (unit; load + cache + unknown-id hard-fail; FR-012, FR-015)
- `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py` (C-008, FR-014)
- `tests/integration/test_workflow_sequence_runtime.py` (Scenario 3; AC-4 — uses the `our-team-design-first` fixture)
- `tests/contract/test_example_round_trip.py` (exercises the `expect: valid` and `expect: invalid` examples above via FR-140)
