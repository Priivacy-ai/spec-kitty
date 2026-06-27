---
title: 'Context: Identity'
description: 'Glossary context for identity: who performs work and who owns semantic decisions, defining the agent and related workflow-coordination roles.'
doc_status: active
updated: '2026-06-14'
related:
- docs/context/execution.md
- docs/context/practices-principles.md
---
## Context: Identity

Terms describing who performs work and who owns semantic decisions.

### Agent

| | |
|---|---|
| **Definition** | Logical collaborator identity used in workflow coordination (for example implementer, reviewer). |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Tool](./execution.md#tool), [Role](#role) |

---

### Role

| | |
|---|---|
| **Definition** | Responsibility assignment for a step or work package (implementer, reviewer, planner, etc.). |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Agent Profile

| | |
|---|---|
| **Definition** | Structured logical collaborator identity and behavior guidance, identified by a stable profile ID, that can govern assignment, handoff, role-scoped behavior, and tool-native custom-agent/subagent projection. |
| **Context** | Identity |
| **Status** | candidate |
| **Applicable to** | `3.x` |
| **Examples** | `architect-alphonso`, `researcher-robbie`, `implementer-ivan`, `reviewer-renata` |
| **Use when** | Describing who the collaborator is, what role boundaries it follows, and how it should be selected or handed off to. |
| **Do NOT use when** | Describing the generated file or host configuration that exposes the profile to Claude Code, Codex, Copilot, Cursor, Windsurf, or another tool; use [Tool Surface](./execution.md#tool-surface) instead. |
| **Related terms** | [Agent](#agent), [Role](#role), [Tool](./execution.md#tool) |

---

### Audience Persona

| | |
|---|---|
| **Definition** | Architecture-level stakeholder persona used to model needs, constraints, and success criteria for Spec Kitty usage and adoption. |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Location** | `docs/context/audience/` |
| **Related terms** | [Mission Participant](#mission-participant), [Human-in-Charge (HiC)](#human-in-charge-hic), [Internal Audience Persona](#internal-audience-persona), [External Audience Persona](#external-audience-persona) |

---

### Internal Audience Persona

| | |
|---|---|
| **Definition** | Persona representing contributors or runtime actors who directly shape or operate Spec Kitty from inside the delivery boundary. |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Persona catalog** | [Internal Audience Index](../../docs/context/audience/internal/README.md), [Lead Developer](../../docs/context/audience/internal/lead-developer.md), [Maintainer](../../docs/context/audience/internal/maintainer.md), [System Architect](../../docs/context/audience/internal/system-architect.md), [Spec Kitty CLI Runtime](../../docs/context/audience/internal/spec-kitty-cli-runtime.md), [AI Collaboration Agent](../../docs/context/audience/internal/ai-collaboration-agent.md), [Project Codebase](../../docs/context/audience/internal/project-codebase.md) |
| **Related terms** | [Audience Persona](#audience-persona), [Mission Participant](#mission-participant) |

---

### External Audience Persona

| | |
|---|---|
| **Definition** | Persona representing evaluators and decision-makers outside the runtime boundary who assess Spec Kitty value, fit, and adoption risk. |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Persona catalog** | [External Audience Index](../../docs/context/audience/external/README.md), [Project Owner](../../docs/context/audience/external/project-owner.md), [External Tech Lead Evaluator](../../docs/context/audience/external/tech-lead-evaluator.md), [External Architect Evaluator](../../docs/context/audience/external/architect-evaluator.md), [External Product Manager Evaluator](../../docs/context/audience/external/product-manager-evaluator.md) |
| **Related terms** | [Audience Persona](#audience-persona), [Mission Owner](#mission-owner) |

---

### Mission Participant

| | |
|---|---|
| **Definition** | Human or tool-backed collaborator participating in a mission and, when execution is active, in one or more mission runs. |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |

---

### Mission Owner

| | |
|---|---|
| **Definition** | Participant responsible for tie-breaking unresolved semantic conflicts when collaborators disagree. |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Rule** | Tie-break only after normal participant resolution fails |

---

### Human-in-Charge (HiC)

| | |
|---|---|
| **Definition** | The human who remains responsible and accountable for decisions made during a mission. Agents assist and propose, but the HiC owns the final call. This principle ensures that automation supports human judgement rather than replacing it. |
| **Context** | Identity |
| **Status** | canonical |
| **Applicable to** | `1.x`, `2.x` |
| **Related terms** | [Mission Owner](#mission-owner), [Collaboration Mode](./execution.md#collaboration-mode), [HiC cross-reference](./practices-principles.md#human-in-charge-cross-reference) |
