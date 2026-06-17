---
work_package_id: WP02
title: Lock-root consolidation + primary_root adoption (DEDUP + EMIT + WPL)
dependencies:
- WP01
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "3025749"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/workspace/root_resolver.py
- src/specify_cli/status/emit.py
- src/specify_cli/status/work_package_lifecycle.py
- tests/status/test_emit.py
- tests/status/test_work_package_lifecycle.py
- tests/specify_cli/coordination/test_worktree_topology.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read:
1. `spec.md` — **FR-001** (root adoption), **C-001** (no new authority), **C-008** (Fix-don't-litigate).
2. `plan.md` — **D-4** (the W9/W10 byte-identical collapse), **D-9** (IC-DEDUP / PR-1 lands before the
   EMIT/WPL fan out — this WP IS that combined unit), **IC-EMIT** / **IC-WPL**.
3. `contracts/behavioral-contracts.md` — **C-ROOT** (resolve from `workspace.primary_root`, CWD-invariant,
   deletion keeps the suite green, MUST NOT change the lock/anchor root value).
4. `research/pre-refactor/pedro-feasibility.md` — **PR-1** (the two bodies are byte-identical; they already
   delegate to `resolve_canonical_root` for the coord/lane arm — the residual is the primary/ad-hoc fallback)
   and `research/pre-refactor/SYNTHESIS.md`.

## Objective

`status/emit.py::_feature_status_lock_root` and `status/work_package_lifecycle.py::_repo_root_for_lock` are
**byte-identical** topology-aware lock-root resolvers. Two moves, in order:
1. **Consolidate** (pre-refactor, behavior-preserving): extract the shared body into ONE helper in
   `workspace/root_resolver.py`; both callsites delegate.
2. **Adopt** (FR-001): route that one helper to consume `workspace.primary_root` from the factory-projected
   context; delete the `.parent.parent` fallback walk.

Merged into one WP because both edits touch `emit.py` + `work_package_lifecycle.py` — separate WPs would
overlap ownership. C-001: `workspace/root_resolver.py` already exists (it owns `resolve_canonical_root`);
you are adding a function to it, not building new authority.

## Subtask guidance

### T007 — Extract the shared lock-root helper (PR-1, behavior-preserving)
Add e.g. `resolve_status_lock_root(feature_dir, repo_root=None)` to `workspace/root_resolver.py` carrying the
byte-identical body (topology classifier → `resolve_canonical_root` → the 3 `.parent.parent` fallbacks +
the `repo_root is not None` short-circuit). Point both `emit.py` and `work_package_lifecycle.py` at it. The
WP01 net + the existing `test_emit.py`/`test_work_package_lifecycle.py` MUST stay green (pure de-dup).

### T008 / T009 — Adopt `workspace.primary_root`, delete the walk
Route the helper's primary/ad-hoc fallback to consume `workspace.primary_root` from the factory context
(honor the boundary contract — read the real `mission_id`, do NOT re-derive `mid8`/`primary_root` inline,
spec §"Boundary contract"). **Delete** the `.parent.parent` walk. C-ROOT: the value MUST be identical to the
hand-rolled result (the WP01 equivalence rows prove it) and CWD-invariant. This is verification-by-deletion.

### T008 / T009 — adoption mechanism (D-12, post-squad clarification)
Route the helper to the **existing public pure resolver** `specify_cli.core.paths.resolve_canonical_root`
(`get_main_repo_root`) — do NOT thread an `ExecutionContext` and do NOT consume the composite fragment object
(the write-site files hold no context). `workspace/root_resolver.py` already re-exports `resolve_canonical_root`;
this is an import+call, not new authority (C-001). The symmetry proof (SC-002) is that read and write now call
the **same** resolver.

### T010 — Retire the private-helper by-name tests (across ALL importers)
WP01 added the PUBLIC lock-root invariant. Retire the tests that assert the **private helper by name** (paula
S-4/S-9) in `test_emit.py` / `test_work_package_lifecycle.py` **AND** update
`tests/specify_cli/coordination/test_worktree_topology.py`, which **imports `_feature_status_lock_root` /
`_repo_root_for_lock` by name** (pedro S-1 / paula B-2) — repoint it to the shared helper (or it ImportErrors
the whole coordination suite). DoD includes: `grep -rn "_feature_status_lock_root\|_repo_root_for_lock" tests/`
shows **zero** surviving by-name imports.

### T011 / T012 — Prove + clean
Run the WP01 net + the status/lifecycle suite **AND the full reachable caller surface**
(`pytest tests/status/ tests/specify_cli/write_side/ tests/specify_cli/coordination/`) — "suite green" must
cover the swap's reachable callers, not only the owned files (paula SF-3). **Mutation check (paula B-3):** with
the swap reverted, the WP01 net MUST go red — if it stays green the proof is vacuous. `ruff`/`mypy` clean ≤15,
no suppressions.

## Definition of Done
- [ ] One shared lock-root helper in `workspace/root_resolver.py`; emit + wpl delegate (no duplicate body).
- [ ] The `.parent.parent` lock-root walks are **deleted**; root comes from `workspace.primary_root`.
- [ ] WP01 net + `tests/status/` suite green (verification-by-deletion); the lock-root value is unchanged
      (C-ROOT equivalence) and CWD-invariant.
- [ ] Private-helper by-name tests retired; public invariant (WP01) carries the coverage.
- [ ] `ruff`/`mypy` clean ≤15, no suppressions. **C-008**: adjacent breakage fixed in-change.

## Reviewer guidance
Confirm the two bodies truly collapsed to one (no lingering duplicate). Confirm the deleted walk's value is
proven equal by the WP01 net, not just asserted. Grep the adopted helper for any inline `mission_id[:8]` /
`feature_dir.parent.parent` — there must be none (boundary contract / FR-005).

## Activity Log

- 2026-06-17T06:21:18Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – Assigned agent via action command
- 2026-06-17T06:39:52Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – WP02 lock-root consolidation+adoption complete (shared resolver, by-name tests retired + coord importer repointed, 871 pass). FORCE: flattened-mission guard. Orchestrator-driven.
- 2026-06-17T06:39:53Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3025749 – Started review via action command
- 2026-06-17T06:47:42Z – user – shell_pid=3025749 – FR-001 lock-root consolidation approved. One shared resolver in workspace/root_resolver.py; emit+wpl are thin shims (2-line delegation). Parent.parent walks deleted from both call sites. By-name test retirement complete (grep confirms zero surviving imports). Mutation check: 7 tests go RED on wrong return value, GREEN on correct implementation. Net edits in test_lock_root_invariant.py and test_characterization_root_walks.py are honest mechanical import-repoints to the shared resolver, not assertion loosening. Cast usage at follow_imports=skip boundary is genuine C-008 fix. ruff+mypy clean on production files. 871 pass.
