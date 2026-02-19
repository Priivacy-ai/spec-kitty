---
work_package_id: WP04
title: Cost Tracking and Pricing Table
lane: "done"
dependencies:
- WP01
base_branch: feature/doctrine-kitty-2x
base_commit: a3505ae86accdeb8991e664f58da7942909cc00f
created_at: '2026-02-15T20:23:50.129546+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 2 - Core Integration
assignee: ''
agent: copilot
shell_pid: '503611'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T19:43:21Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Cost Tracking and Pricing Table

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

Depends on WP01 (SimpleJsonStore). Can run in parallel with WP02 and WP03.

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Ship a default YAML pricing table with rates for major LLM providers
- Implement `PricingTable` loader that reads the YAML
- Implement `cost_summary()` that aggregates ExecutionEvents by agent/model/feature
- When `cost_usd` is null but tokens are present, estimate cost from pricing table
- When `cost_usd` is explicit, use it over the estimate
- Unknown models return 0.0 cost with an "unknown model" flag
- Cost aggregation matches manual calculation within rounding tolerance (0.01 USD)
- 90%+ test coverage

## Context & Constraints

- **Spec**: FR-013 through FR-017 (cost tracking), User Stories 3 and 4
- **Plan**: pricing table co-located in `telemetry/` package
- **Data model**: `CostSummary` and `PricingTable` entities
- **Research**: R6 (pricing location decision)
- **Constitution**: pricing overrides from constitution deferred to Feature 045

## Subtasks & Detailed Guidance

### Subtask T019 – Create default pricing YAML

- **Purpose**: Ship current LLM model pricing so cost estimation works out of the box.
- **Steps**:
  1. Create `src/specify_cli/telemetry/_pricing.yaml`:
     ```yaml
     # Default LLM pricing table
     # Prices in USD per 1,000 tokens
     # Last updated: 2026-02-15
     #
     # Project-specific overrides will be configurable via constitution (Feature 045)
     models:
       # Anthropic Claude
       claude-sonnet-4-20250514:
         input_per_1k: 0.003
         output_per_1k: 0.015
       claude-opus-4-20250514:
         input_per_1k: 0.015
         output_per_1k: 0.075
       claude-haiku-3-5-20241022:
         input_per_1k: 0.0008
         output_per_1k: 0.004

       # OpenAI GPT
       gpt-4.1:
         input_per_1k: 0.002
         output_per_1k: 0.008
       gpt-4.1-mini:
         input_per_1k: 0.0004
         output_per_1k: 0.0016
       gpt-4.1-nano:
         input_per_1k: 0.0001
         output_per_1k: 0.0004

       # Google Gemini
       gemini-2.5-pro:
         input_per_1k: 0.00125
         output_per_1k: 0.01
       gemini-2.5-flash:
         input_per_1k: 0.00015
         output_per_1k: 0.0035
     ```
  2. Use current market rates at time of implementation (the above are estimates — verify before committing)
- **Files**: `src/specify_cli/telemetry/_pricing.yaml` (new)
- **Notes**: The `_` prefix follows the convention from `sync/_events_schema.json` for package-internal data files. YAML chosen over JSON for human readability and comments.

### Subtask T020 – Implement PricingTable loader

- **Purpose**: Load and cache the pricing YAML for cost estimation.
- **Steps**:
  1. Create `src/specify_cli/telemetry/cost.py`
  2. Implement:
     ```python
     _PRICING_PATH = Path(__file__).resolve().parent / "_pricing.yaml"
     _pricing_cache: dict[str, dict[str, float]] | None = None

     def load_pricing_table() -> dict[str, dict[str, float]]:
         """Load model pricing table. Returns {model_id: {input_per_1k, output_per_1k}}."""
         global _pricing_cache
         if _pricing_cache is not None:
             return _pricing_cache
         if not _PRICING_PATH.exists():
             logger.warning("Pricing table not found: %s", _PRICING_PATH)
             _pricing_cache = {}
             return _pricing_cache
         with open(_PRICING_PATH, encoding="utf-8") as f:
             data = yaml.safe_load(f)
         _pricing_cache = data.get("models", {})
         return _pricing_cache
     ```
  3. Use `import yaml` (PyYAML — already a dependency via `ruamel.yaml` or standard `pyyaml`)
  4. Module-level cache avoids re-reading the file on every cost query
- **Files**: `src/specify_cli/telemetry/cost.py` (new, ~30 lines initially)
- **Notes**: Check which YAML library is available. `ruamel.yaml` is in the constitution dependencies but `pyyaml` (`import yaml`) may also be available. Use whichever is standard in the project. If `ruamel.yaml` is preferred, use `from ruamel.yaml import YAML; yaml = YAML(); yaml.load(f)`.

### Subtask T021 – Implement cost_summary() aggregation

