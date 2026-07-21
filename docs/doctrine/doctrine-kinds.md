---
title: Doctrine artifact kinds
description: What each doctrine artifact kind is for, with a real built-in example of each — sourced directly from the charter kind-vocabulary code.
doc_status: active
updated: '2026-07-20'
type: explanation
related:
- docs/doctrine/index.md
- docs/doctrine/create-a-doctrine-artifact.md
- docs/context/doctrine.md
- docs/architecture/org-doctrine-layer.md
- docs/guides/setup-governance.md
---
# Doctrine artifact kinds

Doctrine is the layered set of governed content that shapes how missions and agents behave in a
Spec Kitty project — the rules directives enforce, the techniques tactics teach, the personas
agent profiles define, and so on. Everything in doctrine is one of a fixed set of **kinds**. This
page explains what each kind is for, with a real example drawn from this repository's own
built-in doctrine.

## Single source of truth

The kind list on this page is not invented for the docs — it is read directly from
[`src/charter/kind_vocabulary.py`](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/charter/kind_vocabulary.py)
and [`src/doctrine/artifact_kinds.py`](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/doctrine/artifact_kinds.py),
and cross-checked against the running CLI. You can reproduce the same list yourself:

```bash
# Passing an invalid kind makes the CLI print the full valid list back at you
spec-kitty charter activate bogus-kind some-id
# Error: Unknown kind 'bogus-kind'. Valid kinds: agent-profile, directive,
# mission-step-contract, mission-type, paradigm, procedure, styleguide, tactic,
# toolguide.
```

Strip `mission-type` from that list (it is a *mission* concept, not a doctrine artifact kind —
see [the mission system](../architecture/mission-system.md)) and you have the eight doctrine
artifact kinds documented below: **directive, tactic, styleguide, toolguide, paradigm, procedure,
agent_profile, mission_step_contract**.

> **A note on `template` and `asset`.** If you read `src/doctrine/artifact_kinds.py` directly,
> you will see two more members of the `ArtifactKind` enum: `template` and `asset`. Both are real
> and both are handled by the doctrine system — but neither is one of the eight kinds above,
> and the CLI error message above is the proof: `template` and `asset` do not appear in the
> "Valid kinds" list because they are explicitly excluded from `CHARTER_KIND_TOKENS` (the set
> `charter activate`/`deactivate`/`list`/`context --include` operate over). `template` is
> mission-scoped (it ships as part of a mission type's own template set, not as a
> standalone artifact you activate — `spec-kitty charter list --all` reports it as
> "mission-scoped — not separately activated"). `asset` is a newer, loose-contract kind
> (added alongside `template` for org-pack binary/media references) with no built-in
> artifacts yet. Both are worth knowing exist; neither is part of the eight-kind
> activation vocabulary this page and its companion how-to cover.

## The eight doctrine artifact kinds

### Directive

**Purpose.** A constraint-oriented governance rule that applies across flows or phases.
Directives encode required or advisory expectations and can reference lower-level tactics for
execution. Directives are the "must/should" layer of doctrine — the rule, not the recipe for
following it.

**Location.** `src/doctrine/directives/built-in/*.directive.yaml` (project overlay:
`.kittify/doctrine/directive/`).

**Example.** `DIRECTIVE_001` — "Architectural Integrity Standard"
(`src/doctrine/directives/built-in/001-architectural-integrity-standard.directive.yaml`).
Its `intent` requires that "system designs must maintain clear separation of concerns and
well-defined component boundaries," and its `procedures`/`integrity_rules`/`validation_criteria`
fields spell out how a reviewer checks compliance — without prescribing exactly how to
decompose any given system (that's a tactic's job).

### Tactic

**Purpose.** A reusable behavioral execution pattern that defines *how* work is performed.
Tactics are operational and agent-consumable, and can be selected by directives and mission
context. Where a directive says "you must," a tactic says "here is how, step by step."

**Location.** `src/doctrine/tactics/built-in/**/*.tactic.yaml` (project overlay:
`.kittify/doctrine/tactic/`).

**Example.** `problem-decomposition`
(`src/doctrine/tactics/built-in/architecture/problem-decomposition.tactic.yaml`). Its `steps`
walk an agent through stating a problem in one sentence, enumerating contributing factors,
clustering them into independent sub-problems, and validating completeness — a concrete,
followable procedure for a specific recurring situation (breaking down an ambiguous problem
before committing to a solution).

### Styleguide

**Purpose.** A doctrine artifact defining cross-cutting quality and consistency conventions (for
example coding, documentation, or testing style) that apply across missions and templates.
Styleguides are about *how things should look and read*, not about a specific procedure.

**Location.** `src/doctrine/styleguides/built-in/*.styleguide.yaml` (project overlay:
`.kittify/doctrine/styleguide/`).

**Example.** `plain-language`
(`src/doctrine/styleguides/built-in/plain-language.styleguide.yaml`). Its `principles` govern
this very kind of page: write for the named audience, prefer the short common word, one idea per
sentence, active voice, define a term once and reuse it, show rather than only tell. This page
was written under that styleguide.

### Toolguide

