# Contract: canonical merge-base/diff surface (`core/vcs/git.py`)

This is a function-API contract (internal Python surface), not an HTTP endpoint. Names are indicative; final naming aligns to existing `core/vcs/git.py` conventions at implement time.

## `git_merge_base(repo: Path, ref_a: str, ref_b: str) -> str | None`

- Runs `git merge-base <ref_a> <ref_b>` in `repo`.
- **Returns**: the merge-base SHA (stripped) on success; `None` on non-zero exit OR empty stdout.
- **Never raises** for a git non-zero exit.
- Kwargs: `capture_output=True, text=True, encoding="utf-8", errors="replace", check=False`.

## `git_diff_names(repo: Path, base: str, head: str, *, pathspec: str | None = None, diff_filter: str | None = None) -> tuple[str, ...]`

- Runs `git diff --name-only [--diff-filter=<diff_filter>] <base> <head> [-- <pathspec>]` in `repo`.
- **Returns**: tuple of stripped, non-empty repo-relative paths; empty tuple on non-zero exit.
- `pathspec=None` → no `--` filter. `pathspec="kitty-specs/"` → `-- kitty-specs/`. `pathspec=".github/workflows"` (5th/acceptance site).
- `diff_filter=None` → no filter. `diff_filter="AMR"` → `--diff-filter=AMR` (5th/acceptance site).
- **Note**: `base`/`head` are passed as two separate args (`git diff A B`), matching current `stale_check` and the `<mb>..<ref>` range forms — the caller composes the range/args it needs. Accepts either two refs or a range token as `head` is NOT supported; callers pass explicit `base`, `head`.

> Implementation note: today's sites use both the two-arg form (`git diff --name-only A B`, `stale_check`) and the range form (`git diff --name-only <mb>..HEAD`). The surface standardizes on the **two-arg** form (`A B`), which is equivalent to `A..B` for `--name-only`. Behaviour is identical; the range-string callers switch to two-arg. This equivalence must be covered by an FR-006 test.

## `merge_base_changed_files(worktree: Path, base_ref: str, *, pathspec: str | None = None) -> tuple[str, ...]`

- Signature: `merge_base_changed_files(worktree, base_ref, *, pathspec=None, diff_filter=None)`.
- Convenience for the HEAD-relative case: `mb = git_merge_base(worktree, "HEAD", base_ref)`; if `mb is None` → return `()`; else `git_diff_names(worktree, mb, "HEAD", pathspec=pathspec, diff_filter=diff_filter)`.
- **Returns**: changed-file tuple; `()` on any failure (no merge-base, diff failure).
- **Not for `tasks_dependency_graph`**: that site diffs `mb..check_branch` (branch, not HEAD) — it must call the two primitives directly, never this convenience.
- **5th/acceptance site** (`_changed_workflow_files`): `merge_base_changed_files(worktree, base_ref, pathspec=".github/workflows", diff_filter="AMR")`. Its current `<mb>...HEAD` three-dot is byte-equivalent to the convenience's two-arg `mb HEAD` because `mb` is an ancestor of HEAD — pin this with a test.

## Behavioural contract (all three)

| Condition | Result |
|-----------|--------|
| Normal diff, N files | tuple of N paths (or the SHA for merge-base) |
| Empty merge-base stdout | `git_merge_base` → `None`; convenience → `()` |
| `git merge-base` non-zero exit | `None` / `()` |
| `git diff` non-zero exit | `()` |
| pathspec supplied | diff restricted to that pathspec |
| — any git non-zero — | never raises |

## Consumer expectations (behaviour-preserving, C-001 / NFR-001)

Each repointed site's observable output and degradation are **unchanged**. Existing site tests change only their patch target (e.g. patch `specify_cli.core.vcs.git.subprocess` instead of `_tasks.subprocess`), never their expected values.
