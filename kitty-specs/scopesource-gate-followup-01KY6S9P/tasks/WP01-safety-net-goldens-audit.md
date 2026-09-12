---
work_package_id: WP01
title: 'Safety net: behavior-preservation goldens + sole-caller audit'
dependencies: []
requirement_refs:
- FR-002
- NFR-001
- NFR-006
- NFR-007
planning_base_branch: fix/scopesource-gate-followup
merge_target_branch: fix/scopesource-gate-followup
branch_strategy: Planning artifacts for this mission were generated on fix/scopesource-gate-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/scopesource-gate-followup unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-scopesource-gate-followup-01KY6S9P
base_commit: 7081cf0537c6d2b7cddde3b1bd3c09be2dc61e41
created_at: '2026-07-23T12:13:39.644150+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Safety net
history:
- at: '2026-07-23T10:19:53Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/review/
create_intent:
- tests/review/test_pre_review_gate_sole_caller_audit.py
execution_mode: code_change
model: ''
owned_files:
- tests/review/fixtures/parity/**
- tests/review/test_transition_gate_parity.py
- tests/review/test_pre_review_gate_sole_caller_audit.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2873'
---

# Work Package Prompt: WP01 – Safety net: behavior-preservation goldens + sole-caller audit

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` (`implement`) and `authoritative_surface` (`tests/review/`).

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below)
before starting. Address all feedback before completion.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in fenced code blocks.

---

## Objectives & Success Criteria

**This WP is the mission's load-bearing safety net. Nothing is deleted anywhere until this WP is green
and committed.** It adopts the EXISTING canonical parity harness — never an improvised snapshot — to
freeze the live gate's behavior against the pinned base `eb06ca176`, and characterizes the falsifiable
precondition for the WP04 deletion.

Complete when:

- **`tests/review/fixtures/parity/_capture.py` is re-pinned to `eb06ca176`.** The harness currently
  asserts `git rev-parse HEAD == e4ef6e850` (the half-A base) in `_require_base_commit`
  (`_capture.py:50-60`). Change that authorized base SHA to **`eb06ca176`** and regenerate. The
  machine-emitted `base_commit` field must read `eb06ca176`; a hand-typed SHA anywhere else is forbidden
  (the harness already rejects it — keep that guard).
- **NFR-001 registry-path golden captured** (T002): every reachable `GateOutcome` scenario × the
  `block_enabled`/`force` matrix, via the live `_mt_run_pre_review_gate` / registry hook, `HEAD==base`
  asserted at capture, committed under `tests/review/fixtures/parity/`.
- **NFR-006 override-tier golden captured** (T003) driving a **non-empty** derived scope, so
  `_mt_pre_review_gate_with_override_scope → evaluate_with_scope → run_scoped_tests_at_head` actually
  execute (not the empty-scope short-circuit). A vacuous (empty-scope) override golden FAILS this WP.
- **`test_transition_gate_parity.py` replays both golden sets** (T004) and is green on `eb06ca176`.
- **Sole-live-caller audit** (T005): a green-on-base characterization test proving the `scope_source is
  None` census branch of `evaluate_pre_review_gate` is the ONLY live caller reaching it without a
  `scope_source` — the load-bearing precondition that makes WP04's "no coverage lost" falsifiable.

Requirements covered: **NFR-001, NFR-006, NFR-007** (capture halves); **FR-002** (audit half). This WP is
the carrier for IC-00 and IC-01.

## Context & Constraints

- **Charter**: [`.kittify/charter/charter.md`](../../../.kittify/charter/charter.md) — canonical-sources
  (use the existing harness, do NOT hand-roll a golden), ATDD-first.
- **Design authorities**: [plan.md IC-00/IC-01](../plan.md), [spec.md NFR-001/006/007 + FR-002](../spec.md),
  [data-model.md §6 "Sole-live-caller audit"](../data-model.md), [post-plan-squad.md B-golden / B-vacuous / IC-01-reword](../reviews/post-plan-squad.md).
- **Why canonical (B-golden)**: an implementer who snapshots HEAD *after* the deletion builds a circular
  oracle. The harness's `HEAD==base` assert forbids it; adopting it is non-negotiable (NFR-007).
- **Why non-empty (B-vacuous)**: `run_scoped_tests_at_head`/`evaluate_with_scope` only execute on a
  non-empty scope; a golden that never drives one degrades "functional preservation" to an import check.
- **The sole-live-caller path** (data-model §6): live for_review is `_mt_dispatch_one_gate` →
  `gate_registry.get_gate_handler("spec-kitty-pre-review").run(ctx)` → `_spec_kitty_pre_review_handler`
  (`gate_registry.py:99-114`) → `evaluate_pre_review_gate(scope_source=ctx.scope_source)` — always
  non-`None`. `_mt_pre_review_gate_verdict` (the only census-branch caller) has NO production call site.
- **Quality bars (NFR-002)**: `mypy --strict` + `ruff` zero issues; complexity ≤15. Do NOT add `# noqa` /
  `# type: ignore`.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership; each hot file owned by exactly one WP)
- **Planning base branch**: `fix/scopesource-gate-followup`
- **Merge target branch**: `fix/scopesource-gate-followup`

> Populated by `spec-kitty agent mission tasks`. Do NOT change manually.

## Subtasks & Detailed Guidance

### Subtask T001 – Re-pin the harness to `eb06ca176` and extend it for override-tier capture

- **Purpose**: Make the canonical harness authoritative for THIS mission's base, and able to emit the
  override-tier golden NFR-006 needs.
- **Files**: `tests/review/fixtures/parity/_capture.py` AND `tests/review/test_transition_gate_parity.py`
  (both owned). **There are TWO independent `e4ef6e850` pins — re-pin BOTH** (post-plan squad renata-M1):
- **Steps**:
  1. In `_capture.py` change **both** base-SHA constants at module scope — `BASE_COMMIT` (`:46`, full
     40-char) and `_BASE_SHORT` (`:47`) — from `e4ef6e850` to **`eb06ca176`** (they sit ABOVE the
     `_require_base_commit` function at `:50`, not inside it). Keep the loud `SystemExit`-on-mismatch
     behavior in `_require_base_commit` verbatim — it is the anti-circular-oracle guard. Update the
     docstring references (`_capture.py:10,12,21,22,54`).
  2. In the **replay carrier** `test_transition_gate_parity.py` re-pin its OWN independent `BASE_COMMIT`
     constant (`:61`) + docstrings (`:4,:11`) to `eb06ca176` — otherwise
     `test_fixture_provenance_is_machine_emitted_base_commit` (`:157-160`, which asserts `case["base_commit"]
     == BASE_COMMIT`) goes RED once T002/T003 regenerate fixtures carrying `base_commit=eb06ca176`.
  3. **Gate**: `grep -rn e4ef6e850 tests/review/fixtures/parity/_capture.py tests/review/test_transition_gate_parity.py`
     MUST return zero hits before capturing.
  4. Add an **override-tier scenario generator** alongside the existing registry-path scenarios: capture
     the verdict/metadata tuple produced through `_mt_pre_review_gate_with_override_scope →
     evaluate_with_scope(scope_source=None)` with a frontmatter `pre_review_test_scope` (or config
     override) that resolves to a **non-empty** derived scope. Emit its fixtures under a distinct name
     prefix (e.g. `override_nonempty__block{0,1}__force{0,1}.json`) so registry and override goldens do
     not collide.
- **Notes**: this is *extension*, not redesign — reuse the existing serialization (`_capture.py:230-290`)
  and `capture(out_dir)` loop (`:302-320`). Keep every function ≤15 complexity; extract a small
  override-scenario builder if needed.

### Subtask T002 – Capture the NFR-001 registry-path golden

- **Purpose**: Freeze the live for_review verdict for every reachable `GateOutcome` before any deletion.
- **Steps**: With `HEAD` checked out at `eb06ca176`, run the harness exactly as documented in its
  docstring (`_capture.py:24-25`), e.g.:
  ```bash
  PYTHONPATH=$(pwd)/src python tests/review/fixtures/parity/_capture.py --out tests/review/fixtures/parity
  ```
  Confirm the regenerated fixtures carry `"base_commit": "eb06ca176…"` (machine-emitted). Commit them.
- **Notes**: The existing scenarios (`new_failures`, `no_coverage`, `no_new_failures`,
  `unverified_baseline`, `cancelled`, `timed_out`, `shard_scope_no_new_failures`) are registry-path — they
  regenerate. Do NOT hand-edit fixture JSON.

### Subtask T003 – Capture the NFR-006 override-tier golden (NON-EMPTY scope)

- **Purpose**: Cover the kept override tier NFR-001 does not exercise, and prove the C-002 keep-live set
  runs — not merely imports.
- **Steps**: Generate the `override_nonempty__*` fixtures from T001's override scenario. Verify the case
  drives a **non-empty** scope (assert in T004's replay that `run_scoped_tests_at_head` executed — e.g. a
  non-empty `scope.test_targets` in the captured metadata). Commit.
- **Notes**: If the override scenario short-circuits to the empty-scope path, the golden is vacuous and
  this WP is NOT done — adjust the scenario's changed-file inputs until the derived scope is non-empty.

### Subtask T004 – Wire the replay carrier

- **Purpose**: A committed, runnable replay that re-derives each verdict at HEAD and asserts byte-equality
  with the pinned golden — the guard WP04 must keep green after the deletion.
- **File**: `tests/review/test_transition_gate_parity.py` (owned).
- **Steps**: Extend the existing replay to load BOTH the registry-path and the new `override_nonempty__*`
  fixtures and assert the reconstructed verdict/metadata tuple matches. Add an explicit assertion that the
  override case's captured scope is non-empty (guards against a future vacuous regeneration).
- **Run**: `PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_transition_gate_parity.py -q`.

### Subtask T005 – Sole-live-caller characterization test (green-on-base)

- **Purpose**: Prove (green on `eb06ca176`) the census `scope_source is None` branch is the only live
  caller reaching `evaluate_pre_review_gate` without a source — the WP04 deletion's precondition.
- **File (create)**: `tests/review/test_pre_review_gate_sole_caller_audit.py` (owned, `create_intent`).
- **Steps**: Assert structurally that (a) the registry handler `_spec_kitty_pre_review_handler`
  (`gate_registry.py:99-114`) calls `evaluate_pre_review_gate` with a non-`None` `scope_source`; (b)
  `_mt_pre_review_gate_verdict` (`tasks_move_task.py:1061`) is the only symbol that reaches the census
  branch, and it has no production call site (grep-assert: only the compat re-export in `tasks.py` and the
  compat-surface entry reference it). A code-search-based assertion (import the modules; inspect call
  graph or assert the grep result) is acceptable — the point is a *falsifiable, committed* precondition.
- **Label it a characterization precondition, NOT red-first** (post-plan MINOR): it asserts a property
  already true on base; it is green from the start. Note this in the Activity Log.

## Test Strategy

- **Order**: T001 → T002/T003 (capture) → T004 (replay) → T005 (audit, independent).
- **Run**:
  ```bash
  PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_transition_gate_parity.py tests/review/test_pre_review_gate_sole_caller_audit.py -q
  ```
- **Verify base**: `git rev-parse HEAD` must equal `eb06ca176` while capturing (the harness enforces it).
- **Quality**: `ruff check tests/review/fixtures/parity/_capture.py tests/review/test_pre_review_gate_sole_caller_audit.py` and `mypy --strict` zero-issue.

## Risks & Mitigations

- **Circular oracle** (capturing post-deletion): the `HEAD==base` assert forbids it — never bypass it.
- **Vacuous override golden**: T003's scope must be non-empty; T004 asserts it.
- **Harness drift**: only re-pin the SHA + add the override scenario; do not restructure the serializer.

## Review Guidance

- `_require_base_commit` pins `eb06ca176`; fixtures carry the machine-emitted `base_commit`.
- Override golden drives a non-empty scope (replay asserts it); registry golden covers the reachable
  `GateOutcome` members.
- Audit test is green-on-base and labeled a characterization precondition.
- Zero `# noqa` / `# type: ignore`; complexity ≤15.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append at
> the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-07-23T10:19:53Z – system – Prompt created.

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP01 --to <status>`.
