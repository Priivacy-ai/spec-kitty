# Context Window Efficiency and Budgeting

**Status:** Proposed  
**Date:** 2026-02-16  
**Owner:** Spec Kitty 2.x team  
**Branch Context:** `develop` integration branch for 2.x sync-safe evolution

## Problem Statement

Current agent/tooling flows (Claude, Copilot, and similar integrations) appear to consume significantly more context tokens than task complexity requires.

This is especially visible when:

- task scope is narrow (single-file or low-complexity changes),
- doctrine/persona guidance is relatively compact,
- large static context blocks are repeatedly sent with little per-task variation.

The concern is that prompt payload size is inflating cost and latency without equivalent quality gains.

## Hypothesis

If we split context into budgeted layers (required core, task-scoped dynamic, and optional on-demand references), then we can reduce input-token usage by at least 40% on routine tasks while maintaining comparable output quality and completion success.

## Telemetry Baseline Availability

This experiment reuses existing telemetry instead of introducing a parallel measurement stack.

Current coverage already includes:

- planning commands (`create-feature`, `setup-plan`, `finalize-tasks`) with `role="planner"`,
- implementation/review commands (`workflow implement`, `workflow review`) with role attribution,
- per-feature execution logs in `kitty-specs/*/execution.events.jsonl`,
- aggregation via `spec-kitty agent telemetry cost`.

## Directive-Informed Extension (014/015)

This experiment also evaluates whether a lightweight reflection loop improves
token efficiency over time by reducing repeated mistakes:

- **Directive 014 pattern:** structured work logs after meaningful planning,
  implementation, and review runs.
- **Directive 015 pattern:** optional prompt SWOT capture for ambiguous, novel,
  or high-rework tasks.

Rollout is intentionally staged:

- **Stage A (MVP):** constitution-defined behavior, advisory (no hard blocks).
- **Stage B (future):** status-change hook enforcement after MVP evidence.

## Additional Working Theories

### Theory A: Canonical Vocabulary Reduces Re-interpretation Cost

If a maintained glossary is used as the canonical language source during
specification and planning, agents should spend fewer tokens re-deriving term
meanings and domain boundaries on each run.

### Theory B: Formal Design + Agent Profiles Reduce Context Reload

If architecture journeys/design artifacts and agent profiles are explicit and
referenced as authoritative inputs, planning prompts can focus on deltas instead
of repeatedly reconstructing project intent and role behavior.

### Theory C: Spec-Step Telemetry Closes Planning Blind Spot

Planning telemetry exists, but specification creation needs explicit tracking in
the lifecycle to compare spec vs plan token economics with the same rigor.

### Theory D: Phased Discovery/Load + Working Memory Offload Shrink Active Context

If we apply phased context loading and offload detailed notes to working memory
following doctrine patterns (Directive 002 and Directive 008), active prompt
windows should stay smaller without losing continuity.

### Theory E: Context-Aware Design (Directive 037) Narrows Search Path

If glossary usage is paired with context-aware design discipline (explicit
bounded contexts, boundary translation, and context-owned terminology), agents
should traverse a narrower candidate search path during execution.

## Success and Failure Criteria

### Success Criteria

- Median input tokens per task reduced by `>= 40%` for targeted task classes.
- End-to-end task success rate does not degrade by more than `5%`.
- Median correction loop count (rework turns) does not increase by more than `10%`.
- No regressions on safety/integrity constraints defined by project governance files.

### Failure Criteria

- Token reduction is under `20%` after optimization passes.
- Quality regressions exceed acceptable thresholds.
- Optimization introduces brittle prompting behavior across providers.

## Metrics and Instrumentation Plan

Collect metrics per run and aggregate by task archetype:

