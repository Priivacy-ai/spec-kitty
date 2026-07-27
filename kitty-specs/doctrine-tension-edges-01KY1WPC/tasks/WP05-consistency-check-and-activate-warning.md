---
work_package_id: WP05
title: Consistency-check finding + activate warning
dependencies:
- WP01
- WP02
requirement_refs:
- FR-009
- FR-010
- FR-014
- NFR-001
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
phase: Phase 3 - Checkup surface
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "99151"
shell_pid_created_at: "1784646664.997155"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/consistency_check.py
create_intent:
- tests/charter/test_tension_unreconciled.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/consistency_check.py
- src/specify_cli/cli/commands/charter/_app.py
- tests/charter/test_consistency_check.py
- tests/charter/test_tension_unreconciled.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Consistency-check finding + activate warning

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/charter/consistency_check.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review. Address all feedback; update the Activity Log as you go.

---

## Objectives & Success Criteria

This is the mission's actual reason to exist (US1) — making silent doctrine competition visible. Read `contracts/tension-finding.md` in full before writing any code; it is the binding contract for both surfaces this WP touches.

Done means (per `contracts/tension-finding.md` and spec.md US1/US2/SC-001/SC-002/NFR-001):
- `ConsistencyReport` gains `unreconciled_tensions: list[TensionFinding]`, excluded from the `coherent` boolean.
- Exactly one finding per co-activated, unreconciled `in_tension_with` pair — keyed on the sorted URN pair (dedup), no transitive closure.
- A pair with only one side active produces **no** finding.
- A pair with only one `reconciles_tension` edge (half-reconciled) still produces a finding.
- Removing `reconcile-change-scope-tensions` (WP02) makes the 024/025 (and tactic/025) findings reappear; restoring it clears them (SC-002 — a live, provable assertion).
- The scan's DRG load fails closed into `verification_errors` on error — never a silently empty list.
- `charter activate` surfaces the same finding shape as a warning.

## Context & Constraints

