---
work_package_id: WP04
title: 'merge.py: validator delegate + collapse containment helpers (sole merge.py owner)'
dependencies:
- WP01
- WP03
requirement_refs:
- FR-002
- FR-003
- FR-006
- NFR-001
tracker_refs:
- '#2022'
planning_base_branch: feat/canonical-seams-path-trust-guard-capability
merge_target_branch: feat/canonical-seams-path-trust-guard-capability
branch_strategy: Planning artifacts for this mission were generated on feat/canonical-seams-path-trust-guard-capability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/canonical-seams-path-trust-guard-capability unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "3698747"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/merge.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
- tests/specify_cli/cli/commands/test_merge.py
- tests/merge/test_merge_done_recording.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read:
1. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/spec.md` — **FR-002, FR-003, FR-006**, and
   **C-007** (binding non-goals) + **NFR-001** (behavior-preserving).
2. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/research.md` — **§(c)** sibling seams,
   **§(d)/D-3** the three helpers + which collapse vs the XOR holdout, **D-6** (this WP is the sole merge.py owner).
3. `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/contracts/seam-signatures.md` — delegation
   targets.

## Objective

WP04 is the **sole owner of `merge.py`**. It carries BOTH halves that touch this file (D-6, overlap-free
ownership): Goal A's validator delegate AND Goal B's containment-helper collapse. **Depends on WP01** (the
canonical validator) and **WP03** (`ensure_within_any`). All changes are behavior-preserving (NFR-001).

Start command (after WP01 + WP03 approved): `spec-kitty agent action implement WP04 --agent <name>`.

## Subtasks

