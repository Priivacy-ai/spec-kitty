---
work_package_id: WP01
title: 'Call-shape arm logic: one-hop cross-function + attribute-discipline'
dependencies: []
requirement_refs:
- FR-001
- FR-008
tracker_refs: []
planning_base_branch: feat/coord-authority-gate-hardening
merge_target_branch: feat/coord-authority-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Arm hardening
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1871973"
history:
- at: '2026-06-27T15:59:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_gate_read_literal_ban.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_gate_read_literal_ban.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Call-shape arm logic: one-hop cross-function + attribute-discipline

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objectives & Success Criteria

Harden the AST scanner `callshape_violations` in `tests/architectural/test_gate_read_literal_ban.py` so the static gate catches the two cross-function residual shapes it is blind to today:

- **FR-001 — one-hop cross-function (parameter) detection.** When an in-scope kind-read's first arg is a function **parameter**, follow exactly **one hop** to the caller and flag **only** when the caller binds that arg from a **coord-aware resolver without a primary fold**. This requires two co-dependent mechanism parts (both required — see T001 + T003).
- **FR-008 — attribute-discipline.** When an in-scope kind-read's first arg is an `ast.Attribute` (e.g. `run.feature_dir`), flag it unless it is a **sanctioned primary attribute** (`.target_feature_dir` or a primary-fold-bound field).

**This WP is the arm logic only** — the pure AST scanner plus its self-mutation snippets. The scan-harness scope-unify, the named census, and the runtime/next floor live in **WP02** (`test_coord_read_residuals_closeout.py`). Do not edit that file here.

**Done means:**
- `_COORD_AWARE_CALLSHAPE_RESOLVERS` is widened to the 5-name read-arm-aligned set (T001).
- `callshape_violations` flags the attribute shape (T002) and the one-hop parameter shape (T003), with a module-scoped caller index.
- `test_callshape_arm_identity_passes_parameter_dir` is re-pinned and **not** contradictory with FR-001 (T004).
- Per-shape self-mutation tests `_VIOLATION_CROSS_FUNCTION` and `_VIOLATION_ATTRIBUTE` (RED) + clean counterparts (GREEN) ship, content-anchored via `composite_key` (T005).
- `PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py -q` is green.

## Context & Constraints

- **Design docs**: [spec.md](../spec.md) (FR-001, FR-008, SC-001, SC-006, C-006, C-007), [data-model.md](../data-model.md) §2–§4 (the resolver sets + sanctioned attributes), [contracts/gate-hardening-contracts.md](../contracts/gate-hardening-contracts.md) Contract A.
- **The 3-vs-5 asymmetry is the root cause of FR-001 hollowness.** Today `_COORD_AWARE_CALLSHAPE_RESOLVERS` (line ~164) holds **3** names; the read-arm's `_TOPOLOGY_ROUTED_READ_RESOLVERS` (line ~109) holds **5** (the 3 + `_find_feature_directory` + `resolve_handle_to_read_path`). The named residual `_run_documentation_wiring` ← `setup_plan` binds `feature_dir` from `_resolve_setup_plan_feature_dir` → `_find_feature_directory`, which the 3-name set does **not** recognize as coord-aware. **Without T001's widening, the one-hop check in T003 fires on no live caller and FR-001/SC-001/SC-006 are hollow.** Both T001 and T003 are required for the residual to be reachable.
- **The single real residual** the one-hop check must catch is `mission_setup_plan::_run_documentation_wiring` ← coord-aware `setup_plan` (exactly one hop). A 2–3-hop chain is NOT a current residual — full multi-hop tracking is the deferred fallback (C-006). Do not build multi-hop.
- **False-positive boundary (NFR-004 / C-006).** A blunt parameter-discipline rule is **rejected** (~78–89% false-positive on the 9 in-scope param-takers, incl. the leaf primitive `require_lanes_json`). The one-hop check must whitelist `resolve_planning_read_dir`-bound / primary-fold-bound dirs (`_PRIMARY_FOLD_CALLSHAPE_FUNCS`, line ~175) and key on the read-func families (`_IDENTITY_READ_FUNCS` ~184 / `_LANES_READ_FUNCS` ~189).
- **C-007 (binding):** do NOT special-case `_STATUS_BEARING_MODULES` in the arm logic by forcing a status leg to PRIMARY. The arm stays a pure flag-rule; the read-func-scoped status exclusion lives in WP02's census, not here.
- **CT7 (NFR-001/NFR-002):** anchor every new test via `tests/architectural/_ratchet_keys.composite_key`; **zero new `file.py:NNN` ratchet keys.** Each new shape ships a self-mutation test.
- **Reuse existing arm primitives**: `_names_bound_from(func, callees)` (line ~313), `_func_from_source` (test helper), and the existing two-hop/inline-Call detection. Extend; do not rewrite.

