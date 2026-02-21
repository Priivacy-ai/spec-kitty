# Spec Kitty Doctrine v2 - Final Consolidated Proposal

**Date:** 2026-02-17  
**Status:** Finalized proposal (conceptual)  
**Canonical concept map:** `work/ideas/domain_concepts.puml`

## 1. Goal

Establish a clean governance model for Spec Kitty v2 that:

- keeps orchestration explicit and minimal,
- routes behavioral configuration through Constitution,
- supports pull-based curation from external doctrine sources,
- and validates doctrine artifacts early via schemas/tests.

## 2. Concept Model (aligned to diagram)

## 2.1 Orchestration

- **Mission**
  - Versioned orchestration recipe.
  - Defines states, transitions, guards, and required artifacts.
- **Tool**
  - CLI/runtime execution surface.
  - Runs assigned work for agents.

## 2.2 Governance::Doctrine

- **Paradigm**
  - Shared worldview for framing work.
  - Defines how to think/see.
- **Directive**
  - Cross-cutting mandatory constraints.
  - Defines what must/must not happen.
- **Tactic**
  - Step-by-step execution procedure.
  - Defines how work is carried out.
- **TemplateSet**
  - Artifact output contract bundle.
  - Defines expected structure/shape.
- **AgentProfile**
  - Role definition + default governance.
  - Binds paradigms/directives/tactics.

## 2.3 Governance::Constitution

- **Constitution**
  - Project-level governance profile.
  - Narrows doctrine rules per repository.
  - Selects active doctrine configuration.
- **SelectedAgentProfiles**
  - Configured subset of agent profiles.
  - Active for this project/repository.
- **AvailableTools**
  - Configured set of execution tools.
  - Available for orchestration assignments.

## 2.4 Governance::Curation

- **ImportCandidate**
  - Pull-based curation record.
  - Tracks source, mapping, adaptation.
- **Schema**
  - YAML contract for doctrine artifacts.
  - Used for CI validation in tests.

## 3. Relationship Contract (exactly matching diagram)

1. `Mission --> Constitution` (`constrained by`)
2. `Mission --> Tool` (`runs on`)
3. `Constitution --> Paradigm` (`selects`)
4. `Constitution --> Directive` (`activates`)
5. `Constitution --> TemplateSet` (`chooses`)
6. `Constitution --> SelectedAgentProfiles` (`defines`)
7. `Constitution --> AvailableTools` (`defines`)
8. `SelectedAgentProfiles --> AgentProfile` (`includes`)
9. `AvailableTools --> Tool` (`includes`)
10. `Directive --> Tactic` (`invokes`)
11. `ImportCandidate --> Paradigm` (`curates into`)
12. `Schema --> ImportCandidate` (`validates`)

## 4. Structural Proposal

```text
src/doctrine/
  doctrine.yaml

  missions/
    */mission.yaml

  paradigms/
  directives/
  tactics/
  templates/
    sets/

  agent-profiles/

  schemas/

  curation/
    README.md
    imports/
      <source>/
        manifest.yaml
        candidates/*.import.yaml
    decisions/
```

## 5. Constitution-Centric Execution Rule

Execution configuration is mediated by **Constitution**:

- Mission defines orchestration contract.
- Constitution selects/activates governance assets.
- Constitution defines selected agent profiles and available tools.
- Directive activation determines tactic invocation.

This avoids direct mission-to-doctrine hard wiring and enables per-project variation.

## 6. Curation Rule

Curation is pull-based and traceable:

- external ideas enter as `ImportCandidate`,
- candidates are adapted to Spec Kitty terminology,
- accepted candidates are mapped into doctrine artifacts.

Current diagram-level curation path is intentionally minimal (`ImportCandidate -> Paradigm`).

## 7. Validation Rule

Schemas validate curation and doctrine artifacts early:

- `Schema -> ImportCandidate` is the explicit QA gate in the concept model,
- CI tests under `tests/` enforce schema compliance before runtime use.

## 8. Notes

- This proposal intentionally keeps relationship density low for readability.
- If additional links are introduced later, update `work/ideas/domain_concepts.puml` and this file together.
