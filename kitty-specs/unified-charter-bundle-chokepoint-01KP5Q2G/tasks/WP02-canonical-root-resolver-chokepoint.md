---
work_package_id: WP02
title: Canonical-root resolver and chokepoint plumbing
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-006
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
- T015
agent: "claude:sonnet:implementer:implementer"
shell_pid: "94246"
history:
- at: '2026-04-14T11:16:00Z'
  actor: claude
  event: created
authoritative_surface: src/charter/resolution.py
execution_mode: code_change
owned_files:
- src/charter/resolution.py
- src/charter/sync.py
- tests/charter/test_canonical_root_resolution.py
- tests/charter/test_chokepoint_overhead.py
- tests/charter/test_resolution_overhead.py
- kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP02.yaml
tags: []
---

# WP02 — Canonical-root resolver and chokepoint plumbing

**Tracks**: [Priivacy-ai/spec-kitty#480](https://github.com/Priivacy-ai/spec-kitty/issues/480)
**Depends on**: WP01 (manifest model)
**Merges to**: `main`

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution mode**: lane-based worktree allocated by `finalize-tasks`. Run `spec-kitty agent action implement WP02 --agent <name> --mission unified-charter-bundle-chokepoint-01KP5Q2G`.

---

## Objective

Add the canonical-root resolver that the chokepoint will use to identify the main checkout regardless of whether a reader runs from the main repo or a worktree. Extend `SyncResult` with a new `canonical_root: Path` field so every caller has an explicit anchor. Refactor `ensure_charter_bundle_fresh()` to consult the manifest (WP01) for completeness and the resolver for root resolution, and bind the perf budgets with micro-benchmarks. **No reader call sites are flipped in this WP** — that's WP03's scope.

**Correct algorithm** per [contracts/canonical-root-resolver.contract.md](../contracts/canonical-root-resolver.contract.md). `git rev-parse --git-common-dir` returns paths RELATIVE to `cwd` in the common case, absolute only for linked worktrees. Any implementation that treats the output as always-absolute is wrong.

## Context

- EPIC: [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
- Phase 2 tracking: [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)
- WP tracking issue: [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480)
- User decision Q1=A: resolver lives at `src/charter/resolution.py` (not inside `sync.py`).
- User decision Q2=C: `SyncResult.canonical_root` is a new field; `files_written` remains relative to that root.
- Design-review correction P2 #3: algorithm rewritten to handle relative-vs-absolute stdout and `.git/`-interior edge case.

## Authoritative files (read before starting)

- [spec.md](../spec.md) — FR-003, FR-006, FR-015; C-001, C-002, C-007, C-009
- [plan.md](../plan.md) — WP2.2 section + D-2 (resolver module), D-3 (SyncResult extension), D-10 (research scope)
- [data-model.md](../data-model.md) — extended `SyncResult`; exception types
- [research.md](../research.md) — R-2 (behavioral matrix), R-3 (SyncResult caller audit)
- [contracts/canonical-root-resolver.contract.md](../contracts/canonical-root-resolver.contract.md) — **read cover-to-cover before writing any code**
- [contracts/chokepoint.contract.md](../contracts/chokepoint.contract.md) — extended `SyncResult` contract
- [quickstart.md](../quickstart.md) — smoke-check commands for WP02

---

## Subtask details

### T008 — Create `src/charter/resolution.py`

**Purpose**: Ship the canonical-root resolver. This is the most precision-critical subtask in WP02 — the algorithm must exactly match the contract.

**Steps**:

1. Create `src/charter/resolution.py` (new, ~110 lines) implementing the exact six-step algorithm from [contracts/canonical-root-resolver.contract.md](../contracts/canonical-root-resolver.contract.md):

   ```python
   """Canonical repo root resolution via `git rev-parse --git-common-dir`.

   Contract: kitty-specs/.../contracts/canonical-root-resolver.contract.md

   Key invariant: git rev-parse --git-common-dir stdout is CWD-relative in the
   common case (e.g. '.git' or '../../.git'). Absolute only for linked worktrees.
   Callers MUST resolve the returned path against cwd.
   """
   from __future__ import annotations

   import subprocess
   from functools import lru_cache
   from pathlib import Path


   class NotInsideRepositoryError(RuntimeError):
       def __init__(self, path: Path):
           self.path = path
           super().__init__(
               f"Path {path!r} is not inside a git repository. "
               f"Charter resolution requires a git-tracked project root."
           )


   class GitCommonDirUnavailableError(RuntimeError):
       def __init__(self, path: Path, detail: str):
           self.path = path
           self.detail = detail
           super().__init__(
               f"git rev-parse --git-common-dir failed for {path!r}: {detail}. "
               f"Install a supported git binary and retry."
           )


   @lru_cache(maxsize=256)
   def _resolve_cached(abs_path_str: str) -> str:
       path = Path(abs_path_str)
       # Step 1: normalize file input to parent directory.
       cwd = path.parent if path.is_file() else path

       # Step 2: invoke git once.
       try:
           result = subprocess.run(
               ["git", "rev-parse", "--git-common-dir"],
               cwd=cwd, capture_output=True, text=True, check=False,
           )
       except FileNotFoundError as exc:
           raise GitCommonDirUnavailableError(path, "git binary not found on PATH") from exc

       # Step 3: classify exit code.
       if result.returncode != 0:
           stderr = (result.stderr or "").lower()
           if "not a git repository" in stderr:
               raise NotInsideRepositoryError(path)
           raise GitCommonDirUnavailableError(path, (result.stderr or "").strip())

       # Step 4: resolve stdout relative to cwd when non-absolute.
       raw = result.stdout.strip()
       common_dir = Path(raw)
       common_dir = common_dir if common_dir.is_absolute() else (cwd / common_dir).resolve()

       # Step 5: explicit .git/-interior detection.
       if path == common_dir or common_dir in path.parents:
           raise NotInsideRepositoryError(path)

       # Step 6: canonical root is the parent of the common dir.
       return str(common_dir.parent)


   def resolve_canonical_repo_root(path: Path) -> Path:
       """Resolve `path` to the canonical (main-checkout) project root.

       See contracts/canonical-root-resolver.contract.md for the full contract.
       """
       abs_path = path.resolve()
       return Path(_resolve_cached(str(abs_path)))


   # Expose cache_clear for tests that mutate fixture layout.
   resolve_canonical_repo_root.cache_clear = _resolve_cached.cache_clear  # type: ignore[attr-defined]
   ```

2. The algorithm MUST exactly match the six steps. Common implementation errors to avoid:
   - Treating `stdout` as always-absolute (wrong for main-checkout and subdirectory cases).
   - Skipping file-input normalization (breaks for file paths passed to the resolver).
   - Missing `.git/`-interior detection (invalid canonical root returned).
   - Multiple `git` invocations per cold call (violates NFR-003).

**Files**:
- `src/charter/resolution.py` (new, ~110 lines)

**Validation**:
- [ ] `mypy --strict src/charter/resolution.py` passes.
- [ ] `python -c "from charter.resolution import resolve_canonical_repo_root; print(resolve_canonical_repo_root(__import__('pathlib').Path.cwd()))"` prints an absolute path.

---

### T009 — Write `tests/charter/test_canonical_root_resolution.py`

**Purpose**: Exercise every row of the R-2 behavioral matrix. If any row is missing, a platform regression can slip through.

**Steps**:

1. Create `tests/charter/test_canonical_root_resolution.py` (new, ~220 lines) with one test per row in the R-2 behavioral matrix from [contracts/canonical-root-resolver.contract.md](../contracts/canonical-root-resolver.contract.md#git-rev-parse---git-common-dir-observed-behavior-verified-locally-2026-04-14):

   Test cases required:
   - `test_main_checkout_root_returns_working_dir()` — init a tmp repo; call with cwd=repo; expect the repo path.
   - `test_subdirectory_returns_main_checkout()` — init repo; cd into `src/sub`; call with cwd=subdir; expect repo path (not subdir).
   - `test_file_input_normalized_to_parent()` — call with a file path inside repo; expect repo path.
   - `test_inside_dot_git_raises_not_inside_repo()` — call with cwd=`.git`; expect `NotInsideRepositoryError`.
   - `test_linked_worktree_returns_main_checkout()` — `git worktree add`; call from inside worktree; expect main checkout path, NOT worktree path.
   - `test_non_repo_raises_not_inside_repo()` — call with cwd=`/tmp/not-a-repo`; expect `NotInsideRepositoryError`.
   - `test_missing_git_binary_raises_git_common_dir_unavailable()` — mock `subprocess.run` to raise `FileNotFoundError`; expect `GitCommonDirUnavailableError`.
   - `test_corrupt_repo_raises_git_common_dir_unavailable()` — mock a non-zero exit with stderr that is NOT "not a git repository"; expect `GitCommonDirUnavailableError`.
   - `test_warm_call_uses_cache_no_git_invocation()` — spy on `subprocess.run`; call twice with same path; assert call count is 1.
   - `test_cache_clear_resets_invocation_count()` — spy; call; `resolve_canonical_repo_root.cache_clear()`; call again; assert 2 invocations.
   - `test_sparse_checkout_returns_main_root()` — configure sparse checkout; behavior should be unchanged.
   - `test_detached_head_returns_main_root()` — detach HEAD; behavior should be unchanged.

2. Use `pytest.fixture` for tmp repos. Use `monkeypatch` to spy on `subprocess.run`.

3. Platform awareness: submodule tests are `pytest.mark.skipif(platform.system() == "Windows", reason="submodule edge cases differ on Windows")` as a concession; submodule assertions run on macOS/Linux.

**Files**:
- `tests/charter/test_canonical_root_resolution.py` (new, ~220 lines, 12 test cases)

**Validation**:
- [ ] `pytest tests/charter/test_canonical_root_resolution.py` passes (12 tests).

---

### T010 — Extend `SyncResult` in `src/charter/sync.py`

**Purpose**: Add `canonical_root: Path` field per Q2=C decision.

**Steps**:

1. Edit `src/charter/sync.py` `SyncResult` dataclass (currently at lines 39-47):

   ```python
   @dataclass
   class SyncResult:
       """Result of a charter sync operation."""

       synced: bool
       stale_before: bool
       files_written: list[str]  # Relative to canonical_root.
       extraction_mode: str
       error: str | None = None
       canonical_root: Path | None = None  # NEW (WP02)
   ```

   Rationale for `Path | None`: existing `SyncResult(...)` constructor calls inside `sync.py` (lines 75-80, 125-130, 144-148, 153-157) and in `ensure_charter_bundle_fresh()`'s no-op branch do not pass `canonical_root` until T011 rewires them. The `None` default is a transient state that T011 will eliminate in the SAME commit/PR (every constructor call must set `canonical_root` explicitly before this WP merges).

2. Update every `SyncResult(...)` constructor call in `src/charter/sync.py` to pass `canonical_root=<the resolved canonical root>` — this overlaps with T011's refactor; do them together.

**Files**:
- `src/charter/sync.py` (modified — dataclass definition + constructor call sites; ~10 lines diff)

**Validation**:
- [ ] `python -c "from charter.sync import SyncResult; import inspect; assert 'canonical_root' in inspect.signature(SyncResult).parameters"` succeeds.

---

### T011 — Refactor `ensure_charter_bundle_fresh()` to call resolver + consult manifest

**Purpose**: The chokepoint's semantic upgrade. Make it canonical-root-aware and manifest-authoritative.

**Steps**:

1. Edit `src/charter/sync.py` `ensure_charter_bundle_fresh()` (currently lines 50-90). After the edit:

   ```python
   def ensure_charter_bundle_fresh(repo_root: Path) -> SyncResult | None:
       """Auto-refresh extracted charter artifacts when charter.md exists.

       Resolves repo_root to the canonical (main-checkout) root via
       resolve_canonical_repo_root(). Uses CharterBundleManifest.CANONICAL_MANIFEST
       as the authority for the completeness check.

       See contracts/chokepoint.contract.md for the full contract.
       """
       from charter.bundle import CANONICAL_MANIFEST  # Local import to avoid cycle.
       from charter.resolution import resolve_canonical_repo_root

       canonical_root = resolve_canonical_repo_root(repo_root)
       charter_dir = canonical_root / _KITTIFY_DIRNAME / _CHARTER_DIRNAME
       charter_path = charter_dir / _CHARTER_FILENAME
       if not charter_path.exists():
           return None

       metadata_path = charter_dir / _METADATA_FILENAME
       # v1.0.0 manifest consulted for "what files must exist":
       expected_paths = [canonical_root / p for p in CANONICAL_MANIFEST.derived_files]
       missing_files = [p.name for p in expected_paths if not p.exists()]
       should_force = bool(missing_files)
       stale = False

       if not should_force:
           try:
               stale, _, _ = is_stale(charter_path, metadata_path)
           except Exception as exc:
               logger.warning("Failed to evaluate charter bundle freshness: %s", exc)
               should_force = True

       if not should_force and not stale:
           return SyncResult(
               synced=False,
               stale_before=False,
               files_written=[],
               extraction_mode="",
               canonical_root=canonical_root,
           )

       if missing_files:
           logger.info("Charter bundle incomplete (%s). Attempting auto-sync.", ", ".join(missing_files))
       else:
           logger.info("Charter bundle stale. Attempting auto-sync.")

       result = sync(charter_path, charter_dir, force=should_force)
       # Patch canonical_root into the sync() result.
       result = replace(result, canonical_root=canonical_root)
       if result.error:
           logger.warning("Charter auto-sync failed while refreshing extracted artifacts: %s", result.error)
       return result
   ```

2. `from dataclasses import replace` — add to imports if missing.

3. Exceptions (`NotInsideRepositoryError`, `GitCommonDirUnavailableError`) propagate out of `ensure_charter_bundle_fresh()` unchanged. Do NOT wrap or catch them.

4. Update `sync()` at `src/charter/sync.py:93-159` to set `canonical_root` in every `SyncResult(...)` constructor it returns — use `output_dir.parent.parent.parent` as canonical_root inference, OR simpler: accept `canonical_root` as an optional kw-only arg and default to `None` (then `ensure_charter_bundle_fresh` patches it via `replace()` as shown above). The `replace()` pattern is the simpler fix.

**Files**:
- `src/charter/sync.py` (modified — `ensure_charter_bundle_fresh` body rewritten; ~40 lines diff)

**Validation**:
- [ ] `pytest tests/charter/` (existing tests) passes — no behavioral regression on existing tests except where T012 updated them.
- [ ] `grep -n "resolve_canonical_repo_root" src/charter/sync.py` shows the import and call.
- [ ] `grep -n "CANONICAL_MANIFEST" src/charter/sync.py` shows the import and usage.

---

### T012 — Update `post_save_hook()` + existing SyncResult inspection call sites in `src/charter/sync.py` and its tests

**Purpose**: Ensure no code in WP02's ownership reads `files_written` without knowing the new anchor.

**Steps**:

1. Edit `src/charter/sync.py :: post_save_hook()` (lines 162-184). Any `logger.info(...)` calls that display file paths must anchor them against `result.canonical_root`:

   ```python
   # Before:
   logger.info("Wrote %s", file_name)

   # After:
   full_path = (result.canonical_root / file_name) if result.canonical_root else Path(file_name)
   logger.info("Wrote %s", full_path)
   ```

2. Audit `tests/charter/test_sync.py` (and any existing tests asserting on `SyncResult.files_written` or `SyncResult(...)` construction). Update those tests to:
   - Include `canonical_root=...` when constructing `SyncResult` directly in test fixtures.
   - Anchor path assertions against `canonical_root` where the test checks absolute locations.

3. Do NOT touch `src/specify_cli/cli/commands/charter.py` — that's WP03's scope. WP03 will update the CLI sync handler's display logic.

4. Do NOT touch `src/charter/context.py` — WP03 flips `build_charter_context()` separately.

**Files**:
- `src/charter/sync.py` (modified — `post_save_hook` + possibly other local readers; ~15 lines diff)
- `tests/charter/test_sync.py` (modified — existing tests updated)
- Any other `tests/charter/*.py` file that instantiates `SyncResult` directly

**Validation**:
- [ ] `pytest tests/charter/test_sync.py` passes with the updated assertions.
- [ ] `grep -n "SyncResult(" tests/charter/` — every match includes `canonical_root=` argument.

---

### T013 — Write `tests/charter/test_chokepoint_overhead.py` (NFR-002)

**Purpose**: Bind the chokepoint's warm-overhead budget.

**Steps**:

1. Create `tests/charter/test_chokepoint_overhead.py` (new, ~80 lines):

   ```python
   """NFR-002: chokepoint warm-overhead budget (<10 ms p95)."""
   import time
   from pathlib import Path
   from unittest.mock import patch

   import pytest

   from charter.sync import ensure_charter_bundle_fresh


   @pytest.fixture
   def warm_bundle(tmp_path: Path) -> Path:
       """Create a populated bundle fixture (all v1.0.0 derivatives present, hashes match)."""
       # Init repo, write charter.md, run sync once, return repo path.
       # ...
       return tmp_path


   def test_warm_overhead_p95_under_10ms(warm_bundle: Path) -> None:
       # 100 warm invocations.
       timings_ns: list[int] = []
       for _ in range(100):
           start = time.monotonic_ns()
           result = ensure_charter_bundle_fresh(warm_bundle)
           elapsed = time.monotonic_ns() - start
           timings_ns.append(elapsed)
           assert result is not None
           assert result.synced is False  # No regeneration expected on warm path.

       timings_ms = sorted(t / 1_000_000 for t in timings_ns)
       p95 = timings_ms[int(0.95 * len(timings_ms))]
       assert p95 < 10, f"Chokepoint warm p95 = {p95:.2f}ms (budget: 10ms)"


   def test_warm_chokepoint_does_not_shell_out_to_git_on_cache_hit(warm_bundle: Path) -> None:
       # First call warms the resolver cache.
       ensure_charter_bundle_fresh(warm_bundle)

       # Second call must not invoke subprocess.run for the resolver.
       with patch("charter.resolution.subprocess.run") as spy:
           ensure_charter_bundle_fresh(warm_bundle)
       assert spy.call_count == 0, f"Warm chokepoint triggered {spy.call_count} git invocations"
   ```

**Files**:
- `tests/charter/test_chokepoint_overhead.py` (new, ~80 lines)

**Validation**:
- [ ] `pytest tests/charter/test_chokepoint_overhead.py` passes (2 tests); p95 <10 ms on developer laptop baseline.

---

### T014 — Write `tests/charter/test_resolution_overhead.py` (NFR-003)

**Purpose**: Bind the resolver's overhead budget.

**Steps**:

1. Create `tests/charter/test_resolution_overhead.py` (new, ~70 lines) with similar structure:

   ```python
   def test_warm_resolver_p95_under_5ms(tmp_repo: Path) -> None:
       # Prime the cache, then 100 warm calls.
       resolve_canonical_repo_root(tmp_repo)
       timings_ms: list[float] = []
       for _ in range(100):
           start = time.monotonic_ns()
           resolve_canonical_repo_root(tmp_repo)
           timings_ms.append((time.monotonic_ns() - start) / 1_000_000)
       p95 = sorted(timings_ms)[95]
       assert p95 < 5, f"Resolver warm p95 = {p95:.2f}ms (budget: 5ms)"


   def test_warm_resolver_makes_zero_git_invocations(tmp_repo: Path) -> None:
       resolve_canonical_repo_root(tmp_repo)  # Prime cache.
       with patch("charter.resolution.subprocess.run") as spy:
           for _ in range(100):
               resolve_canonical_repo_root(tmp_repo)
       assert spy.call_count == 0


   def test_cold_resolver_makes_exactly_one_git_invocation(tmp_repo: Path) -> None:
       resolve_canonical_repo_root.cache_clear()
       with patch("charter.resolution.subprocess.run", wraps=__import__("subprocess").run) as spy:
           resolve_canonical_repo_root(tmp_repo)
       assert spy.call_count == 1
   ```

**Files**:
- `tests/charter/test_resolution_overhead.py` (new, ~70 lines)

**Validation**:
- [ ] `pytest tests/charter/test_resolution_overhead.py` passes (3 tests); p95 <5 ms; cold path 1 git invocation; warm path 0.

---

### T015 — Author `occurrences/WP02.yaml` and extend `index.yaml`

**Purpose**: Record every occurrence touched by WP02.

**Steps**:

1. Create `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP02.yaml` per the contract schema:

   ```yaml
   wp_id: WP02
   mission_slug: unified-charter-bundle-chokepoint-01KP5Q2G
   requires_merged: [WP01]
   categories:
     import_path:
       description: "New imports from charter.resolution and charter.bundle."
       include: ["src/charter/**"]
       exclude: []
       occurrences:
         - path: src/charter/sync.py
           pattern: "from charter.resolution import resolve_canonical_repo_root"
           action: leave
           rationale: New import added by T011.
         - path: src/charter/sync.py
           pattern: "from charter.bundle import CANONICAL_MANIFEST"
           action: leave
           rationale: New import added by T011.
     symbol_name:
       description: "New resolver module symbols."
       include: ["src/**", "tests/**"]
       exclude: []
       occurrences:
         - path: src/charter/resolution.py
           pattern: "resolve_canonical_repo_root"
           action: leave
           rationale: Public resolver function.
         - path: src/charter/resolution.py
           pattern: "NotInsideRepositoryError"
           action: leave
         - path: src/charter/resolution.py
           pattern: "GitCommonDirUnavailableError"
           action: leave
         - path: src/charter/sync.py
           pattern: "canonical_root"
           action: leave
           rationale: New SyncResult field.
     test_identifier:
       description: "New test modules."
       include: ["tests/charter/**"]
       exclude: []
       occurrences:
         - path: tests/charter/test_canonical_root_resolution.py
           pattern: "test_.*"
           action: leave
         - path: tests/charter/test_chokepoint_overhead.py
           pattern: "test_.*"
           action: leave
         - path: tests/charter/test_resolution_overhead.py
           pattern: "test_.*"
           action: leave
   carve_outs: []
   must_be_zero_after:
     # Anti-patterns that must NOT appear:
     - "git rev-parse --show-toplevel"  # WP01's temporary; no new usage in WP02 onward.
   verification_notes: "WP02 adds resolver module, extends SyncResult, re-plumbs chokepoint. No reader flips."
   ```

2. Extend `occurrences/index.yaml` to add `WP02` to the `wps` list.

**Files**:
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP02.yaml` (new)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml` (modified)

**Validation**:
- [ ] `python scripts/verify_occurrences.py kitty-specs/.../occurrences/WP02.yaml` exits 0.

---

## Definition of Done

- [ ] T008–T015 all complete.
- [ ] `pytest tests/charter/test_canonical_root_resolution.py tests/charter/test_chokepoint_overhead.py tests/charter/test_resolution_overhead.py` green.
- [ ] Existing `tests/charter/` tests still pass (possibly with T012's test updates).
- [ ] `mypy --strict src/charter/` green.
- [ ] Verifier green against `WP02.yaml`.
- [ ] No edits to `src/specify_cli/core/worktree.py:478-532` (C-011).
- [ ] No edits to `src/charter/compiler.py` or `src/charter/context.py:385-398` (C-012).
- [ ] No edits to reader call sites outside `src/charter/sync.py` (that's WP03's scope).

## Risks

- **Algorithm precision**. The six-step algorithm from the contract must match exactly. Any shortcut (e.g., treating stdout as always-absolute) silently breaks subdirectory or worktree invocations.
- **Benchmark flakiness on CI**. NFR-002 / NFR-003 thresholds may occasionally breach on loaded CI runners. The tests should use `pytest.mark.perf` or similar so CI can retry if needed, but the budget is a hard merge gate on three consecutive runs.
- **Cycle risk with local imports**. `charter.sync` now imports from `charter.bundle` and `charter.resolution`. Use local imports inside functions if a cycle surfaces.

## Reviewer guidance

- Open `src/charter/resolution.py` with the contract open in a split pane. Walk through each step of the algorithm comparing against the contract's six-step list.
- Verify `_resolve_cached` is private (leading underscore) and `resolve_canonical_repo_root` is the public surface.
- Verify `cache_clear` is exposed for tests.
- Verify `SyncResult` gains exactly one new field (`canonical_root`).
- Verify `ensure_charter_bundle_fresh()` calls `resolve_canonical_repo_root()` as its first non-import operation.
- Run benchmarks locally and compare against thresholds. Re-run if CI reports a borderline pass.

## Activity Log

- 2026-04-14T12:32:00Z – claude:sonnet:implementer:implementer – shell_pid=94246 – Started implementation via action command
- 2026-04-14T12:40:16Z – claude:sonnet:implementer:implementer – shell_pid=94246 – WP02 implementation complete: resolver + SyncResult.canonical_root + chokepoint re-plumbed + two perf benches + WP01 TODO(WP02) marker resolved. Carve-outs respected.
