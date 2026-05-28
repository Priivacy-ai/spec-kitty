---
work_package_id: WP04
title: CoordinationWorkspace service + lane sparse-checkout policy
dependencies:
- WP03
requirement_refs:
- C-011
- FR-004
- FR-006
- FR-007
- FR-024
- FR-025
- FR-029
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-coordination-branch-atomic-event-log-01KSPTVW
base_commit: fc1aa41f62840ca1fa430e2d8fc372f384fc5421
created_at: '2026-05-28T11:07:10.230223+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: "claude:opus:reviewer-rita:reviewer"
shell_pid: "27575"
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 2 design
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/coordination/
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/__init__.py
- src/specify_cli/coordination/workspace.py
- src/specify_cli/lanes/**
- src/specify_cli/cli/commands/doctor.py
- tests/specify_cli/coordination/test_workspace.py
- tests/specify_cli/coordination/test_sparse_checkout.py
- tests/specify_cli/lanes/**
- tests/specify_cli/cli/commands/test_doctor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

Introduce the `src/specify_cli/coordination/` package with `CoordinationWorkspace`, the service that manages the per-mission coordination worktree at `.worktrees/<slug>-<mid8>-coord/`. Update the lane allocator to (a) parent each lane branch on the coordination branch, and (b) register the sparse-checkout policy that excludes `status.events.jsonl` and `status.json` from lane working trees. Add doctor checks for sparse-checkout drift and coordination worktree health.

## Context

**Spec source**: FR-024, FR-025, FR-029, C-011, RR-01.
**Predecessor WPs**: WP01, WP02 (PR 1), WP03 (coordination branch exists).
**Contract**: `contracts/coordination_workspace.md` — read first.

**Why sparse-checkout (not filesystem move)**: see `research.md` → R-003. Backward compatible; status files stay under `kitty-specs/<mission>/`; only lane worktrees see them as absent.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Lane B; sequential after WP03.

---

## Cross-review amendments (SUPERSEDE the code skeletons below where they conflict)

1. **Sparse-checkout path resolution**: The skeleton in T016 wrote literally to `.git/info/sparse-checkout`. In linked git worktrees, `.git` is a **file** pointing to a per-worktree gitdir, not a directory. The correct path comes from `git -C <worktree> rev-parse --git-path info/sparse-checkout`. Use that, or use `git sparse-checkout set --no-cone <patterns>` which handles the resolution automatically. The contract file `contracts/coordination_workspace.md` shows the corrected pattern; follow it.

2. **`CoordinationWorkspace.resolve()` normalizes the HEAD comparison**: When verifying a reused worktree's branch, normalize via `actual = symbolic_ref_head.removeprefix("refs/heads/")` and compare to the SHORT branch name. The earlier skeleton's `if actual != f"refs/heads/{branch}" and actual != branch:` is OK as a transitional check; the canonical form is "always short". (C-016.)

3. **The lane allocator does NOT directly modify status files**. Today the allocator may copy or symlink `kitty-specs/<mission>/` artifacts. After this WP, lane worktrees rely on git sparse-checkout to hide `status.events.jsonl` and `status.json`; the allocator does not need to interact with those files directly.

---

## Subtask T015: `CoordinationWorkspace` service

**Purpose**: Resolve/create/teardown the coordination worktree. Idempotent. Single source of truth for "where is the coord worktree for mission X?".

**Steps**:
1. Create `src/specify_cli/coordination/__init__.py` (re-export public surface).
2. Create `src/specify_cli/coordination/workspace.py` with:
   ```python
   from pathlib import Path
   import subprocess

   class CoordinationWorkspaceBranchMismatch(Exception):
       """Worktree exists but is checked out to a different branch."""
       def __init__(self, *, worktree_path: Path, expected_ref: str, actual_ref: str):
           self.worktree_path = worktree_path
           self.expected_ref = expected_ref
           self.actual_ref = actual_ref
           super().__init__(
               f"Coordination worktree at {worktree_path} is on {actual_ref!r}, "
               f"expected {expected_ref!r}. Manual intervention required."
           )

   class CoordinationWorkspace:
       @staticmethod
       def worktree_path(repo_root: Path, mission_slug: str, mid8: str) -> Path:
           return repo_root / ".worktrees" / f"{mission_slug}-{mid8}-coord"

       @staticmethod
       def branch_name(mission_slug: str, mid8: str) -> str:
           return f"kitty/mission-{mission_slug}-{mid8}"

       @classmethod
       def resolve(cls, repo_root: Path, mission_slug: str, mid8: str) -> Path:
           """Return the coordination worktree path. Create if missing. Verify ancestry on reuse."""
           path = cls.worktree_path(repo_root, mission_slug, mid8)
           branch = cls.branch_name(mission_slug, mid8)
           if path.exists():
               # verify HEAD matches expected branch
               actual = subprocess.check_output(
                   ["git", "-C", str(path), "symbolic-ref", "HEAD"],
                   text=True,
               ).strip()
               if actual != f"refs/heads/{branch}" and actual != branch:
                   raise CoordinationWorkspaceBranchMismatch(
                       worktree_path=path, expected_ref=branch, actual_ref=actual,
                   )
               return path
           # create via git worktree add
           subprocess.run(
               ["git", "-C", str(repo_root), "worktree", "add", str(path), branch],
               check=True,
           )
           return path

       @classmethod
       def teardown(cls, repo_root: Path, mission_slug: str, mid8: str) -> None:
           """Remove worktree (idempotent). Does NOT delete the branch."""
           path = cls.worktree_path(repo_root, mission_slug, mid8)
           if not path.exists():
               return
           subprocess.run(
               ["git", "-C", str(repo_root), "worktree", "remove", str(path), "--force"],
               check=False,  # ignore if already removed
           )

       @classmethod
       def is_present(cls, repo_root: Path, mission_slug: str, mid8: str) -> bool:
           return cls.worktree_path(repo_root, mission_slug, mid8).exists()
   ```
3. Add docstrings explaining the contract. Add stable error codes via the exception class.

**Files**:
- `src/specify_cli/coordination/__init__.py`
- `src/specify_cli/coordination/workspace.py`

**Validation**:
- [ ] `CoordinationWorkspace.resolve()` creates the worktree on first call.
- [ ] Second call returns the same path without re-creating.
- [ ] Mismatched HEAD raises `CoordinationWorkspaceBranchMismatch`.

## Subtask T016: Sparse-checkout policy at lane worktree creation

**Purpose**: Lane worktrees must NOT contain `status.events.jsonl` or `status.json`. Register the exclusion pattern at worktree creation.

**Steps**:
1. Define a module-level constant in `src/specify_cli/coordination/workspace.py`:
   ```python
   def lane_sparse_checkout_patterns(mission_slug: str, mid8: str) -> list[str]:
       """Return the lane sparse-checkout pattern lines (one per line)."""
       mission_dir = f"{mission_slug}-{mid8}"  # matches the kitty-specs/<dir> name
       return [
           "/*",  # include everything by default
           f"!kitty-specs/{mission_dir}/status.events.jsonl",
           f"!kitty-specs/{mission_dir}/status.json",
       ]
   ```
2. Create a helper `register_lane_sparse_checkout(lane_worktree_path, mission_slug, mid8)`:
   ```python
   def register_lane_sparse_checkout(lane_path: Path, mission_slug: str, mid8: str) -> None:
       subprocess.run(
           ["git", "-C", str(lane_path), "sparse-checkout", "init", "--no-cone"],
           check=True,
       )
       patterns = lane_sparse_checkout_patterns(mission_slug, mid8)
       sparse_file = lane_path / ".git" / "info" / "sparse-checkout"
       # Note: with git worktrees, `.git` is a file pointing to the gitdir, not a directory.
       # Resolve the actual sparse-checkout path:
       gitdir = subprocess.check_output(
           ["git", "-C", str(lane_path), "rev-parse", "--git-dir"], text=True,
       ).strip()
       sparse_file = Path(gitdir) / "info" / "sparse-checkout"
       sparse_file.write_text("\n".join(patterns) + "\n")
       subprocess.run(
           ["git", "-C", str(lane_path), "read-tree", "-mu", "HEAD"],
           check=True,
       )
   ```
3. Document the gotcha: `git worktree` uses a `.git` *file*, not a directory. The sparse-checkout config lives in the per-worktree gitdir.

**Files**:
- `src/specify_cli/coordination/workspace.py`

**Validation**:
- [ ] After calling `register_lane_sparse_checkout()`, the lane worktree's filesystem does NOT contain the two status files.
- [ ] The primary checkout and coordination worktree still contain the files.

## Subtask T017: Lane allocator updates — parent on coordination branch

**Purpose**: When `finalize-tasks` or `implement` allocates a lane worktree, it must (a) parent the lane branch on the coordination branch (not on `main`), and (b) call `register_lane_sparse_checkout()`.

**Steps**:
1. Locate the lane allocator (likely `src/specify_cli/lanes/allocator.py` or similar). Search for `git worktree add` invocations.
2. Update the worktree creation logic:
   - Resolve the coordination branch from `meta.json` (`coordination_branch` field).
   - Create the lane branch parented on the coordination branch:
     ```python
     subprocess.run(
         ["git", "-C", str(repo_root), "branch",
          lane_branch_name, coordination_branch],
         check=True,
     )
     ```
   - Add the worktree:
     ```python
     subprocess.run(
         ["git", "-C", str(repo_root), "worktree", "add",
          str(lane_worktree_path), lane_branch_name],
         check=True,
     )
     ```
   - Call `register_lane_sparse_checkout(lane_worktree_path, mission_slug, mid8)`.
3. If the mission is on the legacy topology (no `coordination_branch` field in `meta.json`), fall back to the existing behavior (parent on target branch, no sparse-checkout). WP08 will refine this; for now, just preserve the legacy path.

**Files**:
- `src/specify_cli/lanes/allocator.py` (or wherever lane allocation lives)
- Possibly `src/specify_cli/lanes/lanes.py`

**Validation**:
- [ ] Lane branches created for new-topology missions are parented on the coordination branch.
- [ ] Lane branches for legacy missions are still parented on the target branch.
- [ ] Lane worktrees have the sparse-checkout pattern registered.

## Subtask T018: Unit tests — coordination workspace + sparse-checkout

**Purpose**: Verify the lifecycle, idempotency, and sparse-checkout effect.

**Steps**:
1. Create `tests/specify_cli/coordination/test_workspace.py`:
   - `test_resolve_creates_worktree()` — fresh repo + coord branch; resolve creates worktree.
   - `test_resolve_reuses_existing()` — call twice; second is no-op.
   - `test_resolve_branch_mismatch_raises()` — manually check out wrong branch in coord worktree → raises `CoordinationWorkspaceBranchMismatch`.
   - `test_teardown_idempotent()` — call teardown twice; second is no-op.
   - `test_is_present()` — before/after resolve.
2. Create `tests/specify_cli/lanes/test_sparse_checkout.py`:
   - `test_lane_sparse_checkout_excludes_status_files()` — create lane worktree; assert filesystem does not contain `status.events.jsonl` or `status.json`.
   - `test_primary_checkout_unaffected()` — verify the primary checkout still has the files.
3. Use the `tmp_repo_with_mission` fixture (create if missing) that sets up a tmp repo with `mission create` already run.

**Files**:
- `tests/specify_cli/coordination/__init__.py`
- `tests/specify_cli/coordination/test_workspace.py`
- `tests/specify_cli/lanes/test_sparse_checkout.py`

**Validation**:
- [ ] All tests pass.
- [ ] Coverage on `src/specify_cli/coordination/workspace.py` ≥ 90%.

## Subtask T019: Doctor command — sparse-checkout drift + coord worktree health

**Purpose**: `spec-kitty doctor` gains two new checks. Operators can detect when sparse-checkout has been manually edited or the coord worktree is missing.

**Steps**:
1. Locate the doctor command (likely `src/specify_cli/cli/commands/doctor.py`).
2. Add a check function for each active mission:
   ```python
   def _check_coordination_worktree_health(repo_root: Path, mission_meta: dict) -> list[DoctorFinding]:
       """Verify the coordination worktree exists, is on the right branch, has a clean tree."""

   def _check_lane_sparse_checkout_drift(repo_root: Path, mission_meta: dict) -> list[DoctorFinding]:
       """For each lane worktree of this mission, verify the sparse-checkout pattern is current."""
   ```
3. Register both checks in the doctor's check list (alongside existing checks).
4. Each finding includes severity (warning vs error), a message, and a "next step" — typically `spec-kitty agent worktree repair --mission <handle>` (note: the `repair` subcommand is a planned addition, mentioned in `quickstart.md`; if it doesn't exist yet, log a TODO and add a `--dry-run-fix` flag that prints what would be done).
5. Add a check that git version is ≥ 2.25 (RR-01). If older, emit a setup error.

**Files**:
- `src/specify_cli/cli/commands/doctor.py`
- `tests/specify_cli/cli/commands/test_doctor.py`

**Validation**:
- [ ] Doctor passes on a freshly created mission.
- [ ] Manually delete the coordination worktree → doctor surfaces a warning.
- [ ] Manually edit `.git/info/sparse-checkout` in a lane → doctor surfaces a warning.
- [ ] On a mock git < 2.25 (patch the version-detection call) → doctor surfaces a setup error.

---

## Definition of Done

- [ ] All 5 subtasks complete (T015..T019).
- [ ] `pytest tests/specify_cli/coordination/` and `tests/specify_cli/lanes/test_sparse_checkout.py` pass.
- [ ] Doctor checks pass on a freshly-created mission and warn on drift.
- [ ] `mypy --strict src/specify_cli/coordination/` passes.
- [ ] CHANGELOG entry noting the new minimum git version (2.25).

## Risks

- **`.git` is a file in worktrees, not a directory.** Many helpers that assume `.git/info/sparse-checkout` is at a known relative path will fail. Always resolve via `git rev-parse --git-dir` from inside the worktree.
- **Lane sparse-checkout pattern requires non-cone mode** (`--no-cone`). Cone mode does not support negation. Don't accidentally use cone mode.
- **Doctor checks must be fast.** They run on every CLI invocation in some configurations. Cache `git worktree list` results within a single command invocation.

## Reviewer guidance

1. **Idempotency**: `resolve()` and `teardown()` must be safe to call multiple times. No-op on already-correct state, no errors.
2. **HEAD verification on reuse**: `resolve()` checks that an existing worktree is on the expected branch. Mismatch is a structured error.
3. **Sparse-checkout exclusion format**: confirm the patterns use `!` for exclusion and `--no-cone` mode is set.
4. **Lane allocator behavior**: confirm new-topology missions parent on coord branch; legacy missions parent on target.
5. **Doctor messages**: are they actionable? Do they name a `next_step` command?

## References

- Spec: FR-024, FR-025, FR-029, C-011, RR-01
- Plan: PR 2 step 4
- Contract: [`contracts/coordination_workspace.md`](../contracts/coordination_workspace.md)
- Research: R-003 in [`research.md`](../research.md)

## Activity Log

- 2026-05-28T11:07:10Z – claude:opus:implementer-ivan:implementer – shell_pid=21883 – Assigned agent via action command
- 2026-05-28T11:19:56Z – claude:opus:implementer-ivan:implementer – shell_pid=21883 – WP04 ready for review
- 2026-05-28T11:20:56Z – claude:opus:reviewer-rita:reviewer – shell_pid=27575 – Started review via action command
- 2026-05-28T11:22:26Z – claude:opus:reviewer-rita:reviewer – shell_pid=27575 – Review passed: T015-T019 all met. CoordinationWorkspace + stable error code present; lane sparse-checkout uses git rev-parse --git-path (no literal .git/info/); allocator parents on coord branch when meta.json declares it and falls back to mission_branch otherwise; doctor runs git>=2.25, coord-worktree health, and lane sparse-checkout drift. 28/28 tests pass; mypy --strict clean on owned files. Caveats: (1) _compose_mission_dir defensive double-mid8 guard accepted -- correct behavior, idempotent against either slug shape, low blast radius; future WP08 cleanup may consolidate slug helpers. (2) tests/specify_cli/coordination/__init__.py accepted -- needed pytest package marker, trivial. (3) test_doctor_coordination.py accepted -- frontmatter-listed file does not exist; sibling test_doctor_*.py pattern preserves convention. (4) 'doctor coordination' subcommand name accepted -- avoids confusion with retired 'doctor sparse-checkout' semantics.
