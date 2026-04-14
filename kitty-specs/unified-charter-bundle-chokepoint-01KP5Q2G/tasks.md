# Tasks: Unified Charter Bundle and Read Chokepoint

**Mission slug**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Planning base branch**: `main` — Completed changes merge into `main`.
**Generated**: 2026-04-14
**Spec**: [spec.md](spec.md) • **Plan**: [plan.md](plan.md) • **Research**: [research.md](research.md) • **Data model**: [data-model.md](data-model.md) • **Contracts**: [contracts/](contracts/) • **Quickstart**: [quickstart.md](quickstart.md)

Strict sequential WP ordering per C-007: **strict sequence WP01 then WP02 then WP03 then WP04**. Every WP edits SOURCE templates only per C-006 and respects the C-011 / C-012 carve-outs (no worktree symlink edits; no expansion of v1.0.0 manifest scope).

---

## Subtask index (reference table — not a tracking surface)

| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Create `src/charter/bundle.py` with `CharterBundleManifest`, `SCHEMA_VERSION = "1.0.0"`, `CANONICAL_MANIFEST` | WP01 | — | [D] | [D] |
| T002 | Write `architecture/2.x/06_unified_charter_bundle.md` documenting v1.0.0 contract | WP01 | [D] |
| T003 | Create `src/specify_cli/cli/commands/charter_bundle.py` with Typer sub-app for `bundle validate` | WP01 | — | [D] |
| T004 | Re-export `CharterBundleManifest` from `src/charter/__init__.py` | WP01 | [D] |
| T005 | Write `tests/charter/test_bundle_manifest_model.py` | WP01 | [D] |
| T006 | Write `tests/charter/test_bundle_validate_cli.py` (Typer runner integration) | WP01 | [D] |
| T007 | Author `kitty-specs/.../occurrences/WP01.yaml` and seed `index.yaml` | WP01 | — | [D] |
| T008 | Create `src/charter/resolution.py` with `resolve_canonical_repo_root` + exceptions + LRU cache | WP02 | — |
| T009 | Write `tests/charter/test_canonical_root_resolution.py` covering R-2 matrix | WP02 | [P] |
| T010 | Extend `SyncResult` in `src/charter/sync.py` with `canonical_root: Path` | WP02 | — |
| T011 | Refactor `ensure_charter_bundle_fresh()` to call the resolver and consult the manifest | WP02 | — |
| T012 | Update `post_save_hook()` + any existing `SyncResult` inspections inside `src/charter/sync.py` and its tests for `canonical_root` | WP02 | — |
| T013 | Write `tests/charter/test_chokepoint_overhead.py` (NFR-002 benchmarks) | WP02 | [P] |
| T014 | Write `tests/charter/test_resolution_overhead.py` (NFR-003 benchmarks) | WP02 | [P] |
| T015 | Author `kitty-specs/.../occurrences/WP02.yaml` and extend `index.yaml` | WP02 | — |
| T016 | **STEP A**: capture pre-WP03 dashboard typed-contracts baseline via committed `baseline/capture.py` | WP03 | — |
| T017 | Flip `src/charter/context.py :: build_charter_context()` to route through the chokepoint (does NOT touch lines 385-398) | WP03 | — |
| T018 | Flip CLI + prompt-builder readers: `charter.py` handlers + register `charter_bundle` sub-app; `next/prompt_builder.py`; `cli/commands/agent/workflow.py` | WP03 | — |
| T019 | Flip dashboard readers: `charter_path.py`, `scanner.py`, `server.py` — preserve `#361` typed contracts | WP03 | — |
| T020 | Lockstep update to `src/specify_cli/charter/` duplicate package (any live reader) | WP03 | — |
| T021 | Write `tests/charter/test_chokepoint_coverage.py` (AST walk) and `tests/charter/test_bundle_contract.py` | WP03 | [P] |
| T022 | Write `tests/init/test_fresh_clone_no_sync.py` and `tests/charter/test_worktree_charter_via_canonical_root.py` | WP03 | [P] |
| T023 | Write `tests/test_dashboard/test_charter_chokepoint_regression.py` (byte-identical with redactions) | WP03 | [P] |
| T024 | Author `kitty-specs/.../occurrences/WP03.yaml` (includes C-011 / C-012 carve-outs) and extend `index.yaml` | WP03 | — |
| T025 | Create `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` | WP04 | — |
| T026 | Write `tests/upgrade/test_unified_bundle_migration.py` against FR-013 fixture matrix (five fixtures) | WP04 | [P] |
| T027 | Register migration in `src/specify_cli/upgrade/migrations/__init__.py` (if explicit registration is required; auto-discovery may suffice) | WP04 | — |
| T028 | Add `CHANGELOG.md` entry and post `#464` tracking comment reflecting filename + scope corrections | WP04 | [P] |
| T029 | Author `kitty-specs/.../occurrences/WP04.yaml` and **finalize** mission-level `index.yaml` | WP04 | — |

