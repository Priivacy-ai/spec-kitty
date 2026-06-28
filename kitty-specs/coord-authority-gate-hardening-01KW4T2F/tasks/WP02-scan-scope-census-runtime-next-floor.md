---
work_package_id: WP02
title: Scan-scope unify + named census + runtime/next floor
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-005
tracker_refs: []
planning_base_branch: feat/coord-authority-gate-hardening
merge_target_branch: feat/coord-authority-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Arm hardening
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1942833"
history:
- at: '2026-06-27T15:59:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_coord_read_residuals_closeout.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_coord_read_residuals_closeout.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Scan-scope unify + named census + runtime/next floor

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

Drive WP01's hardened arm (`callshape_violations`) over a widened, asymmetry-closed scan surface, and record every in-scope param/attribute read as routed-or-pinned in a **named shrink-only census**:

- **FR-002 — identity-arm scope-unify.** Widen the IDENTITY scan family to also cover `merge/` + `lanes/` + `core/worktree_topology.py` (the lanes arm already covers these — this closes the asymmetry that let the `executor` identity residual escape).
- **FR-005 — runtime/next scan extension.** Extend BOTH the identity and lanes scan families to `src/runtime/next/`, with a `runtime/next` read-site floor (mirroring `_count_read_call_sites`) so the extension is provably non-vacuous.
- **FR-003 — named shrink-only census + sanctioned exclusions.** Every in-scope param/attribute-fed kind-read is routed OR present in a named census; sanctioned exclusions are read-func-scoped (NOT blanket-module).

**This WP owns the scan harness only** (`test_coord_read_residuals_closeout.py`). It **consumes** WP01's arm — do not edit `test_gate_read_literal_ban.py` here. WP01 must land first (dependency).

**Done means:**
- IDENTITY scan dirs/files include `merge/` + `lanes/` + `core/worktree_topology.py` (T006) and both arms include `src/runtime/next/` with a read-site floor (T007).
- A named shrink-only census with a **per-arm stale-pin split** exists; the 3 `get_mission_type(feature_dir)` reads in `runtime_bridge.py` each carry a route-or-pin disposition (T008).
- Sanctioned exclusions (`require_lanes_json`, `_mission_identity_payload`, `read_events` STATUS-leg) are wired **read-func-scoped** so identity/lanes reads in `executor.py`/`recovery.py` stay in-scope (T009).
- SC-006 live-scope coverage is asserted; the anti-vacuity floor is raised post-widen; `PWHEADLESS=1 pytest tests/architectural/ -q` is green with zero false positives (T010).

## Context & Constraints

- **Design docs**: [spec.md](../spec.md) (FR-002, FR-003, FR-005, SC-006, NFR-003, NFR-004, C-005, C-007), [data-model.md](../data-model.md) §1 (scan scopes), §5 (census + exclusions), [contracts/gate-hardening-contracts.md](../contracts/gate-hardening-contracts.md) Contracts B + D.2.
- **Current scan surfaces** (`test_coord_read_residuals_closeout.py`):
  - `_IDENTITY_SCAN_DIRS` (~:93) = `cli/commands/` only; `_IDENTITY_SCAN_FILES` (~:94) = `agent_utils/status.py`.
  - `_LANES_SCAN_DIRS` (~:96) = `merge/` + `lanes/`; `_LANES_SCAN_FILES` (~:100) = `core/worktree_topology.py`.
  - `_CALLSHAPE_KNOWN_RESIDUALS` (~:115) = `frozenset()` (empty today).
  - `_STATUS_BEARING_MODULES` (~:119) = `("src/specify_cli/lanes/recovery.py", "src/specify_cli/merge/executor.py")`; `_STATUS_READ_FUNCS` (~:123) = `frozenset({"read_events"})`.
  - `_count_read_call_sites` (~:165) = the anti-vacuity floor helper.
  - The identity clean-scan test (~:201) and lanes clean-scan test (~:232) each compute `unexpected = flagged - _CALLSHAPE_KNOWN_RESIDUALS` and `stale_pins = _CALLSHAPE_KNOWN_RESIDUALS - flagged`.
