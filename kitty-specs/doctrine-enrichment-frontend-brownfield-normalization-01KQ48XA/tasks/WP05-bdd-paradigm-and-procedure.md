---
work_package_id: WP05
title: BDD Paradigm and Procedure
dependencies: []
requirement_refs:
- FR-009
- FR-010
planning_base_branch: feature/doctrine-enrichment-bdd-profiles
merge_target_branch: feature/doctrine-enrichment-bdd-profiles
branch_strategy: Planning artifacts for this feature were generated on feature/doctrine-enrichment-bdd-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/doctrine-enrichment-bdd-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: "claude:sonnet:curator-carla:implementer"
shell_pid: "96504"
history:
- timestamp: '2026-04-26T08:49:24Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/paradigms/shipped/
execution_mode: code_change
owned_files:
- src/doctrine/paradigms/shipped/behaviour-driven-development.paradigm.yaml
- src/doctrine/procedures/shipped/bdd-scenario-lifecycle.procedure.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Create the `behaviour-driven-development` paradigm (encoding BDD as a three-phase collaboration practice) and the `bdd-scenario-lifecycle` procedure (Formulation → Automation → Maintenance). These artifacts are referenced by profile enrichments in WP06, WP07, and WP08.

**Relationship to existing doctrine**:
- `specification-by-example` paradigm (existing): broader technique of using concrete examples
- `behaviour-driven-development` paradigm (new): specific collaboration model + toolchain mandate
- `example-mapping-workshop` procedure (existing): Discovery phase of BDD
- `bdd-scenario-lifecycle` procedure (new): Formulation → Automation → Maintenance phases

---

## Subtask T018 — Create `behaviour-driven-development.paradigm.yaml`

**File**: `src/doctrine/paradigms/shipped/behaviour-driven-development.paradigm.yaml`

**Schema** (from `paradigm.schema.yaml`): required: `schema_version`, `id`, `name`, `summary`. Optional: `directive_refs`, `opposed_by`.

```yaml
schema_version: "1.0"
id: behaviour-driven-development
name: Behaviour-Driven Development
summary: >
  BDD is a collaboration practice, not a testing methodology. It operates through
  three cyclical phases: Discovery (structured Three Amigos conversations — product
  owner, developer, tester — produce concrete, validated behavioral examples before
  any code is written), Formulation (validated examples are expressed in plain-language
  Given/When/Then specifications that serve as the canonical behavioral contract), and
  Automation (formulated specifications are connected to executable tests that fail
  when the system diverges from the spec, producing living documentation that cannot
  become stale). BDD does not replace unit testing — it sits above the test pyramid
  and is reserved for behaviors with genuine cross-functional business value. The Three
  Amigos is the minimum collaboration unit: one person representing the business need,
  one who will build it, one who will verify it. Distinct from Specification by Example
  (the broader technique); BDD mandates the collaboration process and executable
  automation as the canonical specification form.
directive_refs:
  - DIRECTIVE_034
  - DIRECTIVE_037
```

**Validation**: The existing `specification-by-example.paradigm.yaml` must NOT be modified. The two paradigms coexist — check that both load after this WP.

---

## Subtask T019 — Create `bdd-scenario-lifecycle.procedure.yaml`

**File**: `src/doctrine/procedures/shipped/bdd-scenario-lifecycle.procedure.yaml`

**Schema** (from procedure schema): required: `schema_version`, `id`, `name`, `purpose`, `entry_condition`, `exit_condition`, `steps[]` (title, description, actor). Optional: `anti_patterns`, `references`.