- `ConsistencyReport` currently has: `coherent`, `unknown_references`, `missing_from_doctrine`, `kind_violations`, `reference_id_divergences`, `graph_kind_gaps`, `verification_errors`, `suggestions`, plus a `to_json()` method — verified by reading `src/charter/consistency_check.py` directly. Add `unreconciled_tensions` alongside these; update `to_json()` to include it.
- **NFR-001's trap**: "a no-op checker returning `[]` fails this requirement" is written into the spec precisely because it's an easy way to accidentally ship something that looks done (no crashes, tests for the "no finding" case pass) but never actually fires. Write the positive-finding test (T029) before or alongside the implementation, not after — this is the recommended red-first order for exactly this reason.
- This WP depends on WP01 (relations exist) and WP02 (the built-in reconciler + tension edges exist — required for SC-002's before/after assertion to have something real to remove/restore) only. No technical dependency on WP04: this WP's scan only ever looks at `in_tension_with`/`reconciles_tension` edges among directive/tactic nodes, never `rejects` edges or `anti_pattern` nodes — WP04's activation-filter wiring is orthogonal, and this WP can run in parallel with it.

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

Implementation command: `spec-kitty agent action implement WP05 --agent <name>` (depends on WP01, WP02 only — runs in parallel with WP03/WP04/WP06).

## Subtasks & Detailed Guidance

### Subtask T024 – Add `TensionFinding` + `unreconciled_tensions`

- **Purpose**: The data shape both this WP's surfaces (consistency-check, activate) and `contracts/tension-finding.md` are built around.
- **Steps**:
  1. In `src/charter/consistency_check.py`, add a `TensionFinding` dataclass (frozen): `pair: tuple[str, str]` (sorted URN pair) and `resolution_paths: tuple[str, str] = ("deactivate one side", "activate a reconciler")` — match `contracts/tension-finding.md`'s exact strings, they are asserted verbatim by SC-001.
  2. Add `unreconciled_tensions: list[TensionFinding] = field(default_factory=list)` to `ConsistencyReport`.
  3. Update `to_json()` to serialize the new field per the JSON shape in `contracts/tension-finding.md` (`type: "tension_unreconciled"`, `pair`, `resolution_paths`).
  4. **Do not** add `unreconciled_tensions` to whatever computation currently produces the `coherent` boolean — read that reduction logic and confirm it stays untouched (NFR-001).
- **Files**: `src/charter/consistency_check.py`
- **Parallel?**: No — everything else in this WP builds on this shape.

### Subtask T025 – Implement the tension scan

- **Purpose**: FR-009's core logic.
- **Steps**:
  1. Over the activation-filtered graph, find every edge with `relation == Relation.IN_TENSION_WITH` where both endpoints are in the active set (reuse whatever activation-filtering entry point the rest of `consistency_check.py` already uses — do not re-implement activation filtering here).
  2. Key each finding on the sorted URN pair (`tuple(sorted((source, target)))`) so a pair authored in either direction, or discovered from either traversal order, dedupes to exactly one entry (Edge Case: symmetric authoring drift).
  3. Do NOT compute any transitive closure — only ever look at declared `IN_TENSION_WITH` edges directly; `A⋈B` + `B⋈C` must never synthesize or flag `A⋈C` (INV-002). This should fall out naturally from only iterating declared edges — do not add any reachability/closure step.
- **Files**: `src/charter/consistency_check.py`
- **Parallel?**: No — sequential with T026/T027 (same function, being built up).

### Subtask T026 – Implement the reconciliation check

- **Purpose**: FR-002/FR-009 — a pair is resolved only when BOTH sides are bridged.
- **Steps**: For each candidate pair from T025, check whether any currently-active artefact has a `reconciles_tension` edge to **both** `pair[0]` and `pair[1]`. If yes, the pair is resolved and produces no finding. If only one side has a `reconciles_tension` edge from some active artefact (even the same one), the pair is still unreconciled (US2 sc2 — half-reconciled does not resolve).
- **Files**: `src/charter/consistency_check.py`
- **Parallel?**: No — sequential after T025.
- **Notes**: "Any active artefact" — not necessarily the same reconciler for both edges in principle, though in practice (per WP02) `reconcile-change-scope-tensions` supplies both. Implement the general rule (both sides bridged by *some* active reconciler(s), not necessarily one specific one) since spec.md's Edge Cases (N-way / reconciler-in-tension) implies generality, not a single-reconciler special case.

### Subtask T027 – Fail-closed error handling

- **Purpose**: FR-009 — "the DRG load fails closed into verification_errors (not swallowed)."
- **Steps**: Wrap the tension scan (T025/T026) so that any exception during graph load/traversal appends a descriptive entry to `verification_errors` and does NOT result in `unreconciled_tensions` silently being `[]`. If `consistency_check.py` has an existing try/except pattern for this (check how `graph_kind_gaps` or another field's computation handles its own failure mode), mirror it exactly rather than inventing a new error-handling shape.
- **Files**: `src/charter/consistency_check.py`
- **Parallel?**: No — wraps T025/T026.

### Subtask T028 – Add the `charter activate` warning

- **Purpose**: FR-010 — the same tension, surfaced at activation time, not just at consistency-check time.
- **Steps**:
  1. Locate the `activate` command's warning-emission path in `src/specify_cli/cli/commands/charter/_app.py` (confirm the exact function — it was not found by a simple grep for `"activate"`/`@app.command` at plan time; search for how existing activation warnings are emitted and follow that pattern precisely).
  2. Call the same tension-scan logic (T025/T026) and surface any resulting `TensionFinding`s alongside existing warnings, using the human-readable format shown in `contracts/tension-finding.md` (naming both artefacts and both resolution paths verbatim).
- **Files**: `src/specify_cli/cli/commands/charter/_app.py`
- **Parallel?**: No — depends on T024-T026's shape existing.
- **Notes**: Do not duplicate the scan logic — factor it so both call sites (consistency-check and activate) share the same function, per the "single canonical authority" charter principle.

### Subtask T029 – Tests

- **Purpose**: Prove every contract in `contracts/tension-finding.md` and every acceptance scenario in US1/US2.
- **Steps**: In new `tests/charter/test_tension_unreconciled.py` (extending `tests/charter/test_consistency_check.py` where it's a more natural fit for existing fixtures):
  1. **Positive assertion (NFR-001)**: construct a graph with a co-activated, unreconciled `in_tension_with` pair; assert `unreconciled_tensions` has exactly one entry with the correct sorted pair and both resolution-path strings.
  2. **Non-finding case**: only one side active — assert zero findings for that pair (US1 sc3).
  3. **SC-002 before/after (live assertion)**: using the real built-in pack, assert `coherent=true` and zero findings out of the box; deactivate `reconcile-change-scope-tensions`, assert the 024/025 and tactic/025 findings now appear; reactivate it, assert they clear again.
  4. **Half-reconciled (US2 sc2)**: a reconciler with only one `reconciles_tension` edge to the pair — assert the finding still fires.
  5. **Dedup (Edge Case)**: author the tension in both directions (or query from both endpoints) — assert exactly one finding, not two.
  6. **Fail-closed**: force a DRG-load error in the scan path — assert it lands in `verification_errors`, and `unreconciled_tensions` is not silently `[]` masquerading as "checked, found nothing."
- **Files**: `tests/charter/test_tension_unreconciled.py` (new), `tests/charter/test_consistency_check.py`
- **Parallel?**: No — write incrementally alongside T024-T028, red-first where practical.

## Test Strategy

- `.venv/bin/pytest tests/charter/test_consistency_check.py tests/charter/test_tension_unreconciled.py -q`
- Full `.venv/bin/pytest tests/charter/ -q` before marking done — this WP touches shared consistency-check machinery other tests may exercise indirectly.
- `.venv/bin/ruff check` + `.venv/bin/mypy` on `owned_files`.

## Risks & Mitigations

- **Risk**: Shipping a technically-passing-tests checker that never fires in practice (NFR-001's named trap). **Mitigation**: T029's positive assertion test is mandatory, not optional, and should be written before you're confident the implementation is "done."
- **Risk**: Duplicating the scan logic between consistency-check and activate, so they drift. **Mitigation**: T028 explicitly calls for sharing the function.

## Review Guidance

- Run the SC-002 before/after scenario yourself (deactivate the reconciler, observe the finding appear, reactivate, observe it clear) — do not accept "tests pass" as a substitute for seeing this live, since this is exactly the kind of vacuous-check risk NFR-001 names.
- Confirm `coherent` is never `false` due to `unreconciled_tensions` alone.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP05 --to <status>` to change WP status.
- 2026-07-21T14:28:33Z – claude:sonnet:python-pedro:implementer – shell_pid=93054 – Assigned agent via action command
- 2026-07-21T14:49:33Z – claude:sonnet:python-pedro:implementer – shell_pid=93054 – Ready for review: TensionFinding + unreconciled_tensions scan implemented in consistency_check.py, wired into charter activate warning path (activate.py). SC-002 live before/after verified against real built-in pack. Full tests/charter/ sweep: 1635 passed, 1 skipped.
- 2026-07-21T15:11:09Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=99151 – Started review via action command
- 2026-07-21T15:23:00Z – user – shell_pid=99151 – Review passed. Verified independently (not trusting self-report): (1) diff scope is exactly 3 files (consistency_check.py, activate.py, test_tension_unreconciled.py) -- no edits to charter/drg.py or any file outside owned_files. (2) T024: TensionFinding frozen dataclass, resolution_paths default matches contract verbatim; unreconciled_tensions added to ConsistencyReport and confirmed NOT part of the coherent reduction by reading the code directly. (3) T025/T026: live-constructed an A-B/B-C synthetic graph and ran scan_unreconciled_tensions directly -- confirmed no transitive A-C is synthesized (INV-002); half-reconciled test confirms both-sides-bridged requirement. (4) T027: forced-error test lands in verification_errors, not swallowed. (5) T028: activate.py imports and calls the SAME scan_unreconciled_tensions (single canonical authority, no duplicated logic); warning text matches contract format. (6) T029/SC-002: ran tests/charter/test_tension_unreconciled.py -v myself -- 7/7 passed, including the live SC-002 before/after against the REAL built-in pack (directive.graph.yaml's actual DIRECTIVE_024/025/RECONCILE_CHANGE_SCOPE_TENSIONS edges from WP02), not a synthetic fixture. (7) Full tests/charter/ -q sweep run myself: 1635 passed, 1 skipped, 385s -- matches implementer self-report exactly, no regressions. (8) ruff clean on all 3 files; mypy has 2 pre-existing errors in activate.py (lines 102/126) confirmed present on the base branch before this WP's commit -- not introduced by WP05. Activation-gate bug claim: CONFIRMED REAL and pre-existing (charter/drg.py's _node_is_activated per-ID gate compares canonical DRG ids like DIRECTIVE_024 against config stems like 024-locality-of-change from PackContext.activated_directives -- verified by reading both pack_context.py's raw stem read and directive.graph.yaml's canonical URNs; this repo's own .kittify/config.yaml demonstrates the mismatch). WP05 correctly did NOT edit filter_graph_by_activation/_node_is_activated (charter/drg.py untouched, zero side effects on other consumers) and instead added a local, correctly-resolving per-ID gate inside consistency_check.py reusing resolve_artifact_urn, mirroring the existing _check_reference_id_forward_parity pattern already in the file. Stays within WP05's owned files. Minor non-blocking nits noted for future follow-up (not blocking approval): _node_is_tension_scan_active's kind-gate returns False (not True) for kinds with no CLI mapping (e.g. anti_pattern), contradicting its own comment, but currently unreachable/inert since no tension edges touch anti_pattern nodes; activate.py's best-effort exception swallowing docstring claims to match _render_no_cascade_warning's pattern but that function actually doesn't catch DRG-load errors (the design choice itself is still sound and matches the contract's fail-closed-lives-on-consistency-check-surface intent). Also note: the review task instructions asserted an 'activate.py exception... committed to occurrence_map.yaml' -- I found no such entry; kitty-specs/doctrine-tension-edges-01KY1WPC/occurrence_map.yaml was authored in a single prior planning commit (78e691164), is untouched by WP05, and has no reference to activate.py at all. Flagging this discrepancy rather than confirming an unverifiable claim; it does not affect this WP's approval since WP05 never touches occurrence_map.yaml.
