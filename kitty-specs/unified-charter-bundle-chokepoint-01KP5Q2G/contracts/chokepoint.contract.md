# Contract: `ensure_charter_bundle_fresh()` and extended `SyncResult`

**Module**: `src/charter/sync.py`
**Introduced in**: WP2.2
**Consumes**: `CharterBundleManifest` (WP2.1, v1.0.0), `resolve_canonical_repo_root()` (WP2.2)
**Referenced by**: [plan.md §D-3](../plan.md), [spec.md FR-003, FR-004](../spec.md), [data-model.md](../data-model.md)
**Scope (v1.0.0)**: the chokepoint is authoritative for the files `src/charter/sync.py` materializes — `governance.yaml`, `directives.yaml`, `metadata.yaml`. It is NOT authoritative for `references.yaml` (compiler-produced) or `context-state.json` (runtime-state-produced). This scope is pinned by `CharterBundleManifest.SCHEMA_VERSION = "1.0.0"`. Future manifest versions may broaden scope; those require a new migration.

---

## Function signature

```python
def ensure_charter_bundle_fresh(repo_root: Path) -> SyncResult | None:
    """
    Auto-refresh the unified charter bundle when it is stale or incomplete.

    This is the sole entry point for every reader of the `sync()`-produced
    derivatives (governance.yaml, directives.yaml, metadata.yaml). Direct
    reads of those files that bypass this function are forbidden (enforced by
    tests/charter/test_chokepoint_coverage.py).

    The function resolves `repo_root` to the canonical (main-checkout) project
    root via `resolve_canonical_repo_root()`, then consults
    `CharterBundleManifest.CANONICAL_MANIFEST` for the set of files that must
    exist under the canonical root's `.kittify/charter/` tree. If any required
    file is missing (tracked_files existence + derived_files existence) or the
    bundle is stale (content hash of `charter.md` does not match the hash
    stored in `metadata.yaml`), `sync()` is triggered to regenerate the
    derivatives.

    Args:
        repo_root: Any path inside the project. May be the main checkout or a
            worktree. The function resolves it to the canonical root before
            doing anything else.

    Returns:
        - `SyncResult` on every successful invocation (whether a sync was
          triggered or not).
        - `None` when `charter.md` does not exist at the canonical root — the
          project has no charter and there is nothing to refresh.

    Raises:
        `NotInsideRepositoryError` — `repo_root` is not inside any git repo.
        `GitCommonDirUnavailableError` — the `git` binary is unavailable or
          `git rev-parse --git-common-dir` failed for a non-"not a repo" reason.
    """
```

---

## Extended `SyncResult` dataclass (post-WP2.2)

```python
@dataclass(frozen=True)
class SyncResult:
    synced: bool
    stale_before: bool
    files_written: list[Path]      # paths relative to canonical_root
    extraction_mode: str
    error: str | None
    canonical_root: Path           # NEW in WP2.2 — absolute path to canonical project root
```

**Contract for `files_written`**:

