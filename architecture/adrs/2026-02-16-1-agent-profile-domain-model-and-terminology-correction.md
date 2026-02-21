# Agent Profile Domain Model and Agent/Tool Terminology Correction

**Filename:** `2026-02-16-1-agent-profile-domain-model-and-terminology-correction.md`

**Status:** Proposed

**Date:** 2026-02-16

**Deciders:** Stijn Dejongh, Claude Opus 4.6 (spec assistant)

**Technical Story:** Feature 047 — Agent Profile Domain Model

---

## Context and Problem Statement

Spec-kitty 2.x conflates two distinct concepts under the term "agent":

1. **Tool stack** — the IDE/CLI integration (claude, copilot, cursor, codex). This is infrastructure: which vendor's agent runtime is available and how it's invoked.
2. **Behavioral identity** — the persona operating under constraints (architect, implementer, reviewer). This is the *who*: purpose, specialization, collaboration patterns, reasoning modes.

The current `AgentConfig` (in `agent_config.py`) manages tool availability and selection strategy (`preferred_implementer`, `preferred_reviewer`). It knows nothing about specialization hierarchies, collaboration contracts, or behavioral constraints. The config.yaml `agents.available` list tracks tool stacks, not personas.

Meanwhile, the doctrine reference repository (`doctrine_ref/`) has a rich, mature agent profile system with 21 specialized profiles, a specialization hierarchy (DDR-011), role capabilities (Directive 009), and a 6-section profile template. This design is not represented in the spec-kitty codebase.

Features 042 (Bootstrap), 044 (Governance), 045 (Constitution Sync), and 046 (Routing) all reference "agent profiles" but none defines the canonical entity. The concept is fragmented across four specs with no owner.

## Decision Drivers

* **Language-first architecture** — terminology conflation ("agent" meaning both tool and persona) creates semantic ambiguity that propagates into code, config, and user-facing commands. Per the project's own doctrine approach, linguistic problems predict architectural problems.
* **Domain model clarity** — downstream features (governance, routing, bootstrap) need a well-defined entity to consume. Without it, each feature invents its own partial model.
* **Separation of concerns** — the profile domain model (behavioral identity) should not be coupled to the orchestrator's tool management code. Independent evolution and lower contextual scope improve agentic development velocity.
* **Doctrine alignment** — the doctrine reference repository provides a proven design. Spec-kitty should codify it rather than reinvent it.

## Considered Options

* **Option 1:** Enhance existing `AgentConfig` with profile fields (add specialization, collaboration, etc. to the existing class)
* **Option 2:** Create `AgentProfile` within `specify_cli` alongside `AgentConfig` (new module in existing package)
* **Option 3:** Create a separate `src/doctrine/` package with `AgentProfile` as a domain entity, rename `AgentConfig` to `ToolConfig`

## Decision Outcome

**Chosen option:** "Option 3: Separate `src/doctrine/` package with `AgentProfile`, rename `AgentConfig` to `ToolConfig`", because it provides the cleanest separation of concerns, corrects the terminology conflation at the root, and creates a foundation for shipping doctrine artifacts (profiles, tactics, directives) as a distributable module.

### Consequences

#### Positive

* **Terminology clarity** — "Tool" means infrastructure (claude, copilot), "Agent" means behavioral identity (architect, implementer). Config.yaml keys align with actual semantics.
* **Separation of concerns** — `src/doctrine/` has zero import dependencies on `specify_cli`. The profile model can evolve independently. Lower contextual scope for agents working on either package.
* **Foundation for doctrine distribution** — `src/doctrine/` can house reference profiles, tactics, directives, and other doctrine artifacts. Projects consuming spec-kitty get a coherent doctrine package.
* **Consumer clarity** — Features 042, 044, 045, 046 all import from `doctrine.model.profile` rather than each building their own partial model.
* **Hierarchy and routing** — specialization hierarchy (parent-child inheritance, weighted context matching) enables intelligent agent selection beyond simple preferred/random strategies.

#### Negative

