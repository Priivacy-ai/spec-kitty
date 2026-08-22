---
work_package_id: WP09
title: agent status emit --review-result-json + --help + parity
dependencies:
- WP08
requirement_refs:
- FR-010
- FR-012
- FR-013
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
phase: Phase 2 - Verdict CLI parity
history:
- at: '2026-08-18T21:17:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/status.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_emit_review_result.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/status.py
- tests/specify_cli/cli/commands/agent/test_emit_review_result.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – agent status emit --review-result-json + --help + parity

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Close the review-verdict CLI-parity gap so `agent status emit` can drive a WP through the `in_review` exit with a **structured** verdict — using the **same** validator the orchestrator surface uses (hoisted in WP08).

Done when:
- `agent status emit` accepts `--review-result-json` and validates it via the WP08-hoisted `_parse_review_result_json` (single validator — no second copy).
- The parsed `review_result` is threaded into the `TransitionRequest`.
- A WP walks `in_progress → for_review → in_review → approved → done` through `agent status emit` **alone**.
- The misleading `--help` verdict example is corrected.
- The `in_review → approved` guard admits the `ReviewResult` path on the emit surface (parity with `orchestrator-api transition`, FR-013).
- A red-first `@pytest.mark.regression` test (issue #3547 / #1734) is authored and shown failing on base, green after.

## Context & Constraints

- Spec: [spec.md](../spec.md) FR-010/FR-012/FR-013, SC-004. Contracts: [C-6](../contracts/resolver-and-verdict-contracts.md).
- Charter: `.kittify/charter/charter.md` (single-canonical-authority — one validator; zero-issue ruff/mypy; complexity ≤15).
- **Depends on WP08**, which hoists `_parse_review_result_json` → `status/review_result_parse.py` and the `for_review` gate → `lanes/for_review_gate.py`. Import the parser from its hoisted home; do **not** reintroduce a local copy.
- Verified base anchors: emit params `cli/commands/agent/status.py:223-264`; `TransitionRequest(...)` built without `review_result` at `:317-332`; misleading `--help` example at `:274` (routes a verdict into `--evidence-json`).
- **No out-of-map edit needed**: `TransitionRequest.review_result` **already exists** (`status/models.py`) and is already consumed by the shared emit path (`status/emit.py`, `status/aggregate.py`, `reducer.py`) and the `in_review→approved` guard (`status/wp_state.py`). This WP stays entirely within `cli/commands/agent/status.py`: add the `--review-result-json` option, import the WP08-hoisted parser, and set `review_result=` on the `TransitionRequest` this file already builds at `:317`. No edit to `orchestrator_api/commands.py` (WP08's file) is required.

## Branch Strategy

- **Strategy**: coord-lane
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Populated by `spec-kitty agent mission tasks`. Do NOT change manually.

## Subtasks & Detailed Guidance

### Subtask T026 – Red-first: emit cannot exit in_review on base

- **Purpose**: Prove the gap through the real CLI before fixing it (NFR-001).
- **Steps**:
  1. Create `tests/specify_cli/cli/commands/agent/test_emit_review_result.py`.
  2. Write `@pytest.mark.regression` test pinned to #3547/#1734 that builds a mission with a WP in `in_review` and attempts to advance it to `approved` via `spec-kitty agent status emit` with a structured verdict.
  3. On base this must be **RED**: there is no `--review-result-json`, so the verdict cannot be supplied and the transition cannot carry it.
- **Files**: `tests/specify_cli/cli/commands/agent/test_emit_review_result.py` (new).
- **Validation**: `pytest -k regression and emit_review_result` is red on base, green after T027–T029.

### Subtask T027 – Add --review-result-json, validate via hoisted parser, thread into TransitionRequest

- **Purpose**: Give `emit` a structured verdict input validated identically to the orchestrator surface.
- **Steps**:
  1. Add a `--review-result-json` typer option to the emit command (near the params at `status.py:223-264`).
  2. Parse/validate it via the WP08-hoisted `_parse_review_result_json` (import from `specify_cli.status.review_result_parse`). Do not hand-roll JSON parsing.
  3. Thread the resulting `review_result` into the `TransitionRequest` constructed at `:317-332`.
  4. Reject a malformed verdict with the same error shape both surfaces use.
- **Files**: `src/specify_cli/cli/commands/agent/status.py`.
- **Validation**: an emit-only walk `in_progress → for_review → in_review → approved → done` succeeds; malformed JSON is rejected consistently.

### Subtask T028 – Correct the misleading --help example

- **Purpose**: Stop documenting a non-functional path (FR-012).
- **Steps**:
  1. Replace the `--help` example at `status.py:274` that routes a verdict into `--evidence-json` with the working `--review-result-json` example.
  2. Ensure no remaining help text implies a verdict can travel via `--evidence-json`.
- **Files**: `src/specify_cli/cli/commands/agent/status.py`.
- **Validation**: a `--help` snapshot test asserts the working example is present and the misleading one is gone.

### Subtask T029 – Admit ReviewResult path on in_review→approved (parity)

- **Purpose**: FR-013 — the guard must accept the `ReviewResult` path on the emit surface, matching `orchestrator-api transition`.
- **Steps**:
  1. Ensure the emit transition path presents the `review_result` to the same `in_review → approved` guard used by the orchestrator surface.
  2. Confirm no emit-specific bypass or divergent guard remains.
- **Files**: `src/specify_cli/cli/commands/agent/status.py`.
- **Validation**: the parity test asserts identical acceptance/rejection on both surfaces for the same verdict + state.

## Test Strategy (required)

- `tests/specify_cli/cli/commands/agent/test_emit_review_result.py`: red-first #3547/#1734 regression; the full emit-only lifecycle walk; a `--help` snapshot assertion; a parity assertion (emit vs transition) reusing WP08's gate.
- Run: `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_emit_review_result.py -q`. Confirm red on `upstream/main` (author-then-fix), green on branch.

## Risks & Mitigations

- **Duplicate validator drift**: importing a copy instead of the hoisted parser defeats parity. Mitigation: import from `specify_cli.status.review_result_parse`; add an assertion that both surfaces reference the same callable.
- **WP08 not yet landed**: this WP depends on WP08. Do not start the transition-threading subtasks until WP08's parser/gate are on the coord branch; rebase after WP08.

## Review Guidance

- Confirm one validator (no second JSON parser). Confirm the emit-only walk reaches `done`. Confirm `--help` has no `--evidence-json` verdict example. Confirm the parity test exercises both surfaces.

## Activity Log

- 2026-08-18T21:17:46Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP09 --to <status>`.
