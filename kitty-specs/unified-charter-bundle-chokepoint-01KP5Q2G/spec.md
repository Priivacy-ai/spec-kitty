# Feature Specification: Unified Charter Bundle and Read Chokepoint

**Mission ID**: `01KP5Q2G4Z39ZVRX2FY3NWXZQW` (`mid8`: `01KP5Q2G`)
**Mission Slug**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Mission Type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-04-14 (design-review corrections 2026-04-14)
**Parent EPIC**: [Priivacy-ai/spec-kitty#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) — Charter as Synthesis & Doctrine Reference Graph
**Tracking issue**: [Priivacy-ai/spec-kitty#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) — [Phase 2] Unified emergent bundle layout + read chokepoint
**Architecture reference**: §6 (unified emergent bundle), §11 Phase 2
**Related WP issues**: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478) (WP2.1), [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480) (WP2.2), [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481) (WP2.3), [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479) (WP2.4)
**Closes on merge (issue-linkage from #464)**: [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451) (fresh-clone auto-materialization), [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339) (stale-charter-in-worktree)
**Safety-net dependency**: [#361](https://github.com/Priivacy-ai/spec-kitty/issues/361) — dashboard typed contracts (WPState / Lane)
**Guardrail reference**: [Priivacy-ai/spec-kitty#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) — bulk-edit occurrence-classification pattern (landed)
**Phase 1 predecessor**: [#627](https://github.com/Priivacy-ai/spec-kitty/pull/627) / `db451b8f` (Phase 1 excision — curation, `_proposed/`, inline refs)

---

## Problem Statement

Phase 1 of the Doctrine Reference Graph (DRG) rebuild landed on `main` on 2026-04-14 via [#627](https://github.com/Priivacy-ai/spec-kitty/pull/627) / `db451b8f`. That tranche excised doctrine curation, removed `_proposed/` trees, stripped inline reference fields from shipped artifacts, collapsed to a single `build_charter_context` path, and made DRG-backed charter resolution live. As of the current `main` the charter compilation pipeline is DRG-driven, but the **distribution and read surface** of the compiled bundle is still unfinished:

- **The chokepoint is under-adopted.** `ensure_charter_bundle_fresh()` exists at `src/charter/sync.py:50-90` and auto-refreshes the derived bundle when `charter.md` exists but the extracted YAMLs are missing or stale. Only two internal loaders call it: `load_governance_config()` at `src/charter/sync.py:204` and `load_directives_config()` at `src/charter/sync.py:244`. The primary consumer of charter state — `build_charter_context()` at `src/charter/context.py:406-661` — bypasses the chokepoint. Dashboard charter path resolution at `src/specify_cli/dashboard/charter_path.py:8-17` performs an existence check only, not a freshness guarantee.
- **Readers running inside worktrees observe a missing bundle rather than the main-checkout bundle.** `src/specify_cli/core/worktree.py:478-532` intentionally symlinks `.kittify/memory/` and `.kittify/AGENTS.md` into each worktree — that mechanism is documented in `src/specify_cli/templates/AGENTS.md:168-179` as "a single source of truth for project principles" and is **not** part of the charter bundle. Separately, the worktree setup code does NOT materialize `.kittify/charter/` at all. A reader in a worktree that calls `ensure_charter_bundle_fresh(worktree_path)` today looks at `worktree_path/.kittify/charter/charter.md` which does not exist → returns `None` → the reader degrades to a "no charter" path. Issue [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339) originally proposed mirroring the memory/AGENTS symlink pattern for the charter directory; Phase 2 supersedes that proposal with a better mechanism — canonical-root resolution inside the chokepoint so worktree readers transparently read the main-checkout bundle without any filesystem duplication.
- **The bundle layout is currently implicit rather than contractual.** On current `main`, `.kittify/charter/` carries a flat set of files: `charter.md` (tracked) and — when sync has run — `governance.yaml`, `directives.yaml`, `metadata.yaml` (from `src/charter/sync.py:32-36` `_SYNC_OUTPUT_FILES`). Other files may appear under the same directory: `references.yaml` (produced by the separate compiler pipeline at `src/charter/compiler.py:169-196`), `context-state.json` (runtime first-load state written by `src/charter/context.py:385-398`), and optionally `interview/answers.yaml` and `library/*.md` when the charter was generated interactively. There is no explicit bundle contract declaring which files are "the sync-produced bundle", no manifest, no single entry point describing what a reader can expect to see. Architecture §6 and issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) describe a single compiled governance bundle with **one staleness check, one chokepoint, and one materialization step**. Phase 2 delivers that contract at the scope the chokepoint actually owns — the three `sync()`-produced files.
- **Migration `m_3_2_0_unified_bundle.py` does not exist** and the implemented migration on `main` is `m_3_2_3_unified_bundle.py`. That filename is not being renumbered retroactively, even though the safe command-cleanup migration that once occupied `3.2.2` on `main` was later retargeted to `3.2.0a4` before release (see Constraints C-008).
- **Two `charter` packages continue to coexist in the source tree.** `src/charter/` (canonical per issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)) and `src/specify_cli/charter/` (a near-duplicate with 13 of the 16 files) are both present on `main`. Full package deduplication is **explicitly out of scope** for this tranche — see Non-Goals — but any live path still routed through `src/specify_cli/charter/` must be kept correct in lockstep during WP2.3.

The root problem is that the **chokepoint exists but is not enforced** and **reads running inside worktrees silently get no charter**. The bundle layout is best-made **contractual** (a typed manifest) so the chokepoint and migration can consult a single source of truth. Each of these is a separate acceptance gate in [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464). The tranche closes all three together and delivers the migration that seals the upgrade.

This is a broad mechanical edit across readers, the dashboard scanner, the charter module, and the migration infrastructure. The `#393` bulk-edit occurrence-classification pattern already landed for Phase 1 is the required guardrail: every work package in this mission must produce an occurrence artifact, category-aware include/exclude rules, and verification-by-completeness (the "to-change" set is empty on disk at merge), not hand-eyed diff heroics.

---

## Goals

- Define and ship a **contractual unified bundle manifest** under `src/charter/bundle.py` that declares, in typed form, the files `src/charter/sync.py` materializes today (`governance.yaml`, `directives.yaml`, `metadata.yaml`), their tracked-vs-derived classification, and their required `.gitignore` entries. Architecture §6 / issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) is the authority. This is the v1.0.0 manifest; `references.yaml` and `context-state.json` are explicitly out of v1.0.0 scope (separate pipelines — see Non-Goals).
- Promote `ensure_charter_bundle_fresh()` to the **sole chokepoint** for every reader of the three `sync()`-produced derivatives — synthesis, compilation, context building, dashboard exposure, CLI commands, and internal loaders. Verified by code inventory and targeted regression tests that each reader routes through the chokepoint.
- Commit the repo to **canonical-root resolution** semantics: the chokepoint resolves `repo_root` to the git *common* directory (the main checkout), so a reader running inside a worktree transparently reads the main-repo bundle without requiring any materialization inside the worktree. Closes [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339) (stale/missing charter in worktrees).
- Deliver `spec-kitty charter bundle validate [--json]` as a thin CLI surface over the manifest (Q4=B).
- Land migration **`m_3_2_3_unified_bundle.py`** (next free slot) that, on a populated 3.x project, validates the bundle against the manifest, invokes the chokepoint to ensure derivatives are present, and emits a structured JSON report. The migration scope is minimal by design: the real behavior change is at the reader/chokepoint layer.
- Apply the `#393` bulk-edit guardrail at every work package boundary so the cutover is verified by completeness, not by diff review. Preserve the "no fallback, no backwards compatibility" direction.
- Preserve the `#361` dashboard typed contracts (`WPState`, `Lane`) through the WP2.3 scanner/reader rewire so no dashboard regression lands with the chokepoint adoption.

## Non-Goals

- **Not touching `src/specify_cli/core/worktree.py`'s `.kittify/memory/` and `.kittify/AGENTS.md` symlinks.** Those symlinks (lines 478-532) are documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179` — they provide project memory and agent-instructions sharing across worktrees. They are **not** part of the charter bundle and are orthogonal to this mission. Canonical-root resolution solves the worktree-charter-visibility problem without touching this file.
- **Not extending v1.0.0 manifest scope to `references.yaml` or `context-state.json`.** `references.yaml` is produced by `src/charter/compiler.py:169-196` (a separate pipeline invoked by `spec-kitty charter generate`). `context-state.json` is runtime state written lazily by `src/charter/context.py:385-398`. Both have different invariants than the `sync()`-produced files. Broadening manifest scope to cover them requires its own design tranche and a new manifest schema version.
- **Not deduplicating the two `charter` packages.** `src/charter/` remains canonical; `src/specify_cli/charter/` remains present. If a live path still imports from the duplicate, WP2.3 updates it in lockstep for correctness, but full namespace collapse is explicitly a follow-up tranche.
- **Not redesigning the DRG.** Phase 0 is the baseline. Phase 1 excision is the baseline.
- **Not touching the Charter Synthesizer.** That is [Phase 3 / #465](https://github.com/Priivacy-ai/spec-kitty/issues/465).
- **Not redesigning charter authoring UX.** The `spec-kitty charter interview`, `generate`, and `sync` CLI surfaces stay as-is.
- **Not shipping any fallback, dual-read mode, compatibility shim, soft deprecation, or per-worktree materialization fallback.** Per EPIC [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) and the project's standing "no fallback mechanisms" directive, the cutover is hard.
- **Not relocating the bundle outside the working tree.** The bundle stays at `.kittify/charter/`; canonical-root resolution is achieved by resolver logic, not by filesystem relocation.
- **Not redesigning any migration already shipped.** `m_3_2_0_update_planning_templates.py`, `m_3_2_1_strip_selection_config.py`, `m_3_2_3_unified_bundle.py`, and `m_3_1_1_charter_rename.py` are not reopened. The bundle migration is not being renumbered retroactively after the safe command cleanup moved to `3.2.0a4`.
- **Not adding project-local DRG overlays or provenance sidecars** (Phase 3 / Phase 7).
- **Not rewriting the dashboard scanner semantics beyond the minimum needed to route through the chokepoint and keep `#361` typed contracts intact.**
- **Not integrating the new bundle CLI with `spec-kitty doctor`** (Q4=B scope limit; deferred).

---

## User Scenarios & Testing

### Primary Users

The primary "users" of this tranche are **spec-kitty operators and downstream agent integrators** who clone a spec-kitty project, open worktrees during implementation, and rely on charter-derived context in agent prompts. Contributors to `spec-kitty` itself are the secondary audience — they feel the change as an invariant that "every reader of the three `sync()`-produced derivatives routes through `ensure_charter_bundle_fresh()`."

### Scenario 1 — Fresh clone, no manual sync

- **Given** an operator clones a project that uses spec-kitty for governance, with `charter.md` tracked and `.kittify/charter/` derivatives gitignored.
- **When** they run any charter-derivative command without first running `spec-kitty charter sync` (e.g., `spec-kitty charter context --action specify`, `spec-kitty next`, `spec-kitty agent action implement WP01 --agent claude`, or the dashboard scanner loading mission state).
- **Then** the chokepoint auto-materializes the derived bundle on first read, the command succeeds with correct governance context, and the operator is never asked to run `charter sync` manually. (Closes [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451).)

### Scenario 2 — Agent reading charter from inside a worktree

- **Given** planning has finalized tasks and the operator runs `spec-kitty implement WP01` or `spec-kitty next --agent claude`, which creates a worktree via `setup_feature_directory()`.
- **When** an agent running in the worktree invokes any charter-derivative read path (`build_charter_context`, CLI handlers, the prompt builders, etc.) passing `repo_root = worktree_path`.
- **Then** the chokepoint resolves `repo_root` to the **main-checkout** canonical root via `resolve_canonical_repo_root()`, reads and/or refreshes the bundle at the main-checkout `.kittify/charter/` path, and returns a `SyncResult` whose `canonical_root` points at the main checkout. The agent observes the same governance state an agent in the main checkout would observe. No files are written inside the worktree's `.kittify/charter/` tree, and the worktree's `.kittify/memory/` and `.kittify/AGENTS.md` symlinks (which exist for unrelated reasons) are untouched. (Closes [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339) — the original symlink proposal is superseded.)

### Scenario 3 — Stale bundle after the operator edits `charter.md`

- **Given** an operator edits `charter.md` directly (e.g., via IDE) without running `spec-kitty charter sync`.
- **When** the next reader of any `sync()`-produced derivative executes.
- **Then** the chokepoint detects staleness by comparing `charter.md` content hash against `metadata.yaml`, auto-triggers `sync()` at the canonical root, and the reader receives the refreshed bundle. No reader ever observes a stale derivative.

### Scenario 4 — Operator validates the bundle on demand

- **Given** an operator wants to confirm the project's charter bundle is in a known-good state (e.g., before committing `charter.md` changes, or in CI).
- **When** they run `spec-kitty charter bundle validate` (or `--json` for machine-readable output).
- **Then** the command resolves the canonical root, loads `CharterBundleManifest.CANONICAL_MANIFEST`, validates tracked/derived file presence and `.gitignore` required entries against disk, and reports pass/fail without attempting any repair. Out-of-scope files under `.kittify/charter/` (e.g., `references.yaml`, `context-state.json`) are listed as informational warnings rather than failures.

### Scenario 5 — Dashboard scanner reading governance during a live session

- **Given** the dashboard is running (`spec-kitty dashboard`) against a project whose `.kittify/charter/` has been modified since last scan.
- **When** the scanner materializes typed contracts (`WPState`, `Lane` from [#361](https://github.com/Priivacy-ai/spec-kitty/issues/361)) and surfaces charter presence/status to the UI.
- **Then** every charter-derivative read inside the scanner routes through `ensure_charter_bundle_fresh()`, the typed contracts remain byte-identical to their pre-Phase-2 shape on the same fixture, and no dashboard regression test under `tests/test_dashboard/` regresses.

### Scenario 6 — Operator upgrading a populated 3.x project

- **Given** an operator upgrades a spec-kitty project whose charter is at the Phase 1 layout: `.kittify/charter/charter.md` tracked, derived YAMLs present or absent depending on whether `charter sync` has been run recently, potentially with open worktrees.
- **When** the operator runs `spec-kitty upgrade` (which triggers the migration registry).
- **Then** `m_3_2_3_unified_bundle.py` runs idempotently: validates the bundle at the canonical root against `CharterBundleManifest` v1.0.0, invokes the chokepoint to regenerate any missing derivatives, and reports exactly what it observed in a JSON payload matching `contracts/migration-report.schema.json`. The migration does NOT scan or modify worktrees (there are no charter-related symlinks in worktrees to remove), does NOT touch `.kittify/memory/` or `.kittify/AGENTS.md` symlinks, and does NOT reconcile `.gitignore` (v1.0.0 required entries already match current project `.gitignore`). Re-running the migration is a no-op.

### Scenario 7 — Contributor running the test suite

- **Given** a contributor checks out post-Phase-2 `main`.
- **When** they run the full pytest suite.
- **Then** new test classes under `tests/charter/test_bundle_contract.py`, `tests/charter/test_chokepoint_coverage.py`, `tests/init/test_fresh_clone_no_sync.py`, `tests/charter/test_worktree_charter_via_canonical_root.py`, `tests/test_dashboard/test_charter_chokepoint_regression.py`, and `tests/upgrade/test_unified_bundle_migration.py` all pass; existing charter-related tests pass without modification except those rewired by WP2.3; `mypy --strict` remains green.

### Edge Cases

- **Worktree created when the main-checkout bundle is stale.** The chokepoint resolves to the main checkout and refreshes the bundle there; the worktree agent sees the refreshed state.
- **Multiple worktrees reading concurrently.** The chokepoint's sync step must be safe under concurrent invocation; `src/charter/sync.py` already uses `atomic_write` from `kernel.atomic`, and this mission reuses that primitive for any additional writes.
- **Project with no `charter.md` at all.** Chokepoint returns `None` (per current `ensure_charter_bundle_fresh()` contract at `src/charter/sync.py:54`); readers receive an explicit "missing charter" signal and degrade accordingly. This behavior is preserved unchanged. The migration's JSON report sets `charter_present: false` and `applied: false`.
- **Project with `charter.md` but no derivatives and no network access.** The chokepoint generates derivatives from the local charter file without any external fetch; the bundle contract guarantees no reader requires network to hydrate.
- **Project-local `.kittify/charter/` files that are out of v1.0.0 manifest scope** (`references.yaml`, `context-state.json`, `interview/answers.yaml`, `library/*.md`). The bundle contract and the `bundle validate` CLI surface these as informational warnings, not failures. The migration leaves them untouched.
- **Dashboard open while migration runs.** The migration writes via atomic renames; the dashboard scanner's chokepoint invocation re-reads and finds the new state. Typed contracts survive the transition.
- **`resolve_canonical_repo_root()` invoked from inside `.git/`.** Per R-2, the resolver detects this (after resolving `git rev-parse --git-common-dir` stdout) and raises `NotInsideRepositoryError` — loud failure, no fallback.
- **Contributor attempts to reintroduce a direct-read bypass in a future PR.** The AST-walk test under `tests/charter/test_chokepoint_coverage.py` fails and the PR is blocked.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
| --- | --- | --- |
| FR-001 | The codebase must declare a **bundle manifest contract** at `src/charter/bundle.py` that enumerates, in typed Pydantic form, every file path that constitutes the v1.0.0 unified bundle (the files `src/charter/sync.py :: sync()` materializes), whether each is tracked or derived, and which source file each derived file is derived from. The manifest is the single source of truth consumed by the chokepoint, the migration, and the bundle contract tests. | Draft |
| FR-002 | The unified bundle layout and canonical-root contract must be documented in `architecture/2.x/` (new file or update to §6 section) with the v1.0.0 filename set, tracked-vs-derived classification, gitignore expectations, and the canonical-root resolution contract. The documentation file is the authoritative narrative cited by FR-001. | Draft |
| FR-003 | `ensure_charter_bundle_fresh()` must resolve `repo_root` to the **git common directory** (the main checkout) when invoked from inside a worktree, and must return a `SyncResult` whose file paths reference only the main-checkout bundle. A helper `resolve_canonical_repo_root(path: Path) -> Path` must be introduced at `src/charter/resolution.py` and must use `git rev-parse --git-common-dir` semantics per the algorithm in [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md): normalize file inputs to parent dirs; resolve stdout relative to cwd when non-absolute; detect invocation from inside `.git/` and raise `NotInsideRepositoryError`. | Draft |
| FR-004 | Every reader in `src/` of any file in `CharterBundleManifest.CANONICAL_MANIFEST.derived_files` (v1.0.0: `governance.yaml`, `directives.yaml`, `metadata.yaml`) must route through `ensure_charter_bundle_fresh()` before reading. The exhaustive list (refined during WP2.3 occurrence classification) includes at minimum: `build_charter_context()` at `src/charter/context.py`, `load_governance_config()` at `src/charter/sync.py:187` (already routed), `load_directives_config()` at `src/charter/sync.py:229` (already routed), `resolve_governance()` at `src/charter/resolver.py:43` (already routed indirectly), `resolve_project_charter_path()` at `src/specify_cli/dashboard/charter_path.py:8`, the dashboard scanner's charter-presence probes in `src/specify_cli/dashboard/scanner.py` and `server.py`, the `spec-kitty charter context` CLI handler at `src/specify_cli/cli/commands/charter.py`, the next-prompt builder at `src/specify_cli/next/prompt_builder.py`, and the workflow prompt builder at `src/specify_cli/cli/commands/agent/workflow.py`. The `src/specify_cli/charter/` duplicate package's equivalents are updated in lockstep where they remain live per C-003. Readers of out-of-v1.0.0-scope files (`references.yaml` via the compiler pipeline, `context-state.json` via the context builder's own writes) are **not** required by this FR. | Draft |
| FR-005 | A Pydantic model `CharterBundleManifest` (in `src/charter/bundle.py`) must declare, minimally: `schema_version: str`, `tracked_files: list[Path]`, `derived_files: list[Path]`, `derivation_sources: dict[Path, Path]` (derived → source), `gitignore_required_entries: list[str]`. The v1.0.0 `CANONICAL_MANIFEST` instance must set `schema_version = "1.0.0"`, `derived_files` = `[governance.yaml, directives.yaml, metadata.yaml]`, and `gitignore_required_entries` = the three matching strings. `references.yaml` and `context-state.json` are explicitly NOT in v1.0.0 scope. | Draft |
| FR-006 | `SyncResult` at `src/charter/sync.py` must be extended with a new field `canonical_root: Path` (absolute). `files_written` continues to be a list of paths relative to `canonical_root` (not changed in meaning, but now explicitly anchored). No existing field is renamed or retyped. Every existing reader of `SyncResult` is updated in the same WP (WP2.2) to use `canonical_root` when reconstructing absolute paths — no compat shim per C-001. | Draft |
| FR-007 | Migration `m_3_2_3_unified_bundle.py` under `src/specify_cli/upgrade/migrations/` must, when applied to a populated 3.x project: (a) detect whether `charter.md` exists at the canonical root; (b) if yes, validate the bundle against `CharterBundleManifest` v1.0.0; (c) invoke the chokepoint to regenerate any missing derivatives; (d) produce a structured JSON report matching [`contracts/migration-report.schema.json`](contracts/migration-report.schema.json). The migration must be idempotent: a second apply must be a no-op. It must NOT scan or modify worktrees, NOT remove any symlinks (including `.kittify/memory/` and `.kittify/AGENTS.md` which are not charter bundle files), and NOT reconcile `.gitignore` (v1.0.0 required entries match current project `.gitignore`). | Draft |
| FR-008 | The migration must register with `target_version = "3.2.3"` in the `MigrationRegistry` (pattern matches `m_3_2_0_update_planning_templates.py:50-60`) and must be discoverable via the registry's auto-discovery in `src/specify_cli/upgrade/migrations/__init__.py`. The filename on disk must be `m_3_2_3_unified_bundle.py`. Issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) is updated in the tracking commentary to reflect the corrected filename. | Draft |
| FR-009 | A new test module `tests/init/test_fresh_clone_no_sync.py` must exercise the following flow end-to-end in a temporary cloned-style fixture (populated `charter.md`, no derivatives on disk, no prior `sync` invocation): each reader site in FR-004's minimum list is invoked once; each invocation succeeds; after the first invocation the three v1.0.0 derivatives exist on disk at the canonical root; `spec-kitty charter sync` is **never** called explicitly by the test. | Draft |
| FR-010 | A new test module `tests/charter/test_worktree_charter_via_canonical_root.py` must create a worktree (via `setup_feature_directory()` or an equivalent fixture), invoke a reader site from FR-004 passing `repo_root = worktree_path`, and assert that: (a) the returned `SyncResult.canonical_root` points at the **main checkout**, not the worktree; (b) `files_written` entries resolve to paths under the main checkout; (c) no files have been written inside `<worktree_path>/.kittify/charter/`; (d) the worktree's existing `.kittify/memory/` and `.kittify/AGENTS.md` symlinks (if present via `setup_feature_directory()`) are untouched. This test replaces the previously-planned "no charter symlink in worktree" assertion because no such symlink exists on `main` today. | Draft |
| FR-011 | A new test module `tests/charter/test_chokepoint_coverage.py` must, using a module-level registry of all reader call sites of the v1.0.0 manifest's `derived_files`, assert via Python AST walk of `src/` that every such site either calls `ensure_charter_bundle_fresh()` directly or reaches it through a helper whose implementation routes through the chokepoint. The registry is seeded from the WP2.3 occurrence classification artifact and is the test's source of truth. | Draft |
| FR-012 | A new test module `tests/charter/test_bundle_contract.py` must load `CharterBundleManifest`, instantiate an in-tmpdir charter bundle via the chokepoint, and assert that every file listed as `tracked` exists and is not gitignored, every file listed as `derived` is gitignored, every derived file has a corresponding `derivation_sources` entry, and no **v1.0.0 manifest file** is missing from `.kittify/charter/` after the chokepoint runs. Files present under `.kittify/charter/` but not in the v1.0.0 manifest (e.g., `references.yaml`, `context-state.json`) are surfaced as informational, not failures. | Draft |
| FR-013 | A new test module `tests/upgrade/test_unified_bundle_migration.py` must drive `m_3_2_3_unified_bundle.py` against at least the following fixture matrix: (a) a pre-Phase-2 project with `charter.md` tracked and full derivatives present; (b) a pre-Phase-2 project with `charter.md` tracked but no derivatives (first-run state); (c) a Phase-2-shaped project where the migration has already run (must be a no-op with `applied: false`); (d) a project with stale `metadata.yaml` hash against `charter.md` (chokepoint must refresh during migration); (e) a project where `charter.md` is absent (migration reports `charter_present: false, applied: false` and does not error). Each fixture asserts the full structured JSON report shape. | Draft |
| FR-014 | The dashboard scanner rewire in WP2.3 must preserve the `#361` typed contracts (`WPState`, `Lane`). A regression test under `tests/test_dashboard/test_charter_chokepoint_regression.py` must load a fixture that exercises the dashboard's charter-presence and charter-read paths, assert that each path invokes the chokepoint at least once, and assert that the typed contract outputs are byte-identical (after timestamp/ULID redactions per R-4) to a golden baseline captured pre-WP2.3 on `main` and committed under `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json`. | Draft |
| FR-015 | Each work package must produce an **occurrence classification artifact** at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml` following the `#393` pattern (category-aware include/exclude, explicit per-category rationale, mission-level aggregate index). Completion of the WP is verified by proving the artifact's "to-change" set is empty on disk (verification-by-completeness), not by hand-reviewing semantic diffs. | Draft |
| FR-016 | Post-merge, the following grep invariants must hold on `src/` and `tests/` (permitted exceptions listed in the mission-level occurrence map): zero direct reads of `.kittify/charter/governance.yaml`, `.kittify/charter/directives.yaml`, or `.kittify/charter/metadata.yaml` that do not flow through `ensure_charter_bundle_fresh()`; the string `ensure_charter_bundle_fresh` appears at every reader site enumerated in FR-004; the string `resolve_canonical_repo_root` appears inside `ensure_charter_bundle_fresh()`'s implementation. This FR does NOT sweep for `shutil.copytree` / `os.symlink` patterns inside `src/specify_cli/core/worktree.py` — those are present for the memory/AGENTS sharing mechanism (documented-intentional) and must remain untouched. | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable Threshold | Status |
| --- | --- | --- | --- |
| NFR-001 | Total pytest runtime on CI must not regress by more than 5% compared to the last green run on pre-Phase-2 `main`, measured as p50 over three consecutive CI runs on each of the pre-Phase-2 and post-Phase-2 commits. | ≤5% regression | Draft |
| NFR-002 | The chokepoint's freshness check (existence, hash comparison) must add less than 10 ms to any reader invocation on a warm bundle (all v1.0.0 derivatives present, hash-matched), measured on the dashboard scanner's per-frame charter-read path as the hot loop. Cold regeneration cost is governed by the existing `sync()` path and is explicitly not bounded by this requirement. | <10 ms warm overhead (p95 over 100 invocations on the dashboard fixture) | Draft |
| NFR-003 | Canonical-root resolution (`resolve_canonical_repo_root`) must add less than 5 ms per call on a repo with a worktree-attached working tree, measured as p95 over 100 invocations, and must not shell out to `git` more than once per invocation (subsequent calls use a cached result keyed by working directory). | <5 ms p95 per call; ≤1 git invocation per call | Draft |
| NFR-004 | `mypy --strict` must pass on every new and modified module, and line coverage on new or rewritten code (FR-001 bundle module, FR-003 resolver, FR-007 migration, and every new test module) must be at or above 90%. | 0 mypy errors; ≥90% line coverage on changed files | Draft |
| NFR-005 | Post-merge, the mission-level occurrence map's "must be zero" set must be empty when the scripted completeness check runs in CI. The set includes: direct reads of any v1.0.0 manifest derived file that bypass the chokepoint; reader sites in FR-004 that do not import or call `ensure_charter_bundle_fresh`; any carve-out not explicitly listed in the mission-level occurrence map at merge. | 0 stray occurrences outside the permitted-exceptions list | Draft |
| NFR-006 | `spec-kitty upgrade` on a representative 3.x fixture project (with populated charter bundle) must complete the `m_3_2_3_unified_bundle.py` step in under 2 seconds on a developer laptop baseline (MacBook Pro M-series, SSD, no network IO). | ≤2 s wall time on the FR-013 reference fixture | Draft |

### Constraints

| ID | Constraint | Status |
| --- | --- | --- |
| C-001 | No fallback, no backwards-compatibility shim, no dual-read mode, no soft deprecation — per [EPIC #461 §10](https://github.com/Priivacy-ai/spec-kitty/issues/461) and the project's standing "no fallback mechanisms" directive. | Active |
| C-002 | The `#393` bulk-edit guardrail (explicit occurrence classification, category-aware include/exclude, mission-level occurrence map, verification-by-completeness) is mandatory for every WP in this tranche. | Active |
| C-003 | `src/charter/` is canonical; `src/specify_cli/charter/` is not deduplicated in this tranche. Any reader still routed through the duplicate is updated in lockstep during WP2.3 for correctness. Full namespace collapse is a follow-up tranche. | Active |
| C-004 | GitHub issues [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461), [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464), [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451), [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339), [#361](https://github.com/Priivacy-ai/spec-kitty/issues/361), [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478), [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480), [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481), [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479) are authoritative. Local planning documents under `spec-kitty-planning/` are reference only. | Active |
| C-005 | Phase 0 (DRG schema, `graph.yaml`, merged-graph validator, `build_context_v2()` semantics promoted to `build_charter_context`) and Phase 1 excision are baselines and may not be reopened. | Active |
| C-006 | Only SOURCE templates under `src/specify_cli/missions/*/command-templates/` and `src/specify_cli/skills/` may be edited for any template-touching work. Agent copy directories (`.claude/`, `.amazonq/`, `.augment/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/prompts/`, `.kilocode/`, `.opencode/`, `.qwen/`, `.roo/`, `.windsurf/`, `.kiro/`) are generated copies and must not be hand-edited in this mission. | Active |
| C-007 | Work packages must land in strict dependency order: WP2.1 → WP2.2 → WP2.3 → WP2.4. Each WP is merged behind its own PR, preflight-verified, and validated end-to-end before the next begins. | Active |
| C-008 | The literal filename `m_3_2_0_unified_bundle.py` from issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) is unavailable, and the implemented filename on `main` is `m_3_2_3_unified_bundle.py`. That migration is not being renumbered retroactively after the safe command cleanup moved from `3.2.2` to `3.2.0a4` before release. | Active |
| C-009 | Canonical-root resolution must use git-native semantics (`git rev-parse --git-common-dir`) rather than filesystem-path heuristics, and must correctly interpret the command's stdout (which is relative to `cwd` unless absolute — see [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md) for the full algorithm including file-input normalization and `.git/`-interior detection). | Active |
| C-010 | `#361` dashboard typed contracts (`WPState`, `Lane`) are the regression safety net for the WP2.3 scanner rewire. Any change that modifies typed-contract outputs requires a companion regression entry against the FR-014 baseline. | Active |
| C-011 | `src/specify_cli/core/worktree.py:478-532` — the `.kittify/memory/` and `.kittify/AGENTS.md` symlink/copy block — is documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179` and is **out of scope** for this mission. It must not be edited. The canonical-root resolver supersedes the original #339 proposal to mirror this pattern for `.kittify/charter/`. | Active |
| C-012 | `CharterBundleManifest` v1.0.0 scope is limited to the three files `src/charter/sync.py :: sync()` materializes (`governance.yaml`, `directives.yaml`, `metadata.yaml`). `references.yaml` (compiler pipeline) and `context-state.json` (runtime state) are explicitly out of v1.0.0 scope and not covered by the chokepoint's completeness contract or by the `bundle validate` CLI. Expanding scope requires a new manifest schema version. | Active |

---

## Success Criteria

The Phase 2 tranche is complete when **all** of the following hold on post-merge `main`:

1. A populated 3.x project cloned fresh (with `charter.md` tracked, no derivatives on disk) executes every FR-004 reader path without the operator invoking `spec-kitty charter sync`. The chokepoint auto-materializes derivatives on first read. (Gate 1 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464); closes [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451).)
2. A reader executing inside a worktree receives a `SyncResult` whose `canonical_root` points at the main checkout and whose `files_written` entries resolve to paths under the main checkout. No files are written inside the worktree's `.kittify/charter/` tree. The worktree's pre-existing `.kittify/memory/` and `.kittify/AGENTS.md` symlinks are untouched. (Gate 2 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464); closes [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339).)
3. `tests/charter/test_chokepoint_coverage.py` passes, asserting by AST walk that every reader call site in FR-004 routes through `ensure_charter_bundle_fresh()`. The test's registry of reader sites matches the WP2.3 occurrence artifact verbatim. (Gate 3 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464).)
4. `m_3_2_3_unified_bundle.py` is present under `src/specify_cli/upgrade/migrations/`, registered in the registry, and passes `tests/upgrade/test_unified_bundle_migration.py` on every fixture in the FR-013 matrix. (Gate 4 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464).)
5. `CharterBundleManifest` exists as a typed Pydantic model at `src/charter/bundle.py`, schema version `"1.0.0"`, documenting the three `sync()`-produced derivatives, and is the authority consumed by FR-001, FR-005, FR-007, FR-012.
6. The documentation file under `architecture/2.x/` describing the unified bundle contract is committed and cited from the manifest module docstring.
7. `grep -R "\.kittify/charter/governance\.yaml\|\.kittify/charter/directives\.yaml\|\.kittify/charter/metadata\.yaml" src/` shows every direct path reference either flows through `ensure_charter_bundle_fresh()` (verified by AST test) or is in an explicitly carved-out location (manifest module, migration module, bundle documentation).
8. `grep -n "\.kittify/memory\|\.kittify/AGENTS\.md" src/specify_cli/core/worktree.py` shows lines 478-532 unchanged from pre-Phase-2 `main` (C-011 carve-out verification).
9. Each of WP2.1 / WP2.2 / WP2.3 / WP2.4 has a committed occurrence-classification artifact at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml` and the "to-change" set in each is empty at merge.
10. The pre-WP2.3 dashboard typed-contracts golden baseline is committed at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` and `tests/test_dashboard/test_charter_chokepoint_regression.py` reproduces it byte-identically (after documented redactions) against post-WP2.3 code.
11. The changelog entry for the release that ships this tranche documents: the unified bundle manifest (v1.0.0) and its location; the canonical-root-resolution behavior for worktree readers; the `m_3_2_3_unified_bundle.py` upgrade path; the absence of any compatibility shim; explicit note that `.kittify/memory/` and `.kittify/AGENTS.md` symlinks are unchanged.
12. `mypy --strict` passes and line coverage on new/changed code meets NFR-004.

---

## Key Entities

- **Unified bundle (v1.0.0)** — the set of files `src/charter/sync.py :: sync()` materializes: `governance.yaml`, `directives.yaml`, `metadata.yaml` (plus the tracked source `charter.md`). Declared by `CharterBundleManifest` v1.0.0; does NOT include `references.yaml` (compiler pipeline) or `context-state.json` (runtime state).
- **Canonical repo root** — the main checkout's working directory, equal to the parent of `git rev-parse --git-common-dir`'s resolved output. Used by the chokepoint so a reader running inside a worktree transparently reads the main-checkout bundle.
- **Chokepoint** — `ensure_charter_bundle_fresh()` at `src/charter/sync.py:50-90`. After Phase 2 it is the sole entry path for every reader of the three v1.0.0 manifest derivatives. It resolves to the canonical root, checks completeness and staleness, triggers `sync()` if needed, and returns a `SyncResult | None`.
- **`CharterBundleManifest`** — the typed Pydantic model at `src/charter/bundle.py` that declares the v1.0.0 bundle files, classification, derivation sources, and gitignore required entries.
- **Occurrence classification artifact** — a work-package-scoped YAML at `kitty-specs/<mission_slug>/occurrences/WP2.<n>.yaml` enumerating every string and path occurrence touched by the WP. Mandated by `#393` guardrail.
- **Mission-level occurrence map** — the aggregated index at `kitty-specs/<mission_slug>/occurrences/index.yaml` that lists every permitted-exception path, every category exclusion rationale, and every category whose post-merge occurrence count must be zero. Merge review gate.
- **Dashboard typed contract** — `WPState`, `Lane`, and the surrounding dashboard-scanner response shapes defined in `#361`. Regression safety net for WP2.3.
- **Documented-intentional worktree memory sharing** — `.kittify/memory/` and `.kittify/AGENTS.md` symlinks created by `src/specify_cli/core/worktree.py:478-532` and documented in `src/specify_cli/templates/AGENTS.md:168-179`. NOT part of the charter bundle; NOT touched by this mission (C-011).

---

## Implementation Plan (Work Package Shape)

This section is recommended shape for `/spec-kitty.plan` and `/spec-kitty.tasks`; it is **not** a pre-committed WP layout. It is derived from issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)'s four acceptance gates, the design-review corrections of 2026-04-14, and the code audit captured in the Problem Statement.

### WP2.1 — Unified bundle manifest + architecture doc + bundle CLI

**Tracking issue**: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478)

Deliverables:

- `CharterBundleManifest` Pydantic model at `src/charter/bundle.py`, per FR-005 and v1.0.0 scope (three `sync()` derivatives).
- Architecture documentation file under `architecture/2.x/` describing the unified bundle contract.
- `spec-kitty charter bundle validate [--json]` Typer subcommand under `src/specify_cli/cli/commands/charter.py` per [`contracts/bundle-validate-cli.contract.md`](contracts/bundle-validate-cli.contract.md).
- Unit tests for the manifest model.
- Integration test for the `bundle validate` CLI against a live fixture.
- `occurrences/WP2.1.yaml` enumerating every path literal touched.

No reader or resolver code changes in this WP. Pure additive.

### WP2.2 — Chokepoint finalization (canonical-root resolution, one staleness check)

**Tracking issue**: [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480)

Depends on WP2.1 (the manifest is the authority the chokepoint consults).

Deliverables:

- `resolve_canonical_repo_root(path: Path) -> Path` helper at `src/charter/resolution.py`, implemented via `git rev-parse --git-common-dir` per [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md). Cached per working directory.
- `ensure_charter_bundle_fresh()` refactored to call `resolve_canonical_repo_root()` first and to consult `CharterBundleManifest.CANONICAL_MANIFEST` for completeness.
- `SyncResult` extended with `canonical_root: Path`; every existing caller rewired.
- Unit tests covering the R-2 behavioral matrix.
- Micro-benchmarks for NFR-002, NFR-003.
- `occurrences/WP2.2.yaml`.

No reader cutover in this WP.

### WP2.3 — Reader cutover (every FR-004 reader routes through the chokepoint) + dashboard regression proof

**Tracking issue**: [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481)

Depends on WP2.2 (canonical-root resolution is a prerequisite for worktree-based readers to pass without materialization) and WP2.1 (the manifest informs the AST-walk test registry).

Deliverables:

- **Step 1 (baseline capture, MUST happen before any reader rewire)**: capture pre-WP2.3 dashboard typed-contract JSON at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` via a committed capture script.
- Every reader site in FR-004 is updated to call `ensure_charter_bundle_fresh()` before reading any v1.0.0 manifest derivative. In particular: `build_charter_context()` (bypass at `src/charter/context.py:406-661`), `resolve_project_charter_path()` at `src/specify_cli/dashboard/charter_path.py:8-17`, dashboard scanner + server charter-presence paths, charter CLI handlers, next and workflow prompt builders.
- `src/specify_cli/charter/` duplicate package equivalents updated in lockstep where any remain live per C-003. Pure re-exports untouched.
- New test modules per FR-009, FR-010, FR-011, FR-014.
- `occurrences/WP2.3.yaml` covering import-path, symbol-name, filesystem-path-literal, CLI-command-name, docstring/comment, YAML-key, skill/template-reference, test-identifier categories. Includes explicit `leave` entries for lines 478-532 of `src/specify_cli/core/worktree.py` (C-011 carve-out) and for `src/charter/compiler.py:169-196` and `src/charter/context.py:385-398` (C-012 out-of-scope carve-out).

`#361` typed contracts must be preserved per C-010.

### WP2.4 — Migration `m_3_2_3_unified_bundle.py`

**Tracking issue**: [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479)

Depends on WP2.3 (reader behavior must be in place before the migration's chokepoint-invocation step is meaningful).

Deliverables:

- `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` implementing FR-007 per the migration class pattern visible in `m_3_2_0_update_planning_templates.py:50-60`. Target version `"3.2.3"`. Emits JSON report per [`contracts/migration-report.schema.json`](contracts/migration-report.schema.json).
- `tests/upgrade/test_unified_bundle_migration.py` exercising the FR-013 fixture matrix.
- Issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) body updated in a tracking comment to reflect the `m_3_2_3_unified_bundle.py` filename per C-008 and to reflect the design-review scope corrections (no worktree scanning, v1.0.0 manifest narrowing, corrected resolver algorithm).
- `occurrences/WP2.4.yaml`.

### Sequencing note

WP2.1 → WP2.2 → WP2.3 → WP2.4 is **strict sequential**. Rationale unchanged from the original spec plan; additionally, WP2.3's baseline capture in Step 1 must execute before reader rewires co-mingle with baseline recording.

Parallelization is rejected. The `#393` guardrail depends on clean occurrence artifacts per WP.

---

## Validation & Test Strategy

### Verification-by-completeness (per #393)

Every WP produces an occurrence-classification artifact at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml`. The mission-level aggregate at `.../occurrences/index.yaml` declares the final "must be zero" set (per NFR-005):

```
# Patterns that must not appear on live paths outside carve-outs:
direct_read_of_governance_yaml_bypassing_chokepoint
direct_read_of_directives_yaml_bypassing_chokepoint
direct_read_of_metadata_yaml_bypassing_chokepoint
fr004_reader_missing_ensure_charter_bundle_fresh_call
chokepoint_not_calling_resolve_canonical_repo_root
```

Permitted carve-outs (listed explicitly in the index):

- `src/charter/sync.py` — the chokepoint itself performs the authoritative read.
- `src/charter/bundle.py` — the manifest module declares paths for documentation.
- `src/charter/resolution.py` — the resolver shells out via `subprocess`.
- `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` — the migration performs bundle validation.
- `src/specify_cli/core/worktree.py:478-532` — C-011 out-of-scope (memory/AGENTS sharing).
- `src/charter/compiler.py:169-196` — C-012 out-of-v1.0.0-scope (compiler pipeline).
- `src/charter/context.py:385-398` — C-012 out-of-v1.0.0-scope (runtime state).
- `tests/**` fixture builders and negative-case assertions.
- `architecture/2.x/` documentation references.

### Automated test coverage

1. **Fresh-clone smoke test** (FR-009) — `tests/init/test_fresh_clone_no_sync.py`.
2. **Worktree canonical-root test** (FR-010) — `tests/charter/test_worktree_charter_via_canonical_root.py`.
3. **Chokepoint coverage test** (FR-011) — `tests/charter/test_chokepoint_coverage.py`.
4. **Bundle contract test** (FR-012) — `tests/charter/test_bundle_contract.py`.
5. **Migration matrix** (FR-013) — `tests/upgrade/test_unified_bundle_migration.py`.
6. **Dashboard typed-contract regression** (FR-014) — `tests/test_dashboard/test_charter_chokepoint_regression.py`.
7. **Coverage / type check** — `pytest --cov` enforces NFR-004; `mypy --strict` must pass on every WP PR.
8. **Runtime / warm-overhead benchmarks** — NFR-002 and NFR-003 via micro-benchmarks in `tests/charter/test_chokepoint_overhead.py` and `tests/charter/test_resolution_overhead.py`.

### Manual validation (spot checks)

- On a fresh checkout of the post-Phase-2 commit, clone a populated 3.x project fixture, run `spec-kitty charter context --action specify --json` without any prior `sync`, and confirm the derivatives exist afterward and the JSON is correct.
- Run `spec-kitty next --agent claude` on a feature with tasks finalized; inspect the resulting worktree with `ls -la .worktrees/<slug>-<mid8>-lane-a/.kittify/` and confirm the existing `.kittify/memory/` and `.kittify/AGENTS.md` symlinks are unchanged and no `.kittify/charter/` subtree was created inside the worktree.
- Run `spec-kitty charter bundle validate` on the repo itself; expect exit 0 with warnings listing `references.yaml` and `context-state.json` as out of v1.0.0 scope.
- Run `spec-kitty upgrade` on a representative pre-Phase-2 project; inspect the migration's JSON report; re-run upgrade and confirm the second invocation is a no-op (`applied: false`).

### CI integration

- The mission-level occurrence map check runs as a non-skippable job in each WP PR and in the final merge PR.
- `tests/charter/test_chokepoint_coverage.py` and `tests/charter/test_bundle_contract.py` run in the default pytest job.
- NFR-001 (runtime regression budget) is measured by comparing `pytest --durations=0` summaries from pre- and post-Phase-2 CI runs.
- NFR-002 and NFR-003 micro-benchmarks run in a dedicated perf job whose threshold failures block merge.

---

## Assumptions

- The audit finding that only two internal loaders currently route through `ensure_charter_bundle_fresh()` is exhaustive for the `src/charter/` canonical package as of current `main`. WP2.3 occurrence classification re-verifies by full-repo grep and AST walk.
- `git rev-parse --git-common-dir` is available and behaves per the R-2 behavior matrix on every platform the project supports (macOS, Linux, Windows WSL). The algorithm in `contracts/canonical-root-resolver.contract.md` correctly handles both relative and absolute stdout, file inputs, and `.git/`-interior invocation.
- `src/specify_cli/charter/` contains mostly inert duplicates or wrappers around `src/charter/`. If any file still performs a direct charter read on a live code path, WP2.3 updates it in lockstep.
- The `#361` dashboard typed contracts are stable on current `main`; the FR-014 golden baseline is a point-in-time capture against that stability with documented redactions per R-4.
- `m_3_1_1_charter_rename.py` (Phase 1) correctly normalized all legacy charter layouts.
- `.gitignore` entries for `.kittify/charter/` derivatives on current `main` already cover the v1.0.0 manifest's `gitignore_required_entries` verbatim (and additionally cover `context-state.json` and `references.yaml` which are out of v1.0.0 scope but remain correctly ignored). The migration performs no `.gitignore` reconciliation.
- `kernel.atomic.atomic_write` is safe under concurrent invocation across processes.
- `src/specify_cli/core/worktree.py:478-532` is the only place in the codebase that materializes `.kittify/memory/` and `.kittify/AGENTS.md` into worktrees, and it does NOT materialize `.kittify/charter/` (a prerequisite for the canonical-root-resolution reframe to be correct).
- Downstream tools that embed spec-kitty as a library read charter state through the chokepoint (via `build_charter_context()` or the public `spec-kitty charter context` CLI).
- The `#393` occurrence-classification scripted check from Phase 1 is reusable for Phase 2.

---

## Out of Scope (Deferred to Phase 3+)

- **Charter Synthesizer pipeline and FR1 implementation** ([Phase 3 / #465](https://github.com/Priivacy-ai/spec-kitty/issues/465)).
- **Profile-as-entry-point CLI and host-LLM advise/execute** ([Phase 4 / #466](https://github.com/Priivacy-ai/spec-kitty/issues/466)).
- **Glossary-as-DRG + chokepoint + dashboard tile** ([Phase 5 / #467](https://github.com/Priivacy-ai/spec-kitty/issues/467)).
- **Mission rewrite and retrospective contract** ([Phase 6 / #468](https://github.com/Priivacy-ai/spec-kitty/issues/468)).
- **Schema versioning and provenance hardening** ([Phase 7 / #469](https://github.com/Priivacy-ai/spec-kitty/issues/469)).
- Full deduplication of `src/charter/` vs. `src/specify_cli/charter/` (C-003).
- Expanding the bundle manifest to cover `references.yaml` (compiler pipeline) and `context-state.json` (runtime state) — requires its own design tranche and a new manifest schema version (C-012).
- Editing `.kittify/memory/` / `.kittify/AGENTS.md` sharing behavior in worktrees (C-011 — documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179`).
- Relocating the bundle out of the working tree.
- Adding project-local DRG overlay support beyond what Phase 0 already ships.
- Any change to the `#361` dashboard typed contract shape (only preserved, not evolved).
- `spec-kitty doctor` integration of the bundle CLI (Q4=B scope limit).

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| A reader site is missed by the WP2.3 occurrence classification and continues to perform a direct charter read, silently bypassing the chokepoint. | Medium | High (freshness-safety regression) | FR-011 AST-walk test is the completeness proof; the test's registry is the WP2.3 occurrence artifact. A missed site fails the test. |
| `git rev-parse --git-common-dir` returns unexpected stdout on a supported platform (e.g., Windows WSL with cross-drive paths). | Low | High (reader reads empty bundle) | WP2.2 unit tests include the R-2 fixture matrix. The resolver's explicit algorithm handles both relative-to-cwd and absolute stdout; `.git/`-interior detection is explicit. Any platform inconsistency is surfaced as a loud failure via `GitCommonDirUnavailableError`, not a silent misroute. |
| A reader on `src/specify_cli/charter/` twin remains live and missed by WP2.3 | Medium | Medium (silent bypass) | AST-walk test (FR-011) walks the full `src/` tree. Occurrence classification lists both packages separately. |
| The migration fails idempotency because a second invocation re-encounters a project in a mid-migration state | Low | Medium (confusing upgrade UX) | FR-013 fixture matrix exercises double-apply. The migration is stateless and re-entrant. |
| The dashboard typed-contract baseline captures noise (timestamps, ordering) that makes byte-identical comparison flaky | Medium | Low-Medium (flaky regression test) | R-4 defines redactions; the capture script is committed alongside the baseline and is reproducible. |
| The chokepoint warm-overhead requirement (NFR-002, <10 ms) is breached | Low | Low-Medium (dashboard lag) | WP2.2 caches the charter.md mtime and short-circuits the hash read when mtime is unchanged. |
| A PR lands out of order (e.g., WP2.4 before WP2.3), leaving the migration calling a chokepoint that has not yet been wired through every reader | Low | Medium (broken `main`) | C-007 enforces strict sequencing; orchestrator runs WPs in dependency order. |
| A developer edits `src/specify_cli/core/worktree.py:478-532` during this mission's work, breaking memory/AGENTS sharing | Medium | High (documented behavior regression) | C-011 pins this block as out of scope. WP2.3 occurrence artifact explicitly lists the lines as `leave`. Success Criterion 8 verifies the lines are unchanged at merge via a grep check. |
| The new bundle manifest disagrees with the existing `.gitignore` on some entry | Low | Low | D-12 pins v1.0.0 to the current `.gitignore` state; the migration performs no reconciliation. Disagreement would be caught by `tests/charter/test_bundle_contract.py`. |
| `resolve_canonical_repo_root()` invoked from outside a git repo in a test fixture | Medium | Low (test-only error) | The resolver raises `NotInsideRepositoryError`; callers distinguish this from operational failure. Test fixtures always operate inside a fixture repo. |

---

## Likely File Clusters

For plan-phase sizing. Paths are relative to repo root.

**Bundle manifest (WP2.1)**
- `src/charter/bundle.py` (new — `CharterBundleManifest` Pydantic model, `CANONICAL_MANIFEST`, `SCHEMA_VERSION = "1.0.0"`)
- `src/charter/__init__.py` (add re-export)
- `src/specify_cli/cli/commands/charter.py` (add `bundle validate` subcommand)
- `architecture/2.x/<new-file>.md` (new — unified bundle contract doc)
- `tests/charter/test_bundle_manifest_model.py` (new — manifest unit tests)
- `tests/charter/` (new — `bundle validate` CLI integration test)

**Chokepoint + canonical-root resolver (WP2.2)**
- `src/charter/sync.py` (modify — `ensure_charter_bundle_fresh()` + `SyncResult.canonical_root`)
- `src/charter/resolution.py` (new — `resolve_canonical_repo_root()` + exception types)
- `tests/charter/test_canonical_root_resolution.py` (new)
- `tests/charter/test_chokepoint_overhead.py` (new — NFR-002 micro-benchmarks)
- `tests/charter/test_resolution_overhead.py` (new — NFR-003 micro-benchmarks)

**Reader cutover (WP2.3)**
- `src/charter/context.py` (modify — `build_charter_context()` routes through chokepoint)
- `src/specify_cli/dashboard/charter_path.py` (modify)
- `src/specify_cli/dashboard/scanner.py` (modify — charter-presence paths)
- `src/specify_cli/dashboard/server.py` (modify — charter endpoints)
- `src/specify_cli/cli/commands/charter.py` (modify — handlers)
- `src/specify_cli/next/prompt_builder.py` (modify — charter injection)
- `src/specify_cli/cli/commands/agent/workflow.py` (modify — workflow charter injection)
- `src/specify_cli/charter/*.py` (modify in lockstep per C-003 if live readers remain)
- `tests/init/test_fresh_clone_no_sync.py` (new)
- `tests/charter/test_worktree_charter_via_canonical_root.py` (new)
- `tests/charter/test_chokepoint_coverage.py` (new — AST walk)
- `tests/charter/test_bundle_contract.py` (new)
- `tests/test_dashboard/test_charter_chokepoint_regression.py` (new)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` (new — golden capture)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py` (new — capture script)

**Explicitly NOT in WP2.3 scope (C-011 / C-012)**
- `src/specify_cli/core/worktree.py` — left unchanged
- `src/charter/compiler.py` — left unchanged (compiler pipeline owns references.yaml)
- `src/charter/context.py:385-398` — `context-state.json` write path left unchanged (runtime-state concern)

**Migration (WP2.4)**
- `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` (new)
- `src/specify_cli/upgrade/migrations/__init__.py` (modify if explicit registration is required)
- `tests/upgrade/test_unified_bundle_migration.py` (new — FR-013 fixture matrix)
- `tests/upgrade/fixtures/unified_bundle/` (new fixture tree for pre-Phase-2 projects)

**Occurrence artifacts (every WP)**
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.1.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.2.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.3.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.4.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml`

**Changelog**
- `CHANGELOG.md` (modify — entry per Success Criterion 11)
