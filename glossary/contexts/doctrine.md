## Context: Doctrine

Terms describing the Doctrine domain model and doctrine artifact taxonomy.

### Doctrine Domain

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The domain model that structures reusable governance knowledge in Spec Kitty. It organizes behavior and constraints into composable artifacts (paradigms, directives, tactics, templates, styleguides, and toolguides).                 |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/`                                                                                                                                                                                                                         |
| **Related terms** | [Paradigm](#paradigm), [Directive](#directive), [Tactic](#tactic), [Template Set](#template-set), [Styleguide](#styleguide), [Toolguide](#toolguide), [Governance](./governance.md)                                                |

---

### Guideline

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A high-level doctrine rule expressing non-negotiable or strongly preferred governance behavior. Guidelines sit at the highest precedence and bound what project-level charter may customize.                                     |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | Precedence concept in governance model (no dedicated `src/doctrine/guidelines/` directory in current tree)                                                                                                                           |
| **Related terms** | [Directive](#directive), [Charter Selection](#charter-selection), [Precedence Hierarchy](./governance.md)                                                                                                                  |

---

### Paradigm

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A worldview-level framing for how work is approached in a domain. Paradigms influence selection and interpretation of directives and tactics but are not executable step recipes themselves.                                           |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/paradigms/`                                                                                                                                                                                                              |
| **Related terms** | [Directive](#directive), [Tactic](#tactic), [Charter](#charter-selection)                                                                                                                                                   |

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
| **Related terms** | [Directive](#directive), [Template Set](#template-set), [Toolguide](#toolguide)                                                                                                                                                       |

---

### Procedure

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A reusable doctrine subworkflow that a step contract may delegate to for part of a mission action. Procedures are structured playbooks, not tracked missions and not runtime sessions.                                               |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/procedures/` and related doctrine procedure models                                                                                                                                                                        |
| **Related terms** | [Tactic](#tactic), [Directive](#directive), [Mission Action](./orchestration.md#mission-action), [Step Contract](./orchestration.md#step-contract)                                                                                  |

---

### Template Set

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A structured set of doctrine templates that shape output artifacts and interaction contracts for mission actions and procedures. Template sets allow consistent behavior across mission types while remaining configurable through charter selections. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/templates/sets/`                                                                                                                                                                                                         |
| **Related terms** | [Procedure](#procedure), [Tactic](#tactic), [Charter Selection](#charter-selection)                                                                                                                                         |

---

### Styleguide

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A doctrine artifact defining cross-cutting quality and consistency conventions (for example coding, documentation, or testing style) that apply across missions and templates.                                                         |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/styleguides/`                                                                                                                                                                                                            |
| **Related terms** | [Toolguide](#toolguide), [Schema (Doctrine Artifact)](#schema-doctrine-artifact), [Charter Selection](#charter-selection)                                                                                                   |

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
| **Location**      | `src/doctrine/curation/imports/*/candidates/*.import.yaml`                                                                                                                             |
| **Related terms** | [Directive](#directive), [Tactic](#tactic), [Schema (Doctrine Artifact)](#schema-doctrine-artifact), [ADR (Architectural Decision Record)](./governance.md)                          |

---

### Charter Selection

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The project-level selection layer that activates and narrows doctrine assets (for example selected paradigms, directives, agent profiles, available tools, and template set) without changing doctrine source artifacts.               |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `.kittify/charter/`                                                                                                                                                                                                               |
| **Related terms** | [Doctrine Domain](#doctrine-domain), [Governance](./governance.md), [Configuration & Project Structure](./configuration-project-structure.md)                                                                                        |

---

### Doctrine Catalog

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | The registry of all available paradigms, directives, template sets, and tools that the HiC can select from when building their charter. The charter compiler validates selections against this catalog.                       |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Charter Selection](#charter-selection), [Charter Compiler](./governance.md#charter-compiler), [Human-in-Charge (HiC)](./identity.md#human-in-charge-hic)                                                         |

---

### Specification by Example (Paradigm)

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | A paradigm that builds shared understanding of behavior through concrete, business-readable examples which become the canonical source of truth for requirements, acceptance checks, and living documentation.                        |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/paradigms/shipped/specification-by-example.paradigm.yaml`                                                                                                                                                                |
| **Related terms** | [Paradigm](#paradigm), [Living Documentation Sync (Directive)](#living-documentation-sync-directive), [Usage Examples Sync (Tactic)](#usage-examples-sync-tactic), [Example Mapping Workshop (Procedure)](#example-mapping-workshop-procedure) |

---

### Living Documentation Sync (Directive)

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Directive DIRECTIVE_037. Requires behavior-describing artifacts to evolve together: when observable behavior changes, the canonical examples, acceptance checks, narrative specs, user docs, glossary entries, code-level docs, and architecture records are updated in the same change. |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/directives/shipped/037-living-documentation-sync.directive.yaml`                                                                                                                                                         |
| **Related terms** | [Directive](#directive), [Specification by Example (Paradigm)](#specification-by-example-paradigm), [Usage Examples Sync (Tactic)](#usage-examples-sync-tactic)                                                                        |

---

### Usage Examples Sync (Tactic)

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Tactic `usage-examples-sync`. The step-by-step pattern for keeping canonical usage examples, acceptance checks, and the artifacts that quote them aligned during a behavior change.                                                   |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/tactics/shipped/usage-examples-sync.tactic.yaml`                                                                                                                                                                         |
| **Related terms** | [Tactic](#tactic), [Living Documentation Sync (Directive)](#living-documentation-sync-directive), [Example Mapping Workshop (Procedure)](#example-mapping-workshop-procedure)                                                          |

---

### Example Mapping Workshop (Procedure)

|                   |                                                                                                                                                                                                                                         |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Definition**    | Procedure `example-mapping-workshop`. Turns a behavior request into concrete rules, canonical examples, and open questions that stakeholders and implementers share as the current source of truth for the behavior.                   |
| **Context**       | Doctrine                                                                                                                                                                                                                                |
| **Status**        | canonical                                                                                                                                                                                                                               |
| **Applicable to** | `1.x`, `2.x` |
| **Location**      | `src/doctrine/procedures/shipped/example-mapping-workshop.procedure.yaml`                                                                                                                                                              |
| **Related terms** | [Procedure](#procedure), [Specification by Example (Paradigm)](#specification-by-example-paradigm), [Living Documentation Sync (Directive)](#living-documentation-sync-directive), [Usage Examples Sync (Tactic)](#usage-examples-sync-tactic) |

---

### Charter-Mediated Selection

| | |
|---|---|
| **Definition** | Architectural pattern in which the project / org charter is the sole authority that decides which doctrine artifacts apply to a given mission run. Doctrine is the knowledge store; charter is the selector; runtime asks charter for the activated set rather than reaching into doctrine directly. Enforced via the runtime → charter → doctrine boundary. |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Global Selection](#global-selection), [Context-Scoped Selection](#context-scoped-selection), [Charter Facade](#charter-facade), [Doctrine Pack](#doctrine-pack) |

---

### Global Selection

| | |
|---|---|
| **Definition** | Selection mode in which the charter declares an artifact is *always* active for every WP prompt regardless of action or mission type. Expressed via `selected_<kind>: [<id>, ...]` on the project charter or `required_<kind>: [<id>, ...]` on the org charter. Example: *"this project always uses the python-conventions styleguide."* |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Context-Scoped Selection](#context-scoped-selection), [Charter-Mediated Selection](#charter-mediated-selection) |

---

### Context-Scoped Selection

| | |
|---|---|
| **Definition** | Selection mode in which the charter declares an artifact is active only for a specific [Activation Context](#activation-context) (mission_type × action). Surfaces in the prompt as a fetch command paired with a "when you <action>, run …" conditional. Example: *"when writing a code comment in a software-dev mission, fetch the caveman styleguide."* Implemented via the [Activation Registry](#activation-registry). |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Registry](#activation-registry), [Activation Context](#activation-context), [Global Selection](#global-selection) |

---

### Activation Registry

| | |
|---|---|
| **Definition** | Charter-level list of `(activation_context, doctrine_pack_id, artifact_id)` tuples expressing which doctrine artifacts activate in which contexts. Lives on the charter (not on the artifact) so different projects can activate the same shared artifact in different contexts without forking it. Both project charter and org charter may declare entries; org-declared entries propagate to consumers via the standard org-charter pre-fill. |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Context](#activation-context), [Context-Scoped Selection](#context-scoped-selection), [Doctrine Pack](#doctrine-pack) |

---

### Activation Context

| | |
|---|---|
| **Definition** | The key that scopes a context-scoped activation. A two-field shape — `mission_type` (one of `software-dev`, `documentation`, `research`, `plan`, or `generic`) and `action` (one of `specify`, `plan`, `tasks`, `implement`, `review`, `merge`, `accept`, plus charter verbs). The wildcard `generic` matches any value in its slot. Resolved during charter-context build by matching the current mission's `meta.json mission_type` and the in-flight CLI action against registered entries. |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Registry](#activation-registry), [Mission-Type Profile](#mission-type-profile) |

---

### Doctrine Pack ID

| | |
|---|---|
| **Definition** | The stable identifier of a doctrine pack (declared in the pack's manifest or in `.kittify/config.yaml` `doctrine.org.packs[].name`). Used as the second tuple element in the [Activation Registry](#activation-registry) to disambiguate when multiple packs ship artifacts with the same id. Special values: `project` (the project-layer pack at `.kittify/doctrine/`), `built-in` (the spec-kitty bundled pack). |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Doctrine Pack](#doctrine-pack), [Activation Registry](#activation-registry) |

---

### Trigger Registry

| | |
|---|---|
| **Definition** | Canonical frozenset of agent-action tokens (e.g. `write_comment`, `write_docstring`, `rename_identifier`, `add_dependency`) the prompt builder knows how to emit "when you <token>, …" stanzas for. Any `triggers:` value declared on a shipped doctrine artifact must be a member of this set; the architectural test `test_trigger_registry_coverage.py` enforces no dead triggers. Mission B's WP05 populates the initial set. |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Context](#activation-context), [Activation Registry](#activation-registry) |

---

### Charter Facade

| | |
|---|---|
| **Definition** | A `src/charter/<facade>.py` module that re-exports (or thinly wraps) a doctrine surface so runtime callers can consume it as `from charter.<facade> import X` instead of `from doctrine.<x> import X`. Examples: `charter.profiles`, `charter.mission_steps`, `charter.drg`, `charter.primitives`, `charter.resolution`, `charter.versioning`. The set of facades is the runtime → charter → doctrine boundary's public surface. |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Charter-Mediated Selection](#charter-mediated-selection) |

---

### Mission-Type Profile

| | |
|---|---|
| **Definition** | Shipped governance profile per mission type (`software-dev`, `documentation`, `research`, `plan`) at `src/doctrine/missions/<type>/governance-profile.yaml`. Declares default selections and default activations for that mission type. The charter resolver reads `meta.json mission_type`, picks the matching profile, and unions its declarations into the project + org selections. No `software-dev-default` fallback for non-software missions — the resolver hard-fails if a mission's `mission_type` has no matching profile and the project has not declared its own. |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Context](#activation-context), [Global Selection](#global-selection) |

---

### selected_&lt;kind&gt; / required_&lt;kind&gt;

| | |
|---|---|
| **Definition** | The field-naming convention for [Global Selection](#global-selection) entries. On the project charter (`DoctrineSelectionConfig`), each artifact kind gets a `selected_<kind>: [<id>, ...]` field — `selected_directives`, `selected_styleguides`, `selected_toolguides`, `selected_paradigms`, `selected_tactics`, `selected_procedures`, `selected_agent_profiles`, `selected_mission_step_contracts`. On the org charter (`OrgCharterPolicy`), the mirror is `required_<kind>: [<id>, ...]`. `apply_org_charter_to_interview` unions the org `required_<kind>` into the project `selected_<kind>` non-destructively. The architectural test `test_artifact_selection_completeness.py` enforces parity — every `DoctrineService` artifact kind has both a `selected_*` and a `required_*` field. |
| **Context** | Doctrine |
| **Status** | candidate |
| **Applicable to** | `2.x` |
| **Related terms** | [Global Selection](#global-selection), [Charter-Mediated Selection](#charter-mediated-selection) |

---