```yaml
schema_version: "1.0"
id: bdd-scenario-lifecycle
name: BDD Scenario Lifecycle
purpose: >
  Guide the Formulation, Automation, and Maintenance phases of the BDD cycle,
  picking up where the Example Mapping Workshop (Discovery phase) leaves off.
  Covers translating validated examples into Gherkin specifications, wiring them
  to executable step definitions, and maintaining them as living documentation
  as the system evolves. Toolchain-agnostic — applicable with Cucumber-JVM,
  Cucumber-JS, Behave, SpecFlow, or any Given/When/Then runner.
entry_condition: >
  A canonical set of behavioral examples has been validated with stakeholders,
  typically via the example-mapping-workshop procedure. Each example is expressed
  as a concrete scenario (precondition, action, observable outcome) and has been
  confirmed as representing the intended system behavior.
exit_condition: >
  Each validated example exists as a passing, executable scenario in the test suite.
  No scenario is in a permanently skipped or pending state. The feature file is
  human-readable by a non-technical audience — a product owner can read it and
  confirm it describes the system correctly.
steps:
  - title: Express each example as a Gherkin scenario
    description: >
      Translate each validated example into a Gherkin feature file using
      Feature / Scenario / Given / When / Then structure. Write in domain language —
      use the terms agreed in the Example Mapping session. Avoid implementation
      detail (no database field names, API method names, or UI element IDs in
      the scenario text). One scenario per concrete example.
    actor: agent
  - title: Validate Gherkin readability with a non-technical reviewer
    description: >
      Ask a product owner, analyst, or domain expert to read each scenario and
      confirm it describes what they intended. If a scenario confuses or surprises
      them, revise it. Scenarios that only developers can read have lost their
      communication value — they are expensive test code that provides no additional
      documentation benefit.
    actor: human
  - title: Wire step definitions to application code
    description: >
      For each Given/When/Then step, write or reuse a step definition that implements
      the step using the application's public interface (not internal methods, not
      database queries directly). Use page objects or equivalent abstractions for
      UI steps. Ensure step definitions are reusable across scenarios where the
      step text is identical.
    actor: agent
  - title: Run scenarios red, then implement until green
    description: >
      Run the full suite. New scenarios must fail first (red) — if they pass without
      any implementation, the step definitions are incorrect or the behavior already
      existed. Implement the minimum production code required to pass the failing
      scenarios. Do not write production code beyond what the failing scenarios require.
    actor: agent
  - title: Publish to living documentation
    description: >
      Ensure the CI pipeline runs the BDD suite and publishes the report (HTML
      narrative, Serenity report, or equivalent). The published report is the
      living documentation artifact — it must be accessible to non-technical
      stakeholders and must fail visibly when a scenario breaks.
    actor: agent
  - title: Maintain scenarios as behavior changes
    description: >
      When a business requirement changes, update the Gherkin scenario first, run it
      red, then update the implementation. A scenario that silently passes after a
      requirement change (without being updated) indicates the step definition is
      too loosely coupled to the application contract.
    actor: agent
    on_failure: >
      If scenarios cannot be kept current due to scope, mark them @wip and assign
      an owner. A permanently @wip scenario is a documentation debt — escalate.
anti_patterns:
  - name: Imperative Gherkin
    description: >
      Scenarios that describe UI clicks and form fills rather than business intent.
      "Click the Submit button" is imperative. "Complete the order" is declarative.
      Imperative scenarios break when the UI changes, even if the behavior is unchanged.
  - name: Rubber-stamp scenarios
    description: >
      Scenarios written after the implementation passes to satisfy a process requirement.
      These scenarios always start green and provide no regression protection —
      they cannot fail because the code was not written to make them fail first.
  - name: Shared mutable state between scenarios
    description: >
      Scenario B relying on data created by Scenario A. When Scenario A is skipped or
      fails, Scenario B fails for the wrong reason. Each scenario must establish its own
      preconditions via Given steps.
  - name: Orphaned step definitions
    description: >
      Step definitions with no matching feature file step. Accumulate silently as
      scenarios evolve. Run `cucumber --dry-run` (or equivalent) regularly to detect them.
references:
  - type: procedure
    id: example-mapping-workshop
    reason: >
      The Discovery phase that produces the validated examples this procedure begins with.
  - type: tactic
    id: behavior-driven-development
    reason: >
      The technique tactic for writing individual Given/When/Then scenarios; used
      throughout steps 1–3 of this procedure.
  - type: tactic
    id: acceptance-test-first
    reason: >
      Canonical examples from step 1 hand off into executable acceptance checks
      in step 4.
  - type: directive
    id: DIRECTIVE_034
    reason: >
      BDD scenarios are the failing acceptance tests in the test-first cycle —
      red before green.
  - type: directive
    id: DIRECTIVE_037
    reason: >
      Published scenario reports are living documentation governed by the
      Living Documentation Sync directive.
```

