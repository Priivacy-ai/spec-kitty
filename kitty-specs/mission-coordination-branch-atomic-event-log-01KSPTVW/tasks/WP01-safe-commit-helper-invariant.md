---
work_package_id: WP01
title: safe_commit() helper signature change with HEAD assertion
dependencies: []
requirement_refs:
- C-015
- FR-001
- FR-002
- FR-013
- FR-031
- NFR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-coordination-branch-atomic-event-log-01KSPTVW
base_commit: fc1aa41f62840ca1fa430e2d8fc372f384fc5421
created_at: '2026-05-28T09:54:33.879761+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "opencode"
shell_pid: "88227"
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 1 design
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/git/commit_helpers.py
execution_mode: code_change
owned_files:
- src/specify_cli/git/commit_helpers.py
- tests/specify_cli/git/test_commit_helpers.py
- CHANGELOG.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

Make `destination_ref` a **required keyword-only parameter** on `safe_commit()` and add an internal `HEAD == destination_ref` assertion. This is the **structural invariant** at the core of the entire #1348 fix: once it holds, no future caller — current or new — can silently land a commit on the wrong branch. The next WP migrates every existing caller to pass `destination_ref` explicitly; this WP makes that migration *mandatory* by making the signature uncompilable without it.

The cross-review (see `research.md` → R-002) was emphatic: `destination_ref` must be a commit-target contract, not a policy label. The HEAD assertion is what makes the parameter load-bearing.

## Context

