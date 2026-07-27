---
work_package_id: WP04
title: pre_review_gate deletion + SOURCE_MISMATCH + parity
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-009
- FR-010
- FR-011
- FR-013
- FR-014
- NFR-001
- NFR-002
- NFR-004
- NFR-006
planning_base_branch: fix/scopesource-gate-followup
merge_target_branch: fix/scopesource-gate-followup
branch_strategy: Planning artifacts for this mission were generated on fix/scopesource-gate-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/scopesource-gate-followup unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 4 - deletion + correctness hub
history:
- at: '2026-07-23T10:19:53Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- tests/review/test_pre_review_gate_source_mismatch.py
- tests/review/test_baseline_head_parity.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/pre_review_gate.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
- tests/review/test_pre_review_gate_source_mismatch.py
- tests/review/test_baseline_head_parity.py
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2873'
---

# Work Package Prompt: WP04 – pre_review_gate deletion + SOURCE_MISMATCH + parity

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter and behave per its guidance.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` before starting; address all feedback.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in fenced code blocks.

---

## Objectives & Success Criteria

The correctness + cleanup hub on `pre_review_gate.py` and the compat cluster. This WP is the highest-risk
cut (~450 LoC deletion + the SOURCE_MISMATCH outcome). It runs **only after WP01's goldens exist** — they
are the deletion's oracle.

Complete when:

- **Dead census tier deleted** (FR-001): the 12 symbols + the `scope_source is None` census branch of
  `evaluate_pre_review_gate` + its `filter_groups`/`composite_routing` params — the live private census
  copy in `scope_source.py` is UNTOUCHED.
- **`_mt_pre_review_gate_verdict` deleted atomically** (FR-002 / C-004): the helper + the `tasks.py`
  re-export + the `test_tasks_compat_surface.py` tuple entry + golden **157→156** + the docstring count —
  in ONE commit, never an accidental import break.
- **`isinstance` swapped for the two predicates** (FR-005) at `pre_review_gate.py:881` (empty ⇒
  `NO_COVERAGE`) and `:1013` (`_scope_result_from_source`).
- **Head path rewired onto the selective factory** (FR-014): `_mt_resolve_scope_source` delegates to
  WP02's `resolve_scope_source` (threading the kept seams) so head and baseline share ONE authority —
  asserted through the real wrapper (T024). Without this the head stays on `GateCoverageScopeSource` and
  every non-pytest review false-mismatches.
- **`GateOutcome.SOURCE_MISMATCH`** (FR-011) added as a warn-shaped, fail-open member; constructed in
  `_evaluate_via_scope_source` (FR-009) — which COMPARES an already-loaded baseline's `source_identity`
  (the load stays in `_mt_resolve_gate_baseline` via #2874's seam; do not move it).
- **Console ladder** gains an explicit `SOURCE_MISMATCH` branch + a `NO_NEW_FAILURES` branch + a defensive
  `else`; `verdict_aggregation` fail-open is ASSERTED (filters NOT edited).
- **Four-combination baseline↔head parity** (FR-010) + the SC-004 mismatch demo are green.
- **NFR-001/006 goldens replay byte-identical**; the C-002 keep-live set survives; `SYMBOL_TO_MODULE == 156`.

Requirements covered: **FR-001, FR-002, FR-005 (call-sites), FR-009 (assert), FR-010, FR-011, FR-013
(docs half)**; NFR-001/004/006 (guards). Carrier for IC-02, IC-06 (call-sites), IC-10, IC-11, IC-12.

## Context & Constraints

- **Design authorities**: [data-model.md §2 (SOURCE_MISMATCH), §6 (retire/keep), §7 (compat golden)](../data-model.md);
  [contracts/gate-outcome-contract.md](../contracts/gate-outcome-contract.md); [plan.md IC-02/06/10/11/12](../plan.md);
  [post-plan-squad.md IC-11-fail-open / .value-sites / dead-symbol-cross-module](../reviews/post-plan-squad.md).
- **DELETE — census tier (FR-001, data-model §6)** from `pre_review_gate.py`: `derive_test_scope` (`:324`),
  `_glob_matches_file` (`:231`), `_glob_to_pytest_target` (`:249`), `_src_dir_segment` (`:257`),
  `resolve_excluded_catchall_groups` (`:100`), `NAMED_CATCHALL_GROUPS` (`:96`), `_WHOLE_SRC_TREE_GLOB`
  (`:97`), `_live_filter_groups` (`:204`), `_live_composite_routing` (`:220`), `_SRC_PACKAGE_PREFIX`
  (`:110`), `_TESTS_PREFIX` (`:111`), `_EMPTY_COMPOSITE_ROUTE` (`:115`). Plus the `scope_source is None`
  census branch of `evaluate_pre_review_gate` (`:1104-1118`) and its `filter_groups`/`composite_routing`
  params + the `scope_source=None` default.
- **KEEP LIVE (C-002 — do NOT delete)**: `_CompositeRoute` (`:114`, referenced by the kept seam
  `pre_review_gate._CompositeRoute` at `tasks_move_task.py:845`), `evaluate_with_scope` (`:912`),
  `run_scoped_tests_at_head` (`:630`), `ScopeResult` + `from_override`/`describe_empty_reason`/`is_empty`
  (`:278-321`), `_mt_pre_review_gate_with_override_scope` (`tasks_move_task.py:994`), `_mt_empty_scope_verdict`
  (`tasks_move_task.py:1030`), `_pre_review_gate_filter_groups`/`_pre_review_gate_composite_routing`
  (`tasks_move_task.py:828-847`), `evaluate_pre_review_gate` itself (census branch removed). The private
  census copy in `scope_source.py` is UNTOUCHED. **The WP01 override golden is the guard the keep-live set
  runs, not just imports.**
- **Compat golden delta (C-004 / NFR-004, data-model §7)**: `test_tasks_compat_surface.py:479` `== 157` →
  `== 156` (keep the `# golden-count: cardinality-is-contract` marker); remove `"_mt_pre_review_gate_verdict"`
  from the `_TASKS_MOVE_TASK` tuple (`:249`); update the `tasks_move_task … = 76` → `= 75` docstring
  (`:153`); remove the `_mt_pre_review_gate_verdict as _mt_pre_review_gate_verdict` re-export (`tasks.py:448`).
  ONE atomic commit.
