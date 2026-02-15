# Feature Specification: Routing Provider Interface

**Feature Branch**: `046-routing-provider-interface`
**Created**: 2026-02-15
**Status**: Draft
**Input**: RoutingProvider Protocol with NullRoutingProvider for backward compatibility. Config-driven routing via `agent-tool-routing.yml` with `selection_method: static|llm_enhanced`. Fallback chains at model level.

## Overview

The 2.x orchestrator currently routes tasks at the **agent level** only — each agent maps to a single invoker class, with agent-level fallback (try next agent in the list). There is no model-level routing: you cannot select between GPT-4 and GPT-3.5 within the same agent, and there are no model-level fallback chains.

This feature introduces:

1. **RoutingProvider Protocol** — a Protocol-based abstraction (`route_task() → RoutingDecision`) that decouples model selection from agent selection. Sits above the existing agent invoker registry.
2. **NullRoutingProvider** — backward-compatible default that returns the agent's default model with no routing logic. Existing projects work unchanged.
3. **Config-driven routing** — `agent-tool-routing.yml` defines model preferences, fallback chains, and the selection method per agent profile.
4. **Dual selection method** — `static` (rule-based mapping from phase/complexity to model) and `llm_enhanced` (primary model consulted for context-aware selection).
5. **Model-level fallback chains** — when a model endpoint fails, try the next model in the chain before falling back to the next agent.

### Routing Architecture

```
Task Context (phase, complexity, budget)
    ↓
RoutingProvider.route_task()
    ↓ (static or llm_enhanced)
RoutingDecision (model, endpoint, fallback_chain, reasoning)
    ↓
Agent Invoker (existing) → Execute with selected model
    ↓ (on failure)
Fallback Chain → Try next model → Try next agent
```

### Configuration Format

```yaml
# .kittify/agent-tool-routing.yml
selection_method: static  # or llm_enhanced

profiles:
  implementer:
    primary_model: claude-sonnet-4-5
    fallback_chain:
      - claude-haiku-4-5
      - gpt-4.1
    budget_limit_per_task_usd: 2.00

  reviewer:
    primary_model: claude-sonnet-4-5
    fallback_chain:
      - gpt-4.1
    budget_limit_per_task_usd: 0.50

  planner:
    primary_model: claude-opus-4
    fallback_chain:
      - claude-sonnet-4-5

rules:  # Only used when selection_method: static
  - phase: plan
    complexity: high
    model: claude-opus-4
  - phase: implement
    complexity: low
    model: claude-haiku-4-5
  - phase: review
    model: claude-sonnet-4-5  # Default for all review tasks

llm_enhanced:  # Only used when selection_method: llm_enhanced
  routing_model: claude-haiku-4-5  # Which model makes routing decisions
  max_routing_cost_usd: 0.01       # Cap on routing decision cost
```

**2.x baseline**: `src/specify_cli/orchestrator/agent_config.py` (agent selection with preferred/random strategy), `src/specify_cli/orchestrator/scheduler.py` (agent assignment with concurrency management), `src/specify_cli/orchestrator/monitor.py` (agent-level fallback with NEXT_IN_LIST strategy), `src/specify_cli/orchestrator/invokers/` (one invoker per agent, no model selection).

## User Scenarios & Testing

### User Story 1 — Route a Task to the Appropriate Model (Priority: P1)

As a Spec Kitty orchestrator, when executing a work package, I need to determine which model/endpoint to use based on the task context (complexity, phase, budget), so that the right model handles each task cost-effectively.

**Why this priority**: This is the core routing mechanism. Without it, all tasks go to a single hardcoded model per agent.

**Independent Test**: Configure `agent-tool-routing.yml` with `selection_method: static` and rules mapping "plan" phase to opus, "implement" to sonnet. Submit a plan-phase task. Verify the RoutingDecision selects opus with reasoning referencing the static rule.

#### Functional Requirements

- **FR-1.1**: The system SHALL provide a `RoutingProvider` Protocol with a `route_task(context: TaskContext) → RoutingDecision` method.
- **FR-1.2**: `TaskContext` SHALL include: `phase` (plan/implement/review/accept), `complexity` (low/medium/high), `wp_id`, `feature_slug`, `agent_key`, `budget_remaining_usd` (optional), and `task_description` (summary of the work).
- **FR-1.3**: `RoutingDecision` SHALL include: `model` (model identifier), `endpoint` (optional, for custom endpoints), `fallback_chain` (list of fallback models), `reasoning` (human-readable explanation), and `estimated_cost_usd` (optional).
- **FR-1.4**: The system SHALL load routing configuration from `.kittify/agent-tool-routing.yml`.
- **FR-1.5**: When `selection_method: static`, the system SHALL match task context against the `rules` list in order, returning the first matching rule's model. If no rule matches, use the profile's `primary_model`.
- **FR-1.6**: When `selection_method: llm_enhanced`, the system SHALL send the task context to the `routing_model` and parse its response into a RoutingDecision. The routing call cost SHALL NOT exceed `max_routing_cost_usd`.
- **FR-1.7**: The RoutingDecision SHALL always include a `reasoning` field explaining why this model was selected (rule reference for static, model explanation for llm_enhanced).

