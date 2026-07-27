# Mission Specification: Consolidate git merge-base/diff idiom

**Mission**: merge-base-diff-ssot-01KX44SD
**Type**: software-dev
**Closes**: #2450 (landing follow-up from #2438, surfaced by the paula-patterns squad) · milestone 3.2.x (G2/G3, no-shadow-paths)
**Status**: Draft

## Purpose (stakeholder-facing)

**TL;DR**: Collapse four hand-rolled `git merge-base` → `git diff --name-only` copies onto one shared helper.

Four independent modules each shell out to `git merge-base` then `git diff --name-only` with their own error handling and their own tests. This mission routes all four onto a single `core/vcs/git.py` helper so the changed-files idiom is proven once and cannot drift — extending the 3.2.x milestone's no-shadow-paths / single-seam discipline to a duplicated VCS primitive. This is a **behaviour-preserving** consolidation: no site changes which files it reports or how it degrades on git failure.

## Context & Motivation

`_mt_pre_review_changed_files` (`tasks_move_task.py`) is one of **five** independent copies of the `git merge-base HEAD <base>` → `git diff --name-only <merge_base>..HEAD` idiom (a post-plan brownfield squad corrected the initial count of 4 → 5). The copies:

- `src/specify_cli/lanes/stale_check.py` — `_git_merge_base(repo_root, ref_a, ref_b)` + `_git_diff_names(repo_root, base, head)` (a **2-ref** variant: neither ref is HEAD; returns `set[str]`).
- `src/specify_cli/cli/commands/agent/tasks_shared.py` — `_list_wp_branch_mission_specs_changes` (HEAD-relative, `-- kitty-specs/` pathspec, followed by a **site-specific content re-check** second pass, FR-007/#2274).
- `src/specify_cli/cli/commands/agent/tasks_dependency_graph.py` — upstream-only-planning check (`merge-base HEAD <check_branch>` then `diff --name-only <merge_base>..<check_branch>`; note the diff target is the branch, not HEAD).
- `src/specify_cli/cli/commands/agent/tasks_move_task.py` — `_mt_pre_review_changed_files` (HEAD-relative, full changed set, `tuple[str, ...]`).
- `src/specify_cli/acceptance/__init__.py` — `_changed_workflow_files` (lines ~1088–1116): HEAD-relative merge-base then `diff --name-only --diff-filter=AMR <merge_base>...HEAD -- .github/workflows`. Adds a `--diff-filter` and three-dot `...HEAD` (byte-equivalent to `..HEAD` for `--name-only` because the merge-base is an ancestor of HEAD). **This is the 5th copy the surface must absorb — leaving it stranded ships a 4-consolidated + 1-orphan split-brain, the exact failure this mission exists to prevent.**

Each site independently shells out, with its own error handling, encoding flags, `cwd` type, subprocess indirection, and return type. The merge-base/diff mechanics only need to be proven once.

## User Scenarios & Testing

**Primary actor**: a Spec Kitty contributor maintaining any runtime path that needs "files changed on one ref relative to the merge-base with another ref" (and transitively every user/agent hitting the pre-review gate, stale-lane check, dependency-readiness check, or spec-change detection).

**Primary scenario (happy path)**: A contributor needs the changed-file set for a merge-base comparison. They call the canonical `core/vcs/git.py` helper. It returns the same file set the inline copy returned, with the same empty-on-failure degradation. No new inline `git merge-base`/`git diff --name-only` copy is written.

**Main exception path**: git fails (no merge-base, detached state, subprocess error). The helper degrades to an empty result exactly as each inline copy did today; no exception surfaces to the caller that didn't already surface one.

**Rule that must always hold**: the observable output of each of the four call sites — the exact set/list/tuple/bool it produced, and its failure degradation — is **unchanged** after repointing. This is a refactor, not a behaviour change.

### Acceptance Scenarios

1. **Move-task pre-review gate** (`_mt_pre_review_changed_files`): given a WP worktree with N changed files vs its target branch, the repointed site returns the same full changed-file tuple; on any git failure it returns `()`.
2. **Spec-change detection** (`_list_wp_branch_mission_specs_changes`): the merge-base→`-- kitty-specs/` first pass uses the helper; the FR-007/#2274 content re-check second pass is preserved byte-for-byte; results identical.
3. **Dependency-readiness upstream check** (`tasks_dependency_graph`): the `merge-base HEAD <check_branch>` → `diff <merge_base>..<check_branch>` composition uses the helper primitives; the planning-only bool verdict is unchanged.
4. **Stale-lane check** (`stale_check`): the 2-ref merge-base + base/head diff uses the helper primitives; the returned `set[str]` and `None`/empty degradation are unchanged.
5. **Workflow-evidence acceptance gate** (`acceptance._changed_workflow_files`): the merge-base→`--diff-filter=AMR ...HEAD -- .github/workflows` copy uses the helper (`pathspec=".github/workflows", diff_filter="AMR"`); the returned sorted workflow-file set is unchanged.
6. **Helper direct test**: the helper is exercised directly for normal diff, empty merge-base output, merge-base command failure, diff command failure, pathspec filtering, `diff_filter` filtering, a non-HEAD branch-target diff, and the range↔two-arg equivalence — without going through any call site.

### Edge Cases

- **No merge-base** (unrelated histories): merge-base primitive returns `None`; each site degrades as before (empty).
- **Pathspec filter** vs none: only `tasks_shared` passes `-- kitty-specs/`; the helper's pathspec is optional and defaults to none.
- **Diff target is the branch, not HEAD** (`tasks_dependency_graph`): the diff-names primitive must accept explicit `(base, head)` refs, not assume HEAD.
- **Non-ASCII paths**: the helper standardizes on `encoding="utf-8", errors="replace"`; adopting this at `stale_check` (which lacks it) must not change output for existing ASCII paths.
- **Test subprocess patching**: sites that route through `_tasks.subprocess.run` for injection must remain patchable after repointing.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A single canonical merge-base/diff surface exists in `src/specify_cli/core/vcs/git.py`, exposing: (a) `git_merge_base(repo, ref_a, ref_b) -> str \| None` returning the merge-base SHA or `None` on failure/empty; (b) `git_diff_names(repo, base, head, *, pathspec=None, diff_filter=None) -> tuple[str, ...]` returning the `--name-only` file set (empty tuple on failure), where `diff_filter` maps to `--diff-filter=<value>` (needed by the 5th/acceptance site) and `pathspec` maps to `-- <pathspec>`; (c) a HEAD-relative convenience `merge_base_changed_files(worktree, base_ref, *, pathspec=None, diff_filter=None) -> tuple[str, ...]` = `git_merge_base(HEAD, base_ref)` then `git_diff_names(merge_base, HEAD, pathspec=..., diff_filter=...)`, degrading to `()` on any failure. | Draft |
| FR-002 | `tasks_move_task._mt_pre_review_changed_files` is repointed to `merge_base_changed_files`; its observable output (full changed-file tuple; `()` on failure) is unchanged. | Draft |
| FR-003 | `tasks_shared._list_wp_branch_mission_specs_changes` uses the helper for its merge-base→`pathspec=kitty-specs/` first pass; the site-specific content re-check second pass (FR-007/#2274) is preserved unchanged. | Draft |
| FR-004 | `tasks_dependency_graph`'s upstream-only-planning check uses the helper primitives (`git_merge_base(HEAD, check_branch)`, `git_diff_names(merge_base, check_branch)`); its planning-only bool verdict is unchanged. | Draft |
| FR-005 | `lanes/stale_check._git_merge_base` / `_git_diff_names` are replaced by the helper primitives (2-ref merge-base; `(base, head)` diff); the returned `set[str]` and `None`/empty degradation are unchanged (caller adapts the tuple→set at the boundary). | Draft |
| FR-006 | The helper carries direct unit tests covering: normal diff, empty merge-base, merge-base command failure, diff command failure, pathspec filtering, `diff_filter` filtering, **a non-HEAD branch-target case** (`git_diff_names(repo, mb, <branch>)` where `<branch> != HEAD` — fences the F1 slip where `tasks_dependency_graph` would be wrongly swapped to the HEAD convenience), and **a range↔two-arg equivalence assertion** (helper two-arg output == raw `git diff --name-only <mb>..HEAD` on the same real repo). Each of the five call sites retains a thin integration test proving its own composition (not re-proving the git mechanics). | Draft |
| FR-007 | **(Secondary — alphonso NOTE, lower priority)** Add `ScopeResult.from_override(targets)` classmethod on `src/specify_cli/review/pre_review_gate.py` and retire the hand-built `ScopeResult` construction in `tasks_move_task.py`'s FR-004 override tier. May land in a follow-up WP if it widens scope. Note: `tasks_move_task` carries a `module_defs == _MOVE_SET` symbol-identity guard — any added/removed module-level symbol here fails it, so keep this in its own WP. | Draft |
| FR-008 | `acceptance/__init__.py::_changed_workflow_files` (the 5th copy) is repointed to `merge_base_changed_files(worktree, base_ref, pathspec=".github/workflows", diff_filter="AMR")`; its returned sorted workflow-file set and degradation are unchanged. The three-dot `...HEAD` → helper two-arg equivalence (safe because the merge-base is an ancestor of HEAD) is asserted. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Behaviour-preserving: no expected-value assertion in any existing test changes. | 0 changed expected-value assertions across the 4 sites' tests; only import/patch-target repointing permitted. | Draft |
| NFR-002 | No residual duplication: the `git merge-base` + `git diff --name-only` shell-out for these flows lives in exactly one module. | 0 remaining inline copies among **all 5 sites** (grep-verifiable, incl. `acceptance/__init__.py`); the surface is `core/vcs/git.py` only. | Draft |
| NFR-003 | Lint/type/complexity clean. | ruff + mypy zero issues; cyclomatic complexity ≤ 15 on every new/changed function. | Draft |
| NFR-004 | New-code coverage meets the repo gate. | Helper new-code coverage ≥ project new-code target; all 5 FR-006 branches executed by direct tests. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Behaviour-preserving refactor only — no change to which files any site reports, nor to error-degradation semantics (`None`/empty/`tuple`/`set`/`list`/`bool` at each boundary). | Draft |
| C-002 | The helper standardizes on `encoding="utf-8", errors="replace", check=False`. Adopting these at `stale_check` (which currently omits them) is the ONLY allowed incidental hardening and must not change output for existing paths. | Draft |
| C-003 | Preserve test-seam patchability — sites that route subprocess through `_tasks.subprocess.run` for injection must remain patchable (tests patch the helper's subprocess or the helper itself). | Draft |
| C-004 | Scope is exactly these **5 sites** (incl. `acceptance/__init__.py::_changed_workflow_files`) + the helper + the FR-007 secondary tidy. `GitVCS`'s internal merge-base (rebase stats, `git.py:~415`), commit-count merge-base (`core/stale_detection.py`), `--is-ancestor` ancestry checks, and merge-base-less `diff --name-only` (staged/conflict/`base..head` idioms) are OUT — they are legitimately different uses (confirmed by the post-plan brownfield inventory). Do NOT expand into `acceptance/__init__.py`'s other god-module debt — repoint only `_changed_workflow_files`. | Draft |
| C-005 | No collision with in-flight work — none of these 4 files are owned by the coord-authority trio degod (01KX2T1Q); this mission proceeds independently. | Draft |

## Key Entities

- **Changed-file set** — the `--name-only` output of a merge-base-relative diff, returned as `tuple[str, ...]` from the canonical helper; adapted to `set`/`list` at each call-site boundary.
- **Merge-base SHA** — the common ancestor commit of two refs, or `None` when none exists / git fails.

## Success Criteria

| ID | Criterion | Measure |
|----|-----------|---------|
| SC-001 | The merge-base→diff idiom is implemented once and the five prior inline copies are gone. | Grep for `git merge-base` + `diff --name-only` across the 5 modules returns only helper calls; NFR-002 holds. |
| SC-002 | The consolidation changed no behaviour. | Full suite green with zero expected-value assertion edits (NFR-001). |
| SC-003 | The mechanics are proven directly, not only via integration. | The helper's direct test exercises all 5 FR-006 branches; each site keeps a thin integration test. |

## Assumptions

- **Helper API shape (decided, not deferred)**: two primitives (`git_merge_base`, `git_diff_names`) plus a HEAD-relative convenience (`merge_base_changed_files`), rather than one over-parameterized function. Rationale: the four sites genuinely differ (2-ref vs HEAD-relative merge-base; `..HEAD` vs `..branch` diff target; optional pathspec), and this split mirrors `stale_check`'s already-clean primitive pair without forcing a god-signature. Naming may be refined at plan time to match existing `core/vcs/git.py` conventions.
- **Return type standardized on `tuple[str, ...]`** at the helper; call sites adapt (`set(...)`, `list(...)`) at their boundary — a trivial, behaviour-neutral cast.
- **FR-007 (ScopeResult.from_override)** is genuinely secondary; if plan finds it widens the diff meaningfully it becomes its own WP or a fast-follow, and does not block FR-001–FR-006.
- The repo is `legacy=0` and none of the 4 files are contested by other in-flight missions, so this can land as an independent PR.

## Out of Scope

- `GitVCS` internal merge-base for rebase statistics (`git.py:~415`) and any merge-executor merge-base logic — different callers, different semantics.
- Any change to *which* files a gate acts on, or to the pre-review gate's scoping policy (that behaviour is fixed; only the changed-file **primitive** is consolidated).
- The full 3.2.x SSOT/strangler program beyond this one duplicated primitive.