- Every `Path` in `files_written` is **relative** to `canonical_root` (not absolute, not relative to caller's CWD).
- To reconstruct an absolute path for a specific written file: `canonical_root / files_written[i]`.
- For v1.0.0 manifest, `files_written` entries are drawn from `CANONICAL_MANIFEST.derived_files` (governance.yaml, directives.yaml, metadata.yaml). A sync that writes fewer than all three leaves the not-written files off the list (e.g., if `sync()` fails partway through, only the successfully-written files appear).

**Contract for `canonical_root`**:

- Always absolute.
- Equal to the return value of `resolve_canonical_repo_root(repo_root)` for the `repo_root` passed into the chokepoint call.
- Stable across invocations from the same working directory (per the resolver's LRU cache).

---

## Behavioral contract

### Invariant 1: canonical resolution happens first

`ensure_charter_bundle_fresh(repo_root)` calls `resolve_canonical_repo_root(repo_root)` as its **first** operation. Every subsequent file system access is rooted at the resolved canonical root. A reader in a worktree and a reader in the main checkout produce **byte-identical** `SyncResult.files_written` lists when the bundle is identical.

### Invariant 2: the manifest is authoritative for completeness within its scope

The chokepoint consults `CharterBundleManifest.CANONICAL_MANIFEST` rather than hard-coding the list of files to check. Adding a file to scope in a future schema version requires exactly one edit: the manifest. The chokepoint does not need to change.

However, the manifest v1.0.0 scope is limited to the `sync()`-produced files. The chokepoint does not track, regenerate, or validate `references.yaml` or `context-state.json`. Readers of those files go through their own pipelines (compiler / context builder respectively); those pipelines may themselves route through the chokepoint to guarantee the upstream derivatives are fresh, but the chokepoint is not responsible for materializing them.

### Invariant 3: no path writes happen inside worktrees

When invoked from a worktree path, `files_written` entries are relative to `canonical_root` (the main checkout), and any `sync()` invocation writes to the canonical root's `.kittify/charter/` — **not** to the worktree's `.kittify/charter/`. This is enforced by construction: `sync()` receives `canonical_root` as its base path.

### Invariant 4: staleness is a hash comparison, not a timestamp check

Staleness is detected by comparing the content hash of `canonical_root / ".kittify/charter/charter.md"` against the hash stored in `canonical_root / ".kittify/charter/metadata.yaml"`. Timestamps are not consulted for staleness (they may be consulted as an mtime short-circuit optimization inside the completeness check — see NFR-002 mitigation in plan §Risks).

### Invariant 5: None return means "no charter"

If `charter.md` does not exist at `canonical_root / ".kittify/charter/charter.md"`, the function returns `None`. It does not raise, does not create the file, and does not error. Callers that require a charter must check for `None` and handle accordingly (typical caller: fall back to a "no governance context" path).

### Invariant 6: failure is loud, not silent

Both exception types (`NotInsideRepositoryError`, `GitCommonDirUnavailableError`) propagate. No fallback to filesystem-heuristic resolution per C-001 / C-009.

---

## Interaction with existing contracts

### `sync()`

Unchanged externally. Internally, it now receives `canonical_root` (a `Path`) from the chokepoint and produces paths relative to it. The extraction logic itself is untouched. `_SYNC_OUTPUT_FILES` (at `src/charter/sync.py:32-36`) remains the authoritative list of files `sync()` writes.

### `load_governance_config()` / `load_directives_config()`

Already route through `ensure_charter_bundle_fresh()` at `src/charter/sync.py:204` and `:244`. After WP2.2 they automatically benefit from canonical-root resolution with no code change at those call sites — the `SyncResult` they receive carries the new `canonical_root` field, but they do not need to consume it (they read the derived YAMLs from the paths the chokepoint guarantees).

### `post_save_hook()`

Called after a CLI charter write. Consumes `SyncResult`. WP2.2 updates the hook to anchor displayed paths against `canonical_root` (R-3).

### Compiler pipeline (`write_compiled_charter` at `src/charter/compiler.py:169-196`)

Out of scope for v1.0.0 chokepoint. Callers that need `references.yaml` materialized invoke the compiler pipeline explicitly (`spec-kitty charter generate`). The compiler pipeline MAY call the chokepoint to guarantee upstream `governance.yaml` / `directives.yaml` / `metadata.yaml` are fresh before compiling, but the chokepoint does not call the compiler.

### `build_charter_context()` context-state.json writes (`src/charter/context.py:385-398`)

Out of scope for v1.0.0 chokepoint. `context-state.json` remains lazily written by the context builder and is not validated by the chokepoint. The project `.gitignore` may continue to ignore it; the manifest is silent about it.

---

## Test surface (WP2.2 + WP2.3)

The following tests are introduced / updated to exercise this contract:

- `tests/charter/test_canonical_root_resolution.py` — unit tests for the resolver per R-2 fixture matrix.
- `tests/charter/test_chokepoint_overhead.py` — NFR-002 warm-overhead benchmarks.
- `tests/charter/test_resolution_overhead.py` — NFR-003 resolver overhead benchmarks.
- `tests/charter/test_bundle_contract.py` (WP2.3) — end-to-end manifest-vs-disk check using the chokepoint (v1.0.0 scope only).
- `tests/charter/test_chokepoint_coverage.py` (WP2.3) — AST-walk asserting every reader of the three `sync()`-produced derivatives routes through this function.
- `tests/init/test_fresh_clone_no_sync.py` (WP2.3) — fresh-clone smoke test; chokepoint auto-refreshes `governance.yaml` / `directives.yaml` / `metadata.yaml`.
- `tests/test_dashboard/test_charter_chokepoint_regression.py` (WP2.3) — dashboard typed contracts survive the cutover byte-identically.

---

## Non-goals

- **Not introducing caching on `SyncResult` itself**. Each invocation produces a fresh result. Caching is at the resolver layer only (LRU by working directory) and at the hash-check layer (implementation detail; not part of the contract).
- **Not changing the public API of `SyncResult` in any way beyond adding `canonical_root`**. No renames, no retypings.
- **Not introducing a new "bundle state" enum**. Existing `synced` / `stale_before` / `extraction_mode` fields cover the observable states.
- **Not expanding v1.0.0 to cover `references.yaml` or `context-state.json`.** Those are separate pipelines and out of scope for this tranche.
- **Not touching `src/specify_cli/core/worktree.py`'s `.kittify/memory/` and `.kittify/AGENTS.md` sharing.** Those symlinks are documented-intentional (see `src/specify_cli/templates/AGENTS.md:168-179`) and unrelated to the charter bundle. Canonical-root resolution solves the worktree-charter-visibility problem without touching that code path.