### User Story 2 — Fallback Chain on Model Failure (Priority: P1)

As a Spec Kitty user, when the primary model endpoint is unavailable or returns an error, the system automatically tries the next model in the fallback chain, so my workflow is not blocked by a single provider outage.

**Why this priority**: Resilience is critical for unattended agent workflows (AFK mode). A single model failure should not halt a multi-WP execution.

**Independent Test**: Configure a fallback chain `[model-a, model-b, model-c]`. Mock model-a and model-b as failing. Verify model-c is used and the execution event records all attempts with fallback metadata.

#### Functional Requirements

- **FR-2.1**: Each routing profile SHALL support a `fallback_chain` — an ordered list of model identifiers to try if the primary model fails.
- **FR-2.2**: On primary model failure, the system SHALL iterate through the fallback chain in order, attempting each model until one succeeds.
- **FR-2.3**: After exhausting the model-level fallback chain, the system SHALL fall back to the existing agent-level fallback (try next agent), preserving backward compatibility.
- **FR-2.4**: Each fallback attempt SHALL be recorded in the execution event (Feature 043) with: model attempted, failure reason, attempt number, and time elapsed.
- **FR-2.5**: The system SHALL classify failures to determine fallback behavior: `RATE_LIMIT` (retry with backoff, then fallback), `AUTH_ERROR` (skip to next, likely all models for this provider fail), `TIMEOUT` (retry once, then fallback), `NETWORK_ERROR` (fallback immediately).
- **FR-2.6**: When all models and agents are exhausted, the system SHALL raise a clear `RoutingExhaustedError` with details about each attempted model/agent and their failure reasons.

### User Story 3 — NullRoutingProvider for Backward Compatibility (Priority: P1)

As a Spec Kitty user who hasn't configured routing, the system uses a NullRoutingProvider that always returns the agent's default model, so existing workflows are completely unaffected.

**Why this priority**: Backward compatibility. The vast majority of projects will not configure routing initially.

**Independent Test**: Create a project with no `agent-tool-routing.yml`. Verify `load_routing_provider()` returns a NullRoutingProvider. Verify `route_task()` returns the agent's default model with empty fallback chain. Verify behavior is identical to pre-routing-feature execution.

#### Functional Requirements

- **FR-3.1**: When no `agent-tool-routing.yml` exists, the system SHALL load a `NullRoutingProvider`.
- **FR-3.2**: `NullRoutingProvider.route_task()` SHALL return a RoutingDecision with the agent's default model, empty fallback chain, and reasoning "No routing configured — using agent default".
- **FR-3.3**: The NullRoutingProvider SHALL add zero latency — no file reads, no computation beyond constructing the default RoutingDecision.
- **FR-3.4**: The existing agent selection flow (agent_config.py → scheduler.py) SHALL remain unchanged. The routing provider sits below agent selection — it selects the model, not the agent.

### User Story 4 — LLM-Enhanced Context-Aware Routing (Priority: P2)

As a project owner, I want model selection to be context-aware — a lightweight model analyzes the task and makes an informed decision about which model to use, so that complex tasks get powerful models while simple tasks use cheaper ones.

**Why this priority**: LLM-enhanced routing is the advanced use case. Static routing covers most needs; LLM-enhanced adds intelligence for teams optimizing cost/quality tradeoffs.

**Independent Test**: Configure `selection_method: llm_enhanced` with `routing_model: claude-haiku`. Submit a high-complexity implement task. Verify the routing model is consulted and returns a decision selecting a capable model with reasoning like "implementation requires strong code generation — selecting opus."

#### Functional Requirements

- **FR-4.1**: When `selection_method: llm_enhanced`, the system SHALL send a structured prompt to the `routing_model` containing: task phase, complexity, description, budget, and available models.
- **FR-4.2**: The routing prompt SHALL request a JSON response with: `model`, `reasoning`, and `estimated_tokens`.
- **FR-4.3**: The routing call cost SHALL be tracked and SHALL NOT exceed `max_routing_cost_usd` (default: $0.01).
- **FR-4.4**: If the routing model is unavailable, the system SHALL fall back to static routing rules, then to the profile's primary_model.
- **FR-4.5**: The routing model response SHALL be cached for identical task contexts within the same orchestration session (avoid re-routing retries).
- **FR-4.6**: The routing call itself SHALL be recorded as an ExecutionEvent (Feature 043) with type `routing_decision`.

### User Story 5 — Budget-Aware Routing (Priority: P2)

