# Phase 0 Research: Unified Charter Bundle and Read Chokepoint

**Mission**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Companion**: [plan.md](plan.md) §"Plan-Phase Decisions" D-10

Four narrow investigations producing the concrete inputs that WP2.1–WP2.4 need. Revised 2026-04-14 after design review corrected three P1/P2 findings (worktree scope, manifest scope, resolver algorithm).

---

## R-1 — Exhaustive reader-site inventory

### Question

Which code paths read any of the three `sync()`-produced derivatives (`governance.yaml`, `directives.yaml`, `metadata.yaml`) directly or through `charter.md`, and which of those currently bypass `ensure_charter_bundle_fresh()`? The answer becomes the WP2.3 occurrence artifact's reader registry and the source of truth for `tests/charter/test_chokepoint_coverage.py` (FR-011).

**Scope**: v1.0.0 manifest files only. Readers of `references.yaml` (compiler pipeline) and `context-state.json` (runtime state) are NOT in scope and are NOT required to route through the chokepoint in this tranche.

### Method

1. **Static grep** across `src/`:
   ```
   rg -n 'charter\.md|governance\.yaml|directives\.yaml|metadata\.yaml|\.kittify/charter|build_charter_context|load_governance_config|load_directives_config|resolve_project_charter_path' src/
   ```
2. **Python AST walk** — for every `from charter... import` or `from specify_cli.charter... import`, resolve the symbol and mark the importing module as a candidate reader.
3. **String-literal sweep** — search for any hard-coded relative path fragment that routes into the `.kittify/charter/` tree.
4. **Dynamic-dispatch audit** — importlib / getattr against any `charter*` module.

### Decision

Seed the WP2.3 occurrence artifact with the following registry. WP2.3 verifies and expands this list during implementation.

**Confirmed direct readers (bypass chokepoint today)** — must be flipped in WP2.3:

| Site (file:approx line) | Bypass mechanism | Fix |
| --- | --- | --- |
| `src/charter/context.py:406-661` (`build_charter_context`) | Direct `charter_path.read_text()` (~line 555) — note this reads the tracked `charter.md` but is still covered by the chokepoint contract because staleness vs. derivatives is the concern. | Call `ensure_charter_bundle_fresh()` at the top of the function; use `SyncResult.canonical_root` to anchor subsequent reads. This ensures the reader observes fresh derivatives for downstream `load_governance_config` / `load_directives_config` calls. |
| `src/specify_cli/dashboard/charter_path.py:8-17` (`resolve_project_charter_path`) | Existence-only check without freshness guarantee | Call the chokepoint before the existence check; surface a freshness-aware result. |
| `src/specify_cli/dashboard/scanner.py` charter probes | TBD by implementation grep; suspected direct existence checks in the scanner's per-frame loop | Route through the chokepoint; use NFR-002's warm-overhead budget as the perf bar. |
| `src/specify_cli/dashboard/server.py` charter endpoints | TBD by implementation grep | Same. |
| `src/specify_cli/cli/commands/charter.py` handlers | TBD — need per-handler grep | Handlers that read bundle artifacts before rendering output route through the chokepoint. Handlers that only touch `charter.md` source (e.g., `interview`, `generate`) are out of scope. |
| `src/specify_cli/next/prompt_builder.py` charter injection | TBD — need targeted grep | Route through the chokepoint. |
| `src/specify_cli/cli/commands/agent/workflow.py` workflow charter injection | TBD — need targeted grep | Route through the chokepoint. |

**Confirmed chokepoint-routed readers** — no code change needed except D-3 `canonical_root` field propagation:

| Site | Already uses chokepoint |
| --- | --- |
| `src/charter/sync.py:187-226` (`load_governance_config`) | Yes, at line 204 |
| `src/charter/sync.py:229-264` (`load_directives_config`) | Yes, at line 244 |
| `src/charter/resolver.py:43-135` (`resolve_governance`) | Yes, transitively via the two loaders above |

**Out of R-1 scope** — not required to route through the chokepoint in this tranche:

| Pipeline | File(s) | Rationale |
| --- | --- | --- |
| Compiler (`references.yaml` producer) | `src/charter/compiler.py:169-196` (`write_compiled_charter`) | Produces `references.yaml`, which is out of v1.0.0 manifest scope. |
| Context-state writes | `src/charter/context.py:385-398` | Writes `context-state.json` runtime state; out of v1.0.0 manifest scope. |

**Duplicate-package twins (C-003 lockstep)** — WP2.3 updates only if still live:

- `src/specify_cli/charter/context.py`, `src/specify_cli/charter/sync.py`, etc.
- Files that are pure re-exports are untouched; files carrying a direct-read live path are flipped in lockstep.

**Explicitly OUT of R-1 scope** (not reader sites, not touched by this mission):