---

## Subtask T020 — Verify paradigm and procedure pass schema validation

```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from doctrine.paradigms.repository import ParadigmRepository
r = ParadigmRepository()
all_paradigms = r.load_all()
assert 'behaviour-driven-development' in all_paradigms, 'BDD paradigm not found'
assert 'specification-by-example' in all_paradigms, 'SbE paradigm must still exist'
print('Paradigms OK:', list(all_paradigms.keys()))
"
python3 -c "
import sys; sys.path.insert(0, 'src')
from doctrine.procedures.repository import ProcedureRepository
r = ProcedureRepository()
all_procedures = r.load_all()
assert 'bdd-scenario-lifecycle' in all_procedures, 'bdd-scenario-lifecycle not found'
assert 'example-mapping-workshop' in all_procedures, 'example-mapping-workshop must still exist'
print('Procedures OK:', list(all_procedures.keys()))
"
pytest -m doctrine -q
```

**Validation checklist**:
- [ ] `behaviour-driven-development.paradigm.yaml` in `paradigms/shipped/`
- [ ] `bdd-scenario-lifecycle.procedure.yaml` in `procedures/shipped/`
- [ ] Both load from their repositories
- [ ] `specification-by-example` paradigm still loads (not modified)
- [ ] `example-mapping-workshop` procedure still loads (not modified)
- [ ] `pytest -m doctrine -q` is green

---

## Branch Strategy

No dependencies. Merges into `feature/doctrine-enrichment-bdd-profiles`.

```bash
spec-kitty agent action implement WP05 --agent claude
```

---

## Definition of Done

- Paradigm and procedure YAML files created and validated
- Both load from their respective repositories
- Existing `specification-by-example` and `example-mapping-workshop` artifacts unchanged
- Doctrine test suite green

## Reviewer Guidance

- Verify `behaviour-driven-development` paradigm summary names Three Amigos and the three phases explicitly
- Verify `bdd-scenario-lifecycle` entry condition references `example-mapping-workshop`
- Confirm procedure steps are toolchain-agnostic (framework names allowed only in references/notes)
- Verify `anti_patterns` includes the four named patterns (imperative, rubber-stamp, shared state, orphaned)

## Activity Log

- 2026-04-26T12:26:31Z – claude:sonnet:curator-carla:implementer – shell_pid=96504 – Started implementation via action command
- 2026-04-26T12:32:45Z – claude:sonnet:curator-carla:implementer – shell_pid=96504 – BDD paradigm and procedure created; compliance test fixed for cross-type references; 1133 doctrine tests green
- 2026-04-26T12:33:04Z – claude:sonnet:curator-carla:implementer – shell_pid=96504 – Review passed: behaviour-driven-development paradigm (5 paradigms total, SbE unchanged), bdd-scenario-lifecycle procedure (9 procedures total, example-mapping-workshop unchanged). Deferred references restored correctly. Compliance test extended with procedure/paradigm types. 1133 doctrine tests green.
- 2026-04-26T13:10:27Z – claude:sonnet:curator-carla:implementer – shell_pid=96504 – Done override: Feature merged to feature/doctrine-enrichment-bdd-profiles (squash merge commit 7383936b2)
