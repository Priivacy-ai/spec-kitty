---
work_package_id: WP05
title: Canonical Read Surfaces and Baseline Coverage
dependencies: []
requirement_refs:
- FR-008
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
agent: "claude:fable-5:reviewer-renata:reviewer"
shell_pid: "16773"
history:
- '2026-06-12: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/
execution_mode: code_change
owned_files:
- src/specify_cli/retrospective/gate.py
- src/specify_cli/cli/commands/agent_retrospect.py
- tests/architectural/test_execution_context_parity.py
- tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py
role: implementer
tags: []
---

# WP05 — Canonical Read Surfaces and Baseline Coverage

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its initialization declaration, boundaries, and governance scope for this WP.

## Objective

Finish the Class A strangler's last two stragglers: the retrospective completion gate and the retrospect command surface still read status events from the primary checkout's feature dir instead of the canonical status surface (FR-009, #1735 residuals). Pin the class shut with the AC10 architectural ratchet (FR-008e), and give the already-landed #1827 baseline-recording fix the regression test it never got (FR-010).

## Context

Read first: [contracts/class-a-residual-cleanups.md](../contracts/class-a-residual-cleanups.md) §A-r2/§A-r3, [research.md](../research.md) (Class A background), Class A section of [validation/debbie-analysis.md](../validation/debbie-analysis.md).

The canonical read authority is `resolve_status_surface` (landed with PR #1850's strangler; see its existing consumers for the call shape — grep `resolve_status_surface` in `src/`). Under coordination topology, the authoritative `status.events.jsonl` lives in the coordination worktree; `resolved.feature_dir` is identity-only and reading events through it is exactly the #1735 bug class.

Remaining out-of-scope stragglers (implement.py C-004 fallback etc.) belong to the #1666 umbrella — touch ONLY the two sites below (C-001).

## Subtasks

### T024 — Route the retrospective gate

`retrospective/gate.py:597` (re-locate: the completion-gate event read): obtain events via `resolve_status_surface` instead of any `resolved.feature_dir`-anchored direct read. Add/extend a unit test in the retrospective suite proving the gate sees coord-worktree events when primary and coord surfaces diverge (fixture: write an event only to the coord surface; gate must see it).

### T025 — Route the retrospect command surface

`cli/commands/agent_retrospect.py:432` (the identity-path read): same routing, same divergence-fixture test shape. While there, add the AC7 docstring note on `ResolvedMission.feature_dir` ONLY if that dataclass lives in a file this WP owns — otherwise leave it to the #1666 umbrella (no out-of-ownership edits without rationale).

### T026 — AC10 architectural ratchet (AFTER T024/T025)

Extend `tests/architectural/test_execution_context_parity.py`: forbid `resolved.feature_dir`-anchored `read_events()` calls or direct `status.events.jsonl` opens outside the surface-resolver module(s). Follow the suite's existing AST-walking conventions. Scope the ratchet to the two known read families (research/risks: avoid false positives on legitimate identity uses of `feature_dir`). It must FAIL if T024/T025 are reverted — verify by temporary revert locally.

### T027 — Baseline-recording regression test (AC-A3)

The #1827 defect (post-merge baseline validation running before `baseline_merge_commit` is written) was fixed in rc42 (`9c8bff06f`) but has no regression test. In `tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py`, the baseline helpers are mocked out at `:224-225` — either unmock them there or add a sibling test: run a real coord-topology merge and assert `git show <target>:kitty-specs/<slug>/meta.json` contains `baseline_merge_commit` with the merged SHA. Document the crash-between-record-and-commit re-run edge in the test docstring as known bounded behavior (its fix is in the #1666 umbrella, NOT this WP).

## Branch Strategy

Planning base and merge target are both `main`. Execution worktree/branch come from `lanes.json` via `spec-kitty agent action implement WP05 --agent <name>`. Landing on origin/main via PR only (C-005).

## Definition of Done

- [ ] Both read sites routed through `resolve_status_surface`; divergence-fixture tests prove coord-surface reads (T024/T025)
- [ ] AC10 ratchet green, and red under local revert of T024/T025 (T026)
- [ ] Baseline regression test green against real (unmocked) recording (T027)
- [ ] No edits outside owned_files without a recorded one-line rationale
- [ ] ruff + mypy --strict zero suppressions; ≥90% changed-line coverage; existing ratchets green (NFR-005); terminology guard before push

## Risks & Reviewer Guidance

- **Ratchet false positives** are the main risk: reviewer, run AC10 against the whole tree and confirm zero hits outside the two fixed sites before approving.
- T027's unmocking may slow the suite — keep the real-merge fixture minimal (1 lane is enough for baseline recording).
- Reviewer: confirm neither file touched by T024/T025 re-derives coord paths inline (that would be a new Class A instance — route, don't re-derive).

## Activity Log

- 2026-06-12T12:21:04Z – claude – T024/T025: gate.py + agent_retrospect.py event reads routed through resolve_status_surface with legacy fallback; divergence-fixture tests prove coord-surface reads (new tests/retrospective/test_canonical_read_surface_1735.py — rationale: T024/T025 mandate retrospective-suite tests; new file avoids unowned files). T026: AC10 AST ratchet in test_execution_context_parity.py, scoped to the two read families + seam anti-vacuity; verified RED under revert. T027: real (unmocked) baseline recording regression test in test_merge_coord_topology_1772.py asserting git show main:meta.json carries baseline_merge_commit; crash-window re-run edge documented. ruff exit 0; mypy --strict gate.py clean (agent_retrospect.py has 2 PRE-EXISTING exc errors at HEAD, unchanged); pytest parity+merge-coord+retrospective+integration+retrospect-cli+terminology: 592 passed exit 0.
- 2026-06-12T12:21:58Z – claude:fable-5:reviewer-renata:reviewer – shell_pid=16773 – Started review via action command
- 2026-06-12T12:26:57Z – user – shell_pid=16773 – Review passed: T024/T025 routed through resolve_status_surface seams with no inline coord-path re-derivation; AC10 ratchet green and verified RED under revert of both source files (anti-vacuity confirmed independently); T027 baseline regression test runs real unmocked _record_baseline_merge_commit and asserts git show target:meta.json; divergence-fixture tests pass; ruff exit 0, mypy --strict gate.py clean, agent_retrospect.py 2 exc errors pre-existing at merge-base (line-shifted only); module-scoped ratchet and new test file deviations judged acceptable per task-text pre-authorization.
