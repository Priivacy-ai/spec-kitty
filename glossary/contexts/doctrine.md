## Context: Doctrine

Terms describing the Doctrine domain model and doctrine artifact taxonomy.

### Doctrine Domain

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The domain model that structures reusable governance knowledge in Spec Kitty. It organizes behavior and constraints into composable artifacts (paradigms, directives, tactics, procedures, templates, styleguides, toolguides, and mission step contracts). |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/`                                                                                                                                                                                                                         |
| **Related terms** | [Paradigm](#paradigm), [Directive](#directive), [Tactic](#tactic), [Procedure](#procedure), [Template Set](#template-set), [Styleguide](#styleguide), [Toolguide](#toolguide), [Mission Step Contract](#mission-step-contract), [Action Index](#action-index), [Opposition](#opposition), [Governance](./governance.md) |

---

### Guideline

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A high-level doctrine rule expressing non-negotiable or strongly preferred governance behavior. Guidelines sit at the highest precedence and bound what project-level constitution may customize.                                     |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | Precedence concept in governance model (no dedicated `src/doctrine/guidelines/` directory in current tree)                                                                                                                           |
| **Related terms** | [Directive](#directive), [Constitution Selection](#constitution-selection), [Precedence Hierarchy](./governance.md)                                                                                                                  |

---

### Paradigm

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A worldview-level framing for how work is approached in a domain. Paradigms influence selection and interpretation of directives and tactics but are not executable step recipes themselves.                                           |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/paradigms/`                                                                                                                                                                                                              |
| **Related terms** | [Directive](#directive), [Tactic](#tactic), [Constitution](#constitution-selection)                                                                                                                                                   |

---

### Directive

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A constraint-oriented governance rule that applies across flows or phases. Directives encode required or advisory expectations and can reference lower-level tactics for execution.                                                     |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/directives/`                                                                                                                                                                                                             |
| **Related terms** | [Paradigm](#paradigm), [Tactic](#tactic), [Schema (Doctrine Artifact)](#schema-doctrine-artifact)                                                                                                                                     |

---

### Tactic

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A reusable behavioral execution pattern that defines how work is performed. Tactics are operational and agent-consumable, and can be selected by directives and mission context.                                                      |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/tactics/`                                                                                                                                                                                                                |
| **Related terms** | [Directive](#directive), [Procedure](#procedure), [Template Set](#template-set), [Toolguide](#toolguide)                                                                                                                              |

---

### Procedure

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A stateful, multi-step doctrine workflow with defined entry and exit conditions, ordered steps, and assigned actor roles (human, agent, or system). Unlike a tactic — which is a small composable recipe — a procedure orchestrates a complete flow with explicit state transitions between steps. Procedures may reference tactics within steps but are not themselves referenced by directives. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Location**      | `src/doctrine/procedures/`                                                                                                                                                                                                             |
| **Fields**        | `entry_condition`, `exit_condition`, `steps` (ordered list with `actor`, `tactic_refs`, `on_success`, `on_failure`), `references` |
| **Related terms** | [Tactic](#tactic), [Directive](#directive), [Agent Profile](#agent-profile), [Doctrine Domain](#doctrine-domain) |

---

### Template Set

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A structured set of doctrine templates that shape output artifacts and interaction contracts for workflows. Template sets allow consistent behavior across missions while remaining configurable through constitution selections.         |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/templates/sets/`                                                                                                                                                                                                         |
| **Related terms** | [Tactic](#tactic), [Constitution Selection](#constitution-selection)                                                                                                                                                                   |

---

### Styleguide

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A doctrine artifact defining cross-cutting quality and consistency conventions (for example coding, documentation, or testing style) that apply across missions and templates.                                                         |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/styleguides/`                                                                                                                                                                                                            |
| **Related terms** | [Toolguide](#toolguide), [Schema (Doctrine Artifact)](#schema-doctrine-artifact), [Constitution Selection](#constitution-selection)                                                                                                   |

---

### Toolguide

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A doctrine artifact defining tool-specific operational guidance, syntax, and constraints (for example PowerShell usage conventions) used by agents and contributors during execution.                                                   |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/toolguides/`                                                                                                                                                                                                             |
| **Related terms** | [Styleguide](#styleguide), [Tactic](#tactic), [Execution](./execution.md)                                                                                                                                                             |

---

### Schema (Doctrine Artifact)

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A machine-validated contract that defines allowed structure and fields for doctrine artifacts. Used in CI/tests to fail fast when invalid doctrine files are introduced.                                                               |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/schemas/`                                                                                                                                                                                                                |
| **Related terms** | [Directive](#directive), [Tactic](#tactic), [Styleguide](#styleguide), [Toolguide](#toolguide)                                                                                                                                        |

---

### Import Candidate

|                   |                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A pull-based curation record for an external doctrine idea. Captures source provenance, target classification, adaptation notes, and adoption status before canonization.              |
| **Context**       | Doctrine                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/_reference/*/candidates/*.import.yaml`                                                                                                                                   |
| **Related terms** | [Directive](#directive), [Tactic](#tactic), [Schema (Doctrine Artifact)](#schema-doctrine-artifact), [ADR (Architectural Decision Record)](./governance.md)                          |

---

### Constitution Selection

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The project-level selection layer that activates and narrows doctrine assets (for example selected paradigms, directives, agent profiles, available tools, and template set) without changing doctrine source artifacts.               |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `.kittify/constitution/`                                                                                                                                                                                                               |
| **Related terms** | [Doctrine Domain](#doctrine-domain), [Governance](./governance.md), [Configuration & Project Structure](./configuration-project-structure.md)                                                                                        |

---

### Doctrine Catalog

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The registry of all available paradigms, directives, template sets, and tools that the HiC can select from when building their constitution. The constitution compiler validates selections against this catalog.                       |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Constitution Selection](#constitution-selection), [Constitution Compiler](./governance.md#constitution-compiler), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic)                                                         |

---

### Contradiction

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | An explicit tension between two doctrine artifacts. Modeled as the `opposed_by` field on paradigms, directives, and tactics. Documents that two artifacts' intents conflict under certain conditions, without superseding either. Both artifacts remain valid and applicable. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Fields**        | `type` (directive\|tactic\|paradigm), `id`, `reason` |
| **Location**      | `opposed_by` field on paradigm, directive, and tactic YAML artifacts |
| **Related terms** | [Paradigm](#paradigm), [Directive](#directive), [Tactic](#tactic), [Opposition](#opposition) |

---

### Opposition

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The relationship class representing acknowledged competing principles within doctrine. An opposition exists when two doctrine artifacts pull in different directions under the same or overlapping conditions — for example, a directive requiring exhaustive test coverage opposing one requiring fast iteration. Oppositions are first-class in the doctrine model: they are documented, not resolved away, because the tension is real and contextually valid. The specific modeling mechanism is the `opposed_by` field (see [Contradiction](#contradiction)). |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Related terms** | [Contradiction](#contradiction), [Opposing Element](#opposing-element), [Directive](#directive), [Tactic](#tactic), [Paradigm](#paradigm) |

---

### Opposing Element

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A doctrine artifact that is named in another artifact's `opposed_by` field. Being an opposing element does not make an artifact invalid or lower-priority; it signals that a known tension exists and that the curator has explicitly acknowledged both sides. Agents and humans must resolve which side applies given their current context rather than defaulting to one artifact silently overriding the other. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Related terms** | [Opposition](#opposition), [Contradiction](#contradiction), [Directive](#directive), [Tactic](#tactic), [Paradigm](#paradigm) |

---

### Agent Profile

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A doctrine artifact defining an AI agent's capabilities, constraints, and behavioral contracts. Agent profiles allow the system to reason about which agents can handle which types of work and under what governance constraints. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Location**      | `src/doctrine/agent_profiles/` |
| **Related terms** | [Agent](./identity.md#agent), [Doctrine Domain](#doctrine-domain), [Schema (Doctrine Artifact)](#schema-doctrine-artifact) |

---

### Two-Source Loading

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The doctrine repository pattern that loads artifacts from two sources: shipped defaults (bundled with the doctrine package) and project-level overrides (in the user's repository). Project artifacts can override shipped artifacts via field-level merge or add entirely new ones. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Location**      | `src/doctrine/*/repository.py` |
| **Related terms** | [Doctrine Catalog](#doctrine-catalog), [Doctrine Domain](#doctrine-domain), [Constitution Selection](#constitution-selection) |

---

### Mission Template

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A doctrine artifact that defines the high-level SDD process stages for a specific type of work (software development, documentation, research). Mission templates are consumed by Kitty-core to construct the execution graph for a concrete mission. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Location**      | `src/doctrine/missions/` (software-dev, documentation, research) |
| **Related terms** | [Mission](./orchestration.md#mission), [Doctrine Domain](#doctrine-domain), [Mission-Runtime YAML](./orchestration.md#mission-runtime-yaml), [Mission Step Contract](#mission-step-contract) |

---

### Mission Step Contract

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A doctrine artifact that defines the structural steps of a mission action without embedding governance prose. Each step may delegate its concretization to other doctrine artifacts (paradigms, tactics, directives) via a `delegates_to` field and/or carry freeform `guidance` for step-specific instructions. Replaces inline governance in command templates with a structured, schema-validated contract. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Location**      | `src/doctrine/mission_step_contracts/` |
| **File pattern**  | `*.step-contract.yaml` |
| **Related terms** | [Mission Template](#mission-template), [Delegates To](#delegates-to), [Action Index](#action-index), [Command Template](./orchestration.md#command-template), [Directive](#directive), [Tactic](#tactic), [Paradigm](#paradigm) |

---

### Delegates To

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A delegation link within a mission step contract that connects a structural step to doctrine artifacts for runtime concretization. Specifies the artifact `kind` (paradigm, tactic, directive, etc.) and a list of `candidates` — the constitution's selections determine which candidate actually applies at execution time. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Related terms** | [Mission Step Contract](#mission-step-contract), [Constitution Selection](#constitution-selection), [Paradigm](#paradigm), [Tactic](#tactic), [Directive](#directive) |

---

### Action Index

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A per-action governance scoping artifact that lists which directives, tactics, styleguides, toolguides, and procedures are relevant to a specific mission action (for example implement, review, specify, plan). Used in a two-stage intersection with the project's constitution selections to determine which governance content is injected at execution time. Prevents cross-action governance bleed. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `2.x` |
| **Location**      | `src/doctrine/missions/<mission>/actions/<action>/index.yaml` |
| **Related terms** | [Mission Template](#mission-template), [Directive](#directive), [Tactic](#tactic), [Context Bootstrap](./governance.md#context-bootstrap), [Two-Stage Intersection](./governance.md#two-stage-intersection) |
