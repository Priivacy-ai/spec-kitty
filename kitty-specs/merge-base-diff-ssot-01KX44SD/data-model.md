# Phase 1 Data Model: Consolidate git merge-base/diff idiom

No persistent data. This mission introduces two transient value concepts produced by the canonical VCS surface.

## Value: Merge-base SHA

- **Shape**: `str | None`
- **Produced by**: `git_merge_base(repo, ref_a, ref_b)`
- **Meaning**: the common-ancestor commit SHA of two refs; `None` when git fails or no common ancestor exists (unrelated histories).
- **Invariant**: `None` is the sole failure sentinel — callers that need to degrade branch on `is None`.

## Value: Changed-file set

- **Shape**: `tuple[str, ...]` at the canonical surface; adapted to `set[str]` / `list[str]` at call-site boundaries.
- **Produced by**: `git_diff_names(repo, base, head, *, pathspec=None)` and `merge_base_changed_files(worktree, base_ref, *, pathspec=None)`.
- **Meaning**: repo-relative paths of files differing between `base` and `head` (optionally restricted by `pathspec`), stripped and non-empty.
- **Invariant**: empty tuple is the sole degradation value on git failure — never raises for an expected git non-zero exit (C-001 preserves each site's current empty/`None` degradation).

## Boundary adaptations (per call site)

| Site | Surface call | Boundary cast | Preserved return |
|------|-------------|---------------|------------------|
| `tasks_move_task._mt_pre_review_changed_files` | `merge_base_changed_files(wt, base)` | — | `tuple[str, ...]`, `()` on failure |
| `tasks_shared._list_wp_branch_mission_specs_changes` | `merge_base_changed_files(wt, base, pathspec="kitty-specs/")` (first pass) | `list(...)` + content re-check | `list[str]` |
| `tasks_dependency_graph` upstream check | `git_merge_base(HEAD, br)` + `git_diff_names(mb, br)` | consumed as bool verdict | `bool` |
| `lanes/stale_check` | `git_merge_base(repo, a, b)` + `git_diff_names(repo, mb, head)` | `set(...)` | `set[str]`, `None`/empty degradation |

No state transitions, no lifecycle, no externally visible events.