- **The per-arm stale-pin split is REQUIRED (FR-003).** `_CALLSHAPE_KNOWN_RESIDUALS` is shared by both clean-scan tests. Adding an **identity-only** pin makes the **lanes** test's `stale_pins` assertion go RED (the pin is "stale" for the lanes scan). Remediate by splitting into `_IDENTITY_CALLSHAPE_KNOWN_RESIDUALS` / `_LANES_CALLSHAPE_KNOWN_RESIDUALS` **OR** scoping the stale diff to `census ∩ in-scope-for-this-arm`.
- **The exclusion is READ-FUNC-SCOPED, not blanket-module (C-007 / binding).** Only `read_events` STATUS legs in `_STATUS_BEARING_MODULES` are excluded. **Identity/lanes reads in those same modules stay IN-SCOPE and flaggable** — in particular an injected `resolve_mission_identity(run.feature_dir)` off a coord-aware dir in `merge/executor.py` (SC-006 / FR-008) MUST be caught. Excluding the whole module would let the SC-006 executor residual escape.
- **C-005**: coordinate (do NOT rot) the shrink-only `_DIR_READ_KNOWN_RESIDUALS` #2167 pin — it cites #2167's separate lineage.
- **NFR-004 (zero false positives)**: after each scope widening, run the census and route-or-pin everything newly surfaced. The named residual `mission_setup_plan::_run_documentation_wiring` (the FR-001 one-hop residual from WP01) must be **routed or pinned** here — it cannot stay an unexplained flag.
- **NFR-003 (gate-unmask-cannot-self-validate)**: the FR-005 un-mask is validated by a **verbatim full-`tests/architectural/` dry-run recorded in the PR body** — see [[feedback_gate_unmask_cannot_self_validate]]. Capture the dry-run output as part of this WP's evidence.
- **CT7 (NFR-001/NFR-002)**: content-anchor via `composite_key`; zero new `file.py:NNN` keys; keep the anti-vacuity floor.

## Branch Strategy

- **Strategy**: lane-based (allocated from `lanes.json` after finalize-tasks)
- **Planning base branch**: feat/coord-authority-gate-hardening
- **Merge target branch**: feat/coord-authority-gate-hardening

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T006 – FR-002: widen the IDENTITY scan family

- **Purpose**: Close the asymmetry that let `merge/executor.py:baseline_mission_id` escape the identity arm (the lanes arm already covers `merge/`+`lanes/`+`core/worktree_topology.py`).
- **Steps**:
  1. Extend `_IDENTITY_SCAN_DIRS` to include `merge/` and `lanes/`; extend `_IDENTITY_SCAN_FILES` to include `core/worktree_topology.py` (mirror the existing `_LANES_SCAN_*` definitions so the two arms share the same base surface).
  2. Run the identity clean-scan and route-or-pin anything newly surfaced (feeds T008/T009).
- **Files**: `tests/architectural/test_coord_read_residuals_closeout.py`
- **Notes**: Reuse the existing `_SRC` path-building idiom. Keep the identity and lanes scope definitions visibly parallel.

### Subtask T007 – FR-005: extend both arms to `src/runtime/next/` + read-site floor

- **Purpose**: Close the `src/runtime/next/` blind spot for the identity/lanes families and prove the extension is non-vacuous.
- **Steps**:
  1. Add `src/runtime/next/` to both `_IDENTITY_SCAN_DIRS` and `_LANES_SCAN_DIRS`.
  2. Add a **`runtime/next` read-site floor** using `_count_read_call_sites` (or a sibling) asserting the extended scope sees ≥3 in-family identity reads on the current tree — `runtime_bridge.py` carries `get_mission_type(feature_dir)` at ~:2547 / ~:3237 / ~:3392. The floor proves FR-005 is NOT green merely because the scan matches nothing.
  3. **DECOUPLING (binding)**: the FR-004 read (WP03) is a `tasks/`-dir, parameter-fed shape the call-shape arm **cannot** see — it is gated BEHAVIORALLY by SC-002 (WP03), NOT by this scan. Do not write this scan as if it gates FR-004.
- **Files**: `tests/architectural/test_coord_read_residuals_closeout.py`
- **Notes**: The floor count is content-derived (counts `get_mission_type` call sites), not a `file:line` pin. Keep it that way.
- **NON-FAKEABLE DoD (squad CRITICAL — NFR-003 self-validation trap)**: the floor MUST count reads **within `src/runtime/next/` ONLY**, NOT baseline + new. A baseline-inclusive count of ≥3 stays green even when the scope extension is absent → vacuous. Compute it via `_count_read_call_sites(<runtime/next paths only>, _IDENTITY_READ_FUNCS)`. **Prove revert-sensitivity**: removing `src/runtime/next/` from the scan dirs MUST make the floor assertion fail — exercise that revert during implementation and record the result in the WP review notes / PR body.

### Subtask T008 – FR-003: named shrink-only census + per-arm stale-pin split

