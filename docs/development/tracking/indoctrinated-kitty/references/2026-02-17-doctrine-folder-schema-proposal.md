# Spec Kitty Doctrine v2: Folder + Schema Proposal (Pull-Based Curation)

**Date:** 2026-02-17  
**Status:** Proposal  
**Intent:** Pull ideas from AAD Doctrine and reframe into a clean Spec Kitty conceptual model.

## 1. Target Concepts

- `Mission`: orchestration recipe (state machine + artifact gates + governance selectors)
- `Paradigm`: conceptual worldview / framing assumptions
- `Directive`: mandatory constraints and policy rules
- `Tactic`: executable step-by-step procedure
- `Template`: output contract / artifact shape

## 2. Proposed Folder Structure

```text
src/doctrine/
  doctrine.yaml                     # root manifest + version + registries
  README.md

  schemas/
    doctrine.schema.yaml
    mission.schema.yaml
    paradigm.schema.yaml
    directive.schema.yaml
    tactic.schema.yaml
    template-set.schema.yaml
    import-candidate.schema.yaml

  agent-profiles/
    profile-index.yaml
    implementer.profile.yaml
    reviewer.profile.yaml
    architect.profile.yaml

  missions/
    software-dev/
      mission.yaml                  # orchestration only + selectors
      command-templates/            # thin wrappers; minimal behavioral text
    research/
      mission.yaml
      command-templates/
    documentation/
      mission.yaml
      command-templates/

  paradigms/
    paradigm-index.yaml
    spec-driven-development.paradigm.md
    locality-of-change.paradigm.md
    decision-first-development.paradigm.md

  directives/
    directive-index.yaml
    D001-human-in-charge.directive.yaml
    D017-test-first.directive.yaml
    D034-spec-driven-development.directive.yaml

  tactics/
    tactic-index.yaml
    T001-clarification-before-execution.tactic.md
    T010-atdd-adversarial-acceptance.tactic.md
    T020-decision-capture.tactic.md

  templates/
    template-index.yaml
    sets/
      software-dev.template-set.yaml
      research.template-set.yaml
      documentation.template-set.yaml
    artifacts/
      spec-template.md
      plan-template.md
      tasks-template.md
      task-prompt-template.md

  curation/
    README.md                       # pull-based curation intent + workflow
    imports/
      aad/
        manifest.yaml               # source path + version pin/commit
        candidates/
          C001-locality-of-change.import.yaml
          C002-spec-driven-development.import.yaml
    decisions/
      DCR-001-mission-terminology.md
      DCR-002-approach-to-paradigm.md
```

## 3. Schema Proposals

## 3.1 `doctrine.yaml` (root manifest)

```yaml
schema_version: "1.0"
doctrine:
  name: spec-kitty-doctrine
  version: "2.0.0-alpha"
  terminology:
    mission_term: mission
    paradigm_term: paradigm
    directive_term: directive
    tactic_term: tactic
    template_term: template
registries:
  missions: "./missions"
  agent_profiles: "./agent-profiles/profile-index.yaml"
  schemas: "./schemas"
  paradigms: "./paradigms/paradigm-index.yaml"
  directives: "./directives/directive-index.yaml"
  tactics: "./tactics/tactic-index.yaml"
  templates: "./templates/template-index.yaml"
  curation: "./curation/imports"
```

## 3.2 `mission.yaml` (orchestration-first)

```yaml
schema_version: "2.0"
mission:
  id: software-dev
  name: Software Dev Mission
  version: "2.0.0"
  description: "Software delivery workflow with gated transitions"

orchestration:
  initial_state: discovery
  states:
    - discovery
    - specify
    - plan
    - implement
    - review
    - done
  transitions:
    - trigger: advance
      source: discovery
      dest: specify
    - trigger: advance
      source: specify
      dest: plan
      guards: [G001-spec-exists]
  guards:
    - id: G001-spec-exists
      check: artifact_exists("spec.md")

artifacts:
  required:
    - spec.md
    - plan.md
    - tasks.md
  optional:
    - research.md
    - contracts/

governance_selectors:
  paradigms:
    - spec-driven-development
    - locality-of-change
  directives:
    - D001-human-in-charge
    - D017-test-first
    - D034-spec-driven-development
  tactic_sets:
    - software-dev-core
  template_set: software-dev
```

## 3.3 `*.paradigm.md` frontmatter

```yaml
id: spec-driven-development
name: Spec-Driven Development
version: "1.0.0"
status: adopted
summary: "Change-driven framing: specs describe deltas from current code"
assumptions:
  - code_is_truth
  - specs_are_change_requests
applies_to:
  - software-dev
related:
  directives: [D034-spec-driven-development]
  tactics: [T020-decision-capture]
source:
  origin: aad
  ref: doctrine/approaches/spec-driven-development.md
```

## 3.4 `*.directive.yaml`

```yaml
schema_version: "1.0"
id: D017-test-first
name: Test-First Delivery
version: "1.0.0"
severity: required
scope:
  missions: [software-dev]
  phases: [implement, review]
rules:
  - id: R1
    statement: "Write failing tests before production code changes."
  - id: R2
    statement: "Do not close implementation phase without green acceptance tests."
enforcement:
  blockers:
    - missing_failing_test_evidence
references:
  tactics: [T010-atdd-adversarial-acceptance]
```