## Branch Strategy

- **Strategy**: lane-based (allocated from `lanes.json` after finalize-tasks)
- **Planning base branch**: feat/coord-authority-gate-hardening
- **Merge target branch**: feat/coord-authority-gate-hardening

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T001 – Widen `_COORD_AWARE_CALLSHAPE_RESOLVERS` to the 5-name read-arm-aligned set

- **Purpose**: Make the residual's binding recognizable as coord-aware. Without this, T003's one-hop check is hollow.
- **Steps**:
  1. In `test_gate_read_literal_ban.py`, extend `_COORD_AWARE_CALLSHAPE_RESOLVERS` (~line 164) so it aligns with `_TOPOLOGY_ROUTED_READ_RESOLVERS` (~line 109). Add at minimum `_find_feature_directory` (and/or `_resolve_setup_plan_feature_dir` if the binding chain warrants it) so the `setup_plan → _resolve_setup_plan_feature_dir → _find_feature_directory` chain is cataloged.
  2. Verify the widened set against `_TOPOLOGY_ROUTED_READ_RESOLVERS` — confirm there is no longer a 3-vs-5 gap for the names the one-hop check depends on. Consider asserting alignment in a small test so the two sets cannot silently re-diverge.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`
- **Notes**: Do NOT widen so far that legitimate same-function param-takers get false-flagged — the widening only changes which **caller bindings** count as coord-aware for the one-hop hop in T003.

### Subtask T002 – Add the `ast.Attribute` branch to `callshape_violations` (FR-008)

- **Purpose**: The scanner has no `ast.Attribute` branch today, so `read_func(run.feature_dir)` is invisible (the executor-shape escape).
- **Steps**:
  1. In `callshape_violations` (~line 551), add handling for a first arg that is an `ast.Attribute`. Flag it when it is coord-bearing **unless** it is a sanctioned primary attribute.
  2. Define the sanctioned-primary-attribute allowlist per [data-model.md §4]: `.target_feature_dir` and fields bound from a primary fold. Keep it a small named set (e.g. `_SANCTIONED_PRIMARY_ATTRS = frozenset({"target_feature_dir"})`) so it is content-anchored and greppable.
  3. Any other coord-bearing attribute (e.g. `run.feature_dir`) → flagged. Return the existing `"<read_func>(<arg>)"` shape string for consistency with the other branches.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`
- **Notes**: This is **in-scope, not a fallback** (spec FR-008). The attribute branch composes with the read-func selection (`read_funcs` param) exactly like the Name/Call branches.

### Subtask T003 – Module-scoped caller index + one-hop parameter caller-binding (FR-001)