- **Purpose**: Record every in-scope param/attribute read as routed-or-pinned, precisely, with per-arm stale-pin hygiene.
- **Steps**:
  1. Replace the single `_CALLSHAPE_KNOWN_RESIDUALS` with a **per-arm split** (`_IDENTITY_CALLSHAPE_KNOWN_RESIDUALS` / `_LANES_CALLSHAPE_KNOWN_RESIDUALS`) **OR** scope the stale diff in each clean-scan test to `census ∩ in-scope-for-this-arm`. Pick whichever keeps both clean-scan stale-pin assertions correct.
  2. Census schema (per [data-model.md §5]): `"<rel_path>::<qualname>"` → tracked residual with a tracker reference. **Shrink-only**: a NEW un-pinned flag → RED; a stale pin no longer flagged → RED.
  3. Give each of the 3 `runtime_bridge.py` `get_mission_type` reads an explicit **route-or-pin disposition**: either they route through the kind-aware seam (preferred where safe) or they are recorded as named shrink-only residuals with a tracker ref. Document the choice per site.
  4. Ensure the FR-001 named residual `mission_setup_plan::_run_documentation_wiring` is routed or pinned (it must not be an unexplained flag).
- **Files**: `tests/architectural/test_coord_read_residuals_closeout.py`
- **Notes**: Mirror the existing `_DIR_READ_KNOWN_RESIDUALS` shape; do not rot its #2167 pin (C-005).
- **NON-FAKEABLE DoD (squad CRITICAL — census auditability)**: a "routed" disposition asserted without proof is unauditable. For each of the 3 `runtime_bridge.py` reads AND the `_run_documentation_wiring` residual, the census entry MUST be one of: (a) **PINNED** — carry an inline tracker reference in the census entry (`# PINNED: #NNNN`); or (b) **ROUTED** — the read is genuinely re-pointed at the kind-aware seam and is no longer flagged (so it is simply absent from the census, and the clean-scan proves it). Do NOT record a read as a census entry while claiming it is "routed" — routed means *not flagged*. If a read cannot be routed at WP02-time because it depends on WP03's edit, PIN it with `# PENDING: routed by WP03/T011` and a tracker ref, so the disposition is explicit, not implied.

### Subtask T009 – FR-003: read-func-scoped sanctioned exclusions (C-007)

- **Purpose**: Exclude the genuinely-must-take-a-dir / STATUS-leg reads WITHOUT excluding identity/lanes reads in the same modules.
- **Steps**:
  1. Wire the sanctioned, never-flagged exclusions: leaf primitive `require_lanes_json`, payload helper `_mission_identity_payload`, and `read_events` STATUS-leg reads inside `_STATUS_BEARING_MODULES`.
  2. Scope the status exclusion via `_STATUS_READ_FUNCS = {"read_events"}` ∩ `_STATUS_BEARING_MODULES` — **NOT** a blanket module skip. Add/keep an assertion (or structural guarantee) that an identity read in `executor.py`/`recovery.py` stays in-scope.
  3. These exclusions are NOT census entries — they are true never-flagged exclusions (Contract B).
- **Files**: `tests/architectural/test_coord_read_residuals_closeout.py`
- **Notes**: The `read_events` STATUS leg stays coord-aware (the existing NFR-001 secondary cross-check guards this — do not regress it).
- **NON-FAKEABLE DoD (squad HIGH — C-007 proof, not just module-in-scope)**: `assert "…/executor.py" in _IDENTITY_SCAN_DIRS` is vacuous — it proves the module is scanned, not that an identity read there is still flagged. The DoD is a **positive flag proof**: feed the arm an injected `resolve_mission_identity(<coord-aware dir>)` located in `executor.py`/`recovery.py` and assert it **IS flagged**, while a `read_events(<coord dir>)` in the same module is **NOT** flagged. That pair proves the exclusion keys on the read-func name, not the module.

### Subtask T010 – SC-006 live-scope coverage + raise anti-vacuity floor + full green

- **Purpose**: Prove the scope-unify actually makes `merge/executor.py` identity reads in-scope, and that the widened scan is non-vacuous.
- **Steps**:
  1. Assert SC-006 live coverage: with FR-002 in place, inject **TWO distinct** identity reads off a coord-aware dir in `merge/executor.py` — (1) the **parameter** shape `resolve_mission_identity(param_dir)` and (2) the **attribute** shape `resolve_mission_identity(run.feature_dir)` — and assert **both flag** through the scope-unified arm. A single-shape assertion is insufficient (the attribute shape is FR-008 and must be proven in-scope here, not only synthetically in WP01/T005). This proves the *scope* covers the module for both shapes.
  2. Raise the anti-vacuity read-site floor for the identity arm to reflect the widened scope (the floor census must increase to match the larger surface).
  3. Run `PWHEADLESS=1 pytest tests/architectural/test_coord_read_residuals_closeout.py -q`, then the full `PWHEADLESS=1 pytest tests/architectural/ -q`. Capture the full-suite output verbatim for the PR body (NFR-003).