- **`SOURCE_MISMATCH` construction (data-model §2)**: in `_evaluate_via_scope_source` (`:851-909`), when
  `scope_source_identity(scope_source, raw)` (import from WP02) differs from a KNOWN (non-`"unknown"`)
  `baseline.source_identity`, return `GateVerdict(outcome=SOURCE_MISMATCH, scope=scope, reason="baseline
  captured under <a>; head ran under <b> — failure identities are not comparable")`. If `baseline is None`
  or its `source_identity == "unknown"`, degrade to the existing `UNVERIFIED_BASELINE` path
  (`_classify_current_failures` `:771-805`) — NOT a mismatch. **`_evaluate_via_scope_source` only COMPARES**
  a `BaselineTestResult` that is already loaded upstream by `_mt_resolve_gate_baseline`
  (`tasks_move_task.py:1282-1303`, which already consumes #2874's kind-aware
  `_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)` seam at `:1296`, def `workflow.py:573-587`) — do
  NOT add a baseline read inside `_evaluate_via_scope_source`, and do NOT reconstruct `feature_dir`; the
  new `source_identity` simply rides on the already-loaded result.
- **Fail-open by construction — ASSERT, do NOT edit (FR-011)**: `verdict_aggregation._TERMINAL_OUTCOMES =
  frozenset({TIMED_OUT, CANCELLED})` (`:58-60`) and the block predicate `blocking = (… v.outcome is
  GateOutcome.NEW_FAILURES)` (`:138`) are member allowlists; `SOURCE_MISMATCH` is absent from both → it
  routes to `WARN_PROCEED` automatically. Prove this with a test (SC-004); do NOT add `SOURCE_MISMATCH` to
  any filter.
- **Console ladder (the ONE live edit, data-model §2)**: `_mt_pre_review_gate_console_warning`
  (`tasks_move_task.py:1156-1184`) — add an explicit `SOURCE_MISMATCH` warn branch (name both identities);
  convert the trailing unconditional `return "[dim]…no new failures[/dim]"` (`:1184`) into an explicit
  `NO_NEW_FAILURES` branch; add a defensive `else` rendering `outcome.value` so no future member renders as
  a clean pass. The two other `.value` sites — `tasks_move_task.py:1120` (metadata, benign) and `:1574`
  (guarded `if effect.terminal:` → unreachable for non-terminal `SOURCE_MISMATCH`) — are verified
  non-branching; do NOT change them (note this in review).
- **Consumes from WP02/WP03**: `scope_source_identity`, the two predicates (WP02);
  `BaselineTestResult.source_identity` (WP03). Import; do not redefine.