- **Purpose**: Aggregate ExecutionEvents into per-group cost summaries.
- **Steps**:
  1. In `cost.py`, define `CostSummary` dataclass:
     ```python
     @dataclass
     class CostSummary:
         group_key: str          # Agent name, model ID, or feature slug
         group_by: str           # "agent", "model", or "feature"
         total_input_tokens: int
         total_output_tokens: int
         total_cost_usd: float   # Reported + estimated
         estimated_cost_usd: float  # Portion that was estimated
         event_count: int

         def to_dict(self) -> dict[str, Any]:
             return {
                 "group_key": self.group_key,
                 "group_by": self.group_by,
                 "total_input_tokens": self.total_input_tokens,
                 "total_output_tokens": self.total_output_tokens,
                 "total_cost_usd": round(self.total_cost_usd, 6),
                 "estimated_cost_usd": round(self.estimated_cost_usd, 6),
                 "event_count": self.event_count,
             }
     ```
  2. Implement:
     ```python
     def cost_summary(
         events: list[Event],
         group_by: str = "agent",  # "agent" | "model" | "feature"
     ) -> list[CostSummary]:
     ```
  3. Group events by the `group_by` key:
     - `"agent"`: `event.payload.get("agent", "unknown")`
     - `"model"`: `event.payload.get("model", "unknown")`
     - `"feature"`: `event.aggregate_id`
  4. For each group, sum `input_tokens`, `output_tokens`, `cost_usd`, count events
  5. Handle None token values (treat as 0)
  6. Sort summaries by `total_cost_usd` descending (most expensive first)
  7. Return list of `CostSummary`
- **Files**: `src/specify_cli/telemetry/cost.py` (modify, ~60 lines added)

### Subtask T022 – Add cost estimation from pricing table

- **Purpose**: When an event has tokens but no cost, estimate using the pricing table.
- **Steps**:
  1. In `cost_summary()`, for each event:
     ```python
     cost = event.payload.get("cost_usd")
     estimated = 0.0
     if cost is None:
         # None = not reported by agent → estimate from pricing table
         # Note: 0.0 means "explicitly free" and is NOT estimated
         model = event.payload.get("model")
         input_tokens = event.payload.get("input_tokens") or 0
         output_tokens = event.payload.get("output_tokens") or 0
         if model and model in pricing:
             rates = pricing[model]
             estimated = (
                 (input_tokens / 1000) * rates["input_per_1k"]
                 + (output_tokens / 1000) * rates["output_per_1k"]
             )
             cost = estimated
         else:
             cost = 0.0  # Unknown model
     ```
  2. Track `estimated_cost_usd` separately in each group's running total
  3. Call `load_pricing_table()` once at the start of `cost_summary()`
  4. FR-017: if `cost_usd` is explicitly set (not None, not 0.0), use it — do NOT override with estimate
- **Files**: `src/specify_cli/telemetry/cost.py` (modify, ~20 lines added)
- **Notes**: Use `round(value, 6)` for intermediate calculations. Final display (in CLI) rounds to 4 decimals.

### Subtask T023 – Write unit tests for cost aggregation

- **Purpose**: Verify aggregation correctness, estimation, and edge cases.
- **Steps**:
  1. Create `tests/specify_cli/telemetry/test_cost.py`
  2. Test cases:
     - **test_cost_summary_by_agent**: 4 events for 2 agents, verify per-agent totals
     - **test_cost_summary_by_model**: Events with different models, verify model grouping
     - **test_cost_summary_by_feature**: Events from different features (different `aggregate_id`), verify feature grouping
     - **test_explicit_cost_used**: Event with `cost_usd=0.15`, verify 0.15 used (not estimated)
     - **test_estimated_cost_from_pricing**: Event with tokens but `cost_usd=None`, verify estimate matches manual calculation
     - **test_zero_cost_not_estimated**: Event with `cost_usd=0.0` (explicitly free), verify 0.0 used (not estimated from pricing table)
     - **test_unknown_model_zero_cost**: Event with unknown model, verify cost=0.0
     - **test_empty_events**: Empty event list, verify empty summary
     - **test_none_tokens_treated_as_zero**: Event with `input_tokens=None`, verify treated as 0
     - **test_sort_by_cost_descending**: Multiple groups, verify sorted by cost
     - **test_pricing_table_loads**: Verify `load_pricing_table()` returns non-empty dict with expected models
  3. Use helper to create events with specific payload values
- **Files**: `tests/specify_cli/telemetry/test_cost.py` (new, ~130 lines)
- **Notes**: For the pricing table test, assert that at least the Anthropic and OpenAI models are present. Don't hardcode exact rates (they may be updated).

## Risks & Mitigations

- **Stale pricing rates**: Document in `_pricing.yaml` header that rates are best-effort estimates. Constitution override path (Feature 045) will allow project-specific corrections.
- **Float precision**: Use `round(value, 6)` for all intermediate calculations. SC-004 requires accuracy within 0.01 USD tolerance.
- **YAML library**: Verify which YAML parser is available in the project. If both `pyyaml` and `ruamel.yaml` are present, prefer `pyyaml` (`import yaml`) for simplicity since we only need `safe_load`.

## Review Guidance

- Verify explicit `cost_usd` takes precedence over pricing table estimate (FR-017)
- Verify unknown models produce 0.0 cost (not an error)
- Verify `estimated_cost_usd` tracks only the estimated portion (not total)
- Verify sort order: most expensive group first
- Verify `_pricing.yaml` has reasonable rates for current models
- Run `mypy --strict src/specify_cli/telemetry/cost.py`

## Activity Log

- 2026-02-15T19:43:21Z – system – lane=planned – Prompt created.
- 2026-02-15T20:23:50Z – copilot – shell_pid=503611 – lane=doing – Assigned agent via workflow command
- 2026-02-15T20:55:37Z – copilot – shell_pid=503611 – lane=for_review – Implementation complete: PricingTable, CostSummary, cost_summary with estimation, 14 tests
- 2026-02-15T21:16:06Z – copilot – shell_pid=503611 – lane=done – Review passed: no issues, 29 tests pass