### T014 — Delegate `_validate_mission_slug_path_segment` + FR-003 sibling-seam reject test
**Purpose:** migrate merge.py's validator to the canonical authority (keep `ValueError`); prove the #2019 sibling
seams now inherit the guard. At `merge.py:774`:
- Replace the inline `_MISSION_SLUG_PATH_SEGMENT_RE`/checks with a call to `assert_safe_path_segment(mission_slug)`
  (returns the validated value; already raises `ValueError`, matching the existing test `match="single safe path
  segment"` — adjust the test's match string only if the canonical message differs, see T019).
- Remove the dead `_MISSION_SLUG_PATH_SEGMENT_RE` constant (:102) once unused. Make "removed" a RED/GREEN gate, not
  honor-system: paste `grep -n _MISSION_SLUG_PATH_SEGMENT_RE src/specify_cli/cli/commands/merge.py` showing zero
  hits into the handoff (or add a tiny assertion that the symbol is absent from the module).
- **FR-003 test** in `tests/specify_cli/cli/commands/test_merge.py` (un-fakeable — squad flag): call
  `_assert_status_path_within_target_surface(repo_root=..., mission_slug="../escape", candidate=...)` **DIRECTLY**
  (it calls `primary_feature_dir_for_mission` at `:828`) and assert `ValueError`; add a SECOND test driving the
  `:2382` `target_feature_dir` path. **The test MUST exercise these named sibling functions — NOT be satisfiable
  via `_target_bookkeeping_status_paths`** (already covered), else it proves nothing new. **RED-first:** write
  these assertions BEFORE the delegate edit (they fail until the WP01 primitive guard + this delegate land).
  (Validation fires in the WP01 primitive; these prove the sibling call paths reach it.)

### T015 — dry-run/abort sites catch the ValueError → clean `--abort` diagnostic
**Purpose:** keep `--abort`/dry-run UX clean (research.md §(b)). `_resolve_mission_slug` (:1429) returns a RAW handle
in some branches; its consumers at `:3100`/`:3194`/`:3212` only catch `MissingLanesError`/`CorruptLanesError`. A
malformed `--mission` now raises `ValueError` from the validating primitive.
- At those dry-run/abort sites, catch the validator `ValueError` and surface a clean diagnostic (the same
  "single safe path segment"-style message), not an uncaught traceback.
- Add a test: `merge --abort --mission "../x"` (or the dry-run path) → assert the emitted message **contains the
  "single safe path segment" text** AND a non-zero exit. (A bare `except: raise typer.Exit(1)` with no message
  avoids a traceback but is NOT a clean diagnostic — the message assertion forecloses that gaming path.)

### T016 — Collapse `_assert_status_path_within_target_surface` → ensure_within_any
At `merge.py:820`: replace the body with `ensure_within_any(candidate, roots=[surface_root])` where `surface_root`
is the existing `primary_feature_dir_for_mission(...)` computed root. Behavior byte-identical (single-root
containment). Keep the function name/signature (callers untouched).

### T017 — Collapse `_assert_bookkeeping_snapshot_path_is_trusted` → ensure_within_any (files arm)
At `merge.py:865`: replace the body with `ensure_within_any(candidate, roots=[<the 3 dirs>], files=[<.kittify/
merge-state.json>])`. The 3 dirs (`KITTY_SPECS_DIR`, `WORKTREES_DIR`, `KITTIFY_DIR/runtime/merge`) + the exact-file
allowlist (`KITTIFY_DIR/merge-state.json`) are the EXISTING trusted set — do NOT change the set (NFR-001). Keep the
function name/signature. **Add a trusted-set pin test:** a path under each of the 3 dirs AND the exact file are
ACCEPTED, and a path outside all 4 is REJECTED — so a future drop of (e.g.) `KITTIFY_DIR/runtime/merge` turns RED.

### T018 — Keep `_assert_status_surface_path_is_trusted` as a conditional caller (NO union-widening)
At `merge.py:837`: this helper selects its root by `is_under_worktrees_segment(status_feature_dir)` (worktrees XOR
kitty-specs). **Do NOT fold it into a `roots=[worktrees, kitty-specs]` union** — that would accept a kitty-specs
path while under-worktrees, a behavior change (research.md §(d)). Instead: keep the conditional that picks the
single correct root, THEN delegate to `ensure_within_any(path, roots=[selected_root])`. (It still delegates — only
root *selection* stays inline; after this WP all three containment helpers route through the kernel util.)
- **Un-fakeable XOR test (squad flag):** construct a path that **IS under the kitty-specs root** but where
  `is_under_worktrees_segment(status_feature_dir)` is **True**, and assert it is **REJECTED**. This fixture FAILS
  under a `roots=[worktrees, kitty-specs]` union (union would accept it) and PASSES only under correct XOR root
  selection. A weak fixture that resolves outside both roots would pass even a union — so pin the topology
  explicitly. **RED-first:** write this before converting the helper.

### T019 — Behavior-preserving suites green + quality gate
- Run `tests/specify_cli/cli/commands/test_merge.py` and `tests/merge/test_merge_done_recording.py` green
  (behavior-preserving). Update only assertion strings that legitimately changed (e.g. the validator message), and
  record each such change in the handoff.
- `ruff`+`mypy` clean on `merge.py` (≤15, no suppressions). **Diff-scoped lint sweep** before handoff.
- **C-008 Fix-don't-litigate:** if you hit adjacent breakage in a touched merge.py region, fix it in this change.

## Branch Strategy

Planning/merge base `feat/canonical-seams-path-trust-guard-capability` (PR → main). Worktree per lane from
`lanes.json`. **Depends on WP01 + WP03** — implement after both are approved.

## Definition of Done

- [ ] `_validate_mission_slug_path_segment` delegates to `assert_safe_path_segment` (keeps `ValueError`); dead constant removed.
- [ ] FR-003 test proves a malformed slug rejected at a sibling seam (`:828`/`:2382`).
- [ ] dry-run/abort sites catch the `ValueError` → clean diagnostic (tested).
- [ ] The two pure-root helpers delegate to `ensure_within_any`; the file-arm preserved.
- [ ] `_assert_status_surface_path_is_trusted` stays a conditional caller (XOR preserved, tested) — no union-widening.
- [ ] merge suites green; `ruff`+`mypy` clean.

## Risks / reviewer guidance

- **The XOR holdout (T018) is the highest-risk item.** Reviewer: verify it was NOT collapsed into a union — the
  worktrees-vs-kitty-specs distinction must be byte-preserved, with a test.
- **No trusted-root SET change** (T017): the 3 dirs + the merge-state.json file are exactly today's set.
- **Single-owner invariant (D-6):** this WP must be the ONLY one touching `merge.py`. If a diff hunk in another WP
  also touches merge.py, that is an ownership violation — flag it.
- Reviewer: confirm no write-topology/rollback-semantics change (C-007) — only the containment-check internals move
  to the kernel util.

## Activity Log

- 2026-06-17T20:36:30Z – claude:sonnet:python-pedro:implementer – shell_pid=3698747 – Assigned agent via action command