- **Dead-symbol gate** (paula): `test_no_dead_symbols` keys on cross-module refs, so post-deletion
  `_CompositeRoute` (cross-module-only via `tasks_move_task.py:845`) is not false-flagged. Confirm.
- **#2825 baseline-red-gotcha**: BEFORE attributing any `test_no_dead_symbols` / `test_golden_count_ban`
  failure to this diff, confirm it is pre-existing red on `eb06ca176` (`PYTHONPATH=<worktree>/src` vs
  `upstream/main`). Do NOT green-wash a category-1 pre-existing red.
- **Quality bars (NFR-002)**: `mypy --strict` + `ruff` zero issues, complexity ≤15, ≥90% new coverage.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership)
- **Planning base branch**: `fix/scopesource-gate-followup`
- **Merge target branch**: `fix/scopesource-gate-followup`

## Subtasks & Detailed Guidance

### Subtask T019 – Delete the dead census tier (FR-001)

- **File**: `pre_review_gate.py`. Delete the 12 symbols + the census branch + the dropped params (list
  above). Confirm the live private copy in `scope_source.py` is untouched.
- **Guard**: after the delete, replay `pytest tests/review/test_transition_gate_parity.py -q` — the
  registry AND override goldens MUST stay byte-identical (this is why WP01 lands first).

### Subtask T020 – Delete `_mt_pre_review_gate_verdict` + atomic compat edit (FR-002 / C-004)

- **Files**: `tasks_move_task.py` (delete `_mt_pre_review_gate_verdict` `:1061`), `tasks.py` (remove the
  `:448` re-export), `test_tasks_compat_surface.py` (`:249` tuple entry, `:479` `157→156` keeping the
  golden-count marker, `:153` docstring `76→75`). ONE atomic commit — never a partial that breaks import.
- **Red-first**: the compat test is red on the intermediate (symbol removed, golden not yet decremented)
  and green once all four sites are edited together.

### Subtask T021 – Swap `isinstance`→predicates (FR-005)

- **File**: `pre_review_gate.py:881` (empty ⇒ `NO_COVERAGE` → `empty_scope_is_coverage_gap(scope_source)`)
  and `:1013` (`_scope_result_from_source` → `exposes_scope_breakdown(scope_source)`). Import the
  predicates from `specify_cli.review.scope_source`.
- **Guard**: verdicts unchanged for both shipped sources (WP01 golden green).

### Subtask T022 – `GateOutcome.SOURCE_MISMATCH` + `_evaluate_via_scope_source` construction (FR-009/FR-011)

- **File**: `pre_review_gate.py` (`GateOutcome` `:748`, `_evaluate_via_scope_source` `:851`).
- **Steps**: add `SOURCE_MISMATCH = "source_mismatch"`; in `_evaluate_via_scope_source` construct the warn
  verdict per data-model §2 (known-mismatch → `SOURCE_MISMATCH`; `None`/`"unknown"` baseline →
  `UNVERIFIED_BASELINE`). **Read-site precision (post-plan squad renata):** `_evaluate_via_scope_source`
  receives an ALREADY-LOADED `BaselineTestResult` and only COMPARES its `source_identity` against the
  head token — do NOT move the baseline load here. The load stays in `_mt_resolve_gate_baseline`
  (`tasks_move_task.py:1282-1303`), which already consumes #2874's kind-aware
  `_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)` seam (at `:1296`); the new `source_identity` simply
  rides on the loaded result — do not reconstruct `feature_dir`.
- **Red-first**: `tests/review/test_pre_review_gate_source_mismatch.py` (owned, `create_intent`) — a
  mismatched pair → `SOURCE_MISMATCH`; a `"unknown"` baseline → `UNVERIFIED_BASELINE` (not mismatch).

### Subtask T023 – Console ladder + defensive else + fail-open assert (FR-011)

- **Files**: `tasks_move_task.py:1156-1184`, `tests/review/test_pre_review_gate_source_mismatch.py`.
- **Steps**: add the `SOURCE_MISMATCH` + `NO_NEW_FAILURES` branches + defensive `else` (render
  `outcome.value`). Add an assert-only test that `SOURCE_MISMATCH` is absent from
  `verdict_aggregation._TERMINAL_OUTCOMES` and the block predicate → `aggregate_verdicts` yields
  `WARN_PROCEED` (SC-004). Do NOT edit the filters.

