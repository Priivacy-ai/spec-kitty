# Implementation Plan: Documentation Mission Composition Fix-up

**Branch**: `main` | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Predecessor**: mission `01KQ5M1Y190VANF39KMBWZP6SD` merged at commit `1c03e2f4`

## Summary

Three tightly scoped WPs close the 5 review findings. The substrate is unchanged; only the missing prompt templates, deeper integration coverage, corrected quickstart, and a real action-issuing smoke land.

## Technical Context

Same as predecessor mission. Python 3.13 via `uv run --python 3.13`. Test/lint commands unchanged. Composition substrate (`StepContractExecutor`) unchanged.

## Project Structure

```
src/specify_cli/missions/documentation/templates/   # NEW directory
├── discover.md          # NEW (WP-FIX-1 / T01)
├── audit.md             # NEW
├── design.md            # NEW
├── generate.md          # NEW
├── validate.md          # NEW
├── publish.md           # NEW
└── accept.md            # NEW

tests/integration/test_documentation_runtime_walk.py  # EDIT (WP-FIX-2 / T08-T11)
tests/specify_cli/test_documentation_prompt_resolution.py  # NEW (WP-FIX-1 / T08)

kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md  # EDIT (WP-FIX-3 / T12)
kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke-v2.md  # NEW (WP-FIX-3 / T13)
```

## Decisions

### D1 — Templates are governance prose, not host-LLM scripts

Each `<verb>.md` template is markdown that frames the action for the host LLM: 30-60 lines, mirroring the structure of `src/specify_cli/missions/research/templates/scoping.md` (or whichever research template exists; if research doesn't ship templates either, the implementer follows the same prose style as the predecessor's action-bundle `guidelines.md` files but more procedural). The template names match the runtime sidecar's `prompt_template:` declarations exactly.

**Why**: the runtime resolves `f"{action}.md"` and feeds the file's contents to the host LLM as the action prompt. An empty file would technically satisfy "non-null" but defeat the operator-runnable goal. Non-empty governance-prose markdown is the minimum useful payload.

### D2 — Integration walk uses `decide_next_via_runtime` exclusively for advancement

To prove FR-009 (no legacy-DAG fallback) and SC-003 (dispatch-level guard propagation), the new full-walk test calls `decide_next_via_runtime` (or its programmatic equivalent) 6 times in sequence — once per action — with happy-path artifacts authored progressively (write `spec.md`, advance, write `gap-analysis.md`, advance, etc.). After each advance, inspect the run snapshot to confirm `current_step` moved forward, and inspect the trail directory for the corresponding paired record.

**Why**: this exercises the live dispatch path end-to-end, which is exactly what the spec FR-013 / SC-004 require but the predecessor walk only spot-checked.

### D3 — Dispatch-level guard test asserts `Decision.kind == "blocked"`

For F-4 / FR-005, replace the direct `_check_composed_action_guard()` call with a `decide_next_via_runtime` call on an empty feature_dir. Assert: returned decision has `kind == "blocked"` (or equivalent), `guard_failures` (or `failures`) field non-empty and contains "spec.md", and the run snapshot before/after equal (no advancement).

**Why**: SC-003 explicitly names `_dispatch_via_composition()` as the surface that propagates the failure. Helper-level tests verify the helper, not the contract.

### D4 — Quickstart corrections, not rewrite

The quickstart's pseudocode at lines 47-56 is replaced with a tolerant parser that handles both `kind: query` (with `preview_step`) and `kind: success` (with `step_id`). The verbatim Python check is rewritten to use `d.get("step_id") or d.get("preview_step")` to avoid `KeyError`. No structural changes to the smoke command sequence.

### D5 — `smoke-v2.md` not `smoke.md`

The historical `smoke.md` records the F-2 finding and stays as evidence of what was wrong. The new evidence file is named `smoke-v2.md` and explicitly references its predecessor.

### D6 — Unknown-action test stays at helper level

`decide_next_via_runtime` doesn't expose an "inject arbitrary action verb" entry point — it picks the next action from the runtime template. So the unknown-action assertion (FR-017 from predecessor) cannot be lifted to dispatch level without surgery beyond this fix-up's scope. The helper-level assertion (predecessor walk's `test_unknown_documentation_action_fails_closed`) remains the only feasible coverage and is documented as such in the test docstring.

### D7 — Prompt-resolution unit test sits in `tests/specify_cli/`

The new test `test_documentation_prompt_resolution.py` lives in `tests/specify_cli/` (not `tests/integration/`) because it parametrizes over the 7 step ids and asserts `Decision.prompt_file is not None` via a programmatic runtime call — fast, mocking-free, and orthogonal to the integration walk's full dispatch.

## Premortem Risks

1. The runtime template's `prompt_template:` field may resolve via a different path than `resolve_command(...)`. Mitigation: the implementer reads the runtime resolution code in `src/specify_cli/next/runtime_bridge.py` and `_internal_runtime/engine.py` before authoring templates; if the resolution path is different, the templates land at the path the runtime actually checks.
2. The full-walk test may hit timeouts or non-determinism if the runtime persists state between actions in a way that surprises the test fixture. Mitigation: write happy-path artifacts before each `decide_next_via_runtime` call, and use the test's existing `isolated_repo` fixture pattern.
3. The smoke may fail to issue an action because `spec-kitty next` defaults to query mode unless the operator explicitly issues. Mitigation: read existing `spec-kitty next` flags (`--issue`? `--advance`? programmatic equivalent?) in the predecessor smoke transcript and the research walk to find the issue verb.

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Single mission branch + 1 lane (lane-a). All 3 WPs share the lane sequentially.

## Next command

`/spec-kitty.tasks` — already authored. See `tasks.md`.
