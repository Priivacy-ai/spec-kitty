# Phase 0 Research: Unified Charter Bundle and Read Chokepoint

**Mission**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Companion**: [plan.md](plan.md) §"Plan-Phase Decisions" D-10

Four narrow investigations producing the concrete inputs that WP2.1–WP2.4 need.

---

## R-1 — Exhaustive reader-site inventory

### Question

Which code paths read any artifact under `.kittify/charter/` (directly or indirectly), and which of those currently bypass `ensure_charter_bundle_fresh()`? The answer becomes the WP2.3 occurrence artifact's reader registry and the source of truth for `tests/charter/test_chokepoint_coverage.py` (FR-011).

### Method

1. **Static grep** across `src/`:
   ```
   rg -n 'charter\.md|governance\.yaml|directives\.yaml|metadata\.yaml|references\.yaml|interview/answers\.yaml|context-state\.json|\.kittify/charter|charter_bundle|build_charter_context|load_governance_config|load_directives_config|resolve_project_charter_path' src/
   ```
2. **Python AST walk** — for every `from charter... import` or `from specify_cli.charter... import`, resolve the symbol and mark the importing module as a candidate reader.
3. **String-literal sweep** — search for any hard-coded relative path fragment that routes into the charter tree: `../../../.kittify`, `../../.kittify`, `.kittify/memory`, `.kittify/AGENTS.md`.
4. **Dynamic-dispatch audit** — importlib / getattr against any `charter*` module.

### Decision

Seed the WP2.3 occurrence artifact with the following registry. WP2.3 verifies and expands this list during implementation.

**Confirmed direct readers (bypass chokepoint today)** — must be flipped in WP2.3:

| Site (file:approx line) | Bypass mechanism | Fix |
| --- | --- | --- |
| `src/charter/context.py:406-661` (`build_charter_context`) | Direct `charter_path.read_text()` (~line 555) and `_load_references(references_path)` (~line 637) | Call `ensure_charter_bundle_fresh()` at the top of the function; use `SyncResult.canonical_root` to anchor subsequent reads. |
| `src/specify_cli/dashboard/charter_path.py:8-17` (`resolve_project_charter_path`) | Existence-only check without freshness guarantee | Call the chokepoint before the existence check; surface a freshness-aware result. |
| `src/specify_cli/dashboard/scanner.py` charter probes | TBD by implementation grep; suspected direct existence checks in the scanner's per-frame loop | Route through the chokepoint; use NFR-002's warm-overhead budget as the perf bar. |
| `src/specify_cli/dashboard/server.py` charter endpoints | TBD by implementation grep | Same. |
| `src/specify_cli/cli/commands/charter.py` handlers | TBD — need per-handler grep | Handlers that read bundle artifacts before rendering output route through the chokepoint. Handlers that only touch `charter.md` source (e.g., `interview`, `generate`) are out of scope. |
| `src/specify_cli/next/prompt_builder.py` charter injection | TBD — need targeted grep | Route through the chokepoint. |
| `src/specify_cli/cli/commands/agent/workflow.py` workflow charter injection | TBD — need targeted grep | Route through the chokepoint. |

**Confirmed chokepoint-routed readers** — no change needed except D-3 `canonical_root` field propagation:

| Site | Already uses chokepoint |
| --- | --- |
| `src/charter/sync.py:187-226` (`load_governance_config`) | Yes, at line 204 |
| `src/charter/sync.py:229-264` (`load_directives_config`) | Yes, at line 244 |
| `src/charter/resolver.py:43-135` (`resolve_governance`) | Yes, transitively via the two loaders above |

**Duplicate-package twins (C-003 lockstep)** — WP2.3 updates only if still live:

- `src/specify_cli/charter/context.py`, `src/specify_cli/charter/sync.py`, etc.
- Files that are pure re-exports are untouched; files carrying a direct-read live path are flipped in lockstep.

### Rationale

The three "TBD" entries in the table are deliberate — the plan phase commits to the shape of the fix without pre-committing to the exhaustive line-level inventory, which is the WP2.3 occurrence artifact's responsibility (verification-by-completeness per #393).

