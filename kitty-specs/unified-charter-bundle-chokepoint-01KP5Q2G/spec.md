# Feature Specification: Unified Charter Bundle and Read Chokepoint

**Mission ID**: `01KP5Q2G4Z39ZVRX2FY3NWXZQW` (`mid8`: `01KP5Q2G`)
**Mission Slug**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Mission Type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-04-14
**Parent EPIC**: [Priivacy-ai/spec-kitty#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) — Charter as Synthesis & Doctrine Reference Graph
**Tracking issue**: [Priivacy-ai/spec-kitty#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) — [Phase 2] Unified emergent bundle layout + read chokepoint
**Architecture reference**: §6 (unified emergent bundle), §11 Phase 2
**Related WP issues**: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478) (WP2.1), [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480) (WP2.2), [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481) (WP2.3), [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479) (WP2.4)
**Closes on merge (issue-linkage from #464)**: [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451) (fresh-clone smoke test), [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339) (worktree no-symlink)
**Safety-net dependency**: [#361](https://github.com/Priivacy-ai/spec-kitty/issues/361) — dashboard typed contracts (WPState / Lane)
**Guardrail reference**: [Priivacy-ai/spec-kitty#393](https://github.com/Priivacy-ai/spec-kitty/issues/393) — bulk-edit occurrence-classification pattern (landed)
**Phase 1 predecessor**: [#627](https://github.com/Priivacy-ai/spec-kitty/pull/627) / `db451b8f` (Phase 1 excision — curation, `_proposed/`, inline refs)

---

## Problem Statement

Phase 1 of the Doctrine Reference Graph (DRG) rebuild landed on `main` on 2026-04-14 via [#627](https://github.com/Priivacy-ai/spec-kitty/pull/627) / `db451b8f`. That tranche excised doctrine curation, removed `_proposed/` trees, stripped inline reference fields from shipped artifacts, collapsed to a single `build_charter_context` path, and made DRG-backed charter resolution live. As of the current `main` the charter compilation pipeline is DRG-driven, but the **distribution and read surface** of the compiled bundle is still unfinished:

- **The chokepoint is under-adopted.** `ensure_charter_bundle_fresh()` exists at `src/charter/sync.py:50-90` and auto-refreshes the derived bundle when `charter.md` exists but the extracted YAMLs are missing or stale. Only two internal loaders call it: `load_governance_config()` at `src/charter/sync.py:204` and `load_directives_config()` at `src/charter/sync.py:244`. The primary consumer of charter state — `build_charter_context()` at `src/charter/context.py:406-661` — bypasses the chokepoint and performs direct reads of `charter.md` (line 555) and `references.yaml` (line 637). Dashboard charter path resolution at `src/specify_cli/dashboard/charter_path.py:8-17` performs an existence check only, not a freshness guarantee.
- **Worktrees still symlink charter artifacts into each execution workspace.** `src/specify_cli/core/worktree.py:374-532` (`setup_feature_directory()`) creates relative symlinks from each worktree to `.kittify/memory/` and `.kittify/AGENTS.md` at lines 483-528, with a `shutil.copytree()` fallback on symlink failure at line 514, then adds those paths to `.git/info/exclude` at line 532. Acceptance gate 2 in [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) requires that **no symlink and no copy step** exist for charter materialization. Today's code violates that gate.
- **The bundle layout itself is still shaped by the pre-DRG model.** `.kittify/charter/` carries a flat set of files on current `main` — `charter.md` (tracked), and (when sync has run) `governance.yaml`, `directives.yaml`, `metadata.yaml`, `references.yaml`, `context-state.json`, `interview/answers.yaml`, and an optional `library/*.md` tree (derivatives gitignored via `.gitignore:18-22`). There is no explicit bundle contract: no versioned layout document, no manifest declaring which files are "the bundle", no single entry point describing what a reader can expect to see. Architecture §6 and issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) describe a single compiled governance bundle with **one staleness check, one chokepoint, and one materialization step**. The current layout is close but is not that.
- **Migration `m_3_2_0_unified_bundle.py` does not exist.** The migration folder `src/specify_cli/upgrade/migrations/` shows that the `3.2.0` / `3.2.1` / `3.2.2` slots are already taken by the recently landed `m_3_2_0_update_planning_templates.py`, `m_3_2_1_strip_selection_config.py`, and `m_3_2_2_safe_globalize_commands.py`. The literal filename named in issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) is therefore unavailable on `main`; the next free slot is `m_3_2_3_unified_bundle.py`. The issue text will be updated to match (see Constraints C-008).
- **Two `charter` packages continue to coexist in the source tree.** `src/charter/` (canonical per issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)) and `src/specify_cli/charter/` (a near-duplicate with 13 of the 16 files) are both present on `main`. The canonical chokepoint lives in `src/charter/sync.py`. Full package deduplication is **explicitly out of scope** for this tranche — see Non-Goals — but any live path still routed through `src/specify_cli/charter/` must be kept correct in lockstep during WP2.3 to avoid reader bypass regressions.

The root problem is that the **chokepoint exists but is not enforced**, the **bundle layout is implicit rather than contractual**, and the **worktree execution model still duplicates charter state** onto disk via symlink/copy. Each of these is a separate acceptance gate in [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464). The tranche closes all three together and delivers the migration that upgrades existing 3.x projects.

This is a broad mechanical edit across readers, the worktree setup code, the charter module, the dashboard scanner, and the migration infrastructure. The `#393` bulk-edit occurrence-classification pattern already landed for Phase 1 is the required guardrail: every work package in this mission must produce an occurrence artifact, category-aware include/exclude rules, and verification-by-completeness (the "to-change" set is empty on disk at merge), not hand-eyed diff heroics.

---

## Goals

- Define and ship a **contractual unified bundle layout** under `.kittify/charter/` that makes explicit which files constitute the bundle, which are tracked vs. derived, and how a reader identifies freshness. Architecture §6 / issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) is the authority.
- Promote `ensure_charter_bundle_fresh()` to the **sole chokepoint** for every charter-derivative read in the codebase — synthesis, compilation, context building, dashboard exposure, CLI commands, and internal loaders. Verified by code inventory and by targeted regression tests that each reader routes through the chokepoint.
- Commit the repo to **canonical-root resolution** semantics: the chokepoint resolves `repo_root` to the git *common* directory (the main checkout), so a reader running inside a worktree transparently reads the main-repo bundle without any materialization inside the worktree. No symlink, no copy, no per-worktree derived state.
- **Excise the charter symlink/copy step** from `setup_feature_directory()` in `src/specify_cli/core/worktree.py`. Worktrees inherit charter visibility through the canonical-root resolver, not through filesystem duplication.
- Land migration **`m_3_2_3_unified_bundle.py`** (next free slot) that cleanly upgrades a populated 3.x project to the unified bundle layout: removes stale symlinks/copies from existing worktrees, re-runs the chokepoint to re-materialize the derived bundle, and verifies layout invariants. Updates `.gitignore` if the layout contract changes any tracked-vs-derived assignments.
- Apply the `#393` bulk-edit guardrail at every work package boundary so the cutover is verified by completeness, not by diff review. Preserve the "no fallback, no backwards compatibility" direction.
- Preserve the `#361` dashboard typed contracts (`WPState`, `Lane`) through the WP2.3 scanner/reader rewire so no dashboard regression lands with the chokepoint adoption.

## Non-Goals

- **Not deduplicating the two `charter` packages.** `src/charter/` remains canonical; `src/specify_cli/charter/` remains present. If a live path still imports from the duplicate, the WP2.3 reader cutover updates it in lockstep for correctness, but full namespace collapse is explicitly a follow-up tranche.
- **Not redesigning the DRG.** Phase 0 (graph schema, merged-graph validator, `build_context_v2()` semantics promoted to `build_charter_context`) is the baseline. Phase 1 excision is the baseline. Nothing in this mission reopens either.
- **Not touching the Charter Synthesizer.** That is [Phase 3 / #465](https://github.com/Priivacy-ai/spec-kitty/issues/465).
- **Not redesigning charter authoring UX.** The `spec-kitty charter interview`, `generate`, and `sync` CLI surfaces stay as-is except for any change strictly required by the bundle-layout contract.
- **Not shipping any fallback, dual-read mode, compatibility shim, soft deprecation, or per-worktree materialization fallback.** Per EPIC [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) and the "no fallback mechanisms" project directive, the cutover is hard.
- **Not relocating the bundle outside the working tree** (e.g., into `.git/spec-kitty/`). The bundle stays at `.kittify/charter/`; canonical-root resolution is achieved by resolver logic, not by filesystem relocation.
- **Not redesigning any migration already shipped.** `m_3_2_0_update_planning_templates.py`, `m_3_2_1_strip_selection_config.py`, `m_3_2_2_safe_globalize_commands.py`, and the Phase 1 `m_3_1_1_charter_rename.py` are not reopened. The new migration takes the next free slot.
- **Not adding project-local DRG overlays or provenance sidecars.** Those are Phase 3 / Phase 7 concerns.
- **Not rewriting the dashboard scanner semantics beyond the minimum needed to route through the chokepoint and keep `#361` typed contracts intact.**

---

## User Scenarios & Testing

### Primary Users

The primary "users" of this tranche are **spec-kitty operators and downstream agent integrators** who clone a spec-kitty project, open worktrees during implementation, and rely on charter-derived context in agent prompts. Contributors to `spec-kitty` itself are the secondary audience — they feel the change as an invariant that "every charter read routes through `ensure_charter_bundle_fresh()`."

### Scenario 1 — Fresh clone, no manual sync

- **Given** an operator clones a project that uses spec-kitty for governance, with `charter.md` tracked and `.kittify/charter/` derivatives gitignored.
- **When** they run any charter-derivative command without first running `spec-kitty charter sync` (e.g., `spec-kitty charter context --action specify`, `spec-kitty next`, `spec-kitty agent action implement WP01 --agent claude`, or the dashboard scanner loading mission state).
- **Then** the chokepoint auto-materializes the derived bundle on first read, the command succeeds with correct governance context, and the operator is never asked to run `charter sync` manually. (Closes [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451).)

### Scenario 2 — Worktree created for implementation

- **Given** planning has finalized tasks and the operator runs `spec-kitty implement WP01` or `spec-kitty next --agent claude`, which triggers worktree creation via `setup_feature_directory()`.
- **When** the worktree is set up.
- **Then** **no symlink and no copy** of any charter artifact is created inside the worktree. The agent running in the worktree reads charter state via `ensure_charter_bundle_fresh()`, which resolves to the main-checkout `.kittify/charter/` bundle through the canonical-root resolver. `git status` inside the worktree shows no charter-related symlink or copied file; `.git/info/exclude` is not modified to cover charter artifacts. (Closes [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339).)

### Scenario 3 — Stale bundle after the operator edits `charter.md`

- **Given** an operator edits `charter.md` directly (e.g., via IDE) without running `spec-kitty charter sync`.
- **When** the next charter-derivative read occurs (any reader listed in the WP2.3 occurrence artifact).
- **Then** the chokepoint detects staleness by comparing `charter.md` content hash against `metadata.yaml`, auto-triggers `sync()`, and the reader receives the refreshed bundle. No reader ever observes a stale derivative.

### Scenario 4 — Agent reading charter context from inside a worktree

- **Given** an agent is running `spec-kitty agent action implement WP01 --agent claude` inside `.worktrees/<slug>-<mid8>-lane-a/`.
- **When** the agent's prompt-building path calls `build_charter_context(repo_root=worktree_path, action="implement", ...)`.
- **Then** the chokepoint internally resolves `repo_root` to the git common directory (main checkout), reads the unified bundle from there, and returns the same `CharterContextResult` an agent running in the main checkout would receive. No bundle artifacts are read from or written to the worktree's `.kittify/` path.

### Scenario 5 — Dashboard scanner reading governance during a live session

- **Given** the dashboard is running (`spec-kitty dashboard`) against a project whose `.kittify/charter/` has been modified since last scan.
- **When** the scanner materializes typed contracts (`WPState`, `Lane` from [#361](https://github.com/Priivacy-ai/spec-kitty/issues/361)) and surfaces charter presence/status to the UI.
- **Then** every charter-derivative read inside the scanner routes through `ensure_charter_bundle_fresh()`, the typed contracts remain byte-identical to their pre-Phase-2 shape on the same fixture, and no dashboard regression test under `tests/test_dashboard/` regresses.

### Scenario 6 — Operator upgrading a populated 3.x project

- **Given** an operator upgrades a spec-kitty project that already has the Phase 1 layout: `.kittify/charter/charter.md` tracked, derived YAMLs present from a previous `charter sync`, and potentially one or more open worktrees under `.worktrees/` with charter symlinks in place.
- **When** the operator runs `spec-kitty upgrade` (which triggers the migration registry).
- **Then** `m_3_2_3_unified_bundle.py` runs idempotently: it removes charter-related symlinks or copies from every discovered worktree, validates the bundle manifest at `.kittify/charter/`, re-runs the chokepoint to regenerate any missing derivatives, updates `.gitignore` if the bundle contract changes tracked-vs-derived assignments, and reports exactly what it changed in JSON output. Re-running the migration is a no-op.

### Scenario 7 — Contributor running the test suite

- **Given** a contributor checks out post-Phase-2 `main`.
- **When** they run the full pytest suite.
- **Then** new test classes under `tests/charter/test_bundle_contract.py`, `tests/charter/test_chokepoint_coverage.py`, `tests/init/test_fresh_clone_no_sync.py`, `tests/core/test_worktree_no_charter_materialization.py`, and `tests/upgrade/test_unified_bundle_migration.py` all pass; existing charter-related tests pass without modification except those rewired by WP2.3; `mypy --strict` remains green.

### Edge Cases

- **Worktree created when the main-checkout bundle is stale.** The chokepoint resolves to the main checkout and refreshes the bundle there; the worktree agent sees the refreshed state.
- **Multiple worktrees reading concurrently.** The chokepoint's sync step must be safe under concurrent invocation; `src/charter/sync.py` already uses `atomic_write` from `kernel.atomic` (confirmed in audit), and this mission reuses that primitive for any additional writes.
- **Operator creates a worktree on a filesystem that had the old symlinks.** The migration's post-upgrade reconciliation removes stale symlinks; in the narrow window between upgrade and first implement call, manual leftover symlinks from pre-upgrade runs are caught by the migration's scan step at `.worktrees/<*>/.kittify/memory` and `.worktrees/<*>/.kittify/AGENTS.md`.
- **Project with no `charter.md` at all.** Chokepoint returns `None` (per current `ensure_charter_bundle_fresh()` contract at `src/charter/sync.py:54`); readers receive an explicit "missing charter" signal and degrade accordingly. This behavior is preserved unchanged.
- **Project with `charter.md` but no derivatives and no network access.** The chokepoint generates derivatives from the local charter file without any external fetch; the bundle contract guarantees no reader requires network to hydrate.
- **Dashboard open while migration runs.** The migration writes via atomic renames; the dashboard scanner's chokepoint invocation re-reads and finds the new state. Typed contracts survive the transition.
- **Bundle manifest absent on a pre-Phase-2 project.** The migration creates it as part of the upgrade; the chokepoint treats "manifest missing" identically to "staleness detected" and regenerates.
- **Contributor attempts to reintroduce a symlink step for charter artifacts in `setup_feature_directory()` in a future PR.** A new regression test under `tests/core/test_worktree_no_charter_materialization.py` asserts the absence of any charter-path symlink/copy in a setup'd worktree and fails.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
| --- | --- | --- |
| FR-001 | The codebase must declare a **bundle manifest contract** at `src/charter/bundle.py` (or an equivalently canonical module under `src/charter/`) that enumerates, in typed Pydantic form, every file path that constitutes the unified bundle, whether each is tracked or derived, and which artifacts produce each derived file. The manifest is the single source of truth consumed by the chokepoint, the migration, and the bundle contract tests. | Draft |
| FR-002 | The unified bundle layout under `.kittify/charter/` must be documented in `architecture/2.x/` (new file or update to §6 section) with the final filename set, tracked-vs-derived classification, gitignore expectations, and the canonical-root resolution contract. The documentation file is the authoritative reference cited by FR-001. | Draft |
| FR-003 | `ensure_charter_bundle_fresh()` must resolve `repo_root` to the **git common directory** (the main checkout) when invoked from inside a worktree, and must return a `SyncResult | None` whose file paths reference only the main-checkout bundle. A helper `resolve_canonical_repo_root(path: Path) -> Path` must be introduced (in `src/charter/sync.py` or a new `src/charter/resolution.py`) and must use `git rev-parse --git-common-dir` semantics (via a stdlib/subprocess wrapper or an existing helper in `kernel/` if one exists) rather than re-implementing git layout parsing. | Draft |
| FR-004 | Every charter-derivative reader in `src/` must route through `ensure_charter_bundle_fresh()` before reading any bundle artifact. The exhaustive list (refined during WP2.3 occurrence classification) includes at minimum: `build_charter_context()` at `src/charter/context.py`, the `_load_references()` call in the same module, `load_governance_config()` at `src/charter/sync.py:187` (already routed), `load_directives_config()` at `src/charter/sync.py:229` (already routed), `resolve_governance()` at `src/charter/resolver.py:43` (already routed indirectly), `resolve_project_charter_path()` at `src/specify_cli/dashboard/charter_path.py:8`, the dashboard scanner's charter-presence probes in `src/specify_cli/dashboard/scanner.py` and `server.py`, the `spec-kitty charter context` CLI handler at `src/specify_cli/cli/commands/charter.py`, the next-prompt builder at `src/specify_cli/next/prompt_builder.py`, and the workflow prompt builder at `src/specify_cli/cli/commands/agent/workflow.py`. The `src/specify_cli/charter/` duplicate package's equivalents are updated in lockstep where they remain live per C-003. | Draft |
| FR-005 | `setup_feature_directory()` at `src/specify_cli/core/worktree.py:374-532` must be modified to remove every charter-path symlink and copy step. Specifically: the symlink creation at lines 493-514 for `.kittify/memory/`, the symlink creation at lines 516-528 for `.kittify/AGENTS.md`, the `shutil.copytree()` fallback, and the `.git/info/exclude` entry for those paths at line 532 must all be deleted. Any non-charter symlink/copy behavior currently present at that call site must be preserved unchanged and documented in the WP2.3 occurrence artifact as an explicit non-touched carve-out. | Draft |
| FR-006 | A new Pydantic model `CharterBundleManifest` (in the FR-001 module) must declare, minimally: `tracked_files: list[Path]`, `derived_files: list[Path]`, `derivation_sources: dict[Path, Path]` (derived → source), `gitignore_required_entries: list[str]`, `schema_version: str`. Every bundle-consumer test case must load this manifest and assert layout compliance. | Draft |
| FR-007 | Migration `m_3_2_3_unified_bundle.py` under `src/specify_cli/upgrade/migrations/` must, when applied to a populated 3.x project: (a) scan `.worktrees/*/` and delete any `.kittify/memory`, `.kittify/AGENTS.md`, or other charter-bundle symlinks/copies found there; (b) remove the matching `.git/info/exclude` entries inside each worktree; (c) validate `.kittify/charter/` against the FR-006 manifest; (d) invoke the chokepoint to regenerate any missing derived files; (e) update the project `.gitignore` to match the manifest's `gitignore_required_entries` if the layout contract changes tracked-vs-derived assignments; (f) produce a structured JSON report enumerating every filesystem change. The migration must be idempotent: a second apply must be a no-op. | Draft |
| FR-008 | The migration must register with `target_version = "3.2.3"` in the `MigrationRegistry` (pattern matches `m_3_2_0_update_planning_templates.py:50-60`) and must be discoverable via the registry's auto-discovery path in `src/specify_cli/upgrade/migrations/__init__.py`. The filename on disk must be `m_3_2_3_unified_bundle.py` (next free slot). Issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) is updated in the tracking commentary to reflect the corrected filename. | Draft |
| FR-009 | A new test module `tests/init/test_fresh_clone_no_sync.py` must exercise the following flow end-to-end in a temporary cloned-style fixture (populated `charter.md`, no derivatives on disk, no prior `sync` invocation): each charter-derivative reader enumerated in FR-004's minimum list is invoked once; each invocation succeeds; after the first invocation the derivatives exist on disk; `spec-kitty charter sync` is **never** called explicitly by the test. | Draft |
| FR-010 | A new test module `tests/core/test_worktree_no_charter_materialization.py` must create a feature directory via `setup_feature_directory()` and assert: no symlink exists under the resulting worktree path that points into `.kittify/`; no file under the worktree's `.kittify/` tree is a copy of a main-checkout charter artifact; `.git/info/exclude` inside the worktree contains no `.kittify/memory` or `.kittify/AGENTS.md` entry. | Draft |
| FR-011 | A new test module `tests/charter/test_chokepoint_coverage.py` must, using a module-level registry of all charter-derivative reader call sites, assert via Python AST walk of `src/` that every such site either calls `ensure_charter_bundle_fresh()` directly or reaches it through a helper whose implementation routes through the chokepoint. The registry is seeded from the WP2.3 occurrence classification artifact and is the test's source of truth. | Draft |
| FR-012 | A new test module `tests/charter/test_bundle_contract.py` must load `CharterBundleManifest`, instantiate an in-tmpdir charter bundle via the chokepoint, and assert that every file listed as `tracked` exists and is not gitignored, every file listed as `derived` is gitignored, every derived file has a corresponding `derivation_sources` entry, and no unexpected files appear in `.kittify/charter/`. | Draft |
| FR-013 | A new test module `tests/upgrade/test_unified_bundle_migration.py` must drive `m_3_2_3_unified_bundle.py` against at least the following fixture matrix: (a) a pre-Phase-2 project with legacy charter symlinks in open worktrees; (b) a pre-Phase-2 project with no worktrees; (c) a Phase-2-shaped project (migration must be a no-op); (d) a project with stale `metadata.yaml` hash against `charter.md` (chokepoint must refresh); (e) a project where `charter.md` is absent (migration must skip bundle validation cleanly and not error). Each fixture asserts the full structured JSON report shape. | Draft |
| FR-014 | The dashboard scanner rewire in WP2.3 must preserve the `#361` typed contracts (`WPState`, `Lane`). A regression test under `tests/test_dashboard/test_charter_chokepoint_regression.py` must load a fixture that exercises the dashboard's charter-presence and charter-read paths, assert that each path invokes the chokepoint at least once, and assert that the typed contract outputs are byte-identical to a golden baseline captured pre-WP2.3 on `main` and committed under `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json`. | Draft |
| FR-015 | Each work package must produce an **occurrence classification artifact** at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml` following the `#393` pattern (category-aware include/exclude, explicit per-category rationale, mission-level aggregate index). Completion of the WP is verified by proving the artifact's "to-change" set is empty on disk (verification-by-completeness), not by hand-reviewing semantic diffs. | Draft |
| FR-016 | Post-merge, the following grep invariants must hold on `src/` and `tests/` (permitted exceptions listed in the mission-level occurrence map): zero occurrences of `.kittify/memory` or `.kittify/AGENTS.md` symlink creation in production code paths outside migration logic; zero occurrences of direct reads against `.kittify/charter/<anything>` that do not flow through `ensure_charter_bundle_fresh()`; zero `shutil.copytree` invocations targeting `.kittify/charter/` or `.kittify/memory` outside the migration module; the string `ensure_charter_bundle_fresh` appears at every reader site enumerated in FR-004. | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable Threshold | Status |
| --- | --- | --- | --- |
| NFR-001 | Total pytest runtime on CI must not regress by more than 5% compared to the last green run on pre-Phase-2 `main`, measured as p50 over three consecutive CI runs on each of the pre-Phase-2 and post-Phase-2 commits. | ≤5% regression | Draft |
| NFR-002 | The chokepoint's freshness check (existence, hash comparison) must add less than 10 ms to any reader invocation on a warm bundle (all derivatives present, hash-matched), measured on the dashboard scanner's per-frame charter-read path as the hot loop. Cold regeneration cost is governed by the existing `sync()` path and is explicitly not bounded by this requirement. | <10 ms warm overhead (p95 over 100 invocations on the dashboard fixture) | Draft |
| NFR-003 | Canonical-root resolution (`resolve_canonical_repo_root`) must add less than 5 ms per call on a repo with a worktree-attached working tree, measured as p95 over 100 invocations, and must not shell out to `git` more than once per invocation (subsequent calls use a cached result keyed by working directory). | <5 ms p95 per call; ≤1 git invocation per call | Draft |
| NFR-004 | `mypy --strict` must pass on every new and modified module, and line coverage on new or rewritten code (FR-001 bundle module, FR-003 resolver, FR-007 migration, and every new test module) must be at or above 90%. | 0 mypy errors; ≥90% line coverage on changed files | Draft |
| NFR-005 | Post-merge, the mission-level occurrence map's "must be zero" set must be empty when the scripted completeness check runs in CI. The set includes: residual `.kittify/memory` / `.kittify/AGENTS.md` symlink or copy instructions in non-migration code; direct `.kittify/charter/` file reads that bypass the chokepoint; any carve-out not explicitly listed in the mission-level occurrence map at merge. | 0 stray occurrences outside the permitted-exceptions list | Draft |
| NFR-006 | `spec-kitty upgrade` on a representative 3.x fixture project (with one open worktree and populated charter bundle) must complete the `m_3_2_3_unified_bundle.py` step in under 2 seconds on a developer laptop baseline (MacBook Pro M-series, SSD, no network IO). | ≤2 s wall time on the FR-013 reference fixture | Draft |

### Constraints

| ID | Constraint | Status |
| --- | --- | --- |
| C-001 | No fallback, no backwards-compatibility shim, no dual-read mode, no soft deprecation — per [EPIC #461 §10](https://github.com/Priivacy-ai/spec-kitty/issues/461) and the project's standing "no fallback mechanisms" directive. | Active |
| C-002 | The `#393` bulk-edit guardrail (explicit occurrence classification, category-aware include/exclude, mission-level occurrence map, verification-by-completeness) is mandatory for every WP in this tranche. | Active |
| C-003 | `src/charter/` is canonical; `src/specify_cli/charter/` is not deduplicated in this tranche. Any reader still routed through the duplicate is updated in lockstep during WP2.3 for correctness. Full namespace collapse is a follow-up tranche. | Active |
| C-004 | GitHub issues [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461), [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464), [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451), [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339), [#361](https://github.com/Priivacy-ai/spec-kitty/issues/361), [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478), [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480), [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481), [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479) are authoritative. Local planning documents under `spec-kitty-planning/` are reference only. | Active |
| C-005 | Phase 0 (DRG schema, `graph.yaml`, merged-graph validator, `build_context_v2()` semantics promoted to `build_charter_context`) and Phase 1 excision are baselines and may not be reopened. | Active |
| C-006 | Only SOURCE templates under `src/specify_cli/missions/*/command-templates/` and `src/specify_cli/skills/` may be edited for any template-touching work. Agent copy directories (`.claude/`, `.amazonq/`, `.augment/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/prompts/`, `.kilocode/`, `.opencode/`, `.qwen/`, `.roo/`, `.windsurf/`, `.kiro/`) are generated copies and must not be hand-edited in this mission. | Active |
| C-007 | Work packages must land in strict dependency order: WP2.1 → WP2.2 → WP2.3 → WP2.4. Each WP is merged behind its own PR, preflight-verified, and validated end-to-end before the next begins. Parallelization is rejected for the reasons in the Implementation Plan's Sequencing note. | Active |
| C-008 | The literal filename `m_3_2_0_unified_bundle.py` from issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) is unavailable because slots `3.2.0`, `3.2.1`, and `3.2.2` are already taken on `main`. The deliverable filename is `m_3_2_3_unified_bundle.py`. The issue text is updated in the tracking commentary; no already-shipped migration is renamed or collapsed. | Active |
| C-009 | Canonical-root resolution must use git-native semantics (`git rev-parse --git-common-dir` or an equivalent well-known Git mechanism) rather than filesystem-path heuristics. This ensures the resolver is correct under submodule, sparse-checkout, and detached-HEAD conditions. | Active |
| C-010 | `#361` dashboard typed contracts (`WPState`, `Lane`) are the regression safety net for the WP2.3 scanner rewire. Any change that modifies typed-contract outputs requires a companion regression entry against the FR-014 baseline. | Active |

---

## Success Criteria

The Phase 2 tranche is complete when **all** of the following hold on post-merge `main`:

1. A populated 3.x project cloned fresh (with `charter.md` tracked, no derivatives on disk) executes every charter-derivative reader path without the operator invoking `spec-kitty charter sync`. The chokepoint auto-materializes derivatives on first read. (Gate 1 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464); closes [#451](https://github.com/Priivacy-ai/spec-kitty/issues/451).)
2. Every worktree created by `setup_feature_directory()` contains **no** charter-related symlink, no charter artifact copy, and no `.git/info/exclude` entry for charter paths. `git status` inside a freshly-created worktree shows no charter-path entries. (Gate 2 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464); closes [#339](https://github.com/Priivacy-ai/spec-kitty/issues/339).)
3. `tests/charter/test_chokepoint_coverage.py` passes, asserting by AST walk that every reader call site in FR-004 routes through `ensure_charter_bundle_fresh()`. The test's registry of reader sites matches the WP2.3 occurrence artifact verbatim. (Gate 3 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464).)
4. `m_3_2_3_unified_bundle.py` is present under `src/specify_cli/upgrade/migrations/`, registered in the registry, and passes `tests/upgrade/test_unified_bundle_migration.py` on every fixture in the FR-013 matrix. (Gate 4 of [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464).)
5. `CharterBundleManifest` exists as a typed Pydantic model under `src/charter/bundle.py` (or equivalent canonical path), documents every file in the unified bundle, and is the authority consumed by FR-001, FR-006, FR-007, FR-012.
6. The documentation file under `architecture/2.x/` describing the unified bundle contract is committed and cited from the manifest module docstring.
7. `grep -R "shutil\.copytree\|os\.symlink\|Path\.symlink_to" src/specify_cli/core/worktree.py` returns zero hits touching charter paths (`.kittify/memory`, `.kittify/AGENTS.md`, `.kittify/charter`) outside the migration module.
8. `grep -R "\.kittify/charter" src/` shows every direct path reference either flows through `ensure_charter_bundle_fresh()` (verified by AST test) or is in an explicitly carved-out location (manifest module, migration module, bundle documentation).
9. Each of WP2.1 / WP2.2 / WP2.3 / WP2.4 has a committed occurrence-classification artifact at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml` and the "to-change" set in each is empty at merge.
10. The pre-WP2.3 dashboard typed-contracts golden baseline is committed at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` and `tests/test_dashboard/test_charter_chokepoint_regression.py` reproduces it byte-identically against post-WP2.3 code.
11. The changelog entry for the release that ships this tranche documents: the unified bundle contract and manifest location; the worktree no-symlink/no-copy behavior change; the `m_3_2_3_unified_bundle.py` upgrade path; the absence of any compatibility shim.
12. `mypy --strict` passes and line coverage on new/changed code meets NFR-004.

---

## Key Entities

- **Unified bundle** — the set of files under `.kittify/charter/` that together express the project's compiled governance state. Declared by the `CharterBundleManifest` Pydantic model; distinct from individual derivative files (governance.yaml, directives.yaml, metadata.yaml, references.yaml, interview/answers.yaml, optional library/*.md, context-state.json). After Phase 2 the bundle has a single canonical on-disk layout and a single freshness contract.
- **Canonical repo root** — the main checkout's working directory, equal to `git rev-parse --git-common-dir`'s parent under normal conditions. Used by the chokepoint so a reader running inside a worktree transparently reads the main-checkout bundle.
- **Chokepoint** — `ensure_charter_bundle_fresh()` at `src/charter/sync.py:50-90`. After Phase 2 it is the sole entry path for every charter-derivative read. It resolves to the canonical root, checks completeness and staleness, triggers `sync()` if needed, and returns a `SyncResult | None` per its current contract.
- **`CharterBundleManifest`** — the typed Pydantic model introduced by FR-001 that declares every file in the bundle, its tracked-vs-derived classification, and its derivation sources. Consumed by the chokepoint, the migration, and the bundle contract tests.
- **Occurrence classification artifact** — a work-package-scoped YAML at `kitty-specs/<mission_slug>/occurrences/WP2.<n>.yaml` enumerating every string and path occurrence touched by the WP, categorized, with include/exclude rules and completeness assertions. Mandated by `#393` guardrail.
- **Mission-level occurrence map** — the aggregated index at `kitty-specs/<mission_slug>/occurrences/index.yaml` that lists every permitted-exception path, every category exclusion rationale, and every category whose post-merge occurrence count must be zero. Merge review gate.
- **Dashboard typed contract** — `WPState`, `Lane`, and the surrounding dashboard-scanner response shapes defined in `#361`. Regression safety net for WP2.3.

---

## Implementation Plan (Work Package Shape)

This section is recommended shape for `/spec-kitty.plan` and `/spec-kitty.tasks`; it is **not** a pre-committed WP layout. It is derived from issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)'s four acceptance gates and from the code audit captured in the Problem Statement.

### WP2.1 — Unified bundle layout (design + typed manifest)

**Tracking issue**: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478)

Deliverables:

- `CharterBundleManifest` Pydantic model under `src/charter/bundle.py` (or equivalent canonical path chosen during plan), with fields per FR-006.
- Architecture documentation file under `architecture/2.x/` describing the unified bundle contract: final filename set, tracked-vs-derived classification, gitignore expectations, canonical-root resolution contract, staleness semantics.
- Unit tests for the manifest model: tracked-list non-empty, derived-list non-empty, every derived file has a derivation source, schema version declared.
- `occurrences/WP2.1.yaml` enumerating every path literal touched (category F — dict/YAML key, category C — filesystem path literal, category E — docstring/comment).

No reader or worktree-setup code changes in this WP. Pure additive: introduces the contract.

### WP2.2 — Chokepoint finalization (canonical-root resolution, one staleness check)

**Tracking issue**: [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480)

Depends on WP2.1 (the manifest is the authority the chokepoint consults for "what files must exist").

Deliverables:

- `resolve_canonical_repo_root(path: Path) -> Path` helper in `src/charter/sync.py` or a new `src/charter/resolution.py`, implemented via `git rev-parse --git-common-dir` per C-009. Cached per working directory.
- `ensure_charter_bundle_fresh()` refactored to call `resolve_canonical_repo_root()` at the top and to return file paths rooted at the canonical root.
- `SyncResult` dataclass either unchanged or extended minimally; no contract break for existing callers.
- Unit tests: (1) invoked from a worktree path, returns paths under the main checkout; (2) invoked from the main checkout, behaves as today; (3) invoked from a path that is not inside any repo, raises a structured error; (4) warm-hit overhead meets NFR-002; (5) cold regeneration unchanged from current behavior.
- `occurrences/WP2.2.yaml` (category A — import path, category B — symbol name, category E — docstring/comment).

No reader cutover in this WP. The chokepoint becomes correct; the readers still need to adopt it (WP2.3).

### WP2.3 — Reader cutover (every charter-derivative reader routes through the chokepoint)

**Tracking issue**: [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481)

Depends on WP2.2 (the chokepoint's canonical-root resolution is a prerequisite for worktree-based readers to pass without materialization) and WP2.1 (the manifest informs the AST-walk test registry).

Deliverables:

- Every reader site enumerated in FR-004 is updated to call `ensure_charter_bundle_fresh()` before reading any bundle artifact. Sites include at minimum:
  - `src/charter/context.py:406-661` — `build_charter_context()` (current bypass; reads `charter.md` at line 555 and `references.yaml` at line 637 directly).
  - `src/specify_cli/dashboard/charter_path.py:8-17` — `resolve_project_charter_path()` (current existence-only check).
  - Dashboard scanner / server charter-presence paths in `src/specify_cli/dashboard/scanner.py` and `src/specify_cli/dashboard/server.py` (scope refined by occurrence classification).
  - `src/specify_cli/cli/commands/charter.py` — every CLI handler that reads the bundle prior to rendering output.
  - `src/specify_cli/next/prompt_builder.py` — next-prompt charter injection.
  - `src/specify_cli/cli/commands/agent/workflow.py` — workflow prompt charter injection.
  - `src/specify_cli/charter/` duplicate package's equivalents: updated in lockstep where any remain live (per C-003). Any file whose sole purpose is to route through `src/charter/` stays untouched; any file that still performs direct reads is rewired.
- `setup_feature_directory()` at `src/specify_cli/core/worktree.py:374-532` has lines 483-532 (charter-path symlink/copy/exclude logic) removed. Non-charter symlinks, if any exist at that call site, are preserved and documented in the occurrence artifact.
- New test modules per FR-009, FR-010, FR-011, FR-014. The FR-014 baseline JSON is captured from pre-WP2.3 `main` and committed at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` as a first step in the WP (before any reader rewire).
- `occurrences/WP2.3.yaml` (categories A, B, C, D — CLI command name, E, F, G — skill/template reference, H — test identifier). This is the largest and most detailed occurrence artifact in the tranche.

The dashboard rewire must preserve `#361` typed contracts per C-010.

### WP2.4 — Migration `m_3_2_3_unified_bundle.py`

**Tracking issue**: [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479)

Depends on WP2.3 (the no-symlink behavior must be present in the current code before the migration enforces it on legacy projects).

Deliverables:

- `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` implementing FR-007 per the migration class pattern visible in `m_3_2_0_update_planning_templates.py:50-60` and `m_3_1_1_charter_rename.py`. Target version `"3.2.3"`.
- `tests/upgrade/test_unified_bundle_migration.py` exercising the FR-013 fixture matrix.
- Issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) body updated in a tracking comment to reflect the `m_3_2_3_unified_bundle.py` filename per C-008.
- `occurrences/WP2.4.yaml` (categories C, F, H).

### Sequencing note

WP2.1 → WP2.2 → WP2.3 → WP2.4 is **strict sequential**. Rationale:

- WP2.2 depends on WP2.1 because the chokepoint consults the manifest for "which files must exist" during the completeness check; without the typed manifest the chokepoint would re-encode the layout assumption in code.
- WP2.3 depends on WP2.2 because many readers run inside worktrees; without canonical-root resolution those readers would either still require charter materialization into the worktree (violating Gate 2) or would return incorrect results.
- WP2.3 depends on WP2.1 because the AST-walk test (FR-011) uses the manifest + occurrence artifact as its registry of expected reader sites.
- WP2.4 depends on WP2.3 because the migration's post-upgrade expectation — no charter symlinks in worktrees — is a property of the Phase-2 `setup_feature_directory()` behavior. If the migration ran before WP2.3 landed, a subsequent `spec-kitty next` would re-create the symlinks the migration just removed.

Parallelization is rejected. The #393 guardrail depends on clean occurrence artifacts per WP; overlapping WPs would produce overlapping category maps and invalidate the completeness proof.

---

## Validation & Test Strategy

### Verification-by-completeness (per #393)

Every WP produces an occurrence-classification artifact at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml`. At merge time the reviewer runs a scripted check that walks every category in the artifact and asserts the "to-change" set is empty on disk. This replaces hand-reviewed semantic diffs for the bulk-edit categories.

The mission-level occurrence map at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml` aggregates across WPs and declares the final "must be zero" set (per NFR-005):

```
# Symbolic / filesystem patterns that must not appear on live paths outside carve-outs:
symlink_creation_targeting_kittify_memory
symlink_creation_targeting_kittify_AGENTS_md
shutil_copytree_targeting_kittify
direct_read_of_kittify_charter_bypassing_chokepoint
git_info_exclude_entry_for_kittify_memory
git_info_exclude_entry_for_kittify_AGENTS_md
```

Permitted carve-outs (listed explicitly in the index):
- `src/charter/sync.py` — the chokepoint itself performs the authoritative read.
- `src/charter/bundle.py` — the manifest module declares paths for documentation.
- `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` — the migration performs filesystem reconciliation.
- `tests/**` fixture builders and negative-case assertions.
- `architecture/2.x/` documentation references.

### Automated test coverage

1. **Fresh-clone smoke test** (FR-009) — `tests/init/test_fresh_clone_no_sync.py`. Fixture: a tmpdir repo with only `charter.md` tracked; every FR-004 reader is invoked once without `sync`; each succeeds; derivatives exist on disk afterward.
2. **Worktree no-materialization test** (FR-010) — `tests/core/test_worktree_no_charter_materialization.py`. Drives `setup_feature_directory()`; asserts no symlink/copy/exclude-entry for charter paths in the resulting worktree.
3. **Chokepoint coverage test** (FR-011) — `tests/charter/test_chokepoint_coverage.py`. Python AST walk across `src/`; for each call site in the WP2.3 occurrence artifact's reader registry, asserts the site calls `ensure_charter_bundle_fresh` directly or via a helper whose implementation routes through it.
4. **Bundle contract test** (FR-012) — `tests/charter/test_bundle_contract.py`. Loads `CharterBundleManifest`, materializes a bundle via the chokepoint in tmpdir, asserts layout compliance against the manifest.
5. **Migration matrix** (FR-013) — `tests/upgrade/test_unified_bundle_migration.py`. Five fixtures per FR-013; each asserts structured JSON report shape and idempotency.
6. **Dashboard typed-contract regression** (FR-014) — `tests/test_dashboard/test_charter_chokepoint_regression.py`. Byte-identical comparison against the pre-WP2.3 golden baseline.
7. **Coverage / type check** — `pytest --cov` enforces NFR-004; `mypy --strict` must pass on every WP PR.
8. **Runtime / warm-overhead benchmarks** — NFR-002 and NFR-003 are enforced via micro-benchmarks in `tests/charter/test_chokepoint_overhead.py` and `tests/charter/test_resolution_overhead.py`.

### Manual validation (spot checks)

- On a fresh checkout of the post-Phase-2 commit, clone a populated 3.x project fixture, run `spec-kitty charter context --action specify --json` without any prior `sync`, and confirm the derivatives exist afterward and the JSON is correct.
- Run `spec-kitty next --agent claude` on a feature with tasks finalized; inspect the resulting worktree with `ls -la .worktrees/<slug>-<mid8>-lane-a/.kittify/` and confirm no charter-related symlink or copy is present, and `git status` inside the worktree shows no charter-related entries.
- Run `spec-kitty upgrade` on a representative pre-Phase-2 project with one open worktree; inspect the migration's JSON report; re-run upgrade and confirm the second invocation is a no-op.

### CI integration

- The mission-level occurrence map check runs as a non-skippable job in each WP PR and in the final merge PR.
- `tests/charter/test_chokepoint_coverage.py` and `tests/charter/test_bundle_contract.py` run in the default pytest job.
- NFR-001 (runtime regression budget) is measured by comparing `pytest --durations=0` summaries from pre- and post-Phase-2 CI runs; any run exceeding the 5% budget blocks merge.
- NFR-002 and NFR-003 micro-benchmarks run in a dedicated perf job whose threshold failures block merge.

---

## Assumptions

- The audit finding that only two internal loaders (`load_governance_config()` and `load_directives_config()`) currently route through `ensure_charter_bundle_fresh()` is exhaustive for the `src/charter/` canonical package as of current `main`. WP2.3 occurrence classification re-verifies by full-repo grep and AST walk.
- `git rev-parse --git-common-dir` is available and behaves as documented on every platform the project supports (macOS, Linux, Windows WSL). No fallback is provided; if a user's git is too old, `spec-kitty` fails loudly per the "no fallback" directive.
- `src/specify_cli/charter/` contains mostly inert duplicates or wrappers around `src/charter/`. If any file under the duplicate path still performs a direct charter read on a live code path, WP2.3 updates it in lockstep. No assumption is made that the duplicate is fully inert.
- The `#361` dashboard typed contracts (`WPState`, `Lane`) are stable on current `main`. The FR-014 golden baseline is a point-in-time capture against that stability.
- `m_3_1_1_charter_rename.py` (Phase 1) correctly normalized all legacy charter layouts, so the Phase-2 migration starts from the Phase-1 layout as its precondition. Projects that have not run Phase 1's migration are out of scope for this mission's migration test matrix; the upgrade chain handles them sequentially per the registry's ordering.
- `.gitignore` entries for `.kittify/charter/` derivatives on current `main` (`.gitignore:18-22`) are the correct Phase-2 tracked-vs-derived assignment. If WP2.1's manifest design requires changes, WP2.4's migration applies them.
- `kernel.atomic.atomic_write` (used in `src/charter/sync.py` today) is safe under concurrent invocation across processes, so the chokepoint remains correct when multiple readers attempt to refresh simultaneously.
- The `setup_feature_directory()` charter symlink/copy block (lines 483-532) is the only place in the codebase that materializes charter state into a worktree. WP2.3's occurrence classification re-verifies by grepping for `.kittify/memory`, `.kittify/AGENTS.md`, `shutil.copytree`, `Path.symlink_to`, and `os.symlink` across `src/`.
- Downstream tools that embed spec-kitty as a library read charter state through the chokepoint (via `build_charter_context()` or the public `spec-kitty charter context` CLI). No downstream assumes the existence of a charter symlink inside a worktree.
- The occurrence-classification scripted check from Phase 1 is reusable for Phase 2; if any rework is needed it is in-scope for WP2.3 and documented in the WP2.3 occurrence artifact.

---

## Out of Scope (Deferred to Phase 3+)

- **Charter Synthesizer pipeline and FR1 implementation** ([Phase 3 / #465](https://github.com/Priivacy-ai/spec-kitty/issues/465)).
- **Profile-as-entry-point CLI and host-LLM advise/execute** ([Phase 4 / #466](https://github.com/Priivacy-ai/spec-kitty/issues/466)).
- **Glossary-as-DRG + chokepoint + dashboard tile** ([Phase 5 / #467](https://github.com/Priivacy-ai/spec-kitty/issues/467)).
- **Mission rewrite and retrospective contract** ([Phase 6 / #468](https://github.com/Priivacy-ai/spec-kitty/issues/468)).
- **Schema versioning and provenance hardening** ([Phase 7 / #469](https://github.com/Priivacy-ai/spec-kitty/issues/469)).
- Full deduplication of `src/charter/` vs. `src/specify_cli/charter/` (explicitly deferred per C-003).
- Relocating the bundle out of the working tree (e.g., into `.git/spec-kitty/`).
- Adding project-local DRG overlay support beyond what Phase 0 already ships.
- Any change to the `spec-kitty charter interview` / `generate` authoring UX beyond what the bundle contract strictly requires.
- Any change to the `#361` dashboard typed contract shape (only preserved, not evolved).

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| A reader site is missed by the WP2.3 occurrence classification and continues to perform a direct charter read, silently bypassing the chokepoint. | Medium | High (freshness-safety regression) | FR-011 AST-walk test is the completeness proof; the test's registry is the WP2.3 occurrence artifact. A missed site fails the test. |
| `git rev-parse --git-common-dir` returns an unexpected value under a sparse-checkout, submodule, or detached-HEAD edge case, and the chokepoint resolves to the wrong root. | Medium | High (reader reads empty bundle) | WP2.2 unit tests include explicit sparse-checkout, submodule-attached, and detached-HEAD fixtures. The resolver's behavior is specified in C-009; any platform inconsistency is surfaced as a loud failure, not a silent misroute. |
| Removing charter symlinks from `setup_feature_directory()` breaks an agent that embedded a relative path expectation (`../../../.kittify/memory/...`) in its prompt templates or skill code. | Low | Medium (runtime break in agent tooling) | WP2.3 occurrence classification must include a grep of `src/specify_cli/missions/*/command-templates/`, `src/specify_cli/skills/`, and `src/specify_cli/next/prompt_builder.py` for any `../../../.kittify` path literal. Every hit is either rewired or flagged as an explicit carve-out. |
| The migration fails idempotency because a second invocation re-encounters a legacy worktree whose symlink was created after the first migration apply. | Low | Medium (confusing upgrade UX) | Migration test matrix (FR-013) explicitly exercises double-apply; the migration's scan step must be stateless and re-entrant. |
| The dashboard typed-contract baseline captures noise (timestamps, ordering) that makes byte-identical comparison flaky. | Medium | Low-Medium (flaky regression test) | WP2.3 golden capture must freeze or redact non-deterministic fields before committing `pre-wp23-dashboard-typed.json`. The capture script is committed alongside the baseline so the capture is reproducible. |
| The chokepoint warm-overhead requirement (NFR-002, <10 ms) is breached because the hash check reads the full `charter.md` each call. | Low | Low-Medium (dashboard lag on hot path) | WP2.2 caches the charter.md mtime and short-circuits the hash read when mtime is unchanged since the previous check. |
| A PR lands out of order (e.g., WP2.4 before WP2.3), leaving the migration enforcing a no-symlink invariant that current `setup_feature_directory()` still violates. | Low | High (broken `main`) | C-007 enforces strict sequencing; orchestrator runs WPs in dependency order; branch protection on `main` requires the tracking issue checkboxes to advance in order. |
| `src/specify_cli/charter/` duplicate has a live reader that WP2.3 misses because the audit focused on `src/charter/`. | Medium | Medium (silent bypass) | WP2.3 occurrence classification explicitly includes both package trees; the AST-walk test (FR-011) walks the full `src/` tree, not a single package. |
| The new bundle manifest (FR-001) disagrees with the existing `.gitignore` entries on tracked-vs-derived for a specific file, and the migration's `.gitignore` reconciliation has unintended behavior. | Low | Medium | WP2.4's migration explicitly diffs the current `.gitignore` against the manifest's required entries and prints the diff in the JSON report; operators can review before committing. |
| `resolve_canonical_repo_root()` is invoked from a path that is not inside any git repository (e.g., during test setup). | Medium | Low (test-only error) | The resolver raises a structured `NotInsideRepository` error; callers distinguish this from operational failure. Test fixtures always operate inside a fixture repo. |

---

## Likely File Clusters

For plan-phase sizing. Paths are relative to repo root.

**Bundle manifest (WP2.1)**
- `src/charter/bundle.py` (new — `CharterBundleManifest` Pydantic model)
- `architecture/2.x/<new-file>.md` (new — unified bundle contract doc)
- `tests/charter/test_bundle_manifest_model.py` (new — manifest unit tests)

**Chokepoint + canonical-root resolver (WP2.2)**
- `src/charter/sync.py` (modify — `ensure_charter_bundle_fresh()` resolves canonical root, consults manifest)
- `src/charter/resolution.py` (new, or added into `sync.py` — `resolve_canonical_repo_root()`)
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
- `src/specify_cli/charter/context.py` and `src/specify_cli/charter/sync.py` (modify in lockstep per C-003 if they carry live readers)
- `src/specify_cli/core/worktree.py` (modify — lines 483-532 removed; no-symlink-no-copy for charter paths)
- `tests/init/test_fresh_clone_no_sync.py` (new)
- `tests/core/test_worktree_no_charter_materialization.py` (new)
- `tests/charter/test_chokepoint_coverage.py` (new — AST walk)
- `tests/test_dashboard/test_charter_chokepoint_regression.py` (new)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` (new — golden capture)

**Migration (WP2.4)**
- `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` (new)
- `src/specify_cli/upgrade/migrations/__init__.py` (modify if explicit registration is required; auto-discovery may suffice)
- `tests/upgrade/test_unified_bundle_migration.py` (new — FR-013 fixture matrix)
- `tests/upgrade/fixtures/unified_bundle/` (new fixture tree for pre-Phase-2 projects with legacy symlinks)

**Occurrence artifacts (every WP)**
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.1.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.2.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.3.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.4.yaml`
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml`

**Changelog**
- `CHANGELOG.md` (modify — entry per Success Criterion 11)
