# Phase 0 Research: Post-Merge Reliability And Release Hardening

**Mission**: 068-post-merge-reliability-and-release-hardening
**Date**: 2026-04-07
**Validated against**: commit `7307389a1f529dae9e90279ea972609bb0b420aa`

This document records the architectural decisions made during planning interrogation and the current-main analysis that informed them. No `[NEEDS CLARIFICATION]` markers remain.

---

## Decision 1: Stale-assertion analyzer module location and library

**Decision**: New package at `src/specify_cli/post_merge/stale_assertions.py`. Use Python's stdlib `ast` module for **both** source identifier extraction and test file scanning.

**Rationale**:
- The existing `src/specify_cli/lanes/stale_check.py` module is for **stale lane** detection (overlap with merged lane changes), not stale test assertions. Co-locating WP01 there would invite name collision and conceptual confusion. A new `post_merge/` package gives the analyzer a clean home that signals its post-merge timing and its independence from the lane-merge subsystem.
- `ast` (stdlib) over `libcst`: `libcst` preserves whitespace and comments, which is valuable for code-rewriting tools but useless for an analyzer that only reads. `libcst` adds a dependency, slows parsing, and buys nothing for the FR-001..FR-004 surface.
- `ast` (stdlib) over `tree-sitter`: `tree-sitter` is a multi-language parser. FR-002 narrows the analyzer to Python tests. Adding `tree-sitter` would mean a non-Python build dependency for zero current value.
- `ast` on **both** sides (source + test) instead of `ast` on source + regex on tests: regex over raw test text bleeds false positives from comments and inert string literals (e.g., a docstring mentioning `"foo"` would match). NFR-002's ≤5 FP/100 LOC ceiling is impractical with regex. Parsing test files into ASTs and walking only `Constant` nodes in assertion-bearing positions (`Compare`, `Call(func=Attribute(attr='assertEqual'))`, `Assert`) gives a tight, FP-resistant match.

**Alternatives considered**:
- `libcst` for both — rejected: dependency cost without rewrite benefit.
- `tree-sitter` for cross-language coverage — rejected: out of scope per FR-002 (Python-only).
- `ast` on source + regex on tests — rejected: explodes the FP ceiling.
- Live in `lanes/stale_check.py` next to existing stale-lane code — rejected: name collision and concept confusion.

**Implementation notes**:
- Library entry point: `run_check(base_ref: str, head_ref: str, repo_root: Path) -> StaleAssertionReport`
- The function walks the diff between `base_ref` and `head_ref`, extracts changed Python source identifiers via `ast`, then walks every test file from `git ls-files 'tests/**/*.py'` and emits findings where an assertion-bearing AST node references one of the changed identifiers.
- Confidence indicators (FR-003): `high` (changed function name appears in `assert <name>(...)` directly), `medium` (changed identifier appears in any `Compare`/`Assert` node), `low` (changed string literal matches a `Constant("...")` node anywhere in a test file).

---

## Decision 2: WP04 release-prep command surface

**Decision**: Populate the existing `src/specify_cli/cli/commands/agent/release.py` stub. The command becomes `spec-kitty agent release prep --channel {alpha,beta,stable} [--json]`.

