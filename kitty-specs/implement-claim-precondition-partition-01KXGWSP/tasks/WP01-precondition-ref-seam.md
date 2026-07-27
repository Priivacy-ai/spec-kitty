---
work_package_id: WP01
title: Partition-aware precondition ref seam (read/compare side)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
- NFR-002
- NFR-004
tracker_refs: []
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1209688"
shell_pid_created_at: "1784064017.67"
history:
- at: '2026-07-14T19:15:00Z'
  actor: claude
  note: WP authored from plan IC-01; revised after post-tasks squad (signature + meta.json + write-side split-out).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement_cores.py
- tests/specify_cli/cli/commands/test_implement_cores.py
- tests/specify_cli/cli/commands/test_implement.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**. Apply TDD/ATDD, type safety, idiomatic Python 3.11+.

## Objective

Fix #2533's reported symptom: the implement-claim precondition compares PRIMARY
planning artifacts against the coordination ref, so a solo PR-bound `coord` mission
whose spec/plan/tasks/**meta.json** are committed on the feature branch aborts the
claim with "Planning artifacts not committed." Introduce one **per-path** pure
resolver and route the compare-side staging through it. (The **write-side**
partition — committing a genuinely-dirty PRIMARY artifact to the primary ref — is
WP02; this WP is the read/compare side that resolves the reported bug.)

**Read `../contracts/resolve-precondition-ref.md` first — it is authoritative and was
corrected after the post-tasks squad.**

## Context (read before coding)

- Spec `../spec.md`; Plan `../plan.md`; data-model `../data-model.md`.
- **Root cause**: `resolve_planning_artifact_staging` (`implement_cores.py:454`) hands
  ONE `coord_branch_for_filter` to every helper as the comparison ref. `_files_changed_vs_ref:406`
  loops files diffing each against that single ref; `_committed_meta_mapping:246` and
  `_drop_runtime_frontmatter_only_wp:350` use `ref or "HEAD"`. On a coord mission the
  ref is the coord branch → PRIMARY artifacts absent there read as "changed" → abort
  (`implement.py` message at `:319`, `raise typer.Exit(1)` at `:342`, on the
  `auto_commit=False` path).
- **Partition authority (reuse, no new literal — NFR-004)**: `is_coordination_artifact_residue_path`
  (exported from `mission_runtime`, None-safe). Do NOT use
  `is_primary_artifact_kind(kind_for_mission_file(path))` — `kind_for_mission_file("…meta.json")`
  is `None` → mypy-strict error + misroutes `meta.json` to coord.

### Boundary guards (MUST NOT touch — C-001, C-002)
- `_resolve_claim_commit_target` (status commits stay coord); `mission_runtime/*`
  read-only; keep `_placement_coord_filter` return type `str | None`.
- Additive change inside `implement_cores.py` only — do NOT edit `implement.py` /
  `tasks_move_task.py` source (WP02 owns the write-side implement.py edit; the public
  `resolve_planning_artifact_staging` signature stays stable, so the call sites need
  no change and `tasks_move_task.py` is untouched — hence no PR #2639 rebase concern).

## Subtasks

### T001 — Author RED tests first (unit + integration repro)

1. In `test_implement_cores.py`, add pure unit tests for the not-yet-existing
   `resolve_precondition_ref(repo_rel_path, coord_branch_for_filter)`:
   - `resolve_precondition_ref("kitty-specs/m/spec.md", "kitty/…coord") == "HEAD"`
   - `resolve_precondition_ref("kitty-specs/m/meta.json", "kitty/…coord") == "HEAD"` (BLOCKER-2 case)
   - `resolve_precondition_ref("kitty-specs/m/status.events.jsonl", "kitty/…coord") == "kitty/…coord"`
   - `resolve_precondition_ref("kitty-specs/m/spec.md", None) == "HEAD"`
2. In `test_implement.py`, add an integration repro modeled on
   `test_committing_content_already_on_coord_is_noop:108` (real `tmp_path` git repo,
   `_make_meta(..., with_coord=True)`): a solo PR-bound coord mission with
   `spec.md`/`plan.md`/`tasks.md`/`lanes.json`/`meta.json` committed on the **feature
   branch**, absent on the empty coord branch. Drive `_ensure_planning_artifacts_committed_git`
   **with `auto_commit=False`** (required for the abort path).
3. Assert CURRENT (buggy) behavior so tests are RED: `resolve_planning_artifact_staging`
   returns a non-empty set for those artifacts / the gate raises `typer.Exit(1)`.

**Validation**: new tests FAIL against current code.

### T002 — Add the per-path pure resolver

Add to `implement_cores.py` per the contract:

```python
def resolve_precondition_ref(repo_rel_path: str, coord_branch_for_filter: str | None) -> str:
    if coord_branch_for_filter and is_coordination_artifact_residue_path(repo_rel_path):
        return coord_branch_for_filter
    return "HEAD"
```

Import `is_coordination_artifact_residue_path` from `mission_runtime` (extend the
existing import block at `implement_cores.py:31`). Complexity ≤ 15; pure.

### T003 — Route the staging core through the resolver (keep helper signatures stable)

Preferred design (renata option b — minimal test churn): inside
`resolve_planning_artifact_staging`, **partition** `files` into PRIMARY (→ `"HEAD"`)
and COORD-residue (→ `coord_branch_for_filter`) groups via `resolve_precondition_ref`,
and call the existing `_files_changed_vs_ref(repo_root, group, ref)` once per group —
keeping its `(repo_root, files, ref)` signature intact. For the single-path helpers
`_committed_meta_mapping:246` and `_drop_runtime_frontmatter_only_wp:350`, resolve the
ref per their own path via `resolve_precondition_ref` (replacing `ref or "HEAD"`).

**Validation**: T001 unit + integration tests pass; existing coord behavior preserved;
`meta.json` on a coord mission resolves to `"HEAD"` and drops from the staging set.

### T004 — Re-pin the one changed test + add invariant tests

- **Re-pin ONLY `test_implement_cores.py:287`** (`test_no_ref_returns_all_files`): the
  `None → return all files` short-circuit is gone (callers pass a concrete ref). Re-pin
  to the new reality (or delete if the None input is unreachable). **Do NOT touch
  `:290`** (`test_missing_source_file_is_skipped`) — orthogonal, still valid.
- Add invariant tests: dirty `spec.md` still staged (INV-5); dirty
  `status.events.jsonl` on a coord mission still resolves to the coord ref (coord
  non-regression, NFR-002); `meta.json` on coord → `HEAD` (BLOCKER-2 lock).

### T005 — Campsite (S108) + quality gates

- **S108 (ADJACENT)**: delete the dead `if TYPE_CHECKING:\n    pass` at
  `implement_cores.py:46-47` **and** remove the now-unused `TYPE_CHECKING` from the
  `:29` import (else ruff F401 fires).
- `uv run ruff check src/specify_cli/cli/commands/implement_cores.py`;
  `uv run mypy --strict src/specify_cli/cli/commands/implement_cores.py`; touched tests
  green. Zero new issues; complexity ≤ 15; no new kind→partition literal.

## Branch Strategy

- Planning/base + merge target: `mission/2533-pr-bound-coord-claim-precondition`
  (mission lands via a manual PR to `upstream/main`). Worktree allocated per lane from
  `lanes.json` by `spec-kitty agent action implement WP01 --agent claude`.

## Definition of Done

- [ ] `resolve_precondition_ref(repo_rel_path, coord_branch_for_filter)` exists, pure, per contract.
- [ ] Staging core routes through it (group-partition); helper public signatures stable.
- [ ] Integration repro GREEN (incl. `meta.json`); topology unchanged.
- [ ] `test_implement_cores.py:287` re-pinned; `:290` untouched; invariant tests added.
- [ ] S108 folded (+ `TYPE_CHECKING` import removed); ruff + mypy --strict zero new issues.
- [ ] Boundary guards untouched; no `implement.py`/`tasks_move_task.py` source edit.

## Risks & Reviewer Guidance

- **meta.json trap** — reviewer confirms `meta.json` on a coord mission resolves to
  `HEAD` (the fix is worthless if it doesn't; it's the file `_committed_meta_mapping`
  exists for).
- **No `is_primary_artifact_kind(None)`** — confirm the None-safe residue predicate is
  used, not the kind-based form that trips mypy-strict.
- **Signature stability** — confirm `resolve_planning_artifact_staging` public
  signature is unchanged (so no call-site / `tasks_move_task.py` edit leaks in).
- **Red-first** — the integration test must be authored to fail against pre-fix code
  with `auto_commit=False`.

## Activity Log

- 2026-07-14T20:50:54Z – claude:sonnet:python-pedro:implementer – shell_pid=1140838 – Assigned agent via action command
- 2026-07-14T21:19:15Z – claude:sonnet:python-pedro:implementer – shell_pid=1140838 – Ready for review
- 2026-07-14T21:20:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=1209688 – Started review via action command
- 2026-07-14T21:26:47Z – user – shell_pid=1209688 – Review passed: per-path resolve_precondition_ref uses None-safe is_coordination_artifact_residue_path (meta.json->HEAD, BLOCKER-2 locked by unit + staging-core + integration tests); red-first integration repro raises typer.Exit(1) 'Planning artifacts not committed' listing meta.json against PRE-FIX source, green post-fix; only 3 owned files touched, no implement.py/tasks_move_task.py/mission_runtime edits; signatures stable (_placement_coord_filter str|None, resolve_planning_artifact_staging unchanged); staging re-pins + issue-matrix fixture swap are valid contract re-pins; :287 untouched; S108 folded; ruff+mypy --strict clean, 69 tests green; NFR-004 no new literal.