- **Files**: `tests/architectural/test_coord_read_residuals_closeout.py`
- **Notes**: Zero false positives is the bar — every newly-surfaced flag must be routed or pinned before this is green.

## Test Strategy

- Tests are REQUIRED (this WP IS test-gate harness). Deliverable = widened scan + census + floors, all green.
- Run: `PWHEADLESS=1 pytest tests/architectural/test_coord_read_residuals_closeout.py -q` then `PWHEADLESS=1 pytest tests/architectural/ -q`.
- **NFR-003 evidence**: record the verbatim full-`tests/architectural/` run in the PR body.
- Ruff + mypy clean on the touched file.

## Risks & Mitigations

- **Per-arm stale-pin RED (high)**: an identity-only pin reds the lanes stale-pin assertion. **Mitigation**: T008's per-arm split or scoped diff — verify BOTH clean-scan tests green after adding any pin.
- **C-007 violation**: a blanket-module exclusion would silently let the SC-006 executor residual escape. **Mitigation**: T009 read-func-scoped exclusion + an explicit in-scope assertion for an executor identity read.
- **NFR-003 self-validation trap**: FR-005 could be green merely because the scan matches nothing. **Mitigation**: the runtime/next read-site floor (T007) + the verbatim full-gate dry-run.
- **False positives (NFR-004)**: widening surfaces new flags. **Mitigation**: route-or-pin every one; the named residual must be dispositioned, not hidden.

## Review Guidance

- Confirm BOTH the identity and lanes clean-scan tests are green after the census split (temporarily add a fake identity-only pin and confirm only the identity stale check reacts).
- Confirm the runtime/next floor is content-derived (counts `get_mission_type` sites), not a `file:line` pin, and that it fails if the scope is reverted.
- Confirm the status exclusion is read-func-scoped: an identity read injected into `executor.py` is still flagged.
- Confirm the 3 `get_mission_type` reads + the `_run_documentation_wiring` residual each have a documented route-or-pin disposition.
- Confirm the PR body will carry the verbatim full-`tests/architectural/` output (NFR-003).

## Activity Log

- 2026-06-27T15:59:26Z – system – Prompt created.
- 2026-06-27T17:27:30Z – claude:opus:python-pedro:implementer – shell_pid=1897763 – Assigned agent via action command
- 2026-06-27T17:49:14Z – claude:opus:python-pedro:implementer – shell_pid=1897763 – Scan-scope unify (FR-002 identity+merge/lanes/worktree, FR-005 both arms+runtime/next+revert-sensitive floor), per-arm census split (#2214 _run_documentation_wiring pinned; 3 runtime_bridge get_mission_type clean/ROUTED; require_lanes_json/_mission_identity_payload sanctioned), C-007 read-func-scoped + SC-006 both-shapes proofs. 13/13 closeout green; full tests/architectural 582 passed, 1 pre-existing worktree-path artifact (marker-convention). ruff+mypy exit 0.
- 2026-06-27T17:50:04Z – claude:opus:reviewer-renata:reviewer – shell_pid=1942833 – Started review via action command
- 2026-06-27T18:03:26Z – user – shell_pid=1942833 – Review passed: all 7 traps verified non-vacuous via independent source edits. (1) NFR-003 runtime/next floor genuinely runtime/next-scoped — removing src/runtime/next/ from _IDENTITY_SCAN_DIRS dropped count 3->0 and red BOTH FR-005 tests; revert-sensitivity test executes the revert in-test. (2) Per-arm stale-pin split real — fake identity-only pin red ONLY identity stale check, lanes stayed green. (3) Census ledger auditable — _run_documentation_wiring pinned #2214 AND live-flagged; 3 runtime_bridge get_mission_type reads proven absent from offender set AND not pinned (CLEAN/ROUTED). (4) C-007 exclusion positive proof — synthetic identity read flags, read_events not an identity flag (keys on read-func name). (5) SC-006 both shapes proven in-scope — run.feature_dir attr flags, run.target_feature_dir sanctioned, one-hop param flags w/ module ctx not without. (6) CT7: zero file.py:NNN anchors, ::qualname composite keys, no new manual allowlist. (7) C-005: _DIR_READ_KNOWN_RESIDUALS/#2167 lives in WP01 file, untouched by WP02 commit. 13/13 closeout green; full tests/architectural 582 passed; ruff+mypy exit 0; tree pristine post-edits. Sole failure test_support_helper_tree_is_exempt_from_marker_convention is a pre-existing .worktrees/-path discovery artifact (assert candidates empty), unrelated to owned file — not blocking per WP guidance.
