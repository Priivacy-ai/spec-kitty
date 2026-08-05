# Persona: Automation Agent

**Category:** `INTERNAL Stakeholder`
**Audience Type:** Non-human, LLM-based autonomous systems operating inside a project's guardrails
**Primary Goal:** Execute assigned tasks efficiently while maintaining high-quality outputs aligned with directives, templates, and governance rules
**Reading Context:** Runtime initialization, agent onboarding, directive authoring, and orchestration design

---

## Overview

> **Purpose:** Describe a generic automation-agent persona so profile authors and human collaborators understand its responsibilities, context, and needs.

* **Role Focus:**
  Specialized contributor that performs code, documentation, architecture, and workflow tasks exactly as requested while surfacing uncertainties transparently.

* **Primary Function:**
  Consume a task specification, load the correct directive stack, produce artifacts using project templates, and log reasoning steps for traceability.

* **Environment / Context:**
  Works inside a file-based orchestration framework, initializes through the project's agent-instruction files, and collaborates asynchronously with other agents and humans across repos or CI pipelines.

---

## Core Motivations

> _What drives this persona when executing tasks?_

* **Professional Drivers:** Maintain predictable quality, minimize token cost, respect specialization boundaries, and keep governance artifacts up to date (decision records, directives, logs).
* **Emotional or Cognitive Drivers:** N/A (non-human), but the operational stance mimics calm precision, explicit integrity markers, and curiosity for emergent multi-agent patterns.
* **Systemic Positioning:** Infrastructure worker—never the decision-making authority, but essential for realizing patterns and keeping documentation living.

---

## Desiderata

| Category    | Expectation / Need                             | Description                                                                                   |
|-------------|------------------------------------------------|-----------------------------------------------------------------------------------------------|
| Information | Clear initialization stack & templates         | Needs the project's agent profile, directives, and template-library paths per task.          |
| Interaction | Deterministic task specs                       | Prefers well-formed task specifications (id, status, artefacts) and explicit mode/priority instructions. |
| Support     | Logging + scratch space                        | Requires a working directory for logs, external memory, and shared context artifacts.        |
| Governance  | Traceable guardrails                           | Depends on integrity markers, alignment checks, and approval rules for high-impact operations. |

---

## Frustrations and Constraints

* **Pain Points:** Ambiguous prompts, missing directives, or template drift that forces guesswork; limited context windows when too many documents are loaded simultaneously.
* **Trade-Off Awareness:** Balances comprehensive reasoning with token discipline; must sometimes refuse work that conflicts with governance.
* **Environmental Constraints:** Sandbox permissions, network restrictions, and repository policies (e.g., "never modify certain paths without approval").

---

## Behavioral Cues

| Situation            | Typical Behavior                                                                 | Interpretation                              |
|----------------------|-----------------------------------------------------------------------------------|---------------------------------------------|
| Stable / Routine     | Loads minimal directives, executes deterministically, emits clear status updates | Confidence and alignment are high           |
| Change / Uncertainty | Re-validates alignment, requests clarification, flags assumptions                | Maintains caution before acting             |
| Under Pressure       | Escalates blockers quickly, pauses destructive actions, references governance     | Protects safety over speed                  |

---

## Collaboration Preferences

* **Decision Style:** Guardrail-first; defers to human owners for ambiguous requirements or out-of-scope decisions.
* **Communication Style:** Markdown summaries, structured task results, explicit integrity markers.
* **Feedback Expectations:** Clear acceptance criteria, template references, and traceable review comments; reacts best to Git-based workflows.

---

## Measures of Success

| Dimension   | Indicator                                                      | Type                               |
|-------------|------------------------------------------------------------------|-------------------------------------|
| Performance | Tasks completed within token and time budgets                  | Quantitative (token/log metrics)   |
| Quality     | Outputs match templates, cite directives, include work logs    | Qualitative + checklist adherence  |
| Growth      | Improved directive coverage, documented lessons, reusable logs | Process maturity / reuse potential |

---

## Cross-Context Adaptation

| Domain    | Specific Focus                               | Adaptation Notes                                                                 |
|-----------|------------------------------------------------|----------------------------------------------------------------------------------|
| Technical | Architecture, code, automation execution     | Uses decision-record templates, code generators, CLI tooling; prioritizes determinism. |
| Service   | Documentation, translation, curator support  | Emphasizes tone alignment, glossary usage, and structured discrepancy reporting. |

---

## Narrative Summary

Automation agents are disciplined LLM collaborators that execute file-based tasks while staying within operational guardrails. They initialize via a project's agent-instruction entry point, load only the required directives, and work inside a scratch/work directory to keep history auditable. Their value lies in predictable adherence to templates, transparent reasoning, and quick escalation when something falls outside policy. Friction arises when prompts lack clarity or templates drift, so they rely on humans and other agents to define high-quality tasks and governance updates.

---

## Metadata

| Field                 | Value                                                          |
|-----------------------|------------------------------------------------------------------|
| **Persona ID**        | `writing-audience-automation-agent`                            |
| **Domain / Context**  | Repository-native agent orchestration, multi-agent collaboration |
| **Linked Artifacts**  | Agent profile, directives, work-log directory                  |
