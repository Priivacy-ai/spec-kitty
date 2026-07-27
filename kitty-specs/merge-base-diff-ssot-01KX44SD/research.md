# Phase 0 Research: Consolidate git merge-base/diff idiom

This is a behaviour-preserving consolidation; the only open questions are the shape of the canonical surface and how to preserve each site's exact semantics. All resolved below from a direct read of the four sites.

## Decision 1 — API shape: two primitives + one convenience

- **Decision**: Expose `git_merge_base(repo, ref_a, ref_b) -> str | None`, `git_diff_names(repo, base, head, *, pathspec=None) -> tuple[str, ...]`, and `merge_base_changed_files(worktree, base_ref, *, pathspec=None) -> tuple[str, ...]` in `core/vcs/git.py`.
- **Rationale**: The four sites genuinely differ — `stale_check` uses a **2-ref** merge-base (neither ref is HEAD); `tasks_dependency_graph` diffs `<merge_base>..<check_branch>` (target is the branch, not HEAD); `tasks_shared` adds a `-- kitty-specs/` pathspec. A single `merge_base_diff(worktree, base_ref, path_filter)` (the ticket's first sketch) only serves the HEAD-relative subset and forces the other two into awkward calls. The primitive pair mirrors `stale_check`'s already-clean `_git_merge_base` / `_git_diff_names` split; the convenience covers the common HEAD-relative case (2 of 4 sites).
- **Alternatives considered**: (a) one over-parameterized `merge_base_diff` with `diff_from/diff_to/pathspec` kwargs — rejected (god-signature, poor readability, complexity risk vs NFR-003); (b) leave `stale_check` as-is and only unify the 3 HEAD-relative sites — rejected (leaves a 2-site vs 4-site split; the ticket names all four; the primitive pair unifies cleanly).

## Decision 2 — Return type at the surface: `tuple[str, ...]`

- **Decision**: The surface returns `tuple[str, ...]` (immutable, ordered); call sites adapt to `set` / `list` at their boundary.
- **Rationale**: One canonical return type; `set(...)`/`list(...)` casts at the call site are trivial and behaviour-neutral. `stale_check` wants a `set`, `tasks_shared` a `list`, `tasks_move_task` a `tuple` — all one cast away.
- **Alternatives**: returning `list` — equivalent; tuple chosen for immutability of a shared primitive's output.

## Decision 3 — Subprocess kwargs standardization (C-002)

- **Decision**: The surface uses `capture_output=True, text=True, encoding="utf-8", errors="replace", check=False`.
- **Rationale**: Three of four sites already pass `encoding/errors/check`; `stale_check` omits them. Adopting the robust variant everywhere is the single allowed incidental hardening (C-002) and does not change output for existing ASCII paths.
- **Alternatives**: match each site's exact kwargs — rejected (re-introduces per-site drift, defeats the consolidation).

## Decision 4 — Preserve test-seam patchability (C-003)

- **Decision**: `tasks_move_task` / `tasks_shared` currently route through `_tasks.subprocess.run` so tests can patch. After repointing, the git calls live in `core/vcs/git.py`; tests that injected git behaviour patch either `specify_cli.core.vcs.git.subprocess` or the helper function itself.
- **Rationale**: Keeps injection possible without the `_tasks.subprocess` indirection leaking into the VCS module. Existing site tests get a **patch-target repoint only** — no expected-value edits (NFR-001).
- **Alternatives**: keep the `_tasks.subprocess` indirection in the helper — rejected (couples the VCS primitive to a CLI module's subprocess handle).

## Decision 5 — `tasks_dependency_graph` diff target is the branch, not HEAD

- **Decision**: This site uses the primitives directly: `git_merge_base(repo, "HEAD", check_branch)` then `git_diff_names(repo, merge_base, check_branch)` — **not** the HEAD convenience.
- **Rationale**: It inspects commits HEAD is *behind* on (`<merge_base>..<check_branch>`), a different comparison than the WP's own changes (`<merge_base>..HEAD`). Using the convenience here would silently change which commits are inspected — a behaviour change (violates C-001).

## Out of scope (confirmed)

`GitVCS`'s internal merge-base for rebase statistics (`git.py:~415`) and any merge-executor merge-base are different callers with different semantics — not consolidated (C-004).
