---
work_package_id: WP03
title: Status root-walk adoption (lifecycle_events + store)
dependencies:
- WP01
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "3029545"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/status/lifecycle_events.py
- src/specify_cli/status/store.py
- tests/status/test_lifecycle_events.py
- tests/status/test_store.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read: `spec.md` **FR-001** + **C-008**; `plan.md` **IC-LE** / **IC-STORE**;
`contracts/behavioral-contracts.md` **C-ROOT**; `research/pre-refactor/pedro-feasibility.md` **PR-3** (the
store ancestor-scan early-return tidy is free boy-scout once the net exists).

## Objective

Route two small status root-resolution sites to the **existing public resolver**
`specify_cli.core.paths.resolve_canonical_root` (`get_main_repo_root`) — NOT an `ExecutionContext` thread, NOT
a new authority (D-12, C-001) — and delete the walks. Merged (two tiny same-concern status sites, disjoint
files). FR-001, verification-by-deletion (mutation check: reverting a swap must turn the WP01 net red).

## Subtask guidance

### T013 — lifecycle_events.py
Replace the `.parent.parent` / `.parent.parent.parent` walks with `workspace.primary_root` consumed from the
factory context. Honor the boundary contract (no inline `mid8`/`primary_root` re-derivation). Delete the walk.

### T014 — store.py ancestor scan (+ PR-3 tidy)
Replace the `KITTY_SPECS_DIR` ancestor scan in `store.py::_find_mission_specs_root` with
`workspace.primary_root`. While here (C-008 boy-scout, PR-3): normalize the `candidate`-vs-`two_up` decision
to an early-return / named predicate — but do NOT change the best-effort fallback semantics (the WP01 store
characterization rows pin them). Delete the scan.

### T015 / T016 — Prove + clean
WP01 net + `tests/status/test_lifecycle_events.py` + `tests/status/test_store.py` green. `ruff`/`mypy` clean.

## Definition of Done
- [ ] Both root walks deleted; root from `workspace.primary_root`; values unchanged (C-ROOT equivalence, WP01).
- [ ] WP01 net + the two `tests/status/` modules green (verification-by-deletion).
- [ ] PR-3 store tidy applied without changing fallback semantics.
- [ ] `ruff`/`mypy` clean ≤15, no suppressions. **C-008**: adjacent breakage fixed in-change.

## Reviewer guidance
Confirm the deleted scans' values are proven equal by the WP01 net (especially the store deeper-nesting /
non-kitty-specs fallback rows). No inline re-derivation remains (FR-005).

## Activity Log

- 2026-06-17T06:21:22Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – Assigned agent via action command
- 2026-06-17T06:40:54Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – WP03 status root-walks complete (lifecycle+store -> resolve_canonical_root, 85 pass, behavioral mutation check bites). FORCE: flattened-mission guard. Orchestrator-driven.
- 2026-06-17T06:40:56Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3029545 – Started review via action command
- 2026-06-17T06:45:05Z – user – shell_pid=3029545 – APPROVED. Net-oracle edit is genuine convergence: WP01 lane-a pinned lifecycle coord row as worktree_root (divergent before-value); WP03 adopts resolve_canonical_root which follows the worktree pointer to return main_root — oracle row legitimately updates from worktree_root to main_root. Live mutation check confirmed: resolver returns main_root (not worktree_root) in real coord topology. Both .parent.parent walks deleted; resolve_canonical_root routed from workspace.root_resolver (D-12 re-export from core.paths). store _find_mission_specs_root has correct fallback via _best_effort_specs_root for non-git dirs (PR-3 semantics preserved). git init in fixtures is topology-true: resolve_canonical_root requires a real git repo — the fixture correctly materialises it. ruff+mypy clean, C901 clean, 85 tests pass, no suppressions, no dead code, no frozen-surface violations.