Total: 29 subtasks across 4 work packages. Average 7.25 subtasks/WP. Expected prompt sizes: 350-500 lines per WP.

---

## WP01 — Unified bundle manifest, architecture doc, and bundle CLI

**Tracks**: [#478](https://github.com/Priivacy-ai/spec-kitty/issues/478)
**Dependencies**: none (first WP in the Phase 2 tranche)
**Goal**: Establish the typed bundle manifest contract (v1.0.0), publish the architecture §6 doc, and ship the `spec-kitty charter bundle validate` CLI as a self-contained Typer sub-app. The sub-app is NOT yet registered into the `charter` CLI — WP03 does that as part of its reader cutover.
**Priority**: Foundation (prerequisite for every downstream WP).
**Independent test**: `pytest tests/charter/test_bundle_manifest_model.py tests/charter/test_bundle_validate_cli.py` plus `mypy --strict src/charter/bundle.py src/specify_cli/cli/commands/charter_bundle.py` all pass.
**Estimated prompt size**: ~400 lines.

### Included subtasks

- [x] T001 Create `src/charter/bundle.py` with `CharterBundleManifest`, `SCHEMA_VERSION = "1.0.0"`, `CANONICAL_MANIFEST` (WP01)
- [x] T002 Write `architecture/2.x/06_unified_charter_bundle.md` documenting v1.0.0 contract (WP01) [P]
- [x] T003 Create `src/specify_cli/cli/commands/charter_bundle.py` with Typer sub-app for `bundle validate` (WP01)
- [x] T004 Re-export `CharterBundleManifest` from `src/charter/__init__.py` (WP01) [P]
- [x] T005 Write `tests/charter/test_bundle_manifest_model.py` (WP01) [P]
- [x] T006 Write `tests/charter/test_bundle_validate_cli.py` — Typer runner integration (WP01) [P]
- [x] T007 Author `kitty-specs/.../occurrences/WP01.yaml` and seed `index.yaml` (WP01)

### Implementation sketch

1. **T001** — Define the Pydantic model per `contracts/bundle-manifest.schema.yaml` + `data-model.md`. Instantiate `CANONICAL_MANIFEST` with the three `sync()`-produced derived files. Add a frozen Pydantic validator that rejects overlap between `tracked_files` and `derived_files`.
2. **T002** — Architecture doc cites manifest module, canonical-root contract, out-of-scope list (`references.yaml`, `context-state.json`), and the gitignore policy (MUST-INCLUDE semantics).
3. **T003** — The sub-app implements the CLI behavior from `contracts/bundle-validate-cli.contract.md`: resolve canonical root via a `try/except` path that SURFACES `NotInsideRepositoryError` / `GitCommonDirUnavailableError` cleanly. The resolver module ships later in the tranche; WP01 uses a temporary minimal `subprocess.run(["git", "rev-parse", "--show-toplevel"], ...)` wrapper inside `charter_bundle.py` and annotates it with a TODO anchor so the downstream WP can swap in the real `resolve_canonical_repo_root` import.
4. **T004** — One-line re-export.
5. **T005 / T006** — Unit tests for the model; Typer runner integration test invoking `charter_bundle.app` directly.
6. **T007** — First occurrence artifact. Must list the v1.0.0 manifest file paths under category `filesystem_path_literal` and the `SCHEMA_VERSION` / `CANONICAL_MANIFEST` symbols under `symbol_name`.

### Parallel opportunities

- T002, T004, T005, T006 are marked `[P]` — they can be drafted in parallel once T001 and T003 are done (or in parallel with T001/T003 if the implementer is confident about the manifest shape).

### Dependencies

- None (first WP in the tranche).

### Risks

- The temporary `git rev-parse --show-toplevel` wrapper in T003 must be flagged as TODO so WP02 replaces it with `resolve_canonical_repo_root`. If this TODO is not honored, the CLI will behave incorrectly in worktrees until WP03 lands. Ensure the WP01 occurrence artifact lists the TODO string as `action: rewrite` with `rewrite_to: "resolve_canonical_repo_root"` expected by WP02.

### Parallel tracking rows

See **Included subtasks** above (checkbox format is the tracking surface).

---

## WP02 — Canonical-root resolver + chokepoint plumbing

**Tracks**: [#480](https://github.com/Priivacy-ai/spec-kitty/issues/480)
**Goal**: Add `resolve_canonical_repo_root()` at `src/charter/resolution.py` using the exact six-step algorithm in `contracts/canonical-root-resolver.contract.md`. Extend `SyncResult` with `canonical_root: Path` (Q2=C). Re-plumb `ensure_charter_bundle_fresh()` to consult manifest + resolver. Update internal callers; establish the two perf benchmarks.
**Priority**: Foundation (prerequisite for WP03 and WP04).
**Independent test**: `pytest tests/charter/test_canonical_root_resolution.py tests/charter/test_chokepoint_overhead.py tests/charter/test_resolution_overhead.py` all pass; benchmarks meet NFR-002 / NFR-003 thresholds; `mypy --strict` green.
**Estimated prompt size**: ~500 lines.

### Included subtasks

- [ ] T008 Create `src/charter/resolution.py` with `resolve_canonical_repo_root` + exceptions + LRU cache (WP02)
- [ ] T009 Write `tests/charter/test_canonical_root_resolution.py` covering R-2 matrix (WP02) [P]
- [ ] T010 Extend `SyncResult` in `src/charter/sync.py` with `canonical_root: Path` (WP02)
- [ ] T011 Refactor `ensure_charter_bundle_fresh()` to call the resolver and consult the manifest (WP02)
- [ ] T012 Update `post_save_hook()` + any existing `SyncResult` inspections inside `src/charter/sync.py` and its tests for `canonical_root` (WP02)
- [ ] T013 Write `tests/charter/test_chokepoint_overhead.py` — NFR-002 benchmarks (WP02) [P]
- [ ] T014 Write `tests/charter/test_resolution_overhead.py` — NFR-003 benchmarks (WP02) [P]
- [ ] T015 Author `kitty-specs/.../occurrences/WP02.yaml` and extend `index.yaml` (WP02)

### Implementation sketch

1. **T008** — Implement the six-step algorithm exactly per the contract. LRU cache via `functools.lru_cache(maxsize=256)` on a private `_resolve_cached(abs_path_str: str) -> str` helper. Exceptions subclass `RuntimeError`.
2. **T009** — One test per row in the R-2 behavioral matrix. Include a `subprocess.run` spy to verify at most one `git` invocation per cold call. Include a `cache_clear` reset between tests that mutate fixture layout.
3. **T010** — Add the new field to the dataclass. Update the `SyncResult(...)` constructor calls inside `sync.py` to pass `canonical_root`.
4. **T011** — Top of `ensure_charter_bundle_fresh()` calls `resolve_canonical_repo_root(repo_root)`. Use the resolved path for `charter_dir` computation. Replace the hard-coded `_SYNC_OUTPUT_FILES` completeness check with `CANONICAL_MANIFEST.derived_files`. Preserve the existing `is_stale()` hash comparison. Return a `SyncResult` whose `canonical_root` is set and `files_written` entries are relative to it.
5. **T012** — `post_save_hook()` must anchor its log messages against `canonical_root` when displaying paths. Update internal tests in `tests/charter/` that assert on `SyncResult.files_written` (currently expect raw filenames relative to caller-provided `repo_root`) to assert paths relative to `canonical_root`.
6. **T013** — NFR-002 benchmark: 100 warm invocations of `ensure_charter_bundle_fresh()` against a fresh tmpdir bundle; assert p95 <10 ms. Use `time.monotonic_ns()` for timing; use `subprocess.run` spy to assert ≤0 git calls on warm path.
7. **T014** — NFR-003 benchmark: 100 warm invocations of `resolve_canonical_repo_root()` on the same path; assert p95 <5 ms. Cold path: one call, assert ≤50 ms and exactly one `git` invocation.
8. **T015** — Occurrence artifact covers categories `import_path` (`from charter.resolution import ...`), `symbol_name` (`resolve_canonical_repo_root`, `NotInsideRepositoryError`, `GitCommonDirUnavailableError`), `filesystem_path_literal` (`src/charter/resolution.py`, `src/charter/sync.py` for the modified region), and `test_identifier` (the three new test modules). `requires_merged: [WP01]`.

### Parallel opportunities

- T009, T013, T014 are [P] — each is a new test module.

### Dependencies

- Depends on WP01 (manifest model must exist before chokepoint consults it).

### Risks

- `git rev-parse --git-common-dir` behavior on Windows-WSL / linked worktrees / submodules requires local verification. R-2 matrix test must include all rows; skipping any leaves a platform gap.
- Updating existing tests for `files_written` semantics (T012) may touch more files than expected — the WP02 occurrence artifact must enumerate every test file that asserts on that field.

---

## WP03 — Reader cutover, worktree transparency, dashboard regression proof

**Tracks**: [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481)
**Dependencies**: WP02
**Goal**: Flip every reader of the three v1.0.0 manifest derivatives through the chokepoint, register the `charter_bundle` sub-app into the `charter` CLI so `spec-kitty charter bundle validate` is user-accessible, prove the dashboard typed-contract regression bar holds, and produce the AST-walk coverage test. WP03 is the biggest and most surgical WP — it touches many files but each edit is small.
**Priority**: Core (prerequisite for WP04).
**Independent test**: `pytest tests/charter/test_chokepoint_coverage.py tests/charter/test_bundle_contract.py tests/init/test_fresh_clone_no_sync.py tests/charter/test_worktree_charter_via_canonical_root.py tests/test_dashboard/test_charter_chokepoint_regression.py` all pass; the grep invariants from spec FR-016 hold; `mypy --strict` green; `src/specify_cli/core/worktree.py` lines 478-532 are **unchanged** vs. pre-Phase-2 `main` (C-011 carve-out verification).
**Estimated prompt size**: ~600 lines.

### Included subtasks

- [ ] T016 Capture pre-WP03 dashboard typed-contracts baseline via committed `baseline/capture.py` — **Step A, MUST run first** (WP03)
- [ ] T017 Flip `src/charter/context.py :: build_charter_context()` to route through the chokepoint; does NOT touch lines 385-398 (C-012) (WP03)
- [ ] T018 Flip CLI + prompt-builder readers: `charter.py` handlers + register `charter_bundle` sub-app via `charter_app.add_typer(charter_bundle.app, name="bundle")`; `next/prompt_builder.py`; `cli/commands/agent/workflow.py` (WP03)
- [ ] T019 Flip dashboard readers: `charter_path.py`, `scanner.py`, `server.py`; preserve `#361` typed contracts (WP03)
- [ ] T020 Lockstep update to `src/specify_cli/charter/` duplicate package where live readers remain (WP03)
- [ ] T021 Write `tests/charter/test_chokepoint_coverage.py` (AST walk) and `tests/charter/test_bundle_contract.py` (WP03) [P]
- [ ] T022 Write `tests/init/test_fresh_clone_no_sync.py` and `tests/charter/test_worktree_charter_via_canonical_root.py` (WP03) [P]
- [ ] T023 Write `tests/test_dashboard/test_charter_chokepoint_regression.py` — byte-identical with R-4 redactions (WP03) [P]
- [ ] T024 Author `kitty-specs/.../occurrences/WP03.yaml` (includes C-011 / C-012 carve-outs) and extend `index.yaml` (WP03)

### Implementation sketch

See WP03 prompt file for per-subtask detail. Strict order: T016 first (on pre-WP03 `main`), then T017-T020 in any order, then T021-T024. WP03 also replaces the temporary `git rev-parse --show-toplevel` wrapper in `charter_bundle.py` (T003) with `resolve_canonical_repo_root` now that WP02 has landed.

### Parallel opportunities

- T021, T022, T023 are [P] — test modules can be drafted in parallel once the source-side flips (T017-T020) are in progress. T024 must be last (it summarizes everything).

### Dependencies

- Depends on WP02. Since WP02 itself requires WP01, WP03 transitively assumes both are merged.

### Risks

- **T016 must happen first.** If baseline capture is co-mingled with source edits in WP03, the regression bar becomes circular.
- **C-011 carve-out violation**. A developer could inadvertently touch `src/specify_cli/core/worktree.py:478-532` during WP03. The occurrence artifact's explicit `leave` entry and spec Success Criterion 8 grep check defend against this.
- **Dashboard regression test flakiness**. R-4 redactions must be implemented exactly in both the capture script AND the regression test; any asymmetry produces false positives.
- **Duplicate-package lockstep missed**. AST-walk test (T021) walks the full `src/` tree; if a live reader in `src/specify_cli/charter/` is missed, the test fails.

---

## WP04 — Migration `m_3_2_3_unified_bundle.py`

**Tracks**: [#479](https://github.com/Priivacy-ai/spec-kitty/issues/479)
**Dependencies**: WP03
**Goal**: Ship the registry-discoverable upgrade migration that (a) detects `charter.md` presence, (b) validates the bundle against `CharterBundleManifest` v1.0.0, (c) invokes the chokepoint to regenerate missing derivatives, (d) emits the structured JSON report. **No worktree scanning, no symlink removal, no `.gitignore` reconciliation** (design-review corrections; all three were artifacts of earlier-draft scope bugs).
**Priority**: Final (release-gating WP).
**Independent test**: `pytest tests/upgrade/test_unified_bundle_migration.py` passes against all five FR-013 fixtures; migration registry discovers `m_3_2_3_unified_bundle` at boot; `spec-kitty upgrade` on the FR-013 reference fixture completes in ≤2 s (NFR-006); `mypy --strict` green.
**Estimated prompt size**: ~400 lines.

### Included subtasks

- [ ] T025 Create `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py` (WP04)
- [ ] T026 Write `tests/upgrade/test_unified_bundle_migration.py` against FR-013 fixture matrix (five fixtures) (WP04) [P]
- [ ] T027 Register migration in `src/specify_cli/upgrade/migrations/__init__.py` if explicit registration is required (WP04)
- [ ] T028 Add `CHANGELOG.md` entry and post `#464` tracking comment (WP04) [P]
- [ ] T029 Author `kitty-specs/.../occurrences/WP04.yaml` and **finalize** `index.yaml` (WP04)

### Implementation sketch

See WP04 prompt file. Migration pattern matches `m_3_2_0_update_planning_templates.py:50-60`. JSON report matches `contracts/migration-report.schema.json` exactly.

### Parallel opportunities

- T026 and T028 are [P].

### Dependencies

- Depends on WP03 (chokepoint and bundle contract must be present before the migration exercises them).

### Risks

- **Scope creep**. Implementer may be tempted to add worktree scanning / symlink removal / gitignore reconciliation — all three are **removed from scope** per design-review corrections. Migration scope is explicitly the four bullets in the goal.
- **Idempotency bug**. FR-013 fixture (c) must assert that a second apply is a no-op with `applied: false`. Any stateful write in the migration risks breaking this.

---

## Parallelization summary

- **Across WPs**: NO parallelization. strict sequence WP01 then WP02 then WP03 then WP04 is strict sequential per C-007.
- **Within each WP**: several `[P]` subtasks (primarily test authoring) can run concurrently with the main implementation.
- **MVP**: WP01 + WP02 together deliver the typed foundation (manifest + resolver + chokepoint plumbing). WP03 is where the user-visible behavior change lands. WP04 is the upgrade polish.

---

## Prompt generation stats

- 4 WP prompt files total: `tasks/WP01-unified-bundle-manifest.md`, `tasks/WP02-canonical-root-resolver-chokepoint.md`, `tasks/WP03-reader-cutover-dashboard-regression.md`, `tasks/WP04-migration-unified-bundle.md`
- Average prompt size: ~475 lines (350-600 range per WP)
- All WPs within the 700-line ceiling
- Every WP ≤ 10 subtasks

---

## Next step

User runs `/spec-kitty.implement` (or the implement-review skill if they want automated orchestration) starting with WP01. Each `spec-kitty agent action implement WP<NN> --agent <name>` call resolves the actual workspace/branch via `lanes.json`; do not reconstruct paths by hand.
