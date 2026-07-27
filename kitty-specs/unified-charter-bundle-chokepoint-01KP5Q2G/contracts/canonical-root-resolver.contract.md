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

    Args:
        path: Any path (file or directory). May be absolute or relative. File
              inputs are normalized to their parent directory before invocation.

    Returns:
        Absolute path to the canonical project root (the main checkout).

    Raises:
        NotInsideRepositoryError: `path` is not inside any git repository, or
            the resolved input path is inside a `.git/` directory itself.
        GitCommonDirUnavailableError: `git` binary is unavailable, or
            `git rev-parse --git-common-dir` failed for any reason other
            than "not a git repository".
    """
```

---

## Algorithm (precise)

```
1. Normalize input:
     input_abs = path.resolve()
     if input_abs is a file:
         cwd = input_abs.parent
     else:
         cwd = input_abs

2. Invoke git:
     result = subprocess.run(
         ["git", "rev-parse", "--git-common-dir"],
         cwd=cwd,
         capture_output=True,
         text=True,
         check=False,
     )
     If subprocess.run raises FileNotFoundError (git binary missing):
         raise GitCommonDirUnavailableError(path, "git binary not found on PATH")

3. Classify exit code:
     if result.returncode != 0:
         if "not a git repository" in result.stderr.lower():
             raise NotInsideRepositoryError(path)
         else:
             raise GitCommonDirUnavailableError(path, result.stderr.strip())

4. Parse stdout:
     raw = result.stdout.strip()
     common_dir = Path(raw)
     if not common_dir.is_absolute():
         common_dir = (cwd / common_dir).resolve()
     else:
         common_dir = common_dir.resolve()

5. Detect "inside .git/" edge case:
     if input_abs == common_dir or common_dir in input_abs.parents:
         raise NotInsideRepositoryError(path)

6. Return:
     canonical_root = common_dir.parent
     return canonical_root
```

**Why `common_dir.parent`:** For the main checkout and for any subdirectory inside it, `git rev-parse --git-common-dir` returns a path whose parent is the working directory of the main repo. For a linked worktree, it returns the **shared** git-dir path (absolute), whose parent is also the main checkout's working directory. This is the semantic the contract relies on.

---

## `git rev-parse --git-common-dir` observed behavior (verified locally 2026-04-14)

| Invocation cwd | stdout | is_absolute? | resolved to | canonical_root |
| --- | --- | --- | --- | --- |
| `<repo>` (main checkout) | `.git` | No | `<repo>/.git` | `<repo>` ✓ |
| `<repo>/src/charter` (subdirectory) | `../../.git` | No | `<repo>/.git` | `<repo>` ✓ |
| `<repo>/.git` (inside git dir) | `.` | No | `<repo>/.git` | detected in step 5 → raise `NotInsideRepositoryError` |
| `<repo>/.worktrees/foo` (linked worktree) | `/abs/path/to/<main>/.git` | Yes | `<main>/.git` | `<main>` ✓ |
| `/tmp` (non-repo) | empty; exit 128; stderr contains "not a git repository" | — | — | raise `NotInsideRepositoryError` |
| `<repo>` with submodule-attached checkout at `<repo>/sub` | `.git/modules/sub` | No | `<repo>/.git/modules/sub` | `<repo>/.git/modules` — submodule-specific path, treated as submodule's working directory (see note below) |
| `<repo>` with sparse-checkout enabled | same as main checkout | — | — | same as main checkout ✓ |
| `<repo>` with detached HEAD | same as main checkout | — | — | same as main checkout ✓ |

**Submodule note**: when `path` is inside a submodule's working directory, the resolver returns the submodule's working directory via `common_dir.parent`. The current working directory of the submodule is `common_dir.parent.parent` (two levels up from `.git/modules/<name>`), which is the **submodule's** working tree, distinct from the superproject. Tests in `tests/charter/test_canonical_root_resolution.py` exercise this case explicitly so the behavior is documented, not surprising.

---

## Caching

- **Cache type**: `functools.lru_cache(maxsize=256)` on a private `_resolve_cached(absolute_path_str: str) -> str` helper. The public `resolve_canonical_repo_root(path: Path)` resolves `path` to its absolute form (normalizing files to parents), stringifies for the cache key, calls `_resolve_cached`, and re-wraps the result as `Path`.
- **Cache lifetime**: Process lifetime. Tests that mutate the filesystem layout mid-test must clear the cache explicitly via `resolve_canonical_repo_root.cache_clear()` — the function exposes the cache's `cache_clear` attribute per `functools.lru_cache` convention.
- **Rationale**: NFR-003 binds the resolver to <5 ms p95 with ≤1 `git` invocation per call. Cache amortizes the `subprocess` overhead across the dashboard's hot loop (per-frame charter-read path per NFR-002).

---

## Performance contract (NFR-003)

| Metric | Threshold |
| --- | --- |
| p95 latency per call (cold, first call for a given path) | <50 ms (dominated by the single `subprocess.run` invocation) |
| p95 latency per call (warm, cached) | <5 ms |
| `git` invocations per call (warm) | 0 |
| `git` invocations per call (cold) | 1 |
| Cache size bound | 256 entries (evicted LRU-wise) |

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
| `tests/charter/test_canonical_root_resolution.py` | WP2.2 | Behavioral matrix above — one test per row. Also covers: file input normalized to parent; relative-path stdout correctly resolved; absolute-path stdout used as-is; cache hit/miss accounting. |
| `tests/charter/test_resolution_overhead.py` | WP2.2 | NFR-003 performance thresholds (warm/cold, subprocess spy). |

---

## Non-goals

- **Not resolving paths across multiple repositories in one call**. Each call returns the canonical root for exactly one input path.
- **Not parsing `.git/config` for `core.worktree` or similar**. Git's `--git-common-dir` is authoritative.
- **Not providing a "best-effort fallback" when `git` is missing**. Per C-001, the resolver raises loudly.
- **Not watching for filesystem changes**. If the user manually deletes `.git/` mid-session, subsequent calls will raise; that is correct behavior.
- **Not using `--absolute-git-dir` or re-invoking git a second time to force absolute output.** The contract resolves stdout against `cwd` in step 4 — one subprocess invocation per cold call.
