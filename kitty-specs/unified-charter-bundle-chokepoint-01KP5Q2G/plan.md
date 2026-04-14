# Implementation Plan: Unified Charter Bundle and Read Chokepoint

**Mission ID**: `01KP5Q2G4Z39ZVRX2FY3NWXZQW` (`mid8`: `01KP5Q2G`)
**Mission slug**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Branch**: `main` (planning base = merge target = `main`)
**Date**: 2026-04-14 (design-review corrections 2026-04-14)
**Spec**: [spec.md](spec.md)
**Tracking issue**: [Priivacy-ai/spec-kitty#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)
**Parent EPIC**: [Priivacy-ai/spec-kitty#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**WP tracking issues**: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478) (WP2.1), [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480) (WP2.2), [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481) (WP2.3), [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479) (WP2.4)

---

## Summary

Deliver Phase 2 of [EPIC #461](https://github.com/Priivacy-ai/spec-kitty/issues/461) as four strictly sequential work packages that close [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)'s four acceptance gates:

1. **WP2.1** introduces the typed bundle manifest (`CharterBundleManifest` at `src/charter/bundle.py`) scoped to the three files `src/charter/sync.py` materializes (`governance.yaml`, `directives.yaml`, `metadata.yaml`), adds the `spec-kitty charter bundle validate [--json]` CLI, and publishes the architecture §6 bundle contract doc.
2. **WP2.2** adds the canonical-root resolver at `src/charter/resolution.py` (per user Q1=A) using `git rev-parse --git-common-dir` — **with correct stdout interpretation** (relative-to-cwd vs. absolute; file-input normalization; `.git/`-interior detection) per the algorithm in `contracts/canonical-root-resolver.contract.md`. Extends `SyncResult` with `canonical_root: Path` (per user Q2=C). Re-plumbs `ensure_charter_bundle_fresh()` to consult the manifest and the resolver as its two authoritative inputs.
3. **WP2.3** cuts every FR-004 reader over to the chokepoint (AST-walk-verified) and captures the pre-cutover dashboard-typed-contracts baseline **before** any reader is rewired. The worktree setup code (`src/specify_cli/core/worktree.py:478-532`) is **not touched** — those `.kittify/memory/` and `.kittify/AGENTS.md` symlinks are documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179` and are unrelated to the charter bundle. Canonical-root resolution (from WP2.2) is what lets worktree readers transparently see the main-checkout bundle.
4. **WP2.4** lands migration `m_3_2_3_unified_bundle.py` (next free slot per user Q2=A / spec C-008) scoped to: validate the bundle against the manifest, invoke the chokepoint to ensure derivatives are present, emit a structured JSON report. **No worktree scanning; no symlink removal; no `.gitignore` reconciliation** (v1.0.0 manifest matches current `.gitignore` verbatim, and the `.kittify/memory/` / `.kittify/AGENTS.md` symlinks are C-011 out-of-scope).

The technical approach is the same [#393 occurrence-classification pattern](https://github.com/Priivacy-ai/spec-kitty/issues/393) used for Phase 1. Package deduplication of `src/charter/` vs. `src/specify_cli/charter/` is explicitly deferred to a follow-up tranche (spec C-003); WP2.3 keeps the duplicate package in sync only where a live reader remains.

**Scope deltas vs. the original plan (design-review 2026-04-14)**:

- Gate 2 reframed from "worktree has no charter symlink/copy" to "worktree reader transparently reads main-checkout bundle via canonical-root resolution". Worktree code untouched.
- Manifest v1.0.0 narrowed to the three `sync()`-produced files; `references.yaml` and `context-state.json` explicitly out of v1.0.0 scope (spec C-012).
- Resolver algorithm corrected to account for `git rev-parse --git-common-dir` actual stdout behavior (relative-to-cwd or absolute; `.git/`-interior edge case).
- Migration scope narrowed: no worktree scanning, no symlink removal, no gitignore reconciliation.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement).
**Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, `pydantic`, `pytest`, `mypy --strict` (unchanged — no new runtime deps).
**Storage**: Filesystem only. The unified bundle lives under `.kittify/charter/` (unchanged location; layout now contractual for v1.0.0 manifest files). Derived files remain gitignored per the manifest's `gitignore_required_entries`. Canonical-root resolution uses `git rev-parse --git-common-dir` — a git plumbing invocation via `subprocess`, cached per working directory.
**Testing**: `pytest` with ≥90% coverage on changed code per charter; `mypy --strict` must pass. New test modules under `tests/charter/`, `tests/init/`, `tests/test_dashboard/`, `tests/upgrade/`.
**Target Platform**: `spec-kitty-cli` Python package distributed via PyPI. Must remain correct on macOS / Linux / Windows-WSL. No fallback per C-001.
**Project Type**: Single project (refactor + additions inside `src/charter/`, `src/specify_cli/dashboard/`, `src/specify_cli/cli/commands/`, `src/specify_cli/upgrade/migrations/`, and related test paths). **`src/specify_cli/core/worktree.py` is NOT touched.**
**Performance Goals**: Pytest runtime regression ≤5% (NFR-001). Chokepoint warm overhead <10 ms p95 (NFR-002). Resolver <5 ms p95 with ≤1 git invocation per call (NFR-003). Migration ≤2 s on the FR-013 reference fixture (NFR-006).
**Constraints**: No fallback / no backwards compatibility / no shim (C-001). `#393` guardrail per WP (C-002). Package dedup out of scope (C-003). Phase 0 / Phase 1 untouchable (C-005). SOURCE-only template edits (C-006). Strict WP sequencing (C-007). Migration filename `m_3_2_3_unified_bundle.py` (C-008). `git rev-parse --git-common-dir` mandated with correct-algorithm clause (C-009). `#361` regression safety net (C-010). **`src/specify_cli/core/worktree.py:478-532` out of scope (C-011)**. **v1.0.0 manifest scope limited to `sync()`-produced files (C-012)**.
**Scale/Scope**: ~350 LOC net addition (bundle module + resolver module + CLI subcommand + migration + contract docs + tests). **~0 LOC deletion** (worktree block stays). ~8 reader sites flipped in WP2.3 across both `src/charter/` and `src/specify_cli/charter/`. 5+ new test modules; 1 golden baseline JSON committed in-mission.

---

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Charter file**: `/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/.kittify/charter/charter.md` exists.

**Governance file**: not on disk; bootstrap emits `governance.yaml not found. Run 'spec-kitty charter sync'`. **Informational, not a gate violation** — Phase 2 makes that warning self-repair via chokepoint auto-refresh.

**Charter-derived policy applied to this mission**:

| Policy | Applies? | How honored |
| --- | --- | --- |
| `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy --strict` | Yes | No new runtime deps introduced. New `spec-kitty charter bundle validate` uses `typer`. Bundle manifest uses Pydantic. |
| ≥90% test coverage on new code (NFR-004) | Yes | Every new module (`bundle.py`, `resolution.py`, `m_3_2_3_unified_bundle.py`) and every new test module measured in CI coverage gate. |
| `mypy --strict` passes (NFR-004) | Yes | Every WP PR blocks on mypy-strict in CI. |
| Integration tests for CLI commands | Yes | WP2.1 integration test for `bundle validate`; WP2.3 fresh-clone + worktree integration tests; WP2.4 migration integration test against the FR-013 matrix. |
| CLI ops <2 s for typical projects | Yes | NFR-006 binds migration ≤2 s. NFR-002 binds chokepoint overhead <10 ms. |
| Dashboard supports 100+ WPs without lag | Yes | NFR-002's warm-overhead budget explicitly targets the dashboard scanner hot loop. |

**DIRECTIVE_003 (Decision Documentation)**: Every plan-phase decision is recorded in "Plan-Phase Decisions (locked)" below and in the contract files. Design-review corrections 2026-04-14 added C-011, C-012 and reframed Goals / Non-Goals / WP scope.

**DIRECTIVE_010 (Specification Fidelity)**: Plan-phase refinements are recorded here. Design-review corrections are recorded in spec.md, data-model.md, research.md, contracts/ (all updated 2026-04-14).

**Gate status**: PASS both pre-research and post-design. No violations.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── bundle-manifest.schema.yaml             # CharterBundleManifest v1.0.0 (JSON Schema)
│   ├── chokepoint.contract.md                  # ensure_charter_bundle_fresh + SyncResult extension
│   ├── canonical-root-resolver.contract.md     # resolve_canonical_repo_root (with precise algorithm)
│   ├── migration-report.schema.json            # m_3_2_3 JSON output shape
│   ├── bundle-validate-cli.contract.md         # spec-kitty charter bundle validate
│   └── occurrence-artifact.schema.yaml         # per-WP #393 artifact shape (reused)
├── baseline/                                   # created at top of WP2.3
│   ├── capture.py                              # commits alongside golden baseline
│   └── pre-wp23-dashboard-typed.json           # FR-014 golden capture
├── occurrences/                                # created across WPs + implementation
│   ├── index.yaml                              # mission-level aggregate
│   ├── WP2.1.yaml
│   ├── WP2.2.yaml
│   ├── WP2.3.yaml
│   └── WP2.4.yaml
├── checklists/
│   └── requirements.md
├── research/                                   # (empty placeholder)
├── tasks/                                      # /spec-kitty.tasks output
├── meta.json
├── status.events.jsonl
└── tasks.md                                    # /spec-kitty.tasks output
```

### Source code (repository root)

```
src/
├── charter/                                    # canonical package (C-003)
│   ├── __init__.py                             # WP2.1: re-export CharterBundleManifest
│   ├── bundle.py                               # NEW (WP2.1) — CharterBundleManifest + SCHEMA_VERSION = "1.0.0" + CANONICAL_MANIFEST (3 derived files)
│   ├── resolution.py                           # NEW (WP2.2) — resolve_canonical_repo_root() per Q1=A + NotInsideRepositoryError + GitCommonDirUnavailableError
│   ├── sync.py                                 # WP2.2: SyncResult += canonical_root: Path (Q2=C); ensure_charter_bundle_fresh() calls resolution + manifest
│   ├── context.py                              # WP2.3: build_charter_context() routes through chokepoint; lines 385-398 (context-state.json writes) untouched (C-012 carve-out)
│   ├── compiler.py                             # UNTOUCHED (C-012 — compiler pipeline owns references.yaml)
│   ├── resolver.py                             # UNTOUCHED unless occurrence classification surfaces a bypass
│   └── (other modules)                         # reviewed in occurrence classification; edited only if they bypass chokepoint
├── specify_cli/
│   ├── charter/                                # CLI-facing duplicate; C-003 lockstep
│   │   ├── context.py                          # WP2.3: lockstep if still a live reader site
│   │   ├── sync.py                             # WP2.3: lockstep if still a live reader site
│   │   └── (others)                            # untouched unless occurrence classification surfaces a bypass
│   ├── cli/
│   │   └── commands/
│   │       └── charter.py                      # WP2.1: add `bundle validate` subcommand (Q4=B); WP2.3: handler call-sites flip
│   ├── core/
│   │   └── worktree.py                         # UNTOUCHED (C-011 carve-out — memory/AGENTS sharing is documented-intentional)
│   ├── dashboard/
│   │   ├── charter_path.py                     # WP2.3: route through chokepoint; preserve #361 typed contract (C-010)
│   │   ├── scanner.py                          # WP2.3: charter-presence probes route through chokepoint
│   │   └── server.py                           # WP2.3: charter endpoints route through chokepoint
│   ├── next/
│   │   └── prompt_builder.py                   # WP2.3: charter injection via chokepoint
│   ├── cli/commands/agent/
│   │   └── workflow.py                         # WP2.3: charter injection via chokepoint
│   └── upgrade/migrations/
│       └── m_3_2_3_unified_bundle.py           # NEW (WP2.4) — migration class (C-008)

architecture/
└── 2.x/
    └── 06_unified_charter_bundle.md            # NEW (WP2.1) — architecture §6 bundle contract doc (FR-002)

tests/
├── charter/
│   ├── test_bundle_manifest_model.py           # NEW (WP2.1)
│   ├── test_canonical_root_resolution.py       # NEW (WP2.2)
│   ├── test_chokepoint_overhead.py             # NEW (WP2.2) — NFR-002 benchmarks
│   ├── test_resolution_overhead.py             # NEW (WP2.2) — NFR-003 benchmarks
│   ├── test_chokepoint_coverage.py             # NEW (WP2.3) — AST-walk proof
│   ├── test_bundle_contract.py                 # NEW (WP2.3) — manifest-vs-disk assertion
│   └── test_worktree_charter_via_canonical_root.py   # NEW (WP2.3) — worktree reader transparency
├── init/
│   └── test_fresh_clone_no_sync.py             # NEW (WP2.3)
├── test_dashboard/
│   └── test_charter_chokepoint_regression.py   # NEW (WP2.3) — byte-identical (with redactions) against pre-WP2.3 baseline
└── upgrade/
    └── test_unified_bundle_migration.py        # NEW (WP2.4) — FR-013 fixture matrix

scripts/
└── verify_occurrences.py                       # reused from Phase 1
```

**Structure Decision**: Single-project Python layout. All source changes land in existing `src/` subtrees; two new modules (`src/charter/bundle.py`, `src/charter/resolution.py`) and one new migration. One new architecture doc. Twin charter packages stay separate (C-003). **Worktree code untouched (C-011). Compiler + context-state.json writes untouched (C-012).**

---

## Plan-Phase Decisions (locked)

### D-1 — Bundle manifest module location (WP2.1)
**Decision**: `CharterBundleManifest` lives at `src/charter/bundle.py`. The module exports `CharterBundleManifest` (Pydantic model), `SCHEMA_VERSION = "1.0.0"` (per user Q3=A), and `CANONICAL_MANIFEST` (the single shipped v1.0.0 manifest: three derived files). `src/charter/__init__.py` re-exports `CharterBundleManifest`.

**Rationale**: Matches the canonical package choice in spec C-003. Keeps the manifest side-by-side with `sync.py` and `resolution.py`.

**Artifact**: [`contracts/bundle-manifest.schema.yaml`](contracts/bundle-manifest.schema.yaml).

### D-2 — Canonical-root resolver module location (WP2.2) — Q1=A
**Decision**: `resolve_canonical_repo_root()` lives at `src/charter/resolution.py` (new module). Exports `NotInsideRepositoryError`, `GitCommonDirUnavailableError`. LRU cache keyed by absolute invocation path.

**Implementation discipline** (per C-009; **corrected 2026-04-14**): the resolver implements the exact algorithm in [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md):
1. Normalize file inputs to parent directory.
2. `subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=<directory>, ...)` — one invocation per cold call.
3. Classify exit code: non-zero with "not a git repository" → `NotInsideRepositoryError`; other non-zero → `GitCommonDirUnavailableError`.
4. Parse stdout: strip; if relative, resolve via `(cwd / stdout).resolve()`; if absolute, use as-is.
5. Explicit `.git/`-interior detection: if resolved input path is the common_dir or a descendant, raise `NotInsideRepositoryError`.
6. Return `common_dir.parent`.

**Rationale**: User-affirmed in Q1=A. The corrected algorithm handles real `git rev-parse --git-common-dir` behavior: stdout is relative to `cwd` unless the git dir is physically absolute (linked worktree case). The original contract's "return the working directory" shortcut was wrong and would have mis-resolved subdirectory invocations.

**Artifact**: [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md).

### D-3 — `SyncResult` extension (WP2.2) — Q2=C
**Decision**: `SyncResult` gains one new field: `canonical_root: Path`. `files_written` continues to be a list of paths **relative to `canonical_root`**. No existing field is renamed or retyped.

**Rationale**: User-affirmed in Q2=C. Preserves explicit path semantics when a caller invokes the chokepoint from a worktree.

**Artifact**: [`contracts/chokepoint.contract.md`](contracts/chokepoint.contract.md).

### D-4 — Bundle CLI surface (WP2.1) — Q4=B
**Decision**: Add `spec-kitty charter bundle validate [--json]` as a new Typer subcommand. Thin wrapper; no `doctor` integration in this tranche.

**Artifact**: [`contracts/bundle-validate-cli.contract.md`](contracts/bundle-validate-cli.contract.md).

### D-5 — Twin-package lockstep (C-003)
**Decision**: Every WP2.3 edit that touches a reader in `src/charter/` is mirrored in `src/specify_cli/charter/` **only if the duplicate file still contains a live direct-read path**. Occurrence artifact lists both files separately; AST-walk test walks the full `src/` tree.

### D-6 — Dashboard typed-contract baseline is WP2.3 step 1 (C-010 / FR-014)
**Decision**: Before any reader is rewired in WP2.3, capture the pre-WP2.3 dashboard typed contracts as a committed golden JSON at `kitty-specs/.../baseline/pre-wp23-dashboard-typed.json` via a committed capture script at `baseline/capture.py`.

### D-7 — Occurrence-classification artifact shape (C-002 / FR-015)
**Decision**: Identical pattern to Phase 1. Per-WP YAML artifacts + mission-level aggregate. Schema reused from Phase 1. Verifier script `scripts/verify_occurrences.py` reused as-is.

### D-8 — Charter Check note
**Decision**: Informational only. Governance-file absence does not block Phase 2 and is in-scope for self-repair via chokepoint auto-sync-on-first-read.

### D-9 — Strict sequencing (C-007)
**Decision**: WP2.1 → WP2.2 → WP2.3 → WP2.4. Parallelization rejected.

### D-10 — Research scope
**Decision**: Four narrow Phase 0 investigations captured in `research.md`:

- **R-1** — exhaustive reader-site inventory across both `src/charter/` and `src/specify_cli/charter/`, plus `src/specify_cli/dashboard/`, `src/specify_cli/cli/commands/`, `src/specify_cli/next/`. **Scope narrowed 2026-04-14** to v1.0.0 manifest files only.
- **R-2** — `git rev-parse --git-common-dir` behavior matrix. **Corrected 2026-04-14** to record actual stdout shapes (relative-to-cwd vs absolute; `.` from inside `.git/`).
- **R-3** — `SyncResult` caller audit.
- **R-4** — dashboard typed-contract surface inventory.

### D-11 — Phase 1 artifacts
**Decision**: Produced together with this plan — `research.md`, `data-model.md`, `quickstart.md`, and the five contract files under `contracts/` (six if we count the re-published occurrence-artifact schema).

### D-12 — `.gitignore` policy for the bundle
**Decision**: The v1.0.0 manifest's `gitignore_required_entries` is a MUST-INCLUDE set (not "only these"). Current `.gitignore:18-22` already covers the three required entries plus two additional entries for out-of-v1.0.0-scope files (`context-state.json`, `references.yaml`). The migration performs **no `.gitignore` reconciliation** — it's a no-op on first apply.

### D-13 — Out-of-v1.0.0-scope files (C-012) — **added 2026-04-14 from design review**
**Decision**: `references.yaml` (produced by `src/charter/compiler.py:169-196`) and `context-state.json` (written by `src/charter/context.py:385-398`) are **explicitly out of v1.0.0 manifest scope**. The chokepoint does not validate, regenerate, or take ownership of those files. Readers of those files go through their own pipelines. Expanding scope to cover them requires a new manifest schema version (e.g., 1.1.0 or 2.0.0) and its own migration.

**Rationale**: The original plan's manifest declared those files as `derived_files` with `sync()` as the derivation source — which is factually wrong on `main` (sync only writes three files per `src/charter/sync.py:32-36`). Rather than expand the chokepoint to also invoke the compiler pipeline and the context-state writer, v1.0.0 limits scope to what `sync()` owns. This keeps the chokepoint semantics clean and defers the larger scoping decision to a later tranche.

### D-14 — Worktree code is out of scope (C-011) — **added 2026-04-14 from design review**
**Decision**: `src/specify_cli/core/worktree.py:478-532` — the `.kittify/memory/` and `.kittify/AGENTS.md` symlink/copy block — is **not touched** by this mission. Those symlinks are documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179` and solve a separate concern (project memory and agent-instructions sharing), not the charter bundle. The worktree-charter-visibility problem described in `#339` is solved by canonical-root resolution in WP2.2, not by touching this file.

**Rationale**: The original plan's WP2.3 Step F proposed deleting lines 478-532 on the theory that they were "charter materialization". Verification against live code showed those lines materialize `.kittify/memory/` and `.kittify/AGENTS.md`, NOT `.kittify/charter/`. Removing them would break documented operator behavior and would not address the gate-2 concern (which is about charter visibility in worktrees, solved by canonical-root resolution).

---

## Work Package Shape (recommended for `/spec-kitty.tasks`)

Four strictly sequential WPs. Each WP PR includes: source edits, test edits, its occurrence artifact, and a verifier-green CI run.

### WP2.1 — Unified bundle manifest + architecture doc + bundle CLI (tracks [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478))

**Scope**:
- Add `src/charter/bundle.py` with `CharterBundleManifest` (Pydantic model), `SCHEMA_VERSION = "1.0.0"`, `CANONICAL_MANIFEST`. Three derived files per v1.0.0 scope: `governance.yaml`, `directives.yaml`, `metadata.yaml`.
- Add `architecture/2.x/06_unified_charter_bundle.md` documenting the bundle contract, v1.0.0 scope, canonical-root contract, staleness semantics, gitignore policy, and explicit out-of-scope note for `references.yaml` / `context-state.json`.
- Add `spec-kitty charter bundle validate [--json]` Typer subcommand per [`contracts/bundle-validate-cli.contract.md`](contracts/bundle-validate-cli.contract.md). Warnings for out-of-v1.0.0-scope files.
- Re-export `CharterBundleManifest` from `src/charter/__init__.py`.
- Add `tests/charter/test_bundle_manifest_model.py`.
- Add integration test for `spec-kitty charter bundle validate`.
- Author `kitty-specs/.../occurrences/WP2.1.yaml` and seed `.../occurrences/index.yaml`.

**Acceptance gates for WP2.1 PR**:
- All tests green.
- Verifier green against WP2.1.yaml.
- `spec-kitty charter bundle validate --json` on the repo exits 0 and prints warnings for `references.yaml` / `context-state.json` as out-of-scope.
- `mypy --strict` passes.

### WP2.2 — Canonical-root resolver + chokepoint plumbing (tracks [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480))

**Depends on**: WP2.1 merged (chokepoint consults the manifest).

**Scope**:
- Add `src/charter/resolution.py` implementing the **corrected algorithm** per [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md) — file-input normalization; stdout parsed relative-to-cwd or absolute; explicit `.git/`-interior detection; LRU cache.
- Extend `SyncResult` in `src/charter/sync.py` with `canonical_root: Path` per D-3. Keep `files_written` relative to `canonical_root`.
- Re-plumb `ensure_charter_bundle_fresh()` to call `resolve_canonical_repo_root()` first, consult `CharterBundleManifest.CANONICAL_MANIFEST` (v1.0.0 completeness check — three files), then delegate to `sync()`.
- Update every existing `SyncResult` caller per R-3.
- Add `tests/charter/test_canonical_root_resolution.py` covering the R-2 fixture matrix (including the `.git/`-interior edge case).
- Add `tests/charter/test_chokepoint_overhead.py` (NFR-002).
- Add `tests/charter/test_resolution_overhead.py` (NFR-003).
- Author `kitty-specs/.../occurrences/WP2.2.yaml`.

**Acceptance gates for WP2.2 PR**:
- All tests green.
- Verifier green.
- Benchmark thresholds met.
- `mypy --strict` passes.
- WP2.1 gates still hold.

### WP2.3 — Reader cutover + dashboard regression proof (tracks [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481))

**Depends on**: WP2.2 merged.

**Scope** (step order matters):

**A. Baseline capture (must happen BEFORE any reader rewire)**:
- Run the committed capture script at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py` on pre-WP2.3 `main` (or `HEAD~` reference if edits unavoidable) to produce `baseline/pre-wp23-dashboard-typed.json`.

**B. Reader cutover** (canonical package `src/charter/`):
- Flip `src/charter/context.py :: build_charter_context()` (lines 406–661 today) to call `ensure_charter_bundle_fresh()` before direct reads of `charter.md` (~line 555). Paths resolved via `SyncResult.canonical_root`.
- Any other `src/charter/` reader surfaced by R-1 that still bypasses the chokepoint.
- **Do NOT touch `src/charter/context.py:385-398`** (context-state.json write path is C-012 out-of-scope carve-out).
- **Do NOT touch `src/charter/compiler.py:169-196`** (compiler pipeline is C-012 out-of-scope carve-out).

**C. Reader cutover** (CLI surfaces + agent/next prompt builders):
- `src/specify_cli/cli/commands/charter.py` — every handler that reads bundle artifacts before rendering output.
- `src/specify_cli/next/prompt_builder.py` — charter injection.
- `src/specify_cli/cli/commands/agent/workflow.py` — workflow charter injection.

**D. Reader cutover** (dashboard — safety-net cluster per C-010):
- `src/specify_cli/dashboard/charter_path.py :: resolve_project_charter_path()` (lines 8–17).
- `src/specify_cli/dashboard/scanner.py` charter-presence probes.
- `src/specify_cli/dashboard/server.py` charter endpoints.
- `#361` typed contracts remain byte-identical (with documented redactions) against the Step A baseline.

**E. Duplicate-package lockstep (C-003 / D-5)**:
- Any remaining live reader in `src/specify_cli/charter/` enumerated in the WP2.3 occurrence artifact is updated in the same PR. Pure re-export files are left untouched.

**F. Tests**:
- Add `tests/charter/test_chokepoint_coverage.py` — AST-walk over `src/` asserting every call site in the WP2.3 occurrence artifact's reader registry routes through `ensure_charter_bundle_fresh`. The registry is the test's source of truth.
- Add `tests/charter/test_bundle_contract.py` — loads `CharterBundleManifest`, materializes a bundle in tmpdir via the chokepoint, asserts layout compliance.
- Add `tests/init/test_fresh_clone_no_sync.py` (FR-009).
- Add `tests/charter/test_worktree_charter_via_canonical_root.py` (FR-010) — creates a worktree, invokes an FR-004 reader with `repo_root = worktree_path`, asserts `SyncResult.canonical_root` points at the main checkout, asserts no files written inside `<worktree>/.kittify/charter/`, asserts existing `.kittify/memory/` and `.kittify/AGENTS.md` symlinks (if present) are untouched.
- Add `tests/test_dashboard/test_charter_chokepoint_regression.py` (FR-014) — byte-identical (post-redaction) comparison against baseline.

**G. Occurrence artifact**:
- Author `kitty-specs/.../occurrences/WP2.3.yaml` covering categories A-H. **Must include explicit `leave` entries for**:
  - `src/specify_cli/core/worktree.py:478-532` (C-011 carve-out — memory/AGENTS sharing).
  - `src/charter/compiler.py:169-196` (C-012 carve-out — compiler pipeline).
  - `src/charter/context.py:385-398` (C-012 carve-out — context-state.json writes).
- Update `index.yaml` with the NFR-005 must-be-zero set.

**Acceptance gates for WP2.3 PR**:
- All tests green.
- Verifier green.
- `tests/charter/test_chokepoint_coverage.py` passes.
- `tests/test_dashboard/test_charter_chokepoint_regression.py` passes.
- `tests/charter/test_worktree_charter_via_canonical_root.py` passes.
- `grep -n "\.kittify/memory\|\.kittify/AGENTS\.md" src/specify_cli/core/worktree.py` matches pre-Phase-2 output exactly (C-011 carve-out verification per spec §Success Criterion 8).
- Grep invariants from spec FR-016 pass.
- Runtime within NFR-001.
- `mypy --strict` passes.

### WP2.4 — Migration `m_3_2_3_unified_bundle.py` (tracks [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479))

**Depends on**: WP2.3 merged.

**Scope**:
- Add `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py`. `target_version = "3.2.3"`. Follows `m_3_2_0_update_planning_templates.py:50-60` pattern.
- Behavior per [`contracts/migration-report.schema.json`](contracts/migration-report.schema.json) and spec FR-007:
  - (a) Detect whether `charter.md` exists at the canonical root.
  - (b) If yes, validate the bundle against `CharterBundleManifest` v1.0.0.
  - (c) Invoke the chokepoint to regenerate any missing derivatives.
  - (d) Emit structured JSON report.
  - **Explicitly does NOT**: scan worktrees, remove symlinks, reconcile `.gitignore`. v1.0.0 manifest matches current `.gitignore`; worktree symlinks are C-011 out-of-scope.
- Idempotent: second apply is a no-op (`applied: false`).
- Update issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) body in a tracking comment to reflect `m_3_2_3_unified_bundle.py` filename (C-008), the design-review scope corrections, and the v1.0.0 manifest narrowing.
- Add `tests/upgrade/test_unified_bundle_migration.py` — FR-013 fixture matrix (five fixtures).
- Add `CHANGELOG.md` entry per spec §Success Criterion 11, explicitly noting: unified bundle manifest v1.0.0; canonical-root-resolution behavior for worktree readers; `m_3_2_3_unified_bundle.py` upgrade path; absence of compat shim; **explicit note that `.kittify/memory/` and `.kittify/AGENTS.md` symlinks are unchanged**.
- Author `kitty-specs/.../occurrences/WP2.4.yaml` and finalize `index.yaml`.

**Acceptance gates for WP2.4 PR**:
- All tests green.
- Verifier green against WP2.4.yaml and mission-level `index.yaml`.
- Migration registry discovers `m_3_2_3_unified_bundle` at boot.
- `spec-kitty upgrade` on the FR-013 reference fixture completes in ≤2 s.
- `mypy --strict` passes.
- All previous WP gates still hold.

---

## Risk & Mitigation Plan (operational)

Cross-reference spec §Risks. Operational mitigations below are the plan-level elaboration.

| Spec risk | Plan-phase mitigation |
| --- | --- |
| A reader site is missed in WP2.3 occurrence classification | R-1 is exhaustive Phase 0 investigation using static grep + Python AST walk + string-literal sweep. `tests/charter/test_chokepoint_coverage.py` is the completeness proof. |
| `git rev-parse --git-common-dir` misbehaves under submodule/sparse/detached-HEAD/linked-worktree | R-2 produces the edge-case matrix that becomes `tests/charter/test_canonical_root_resolution.py`'s fixture set. **Corrected algorithm** in `contracts/canonical-root-resolver.contract.md` handles relative-vs-absolute stdout and `.git/`-interior detection explicitly. |
| A developer edits `src/specify_cli/core/worktree.py:478-532` during this mission's work | C-011 pins this block. WP2.3 occurrence artifact lists lines 478-532 as `leave`. Success Criterion 8 verifies the lines are unchanged at merge. |
| Migration fails idempotency | FR-013 fixture matrix exercises double-apply. Migration is stateless and re-entrant. |
| Dashboard golden baseline captures non-deterministic fields | R-4 redaction contract; capture script committed alongside baseline. |
| NFR-002 warm overhead breached | WP2.2 mtime short-circuit in the chokepoint's completeness check. |
| WP PR lands out of order | C-007; occurrence artifact's `requires_merged` field. |
| Live reader in `src/specify_cli/charter/` missed | AST-walk test walks full `src/` tree. |
| Manifest disagrees with `.gitignore` | D-12: v1.0.0 manifest matches current `.gitignore`. |
| `resolve_canonical_repo_root` invoked outside a git repo | Raises `NotInsideRepositoryError`; test fixtures always operate inside a fixture repo. |
| Reader in `src/charter/compiler.py` or `src/charter/context.py:385-398` is accidentally rewired | C-012 pins these as out-of-v1.0.0-scope carve-outs. WP2.3 occurrence artifact lists them explicitly as `leave`. |

---

## Complexity Tracking

No Charter Check violations. Two new modules added (`src/charter/bundle.py`, `src/charter/resolution.py`) and one new migration; each is a single well-scoped concern matching the spec FR directly. The new `spec-kitty charter bundle validate` subcommand is a thin Typer wrapper — no architectural complexity added. Scope corrections removed unnecessary worktree-editing and migration-scanning work.

---

## Branch Contract (restated, pass 2/2)

- Current branch at plan start: `main`
- Planning/base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true`

All four WP PRs open against `main` and merge back to `main`.

---

## Next Step

User runs `/spec-kitty.tasks --mission unified-charter-bundle-chokepoint-01KP5Q2G` to materialize the four WPs listed above into `tasks.md` and per-WP task files under `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/tasks/`.
