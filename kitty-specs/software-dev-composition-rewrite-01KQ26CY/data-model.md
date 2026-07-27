# Data Model — Software-Dev Mission Composition Rewrite

**Mission**: `software-dev-composition-rewrite-01KQ26CY`
**Phase**: 1 (design)
**Date**: 2026-04-25

This slice introduces no new persistent data model. All "data" is declarative configuration (one new YAML file, one Python lookup table extension, one integration seam with typed in-memory contexts). This document captures the shape of each.

---

## Entity 1 — `tasks.step-contract.yaml` (new file)

**Path**: `src/doctrine/mission_step_contracts/shipped/tasks.step-contract.yaml`

**Schema**: Conforms to `doctrine.mission_step_contracts.models.MissionStepContract` (`schema_version: "1.0"`).

**Shape** (binding spec — see contracts/tasks-step-contract-schema.md for full schema):

```yaml
schema_version: "1.0"
id: tasks
action: tasks
mission: software-dev
steps:
  - id: bootstrap
    description: Load charter context for this action
    command: "spec-kitty charter context --action tasks --role tasks --json"
    inputs:
      - flag: --profile
        source: wp.agent_profile
        optional: true
      - flag: --tool
        source: env.agent_tool
        optional: true

  - id: outline
    description: Produce tasks.md — the work-package outline derived from the plan
    delegates_to:
      kind: tactic
      candidates:
        - problem-decomposition
        - requirements-validation-workflow

  - id: packages
    description: Generate individual tasks/WP##.md prompt files
    delegates_to:
      kind: directive
      candidates:
        - 010-specification-fidelity-requirement
        - 024-locality-of-change

  - id: finalize
    description: Validate dependencies and finalize WP metadata
    command: "spec-kitty agent mission finalize-tasks"
    delegates_to:
      kind: directive
      candidates:
        - 024-locality-of-change
```

**Validation rules**:
- `id`, `action`, `mission` must each be `tasks`/`tasks`/`software-dev` exactly. Repository validation in the executor will fail loudly otherwise.
- Every `delegates_to.candidates` entry must be present in `actions/tasks/index.yaml` (current set: directives 003, 010, 024; tactics adr-drafting-workflow, problem-decomposition, requirements-validation-workflow). The contract above respects that.
- Step IDs are namespaced inside the contract — they may collide with step IDs in other contracts (e.g. `bootstrap`); only `(contract_id, step_id)` is unique.

**State transitions**: None. This is declarative configuration loaded at executor startup.

---

## Entity 2 — `_ACTION_PROFILE_DEFAULTS` extension

**Path**: `src/specify_cli/mission_step_contracts/executor.py`

**Current state** (line 36):

```python
_ACTION_PROFILE_DEFAULTS: dict[tuple[str, str], str] = {
    ("software-dev", "specify"): "researcher-robbie",
    ("software-dev", "plan"): "architect-alphonso",
    ("software-dev", "implement"): "implementer-ivan",
    ("software-dev", "review"): "reviewer-renata",
}
```

**Post-rewrite** (one entry added):

```python
_ACTION_PROFILE_DEFAULTS: dict[tuple[str, str], str] = {
    ("software-dev", "specify"): "researcher-robbie",
    ("software-dev", "plan"): "architect-alphonso",
    ("software-dev", "tasks"): "architect-alphonso",   # NEW (D-2)
    ("software-dev", "implement"): "implementer-ivan",
    ("software-dev", "review"): "reviewer-renata",
}
```

**Validation rules**: One entry per `(mission, action)` pair. The runtime asserts profile resolution via `_resolve_profile_hint` — operator `--profile` overrides; otherwise the table is consulted; otherwise `StepContractExecutionError` fires.

---

## Entity 3 — Integration seam in `runtime_bridge.py`

**Path**: `src/specify_cli/next/runtime_bridge.py`

**Composition dispatch contract**:

| Input | Source | Required |
|---|---|---|
| `mission` | runtime DAG step's mission key (e.g. `"software-dev"`) | yes |
| `action` | normalized step ID (legacy `tasks_outline`/`tasks_packages`/`tasks_finalize` collapse to `"tasks"`) | yes |
| `repo_root` | bridge's `repo_root` | yes |
| `actor` | bridge's resolved actor (default `"unknown"`) | yes |
| `profile_hint` | optional `--profile` from CLI | no |
| `request_text` | optional invocation prompt text | no |
| `mode_of_work` | optional `ModeOfWork` from CLI | no |

**Dispatch rule** (single decision point):

```
IF  mission == "software-dev"
AND action ∈ {"specify","plan","tasks","implement","review"}
THEN call StepContractExecutor.execute(StepContractExecutionContext(...))
ELSE fall through to existing legacy DAG path
```

**Outputs**:
- Success: `StepContractExecutionResult` with `invocation_ids` chain. Bridge then runs the (possibly migrated) CLI guard for the action against the on-disk artifacts.
- Failure (`StepContractExecutionError`): bridge propagates as a structured CLI error (non-zero exit, message preserved). FR-009.

**Invariants**:
- Lane-state writes inside any composed step continue to use `emit_status_transition` (typed substrate). FR-007 / C-003.
- The composed `tasks` step's post-action guard asserts: `tasks.md` exists, `tasks/` contains ≥1 `WP*.md` file, and every `WP*.md` has a raw `dependencies:` field in its frontmatter (reuses `_has_raw_dependencies_field`). This collapses the legacy three-step guard into one without weakening assertions.

---

## Entity 4 — Deprecation header on legacy template

**Path**: `src/doctrine/missions/software-dev/mission-runtime.yaml`

**Change**: Prepend a comment block. No functional change to YAML body.

```yaml
# DEPRECATED (since #503 / phase 6 wp6.2): this template is no longer the
# authoritative source for action dispatch on the built-in software-dev
# mission. The live runtime path is now driven by mission step contracts
# under src/doctrine/mission_step_contracts/shipped/ via
# StepContractExecutor + ProfileInvocationExecutor composition. This file
# is retained as a transitional reference and may be removed in a future
# slice. Do not extend it.
```

**Validation**: YAML parser must still load the file unchanged (header lines are pure comments). Existing tests that parse this template continue to pass.

---

## Cross-entity invariants

- **Action governance scope is inherited only from `actions/<action>/index.yaml`.** No composed step pulls in directives from another action's slice. Verified by the test that asserts each composed action's resolved `ResolvedContext.artifact_urns` is a subset of the URNs declared in its `index.yaml`.
- **Profile defaults are only consulted when no operator `--profile` was passed.** Existing executor logic.
- **No raw lane string writes.** Any code path inside the composed steps that touches lane state must go through `emit_status_transition`. Asserted by the integration test.