**Purpose.** A doctrine artifact defining tool-specific operational guidance, syntax, and
constraints (for example a particular diagramming tool's conventions) used by agents and
contributors during execution. Toolguides are scoped to one external tool, not to a general
technique.

**Location.** `src/doctrine/toolguides/built-in/*.toolguide.yaml`, each pointing at a
companion `guide_path` (project overlay: `.kittify/doctrine/toolguides/`).

**Example.** `mermaid-diagramming`
(`src/doctrine/toolguides/built-in/mermaid-diagramming.toolguide.yaml`), which points at
`MERMAID_DIAGRAMMING.md` for syntax patterns, theming, and rendering conventions when a mission
needs a diagram-as-code artifact.

### Paradigm

**Purpose.** A worldview-level framing for how work is approached in a domain. Paradigms
influence the selection and interpretation of directives and tactics but are not executable step
recipes themselves — they are the lens, not the checklist.

**Location.** `src/doctrine/paradigms/built-in/*.paradigm.yaml` (project overlay:
`.kittify/doctrine/paradigms/`).

**Example.** `domain-driven-design`
(`src/doctrine/paradigms/built-in/domain-driven-design.paradigm.yaml`). Its `summary` frames
software design around a deep model of the business domain (Bounded Contexts, Ubiquitous
Language, Aggregates); its `directive_refs` link it to `DIRECTIVE_001`, `DIRECTIVE_031`, and
`DIRECTIVE_032`, and it authors `rejects` DRG edges naming the anti-patterns it warns against
(for example the `anemic-domain-model` anti-pattern node) so the consistency-check and rendered
agent context can surface "avoid this" targets. (This replaces the retired `opposed_by` field —
see [ADR 2026-07-21-1](../adr/3.x/2026-07-21-1-in-tension-with-drg-edge.md).)

### Procedure

**Purpose.** A reusable doctrine subworkflow that a step contract may delegate to for part of a
mission action. Procedures are structured, stateful playbooks with defined entry/exit
conditions — unlike tactics (small composable techniques), procedures orchestrate multi-step
flows that can be paused, resumed, and validated. They are not tracked missions and not runtime
sessions.

**Location.** `src/doctrine/procedures/built-in/*.procedure.yaml` (project overlay:
`.kittify/doctrine/procedure/`).

**Example.** `adversarial-squad-deployment`
(`src/doctrine/procedures/built-in/adversarial-squad-deployment.procedure.yaml`). Its
`entry_condition` is "a work product has reached a review point-cut... and an independent
multi-lens assessment would reduce the risk of a costly miss"; its `steps` cover choosing the
point-cut, selecting complementary profiles, running the delegates in parallel, and
synthesizing a verdict — a bounded, resumable workflow, not a single technique.

### Agent Profile

**Purpose.** A structured logical collaborator identity and behavior guidance, identified by a
stable profile ID, that governs assignment, handoff, role-scoped behavior, and tool-native
custom-agent/subagent projection. An agent profile is *who* is doing the work and *how they are
allowed to operate* — roles, capabilities, directive references, and collaboration rules — not a
technique or a rule in isolation.

**Location.** `src/doctrine/agent_profiles/built-in/*.agent.yaml` (project overlay:
`.kittify/doctrine/agent_profiles/`; key field is `profile-id`, not `id`).

**Example.** `doctrine-daphne`
(`src/doctrine/agent_profiles/built-in/doctrine-daphne.agent.yaml`) — the profile this very page
was authored under. Its `roles` are `curator` and `onboarding-guide`; its `capabilities` include
`artifact-kind-classification` and `pack-artifact-authoring`; its `context-sources` pull in the
paradigm/directive/tactic/procedure/styleguide layers plus specific directives (`003`, `018`,
`032`, `043`, `044`) so the agent has the right doctrine loaded before curating more of it.

### Mission step contract

**Purpose.** A structured contract for one mission action, including step sequencing, guard
evaluation, prompt binding, and delegation hooks. Mission step contracts are what turn a mission
type's abstract action sequence (specify → plan → tasks → implement → review) into concrete,
executable steps — each step can delegate to a directive, tactic, or procedure.

**Location.** `src/doctrine/missions/built_in_step_contracts/*.step-contract.yaml`
(project overlay: `.kittify/doctrine/mission_step_contracts/`).

**Example.** `specify` action, software-dev mission
(`src/doctrine/missions/built_in_step_contracts/specify.step-contract.yaml`). Its `bootstrap`
step loads charter context; `capture_intent` delegates to directives
`010-specification-fidelity-requirement` and `037-living-documentation-sync`; `map_examples`
delegates to the `example-mapping-workshop` procedure; `validate_requirements` delegates to the
`requirements-validation-workflow` tactic. This is the contract that makes `/spec-kitty.specify`
pull in exactly that doctrine, in that order.

## Where to go next

- To author and activate a new artifact of any of these kinds, follow
  [Create a doctrine artifact](create-a-doctrine-artifact.md).
- For how built-in, org, and project doctrine layers combine and override each other, see
  [Understanding the Org Doctrine Layer](../architecture/org-doctrine-layer.md).
- For the canonical glossary definitions these purpose statements are grounded in, see the
  [doctrine context glossary](../context/doctrine.md) and the
  [Agent Profile](../context/identity.md#agent-profile) /
  [step contract](../context/orchestration.md#step-contract) entries.
