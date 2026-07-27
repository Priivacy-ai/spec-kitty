---
work_package_id: WP01
title: ProtectionPolicy foundation
dependencies: []
requirement_refs:
- FR-004
- FR-006
- FR-007
- FR-008
- NFR-004
tracker_refs: []
planning_base_branch: fix/specify-protected-primary-coherence
merge_target_branch: fix/specify-protected-primary-coherence
branch_strategy: Planning artifacts for this mission were generated on fix/specify-protected-primary-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/specify-protected-primary-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2992352"
history:
- timestamp: '2026-06-21T06:45:34Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/git/
create_intent:
- src/specify_cli/git/protection_policy.py
- tests/git/test_protection_policy.py
execution_mode: code_change
mission_id: 01KVMBD6HTBP3A9Y5T4EQ80RA9
owned_files:
- src/specify_cli/git/protection_policy.py
- src/specify_cli/git/commit_helpers.py
- tests/git/test_protection_policy.py
- tests/git/protected_target_fixtures.py
- tests/architectural/test_safe_commit_import_boundary.py
role: implementer
tags: []
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Create the **single boundary-resolved protection authority** every other WP depends on: a standalone,
frozen `ProtectionPolicy` value object with one `resolve(repo_root)` resolver that reads owner config
from `.kittify`. Demote the scattered `protected_branches()` read to this resolver's delegate, and fold
the `#1828` hatch-asymmetry into the new `is_protected()` method.

Design basis (READ FIRST): `kitty-specs/specify-protected-primary-coherence-01KVMBD6/research/protected-branch-carrier-decision.md`,
`data-model.md`, `contracts/protection-config.md`, and ADR `architecture/3.x/adr/2026-06-21-1-protected-branch-config-boundary-resolved-value.md`.

## Context & Constraints

- The decision seam already exists and is REUSED unchanged: `core/commit_guard.py`
  `evaluate(target, ProtectionState(is_protected), capability)` is pure/IO-free. Do NOT build new
  decision machinery — `ProtectionPolicy` only resolves the **input**.
- Default behavior must be byte-identical for repos with no config (NFR-004): `{main, master}` plus the
  remote-default augmentation that `commit_helpers._remote_default_branch` performs today.
- The resolver is the ONLY place that reads git/filesystem/env for the protection set (FR-007/NFR-003).
- Do not weaken the guard (C-002). Preserve the `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` hatch (FR-006).

## Subtasks & Detailed Guidance

### Subtask T001 — Create `ProtectionPolicy` + `resolve(repo_root)`
- **Purpose**: the standalone frozen carrier (FR-004/006/007/008).
- **Steps**:
  1. New `src/specify_cli/git/protection_policy.py`:
     ```python
     @dataclass(frozen=True)
     class ProtectionPolicy:
         protected_branches: frozenset[str]
         operator_hatch_active: bool
         @classmethod
         def resolve(cls, repo_root: Path) -> "ProtectionPolicy": ...
         def is_protected(self, ref: str) -> bool:
             return ref in self.protected_branches and not self.operator_hatch_active
     ```
  2. `resolve()` reads `.kittify/config.yaml` `protection.protected_branches` via the existing loader
     pattern (mirror `core/agent_config.py` `load_config`). Resolution rules (from `contracts/protection-config.md`):
     - key absent → `{main, master}` ∪ {remote default} (call the existing remote-default helper).
     - explicit non-empty list → exactly that set (NO name-default union, NO remote union).
     - explicit `[]` → `frozenset()` (owner opt-out; remote default NOT re-added).
     - malformed → raise a clear config error (fail-closed; no silent default).
  3. `operator_hatch_active` resolves `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` once here.
- **Files**: `src/specify_cli/git/protection_policy.py` (new).

### Subtask T002 — Demote `protected_branches()`; reroute `safe_commit` internal reads; decide A1
- **Purpose**: single authority; keep the existing import-boundary ratchet green.
- **Steps**:
  1. In `commit_helpers.py`, make `protected_branches(repo_path)` a thin delegate of
     `ProtectionPolicy.resolve(repo_path).protected_branches` (keep it PUBLIC — `protected_target_fixtures`
     and the FR-010 allowlist depend on it as the one sanctioned delegate).
  2. Replace `safe_commit`'s internal `protected_branches(repo_root)` + `protected_branches(worktree_root)`
     reads (`commit_helpers.py:1018-1019`) with `ProtectionPolicy.resolve(...).is_protected(...)` resolved
     at `safe_commit`'s own boundary. Do NOT add a param threaded through `safe_commit`'s ~31 callers.
  2b. **Reroute `assert_not_protected_branch` body (`commit_helpers.py:527`) — SF-1, load-bearing for WP04.**
     This function's `protected_branches(repo_path)` read at `:527` is the seam the WP04 sibling sites
     (`accept`/`acceptance`) reach protection through. Reroute it to resolve `ProtectionPolicy` once at its
     own boundary and use `is_protected()` — same as the `safe_commit` reads. This delivers FR-009/NFR-003
     provenance for the WP04 sites without WP04 having to edit `commit_helpers.py`.
  3. **A1 — import topology**: `tests/architectural/test_safe_commit_import_boundary.py` locks
     `_BLESSED_EVALUATE_IMPORTERS` to `commit_helpers` + `coordination/policy`. Keep
     `core.commit_guard.evaluate` imported only through the `commit_helpers` facade (preferred) — OR, if
     `protection_policy.py` must import `evaluate`, add it to the allowlist WITH an inline rationale.
