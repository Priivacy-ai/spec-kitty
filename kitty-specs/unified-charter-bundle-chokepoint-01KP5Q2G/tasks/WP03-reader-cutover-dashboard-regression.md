---
work_package_id: WP03
title: Reader cutover, worktree transparency, and dashboard regression proof
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-009
- FR-010
- FR-011
- FR-012
- FR-014
- FR-015
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
- T022
- T023
- T024
history:
- at: '2026-04-14T11:16:00Z'
  actor: claude
  event: created
authoritative_surface: src/charter/context.py
execution_mode: code_change
owned_files:
- src/charter/context.py
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/next/prompt_builder.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/dashboard/charter_path.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/dashboard/server.py
- src/specify_cli/charter/**
- tests/charter/test_chokepoint_coverage.py
- tests/charter/test_bundle_contract.py
- tests/charter/test_worktree_charter_via_canonical_root.py
- tests/init/test_fresh_clone_no_sync.py
- tests/test_dashboard/test_charter_chokepoint_regression.py
- kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/**
- kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP03.yaml
tags: []
---

# WP03 — Reader cutover, worktree transparency, and dashboard regression proof

**Tracks**: [Priivacy-ai/spec-kitty#481](https://github.com/Priivacy-ai/spec-kitty/issues/481)
**Depends on**: WP02 (resolver + extended SyncResult)
**Merges to**: `main`

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution mode**: lane-based worktree allocated by `finalize-tasks`. Run `spec-kitty agent action implement WP03 --agent <name> --mission unified-charter-bundle-chokepoint-01KP5Q2G`.

---

## Objective

Flip every reader of the three v1.0.0 manifest derivatives through the chokepoint. Capture the pre-cutover dashboard typed-contract baseline BEFORE any reader is rewired so the post-cutover byte-identical regression assertion is meaningful. Register the `charter_bundle` sub-app from WP01 into the main `charter` CLI so `spec-kitty charter bundle validate` is user-accessible. Replace the `TODO(WP02)` wrapper in WP01's sub-app with the real resolver. Ship the AST-walk coverage test, the bundle contract test, the fresh-clone smoke test, the worktree transparency test, and the dashboard regression test.

**DO NOT touch**: `src/specify_cli/core/worktree.py:478-532` (C-011), `src/charter/compiler.py` (C-012), `src/charter/context.py:385-398` (C-012).

## Context

- EPIC: [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
- Phase 2 tracking: [#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)
- WP tracking issue: [#481](https://github.com/Priivacy-ai/spec-kitty/issues/481)
- Safety net: `#361` dashboard typed contracts (`WPState`, `Lane`). Must survive byte-identically with R-4 redactions.
- Design-review correction P1 #1: worktree code is OUT of scope. Canonical-root resolution (from WP02) is what makes worktree readers transparently see the main-checkout bundle — not any edit to `worktree.py`.

## Authoritative files (read before starting)

- [spec.md](../spec.md) — FR-004, FR-009, FR-010, FR-011, FR-012, FR-014, FR-015, FR-016; C-001, C-002, C-003, C-006, C-007, C-010, C-011, C-012
- [plan.md](../plan.md) — WP2.3 section + D-5 (lockstep), D-6 (baseline), D-12 (gitignore policy)
- [research.md](../research.md) — R-1 (reader inventory), R-4 (dashboard baseline method)
- [contracts/chokepoint.contract.md](../contracts/chokepoint.contract.md) — invariants 1-6
- [contracts/bundle-validate-cli.contract.md](../contracts/bundle-validate-cli.contract.md) — CLI shape
- [quickstart.md](../quickstart.md) — WP03 smoke-check recipe, common pitfalls

---

## Subtask details

### T016 — **STEP A**: Capture pre-WP03 dashboard typed-contracts baseline

**Purpose**: The FR-014 regression assertion has no authority unless the baseline was captured on pre-WP2.3 `main`. This subtask MUST run first — before any source edit in T017+.

**Steps**:

1. On a branch rooted at pre-WP03 `main`, create `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py` (new, ~150 lines). The script must:
   - Boot the dashboard in a temp fixture project with a pre-staged charter and one mission with three WPs in varying states (states: `planned`, `in_progress`, `done`).
   - Hit the dashboard endpoints that produce `WPState` / `Lane` typed contracts (enumerate them from `src/specify_cli/dashboard/server.py` routes).
   - Apply R-4 redactions before writing JSON:
     - Sort all mapping keys (`json.dumps(..., sort_keys=True, indent=2)`).
     - Replace any `"*_at"` timestamp field value with the literal `"<ts>"`.
     - Replace any ULID field value whose key is NOT an identity field with `"<ulid>"`.
     - Sort all arrays whose order is semantically irrelevant (mission list, WP list).

2. Run the capture script once and commit the output:

   ```bash
   python kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py \
     > kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json
   git add kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/
   git commit -m "WP03: capture pre-cutover dashboard typed-contract baseline"
   ```

3. The capture script must remain committed so T023's regression test can call it again on post-cutover code and diff the outputs.

**Files**:
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py` (new, ~150 lines)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` (new, committed)

**Validation**:
- [ ] `python kitty-specs/.../baseline/capture.py` exits 0 and prints valid JSON.
- [ ] Committed JSON has timestamps redacted to `"<ts>"`.
- [ ] Git log shows this commit BEFORE any T017+ commit.

---

### T017 — Flip `build_charter_context()` at `src/charter/context.py`

**Purpose**: The primary reader today bypasses the chokepoint. This subtask makes it route through.

**Steps**:

1. At the top of `build_charter_context()` (currently line 406), add the chokepoint call:

   ```python
   def build_charter_context(
       repo_root: Path,
       *,
       profile: str | None = None,
       action: str,
       mark_loaded: bool = True,
       depth: int | None = None,
   ) -> CharterContextResult:
       from charter.sync import ensure_charter_bundle_fresh  # Local import.

       sync_result = ensure_charter_bundle_fresh(repo_root)
       # If sync_result is None, charter.md is absent; preserve existing missing-charter semantics.
       canonical_root = sync_result.canonical_root if sync_result else repo_root
       # ...rest of the function uses `canonical_root` instead of `repo_root` for charter_dir computation.
   ```

2. Replace every in-function occurrence of `repo_root` that constructs a path into `.kittify/charter/` with `canonical_root`. Specifically line ~555 `charter_path.read_text()` and line ~637 `_load_references(references_path)` — their paths must root at `canonical_root`.

3. **DO NOT TOUCH lines 385-398** (the `context-state.json` write path). That is C-012 out-of-scope. The write path continues to use whatever anchor it uses today.

4. Preserve the `None` return when `sync_result` is `None` AND `charter.md` is absent, matching existing semantics.

**Files**:
- `src/charter/context.py` (modified — function head rewired; ~15 lines diff; lines 385-398 untouched)

**Validation**:
- [ ] `pytest tests/charter/test_context.py tests/agent/test_workflow_charter_context.py` green.
- [ ] `grep -n "ensure_charter_bundle_fresh" src/charter/context.py` finds the new import + call.
- [ ] `diff <(git show main:src/charter/context.py | sed -n '385,398p') <(sed -n '385,398p' src/charter/context.py)` shows no changes (line-range preservation, C-012 verification).

---

### T018 — Flip CLI + prompt-builder readers; register `charter_bundle` sub-app

**Purpose**: Every CLI handler, the next-prompt builder, and the workflow prompt builder must route through the chokepoint.

**Steps**:

1. Edit `src/specify_cli/cli/commands/charter.py`:
   - Add at the top: `from .charter_bundle import app as charter_bundle_app`
   - Add the registration: `app.add_typer(charter_bundle_app, name="bundle")` (where `app` is the existing charter Typer app).
   - For every handler in this file that reads bundle artifacts before rendering output, call `ensure_charter_bundle_fresh(Path.cwd())` at the handler's entry and anchor subsequent reads against `sync_result.canonical_root`. Specifically: `context`, `status`, and any handler that reads governance.yaml / directives.yaml / metadata.yaml.
   - Do NOT touch the `interview` or `generate` handlers — they only write `charter.md` and call the compiler/sync pipelines; the chokepoint is not a prerequisite for their writes.

2. Edit `src/specify_cli/cli/commands/charter_bundle.py`:
   - Replace the `_resolve_canonical_root_TEMP` wrapper with `from charter.resolution import resolve_canonical_repo_root`.
   - Remove the `TODO(WP02)` marker.

3. Edit `src/specify_cli/next/prompt_builder.py`:
   - Audit every code path that injects charter context into the next-prompt. If it reads `governance.yaml` / `directives.yaml` / `metadata.yaml` directly, or calls `build_charter_context`, it already routes through the chokepoint (T017). Any OTHER direct read must be flipped.

4. Edit `src/specify_cli/cli/commands/agent/workflow.py`:
   - Same audit: find every reader of v1.0.0 manifest files; route through the chokepoint.

**Files**:
- `src/specify_cli/cli/commands/charter.py` (modified — handler flips + registration; ~25 lines diff)
- `src/specify_cli/cli/commands/charter_bundle.py` (modified — TODO resolved; ~6 lines diff)
- `src/specify_cli/next/prompt_builder.py` (modified per audit)
- `src/specify_cli/cli/commands/agent/workflow.py` (modified per audit)

**Validation**:
- [ ] `spec-kitty charter bundle validate --json` (after dev-install) exits 0 and prints structured JSON.
- [ ] `spec-kitty charter context --action specify --json` works from both main checkout and a worktree, returning the same JSON.
- [ ] `grep -n "TODO(WP02)" src/` returns no rows.

---

### T019 — Flip dashboard readers (`#361` typed contracts preserved)

**Purpose**: Route the dashboard's charter-presence and charter-read probes through the chokepoint without changing the typed-contract output shape.

**Steps**:

1. Edit `src/specify_cli/dashboard/charter_path.py :: resolve_project_charter_path()` (lines 8-17):
   - Call `ensure_charter_bundle_fresh(repo_root)` first.
   - If `sync_result is None`: return the "no charter" signal (preserve existing behavior).
   - Otherwise: return the path rooted at `sync_result.canonical_root`.

2. Edit `src/specify_cli/dashboard/scanner.py`:
   - Audit for every direct access to `.kittify/charter/<file>`. Route each through the chokepoint.
   - Preserve the per-frame hot-loop shape so NFR-002 isn't breached (the chokepoint's warm-overhead budget is <10 ms per call).

3. Edit `src/specify_cli/dashboard/server.py`:
   - Audit endpoints that return `WPState` / `Lane` typed contracts and touch charter state. Route through the chokepoint.

4. After these edits: the dashboard's JSON responses for `WPState` / `Lane` must be byte-identical (with R-4 redactions) to the pre-WP03 baseline. T023 tests this.

**Files**:
- `src/specify_cli/dashboard/charter_path.py` (modified; ~10 lines diff)
- `src/specify_cli/dashboard/scanner.py` (modified per audit)
- `src/specify_cli/dashboard/server.py` (modified per audit)

**Validation**:
- [ ] `pytest tests/test_dashboard/` — existing tests still pass.
- [ ] Manual: boot dashboard, click around; charter-present badge still shows.

---

### T020 — Lockstep update to `src/specify_cli/charter/` duplicate package

**Purpose**: Any live reader in the duplicate package must route through the chokepoint too (C-003 lockstep).

**Steps**:

1. Grep `src/specify_cli/charter/` for direct reads of `governance.yaml` / `directives.yaml` / `metadata.yaml` / `charter.md`:
   ```
   rg -n 'governance\.yaml|directives\.yaml|metadata\.yaml|\.kittify/charter' src/specify_cli/charter/
   ```

2. For every hit, determine if the file is a live reader or a pure re-export of `src/charter/` symbols:
   - If pure re-export: LEAVE untouched.
   - If live reader with a direct read: flip it to route through the chokepoint, matching the T017/T018 pattern.

3. Add an explicit entry to the WP03 occurrence artifact for every touched file.

**Files**:
- `src/specify_cli/charter/context.py`, `src/specify_cli/charter/sync.py`, etc. — modified if live readers remain.

**Validation**:
- [ ] `rg -n 'charter_path\.read_text\(\)|references_path' src/specify_cli/charter/ src/charter/` — every hit routes through `ensure_charter_bundle_fresh` somewhere in its call stack.

---

### T021 — Write `tests/charter/test_chokepoint_coverage.py` and `test_bundle_contract.py`

**Purpose**: Two principal proofs that the chokepoint is enforced and the v1.0.0 manifest holds.

**Steps**:

1. Create `tests/charter/test_chokepoint_coverage.py` (new, ~150 lines):
   - Use Python's `ast` module.
   - Walk every `.py` file under `src/`.
   - For each file, find every function/method that reads any of the three v1.0.0 manifest derivatives (by file path literal OR by calling `load_governance_config` / `load_directives_config` / `build_charter_context` / etc).
   - Assert the function either directly calls `ensure_charter_bundle_fresh` OR is a delegating wrapper that ultimately calls it.
   - Registry of expected reader sites is seeded from `occurrences/WP03.yaml` (verifiable canary).
   - Carve-outs: `src/charter/sync.py` itself, `src/charter/bundle.py`, `src/charter/resolution.py`, `src/charter/compiler.py`, `src/charter/context.py:385-398` region, `src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py`.

2. Create `tests/charter/test_bundle_contract.py` (new, ~100 lines):
   - Fixture: tmp repo with populated charter.
   - Call `ensure_charter_bundle_fresh(repo)`.
   - Load `CANONICAL_MANIFEST`.
   - Assert every `tracked_file` exists and is tracked in git (via `git ls-files`).
   - Assert every `derived_file` exists after the chokepoint runs.
   - Assert every `gitignore_required_entry` is on its own line in `.gitignore`.
   - Assert `SyncResult.canonical_root` equals the repo path.
   - Optional: enumerate files under `.kittify/charter/` not in the manifest; verify they're not flagged as missing.

**Files**:
- `tests/charter/test_chokepoint_coverage.py` (new, ~150 lines)
- `tests/charter/test_bundle_contract.py` (new, ~100 lines)

**Validation**:
- [ ] `pytest tests/charter/test_chokepoint_coverage.py tests/charter/test_bundle_contract.py` green.

---

### T022 — Write `tests/init/test_fresh_clone_no_sync.py` and `test_worktree_charter_via_canonical_root.py`

**Purpose**: FR-009 (fresh-clone smoke) + FR-010 (worktree transparency).

**Steps**:

1. Create `tests/init/test_fresh_clone_no_sync.py` (new, ~120 lines):
   - Fixture: tmp git repo with `charter.md` tracked, derivatives deleted.
   - Never calls `spec-kitty charter sync` explicitly.
   - Invokes each FR-004 reader once:
     - `build_charter_context(repo_root, action="specify")`
     - `resolve_project_charter_path(repo_root)`
     - A sample CLI handler via Typer runner.
     - A sample next-prompt builder call.
   - After each invocation, assert the three derivatives exist on disk.
   - Assert no `ImportError` or `NotInsideRepositoryError` is raised.

2. Create `tests/charter/test_worktree_charter_via_canonical_root.py` (new, ~130 lines):
   - Fixture: main-checkout repo + one linked worktree via `git worktree add`.
   - Invoke `build_charter_context(worktree_path, action="specify")`.
   - Assert the returned result's internal `sync_result.canonical_root` (or equivalent exposed field) points at the main checkout, NOT the worktree.
   - Assert no files were written inside `<worktree>/.kittify/charter/`.
   - Assert the pre-existing `.kittify/memory` / `.kittify/AGENTS.md` symlinks (if they were set up in the fixture) remain untouched.

**Files**:
- `tests/init/test_fresh_clone_no_sync.py` (new, ~120 lines)
- `tests/charter/test_worktree_charter_via_canonical_root.py` (new, ~130 lines)

**Validation**:
- [ ] Both test modules pass.

---

### T023 — Write `tests/test_dashboard/test_charter_chokepoint_regression.py`

**Purpose**: FR-014 byte-identical regression against the baseline.

**Steps**:

1. Create `tests/test_dashboard/test_charter_chokepoint_regression.py` (new, ~130 lines):
   - Read the committed baseline at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json`.
   - Run the committed `baseline/capture.py` again on the current tree (post-cutover code).
   - Apply the same R-4 redactions.
   - Diff the two JSON objects; assert byte-identical.

   Provide a clear diff message on failure (show the unified diff of the two JSON payloads).

**Files**:
- `tests/test_dashboard/test_charter_chokepoint_regression.py` (new, ~130 lines)

**Validation**:
- [ ] Test passes on post-WP03 code; the byte-identical assertion holds against the committed baseline.

---

### T024 — Author `occurrences/WP03.yaml`

**Purpose**: This is the largest occurrence artifact in the mission. It declares every reader site WP03 flips plus the C-011 / C-012 carve-outs.

**Steps**:

1. Create `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP03.yaml` per the contract schema:

   ```yaml
   wp_id: WP03
   mission_slug: unified-charter-bundle-chokepoint-01KP5Q2G
   requires_merged: [WP01, WP02]
   categories:
     reader_call_site_flip:
       description: "Every reader of v1.0.0 manifest derivatives now routes through ensure_charter_bundle_fresh."
       include: ["src/**"]
       exclude: []
       occurrences:
         - path: src/charter/context.py
           pattern: "build_charter_context"
           action: rewrite
           rewrite_to: "Calls ensure_charter_bundle_fresh() at function head."
         - path: src/specify_cli/cli/commands/charter.py
           pattern: "app.add_typer"
           action: rewrite
           rewrite_to: "Registers charter_bundle_app (from WP01)."
         # ...one entry per R-1 reader site...
     docstring_comment:
       description: "TODO(WP02) markers removed."
       include: ["src/**"]
       exclude: []
       occurrences:
         - path: src/specify_cli/cli/commands/charter_bundle.py
           pattern: "TODO(WP02)"
           action: delete
           rationale: Replaced with real resolve_canonical_repo_root import.
     test_identifier:
       description: "New test modules for this WP."
       include: ["tests/**"]
       exclude: []
       occurrences:
         - path: tests/charter/test_chokepoint_coverage.py
           pattern: "test_.*"
           action: leave
         # ...one entry per new test module...
   carve_outs:
     - path: src/specify_cli/core/worktree.py
       reason: "C-011: .kittify/memory + .kittify/AGENTS.md symlinks are documented-intentional. Lines 478-532 MUST NOT be touched."
     - path: src/charter/compiler.py
       reason: "C-012: compiler pipeline owns references.yaml. Out of v1.0.0 manifest scope."
     - path: src/charter/context.py
       reason: "C-012: context-state.json write path at lines 385-398 is runtime-state. DO NOT TOUCH that region specifically; the rest of the file IS in WP03 scope."
   must_be_zero_after:
     - "TODO(WP02)"
     - "_resolve_canonical_root_TEMP"
     - "read_text_charter_md_direct_bypass"  # symbolic category
   verification_notes: |
     WP03 is the largest WP. Every reader site in FR-004 is flipped. C-011 and C-012
     carve-outs are explicit - verifier will fail the PR if any edit touches those lines.
   ```

2. Extend `occurrences/index.yaml` to add WP03 to the `wps` list and finalize the mission-level carve-outs and must-be-zero set (unchanged from the WP01 seed).

**Files**:
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP03.yaml` (new)
- `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml` (modified)

**Validation**:
- [ ] `python scripts/verify_occurrences.py kitty-specs/.../occurrences/WP03.yaml` exits 0.
- [ ] `git diff main..HEAD -- src/specify_cli/core/worktree.py` shows no changes (C-011 verification).

---

## Definition of Done

- [ ] T016 committed FIRST (baseline capture commit precedes all reader-flip commits).
- [ ] T017–T024 all complete.
- [ ] `pytest tests/charter/test_chokepoint_coverage.py tests/charter/test_bundle_contract.py tests/charter/test_worktree_charter_via_canonical_root.py tests/init/test_fresh_clone_no_sync.py tests/test_dashboard/test_charter_chokepoint_regression.py` green.
- [ ] `pytest tests/` full suite green with NFR-001 budget respected (≤5% runtime regression vs. pre-Phase-2).
- [ ] `mypy --strict` green across all modified files.
- [ ] Verifier green against `WP03.yaml` and `index.yaml`.
- [ ] `diff <(git show main:src/specify_cli/core/worktree.py | sed -n '478,532p') <(sed -n '478,532p' src/specify_cli/core/worktree.py)` is empty (C-011).
- [ ] `grep -n "TODO(WP02)" src/` returns zero rows.
- [ ] The FR-016 grep invariants hold.

## Risks

- **Baseline capture ordering**. If T016 is not the first commit on the WP03 branch, the regression bar is circular.
- **C-011 carve-out violation**. A grep-and-replace edit could accidentally touch `worktree.py:478-532`. The occurrence artifact's explicit `leave` entry + the post-merge grep check are the defense.
- **Duplicate-package miss**. AST-walk test must walk the full `src/` tree including `src/specify_cli/charter/`. If a live reader there is missed, the test fails and the PR is blocked.
- **Dashboard typed-contract drift**. Any change to the scanner's data shape breaks the byte-identical assertion. Route readers through the chokepoint without modifying scan output semantics.

## Reviewer guidance

- Verify T016 commit lands FIRST on the WP03 branch (`git log --oneline`).
- Walk through R-1 reader inventory row-by-row; for each, verify the reader now calls `ensure_charter_bundle_fresh` (or a wrapper that does).
- Verify `git diff main..HEAD -- src/specify_cli/core/worktree.py` is empty.
- Run the dashboard regression test locally; inspect the JSON diff on failure.
- Run `spec-kitty charter bundle validate --json` from both the main checkout and a worktree — the output should be identical.
