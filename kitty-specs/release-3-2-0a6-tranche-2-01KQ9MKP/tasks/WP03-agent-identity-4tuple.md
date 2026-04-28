---
work_package_id: WP03
title: Agent identity 4-tuple parser (#833)
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-007
planning_base_branch: release/3.2.0a6-tranche-2
merge_target_branch: release/3.2.0a6-tranche-2
branch_strategy: lane-based
subtasks:
- T013
- T014
- T015
- T016
- T017
history:
- at: '2026-04-28T09:30:00Z'
  by: spec-kitty.tasks
  note: Created as part of tranche-2 specify→plan→tasks pipeline
authoritative_surface: src/specify_cli/status/wp_metadata.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/wp_metadata.py
- tests/specify_cli/status/test_wp_metadata_resolved_agent.py
- tests/integration/test_agent_identity_prompt.py
tags: []
---

# WP03 — Agent identity 4-tuple parser (#833)

## Branch Strategy

- **Planning/base branch**: `release/3.2.0a6-tranche-2`
- **Final merge target**: `release/3.2.0a6-tranche-2`
- Lane C, position 1 (WP04 follows in the same lane). Implementation command: `spec-kitty agent action implement WP03 --agent claude`.

## Objective

`WPMetadata.resolved_agent()` parses every supported colon arity of the `--agent` string into the `(tool, model, profile_id, role)` 4-tuple without silent discard, and the implement/review prompt-render path surfaces all four fields to the rendered prompt context.

## Context

GitHub issue #833. Today, passing `claude:opus-4-7:reviewer-default:reviewer` silently discards `model`, `profile_id`, and `role` — only `tool` survives. Every implement/review prompt for that WP runs with default model and default role, invisibly.

**FRs**: FR-005, FR-006, FR-007 · **NFR**: NFR-004 · **SC**: SC-003 · **Spec sections**: Scenario 3, Domain Language ("Resolved agent identity") · **Data shape**: [data-model.md §2](../data-model.md)

## Always-true rules

- Parsing is total — every supplied non-empty segment is preserved verbatim.
- Empty positional segments fall back to defaults; trailing missing segments fall back to defaults.
- The 4-tuple flows end-to-end through the prompt-render layer.

---

## Subtask T013 — Update `WPMetadata.resolved_agent()` parser

**Purpose**: Make the parser handle 1, 2, 3, and 4 segments with defaults filling any empty trailing positions.

**Steps**:

1. Open `src/specify_cli/status/wp_metadata.py` and locate `resolved_agent()`.
2. Replace the parser with the table from [data-model.md §2](../data-model.md):

   ```python
   def resolved_agent(self) -> tuple[str, str, str, str]:
       raw = self.agent or ""
       segments = raw.split(":")
       # Pad to 4 segments with empty strings.
       while len(segments) < 4:
           segments.append("")

       tool, model, profile_id, role = segments[:4]
       if not tool:
           raise ValueError(f"Empty agent string for WP {self.wp_id}")

       defaults = _agent_defaults(tool)  # existing helper or inline
       return (
           tool,
           model or defaults.model,
           profile_id or defaults.profile_id,
           role or "implementer",
       )
   ```
3. Add a helper `_agent_defaults(tool: str) -> _AgentDefaults` (or reuse an existing one) that returns the registry's current defaults.
4. Type-annotate the return as `tuple[str, str, str, str]`. If a downstream caller expects a different shape (e.g., a NamedTuple), define one and return it consistently.

**Files to edit**:
- `src/specify_cli/status/wp_metadata.py`

**Acceptance**:
- `mypy --strict` passes.
- The function is total: any non-empty `tool` produces a complete 4-tuple.

---

## Subtask T014 — Document defaults table for missing fields

**Purpose**: Make the fallback rules visible and stable.

**Steps**:

1. In the docstring of `resolved_agent()`, include the defaults table (verbatim from data-model.md §2):
   ```
   tool                              -> (tool, default_model, default_profile_id, "implementer")
   tool:model                        -> (tool, model,         default_profile_id, "implementer")
   tool:model:profile_id             -> (tool, model,         profile_id,         "implementer")
   tool:model:profile_id:role        -> (tool, model,         profile_id,         role)
   ```
2. Note: empty positional segments (e.g., `tool::profile_id:role`) fall back to the corresponding default.
3. Reference issue #833 in the docstring.

---

## Subtask T015 — Wire 4-tuple through implement/review prompt context

**Purpose**: Ensure `model`, `profile_id`, `role` actually reach the rendered prompt.

**Steps**:

1. Identify the prompt-render call site that consumes `resolved_agent()`. Likely entry point: `src/specify_cli/cli/commands/agent/workflow.py` (do **not** re-architect this file in WP03; only confirm the 4-tuple unpacks correctly).
2. If the consumer pulls only `tool` and silently ignores the rest, update the unpack to bind all four fields and pass them into the template/context dict used by the prompt renderer.
3. **Avoid scope creep into WP04's surface.** WP04 owns the review-cycle paths in the same file. Confine your edits in `workflow.py` to the smallest change that flows the 4-tuple to the renderer. Mark the touched lines clearly.

**Files to edit**:
- `src/specify_cli/cli/commands/agent/workflow.py` (small, focused — flag for WP04 reviewer)

**Note**: the file `cli/commands/agent/workflow.py` is owned by WP04 in this tranche. WP03's edit there is a narrow surgical change (consume the new tuple shape) that WP04 must not undo. Coordinate via the dependency declaration (`WP04 dependencies: ["WP03"]`).

---

## Subtask T016 — Unit tests at every arity  [P]

**Purpose**: Lock in the parser contract.

**Steps**:

1. Create `tests/specify_cli/status/test_wp_metadata_resolved_agent.py`.
2. Tests:
   - `test_one_segment_uses_all_defaults`: `agent="claude"` → `("claude", default_model, default_profile_id, "implementer")`.
   - `test_two_segments_preserves_model`: `agent="claude:opus-4-7"` → `("claude", "opus-4-7", default_profile_id, "implementer")`.
   - `test_three_segments_preserves_profile`: `agent="claude:opus-4-7:reviewer-default"` → `("claude", "opus-4-7", "reviewer-default", "implementer")`.
   - `test_four_segments_preserves_role`: `agent="claude:opus-4-7:reviewer-default:reviewer"` → `("claude", "opus-4-7", "reviewer-default", "reviewer")`.
   - `test_empty_positional_segment_falls_back`: `agent="claude::reviewer-default:reviewer"` → `("claude", default_model, "reviewer-default", "reviewer")`.
   - `test_trailing_empty_segments_fall_back`: `agent="claude:opus-4-7:::"` → `("claude", "opus-4-7", default_profile_id, "implementer")`.
   - `test_empty_tool_raises`: `agent=":opus-4-7"` raises `ValueError`.

**Files to create**:
- `tests/specify_cli/status/test_wp_metadata_resolved_agent.py` (~120 lines)

---

## Subtask T017 — Integration test: rendered prompt contains supplied identity

**Purpose**: Prove the wiring all the way to the generated prompt.

**Steps**:

1. Create `tests/integration/test_agent_identity_prompt.py`.
2. Test body:
   - Set up a minimal mission + WP with `agent="claude:opus-4-7:reviewer-default:reviewer"`.
   - Trigger the implement-prompt render path (use the existing test helper for prompt generation).
   - Assert the rendered prompt contains the strings `opus-4-7`, `reviewer-default`, and `reviewer`.
   - Add a partial-string case: `agent="claude:opus-4-7"`. Assert the rendered prompt contains `opus-4-7` and the documented default `profile_id` / `role`.
3. If the render path is hard to invoke from a unit-style test, use the existing CLI runner fixture and inspect the generated prompt file under the test's `tmp_path`.

**Files to create**:
- `tests/integration/test_agent_identity_prompt.py` (~90 lines)

---

## Test Strategy

- **Unit**: T016 hits every parser arity and the empty-tool error case.
- **Integration**: T017 proves the wiring to the prompt renderer.
- **Coverage**: ≥ 90% on `resolved_agent()` (NFR-002).
- **Type safety**: `mypy --strict` clean.

## Definition of Done

- [ ] T013 — parser updated and total at every arity.
- [ ] T014 — docstring records the defaults table and references #833.
- [ ] T015 — the 4-tuple flows into prompt rendering.
- [ ] T016 — unit tests pass at every arity + edge cases.
- [ ] T017 — integration test passes for full and partial inputs.
- [ ] `mypy --strict` clean on touched modules.
- [ ] No silent fallback to default `model`/`profile_id`/`role` when the input supplies them.

## Risks

- **Risk**: Existing partial-string callers depend on the current silent discard.
  **Mitigation**: This change is strictly additive for partial inputs (still defaults to the same values). Only 4-arity inputs see new behavior. NFR-004 regression tests at every arity.
- **Risk**: Edits to `cli/commands/agent/workflow.py` collide with WP04.
  **Mitigation**: WP04 declares `dependencies: ["WP03"]` so they execute serially in the same lane. Keep WP03's edit in `workflow.py` minimal and clearly scoped.

## Reviewer guidance

- Verify the parser is total (every input shape produces a 4-tuple or raises with a clear error).
- Confirm `model`, `profile_id`, `role` reach the rendered prompt — read the integration test assertions carefully.
- Verify no caller of `resolved_agent()` was silently broken by the new return shape.

## Out of scope

- Migrating to a JSON-encoded `--agent` flag.
- Changing the agent registry or the per-tool defaults themselves.
- WP04's review-cycle counter changes.