### Alternatives considered

- **"Only flip `build_charter_context`"** — rejected. FR-011's AST walk would fail against the dashboard and next-prompt readers. Acceptance Gate 3 ("every charter-derivative reader goes through `ensure_charter_bundle_fresh()`") is universal.
- **"Flip everything via a module-level monkey-patch or decorator"** — rejected. Too clever; defeats static analysis; makes the AST-walk test non-trivial.
- **"Cut over duplicate-package readers as part of WP2.3 by deleting `src/specify_cli/charter/` entirely"** — rejected per spec C-003 / Q3=B.

---

## R-2 — `git rev-parse --git-common-dir` behavior matrix

### Question

Under what conditions does `git rev-parse --git-common-dir` return an unexpected value or fail? The answer becomes the fixture matrix for `tests/charter/test_canonical_root_resolution.py` and the basis for the `GitCommonDirUnavailableError` surface.

### Method

Prototype `resolve_canonical_repo_root()` against the following fixture conditions and record exit-code + stdout behavior. Each condition exercised locally before the plan is considered complete. Findings become the test matrix.

### Decision

| Condition | Observed behavior | Resolver response |
| --- | --- | --- |
| Plain repo (main checkout) | exit 0; stdout = `.git` (or absolute) | Return parent of `.git` (the repo working directory). |
| Worktree attached via `git worktree add` | exit 0; stdout = absolute path to the main repo's `.git` dir (not `.git/worktrees/<name>`) | Return parent of that path — the main checkout. ✅ This is the designed behavior per Q1=A. |
| Linked worktree (bare main repo + multiple worktrees) | exit 0; stdout = absolute path to the common git dir | Return the parent of the common git dir. Same resolution. |
| Submodule-attached checkout | exit 0; stdout = path inside `<parent>/.git/modules/<name>` | Return the submodule's working directory (the parent of `.git`-as-file). Distinct from the superproject. Acceptable — spec-kitty operates on the submodule as its own project. |
| Sparse checkout | exit 0; stdout = `.git` — unaffected by sparse status | Same as plain repo. |
| Detached HEAD | exit 0; stdout = `.git` — unaffected by HEAD state | Same as plain repo. |
| Inside `.git` dir itself | exit 0; stdout = `.` | Treated as an error case — resolver raises `NotInsideRepositoryError`. Tests in `tests/charter/test_canonical_root_resolution.py` exercise this. |
| Non-repo path (e.g., `/tmp`) | exit 128; stderr = `fatal: not a git repository` | Resolver raises `NotInsideRepositoryError`. |
| `git` binary missing from PATH | `FileNotFoundError` from `subprocess.run` | Resolver re-raises as `GitCommonDirUnavailableError` with a structured message identifying the missing binary. No fallback per C-001 / C-009. |

### Rationale

Git's `--git-common-dir` is the canonical plumbing for this exact question; no filesystem-path heuristic is required. The LRU cache keys on absolute path of the invocation directory so repeated calls from the same directory hit cache.

### Alternatives considered

- **`gitpython` library** — rejected. Adds a runtime dependency for a one-line `subprocess` call. Charter §Technical Standards pins dependencies tightly.
- **Hand-rolled `.git/` walk** — rejected per C-009. Fragile under submodules and worktrees.

---

## R-3 — `SyncResult` caller audit

### Question

Which callers of the chokepoint (or of `sync()`) inspect the returned `SyncResult` today, and of those, which would observe incorrect paths once `files_written` becomes relative to `canonical_root` rather than the caller-provided `repo_root`?

### Method

Grep across `src/` and `tests/`:
```
rg -n 'SyncResult|files_written|sync_result|ensure_charter_bundle_fresh|post_save_hook' src/ tests/
```

### Decision

**Current `SyncResult` callers on `main`** (inventory seeded from the audit; refined during WP2.2):