- `input_tokens`
- `output_tokens`
- `total_tokens`
- `latency_ms`
- `task_success` (pass/fail against acceptance checks)
- `rework_turns` (number of corrective prompt cycles)
- `provider` / `model`
- `context_profile` (`baseline`, `budgeted-v1`, `budgeted-v2`)
- `role` (`planner`, `implementer`, `reviewer`) for phase-aware comparisons
- `worklog_created` (yes/no)
- `prompt_swot_created` (yes/no)
- `glossary_reused` (yes/no)
- `design_artifact_reused` (yes/no)
- `agent_profile_reused` (yes/no)
- `phased_context_loading_used` (yes/no)
- `working_memory_offload_used` (yes/no)
- `offload_artifact_count` (count)
- `context_reload_count` (count per run)
- `search_path_proxy` (count of candidate files/terms consulted before action)
- `phase` (`specify`, `plan`, `implement`, `review`)

Data sources:

- Execution events from existing telemetry foundation (`ExecutionEvent` payload fields).
- `spec-kitty agent telemetry cost --json` for aggregated token/cost reporting.
- Reflection artifacts captured by constitution policy (work logs + prompt SWOT docs).
- Existing spec-kitty task outcomes and test execution status for quality checks.
- Presence/usage of glossary and architecture design artifacts in phase inputs.
- Offload artifacts and notes referenced during phased loading.

No new telemetry schema is required for initial experiment runs. Add schema fields only if an analysis gap is confirmed.

## Experiment Design

### Phase 1: Baseline Readiness Check

Validate telemetry completeness before sampling:

- confirm planning and implementation commands emit `ExecutionEvent`,
- confirm token fields are populated for sampled runs,
- confirm `role` attribution is consistent for planning vs implementation.

### Phase 2: Baseline Capture

Run a representative sample of tasks in current mode:

- small implementation task,
- review/refactor task,
- spec/planning task.

Record all metrics under `context_profile=baseline`.

### Phase 3: Context Decomposition

Refactor prompt assembly into three buckets:

- **Core required:** minimal guardrails and execution contract.
- **Task-scoped dynamic:** only files/spec sections directly relevant to the requested work.
- **On-demand references:** doctrine/background loaded only when explicitly needed.

### Phase 4: Budgeted Variants

Test at least two budgeted profiles:

- `budgeted-v1`: conservative trimming, low risk.
- `budgeted-v2`: aggressive trimming with retrieval fallback.

### Phase 5: Comparative Evaluation

Compare baseline vs variants on:

- token efficiency,
- quality outcomes,
- latency and retry behavior,
- cross-provider stability.
- planning-vs-implementation efficiency deltas using `role`.
- reflection adoption impact (`worklog_created`/`prompt_swot_created` vs rework).

### Phase 6: Constitution MVP and Hook Decision

1. Add a constitution section that defines "reflect and capture" expectations:
   - when work logs are expected,
   - when prompt SWOT is recommended,
   - where artifacts are stored,
   - that enforcement is advisory for MVP.
2. Run at least one iteration with that constitution active.
3. If data shows value, create follow-up work to enforce via status-change hooks.

### Phase 7: Spec/Plan Knowledge-Reuse Evaluation

Compare runs with and without explicit glossary/design references in prompt
inputs, then evaluate:

- token reduction during `specify` and `plan`,
- clarification-loop reduction,
- quality stability of generated artifacts.
- effect of explicit agent profiles during specification/planning.

### Phase 8: Telemetry Scope Decision (No Implementation in This Experiment)

Document a concrete proposal for adding specification-step telemetry capture to
the lifecycle, including:

- event boundaries for `specify`,
- required fields for phase-level analysis,
- compatibility with existing telemetry model.

This experiment phase stops at proposal and decision; implementation is deferred
to a follow-up feature.

### Phase 9: Phased Load + Offload Technique Evaluation (No Implementation)

Define and compare two prompt assembly modes at experiment-design level:

- **Monolithic load:** broad context loaded upfront.
- **Phased load/offload:** core governance always loaded, task-specific detail
  loaded incrementally, detailed notes offloaded to external working memory.

Evaluate deltas for token use, rework, and continuity quality.

### Phase 10: Context-Aware Search-Path Evaluation (No Implementation)

Document how glossary + Directive 037 context-aware rules are expected to reduce
agent search breadth, then test with proxy measures (`search_path_proxy`,
`context_reload_count`) across similar tasks.

## Execution Approach