**Spec source**: FR-031, FR-013, C-015, NFR-007. See `spec.md` for full text.
**Contract**: `contracts/safe_commit_signature.md` — read this first; it has the exact signature, error codes, and CLI behavior.
**Source issue**: [Priivacy-ai/spec-kitty#1348](https://github.com/Priivacy-ai/spec-kitty/issues/1348)

**Why this WP exists**: The current `safe_commit()` checks for protected branches but trusts `git commit` to land the commit on the currently-checked-out branch. When workflow callers pass `destination_ref` as a policy label only (without verifying HEAD), they create a class of bug where the policy approves a commit "for the coordination branch" but the actual commit lands on `main` because that's what HEAD is. That's the same failure mode as #1348 with the staging point shifted by one layer. The HEAD assertion closes that gap.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- The lane allocator (from `finalize-tasks`) will assign this WP a lane worktree at `.worktrees/<slug>-<mid8>-lane-<id>/`. **Do all code editing inside the lane worktree.** This WP's bookkeeping commits will land via the existing (pre-this-WP) `safe_commit()` behavior — once your changes ship, the new behavior governs all future commits.
- Branch name follows `kitty/mission-<slug>-<mid8>-lane-<id>` per the existing convention.

---

## Subtask T001: Update `safe_commit()` signature to keyword-only `destination_ref`

**Purpose**: Change the function signature so callers MUST pass `destination_ref` explicitly. mypy strict catches missing-arg at every typed call site.

**Steps**:
1. In `src/specify_cli/git/commit_helpers.py`, locate the current `safe_commit()` definition. (Its current signature is approximately `def safe_commit(repo_root: Path, message: str, paths: list[Path]) -> CommitResult` — confirm by reading the file.)
2. Refactor to keyword-only, required `destination_ref`:
   ```python
   def safe_commit(
       *,
       repo_root: Path,
       worktree_root: Path,
       destination_ref: str,
       message: str,
       paths: tuple[Path, ...],
   ) -> CommitResult: ...
   ```
3. Convert `paths` from `list[Path]` to `tuple[Path, ...]` for immutability (matches the `GitChangeSet` invariant in `data-model.md`).
4. Add `worktree_root` as a required parameter — distinguishes the worktree the commit lands in from the primary `repo_root`.
5. Update the module-level docstring to describe the new contract.

**Files**:
- `src/specify_cli/git/commit_helpers.py` — modify signature and call sites within the module.

**Validation**:
- [ ] `safe_commit()` rejects positional args (keyword-only `*` separator present).
- [ ] mypy --strict reports a clear error for any call missing `destination_ref`.
- [ ] The function's docstring explains the HEAD assertion behavior.

## Subtask T002: HEAD assertion + structured error types

**Purpose**: Inside `safe_commit()`, verify that the worktree's HEAD matches `destination_ref` before any staging or commit happens. Raise a structured error otherwise.

**Steps**:
1. Define exception class:
   ```python
   class SafeCommitHeadMismatch(Exception):
       def __init__(self, *, destination_ref: str, observed_head: str, worktree_root: Path):
           self.destination_ref = destination_ref
           self.observed_head = observed_head
           self.worktree_root = worktree_root
           super().__init__(
               f"safe_commit: worktree {worktree_root} HEAD is {observed_head!r}, "
               f"expected {destination_ref!r}. Checkout {destination_ref} first."
           )
   ```
2. Inside `safe_commit()`, before any `git add` / `git commit`:
   - **First validate `destination_ref` shape** (C-016): if it starts with `refs/heads/`, raise `SafeCommitDestinationRefShape`. Callers must pass short branch names, never fully-qualified refs. This catches the common drift from `git symbolic-ref` output being passed verbatim.
   - Run `subprocess.check_output(["git", "-C", str(worktree_root), "symbolic-ref", "HEAD"])` → raw output, strip whitespace.
   - **Normalize**: `actual_head = raw.removeprefix("refs/heads/")` — this is the short form, matching the canonical `destination_ref`.
   - If `actual_head != destination_ref` → raise `SafeCommitHeadMismatch(destination_ref=destination_ref, observed_head=actual_head, worktree_root=worktree_root)`. Both fields are in short form so operators see consistent branch names.
3. Add `ProtectedBranchRefused`, `SafeCommitDestinationNotFound`, `SafeCommitEmptyChangeset`, `SafeCommitNotAWorktree`, `SafeCommitDestinationRefShape` if they do not already exist. Match the error codes from `contracts/safe_commit_signature.md`.
4. Every exception MUST carry: `error_code` (stable identifier per NFR-007), `message`, `destination_ref`, and (when relevant) `observed_head` and `worktree_root`. JSON-serializable.

**Files**:
- `src/specify_cli/git/commit_helpers.py` — exception classes + assertion logic.

**Validation**:
- [ ] HEAD mismatch raises `SafeCommitHeadMismatch` with all four fields populated.
- [ ] Protected branch raises `ProtectedBranchRefused` (existing class, kept).
- [ ] Empty `paths` raises `SafeCommitEmptyChangeset`.
- [ ] Each exception's `error_code` matches the table in `contracts/safe_commit_signature.md`.

## Subtask T003: Remove silent `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` bypass entries

**Purpose**: The current exception list contains spec-kitty-internal entries (planning-artifact commit messages) that silently land on protected branches. Per FR-013, these must go. Documented exceptions for `upgrade`/`release` workflows MAY remain but MUST be documented in the module docstring.

**Steps**:
1. In `src/specify_cli/git/commit_helpers.py`, locate `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` (or the equivalent tuple/constant).
2. Remove any entry that exists solely to let spec-kitty bypass its own guard. Specifically, remove anything matching `"chore: planning artifacts for "` and similar planning-artifact patterns.
3. Keep documented exceptions for non-spec-kitty workflows:
   - `"chore: apply spec-kitty upgrade changes"` (upgrade flow)
   - `"chore: release "` and `"release: "` (release flow)
4. Add a module-level docstring section "Protected-branch exception policy" explaining:
   - The current exception list.
   - Why each entry exists.
   - That all NEW exceptions require a doctrine-level decision (DIRECTIVE_003).

**Files**:
- `src/specify_cli/git/commit_helpers.py`.

**Validation**:
- [ ] A grep for `"chore: planning artifacts"` in `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` returns zero hits.
- [ ] The module docstring lists every remaining exception with a rationale.

## Subtask T004: Unit tests

**Purpose**: Test surface for the new behavior. Each error class gets at least one test; the happy path + HEAD mismatch + protected branch + empty paths get explicit coverage.

**Steps**:
1. In `tests/specify_cli/git/test_commit_helpers.py`, add the following test cases:
   - `test_safe_commit_happy_path()` — worktree on `destination_ref`, non-protected → commit succeeds.
   - `test_safe_commit_head_mismatch()` — worktree on a different branch → raises `SafeCommitHeadMismatch` with all four fields populated. Assert the error's `destination_ref` and `observed_head` fields match expectations.
   - `test_safe_commit_protected_branch()` — `destination_ref=main` → raises `ProtectedBranchRefused`.
   - `test_safe_commit_empty_paths()` — empty `paths` tuple → raises `SafeCommitEmptyChangeset`.
   - `test_safe_commit_destination_not_found()` — non-existent ref → raises `SafeCommitDestinationNotFound`.
   - `test_safe_commit_keyword_only()` — positional call → `TypeError`.
2. Use `pytest` fixtures to set up tmp git repos and worktrees. The existing fixtures in this test module likely provide a `tmp_repo` fixture; reuse it.
3. For the protected-branch test, use a test-local protected list (do not modify the real one).

**Files**:
- `tests/specify_cli/git/test_commit_helpers.py` — new tests added; preserve existing tests.

**Validation**:
- [ ] `pytest tests/specify_cli/git/test_commit_helpers.py -v` passes.
- [ ] Coverage on `safe_commit()` ≥ 95% (this WP's surface is small enough to hit that easily).

## Subtask T005: CHANGELOG entry for PR 1

**Purpose**: Document the breaking-ish change for any external script that calls `safe_commit()` (the public `spec-kitty safe-commit` CLI, primarily).

**Steps**:
1. In `CHANGELOG.md`, add an entry under an "Unreleased" section (or whatever the project convention is) noting:
   - **BREAKING**: `safe_commit()` now requires keyword-only `destination_ref` and `worktree_root` parameters.
   - **BREAKING**: `spec-kitty safe-commit` CLI requires `--to-branch <ref>` (with a deprecation env var `SPEC_KITTY_INFER_DESTINATION_REF=1` for backward compat during one minor release).
   - The HEAD assertion is now structurally enforced; any worktree HEAD that doesn't match the declared destination raises `SAFE_COMMIT_HEAD_MISMATCH`.
   - Closes part of #1348 (the structural-cause portion).
2. Match the existing CHANGELOG style (look at the most recent entries).

**Files**:
- `CHANGELOG.md`.

**Validation**:
- [ ] Entry is present and matches the project's CHANGELOG style.
- [ ] References issue #1348.
- [ ] Notes the deprecation env var path with a removal timeline.

---

## Definition of Done

- [ ] All 5 subtasks complete (T001..T005).
- [ ] `pytest tests/specify_cli/git/test_commit_helpers.py` passes.
- [ ] `mypy --strict src/specify_cli/git/commit_helpers.py` passes with zero errors.
- [ ] Coverage on `safe_commit()` ≥ 95%.
- [ ] CHANGELOG entry committed.
- [ ] No spec-kitty-internal entries remain in `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS`.

After this WP lands, the rest of the codebase will not compile (every existing `safe_commit()` call site needs `destination_ref`). That is intentional and **WP02 immediately follows** to migrate every caller.

## Risks

- **Cascading mypy errors**: Expected and intentional. Do NOT soften the type signature to silence them. WP02 fixes them.
- **Concurrent PRs touching `safe_commit()`**: If another PR is in flight, coordinate with maintainers. This change is foundational.
- **Test fixtures**: If existing tests rely on the old signature, update them in this WP (they're in the same file).

## Reviewer guidance

When reviewing this WP, focus on:
1. **Signature correctness**: is `destination_ref` truly keyword-only (`*` separator)? Is `worktree_root` present? Is `paths` a tuple?
2. **HEAD assertion ordering**: is it the FIRST check inside `safe_commit()`, before staging, before any state mutation?
3. **Error fields**: does every exception carry `error_code`, `message`, and `destination_ref` for scripted detection (NFR-007)?
4. **No silent fallback**: confirm there is NO path that infers `destination_ref` from CWD/HEAD when the caller omits it. mypy should refuse to compile such a call.
5. **CHANGELOG**: does the entry clearly call this a breaking change and reference #1348?

## References

- Spec: FR-013, FR-031, C-015, NFR-007
- Plan: PR 1 step 1
- Contract: [`contracts/safe_commit_signature.md`](../contracts/safe_commit_signature.md)
- Research: R-002 in [`research.md`](../research.md)

## Activity Log

- 2026-05-28T09:54:34Z – claude – shell_pid=88169 – Assigned agent via action command
- 2026-05-28T10:22:24Z – claude – shell_pid=88169 – Moved to for_review
- 2026-05-28T10:22:59Z – opencode – shell_pid=88227 – Started review via action command
- 2026-05-28T10:26:26Z – opencode – shell_pid=88227 – Moved to approved
- 2026-05-28T12:52:25Z – opencode – shell_pid=88227 – Done override: Mission merged to main in 886dde756