### Subtask T024 – Rewire the head-path factory + dual-impl/dual-parse-mode parity + SC-004 demo (FR-010/FR-014)

- **Files**: `tasks_move_task.py` (`_mt_resolve_scope_source` `:1250`, its call-site `:1310`);
  `tests/review/test_baseline_head_parity.py` (owned, `create_intent`).
- **Step 1 — REWIRE (load-bearing, post-plan squad priti-M1; without it FR-014/SC-001 are incomplete for
  the live gate).** Today `_mt_resolve_scope_source` (`:1250`) hard-constructs `GateCoverageScopeSource`
  and the head path calls it at `:1310`. Rewire the thin wrapper to **delegate to WP02's
  `resolve_scope_source(gate_repo_root, filter_groups_override=_pre_review_gate_filter_groups(),
  composite_routing_override=_pre_review_gate_composite_routing())`** — threading the KEPT monkeypatch
  seams (`:828-847`) so they stay overridable and no import cycle forms. This makes the **head** path use
  the SAME FR-014-selected source as WP03's baseline path; skipping it leaves head on
  `GateCoverageScopeSource` while baseline uses the selected source → guaranteed `SOURCE_MISMATCH` on
  every non-pytest review (the mission's own bug, re-skinned).
- **Step 2 — PARITY**: prove baseline+head land in ONE failure-identity namespace under BOTH
  `GateCoverageScopeSource` AND `DeclaredCommandScopeSource`, for a **worktree-relative-JUnit** case AND a
  **FAIL-text** case (the B1 cases) — all four combinations required. A deliberately mismatched pair raises
  `SOURCE_MISMATCH`. This is the SC-001/US1 + SC-004 proof. Consumes WP03's baseline + this WP's head path.
- **Step 3 — ASSERT THE WIRING**: drive at least one parity case through `_mt_resolve_scope_source`
  (the real wrapper), not only via direct source injection — so a future un-rewire is caught (a
  direct-injection-only test would pass even with the head path unwired).

### Subtask T025 – Docstring/CHANGELOG scrub + replay goldens (FR-013)

- **Files**: `pre_review_gate.py` (docstrings referencing deleted symbols / dropped params), `CHANGELOG.md`.
- **Steps**: scrub stale docstrings so no docs-code-sync gate references the deleted symbols as live; add a
  `CHANGELOG.md` entry for the deletion + SOURCE_MISMATCH. Final: replay
  `pytest tests/review/test_transition_gate_parity.py` (both golden sets) — byte-identical.

## Test Strategy

- **Order**: T019 (delete, goldens green) → T020 (atomic compat) → T021 (predicate swap) → T022/T023
  (SOURCE_MISMATCH) → T024 (parity) → T025 (scrub + final replay).
- **Run**:
  ```bash
  PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_transition_gate_parity.py \
    tests/review/test_pre_review_gate_source_mismatch.py tests/review/test_baseline_head_parity.py \
    tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py -q
  ```
- **Gate family (confirm pre-existing reds first, #2825)**:
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_golden_count_ban.py -q
  ```
- **Quality**: `ruff check` + `mypy --strict` on `pre_review_gate.py`, `tasks_move_task.py`, `tasks.py`;
  ≥90% new coverage; complexity ≤15.

## Risks & Mitigations

- **Circular oracle / behavior drift**: WP01 golden replays after T019/T021 — any drift is a real
  regression, fix the code not the golden.
- **Non-atomic compat edit (C-004)**: edit all four sites in one commit.
- **Editing the fail-open filters**: assert, never add `SOURCE_MISMATCH` to `_TERMINAL_OUTCOMES` / block.
- **Console fall-through**: the defensive `else` closes the silent-clean-pass class.
- **Firing mismatch on the override tier**: `_evaluate_via_scope_source` compares only in the injected head
  path; the override tier (`scope_source=None`) never reaches it.

## Review Guidance

- 12 census symbols + branch + params gone; private `scope_source.py` copy intact; keep-live set survives
  (WP01 override golden green).
- Compat edit atomic; `SYMBOL_TO_MODULE == 156` with the golden-count marker.
- `SOURCE_MISMATCH` warn-shaped, fail-open (asserted, filters untouched); console ladder exhaustive with
  defensive `else`; `"unknown"` baseline → `UNVERIFIED_BASELINE`.
- Four parity combinations present and green; both `.value` sites verified non-branching; zero suppressions.

## Activity Log

> **CRITICAL**: chronological order, append at the END.

- 2026-07-23T10:19:53Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP04 --to <status>`.
