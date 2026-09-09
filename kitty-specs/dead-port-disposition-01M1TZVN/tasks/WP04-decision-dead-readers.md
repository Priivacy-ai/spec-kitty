---
work_package_id: WP04
title: decision.py Dead DSL Readers
dependencies: []
requirement_refs:
- C-001
- FR-015
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dead-port-disposition-01M1TZVN
base_commit: 1ceba9f2259968b99f5bb85cdc56e38c92622489
created_at: '2026-09-06T18:33:35.555051+00:00'
subtasks:
- T016
- T017
phase: Wave 0 - Post-Mission-A deletion
agent: claude
history:
- at: '2026-09-06T12:40:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/decision.py
- tests/next/test_decision_unit.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – `decision.py` Dead DSL Readers

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

FR-015 via decision OD9 (`01M1VAHS32VMZPYYXWKW7D2KPG`): this small WP owns `src/runtime/next/decision.py` alone and deletes the two `.. deprecated:: 2.0.0` dead DSL readers. **Mission-level gate (C-001)**: `decision.py` is one of Mission A's four shared files (A's WP05 edits `:373`); claim this WP only after Mission A has merged into the branch. If `git log` does not show Mission A's merge, stop and report.

Done means:

- `derive_mission_state` (`decision.py:187-216`) and `evaluate_guards` (`:218-235`), including their deprecation blocks and the lazy `from specify_cli.mission_v1.events import read_events` at `:200`, are deleted. Nothing else in the file changes (Mission A's WP05 edits around `:369-377` must be preserved exactly).
- `tests/next/test_decision_unit.py`: the `derive_mission_state` import (`:28`) and the legacy section (`:189-219`) are deleted; the rest of the file is untouched.
- Zero callers proven (`runtime_bridge_cores`' `evaluate_guards*` family is an unrelated same-name function — say so in the Activity Log with the grep output).
- `tests/next`, `tests/runtime/next`, and `tests/architectural/test_layer_rules.py` green; the runtime ledger row `mission_v1` stays (live edge `next_invocation_lifecycle.py:332`).

## Context & Constraints

- Spec FR-015, C-001, edge case "Mission A's WP05 lane still open at tasks-time" (resolved: OD9 → this WP). Contract `contracts/dsl-retirement.md` §5. Data model §5 last row. Research §2 OD9, §3 D-3.
- If WP01 (DSL retirement) has already landed, `mission_v1.events.read_events` still exists (events.py survives) — the deletion here is independent of WP01's order.
- C-007: run `test_runtime_ledger_has_no_stale_entries`; no ledger edit is expected.
- Sonar/CLAUDE.md rules; no `# noqa`.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP04 --mission dead-port-disposition-01M1TZVN`.

## Subtasks & Detailed Guidance

### Subtask T016 – Zero-caller proof

- **Purpose**: Deleting a function with a hidden caller is the classic dead-code mistake in reverse.
- **Steps**: `grep -rn "derive_mission_state" src tests docs`; `grep -rn "evaluate_guards" src tests | grep -v runtime_bridge_cores`; confirm the only hits are the two definitions in `decision.py` and `tests/next/test_decision_unit.py`. Also AST-scan `src/` for `Attribute`/`Name` calls of both names (a five-line script, paste it and its output into the Activity Log). Confirm `next_invocation_lifecycle.py:332` is the remaining `mission_v1.events` consumer.
- **Files**: none (proof only).
- **Parallel?**: No.

### Subtask T017 – Delete the readers and their legacy tests

- **Purpose**: FR-015.
- **Steps**: read `decision.py:180-240` first (verify the current line numbers; Mission A's merge may have shifted them). Delete both functions whole (decorators, docstrings, bodies) and the now-unused lazy import; remove any now-unused top-level imports (`ruff` will flag them). In `tests/next/test_decision_unit.py`, delete the `derive_mission_state` import from the import block (`:28`) and the `# derive_mission_state (legacy)` section (`:189-219`). Run the tests. Confirm `git diff --stat` shows exactly two files.
- **Files**: `src/runtime/next/decision.py`, `tests/next/test_decision_unit.py`.
- **Parallel?**: No.

## Test Strategy

```bash
.venv/bin/pytest tests/next tests/runtime/next tests/runtime/test_bridge_decision_builder.py tests/runtime/test_bridge_decide_next.py -q
.venv/bin/pytest tests/architectural/test_layer_rules.py -q
PWHEADLESS=1 make test-fast
.venv/bin/ruff check src/runtime/next/decision.py tests/next/test_decision_unit.py && .venv/bin/mypy src/runtime/next/decision.py
```

## Risks & Mitigations

- Line drift after Mission A's merge → re-read before deleting; delete by function name, not by line.
- A hidden consumer in `docs/` code samples → grep `docs`; reword if found (docs are not owned — note it).

## Review Guidance

- Two-file diff; both functions gone; Mission A's `:369-377` hunk intact; proof pasted; ledger green.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T12:40:00Z – system – Prompt created.
- 2026-09-06T18:46:12Z – claude – shell_pid=88278 – T016 zero-caller proof. grep -rn derive_mission_state src tests docs -> src/runtime/next/decision.py:14 (docstring), :190 (def); tests/next/test_decision_unit.py:28,189,195,198,211,219; tests/next/test_query_mode_unit.py:39,41,44 (UNDOCUMENTED consumer test_derive_mission_state_imports_legacy_events_lazily); tests/architectural/test_no_dead_symbols.py:3244 (_WIDENED_SCOPE_GRANDFATHERED_470 row); docs hits only in two single-line census JSONs under docs/reports/test-sanitation/ (data, not code). grep -rn evaluate_guards src tests | grep -v runtime_bridge_cores -> the only decision.py-bound hits are decision.py:14,:221 and test_decision_unit.py:29,223,234-406; every other hit (runtime_bridge.py, runtime_bridge_io.py, runtime_bridge_composition.py, tests/runtime/*, tests/next/test_runtime_bridge_unit.py:1149, tests/dossier/*) names runtime_bridge_cores' unrelated evaluate_guards/evaluate_guards_strict(snapshot) family, plus test_no_dead_symbols.py:3245 grandfathered row.
- 2026-09-06T18:46:13Z – claude – shell_pid=88278 – T016 AST scan (5 lines): import ast,pathlib; NAMES={'derive_mission_state','evaluate_guards'}; for p in pathlib.Path('src').rglob('*.py'): for n in ast.walk(ast.parse(p.read_text())): if isinstance(n,ast.Call) and ((isinstance(n.func,ast.Name) and n.func.id in NAMES) or (isinstance(n.func,ast.Attribute) and n.func.attr in NAMES)): print(p,n.lineno,ast.unparse(n.func)). Output: EMPTY (exit 0) -> zero Name/Attribute calls of either symbol anywhere in src/. mission_v1.events consumers outside the package after deletion: only src/runtime/next/next_invocation_lifecycle.py:332 (emit_event) -> mission_v1 ledger row stays; no ledger edit.
- 2026-09-06T18:46:15Z – claude – shell_pid=88278 – T017 done. Deleted derive_mission_state, evaluate_guards, their deprecation blocks, the lazy read_events import, the private helper _describe_guard (only reachable from evaluate_guards), the now-unused SimpleNamespace import, and the docstring sentence claiming the readers were preserved. test_decision_unit.py: import lines + both legacy sections (TestDeriveMissionState, TestEvaluateGuards) removed; two method-local 'import json' re-imports at the DecisionKind serialisation tests dropped because ruff F811 fired once the legacy section stopped being the first user of module-level json (HEAD was ruff-clean; knock-on, not pre-existing). DEVIATION: git diff --stat shows THREE files, not two -> tests/next/test_query_mode_unit.py:39-45 held an undocumented consumer (test_derive_mission_state_imports_legacy_events_lazily); it was deleted rather than left red. Mission A WP05 materialize_snapshot hunk untouched. Verification: pytest tests/next tests/runtime/next tests/runtime/test_bridge_decision_builder.py tests/runtime/test_bridge_decide_next.py tests/runtime/test_run_state_hardening.py -n 3 --dist loadfile -> 661 passed; pytest tests/architectural/test_layer_rules.py test_no_dead_symbols.py test_cold_import_status_boundary.py -> 89 passed; ruff check + ruff format --check clean; mypy decision.py: no issues (same as HEAD). FOLLOW-UP (not owned): test_no_dead_symbols.py:3244-3245 _WIDENED_SCOPE_GRANDFATHERED_470 rows for the two deleted symbols are now orphaned but do not red the gate; left for WP03 (which owns that file's re-pins) to prune.
- 2026-09-06T19:07:05Z – claude – shell_pid=23592 – Independent review (claude): APPROVED at 82523b2ab. Reproduced: grep+AST zero-caller proof; 661 passed behavioural set (-n 3 loadfile); 89 passed gates incl. 42 ledger tests; ruff check + mypy clean. Deviations accepted: 3-file diff (test_query_mode_unit.py undocumented consumer), _describe_guard + SimpleNamespace + two method-local json imports removed as knock-on. Non-blocking: ruff format --check drift is pre-existing on base (identical 7/5 hunks); WP03 prompt does NOT cover pruning the two orphaned _WIDENED_SCOPE_GRANDFATHERED_470 rows for runtime.next.decision::derive_mission_state/evaluate_guards -- WP03 T014 should prune them when it edits test_no_dead_symbols.py.