* **Migration cost** — renaming `AgentConfig` to `ToolConfig` touches every file that imports it. Backward compatibility alias needed during transition.
* **New package** — `src/doctrine/` is a new top-level package in the monorepo, adding to the build/test/distribution surface.
* **Config.yaml migration** — existing projects have `agents:` key; new projects should use `tools:`. Dual-read with deprecation warning needed.
* **Profile maintenance** — shipped reference profiles are now code artifacts that need versioning, testing, and release management.

#### Neutral

* The doctrine reference repository (`doctrine_ref/`) remains an external symlink for design reference. `src/doctrine/` is the codified, distributable implementation — not a copy of the reference repo.
* `ToolConfig` retains `SelectionStrategy`, `preferred_implementer`, `preferred_reviewer` — these select tools, not personas. The naming now matches the semantics.

### Confirmation

* **Import analysis**: `src/doctrine/` has zero imports from `specify_cli` (verified by CI check or manual `grep`).
* **Round-trip test**: All shipped profiles load, serialize, and deserialize with identical state.
* **Backward compatibility**: Projects with `agents:` key in config.yaml load without error after rename.
* **Consumer adoption**: Features 044 and 046 reference `doctrine.model.profile.AgentProfile` in their planning artifacts.

## Pros and Cons of the Options

### Option 1: Enhance existing AgentConfig

Add profile fields (purpose, specialization, collaboration_contract, etc.) directly to `AgentConfig` in `agent_config.py`.

**Pros:**

* Minimal structural change — no new packages or files
* Single class to understand

**Cons:**

* Perpetuates the agent/tool terminology conflation
* Couples infrastructure config (which tools are available) with behavioral identity (what the persona does)
* `AgentConfig` becomes a god-object mixing tool selection, profile loading, hierarchy management, and collaboration contracts
* No separation of concerns — governance and routing import orchestrator internals

### Option 2: Create AgentProfile within specify_cli

Add `src/specify_cli/model/agent_profile.py` alongside the existing orchestrator code. Keep `AgentConfig` as-is.

**Pros:**

* No new top-level package — simpler build/distribution
* Profile model colocated with its primary consumer (orchestrator)

**Cons:**

* Does not correct the terminology conflation — `AgentConfig` still manages "agents" that are really tools
* `specify_cli` grows larger, increasing contextual scope for agents working in it
* No foundation for shipping doctrine artifacts (tactics, directives) as a coherent module
* Profile model coupled to orchestrator release cycle

### Option 3: Separate `src/doctrine/` package (chosen)

Create `src/doctrine/` as a new top-level Python package. Move the profile domain model there. Rename `AgentConfig` to `ToolConfig`.

**Pros:**

* Cleanest separation of concerns — behavioral identity vs infrastructure config
* Terminology correction at the source
* Foundation for doctrine distribution (profiles, tactics, directives)
* Lower contextual scope for agentic development
* Independent evolution of profile model

**Cons:**

* New package adds build/distribution complexity
* Migration cost for the rename
* Two places to look for "agent" related code (mitigated by clear naming: `doctrine.model.profile` vs `specify_cli.orchestrator.tool_config`)

## More Information

**Related ADRs:**
* ADR 2026-01-23-6 (Config-Driven Agent Management) — established `config.yaml` as agent config source; this ADR renames the concept from "agent" to "tool"

**Design Sources:**
* `doctrine_ref/templates/automation/NEW_SPECIALIST.agent.md` — 6-section profile template
* `doctrine_ref/decisions/DDR-011-agent-specialization-hierarchy.md` — hierarchy design
* `doctrine_ref/directives/005_agent_profiles.md` — profile directive
* `doctrine_ref/directives/009_role_capabilities.md` — canonical verbs
* `doctrine_ref/approaches/language-first-architecture.md` — linguistic architecture approach
* `doctrine_ref/docs/ddd-core-concepts-reference.md` — DDD modeling reference

**Feature Spec:**
* `kitty-specs/047-agent-profile-domain-model/spec.md`

**Consuming Features:**
* 042 (Bootstrap) — profile selection during onboarding
* 044 (Governance) — profile validation at lifecycle hooks
* 045 (Constitution Sync) — profile extraction to `agents.yaml`
* 046 (Routing) — specialization hierarchy for model selection
