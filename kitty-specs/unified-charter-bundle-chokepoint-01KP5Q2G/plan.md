# Implementation Plan: Unified Charter Bundle and Read Chokepoint

**Mission ID**: `01KP5Q2G4Z39ZVRX2FY3NWXZQW` (`mid8`: `01KP5Q2G`)
**Mission slug**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Branch**: `main` (planning base = merge target = `main`)
**Date**: 2026-04-14
**Spec**: [spec.md](spec.md)
**Tracking issue**: [Priivacy-ai/spec-kitty#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)
**Parent EPIC**: [Priivacy-ai/spec-kitty#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**WP tracking issues**: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478) (WP2.1), [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480) (WP2.2), [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481) (WP2.3), [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479) (WP2.4)

---

## Summary

Deliver Phase 2 of [EPIC #461](https://github.com/Priivacy-ai/spec-kitty/issues/461) as four strictly sequential work packages that close [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)'s four acceptance gates:

1. **WP2.1** introduces the typed bundle manifest (`CharterBundleManifest` at `src/charter/bundle.py`), a new CLI surface `spec-kitty charter bundle validate [--json]`, and the architecture §6 bundle contract doc.
2. **WP2.2** adds the canonical-root resolver at `src/charter/resolution.py` (per user Q1=A) using `git rev-parse --git-common-dir`, extends `SyncResult` with a new `canonical_root: Path` field and keeps `files_written` relative to that root (per user Q2=C), and re-plumbs `ensure_charter_bundle_fresh()` to consult the manifest and the resolver as its two authoritative inputs.
3. **WP2.3** cuts every charter-derivative reader over to the chokepoint (AST-walk-verified), removes lines 483–532 of `src/specify_cli/core/worktree.py` so worktrees no longer symlink or copy charter state, and captures the pre-cutover dashboard-typed-contracts baseline at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` **before** any reader is rewired.
4. **WP2.4** lands migration `m_3_2_3_unified_bundle.py` (next free slot per user Q2=A / spec C-008) that scans every open worktree for legacy charter symlinks/copies, removes them, validates the bundle manifest, re-runs the chokepoint for missing derivatives, reconciles `.gitignore`, and emits a structured JSON report.

The technical approach is the same [#393 occurrence-classification pattern](https://github.com/Priivacy-ai/spec-kitty/issues/393) used for Phase 1: every WP ships its own artifact under `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml`, a mission-level `index.yaml` aggregates the "must-be-zero" set, and a verifier script (reused from Phase 1) enforces verification-by-completeness. Package deduplication of `src/charter/` vs. `src/specify_cli/charter/` is explicitly deferred to a follow-up tranche (spec C-003); the WP2.3 occurrence artifact keeps both trees in sync wherever a live reader remains in the duplicate.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement).
**Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, `pydantic`, `pytest`, `mypy --strict` (unchanged — no new runtime deps).
**Storage**: Filesystem only. The unified bundle lives under `.kittify/charter/` (unchanged location; layout now contractual). Derived files remain gitignored per the manifest's `gitignore_required_entries`. Canonical-root resolution uses `git rev-parse --git-common-dir` — a git plumbing invocation via `subprocess`, cached per working directory.
**Testing**: `pytest` with ≥90% coverage on changed code per charter; `mypy --strict` must pass. New test modules under `tests/charter/`, `tests/core/`, `tests/init/`, `tests/test_dashboard/`, `tests/upgrade/`.
**Target Platform**: The `spec-kitty-cli` Python package distributed via PyPI. Must remain correct on macOS / Linux / Windows-WSL (C-009's `git rev-parse` requirement is universal on supported platforms; no fallback per C-001).
**Project Type**: Single project (pure refactor and additions inside `src/charter/`, `src/specify_cli/core/`, `src/specify_cli/dashboard/`, `src/specify_cli/cli/commands/`, `src/specify_cli/upgrade/migrations/`, and related test paths).
**Performance Goals**: Do not regress pytest runtime more than 5% (NFR-001). Chokepoint warm overhead <10 ms p95 (NFR-002). Resolver <5 ms p95 with ≤1 git invocation per call (NFR-003). Migration completes in <2 s on the FR-013 reference fixture (NFR-006).
**Constraints**: No fallback / no backwards compatibility / no shim (C-001). `#393` occurrence-classification guardrail mandatory per WP (C-002). Package dedup out of scope; lockstep-only updates to `src/specify_cli/charter/` (C-003). Phase 0 / Phase 1 baselines are untouchable (C-005). SOURCE-only template edits (C-006). Strict WP sequencing WP2.1 → WP2.2 → WP2.3 → WP2.4 (C-007). Migration filename is `m_3_2_3_unified_bundle.py` (C-008; spec deviates from the issue-text literal because slots 3.2.0 / 3.2.1 / 3.2.2 are taken on `main`). `git rev-parse --git-common-dir` is mandated (C-009). `#361` dashboard typed contracts are the regression safety net (C-010).
**Scale/Scope**: ~400 LOC net addition (new bundle module + resolver module + CLI subcommand + migration + contract docs + tests) and ~60 LOC net deletion (worktree charter symlink block at `src/specify_cli/core/worktree.py:483–532`). ~8 reader sites flipped in WP2.3 across both `src/charter/` and `src/specify_cli/charter/`. 5+ new test modules; 1 golden baseline JSON committed in-mission.

---

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Charter file**: `/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/.kittify/charter/charter.md` exists.

**Governance file**: `/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/.kittify/charter/governance.yaml` is not on disk today; the bootstrap `spec-kitty charter context --action plan --json` emits `governance.yaml not found. Run 'spec-kitty charter sync'`. This is **informational, not a gate violation** — Phase 2 does not require `governance.yaml` to exist at plan time, and the whole point of this mission is to make that file be generated on first read by the chokepoint. The chokepoint-refresh-on-first-read behavior is itself an **in-flight repair** of the phenomenon causing the warning.

**Charter-derived policy applied to this mission**:

| Policy | Applies? | How honored |
| --- | --- | --- |
| `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy --strict` (charter §Technical Standards) | Yes | No new runtime deps introduced. New `spec-kitty charter bundle validate` subcommand uses `typer`. Bundle manifest uses Pydantic (already in tree). |
| ≥90% test coverage on new code (NFR-004) | Yes | Every new module (`bundle.py`, `resolution.py`, `m_3_2_3_unified_bundle.py`) and every new test module measured in CI coverage gate. |
| `mypy --strict` passes (NFR-004) | Yes | Every WP PR blocks on mypy-strict in CI. |
| Integration tests for CLI commands (charter §Testing Requirements) | Yes | WP2.1 includes an integration test for `spec-kitty charter bundle validate` against a live fixture; WP2.3 includes a fresh-clone integration test and a worktree-setup integration test; WP2.4 includes a migration integration test against the FR-013 fixture matrix. |
| CLI ops <2 s for typical projects (charter §Performance and Scale) | Yes | NFR-006 binds the migration's wall time to ≤2 s on the FR-013 reference fixture. NFR-002 binds the chokepoint warm overhead to <10 ms. |
| Dashboard supports 100+ WPs without lag (charter §Performance and Scale) | Yes | NFR-002's warm-overhead budget explicitly targets the dashboard scanner's per-frame charter-read path as the hot loop. |

**DIRECTIVE_003 (Decision Documentation)**: Every plan-phase decision is recorded in this plan.md (see "Plan-Phase Decisions (locked)" below) and in the contract files under `contracts/`. No decisions are deferred to implementation silently.

**DIRECTIVE_010 (Specification Fidelity)**: Any deviation from `spec.md` during implementation is logged in `spec.md` as an amendment and re-reviewed before merge. Plan-phase refinements below (D-2 resolver module location, D-3 `SyncResult` `canonical_root` field) are recorded explicitly here.

**Gate status**: PASS. No violations. Governance-file absence is informational and in-scope to self-heal.

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
│   ├── bundle-manifest.schema.yaml             # CharterBundleManifest (JSON Schema)
│   ├── chokepoint.contract.md                  # ensure_charter_bundle_fresh + SyncResult extension
│   ├── canonical-root-resolver.contract.md     # resolve_canonical_repo_root (Q1=A / C-009)
│   ├── migration-report.schema.json            # m_3_2_3 JSON output shape (FR-007)
│   ├── bundle-validate-cli.contract.md         # spec-kitty charter bundle validate (Q4=B)
│   └── occurrence-artifact.schema.yaml         # per-WP #393 artifact shape (reused)
├── baseline/                                   # created at the top of WP2.3
│   └── pre-wp23-dashboard-typed.json           # FR-014 golden capture
├── occurrences/                                # created across WPs + implementation
│   ├── index.yaml                              # mission-level aggregate
│   ├── WP2.1.yaml
│   ├── WP2.2.yaml
│   ├── WP2.3.yaml
│   └── WP2.4.yaml
├── checklists/
│   └── requirements.md
├── research/                                   # (empty placeholder scaffolded by mission create)
├── tasks/                                      # /spec-kitty.tasks output
├── meta.json
├── status.events.jsonl
└── tasks.md                                    # /spec-kitty.tasks output
```

### Source code (repository root)

```
src/
├── charter/                                    # canonical package (C-003)
│   ├── __init__.py                             # WP2.1: re-export CharterBundleManifest; WP2.3: no change
│   ├── bundle.py                               # NEW (WP2.1) — CharterBundleManifest Pydantic model + SCHEMA_VERSION = "1.0.0"
│   ├── resolution.py                           # NEW (WP2.2) — resolve_canonical_repo_root() per Q1=A
│   ├── sync.py                                 # WP2.2: SyncResult += canonical_root: Path (Q2=C); ensure_charter_bundle_fresh() calls resolution + manifest
│   ├── context.py                              # WP2.3: build_charter_context() routes through chokepoint
│   ├── compiler.py                             # WP2.3: untouched unless occurrence classification surfaces a direct read
│   ├── resolver.py                             # WP2.3: untouched unless occurrence classification surfaces a direct read
│   ├── _drg_helpers.py                         # Phase 1 addition; untouched
│   └── (other modules)                         # reviewed in occurrence classification; edited only if they bypass chokepoint
├── specify_cli/
│   ├── charter/                                # CLI-facing duplicate; C-003 lockstep
│   │   ├── bundle.py                           # WP2.3 only if a live reader needs the manifest locally (likely re-export from src/charter)
│   │   ├── context.py                          # WP2.3: lockstep if still a live reader site
│   │   ├── sync.py                             # WP2.3: lockstep if still a live reader site
│   │   └── (others)                            # untouched unless occurrence classification surfaces a bypass
│   ├── cli/
│   │   └── commands/
│   │       └── charter.py                      # WP2.1: add `bundle validate` subcommand (Q4=B); WP2.3: handler call-sites flip
│   ├── core/
│   │   └── worktree.py                         # WP2.3: DELETE lines 483–532 (charter symlink/copy/exclude block)
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
│   └── test_bundle_contract.py                 # NEW (WP2.3) — manifest-vs-disk assertion
├── core/
│   └── test_worktree_no_charter_materialization.py  # NEW (WP2.3)
├── init/
│   └── test_fresh_clone_no_sync.py             # NEW (WP2.3)
├── test_dashboard/
│   └── test_charter_chokepoint_regression.py   # NEW (WP2.3) — byte-identical against pre-WP2.3 baseline
└── upgrade/
    └── test_unified_bundle_migration.py        # NEW (WP2.4) — FR-013 fixture matrix

scripts/
└── verify_occurrences.py                       # reused from Phase 1; no changes expected
```

**Structure Decision**: Single-project Python layout. All source changes land in existing `src/` subtrees; two new modules are added (`src/charter/bundle.py`, `src/charter/resolution.py`) and one new migration module (`src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py`). One new architecture doc under `architecture/2.x/`. No new top-level directories introduced. The twin charter packages stay separate (C-003).

---

## Plan-Phase Decisions (locked)

### D-1 — Bundle manifest module location (WP2.1)
**Decision**: `CharterBundleManifest` lives at `src/charter/bundle.py`. The module exports `CharterBundleManifest` (Pydantic model), `SCHEMA_VERSION = "1.0.0"` (per user Q3=A), and `CANONICAL_MANIFEST` (a module-level instance representing the single shipped manifest for the current schema version). `src/charter/__init__.py` re-exports `CharterBundleManifest` so downstream readers have one canonical import path.

**Rationale**: Matches the canonical package choice in spec C-003. Keeps the manifest side-by-side with `sync.py` (which consumes it) and the new `resolution.py` (which does not consume it but is thematically adjacent).

**Artifact**: [`contracts/bundle-manifest.schema.yaml`](contracts/bundle-manifest.schema.yaml) (JSON Schema draft-7) is committed as the external contract so non-Python consumers (e.g., the dashboard UI or external tooling) can validate the bundle without importing Python.

### D-2 — Canonical-root resolver module location (WP2.2) — Q1=A
**Decision**: `resolve_canonical_repo_root()` lives at `src/charter/resolution.py` (a new module). The module also exports `NotInsideRepositoryError` (raised when invoked outside any git repo) and `GitCommonDirUnavailableError` (raised when `git rev-parse --git-common-dir` fails for any reason that isn't "not a repo"). A module-level LRU cache keyed by the absolute path of the invocation directory caches the canonical-root resolution for the lifetime of the process.

**Rationale**: User-affirmed in Q1=A. Isolates git-plumbing concerns from sync/materialization logic, keeps `sync.py` focused on its existing extraction/staleness responsibilities, and makes unit-testing the resolver against synthetic repo fixtures straightforward.

**Implementation discipline** (per C-009): the resolver shells out once via `subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=path, capture_output=True, text=True, check=False)` and interprets non-zero exit codes as `NotInsideRepositoryError`. It does not re-implement git layout parsing; it does not read `.git/config`; it does not touch the filesystem beyond what `git rev-parse` itself touches.

**Artifact**: [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md).

### D-3 — `SyncResult` extension (WP2.2) — Q2=C
**Decision**: `SyncResult` gains one new field: `canonical_root: Path`. `files_written` continues to be a list of paths **relative to `canonical_root`**. No existing field is renamed or retyped.

**Rationale**: User-affirmed in Q2=C. Preserves explicit path semantics when a caller invokes the chokepoint from a worktree — callers can reconstruct absolute paths unambiguously (`canonical_root / p` for each `p in files_written`) and know at which root those paths are anchored. Adding a field rather than changing the meaning of existing fields avoids silent behavior change for callers that inspect `files_written` today.

**Back-compat note** (still not a shim): every existing reader of `SyncResult` is enumerated in the WP2.2 occurrence artifact. Readers that treat `files_written` as "paths relative to the current working directory" or "paths relative to `repo_root` passed in by the caller" are adjusted to use `canonical_root` explicitly. This is a direct edit; there is no dual-interpretation mode.

**Artifact**: [`contracts/chokepoint.contract.md`](contracts/chokepoint.contract.md).

### D-4 — Bundle CLI surface (WP2.1) — Q4=B
**Decision**: Add `spec-kitty charter bundle validate [--json]` as a new Typer subcommand under `src/specify_cli/cli/commands/charter.py`. The command loads `CANONICAL_MANIFEST`, resolves the canonical root via `resolve_canonical_repo_root(Path.cwd())`, runs the manifest-vs-disk contract check, and prints/returns a structured result. Exit code 0 if the bundle is compliant; non-zero with a structured error list otherwise.

**Rationale**: User-affirmed in Q4=B. A thin wrapper is cheap to add alongside the manifest module in WP2.1, useful for CI (dogfood check on every spec-kitty PR) and for operators running health checks. The command intentionally does NOT integrate with `spec-kitty doctor` — that broader integration is deferred to a follow-up tranche (Q4=B scope limit).

**Artifact**: [`contracts/bundle-validate-cli.contract.md`](contracts/bundle-validate-cli.contract.md).

### D-5 — Twin-package lockstep (C-003)
**Decision**: Every WP2.3 edit that touches a reader in `src/charter/` is mirrored in `src/specify_cli/charter/` **only if the duplicate file still contains a live direct-read path**. The WP2.3 occurrence artifact lists every duplicate-package file separately (as distinct `import_path` entries) so the verifier catches a one-sided edit. Files in the duplicate that are pure re-exports of `src/charter/` symbols are left untouched (they transitively pick up the behavior change).

**Rationale**: Spec C-003 pins deduplication out of scope. Phase 2 cannot introduce drift between the two packages, and cannot silently leave a bypass alive in the duplicate. The AST-walk test (FR-011) in WP2.3 walks the full `src/` tree and would fail if a bypass remained.

### D-6 — Dashboard typed-contract baseline capture is WP2.3 step 1 (C-010 / FR-014)
**Decision**: Before any reader is rewired in WP2.3, a first-step deliverable captures the pre-WP2.3 dashboard typed contracts (FR-014) as a golden JSON file at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json`. The capture script is committed alongside the baseline so it is reproducible. Only after this baseline is in the PR branch does WP2.3 begin rewiring readers.

**Rationale**: The byte-identical regression assertion in FR-014 has no authority unless the baseline was captured on pre-WP2.3 `main`. Capturing after the rewire begins would bake the post-WP2.3 shape in as the reference and defeat the regression test.

### D-7 — Occurrence-classification artifact shape (C-002 / FR-015)
**Decision**: Identical pattern to Phase 1. Per-WP YAML artifacts at `kitty-specs/.../occurrences/WP2.<n>.yaml` + mission-level aggregate at `.../occurrences/index.yaml`. Schema reused from Phase 1's `contracts/occurrence-artifact.schema.yaml` (the Phase 1 file is authoritative; this mission's `contracts/occurrence-artifact.schema.yaml` re-points to it or re-publishes it verbatim for reading convenience). Verifier script `scripts/verify_occurrences.py` (added in Phase 1 WP1.1) is reused as-is.

**CI enforcement**: Verifier runs as a non-skippable check on every WP PR and on the final mission merge PR.

### D-8 — Charter Check note
**Decision**: Informational only, not a gate. Governance-file absence does not block Phase 2 and is in-scope for self-repair via the chokepoint's auto-sync-on-first-read behavior.

### D-9 — Strict sequencing (C-007)
**Decision**: WP2.1 → WP2.2 → WP2.3 → WP2.4, each its own merged PR, each preflight-verified, each verifier-green before the next begins. Parallelization explicitly rejected in spec §Implementation Plan Sequencing note; plan re-affirms the rejection because:

- WP2.2's `ensure_charter_bundle_fresh()` consults the manifest for "what files must exist" — manifest must exist first (WP2.1).
- WP2.3's AST-walk test uses the manifest + the occurrence artifact as its registry — manifest must exist first (WP2.1); chokepoint must resolve canonical root first (WP2.2) for worktree-based readers to pass.
- WP2.4's migration expects the no-symlink `setup_feature_directory()` behavior to be present in-code so a post-upgrade `spec-kitty next` doesn't immediately re-create the symlinks the migration just removed.

### D-10 — Research scope
**Decision**: Four narrow Phase 0 investigations captured in `research.md`:

- **R-1** — exhaustive reader-site inventory across both `src/charter/` and `src/specify_cli/charter/`, plus `src/specify_cli/core/`, `src/specify_cli/dashboard/`, `src/specify_cli/cli/commands/`, `src/specify_cli/next/` → produces the WP2.3 occurrence artifact's reader registry.
- **R-2** — `git rev-parse --git-common-dir` behavior under worktree, submodule, sparse-checkout, and detached-HEAD conditions → produces the `resolve_canonical_repo_root` contract and edge-case test matrix.
- **R-3** — `SyncResult` caller audit → produces the list of consumers that need to be re-pointed to the new `canonical_root` field.
- **R-4** — dashboard typed-contract surface inventory → produces the specific JSON shape to freeze as the FR-014 golden baseline.

### D-11 — Phase 1 artifacts
**Decision**: Produced together with this plan — `research.md`, `data-model.md`, `quickstart.md`, and the five contract files under `contracts/`.

### D-12 — `.gitignore` policy for the bundle
**Decision**: The manifest's `gitignore_required_entries` is the authority; the migration reconciles project `.gitignore` to match. The initial CANONICAL_MANIFEST in WP2.1 sets `tracked_files = [".kittify/charter/charter.md"]` and derives the gitignore entries from `derived_files`. This matches current `.gitignore:18–22` verbatim on `main`; no entries change on the first-version manifest. Future manifest versions that add tracked artifacts bump `SCHEMA_VERSION` and ship with a migration that reconciles.

**Rationale**: The existing `.gitignore` entries are already correct for the post-Phase-2 layout (charter.md tracked, derivatives gitignored). Version 1.0.0 of the manifest is therefore a documentation-of-current-state deliverable, not a layout change — the chokepoint and migration are what change, not the filesystem contract.

---

## Work Package Shape (recommended for `/spec-kitty.tasks`)

Four strictly sequential WPs. Each WP PR includes: source edits, test edits, its occurrence artifact, and a verifier-green CI run.

### WP2.1 — Unified bundle manifest + architecture doc + bundle CLI (tracks [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478))

**Scope**:
- Add `src/charter/bundle.py` with `CharterBundleManifest` (Pydantic model), `SCHEMA_VERSION = "1.0.0"`, `CANONICAL_MANIFEST` instance. Fields per [`contracts/bundle-manifest.schema.yaml`](contracts/bundle-manifest.schema.yaml): `tracked_files`, `derived_files`, `derivation_sources`, `gitignore_required_entries`, `schema_version`.
- Add `architecture/2.x/06_unified_charter_bundle.md` documenting the bundle contract, tracked-vs-derived classification, canonical-root resolution contract, staleness semantics, and the gitignore policy.
- Add `spec-kitty charter bundle validate [--json]` Typer subcommand under `src/specify_cli/cli/commands/charter.py` per [`contracts/bundle-validate-cli.contract.md`](contracts/bundle-validate-cli.contract.md).
- Re-export `CharterBundleManifest` from `src/charter/__init__.py`.
- Add `tests/charter/test_bundle_manifest_model.py` — asserts model round-trips via Pydantic, `CANONICAL_MANIFEST` is non-empty, every `derived_files` entry has a `derivation_sources` mapping, `schema_version == "1.0.0"`.
- Add integration test for `spec-kitty charter bundle validate` against a live fixture under `tests/charter/`.
- Author `kitty-specs/.../occurrences/WP2.1.yaml` and seed `kitty-specs/.../occurrences/index.yaml`.

**Acceptance gates for WP2.1 PR**:
- All tests green.
- Verifier green against WP2.1.yaml.
- `spec-kitty charter bundle validate --json` on the repo itself exits 0 and prints a structured pass report.
- `mypy --strict` passes.

### WP2.2 — Canonical-root resolver + chokepoint plumbing (tracks [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480))

**Depends on**: WP2.1 merged (chokepoint consults the manifest).

**Scope**:
- Add `src/charter/resolution.py` with `resolve_canonical_repo_root(path: Path) -> Path`, `NotInsideRepositoryError`, `GitCommonDirUnavailableError`, and the LRU cache. Implementation per [`contracts/canonical-root-resolver.contract.md`](contracts/canonical-root-resolver.contract.md).
- Extend `SyncResult` in `src/charter/sync.py` with a new `canonical_root: Path` field per [`contracts/chokepoint.contract.md`](contracts/chokepoint.contract.md) and D-3. Keep `files_written` relative to `canonical_root`.
- Re-plumb `ensure_charter_bundle_fresh()` at `src/charter/sync.py:50-90` to call `resolve_canonical_repo_root()` first, then consult `CharterBundleManifest` (from WP2.1) for the "what files must exist" completeness check, then delegate to `sync()` if incomplete or stale.
- Update every existing `SyncResult` caller (enumerated in R-3) to use `canonical_root` explicitly.
- Add `tests/charter/test_canonical_root_resolution.py` covering the R-2 fixture matrix: plain repo, worktree-attached, submodule-attached, sparse-checkout, detached-HEAD, non-repo path (raises `NotInsideRepositoryError`).
- Add `tests/charter/test_chokepoint_overhead.py` (NFR-002 micro-benchmarks, asserting <10 ms p95 warm overhead on the dashboard fixture).
- Add `tests/charter/test_resolution_overhead.py` (NFR-003 micro-benchmarks, asserting <5 ms p95 per call and ≤1 git invocation per call via `subprocess` spy).
- Author `kitty-specs/.../occurrences/WP2.2.yaml` and update `index.yaml`.

**Acceptance gates for WP2.2 PR**:
- All tests green.
- Verifier green against WP2.2.yaml.
- Benchmark thresholds met in CI perf job.
- `mypy --strict` passes.
- WP2.1 acceptance gates still hold.

### WP2.3 — Reader cutover + worktree symlink excision + dashboard regression proof (tracks [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481))

**Depends on**: WP2.2 merged (canonical-root resolution is a prerequisite for worktree-based readers).

**Scope** (step order matters):

**A. Baseline capture (must happen BEFORE any reader rewire)**:
- Run the capture script (committed alongside the baseline) to produce `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json`. This must run on pre-WP2.3 `main` (i.e., at the top of the WP2.3 branch before any source edit) or on an explicit `HEAD~` reference if the agent cannot avoid co-mingling edits with capture.

**B. Reader cutover** (canonical package `src/charter/`):
- Flip `src/charter/context.py :: build_charter_context()` (lines 406–661 today) to call `ensure_charter_bundle_fresh()` before the direct reads of `charter.md` (line 555) and `references.yaml` (line 637). Paths resolved via `SyncResult.canonical_root` from WP2.2's D-3 extension.
- Any other `src/charter/` reader surfaced by R-1 that still bypasses the chokepoint.

**C. Reader cutover** (CLI surfaces + agent/next prompt builders):
- `src/specify_cli/cli/commands/charter.py` — every handler that reads bundle artifacts before rendering output.
- `src/specify_cli/next/prompt_builder.py` — charter injection.
- `src/specify_cli/cli/commands/agent/workflow.py` — workflow charter injection.

**D. Reader cutover** (dashboard — safety-net cluster per C-010):
- `src/specify_cli/dashboard/charter_path.py :: resolve_project_charter_path()` (lines 8–17).
- `src/specify_cli/dashboard/scanner.py` charter-presence probes.
- `src/specify_cli/dashboard/server.py` charter endpoints.
- `#361` typed contracts (`WPState`, `Lane`) remain byte-identical against the Step A baseline.

**E. Duplicate-package lockstep (C-003 / D-5)**:
- Any remaining live reader in `src/specify_cli/charter/` enumerated in the WP2.3 occurrence artifact is updated in the same PR. Pure re-export files are left untouched.

**F. Worktree symlink/copy excision**:
- Delete `src/specify_cli/core/worktree.py` lines 483–532 (the `.kittify/memory` + `.kittify/AGENTS.md` symlink/copy/`.git/info/exclude` block). Non-charter symlinks at that call site, if any, are preserved and listed in the occurrence artifact as explicit non-touched carve-outs.

**G. Tests**:
- Add `tests/charter/test_chokepoint_coverage.py` — AST-walk over `src/` asserting every call site in the WP2.3 occurrence artifact's reader registry routes through `ensure_charter_bundle_fresh` (directly or via a helper whose implementation does). The registry is the test's source of truth.
- Add `tests/charter/test_bundle_contract.py` — loads `CharterBundleManifest`, materializes a bundle in tmpdir via the chokepoint, asserts layout compliance.
- Add `tests/init/test_fresh_clone_no_sync.py` (FR-009) — fresh-clone-style fixture; every FR-004 reader invoked once without `sync`; each succeeds; derivatives exist afterward.
- Add `tests/core/test_worktree_no_charter_materialization.py` (FR-010) — drives `setup_feature_directory()`; asserts no symlink/copy/exclude-entry for charter paths in the resulting worktree.
- Add `tests/test_dashboard/test_charter_chokepoint_regression.py` (FR-014) — byte-identical comparison against `pre-wp23-dashboard-typed.json`.

**H. Occurrence artifact**:
- Author `kitty-specs/.../occurrences/WP2.3.yaml` covering categories A (import path), B (symbol name), C (filesystem path literal), D (CLI command name), E (docstring/comment), F (dict/YAML key), G (skill/template reference), H (test identifier). Update `index.yaml` with the complete mission-level "zero occurrences" assertion covering the NFR-005 must-be-zero set.

**Acceptance gates for WP2.3 PR**:
- All tests green.
- Verifier green against WP2.3.yaml and mission-level `index.yaml`.
- `tests/charter/test_chokepoint_coverage.py` passes against the registry.
- `tests/test_dashboard/test_charter_chokepoint_regression.py` passes byte-identically against the baseline.
- On a freshly-created worktree via `setup_feature_directory()`: `git status` is clean of charter entries; no `.kittify/memory` or `.kittify/AGENTS.md` symlink or copy present; `.git/info/exclude` contains no charter paths.
- Grep invariants from spec FR-016 pass.
- Test suite runtime within the 5% regression budget vs. the pre-Phase-2 baseline (NFR-001).
- `mypy --strict` passes.

### WP2.4 — Migration `m_3_2_3_unified_bundle.py` (tracks [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479))

**Depends on**: WP2.3 merged (no-symlink `setup_feature_directory()` must be present before the migration enforces it on legacy projects).

**Scope**:
- Add `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py`. `target_version = "3.2.3"`. Structure follows `m_3_2_0_update_planning_templates.py:50-60` and `m_3_1_1_charter_rename.py` patterns.
- Behavior per [`contracts/migration-report.schema.json`](contracts/migration-report.schema.json) and spec FR-007:
  - (a) Scan `.worktrees/*/` for `.kittify/memory`, `.kittify/AGENTS.md`, and other charter-bundle symlinks/copies; delete them.
  - (b) Remove matching `.git/info/exclude` entries inside each worktree.
  - (c) Validate `.kittify/charter/` against the FR-006 / WP2.1 manifest.
  - (d) Invoke the chokepoint to regenerate any missing derived files.
  - (e) Reconcile project `.gitignore` against `gitignore_required_entries` from the manifest (per D-12 this is a no-op on the 1.0.0 manifest; the reconciliation logic exists for future manifest versions).
  - (f) Emit a structured JSON report per [`contracts/migration-report.schema.json`](contracts/migration-report.schema.json).
- Idempotent: second apply is a no-op (verified in FR-013 fixture matrix).
- Update the issue [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464) body in a tracking comment to reflect the `m_3_2_3_unified_bundle.py` filename per C-008.
- Add `tests/upgrade/test_unified_bundle_migration.py` — FR-013 fixture matrix (five fixtures: pre-Phase-2 with legacy worktree symlinks; pre-Phase-2 with no worktrees; Phase-2-shaped project (no-op); stale-hash project; no-charter project).
- Add `CHANGELOG.md` entry per spec Success Criterion 11.
- Author `kitty-specs/.../occurrences/WP2.4.yaml` and finalize `index.yaml`.

**Acceptance gates for WP2.4 PR**:
- All tests green.
- Verifier green against WP2.4.yaml and the finalized mission-level `index.yaml`.
- Migration registry discovers `m_3_2_3_unified_bundle` at boot (smoke test).
- `spec-kitty upgrade` on the FR-013 reference fixture completes in ≤2 s wall time (NFR-006).
- `mypy --strict` passes.
- All previous WP acceptance gates still hold.

---

## Risk & Mitigation Plan (operational)

Cross-reference spec §Risks. Operational mitigations below are the plan-level elaboration.

| Spec risk | Plan-phase mitigation |
| --- | --- |
| A reader site is missed in WP2.3 occurrence classification | R-1 is an exhaustive Phase 0 investigation using static grep + Python AST walk + string-literal sweep. `tests/charter/test_chokepoint_coverage.py` is the completeness proof. A missed site fails the test. |
| `git rev-parse --git-common-dir` misbehaves under submodule/sparse/detached-HEAD | R-2 produces the edge-case matrix that becomes `tests/charter/test_canonical_root_resolution.py`'s fixture set. C-009 mandates git-native semantics — the resolver does not re-implement layout parsing, so any misbehavior is a git bug, not a spec-kitty bug, and is surfaced via the structured `GitCommonDirUnavailableError`. |
| Removing charter symlinks breaks an agent that embedded a relative `../../../.kittify/memory/...` path | R-1's string-literal sweep must include `../../../.kittify` and `../../.kittify` and variants. Every hit is rewired or flagged. |
| Migration fails idempotency | FR-013 fixture matrix explicitly exercises double-apply. The migration's scan step is stateless and re-entrant. |
| Dashboard golden baseline captures non-deterministic fields | D-6 mandates the baseline capture script be committed alongside the JSON; the script redacts timestamps and normalizes ordering before the commit. Both the script and the JSON live under `kitty-specs/.../baseline/`. |
| NFR-002 warm overhead breached by hash reads | Plan D-3 allows (but does not mandate) an mtime short-circuit inside the chokepoint's completeness check; `tests/charter/test_chokepoint_overhead.py` is the enforcement bar. |
| WP PR lands out of order | C-007 enforces sequencing; the occurrence artifact's `requires_merged: [WP2.<prev>]` field gates the verifier; branch protection on `main` keeps the WP issue checkboxes advancing in order. |
| Live reader in `src/specify_cli/charter/` missed | AST-walk test in FR-011 walks the full `src/` tree, not a single package. Occurrence classification lists both packages separately. |
| Manifest disagrees with existing `.gitignore` | D-12 pins v1.0.0 manifest to the current `.gitignore` state; the migration's reconciliation is a no-op on first apply. Disagreement is caught by `tests/charter/test_bundle_contract.py`. |
| `resolve_canonical_repo_root` invoked outside a git repo (e.g., test setup) | Resolver raises `NotInsideRepositoryError`; callers distinguish this from operational failure. Test fixtures always operate inside a fixture repo. |

---

## Complexity Tracking

No Charter Check violations. No complexity budget items. Two new modules added (`src/charter/bundle.py`, `src/charter/resolution.py`) and one new migration module; each is a single well-scoped concern matching the spec FR directly. The new `spec-kitty charter bundle validate` subcommand is a thin Typer wrapper over existing primitives — no architectural complexity added.

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