- `src/specify_cli/core/worktree.py:478-532` — creates `.kittify/memory/` and `.kittify/AGENTS.md` symlinks. These are **project memory and agent-instructions sharing**, NOT charter bundle materialization. They are documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179` ("a single source of truth for project principles"). The v2.3 worktree-visibility gate is solved by canonical-root resolution in `ensure_charter_bundle_fresh()`, not by touching this file.

### Rationale

The three "TBD" entries in the table are deliberate — the plan phase commits to the shape of the fix without pre-committing to the exhaustive line-level inventory, which is the WP2.3 occurrence artifact's responsibility (verification-by-completeness per #393).

### Alternatives considered

- **"Only flip `build_charter_context`"** — rejected. FR-011's AST walk would fail against the dashboard and next-prompt readers. Acceptance Gate 3 ("every charter-derivative reader goes through `ensure_charter_bundle_fresh()`") is universal within v1.0.0 scope.
- **"Flip everything via a module-level monkey-patch or decorator"** — rejected. Too clever; defeats static analysis; makes the AST-walk test non-trivial.
- **"Cut over duplicate-package readers as part of WP2.3 by deleting `src/specify_cli/charter/` entirely"** — rejected per spec C-003 / Q3=B.
- **"Extend Phase 2 to also route references.yaml / context-state.json readers through the chokepoint"** — rejected. Those are separate pipelines with different invariants; conflating them into v1.0.0 manifest scope was the original P1 finding. Deferred to a later tranche with its own manifest schema version.

---

## R-2 — `git rev-parse --git-common-dir` behavior matrix (corrected)

### Question

Under what conditions does `git rev-parse --git-common-dir` return an unexpected value or fail? What is the **actual** stdout format across invocation conditions? The answer becomes the fixture matrix for `tests/charter/test_canonical_root_resolution.py` and the basis for the `GitCommonDirUnavailableError` surface.

### Method

Prototype `resolve_canonical_repo_root()` against each fixture condition and record exit-code + **actual** stdout behavior. **Corrected 2026-04-14** after local verification revealed the original R-2 table's paths were paraphrased rather than observed.

### Decision

The resolver's algorithm accounts for the observed stdout shape. The algorithm, documented in full at [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md), is:

```
1. Normalize file inputs to parent directory.
2. subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=<dir>, ...)
3. Classify exit code; raise on "not a repo" or other failure.
4. Resolve stdout: stdout may be relative to cwd or absolute; resolve via
   Path(stdout) if absolute else (cwd / stdout).resolve().
5. Detect "inside .git/" edge case: if resolved input is the common_dir or
   a descendant, raise NotInsideRepositoryError.
6. canonical_root = common_dir.parent.
```

Observed stdout (verified locally 2026-04-14):

| cwd | stdout | absolute? | resolves to | canonical_root |
| --- | --- | --- | --- | --- |
| `<repo>` | `.git` | No | `<repo>/.git` | `<repo>` ✓ |
| `<repo>/src/charter` | `../../.git` | No | `<repo>/.git` | `<repo>` ✓ |
| `<repo>/.git` (inside git dir) | `.` | No | `<repo>/.git` | step 5 detects → raise `NotInsideRepositoryError` |
| `<repo>/.worktrees/foo` (linked worktree) | absolute path to `<main>/.git` | Yes | `<main>/.git` | `<main>` ✓ |
| Non-repo path | empty; exit 128; stderr contains `not a git repository` | — | — | raise `NotInsideRepositoryError` |
| Submodule | `.git/modules/sub` (relative to `<repo>`) | No | `<repo>/.git/modules/sub` | `<repo>/.git/modules` — submodule-specific; documented edge case |
| Sparse checkout | same as plain repo | — | — | same |
| Detached HEAD | same as plain repo | — | — | same |
| `git` binary missing | raises `FileNotFoundError` in `subprocess.run` | — | — | raise `GitCommonDirUnavailableError` |

### Rationale

Git's `--git-common-dir` is the canonical plumbing for this exact question. The original R-2 table incorrectly claimed "Returns the working directory" — in reality, `--git-common-dir` returns the **git common directory** (either relative to cwd or absolute), and `canonical_root` is its `.parent`. The algorithm accounts for both relative and absolute stdout and for the `.` edge case when invoked from inside `.git/` itself.

### Alternatives considered

- **`gitpython` library** — rejected. Adds a runtime dependency for a one-line `subprocess` call. Charter §Technical Standards pins dependencies tightly.
- **Hand-rolled `.git/` walk** — rejected per C-009. Fragile under submodules and worktrees.
- **Second `git` call to `--absolute-git-dir`** — rejected. Doubles the subprocess count per cold call, breaking NFR-003's ≤1-invocation-per-call budget. Resolving stdout against `cwd` in one step achieves the same result.

---

## R-3 — `SyncResult` caller audit

### Question

Which callers of the chokepoint (or of `sync()`) inspect the returned `SyncResult` today, and of those, which would observe incorrect paths once `files_written` becomes relative to `canonical_root` rather than the caller-provided `repo_root`?

### Method

Grep across `src/` and `tests/`:
```
rg -n 'SyncResult|files_written|sync_result|ensure_charter_bundle_fresh|post_save_hook' src/ tests/
```

Narrow scope: only the three v1.0.0 manifest files (`governance.yaml`, `directives.yaml`, `metadata.yaml`) are in the chokepoint's ownership. Callers that read other charter artifacts are not rewired by this mission.

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

- **Absolute paths in `files_written`** (Q2=A) — rejected by user. Causes noise in logs and breaks snapshot tests.
- **Keep `files_written` relative to caller-supplied `repo_root`** (Q2=B) — rejected by user. Ambiguous.

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
   - Sort all array fields whose order is semantically irrelevant.

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

Design-review corrections (2026-04-14) also resolved:

- Scope correction (worktree code untouched; gate 2 reframed to reader behavior).
- Manifest v1.0.0 narrowing (`sync()`-produced files only; `references.yaml` / `context-state.json` deferred).
- Resolver algorithm correction (stdout is relative-to-cwd or absolute; algorithm resolves accordingly; file inputs normalized to parent dir; `.git/`-interior detected explicitly).

WP2.1–WP2.4 may proceed to implementation once `/spec-kitty.tasks` materializes the task files.
