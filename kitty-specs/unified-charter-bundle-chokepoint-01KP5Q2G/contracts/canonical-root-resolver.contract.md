# Contract: `resolve_canonical_repo_root()`

**Module**: `src/charter/resolution.py` (new in WP2.2, per D-2 / Q1=A)
**Companion**: [plan.md §D-2](../plan.md), [spec.md FR-003, C-009, NFR-003](../spec.md), [research.md §R-2](../research.md)

---

## Function signature

```python
def resolve_canonical_repo_root(path: Path) -> Path:
    """
    Resolve `path` to the canonical (main-checkout) project root.

    Uses `git rev-parse --git-common-dir` to locate the shared git directory
    for the given path, then returns the parent of that directory — the main
    checkout — regardless of whether `path` is inside the main checkout or
    inside a linked worktree.

    Implementation uses `subprocess.run(["git", "rev-parse", "--git-common-dir"],
    cwd=path, capture_output=True, text=True, check=False)`. The resolver does
    NOT re-implement git layout parsing; it does NOT read `.git/config`; it
    does NOT touch the filesystem beyond what `git rev-parse` itself touches.

    Results are cached via an LRU keyed by the absolute path of the invocation
    directory. Cache size is bounded at 256 entries per process — large enough
    that every reasonable working directory the process ever invokes from is
    hit-cached for the process lifetime.

    Args:
        path: Any path (file or directory). May be absolute or relative. The
              resolver uses `path.resolve()` internally for cache keying.

    Returns:
        Absolute path to the canonical project root (the main checkout).

    Raises:
        NotInsideRepositoryError: `path` is not inside any git repository, or
            `path` is inside a `.git` directory itself.
        GitCommonDirUnavailableError: `git` binary is unavailable, or
            `git rev-parse --git-common-dir` failed for any reason other
            than "not a git repository".
    """
```

---

## Behavioral matrix (from R-2)

| Condition | Behavior |
| --- | --- |
| Plain repo, `path` = repo working directory | Returns the working directory. |
| Plain repo, `path` = subdirectory of the working directory | Returns the working directory. |
| Plain repo, `path` = file inside the working directory | Returns the working directory (via `path.resolve().parent` for file inputs). |
| Worktree attached via `git worktree add`, `path` inside the worktree | Returns the **main checkout's working directory**, not the worktree's working directory. |
| Linked worktree on a bare parent, `path` inside any worktree | Returns the common parent of all worktrees (the bare repo's parent when applicable). |
| Submodule, `path` inside the submodule | Returns the submodule's working directory (distinct from the superproject). |
| Sparse checkout, `path` anywhere inside | Unaffected; returns the working directory. |
| Detached HEAD, `path` anywhere inside | Unaffected; returns the working directory. |
| `path` is `.git` itself, or inside `.git` | Raises `NotInsideRepositoryError` (per R-2 decision). |
| `path` is outside any git repository (`/tmp`, etc.) | Raises `NotInsideRepositoryError`. |
| `git` not on PATH | Raises `GitCommonDirUnavailableError`. |
| `git rev-parse` exits non-zero with a non-"not a repo" error | Raises `GitCommonDirUnavailableError`. |

---

## Caching

- **Cache type**: `functools.lru_cache(maxsize=256)` on a private `_resolve_cached(absolute_path: str) -> str` helper. The public `resolve_canonical_repo_root(path: Path)` resolves `path` to its absolute form, stringifies for the cache key, calls `_resolve_cached`, and re-wraps the result as `Path`.
- **Cache lifetime**: Process lifetime. Tests that mutate the filesystem layout (e.g., convert a path from "inside a repo" to "outside a repo" mid-test) must clear the cache explicitly via `resolve_canonical_repo_root.cache_clear()` — the function exposes the cache's `cache_clear` attribute per `functools.lru_cache` convention.
- **Rationale**: NFR-003 binds the resolver to <5 ms p95 with ≤1 `git` invocation per call. Cache amortizes the `subprocess` overhead across the dashboard's hot loop (per-frame charter-read path per NFR-002).

---

## Performance contract (NFR-003)

| Metric | Threshold |
| --- | --- |
| p95 latency per call (cold, first call for a given path) | <50 ms (dominated by the single `subprocess.run` invocation) |
| p95 latency per call (warm, cached) | <5 ms |
| `git` invocations per call (warm) | 0 |
| `git` invocations per call (cold) | 1 |
| Cache size bound | 256 entries (evicted LRU-wise; unbounded in practice for any reasonable invocation pattern) |

`tests/charter/test_resolution_overhead.py` enforces these thresholds with a `subprocess.run` spy and a timing harness.

---

## Error-surface contract

### `NotInsideRepositoryError`

```python
class NotInsideRepositoryError(RuntimeError):
    """
    Raised when `resolve_canonical_repo_root(path)` is called with a path
    that is not inside any git repository (or is inside a `.git/` directory
    itself, which the resolver treats as "not a valid project root").
    """
    def __init__(self, path: Path):
        self.path = path
        super().__init__(
            f"Path {path!r} is not inside a git repository. "
            f"Charter resolution requires a git-tracked project root."
        )
```

### `GitCommonDirUnavailableError`

```python
class GitCommonDirUnavailableError(RuntimeError):
    """
    Raised when `git rev-parse --git-common-dir` cannot be invoked (binary
    missing) or fails with a non-"not a repo" error (corrupt .git, permission
    denied, etc.).
    """
    def __init__(self, path: Path, detail: str):
        self.path = path
        self.detail = detail
        super().__init__(
            f"git rev-parse --git-common-dir failed for {path!r}: {detail}. "
            f"Install a supported git binary and retry."
        )
```

Neither exception has a fallback handler in `ensure_charter_bundle_fresh()`. Both propagate to the caller and surface as loud failures per C-001.

---

## Test surface

| Test | WP | Focus |
| --- | --- | --- |
| `tests/charter/test_canonical_root_resolution.py` | WP2.2 | Behavioral matrix from the R-2 findings (one test per row). |
| `tests/charter/test_resolution_overhead.py` | WP2.2 | NFR-003 performance thresholds (warm/cold, subprocess spy). |

---

## Non-goals

- **Not resolving paths across multiple repositories in one call**. Each call returns the canonical root for exactly one input path.
- **Not parsing `.git/config` for `core.worktree` or similar**. Git's `--git-common-dir` is authoritative.
- **Not providing a "best-effort fallback" when `git` is missing**. Per C-001, the resolver raises loudly.
- **Not watching for filesystem changes**. If the user manually deletes `.git/` mid-session, subsequent calls will raise; that is correct behavior.