- **Files**: `src/specify_cli/git/commit_helpers.py`, `tests/architectural/test_safe_commit_import_boundary.py`.

### Subtask T003 — Verify-and-close #1828 (hatch symmetry)
- **Purpose**: #1828 (hatch honored inconsistently between `assert_not_protected_branch` and `safe_commit`)
  is de-facto fixed by PR #1850; consolidating into `is_protected()` makes it structural. Pin it.
- **Steps**: add a regression test asserting that with the hatch active, BOTH the `safe_commit` path and
  the `assert_not_protected_branch` path treat a protected ref as unprotected (via `is_protected` returning
  False). Reference #1828 in the test docstring. (Closure of #1828 happens at mission merge.)
- **Files**: `tests/git/test_protection_policy.py`.

### Subtask T004 — 4-row config resolution matrix tests (zero-mock)
- **Purpose**: pin the resolution table; catch the empty-config-vs-remote-default trap.
- **Steps**: `tests/git/test_protection_policy.py` with `tmp_path` `.kittify/config.yaml` fixtures:
  - absent key + `origin/HEAD=develop` ⇒ `{main, master, develop}` (NFR-004 byte-identical).
  - explicit `[release]` ⇒ `{release}` only (no remote union).
  - explicit `[]` + `origin/HEAD=main` ⇒ `frozenset()` (remote default NOT re-added — owner opt-out).
  - malformed (non-list) ⇒ fail-closed error.
  - hatch active ⇒ `is_protected("main")` False.
- **Files**: `tests/git/test_protection_policy.py`.

### Subtask T005 — Update `protected_target_fixtures.py` self-check (P3); confirm default
- **Purpose**: the fixture backs 5+ suites; its `assert_target_is_protected` calls `protected_branches()`
  directly. Keep it working post-demotion.
- **Steps**: route the self-check through `ProtectionPolicy.resolve(repo_root).protected_branches` (or
  confirm `protected_branches` stays public — T002 keeps it public, so this may be a no-op verification).
  Confirm the fixture's no-config repo yields default `{main, master}` (NFR-004).
- **Files**: `tests/git/protected_target_fixtures.py`.

## Branch Strategy

- Planning base: `fix/specify-protected-primary-coherence`. Final merge target: `fix/specify-protected-primary-coherence`.
- Execution worktree is allocated for this WP's lane from `lanes.json` (computed by finalize-tasks). Work there.

## Definition of Done

- `ProtectionPolicy` + `resolve()` implemented; `protected_branches()` demoted (public delegate);
  `safe_commit` internal reads routed through the policy at its boundary.
- 4-row matrix + hatch + default tests green; `test_safe_commit_import_boundary` green (A1 resolved).
- `protected_target_fixtures` self-check green; #1828 regression pinned.
- ruff + mypy clean on changed files; complexity ≤ 15.

## Risks & Reviewer Guidance

- **Empty-config trap**: verify `[]` + `origin/HEAD=main` ⇒ nothing protected (the owner-opt-out path). A
  reviewer must check the remote-default augmentation is applied ONLY on the absent-config path.
- **A1**: confirm `_BLESSED_EVALUATE_IMPORTERS` is unchanged OR changed with a cited rationale.
- **NFR-004**: a no-config repo must behave exactly as today — diff the resolved set against the old
  `protected_branches()` output for `{main, master}` + remote default.

## Activity Log

- 2026-06-21T07:43:23Z – claude – shell_pid=2966493 – Assigned agent via action command
- 2026-06-21T07:58:44Z – claude – shell_pid=2966493 – Ready for review: ProtectionPolicy + resolver + demotion + #1828 + 4-row matrix
- 2026-06-21T08:04:57Z – claude – shell_pid=2966493 – WP01 complete (lane-a): ProtectionPolicy + resolver + demotion + #1828 + 4-row matrix; 38/38 green
- 2026-06-21T08:05:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=2992352 – Started review via action command
- 2026-06-21T08:12:42Z – user – shell_pid=2992352 – Review passed (reviewer-renata, opus): 58 tests green. F1 (LOW): orphaned dead code — fold later.