- **Purpose**: Add the only arm-**signature** change: per-function → module/caller context, so a parameter-fed read can be followed one hop to its caller's binding.
- **Steps**:
  1. The current signature is `callshape_violations(func, *, read_funcs)` — per-function, no caller visibility. Introduce a **module-scoped caller index** (e.g. build a map of {callee qualname → list of call sites with their arg bindings} for the module's AST) and thread it into the flag-rule so that, when the flagged call's first arg is a **function parameter**, the rule can look up the caller(s) that pass into this function and inspect how they bind that arg.
  2. Flag the parameter shape **only** when the one-hop caller binds the arg from a coord-aware resolver (`_COORD_AWARE_CALLSHAPE_RESOLVERS`, now 5 names) **without** a primary fold (`_PRIMARY_FOLD_CALLSHAPE_FUNCS`). A parameter whose caller-binding is primary/seam-bound or non-coord-aware is **NOT** flagged.
  3. **Retain the existing same-function PARAM-exemption EXCEPT where this one-hop check fires.** The exemption that lets a plain caller-supplied param pass must stay for the non-coord-aware case; it is only overridden when the one-hop caller binding is coord-aware-without-fold.
  4. Keep the change additive to the existing two-hop-local-Name and inline-Call branches (Contract A items 1 & 2). Prefer a small helper for the one-hop lookup over inflating `callshape_violations` past the complexity ceiling (15) — extract if needed.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`
- **Notes**: One hop ONLY. Do not implement transitive/multi-hop tracking (C-006). The caller index is module-scoped, so the test harness that calls `callshape_violations` (in WP02) must be able to supply module/caller context — design the new parameter so WP02's scan loop can pass it. Document the new signature in the docstring.

### Subtask T004 – Re-pin `test_callshape_arm_identity_passes_parameter_dir`

- **Purpose**: FR-001 changes when a parameter is flagged; the existing precision-guard test must stay consistent, not contradictory.
- **Steps**:
  1. Inspect `test_callshape_arm_identity_passes_parameter_dir` (~line 1293) and its `_IDENTITY_CLEAN_PARAMETER_DIR` snippet. Today it asserts a plain caller-supplied parameter dir passes (no flag).
  2. After FR-001, a plain parameter whose caller has **no coord-aware binding** must STILL pass. Re-pin the snippet/assertion so this stays true — and ensure it does NOT accidentally describe a coord-aware-caller binding (which would now correctly flag). If the snippet needs a companion caller to make the "no coord-aware binding" explicit under the module-scoped harness, add it.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`
- **Notes**: Do not delete this test to make it pass (see [[feedback_failing_test_remediation_framework]]) — adjust it to remain a correct precision guard that is consistent with FR-001.

### Subtask T005 – Per-shape self-mutation tests (NFR-002 / SC-001 / SC-006)

- **Purpose**: Make each new shape an automated regression (synthetic offender → RED, clean → GREEN), not a one-time manual inject.
- **Steps**:
  1. Add `_VIOLATION_CROSS_FUNCTION`: a synthetic module-source snippet where a function's param dir is bound **one hop up** from a coord-aware resolver (no primary fold) and passed into an identity/lanes read → assert `callshape_violations` flags it (RED-side). Add a **clean counterpart** where the caller binds from a primary fold → assert no flag (GREEN-side). **NON-FAKEABLE DoD (squad HIGH — prove the one-hop machinery, not the pre-existing two-hop branch)**: the snippet MUST have **zero local same-function coord-aware binding** in the callee — the coord-awareness must come SOLELY from the one-hop caller, so the test would NOT flag without T001's widening + T003's caller index. Add an inline comment: `# Proves FR-001: flags only via one-hop caller binding (no same-function binding present)`. Otherwise the test can pass on the existing two-hop-local branch while the new machinery is untested.
  2. Add `_VIOLATION_ATTRIBUTE`: `resolve_mission_identity(run.feature_dir)` in an executor-shape function → assert flagged; `.target_feature_dir` counterpart → assert not flagged.
  3. Anchor each new test via `_ratchet_keys.composite_key` (qualname/token-line). **No `file.py:NNN` keys.**
  4. Run `PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py -q` and confirm all green.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`
- **Notes**: These synthetic AST snippets are tested directly against `callshape_violations` and do NOT need the scan harness — they prove the arm logic in isolation. The **live-scope** SC-006 proof (that `merge/executor.py` is actually in the identity scan scope) is WP02's T010.

## Test Strategy

- Tests are REQUIRED (this WP is itself test-gate logic). The deliverable is the hardened arm + its self-mutation tests.
- Run: `PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py -q`.
- Ruff + mypy clean on the touched file (zero new issues/warnings; no suppressions).

## Risks & Mitigations

- **FR-001 hollowness (highest risk)**: if T001's widening is skipped or incomplete, T003's one-hop check matches no live caller and the gate is green-but-useless. **Mitigation**: T003's self-mutation `_VIOLATION_CROSS_FUNCTION` must exercise the *exact* binding shape (coord-aware caller → param → read); and WP02's live scan must surface/route-or-pin the real `_run_documentation_wiring` residual. Cross-check with WP02.
- **Complexity ceiling (15)**: the one-hop logic can balloon `callshape_violations`. **Mitigation**: extract the one-hop lookup and the attribute check into small named helpers with focused tests.
- **False positives (NFR-004)**: over-broad widening or a blunt param rule trips legit param-takers. **Mitigation**: key strictly on read-func families + coord-aware-without-primary-fold caller binding; keep `test_callshape_arm_identity_passes_parameter_dir` green.

## Review Guidance

- Confirm `_COORD_AWARE_CALLSHAPE_RESOLVERS` now aligns with `_TOPOLOGY_ROUTED_READ_RESOLVERS` and that the alignment is itself guarded against silent re-divergence.
- Confirm the one-hop check is exactly one hop (no transitive walk) and the same-function PARAM-exemption is retained except where one-hop fires.
- Confirm both self-mutation tests genuinely go RED on the offender and GREEN on the clean counterpart (reviewer should temporarily flip an assertion to verify non-vacuity).
- Confirm zero new `file.py:NNN` anchors (grep), and ruff/mypy clean.

## Activity Log

- 2026-06-27T15:59:26Z – system – Prompt created.
- 2026-06-27T16:59:57Z – claude:opus:python-pedro:implementer – shell_pid=1824424 – Assigned agent via action command
- 2026-06-27T17:17:40Z – claude:opus:python-pedro:implementer – shell_pid=1824424 – Call-shape arm FR-001 one-hop + FR-008 attribute shipped; 30/30 test_gate_read_literal_ban.py green; full tests/architectural/ = 1 pre-existing unrelated failure (test_pytest_marker_convention support-helper-tree, fails with my changes stashed); ruff+mypy diff-scoped exit 0.
- 2026-06-27T17:18:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=1871973 – Started review via action command
- 2026-06-27T17:25:59Z – user – shell_pid=1871973 – Review passed: FR-001 one-hop+5-name widen, FR-008 attribute-discipline; all 6 hollowness traps verified. (1) _COORD_AWARE_CALLSHAPE_RESOLVERS = read-arm 5-set superset + _resolve_setup_plan_feature_dir, alignment-guarded vs re-divergence. (2) _VIOLATION_CROSS_FUNCTION non-vacuity REAL — companion assert proves no flag without module= (callee zero same-fn coord binding -> flags ONLY via one-hop machinery, not pre-existing two-hop). (3) _VIOLATION_ATTRIBUTE exact-list both sides. (4) CT7 zero file.py:NNN, composite_key anchored. (5) passes_parameter_dir re-pinned/strengthened, not weakened. (6) callshape_violations C901<=15 via extracted helpers. 30/30 green, ruff+mypy clean, single-file scope. Pre-existing marker-test failure independently confirmed environmental (.worktrees dot-prefix). Approval gate unblocked by formalizing 3 context/lineage matrix rows (#2155/#2194/#2212).