Use an iterative, low-cost experimental loop with intentionally small feature
scope and one-variable-at-a-time changes.

### Guiding Principles

- Keep each experiment run small to control token spend.
- Change one optimization lever at a time.
- Execute real feature work after each saved change to measure actual impact.
- Compare against a stable baseline workload, not ad-hoc tasks.

### Baseline Strategy (Mini-Feature First)

Create a dedicated mini-feature in `kitty-specs/` focused on telemetry coverage
for early lifecycle phases. The goal is to establish a repeatable baseline for
specification + planning costs with minimal implementation overhead.

Baseline run requirements:

- run a full `specify` + `plan` flow on the mini-feature,
- ensure execution events are emitted for available planning commands,
- collect session/tool-level total cost at session close,
- record baseline as `context_profile=baseline` with fixed prompt inputs.

Note: This gives an operational estimate of `spec` + `planning` cost. Precision
improves as phase-level telemetry coverage becomes more complete.

### Iterative Draft Plan

1. **Iteration 0 — Baseline Capture**
   - Establish mini-feature and collect baseline `specify` + `plan` costs.
   - Freeze workload definition for all subsequent comparisons.
2. **Iteration 1 — Glossary Introduction**
   - Add glossary usage in discovery/spec/planning inputs.
   - Re-run same mini-feature workload and compare deltas.
3. **Iteration 2 — Design Artifact Formalization**
   - Add explicit design/journey artifacts as authoritative references.
   - Re-run workload and measure token + rework changes.
4. **Iteration 3 — Agent Profile Contexting**
   - Add explicit profile-driven role context in planning flow.
   - Re-run workload and compare to Iteration 2.
5. **Iteration 4 — Phased Discovery/Load**
   - Apply phased loading rules (core always loaded, details staged in).
   - Re-run workload and measure context window reduction.
6. **Iteration 5 — Working Memory Offload**
   - Introduce offload notes/artifacts for detailed transient context.
   - Re-run workload and evaluate continuity vs token savings.
7. **Iteration 6 — Context-Aware Design Narrowing**
   - Apply bounded-context vocabulary and boundary translation discipline.
   - Re-run workload and evaluate search-path proxies.
8. **Iteration 7 — Consolidation Decision**
   - Rank interventions by impact/cost/risk.
   - Propose ADR + implementation backlog for top-performing changes.

### Per-Iteration Measurement Protocol

- Use the same task script and acceptance checks each run.
- Record metrics immediately after run completion.
- Save run report with:
  - applied change,
  - token/cost delta vs baseline,
  - quality/rework delta,
  - keep/drop recommendation.
- Do not stack additional optimizations until the current one is measured.

## Risks and Mitigations

- **Risk:** Over-trimming removes needed constraints.  
  **Mitigation:** Keep non-negotiable safety and workflow constraints in the core bucket.

- **Risk:** Provider-specific behavior diverges.  
  **Mitigation:** Evaluate each supported tool/provider separately before default rollout.

- **Risk:** Lower context increases rework turns and hidden cost.  
  **Mitigation:** Track rework_turns and total_tokens, not just input_tokens.

## Decision Gate

Promote this experiment to:

- an ADR if budgeted context strategy proves stable and beneficial, and
- implementation work packages in `kitty-specs/` for rollout, migration, and tooling updates.

If results are mixed, keep the experiment open and scope follow-up variants instead of forcing an ADR prematurely.

## Open Questions

1. Which current prompt components are immutable vs negotiable?
2. What is the right per-task token budget target by task archetype?
3. Should doctrine/persona context be summarized dynamically or loaded from precompiled condensed artifacts?

## Reference Directives

- `doctrine_ref/directives/002_context_notes.md` (phased loading and offload discipline)
- `doctrine_ref/directives/008_artifact_templates.md` (artifact-template and path-reference strategy)
- `doctrine_ref/directives/014_worklog_creation.md` (work-log structure for reflection loop)
- `doctrine_ref/directives/015_store_prompts.md` (prompt SWOT practice)
- `doctrine_ref/directives/037_context_aware_design.md` (bounded-context and search-path narrowing)