As a project owner, I want routing to respect per-task budget limits, so that expensive models are only used when the budget allows.

**Why this priority**: Budget awareness connects routing to cost tracking (Feature 043). Without it, routing ignores financial constraints.

**Independent Test**: Configure `budget_limit_per_task_usd: 0.50` for the reviewer profile. Route a review task when estimated cost of the primary model exceeds $0.50. Verify the system selects a cheaper model from the fallback chain.

#### Functional Requirements

- **FR-5.1**: Each routing profile SHALL support an optional `budget_limit_per_task_usd` field.
- **FR-5.2**: When a budget limit is set, the routing system SHALL estimate the task cost (using Feature 043's pricing table) before selecting a model.
- **FR-5.3**: If the estimated cost of the primary model exceeds the budget, the system SHALL try cheaper models from the fallback chain.
- **FR-5.4**: If no model fits within budget, the system SHALL warn and proceed with the cheapest available model (advisory, not blocking — unless governance escalates to block via Feature 044).
- **FR-5.5**: Budget enforcement SHALL integrate with the constitution layer — budget limits defined in `agent-tool-routing.yml` can be overridden by the constitution's governance enforcement section.

### User Story 6 — Routing Observability (Priority: P3)

As a Spec Kitty operator, I want to see which model was selected for each task and why, so I can tune my routing configuration.

**Why this priority**: Observability enables configuration improvement over time. Lower priority because routing must work before it can be observed.

**Independent Test**: Run several tasks with routing configured. Run `spec-kitty agent telemetry routing`. Verify a report shows per-task routing decisions with model, reasoning, cost, and whether fallback was used.

#### Functional Requirements

- **FR-6.1**: Every routing decision SHALL be recorded as an ExecutionEvent (Feature 043) with: selected model, reasoning, fallback attempts (if any), routing method (static/llm_enhanced), and routing latency.
- **FR-6.2**: The `spec-kitty agent telemetry` command SHALL support a `--routing` flag showing routing decision statistics: model distribution, fallback frequency, budget utilization.
- **FR-6.3**: Routing events SHALL integrate with the governance system (Feature 044) — governance hooks can validate that routing decisions comply with constitution rules.

## Success Criteria

1. **SC-1**: Static routing selects the correct model based on phase/complexity rules with zero AI invocation overhead.
2. **SC-2**: LLM-enhanced routing selects context-appropriate models with routing cost under $0.01 per decision.
3. **SC-3**: Fallback chains recover from model failures without manual intervention, trying all configured models before agent-level fallback.
4. **SC-4**: NullRoutingProvider adds zero latency and preserves exact pre-feature behavior for unconfigured projects.
5. **SC-5**: Budget limits prevent expensive model usage when cheaper alternatives are available and sufficient.
6. **SC-6**: All routing decisions are recorded in telemetry with reasoning, enabling configuration tuning.
7. **SC-7**: The routing config file (`agent-tool-routing.yml`) is human-readable and editable without requiring code changes.

## Scope Boundaries

### In Scope
- RoutingProvider Protocol + NullRoutingProvider + ConfigDrivenRoutingProvider
- `agent-tool-routing.yml` configuration file
- Static rule-based routing (phase/complexity → model)
- LLM-enhanced context-aware routing
- Model-level fallback chains
- Budget-aware model selection
- Integration with telemetry (Feature 043) and governance (Feature 044)
- Routing observability via telemetry commands

### Out of Scope
- Agent-level routing changes — existing agent selection (agent_config.py) remains unchanged
- Custom endpoint management (bring-your-own API endpoints) — deferred
- Multi-provider aggregation (split a task across multiple models) — deferred
- Real-time model performance monitoring — deferred
- Automated routing optimization (learning from past decisions) — deferred

## Dependencies

- **Feature 043** (Telemetry Foundation) — routing decisions recorded as ExecutionEvents; budget limits use the pricing table for cost estimation
- **Feature 044** (Governance + Doctrine Provider) — governance hooks can validate routing decisions; budget enforcement can be escalated to blocking
- **Feature 045** (Constitution Parser) — routing config overrides can flow from the constitution layer

## Glossary Alignment

| Term | Definition (per project glossary) |
|------|-----------------------------------|
| **RoutingProvider** | Protocol-based abstraction that maps task context to a model selection decision (RoutingDecision). |
| **RoutingDecision** | The output of routing: selected model, endpoint, fallback chain, reasoning, and estimated cost. |
| **NullRoutingProvider** | Default implementation that returns the agent's default model with no routing logic. Ensures backward compatibility. |
| **Fallback Chain** | An ordered list of model identifiers to try when the primary model fails. Exhausted before agent-level fallback. |
| **Selection Method** | The routing strategy: `static` (rule-based) or `llm_enhanced` (context-aware via lightweight model consultation). |
| **Task Context** | The input to routing: phase, complexity, work package, budget, and task description. |