**Rationale**:
- `agent/release.py` is **already a registered live subapp** at `agent/__init__.py:20` with `no_args_is_help=True`. `spec-kitty agent release` returns help text today. It's a public CLI surface, not dead code.
- Removing the registration would break a public surface (even if no one's productively using it). Honoring the existing reservation is lower-risk and consistent with the agent-facing namespace pattern (`agent tasks`, `agent mission`, `agent status`).
- The stub has a stale comment "Deep implementation in WP05" left over from a prior mission's planning. WP04 updates that comment as part of populating the file.

**Alternatives considered**:
- New top-level `spec-kitty release prep` command group parallel to `merge`/`implement` — rejected: invents a new surface when a registered one already exists, creates a deletion cleanup task.
- Both surfaces (top-level + agent) — rejected: unnecessary duplication for a single command.

**Implementation notes**:
- Internal logic optionally lives in `src/specify_cli/release/` package (`changelog.py`, `version.py`, `payload.py`) so the `agent/release.py` file stays a thin shim that wires typer arguments to library functions. If the surface stays small (≤100 LOC), inline it instead.
- The agent surface produces JSON by default when `--json` is passed (consistent with `agent mission` patterns) and printable text otherwise.
- FR-014 enforces local-only: changelog is built from `kitty-specs/<mission>/` artifacts and `meta.json`, not from GitHub API calls.

---

## Decision 3: WP01 CLI subcommand path and library-import wiring

**Decision**: New `agent tests` subgroup at `src/specify_cli/cli/commands/agent/tests.py`. Command: `spec-kitty agent tests stale-check --base <ref> --head <ref>`. The merge command invokes the analyzer via direct library import (`from specify_cli.post_merge.stale_assertions import run_check`), NOT by spawning the CLI subcommand.

**Rationale**:
- Two thin shims around one library function is cleaner than one shim and a subprocess invocation. Subprocess spawning would add startup cost (typer + rich init), JSON serialization round-trips, and error-propagation friction. None of those are warranted when the merge runner and the CLI live in the same Python process.
- The new `agent tests` group hosts `stale-check` today and gives `agent tests baseline`, `agent tests run`, etc. a natural place to grow. It matches the existing `agent tasks`/`agent mission`/`agent status` pattern.
- Locking the command name (instead of leaving it as a placeholder example) keeps FR-004 testable: tests can assert the exact CLI path.

**Alternatives considered**:
- Place under `agent` directly as `spec-kitty agent stale-assertions` — rejected: less namespacing room for future test tooling.
- Wire as a flag on `spec-kitty merge --check-stale-assertions` — rejected: makes the analyzer non-discoverable as an independent tool, conflates the merge runner with the diff tool.
- Subprocess spawn from merge runner — rejected: see rationale above.

**Implementation notes**:
- `cli/commands/agent/tests.py` registers a typer subapp; `agent/__init__.py` adds `app.add_typer(tests.app, name="tests")`.
- The merge runner adds a single import (`from specify_cli.post_merge.stale_assertions import run_check`) and calls it after the FR-019 `safe_commit` step but before the merge summary print.
- Both call sites pass the same `(base_ref, head_ref, repo_root)` arguments and consume the same `StaleAssertionReport` dataclass.

---

## Current-Main Analysis: existing modules WP01/WP02/WP04/WP05 will integrate with

### `src/specify_cli/git/commit_helpers.py` (WP02 dependency)

`safe_commit` is defined at `commit_helpers.py:38` and re-exported from `specify_cli/git/__init__.py`. The helper takes `repo_path`, `files_to_commit`, `commit_message`, and `allow_empty`. It uses a stash-and-restore pattern to preserve unrelated staged changes (verified by reading the stash-list scanning logic). FR-019 invokes it identically to the existing `cli/commands/implement.py:460` call site.

**No modification needed.** WP02 imports it as-is.

### `src/specify_cli/lanes/stale_check.py` (WP01 namespace neighbor)

Existing module for **stale lane** detection: a lane branch is stale when the mission branch has advanced and the changed files overlap. Algorithm: merge-base + diff intersection. **Different concept from WP01's stale-test-assertion analyzer.** Co-location was rejected; WP01 lives in a new `post_merge/` package.

**No modification needed.** WP01 only needs to avoid name collision with this module.

### `src/specify_cli/cli/commands/agent/release.py` (WP04 target)

Currently a stub typer app:

```python
"""Release packaging commands for AI agents."""
import typer
app = typer.Typer(name="release", help="Release packaging commands for AI agents", no_args_is_help=True)
# Deep implementation in WP05
```

The app is registered in `agent/__init__.py:20`. The "Deep implementation in WP05" comment is from a prior mission's planning and is stale — WP04 updates it.

**Modified by WP04** to add the `prep` subcommand.

### `src/specify_cli/lanes/recovery.py` (WP05 target)

Contains `scan_recovery_state` at lines 174-267. Current implementation iterates branches matching `kitty/mission-{slug}*` returned by `_list_mission_branches`. **Does not consult mission status events.** When dependency lane branches have been merged-and-deleted, no live branches exist to scan, so the function returns "nothing to recover" — leaving the user with an unblockable workflow. FR-021 extends this to consult `kitty-specs/<mission>/status.events.jsonl` alongside live branch state.

**Modified by WP05** for FR-021. Existing tests in the recovery test file should be extended (not replaced) — current coverage exists for the live-branch path, which still needs to work.

### `src/specify_cli/cli/commands/implement.py` (WP05 target)

Currently does not accept a `--base` flag. After upstream lanes have been merged and their branches deleted, a user starting a downstream WP has no supported way to point at the post-merge target branch as the implementation base. FR-021 adds `--base main` (or any explicit branch ref) so the post-merge unblocking path documented in Scenario 7 works without manual `.kittify/` edits.

**Modified by WP05** for FR-021.

### `src/specify_cli/cli/commands/merge.py` (WP02 target)

`_run_lane_based_merge` lives at lines 277-464. Key call sites WP02 modifies:
- The `--strategy` typer parameter is currently declared in the CLI signature but **discarded** before reaching the lane-merge implementation. WP02 wires it through.
- `_mark_wp_merged_done` is called in a loop that writes `done` events via `emit_status_transition` → `_store.append_event`. **No `safe_commit` follows.** WP02 adds the safe_commit between the mark-done loop and the worktree-removal step.
- `cleanup_merge_workspace` and `clear_state` at the end touch `.kittify/runtime/merge/<mission_id>/state.json`, which is intentionally ephemeral runtime state — out of scope for the FR-019 fix per the spec's "Scope (preempting 'what about MergeState?')" subsection.

**Modified by WP02** for FR-005..FR-009, FR-019, FR-020.

### `src/specify_cli/lanes/merge.py` (WP02 target)

Contains the lower-level lane merge logic that hardcodes merge commits at line 227. WP02 changes this to honor the strategy parameter passed down from the CLI surface.

**Modified by WP02** for FR-005..FR-007.

### `.github/workflows/ci-quality.yml` (WP03 target — conditional)

Currently enforces critical-path diff coverage and emits a separate advisory full-diff report. WP03 begins with a written validation (FR-010) of whether this satisfies the policy intent of #455. If yes, FR-011 fires and the workflow is left alone (only docs/messages tightened). If no, FR-012 fires and the workflow is adjusted.

**Possibly modified by WP03** depending on the validation outcome.

---

## Failure-Mode Reproduction: FR-019 (status-events loss)

The full reproduction trail is captured in `spec.md` under "Mission 067 Failure-Mode Evidence (A): #416 status-events loss". Summary for plan-phase reference:

1. `_run_lane_based_merge` writes `done` events via `_mark_wp_merged_done` → `emit_status_transition` → `_store.append_event` (a pure file-write).
2. **No `safe_commit` follows.**
3. When the user resets the working tree to rebuild the merge externally (e.g., for a squash PR to satisfy linear-history protection), the uncommitted events are wiped.
4. The squash commit is built from the committed working tree, which never contained the events.

**Verification**: `status.events.jsonl` was read at `bc47f57d` (the local mission→main merge commit, still reachable via reflog). 43 lines, identical to current. Zero `to_lane: done` entries. Confirms the events lived only in the post-merge working tree, never in committed state.

**Fix surface**: see FR-019 in `spec.md`.

---

## Failure-Mode Reproduction: FR-021 (post-merge recovery deadlock)

The full reproduction trail is captured in `spec.md` under "Mission 067 Failure-Mode Evidence (B): #415 post-merge recovery deadlock". Summary for plan-phase reference:

1. A mission has WPs WP01–WP06 in a dependency chain.
2. WP01–WP05 are implemented, reviewed, and merged. Their lane branches are deleted by post-merge cleanup.
3. The user wants to start WP06.
4. `scan_recovery_state` only iterates branches matching `kitty/mission-{slug}*`. Finding none, it declares the workspace clean.
5. `spec-kitty implement WP06` has no `--base` flag, so it can't be told to start from the current target branch tip.
6. The user has no supported path to start WP06 without manual `.kittify/` state edits.

**Fix surface**: extend `scan_recovery_state` to consult mission status events alongside live branch state; add `--base <ref>` to the `implement` command.

---

## Library-Import Wiring Rationale (Decision 3 follow-up)

The merge runner imports the analyzer directly:

```python
from specify_cli.post_merge.stale_assertions import run_check
report = run_check(base_ref=merge_base, head_ref="HEAD", repo_root=repo_root)
```

This is preferred over spawning `subprocess.run(["spec-kitty", "agent", "tests", "stale-check", ...])` because:

1. **Startup cost**: typer + rich init burns ~150ms per CLI invocation. Inline import is essentially free.
2. **Error propagation**: in-process exceptions propagate naturally; subprocess errors require parsing stderr and reconstructing exception types.
3. **Output handling**: the merge summary needs the analyzer's findings as a Python object, not as JSON-via-pipe that has to be re-parsed.
4. **Test surface**: integration tests exercise the merge runner end-to-end without needing to mock `subprocess` behavior.
5. **Single source of truth**: the CLI command and the merge runner are both thin shims around the same `run_check` library function. There's no risk of one shim drifting from the other.

---

## Outstanding `[NEEDS CLARIFICATION]` items

**None.** All planning interrogation answers are locked in `plan.md` and reflected here.
