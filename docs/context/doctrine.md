---
title: 'Context: Doctrine'
description: 'Glossary context for the Doctrine domain model and artifact taxonomy: how reusable governance knowledge is structured into composable behavior and constraints.'
doc_status: active
updated: '2026-07-21'
related:
- docs/context/configuration-project-structure.md
- docs/context/execution.md
- docs/context/governance.md
- docs/context/identity.md
- docs/context/orchestration.md
---
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
| **Related terms** | [Tactic](#tactic), [Directive](#directive), [Mission Action](./orchestration.md#mission-action), [step contract](./orchestration.md#step-contract)                                                                                  |

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
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Global Selection](#global-selection), [Context-Scoped Selection](#context-scoped-selection), [Charter Facade](#charter-facade), [Doctrine Pack](#doctrine-pack) |

---

### Global Selection

| | |
|---|---|
| **Definition** | Selection mode in which the charter declares an artifact is *always* active for every WP prompt regardless of action or mission type. Expressed via `selected_<kind>: [<id>, ...]` on the project charter or `required_<kind>: [<id>, ...]` on the org charter. Example: *"this project always uses the python-conventions styleguide."* |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Context-Scoped Selection](#context-scoped-selection), [Charter-Mediated Selection](#charter-mediated-selection) |

---

### Context-Scoped Selection

| | |
|---|---|
| **Definition** | Selection mode in which the charter declares an artifact is active only for a specific [Activation Context](#activation-context) (mission_type × action). Surfaces in the prompt as a fetch command paired with a "when you <action>, run …" conditional. Example: *"when writing a code comment in a software-dev mission, fetch the caveman styleguide."* Implemented via the [Activation Registry](#activation-registry). |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Registry](#activation-registry), [Activation Context](#activation-context), [Global Selection](#global-selection) |

---

### Activation Registry

| | |
|---|---|
| **Definition** | Charter-level list of `(activation_context, doctrine_pack_id, artifact_id)` tuples expressing which doctrine artifacts activate in which contexts. Lives on the charter (not on the artifact) so different projects can activate the same shared artifact in different contexts without forking it. Both project charter and org charter may declare entries; org-declared entries propagate to consumers via the standard org-charter pre-fill. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Context](#activation-context), [Context-Scoped Selection](#context-scoped-selection), [Doctrine Pack](#doctrine-pack) |

---

### Activation Context

| | |
|---|---|
| **Definition** | The key that scopes a context-scoped activation. A two-field shape — `mission_type` (one of `software-dev`, `documentation`, `research`, `plan`, or `generic`) and `action` (one of `specify`, `plan`, `tasks`, `implement`, `review`, `merge`, `accept`, plus charter verbs). The wildcard `generic` matches any value in its slot. Resolved during charter-context build by matching the current mission's `meta.json mission_type` and the in-flight CLI action against registered entries. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Registry](#activation-registry), [Mission-Type Profile](#mission-type-profile) |

---

### Doctrine Pack

| | |
|---|---|
| **Definition** | A versioned, distributable bundle of doctrine artefacts (glossary terms, tactics, directives, agent profiles, styleguides, and toolguides) that can be installed into a project to govern its development practices. Packs are identified by a stable [Doctrine Pack ID](#doctrine-pack-id) and registered in `.kittify/config.yaml` under `doctrine.org.packs`. The spec-kitty built-in pack is the base layer; project-layer overrides live at `.kittify/doctrine/`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Doctrine Pack ID](#doctrine-pack-id), [Activation Registry](#activation-registry), [Organisation Tier](#organisation-tier) |

---

### Doctrine Pack ID

| | |
|---|---|
| **Definition** | The stable identifier of a doctrine pack (declared in the pack's manifest or in `.kittify/config.yaml` `doctrine.org.packs[].name`). Used as the second tuple element in the [Activation Registry](#activation-registry) to disambiguate when multiple packs ship artifacts with the same id. Special values: `project` (the project-layer pack at `.kittify/doctrine/`), `built-in` (the spec-kitty bundled pack). |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Doctrine Pack](#doctrine-pack), [Activation Registry](#activation-registry) |

---

### Trigger Registry

| | |
|---|---|
| **Definition** | Canonical frozenset of agent-action tokens (e.g. `write_comment`, `write_docstring`, `rename_identifier`, `add_dependency`) the prompt builder knows how to emit "when you <token>, …" stanzas for. Any `triggers:` value declared on a shipped doctrine artifact must be a member of this set; the architectural test `test_trigger_registry_coverage.py` enforces no dead triggers. Mission B's WP05 populates the initial set. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Context](#activation-context), [Activation Registry](#activation-registry) |

---

### Charter Facade

| | |
|---|---|
| **Definition** | A `src/charter/<facade>.py` module that re-exports (or thinly wraps) a doctrine surface so runtime callers can consume it as `from charter.<facade> import X` instead of `from doctrine.<x> import X`. Examples: `charter.profiles`, `charter.mission_steps`, `charter.drg`, `charter.primitives`, `charter.resolution`, `charter.versioning`. The set of facades is the runtime → charter → doctrine boundary's public surface. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Charter-Mediated Selection](#charter-mediated-selection) |

---

### Mission-Type Profile

| | |
|---|---|
| **Definition** | Shipped governance profile per mission type (`software-dev`, `documentation`, `research`, `plan`) at `src/doctrine/missions/<type>/governance-profile.yaml`. Declares default selections and default activations for that mission type. The charter resolver reads `meta.json mission_type`, picks the matching profile, and unions its declarations into the project + org selections. No `software-dev-default` fallback for non-software missions — the resolver hard-fails if a mission's `mission_type` has no matching profile and the project has not declared its own. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Context](#activation-context), [Global Selection](#global-selection) |

---

### selected_&lt;kind&gt; / required_&lt;kind&gt;

| | |
|---|---|
| **Definition** | The field-naming convention for [Global Selection](#global-selection) entries. On the project charter (`DoctrineSelectionConfig`), each artifact kind gets a `selected_<kind>: [<id>, ...]` field — `selected_directives`, `selected_styleguides`, `selected_toolguides`, `selected_paradigms`, `selected_tactics`, `selected_procedures`, `selected_agent_profiles`, `selected_mission_step_contracts`. On the org charter (`OrgCharterPolicy`), the mirror is `required_<kind>: [<id>, ...]`. `apply_org_charter_to_interview` unions the org `required_<kind>` into the project `selected_<kind>` non-destructively. The architectural test `test_artifact_selection_completeness.py` enforces parity — every `DoctrineService` artifact kind has both a `selected_*` and a `required_*` field. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Global Selection](#global-selection), [Charter-Mediated Selection](#charter-mediated-selection) |

---

<!-- ================================================================== -->
<!-- Slice F org-tier terms (WP08 / C-010)                              -->
<!-- Status: canonical — promoted by WP12 T065                          -->
<!-- ================================================================== -->

### Three-layer DRG

| | |
|---|---|
| **Definition** | The three-tier Doctrine Relationship Graph composed of: (1) the shipped built-in layer (`src/doctrine/drg/shipped.json`), (2) zero or more org-tier extension fragments (`drg/fragment.yaml` inside each configured org pack), and (3) optional project-tier annotations declared in the project charter. Each tier is additive; org and project tiers may only extend or annotate shipped nodes — they cannot remove or reclassify them. Resolved at runtime by `charter.drg.merge_three_layers`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Doctrine Pack](#doctrine-pack), [Organisation Tier](#organisation-tier), [Charter-Mediated Selection](#charter-mediated-selection) |

---

### Tension — `in_tension_with` (DRG Relation)

| | |
|---|---|
| **Definition** | A symmetric, non-transitive [Three-layer DRG](#three-layer-drg) relation marking two co-valid, co-activatable artefacts that compete on the same decision. Stored as a single canonical edge (lexicographically-smaller URN as source) and queryable from either endpoint; it does not imply that either side is deprecated, superseded, or wrong — both remain valid rules until an operator deactivates one side or activates a reconciler ([Reconciliation](#reconciliation--reconciles_tension-drg-relation)). Canonical source: `RELATION_DESCRIPTIONS[Relation.IN_TENSION_WITH]` in `src/doctrine/drg/models.py`; human-readable mirror and worked examples in `docs/architecture/doctrine-relationships.md` ("Tension vocabulary"). |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [Reconciliation](#reconciliation--reconciles_tension-drg-relation), [Rejection](#rejection--rejects-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Reconciliation — `reconciles_tension` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation linking an active reconciliation artefact to one side of a declared [Tension](#tension--in_tension_with-drg-relation) pair. A tension pair is treated as resolved only when an active artefact carries this edge to **both** sides of the pair — an edge to just one side leaves the pair half-reconciled and still flagged. It is authored explicitly and is never inferred from an `in_tension_with` edge. Canonical source: `RELATION_DESCRIPTIONS[Relation.RECONCILES_TENSION]` in `src/doctrine/drg/models.py`; human-readable mirror in `docs/architecture/doctrine-relationships.md` ("Tension vocabulary"). |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [Tension](#tension--in_tension_with-drg-relation), [Rejection](#rejection--rejects-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Rejection — `rejects` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation from a good artefact to a marked anti-pattern or smell node (`NodeKind.ANTI_PATTERN`), expressing rejection of a named bad practice. It is distinct from [Tension](#tension--in_tension_with-drg-relation) — the target is not a competing equal, it is a bad practice — and from `replaces`/supersession, since the target was never a valid rule to begin with. Canonical source: `RELATION_DESCRIPTIONS[Relation.REJECTS]` in `src/doctrine/drg/models.py`; human-readable mirror in `docs/architecture/doctrine-relationships.md` ("Tension vocabulary"). |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `3.x` |
| **Related terms** | [Tension](#tension--in_tension_with-drg-relation), [Reconciliation](#reconciliation--reconciles_tension-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

<!-- ================================================================== -->
<!-- Remaining DRG relations (WP04, mission                             -->
<!-- drg-relation-parity-activation-gate-01KY48PD, FR-008)               -->
<!-- These entries paraphrase the canonical registry for reader          -->
<!-- completeness. This glossary is deliberately NOT the parity-enforced -->
<!-- doc surface -- that role belongs solely to                         -->
<!-- docs/architecture/doctrine-relationships.md, whose per-relation     -->
<!-- section bodies are checked verbatim against                        -->
<!-- RELATION_DESCRIPTIONS by tests/doctrine/test_relation_doc_parity.py.-->
<!-- Do not attempt to make the prose below content-equal to the         -->
<!-- registry; a wording drift here is expected and harmless.            -->
<!-- ================================================================== -->

### Hard Dependency — `requires` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation marking a mandatory prerequisite: the source artifact cannot be meaningfully resolved without the target also being present and considered. Governance-context resolution for a mission-step action walks `requires` edges transitively (no hop limit) once it has collected the action's [scoped](#governance-scope--scope-drg-relation) artifacts, and the charter activation cascade follows the same edge to pull in artifacts that must also be active. It is the most heavily used relation in the built-in graph. Canonical source: `RELATION_DESCRIPTIONS[Relation.REQUIRES]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Soft Recommendation](#soft-recommendation--suggests-drg-relation), [Governance Scope](#governance-scope--scope-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Soft Recommendation — `suggests` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation pointing at content that is relevant but optional. Unlike [Hard Dependency](#hard-dependency--requires-drg-relation), which is walked transitively with no depth limit, governance-context resolution only follows `suggests` edges a bounded number of hops, and the charter activation cascade treats a `suggests` target as something an operator may accept or decline. It is emitted more often than any other relation in the built-in graph, but that volume is incidental — the depth-bounded walk, not the count, is what separates it from `requires`. Canonical source: `RELATION_DESCRIPTIONS[Relation.SUGGESTS]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Hard Dependency](#hard-dependency--requires-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Workflow Application — `applies` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation from an agent profile to the concrete procedure or tactic it executes as its operating workflow. It is deliberately rare in the built-in graph — most profiles describe how they work through the `specialization` field's prose rather than a graph edge — so seeing only a handful of `applies` edges is expected, not a gap. Distinct from [Governance Scope](#governance-scope--scope-drg-relation): `applies` names what a profile *does*, `scope` names what an action is *governed by*; the two edge-roles are never interchangeable even though both link an actor-adjacent node to guidance content. Canonical source: `RELATION_DESCRIPTIONS[Relation.APPLIES]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Governance Scope](#governance-scope--scope-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Governance Scope — `scope` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation from a mission-step action node to the directives and tactics that govern performing that action. It is the entry point of governance-context resolution: the resolver first walks `scope` edges from the action node, then expands through [Hard Dependency](#hard-dependency--requires-drg-relation) and [Soft Recommendation](#soft-recommendation--suggests-drg-relation) edges from what it found. It is one of the most heavily emitted relations tied to action nodes in the built-in graph. Distinct from [Workflow Application](#workflow-application--applies-drg-relation) — see that entry for the contrast. Canonical source: `RELATION_DESCRIPTIONS[Relation.SCOPE]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Workflow Application](#workflow-application--applies-drg-relation), [Hard Dependency](#hard-dependency--requires-drg-relation), [Soft Recommendation](#soft-recommendation--suggests-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Glossary Vocabulary — `vocabulary` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation from a resolved doctrine artifact to a glossary-scope node, meant to surface which glossary sections are relevant once governance context has been resolved for an action. The traversal step exists and is exercised by tests, but no built-in or org-pack artifact currently emits a `vocabulary` edge — treat it as intended-but-dormant rather than actively exercised. Canonical source: `RELATION_DESCRIPTIONS[Relation.VOCABULARY]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Governance Scope](#governance-scope--scope-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Template Instantiation — `instantiates` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation from a mission-step action node to the template it produces as its concrete output. It appears only between `action` and `template` nodes in the built-in graph, in modest numbers, and is distinct from [Governance Scope](#governance-scope--scope-drg-relation): `scope` links an action to content it must follow, `instantiates` links it to content it produces. Canonical source: `RELATION_DESCRIPTIONS[Relation.INSTANTIATES]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Governance Scope](#governance-scope--scope-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Supersession — `replaces` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation asserting that the source artifact fully supersedes the target, which stops applying once the source is active. It is retained for backward compatibility with older, hand-authored fragments; no built-in artifact emits it today, since current practice either deactivates the superseded artifact directly or, for pack overlays, expresses supersession through [Overlay Override](#overlay-override--overrides-drg-relation). Distinct from [Tension](#tension--in_tension_with-drg-relation), which never implies either side is deprecated or wrong. Canonical source: `RELATION_DESCRIPTIONS[Relation.REPLACES]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Overlay Override](#overlay-override--overrides-drg-relation), [Tension](#tension--in_tension_with-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Delegation — `delegates_to` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation expressing a *runtime* handoff: one agent profile hands work to another at execution time. It is kept deliberately separate from [Lineage](#lineage--specializes_from-drg-relation) so a static "derives from" relationship never gets conflated with a live work handoff. No built-in artifact emits a `delegates_to` edge today — delegation is currently expressed in profile `collaboration.handoff_to` prose rather than as a graph edge, so treat this relation as intended-but-dormant. Canonical source: `RELATION_DESCRIPTIONS[Relation.DELEGATES_TO]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Lineage](#lineage--specializes_from-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Lineage — `specializes_from` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional, static [Three-layer DRG](#three-layer-drg) relation: a profile or artifact derives from a parent, narrowing or extending it. In the built-in graph this appears only between `agent_profile` nodes (e.g. a language-specialist implementer profile specializing from the generic implementer profile), and is resolved through `AgentProfileRepository.resolve_profile` graph traversal at composition time. Deliberately distinct from [Delegation](#delegation--delegates_to-drg-relation) so inheritance never leaks into runtime handoff traversal. Canonical source: `RELATION_DESCRIPTIONS[Relation.SPECIALIZES_FROM]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Delegation](#delegation--delegates_to-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Overlay Enhancement — `enhances` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional org-pack overlay relation: a pack artifact field-merges additional content into a built-in artifact, preserving the built-in's existing action sequence and step I/O rather than discarding them. No built-in artifact emits this edge — by design, `enhances` only ever originates from an org- or project-tier pack fragment layered on top of a shipped artifact, never between two built-in nodes. Distinct from [Overlay Override](#overlay-override--overrides-drg-relation), which replaces rather than merges. Canonical source: `RELATION_DESCRIPTIONS[Relation.ENHANCES]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Overlay Override](#overlay-override--overrides-drg-relation), [Three-layer DRG](#three-layer-drg), [Organisation Tier](#organisation-tier) |

---

### Overlay Override — `overrides` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional org-pack overlay relation: a pack artifact declares a full replacement of a built-in artifact's content rather than a field-merge. Like [Overlay Enhancement](#overlay-enhancement--enhances-drg-relation), no built-in artifact emits this edge by design — it only ever originates from an org- or project-tier overlay. Silently dropping steps or stripping step input/output when applying an `overrides` edge is rejected rather than tolerated. Canonical source: `RELATION_DESCRIPTIONS[Relation.OVERRIDES]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Overlay Enhancement](#overlay-enhancement--enhances-drg-relation), [Three-layer DRG](#three-layer-drg), [Organisation Tier](#organisation-tier) |

---

### Refinement — `refines` (DRG Relation)

| | |
|---|---|
| **Definition** | A directional [Three-layer DRG](#three-layer-drg) relation: an artifact narrows or sharpens the applicability or meaning of a parent or built-in target without replacing it. It is a first-class, traversable relation in its own right — never a stand-in for [Workflow Application](#workflow-application--applies-drg-relation) or [Lineage](#lineage--specializes_from-drg-relation). No built-in artifact currently emits a `refines` edge, so treat it as intended-but-dormant; an earlier version of the org-to-DRG bridge silently downgraded authored `refines` edges to `applies`, but that lossy downgrade has since been removed. Canonical source: `RELATION_DESCRIPTIONS[Relation.REFINES]` in `src/doctrine/drg/models.py`. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x`, `3.x` |
| **Related terms** | [Workflow Application](#workflow-application--applies-drg-relation), [Lineage](#lineage--specializes_from-drg-relation), [Three-layer DRG](#three-layer-drg) |

---

### Organisation Tier

| | |
|---|---|
| **Definition** | The middle layer of the three-layer DRG model, contributed by one or more configured org doctrine packs. Each pack ships an `org-charter.yaml` (governance policies and required artifact selections) and an optional `drg/fragment.yaml` (DRG extension nodes and edges). Organisation-tier content propagates to all consumer projects via `apply_org_charter_to_interview` and the standard charter pre-fill path. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Three-layer DRG](#three-layer-drg), [Doctrine Pack](#doctrine-pack), [Charter Selection](#charter-selection) |

---

### CharterScope

| | |
|---|---|
| **Definition** | A resolution context (`charter.scope::CharterScope`) that maps a filesystem path to the appropriate charter when multiple charters coexist in a monorepo. Single-project repositories use `CharterScope.default(repo_root)` which returns the root-scoped charter. Monorepos with multiple sub-project charters configure `charter_scopes:` in `.kittify/config.yaml`; `CharterScope.resolve(repo_root, feature_dir)` then finds the nearest-enclosing charter for any given feature directory. The resolved `scope.root` is forwarded to `build_charter_context` (or via `build_with_scope`) so the correct per-package charter governs prompt generation. See ADR-8 (`docs/adr/3.x/2026-05-18-1-monorepo-charter-scope.md`). |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Three-layer DRG](#three-layer-drg), [Charter-Mediated Selection](#charter-mediated-selection), [Workflow Sequence](#workflow-sequence) |

---

### Workflow Sequence

| | |
|---|---|
| **Definition** | A named, ordered list of mission-action steps with declared entry conditions, exit conditions, and optional per-step runtime hooks. Stored as a `WorkflowSequence` Pydantic model in `spec-kitty next`'s internal runtime schema registry. Org packs may contribute custom workflow sequences that extend or override the shipped set when activated via the Activation Registry. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Activation Registry](#activation-registry), [Mission-Type Profile](#mission-type-profile), [Procedure](#procedure) |

---

### Workflow ID

| | |
|---|---|
| **Definition** | The stable, kebab-case identifier of a Workflow Sequence (e.g. `software-dev-default`). Used as the lookup key in the workflow schema registry and in the `meta.json` `workflow_id` field to record which sequence drove a given mission run. Org packs must not reuse shipped workflow IDs without explicit override semantics. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Workflow Sequence](#workflow-sequence), [Mission-Type Profile](#mission-type-profile) |

---

### Ratchet Baseline

| | |
|---|---|
| **Definition** | A snapshot of a quality metric (failure count, symbol count, dead-module count) recorded in `tests/architectural/ratchet-baseline-*.md` and enforced by the corresponding architectural gate. A ratchet baseline only moves in the decreasing direction during normal development; any increase fails CI. Org packs may declare additional ratchet metrics via governance policies, but cannot lower an existing shipped baseline. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Three-layer DRG](#three-layer-drg), [Organisation Tier](#organisation-tier) |

---

### Cat-7 Grandfathered Orphan

| | |
|---|---|
| **Definition** | A dead-module or dead-symbol violation that has been explicitly classified as category 7 ("deferred — grandfathered") in the remediation tracking spreadsheet. Cat-7 items are excluded from the active failure count tracked by the ratchet baseline but must not be added to the allowlist via side-effect imports (the C2 anti-pattern). Each cat-7 record must carry a deferral reason and a target WP for cleanup. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Ratchet Baseline](#ratchet-baseline), [Symbol-level Dead Code](#symbol-level-dead-code), [Catalog Miss](#catalog-miss) |

---

### Symbol-level Dead Code

| | |
|---|---|
| **Definition** | A public symbol (function, class, constant) exported by a module but not referenced by any other module or test in the codebase, as detected by `tests/architectural/test_no_dead_symbols.py`. Distinguished from module-level dead code (an entire module with no importers). Symbol-level findings are reported per-file and contribute to the dead-symbol ratchet baseline. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Ratchet Baseline](#ratchet-baseline), [Cat-7 Grandfathered Orphan](#cat-7-grandfathered-orphan), [`__all__` Declaration Convention](#__all__-declaration-convention) |

---

### Catalog Miss

| | |
|---|---|
| **Definition** | A doctrine artifact ID referenced by a charter selection (e.g. `selected_directives: [foo]`) that does not resolve to any known artifact in the shipped pack, any configured org pack, or the project-layer doctrine tree. Catalog misses are reported as errors by `spec-kitty doctor doctrine` and by the `test_no_dead_symbols.py` gate when the referencing code reaches into the doctrine catalog. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Doctrine Catalog](#doctrine-catalog), [Charter Selection](#charter-selection), [Organisation Tier](#organisation-tier) |

---

### `__all__` Declaration Convention

| | |
|---|---|
| **Definition** | The project convention that every Python module with a public API must declare an `__all__` list enumerating its exported symbols. The `test_no_dead_symbols.py` architectural gate uses `__all__` as the canonical public surface; symbols absent from `__all__` are not counted as dead even if unreferenced, and symbols present in `__all__` but never imported externally are flagged as candidates for removal. |
| **Context** | Doctrine |
| **Status** | canonical |
| **Applicable to** | `2.x` |
| **Related terms** | [Symbol-level Dead Code](#symbol-level-dead-code), [Ratchet Baseline](#ratchet-baseline) |

---
