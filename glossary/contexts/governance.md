## Context: Governance

Terms describing behavioral governance — rules, validation, and compliance.

### Doctrine (Agentic Doctrine)

| | |
|---|---|
| **Definition** | Spec Kitty's behavioral governance framework — a stack of Guidelines → Approaches → Directives → Tactics → Templates providing policy enforcement, decision traceability, agent profiles, and precedence-driven constraint systems. Distributed as a git subtree at `doctrine/`. |
| **Context** | Governance |
| **Status** | canonical |
| **Related terms** | [Guideline](#guideline), [Directive](#directive), [Approach](#approach), [Tactic](#tactic), [Constitution](#constitution) |

---

### Guideline

| | |
|---|---|
| **Definition** | A high-level, immutable governance rule from the governance stack. Two levels: **general** (highest precedence, non-negotiable framework values) and **operational** (day-to-day behavioral norms). No project-level override may contradict them. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `doctrine/guidelines/general/`, `doctrine/guidelines/operational/` |
| **Related terms** | [Precedence Hierarchy](#precedence-hierarchy), [Directive](#directive), [Constitution](#constitution) |

---

### Directive

| | |
|---|---|
| **Definition** | A numbered, cross-cutting behavioral constraint from the governance stack. Directives have phase tags (indicating when they apply), severity (advisory/required), and structured rules. They can be narrowed by the Constitution but not removed. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `doctrine/directives/*.md` (YAML front matter + markdown body) |
| **In code** | `Directive` (dataclass), referenced by integer ID (`directive_refs`) |
| **Related terms** | [Guideline](#guideline), [Precedence Hierarchy](#precedence-hierarchy), [Agent Profile](#agent-profile) |
| **Examples** | Directive 017 (TDD Required), Directive 023 (Conventional Commits), Directive 034 (Spec-Driven Development) |

---

### Approach

| | |
|---|---|
| **Definition** | A mental model and domain-specific philosophical framework within the governance stack. Approaches define *how to think* about a domain or problem type — distinct from step-by-step [Tactics](#tactic). Approaches are **user-selectable**: during [Bootstrap](#bootstrap), users choose which approaches their specialist agents should follow (e.g., "use TDD", "use test-first bug fixing", "use locality-of-change"). Selected approaches are stored as project-level preferences in the [Constitution](#constitution) and shape agent behavior for all features. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `doctrine/approaches/*.md` |
| **Related terms** | [Tactic](#tactic), [Mission](#mission), [Constitution](#constitution), [Bootstrap](#bootstrap) |
| **Examples** | TDD (Test-Driven Development), Test-First Bug Fixing, Locality of Change, Decision-First Development, Living Glossary Practice |
| **Distinction** | Users select approaches during bootstrap. Agents consume the associated tactics during execution. |

---

### Tactic

| | |
|---|---|
| **Definition** | A step-by-step execution pattern within the governance stack — concrete procedures for performing specific activities. Together with Templates, they form the lowest precedence governance layer. Tactics are **agent-facing**: agents pull in the specific tactic files they need during execution. Users do not select tactics directly — they select [Approaches](#approach) (e.g., "use TDD"), and the relevant tactics follow as implementation details. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `doctrine/tactics/*.tactic.md` |
| **Related terms** | [Approach](#approach), [Template (Doctrine)](#template-doctrine), [Slash Command](#slash-command) |
| **Distinction** | Approaches define *how to think* (user-selectable). Tactics define *how to execute* (agent-consumed). |

---

### Template (Doctrine)

| | |
|---|---|
| **Definition** | An output contract and artifact scaffold within the governance stack — the structured format that Tactics produce. Not to be confused with spec-kitty's slash command templates. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `doctrine/templates/` |
| **Related terms** | [Tactic](#tactic) |

---

### Constitution

| | |
|---|---|
| **Definition** | A project-level governance document that narrows or extends Doctrine rules for a specific repository. Human-readable markdown created via `/spec-kitty.constitution` in current implementation. May narrow directive thresholds but must not contradict Guidelines. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `.kittify/memory/constitution.md` |
| **In code** | Constitution command templates; parser and enforcement are evolving under Feature 044 |
| **Related terms** | [Guideline](#guideline), [Precedence Hierarchy](#precedence-hierarchy) |
| **Precedence position** | 3 (after General and Operational Guidelines; before Directives) |

---

### Precedence Hierarchy

| | |
|---|---|
| **Definition** | The conflict resolution order when governance rules disagree. Higher-precedence rules override lower ones. This is the governing rule for resolving conceptual conflicts in governance terms. |
| **Context** | Governance |
| **Status** | canonical |
| **In code** | Defined in Feature 044 governance spec; implementation is in progress |
| **Related terms** | [Guideline](#guideline), [Constitution](#constitution), [Directive](#directive), [Approach](#approach), [Tactic](#tactic) |
| **Operational rule** | When sources disagree, apply this hierarchy first; use newer accepted ADRs over older ADRs; then align with current implementation behavior |

```
General Guidelines > Operational Guidelines > Constitution > Directives > Approaches > Tactics/Templates
```

---

### Governance Plugin

| | |
|---|---|
| **Definition** | An ABC that validates workflow state at lifecycle boundaries. Returns a `ValidationResult` (pass/warn/block) with reasons, directive references, and suggested actions. The `NullGovernancePlugin` is the default no-op implementation. |
| **Context** | Governance |
| **Status** | canonical |
| **In code** | `GovernancePlugin` (ABC), `NullGovernancePlugin`, `DoctrineGovernancePlugin` |
| **Related terms** | [Validation Result](#validation-result), [Governance Context](#governance-context) |

---

### Validation Result

| | |
|---|---|
| **Definition** | Structured output of a governance check. Contains status (pass/warn/block), reasons, directive references, and suggested actions. |
| **Context** | Governance |
| **Status** | canonical |
| **In code** | `ValidationResult` (Pydantic BaseModel, frozen) |
| **Related terms** | [Governance Plugin](#governance-plugin), [Validation Event](#validation-event) |
| **Fields** | `status` (ValidationStatus), `reasons` (list[str]), `directive_refs` (list[int]), `suggested_actions` (list[str]) |

---

### Governance Context

| | |
|---|---|
| **Definition** | The context object passed to governance hooks. Provides the plugin with enough information to make a validation decision without direct file access. |
| **Context** | Governance |
| **Status** | canonical |
| **In code** | `GovernanceContext` (Pydantic BaseModel, frozen) |
| **Related terms** | [Governance Plugin](#governance-plugin), [Tool](#tool), [Agent](#agent), [Role](#role) |

**Fields**:
- `phase` — Current lifecycle phase
- `feature_slug` — Feature identifier
- `work_package_id` — WP being validated
- `tool_id` — Which tool is executing
- `agent_profile_id` — Which Doctrine agent profile applies
- `agent_role` — Role: implementer, reviewer, etc.

---

### Two-Masters Problem

| | |
|---|---|
| **Definition** | The conflict that arises when both [Guidelines](#guideline) and the [Constitution](#constitution) claim top-level behavioral authority over agents. Resolved by the [Precedence Hierarchy](#precedence-hierarchy): Constitution sits at position 3 — it customizes within Guideline bounds, not above them. |
| **Context** | Governance |
| **Status** | canonical |
| **Synonyms** | Dual Authority Problem |
| **Related terms** | [Precedence Hierarchy](#precedence-hierarchy), [Constitution](#constitution), [Guideline](#guideline) |

---

### ADR (Architectural Decision Record)

| | |
|---|---|
| **Definition** | An immutable record of a single architecturally significant decision, including context, alternatives considered, decision outcome, and consequences. Accepted ADRs are not edited; changes are captured by superseding ADRs. |
| **Context** | Governance |
| **Status** | canonical |
| **Location** | `architecture/adrs/` |
| **Related terms** | [Constitution](#constitution), [Precedence Hierarchy](#precedence-hierarchy), [Living Specification](#living-specification) |

---