| Caller (file:approx line) | Uses `files_written`? | Needs rewire? |
| --- | --- | --- |
| `src/charter/sync.py :: post_save_hook()` (lines 162-184) | Yes — displays the file list | Rewire to use `SyncResult.canonical_root / p` for each displayed path. |
| `src/charter/sync.py :: ensure_charter_bundle_fresh()` (lines 50-90) | Returns `SyncResult` | Behavior moved to use `canonical_root` internally; callers outside see it in the new field. |
| `src/specify_cli/cli/commands/charter.py :: sync()` (line ~347) | Inspects the result and prints | Rewire to use `canonical_root` when formatting output. |
| Tests under `tests/charter/` that assert on `files_written` | Varies | Rewire each assertion to anchor paths against `canonical_root`. |

### Decision

Add `canonical_root: Path` as a new field in WP2.2. Keep `files_written: list[Path]` relative to that root. Rewire every caller listed above in WP2.2 (the same PR that introduces the field). Do not ship a back-compat shim; each caller is edited directly per C-001.

### Rationale

Spec Q2=C user decision. Adding a field avoids silent behavior change for callers that previously treated `files_written` as "relative to `repo_root` passed in by caller" — that interpretation is now wrong for worktree callers, and the new field is the explicit anchor.

### Alternatives considered

- **Absolute paths in `files_written`** (Q2=A) — rejected by user. Causes noise in logs and breaks snapshot tests that compared paths against expected relative strings.
- **Keep `files_written` relative to caller-supplied `repo_root`** (Q2=B) — rejected by user. Ambiguous: worktree callers would see different paths depending on where they were when they called, and any refactor that changes the invocation directory would silently change the path strings.

---

## R-4 — Dashboard typed-contract surface

### Question

What exactly is the shape of the dashboard typed-contract output that must survive byte-identically through WP2.3? Where does the output come from, and what non-deterministic fields must be redacted before the baseline is captured?

### Method

1. Identify the dashboard endpoints that expose `WPState` and `Lane` types (from `#361`).
2. Run a representative fixture through them on pre-WP2.3 `main` and inspect the JSON.
3. Enumerate non-deterministic fields (timestamps, IDs, ordering of mappings).

### Decision

Golden baseline captured at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` by a committed capture script `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py`. Capture logic:

1. Boot the dashboard in a temp fixture project with a pre-staged charter and one mission with three WPs in varying states.
2. Hit the dashboard endpoints that produce `WPState` / `Lane` contracts (endpoint list enumerated in WP2.3 step A).
3. Before writing JSON:
   - Sort all mapping keys (Python `json.dumps(..., sort_keys=True)`).
   - Replace any `"*_at"` timestamp field with the literal string `"<ts>"`.
   - Replace any ULID field value whose key is not an identity field (identity fields like `mission_id`, `wp_id` stay verbatim) with a stable placeholder.
   - Sort all array fields whose order is semantically irrelevant (mission list, WP list within a mission).

The regression test `tests/test_dashboard/test_charter_chokepoint_regression.py` applies the same redactions to the post-WP2.3 output before comparing.

### Rationale

`#361` typed contracts are a stability guarantee, not a UI ordering guarantee. Redacting timestamps and sorting prevents flaky failures while still catching any actual semantic drift.

### Alternatives considered

- **Compare entire JSON verbatim** — rejected. Flaky on every run due to timestamps.
- **Compare only a subset of fields** — rejected. Narrows the regression surface; a reshape that drops a field silently would pass.
- **Commit the fixture project as part of `tests/fixtures/`** — deferred. The capture script assembles it in-process for now; if the fixture becomes large (>100 files), promote it to a committed fixture directory in a follow-up.

---

## Phase 0 complete

All four investigations resolved. Every open `[NEEDS CLARIFICATION]` from the spec is closed:

- Q1 (resolver location) → `src/charter/resolution.py` (D-2).
- Q2 (SyncResult path semantics) → new `canonical_root` field; `files_written` relative to it (D-3 / R-3).
- Q3 (manifest schema version) → `"1.0.0"` independent of package version (D-1).
- Q4 (bundle CLI surface) → `spec-kitty charter bundle validate [--json]` only; no `doctor` integration in this tranche (D-4).

WP2.1–WP2.4 may proceed to implementation once `/spec-kitty.tasks` materializes the task files.