## 3.5 `*.tactic.md` frontmatter

```yaml
id: T010-atdd-adversarial-acceptance
name: ATDD Adversarial Acceptance
version: "1.0.0"
status: adopted
intent: "Define acceptance boundaries through misuse and edge cases"
inputs:
  - feature_spec
  - constraints
outputs:
  - acceptance_test_cases
steps:
  - identify_happy_path
  - enumerate_failure_modes
  - encode_boundary_tests
exit_criteria:
  - acceptance_boundaries_documented
  - tests_fail_before_implementation
references:
  directives: [D017-test-first]
```

## 3.6 `*.template-set.yaml`

```yaml
schema_version: "1.0"
id: software-dev
name: Software Dev Template Set
version: "1.0.0"
templates:
  spec: "../artifacts/spec-template.md"
  plan: "../artifacts/plan-template.md"
  tasks: "../artifacts/tasks-template.md"
  task_prompt: "../artifacts/task-prompt-template.md"
```

## 3.7 `*.import.yaml` (pull-based curation record)

```yaml
schema_version: "1.0"
id: C002-spec-driven-development
source:
  stack: aad
  path: "doctrine/approaches/spec-driven-development.md"
  version_pin: "2026-02-07"
selection:
  why_selected: "Aligns with Spec Kitty delta-spec philosophy"
classification:
  source_type: approach
  target_type: paradigm
adaptation:
  changes:
    - "Removed AAD-specific role names"
    - "Aligned terms with Spec Kitty mission/phase model"
status: adopted
linked_artifacts:
  paradigm: spec-driven-development
  directives: [D034-spec-driven-development]
notes: "Curated, not copied verbatim"
```

## 3.8 `agent-profiles/*.profile.yaml`

```yaml
schema_version: "1.0"
id: implementer
name: Implementation Agent
version: "1.0.0"
role: implementer
default_governance:
  paradigms: [spec-driven-development, locality-of-change]
  directives: [D001-human-in-charge, D017-test-first]
  tactic_sets: [software-dev-core]
capabilities:
  - write_code
  - write_tests
  - refactor
handoff:
  next_on_success: reviewer
```

## 3.9 `curation/README.md` (intent + workflow)

```markdown
# Curation

This directory manages pull-based doctrine curation for Spec Kitty.

## Intent
- Pull useful concepts from external sources (AAD and others)
- Reclassify them into Spec Kitty doctrine concepts
- Record provenance and adaptation decisions
- Keep imports traceable, selective, and non-verbatim by default

## Workflow
1. Add source manifest/version pin under `imports/<source>/manifest.yaml`
2. Create import candidate record in `imports/<source>/candidates/*.import.yaml`
3. Classify candidate target type (`paradigm|directive|tactic|template`)
4. Adapt language to Spec Kitty canonical glossary
5. Link accepted artifacts and decision records

## Example Journey
Lead developer reads about the **ZOMBIES TDD** approach and wants it as
standard behavior for implementation agents.

- Candidate created: `C0XX-zombies-tdd.import.yaml`
- Classification: source approach -> target tactic (plus optional paradigm notes)
- Adoption:
  - add/update tactic in `tactics/`
  - reference from Directive D017 or a related testing directive
  - add to implementer profile defaults in `agent-profiles/implementer.profile.yaml`
  - document rationale in `curation/decisions/`
```

## 3.10 `schemas/*.schema.yaml` + CI validation

The `schemas/` directory stores YAML/JSON Schema contracts for doctrine artifacts.
These schemas are consumed by validation tests under `tests/` as an early QA gate.

Suggested tests:

- `tests/doctrine/test_doctrine_manifest_schema.py`
- `tests/doctrine/test_mission_schema.py`
- `tests/doctrine/test_governance_artifact_schemas.py`
- `tests/doctrine/test_import_candidate_schema.py`

Validation behavior:

1. Load all doctrine artifacts by type.
2. Validate each file against corresponding schema in `src/doctrine/schemas/`.
3. Fail CI on schema violations before runtime mission execution.
4. Add fixture-based regression tests for known invalid examples.

## 4. Practical Migration Plan

1. Keep existing mission files; add `governance_selectors` block first.
2. Move behavioral prose out of mission command templates into tactic/template assets.
3. Introduce `schemas/` and wire schema validation tests in `tests/doctrine/`.
4. Create 3-5 seed paradigms and 5-10 directives/tactics from AAD candidates.
5. Add curation records for each pulled concept (traceability) and maintain `curation/README.md`.
6. Add agent-profile defaults that bind mission selectors to practical execution behavior.
7. Update glossary terms to canonicalize `Paradigm` and orchestration-first `Mission`.

## 5. Design Constraints

- Do not import AAD folders 1:1.
- Reclassify by function, not by source directory name.
- Missions remain orchestration contracts, not behavior dumps.
- Every imported idea must include provenance + adaptation note.
